"""Session 7 (2026-09-16): the author's rulings R6-5 to R6-12.

  R6-5 / R6-10  phrase-level creed and definition resolution replaces chunk-locator creed resolution
  R6-6 / R6-9   the adoption field, fail-closed, and the second tier's rank
  R6-7          the Spirit-name code guard
  R6-8          the ratified agency tag (Q-274 ATTRIBUTE); the proposals are not in force
  R6-11         verifier gate6-v1.4, and the creedal-silence hard stop
  Task 6        the ladder-aware coverage record (NOT CONSULTED is not NO TEXT)

The tier tests run against the real workbook and the real chunk store: the rule is about what the REGISTERED texts of a
branch actually say, and a stub would only test the stub. They skip where the chunk store is not built."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.registry import Registry, bare_tier, tier_rank, SECOND_TIER  # noqa: E402
from sjn_recovery.packets import empty_result_option, no_text_rows, ladder_tier  # noqa: E402
from sjn_recovery.config import EMPTY_RESULT  # noqa: E402
from sjn_recovery.agents import (phrase_names_the_spirit, required_subject_is_the_spirit, strip_accents,  # noqa: E402
                                 SPIRIT_NAME_TOKENS)
from sjn_recovery import guards, prompts, rulings, store  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    try:
        r = Registry()
    except Exception as e:                                             # no workbook in this checkout
        pytest.skip(f"registry unavailable: {e}")
    if not store.load_chunks("BSR-EO-01") or not store.load_chunks("BSR-EO-07"):
        pytest.skip("chunk store (.cache/sjn-recovery/chunks) is not built in this checkout")
    return r


def _chunk(rid, match):
    return next(c for c in store.load_chunks(rid) if match.casefold() in (c["locator"] or "").casefold())


# ---------------------------------------------------------------- R6-5: the re-type is applied in memory
def test_eo01_is_retyped_as_the_hopko_row_it_is(reg):
    row = reg.by_id["BSR-EO-01"]
    assert bare_tier(row["authority_tier"]) == "CATECHETICAL" and "Hopko" in row["standard_title"]
    assert row["reception_scope"] == "JURISDICTIONAL" and row["same_work_as"] == "BSR-EO-02"
    ov = reg.registry_overrides["BSR-EO-01"]
    assert ov["ruling"] == "R6-5_bsr_eo_01_retype"
    assert ov["applied"]["authority_tier"] == {"workbook": "CONCILIAR", "ruled": "CATECHETICAL"}
    assert rulings.same_work_rows()["BSR-EO-01"] == "BSR-EO-02"          # one work, one observation
    assert rulings.independence_groups()["HOPKO-OF-VOL1"] == ["BSR-EO-01", "BSR-EO-02"]


def test_a_workbook_that_disagrees_with_a_registry_override_fails_loudly(reg, monkeypatch):
    rows = [dict(r) for r in reg.rows_all]
    for r in rows:
        if r["registry_id"] == "BSR-EO-01":
            r["same_work_as"] = "BSR-EO-99"                              # the workbook grew the column, and disagrees
    monkeypatch.setattr("sjn_recovery.registry.load_registry", lambda wb: rows)
    with pytest.raises(SystemExit, match="disagrees with author ruling"):
        Registry()


# ---------------------------------------------------------------- Task 2c: phrase-level resolution
def test_an_eo01_exposition_sentence_resolves_official_exposition_not_conciliar(reg):
    c = _chunk("BSR-EO-01", 'The Symbol of Faith — "Faith"')
    phrase = "Faith is the foundation of the spiritual life"
    assert bare_tier(reg.effective_tier("BSR-EO-01", c, phrase)) == SECOND_TIER
    assert reg.resolve_registered_phrase("Eastern Orthodox", phrase) is None


def test_begotten_not_made_quoted_inside_eo01_resolves_conciliar(reg):
    c = _chunk("BSR-EO-01", 'The Symbol of Faith — "Son of God"')
    hit = reg.resolve_registered_phrase("Eastern Orthodox", "begotten, not made")
    assert hit and hit["kind"] == "CREED" and hit["tier"] == "CONCILIAR"
    assert bare_tier(reg.effective_tier("BSR-EO-01", c, "begotten, not made")) == "CONCILIAR"


def test_an_an05_why_does_the_creed_say_answer_is_not_conciliar(reg):
    if not store.load_chunks("BSR-AN-05"):
        pytest.skip("BSR-AN-05 has no corpus in this checkout")
    c = _chunk("BSR-AN-05", "Why does the Creed say")
    phrase = " ".join(c["text"].split()[:14])
    eff = reg.effective_tier("BSR-AN-05", c, phrase)
    assert bare_tier(eff) != "CONCILIAR"
    expected = "CATECHETICAL" if reg.adoption("BSR-AN-05")["adoption_status"] == "ADOPTED" else SECOND_TIER
    assert bare_tier(eff) == expected


def test_the_eo07_creed_chunk_resolves_conciliar(reg):
    c = _chunk("BSR-EO-07", "THE SYMBOL OF FAITH")
    assert bare_tier(reg.effective_tier("BSR-EO-07", c, "I believe in one God, the Father Almighty")) == "CONCILIAR"
    assert bare_tier(reg.effective_tier("BSR-EO-07", c)) == "CONCILIAR"   # the chunk-level route survives on this row


def test_rc06_nicene_resolves_conciliar_unchanged(reg):
    c = _chunk("BSR-RC-06", "Nicene Creed")
    assert bare_tier(reg.effective_tier("BSR-RC-06", c)) == "CONCILIAR"
    assert bare_tier(reg.effective_tier("BSR-RC-06", c, "consubstantial with the Father")) == "CONCILIAR"


def test_a_canon_or_anathema_phrase_quoted_in_a_catechism_keeps_the_host_tier(reg):
    """R6-10 excludes canons and anathemas. BSR-RC-02's canons and BSR-RC-04's Damnamus ergo are never definition texts,
    so a phrase drawn from one resolves to the host row, never CONCILIAR."""
    defs = {(t["registry_id"], t["locator"]) for t in reg.registered_definition_texts("Roman Catholic")}
    assert not any("canon" in loc.casefold() or "damnamus" in loc.casefold() for _, loc in defs)
    canon = _chunk("BSR-RC-02", "Canon I.1")
    phrase = " ".join(canon["text"].split()[:12])
    assert reg.resolve_registered_phrase("Roman Catholic", phrase) is None
    host = _chunk("BSR-RC-01", "")if False else store.load_chunks("BSR-RC-01")[0]
    assert bare_tier(reg.effective_tier("BSR-RC-01", host, phrase)) == "CATECHETICAL"     # RC-01 is ADOPTED


def test_chunk_level_creed_resolution_is_disabled_off_the_allowed_rows(reg):
    assert reg.chunk_level_creed_rows == {"BSR-EO-07", "BSR-EO-14", "BSR-RC-06", "BSR-RC-08"}
    for rid, loc in (("BSR-EO-04", "On the Creed generally"), ("BSR-AN-04", "The Creeds"), ("BSR-AN-05", "What is a creed?"),
                     ("BSR-LU-01", "The Creed"), ("BSR-RP-04", "Nicene Creed")):
        if not store.load_chunks(rid):
            continue
        c = next((c for c in store.load_chunks(rid) if loc.casefold() in (c["locator"] or "").casefold()), None)
        if c is None:
            continue
        assert bare_tier(reg.effective_tier(rid, c)) != "CONCILIAR", f"{rid} still resolves CONCILIAR by chunk locator"


def test_a_short_phrase_never_buys_the_creed_tier(reg):
    for short in ("God", "the Father", "one God"):
        assert reg.resolve_registered_phrase("Eastern Orthodox", short) is None


# ---------------------------------------------------------------- Task 3d: the adoption field
def test_the_second_tier_rank_is_asserted_from_app_config(reg):
    a = reg.assert_second_tier_rank()
    assert a["ok"] and a["second_tier"] == a["catechetical"] + 1
    assert tier_rank(SECOND_TIER) == tier_rank("CATECHETICAL") + 1


def test_eo01_and_eo02_exposition_is_official_exposition_and_says_not_officially_adopted(reg):
    for rid in ("BSR-EO-01", "BSR-EO-02"):
        assert reg.adoption(rid)["adoption_status"] == "ISSUED_UNADOPTED"
        assert bare_tier(reg.exposition_tier(rid)) == SECOND_TIER
        d = reg.adoption_disclosure(rid)
        assert d["text"].startswith("not officially adopted") and "catechism, not synodally adopted" in d["text"]


def test_eo04_exposition_stays_catechetical_with_the_one_church_disclosure(reg):
    a = reg.adoption("BSR-EO-04")
    assert a["adoption_status"] == "ADOPTED" and a["adoption_body_scope"] == "ONE_CHURCH"
    assert bare_tier(reg.exposition_tier("BSR-EO-04")) == "CATECHETICAL"
    d = reg.adoption_disclosure("BSR-EO-04")
    assert "Holy Governing Synod" in d["text"] and "(one church)" in d["text"]
    assert "1830" in a["adoption_act"] and "1839" in a["adoption_act"]          # both dates recorded
    assert reg.adoption_policy["scope_rule"] == "BRANCH_WIDE_WITH_DISCLOSURE"


def _as_unverified(reg, rid):
    """Session 11: R6-35..R6-40 left no UNVERIFIED row in the registry, so the fail-closed default is exercised on a real row
    given the migration's own UNVERIFIED record. Returns the record it replaced, for restore."""
    saved = reg.adoption_map[rid]
    a = reg.adoption_map[rid] = dict(saved)
    for k in ("adopting_body", "translation_disclosure", "disclosure_wording", "guard"):
        a.pop(k, None)
    a.update({"adoption_status": "UNVERIFIED", "adoption_act": "", "adoption_body_scope": "", "source": "UNVERIFIED (default)",
              "adoption_verified": "not verified; R6-6 fails closed (resolved as ISSUED_UNADOPTED)"})
    return saved


def test_an_unverified_catechetical_row_fails_closed_and_says_adoption_unverified(reg):
    real = [rid for rid, a in reg.adoption_map.items()
            if a["adoption_status"] == "UNVERIFIED" and a["bare_tier"] == "CATECHETICAL"]
    rows = real or [rid for rid, a in reg.adoption_map.items() if a["bare_tier"] == "CATECHETICAL"][:3]
    assert rows, "no catechetical row to test"
    for rid in rows:
        saved = None if rid in real else _as_unverified(reg, rid)
        try:
            assert bare_tier(reg.exposition_tier(rid)) == SECOND_TIER
            assert reg.adoption_disclosure(rid)["text"].startswith("adoption unverified")
            assert reg.adoption_disclosure(rid)["fails_closed"] is True
        finally:
            if saved is not None:
                reg.adoption_map[rid] = saved


def test_a_confessional_row_is_never_demoted_by_an_unverified_adoption(reg):
    """Clause 3 reaches catechetical and expository rows. The Westminster Larger Catechism and the Heidelberg are
    CONFESSIONAL; left UNVERIFIED their tier does not move, and the card still discloses it. (Both were ruled ADOPTED on
    2026-09-17, R6-38 / R6-40, so the UNVERIFIED case is exercised on their migration record.)"""
    for rid in ("BSR-RP-03", "BSR-RP-05"):
        if rid not in reg.by_id:
            continue
        saved = _as_unverified(reg, rid)
        try:
            assert reg.adoption(rid)["adoption_status"] == "UNVERIFIED"
            assert reg.exposition_tier(rid) == reg.by_id[rid]["authority_tier"]
            assert bare_tier(reg.exposition_tier(rid)) == "CONFESSIONAL"
            assert reg.adoption_disclosure(rid)["text"].startswith("adoption unverified")
        finally:
            reg.adoption_map[rid] = saved
        assert bare_tier(reg.exposition_tier(rid)) == "CONFESSIONAL"          # and ADOPTED, as ruled, it does not move either


def test_bare_tier_ignores_the_display_qualifier(reg):
    assert bare_tier(reg.exposition_tier("BSR-EO-01")) == SECOND_TIER
    assert "(" in reg.exposition_tier("BSR-EO-01")                       # the qualifier is there, and is disclosure only
    assert tier_rank(reg.exposition_tier("BSR-EO-01")) == tier_rank(SECOND_TIER)


# ---------------------------------------------------------------- Task 6: the ladder-aware coverage record
class _LadderReg:
    """The EO rows with their ladder tiers, and nothing else the record needs."""
    def __init__(self):
        from sjn_recovery.config import EO_CONSULTATION_LADDER
        self.by_id = {rid: {"registry_id": rid, "branch": "Eastern Orthodox", "eo_ladder_tier": t}
                      for rid, t in EO_CONSULTATION_LADDER.items()}

    def is_fallback(self, rid):
        return False


FULL = {"coverage": "FULL", "supplied": 9, "of": 9}
TIER_A = ["BSR-EO-06", "BSR-EO-07", "BSR-EO-08", "BSR-EO-09", "BSR-EO-12"]
TIER_B = ["BSR-EO-01", "BSR-EO-02", "BSR-EO-04", "BSR-EO-05", "BSR-EO-10", "BSR-EO-14"]
EO_ROWS = [{"registry_id": r} for r in TIER_A + TIER_B + ["BSR-EO-11", "BSR-EO-13"]]


def _st(cov):
    return {"coverage_final": cov, "passes": {"1": {"per_standard": {}}}}


def test_a_tier_a_only_filled_card_has_no_no_text_rows():
    reg = _LadderReg()
    st = _st({r: FULL for r in TIER_A})
    nt, nc = no_text_rows(st, EO_ROWS, reg, {}, card_empty=False, ladder_entered={"A"})
    assert nt == [], nt
    assert {x["registry_id"] for x in nc} == set(TIER_B) | {"BSR-EO-11", "BSR-EO-13"}
    assert all(x["status"].startswith("NOT CONSULTED (ladder tier") for x in nc)


def test_an_a_plus_b_empty_card_read_whole_is_offered_reviewed():
    reg = _LadderReg()
    st = _st({r: FULL for r in TIER_A + TIER_B})
    nt, nc = no_text_rows(st, EO_ROWS, reg, {}, card_empty=True, ladder_entered={"A", "B"})
    assert nt == []
    assert {x["registry_id"] for x in nc} == {"BSR-EO-11", "BSR-EO-13"}       # Tier C, out of the REVIEWED test
    e = empty_result_option(st["coverage_final"], {}, no_text=nt, not_consulted=nc)
    assert e["offered"] is True and e["rendered_state"] == EMPTY_RESULT
    by = {r["registry_id"]: r for r in e["standards_reviewed"]}
    assert by["BSR-EO-11"]["status"] == "NOT CONSULTED (ladder tier C)" and "BSR-EO-11" not in e["review_incomplete"]


def test_an_a_plus_b_empty_card_missing_a_due_tier_b_row_refuses_reviewed_and_names_it():
    reg = _LadderReg()
    cov = {r: FULL for r in TIER_A + TIER_B if r != "BSR-EO-01"}              # EO-01 is a Tier B row (R6-5), and was due
    st = _st(cov)
    nt, nc = no_text_rows(st, EO_ROWS, reg, {}, card_empty=True, ladder_entered={"A", "B"})
    assert [x["registry_id"] for x in nt] == ["BSR-EO-01"] and nt[0]["ladder_tier"] == "B"
    e = empty_result_option(cov, {}, no_text=nt, not_consulted=nc)
    assert e["offered"] is False and e["review_incomplete"] == ["BSR-EO-01"]
    assert "BSR-EO-01 supplied no text" in e["why_not_offered"]


def test_eo11_and_eo13_are_tier_c_and_eo01_is_tier_b(reg):
    assert ladder_tier(reg, "BSR-EO-11") == "C" and ladder_tier(reg, "BSR-EO-13") == "C"
    assert ladder_tier(reg, "BSR-EO-01") == "B" and ladder_tier(reg, "BSR-EO-07") == "A"
    assert ladder_tier(reg, "BSR-RC-01") is None                              # a flat branch has no ladder


# ---------------------------------------------------------------- R6-7 / R6-8 / R6-11
def test_the_spirit_token_set_covers_english_and_the_greek_pneuma_forms():
    assert set(SPIRIT_NAME_TOKENS) == {"holy spirit", "holy ghost", "spirit", "pneuma", "πνευμα"}
    for p in ("the Holy Ghost Almighty", "and in the Holy Spirit, the Lord, the giver of life", "τὸ Πνεῦμα τὸ Ἅγιον",
              "τοῦ Πνεύματος τοῦ Ἁγίου", "renewed by the Holy Spirit"):
        assert phrase_names_the_spirit(p), p
    for p in ("one God, Father, Son and Holy", "the Father Almighty, maker of heaven and earth",
              "yet they are not three Almighties but one Almighty"):
        assert not phrase_names_the_spirit(p), p
    assert strip_accents("Πνεῦμα") == "πνευμα"


def test_the_guard_refuses_a_creed_clause_cut_short_of_the_spirits_name():
    """The consequence the author should see. R6-7 as the prompt states it is unconditional: on a family typed THE HOLY
    SPIRIT (RNR-H34 Giver of life, RNR-H35 Eternal power and might) the cited phrase must ITSELF name the Spirit. So the
    Creed's own "the Lord, the giver of life", cut short of "and in the Holy Spirit", is refused — the locator must cut
    the clause so the Spirit's name is inside it. Not a defect: it is the rule applied to its own hardest case."""
    assert not phrase_names_the_spirit("the Lord, the giver of life, who proceedeth from the Father")
    assert phrase_names_the_spirit("in the Holy Spirit, the Lord, the giver of life")


def test_the_spirit_guard_fires_only_where_the_required_subject_is_the_spirit():
    assert required_subject_is_the_spirit({"subject_scope": "THE HOLY SPIRIT"})
    assert not required_subject_is_the_spirit({"subject_scope": rulings.required_subjects()["RNR-H06"]})
    assert not required_subject_is_the_spirit({"subject_scope": "THE SON (the eternal Son / Logos, as divine)"})


def test_q274s_family_keeps_its_r6_8_tag_and_r6_14_supersedes_the_proposals():
    """Session 7 carried only RNR-H35. R6-14 (session 8) ratified all seven and retired the PROPOSED file; H35 is unchanged."""
    assert rulings.agency_tags()["RNR-H35"] == "ATTRIBUTE"
    assert rulings.agency_blocks_eo() is False
    path = os.path.join(os.path.dirname(rulings.RULINGS_PATH), "spirit-family-agency-tags-PROPOSED.json")
    assert not os.path.exists(path)


def test_v14_carries_the_creed_lines_and_the_two_new_lines_and_v13_does_not():
    s14, s13 = prompts.VERIFIER_SYSTEMS["gate6-v1.4"], prompts.VERIFIER_SYSTEMS["gate6-v1.3"]
    assert "A CREED IS NOT A FIXED FORMULA IN THIS SENSE." in s14 and "A CREED IS NOT" not in s13
    assert "an acclamation or a liturgical formula" not in s14        # line 4 no longer floors a liturgical formula
    assert "an acclamation or a liturgical formula" in s13
    assert "Do NOT raise IDIOM_OR_FORMULA for a creedal clause" in s14
    assert prompts.CREEDAL_SILENCE_LINE in s14 and prompts.JOINT_PREDICATION_LINE in s14 and prompts.AGENCY_LINE in s14
    assert "A NEIGHBOURING proposition is never PARTIAL" in s14       # everything v1.3 said, it still says
    assert list(prompts.VERIFIER_SYSTEMS)[:3] == ["gate6-v1.2", "gate6-v1.3", "gate6-v1.4"]


def test_the_agency_class_reaches_the_verifier_only_when_ratified():
    import json
    base = {"family_id": "RNR-H35", "predicate": "Eternal power and might", "definition": "d", "floor_note": "",
            "subject_scope": "THE HOLY SPIRIT", "agency_class": "ATTRIBUTE", "agency_class_source": "AUTHOR_RULING_R6-8"}
    cand = {"registry_id": "R", "locator": "L", "phrase": "p", "floor_claim": "FULL"}
    assert json.loads(prompts.verifier_user(base, cand, {}))["agency_class"] == "ATTRIBUTE"
    assert "agency_class" not in json.loads(prompts.verifier_user({k: v for k, v in base.items()
                                                                  if not k.startswith("agency")}, cand, {}))


def test_a_divergence_resting_on_a_creeds_silence_is_refused_in_code():
    prop = {"rendered_state": "D", "state_reason": "The Nicene Creed does not contain the predicate, so the tradition diverges.",
            "source_note": ""}
    stop = guards.creedal_silence_stop(prop, {"hazard_flags": []}, family_code="Q")
    assert stop and stop["divergence_refused_by"] == guards.CREEDAL_SILENCE_STOP and stop["rendered_state"] == "Q"
    assert stop["rendered_state_proposed"] == "D"
    # the hazard alone is enough where the reason names a creed
    prop2 = {"rendered_state": "D", "state_reason": "The Creed is quoted only in part here.", "source_note": ""}
    assert guards.creedal_silence_stop(prop2, {"hazard_flags": ["SOURCE_SILENCE_VS_DENIAL"]}, "A")
    # a divergence on the standard's own words is untouched, and a non-divergent state is never refused
    prop3 = {"rendered_state": "D", "state_reason": "The article positively denies the predicate in its own voice.", "source_note": ""}
    assert guards.creedal_silence_stop(prop3, {"hazard_flags": []}, "A") is None
    assert guards.creedal_silence_stop(dict(prop, rendered_state="Q"), {"hazard_flags": []}, "A") is None
