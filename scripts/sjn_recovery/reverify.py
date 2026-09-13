"""Re-verify ONE stored candidate under the current verifier prompt, both models (Gate 6 session 5, Task 6: Q-003).

  python scripts/sjn_recovery/reverify.py --run-id live-1 --queue-id Q-003 --candidate-id Q-003-p3-BSR-LU-01-b22-1   # issues the two calls
  python scripts/sjn_recovery/api_executor.py --run-id live-1 --workers 2 --max-cost-usd 1 --key-file <.env>
  python scripts/sjn_recovery/reverify.py --run-id live-1 --queue-id Q-003 --candidate-id Q-003-p3-BSR-LU-01-b22-1   # ingests, finalises
  python scripts/sjn_recovery/run.py --run-id live-1 --branch Lutheran --verifier-models sonnet,opus --rebuild-packet-only

The stored rubrics are moved, not deleted, to `superseded_rubrics` (with their prompt version and the final verdict they
gave); both models then verify the candidate afresh under the current prompt (gate6-v1.2, with IDIOM_OR_FORMULA), and the
verdict is finalised by the ordinary rule (agents.finalize: the candidate's stored route, the lower floor). No other
candidate is touched; the cell's allocation and coder state are recomputed by the rebuild. Nothing writes to the workbook."""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, open_cells, assert_gate6_scope  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import prompts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--queue-id", required=True)
    ap.add_argument("--candidate-id", required=True)
    ap.add_argument("--verifier-models", default="sonnet,opus")
    ap.add_argument("--reason", default="session 5 Task 6: let IDIOM_OR_FORMULA (verifier gate6-v1.2) decide the candidate that motivated it")
    a = ap.parse_args()
    reg = Registry()
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    assert_gate6_scope(reg, queue, print)
    cell = next(c for c in open_cells(queue) if c["queue_id"] == a.queue_id)
    vmodels = a.verifier_models.split(",")
    llm = LLM(a.run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, a.run_id, "cells"), "sonnet", vmodels, log=print, run_coder=False)
    st = runner.load(a.queue_id)
    cand = next(c for p in st["passes"].values() for c in p.get("candidates", []) if c["candidate_id"] == a.candidate_id)
    v = st["verifications"][a.candidate_id]
    if "superseded_rubrics" not in v:
        v["superseded_rubrics"] = {"moved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "reason": a.reason,
                                   "rubrics": {m: v.pop(m) for m in vmodels if m in v},
                                   "final": v.get("final"), "final_at_run": v.get("final_at_run")}
    pending = False
    for m in vmodels:
        if m not in v or v[m].get("status") in ("PENDING", "UNPARSEABLE"):
            v[m] = runner.verify(cell, cand, m)
        if v[m].get("status") == "PENDING":
            pending = True
    if pending:
        runner.save(st)
        print(f"== {a.candidate_id}: {sum(1 for m in vmodels if v[m].get('status') == 'PENDING')} verifier call(s) pending under {prompts.prompt_version('verifier')}")
        return 10
    fin = runner.finalize(v, runner.primary, runner.adjudicator)
    v["reverified"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "prompt_version": prompts.prompt_version("verifier"),
                       "models": vmodels, "route_kept": v.get("_route"), "reason": a.reason}
    runner.save(st)
    for m in vmodels:
        r = v[m]
        print(f"-- {m} ({r.get('prompt_version')}): verdict {r.get('verdict')} floor {r.get('floor')} (model floor {r.get('floor_model', r.get('floor'))}; "
              f"capped by {r.get('floor_capped_by')}) hazards {r.get('hazard_flags')} asserted_outside_formula {r.get('asserted_outside_formula')}")
    print(f"== final: {fin['verdict']} at {fin['floor_final']} ({fin['reason_code_final']}); route {fin['route']}; floors {fin['floor_by_model']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
