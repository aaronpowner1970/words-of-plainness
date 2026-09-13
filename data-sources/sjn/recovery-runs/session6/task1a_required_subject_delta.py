"""Session 6, Ruling 1a: the proposed workbook delta for required_subject. No model calls; the workbook is not written.

The workbook has NO required-subject column: Inherited 57 carries Predicate ID, mode, family, definition, code, lens, floor note,
provenance, confidence, source record and locator — and the harness DERIVES the subject in code (registry.subject_scope, from the
definition's wording and the mode). So the delta is a new column, "Required subject", on Inherited 57: all 57 rows, 52 carrying
the harness-derived value unchanged and the five R6-1 families retyped. Writes
  wop-scratch/WoP_SJN_RequiredSubject_Delta_20260913.csv   (57 rows: family, old, new, changed, source, affected queue_ids)
  recovery-runs/session6/task1a-required-subject-delta.json"""
import csv
import hashlib
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_pipeline.workbook import s  # noqa: E402
from sjn_recovery.registry import Registry, load_queue, open_cells, subject_scope  # noqa: E402
from sjn_recovery import rulings  # noqa: E402

DST = r"C:\Users\aaron\Documents\wop-scratch\WoP_SJN_RequiredSubject_Delta_20260913.csv"
reg = Registry()
_, rows, _ = reg.wb.table("Inherited 57", "Predicate ID")
cols = [k for k in rows[0].keys() if k != "__row"]
ruled = rulings.required_subjects()
fam = (rulings.load()["rulings"]["R6-1_required_subject"])["families"]
queue = load_queue(reg.wb)
open_ids = {c["queue_id"] for c in open_cells(queue)}
out = []
for r in rows:
    pid = s(r["Predicate ID"])
    old = subject_scope(pid, s(r.get("Historical source-report definition")), s(r.get("Original mode")))
    new = ruled.get(pid, old)
    cells = [c for c in queue if c["family_id"] == pid]
    out.append({"predicate_id": pid, "predicate": s(r.get("Normalized predicate family")), "mode": s(r.get("Original mode")),
                "required_subject_old (harness-derived; no workbook column)": old, "required_subject_new": new,
                "changed": "RETYPED (R6-1)" if pid in ruled else "", "ruling_example": fam.get(pid, {}).get("ruling_example", ""),
                "affected_queue_ids": "; ".join(f"{c['queue_id']} ({c['branch']}{', open' if c['queue_id'] in open_ids else ''})" for c in cells) if pid in ruled else "",
                "queue_cells": len(cells), "open_cells": sum(1 for c in cells if c["queue_id"] in open_ids)})
with open(DST, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)
res = {"workbook": os.path.basename(reg.path), "inherited_57_columns": cols, "has_required_subject_column": "Required subject" in cols,
       "file": os.path.basename(DST), "sha256": hashlib.sha256(open(DST, "rb").read()).hexdigest(),
       "proposed_workbook_change": "Inherited 57: add column 'Required subject' (57 rows) with required_subject_new; five families retyped",
       "retyped": [x for x in out if x["changed"]]}
json.dump(res, open(os.path.join(os.path.dirname(__file__), "task1a-required-subject-delta.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print("Inherited 57 columns:", cols)
for x in res["retyped"]:
    print(f"== {x['predicate_id']} {x['predicate']} ({x['queue_cells']} queue cells, {x['open_cells']} open)\n   OLD {x['required_subject_old (harness-derived; no workbook column)']}\n   NEW {x['required_subject_new']}\n   {x['affected_queue_ids']}")
