"""Session 14, phase 3: the registered-section extents the author ratified (R6-57 / Codex B1(e)), and the two holds
this session must not cross (R6-55 allocation, R6-56 no tier move).

R6-57 was ALREADY implemented by session 13 phase 2. This session verified that against the artifacts — the
registered-sections file, the stored chunks and the registry's own registered keys, not the session 13 report's
description of them — and these tests lock the three judgments so no later session loses them silently."""
import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import rulings, store, config  # noqa: E402
from sjn_recovery.registry import Registry, bare_tier, s  # noqa: E402

AN03 = ("BSR-AN-03", "Athanasian Creed (Quicunque Vult), At Morning Prayer, BCP")
EO06_CHALCEDON_10 = ("BSR-EO-06", "Definition of Faith, Council of Chalcedon (451), paragraph 10")


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:
        pytest.skip(f"registry unavailable: {e}")


def _section(rid, locator):
    return next((e for e in rulings.registered_sections() if (e["registry_id"], e["locator"]) == (rid, locator)), None)


def _registered(reg, rid, locator):
    for branch in config.BRANCHES:
        for t in reg.registered_creed_texts(branch) + reg.registered_definition_texts(branch):
            if (t["registry_id"], t["locator"]) == (rid, locator):
                return t
    return None


# ---------------------------------------------------------------- R6-57 (1): the creed portion of a mixed block
def test_a_mixed_block_registers_only_its_creed_portion_and_records_the_extent(reg):
    """Codex B1(e): a registered section runs as far as the creed itself runs, not as far as the stored block runs.
    Every section whose stored chunk carries more than the creed records `text_through`, and the registered key stops
    there — checked on the stored chunk, not on a description of it."""
    mixed = [e for e in rulings.registered_sections() if e.get("text_through")]
    assert {(e["registry_id"], e["locator"]) for e in mixed} == {
        ("BSR-LU-01", "Ecumenical Creeds: The Apostles' Creed"),
        ("BSR-RP-04", "Book of Confessions 1.3 (Nicene Creed)"),
        ("BSR-RP-04", "Book of Confessions 2.3 (Apostles' Creed)"),
        AN03,
    }, "the four mixed blocks session 13 found and the author ratified in R6-57"
    for e in mixed:
        t = _registered(reg, e["registry_id"], e["locator"])
        assert t is not None, e
        chunk = next(c for c in store.load_chunks(e["registry_id"]) if c["locator"] == e["locator"])
        i = chunk["text"].find(e["text_through"])
        assert i >= 0, (e["registry_id"], e["locator"], "text_through must occur in the stored chunk")
        # the extent is RECORDED: registered chars stop at the marker, and the chunk really does run on past it
        assert t["chars"] == i + len(e["text_through"]), (e["registry_id"], e["locator"])
        assert t["chars"] < len(chunk["text"]), "a mixed block registers less than the whole chunk"
        assert e.get("note"), "B1(e): the extent is recorded with what lies outside it"


def test_the_gloria_patri_after_an03_is_left_out_as_liturgical_matter(reg):
    """R6-57 (2). The BCP appoints the Gloria Patri after the Quicunque Vult at Morning Prayer, and the stored chunk
    carries it. It is liturgical matter printed alongside the creed, not the creed, so it is outside the extent."""
    e = _section(*AN03)
    assert e["text_through"] == "he cannot be saved."
    chunk = next(c for c in store.load_chunks(AN03[0]) if c["locator"] == AN03[1])
    assert "Glory be to the Father" in chunk["text"], "the test binds only while the chunk really carries the Gloria"
    t = _registered(reg, *AN03)
    assert t is not None and "glory be to the father" not in t["key"]
    assert t["key"].rstrip().endswith("he cannot be saved")
    # and no phrase taken from the Gloria can resolve through AN-03
    assert reg.resolve_registered_phrase("Anglican", "Glory be to the Father, and to the Son") is None


def test_eo06_chalcedon_paragraph_10_is_left_out_as_acts_narrative(reg):
    """R6-57 (3). Chalcedon paragraph 10 is the acts' record of the bishops' acclamation after the definition was read
    ('After the reading of the definition, all the most religious Bishops cried out ...'), not the definition."""
    listed = rulings.registered_sections()
    assert EO06_CHALCEDON_10 not in {(e["registry_id"], e["locator"]) for e in listed}
    not_reg = {(e["registry_id"], e["locator"]): e for e in
               json.load(open(rulings.REGISTERED_SECTIONS_PATH, encoding="utf-8"))["not_registered"]}
    assert EO06_CHALCEDON_10 in not_reg and "not the definition itself" in not_reg[EO06_CHALCEDON_10]["why"]
    assert _registered(reg, *EO06_CHALCEDON_10) is None
    # paragraphs 1-9 of Chalcedon ARE registered; only the acclamation paragraph is out. And the Constantinople III
    # definition's own paragraph 10 is a definition paragraph and stays registered — the exclusion is by document.
    chal = [t for t in reg.registered_definition_texts("Eastern Orthodox")
            if t["registry_id"] == "BSR-EO-06" and "Chalcedon" in t["locator"]]
    assert [t["locator"].rsplit(" ", 1)[1] for t in chal] == [str(i) for i in range(1, 10)]
    assert _registered(reg, "BSR-EO-06", "Definition of Faith, Third Council of Constantinople (680–681), paragraph 10")


def test_an_extent_marker_that_does_not_occur_in_the_stored_chunk_fails_loudly(tmp_path, monkeypatch, reg):
    """B1(e) is only worth as much as its enforcement: a text_through the chunk does not carry is a hard stop, never a
    silent whole-chunk registration."""
    listed = copy.deepcopy(json.load(open(rulings.REGISTERED_SECTIONS_PATH, encoding="utf-8")))
    for e in listed["sections"]:
        if (e["registry_id"], e["locator"]) == AN03:
            e["text_through"] = "this string is not in the Book of Common Prayer"
    p = tmp_path / "sections.json"
    p.write_text(json.dumps(listed, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(p))
    r = Registry()
    with pytest.raises(SystemExit) as ex:
        r.registered_creed_texts("Anglican")
    assert "text_through" in str(ex.value)


def test_dropping_an03s_extent_would_register_the_gloria(tmp_path, monkeypatch):
    """The mutation check for R6-57 (2): without the extent, the Gloria enters the registered key. This is what the
    ruling prevents, shown rather than asserted."""
    listed = copy.deepcopy(json.load(open(rulings.REGISTERED_SECTIONS_PATH, encoding="utf-8")))
    for e in listed["sections"]:
        if (e["registry_id"], e["locator"]) == AN03:
            e.pop("text_through", None)
    p = tmp_path / "sections.json"
    p.write_text(json.dumps(listed, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(p))
    r = Registry()
    t = next(t for t in r.registered_creed_texts("Anglican") if t["registry_id"] == AN03[0] and t["locator"] == AN03[1])
    assert "glory be to the father" in t["key"]
    assert r.resolve_registered_phrase("Anglican", "Glory be to the Father, and to the Son") is not None


def test_listing_eo06_chalcedon_paragraph_10_would_register_the_acclamation(tmp_path, monkeypatch):
    """The mutation check for R6-57 (3)."""
    listed = copy.deepcopy(json.load(open(rulings.REGISTERED_SECTIONS_PATH, encoding="utf-8")))
    listed["sections"].append({"registry_id": EO06_CHALCEDON_10[0], "locator": EO06_CHALCEDON_10[1], "kind": "DEFINITION",
                               "what": "planted by the mutation check"})
    listed["not_registered"] = [e for e in listed["not_registered"]
                                if (e["registry_id"], e["locator"]) != EO06_CHALCEDON_10]
    p = tmp_path / "sections.json"
    p.write_text(json.dumps(listed, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(p))
    r = Registry()
    hit = [t for t in r.registered_definition_texts("Eastern Orthodox")
           if (t["registry_id"], t["locator"]) == EO06_CHALCEDON_10]
    assert hit, "the mutation must actually register it, or the real test proves nothing"


# ---------------------------------------------------------------- R6-56: no tier moves in this session
def test_no_row_moved_tier_in_this_session(reg):
    """R6-56 / Codex B1(d): a row on the line waits at its present tier. The only authority_tier override in force is
    session 13's R6-44 on BSR-LU-03; BSR-AN-02 and BSR-RC-01 carry none and resolve at their workbook tier."""
    moved = {rid: ov["field_rulings"]["authority_tier"] for rid, ov in rulings.registry_overrides().items()
             if "authority_tier" in ov["fields"]}
    # the two that were already in force before this session, and nothing else: R6-5 (session 7, BSR-EO-01 re-typed as
    # the Hopko row it is) and R6-44 (session 13, the confessed catechism). Session 14 moves no row.
    assert moved == {"BSR-EO-01": "R6-5_bsr_eo_01_retype", "BSR-LU-03": "R6-44_confessed_catechisms"}, moved
    for rid in ("BSR-AN-02", "BSR-RC-01"):
        row = reg.by_id[rid]
        assert bare_tier(s(row["authority_tier"])) == "CATECHETICAL", (rid, row["authority_tier"])
        assert not (row.get("_author_ruling_override") or {}).get("applied", {}).get("authority_tier")


# ---------------------------------------------------------------- R6-55: allocation unchanged
def test_q195_third_lutheran_seat_holds_at_lu01_2_and_the_lcms_slot_at_lu02_1(reg, tmp_path, monkeypatch):
    """R6-55 / Codex F.11: allocation across speaks_for groups is accepted as it stands. Q-195's worked example is
    locked here — recomputed from the stored cell state through the live allocator, no model calls — so the seats
    cannot move without a ruling on F.11."""
    from sjn_recovery.agents import CellRunner
    from sjn_recovery.registry import load_predicates, load_comparators, load_queue, open_cells
    from sjn_recovery import packets as pk

    class _NoLlm:
        run_id = "test"

        def complete(self, *a, **k):
            raise AssertionError("R6-55's check makes no model call")

    state_dir = os.path.join(config.RUNS_DIR, "live-1", "cells")
    if not os.path.exists(os.path.join(state_dir, "Q-195.json")):
        pytest.skip("live-1 Q-195 state not present")
    preds, comps = load_predicates(reg.wb), load_comparators(reg.wb)
    cell = next(c for c in open_cells(load_queue(reg.wb)) if c["queue_id"] == "Q-195")
    runner = CellRunner(_NoLlm(), reg, preds, comps, state_dir, "sonnet", ["sonnet", "opus"],
                        log=lambda *x: None, run_coder=False)
    runner.save = lambda st: None                       # never write a cell state from a test
    runner.refinalize(runner.load("Q-195"), "Lutheran")
    # the seats are the BUILD-time allocation (tiers re-resolved from the phrase, R6-5 clause 1 / R6-10), not the
    # coder-time one the cell state stores: the card is what the author sees, so the card is what R6-55 locks
    out = tmp_path / "packets"
    monkeypatch.setattr(pk, "PACKETS_DIR", str(out))
    packet = pk.build_branch_packet("Lutheran", [cell], runner, reg, preds, comps, "test-r6-55", log=lambda *x: None)
    card = next(c for c in packet["cards"] if c["queue_id"] == "Q-195")
    kept = [e["candidate_id"] for e in card["candidates"]]
    assert kept == ["Q-195-p1-BSR-LU-01-1", "Q-195-p1-BSR-LU-02-1", "Q-195-p1-BSR-LU-01-2"], kept
    assert all(e["effective_tier"] == "CONFESSIONAL" for e in card["candidates"])
    # the LCMS confessional slot is held by the Augsburg Confession, before and after (the v0.6 correction to R6-41)
    groups = {e["candidate_id"]: e["speaks_for_group"] for e in card["candidates"]}
    assert groups["Q-195-p1-BSR-LU-02-1"] == "lcms"
    assert sum(1 for g in groups.values() if g == "lcms") == 1
    # and LU-03-1, the FULL Small Catechism sentence, is cut by the group cap, not by its floor: it is not on the card
    assert "Q-195-p1-BSR-LU-03-1" not in kept
    assert any(r.get("candidate_id") == "Q-195-p1-BSR-LU-03-1" and r.get("stage") == "tier allocation"
               for r in card["rejections"]), [(r.get("candidate_id"), r.get("stage")) for r in card["rejections"]]
