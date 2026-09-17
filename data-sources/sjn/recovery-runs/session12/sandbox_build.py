"""Session 12 (2026-09-17): build the seven finished live-1 packets into a SANDBOX directory — no model calls, no network, no
cell-state or run.json writes. Used to measure what a rule or a re-chunk changes before anything is committed; it is not the
session's rebuild (phase 6 does that once, through run.py --rebuild-packet-only).

  python data-sources/sjn/recovery-runs/session12/sandbox_build.py <out_dir> [--branch "Anglican" ...]

The committed packets are never touched: SJN_PACKETS_DIR is set to <out_dir> before the harness is imported."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ATTEMPTS = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--branch", action="append")
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    os.environ["SJN_PACKETS_DIR"] = out_dir
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from sjn_recovery import llm as llm_mod
    import requests

    def _refuse_call(self, role, *x, **k):
        ATTEMPTS.append({"role": role})
        raise SystemExit(f"STOP: a model call ({role}) was attempted during the sandbox build")

    def _refuse_net(*x, **k):
        ATTEMPTS.append({"network": str(x[:2])[:200]})
        raise SystemExit("STOP: a network request was attempted during the sandbox build")

    llm_mod.LLM.complete = _refuse_call
    requests.Session.request = _refuse_net
    requests.request = _refuse_net

    from sjn_recovery.config import RUNS_DIR, BRANCHES, PACKETS_DIR
    assert os.path.abspath(PACKETS_DIR) == out_dir, (PACKETS_DIR, out_dir)
    from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, open_cells
    from sjn_recovery.agents import CellRunner
    from sjn_recovery.packets import build_branch_packet
    from sjn_recovery.llm import LLM

    run = json.load(open(os.path.join(RUNS_DIR, "live-1", "run.json"), encoding="utf-8"))
    cost = json.load(open(os.path.join(RUNS_DIR, "live-1", "cost-state.json"), encoding="utf-8"))
    finished = [b for b in BRANCHES if b in run["branches"] and (cost["branches"].get(b) or {}).get("status") == "DONE"]
    branches = a.branch or finished
    reg = Registry()
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    cells = open_cells(queue)
    llm = LLM("live-1", backend="batch", model="sonnet", log=lambda *x: None)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, "live-1", "cells"), "sonnet", run["verifier_models"],
                        log=lambda *x: None, run_coder=False, exhaust=False)
    runner.save = lambda st: None                      # never write a cell state from the sandbox
    cache, disk_load = {}, runner.load
    runner.load = lambda qid: cache[qid] if qid in cache else cache.setdefault(qid, disk_load(qid))
    for br in branches:
        bc = [c for c in cells if c["branch"] == br]
        for c in bc:                                    # the same re-finalisation run.py applies, held in memory only
            st = runner.load(c["queue_id"])
            if st:
                runner.refinalize(st, br)
        build_branch_packet(br, bc, runner, reg, preds, comps, "live-1", log=print,
                            rebuilt_from={"note": "session 12 SANDBOX build (not committed; no model calls)"})
    print(json.dumps({"model_calls_attempted": len(ATTEMPTS), "branches": branches, "out_dir": out_dir}))


if __name__ == "__main__":
    main()
