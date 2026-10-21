"""Tests for CODE-AOID2-52: D1-D3 and the teaching additions T1-T6.

Switch OFF: none of the additions exists. Switch ON: each addition renders once on each of the thirteen Articles,
exactly as approved (wording copied from WoP_AOID2_TeachingPractices_Scores.md, section "Teaching additions T1-T6");
T4 keeps the learner's question in local storage only and works with storage blocked; T6 shows "Not recorded"
or the recorded number in "Borderline readings" and names A2-F1's four families.

Run: python -m pytest scripts/aoid_tests/test_teaching.py
"""
import json
import re

import pytest

from test_step89 import (BAPTISM_FAMILIES, COUNTS, SE, browser, server, site_off, site_on, text_of)  # noqa: F401  (fixtures)

TEACHING_FILE = SE / "WoP_AOID2_TeachingPractices_Scores.md"
ARTICLE_IDS = ["a%02d" % n for n in range(2, 15)]            # a14 is the new Article 1
T1 = {
    "declaration": "Here you read what we confess together. Weigh each line against your own life.",
    "disclosure": "Here you see where the churches agree, where they divide, and why each reading was counted as it was.",
    "record": "Here you test each count against the churches' own words. Check any you doubt.",
}
T2_REST = (" Which teachings in this Article do you think nearly every Christian tradition confesses? Which do you think divides them? "
           "Hold your answer, then see what the record shows.")
T3 = "If you believe we have misstated what your church teaches, tell us. We will look again."
T4_LABEL = "A question of your own to come back to:"
T4_NOTE = "Kept only in this browser. Nothing is sent."
T5 = "As you read, mark the line you already live, and the line you most need to."


def html_text(s):
    return text_of(s)


def panel(page_html, art, name):
    """Like test_step89.panel, but the last Article (no divider after it) ends at the end of the page section."""
    m = re.search(r'<div role="tabpanel"[^>]*id="%s-%s".*?(?=<div role="tabpanel"|<div class="articles-divider"|</section>)' % (art, name), page_html, re.S)
    assert m, f"{art} {name} panel not found"
    return m.group(0)


def test_teaching_wording_is_the_approved_file():
    src = TEACHING_FILE.read_text(encoding="utf8")
    for w in list(T1.values()) + [T3, T4_LABEL, T4_NOTE, T5, "Before you read on:" + T2_REST]:
        assert w in src, w
    assert src.count("Teaching additions T1-T6, APPROVED by Aaron 21 Oct 2026, 12:59 ET") == 1


@pytest.mark.parametrize("art", ARTICLE_IDS)
def test_teaching_additions_on_every_article(site_on, art):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    decl, disc, rec = panel(arts, art, "declaration"), panel(arts, art, "disclosure"), panel(arts, art, "record")
    # T1: the first line under each tab, in small type
    assert html_text(decl).startswith(T1["declaration"])
    assert re.search(r'<p[^>]*class="[^"]*an-practice[^"]*"[^>]*>%s</p>' % re.escape(T1["declaration"]), decl)
    assert html_text(rec).startswith(T1["record"])
    assert 'class="sync-para an-practice"' in rec or 'class="an-practice"' in rec
    # T2: boxed prompt above everything else on the Disclosure tab, bold lead-in, no input, then the T1 line
    box = re.search(r'<div class="an-before"[^>]*>.*?</div>', disc, re.S)
    assert box and "<strong>Before you read on:</strong>" in box.group(0)
    assert html_text(box.group(0)) == "Before you read on:" + T2_REST
    head, tail = disc.split(box.group(0), 1)
    assert re.sub(r"<[^>]+>", "", head).strip() == ""                       # nothing before it
    assert "<textarea" not in box.group(0) and "<input" not in box.group(0)
    assert html_text(tail).startswith(T1["disclosure"])
    # T3: the last thing in the Declaration tab, linked to /aoid/corrections/
    assert re.search(r'<a href="/aoid/corrections/">%s</a></p>\s*</div>$' % re.escape(T3), decl.rstrip())
    # T5: above the Article's text
    assert decl.index(T5) < decl.index('class="article-body"')
    # T4: after the reflection block, label tied to the box, note after the box
    i = decl.index('class="article-rjw"')
    j = decl.index('<div class="an-learner"', i)
    assert decl.index("</textarea>", i) < j
    assert re.search(r'<label class="an-learner-label" for="%s-learner-question"><strong>%s</strong></label>' % (art, re.escape(T4_LABEL)), decl)
    assert re.search(r'<textarea class="an-learner-box" id="%s-learner-question"[^>]*></textarea><p[^>]*class="[^"]*an-learner-note[^"]*"[^>]*><em>%s</em></p>' % (art, re.escape(T4_NOTE)), decl)


def test_teaching_additions_placed_once_per_article_and_absent_when_off(site_on, site_off):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    assert arts.count("Before you read on:") == 13 and arts.count(T5) == 13 and arts.count('class="an-learner"') == 13
    assert arts.count(T3) == 13 and arts.count(T4_LABEL) == 13 and arts.count(T4_NOTE) == 13
    assert sum(html_text(arts).count(w) for w in T1.values()) == 39
    off = (site_off / "articles" / "index.html").read_text(encoding="utf8")
    for needle in ("Before you read on", T5, T4_LABEL, T4_NOTE, T3, "an-learner", "an-practice", T1["declaration"], "Not recorded"):
        assert needle not in off, needle


def test_summary_table_borderline_and_confirming_cells(site_on):
    """T6: Borderline readings is "Not recorded" where it was never recorded and the number (0 included) where it was."""
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    data = json.loads(COUNTS.read_text(encoding="utf8"))
    n = 0
    for f in data["floors"]:
        if f["status"] == "UNSCORED":
            continue
        art = f["spans"][0].split(".")[0].lower()
        m = re.search(r'<tr id="%s-record-%s">(.*?)</tr>' % (art, re.escape(f["id"])), arts, re.S)
        cells = [html_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", m.group(1), re.S)]
        want = str(f["borderline"]) if f["status"] == "MATCH" and f["borderline"] is not None else "Not recorded"
        assert cells[5] == want, f["id"]
        n += 1
    assert n >= 30
    a2f1 = re.search(r'<tr id="a02-record-A2-F1">(.*?)</tr>', arts, re.S).group(1)
    assert html_text(re.findall(r"<td>(.*?)</td>", a2f1, re.S)[-1]) == "4 (Eastern Orthodox, Anabaptist, Oriental Orthodox, Church of the East)"


def test_d1_baptism_table_document_names():
    rows = {r["family"]: r["document"] for r in json.loads(BAPTISM_FAMILIES.read_text(encoding="utf8"))["rows"]}
    assert rows["Methodist"] == ("United Methodist Book of Discipline (2024): Confession of Faith, Article VI; "
                                 "Articles of Religion, Article XVII; paragraph 129")
    assert "Articles VI and XVII" not in json.dumps(rows)
    assert rows["Pentecostal (with independent charismatic churches)"].startswith("United Pentecostal Church International, Articles of Faith;")
    assert rows["Stone-Campbell"].startswith("The Design of the Christian Church (Disciples of Christ),")
    assert rows["Adventist"].startswith("General Conference of Seventh-day Adventists, Church Manual (20th edition, revised 2022)")
    assert rows["Church of the East"].endswith("Holy Synod statement of the Assyrian Church of the East (Erbil, April 2024)")


def test_d2_galatians_sentence_final_form(site_on):
    d2 = ("That faith works by love (Galatians 5:6) is confessed in their own words by the Catholic, Eastern Orthodox, Lutheran and Reformed "
          "traditions, and in sense by the Anglican, Holiness, Anabaptist and Jehovah's Witness, and on a borderline reading by the Baptist.")
    assert d2 in html_text((site_on / "articles" / "index.html").read_text(encoding="utf8"))
    assert d2 in (SE / "WoP_AOID2_Step89_Article11_Baptism_Approved_20261020.md").read_text(encoding="utf8")
    assert "Anglican, Baptist, Holiness" not in (site_on / "articles" / "index.html").read_text(encoding="utf8")


def learner_page(browser, server, width, block_storage=False):
    ctx = browser.new_context(service_workers="block", viewport={"width": width, "height": 900})
    if block_storage:
        ctx.add_init_script("""
            Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked', 'SecurityError'); }, configurable: true });
        """)
    pg = ctx.new_page()
    errors, requests = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("request", lambda r: requests.append((r.method, r.url)))
    pg.route("**/*", lambda route: route.abort() if not route.request.url.startswith(server) else route.continue_())
    pg.goto(server + "/articles/", wait_until="domcontentloaded")
    pg.wait_for_selector("#a11-learner-question", state="attached")
    pg.wait_for_load_state("load")
    return ctx, pg, errors, requests


@pytest.mark.parametrize("width", [1280, 390])
def test_learner_question_stored_in_local_storage_only(browser, server, width):
    ctx, pg, errors, requests = learner_page(browser, server, width)
    pg.evaluate("() => document.getElementById('a11-learner-question').scrollIntoView()")
    box = pg.locator("#a11-learner-question")
    assert pg.locator("label[for=a11-learner-question]").inner_text() == T4_LABEL
    before = len(requests)
    box.fill("Why did He weep?")
    assert pg.evaluate("() => localStorage.getItem('wop-aoid2-learner-a11')") == "Why did He weep?"
    assert pg.evaluate("() => localStorage.getItem('wop-aoid2-learner-a02')") is None            # per Article
    pg.reload(wait_until="domcontentloaded")
    pg.wait_for_selector("#a11-learner-question", state="attached")
    assert pg.input_value("#a11-learner-question") == "Why did He weep?"
    pg.locator("#a11-learner-question").fill("")
    assert pg.evaluate("() => localStorage.getItem('wop-aoid2-learner-a11')") is None
    assert pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    assert not [r for r in requests[before:] if r[0] != "GET"]                                      # nothing is transmitted
    assert errors == []
    ctx.close()


@pytest.mark.parametrize("width", [1280, 390])
def test_learner_question_works_with_storage_blocked(browser, server, width):
    ctx, pg, errors, requests = learner_page(browser, server, width, block_storage=True)
    # Other site scripts that read storage unguarded already raise "blocked" at load (the switch-OFF build does the same);
    # what T4 must add is nothing: no further error from typing, switching tabs or the T4 script.
    at_load = list(errors)
    pg.evaluate("() => document.getElementById('a11-learner-question').scrollIntoView()")
    pg.locator("#a11-learner-question").fill("Still typing")
    assert pg.input_value("#a11-learner-question") == "Still typing"
    pg.evaluate("() => document.getElementById('a11-tab-record').click()")
    pg.wait_for_selector("#a11-record:not([hidden])", state="attached")
    assert pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    assert errors == at_load
    ctx.close()
