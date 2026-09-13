"""Launch one or more branches of a live run IN ORDER, failing loudly (Gate 6 session 5, Task 8a).

  python scripts/sjn_recovery/launch_branches.py --run-id live-1 --branches "Eastern Orthodox" --branch-cost-cap-usd <cap> \
         --key-file <.env> [--out recovery-runs/live-1/launch-<date>.out]

Replaces the ad hoc shell loop of session 4, which piped branch_loop.py through `grep` and echoed `$?` — grep's exit status,
not the branch's — so a Methodist / Wesleyan run.py crash (exit 1) was reported as "done rc=0" and the loop moved on.

Rules:
  * every branch_loop.py exit code is read directly from the child process, never through a pipe;
  * a non-zero exit stops the launcher at once: no later branch starts, the launcher prints a !! LAUNCH FAILED banner and
    exits with that same non-zero code;
  * an exit 0 is not believed on its own: the branch's packet must exist, be built after the branch started, carry
    `partial: false`, `cells_not_finished: 0`, and every card DONE / EMPTY — otherwise the launcher fails with exit 4;
  * everything the child prints is written to the --out file line by line (the loop's own log is unchanged).
One branch per author go remains the policy; the launcher only guarantees that a failure is caught by the harness."""
import argparse
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import PACKETS_DIR, RUNS_DIR  # noqa: E402

PACKET_NOT_TRUSTED = 4


def slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def verify_packet(branch, started):
    """(ok, detail): a finished branch's packet, written after `started`, not partial, every cell finished."""
    p = os.path.join(PACKETS_DIR, f"{slug(branch)}.json")
    if not os.path.exists(p):
        return False, f"no packet at {p}"
    with open(p, encoding="utf-8") as fh:
        pk = json.load(fh)
    if str(pk.get("built_at") or "") < started:
        return False, f"packet built_at {pk.get('built_at')} predates this launch ({started}): it is not this run's packet"
    if pk.get("partial"):
        return False, f"packet is PARTIAL: cap_state {pk.get('cap_state')}"
    if pk.get("cells_not_finished"):
        return False, f"packet has {pk['cells_not_finished']} unfinished cell(s)"
    bad = [c["queue_id"] for c in pk.get("cards", []) if c.get("status") not in ("DONE", "EMPTY", "EMPTY_WITNESS_ONLY")]
    if bad:
        return False, f"cards not finished: {bad[:10]}"
    return True, f"{pk['cells']} cells, {pk['cells_with_candidates']} with candidates, {pk['cells_empty']} empty, partial false"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--branches", required=True, help="comma-separated, run in this order")
    ap.add_argument("--branch-cost-cap-usd", type=float, required=True)
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--out")
    ap.add_argument("--extra", default="", help="extra arguments passed through to branch_loop.py (space-separated)")
    a = ap.parse_args()
    out = a.out or os.path.join(RUNS_DIR, a.run_id, f"launch-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.out")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    def say(line):
        print(line, flush=True)
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    branches = [b.strip() for b in a.branches.split(",") if b.strip()]
    say(f"=== launch {now()}: run {a.run_id}, branches {branches}, cap {a.branch_cost_cap_usd} USD each")
    for br in branches:
        started = now()
        say(f"=== {br} {started}")
        cmd = [sys.executable, os.path.join(HERE, "branch_loop.py"), "--run-id", a.run_id, "--branch", br,
               "--branch-cost-cap-usd", str(a.branch_cost_cap_usd), "--key-file", a.key_file] + a.extra.split()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            if line.startswith("  ok  "):
                continue
            say(line.rstrip("\n"))
        rc = proc.wait()                                   # the child's own exit code — never a pipe's
        if rc != 0:
            say(f"!! LAUNCH FAILED: {br} branch_loop.py exited {rc} at {now()}; no further branch starts "
                f"({', '.join(branches[branches.index(br) + 1:]) or 'none'} not run)")
            return rc
        ok, detail = verify_packet(br, started)
        if not ok:
            say(f"!! LAUNCH FAILED: {br} exited 0 but its packet cannot be trusted as finished — {detail}; no further branch starts")
            return PACKET_NOT_TRUSTED
        say(f"=== {br} done rc=0 {now()} — packet verified: {detail}")
    say(f"=== launch ended {now()}: {len(branches)} branch(es) complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
