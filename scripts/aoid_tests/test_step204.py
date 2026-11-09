"""Tests for AOID2 step 204 (CODE-AOID2-114): the fixes Aaron ruled on 9 Nov 2026 (CHAT-AOID2-114a) in his review
of the CODE-AOID2-73 report.

Ruling 3a: the two A14 s12 Alma anchor comments end at "prepared by an angel."; the scope note's
"; the pairing with Hebrews 13:2" is a note to the apparatus, not a gloss. D&C 124:22-24 is unchanged.
Ruling 3b: the A14 s9 Articles of Faith 1:13 comment ends with an ellipsis inside its quotation marks.
Ruling 6: with the Second Edition switch ON, the two lines that describe the podcasts (the Learning Pathways card
description and the podcast modal label) carry the same "First Edition" tag as the Plainness Edition PDF link;
with the switch OFF they are unchanged.
Ruling 8: the Second Edition copy of the progress script may differ from src/js/articles-progress.js only in its
Prologue logic (the data-prologue handling and the header comment).

Run: python -m pytest scripts/aoid_tests/test_step204.py
"""
import difflib
import functools
import http.server
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
DATA = json.loads((REPO / "src" / "_data" / "apparatusData.json").read_text(encoding="utf-8"))

ALMA = "Amulek receives the hungry stranger into his house, prepared by an angel."
ALMA_OLD_CLAUSE = "; the pairing with Hebrews 13:2"
NAUVOO = 'the Nauvoo House, "that strangers may come from afar to lodge therein"'
AOF_1_13 = '"We believe in being honest, true…"'
DC_64 = '"of you it is required to forgive all men"'

TAG = '<span class="an-edition-tag">First Edition</span>'
CARD_DESC = ("Dramatized interfaith conversations covering all thirteen articles in three short podcast episodes. "
             "Based on real ministry experiences.")
POD_LABEL = "A dramatized companion &middot; the thirteen Articles as lived conversation"

FE_JS = REPO / "src" / "js" / "articles-progress.js"
SE_JS = REPO / "src" / "aoid-second-edition" / "articles-progress.js"


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


def read(site, rel):
    return (site / rel).read_text(encoding="utf8")


def restoration_anchor(span, ref):
    hits = [a for a in DATA["A14"][span]["restoration"] if a["ref"] == ref]
    assert len(hits) == 1, (span, ref, len(hits))
    return hits[0]


def embedded_comment(text):
    """The apparatus is embedded in the page as indented JSON; this is how one comment field reads there."""
    return '"comment": ' + json.dumps(text, ensure_ascii=False)


# ---------------------------------------------------------------- ruling 3a: the Alma comments
def test_alma_comments_trimmed_in_the_data():
    assert restoration_anchor("s12", "Alma 8:19–21")["comment"] == ALMA
    assert restoration_anchor("s12", "Alma 10:7–9")["comment"] == ALMA
    assert restoration_anchor("s12", "D&C 124:22–24")["comment"] == NAUVOO  # unchanged, lowercase "the" kept
    for sid, s in DATA["A14"].items():
        for col in ("biblical", "restoration"):
            for a in s[col]:
                assert ALMA_OLD_CLAUSE not in a["comment"], (sid, a["ref"])


def test_alma_comments_trimmed_in_the_on_build(site_on):
    page = read(site_on, "articles/index.html")
    assert page.count(embedded_comment(ALMA)) >= 2  # both Alma anchors
    assert ALMA_OLD_CLAUSE not in page
    assert embedded_comment(NAUVOO) in page


# ---------------------------------------------------------------- ruling 3b: Articles of Faith 1:13
def test_articles_of_faith_comment_ends_with_an_ellipsis_in_the_data():
    assert restoration_anchor("s9", "Articles of Faith 1:13")["comment"] == AOF_1_13
    assert restoration_anchor("s8", "D&C 64:9–10")["comment"] == DC_64  # unchanged


def test_articles_of_faith_comment_in_the_on_build(site_on):
    page = read(site_on, "articles/index.html")
    assert embedded_comment(AOF_1_13) in page
    assert embedded_comment('"We believe in being honest, true."') not in page


def test_off_build_carries_no_a14_comment(site_off):
    page = read(site_off, "articles/index.html")
    assert "Amulek receives" not in page and embedded_comment(AOF_1_13) not in page


# ---------------------------------------------------------------- ruling 6: First Edition tags on the podcast lines
def test_podcast_lines_tagged_on(site_on):
    page = read(site_on, "articles/index.html")
    assert f'<span class="pw-card-desc">{CARD_DESC} {TAG}</span>' in page
    assert f'<p class="pod-label">{POD_LABEL} {TAG}</p>' in page


def test_podcast_lines_unchanged_off(site_off):
    page = read(site_off, "articles/index.html")
    assert f'<span class="pw-card-desc">{CARD_DESC}</span>' in page
    assert f'<p class="pod-label">{POD_LABEL}</p>' in page
    assert "an-edition-tag" not in page


def serve(site):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_podcast_tags_show_and_are_not_hidden_from_assistive_tech_on(site_on):
    srv = serve(site_on)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/articles/")
            card = pg.locator("#pwListen .pw-card-desc .an-edition-tag")
            assert card.count() == 1
            card.scroll_into_view_if_needed()
            assert card.is_visible() and card.text_content() == "First Edition"
            pg.click("#pwListen")
            pg.wait_for_selector("#podModal.open")
            label = pg.locator("#podModal .pod-label .an-edition-tag")
            assert label.count() == 1 and label.is_visible() and label.text_content() == "First Edition"
            for sel in ("#pwListen .pw-card-desc .an-edition-tag", "#podModal .pod-label .an-edition-tag"):
                assert pg.evaluate("s => document.querySelector(s).closest('[aria-hidden=\"true\"]') === null", sel), sel
            b.close()
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- ruling 8: the two progress scripts stay in step
# Every known difference between the Second Edition copy and the First Edition original, as
# (what the Second Edition copy has, what the First Edition original has in its place). The test swaps each
# Second Edition block for its First Edition counterpart and then requires the two files to be identical, so any
# other difference, in either file, fails. A change to one of these blocks also fails: update this list in the
# same commit as a deliberate change to the Prologue logic.
PROLOGUE_DIFFERENCES = [
    ("header comment",
     "   SECOND EDITION COPY (step 115). Built only when the Second Edition switch is ON,\n"
     "   served as /js/articles-progress-second-edition.js in place of\n"
     "   /js/articles-progress.js. The one difference: a section marked\n"
     "   data-prologue (Of Plainness, the unnumbered Prologue) is watched like the\n"
     "   rest but is not an Article. While it is in view the readout holds the\n"
     "   pre-count state, and Of Love for God and Neighbor is Article 1 of 13.\n"
     "\n",
     ""),
    ("counted list (data-prologue handling)",
     "        // Articles only: the Prologue is not counted.\n"
     "        var counted = sections.filter(function (s) { return !s.hasAttribute('data-prologue'); })\n"
     "            .map(function (s) { return s.id; });\n",
     ""),
    ("index and title from the counted list",
     "            var idx = current ? counted.indexOf(current) : -1;\n"
     "            var title = idx < 0 ? '' : titleOf(document.getElementById(current));\n",
     "            var idx = current ? order.indexOf(current) : -1;\n"
     "            var title = idx < 0 ? '' : titleOf(sections[idx]);\n"),
    ("comment naming the Prologue",
     "            // Pre-count (A00 opener, Prologue, Learning Pathways): no badge,\n",
     "            // Pre-count (A00 opener, prologue, Learning Pathways): no badge,\n"),
]


def normalised_second_edition_copy(se_text):
    for label, se_block, fe_block in PROLOGUE_DIFFERENCES:
        n = se_text.count(se_block)
        assert n == 1, f"Second Edition copy: the known Prologue block '{label}' occurs {n} times, expected once"
        se_text = se_text.replace(se_block, fe_block)
    return se_text


def lf(path):
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def test_progress_scripts_differ_only_in_the_prologue_logic():
    fe, se = lf(FE_JS), lf(SE_JS)
    norm = normalised_second_edition_copy(se)
    if norm != fe:
        diff = "".join(difflib.unified_diff(fe.splitlines(True), norm.splitlines(True),
                                            "src/js/articles-progress.js",
                                            "src/aoid-second-edition/articles-progress.js (Prologue logic swapped out)",
                                            n=1))
        pytest.fail("the two progress scripts differ outside the Prologue logic:\n" + diff[:4000])
