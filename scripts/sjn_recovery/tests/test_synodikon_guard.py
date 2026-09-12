"""FIX 0 — the Synodikon guard (BSR-EO-09). Run: python -m pytest scripts/sjn_recovery/tests -q

The known anathema sentence from the ratified PDF is fed through the guard and through the candidate
guards exactly as the pipeline applies them, and the tests assert that no candidate can be produced
from its inner clause. The built corpus, when present, is checked the same way for every chunk."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sjn_recovery import guards, store  # noqa: E402
from sjn_recovery.sources import synodikon_guard, ANATHEMA_MARKER  # noqa: E402

KNOWN = ("To those who dare to say that the Son of God, and likewise the Holy Spirit, are not one in essence "
         "with the Father, and confess that the Father, and the Son, and the Holy Spirit are not one God: ANATHEMA!")
INNER = ["the Son of God, and likewise the Holy Spirit, are not one in essence with the Father",
         "are not one in essence with the Father",
         "the Father, and the Son, and the Holy Spirit are not one God",
         "the Holy Spirit are not one God"]
SECTION_3 = ("This is the Apostolic Faith. This is the Faith of the Fathers. This is the Faith of the Orthodox. "
             "As, therefore, we bless and praise those who have submitted their reason to the obedience of Divine "
             "revelation, so following the Sacred Scriptures we reject and anathematize all those who oppose His truth. "
             "To those who deny the existence of God, and asset that the world is self-existing: ANATHEMA! "
             "People: Anathema! Anathema! Anathema! "
             "To those who say that God is not a Spirit, but flesh; or that He is not just, not merciful, not wise or "
             "omniscient, and utter such blasphemies: ANATHEMA! People: Anathema! Anathema! Anathema! "
             + KNOWN + " People: Anathema! Anathema! Anathema!")


class FakeRegistry:
    def __init__(self):
        self.by_id = {"BSR-EO-09": {"branch": "Eastern Orthodox", "registry_id": "BSR-EO-09"}}

    def is_fallback(self, rid):
        return False

    def citation_refusal(self, rid):
        return None


def _chunk(visible, withheld):
    return {"registry_id": "BSR-EO-09", "standard_title": "Synodikon", "authority_tier": "CONFESSIONAL (liturgically proclaimed)",
            "locator": "Synodikon §3", "division": "section", "text": visible, "text_hash": "x", "noncitable_spans": withheld}


def test_known_sentence_is_withheld_whole():
    visible, withheld = synodikon_guard(SECTION_3)
    texts = [w["text"] for w in withheld]
    assert any(KNOWN in t for t in texts), "the known anathema sentence must be withheld in full"
    for clause in INNER:
        assert clause.casefold() not in visible.casefold(), f"inner clause leaked into citable text: {clause!r}"
    assert "anathema" not in visible.casefold().replace(ANATHEMA_MARKER.casefold(), ""), "no anathema wording may survive"
    assert ANATHEMA_MARKER in visible
    # the Church's own-voice sentences around the anathemas remain citable
    assert "This is the Apostolic Faith" in visible
    assert "we reject and anathematize" not in visible   # carries the word; withheld by the belt-and-braces rule


def test_inner_clause_cannot_become_a_candidate():
    visible, withheld = synodikon_guard(SECTION_3)
    chunk = _chunk(visible, withheld)
    by_key = {"c1": chunk}
    for clause in INNER:
        cand = {"chunk_key": "c1", "registry_id": "BSR-EO-09", "locator": "Synodikon §3", "phrase": clause,
                "rationale": "test", "floor_claim": "FULL"}
        ok, why, _ = guards.vet_candidate(cand, by_key, "Eastern Orthodox", FakeRegistry(), allow_fallback=False)
        assert not ok, f"a candidate was produced from an anathema inner clause: {clause!r}"
        assert "ANATHEMA_SPAN" in why or "not present verbatim" in why


def test_check_noncitable_refuses_even_if_text_were_present():
    # Defence in depth: even if a chunk's visible text somehow still carried the clause, the span list refuses it.
    chunk = _chunk(KNOWN, [{"kind": "anathema", "text": KNOWN}])
    ok, why = guards.check_noncitable("are not one in essence with the Father", chunk)
    assert not ok and "ANATHEMA_SPAN" in why


def test_safe_region_creed_is_citable():
    creed = ("I believe in one God, the Father Almighty, Maker of heaven and earth, of all things visible and invisible. "
             "And in one Lord Jesus Christ, the Son of God, the Only-begotten, begotten of the Father before all ages: light "
             "from light, true God from true God, begotten, not made, of one essence with the Father, through whom all things were made;")
    visible, withheld = synodikon_guard(creed)
    assert not withheld and visible == creed.strip()
    ok, why = guards.check_phrase("of one essence with the Father, through whom all things were made", visible)
    assert ok, why


def test_built_corpus_if_present():
    chunks = store.load_chunks("BSR-EO-09")
    if not chunks:
        pytest.skip("BSR-EO-09 corpus not built")
    assert len(chunks) == 6
    creed = [c for c in chunks if "Symbol of Faith" in c["locator"]]
    assert creed and not creed[0].get("noncitable_spans"), "section 2 is the safe region and must carry no withheld span"
    ok, why = guards.check_phrase("of one essence with the Father", creed[0]["text"])
    assert ok, why
    total_withheld = 0
    for c in chunks:
        total_withheld += len(c.get("noncitable_spans") or [])
        low = c["text"].casefold().replace(ANATHEMA_MARKER.casefold(), "")
        assert "anathema" not in low, f"anathema wording survives in {c['locator']}"
        for clause in INNER:
            assert clause.casefold() not in low, f"{clause!r} leaked into {c['locator']}"
            cand = {"chunk_key": "c1", "registry_id": "BSR-EO-09", "locator": c["locator"], "phrase": clause,
                    "rationale": "t", "floor_claim": "FULL"}
            ok, why, _ = guards.vet_candidate(cand, {"c1": c}, "Eastern Orthodox", FakeRegistry(), allow_fallback=False)
            assert not ok
    known_withheld = any(KNOWN.casefold() in (w["text"].casefold()) for c in chunks for w in (c.get("noncitable_spans") or []))
    assert known_withheld, "the known sentence must be among the withheld spans of the built corpus"
    # the ROEA text carries 11 anathemas, their 11 responses, and one own-voice sentence with the word ("we reject and anathematize")
    assert total_withheld >= 22, f"expected the 11 anathemas and their 11 responses to be withheld, got {total_withheld}"
