"""Session 14, phase 6 (CODE-SJN-19): ONE coder proposal for ONE named, already-seated candidate.

The session 13 report (§Q-179, and its remaining-item 5) names Q-179 LU-02-2 -- Augsburg Confession Art. XIX,
"God does create and preserve nature", FULL -- as seated by the session 13 tier moves but carrying NO coder
proposal, needing "one coder call when next run".

run.py would code it, but only by re-entering the FINISHED Lutheran branch, which re-runs locator and verifier
passes across 39 cells. This issues exactly the one coder call agents.CellRunner.code() would have issued for
this candidate, against the stored final rubric, and writes it into the cell's `coding` map. Nothing else in the
cell is touched; the packet rebuild that follows reads it like any other proposal.

Refuses unless the candidate is a CURRENT survivor AND seated on the CURRENT PACKET CARD.

The seating test reads the packet, not the cell state's stored `allocation.kept`. The two disagree on 11 of 247
cards and on MEMBERSHIP (not merely slot order) on three -- Q-179, Q-195 and Q-205 -- because refinalize()
allocates over the candidates as STORED while packets.py allocates over the entries it has relocated and
re-asserted against the current store. The packet is the publication-facing allocator: it is what the author
reads, what the extract is cut from, and it is packets.py itself that writes `coder_note` for a candidate its
own allocation seats but the branch coder never coded. So the packet decides what "reaches the card".

  python data-sources/sjn/recovery-runs/session14/phase6_code_one.py --queue-id Q-179 --candidate-id Q-179-p1-BSR-LU-02-2
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

from sjn_recovery.config import RUNS_DIR                                      # noqa: E402
from sjn_recovery.registry import (Registry, load_predicates, load_comparators,  # noqa: E402
                                   load_queue, open_cells, assert_gate6_scope)
from sjn_recovery.llm import LLM                                              # noqa: E402
from sjn_recovery.agents import CellRunner                                    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="live-1")
    ap.add_argument("--queue-id", required=True)
    ap.add_argument("--candidate-id", required=True)
    ap.add_argument("--packet", required=True, help="the rebuilt branch packet; its card decides what is seated")
    ap.add_argument("--out")
    a = ap.parse_args()

    reg = Registry()
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    assert_gate6_scope(reg, queue, print)
    cell = {c["queue_id"]: c for c in open_cells(queue)}[a.queue_id]
    llm = LLM(a.run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, a.run_id, "cells"),
                        "sonnet", ["sonnet", "opus"], log=print, run_coder=True)
    st = runner.load(a.queue_id)
    card = next((c for c in json.load(open(a.packet, encoding="utf-8"))["cards"]
                 if c["queue_id"] == a.queue_id), None)
    if card is None:
        raise SystemExit(f"REFUSED: {a.queue_id} has no card in {a.packet}")
    seated = [e["candidate_id"] for e in card.get("candidates", [])]
    if a.candidate_id not in seated:
        raise SystemExit(f"REFUSED: {a.candidate_id} is not seated on the current packet card {seated} — "
                         "a coder proposal is only written for a candidate that reaches the card")
    cand = next((c for c in st["survivors"] if c["candidate_id"] == a.candidate_id), None)
    if cand is None:
        raise SystemExit(f"REFUSED: {a.candidate_id} is not a current survivor of {a.queue_id}")
    existing = (st.get("coding") or {}).get(a.candidate_id)
    if existing and existing.get("status") == "DONE":
        print(f"== {a.candidate_id} already has a DONE coder proposal; nothing issued")
        return 0

    rubric = runner.final_rubric(st, a.candidate_id)
    proposal = runner.code(cell, cand, rubric)
    st.setdefault("coding", {})[a.candidate_id] = proposal
    st["coded_out_of_band"] = dict(st.get("coded_out_of_band") or {}, **{a.candidate_id: {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "why": "session 14 phase 6 (CODE-SJN-19): seated by the session 13 tier moves after the branch coder ran; "
               "one coder call, issued without re-entering the finished Lutheran branch",
        "call_id": proposal.get("call_id")}})
    runner.save(st)
    print(f"== {a.queue_id} {a.candidate_id}: coder status {proposal.get('status')} "
          f"rendered_state={proposal.get('rendered_state')!r} diverges={proposal.get('diverges_from_family_code')!r}")
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"queue_id": a.queue_id, "candidate_id": a.candidate_id, "proposal": proposal},
                      fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    return 10 if proposal.get("status") == "PENDING" else 0


if __name__ == "__main__":
    sys.exit(main())
