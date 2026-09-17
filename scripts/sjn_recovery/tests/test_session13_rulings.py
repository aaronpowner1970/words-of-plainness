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


# ---------------------------------------------------------------- phase 3: R6-44, confessed catechisms
def test_lu03_is_confessional_with_the_workbook_value_recorded_and_keeps_disclosure_and_guard(reg):
    from sjn_recovery.registry import SECOND_TIER
    row = reg.by_id["BSR-LU-03"]
    assert row["authority_tier"] == "CONFESSIONAL"
    ov = row["_author_ruling_override"]
    assert ov["applied"]["authority_tier"] == {"workbook": "CATECHETICAL", "ruled": "CONFESSIONAL"}
    assert ov["field_rulings"] == {"draft_recommendation": "R6-37_lu03_adoption", "authority_tier": "R6-44_confessed_catechisms"}
    assert "(c) 2019" in row["draft_recommendation"]                               # R6-37's override survives R6-44's
    assert reg.adoption("BSR-LU-03")["adoption_status"] == "ADOPTED"
    d = reg.adoption_disclosure("BSR-LU-03")["text"]
    assert d == "approved by The Lutheran Church-Missouri Synod (one church); English translation: Concordia Publishing House (c) 2019"
    c = store.load_chunks("BSR-LU-03")[0]
    assert reg.apparatus_guard("BSR-LU-03", c) is None and reg.effective_tier("BSR-LU-03", c) == "CONFESSIONAL"
    probe = dict(c, text="The Central Thought " + c["text"])
    assert reg.apparatus_guard("BSR-LU-03", probe) and bare_tier(reg.effective_tier("BSR-LU-03", probe)) == SECOND_TIER
    # no other row moved: every other override on authority_tier is an earlier ruling's
    moved = {rid for rid, o in reg.registry_overrides.items() if "authority_tier" in o["applied"]}
    assert {rid for rid in moved if reg.registry_overrides[rid]["field_rulings"]["authority_tier"] == "R6-44_confessed_catechisms"} == {"BSR-LU-03"}


def test_several_rulings_on_one_row_combine_and_a_conflict_fails_loudly():
    doc = {"rulings": {
        "R6-A": {"registry_id": "BSR-X-01", "overrides": {"draft_recommendation": "INCLUDE"}},
        "R6-B": {"registry_id": "BSR-X-01", "overrides": {"authority_tier": "CONFESSIONAL"}},
        "R6-C": {"registry_id": "BSR-X-02", "overrides": {"scope_caveat": "c"}}}}
    ov = rulings.registry_overrides(doc)
    assert ov["BSR-X-01"]["fields"] == {"draft_recommendation": "INCLUDE", "authority_tier": "CONFESSIONAL"}   # neither replaces the other
    assert ov["BSR-X-01"]["rulings"] == ["R6-A", "R6-B"] and ov["BSR-X-01"]["ruling"] == "R6-A; R6-B"
    assert ov["BSR-X-01"]["field_rulings"] == {"draft_recommendation": "R6-A", "authority_tier": "R6-B"}
    assert ov["BSR-X-02"]["fields"] == {"scope_caveat": "c"}
    doc["rulings"]["R6-D"] = {"registry_id": "BSR-X-01", "overrides": {"authority_tier": "CATECHETICAL"}}
    with pytest.raises(SystemExit):
        rulings.registry_overrides(doc)
    doc["rulings"]["R6-D"]["overrides"]["authority_tier"] = "CONFESSIONAL"                                     # agreeing rulings combine
    assert rulings.registry_overrides(doc)["BSR-X-01"]["field_rulings"]["authority_tier"] == "R6-B"


# ---------------------------------------------------------------- phase 4: R6-45, R6-46.1, the corpus builder
def test_an04_historical_documents_chunks_carry_the_scope_marker_and_are_never_registered(reg, tmp_path, monkeypatch):
    import json
    assert set(rulings.scope_markers()) == {"BSR-AN-04"}
    hist = [c for c in store.load_chunks("BSR-AN-04") if c["locator"].startswith("Historical Documents of the Church")]
    outline = [c for c in store.load_chunks("BSR-AN-04") if c["locator"].startswith("Outline of the Faith")]
    assert outline and all(reg.scope_marker("BSR-AN-04", c) is None for c in outline)
    for c in hist:
        m = reg.scope_marker("BSR-AN-04", c)
        assert m["marker"] == "AWAITING_SCOPE_RULING" and m["ruling"] == "R6-45_an04_historical_documents_scope"
        res = reg.tier_resolution("BSR-AN-04", c, " ".join(c["text"].split()[:8]))
        assert res["awaits_scope_ruling"] == m
        assert not reg.is_registered_section("BSR-AN-04", c["locator"])
    registered = {(t["registry_id"], t["locator"]) for t in reg.registered_creed_texts("Anglican") + reg.registered_definition_texts("Anglican")}
    assert not any(rid == "BSR-AN-04" for rid, _ in registered)
    assert not any(reg.scope_marker(rid, {"locator": loc}) for rid, loc in registered)
    # listing a marked section fails loudly, even if a row gate would otherwise let it through
    probe = {"registry_id": "BSR-AN-04", "locator": "Historical Documents of the Church (BCP p. 864) — Quicunque Vult", "kind": "CREED", "what": "x"}
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"sections": [probe]}), encoding="utf-8")
    monkeypatch.setattr(rulings, "REGISTERED_SECTIONS_PATH", str(f))
    with pytest.raises(SystemExit):
        Registry().registered_creed_texts("Anglican")


def test_an05_guard_covers_only_the_front_matter_before_part_i(reg):
    from sjn_recovery import sources
    chunks = store.load_chunks("BSR-AN-05")
    guarded = [c["locator"] for c in chunks if reg.apparatus_guard("BSR-AN-05", c)]
    part_i = [c for c in chunks if c["division"] == sources.ACNA_PART_I_INTRO]
    if not part_i:
        pytest.skip("BSR-AN-05 not yet re-chunked in this checkout")
    assert guarded == ["To Be a Christian, front matter — introduction: drafting guidelines, the Committee's sign-off, Scripture references, collect"]
    assert len(part_i) == 1 and reg.apparatus_guard("BSR-AN-05", part_i[0]) is None
    assert reg.effective_tier("BSR-AN-05", part_i[0]) == "CATECHETICAL"
    first_q = next(i for i, c in enumerate(chunks) if c["division"] == "question")
    assert [c["division"] for c in chunks[:first_q]] == [sources.ACNA_FRONT_MATTER, sources.ACNA_PART_I_INTRO]


def test_a_only_build_keeps_the_manifest_entries_of_rows_the_registry_filters_out():
    from sjn_recovery import corpus
    prev = {"BSR-EO-02": {"status": "UNCHANGED"}, "BSR-EO-03": {"status": "HOST_RETIRED", "n_chunks": 0}, "BSR-EO-04": {"status": "UNCHANGED"}}
    results = {"BSR-EO-02": {"status": "UNCHANGED"}, "BSR-EO-04": {"status": "REBUILT (drift accepted)"}}
    kept = corpus.keep_unyielded_entries(results, prev, {"BSR-EO-04"})
    assert kept == ["BSR-EO-03"]
    assert list(results) == ["BSR-EO-02", "BSR-EO-03", "BSR-EO-04"]                 # manifest order kept
    assert results["BSR-EO-03"] == {"status": "HOST_RETIRED", "n_chunks": 0} and results["BSR-EO-04"]["status"] == "REBUILT (drift accepted)"
    full = {"BSR-EO-02": {"status": "UNCHANGED"}}
    assert corpus.keep_unyielded_entries(full, prev, None) == [] and list(full) == ["BSR-EO-02"]   # a full build keeps none
    # the committed manifest carries BSR-EO-03, which the registry filters out
    m = store.load_manifest()["standards"]
    assert m["BSR-EO-03"]["status"] == "HOST_RETIRED"


# ---------------------------------------------------------------- phase 5: rows added by ruling, BSR-BA-04 (R6-42)
def _rulings_copy(tmp_path, monkeypatch, mutate):
    import json
    d = json.load(open(rulings.RULINGS_PATH, encoding="utf-8"))
    mutate(d["rulings"])
    f = tmp_path / "rulings.json"
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rulings, "RULINGS_PATH", str(f))
    return d


def test_a_row_added_by_ruling_is_a_separate_path_and_the_workbook_wins_once_it_agrees(reg, tmp_path, monkeypatch):
    base = {"registry_id": "BSR-XX-01", "branch": "Baptist", "standard_title": "T", "authority_tier": "OFFICIAL_EXPOSITION",
            "speaks_for": "S", "reception_scope": "JURISDICTIONAL", "publisher_domain": "example.org",
            "canonical_url": "https://example.org/x", "fetch_mode": "HTML", "scope_caveat": "C"}
    doc = {"rulings": {"R6-A": {"add_row": True, "new_row": dict(base), "ruled": "2026-09-17"},
                       "R6-B": {"new_row": dict(base, registry_id="BSR-XX-02")}}}              # no add_row: records a proposal only
    assert set(rulings.added_rows(doc)) == {"BSR-XX-01"}
    assert rulings.registry_overrides(doc) == {}                                                 # the override hook never sees it
    for bad in ({"registry_id": "BSR-BA-04 (confirmed as the next free Baptist id in phase 4)"}, {"scope_caveat": ""}):
        with pytest.raises(SystemExit):
            rulings.added_rows({"rulings": {"R6-A": {"add_row": True, "new_row": dict(base, **bad)}}})
    # the live registry: BSR-BA-04 is added, recorded as coming from the ruling
    row = reg.by_id["BSR-BA-04"]
    assert row["_author_ruling_added"]["ruling"] == "R6-42_ba04_identity_statement" and row["__row"] is None
    assert {"registry_id": "BSR-BA-04", "ruling": "R6-42_ba04_identity_statement", "status": "ADDED"} in reg.rulings_applied
    # an unknown branch spelling fails loudly
    _rulings_copy(tmp_path, monkeypatch, lambda R: R["R6-42_ba04_identity_statement"]["new_row"].update(branch="Baptists"))
    with pytest.raises(SystemExit):
        Registry()
    # once the workbook carries the id: agreeing values -> read from the workbook; a disagreement fails loudly
    wb3 = {k: reg.by_id["BSR-BA-03"][k] for k in rulings.ADDED_ROW_REQUIRED}

    def as_ba03(R, **change):
        R["R6-42_ba04_identity_statement"]["add_row"] = False
        R["R6-X"] = {"add_row": True, "new_row": dict(wb3, **change), "ruled": "2026-09-17"}
    _rulings_copy(tmp_path, monkeypatch, lambda R: as_ba03(R))
    r2 = Registry()
    assert r2.by_id["BSR-BA-03"]["_author_ruling_added"]["source"].startswith("WORKBOOK") and "BSR-BA-04" not in r2.by_id
    _rulings_copy(tmp_path, monkeypatch, lambda R: as_ba03(R, authority_tier="CONFESSIONAL"))
    with pytest.raises(SystemExit):
        Registry()


def test_ba04_row_resolves_and_discloses_as_ruled(reg):
    R = rulings.load()["rulings"]["R6-42_ba04_identity_statement"]
    row = reg.by_id["BSR-BA-04"]
    for f in rulings.ADDED_ROW_REQUIRED:
        assert row[f] == R["new_row"][f], f
    assert row["registry_id"] == "BSR-BA-04" and row["branch"] == "Baptist" and row["status"] == "AUTHOR_RATIFIED"
    assert "BSR-BA-04" in [r["registry_id"] for r in reg.for_branch("Baptist")] and not reg.is_fallback("BSR-BA-04")
    assert reg.domains("BSR-BA-04") == ["abc-usa.org"] and reg.citation_refusal("BSR-BA-04") is None
    a = reg.adoption("BSR-BA-04")
    assert (a["adoption_status"], a["adoption_body_scope"]) == ("ADOPTED", "ONE_CHURCH")
    assert reg.adoption_disclosure("BSR-BA-04")["text"] == (
        "American Baptist Churches USA holds no binding creed. Its cooperating churches affirm this statement as descriptive "
        "of American Baptist faith and practice.")
    chunks = store.load_chunks("BSR-BA-04")
    if not chunks:
        pytest.skip("BSR-BA-04 has no corpus in this checkout")
    assert all(reg.effective_tier("BSR-BA-04", c) == "OFFICIAL_EXPOSITION" for c in chunks)
    assert chunks[0]["text"].startswith("American Baptists worship the triune God")
    assert chunks[-1]["text"].endswith("That Jesus shall reign for ever and ever.")
    assert not any("covenanting partners" in c["text"] or "Standing Rules" in c["text"] for c in chunks)
    assert any("God’s reconciling grace" in c["text"] for c in chunks)                     # the apostrophe survives decoding
    assert [c["locator"] for c in chunks if "People" in c["locator"]][:2] == ["We Are American Baptists — A Redeemed People",
                                                                              "We Are American Baptists — A Biblical People"]
    # and BSR-BA-03's own disclosure wording is untouched
    assert reg.adoption_disclosure("BSR-BA-03")["text"] == "Descriptive denominational statement; American Baptist Churches USA does not adopt binding creeds"


def test_ba04_adapter_keeps_the_statement_and_excludes_the_head_note():
    from sjn_recovery import sources
    url = "https://www.abc-usa.org/we-are-american-baptists"
    page = ("<html><head><meta charset='UTF-8'></head><body><nav>Who We Are</nav><div class='content-section'>"
            "<h3><strong>“We Are American Baptists”</strong></h3>"
            "<p><em>“We Are American Baptists” is an expression adopted by the covenanting partners of American Baptist Churches, 6/19/98. "
            "It can be found in the Standing Rules, under Addendum #1.</em></p>"
            "<p>American Baptists worship the triune God of the Bible.</p><p class='content-img'><img src='x.jpg'/></p>"
            "<p>We are called to proclaim God’s reconciling grace.</p>"
            "<p>THEREFORE…With Baptist brothers and sisters around the world, we believe:</p><ul><li>That the Bible is the final authority;</li></ul>"
            "<p>Within the larger Baptist family, American Baptists emphasize convictions.</p><p>We affirm that God through Jesus Christ calls us to be:</p>"
            "<p><strong>A Redeemed People</strong></p><ul><li>who claim a personal relationship to God;</li><li>who live as visible saints.</li></ul>"
            "<p><strong>We further believe</strong></p><ul><li>That we live with a realizable hope; and</li><li>That Jesus shall reign for ever and ever.</li></ul>"
            "<p>&nbsp;</p><p><a href='x.pdf'>View a Print Ready version here</a>.</p></div><footer>f</footer></body></html>")
    as_fetched = page.encode("utf-8").decode("latin-1")                                            # the fetcher's ISO-8859-1 reading

    class _F:
        def get(self, u):
            class FR:
                ok, status, error, final_url, redirects, cross_host_redirect, content_type = True, 200, "", u, [], "", "text/html"
            FR.html = self.pages[u]
            return FR()
    f = _F()
    row = {"registry_id": "BSR-BA-04", "branch": "Baptist", "standard_title": "T", "authority_tier": "OFFICIAL_EXPOSITION",
           "scope_caveat": "", "reception_scope": "JURISDICTIONAL", "canonical_url": url}
    f.pages = {url: as_fetched}
    out, notes = sources.abc_usa_we_are_american_baptists(sources.Ctx(row, f, log=lambda m: None, admitted_hosts=None))
    locs = [c["locator"] for c in out]
    assert locs == ["We Are American Baptists, ¶1", "We Are American Baptists, ¶2",
                    "We Are American Baptists — Therefore, with Baptists around the world, we believe",
                    "We Are American Baptists — American Baptist convictions (introduction to the lists)",
                    "We Are American Baptists — A Redeemed People", "We Are American Baptists — We further believe"]
    assert out[1]["text"] == "We are called to proclaim God’s reconciling grace."
    assert out[4]["text"] == "A Redeemed People who claim a personal relationship to God; who live as visible saints."
    assert not any("covenanting" in c["text"] or "Print Ready" in c["text"] or "Who We Are" in c["text"] for c in out)
    assert "re-decoded as UTF-8" in notes[0]
    for broken in (as_fetched.replace("That Jesus shall reign for ever and ever.", "That Jesus reigns."),
                   as_fetched.replace("covenanting partners", "partners")):
        f.pages = {url: broken}
        with pytest.raises(sources.FetchError):
            sources.abc_usa_we_are_american_baptists(sources.Ctx(row, f, log=lambda m: None, admitted_hosts=None))
