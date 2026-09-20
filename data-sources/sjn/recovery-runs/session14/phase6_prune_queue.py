"""Session 14, phase 6 (CODE-SJN-19): undo run.py's BRANCH-WIDE review-queue sweep, keeping the queue
forward-looking.

run.py's record_review_queue() walks EVERY candidate of the branch it just ran and queues every doubtful
accept it finds, whatever instrument gave it. Driving Track B through branch_loop therefore swept 18
PRE-EXISTING Baptist accepts into the queue -- all of them BSR-BA-01/02/03, none of them the BSR-BA-04 row
this run read, and every one entering on the ACCEPT_WITH_CAVEAT_AT_PARTIAL limb that CODE-SJN-16 section 3.4
flagged and the author HAS NOT RULED ON. The packet builder then held all 18 off their cards, which silently
stripped seats from the Baptist packet.

The prompt for this run is explicit: the queue stays forward-looking; the existing accepts are not to be swept
in. So this prunes the queue back to the items THIS RUN's own instrument produced.

THE TEST IS THE INSTRUMENT, NOT A HAND-WRITTEN LIST: an item is kept only if every deciding rubric behind its
verdict is a gate6-v1.3 MAJORITY. A pre-session-14 verdict is a single call by definition and cannot pass;
anything this run voted on does. Items removed are written to --out with their reason, so the author can admit
them with one ruling if he wants them.

  python .../phase6_prune_queue.py --out session14/phase6-queue-pruned.json [--dry-run]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery.config import RUNS_DIR                      # noqa: E402
from sjn_recovery import review_queue                          # noqa: E402
from sjn_recovery.agents import instrument, is_voted_v13       # noqa: E402

SKIP = ("final", "_route", "final_at_run", "superseded_rubrics", "reverified", "repointed")


def deciding_rubrics(ver):
    return {m: r for m, r in ver.items() if isinstance(r, dict) and m not in SKIP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="live-1")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    q = review_queue.load()
    path = q.get("_path") or review_queue.QUEUE_PATH
    kept, removed = [], []
    for it in review_queue.items(q):
        st = json.load(open(os.path.join(RUNS_DIR, a.run_id, "cells", f"{it['queue_id']}.json"), encoding="utf-8"))
        rubs = deciding_rubrics((st.get("verifications") or {}).get(it["candidate_id"]) or {})
        voted = bool(rubs) and all(is_voted_v13(r) for r in rubs.values())
        if voted:
            kept.append(it)
        else:
            removed.append(dict(it, removed_because=(
                "queued by run.py's branch-wide sweep, not by this run's own reading: its deciding rubric(s) are "
                + "; ".join(f"{m}: {instrument(r)['prompt_version']} x{instrument(r)['call_count']} "
                            f"({instrument(r)['voting']})" for m, r in sorted(rubs.items()))
                + ". The queue stays forward-looking until the author rules on the existing accepts.")))
    print(f"== queue {len(review_queue.items(q))} item(s): keeping {len(kept)}, removing {len(removed)}")
    for r in removed:
        print(f"   REMOVE {r['queue_id']} {r['candidate_id']} ({r.get('registry_id')}) {','.join(r['reasons'])}")
    for k in kept:
        print(f"   KEEP   {k['queue_id']} {k['candidate_id']} ({k.get('registry_id')}) {','.join(k['reasons'])}")
    if a.dry_run:
        return 0
    q.pop("_missing", None); q.pop("_path", None)
    q["items"] = sorted(kept, key=lambda i: i["candidate_id"])
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(q, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"kept": [i["candidate_id"] for i in kept], "removed": removed}, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    print(f"   wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
