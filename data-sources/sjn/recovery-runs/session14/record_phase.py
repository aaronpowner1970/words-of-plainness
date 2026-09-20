"""Session 14: record, in author-rulings-pending-workbook.json, how each ruling was implemented once its phase passes
its tests. Idempotent.   python data-sources/sjn/recovery-runs/session14/record_phase.py <phase>"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")


def phase2(R):
    r = R["R6-54_production_voting_and_review_queue"]
    r["queue_file"] = "data-sources/sjn/recovery-runs/author-review-queue.json"
    r["as_implemented"] = (
        "VOTING. agents.CellRunner.verify_voted makes VOTES_PER_CANDIDATE (3) draws of the same verifier call and "
        "agents.vote takes the majority over VERDICT CLASS (the code-recomputed verdict, not the model's own line). The "
        "floor is the LOWEST floor among the majority's rubrics and the verdict is recomputed at it by the same "
        "verdict_from_rubric() every other path uses, so rule 2a's shape holds inside one model's vote: an "
        "ACCEPT_WITH_CAVEAT majority whose lowest majority floor is WORD_ONLY refuses BELOW_FLOOR. A dissenting draw's "
        "floor is NOT in the majority and cannot lower it. A vote with no majority (1/1/1) fails closed to the most "
        "conservative class present, never to a plurality of one. _verify_pass routes the primary, the opus slice and "
        "the 2c sample through verify_voted, so opus routes vote the same way. All three draws are issued before the "
        "vote is taken, so a pending draw never becomes a two-call majority. "
        "IDENTITY. Replicate r takes attempt base llm.REPLICATE_STRIDE * r (the session-8 `attempt + 100` convention), "
        "so each draw has its own call identity and the audit log's duplicate suppression cannot serve one answer back "
        "as three; replicate 0 keeps attempts 0 / 1, so every call identity written before session 14 is unchanged and "
        "an answered call is still served from the log. "
        "INSTRUMENT. agents.instrument() puts prompt version, call count, vote split, majority class and share, dissent "
        "and the replicate call ids on every voted rubric; a rubric stored before session 14 is labelled with what it "
        "actually was (its own version, ONE call, no vote split) and is never relabelled as a majority verdict. "
        "finalize() records the instrument of every deciding rubric, `v13_majority` and "
        "`public_certification_eligible`, with `public_certification_bar` naming the instrument where it is not. "
        "QUEUE. scripts/sjn_recovery/review_queue.py reads and writes the committed queue file; run.record_review_queue "
        "writes a branch's doubtful accepts to it after the branch finishes (and after a cost-cap stop). "
        "packets.build_branch_packet tests review_queue.hold() BEFORE a candidate reaches `accepted`, so a held item "
        "takes no seat, no lead and no parallel-witness record; it is kept on the card under `review_queue_held` and it "
        "withdraws the card's NOT LOCATED - CURRENT STANDARD REVIEWED offer. emit.assert_review_queue_clear runs in "
        "sjn-build-data.py BEFORE the first file is written and hard-stops on any held candidate id anywhere in the "
        "payload, or any CERTIFIED cell whose id carries a held item. An author_ruling of ADMIT releases an item; "
        "REFUSE keeps it barred with the author's reason; anything else is held (fail closed). "
        "NO CODE REFUSAL ON A SELF-REPORT (Codex C3): doubt queues, never refuses; the one guard that ever refused on a "
        "model self-report (R6-18's asserted_outside_formula) is scoped to gate6-v1.6, not the version in force.")
    r["queue_volume_before_use"] = {
        "what": "Codex C3(a): how many EXISTING accepts would enter the queue. session14/queue-volume.json",
        "reading_A_literal": "204 of 676 stored accepts (133 of 467 seated) are ACCEPT_WITH_CAVEAT at a PARTIAL final floor",
        "dissent_limb": "cannot fire on any stored verdict: all 735 stored rubrics are SINGLE calls (0 carry an instrument), "
                        "so there is no vote to dissent from",
        "note": "the queue is forward-looking: it is populated by voted runs. No stored verdict was enqueued by this session"}
    r["test"] = ("test_session14_voting (16 tests): three v1.3 calls per candidate under distinct identities; majority over "
                 "verdict class; lowest floor among the majority; a WORD_ONLY majority floor refuses BELOW_FLOOR; no "
                 "majority fails closed; opus routes voted the same way; all three draws issued before the vote; a stored "
                 "verdict labelled with its actual instrument; no seated verdict public-certification eligible on anything "
                 "but a v1.3 majority (checked against the real live-1 rubrics); doubt is dissent or caveat-at-PARTIAL; no "
                 "code path refuses on a model self-report at v1.3; the queue is a committed file of the ruled shape; held "
                 "until the author rules, unknown decision fails closed; a queued item cannot reach src/_data/sjn; the bar "
                 "runs before the first file is written; the packet builder seats no held item. "
                 "Mutation-checked: a planted queue item on Q-070's LEAD removed that seat from the sandbox Baptist packet "
                 "and withdrew the card's REVIEWED offer")


def phase3(R):
    R["R6-57_registered_section_extents"]["as_implemented"] = (
        "Already implemented by session 13 phase 2 and verified here against the artifact, not against its description: "
        "registered-sections.json carries `text_through` on the four mixed blocks (BSR-RP-04 1.3 and 2.3, BSR-LU-01 "
        "Ecumenical Creeds: The Apostles' Creed, BSR-AN-03), Registry._registered_sections ends the registered key after "
        "that string and fails loudly if it does not occur in the stored chunk, and BSR-EO-06 'Definition of Faith, "
        "Council of Chalcedon (451), paragraph 10' stands in the file's `not_registered` list with its reason. The three "
        "judgments the author ratified are now LOCKED BY TEST; nothing was re-implemented")
    R["R6-57_registered_section_extents"]["test"] = (
        "test_session14_extents: the AN-03 extent ends at 'he cannot be saved.' and the registered key carries no Gloria "
        "Patri while the stored chunk does; EO-06 Chalcedon paragraph 10 is in not_registered and in no branch's "
        "registered definitions; every mixed block registers only its creed portion and records its extent; a "
        "text_through that does not occur in the chunk fails loudly. Mutation-checked: removing AN-03's text_through, "
        "and listing EO-06 paragraph 10, each make the tests fail")
    R["R6-55_allocation_across_speaks_for_groups"]["as_implemented"] = (
        "No code change: the allocator is unchanged and Q-195's third Lutheran seat holds at Q-195-p1-BSR-LU-01-2, as "
        "the session 13 report describes it. Locked by test so no later session moves it without ruling on F.11")
    R["R6-55_allocation_across_speaks_for_groups"]["test"] = (
        "test_session14_extents: test_q195_third_lutheran_seat_holds_at_lu01_2_and_the_lcms_slot_at_lu02_1")
    R["R6-56_evidence_bar_for_a_tier_move"]["as_implemented"] = (
        "No tier moves in this session. BSR-AN-02 and BSR-RC-01 carry no authority_tier override in the rulings file and "
        "resolve at their workbook tier; the hold is locked by test")
    R["R6-56_evidence_bar_for_a_tier_move"]["test"] = (
        "test_session14_rulings: test_r6_56_holds_an02_and_rc01_at_their_present_tier; "
        "test_session14_extents: test_no_row_moved_tier_in_this_session")


PHASES = {"2": phase2, "3": phase3}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in PHASES:
        raise SystemExit(f"usage: record_phase.py <{'|'.join(sorted(PHASES))}>")
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    PHASES[sys.argv[1]](d["rulings"])
    out = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if out != raw:
        with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        print(f"phase {sys.argv[1]} recorded")
    else:
        print(f"phase {sys.argv[1]} unchanged")


if __name__ == "__main__":
    main()
