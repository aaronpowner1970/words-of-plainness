"""Live run driver (spec §7) — BUILT IN GATE 6, NOT EXECUTED UNTIL THE AUTHOR DECIDES after calibration.

  python scripts/sjn_recovery/run.py --run-id live-1 --branch "Roman Catholic" --locator-model sonnet --verifier-models <chosen> [--backend batch]
  python scripts/sjn_recovery/run.py --run-id live-1 --all-branches ...

Per branch, in the §7 order (Roman Catholic → Lutheran → Reformed/Presbyterian → Baptist → Methodist/Wesleyan
→ Anglican → Mennonite/Anabaptist → Eastern Orthodox): every open cell (NOT LOCATED — NOT YET RECOVERED and
the other NOT LOCATED states) runs locator (two-pass where a fallback row exists) → verifier → coder, and the
packet builder writes recovery-packets/<branch>.json. Nothing writes to the workbook."""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, BRANCHES, ensure_dirs  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, open_cells  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery.packets import build_branch_packet  # noqa: E402
from sjn_recovery import prompts  # noqa: E402


def log(msg):
    print(msg, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--workbook")
    ap.add_argument("--backend", default="batch")
    ap.add_argument("--locator-model", default="sonnet")
    ap.add_argument("--verifier-models", required=True, help="primary verifier first (the calibration-chosen model)")
    ap.add_argument("--coder-model")
    ap.add_argument("--branch")
    ap.add_argument("--all-branches", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--i-have-author-authorization", action="store_true",
                    help="required: the live run starts only after the author reviews the calibration report")
    ap.add_argument("--projection-per-cell-usd", type=float, default=0.405,
                    help="the calibrated per-cell cost the branch is measured against (cal-3: 9.4 calls, 0.405 USD per cell)")
    ap.add_argument("--branch-cost-cap-usd", type=float, default=None,
                    help="recorded per branch; the executor (api_executor.py --max-cost-usd) is what enforces it")
    a = ap.parse_args()
    if not a.i_have_author_authorization:
        log("Refusing to start the live run: pass --i-have-author-authorization after the author has reviewed "
            "data-sources/sjn/recovery-runs/calibration-report.md (Gate 6 spec §6, launch constraint 2).")
        return 2
    ensure_dirs()
    reg = Registry(a.workbook)
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    cells = open_cells(queue)
    branches = BRANCHES if a.all_branches else [a.branch]
    vmodels = a.verifier_models.split(",")
    llm = LLM(a.run_id, backend=a.backend, model=a.locator_model, log=log)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, a.run_id, "cells"), a.locator_model, vmodels,
                        coder_model=a.coder_model, log=log, run_coder=True)
    branch_cost = {}
    for br in branches:
        bc = [c for c in cells if c["branch"] == br]
        if a.limit:
            bc = bc[:a.limit]
        done = 0
        for c in bc:
            st = runner.run_cell(c)
            done += st.get("phase") == "DONE"
        log(f"== {br}: {done}/{len(bc)} open cells DONE; pending calls {len(set(llm.pending))}")
        branch_cost[br] = branch_spend(llm, bc, a.projection_per_cell_usd, a.branch_cost_cap_usd)
        log(f"   spend so far: {branch_cost[br]['calls']} metered calls, {branch_cost[br]['cost_usd']:.2f} USD "
            f"({branch_cost[br]['cost_per_cell_usd']:.3f}/cell vs projection {a.projection_per_cell_usd:.3f}; "
            f"projected {branch_cost[br]['projected_usd']:.2f}; cap {a.branch_cost_cap_usd})")
        if done == len(bc):
            build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log)
    with open(os.path.join(RUNS_DIR, a.run_id, "run.json"), "w", encoding="utf-8") as fh:
        json.dump({"run_id": a.run_id, "kind": "live", "workbook": os.path.basename(reg.path), "app_master_version": reg.app_master_version,
                   "locator_model": a.locator_model, "verifier_models": vmodels, "coder_model": a.coder_model or a.locator_model,
                   "backend": a.backend, "prompt_version": prompts.PROMPT_VERSION, "prompt_versions": prompts.PROMPT_VERSIONS, "branches": branches,
                   "retrieval": "PER_STANDARD", "routing": runner.routing, "slice_rows": sorted(runner.slice_rows),
                   "projection_per_cell_usd": a.projection_per_cell_usd, "branch_cost_cap_usd": a.branch_cost_cap_usd,
                   "branch_spend": branch_cost, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh, indent=1)
    return 10 if llm.pending else 0


def branch_spend(llm, cells, projection_per_cell, cap):
    """Metered spend of this run on one branch's cells, from the audit log (calls whose meta names one of
    the branch's queue ids), against the calibrated projection and the per-branch cap."""
    qids = {c["queue_id"] for c in cells}
    recs = [r for r in llm._cache.values() if r.get("run_id") == llm.run_id and (r.get("meta") or {}).get("queue_id") in qids]
    cost = sum(r.get("cost_usd") or 0.0 for r in recs)
    by_role = {}
    for r in recs:
        k = f"{r.get('role')}/{r.get('executor_model') or r.get('model')}"
        b = by_role.setdefault(k, {"calls": 0, "cost_usd": 0.0})
        b["calls"] += 1; b["cost_usd"] += r.get("cost_usd") or 0.0
    return {"cells": len(cells), "calls": len(recs), "cost_usd": round(cost, 4), "calls_per_cell": round(len(recs) / max(1, len(cells)), 2),
            "cost_per_cell_usd": round(cost / max(1, len(cells)), 4), "projection_per_cell_usd": projection_per_cell,
            "projected_usd": round(projection_per_cell * len(cells), 2), "cap_usd": cap, "over_cap": bool(cap and cost > cap),
            "estimated": any((r.get("usage") or {}).get("estimated") for r in recs), "by_role": by_role}


if __name__ == "__main__":
    sys.exit(main())
