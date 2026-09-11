"""Batch-backend job exchange helpers.

  python scripts/sjn_recovery/jobs.py status  --run-id RUN
  python scripts/sjn_recovery/jobs.py bundles --run-id RUN --role verifier --model sonnet --size 5
        writes .cache/sjn-recovery/jobs/RUN/bundles/<role>-<model>-NN.json listing job files

An executor (in this build: Claude Code subagents, one isolated session per bundle) reads each job file,
answers the `system` + `user` prompt as the requested model, and writes
.cache/sjn-recovery/jobs/RUN/done/<call_id>.json = {"call_id", "output", "model", "executor"}.
Re-running the harness ingests the done files (llm.py batch backend)."""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sjn_recovery.config import JOBS_DIR  # noqa: E402


def status(run_id):
    d = os.path.join(JOBS_DIR, run_id)
    pend = os.path.join(d, "pending"); done = os.path.join(d, "done")
    by = {}
    for f in os.listdir(pend) if os.path.isdir(pend) else []:
        if not f.endswith(".json"):
            continue
        if os.path.exists(os.path.join(done, f)) or os.path.exists(os.path.join(done, f[:-5] + ".txt")):
            continue
        with open(os.path.join(pend, f), encoding="utf-8") as fh:
            j = json.load(fh)
        k = (j["role"], j["model"])
        by[k] = by.get(k, 0) + 1
    n_done = len([f for f in os.listdir(done) if f.endswith((".json", ".txt"))]) if os.path.isdir(done) else 0
    print(f"run {run_id}: done={n_done} pending={sum(by.values())} " + " ".join(f"{r}/{m}={n}" for (r, m), n in sorted(by.items())))
    return by


def bundles(run_id, role, model, size):
    d = os.path.join(JOBS_DIR, run_id)
    pend = os.path.join(d, "pending"); done = os.path.join(d, "done"); bd = os.path.join(d, "bundles")
    os.makedirs(bd, exist_ok=True)
    for f in os.listdir(bd):
        if f.startswith(f"{role}-{model}-"):
            os.remove(os.path.join(bd, f))
    jobs = []
    for f in sorted(os.listdir(pend)):
        if not f.endswith(".json") or os.path.exists(os.path.join(done, f)) or os.path.exists(os.path.join(done, f[:-5] + ".txt")):
            continue
        with open(os.path.join(pend, f), encoding="utf-8") as fh:
            j = json.load(fh)
        if j["role"] == role and j["model"] == model:
            jobs.append(os.path.join(pend, f))
    n = 0
    for i in range(0, len(jobs), size):
        n += 1
        with open(os.path.join(bd, f"{role}-{model}-{n:02d}.json"), "w", encoding="utf-8") as fh:
            json.dump({"run_id": run_id, "role": role, "model": model, "done_dir": done, "jobs": jobs[i:i + size]}, fh, indent=1)
    print(f"{len(jobs)} pending {role}/{model} jobs -> {n} bundles of ≤{size} in {bd}")
    return n


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("status"); s.add_argument("--run-id", required=True)
    b = sub.add_parser("bundles"); b.add_argument("--run-id", required=True); b.add_argument("--role", required=True)
    b.add_argument("--model", required=True); b.add_argument("--size", type=int, default=5)
    a = ap.parse_args()
    if a.cmd == "status":
        status(a.run_id)
    elif a.cmd == "bundles":
        bundles(a.run_id, a.role, a.model, a.size)


if __name__ == "__main__":
    main()
