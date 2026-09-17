"""Session 12 (2026-09-17): corpus repair, the seating rule, the new Baptist row.

  R6-38 completion   the author accepts session 11's LU-01 values (unchanged)
  R6-36 completion   BSR-AN-05 stays ADOPTED, ONE_CHURCH; the competence check is appended to adoption_verified; no card change
  R6-41              Codex B3(a), the original holds the seat (allocation.allocate step 5a)

Registry tests run against the real workbook and skip where it is missing; the allocation tests are pure."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery.allocation import allocate  # noqa: E402
from sjn_recovery import rulings  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:                                             # no workbook in this checkout
        pytest.skip(f"registry unavailable: {e}")


# ---------------------------------------------------------------- phase 1: the rulings
def test_lu01_completion_is_author_accepted_and_values_unchanged(reg):
    lu01 = rulings.adoption_rows()["BSR-LU-01"]
    assert lu01["adoption_status"] == "ADOPTED" and lu01["adoption_body_scope"] == "ONE_CHURCH"
    assert lu01["adopting_body"] == "The Lutheran Church-Missouri Synod"
    acc = lu01["amended"]["completed_by_verification"]["author_accepted"]
    assert acc["date"] == "2026-09-17" and "LCMS Constitution Art. II" in acc["accepted"]
    assert reg.adoption_disclosure("BSR-LU-01")["text"] == "approved by The Lutheran Church-Missouri Synod (one church)"


def test_an05_completion_appended_and_disclosure_unchanged(reg):
    an05 = rulings.adoption_rows()["BSR-AN-05"]
    assert an05["adoption_status"] == "ADOPTED" and an05["adoption_body_scope"] == "ONE_CHURCH"
    assert an05["adoption_verified"].startswith("anglican.ink communique")                       # appended, not replaced
    assert an05["adoption_verified"].endswith("A special Provincial Assembly between June 2017 and June 2019 was not specifically searched.")
    assert "Competence checked 17 Sep 2026 (Cowork, Claude Browser pdf.js text layer)" in an05["adoption_verified"]
    assert reg.adoption_disclosure("BSR-AN-05")["text"] == \
        "approved by College of Bishops of the Anglican Church in North America (one church)"


def test_r6_41_and_r6_42_are_recorded():
    R = rulings.load()["rulings"]
    assert R["R6-41_original_holds_the_seat"]["status"] == "RATIFIED"
    assert R["R6-42_ba04_identity_statement"]["status"] == "RATIFIED"
    assert R["R6-36_an05_adoption"]["completion"]["qa_track_discharged"] is True
    assert R["R6-38_adoption_scope_reach"]["completion"]["status"] == "RATIFIED"


# ---------------------------------------------------------------- phase 2: R6-41, the original holds the seat
ATH = {"registry_id": "BSR-AN-03", "locator": "Athanasian Creed", "tier": "CONFESSIONAL"}


def _c(cid, rid, tier, locator, phrase, floor="FULL", raised_by=None, speaks_for=None):
    return {"candidate_id": cid, "registry_id": rid, "effective_tier": tier, "authority_tier": tier, "locator": locator,
            "phrase": phrase, "floor_claim": floor, "fallback_tier": False, "witness": False, "reception_scope": "JURISDICTIONAL",
            "raised_by_registered_text": raised_by or []}


GROUPS = {"BSR-AN-01": "church of england", "BSR-AN-02": "church of england", "BSR-AN-03": "church of england",
          "BSR-AN-04": "the episcopal church", "BSR-LU-01": "book of concord churches", "BSR-LU-02": "lcms", "BSR-LU-03": "lcms"}


def test_a_quoting_candidate_never_displaces_or_leads_over_the_registered_text_it_resolves_to():
    """Q-205 shape: the catechism's quotation of the creed was seated and the creed text cut; and the Q-317 shape: the reprint led."""
    art = _c("art", "BSR-AN-01", "CONFESSIONAL", "Article IV", "until he return to judge all Men")
    quote = _c("quote", "BSR-AN-02", "CONFESSIONAL", "Catechism Q.5", "he shall come to judge the quick and the dead", raised_by=[ATH])
    creed = _c("creed", "BSR-AN-03", "CONFESSIONAL", "Athanasian Creed", "from whence he shall come to judge the quick and the dead")
    tec = _c("tec", "BSR-AN-04", "CATECHETICAL", "Outline p. 862", "Christ will come in glory and judge the living and the dead")
    for order in ([art, quote, creed, tec], [quote, art, tec, creed], [creed, quote, art, tec]):
        a = allocate(order, groups=GROUPS, same_text_rows={})
        assert "creed" in a["kept"] and "quote" not in a["kept"], order
        assert a["kept"].index("creed") < len(a["kept"])
        assert [w["candidate_id"] for w in a["parallel_witnesses"]["creed"]] == ["quote"]
        assert a["parallel_witnesses"]["creed"][0]["rule"] == "ORIGINAL_HOLDS_SEAT"
        assert a["dropped"]["quote"].startswith("ORIGINAL_HOLDS_SEAT")
    # the lead: a reprint in another group that would lead its tier yields the lead to the original
    reprint = _c("reprint", "BSR-AN-04", "CONFESSIONAL", "Outline p. 862", "The Father incomprehensible, the Son incomprehensible", raised_by=[ATH])
    creed2 = _c("creed2", "BSR-AN-03", "CONFESSIONAL", "Athanasian Creed", "one uncreated, and one incomprehensible", floor="PARTIAL")
    a = allocate([reprint, creed2, art], groups=GROUPS, same_text_rows={})
    assert a["kept"][0] == "creed2" and "reprint" not in a["kept"]
    assert [w["candidate_id"] for w in a["parallel_witnesses"]["creed2"]] == ["reprint"]
    # a candidate from ANOTHER chunk of the registered row is not the original
    other = _c("other", "BSR-AN-03", "CONFESSIONAL", "some other chunk", "one uncreated, and one incomprehensible")
    a = allocate([reprint, other], groups=GROUPS, same_text_rows={})
    assert "reprint" in a["kept"] and not a["parallel_witnesses"]


def test_a_quoting_candidate_keeps_its_seat_when_the_original_is_not_a_candidate():
    """Q-297 shape: the CCC's phrase is verbatim in BSR-RC-08's Nicene Creed, and no BSR-RC-08 candidate is in the cell."""
    nicene08 = {"registry_id": "BSR-RC-08", "locator": "Nicene Creed", "tier": "CONCILIAR"}
    ccc = _c("ccc", "BSR-RC-01", "CONCILIAR", "CCC 242", "begotten not made, consubstantial with the Father", raised_by=[nicene08])
    lat = _c("lat", "BSR-RC-04", "CONCILIAR", "Constitution 1", "The Father is from none")
    nic06 = _c("nic06", "BSR-RC-06", "CONCILIAR", "Nicene Creed", "begotten, not made, of one Being with the Father")
    base = allocate([ccc, lat, nic06], groups={}, same_text_rows={})
    stripped = allocate([dict(ccc, raised_by_registered_text=[]), lat, nic06], groups={}, same_text_rows={})
    assert base["kept"] == stripped["kept"] and "ccc" in base["kept"] and base["kept"][0] == "ccc"
    assert not base["parallel_witnesses"]
    # a registered text at a DIFFERENT tier than the one the candidate was raised to is not the original either
    lower = _c("low", "BSR-RC-08", "CONFESSIONAL", "Nicene Creed", "and was made man")
    a = allocate([ccc, lower], groups={}, same_text_rows={})
    assert "ccc" in a["kept"] and not a["parallel_witnesses"]


def test_q195_pattern_is_preserved():
    """Q-195: the slot of the body's group is held; a distinct lower-tier sentence of the same body is seated.

    As the stored cell stands: BSR-LU-03-1 ("God, the Father Almighty, Maker of heaven and earth") was raised to CONFESSIONAL by
    BSR-LU-01's Apostles' Creed, which has no candidate in the cell; BSR-LU-02-1 holds the 'lcms' CONFESSIONAL slot, BSR-LU-03-1 is
    cut by the group rule and BSR-LU-03-2 (CATECHETICAL) is seated. And with the creed text itself a candidate of the cell, the
    creed holds the slot, the quotation is its parallel witness, and the distinct lower-tier sentence is still seated."""
    creed_text = {"registry_id": "BSR-LU-01", "locator": "Ecumenical Creeds: The Apostles' Creed", "tier": "CONFESSIONAL"}
    ac3 = _c("LU-01-1", "BSR-LU-01", "CONFESSIONAL", "Augsburg Confession: Article III", "forever reign and have dominion over all creatures")
    ac1 = _c("LU-02-1", "BSR-LU-02", "CONFESSIONAL", "Augsburg Confession: Article I", "the Maker and Preserver of all things")
    lc = _c("LU-01-2", "BSR-LU-01", "CONFESSIONAL", "Large Catechism", "the command of the Supreme Majesty", floor="PARTIAL")
    q1 = _c("LU-03-1", "BSR-LU-03", "CONFESSIONAL", "Small Catechism, The Creed", "God, the Father Almighty, Maker of heaven and earth",
            raised_by=[creed_text])
    q2 = _c("LU-03-2", "BSR-LU-03", "CATECHETICAL", "Small Catechism, The Creed", "I believe that God has made me and all creatures")
    a = allocate([ac3, ac1, lc, q1, q2], groups=GROUPS, same_text_rows={})
    assert a["kept"] == ["LU-01-1", "LU-02-1", "LU-03-2"]
    assert "group" in a["dropped"]["LU-03-1"] and not a["parallel_witnesses"]
    creed = _c("creed", "BSR-LU-01", "CONFESSIONAL", "Ecumenical Creeds: The Apostles' Creed", "Maker of heaven and earth")
    b = allocate([ac1, q1, q2, creed], groups=GROUPS, same_text_rows={})
    assert "creed" in b["kept"] and "LU-03-2" in b["kept"] and "LU-03-1" not in b["kept"]
    assert [w["candidate_id"] for w in b["parallel_witnesses"]["creed"]] == ["LU-03-1"]


def test_registry_raised_by_names_the_registered_text_and_never_the_candidates_own_chunk(reg):
    from sjn_recovery import store
    an03 = [c for c in store.load_chunks("BSR-AN-03") if "Athanasian" in (c.get("locator") or "")]
    if not an03:
        pytest.skip("BSR-AN-03 has no corpus in this checkout")
    phrase = "from whence he shall come to judge the quick and the dead"
    assert reg.raised_by("BSR-AN-03", an03[0], phrase) == []                        # the creed text does not quote itself
    hits = reg.raised_by("BSR-AN-02", None, "he shall come to judge the quick and the dead")
    assert any(h["registry_id"] == "BSR-AN-03" for h in hits)
    assert reg.raised_by("BSR-AN-02", None, "a phrase no creed contains at all") == []
