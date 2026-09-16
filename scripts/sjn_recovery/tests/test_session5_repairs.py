"""Session 5 (2026-09-13): NO TEXT blocks REVIEWED; the www-label redirect rule; PDF magic-byte sniffing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.packets import empty_result_option, no_text_rows  # noqa: E402
from sjn_recovery.config import EMPTY_RESULT, EMPTY_RESULT_INCOMPLETE  # noqa: E402
from sjn_pipeline.fetch import www_label_only  # noqa: E402


class _Reg:
    def __init__(self, fallback=()):
        self.fb = set(fallback)

    def is_fallback(self, rid):
        return rid in self.fb


def _rows(*rids):
    return [{"registry_id": r} for r in rids]


def _st(cov, no_corpus=(), passes=("1",)):
    ps = {pk: {"per_standard": {r: {"status": "NO_CORPUS"} for r in no_corpus}} for pk in passes}
    return {"coverage_final": cov, "passes": ps}


FULL = {"coverage": "FULL", "supplied": 21, "of": 21}


def test_a_row_with_no_text_blocks_reviewed_like_a_sampled_row():
    cov = {"BSR-BA-01": FULL, "BSR-BA-03": {"coverage": "FULL", "supplied": 10, "of": 10}}
    manifest = {"BSR-BA-02": {"status": "HOST_REDIRECTS_CROSS_HOST", "notes": ["301 onto www"]}}
    nt, _nc = no_text_rows(_st(cov, no_corpus=["BSR-BA-02"]), _rows("BSR-BA-01", "BSR-BA-02", "BSR-BA-03"), _Reg(), manifest, card_empty=True)
    assert [x["registry_id"] for x in nt] == ["BSR-BA-02"] and "NO_CORPUS" in nt[0]["reason"]
    e = empty_result_option(cov, {}, no_text=nt)
    assert e["offered"] is False and e["rendered_state"] is None and e["honest_state_if_not_offered"] == EMPTY_RESULT_INCOMPLETE
    assert e["review_incomplete"] == ["BSR-BA-02"]
    by = {r["registry_id"]: r for r in e["standards_reviewed"]}
    assert by["BSR-BA-02"]["status"] == "NO TEXT" and by["BSR-BA-02"]["manifest_status"] == "HOST_REDIRECTS_CROSS_HOST"
    assert "BSR-BA-02 supplied no text" in e["why_not_offered"]
    assert empty_result_option(cov, {}, no_text=[])["rendered_state"] == EMPTY_RESULT


def test_a_row_built_after_the_cell_ran_is_still_no_text_on_that_card():
    # the manifest now has a hash (corpus built later), but the cell's coverage never saw the row
    manifest = {"BSR-RC-08": {"status": "BUILT", "text_hash": "abc"}}
    nt, _nc = no_text_rows(_st({"BSR-RC-01": FULL}), _rows("BSR-RC-01", "BSR-RC-08"), _Reg(), manifest, card_empty=False)
    assert [x["registry_id"] for x in nt] == ["BSR-RC-08"] and "never supplied" in nt[0]["reason"]


def test_a_fallback_row_counts_only_on_an_empty_card_or_where_pass_two_ran():
    rows, reg = _rows("BSR-AN-01", "BSR-AN-05"), _Reg(fallback=["BSR-AN-05"])
    st = _st({"BSR-AN-01": FULL})
    assert no_text_rows(st, rows, reg, {}, card_empty=False) == ([], [])
    assert [x["registry_id"] for x in no_text_rows(st, rows, reg, {}, card_empty=True)[0]] == ["BSR-AN-05"]


def test_a_card_that_consulted_nothing_offers_nothing():
    e = empty_result_option({}, {}, no_text=[])
    assert e["offered"] is False and "no standard was consulted" in e["why_not_offered"]


def test_www_label_only_redirect_rule():
    ok = [("https://the1689confession.com/1689/chapter-2", "https://www.the1689confession.com/1689/chapter-2"),
          ("https://www.example.org/a?x=1", "https://example.org/a?x=1"),
          ("http://the1689confession.com/1689/chapter-2", "https://www.the1689confession.com/1689/chapter-2")]
    refused = [("https://the1689confession.com/1689/chapter-2", "https://www.the1689confession.com/1689/"),        # path changed
               ("https://globalmethodist.org/x", "https://www.globalmethodist.org/y"),                               # path changed
               ("https://lcms.org/a", "https://files.lcms.org/a"),                                                   # another label
               ("https://www.example.org/a", "http://example.org/a"),                                                # https -> http
               ("https://example.org/a", "https://www.example.com/a"),                                               # another domain
               ("https://example.org/a", "https://www.example.org/a?x=1"),                                           # query changed
               ("https://archive.org/download/x", "https://dn720.eu.archive.org/download/x"),                        # CDN hop
               ("https://example.org/a", "https://example.org/a")]                                                   # not a host change
    assert all(www_label_only(a, b) for a, b in ok)
    assert not any(www_label_only(a, b) for a, b in refused)
