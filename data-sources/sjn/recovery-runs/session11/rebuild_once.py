"""Session 11 (2026-09-17): rebuild the seven finished live-1 packets ONCE under R6-35..R6-40 — no model calls.

Runs `run.py --rebuild-packet-only` for each finished branch, in the §7 order, with every model call and every network request
refused in-process (a call would raise before any request left the machine). The seven branches are read from the run
records (live-1/run.json `branches`, each DONE in live-1/cost-state.json), not typed by hand.

  python data-sources/sjn/recovery-runs/session11/rebuild_once.py"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery import llm as llm_mod  # noqa: E402
from sjn_recovery.config import RUNS_DIR, BRANCHES  # noqa: E402

ATTEMPTS = []


def _refuse_call(self, role, *a, **k):
    ATTEMPTS.append({"role": role, "meta": k.get("meta")})
    raise SystemExit(f"STOP: a model call ({role}) was attempted during the no-call rebuild")


def _refuse_net(*a, **k):
    ATTEMPTS.append({"network": str(a[:2])[:200]})
    raise SystemExit("STOP: a network request was attempted during the no-call rebuild")


llm_mod.LLM.complete = _refuse_call
import requests  # noqa: E402
requests.Session.request = _refuse_net
requests.request = _refuse_net

NOTE = ("session 11 (2026-09-17), the ONE rebuild R6-16 held for (no model calls): adoption ratified — R6-35 BSR-AN-02, R6-36 BSR-AN-05, "
        "R6-37 BSR-LU-03 (translator disclosed; publisher-apparatus guard), R6-38 scope = verified reach (BSR-RP-03 added; BSR-RP-02 and "
        "BSR-LU-01 amended to ONE_CHURCH), R6-39 BSR-BA-03 ISSUED_UNADOPTED with its own wording, R6-40 BSR-RC-07 / BSR-AN-04 / BSR-RP-05; "
        "the first build since session 6, so the session 7-9 resolution rules (R6-5/R6-10 phrase-level creed resolution, R6-6/R6-9 "
        "adoption field, Task 6 ladder fields) are reflected here for the first time")


def main():
    run = json.load(open(os.path.join(RUNS_DIR, "live-1", "run.json"), encoding="utf-8"))
    cost = json.load(open(os.path.join(RUNS_DIR, "live-1", "cost-state.json"), encoding="utf-8"))
    finished = [b for b in BRANCHES if b in run["branches"] and (cost["branches"].get(b) or {}).get("status") == "DONE"]
    print("finished branches (run.json branches, cost-state DONE):", finished)
    if len(finished) != 7:
        raise SystemExit(f"STOP: expected seven finished branches, found {len(finished)}")
    from sjn_recovery import run as run_mod
    for br in finished:
        sys.argv = ["run.py", "--run-id", "live-1", "--branch", br, "--verifier-models", ",".join(run["verifier_models"]),
                    "--rebuild-packet-only", "--rebuild-note", NOTE]
        rc = run_mod.main()
        if rc != 0:
            raise SystemExit(f"STOP: rebuild of {br} returned {rc}")
    print(json.dumps({"model_calls_attempted": len(ATTEMPTS), "branches_rebuilt": finished}))


if __name__ == "__main__":
    main()
