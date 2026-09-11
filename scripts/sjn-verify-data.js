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
  "vectors.json", "clarifications.json", "glossary.json", "ranges.json", "branches.json"];
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

  // R001 (Gate 5 — registry-only citations). The pipeline already runs R001 as a BLOCK rule; this is an
  // independent re-check of the committed data set so the guard does not depend on the Python run alone:
  // every citation URL on a cell must sit on a host admitted by an AUTHOR_RATIFIED Branch Source Registry
  // row of that cell's own branch. Retired lineage-only rows are not citations.
  const bPath = path.join(DIR, "branches.json");
  const cPath = path.join(DIR, "cells.json");
  if (fs.existsSync(bPath) && fs.existsSync(cPath)) {
    const branches = JSON.parse(fs.readFileSync(bPath, "utf8"));
    const cells = JSON.parse(fs.readFileSync(cPath, "utf8"));
    const enforce = !!(branches.policy && branches.policy.registry_only_enforcement);
    const r001 = (meta.rules || []).find((r) => r.rule === "R001");
    if (enforce && !(r001 && r001.status === "PASS")) fail(`R001 registry-only rule not PASS in meta (status ${r001 && r001.status})`);
    const norm = (h) => (h || "").toLowerCase().replace(/^www\./, "");
    const reg = (h) => h.split(".").slice(-2).join(".");   // organization-level domain, as in sjn_pipeline/registry.py
    const matches = (host, domain) => host === domain || host.endsWith("." + domain) || reg(host) === reg(domain);
    const idx = {};
    for (const row of branches.registry || []) {
      if (row.status !== "AUTHOR_RATIFIED") continue;
      (idx[row.branch] = idx[row.branch] || []).push(...(row.admitted_domains || []).map(norm));
    }
    const viol = [];
    for (const c of cells.cells || []) {
      if (!c.evidence || c.lineage_only) continue;
      for (const k of ["authority_url", "text_url"]) {
        const u = c.evidence[k];
        if (!u) continue;
        let host = "";
        try { host = norm(new URL(u).hostname); } catch (e) { viol.push(`${c.id}: unparseable URL ${u}`); continue; }
        if (!(idx[c.branch] || []).some((d) => matches(host, d))) viol.push(`${c.id} (${c.branch}): ${host}`);
      }
    }
    if (enforce && viol.length) fail(`R001: ${viol.length} citation host(s) outside the branch registry: ${viol.slice(0, 6).join("; ")}`);
    if (enforce && !(branches.counts && branches.counts.ratified > 0)) fail("R001: branches.json carries no AUTHOR_RATIFIED registry rows");
  }
}

if (problems.length) {
  console.error("✖ SJN data verification failed:");
  for (const p of problems) console.error("   - " + p);
  console.error("  Re-run the pipeline: python scripts/sjn-build-data.py");
  process.exit(1);
}
console.log("✔ SJN data verified (Seeking Jesus of Nazareth): live green pipeline run, integrity intact.");
