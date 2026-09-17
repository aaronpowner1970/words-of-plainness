"""Session 13 (2026-09-17): rulings R6-43 to R6-46.

  phase 1  the rulings are recorded
  phase 2  R6-43 / Codex B1(a): registration is by section (registry.registered_sections, registered-sections.json)
  phase 3  R6-44 / Codex B1(b): BSR-LU-03 is CONFESSIONAL; the override hook combines several rulings on one row"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import rulings, store, config  # noqa: E402
from sjn_recovery.registry import Registry, bare_tier  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:
        pytest.skip(f"registry unavailable: {e}")


# ---------------------------------------------------------------- phase 1
def test_r6_43_to_r6_46_are_recorded():
    R = rulings.load()["rulings"]
    for key in ("R6-43_registration_by_section", "R6-44_confessed_catechisms", "R6-45_an04_historical_documents_scope",
                "R6-46_session12_confirmations"):
        assert R[key]["status"] == "RATIFIED" and R[key]["ruled"] == "2026-09-17", key
        assert "session 13" in R[key]["source"], key
    assert R["R6-44_confessed_catechisms"]["rows_moved"] == ["BSR-LU-03"]
    assert set(R["R6-46_session12_confirmations"]["items"]) == {"1_an05_guard", "2_rp05_notes", "3_r6_41_interpretations",
                                                               "4_phase2_seat_effects", "5_in_scope"}


# ---------------------------------------------------------------- phase 2: R6-43, registration is by section
TREATMENT = r"catechism|commentary|exposition|explanation|introduction|preface|\bQ\.|Q&A|question"


def _all_registered(reg):
    return [(kind, t) for b in config.BRANCHES
            for kind, texts in (("CREED", reg.registered_creed_texts(b)), ("DEFINITION", reg.registered_definition_texts(b)))
            for t in texts]


def test_r6_27_extends_to_sections_no_registered_section_is_a_catechism_or_commentary_section(reg):
    import re
    registered = _all_registered(reg)
    assert registered, "the test binds only if something is registered"
    for kind, t in registered:
        row = reg.by_id[t["registry_id"]]
        assert bare_tier(row["authority_tier"]) != "CATECHETICAL", t["locator"]                  # R6-27 on rows, as before
        chunk = next(c for c in store.load_chunks(t["registry_id"]) if c["locator"] == t["locator"])
        assert not re.search(TREATMENT, f"{chunk['locator']} {chunk.get('division') or ''}", re.I), (t["registry_id"], t["locator"])
        assert t["section"]["kind"] == kind
    # the registered key never carries the commentary a stored chunk runs on into (RP-04 1.3 / 2.3, LU-01, AN-03)
    keys = {(t["registry_id"], t["locator"]): t["key"] for _, t in registered}
    assert "marcion" not in keys[("BSR-RP-04", "Book of Confessions 1.3 (Nicene Creed)")]
    assert "scots confession" not in keys[("BSR-RP-04", "Book of Confessions 2.3 (Apostles' Creed)")]
    assert "universal" not in keys[("BSR-LU-01", "Ecumenical Creeds: The Apostles' Creed")]
    assert not keys[("BSR-AN-03", "Athanasian Creed (Quicunque Vult), At Morning Prayer, BCP")].endswith("world without end amen")
    # mutation: a listed catechism section is refused by the test's own predicate
    assert re.search(TREATMENT, "Small Catechism: II. The Creed, ¶1–3 paragraph-range", re.I)


def test_lu01_small_and_large_catechism_creed_sections_are_not_registered(reg):
    locs = {t["locator"] for t in reg.registered_creed_texts("Lutheran") if t["registry_id"] == "BSR-LU-01"}
    stored = [c["locator"] for c in store.load_chunks("BSR-LU-01")]
    catechism_creed = [loc for loc in stored if loc.startswith(("Small Catechism: II. The Creed", "Large Catechism: The Apostles' Creed"))]
    assert catechism_creed, "the test binds: the store carries the catechisms' Creed sections"
    assert not (set(catechism_creed) & locs)
    assert not any(reg.is_registered_section("BSR-LU-01", loc) for loc in catechism_creed)
    # a phrase only Luther's exposition carries resolves to nothing
    lc = next(c for c in store.load_chunks("BSR-LU-01") if c["locator"] == "Large Catechism: The Apostles' Creed, ¶10–17")
    phrase = " ".join(lc["text"].split()[:10])
    assert not any(h["registry_id"] == "BSR-LU-01" and "Catechism" in h["locator"] for h in reg.registered_phrase_hits("Lutheran", phrase))


def test_lu01_ecumenical_creeds_sections_are_registered(reg):
    locs = {t["locator"] for t in reg.registered_creed_texts("Lutheran") if t["registry_id"] == "BSR-LU-01"}
    assert locs == {"Ecumenical Creeds: The Apostles' Creed", "Ecumenical Creeds: The Nicene Creed", "Ecumenical Creeds: The Athanasian Creed"}
    hit = reg.resolve_registered_phrase("Lutheran", "begotten of the Father before all worlds")
    assert hit and hit["locator"] == "Ecumenical Creeds: The Nicene Creed" and hit["tier"] == "CONFESSIONAL"


def test_every_listed_section_is_stored_and_the_list_is_the_only_registration_path(reg, tmp_path, monkeypatch):
    import json
    listed = rulings.registered_sections()
    registered = {(t["registry_id"], t["locator"]) for _, t in _all_registered(reg)}
    stored_rows = {e["registry_id"] for e in listed if store.load_chunks(e["registry_id"])}
    assert {(e["registry_id"], e["locator"]) for e in listed if e["registry_id"] in stored_rows} == registered
    # an empty list registers nothing, whatever the locators and row tiers say
    empty = tmp_path / "sections.json"
    empty.write_text(json.dumps({"sections": []}), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(empty))
    r2 = Registry()
    assert r2.registered_creed_texts("Lutheran") == [] and r2.registered_definition_texts("Roman Catholic") == []
    # a CATECHETICAL row listed as a creed section fails loudly (R6-22 / R6-27)
    bad = tmp_path / "bad.json"
    loc = store.load_chunks("BSR-RC-01")[0]["locator"]
    bad.write_text(json.dumps({"sections": [{"registry_id": "BSR-RC-01", "locator": loc, "kind": "CREED", "what": "x"}]}), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(bad))
    r3 = Registry()
    assert bare_tier(r3.by_id["BSR-RC-01"]["authority_tier"]) == "CATECHETICAL"
    with pytest.raises(SystemExit):
        r3.registered_creed_texts("Roman Catholic")


def test_sections_spanning_several_chunks_are_reported():
    spans = {e["section_spans_chunks"] for e in rulings.registered_sections() if e.get("section_spans_chunks")}
    assert "Book of Confessions 1.1-1.3 (3 chunks)" in spans and "Constitution 1, paragraphs 1-4 (4 chunks)" in spans
