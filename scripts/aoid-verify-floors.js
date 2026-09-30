#!/usr/bin/env node
/**
 * Floor-transfer check for the Articles of Interfaith Discipleship (AoID).
 *
 * Enforces codex A4(a) and A4(d) (Comparison_Principles_Codex.md): a span's written scope note IS its
 * apparatus `panel_comment`; where a floor was ratified before its span existed, the floor is held in
 * its ratified document (data-sources/aoid/floors/) and the panel_comment is transcribed from it
 * verbatim. This script reads data-sources/aoid/floor_ledger.yaml and, for every item under `scored:`,
 * puts each item in exactly one state:
 *
 *   TRANSFERRED  the ledger names a span, the span exists in src/_data/apparatusData.json, and its
 *                panel_comment equals the ratified floor text (after whitespace normalisation).
 *   PENDING      the ledger names no span (span: null). Lawful under A4(d). Does not fail the run.
 *   FAILED       anything else: span absent, no panel_comment, panel_comment differs from the floor,
 *                floor document or heading not found (or ambiguous), floor text changed since its
 *                recorded hash (a floor changed without a ruling), hash not yet recorded, or a
 *                malformed ledger entry. Exits non-zero.
 *
 * Usage:
 *   node scripts/aoid-verify-floors.js                  run the check
 *   node scripts/aoid-verify-floors.js --record-hashes  fill empty floor_sha256 values in the ledger
 *                                                       (never overwrites a recorded hash)
 *   Overrides, for testing without touching the repo: --ledger <file> --apparatus <file> --root <dir>
 *
 * NORMALISATION (used for the hash and for the comparison, identical in both):
 *   1. Take the floor's blockquote lines and strip one leading ">" and any spaces after it.
 *   2. Join the lines, then replace every run of Unicode whitespace (regex \s+) with one space.
 *   3. Trim leading and trailing whitespace.
 *   Nothing else: no case folding, no Unicode normalisation, no quote or dash changes. The hash is
 *   SHA-256 of the UTF-8 bytes of the result. The panel_comment is normalised by steps 2 and 3.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const yaml = require("js-yaml");

const args = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 ? path.resolve(args[i + 1]) : dflt;
};
const ROOT = opt("--root", path.join(__dirname, ".."));
const LEDGER = opt("--ledger", path.join(ROOT, "data-sources", "aoid", "floor_ledger.yaml"));
const APPARATUS = opt("--apparatus", path.join(ROOT, "src", "_data", "apparatusData.json"));
const RECORD = args.includes("--record-hashes");

const SPAN_RE = /^A\d{2}\.s\d+$/;
const HASH_RE = /^[0-9a-f]{64}$/;
const norm = (s) => s.replace(/\s+/g, " ").trim();
const sha = (s) => crypto.createHash("sha256").update(s, "utf8").digest("hex");

/** First difference between two strings, with a little context, for a failure message. */
function describeDiff(floor, comment) {
  let i = 0;
  while (i < floor.length && i < comment.length && floor[i] === comment[i]) i++;
  const cut = (s) => JSON.stringify(s.slice(Math.max(0, i - 15), i + 40));
  return `first difference at character ${i} (floor ${floor.length} chars, panel_comment ${comment.length} chars): floor ...${cut(floor)} vs panel_comment ...${cut(comment)}`;
}

/**
 * The floor is the blockquote after the line beginning "**Panel comment (the floor)" inside the
 * section whose "## " heading line is exactly `## <heading>`. Returns {text} or {error}.
 */
function extractFloor(docPath, heading) {
  if (!fs.existsSync(docPath)) return { error: `floor document not found: ${docPath}` };
  const lines = fs.readFileSync(docPath, "utf8").split(/\r?\n/);
  const starts = lines.reduce((a, l, i) => (l.trimEnd() === `## ${heading}` ? a.concat(i) : a), []);
  if (starts.length === 0) return { error: `floor heading not found: "## ${heading}"` };
  if (starts.length > 1) return { error: `floor heading is ambiguous (${starts.length} matches): "## ${heading}"` };
  let end = lines.length;
  for (let i = starts[0] + 1; i < lines.length; i++) if (/^## /.test(lines[i])) { end = i; break; }
  const labels = [];
  for (let i = starts[0] + 1; i < end; i++) if (lines[i].startsWith("**Panel comment (the floor)")) labels.push(i);
  if (labels.length !== 1) return { error: `expected exactly one "**Panel comment (the floor)" line under "## ${heading}", found ${labels.length}` };
  let i = labels[0] + 1;
  while (i < end && lines[i].trim() === "") i++;
  const quote = [];
  while (i < end && lines[i].startsWith(">")) quote.push(lines[i++].replace(/^>\s?/, ""));
  if (quote.length === 0) return { error: `no blockquote follows the "**Panel comment (the floor)" line under "## ${heading}"` };
  // A blank line inside the floor would end the blockquote in markdown; a second quote block is ambiguous.
  while (i < end && lines[i].trim() === "") i++;
  if (i < end && lines[i].startsWith(">")) return { error: `a second blockquote follows the floor under "## ${heading}"; floor cannot be located unambiguously` };
  const text = norm(quote.join(" "));
  if (!text) return { error: `floor blockquote under "## ${heading}" is empty` };
  return { text };
}

const results = [];
const loud = []; // ledger-level problems, reported separately
const fatal = (m) => { console.error(`LEDGER PROBLEM: ${m}`); process.exit(2); };

if (!fs.existsSync(LEDGER)) fatal(`ledger not found: ${LEDGER}`);
let ledgerRaw = fs.readFileSync(LEDGER, "utf8");
let ledger;
try { ledger = yaml.load(ledgerRaw); } catch (e) { fatal(`ledger is not valid YAML: ${e.message}`); }
if (!ledger || !Array.isArray(ledger.scored)) fatal("ledger has no `scored:` list");

let apparatus = null;
if (!fs.existsSync(APPARATUS)) fatal(`apparatus data not found: ${APPARATUS}`);
try { apparatus = JSON.parse(fs.readFileSync(APPARATUS, "utf8")); } catch (e) { fatal(`apparatus data is not valid JSON: ${e.message}`); }

const seen = new Set();
const toRecord = []; // {item, hash}

for (const [n, e] of ledger.scored.entries()) {
  const label = e && e.item !== undefined ? String(e.item) : `scored[${n}]`;
  const r = { item: label, state: "FAILED", span: null, doc: e && e.floor_document, detail: "" };
  results.push(r);

  const missing = ["item", "floor_document", "floor_heading", "span", "floor_sha256"].filter((k) => !e || !(k in e));
  if (missing.length) { r.malformed = true; r.detail = `malformed ledger entry: missing ${missing.join(", ")}`; loud.push(r); continue; }
  if (seen.has(label)) { r.malformed = true; r.detail = "malformed ledger entry: duplicate item"; loud.push(r); continue; }
  seen.add(label);
  if (e.span !== null && !(typeof e.span === "string" && SPAN_RE.test(e.span))) {
    r.malformed = true; r.detail = `malformed ledger entry: span must be null or like "A03.s2", got ${JSON.stringify(e.span)}`; loud.push(r); continue;
  }
  if (typeof e.floor_sha256 !== "string" || (e.floor_sha256 !== "" && !HASH_RE.test(e.floor_sha256))) {
    r.malformed = true; r.detail = "malformed ledger entry: floor_sha256 must be empty or 64 lowercase hex characters"; loud.push(r); continue;
  }
  r.span = e.span;

  const floor = extractFloor(path.join(ROOT, e.floor_document), e.floor_heading);
  if (floor.error) { r.floorMissing = true; r.detail = floor.error; loud.push(r); continue; }
  const hash = sha(floor.text);

  if (e.floor_sha256 === "") {
    if (RECORD) toRecord.push({ item: label, hash });
    else { r.detail = "floor_sha256 not recorded in the ledger; run with --record-hashes once, after the floor is confirmed"; continue; }
  } else if (e.floor_sha256 !== hash) {
    r.detail = `floor changed without a ruling: hash now ${hash}, ledger records ${e.floor_sha256}`;
    continue;
  }

  if (e.span === null) { r.state = "PENDING"; r.detail = "no span yet (lawful under A4(d))"; continue; }

  const [art, sp] = e.span.split(".");
  const node = apparatus && apparatus[art] && apparatus[art][sp];
  if (!node) { r.detail = `span ${e.span} does not exist in apparatusData.json`; continue; }
  const pc = typeof node.panel_comment === "string" ? node.panel_comment : "";
  if (!norm(pc)) { r.detail = `span ${e.span} has no panel_comment`; continue; }
  if (norm(pc) !== floor.text) { r.detail = `panel_comment does not match the ratified floor: ${describeDiff(floor.text, norm(pc))}`; continue; }
  r.state = "TRANSFERRED"; r.detail = "panel_comment matches the ratified floor";
}

if (RECORD) {
  // Fill only empty values, by text edit, so the ledger's comments and layout are kept.
  let out = ledgerRaw;
  for (const { item, hash } of toRecord) {
    const re = new RegExp(`(- item: ${item.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\r?\\n(?:(?!\\n\\s*- item:)[\\s\\S])*?floor_sha256: )""`);
    if (!re.test(out)) fatal(`could not locate floor_sha256 for item ${item} in the ledger text`);
    out = out.replace(re, `$1"${hash}"`);
  }
  if (out !== ledgerRaw) { fs.writeFileSync(LEDGER, out); console.log(`Recorded ${toRecord.length} floor hash(es) in ${path.relative(ROOT, LEDGER)}.`); }
  else console.log("No empty floor_sha256 values to record.");
}

console.log("AoID floor-transfer check (codex A4(a), A4(d))");
console.log("States: TRANSFERRED = panel_comment matches floor | PENDING = no span yet, lawful | FAILED = does not meet A4(d)\n");
for (const r of results) {
  console.log(`  ${r.item}: ${r.state}`);
  console.log(`      span:           ${r.span === null ? "none" : r.span || "(unreadable)"}`);
  console.log(`      floor document: ${r.doc || "(unreadable)"}`);
  console.log(`      ${r.detail}`);
}

const pend = Array.isArray(ledger.pending_floors) ? ledger.pending_floors : [];
console.log(`\nPending floors (ratified, not yet scored; nothing to test): ${pend.length}`);
const pendProblems = [];
for (const p of pend) {
  const ok = p && p.document && fs.existsSync(path.join(ROOT, p.document));
  console.log(`  ${p && p.items}: ${p && p.document} ${ok ? "" : "  <-- DOCUMENT NOT FOUND"}`);
  if (!ok) pendProblems.push(p && p.document);
}

const failed = results.filter((r) => r.state === "FAILED");
const t = results.filter((r) => r.state === "TRANSFERRED").length;
const pd = results.filter((r) => r.state === "PENDING").length;
if (loud.length || pendProblems.length) {
  console.error("\n*** LEDGER / FLOOR PROBLEMS (an entry cannot be checked at all) ***");
  for (const r of loud) console.error(`  ${r.item}: ${r.detail}`);
  for (const d of pendProblems) console.error(`  pending floor document not found: ${d}`);
}
console.log(`\n${t} transferred, ${pd} pending, ${failed.length} failed.`);
process.exit(failed.length || pendProblems.length ? 1 : 0);
