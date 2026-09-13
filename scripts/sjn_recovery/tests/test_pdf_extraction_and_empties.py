"""2026-09-13 (after the Anglican packet review): PDF extraction repairs (Task 1), auditable empties (Task 2),
the widened opus slice (Task 3) and the ratified Gate 6 scope assertion.
Run: python -m pytest scripts/sjn_recovery/tests -q"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sjn_recovery.textutil import (join_soft_hyphens, strip_page_furniture, page_furniture_lines, intraword_split_candidates,  # noqa: E402
                                   repair_intraword_splits)
from sjn_recovery.agents import caveat_slice_hit  # noqa: E402
from sjn_recovery.packets import empty_result_option  # noqa: E402
from sjn_recovery.config import EMPTY_RESULT, EMPTY_RESULT_INCOMPLETE  # noqa: E402
from sjn_recovery import registry as R  # noqa: E402

FF, NL, SHY = chr(12), chr(10), chr(0xAD)


# ---------------------------------------------------------------- Task 1b: soft hyphens
def test_soft_hyphen_line_break_is_joined_and_midline_soft_hyphen_removed():
    stats = {}
    out = join_soft_hyphens("cove" + SHY + NL + "nantal union; self" + SHY + "dedication", stats)
    assert out == "covenantal union; selfdedication"
    assert stats == {"soft_hyphen_breaks_joined": 1, "soft_hyphens_removed_midline": 1}


# ---------------------------------------------------------------- Task 1a: page furniture
def _page(n, header, body_lines, footer=None):
    lines = [str(n), header] + body_lines + ([footer] if footer else [])
    return NL.join(lines)


def test_running_header_is_stripped_from_the_zone_but_a_body_heading_stays():
    body = ["Marriage is therefore holy and should", "Q.", "What is marriage?", "A.", "Amen."]
    pages = [_page(100 + i, "the ten commandments", body, footer=f"{100 + i}   Catechism") for i in range(6)]
    # the section title also stands once in the BODY of a page (its first page): that occurrence must survive
    pages[0] = NL.join(["100", "the ten commandments", "intro line", "the ten commandments", "body continues", "Q.", "What is marriage?", "A.", "Amen.", "100   Catechism"])
    rep = {}
    out = strip_page_furniture(FF.join(pages), rep)
    for p in out.split(FF)[1:]:
        assert "the ten commandments" not in p and "Catechism" not in p
    assert "the ten commandments" in out.split(FF)[0]          # the body heading on the first page survives
    assert rep["top"]["the ten commandments"] == 6 and rep["bottom"]["# catechism"] == 6
    # "Q." and "Amen." recur on every page but are body lines: the share test keeps them
    assert "q." not in rep["top"] and "amen." not in rep["bottom"]
    assert all("Q." in p and "Amen." in p for p in out.split(FF))


def test_stacked_furniture_is_peeled_over_rounds():
    words = ["saving", "sound", "true", "full", "plain", "whole", "right", "sure"]
    def body(i):        # real body text differs from page to page; a line identical on every page would be furniture by definition
        return [f"God to be necessary for the {words[i]} understanding of such things", "and thate there are some circumstances concerning worship"]
    pages = [NL.join(["THE WESTMINSTER CONFESSION OF FAITH", f"6.0{i}–.011", "Presbyterian Church", "in the United States",
                      "The United Presbyterian Church", "in the United States of America", str(150 + i)] + body(i)) for i in range(8)]
    rep = {}
    out = strip_page_furniture(FF.join(pages), rep)
    first = [l for l in out.split(FF)[0].split(NL) if l.strip()]
    assert "in the United States of America" not in first and "The United Presbyterian Church" not in first
    assert first[-2:] == body(0)
    assert rep["rounds"] >= 2


def test_prose_openers_and_sentences_are_never_furniture():
    pages = [NL.join([str(i), "or the following", "A hymn, psalm, or anthem may be sung.", "body"]) for i in range(5)]
    found, _ = page_furniture_lines(pages)
    assert "or the following" not in found["top"] and "a hymn, psalm, or anthem may be sung." not in found["top"]


# ---------------------------------------------------------------- Task 1b: intra-word splits (evidence only)
def test_attested_join_needs_closed_form_and_non_word_fragments():
    doc = "we read Mat thew and Matthew again; Mat thew twice. for give is not joined: for and give are words for us to give."
    cands = intraword_split_candidates(doc)
    assert [(c["a"], c["b"], c["evidence"]) for c in cands] == [("mat", "thew", "ATTESTED")]
    joins = []
    out = repair_intraword_splits(doc, joins=joins)
    assert out.count("Matthew") == 3 and "for give" in out and len(joins) == 2


def test_overlapping_pairs_are_all_seen():
    # a consuming regex would swallow "the cove" and never examine "cove nant"
    doc = "in the cove nant community; a lifelong cove nant between; a new cove nant with us; the covenant"
    cands = intraword_split_candidates(doc)
    assert any(c["a"] == "cove" and c["b"] == "nant" and c["pairs"] == 3 for c in cands)
    assert "covenant community" in repair_intraword_splits(doc)


def test_stem_extension_joins_only_after_two_attested_joins_on_the_same_fragment():
    doc = "a cove nant with us; the cove nant community; the covenant; the cove nantal union"
    cands = {(c["a"], c["b"]): c for c in intraword_split_candidates(doc)}
    assert cands[("cove", "nant")]["evidence"] == "ATTESTED"
    assert cands[("cove", "nantal")]["evidence"] == "STEM" and cands[("cove", "nantal")]["stem"] == "covenant"
    assert "covenantal union" in repair_intraword_splits(doc)
    # one attested join is not enough for a stem extension
    doc1 = "a cove nant with us; the covenant; the cove nantal union"
    assert ("cove", "nantal") not in {(c["a"], c["b"]) for c in intraword_split_candidates(doc1)}


def test_corpus_vocabulary_may_attest_the_closed_form_but_never_the_fragments():
    doc = "the cove nant community; a cove nant with us"          # "covenant" never closed in this document
    assert intraword_split_candidates(doc) == []
    cands = intraword_split_candidates(doc, corpus_vocab={"covenant"})
    assert [(c["a"], c["b"], c["closed_form_in_corpus"]) for c in cands] == [("cove", "nant", True)]
    # a fragment that is a real word of the document blocks the join whatever the corpus says
    doc2 = "the cove nant community; the cove is quiet"
    assert intraword_split_candidates(doc2, corpus_vocab={"covenant"}) == []


# ---------------------------------------------------------------- Task 3: the caveat slice
def test_caveat_slice_fires_on_partial_floor_or_named_hazards_only():
    assert caveat_slice_hit({"verdict": "ACCEPT_WITH_CAVEAT", "floor": "PARTIAL", "hazard_flags": []})
    assert caveat_slice_hit({"verdict": "ACCEPT_WITH_CAVEAT", "floor": "FULL", "hazard_flags": ["SEMANTIC_FLOOR"]})
    assert caveat_slice_hit({"verdict": "ACCEPT_WITH_CAVEAT", "floor": "FULL", "hazard_flags": ["SAME_WORD_DIFFERENT_MEANING"]})
    assert not caveat_slice_hit({"verdict": "ACCEPT_WITH_CAVEAT", "floor": "FULL", "hazard_flags": ["AUTHORITY_SCOPE"]})
    assert not caveat_slice_hit({"verdict": "ACCEPT", "floor": "PARTIAL", "hazard_flags": []})
    assert not caveat_slice_hit({"verdict": "REJECT", "floor": "PARTIAL", "hazard_flags": ["SEMANTIC_FLOOR"]})
    assert not caveat_slice_hit(None)


# ---------------------------------------------------------------- Task 2a/2b/2d: the empty-result option
def test_reviewed_state_is_offered_only_when_every_standard_is_full_or_exhausted():
    cov = {"BSR-AN-01": {"coverage": "FULL", "supplied": 39, "of": 39},
           "BSR-AN-05": {"coverage": "RETRIEVED", "supplied": 80, "of": 368}}
    rat = {"BSR-AN-01": "Article I predicates 'true' of God against false gods, not truthfulness", "BSR-AN-05": "sampled"}
    e = empty_result_option(cov, rat)
    assert e["offered"] is False and e["rendered_state"] is None
    assert e["honest_state_if_not_offered"] == EMPTY_RESULT_INCOMPLETE and e["review_incomplete"] == ["BSR-AN-05"]
    assert "80 of 368" in e["why_not_offered"]
    by = {r["registry_id"]: r for r in e["standards_reviewed"]}
    assert by["BSR-AN-01"]["status"] == "REVIEWED WHOLE" and by["BSR-AN-05"]["status"] == "SAMPLED" and by["BSR-AN-05"]["share"] == 0.217
    assert by["BSR-AN-01"]["silence_rationale"].startswith("Article I")
    cov["BSR-AN-05"] = {"coverage": "EXHAUSTED", "supplied": 368, "of": 368, "exhaustion": {"batches_done": 6, "batches_total": 6}}
    e2 = empty_result_option(cov, rat)
    assert e2["offered"] is True and e2["rendered_state"] == EMPTY_RESULT and e2["review_incomplete"] == []


# ---------------------------------------------------------------- the ratified Gate 6 scope
class _Reg:
    def __init__(self, config):
        self.config = config


def _cell(qid, state, retired=False):
    return {"queue_id": qid, "rendered_state": state, "retired": retired}


def test_gate6_scope_reads_the_rule_and_asserts_the_count():
    cfg = {"gate6_open_cell_rule": "OPEN when Rendered State (app-safe) begins 'NOT LOCATED' AND Historical Witness Retired is not TRUE.",
           "gate6_closed_states": "OUT OF SCOPE|VECTOR PENDING|VECTOR COMPLETE|PENDING REVIEW|Historical Witness Retired = TRUE",
           "gate6_open_cell_count": 2}
    q = [_cell("Q-1", "NOT LOCATED — NOT YET RECOVERED"), _cell("Q-2", "NOT LOCATED — CURRENT STANDARD REVIEWED"),
         _cell("Q-3", "NOT LOCATED — CURRENT SOURCE", retired=True), _cell("Q-4", "VECTOR PENDING"), _cell("Q-5", "A"), _cell("Q-6", "OUT OF SCOPE")]
    sc = R.gate6_scope(_Reg(cfg), q)
    assert sc["ok"] and sc["computed_open"] == 2 and sc["closed"] == 3 and sc["released"] == 1
    assert sc["closed_by_state"] == {"Historical Witness Retired = TRUE": 1, "VECTOR PENDING": 1, "OUT OF SCOPE": 1}
    cfg["gate6_open_cell_count"] = 3
    sc = R.gate6_scope(_Reg(cfg), q)
    assert not sc["ok"] and any("!= APP CONFIG gate6_open_cell_count 3" in p for p in sc["problems"])
    q.append(_cell("Q-7", "SOMETHING NEW"))
    cfg["gate6_open_cell_count"] = 2
    sc = R.gate6_scope(_Reg(cfg), q)
    assert not sc["ok"] and any("outside gate6_closed_states" in p for p in sc["problems"])
    sc = R.gate6_scope(_Reg({}), q[:6])
    assert not sc["ok"]                                   # a workbook without the keys cannot be run
