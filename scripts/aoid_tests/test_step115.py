"""Tests for AOID2 step 115 (Phase C3b, CODE-AOID2-73): the Articles menu, progress counter and pathway copy in line
with the Second Edition shape (an unnumbered Prologue, then thirteen numbered Articles, "Of Love for God and Neighbor"
(A14) as Article 1), the preserved First Edition page, the A14 title maps behind the switch, and the A14 apparatus notes.

Switch OFF: the site is as it stood; no Article 1 title is in any public file. Switch ON: the drawer, counter and copy
carry the new shape.

Run: python -m pytest scripts/aoid_tests/test_step115.py
"""
import functools
import http.server
import json
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
SE = REPO / "data-sources" / "aoid" / "second-edition"
APPROVED_A14 = SE / "WoP_AOID2_Step78_Article1_ApprovedWording_20261012.md"
SCOPE_A14 = REPO / "data-sources" / "aoid" / "floors" / "WoP_AOID2_ScopeNotes_A14_Love_Draft_20260922.md"
DATA = json.loads((REPO / "src" / "_data" / "apparatusData.json").read_text(encoding="utf-8"))
A14_TITLE = "Of Love for God and Neighbor"
FE_LEAD = ("This is the First Edition of the Articles of Interfaith Discipleship, kept here as first given. "
           '<a href="/articles/">Read the current Second Edition.</a>')
CARD_ON = "Begin with the Prologue and read on through all thirteen Articles in order, start to finish."
CARD_OFF = "Begin at the first article and read all thirteen declarations in order, start to finish."


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


def serve(site):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def read(site, rel):
    return (site / rel).read_text(encoding="utf8")


def drawer(page_html):
    m = re.search(r'<ol class="an-drawer-list">(.*?)</ol>', page_html, re.S)
    assert m
    return re.findall(r'<li><a href="#([^"]+)"\s+class="an-link"><span class="an-num"( aria-hidden="true")?>(\d*)</span>(.*?)</a></li>', m.group(1))


def public_files(site):
    return [p for p in site.rglob("*") if p.is_file() and p.suffix in (".html", ".js", ".json", ".css", ".xml", ".txt", ".vtt")]


# ---------------------------------------------------------------- item 1: drawer
def test_drawer_off_unchanged(site_off):
    rows = drawer(read(site_off, "articles/index.html"))
    assert [(r[2], r[3]) for r in rows][:3] == [("1", "Of Plainness"), ("2", "Of God"), ("3", "Of Creation and Life")]
    assert [r[2] for r in rows] == [str(i) for i in range(1, 14)]


def test_drawer_on_prologue_unnumbered_then_article_1_is_love(site_on):
    rows = drawer(read(site_on, "articles/index.html"))
    assert len(rows) == 14
    assert rows[0][0] == "of-plainness" and rows[0][2] == "" and rows[0][3] == "Prologue: Of Plainness"
    assert rows[1][0] == "of-love-for-god-and-neighbor" and rows[1][2] == "1" and rows[1][3] == A14_TITLE
    assert [r[2] for r in rows[2:]] == [str(i) for i in range(2, 14)]
    assert rows[2][3] == "Of God" and rows[-1][3] == "Of Our Confidence"


# ---------------------------------------------------------------- item 2: progress counter
def test_progress_script_choice(site_off, site_on):
    off, on = read(site_off, "articles/index.html"), read(site_on, "articles/index.html")
    assert '<script src="/js/articles-progress.js?' in off
    assert '<script src="/js/articles-progress-second-edition.js?' in on
    assert not (site_off / "js" / "articles-progress-second-edition.js").exists()
    assert 'data-prologue="true"' in on and "data-prologue" not in off


def progress_text(browser, site, anchor):
    srv = serve(site)
    try:
        pg = browser.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/articles/")
        pg.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
        pg.evaluate("id => { const e = document.getElementById(id); window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 200); }", anchor)
        pg.wait_for_timeout(1200)
        t = pg.evaluate("document.getElementById('anProgress').textContent")
        pg.close()
        return t
    finally:
        srv.shutdown()


def test_counter_on_does_not_count_the_prologue(browser, site_on):
    assert progress_text(browser, site_on, "of-plainness") == "Invitation"
    assert progress_text(browser, site_on, "of-love-for-god-and-neighbor") == "Article 1 of 13 — " + A14_TITLE
    assert progress_text(browser, site_on, "of-our-confidence") == "Article 13 of 13 — Of Our Confidence"


def test_counter_off_unchanged(browser, site_off):
    assert progress_text(browser, site_off, "of-plainness") == "Article 1 of 13 — Of Plainness"
    assert progress_text(browser, site_off, "of-our-confidence") == "Article 13 of 13 — Of Our Confidence"


# ---------------------------------------------------------------- item 3: pathway copy
def test_read_straight_through_card(site_off, site_on):
    off, on = read(site_off, "articles/index.html"), read(site_on, "articles/index.html")
    assert f'<span class="pw-card-desc">{CARD_OFF}</span>' in off and CARD_ON not in off
    assert f'<span class="pw-card-desc">{CARD_ON}</span>' in on and CARD_OFF not in on
    assert "getElementById('of-plainness')" in on  # the card still starts at the Prologue


# ---------------------------------------------------------------- item 6: edition note at the end of the Prologue
def test_edition_note_moved_to_end_of_prologue(site_on, site_off):
    on = read(site_on, "articles/index.html")
    i = on.index('id="of-plainness"')
    seg = on[i:on.index("</section>", i)]
    pos = {k: seg.index(k) for k in ("We accept", "prologue-edition-note", "article-rjw", "article-footnote")}
    assert pos["We accept"] < pos["prologue-edition-note"] < pos["article-rjw"] < pos["article-footnote"]
    assert seg.count("prologue-edition-note") == 1
    assert "prologue-edition-note" not in read(site_off, "articles/index.html")


# ---------------------------------------------------------------- item 7: the First Edition page
def test_first_edition_page(site_off, site_on):
    assert not (site_off / "articles" / "first-edition").exists()
    page = read(site_on, "articles/first-edition/index.html")
    assert '<meta name="robots" content="noindex">' in page
    m = re.search(r'<div class="fe">\s*(<p class="fe-lead">.*?</p>)', page, re.S)
    assert m and m.group(1) == f'<p class="fe-lead">{FE_LEAD}</p>'
    assert '<p class="fe-lead">' not in read(site_on, "articles/index.html")


# ---------------------------------------------------------------- item 8: no Article 1 title in the OFF site
def test_off_site_has_no_article_1_title(site_off):
    hits = []
    for p in public_files(site_off):
        t = p.read_text(encoding="utf8", errors="replace")
        if "Love for God" in t or "rjw-A14" in t or re.search(r"(?<!RNR-)A14", t):
            hits.append(str(p.relative_to(site_off)))
    assert hits == []


def test_on_site_carries_the_a14_title_map(site_on):
    assert f'A14: "{A14_TITLE}"' in read(site_on, "articles/index.html")
    assert f'A14: "{A14_TITLE}"' in read(site_on, "my-reflections/index.html")
    for js in ("articles-panel.js", "my-reflections.js"):
        assert "A14" not in read(site_on, f"js/{js}")


# ---------------------------------------------------------------- items 9 and 10: A14 apparatus
def section5():
    t = APPROVED_A14.read_text(encoding="utf8").replace("\r\n", "\n").split("## 5.")[1]
    n1 = re.search(r"Note 1 \(self-love, ruling 1\):\n(.+)\n", t).group(1)
    n2 = re.search(r"Note 2 \(cross-reference, ruling 5\):\n(.+)\n", t).group(1)
    n3 = re.search(r"Note 3 \(existing, from the floor document\): (.+)", t).group(1)
    return n1, n2, n3[0].upper() + n3[1:]


def paras(span):
    return DATA["A14"][span]["panel_comment"].split("\n\n")


def test_a14_l1_notes_are_spread_one_per_span():
    n1, n2, n3 = section5()
    floor = paras("s1")[0]
    assert floor.startswith("The Article confesses only what Matthew 22:36-40 confesses")
    assert paras("s1") == [floor, n2]
    assert paras("s2") == [floor, n1]
    assert paras("s3") == [floor, n3]
    assert paras("s4") == [floor] and paras("s5") == [floor]


def test_a14_anchor_comments_come_from_the_scope_note():
    doc = SCOPE_A14.read_text(encoding="utf8")
    filled = []
    for sid, s in DATA["A14"].items():
        for col in ("biblical", "restoration"):
            for a in s[col]:
                if a["comment"]:
                    filled.append((sid, a["ref"]))
                    assert a["comment"] in doc, (sid, a["ref"])
    for want in (("s12", "D&C 124:22–24"), ("s12", "Alma 8:19–21"), ("s12", "Alma 10:7–9"), ("s8", "D&C 64:9–10"), ("s1", "D&C 59:5–6")):
        assert want in filled, want
    assert len(filled) == 10
