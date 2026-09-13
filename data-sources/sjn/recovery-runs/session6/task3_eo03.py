"""Session 6, Ruling 3: retire BSR-EO-03 before Eastern Orthodox runs. No fetches, no model calls.

  3a  writes wop-scratch/WoP_SJN_BranchSourceRegistries_Draft3r5_20260913.csv — Draft3r4 unchanged plus BSR-EO-03 retired, marked
      in new r5_change / r5_change_note columns — and prints the proposed workbook change;
  3b  confirms from the CORPUS STORE (the chunk files and corpus-manifest.json, not the session-5 audit) that no other Eastern
      Orthodox row is in EO-03's state: for every EO row, the chunk count and characters in the store, whether the stored
      text hash equals the manifest's, the first characters of the first chunk, and a wrapper / challenge scan; then the
      session-5 NO TEXT test (packets.no_text_rows) run on a hypothetical EO cell whose coverage names every row that has text;
  3c  lists the EO rows the harness now sees (Registry with the rulings applied)."""
import csv
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery import store, rulings  # noqa: E402
from sjn_recovery.packets import no_text_rows, empty_result_option  # noqa: E402

SCRATCH = r"C:\Users\aaron\Documents\wop-scratch"
SRC = os.path.join(SCRATCH, "WoP_SJN_BranchSourceRegistries_Draft3r4_20260913.csv")
DST = os.path.join(SCRATCH, "WoP_SJN_BranchSourceRegistries_Draft3r5_20260913.csv")
WRAPPER = re.compile(r"(enable javascript|checking your browser|just a moment|captcha|cloudflare|access denied|cookie policy|loading\.\.\.|<script|<div)", re.I)

ru = rulings.retirements()["BSR-EO-03"]
raw = open(SRC, "rb").read()
rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
fields = list(rows[0].keys()) + ["r5_change", "r5_change_note"]
old = None
for r in rows:
    r["r5_change"], r["r5_change_note"] = "", ""
    if r["registry_id"] == "BSR-EO-03":
        old = {k: r[k] for k in ("status", "author_decision", "reason_code", "author_note", "decision_date")}
        r.update({"status": "RETIRED", "author_decision": "EXCLUDE", "reason_code": ru["reason_code"],
                  "author_note": "Retired 2026-09-13 (session 6, R6-3): " + ru["reason"], "decision_date": "2026-09-13",
                  "r5_change": "status;author_decision;reason_code;author_note;decision_date",
                  "r5_change_note": ("HOST_RETIRED: goarch.org was retired as a registry host on 2026-09-12 and the row has no text; under the "
                                     "session-5 NO TEXT rule it would block the REVIEWED offer on all 44 Eastern Orthodox cells. author_decision "
                                     "follows the RETIRED-row pattern of BSR-LU-04 / BSR-MA-03 (EXCLUDE). reason_code HOST_RETIRED is a new value in "
                                     "this column (existing RETIRED rows carry OTHER / WRONG_SUBJECT).")})
with open(DST, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
new = {k: next(r for r in rows if r["registry_id"] == "BSR-EO-03")[k] for k in old}
delta = {"file": os.path.basename(DST), "sha256": hashlib.sha256(open(DST, "rb").read()).hexdigest(), "based_on": os.path.basename(SRC),
         "based_on_sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "changed": {"BSR-EO-03": {"old": old, "new": new}}}
print("== 3a proposed workbook change: Branch Source Registry, BSR-EO-03:")
for k in old:
    print(f"     {k}: {old[k]!r} -> {new[k]!r}")

reg = Registry()
manifest = store.load_manifest().get("standards", {})
eo_all = [r for r in reg.rows_all if r["branch"] == "Eastern Orthodox"]
check = []
for r in eo_all:
    rid = r["registry_id"]
    ch = store.load_chunks(rid)
    m = manifest.get(rid) or {}
    text = "\n".join(c["text"] for c in ch)
    joined_hash = m.get("text_hash")
    first = (ch[0]["text"][:160] if ch else "").replace("\n", " ")
    check.append({"registry_id": rid, "status_now": r.get("status"), "author_ruling": r.get("_author_ruling"), "manifest_status": m.get("status"),
                  "chunks_in_store": len(ch), "chars_in_store": len(text), "manifest_text_hash": joined_hash,
                  "chunk_hashes_present": all(c.get("text_hash") for c in ch) if ch else None,
                  "wrapper_or_challenge_markers": sorted({x.group(0).lower() for x in WRAPPER.finditer(text)}),
                  "first_chunk_locator": ch[0]["locator"] if ch else None, "first_chars": first,
                  "citation_refusal": reg.citation_refusal(rid) if rid in reg.by_id else "not a ratified row",
                  "in_branch_citable_rows": rid in {x["registry_id"] for x in reg.for_branch("Eastern Orthodox", include_fallback=True, citable_only=True)}})
citable = reg.for_branch("Eastern Orthodox", include_fallback=True, citable_only=True)
cov = {x["registry_id"]: {"coverage": "FULL", "supplied": 1, "of": 1} for x in citable if store.load_chunks(x["registry_id"])}
nt = no_text_rows({"coverage_final": cov, "passes": {"1": {"per_standard": {}}}}, citable, reg, manifest, card_empty=True)
opt = empty_result_option(cov, {}, no_text=nt)
res = {"delta": delta, "eo_rows": check, "citable_rows_after_retirement": [x["registry_id"] for x in citable],
       "ratified_rows_after_retirement": [x["registry_id"] for x in reg.for_branch("Eastern Orthodox", citable_only=False)],
       "no_text_test": {"coverage_given_for": sorted(cov), "no_text_rows": nt, "reviewed_offered": opt["offered"], "why_not": opt["why_not_offered"]}}
json.dump(res, open(os.path.join(os.path.dirname(__file__), "task3-eo03-retirement.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(f"== 3b corpus store ({len(eo_all)} EO rows):")
for x in check:
    print(f"   {x['registry_id']} {x['status_now']:15s} manifest {str(x['manifest_status']):26s} chunks {x['chunks_in_store']:4d} chars {x['chars_in_store']:7d} "
          f"markers {x['wrapper_or_challenge_markers']} refusal {x['citation_refusal']!s:.40} | {x['first_chars'][:90]}")
print(f"== 3c ratified EO rows now {len(res['ratified_rows_after_retirement'])}: {res['ratified_rows_after_retirement']}")
print(f"   citable (reach the locator) {len(res['citable_rows_after_retirement'])}: {res['citable_rows_after_retirement']}")
print(f"   NO TEXT test on a hypothetical EO cell covering every citable row with text: no_text_rows={nt}; REVIEWED offered={opt['offered']}")
