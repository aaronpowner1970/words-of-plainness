"""Same-standard recall of a calibration run RECOMPUTED under the current verdict rule from its stored rubrics —
no model calls, nothing on disk changed (session 4, 2026-09-13: what the lower-floor rule 2a/2b/2c costs in recall).

  python scripts/sjn_recovery/recall_recompute.py --run-id cal-3 [--out recovery-runs/cal-3/lower-floor-recall-20260913.json]

For every released cell of the calibration set: the gated metric (a surviving candidate on the standard the released
cell cites — calibrate.equivalent_registry_ids) under the verdicts the run finalised on, and again after re-finalising
every stored verification in memory with agents.CellRunner.finalize (the lower floor of the two models is final;
opus adjudicates lines 1–3 only on the adjudicating routes). Also the count of candidates the rule refuses."""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, LOWER_FLOOR_RULE  # noqa: E402
from sjn_recovery.registry import Registry, load_queue  # noqa: E402
from sjn_recovery.agents import CellRunner, ACCEPTS  # noqa: E402
from sjn_recovery.calibrate import equivalent_registry_ids, calibration_cells  # noqa: E402


def survivors(st, witness_ok=False):
    out = []
    for pk, p in (st.get("passes") or {}).items():
        for cd in p.get("candidates", []):
            fin = (st["verifications"].get(cd["candidate_id"]) or {}).get("final") or {}
            if fin.get("verdict") in ACCEPTS:
                out.append(cd)
    if out and all(cd.get("witness") for cd in out):
        return []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="cal-3")
    ap.add_argument("--out")
    a = ap.parse_args()
    reg = Registry(None)
    queue = load_queue(reg.wb)
    rel, _ = calibration_cells(queue)
    run_dir = os.path.join(RUNS_DIR, a.run_id)
    meta = json.load(open(os.path.join(run_dir, "run.json"), encoding="utf-8"))
    primary, adjudicator = meta.get("primary", "sonnet"), meta.get("adjudicator", "opus")
    n = hit_before = hit_after = 0
    lost, gained, refused = [], [], []
    per_branch = {}
    for c in rel:
        p = os.path.join(run_dir, "cells", f"{c['queue_id']}.json")
        if not os.path.exists(p):
            continue
        st = json.load(open(p, encoding="utf-8"))
        if st.get("phase") != "DONE":
            continue
        eq = equivalent_registry_ids(c)
        n += 1
        b = per_branch.setdefault(c["branch"], {"n": 0, "before": 0, "after": 0})
        b["n"] += 1
        before = any(cd["registry_id"] in eq for cd in survivors(st))
        # re-finalise in memory
        for cid, v in st["verifications"].items():
            old = (v.get("final") or {}).get("verdict")
            CellRunner.finalize(v, primary, adjudicator)
            if old in ACCEPTS and v["final"]["verdict"] not in ACCEPTS:
                refused.append({"queue_id": c["queue_id"], "branch": c["branch"], "candidate_id": cid, "route": v["final"].get("route"),
                                "floors": v["final"].get("floor_by_model"), "floor_final": v["final"].get("floor_final"),
                                "on_cited_standard": cid.split("-p")[1].split("-", 1)[1].rsplit("-", 1)[0] in eq if "-p" in cid else None})
        after = any(cd["registry_id"] in eq for cd in survivors(st))
        hit_before += before; hit_after += after
        b["before"] += before; b["after"] += after
        if before and not after:
            lost.append({"queue_id": c["queue_id"], "branch": c["branch"], "predicate": c["predicate"], "cited": sorted(eq)})
        if after and not before:
            gained.append({"queue_id": c["queue_id"], "branch": c["branch"], "predicate": c["predicate"]})
    out = {"run_id": a.run_id, "verdict_rule": LOWER_FLOOR_RULE, "metric": "SAME_STANDARD (gated)", "cells": n,
           "recall_at_run": round(hit_before / n, 4) if n else None, "recall_lower_floor": round(hit_after / n, 4) if n else None,
           "hits_at_run": hit_before, "hits_lower_floor": hit_after, "cells_lost": lost, "cells_gained": gained,
           "candidates_refused_by_rule": len(refused), "refused": refused,
           "per_branch": {k: dict(v, recall_at_run=round(v["before"] / v["n"], 3), recall_lower_floor=round(v["after"] / v["n"], 3)) for k, v in per_branch.items()},
           "note": "recomputed in memory from the stored rubrics of the run; the run's own files are unchanged; the verifier prompt of the run "
                   "(gate6-v1.1) predates the IDIOM_OR_FORMULA hazard, so Task 3 is not reflected here"}
    path = a.out or os.path.join(run_dir, "lower-floor-recall-20260913.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1); fh.write("\n")
    print(f"== {a.run_id}: same-standard recall {hit_before}/{n} = {out['recall_at_run']} at run -> {hit_after}/{n} = {out['recall_lower_floor']} under {LOWER_FLOOR_RULE}; "
          f"cells lost {len(lost)}, gained {len(gained)}; candidates refused by the rule {len(refused)}")
    for x in lost:
        print("   lost:", x)
    for k, v in out["per_branch"].items():
        print(f"   {k}: {v['before']}/{v['n']} -> {v['after']}/{v['n']}")
    print("   ->", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
