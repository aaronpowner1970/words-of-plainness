"""The four packet-shape fixes adopted 2026-09-12 after the Roman Catholic packet, plus the two re-chunked rows.
Run: python -m pytest scripts/sjn_recovery/tests -q

  1a  witness rows sort LAST within an authority-tier tie (unit-tested here, since the fix is invisible on Anglican)
  1b  a controlling-language phrase is paired with its English witness on one card
  1c  the coder runs only on candidates the allocation keeps
  1d  the per-branch cost cap persists across invocations (cost-state.json)
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sjn_recovery.allocation import allocate, is_witness_like, translation_pairs  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import coststate, api_executor, sources  # noqa: E402


def _c(cid, rid, tier, witness=False, reception="UNIVERSAL", locator="", fallback=False):
    return {"candidate_id": cid, "registry_id": rid, "authority_tier": tier, "effective_tier": tier, "witness": witness,
            "reception_scope": reception, "locator": locator, "fallback_tier": fallback}


# ---------------------------------------------------------------- 1a
def test_witness_sorts_last_within_a_tier_tie():
    # the Roman Catholic defect: BSR-RC-03 (CONCILIAR (translation), TRANSLATION_WITNESS) led cells over BSR-RC-02 (CONCILIAR)
    w = _c("w", "BSR-RC-03", "CONCILIAR (translation)", witness=True, reception="TRANSLATION_WITNESS", locator="Chapter IV (English witness), paragraph 2")
    c = _c("c", "BSR-RC-02", "CONCILIAR", locator="Caput IV — De Fide Et Ratione")
    lower = _c("l", "BSR-RC-07", "CATECHETICAL", locator="Compendium Q.40")
    a = allocate([w, c, lower])                       # witness first in input order
    assert a["kept"] == ["c", "w", "l"], a
    assert a["roles"]["c"] == "PRIMARY" and a["corroborating_lower_tier"] == {"c": False, "w": False, "l": True}


def test_translation_marker_in_the_tier_alone_sorts_last():
    # a row marked "(translation)" in authority_tier sorts last even if no witness flag reached the candidate
    t = _c("t", "BSR-EO-13", "CONCILIAR (translation)", witness=False, reception="UNIVERSAL", locator="Definition of Faith (Session XVIII), paragraph 2")
    c = _c("c", "BSR-EO-06", "CONCILIAR", locator="Definition of Faith, Council of Chalcedon (451), paragraph 2")
    assert is_witness_like(t) and not is_witness_like(c)
    assert allocate([t, c])["kept"] == ["c", "t"]


def test_cap_is_filled_tier_by_tier_and_witness_never_displaces_a_lower_tier_witness():
    c1 = _c("c1", "BSR-RC-02", "CONCILIAR"); c2 = _c("c2", "BSR-RC-04", "CONCILIAR")
    w = _c("w", "BSR-RC-05", "CONCILIAR (translation)", witness=True, reception="TRANSLATION_WITNESS")
    k = _c("k", "BSR-RC-01", "CATECHETICAL")
    a = allocate([w, c1, c2, k])
    assert a["kept"] == ["c1", "c2", "k"] and a["dropped"]["w"].startswith("candidate cap")


# ---------------------------------------------------------------- 1b
PAIRS = {"BSR-RC-03": "BSR-RC-02", "BSR-RC-05": "BSR-RC-04"}


def test_english_witness_is_paired_onto_the_controlling_entry_by_chapter():
    la1 = _c("la1", "BSR-RC-02", "CONCILIAR", locator="Caput I — De Deo Rerum Omnium Creatore")
    la4 = _c("la4", "BSR-RC-02", "CONCILIAR", locator="Caput IV — De Fide Et Ratione")
    en1 = _c("en1", "BSR-RC-03", "CONCILIAR (translation)", witness=True, reception="TRANSLATION_WITNESS", locator="Chapter I (English witness), paragraph 1")
    q = _c("q", "BSR-RC-07", "CATECHETICAL", locator="Compendium Q.40")
    a = allocate([en1, la4, la1, q], PAIRS)
    assert a["kept"] == ["la4", "la1", "q"]
    assert a["english_witness"] == {"la1": "en1"} and a["roles"]["la1"] == "CONTROLLING" and a["roles"]["la4"] == "PRIMARY"
    assert a["dropped"]["en1"].startswith("paired as the English witness of la1")
    assert "en1" not in a["kept"] and a["witness_only"] == []


def test_witness_without_a_surviving_controlling_candidate_keeps_the_plain_witness_rules():
    en1 = _c("en1", "BSR-RC-03", "CONCILIAR (translation)", witness=True, reception="TRANSLATION_WITNESS", locator="Chapter I (English witness), paragraph 1")
    a = allocate([en1], PAIRS)
    assert a["kept"] == [] and a["witness_only"] == ["en1"] and a["dropped"]["en1"].startswith("WITNESS_ONLY")
    q = _c("q", "BSR-RC-07", "CATECHETICAL")
    b = allocate([en1, q], PAIRS)
    # unpaired (no BSR-RC-02 survivor): a plain witness under the plain rules — the tier governs before the witness
    # tie-break, so CONCILIAR (translation) still precedes CATECHETICAL, and the cell does not rest on it alone
    assert b["kept"] == ["en1", "q"] and b["english_witness"] == {} and b["witness_only"] == []


def test_witness_leads_only_within_its_own_tier_never_across_tiers():
    en1 = _c("en1", "BSR-RC-03", "CONCILIAR (translation)", witness=True, reception="TRANSLATION_WITNESS")
    q = _c("q", "BSR-RC-07", "CATECHETICAL")
    assert allocate([q, en1])["kept"] == ["en1", "q"]   # tier order is authority; the witness rule is a tie-break within the tier


def test_fallback_guard_runs_before_pairing_and_the_witness_only_guard():
    fb = _c("fb", "BSR-AN-05", "CATECHETICAL", fallback=True)
    c = _c("c", "BSR-AN-01", "CONFESSIONAL")
    a = allocate([fb, c])
    assert a["kept"] == ["c"] and a["dropped"]["fb"].startswith("fallback-tier")
    assert allocate([fb])["kept"] == ["fb"]


def test_translation_pairs_are_derived_from_the_live_registry():
    from sjn_recovery.registry import Registry
    try:
        reg = Registry()
    except Exception as e:
        pytest.skip(str(e))
    assert translation_pairs(reg, "Roman Catholic") == {"BSR-RC-03": "BSR-RC-02", "BSR-RC-05": "BSR-RC-04"}
    eo = translation_pairs(reg, "Eastern Orthodox")
    assert eo.get("BSR-EO-11") == "BSR-EO-06"          # named in its reception_note as the controlling text
    assert eo.get("BSR-EO-13") == "BSR-EO-06"          # shares the document name (Third Constantinople)
    assert translation_pairs(reg, "Anglican") == {}     # no witness rows: the fix is invisible on Anglican


# ---------------------------------------------------------------- 1c
class _FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies); self.calls = []; self.pending = []; self._cache = {}; self.run_id = "t"

    def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
        self.calls.append((role, meta))
        return self.replies.pop(0), {"call_id": f"c{len(self.calls)}"}


class _Reg:
    verifier_routing = "PRIMARY_ONLY"
    fallback_ids = set()

    def __init__(self, rows):
        self.by_id = rows

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return False

    def is_fallback(self, rid):
        return False

    def is_witness(self, rid):
        return self.by_id[rid].get("witness", False)

    def for_branch(self, branch, include_fallback=True, citable_only=True):
        return [dict(r, registry_id=k) for k, r in self.by_id.items()]

    def public(self, rid):
        r = self.by_id[rid]
        return {"standard_title": rid, "authority_tier": r["authority_tier"], "scope_caveat": "", "reception_scope": r.get("reception_scope", "UNIVERSAL"),
                "witness_only": r.get("witness", False)}

    def citation_refusal(self, rid):
        return None


def _accepted(cid, rid, tier, chunk="the Father almighty, maker of heaven and earth", witness=False):
    return {"candidate_id": cid, "pass": 1, "registry_id": rid, "locator": "L", "phrase": "maker of heaven and earth",
            "rationale": "r", "floor_claim": "FULL", "chunk_text": chunk, "chunk_hash": "h", "division": "d",
            "fallback_tier": False, "witness": witness, "effective_tier": tier, "locator_rank": 1}


def test_coder_runs_only_on_allocated_candidates(tmp_path):
    rows = {"BSR-RC-02": {"branch": "Roman Catholic", "authority_tier": "CONCILIAR", "standard_title": "Vatican I, *Dei Filius* (Latin, official)"},
            "BSR-RC-03": {"branch": "Roman Catholic", "authority_tier": "CONCILIAR (translation)", "witness": True, "reception_scope": "TRANSLATION_WITNESS",
                          "standard_title": "*Dei Filius* English (EWTN)"},
            "BSR-RC-01": {"branch": "Roman Catholic", "authority_tier": "CATECHETICAL", "standard_title": "Catechism"},
            "BSR-RC-07": {"branch": "Roman Catholic", "authority_tier": "CATECHETICAL", "standard_title": "Compendium"}}
    cands = [_accepted("a", "BSR-RC-03", "CONCILIAR (translation)", witness=True), _accepted("b", "BSR-RC-02", "CONCILIAR"),
             _accepted("c", "BSR-RC-01", "CATECHETICAL"), _accepted("d", "BSR-RC-07", "CATECHETICAL"), _accepted("e", "BSR-RC-01", "CATECHETICAL")]
    rub = {"model": "sonnet", "status": "DONE", "phrase_verbatim": "Y", "subject_is_required": "Y", "speech_act_is_assertion": "Y",
           "floor": "FULL", "hazard_flags": [], "verdict_model": "ACCEPT", "verdict": "ACCEPT", "reason_code_final": "OK"}
    st = {"queue_id": "Q-1", "branch": "Roman Catholic", "family_id": "RNR-H01", "predicate": "Creator",
          "passes": {"1": {"status": "DONE", "standards": list(rows), "candidates": cands, "dropped": [], "unslotted": []}},
          "verifications": {c["candidate_id"]: {"sonnet": dict(rub)} for c in cands}, "coding": {}, "phase": "coding",
          "routing": "PRIMARY_ONLY", "primary": "sonnet", "adjudicator": None, "slice_rows": []}
    os.makedirs(tmp_path, exist_ok=True)
    with open(os.path.join(tmp_path, "Q-1.json"), "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    coder_reply = json.dumps({"rendered_state": "A", "diverges_from_family_code": False, "state_reason": "r", "source_note": "n"})
    llm = _FakeLLM([coder_reply] * 10)
    preds = {"RNR-H01": {"family_id": "RNR-H01", "predicate": "Creator", "definition": "d", "floor_note": "f", "subject_scope": "GOD",
                         "family_code": "A", "lexical_floor": False, "mode": "m"}}
    r = CellRunner(llm, _Reg(rows), preds, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=True)
    r._pairs["Roman Catholic"] = {"BSR-RC-03": "BSR-RC-02"}
    out = r.run_cell({"queue_id": "Q-1", "branch": "Roman Catholic", "family_id": "RNR-H01", "predicate": "Creator"})
    coded = [m["candidate_id"] for role, m in llm.calls if role == "coder"]
    assert out["phase"] == "DONE" and len(out["survivors"]) == 5
    assert out["allocation"]["kept"] == ["b", "c", "d"], out["allocation"]     # a paired onto b; e cut by the cap
    assert sorted(coded) == ["b", "c", "d"], coded                             # 3 coder calls, not 5
    assert set(out["coder_skipped"]) == {"a", "e"} and out["allocation"]["english_witness"] == {"b": "a"}
    assert all(m.get("branch") == "Roman Catholic" for role, m in llm.calls)    # 1d: branch travels in the meta


# ---------------------------------------------------------------- 1d
def test_cost_state_survives_invocations_and_holds_the_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(coststate, "RUNS_DIR", str(tmp_path))
    # invocation 1: run.py registers the branch, the executor credits three calls
    s = coststate.load("t-run")
    coststate.register_branch(s, "Anglican", 1.0, ["Q-021", "Q-029"])
    coststate.save(s)
    s = coststate.load("t-run")
    for c in (0.3, 0.3, 0.2):
        coststate.credit(s, "Anglican", c); coststate.save(s)
    # invocation 2: a fresh process reads the file and resumes from 0.8, not 0
    s2 = coststate.load("t-run")
    b = s2["branches"]["Anglican"]
    assert b["spent_usd"] == 0.8 and b["calls"] == 3 and b["status"] == "RUNNING" and not coststate.over_cap(b)
    coststate.credit(s2, "Anglican", 0.25); coststate.save(s2)
    s3 = coststate.load("t-run")
    b = s3["branches"]["Anglican"]
    assert b["spent_usd"] == 1.05 and b["status"] == "CAP_HIT" and coststate.over_cap(b) and b["cap_hit_at"]
    # the executor skips a capped branch's jobs and answers the others
    assert api_executor.branch_for_job(s3, {"meta": {"queue_id": "Q-029"}}) == "Anglican"
    assert api_executor.branch_for_job(s3, {"meta": {"branch": "Anglican", "queue_id": "Q-021"}}) == "Anglican"
    assert api_executor.branch_for_job(s3, {"meta": {"queue_id": "PNM-001"}}) is None
    assert api_executor.branch_capped(s3, "Anglican") and not api_executor.branch_capped(s3, None)
    coststate.credit(s3, None, 0.5)                    # a planted item: charged to `unassigned`, never capped
    assert s3["unassigned"]["spent_usd"] == 0.5 and s3["branches"]["Anglican"]["spent_usd"] == 1.05
    # the audit log can only raise the counter, never lower it
    coststate.reconcile(s3, "Anglican", 0.9, 2)
    assert s3["branches"]["Anglican"]["spent_usd"] == 1.05
    coststate.reconcile(s3, "Anglican", 1.2, 5)
    assert s3["branches"]["Anglican"]["spent_usd"] == 1.2 and s3["branches"]["Anglican"]["calls"] == 5
    # the author raises the cap: the branch may continue
    coststate.register_branch(s3, "Anglican", 5.0, ["Q-021", "Q-029"])
    assert s3["branches"]["Anglican"]["status"] == "RUNNING" and not coststate.over_cap(s3["branches"]["Anglican"])
    assert os.path.exists(os.path.join(str(tmp_path), "t-run", "cost-state.json"))


# ---------------------------------------------------------------- the two re-chunked rows (adapters, offline)
class _RenderedFetcher:
    def __init__(self, blocks):
        self.blocks = blocks

    def rendered(self, url):
        class FR:
            ok = True; status = 200; error = ""
            rendered = {"blocks": self.blocks, "body": " ".join(b["text"] for b in self.blocks)}
        return FR()


class _HtmlFetcher:
    def __init__(self, html):
        self.html_ = html

    def get(self, url):
        class FR:
            ok = True; status = 200; error = ""; html = self.html_; final_url = url; redirects = []; cross_host_redirect = ""
        return FR()


def test_an03_rendered_adapter_chunks_only_the_creed_and_asserts_the_opening():
    blocks = ([{"tag": "h1", "text": "At Morning Prayer"}, {"tag": "p", "text": "Upon these Feasts; Christmas Day, ..."},
               {"tag": "h3", "text": "QUICUNQUE VULT"},
               {"tag": "p", "text": "WHOSOEVER will be saved: before all things it is necessary that he hold the Catholick Faith."}]
              + [{"tag": "p", "text": f"Verse {i} of the creed, the Father eternal, the Son eternal: and the Holy Ghost eternal."} for i in range(2, 44)]
              + [{"tag": "p", "text": "Glory be to the Father, and to the Son: and to the Holy Ghost;"},
                 {"tag": "p", "text": "As it was in the beginning, is now, and ever shall be: world without end. Amen."},
                 {"tag": "p", "text": "Text from The Book of Common Prayer, the rights in which are vested in the Crown, is reproduced by permission."},
                 {"tag": "h4", "text": "Join us in Daily Prayer"}, {"tag": "p", "text": "Find Morning, Evening and Night Prayer"}])
    row = {"registry_id": "BSR-AN-03", "branch": "Anglican", "standard_title": "Athanasian Creed (Quicunque Vult), BCP", "authority_tier": "CONFESSIONAL",
           "scope_caveat": "", "reception_scope": "JURISDICTIONAL", "publisher_domain": "churchofengland.org",
           "canonical_url": "https://www.churchofengland.org/prayer-and-worship/worship-texts-and-resources/book-common-prayer/creed-s-athanasius"}
    ctx = sources.Ctx(row, _RenderedFetcher(blocks), log=lambda m: None, admitted_hosts=["churchofengland.org"])
    chunks, notes = sources.athanasian_creed_cofe(ctx)
    assert len(chunks) == 1 and ctx.urls[0]["mode"] == "rendered"
    t = chunks[0]["text"]
    assert "Upon these Feasts" not in t and "Text from The Book of Common Prayer" not in t and "Join us" not in t
    assert t.startswith("WHOSOEVER will be saved") and t.endswith("world without end. Amen.")
    from sjn_recovery import guards
    ok, why = guards.check_phrase(sources.AN03_ASSERT, t)
    assert ok, why


def test_an03_adapter_refuses_chrome_only_render():
    row = {"registry_id": "BSR-AN-03", "branch": "Anglican", "standard_title": "x", "authority_tier": "x", "scope_caveat": "",
           "canonical_url": "https://www.churchofengland.org/x", "publisher_domain": "churchofengland.org"}
    ctx = sources.Ctx(row, _RenderedFetcher([{"tag": "h1", "text": "Book of Common Prayer"}, {"tag": "li", "text": "Menu"}]), log=lambda m: None,
                      admitted_hosts=["churchofengland.org"])
    with pytest.raises(sources.FetchError):
        sources.athanasian_creed_cofe(ctx)


def test_rc08_adapter_keeps_the_two_creeds_apart():
    html = ("<html><body><h1>Credo</h1><b>The Apostles' Creed</b><p>I believe in God the Father almighty,</p><p>Creator of heaven and earth.</p>"
            "<p>to judge the living and the dead.</p><p>Amen.</p><b>The Nicene Creed</b><p>I believe in one God,</p><p>maker of heaven and earth,</p>"
            "<p>begotten, not made, consubstantial with the Father;</p><p>to judge the living and the dead</p><p>Amen.</p>"
            "<span>Your contribution for a great mission:</span></body></html>")
    row = {"registry_id": "BSR-RC-08", "branch": "Roman Catholic", "standard_title": "Apostles' and Nicene Creeds (Credo), Vatican News prayer text",
           "authority_tier": "CONFESSIONAL (row floor; Nicene resolves CONCILIAR)", "scope_caveat": "", "reception_scope": "UNIVERSAL",
           "publisher_domain": "vaticannews.va", "canonical_url": "https://www.vaticannews.va/en/prayers/the-apostles_-creed.html"}
    ctx = sources.Ctx(row, _HtmlFetcher(html), log=lambda m: None, admitted_hosts=["vaticannews.va"])
    chunks, notes = sources.vaticannews_creeds(ctx)
    by = {c["locator"]: c["text"] for c in chunks}
    assert set(by) == {"Apostles' Creed", "Nicene Creed"}
    assert "consubstantial" in by["Nicene Creed"] and "consubstantial" not in by["Apostles' Creed"]
    assert "judge the living and the dead" in by["Apostles' Creed"] and "judge the living and the dead" in by["Nicene Creed"]
    assert "Your contribution" not in by["Nicene Creed"]
