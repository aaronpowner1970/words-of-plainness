#!/usr/bin/env node
/**
 * Floor-transfer check for the Articles of Interfaith Discipleship (AoID).
 *
 * Enforces codex A4(a) and A4(d) (Comparison_Principles_Codex.md): a span's written scope note IS its
 * apparatus `panel_comment`; where a floor was ratified before its span existed, the floor is held in
 * its ratified document (data-sources/aoid/floors/) and the panel_comment is transcribed from it
 * verbatim. This script reads data-sources/aoid/floor_ledger.yaml and, for every item under `scored:`,
 * puts each span of the item in exactly one state:
 *
 *   TRANSFERRED  the ledger names the span, the span exists in src/_data/apparatusData.json, and its
 *                panel_comment equals the ratified floor text (after whitespace normalisation).
 *   PENDING      the ledger names no span (span: null). Lawful under A4(d). Does not fail the run.
 *   FAILED       anything else: span absent, no panel_comment, panel_comment differs from the floor,
 *                floor document, heading or anchor not found (or ambiguous), floor text changed since
 *                its recorded hash (a floor changed without a ruling), hash not yet recorded, or a
 *                malformed ledger entry. Exits non-zero.
 *
 * `span` may be null, one span string, or a list of span strings; each span is checked on its own and
 * reported on its own. `floor_heading` may be a heading at level 2, 3 or 4 of the floor document.
 * The optional `floor_anchor` selects the floor inside a section that holds more than one blockquote
 * (see extractFloor). The rules are set out in data-sources/aoid/FLOOR_CHECK.md.
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
 * The section is the one whose heading line (level 2, 3 or 4) has exactly the text `heading`; it ends
 * at the next heading of the same or higher level.
 *   Without `anchor`: the floor is the blockquote after the one line beginning
 *     "**Panel comment (the floor)" in the section (a second blockquote after it is an error).
 *   With `anchor`: the anchor text must occur in exactly one line of the section (the heading line
 *     counts as part of the section), and the floor is
 *     the first blockquote after that line; the label line is not required.
 * Returns {text} or {error}.
 */
function extractFloor(docPath, heading, anchor) {
  if (!fs.existsSync(docPath)) return { error: `floor document not found: ${docPath}` };
  const lines = fs.readFileSync(docPath, "utf8").split(/\r?\n/);
  const headingOf = (l) => { const m = /^(#{1,6}) (.*)$/.exec(l.trimEnd()); return m ? { level: m[1].length, text: m[2] } : null; };
  const starts = [];
  lines.forEach((l, i) => {
    const h = headingOf(l);
    if (h && h.level >= 2 && h.level <= 4 && h.text === heading) starts.push({ i, level: h.level });
  });
  if (starts.length === 0) return { error: `floor heading not found at level 2, 3 or 4: "${heading}"` };
  if (starts.length > 1) return { error: `floor heading is ambiguous (${starts.length} matches): "${heading}"` };
  const start = starts[0].i;
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    const h = headingOf(lines[i]);
    if (h && h.level <= starts[0].level) { end = i; break; }
  }
  const takeQuote = (from) => {
    const quote = [];
    let i = from;
    while (i < end && lines[i].startsWith(">")) quote.push(lines[i++].replace(/^>\s?/, ""));
    return { quote, next: i };
  };

  let quote;
  if (anchor !== undefined) {
    const hits = [];
    for (let i = start; i < end; i++) if (lines[i].includes(anchor)) hits.push(i);
    if (hits.length === 0) return { error: `floor_anchor not found in the section "${heading}": ${JSON.stringify(anchor)}` };
    if (hits.length > 1) return { error: `floor_anchor found on ${hits.length} lines of the section "${heading}" (must be exactly one): ${JSON.stringify(anchor)}` };
    let i = hits[0] + 1;
    while (i < end && !lines[i].startsWith(">")) i++;
    quote = takeQuote(i).quote;
    if (quote.length === 0) return { error: `no blockquote follows floor_anchor ${JSON.stringify(anchor)} in the section "${heading}"` };
  } else {
    const labels = [];
    for (let i = start + 1; i < end; i++) if (lines[i].startsWith("**Panel comment (the floor)")) labels.push(i);
    if (labels.length !== 1) return { error: `expected exactly one "**Panel comment (the floor)" line under "${heading}", found ${labels.length}` };
    let i = labels[0] + 1;
    while (i < end && lines[i].trim() === "") i++;
    const t = takeQuote(i);
    quote = t.quote;
    if (quote.length === 0) return { error: `no blockquote follows the "**Panel comment (the floor)" line under "${heading}"` };
    // A blank line inside the floor would end the blockquote in markdown; a second quote block is ambiguous.
    i = t.next;
    while (i < end && lines[i].trim() === "") i++;
    if (i < end && lines[i].startsWith(">")) return { error: `a second blockquote follows the floor under "${heading}"; floor cannot be located unambiguously` };
  }
  const text = norm(quote.join(" "));
  if (!text) return { error: `floor blockquote under "${heading}" is empty` };
  return { text };
}

const results = []; // one per ledger item: {item, doc, units: [{span, state, detail}]}
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
  const r = { item: label, doc: e && e.floor_document, units: [] };
  results.push(r);
  // An item-level problem applies to every span of the item.
  const failAll = (detail, spans) => {
    const list = spans && spans.length ? spans : [null];
    r.units = list.map((span) => ({ span, state: "FAILED", detail }));
  };
  const malformed = (detail) => { failAll(detail); loud.push({ item: label, detail }); };

  const missing = ["item", "floor_document", "floor_heading", "span", "floor_sha256"].filter((k) => !e || !(k in e));
  if (missing.length) { malformed(`malformed ledger entry: missing ${missing.join(", ")}`); continue; }
  if (seen.has(label)) { malformed("malformed ledger entry: duplicate item"); continue; }
  seen.add(label);

  const spans = e.span === null ? [null] : Array.isArray(e.span) ? e.span : [e.span];
  const spanOk = (s) => typeof s === "string" && SPAN_RE.test(s);
  if (e.span !== null && (spans.length === 0 || !spans.every(spanOk))) {
    malformed(`malformed ledger entry: span must be null, a span like "A03.s2", or a non-empty list of such spans, got ${JSON.stringify(e.span)}`); continue;
  }
  if (new Set(spans).size !== spans.length) { malformed("malformed ledger entry: a span is listed twice"); continue; }
  if (typeof e.floor_sha256 !== "string" || (e.floor_sha256 !== "" && !HASH_RE.test(e.floor_sha256))) {
    malformed("malformed ledger entry: floor_sha256 must be empty or 64 lowercase hex characters"); continue;
  }
  if ("floor_anchor" in e && (typeof e.floor_anchor !== "string" || !e.floor_anchor.trim())) {
    malformed("malformed ledger entry: floor_anchor, when given, must be a non-empty string"); continue;
  }

  const floor = extractFloor(path.join(ROOT, e.floor_document), e.floor_heading, "floor_anchor" in e ? e.floor_anchor : undefined);
  if (floor.error) { failAll(floor.error, spans); loud.push({ item: label, detail: floor.error }); continue; }
  const hash = sha(floor.text);

  if (e.floor_sha256 === "") {
    if (RECORD) toRecord.push({ item: label, hash });
    else { failAll("floor_sha256 not recorded in the ledger; run with --record-hashes once, after the floor is confirmed", spans); continue; }
  } else if (e.floor_sha256 !== hash) {
    failAll(`floor changed without a ruling: hash now ${hash}, ledger records ${e.floor_sha256}`, spans);
    continue;
  }

  for (const span of spans) {
    const u = { span, state: "FAILED", detail: "" };
    r.units.push(u);
    if (span === null) { u.state = "PENDING"; u.detail = "no span yet (lawful under A4(d))"; continue; }
    const [art, sp] = span.split(".");
    const node = apparatus && apparatus[art] && apparatus[art][sp];
    if (!node) { u.detail = `span ${span} does not exist in apparatusData.json`; continue; }
    const pc = typeof node.panel_comment === "string" ? node.panel_comment : "";
    if (!norm(pc)) { u.detail = `span ${span} has no panel_comment`; continue; }
    if (norm(pc) !== floor.text) { u.detail = `panel_comment does not match the ratified floor: ${describeDiff(floor.text, norm(pc))}`; continue; }
    u.state = "TRANSFERRED"; u.detail = "panel_comment matches the ratified floor";
  }
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
  if (r.units.length === 1) {
    const u = r.units[0];
    console.log(`  ${r.item}: ${u.state}`);
    console.log(`      span:           ${u.span === null ? "none" : u.span}`);
    console.log(`      floor document: ${r.doc || "(unreadable)"}`);
    console.log(`      ${u.detail}`);
  } else {
    console.log(`  ${r.item}: ${r.units.length} spans`);
    console.log(`      floor document: ${r.doc || "(unreadable)"}`);
    for (const u of r.units) console.log(`      ${u.span === null ? "none" : u.span}: ${u.state}  ${u.detail}`);
  }
}

const pend = Array.isArray(ledger.pending_floors) ? ledger.pending_floors : [];
console.log(`\nPending floors (ratified, not yet scored; nothing to test): ${pend.length}`);
const pendProblems = [];
for (const p of pend) {
  const ok = p && p.document && fs.existsSync(path.join(ROOT, p.document));
  console.log(`  ${p && p.items}: ${p && p.document} ${ok ? "" : "  <-- DOCUMENT NOT FOUND"}`);
  if (!ok) pendProblems.push(p && p.document);
}

const units = results.flatMap((r) => r.units);
const failed = units.filter((u) => u.state === "FAILED").length;
const t = units.filter((u) => u.state === "TRANSFERRED").length;
const pd = units.filter((u) => u.state === "PENDING").length;
if (loud.length || pendProblems.length) {
  console.error("\n*** LEDGER / FLOOR PROBLEMS (an entry cannot be checked at all) ***");
  for (const l of loud) console.error(`  ${l.item}: ${l.detail}`);
  for (const d of pendProblems) console.error(`  pending floor document not found: ${d}`);
}
console.log(`\n${t} transferred, ${pd} pending, ${failed} failed (counted by span).`);
process.exit(failed || pendProblems.length ? 1 : 0);
