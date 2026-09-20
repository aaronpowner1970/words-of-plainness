"""Session 14, phase 4: the AN-04 / AN-06 corpus repair (Codex F.10; R6-45, R6-47, R6-48, R6-49, R6-50, R6-51).

  R6-51  BSR-AN-04 is BCP pp. 844-862; the p. 844 rubric is integral text, stored with its locator, unregistered
  R6-48  BSR-AN-06 is the Chalcedonian Definition and the Quicunque Vult, BCP pp. 863-865; registered sections none
  R6-47  those sections are WITNESS sections: adopted but not confessed; they cannot seat a cell alone
  R6-50  named same-text pair, scoped to the Quicunque Vult section: BSR-AN-03 holds the slot
  R6-49  the TEC Articles of Religion are not fetched and not added

The two tests Codex F.10 names by hand are here: no Quicunque Vult chunk ends at "one Almighty.", and no chunk runs
past p. 865."""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import rulings, sources, store, config, packets  # noqa: E402
from sjn_recovery.registry import Registry, bare_tier, is_witness_row, s  # noqa: E402
from sjn_recovery.allocation import translation_pairs  # noqa: E402

CUT_AT = "one Almighty."
LAST_SENTENCE = "This is the Catholic Faith, which except a man believe faithfully, he cannot be saved."
QUICUNQUE = "Quicunque Vult"


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:
        pytest.skip(f"registry unavailable: {e}")


@pytest.fixture(scope="module")
def an06_chunks():
    c = store.load_chunks("BSR-AN-06")
    if not c:
        pytest.skip("BSR-AN-06 has no stored chunks")
    return c


def _pages(locator):
    """Every BCP page number a locator names: 'p. 864' -> [864]; 'pp. 864-865' -> [864, 865]."""
    m = re.search(r"\(BCP pp?\. ([0-9–\-]+)\)", locator)
    return [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []


# ---------------------------------------------------------------- R6-48: the two tests Codex F.10 names
def test_no_an06_quicunque_vult_chunk_ends_at_one_almighty(an06_chunks):
    """The session 12/13 defect: the Quicunque Vult runs across the BCP p. 864/865 break, and the AN-04 adapter's
    20-page window ended at p. 864, so the stored chunk broke off a third of the way in, mid-argument, before a word of
    the Incarnation half. The creed is now joined and ends where it ends."""
    quicunque = [c for c in an06_chunks if QUICUNQUE in c["locator"]]
    assert len(quicunque) == 1, [c["locator"] for c in quicunque]
    for c in an06_chunks:
        assert not c["text"].rstrip().endswith(CUT_AT), (c["locator"], c["text"][-60:])
    assert quicunque[0]["text"].rstrip().endswith(LAST_SENTENCE)
    # and the whole creed is there: the opening, the cut point, and the Incarnation half beyond it
    t = quicunque[0]["text"]
    assert t.startswith("Whosoever will be saved")
    assert CUT_AT in t, "the old cut point must still be INSIDE the chunk, not at its end"
    assert "the Incarnation of our Lord Jesus Christ" in t and "descended into hell" in t


def test_no_an06_chunk_runs_past_bcp_p_865(an06_chunks):
    """R6-48's extent: pp. 863-865. The 1549 Preface (p. 866) and the Articles of Religion (p. 867 on) are not SJN's."""
    for c in an06_chunks:
        pp = _pages(c["locator"])
        assert pp, c["locator"]
        assert min(pp) >= 863 and max(pp) <= 865, (c["locator"], pp)
        assert "First Book of Common Prayer" not in c["text"]
        assert "Articles of Religion" not in c["text"]


def test_the_historical_documents_are_their_own_row(reg, an06_chunks):
    """R6-48: one row, both documents, the title page stored so the extent is visible. No AN-07 id."""
    assert "BSR-AN-07" not in reg.by_id
    assert [c["locator"] for c in an06_chunks] == [
        "Historical Documents of the Church (BCP p. 863) — title page",
        "Historical Documents of the Church (BCP p. 864) — Definition of the Union of the Divine and Human Natures "
        "in the Person of Christ Council of Chalcedon, 451 A.D., Act V",
        "Historical Documents of the Church (BCP pp. 864–865) — Quicunque Vult commonly called The Creed of "
        "Saint Athanasius",
    ]
    assert [c["division"] for c in an06_chunks] == ["title page", "historical document", "historical document"]
    row = reg.by_id["BSR-AN-06"]
    assert row["branch"] == "Anglican" and row["status"] == "AUTHOR_RATIFIED"
    assert row.get("_author_ruling_added", {}).get("ruling") == "R6-48_an06_historical_documents_row"
    ad = reg.adoption("BSR-AN-06")
    assert ad["adoption_status"] == "ADOPTED" and ad["adoption_body_scope"] == "ONE_CHURCH"
    assert "1979-A133" in ad["adoption_act"] and "C-8" in ad["adoption_act"]          # R6-52


def test_the_adapter_refuses_a_quicunque_vult_that_is_cut_at_the_page_break():
    """The guard, not just the outcome: an adapter fed a BCP whose Quicunque Vult stops at the page break REFUSES,
    rather than storing a third of a creed as the creed. Mutation-checked by construction."""
    class _Ctx:
        row = {"registry_id": "BSR-AN-06", "branch": "Anglican", "standard_title": "t", "authority_tier": "x",
               "scope_caveat": "", "reception_scope": "JURISDICTIONAL",
               "canonical_url": "https://www.episcopalchurch.org/x.pdf"}
        rid = "BSR-AN-06"

        def __init__(self, text):
            self._t = text

        def pdf(self, url):
            return self._t

        chunk = sources.Ctx.chunk

    good = "\f".join([
        "Historical\nDocuments\nof the Church\n",
        "Definition of the Union of the Divine\nand Human Natures in the Person of Christ\n"
        "Council of Chalcedon, 451 A.D., Act V\nTherefore, following the holy fathers, we all teach.\n"
        "Quicunque Vult\ncommonly called\nThe Creed of Saint Athanasius\n"
        "Whosoever will be saved, before all things it is necessary.\n"
        "And yet they are not three Almighties, but one Almighty.\n",
        "So the Father is God, the Son is God, and the Holy Ghost is God.\n" + LAST_SENTENCE + "\n",
        "Preface\nThe First Book of Common Prayer (1549)\nThere was never any thing.\n"])
    out, notes = sources.tec_historical_documents(_Ctx(good))
    assert len(out) == 3 and out[2]["text"].rstrip().endswith(LAST_SENTENCE)
    assert "pp. 2–3" in out[2]["locator"]                      # joined across the page break (synthetic page numbers)
    cut = "\f".join(good.split("\f")[:2] + [good.split("\f")[3]])   # the p. 865 page removed: the creed is cut
    with pytest.raises(sources.FetchError) as ex:
        sources.tec_historical_documents(_Ctx(cut))
    assert "does not end at its last sentence" in str(ex.value)


# ---------------------------------------------------------------- R6-51: AN-04's extent and the p. 844 rubric
def test_an04_is_bcp_pp_844_to_862_with_the_rubric_stored_and_unregistered(reg):
    chunks = store.load_chunks("BSR-AN-04")
    assert chunks, "BSR-AN-04 has no stored chunks"
    first = chunks[0]
    assert first["locator"] == "Outline of the Faith (BCP p. 844) — Concerning the Catechism (rubric)"
    assert first["division"] == sources.TEC_P844_RUBRIC_DIVISION
    assert first["text"].startswith("This catechism is primarily intended for use by parish priests")
    pages = sorted({p for c in chunks for p in re.findall(r"\(BCP p\. (\d+)\)", c["locator"])})
    assert min(int(p) for p in pages) == 844 and max(int(p) for p in pages) == 862
    # nothing from the Historical Documents is on this row any more
    assert not any("Historical Documents" in c["locator"] for c in chunks)
    assert not any("Quicunque" in c["text"] or "Chalcedon" in c["text"] for c in chunks)
    # R6-51: the rubric is integral text, and it is NOT a registered section
    assert not reg.is_registered_section("BSR-AN-04", first["locator"])
    # R6-45's scope marker is discharged: no AN-04 chunk awaits a scope ruling any more
    assert not any(reg.scope_marker("BSR-AN-04", c) for c in chunks)


# ---------------------------------------------------------------- R6-47: witness sections, never registered
def test_an06_has_no_registered_sections_and_the_r6_27_test_covers_it(reg, an06_chunks):
    """R6-47 / Codex B1(a), B1(c). The creed-registration path is registered-sections.json and nothing else, so the
    check is: no AN-06 section is listed, none resolves as a registered creed or definition text, and the reason is
    on the record in the file's `not_registered` list."""
    listed = {(e["registry_id"], e["locator"]) for e in rulings.registered_sections()}
    assert not any(rid == "BSR-AN-06" for rid, _ in listed)
    for branch in config.BRANCHES:
        for t in reg.registered_creed_texts(branch) + reg.registered_definition_texts(branch):
            assert t["registry_id"] != "BSR-AN-06", t
    for c in an06_chunks:
        assert not reg.is_registered_section("BSR-AN-06", c["locator"])
    not_reg = {(e["registry_id"], e["locator"]): e for e in
               json.load(open(rulings.REGISTERED_SECTIONS_PATH, encoding="utf-8"))["not_registered"]}
    an06 = [e for (rid, _), e in not_reg.items() if rid == "BSR-AN-06"]
    assert len(an06) == 2 and all("R6-47" in e["why"] and "not confessed" in e["why"].casefold() for e in an06)


def test_listing_an06_as_a_registered_section_fails_loudly(tmp_path, monkeypatch, an06_chunks):
    """The mutation check for R6-47: the fail-closed treatment is enforced, not merely described. A CATECHETICAL row
    is refused by R6-27; BSR-AN-06 is not CATECHETICAL, so the guard that must catch it is the one on witness rows."""
    d = json.load(open(rulings.REGISTERED_SECTIONS_PATH, encoding="utf-8"))
    d["sections"].append({"registry_id": "BSR-AN-06", "locator": an06_chunks[2]["locator"], "kind": "CREED",
                          "what": "planted by the mutation check"})
    p = tmp_path / "sections.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(p))
    r = Registry()
    with pytest.raises(SystemExit) as ex:
        r.registered_creed_texts("Anglican")
    assert "BSR-AN-06" in str(ex.value)


def test_an06_is_a_witness_row_and_cannot_seat_a_cell_alone(reg):
    """R6-47 / Codex B1(c). The witness treatment is carried by the row's own tier, so no later edit can drop a flag
    and quietly promote it; `is_witness_row` reads it, and allocation's witness-only guard does the rest."""
    row = reg.by_id["BSR-AN-06"]
    assert is_witness_row(row) and reg.is_witness("BSR-AN-06")
    assert "witness" in s(row["authority_tier"]).casefold()
    assert "not confessed" in s(row["authority_tier"])
    # fail closed: below its genre's tier, and below the confessed Anglican rows
    assert bare_tier(s(row["authority_tier"])) == "OFFICIAL_EXPOSITION"
    # and it is not pulled into rule 1b's English-translation pairing: R6-50 declares its relationship instead
    assert translation_pairs(reg, "Anglican") == {}


# ---------------------------------------------------------------- R6-50: the pair, scoped to the Quicunque Vult
def test_the_same_text_pair_is_scoped_to_the_quicunque_vult_section():
    """R6-50 names the pair for the Quicunque Vult SECTION. BSR-AN-06 also holds the Chalcedonian Definition, which is
    a different text from BSR-AN-03's Athanasian Creed and must compete for its own slot, not be recorded as a
    parallel witness of it."""
    d = rulings.same_text_declarations()
    assert d["BSR-AN-06"]["same_text_as"] == "BSR-AN-03"
    assert d["BSR-AN-06"]["locator_contains"] == QUICUNQUE
    assert rulings.same_text_rows()["BSR-AN-06"] == "BSR-AN-03"
    from sjn_recovery.allocation import allocate
    chal = "Historical Documents of the Church (BCP p. 864) — Definition ... Council of Chalcedon"
    quic = "Historical Documents of the Church (BCP pp. 864–865) — Quicunque Vult commonly called ..."
    base = {"authority_tier": "CONFESSIONAL", "reception_scope": "JURISDICTIONAL", "fallback_tier": False,
            "floor_claim": "FULL", "slot": "GUARANTEED"}
    # distinct phrases, so R6-4's TEXTUAL same-text guard is not what decides this: only the DECLARED pair is
    cands = [dict(base, candidate_id="an03", registry_id="BSR-AN-03", locator="Athanasian Creed", witness=False,
                  phrase="neither confounding the Persons nor dividing the Substance"),
             dict(base, candidate_id="quic", registry_id="BSR-AN-06", locator=quic, witness=True,
                  phrase="the Father uncreate, the Son uncreate, and the Holy Ghost uncreate"),
             dict(base, candidate_id="chal", registry_id="BSR-AN-06", locator=chal, witness=True,
                  phrase="without confusion, without change, without division, without separation")]
    a = allocate(cands, groups={})
    # the Quicunque Vult takes no slot beside AN-03; the Chalcedonian Definition competes and keeps one
    assert "quic" not in a["kept"] and "chal" in a["kept"] and "an03" in a["kept"]
    assert [w["candidate_id"] for w in a["parallel_witnesses"].get("an03", [])] == ["quic"]


# ---------------------------------------------------------------- R6-49: the Articles of Religion are held
def test_the_tec_articles_of_religion_are_not_fetched_and_not_added(reg):
    """R6-49: held for the Codex F.9 adoption QA. Nothing in this session fetches them or adds a row for them."""
    assert not any("Articles of Religion" in s(r.get("standard_title")) and r["branch"] == "Anglican"
                   and r["registry_id"] != "BSR-AN-01" for r in reg.rows), \
        "no new Anglican Articles of Religion row"
    for rid in ("BSR-AN-04", "BSR-AN-06"):
        for c in store.load_chunks(rid):
            assert "Articles of Religion" not in c["text"], (rid, c["locator"])
            assert "Of Faith in the Holy Trinity" not in c["text"], (rid, c["locator"])
    assert "Articles of Religion" in sources.TEC_HISTORICAL_STOP_HEADINGS


# ---------------------------------------------------------------- the cross-row relocation
def test_a_candidate_whose_text_moved_to_another_row_follows_the_text():
    """R6-48. Every earlier re-chunk moved text within one row. Here the text leaves BSR-AN-04 for BSR-AN-06, and a
    stored candidate must follow it: the evidence is unchanged, the row holding it is not. The mapping COMPOSES across
    session 13's and session 14's files, because the candidates are stored under the ORIGINAL p. 862 locator."""
    moves = packets.relocations()
    key = ("BSR-AN-04", "Outline of the Faith (BCP p. 862) — The Christian Hope: Q. What, then, is our assurance "
                        "as Christians?")
    assert key in moves, sorted(k[1][:40] for k in moves if k[0] == "BSR-AN-04")
    rids = {rid for rid, _ in moves[key]["new_ids"]}
    assert rids == {"BSR-AN-04", "BSR-AN-06"}
    assert moves[key]["composed_through"], "the two hops must be composed, or 19 citations are dropped at build"
    # and relocate() actually follows it, re-asserting the phrase in the chunk BSR-AN-06 now holds
    idx = {(c["registry_id"], c["locator"]): c for rid in ("BSR-AN-04", "BSR-AN-06") for c in store.load_chunks(rid)}
    cand = {"registry_id": "BSR-AN-04", "locator": key[1],
            "phrase": "one and the same Christ, Son, Lord, Only-begotten"}
    chunk, rel = packets.relocate(cand, idx, moves)
    assert chunk is not None and chunk["registry_id"] == "BSR-AN-06"
    assert rel["cross_row"] is True and rel["registry_id_now"] == "BSR-AN-06"
    assert "Chalcedon" in rel["locator_now"]
    # a phrase that is in NO mapped chunk is not relocated anywhere
    chunk, rel = packets.relocate(dict(cand, phrase="this phrase is in no chunk of the Book of Common Prayer"), idx, moves)
    assert rel is None
