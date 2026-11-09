"""Tests for AOID2 step 209 (CODE-AOID2-116): the Broken Vessels study, section "The Doctrine and the Ministry"
(id="doctrine-and-ministry"), corrected to the wording Aaron approved on 9 Nov 2026 (CHAT-AOID2-114a, option 1;
AOID2 step 208).

Paragraph 1 names Article 10 by its title, "Of Living by Grace". Paragraph 2 is replaced whole: Article 8 is
"Of Fellow Believers", Article 9 "Of Finding Our Way" takes the place of the non-existent "Article 12, Of the
Restoration", and "Of Covenants and Commitments" is Article 11, not Article 13. Articles 2-13 carry the same numbers
in both editions, so the page reads the same with the Second Edition switch OFF and ON.

Run: python -m pytest scripts/aoid_tests/test_step209.py
"""
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "pages" / "studies" / "broken-vessels.njk"
PAGE = "studies/broken-vessels/index.html"

# Copied from the approved-wording file (WoP_AOID2_Step208_BrokenVessels_ApprovedWording_20261109.md), not retyped.
APPROVED_P2 = "The doctrine resonates beyond Article 10. Article 8, <em>Of Fellow Believers</em>, names the unilateral fellowship the church is called to extend across institutional differences &mdash; and that fellowship is possible only because no institution is the foundation of any disciple's salvation. Article 9, <em>Of Finding Our Way</em>, holds that the disciple's walk does not require the approval of any person, tradition, or institution beyond the approval of Christ Himself. Article 11, <em>Of Covenants and Commitments</em>, names the disciple's covenant relationship with God Himself rather than with any structure that claims Him."
P1_TITLE = "Article 10, <em>Of Living by Grace</em>"
GONE = ("Of the Restoration", "Of Our Fellow Believers", "Article 13, <em>Of Covenants")


def build(out, on):
    env = {k: v for k, v in os.environ.items() if k not in ("WOP_AOID2_SECOND_EDITION", "WOP_AOID2_BUILD_REVIEW")}
    if on:
        env["WOP_AOID2_SECOND_EDITION"] = "1"
    r = subprocess.run(["npx", "@11ty/eleventy", f"--output={Path(out).as_posix()}"], cwd=REPO, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", shell=(os.name == "nt"))
    assert r.returncode == 0, r.stderr[-2000:] + r.stdout[-1000:]


@pytest.fixture(scope="module")
def site_off(tmp_path_factory):
    out = tmp_path_factory.mktemp("off")
    build(out, False)
    return out


@pytest.fixture(scope="module")
def site_on(tmp_path_factory):
    out = tmp_path_factory.mktemp("on")
    build(out, True)
    return out


def section(html):
    start = html.index('id="doctrine-and-ministry"')
    return html[start:html.index("</section>", start)]


def check(html):
    sec = section(html)
    assert '<p class="study-prose">' + APPROVED_P2 + "</p>" in sec
    assert P1_TITLE + "," in sec
    assert "<em>Living by Grace</em>" not in sec
    for gone in GONE:
        assert gone not in html, gone


def test_source_carries_the_approved_wording():
    check(SRC.read_text(encoding="utf-8"))


def test_built_page_off(site_off):
    check((site_off / PAGE).read_text(encoding="utf-8"))


def test_built_page_on(site_on):
    check((site_on / PAGE).read_text(encoding="utf-8"))
