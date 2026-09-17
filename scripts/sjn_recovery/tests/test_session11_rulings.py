"""Session 11 (2026-09-17): the adoption ratification, rulings R6-35 to R6-40 (Comparison Principles Codex B2(a)-(e)).

  R6-35 / R6-36 / R6-40  BSR-RC-07, BSR-AN-02, BSR-AN-04, BSR-AN-05 ADOPTED: their exposition stays CATECHETICAL
  R6-37                  BSR-LU-03 ADOPTED with its translator disclosed; publisher apparatus never inherits it (the guard)
  R6-38                  the scope is the verified reach of the named body (BSR-RP-03 added; BSR-RP-02, BSR-LU-01 amended)
  R6-39                  BSR-BA-03 ISSUED_UNADOPTED with its own disclosure wording, tier unchanged
  goal 3a/3e/3f          the registry corrections, in memory until the workbook carries them
  goal 3c                the Heidelberg chunker keeps an asterisked "Q & A 80*" heading

Tier tests run against the real workbook and chunk store and skip where either is missing."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.registry import Registry, bare_tier, tier_rank, SECOND_TIER  # noqa: E402
from sjn_recovery import rulings, sources, store  # noqa: E402

ADOPTED_CATECHETICAL = ("BSR-RC-07", "BSR-AN-02", "BSR-AN-04", "BSR-AN-05", "BSR-LU-03")
NAMED_REACH = ("BSR-AN-02", "BSR-AN-04", "BSR-AN-05", "BSR-LU-03", "BSR-RP-02", "BSR-RP-03", "BSR-RP-05", "BSR-LU-01")


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:                                             # no workbook in this checkout
        pytest.skip(f"registry unavailable: {e}")


def _lu03_chunk():
    chunks = store.load_chunks("BSR-LU-03")
    if not chunks:
        pytest.skip("BSR-LU-03 has no corpus in this checkout")
    return chunks[0]


# ---------------------------------------------------------------- R6-35 / R6-36 / R6-37 / R6-40
def test_the_ratified_rows_resolve_and_disclose_as_ruled(reg):
    rows = rulings.adoption_rows()
    for rid in ADOPTED_CATECHETICAL:
        assert rows[rid]["adoption_status"] == "ADOPTED"
        assert bare_tier(reg.by_id[rid]["authority_tier"]) == "CATECHETICAL"
        assert reg.exposition_tier(rid) == "CATECHETICAL", rid
        for c in store.load_chunks(rid)[:25]:
            if reg.apparatus_guard(rid, c):
                continue
            assert bare_tier(reg.exposition_tier(rid, None, c)) == "CATECHETICAL", (rid, c["locator"])
    assert rows["BSR-RC-07"]["adoption_body_scope"] == "WHOLE_BRANCH" and reg.adoption_disclosure("BSR-RC-07") is None
    for rid in NAMED_REACH:
        a = reg.adoption(rid)
        d = reg.adoption_disclosure(rid)
        assert a["adoption_status"] == "ADOPTED" and a["adoption_body_scope"] in ("ONE_CHURCH", "MULTILATERAL"), rid
        assert d and a["adopting_body"] in d["text"], rid
        assert ("(one church)" if a["adoption_body_scope"] == "ONE_CHURCH" else "(several churches)") in d["text"], rid
    assert reg.adoption_disclosure("BSR-LU-03")["text"].endswith("English translation: Concordia Publishing House (c) 2019")
    assert reg.adoption_disclosure("BSR-RP-05")["text"].endswith("English translation: CRC/RCA joint translation, 2011")


def test_no_adopted_row_still_says_adoption_unverified(reg):
    for rid, a in reg.adoption_map.items():
        if a["adoption_status"] != "ADOPTED":
            continue
        d = reg.adoption_disclosure(rid)
        assert not d or "adoption unverified" not in d["text"], rid
        assert "unverified" not in bare_tier(reg.exposition_tier(rid)).casefold()


def test_the_earlier_rows_are_unchanged(reg):
    rows = rulings.adoption_rows()
    assert rows["BSR-EO-01"]["adoption_status"] == rows["BSR-EO-02"]["adoption_status"] == "ISSUED_UNADOPTED"
    assert rows["BSR-EO-04"]["adopting_body"] == "Most Holy Governing Synod of the Russian Church"
    assert rows["BSR-RC-01"] == {"adoption_status": "ADOPTED", "adoption_body_scope": "WHOLE_BRANCH", "adoption_act": "Fidei Depositum, 1992",
                                 "adoption_verified": "author ruling 2026-09-16", "adopting_body": "the Apostolic See"}


# ---------------------------------------------------------------- R6-38
def test_the_amended_rows_name_a_body_no_wider_than_verified(reg):
    rows = rulings.adoption_rows()
    assert not [rid for rid, v in rows.items() if v.get("adopting_body") == "the confessing church"]
    assert sorted(rid for rid, v in rows.items() if v.get("adoption_body_scope") == "WHOLE_BRANCH") == ["BSR-RC-01", "BSR-RC-07"]
    rp02 = rows["BSR-RP-02"]
    assert rp02["adoption_body_scope"] == "ONE_CHURCH" and "Orthodox Presbyterian Church" in rp02["adopting_body"]
    assert "OPC" in rp02["adoption_act"] and "OPC" in reg.by_id["BSR-RP-02"]["standard_title"]      # the registry names the OPC
    assert rp02["amended"]["was"] == {"adoption_body_scope": "WHOLE_BRANCH", "adopting_body": "the confessing church"}
    lu01 = rows["BSR-LU-01"]
    assert lu01["adoption_status"] == "ADOPTED"
    assert lu01["adoption_body_scope"] == "ONE_CHURCH" and lu01["adopting_body"] == "The Lutheran Church-Missouri Synod"
    assert "Art. II" in lu01["amended"]["completed_by_verification"]["named_adopting_act_on_record"]
    for rid in ("BSR-RP-02", "BSR-RP-03", "BSR-RP-05", "BSR-LU-01"):
        assert bare_tier(reg.exposition_tier(rid)) == "CONFESSIONAL"                              # no tier effect


# ---------------------------------------------------------------- R6-39
def test_ba03_uses_its_disclosure_wording_exactly(reg):
    a = reg.adoption("BSR-BA-03")
    assert a["adoption_status"] == "ISSUED_UNADOPTED"
    d = reg.adoption_disclosure("BSR-BA-03")
    assert d["text"] == "Descriptive denominational statement; American Baptist Churches USA does not adopt binding creeds"
    assert reg.exposition_tier("BSR-BA-03") == reg.by_id["BSR-BA-03"]["authority_tier"] == "OFFICIAL_EXPOSITION"


# ---------------------------------------------------------------- R6-37: the apparatus guard
def test_the_stored_lu03_chunk_is_luthers_text_and_is_not_guarded(reg):
    c = _lu03_chunk()
    assert reg.apparatus_guard("BSR-LU-03", c) is None
    assert reg.exposition_tier("BSR-LU-03", None, c) == "CATECHETICAL"


@pytest.mark.parametrize("extra", [
    " The Central Thought God the Father made all things and still preserves them.",
    " Explanation: In this article we learn that God is our Creator. What does this mean for me today?",
])
def test_an_lu03_apparatus_chunk_never_resolves_catechetical(reg, extra):
    base = _lu03_chunk()
    for text in (base["text"] + extra, extra.strip(), "The Central Thought " + base["text"]):
        c = dict(base, text=text, locator=base["locator"] + " [apparatus test]")
        assert reg.apparatus_guard("BSR-LU-03", c), text[:60]
        for phrase in (None, "God the Father made all things", "What does this mean for me today", "I believe that God has made me and all creatures"):
            eff = reg.effective_tier("BSR-LU-03", c, phrase)
            assert bare_tier(eff) != "CATECHETICAL", (text[:60], phrase, eff)
        assert bare_tier(reg.exposition_tier("BSR-LU-03", None, c)) == SECOND_TIER
        res = reg.tier_resolution("BSR-LU-03", c, "God the Father made all things")
        assert bare_tier(res["effective_tier"]) == SECOND_TIER and res["apparatus_guard"]
        assert "publisher-added matter" in res["adoption_disclosure"]["text"]
        assert "apparatus guard" in res["why"]


def test_the_guard_is_generic_and_applies_only_where_a_ruling_carries_one(reg):
    guards = rulings.adoption_guards()
    assert sorted(guards) == ["BSR-LU-03"]                                  # not applied to any other row in session 11
    c = store.load_chunks("BSR-AN-05")[:1] or [{"text": "The Central Thought x", "locator": "x", "division": "x"}]
    probe = dict(c[0], text="The Central Thought " + c[0]["text"])
    assert reg.apparatus_guard("BSR-AN-05", probe) is None                  # unguarded row: no effect
    saved = dict(reg._adoption_guards)
    try:
        reg._adoption_guards["BSR-AN-05"] = dict(guards["BSR-LU-03"], registry_id="BSR-AN-05", integral_text_pattern=None)
        assert reg.apparatus_guard("BSR-AN-05", probe)
        assert bare_tier(reg.exposition_tier("BSR-AN-05", None, probe)) == SECOND_TIER
        reg._adoption_guards["BSR-BA-03"] = dict(guards["BSR-LU-03"], registry_id="BSR-BA-03", integral_text_pattern=None)
        low = {"text": "The Central Thought", "locator": "x", "division": "x"}
        assert reg.exposition_tier("BSR-BA-03", None, low) == "OFFICIAL_EXPOSITION"   # never raises, never below its own rank
        cw = {"text": "The Central Thought", "locator": "x", "division": "x"}
        assert tier_rank(reg.exposition_tier("BSR-AN-05", None, cw)) == tier_rank(SECOND_TIER)
    finally:
        reg._adoption_guards.clear(); reg._adoption_guards.update(saved)


def test_a_malformed_guard_fails_loudly():
    bad = {"rulings": {"R6-X": {"guard": {"registry_id": "BSR-LU-03", "kind": "PUBLISHER_APPARATUS", "resolves_to": "CATECHETICAL",
                                          "apparatus_markers": ["x"]}}}}
    with pytest.raises(SystemExit):
        rulings.adoption_guards(bad)
    with pytest.raises(SystemExit):
        rulings.adoption_guards({"rulings": {"R6-X": {"guard": {"registry_id": "BSR-LU-03", "kind": "PUBLISHER_APPARATUS",
                                                               "resolves_to": "OFFICIAL_EXPOSITION"}}}})


# ---------------------------------------------------------------- goal 3a / 3e / 3f: registry corrections in memory
def test_the_registry_corrections_are_applied_in_memory(reg):
    rc07 = reg.by_id["BSR-RC-07"]
    assert rc07["canonical_url"] == "https://www.vatican.va/archive/compendium_ccc/documents/archive_2005_compendium-ccc_en.html"
    chunks = store.load_chunks("BSR-RC-07")
    if chunks:
        assert {c["source_url"] for c in chunks} == {rc07["canonical_url"]}
    assert "2017 explanation edition" not in reg.by_id["BSR-LU-03"]["draft_recommendation"]
    assert "(c) 2019" in reg.by_id["BSR-LU-03"]["draft_recommendation"]
    assert "CURRENT_OFFICIAL_WITNESS" not in reg.by_id["BSR-BA-03"]["draft_recommendation"]
    assert reg.by_id["BSR-BA-03"]["authority_tier"] == "OFFICIAL_EXPOSITION"                    # tier not changed
    for rid in ("BSR-RC-07", "BSR-LU-03", "BSR-BA-03"):
        assert reg.registry_overrides[rid]["applied"], rid


# ---------------------------------------------------------------- goal 3c: the Heidelberg chunker
class _HtmlFetcher:
    def __init__(self, html):
        self.html_ = html

    def get(self, url):
        class FR:
            ok = True; status = 200; error = ""; html = self.html_; final_url = url; redirects = []; cross_host_redirect = ""
        return FR()


def test_the_heidelberg_chunker_keeps_an_asterisked_heading():
    html = ("<html><body><h4>Lord’s Day 29</h4><div>Q &amp; A 79</div><p>Q. Why then does Christ call the bread his body?</p>"
            "<p>A. Christ has good reason for these words.</p><h4>Lord’s Day 30</h4><div>Q &amp; A 80*</div>"
            "<p>Q. How does the Lord’s Supper differ from the Roman Catholic Mass?</p><p>A. The Lord’s Supper declares to us.</p>"
            "<div>Q &amp; A 81</div><p>Q. Who should come to the Lord’s table?</p></body></html>")
    row = {"registry_id": "BSR-RP-05", "branch": "Reformed / Presbyterian", "standard_title": "Heidelberg Catechism", "authority_tier": "CONFESSIONAL",
           "scope_caveat": "", "reception_scope": "JURISDICTIONAL", "publisher_domain": "crcna.org",
           "canonical_url": "https://www.crcna.org/welcome/beliefs/confessions/heidelberg-catechism"}
    ctx = sources.Ctx(row, _HtmlFetcher(html), log=lambda m: None, admitted_hosts=["crcna.org"])
    out, _ = sources.heidelberg_crcna(ctx)
    locs = [c["locator"] for c in out]
    assert locs == ["Q&A 79 (Lord’s Day 29)", "Q&A 80 (Lord’s Day 30)", "Q&A 81 (Lord’s Day 30)"]
    assert "Roman Catholic Mass" not in out[0]["text"] and "Roman Catholic Mass" in out[1]["text"]
