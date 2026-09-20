"""Session 14, phase 6 (CODE-SJN-19): record THIS RUN's doubtful accepts in the author review queue.

R6-54 / Codex C3(a). run.py's record_review_queue() walks every candidate of a whole branch, which on this
run would sweep the 204 pre-existing accepts CODE-SJN-16 §3.4 identified into the queue. The author has NOT
ruled on that sweep, and the prompt for this run says the queue stays FORWARD-LOOKING. So the entry shape
below is run.py's, field for field, but the scope is exactly the candidates THIS run re-verified or newly
verified -- named explicitly, never derived from a branch.

Doubt is any dissenting vote, or ACCEPT_WITH_CAVEAT at PARTIAL; finalize() computes it and puts it on the
final verdict as `review_queue_reasons`. Nothing is refused here: the item keeps the verdict the verifier
gave and waits for the author.

  python data-sources/sjn/recovery-runs/session14/phase6_record_queue.py --candidates <json with candidate_id/queue_id>
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery.config import RUNS_DIR                      # noqa: E402
from sjn_recovery import review_queue                          # noqa: E402
from sjn_recovery.registry import Registry, load_queue, open_cells  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="live-1")
    ap.add_argument("--candidates", required=True, help="json list of {queue_id, candidate_id}")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    reg = Registry()
    cells = {c["queue_id"]: c for c in open_cells(load_queue(reg.wb))}
    want = json.load(open(a.candidates, encoding="utf-8"))
    scope = {(w["queue_id"], w["candidate_id"]) for w in want}

    entries, skipped = [], []
    for qid, cid in sorted(scope):
        cell = cells[qid]
        st = json.load(open(os.path.join(RUNS_DIR, a.run_id, "cells", f"{qid}.json"), encoding="utf-8"))
        cand = next((c for p in st["passes"].values() for c in p.get("candidates", []) if c["candidate_id"] == cid), None)
        fin = ((st.get("verifications") or {}).get(cid) or {}).get("final") or {}
        reasons = fin.get("review_queue_reasons") or []
        if not reasons:
            skipped.append((qid, cid, fin.get("verdict")))
            continue
        entries.append({"queue_id": qid, "candidate_id": cid, "branch": st.get("branch"),
                        "registry_id": cand.get("registry_id"), "locator": cand.get("locator"),
                        "phrase": cand.get("phrase"), "predicate": cell.get("predicate"),
                        "reasons": reasons, "verdict": fin.get("verdict"), "floor_final": fin.get("floor_final"),
                        "instrument": fin.get("instrument_of_record"),
                        "detail": "; ".join(reasons),
                        "entered": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "author_ruling": None})
    print(f"== scope {len(scope)} candidate(s): {len(entries)} doubtful, {len(skipped)} with no queue reason")
    for e in entries:
        print(f"   QUEUE {e['queue_id']} {e['candidate_id']} {e['verdict']}/{e['floor_final']} <- {e['detail']}")
    if a.dry_run:
        return 0
    if entries:
        added, updated = review_queue.add(entries, log=print)
        print(f"   {added} added, {updated} refreshed")
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"scope": sorted(scope), "entries": entries,
                       "no_queue_reason": skipped}, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
