"""Re-verify stored candidates under the current verifier prompt (Gate 6 session 5, Task 6: Q-003; session 6: R6-1 and
truncated replies).

  python scripts/sjn_recovery/reverify.py --run-id live-1 --queue-id Q-003 --candidate-id Q-003-p3-BSR-LU-01-b22-1   # issues the two calls
  python scripts/sjn_recovery/api_executor.py --run-id live-1 --workers 2 --max-cost-usd 1 --key-file <.env>
  python scripts/sjn_recovery/reverify.py --run-id live-1 --queue-id Q-003 --candidate-id Q-003-p3-BSR-LU-01-b22-1   # ingests, finalises
  python scripts/sjn_recovery/run.py --run-id live-1 --branch Lutheran --verifier-models sonnet,opus --rebuild-packet-only

  python scripts/sjn_recovery/reverify.py --run-id live-1 --candidates-file <json>     # many: [{queue_id, candidate_id, models, reason}]

The stored rubrics are moved, not deleted, to `superseded_rubrics` (with their prompt version and the final verdict they
gave); the named models then verify the candidate afresh under the current prompt and the current predicate record (session 6:
the R6-1 required_subject), and the verdict is finalised by the ordinary rule (agents.finalize: the candidate's stored route,
the lower floor, any floor ruling). A candidate is re-verified by the models that verified it before (a candidate that carried
an opus rubric gets both again), so its route is unchanged. No other candidate is touched; the cell's allocation and coder
state are recomputed by the rebuild. Nothing writes to the workbook."""
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

MODELS = ("sonnet", "opus")


def reverify_one(runner, cells, item, log=print):
    """Returns (status, summary) — status PENDING while a call is unanswered."""
    qid, cid, reason = item["queue_id"], item["candidate_id"], item["reason"]
    cell = cells[qid]
    st = runner.load(qid)
    cand = next(c for p in st["passes"].values() for c in p.get("candidates", []) if c["candidate_id"] == cid)
    v = st["verifications"][cid]
    vmodels = item.get("models") or [m for m in MODELS if isinstance(v.get(m), dict)] or ["sonnet"]
    if "superseded_rubrics" not in v or v["superseded_rubrics"].get("reason") != reason:
        prior = v.get("superseded_rubrics")
        v["superseded_rubrics"] = {"moved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "reason": reason,
                                   "rubrics": {m: v.pop(m) for m in vmodels if m in v},
                                   "final": v.get("final"), "final_at_run": v.get("final_at_run")}
        if prior:
            v["superseded_rubrics"]["earlier"] = prior
    pending = False
    for m in vmodels:
        if m not in v or v[m].get("status") in ("PENDING", "UNPARSEABLE"):
            v[m] = runner.verify(cell, cand, m)
        if v[m].get("status") == "PENDING":
            pending = True
    if pending:
        runner.save(st)
        return "PENDING", None
    fin = runner.finalize(v, runner.primary, runner.adjudicator)
    v["reverified"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "prompt_version": prompts.prompt_version("verifier"),
                       "models": vmodels, "route_kept": v.get("_route"), "reason": reason,
                       "required_subject": runner.predicates[cell["family_id"]]["subject_scope"]}
    runner.save(st)
    old = (v["superseded_rubrics"].get("final") or {})
    return "DONE", {"queue_id": qid, "candidate_id": cid, "models": vmodels, "route": fin.get("route"),
                    "before": {"verdict": old.get("verdict"), "reason_code": old.get("reason_code_final"), "floor": old.get("floor_final")},
                    "after": {"verdict": fin["verdict"], "reason_code": fin["reason_code_final"], "floor": fin["floor_final"],
                              "floor_by_model": fin.get("floor_by_model")},
                    "rubrics": {m: {k: v[m].get(k) for k in ("subject_is_required", "grammatical_subject", "speech_act_is_assertion", "floor",
                                                             "floor_reason", "hazard_flags", "verdict", "reason_code_final", "call_id")} for m in vmodels}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--queue-id")
    ap.add_argument("--candidate-id")
    ap.add_argument("--candidates-file")
    ap.add_argument("--out")
    ap.add_argument("--verifier-models", default="sonnet,opus")
    ap.add_argument("--reason", default="session 5 Task 6: let IDIOM_OR_FORMULA (verifier gate6-v1.2) decide the candidate that motivated it")
    a = ap.parse_args()
    reg = Registry()
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    assert_gate6_scope(reg, queue, print)
    cells = {c["queue_id"]: c for c in open_cells(queue)}
    llm = LLM(a.run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, a.run_id, "cells"), "sonnet", ["sonnet", "opus"], log=print, run_coder=False)
    if a.candidates_file:
        items = json.load(open(a.candidates_file, encoding="utf-8"))
    else:
        items = [{"queue_id": a.queue_id, "candidate_id": a.candidate_id, "models": a.verifier_models.split(","), "reason": a.reason}]
    done, pending = [], 0
    for it in items:
        status, summary = reverify_one(runner, cells, it)
        if status == "PENDING":
            pending += 1
        else:
            done.append(summary)
    if pending:
        print(f"== {pending} of {len(items)} candidate(s) have verifier call(s) pending under {prompts.prompt_version('verifier')}")
        return 10
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(done, fh, ensure_ascii=False, indent=1)
    for d in done:
        print(f"-- {d['queue_id']} {d['candidate_id']}: {d['before']['verdict']}/{d['before']['reason_code']} -> {d['after']['verdict']}/{d['after']['reason_code']} "
              f"at {d['after']['floor']} (floors {d['after']['floor_by_model']}; route {d['route']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
