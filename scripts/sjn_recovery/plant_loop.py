"""Drive a planted near-miss re-validation to completion: calibrate.py plant (writes verifier jobs) ↔ api_executor.py
(answers them) until nothing is pending, then plant-summary. Session 4 (fa-3): both models on every item, verifier
prompt gate6-v1.2, the lower-floor verdict rule.

  python scripts/sjn_recovery/plant_loop.py --run-id fa-3 --max-cost-usd 9 --key-file <.env> [--both-models]

Logs to data-sources/sjn/recovery-runs/<run>/plant-loop.log. The key file path is passed through and never printed."""
import argparse
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--verifier-models", default="sonnet,opus")
    ap.add_argument("--max-cost-usd", type=float, required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-rounds", type=int, default=8)
    ap.add_argument("--both-models", action="store_true")
    a = ap.parse_args()
    run_dir = os.path.join(RUNS_DIR, a.run_id)
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, "plant-loop.log")

    def log(line):
        print(line, flush=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def run(cmd, tag):
        log(f"-- {tag} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr and p.stderr.strip() else "")
        for l in out.rstrip().splitlines():
            if l.startswith("  ok  "):
                continue
            log(l)
        return p.returncode, out

    py = sys.executable
    plant = [py, os.path.join(HERE, "calibrate.py"), "plant", "--run-id", a.run_id, "--verifier-models", a.verifier_models] + (["--both-models"] if a.both_models else [])
    spent = 0.0
    for rnd in range(1, a.max_rounds + 1):
        rc, _ = run(plant, f"round {rnd}: plant")
        if rc == 0:
            break
        if rc != 10:
            log(f"!! plant failed (exit {rc})"); return rc
        rc, out = run([py, os.path.join(HERE, "api_executor.py"), "--run-id", a.run_id, "--workers", str(a.workers),
                       "--max-cost-usd", str(round(a.max_cost_usd - spent, 2)), "--key-file", a.key_file], f"round {rnd}: api_executor")
        answered = sum(1 for l in out.splitlines() if l.startswith("  ok  "))
        for l in out.splitlines():
            if l.startswith("== answered"):
                try:
                    spent += float(l.split("metered cost $")[1].split(" ")[0])
                except Exception:
                    pass
        log(f"   executor exit {rc} answered {answered}; spent so far ≈ {spent:.2f} USD of {a.max_cost_usd}")
        if rc != 0 and answered == 0:
            log("!! executor answered nothing (budget or fatal error); stopping"); return 1
    else:
        log("!! max rounds reached with calls pending"); return 1
    run([py, os.path.join(HERE, "calibrate.py"), "plant-summary", "--run-id", a.run_id, "--verifier-models", a.verifier_models], "plant-summary")
    log(f"== {a.run_id} complete {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
