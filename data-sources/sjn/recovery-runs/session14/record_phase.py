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


def phase4(R):
    R["R6-47_adoption_is_not_confession"]["as_implemented"] = (
        "BSR-AN-06 carries the witness treatment in its OWN authority_tier, "
        "'OFFICIAL_EXPOSITION (witness; adopted historical document, not confessed)', so registry.is_witness_row reads "
        "it and no later edit can drop a flag and quietly promote the row. Fail closed under B1(c): below the genre's "
        "tier, below every confessed Anglican row, and allocation's witness-only guard means it cannot seat a cell "
        "alone. Its sections are in registered-sections.json's `not_registered` list with R6-47's reason, so no AN-06 "
        "chunk is a registered creed or definition text. The TIER VALUE is Code's reading of B1(c), not an author "
        "ruling: three ranked readings with their weaknesses are in session14/write_an06.py, and the report measures "
        "the difference (the chosen reading changes no lead; the genre-tier reading would move five)")
    R["R6-47_adoption_is_not_confession"]["test"] = (
        "test_session14_an06: test_an06_is_a_witness_row_and_cannot_seat_a_cell_alone, "
        "test_an06_has_no_registered_sections_and_the_r6_27_test_covers_it, "
        "test_listing_an06_as_a_registered_section_fails_loudly (mutation check)")

    R["R6-48_an06_historical_documents_row"]["as_implemented"] = (
        "sources.tec_historical_documents chunks BCP pp. 863-865 from the fetch cache: the p. 863 title page, the "
        "Chalcedonian Definition (p. 864) and the Quicunque Vult JOINED across the p. 864/865 break. A document is "
        "accumulated across pages until the next printed heading, and the walk stops at the first stop heading "
        "(Preface / Articles of Religion / Chicago-Lambeth). The adapter REFUSES rather than stores if the Quicunque "
        "Vult does not end at its last sentence, if there is not exactly one of them, or if a chunk runs past the "
        "row's extent. The row itself comes through the R6-42 row-added-by-ruling path (rulings.added_rows / "
        "Registry._add_ruled_rows), with its adoption block and card disclosure. Corpus: 3 chunks, 4,899 chars, "
        "text_hash 4f8ff6f90301bcb9..., embedded; no network (fetch cache reused, 0 new files)")
    R["R6-48_an06_historical_documents_row"]["test"] = (
        "test_session14_an06: test_no_an06_quicunque_vult_chunk_ends_at_one_almighty, "
        "test_no_an06_chunk_runs_past_bcp_p_865, test_the_historical_documents_are_their_own_row, "
        "test_the_adapter_refuses_a_quicunque_vult_that_is_cut_at_the_page_break, "
        "test_a_candidate_whose_text_moved_to_another_row_follows_the_text")

    R["R6-49_tec_articles_of_religion_held"]["as_implemented"] = (
        "sources.TEC_HISTORICAL_STOP_HEADINGS stops the BSR-AN-06 walk at 'Articles of Religion' (and at the 1549 "
        "Preface and the Chicago-Lambeth Quadrilateral). No row was added and no page past BCP p. 865 was chunked")
    R["R6-49_tec_articles_of_religion_held"]["test"] = (
        "test_session14_an06: test_the_tec_articles_of_religion_are_not_fetched_and_not_added")

    R["R6-50_an06_an03_same_text_pair"]["as_implemented"] = (
        "rulings.same_text_declarations reads the pair from the ruling that declared it, WITH ITS SCOPE: R6-50 names "
        "the Quicunque Vult SECTION, not the whole row, so the declaration carries locator_contains 'Quicunque Vult'. "
        "allocation.allocate applies a scoped declaration only to candidates located in that section: the Quicunque "
        "Vult takes no slot beside BSR-AN-03 and is recorded as a parallel witness, while the Chalcedonian Definition "
        "competes for its own slot. Without the scope the Chalcedonian Definition would have been recorded as a "
        "parallel witness of the Athanasian Creed on four cards (measured before the scope was added). BSR-AN-06 is "
        "also excluded from rule 1b's English-translation pairing (allocation.declared_same_text_alternate): one row, "
        "one relationship")
    R["R6-50_an06_an03_same_text_pair"]["test"] = (
        "test_session14_an06: test_the_same_text_pair_is_scoped_to_the_quicunque_vult_section; "
        "test_session6_rulings: test_rulings_file_declares_the_eo_pair_and_the_refusals")

    R["R6-51_an04_extent_and_p844_rubric"]["as_implemented"] = (
        "sources.tec_outline_of_faith now stores the BCP p. 844 rubric 'Concerning the Catechism' as its first chunk, "
        "with division 'rubric (integral text)', and REFUSES if that page does not open with the rubric. It stops at "
        "the Historical Documents title page as session 12 made it, and no longer chunks the pages after it. The "
        "rubric is not a registered section (it is a rubric about the catechism, not a creed or definition). Corpus: "
        "126 -> 125 chunks (1 rubric + 124 Q/A), 23,763 -> 22,067 chars, text_hash 44e8a00c... -> e7cc6179...; no "
        "network. R6-45's scope marker is discharged: no AN-04 chunk awaits a scope ruling any more")
    R["R6-51_an04_extent_and_p844_rubric"]["test"] = (
        "test_session14_an06: test_an04_is_bcp_pp_844_to_862_with_the_rubric_stored_and_unregistered; "
        "test_session12_corpus_repair: test_the_outline_ends_at_the_historical_documents_title_page (updated)")

    R["R6-52_1979_a133_citation"]["as_implemented"] = (
        "BSR-AN-06's adoption_act cites Journal 1979 p. C-8 per the Archives and records the 1985 note's C-9 as "
        "UNRECONCILED, in the same words; it is not silently corrected and it is not counted as a second instrument")
    R["R6-52_1979_a133_citation"]["test"] = "test_session14_an06: test_the_historical_documents_are_their_own_row"

    R["R6-53_tec_glossary_context_only"]["as_implemented"] = (
        "Neither the TEC glossary nor the Brief Dictionary is a registry row, a fetched host or a source in any "
        "adoption_verified field except as named context: BSR-AN-06's adoption_verified records them as context only. "
        "No code path reads them")
    R["R6-53_tec_glossary_context_only"]["test"] = (
        "no code to test: recorded on BSR-AN-06's adoption_verified. The negative is enumerable — the registry has no "
        "row on a Church Publishing host, and the fetch audit records no request to one")

    r45 = R["R6-45_an04_historical_documents_scope"]
    r45["superseded_by"] = ("R6-48 (session 14): the Historical Documents became their own row, BSR-AN-06, so BSR-AN-04 "
                            "holds no chunk the R6-45 marker matches. The marker is left in force and inert: it would "
                            "fire again if any Historical Documents chunk were ever rebuilt on BSR-AN-04")
    r45["discharged"] = "2026-09-19, session 14 phase 4"


PHASES = {"2": phase2, "3": phase3, "4": phase4}


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
