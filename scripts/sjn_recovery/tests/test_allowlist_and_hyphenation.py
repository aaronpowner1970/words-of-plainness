"""R001 parser rule (publisher_domain only; AC-15 controlled storage), retired hosts, de-hyphenation at
extraction, and the shorten-to-fit re-cut (2026-09-12). Run: python -m pytest scripts/sjn_recovery/tests -q"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sjn_pipeline.registry import (admission, admitted_domains, legacy_admitted_domains, branch_domain_index,  # noqa: E402
                                   resolve_row, is_controlled_storage_host, linked_from_url)
from sjn_recovery.textutil import dehyphenate, hyphenation_residue  # noqa: E402
from sjn_recovery import sources, guards  # noqa: E402
from sjn_recovery.agents import legal_spans, CellRunner  # noqa: E402

POLICY = {"controlled_storage_policy": "ADMIT_IF_LINKED_FROM_OFFICIAL_DOMAIN"}


def _row(rid, branch, pub, url="", title="", note="", author_note=""):
    return {"registry_id": rid, "branch": branch, "status": "AUTHOR_RATIFIED", "publisher_domain": pub, "canonical_url": url,
            "standard_title": title, "reception_note": note, "author_note": author_note, "authority_tier": "CONFESSIONAL", "reception_scope": "UNIVERSAL"}


# ---------------------------------------------------------------- R001 parser rule
def test_prose_hosts_are_never_admitted():
    rc06 = _row("BSR-RC-06", "Roman Catholic", "vatican.va", "https://www.vatican.va/archive/ENG0015/__P13.HTM",
                "Creeds as received (Apostles', Nicene, Athanasian) on vatican.va / vaticannews.va")
    an03 = _row("BSR-AN-03", "Anglican", "ccel.org", 'ccel.org as cited (1 released cell); official: churchofengland.org BCP "At Morning Prayer"')
    rc04 = _row("BSR-RC-04", "Roman Catholic", "papalencyclicals.net", "https://www.papalencyclicals.net/councils/ecum12-2.htm (not on vatican.va)")
    for row, prose_host in ((rc06, "vaticannews.va"), (an03, "churchofengland.org"), (rc04, "vatican.va")):
        assert prose_host in legacy_admitted_domains(row)[1], "the retired parser admitted the prose host"
        primary, extra = admitted_domains(row, POLICY)
        assert primary == row["publisher_domain"] and extra == [], "the current rule admits publisher_domain only"


def test_ac15_controlled_storage_requires_the_prefix_and_the_policy():
    mw03 = _row("BSR-MW-03", "Methodist / Wesleyan", "irp.cdn-website.com",
                "https://irp.cdn-website.com/1876eae9/files/uploaded/2024-Book-of-Doctrines-Discipline-FINAL-15JAN2025.pdf",
                note="LINKED FROM: https://www.globalmethodist.org/our-beliefs---governance - the church's official page")
    assert is_controlled_storage_host("irp.cdn-website.com") and not is_controlled_storage_host("globalmethodist.org")
    assert linked_from_url(mw03) == "https://www.globalmethodist.org/our-beliefs---governance"
    a = admission(mw03, POLICY)
    assert not a["refused"] and a["primary"] == "irp.cdn-website.com" and a["extra"] == ["globalmethodist.org"] and a["kind"] == "controlled_storage"
    # absent the prefix: refused
    no_prefix = dict(mw03, reception_note="Admitted under the controlled-storage ruling; linked from https://www.globalmethodist.org/x")
    assert admission(no_prefix, POLICY)["refused"] and admitted_domains(no_prefix, POLICY) == ("", [])
    # prefix present but not opening the note: refused
    buried = dict(mw03, reception_note="See LINKED FROM: https://www.globalmethodist.org/x")
    assert admission(buried, POLICY)["refused"]
    # the policy key absent or different: refused
    assert admission(mw03, {})["refused"] and admission(mw03, {"controlled_storage_policy": "REFUSE"})["refused"]
    # LINKED FROM naming another storage host, or the storage host itself: refused
    assert admission(dict(mw03, reception_note="LINKED FROM: https://x.blob.core.windows.net/a"), POLICY)["refused"]
    assert admission(dict(mw03, reception_note="LINKED FROM: https://irp.cdn-website.com/a"), POLICY)["refused"]
    # an ordinary row is untouched by AC-15 even with the prefix
    plain = _row("BSR-X", "Anglican", "churchofengland.org", note="LINKED FROM: https://example.org/")
    assert admission(plain, POLICY) == {"primary": "churchofengland.org", "extra": [], "kind": "primary", "refused": False, "reason": "", "linked_from": None}


def test_branch_index_resolves_only_admitted_hosts():
    rows = [_row("BSR-RC-06", "Roman Catholic", "vatican.va", title="Creeds on vatican.va / vaticannews.va"),
            _row("BSR-MW-03", "Methodist / Wesleyan", "irp.cdn-website.com", note="LINKED FROM: https://www.globalmethodist.org/our-beliefs---governance"),
            _row("BSR-MW-09", "Methodist / Wesleyan", "files.example-cdn.amazonaws.com", note="no prefix")]
    idx = branch_domain_index(rows, POLICY)
    assert resolve_row(idx, "Roman Catholic", "https://www.vaticannews.va/en/prayers/the-apostles_-creed.html")[0] is None
    assert resolve_row(idx, "Roman Catholic", "https://www.vatican.va/archive/ENG0015/__P13.HTM")[1] == "BSR-RC-06"
    assert resolve_row(idx, "Methodist / Wesleyan", "https://irp.cdn-website.com/1876eae9/files/uploaded/x.pdf")[:2] == ("controlled_storage", "BSR-MW-03")
    assert resolve_row(idx, "Methodist / Wesleyan", "https://www.globalmethodist.org/our-beliefs---governance")[:2] == ("official_link", "BSR-MW-03")
    assert "files.example-cdn.amazonaws.com" not in idx["Methodist / Wesleyan"]


def test_live_registry_allowlist_if_present():
    from sjn_recovery.registry import Registry
    try:
        reg = Registry()
    except Exception as e:
        pytest.skip(str(e))
    assert reg.domains("BSR-RC-06") == ["vatican.va"]
    assert reg.domains("BSR-AN-03") == ["ccel.org"]
    assert reg.domains("BSR-MW-03") == ["irp.cdn-website.com", "globalmethodist.org"]
    assert reg.domains("BSR-EO-13") == ["newadvent.org"]


# ---------------------------------------------------------------- retired hosts and the host guard
class _Fetcher:
    def get(self, url):
        raise AssertionError(f"a retired or non-admitted host was requested: {url}")

    def rendered(self, url):
        raise AssertionError(f"a retired or non-admitted host was requested: {url}")


def test_retired_host_is_never_requested():
    assert sources.retired_host("https://www.goarch.org/-/the-divine-liturgy-of-saint-john-chrysostom")
    assert sources.retired_host("https://goarch.org/x") and sources.retired_host("https://www.sf.goarch.org/x")
    assert sources.retired_host("https://goarchdiocese.ca/divine-liturgy-of-saint-john-chrysostom/") is None
    assert sources.retired_host("https://www.acrod.org/prayercorner/liturgicaltexts/divineliturgy") is None
    ctx = sources.Ctx({"registry_id": "BSR-EO-03", "branch": "Eastern Orthodox", "standard_title": "x", "authority_tier": "x", "scope_caveat": "",
                       "canonical_url": "https://www.goarch.org/-/x", "publisher_domain": "goarch.org"}, _Fetcher(), log=lambda m: None,
                      admitted_hosts=["goarch.org"])
    with pytest.raises(sources.RetiredHostError):
        ctx.html("https://www.goarch.org/-/x")


def test_host_guard_refuses_a_host_the_row_does_not_admit():
    ctx = sources.Ctx({"registry_id": "BSR-AN-03", "branch": "Anglican", "standard_title": "x", "authority_tier": "x", "scope_caveat": "",
                       "canonical_url": "ccel.org as cited", "publisher_domain": "ccel.org"}, _Fetcher(), log=lambda m: None, admitted_hosts=["ccel.org"])
    with pytest.raises(sources.HostNotAdmittedError):
        ctx.html("https://www.churchofengland.org/prayer-and-worship/x")
    with pytest.raises(sources.HostNotAdmittedError):
        ctx.rendered("https://www.churchofengland.org/prayer-and-worship/x")
    assert "BSR-AN-03" in sources.ADAPTERS and sources.ADAPTERS["BSR-AN-03"] is sources.athanasian_creed_ccel
    assert sources.ADAPTERS["BSR-EO-07"] is sources.acrod_liturgy and "BSR-EO-13" in sources.ADAPTERS and "BSR-EO-14" in sources.ADAPTERS
    assert sources.ADAPTERS["BSR-MW-03"] is sources.gmc_bdd_2024


# ---------------------------------------------------------------- de-hyphenation
def test_dehyphenate_joins_line_break_splits_and_keeps_suspended_hyphens():
    doc = ("THERE is but one living and true God, ever- lasting, without body, parts, or passions; "
           "begotten from everlasting of the Father. Vaults, wine- and beer-cellars; patres- et matresfamilias. "
           "holy, good and life-\ncreating Spirit; the life-creating Cross; heav-\nenly gifts; our na-\nture is; "
           "Thirty- Nine Articles; the opin- ion of St Augustine.")
    st = {}
    out = dehyphenate(doc, stats=st)
    assert "God, everlasting, without" in out                # closed form elsewhere in the document
    assert "life-creating Spirit" in out                      # hyphenated compound elsewhere: hyphen kept
    assert "heavenly gifts" in out and "our nature is" in out and "the opinion of" in out   # default: join
    assert "wine- and beer-cellars" in out and "patres- et matresfamilias" in out          # suspended hyphens kept
    assert "Thirty- Nine" in out                              # capital continuation: never touched
    assert st == {"joined_closed": 1, "joined_compound": 1, "joined_default": 3, "suspended_kept": 2}
    assert hyphenation_residue(out) == []


def test_dehyphenate_chunks_recomputes_hash_and_keeps_synodikon_spans_consistent():
    from sjn_recovery.textutil import sha
    chunks = [{"registry_id": "BSR-AN-01", "locator": "Article I", "text": "one living and true God, ever- lasting, without body", "text_hash": "old"},
              {"registry_id": "BSR-AN-01", "locator": "Article II", "text": "begotten from everlasting of the Father", "text_hash": sha("begotten from everlasting of the Father")}]
    rep = sources.dehyphenate_chunks(chunks)
    assert chunks[0]["text"] == "one living and true God, everlasting, without body" and chunks[0]["text_hash"] == sha(chunks[0]["text"])
    assert rep["changed"] == 1 and rep["residue"] == []
    ok, why = guards.check_phrase("one living and true God, everlasting", chunks[0]["text"])
    assert ok, why
    syn = [{"registry_id": "BSR-EO-09", "locator": "§3", "text": "This is the Faith. [withheld] the ever- lasting God", "text_hash": "x",
            "full_text": "This is the Faith. To those who deny the ever- lasting God: ANATHEMA!",
            "noncitable_spans": [{"kind": "anathema", "text": "To those who deny the ever- lasting God: ANATHEMA!"}]},
           {"registry_id": "BSR-EO-09", "locator": "§2", "text": "the everlasting Kingdom", "text_hash": "y"}]
    sources.dehyphenate_chunks(syn)
    assert "everlasting God" in syn[0]["text"] and "everlasting God" in syn[0]["noncitable_spans"][0]["text"] and "everlasting God" in syn[0]["full_text"]
    ok, why = guards.check_noncitable("deny the everlasting God", syn[0])
    assert not ok and "ANATHEMA_SPAN" in why


# ---------------------------------------------------------------- shorten-to-fit re-cut
LONG = ("There is but one living and true God, everlasting, without body or parts, of infinite power, wisdom, and goodness; "
        "the maker and preserver of all things, both visible and invisible.")
SIXTEEN = "one living and true God, everlasting, without body or parts, of infinite power, wisdom, and goodness"


def test_legal_spans_are_verbatim_and_within_limit():
    spans = legal_spans(SIXTEEN + " the maker of all")
    assert spans and all(len(s.split()) <= 15 for s in spans)
    src = (SIXTEEN + " the maker of all").split()
    for sp in spans:
        ws = sp.split()
        assert any(src[i:i + len(ws)] == ws for i in range(len(src))), sp
    assert spans == sorted(spans, key=lambda x: (len(x.split()), x))


class _FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies); self.calls = []; self.pending = []

    def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
        self.calls.append((role, user))
        out = self.replies.pop(0)
        return out, {"call_id": f"c{len(self.calls)}"}


class _FakeReg:
    verifier_routing = "PRIMARY_ONLY"

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return False

    def is_fallback(self, rid):
        return False


def _runner(replies, tmp_path):
    return CellRunner(_FakeLLM(replies), _FakeReg(), {}, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)


PRED = {"family_id": "RNR-H08", "predicate": "Wise / all-wise", "definition": "d", "subject_scope": "GOD"}
CHUNK = {"registry_id": "BSR-MW-01", "locator": "Article I", "text": LONG, "text_hash": "h"}
CAND = {"chunk_key": "c1", "registry_id": "BSR-MW-01", "locator": "Article I", "phrase": LONG, "rationale": "r", "floor_claim": "FULL"}


def test_recut_shortens_on_the_second_attempt(tmp_path):
    import json
    r = _runner([json.dumps({"phrase": SIXTEEN, "rationale": "r", "floor_claim": "FULL"}),
                 json.dumps({"phrase": "one living and true God, everlasting, without body or parts, of infinite power, wisdom", "rationale": "r", "floor_claim": "FULL"})], tmp_path)
    status, new, raw, too_long = r._recut({"queue_id": "Q-063", "branch": "Methodist / Wesleyan", "family_id": "RNR-H08"}, PRED, CAND, CHUNK, "c1", "BSR-MW-01", 1)
    assert status == "DONE" and new["recut_attempts"] == 2 and too_long == [SIXTEEN]
    assert len(new["phrase"].split()) <= 15 and new["recut_from"] == LONG
    ok, why = guards.check_phrase(new["phrase"], CHUNK["text"])
    assert ok, why
    assert "your_re_cuts_so_far_still_too_long" in r.llm.calls[1][1] and "its_word_count" in r.llm.calls[0][1]


def test_recut_offers_legal_spans_on_the_third_attempt_and_drops_only_when_nothing_fits(tmp_path):
    import json
    r = _runner([json.dumps({"phrase": SIXTEEN, "rationale": "r", "floor_claim": "FULL"}),
                 json.dumps({"phrase": SIXTEEN, "rationale": "r", "floor_claim": "FULL"}),
                 json.dumps({"phrase": "of infinite power, wisdom, and goodness;", "rationale": "r", "floor_claim": "FULL"})], tmp_path)
    status, new, raw, too_long = r._recut({"queue_id": "Q-071", "branch": "Methodist / Wesleyan", "family_id": "RNR-H08"}, PRED, CAND, CHUNK, "c1", "BSR-MW-01", 1)
    assert status == "DONE" and new["recut_attempts"] == 3 and "spans_of_your_earlier_phrase_that_fit_15_words" in r.llm.calls[2][1]
    r2 = _runner([json.dumps({"phrase": SIXTEEN, "rationale": "r", "floor_claim": "FULL"})] * 3, tmp_path)
    status, new, raw, too_long = r2._recut({"queue_id": "Q-071", "branch": "Methodist / Wesleyan", "family_id": "RNR-H08"}, PRED, CAND, CHUNK, "c1", "BSR-MW-01", 1)
    assert status == "STILL_TOO_LONG" and new is None and len(too_long) == 3
    r3 = _runner([json.dumps({"result": "NO_VALID_CUT"})], tmp_path)
    status, new, raw, too_long = r3._recut({"queue_id": "Q-071", "branch": "Methodist / Wesleyan", "family_id": "RNR-H08"}, PRED, CAND, CHUNK, "c1", "BSR-MW-01", 1)
    assert status == "NO_VALID_CUT" and new is None
