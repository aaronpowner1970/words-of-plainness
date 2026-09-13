"""Author rulings the harness applies in memory until the workbook carries them (Gate 6 session 6, 2026-09-13).

The rulings live in data-sources/sjn/recovery-runs/author-rulings-pending-workbook.json — committed, so every run.py /
reverify.py / truepos.py start reads the same rulings and the Eastern Orthodox launch cannot run without them. Nothing
here writes to the workbook. Each ruling says which workbook change supersedes it; when the workbook already holds that
change it is read from the workbook and checked against the ruling (a disagreement fails loudly).

  R6-1  required_subject for Lord / Life-giving / Judge / Savior / Not made admits the Son or the Spirit AS DIVINE
  R6-2  the hedged-PARTIAL floor rule; the three refused Baptist cells
  R6-3  BSR-EO-03 RETIRED (HOST_RETIRED)
  R6-4  one text, one slot: the textual guard lives in allocation.py; declared same-text rows (different wording) here"""
import json
import os

from .config import RUNS_DIR, ROOT

RULINGS_PATH = os.environ.get("SJN_RULINGS_PATH") or os.path.join(RUNS_DIR, "author-rulings-pending-workbook.json")
AUTHOR_RULING_FLOOR_CAP = "AUTHOR_RULING_R6-2"


def load(path=None):
    p = path or RULINGS_PATH
    if not os.path.exists(p):
        # the rulings are part of the harness from session 6 on: a run without them is not the run the author ratified
        raise SystemExit(f"author rulings file missing: {p} — nothing runs without the session-6 rulings")
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    d["_path"] = os.path.relpath(p, ROOT).replace("\\", "/")
    return d


def required_subjects(r=None):
    """{family_id: required_subject} retyped by R6-1."""
    r = r or load()
    fams = ((r.get("rulings") or {}).get("R6-1_required_subject") or {}).get("families") or {}
    return {pid: f["required_subject"] for pid, f in fams.items()}


def retirements(r=None):
    """{registry_id: ruling} for rows the author retired before the workbook records it."""
    r = r or load()
    out = {}
    for key, ru in (r.get("rulings") or {}).items():
        if ru.get("registry_id") and ru.get("status") == "RETIRED":
            out[ru["registry_id"]] = dict(ru, ruling=key)
    return out


def refused_candidates(r=None):
    """{candidate_id: {queue_id, predicate}} refused by R6-2 (2c)."""
    r = r or load()
    cells = ((r.get("rulings") or {}).get("R6-2_hedged_partial") or {}).get("refused_cells") or {}
    return {cid: {"queue_id": qid, "predicate": c.get("predicate")} for qid, c in cells.items() if isinstance(c, dict)
            for cid in c.get("candidates") or []}


def same_text_rows(r=None):
    """{alternate_registry_id: controlling_registry_id} declared by R6-4 (one text, different wording)."""
    r = r or load()
    rows = ((r.get("rulings") or {}).get("R6-4_one_text_one_slot") or {}).get("same_text_rows") or {}
    return {rid: v["same_text_as"] for rid, v in rows.items() if isinstance(v, dict) and v.get("same_text_as")}


def summary(r=None):
    """What the harness applied, for run logs and packet headers."""
    r = r or load()
    return {"file": r.get("_path"), "required_subject_retyped": sorted(required_subjects(r)),
            "registry_retired": sorted(retirements(r)), "refused_candidates": sorted(refused_candidates(r)),
            "same_text_rows": same_text_rows(r),
            "status": "AUTHOR RULED 2026-09-13; applied in memory; workbook not written (deltas pending ratification)"}
