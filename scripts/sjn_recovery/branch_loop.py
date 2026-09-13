"""Drive ONE branch of the live run to completion: run.py (writes jobs) ↔ api_executor.py (answers them)
until run.py exits 0 (packet written) or the branch's cost cap stops it.

  python scripts/sjn_recovery/branch_loop.py --run-id live-1 --branch Lutheran --branch-cost-cap-usd 40 \
         --key-file <path to .env with ANTHROPIC_API_KEY> [--max-rounds 80] [--workers 6]

Every round is appended to data-sources/sjn/recovery-runs/<run>/<branch-slug>-loop.log (the Anglican run was
driven the same way by hand; this is that loop in one file). The key file path is passed through to the
executor and never printed. One branch per invocation — the next branch needs the author's explicit go."""
import argparse
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR  # noqa: E402


def slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--locator-model", default="sonnet")
    ap.add_argument("--verifier-models", default="sonnet,opus")
    ap.add_argument("--branch-cost-cap-usd", type=float, required=True)
    ap.add_argument("--max-cost-usd-per-invocation", type=float, default=None, help="executor per-invocation guard (default: the branch cap)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-rounds", type=int, default=80)
    ap.add_argument("--projection-per-cell-usd", type=float, default=0.336)
    a = ap.parse_args()
    run_dir = os.path.join(RUNS_DIR, a.run_id)
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, f"{slug(a.branch)}-loop.log")

    def log(line):
        print(line, flush=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def run(cmd, tag):
        log(f"-- round {rnd}: {tag} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr and p.stderr.strip() else "")
        for l in out.rstrip().splitlines():
            if l.startswith("  ok  ") and tag == "api_executor":
                continue                    # per-call lines stay in the executor's own output, not the loop log
            log(l)
        return p.returncode, out

    py = sys.executable
    log(f"== {a.branch} loop started {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} (cap {a.branch_cost_cap_usd} USD, max rounds {a.max_rounds})")
    for rnd in range(1, a.max_rounds + 1):
        rc, out = run([py, os.path.join(HERE, "run.py"), "--run-id", a.run_id, "--branch", a.branch,
                       "--locator-model", a.locator_model, "--verifier-models", a.verifier_models,
                       "--branch-cost-cap-usd", str(a.branch_cost_cap_usd), "--projection-per-cell-usd", str(a.projection_per_cell_usd),
                       "--i-have-author-authorization"], "run.py")
        log(f"   run.py exit {rc}")
        if rc == 0:
            log(f"== branch complete (run.py exit 0) {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
            break
        if rc != 10:
            log(f"!! run.py failed (exit {rc}); loop stopped")
            return rc
        rc, out = run([py, os.path.join(HERE, "api_executor.py"), "--run-id", a.run_id, "--workers", str(a.workers),
                       "--max-cost-usd", str(a.max_cost_usd_per_invocation or a.branch_cost_cap_usd), "--key-file", a.key_file], "api_executor")
        answered = sum(1 for l in out.splitlines() if l.startswith("  ok  "))
        log(f"   executor exit {rc} answered {answered}")
        if rc != 0 and answered == 0:
            log("!! executor answered nothing (cap, spend limit or fatal error); running run.py once more to write the partial packet")
            rc2, _ = run([py, os.path.join(HERE, "run.py"), "--run-id", a.run_id, "--branch", a.branch,
                          "--locator-model", a.locator_model, "--verifier-models", a.verifier_models,
                          "--branch-cost-cap-usd", str(a.branch_cost_cap_usd), "--projection-per-cell-usd", str(a.projection_per_cell_usd),
                          "--i-have-author-authorization"], "run.py")
            log(f"   run.py exit {rc2}; loop stopped")
            return 1
    else:
        log(f"!! max rounds ({a.max_rounds}) reached; loop stopped with calls still pending")
        return 1
    log(f"== {a.branch} loop ended {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
