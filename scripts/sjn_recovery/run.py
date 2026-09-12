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
from sjn_recovery import prompts, coststate  # noqa: E402


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
    run_path = os.path.join(RUNS_DIR, a.run_id, "run.json")
    prior = {}
    if os.path.exists(run_path):
        with open(run_path, encoding="utf-8") as fh:
            prior = json.load(fh)
    branch_cost = dict(prior.get("branch_spend") or {})
    # 1d: the per-branch cap lives in recovery-runs/<run>/cost-state.json and survives every invocation of
    # run.py and api_executor.py. Registered here before the first cell; enforced by the executor; reconciled below.
    state = coststate.load(a.run_id)
    for br in branches:
        bc = [c for c in cells if c["branch"] == br]
        if a.limit:
            bc = bc[:a.limit]
        b = coststate.register_branch(state, br, a.branch_cost_cap_usd, [c["queue_id"] for c in bc])
        coststate.save(state)
        cap_hit = coststate.over_cap(b)
        if cap_hit:
            log(f"!! {br}: cost cap already reached ({b['spent_usd']:.2f} of {b['cap_usd']} USD, status {b['status']}); "
                f"running no further cells; the partial packet is written below. Raise --branch-cost-cap-usd to continue.")
        else:
            for c in bc:
                runner.run_cell(c)
        done = sum(1 for c in bc if (runner.load(c["queue_id"]) or {}).get("phase") == "DONE")
        log(f"== {br}: {done}/{len(bc)} open cells DONE; pending calls {len(set(llm.pending))}")
        spend = branch_spend(llm, bc, a.projection_per_cell_usd, a.branch_cost_cap_usd)
        coststate.reconcile(state, br, spend["cost_usd"], spend["calls"])
        b = state["branches"][br]
        cap_hit = coststate.over_cap(b)
        spend["cap_state"] = {k: b.get(k) for k in ("cap_usd", "spent_usd", "calls", "status", "cap_hit_at")}
        spend["coder"] = coder_savings(llm, runner, bc)
        log(f"   spend so far: {spend['calls']} metered calls, {spend['cost_usd']:.2f} USD "
            f"({spend['cost_per_cell_usd']:.3f}/cell vs projection {a.projection_per_cell_usd:.3f}; "
            f"projected {spend['projected_usd']:.2f}; cap {b['cap_usd']}; cost-state {b['spent_usd']:.2f} {b['status']})")
        if spend["coder"]["survivors"]:
            cs = spend["coder"]
            log(f"   coder (1c): {cs['coded']} coded of {cs['survivors']} survivors; {cs['skipped_by_allocation']} skipped by allocation "
                f"= {cs['usd_avoided_measured']:.2f} USD at the measured {cs['mean_coder_call_usd']:.4f}/call")
        if done == len(bc):
            b["status"] = "DONE"
            build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log)
        elif cap_hit:
            b["status"] = "CAP_HIT"
            log(f"!! {br}: STOPPED by the cost cap ({b['spent_usd']:.2f} of {b['cap_usd']} USD) with {len(bc) - done} cell(s) unfinished — "
                f"writing the PARTIAL packet")
            build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log, partial=spend["cap_state"])
        coststate.save(state)
        branch_cost[br] = spend
    all_branches = [x for x in BRANCHES if x in set(prior.get("branches") or []) | set(branches)]
    with open(run_path, "w", encoding="utf-8") as fh:
        json.dump({"run_id": a.run_id, "kind": "live", "workbook": os.path.basename(reg.path), "app_master_version": reg.app_master_version,
                   "locator_model": a.locator_model, "verifier_models": vmodels, "coder_model": a.coder_model or a.locator_model,
                   "backend": a.backend, "prompt_version": prompts.PROMPT_VERSION, "prompt_versions": prompts.PROMPT_VERSIONS, "branches": all_branches,
                   "retrieval": "PER_STANDARD", "routing": runner.routing, "slice_rows": sorted(runner.slice_rows),
                   "projection_per_cell_usd": a.projection_per_cell_usd, "branch_cost_cap_usd": a.branch_cost_cap_usd,
                   "cost_state_file": os.path.relpath(coststate.path_for(a.run_id), os.path.dirname(os.path.dirname(RUNS_DIR))).replace("\\", "/"),
                   "branch_spend": branch_cost, "workbooks": sorted(set((prior.get("workbooks") or [prior.get("workbook")] if prior else []) + [os.path.basename(reg.path)]) - {None}),
                   "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh, indent=1)
    return 10 if llm.pending else 0


def coder_savings(llm, runner, cells):
    """1c, MEASURED on this branch: survivors vs coder calls actually made vs candidates the allocation
    dropped before the coder ran; USD avoided = skipped × this branch's own mean metered coder-call cost."""
    survivors = coded = skipped = 0
    for c in cells:
        st = runner.load(c["queue_id"]) or {}
        survivors += len(st.get("survivors") or [])
        coded += sum(1 for v in (st.get("coding") or {}).values() if v.get("status") == "DONE")
        skipped += len(st.get("coder_skipped") or {})
    qids = {c["queue_id"] for c in cells}
    costs = [r.get("cost_usd") or 0.0 for r in llm._cache.values()
             if r.get("run_id") == llm.run_id and r.get("role") == "coder" and (r.get("meta") or {}).get("queue_id") in qids]
    mean = (sum(costs) / len(costs)) if costs else 0.0
    return {"survivors": survivors, "coded": coded, "skipped_by_allocation": skipped, "mean_coder_call_usd": round(mean, 5),
            "usd_avoided_measured": round(skipped * mean, 4),
            "basis": "skipped = survivors the allocator dropped before coding (measured); USD = skipped x this branch's mean metered coder call"}


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
