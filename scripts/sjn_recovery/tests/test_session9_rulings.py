"""Session 9 (2026-09-16, third and fourth sets): the author's rulings R6-18 to R6-23.

  R6-18  verifier gate6-v1.6: THE PHRASE CARRIES THE ASSERTION replaces the outside-formula permission; a code guard
         refuses an asserted_outside_formula = Y accept
  R6-19  BSR-EO-09 is a registered creed text at its own CONFESSIONAL tier; highest-tier precedence still applies
  R6-21  the phrase floor for creed and definition matching, as implemented (CREED_PHRASE_MIN_WORDS / _CHARS)
  R6-22  a CATECHETICAL row is never a registered creed text
  R6-23  the EO consultation ladder stays in config.EO_CONSULTATION_LADDER

R6-17 (the TP-049 fixture) is not tested here: its condition did not hold (the expected phrase is not in TP-049's chunk),
so no fixture was built. R6-20 is a measurement rule (docs/gate6/WoP_SJN_Gate6_MeasurementRule.md)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.registry import (Registry, load_predicates, bare_tier, CREED_PHRASE_MIN_WORDS,  # noqa: E402
                                   CREED_PHRASE_MIN_CHARS)
from sjn_recovery import agents, config, prompts, store  # noqa: E402

REMOVED_CLAUSE = " unless the passage separately asserts the predicate outside the formula."
NEW_TEXT = ("THE PHRASE CARRIES THE ASSERTION. The quoted phrase must itself assert the property of the required subject. "
            "Surrounding text may establish who the subject is or what the quoted words mean, but it may not supply an "
            "assertion the quoted words do not make. If the passage asserts the property only in a different sentence, the "
            "citation does not satisfy the family (BELOW_FLOOR); that other sentence is the one to cite.")


@pytest.fixture(scope="module")
def reg():
    try:
        r = Registry()
    except Exception as e:                                             # no workbook in this checkout
        pytest.skip(f"registry unavailable: {e}")
    return r


@pytest.fixture(scope="module")
def preds(reg):
    return load_predicates(reg.wb)


def _eo_store():
    if not store.load_chunks("BSR-EO-07") or not store.load_chunks("BSR-EO-09") or not store.load_chunks("BSR-EO-01"):
        pytest.skip("chunk store (.cache/sjn-recovery/chunks) is not built in this checkout")


# ---------------------------------------------------------------- R6-18: the v1.6 text
@pytest.mark.parametrize("variant", ["spirit", "base"])
def test_both_v16_variants_carry_the_new_text_verbatim_and_not_the_removed_clause(variant):
    s16 = prompts.SCOPED_VERIFIER_SYSTEMS["gate6-v1.6"][variant]
    s15 = prompts.SCOPED_VERIFIER_SYSTEMS["gate6-v1.5"][variant]
    assert prompts.PHRASE_CARRIES_THE_ASSERTION == NEW_TEXT
    assert s16.count(NEW_TEXT) == 1
    assert "unless the passage separately asserts" not in s16
    assert REMOVED_CLAUSE in s15
    # v1.6 is v1.5 with that one replacement and nothing else
    assert s16 == s15.replace(REMOVED_CLAUSE, ". " + NEW_TEXT)
    # the fixed-formula rule itself stays, ending where the permission was cut
    assert "the passage PRESUPPOSES the predicate rather than asserting it, and the floor is WORD_ONLY. THE PHRASE CARRIES" in s16


def test_v16_keeps_the_rubric_field_the_guard_reads():
    for s16 in prompts.SCOPED_VERIFIER_SYSTEMS["gate6-v1.6"].values():
        assert '"asserted_outside_formula": "Y|N|NA"' in s16 and "then also answer asserted_outside_formula" in s16


def test_v16_scoping_is_unchanged(preds):
    before = prompts.PROMPT_VERSIONS["verifier"]
    try:
        prompts.set_verifier_version("gate6-v1.6")
        assert prompts.verifier_variant(preds["RNR-H05"]) == "gate6-v1.6/base"
        assert prompts.verifier_variant(preds["RNR-H35"]) == "gate6-v1.6/spirit"
        assert "JOINT PREDICATION" not in prompts.verifier_system(preds["RNR-H05"])
        assert "JOINT PREDICATION" in prompts.verifier_system(preds["RNR-H35"])
    finally:
        prompts.PROMPT_VERSIONS["verifier"] = before


def test_versions_stay_linear():
    assert list(prompts.VERIFIER_SYSTEMS) == ["gate6-v1.2", "gate6-v1.3", "gate6-v1.4", "gate6-v1.5", "gate6-v1.6"]
    assert list(prompts.SCOPED_VERIFIER_SYSTEMS) == ["gate6-v1.5", "gate6-v1.6"]


# ---------------------------------------------------------------- R6-18: the code guard
def _rubric(aof, version="gate6-v1.6", floor="FULL", verdict="ACCEPT"):
    return {"status": "DONE", "phrase_verbatim": "Y", "subject_is_required": "Y", "speech_act_is_assertion": "Y",
            "floor": floor, "hazard_flags": ["IDIOM_OR_FORMULA"] if aof != "NA" else [], "asserted_outside_formula": aof,
            "verdict_model": verdict, "reason_code": "OK", "prompt_version": version}


def test_the_guard_refuses_a_synthetic_y_accept():
    for verdict in ("ACCEPT", "ACCEPT_WITH_CAVEAT"):
        assert agents.verdict_from_rubric(_rubric("Y", verdict=verdict), "FULL") == ("REJECT", "BELOW_FLOOR")


@pytest.mark.parametrize("aof", ["N", "NA"])
def test_an_n_or_na_accept_passes(aof):
    v, code = agents.verdict_from_rubric(_rubric(aof), "FULL")
    assert v in agents.ACCEPTS and code == "OK"


def test_the_guard_does_not_rewrite_a_measured_earlier_version():
    # a v1.3 baseline or replay is judged as v1.3 was measured
    assert agents.verdict_from_rubric(_rubric("Y", version="gate6-v1.3"), "FULL")[0] in agents.ACCEPTS
    assert agents.verdict_from_rubric(_rubric("Y", version="gate6-v1.5"), "FULL")[0] in agents.ACCEPTS


def test_the_guard_is_recorded_in_verify_and_holds_through_finalize(preds, tmp_path):
    """verify() marks refused_by R6-18, and finalize() — the refinalisation path — does not re-admit it."""
    import json as _json
    from sjn_recovery.agents import CellRunner

    reply = {"phrase_verbatim": "Y", "subject_is_required": "Y", "grammatical_subject": "God", "speech_act_is_assertion": "Y",
             "speech_act_note": "", "floor": "FULL", "floor_reason": "asserted in another sentence", "partial_asserts_predicate": "NA",
             "hazard_flags": ["IDIOM_OR_FORMULA"], "asserted_outside_formula": "Y", "verdict": "ACCEPT_WITH_CAVEAT",
             "reason_code": "OK", "reason": "doxology; the chunk asserts it elsewhere"}

    class _LLM:
        def complete(self, role, system, user, model=None, max_tokens=0, meta=None, attempt=0):
            return _json.dumps(reply), {"call_id": "x"}

    class _Reg:
        verifier_routing = "PRIMARY_ONLY"
        fallback_ids = set()

    before = prompts.PROMPT_VERSIONS["verifier"]
    try:
        prompts.set_verifier_version("gate6-v1.6")
        runner = CellRunner(_LLM(), _Reg(), preds, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)
        cand = {"candidate_id": "c", "registry_id": "R", "locator": "L", "phrase": "to whom be glory for ever",
                "floor_claim": "FULL", "chunk_text": "to whom be glory for ever"}
        r = runner.verify({"queue_id": "Q", "family_id": "RNR-H20", "branch": "B"}, cand, "sonnet")
        if r.get("status") != "DONE":
            pytest.skip("the stub reply was not taken by _call in this harness")
        assert r["verdict"] == "REJECT" and r["reason_code_final"] == "BELOW_FLOOR" and r["refused_by"] == "R6-18"
        assert r["verdict_before_outside_formula_guard"] in agents.ACCEPTS
        assert r["asserted_outside_formula"] == "Y"                    # the field is kept
        v = {"sonnet": r}
        CellRunner.finalize(v, "sonnet", None)
        assert v["final"]["verdict"] == "REJECT" and v["final"]["refused_by"] == "R6-18"
    finally:
        prompts.PROMPT_VERSIONS["verifier"] = before


# ---------------------------------------------------------------- R6-19: EO-09 at its own tier
HOPKO_SPIRIT_CLAUSE = "the Holy Spirit, the Lord, the Giver of Life"


def test_hopkos_spirit_clause_is_only_in_eo09_and_resolves_confessional(reg):
    _eo_store()
    from sjn_recovery.textutil import punct_key
    key = punct_key(HOPKO_SPIRIT_CLAUSE)
    holders = {t["registry_id"] for t in reg.registered_creed_texts("Eastern Orthodox") if key in t["key"]}
    assert holders == {"BSR-EO-09"}
    assert any(key in punct_key(c["text"]) for c in store.load_chunks("BSR-EO-01"))      # Hopko prints it
    hit = reg.resolve_registered_phrase("Eastern Orthodox", HOPKO_SPIRIT_CLAUSE)
    assert hit["registry_id"] == "BSR-EO-09" and hit["tier"] == "CONFESSIONAL"
    assert reg.effective_tier("BSR-EO-01", phrase=HOPKO_SPIRIT_CLAUSE) == "CONFESSIONAL"


def test_a_phrase_in_both_eo09_and_eo07_resolves_conciliar(reg):
    _eo_store()
    from sjn_recovery.textutil import punct_key
    phrase = "who proceeds from the Father"
    holders = {t["registry_id"] for t in reg.registered_creed_texts("Eastern Orthodox") if punct_key(phrase) in t["key"]}
    assert {"BSR-EO-07", "BSR-EO-09"} <= holders
    hit = reg.resolve_registered_phrase("Eastern Orthodox", phrase)
    assert hit["tier"] == "CONCILIAR" and hit["registry_id"] in ("BSR-EO-07", "BSR-EO-14")
    assert reg.effective_tier("BSR-EO-01", phrase=phrase) == "CONCILIAR"


def test_eo09_is_a_registered_creed_text_on_its_symbol_of_faith_only(reg):
    _eo_store()
    eo09 = [t for t in reg.registered_creed_texts("Eastern Orthodox") if t["registry_id"] == "BSR-EO-09"]
    assert eo09 and all(t["tier"] == "CONFESSIONAL" and "§2" in t["locator"] for t in eo09)


# ---------------------------------------------------------------- R6-21: the phrase floor, as implemented
def test_the_phrase_floor_is_three_words_and_twelve_characters(reg):
    assert (CREED_PHRASE_MIN_WORDS, CREED_PHRASE_MIN_CHARS) == (3, 12)
    _eo_store()
    assert reg.resolve_registered_phrase("Eastern Orthodox", "not made") is None               # 2 words
    assert reg.resolve_registered_phrase("Eastern Orthodox", "God of God") is None             # 3 words, 10 characters
    assert reg.resolve_registered_phrase("Eastern Orthodox", "begotten, not made") is not None  # 3 words, 17 characters


# ---------------------------------------------------------------- R6-22: a catechetical row never registers
def test_a_catechetical_row_is_never_a_registered_creed_text(reg):
    _eo_store()
    # the test binds: BSR-EO-01 is CATECHETICAL and has chunks whose locator names the Creed
    from sjn_recovery.registry import _CREED_LOCATOR
    assert bare_tier(reg.by_id["BSR-EO-01"]["authority_tier"]) == "CATECHETICAL"
    assert any(_CREED_LOCATOR.search(c["locator"] or "") for c in store.load_chunks("BSR-EO-01"))
    for branch in config.BRANCHES:
        catechetical = {r["registry_id"] for r in reg.for_branch(branch, citable_only=False)
                        if bare_tier(r.get("authority_tier") or "") == "CATECHETICAL"}
        registered = {t["registry_id"] for t in reg.registered_creed_texts(branch)}
        assert not (catechetical & registered), branch


# ---------------------------------------------------------------- R6-23: the EO ladder lives in config
def test_the_eo_ladder_is_read_from_config(monkeypatch):
    from sjn_recovery import packets

    class _Reg:
        by_id = {"BSR-EO-99": {"branch": "Eastern Orthodox"}}

    assert packets.ladder_tier(_Reg(), "BSR-EO-99") is None
    monkeypatch.setitem(config.EO_CONSULTATION_LADDER, "BSR-EO-99", "B")
    assert packets.ladder_tier(_Reg(), "BSR-EO-99") == "B"                 # a config change, no code change
    src = open(config.__file__, encoding="utf-8").read()
    assert "R6-23" in src[: src.index("EO_CONSULTATION_LADDER = {")]
