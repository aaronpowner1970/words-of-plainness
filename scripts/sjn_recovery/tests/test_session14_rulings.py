"""Session 14 (2026-09-19): rulings R6-47 to R6-57 (Comparison Principles Codex v0.8).

  phase 1  the eleven rulings are recorded
  phase 2  R6-54 / Codex C1(a), C3(a): production majority voting and the author review queue
  phase 3  R6-57 / Codex B1(e): registered section extents; R6-55 and R6-56 holds
  phase 4  R6-47 to R6-53: the AN-04 / AN-06 corpus repair"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import rulings  # noqa: E402

SESSION14_RULINGS = (
    "R6-47_adoption_is_not_confession",
    "R6-48_an06_historical_documents_row",
    "R6-49_tec_articles_of_religion_held",
    "R6-50_an06_an03_same_text_pair",
    "R6-51_an04_extent_and_p844_rubric",
    "R6-52_1979_a133_citation",
    "R6-53_tec_glossary_context_only",
    "R6-54_production_voting_and_review_queue",
    "R6-55_allocation_across_speaks_for_groups",
    "R6-56_evidence_bar_for_a_tier_move",
    "R6-57_registered_section_extents",
)


# ---------------------------------------------------------------- phase 1
def test_r6_47_to_r6_57_are_recorded():
    R = rulings.load()["rulings"]
    for key in SESSION14_RULINGS:
        assert key in R, key
        assert R[key]["status"] == "RATIFIED", key
        assert "session 14" in R[key]["source"], key
        assert "v0.8" in R[key]["codex"], key
        assert R[key]["rule"].strip(), key


def test_r6_54_carries_the_voting_and_queue_shapes_the_codex_ruled():
    r = rulings.load()["rulings"]["R6-54_production_voting_and_review_queue"]
    assert r["voting"]["calls_per_candidate"] == 3
    assert r["voting"]["prompt_version"] == "gate6-v1.3"
    assert r["voting"]["majority_over"] == "verdict class"
    assert set(r["voting"]["instrument_recorded"]) == {"prompt_version", "call_count", "vote_split"}
    assert r["doubt"] == ["any dissenting vote", "ACCEPT_WITH_CAVEAT at a PARTIAL floor"]
    assert r["queue"]["committed_file"] is True
    assert set(r["queue"]["bars"]) == {"the packet builder", "the emit step"}


def test_r6_57_ratifies_the_three_session13_extent_judgments():
    r = rulings.load()["rulings"]["R6-57_registered_section_extents"]
    assert set(r["ratifies"]) == {"1_mixed_block_extent", "2_gloria_patri_left_out", "3_eo06_chalcedon_para_10_left_out"}


def test_r6_56_holds_an02_and_rc01_at_their_present_tier():
    r = rulings.load()["rulings"]["R6-56_evidence_bar_for_a_tier_move"]
    assert set(r["rows_held"]) == {"BSR-AN-02", "BSR-RC-01"}
    # the hold is a hold: no ruling may carry an authority_tier override for either row
    for rid, ov in rulings.registry_overrides().items():
        if rid in ("BSR-AN-02", "BSR-RC-01"):
            assert "authority_tier" not in ov["fields"], (rid, ov)
