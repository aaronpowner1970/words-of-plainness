#!/usr/bin/env node
/**
 * Build-time guard for Seeking Jesus of Nazareth artwork (src/_data/sjnArtwork.json).
 *
 * Runs twice per build:
 *   - as part of `prebuild` (npm run build, which is what Vercel runs), and
 *   - from src/_data/sjnArtworkCheck.js, so a bare `npx @11ty/eleventy` or
 *     `eleventy --serve` enforces the same rule.
 *
 * Refuses the build when:
 *   1. an item has an unknown status, or its key does not match its id;
 *   2. an APPROVED_DEPLOY item is missing a required field, has unsafe alt text,
 *      or has any expected file missing, empty, or not the pixel size its
 *      srcset descriptor claims;
 *   3. any file in srcDir is not claimed by an APPROVED_DEPLOY item (so a pending
 *      candidate dropped there is caught before passthrough copy publishes it);
 *   4. any file anywhere under src/assets looks like handoff artwork outside
 *      srcDir (SJ-## candidates, storyboards, internal reference sheets);
 *   5. a template calls sjArt("…") with an id the register does not contain.
 *
 * Pending, not-yet-generated and rejected items are allowed in the register.
 * The macro renders nothing for them.
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const DATA = path.join(ROOT, "src", "_data", "sjnArtwork.json");
const STATUSES = ["APPROVED_DEPLOY", "PENDING_USER_SELECTION", "NOT_GENERATED", "REJECTED"];
const FORMATS = ["webp", "jpg"];
const FORBIDDEN_NAMES = [
  /(^|[^a-z])sj-?\d{2}[_-]/i,                 // handoff naming (SJ-01_B_1600.webp, sj-02-…) outside srcDir
  /light-toward-which-we-walk/i,
  /canonical[_-]?mortal[_-]?jesus/i,
  /original[_-]?interfaith[_-]?table/i,
  /collection[_-]?direction/i,
];

// ---- image header readers (enough to read width/height; no dependencies) ----
function jpegSize(buf) {
  if (buf[0] !== 0xff || buf[1] !== 0xd8) return null;
  let i = 2;
  while (i + 9 < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const m = buf[i + 1];
    if (m === 0xd8 || m === 0x01 || (m >= 0xd0 && m <= 0xd7)) { i += 2; continue; }
    const len = buf.readUInt16BE(i + 2);
    if ((m >= 0xc0 && m <= 0xcf) && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) {
      return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
    }
    i += 2 + len;
  }
  return null;
}
function webpSize(buf) {
  if (buf.toString("ascii", 0, 4) !== "RIFF" || buf.toString("ascii", 8, 12) !== "WEBP") return null;
  const kind = buf.toString("ascii", 12, 16);
  if (kind === "VP8 ") return { w: buf.readUInt16LE(26) & 0x3fff, h: buf.readUInt16LE(28) & 0x3fff };
  if (kind === "VP8L") {
    const b = buf.readUInt32LE(21);
    return { w: (b & 0x3fff) + 1, h: ((b >> 14) & 0x3fff) + 1 };
  }
  if (kind === "VP8X") return { w: buf.readUIntLE(24, 3) + 1, h: buf.readUIntLE(27, 3) + 1 };
  return null;
}

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out); else out.push(p);
  }
  return out;
}

function verifyArtwork() {
  const problems = [];
  const fail = (m) => problems.push(m);
  if (!fs.existsSync(DATA)) return { problems: ["src/_data/sjnArtwork.json missing"], approved: [] };
  let reg;
  try { reg = JSON.parse(fs.readFileSync(DATA, "utf8")); }
  catch (e) { return { problems: [`sjnArtwork.json is not valid JSON: ${e.message}`], approved: [] }; }

  const items = reg.items || {};
  const basePath = reg.basePath || "";
  const srcDir = path.join(ROOT, reg.srcDir || "");
  if (!/^\/assets\/images\/[a-z0-9-]+\/$/.test(basePath)) fail(`basePath "${basePath}" must look like /assets/images/<folder>/`);
  if (path.posix.join("src", basePath) !== `${(reg.srcDir || "").replace(/\\/g, "/")}/`) fail(`basePath and srcDir disagree (${basePath} vs ${reg.srcDir})`);

  const claimed = new Set();
  const approved = [];
  for (const [key, a] of Object.entries(items)) {
    if (!a || a.id !== key) { fail(`${key}: key does not match id`); continue; }
    if (!STATUSES.includes(a.status)) { fail(`${key}: unknown status "${a.status}"`); continue; }
    if (a.status !== "APPROVED_DEPLOY") continue;
    approved.push(key);
    for (const f of ["slug", "widths", "formats", "fallbackWidth", "nativeWidth", "nativeHeight", "sizes", "alt"]) {
      if (a[f] === undefined || a[f] === null || a[f] === "") fail(`${key}: approved but "${f}" is missing`);
    }
    if (typeof a.alt === "string" && (a.alt.trim().length < 20 || /["<>]/.test(a.alt))) fail(`${key}: alt text missing, too short, or contains " < >`);
    if (!/^[a-z0-9-]+$/.test(a.slug || "")) fail(`${key}: slug "${a.slug}" must be lowercase letters, digits, hyphens`);
    const widths = Array.isArray(a.widths) ? a.widths : [];
    if (!widths.length || widths.some((w, i) => !Number.isInteger(w) || (i && w <= widths[i - 1]))) fail(`${key}: widths must be ascending integers`);
    if (!widths.includes(a.fallbackWidth)) fail(`${key}: fallbackWidth ${a.fallbackWidth} is not one of the widths`);
    if (Math.max(...widths, 0) > a.nativeWidth) fail(`${key}: a width exceeds nativeWidth`);
    const formats = Array.isArray(a.formats) ? a.formats : [];
    if (!formats.includes("jpg")) fail(`${key}: formats must include jpg (the <img> fallback)`);
    for (const fmt of formats) if (!FORMATS.includes(fmt)) fail(`${key}: unsupported format "${fmt}"`);

    for (const fmt of formats) for (const w of widths) {
      const name = `${a.slug}-${w}.${fmt}`;
      claimed.add(name);
      const p = path.join(srcDir, name);
      if (!fs.existsSync(p)) { fail(`${key}: approved asset missing: ${reg.srcDir}/${name}`); continue; }
      const buf = fs.readFileSync(p);
      if (!buf.length) { fail(`${key}: ${name} is empty`); continue; }
      const dim = fmt === "jpg" ? jpegSize(buf) : webpSize(buf);
      if (!dim) { fail(`${key}: ${name} is not a readable ${fmt}`); continue; }
      const expectH = Math.round((w * a.nativeHeight) / a.nativeWidth);
      if (dim.w !== w || Math.abs(dim.h - expectH) > 2) fail(`${key}: ${name} is ${dim.w}x${dim.h}, expected ${w}x${expectH}`);
    }
  }

  // 3. nothing unapproved in the artwork folder
  for (const p of walk(srcDir)) {
    const name = path.relative(srcDir, p).replace(/\\/g, "/");
    if (!claimed.has(name)) fail(`unapproved or unregistered file in ${reg.srcDir}: ${name}`);
  }
  // 4. no handoff artwork anywhere else under src/assets
  const assets = path.join(ROOT, "src", "assets");
  for (const p of walk(assets)) {
    if (p.startsWith(srcDir + path.sep)) continue;
    const base = path.basename(p);
    if (FORBIDDEN_NAMES.some((re) => re.test(base))) fail(`handoff artwork outside the register: ${path.relative(ROOT, p).replace(/\\/g, "/")}`);
  }
  // 5. every sjArt("…") call names a registered id
  const tpl = walk(path.join(ROOT, "src")).filter((p) => /\.(njk|md|html)$/.test(p) && !p.endsWith(`macros${path.sep}sjn-art.njk`));
  for (const p of tpl) {
    const src = fs.readFileSync(p, "utf8");
    for (const m of src.matchAll(/sjArt\(\s*["']([^"']+)["']\s*\)/g)) {
      if (!items[m[1]]) fail(`${path.relative(ROOT, p).replace(/\\/g, "/")}: sjArt("${m[1]}") is not in sjnArtwork.json`);
    }
  }
  return { problems, approved };
}

module.exports = { verifyArtwork };

if (require.main === module) {
  const { problems, approved } = verifyArtwork();
  if (problems.length) {
    console.error(`[sjn-verify-artwork] FAIL (${problems.length})`);
    for (const p of problems) console.error("  - " + p);
    process.exit(1);
  }
  console.log(`[sjn-verify-artwork] PASS: ${approved.length} approved (${approved.join(", ") || "none"}); no unapproved artwork under src/assets`);
}
