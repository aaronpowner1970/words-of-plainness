#!/usr/bin/env node
/**
 * Build-time guard for the Seeking Jesus of Nazareth data set (runs as `prebuild`).
 *
 * The Python pipeline (scripts/sjn-build-data.py) does the live work: workbook
 * re-validation, live URL fetches, Playwright-rendered scripture pages, PDF
 * normalization, phrase-containment assertions. Its emitted JSON is committed.
 * This verifier refuses the Eleventy build if that committed data set is not a
 * green, live, integrity-checked pipeline run — so nothing stale, cached, or
 * failing can reach a public page, without requiring Python/Playwright on Vercel.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DIR = path.join(__dirname, "..", "src", "_data", "sjn");
const REQUIRED = ["meta.json", "predicates.json", "cells.json", "inferences.json", "godhead.json",
  "vectors.json", "clarifications.json", "glossary.json", "ranges.json"];
const problems = [];
const fail = (m) => problems.push(m);

function sha(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

if (!fs.existsSync(path.join(DIR, "meta.json"))) {
  fail("src/_data/sjn/meta.json missing — run `npm run sjn:pipeline`");
} else {
  const meta = JSON.parse(fs.readFileSync(path.join(DIR, "meta.json"), "utf8"));
  if (meta.status !== "PASS") fail(`meta.status is ${meta.status}`);
  if (meta.blocking_failures !== 0) fail(`blocking_failures = ${meta.blocking_failures}`);
  if (meta.fetch_policy !== "LIVE") fail(`fetch_policy is ${meta.fetch_policy}; committed data must come from a LIVE run`);
  if (!/^[0-9a-f]{64}$/.test(meta.canonical_hash || "")) fail("canonical_hash missing");
  for (const f of REQUIRED) {
    const p = path.join(DIR, f);
    if (!fs.existsSync(p)) { fail(`${f} missing`); continue; }
    if (f === "meta.json") continue;
    const rec = (meta.files || {})[f];
    if (!rec) { fail(`${f} not recorded in meta.files`); continue; }
    const actual = sha(p);
    if (actual !== rec.sha256) fail(`${f} sha256 mismatch (edited after the pipeline run?)`);
    const obj = JSON.parse(fs.readFileSync(p, "utf8"));
    if (obj.canonical_hash !== meta.canonical_hash) fail(`${f} canonical_hash differs from meta`);
  }
  const blockFails = (meta.rules || []).filter((r) => r.severity === "BLOCK" && r.status === "FAIL");
  if (blockFails.length) fail(`BLOCK rules failing: ${blockFails.map((r) => r.rule).join(", ")}`);
  const c = meta.counts || {};
  const expect = { predicates: 83, cells: 456, inferences: 13, godhead: 4, vectors: 3 };
  for (const [k, v] of Object.entries(expect)) if (c[k] !== v) fail(`counts.${k} = ${c[k]}, expected ${v}`);
  const pa = c.phrase_assertions || {};
  for (const k of ["HISTORICAL", "RESTORATION", "CASE-STUDY", "CLARIFICATION", "QUEUE-CELL"]) {
    if (!pa[k] || pa[k].pass !== pa[k].total) fail(`phrase assertions ${k}: ${pa[k] && pa[k].pass}/${pa[k] && pa[k].total}`);
  }
  if (meta.policies && meta.policies.full_branch_map_enabled !== false) fail("full_branch_map_enabled must be false");
}

if (problems.length) {
  console.error("✖ SJN data verification failed:");
  for (const p of problems) console.error("   - " + p);
  console.error("  Re-run the pipeline: python scripts/sjn-build-data.py");
  process.exit(1);
}
console.log("✔ SJN data verified (Seeking Jesus of Nazareth): live green pipeline run, integrity intact.");
