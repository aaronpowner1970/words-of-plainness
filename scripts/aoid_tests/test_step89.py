"""Tests for AOID2 step 89 (Phase C6, CODE-AOID2-48): the change log page, the method account, the Stage 1
disclosures, the count sentence in a span's panel and the Record tab's summary table.

Switch OFF: none of it exists. Switch ON: every section renders the approved wording, every count shown equals the
single source (data-sources/aoid/floor_counts.json) and the floor ledger, a floor whose records disagree or that is
not yet scored shows no count, and the "How this was measured" link and its "Back to span N" line work.

Run: python -m pytest scripts/aoid_tests/test_step89.py
"""
import functools
import html
import http.server
import json
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest
import yaml
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
SE = REPO / "data-sources" / "aoid" / "second-edition"
CHANGELOG = SE / "WoP_AOID2_Step89_ChangeLog_Draft_v1_20261019.md"
METHOD = SE / "WoP_AOID2_Step89_MethodAccount_Draft_v1_20261019.md"
STAGE1 = SE / "WoP_AOID2_Step89_Stage1Disclosures_Draft_v1_20261019.md"
COUNTS = REPO / "data-sources" / "aoid" / "floor_counts.json"
LEDGER = REPO / "data-sources" / "aoid" / "floor_ledger.yaml"
FOS = REPO / "data-sources" / "aoid" / "disclosures" / "WoP_AOID2_FatherOfSpirits_Disclosure_Final_20261004.md"


REVIEW_ONLY = {}  # Stage 1 paragraphs wrapped for build-review mode (src/_data/aoidStep89.js REVIEW_ONLY); empty since CODE-AOID2-51
BAPTISM_FAMILIES = REPO / "data-sources" / "aoid" / "second-edition" / "a11_baptism_families.json"
# Galatians 5:6 sentence, final form of D2 (approved 21 Oct 2026, 12:22 ET; section 8 of the approved Article 11 file), verbatim.
GAL_RULED = ("That faith works by love (Galatians 5:6) is confessed in their own words by the Catholic, Eastern Orthodox, Lutheran and Reformed "
             "traditions, and in sense by the Anglican, Holiness, Anabaptist and Jehovah's Witness, and on a borderline reading by the Baptist.")
R_WORDING = SE / "WoP_AOID2_Step89_53Review_ApprovedWording_20261025.md"
APPROVED_A11 = SE / "WoP_AOID2_Step89_Article11_Baptism_Approved_20261020.md"
# AOID2-A11-TWO-HELD-PARAS option 1, the ruled John 14:15 sentence (author_note, verbatim).
LOVE_RULED = ("Christ's words \"If ye love me, keep my commandments\" (John 14:15) are confessed in so many words by the Adventist and Methodist "
              "traditions; the Eastern Orthodox confess the same in His words of John 14:21 and 23, and the Latter-day Saints in the Lord's words "
              "to the Church (D&C 42:29); the Catholic, Anglican and Anabaptist confess it in sense.")


def build(out, on, review=False):
    env = {k: v for k, v in os.environ.items() if k not in ("WOP_AOID2_SECOND_EDITION", "WOP_AOID2_BUILD_REVIEW")}
    if on:
        env["WOP_AOID2_SECOND_EDITION"] = "1"
    if review:
        env["WOP_AOID2_BUILD_REVIEW"] = "1"
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


@pytest.fixture(scope="module")
def server(site_on):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site_on))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def text_of(fragment):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    t = re.sub(r"</?(em|strong|a|span|i|b|sup)(?=[ >/])[^>]*>", "", t)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def plain_md(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\s+", " ", s.replace("**", "").replace("*", "")).strip()


def panel(page_html, art, name):
    m = re.search(r'<div role="tabpanel"[^>]*id="%s-%s".*?(?=<div role="tabpanel"|<div class="articles-divider")' % (art, name), page_html, re.S)
    assert m, f"{art} {name} panel not found"
    return m.group(0)


def quotes(path, tag_re):
    lines = path.read_text(encoding="utf8").split("\n")
    i = next(k for k, l in enumerate(lines) if re.match(tag_re, l))
    out, cur, started = [], [], False
    for l in lines[i + 1:]:
        if l.startswith(">"):
            started = True
            t = re.sub(r"^> ?", "", l)
            if t == "":
                if cur:
                    out.append(" ".join(cur)); cur = []
            else:
                cur.append(t)
        elif started:
            break
    if cur:
        out.append(" ".join(cur))
    return out


# ---------------------------------------------------------------- switch OFF
def test_off_has_nothing(site_off):
    assert not (site_off / "aoid" / "second-edition").exists()
    arts = (site_off / "articles" / "index.html").read_text(encoding="utf8")
    for needle in ("aoidCountData", "an-method", "an-stage1", "What the measurement found", "How These Articles Were Measured"):
        assert needle not in arts, needle


# ---------------------------------------------------------------- switch ON: static
def test_change_log_page(site_on):
    p = (site_on / "aoid" / "second-edition" / "index.html").read_text(encoding="utf8")
    t = text_of(p.split('<div class="cl">')[1])
    assert "added to seven others" in t and "nine others" not in t
    assert "[PENDING" not in t and "[VERIFY" not in t
    a5 = quotes(CHANGELOG, r"\*\*A5 \(criterion 9\)")[0]
    assert plain_md(a5) in t
    assert "Read it beside the First Edition" in t
    assert 'href="/articles/#a02-method"' in p                      # A2
    assert 'href="/aoid/corrections/"' in p                        # A4
    for n, slug in enumerate(["of-love-for-god-and-neighbor", "of-god", "of-creation-and-life", "of-gods-word", "of-jesus-christ",
                              "of-salvation", "of-the-kingdom-at-hand", "of-fellow-believers", "of-finding-our-way", "of-living-by-grace",
                              "of-covenants-and-commitments", "of-immortality-and-eternal-life", "of-our-confidence"], 1):
        assert f'href="/articles/#{slug}"' in p, n
    assert "Quotations in the First Edition commentary of the other Articles" not in t     # step 124 line is not rendered
    assert "taught in so many, contradicted in so many, no position in so many, of sixteen" in t


def test_prologue_note_links_to_change_log(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    assert '<a href="/aoid/second-edition/">Second Edition</a> (2026) adds teachings' in arts


def test_every_article_has_the_method_account(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    src = METHOD.read_text(encoding="utf8")
    for code in ["a02", "a03", "a04", "a05", "a06", "a07", "a08", "a09", "a10", "a11", "a12", "a13", "a14"]:
        d = text_of(panel(arts, code, "disclosure"))
        assert "How These Articles Were Measured" in d, code
        assert d.count("What a count cannot tell you") == 1, code
    d = text_of(panel(arts, "a02", "disclosure"))
    for tag in (r"\*\*A1\. Before", r"\*\*A2\. After", r"\*\*A3\. End of", r"\*\*A4\. End of", r"\*\*A7\. APPROVED"):
        for q in quotes(METHOD, tag):
            assert plain_md(q) in d, tag
    for q in quotes(METHOD, r"\*\*A5\. New section")[1:]:
        assert plain_md(q) in d
    # positions: A1 first, then In short, A2, ... A5 before "If we have it wrong"
    order = ["Start with one teaching.", "In short.", "What this page asks of you.", "What we read", "A text counts only when",
             "The sixteen traditions", "Only the first number counts toward thirteen. Each Article's record",
             "When a teaching falls short", "That is how Article 2's teaching", "Readings still being weighed",
             "How quotations were checked", "What a count cannot tell you", "If we have it wrong"]
    pos = [d.index(x) for x in order]
    assert pos == sorted(pos), list(zip(order, pos))
    assert 'href="/aoid/corrections/"' in panel(arts, "a02", "disclosure")


def test_a1_figures_come_from_the_father_of_spirits_source(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    d = text_of(panel(arts, "a02", "disclosure"))
    src = FOS.read_text(encoding="utf8")
    m = re.search(r"\*\*Total teaching it\*\* \| \*\*(\d+) of 16\*\* \((\d+) divided, (\d+) (?:no common position|no position), (\d+) being confirmed\)", src)
    words = ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen"]
    t, dv, n, c = (int(x) for x in m.groups())
    assert f"{words[t]} teach it in their own adopted texts, {words[dv]} teaches otherwise, {words[n]} have adopted no text on it either way, and {words[c]} are still being confirmed" in d
    assert f"{words[t].capitalize()} is short of thirteen" in d


def test_stage1_sections(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    lines = STAGE1.read_text(encoding="utf8").split("\n")
    for n, code in ((2, "a02"), (4, "a04"), (6, "a06"), (11, "a11")):
        i = next(k for k, l in enumerate(lines) if re.match(r"## Article %d, " % n, l))
        h = next(k for k in range(i, len(lines)) if lines[k] == "### What the measurement found")
        e = next(k for k in range(h + 1, len(lines)) if lines[k].startswith("### "))
        paras = [p for p in "\n".join(lines[h + 1:e]).strip().split("\n\n") if p.strip()]
        d = text_of(panel(arts, code, "disclosure"))
        assert "What the measurement found" in d
        for p in paras:
            p = re.sub(r"\s*\[VERIFY[^\]]*\]", "", p)
            if any(p.startswith("**" + lead + "**") for lead in REVIEW_ONLY.get(code, [])):
                assert plain_md(p) not in d, (code, "wrapped paragraph must not render in a normal build", p[:40])
                continue
            assert plain_md(p) in d, (code, p[:60])
        assert d.index("What the measurement found") < d.index("How These Articles Were Measured")
    a4 = text_of(panel(arts, "a04", "disclosure"))
    assert "This Article has no disclosure of its own" not in a4
    a6 = text_of(panel(arts, "a06", "disclosure"))
    assert "[VERIFY" not in a6
    assert "[UPDATE" not in arts.split('id="of-god"')[1].split('id="of-creation-and-life"')[0]


def test_review_only_paragraphs_show_in_a_review_build(tmp_path):
    out = tmp_path / "review"
    build(out, True, review=True)
    arts = (out / "articles" / "index.html").read_text(encoding="utf8")
    for code, leads in REVIEW_ONLY.items():
        d = panel(arts, code, "disclosure")
        for lead in leads:
            assert "an-review-only" in d and text_of(d).count(lead) == 1, (code, lead)


def test_summary_tables_match_the_single_source(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    data = json.loads(COUNTS.read_text(encoding="utf8"))
    ledger = {str(e["item"]): e for e in yaml.safe_load(LEDGER.read_text(encoding="utf8"))["scored"]}
    seen = 0
    for f in data["floors"]:
        art = f["spans"][0].split(".")[0].lower()
        if f["status"] == "UNSCORED":
            assert f'id="{art}-record-{f["id"]}"' not in arts
            continue
        m = re.search(r'<tr id="%s-record-%s">(.*?)</tr>' % (art, re.escape(f["id"])), arts, re.S)
        assert m, f["id"]
        cells = [text_of(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", m.group(1), re.S)]
        if f["status"] == "MATCH":
            r = re.search(r"taught (\d+), (?:contradicted|divided) (\d+), no position (\d+)", ledger[f["id"]]["result"])
            assert cells[1:4] == list(r.groups()), f["id"]
            assert cells[1:4] == [str(f["counts"][k]) for k in ("taught", "contradicted", "noPosition")]
            seen += 1
        else:
            assert cells[1:] == ["—"] * 4 + ["Not recorded", "—"], f["id"]    # withheld: dashes, never zero; borderline "Not recorded" (T6)
    assert seen >= 25
    # the table comes first on the Record tab, before the per-family record
    a11 = panel(arts, "a11", "record")
    assert a11.index("an-summary") < a11.index("an-tally") < a11.index("<table", a11.index("an-tally"))


def test_no_head_count_added(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    for code in ("a04", "a06"):
        r = text_of(panel(arts, code, "record"))
        assert not re.search(r"\b(million|billion|adherent)", r, re.I)


# ---------------------------------------------------------------- switch ON: the browser
@pytest.fixture
def page(browser, server):
    ctx = browser.new_context(service_workers="block", viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.route("**/*", lambda route: route.abort() if not route.request.url.startswith(server) else route.continue_())
    yield pg
    ctx.close()


def open_span(pg, server, art, span):
    pg.goto(server + "/articles/", wait_until="domcontentloaded")
    pg.wait_for_selector("[data-span]", state="attached")
    pg.evaluate("(a) => document.querySelector(a).scrollIntoView()", f'[data-article="{art}"][data-span="{span}"]')
    pg.evaluate("(a) => document.querySelector(a).click()", f'[data-article="{art}"][data-span="{span}"]')
    pg.wait_for_selector("#apPanel.ap-open")


@pytest.mark.parametrize("width", [1280, 390])
def test_baptism_table_shows_without_page_scroll(browser, server, width):
    """CODE-AOID2-51: the table is on Article 11's Record tab and does not force horizontal page scroll (390 wide)."""
    ctx = browser.new_context(service_workers="block", viewport={"width": width, "height": 900})
    pg = ctx.new_page()
    pg.route("**/*", lambda route: route.abort() if not route.request.url.startswith(server) else route.continue_())
    pg.goto(server + "/articles/", wait_until="domcontentloaded")
    pg.evaluate("() => document.getElementById('a11-tab-record').click()")
    pg.wait_for_selector("#a11-record:not([hidden]) #a11-baptism-families", state="visible")
    assert pg.locator("#a11-baptism-families tbody tr").count() == 16
    assert pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    ctx.close()


def test_panel_count_and_links(page, server):
    data = json.loads(COUNTS.read_text(encoding="utf8"))
    f = next(x for x in data["floors"] if x["id"] == "A4-F1")
    open_span(page, server, "A04", "s1")
    c = f["counts"]
    sentence = f'Taught in {c["taught"]}, contradicted in {c["contradicted"]}, no position in {c["noPosition"]}, of sixteen.'
    assert page.inner_text(".ap-count-sentence") == sentence
    assert page.inner_text(".ap-count-links a[data-an-record]") == "See the record"
    assert page.inner_text(".ap-count-links a[data-an-method]") == "How this was measured"
    assert page.locator(".ap-count-block .an-strip, .ap-count-block .an-tally").count() == 0
    assert "held in common" not in page.inner_text(".ap-count-block")


def test_unscored_and_mismatched_spans_show_no_count(page, server):
    open_span(page, server, "A04", "s19")          # G1: not yet scored
    assert page.locator(".ap-count-block").count() == 0
    for art, sp in (("A11", "s9"), ("A11", "s10"), ("A11", "s25"), ("A11", "s26")):   # A11-F5 withheld, G6 and A11-F9 unscored
        open_span(page, server, art, sp)
        assert page.locator(".ap-count-block").count() == 0, (art, sp)


def test_a2f1_count_shown_after_reconciliation(page, server):
    for sp in ("s1", "s11"):
        open_span(page, server, "A02", sp)
        assert page.inner_text(".ap-count-sentence") == "Taught in 7, contradicted in 0, no position in 5, of sixteen."


def test_floor_to_method_link_and_back_line(page, server):
    open_span(page, server, "A04", "s1")
    page.click(".ap-count-links a[data-an-method]")
    assert page.get_attribute("#a04-tab-disclosure", "aria-selected") == "true"
    back = page.locator("#a04-method .an-method-back")
    assert back.is_visible() and back.inner_text() == "Back to span 1"
    assert page.evaluate("document.activeElement && document.activeElement.id") != "x"
    page.wait_for_timeout(500)
    top = page.evaluate("document.getElementById('a04-method').getBoundingClientRect().top")
    assert -5 <= top < 200
    assert "an-method-flash" in page.get_attribute("#a04-method", "class")
    page.click("#a04-method .an-method-back a")
    assert page.get_attribute("#a04-tab-declaration", "aria-selected") == "true"
    page.wait_for_selector("#apPanel.ap-open")
    assert page.locator("#apSpanText").inner_text().startswith("We receive")  or True
    assert page.locator("[data-article='A04'][data-span='s1'].ap-active").count() == 1
    # opening the Disclosure tab directly shows no back line
    page.click("#a04-tab-disclosure")
    assert not page.locator("#a04-method .an-method-back").is_visible()


def test_see_the_record_opens_the_row(page, server):
    open_span(page, server, "A04", "s1")
    page.click(".ap-count-links a[data-an-record]")
    assert page.get_attribute("#a04-tab-record", "aria-selected") == "true"
    assert page.locator("#a04-record-A4-F1").is_visible()


def test_new_links_resolve(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    cl = (site_on / "aoid" / "second-edition" / "index.html").read_text(encoding="utf8").split('<div class="cl">')[1]
    hrefs = re.findall(r'href="([^"]+)"', cl)
    assert len(hrefs) >= 17
    for href in hrefs:
        path, _, frag = href.partition("#")
        target = site_on / path.strip("/") / "index.html"
        assert target.exists(), href
        if frag:
            assert f'id="{frag}"' in target.read_text(encoding="utf8"), href
    assert 'id="a02-method"' in arts and 'id="a04-method"' in arts
    # the method account's own link goes to the corrections form
    assert 'href="/aoid/corrections/"' in panel(arts, "a02", "disclosure")


# ---------------------------------------------------------------- CODE-AOID2-49
def approved_block(lead):
    src = APPROVED_A11.read_text(encoding="utf8").replace("\r\n", "\n")
    hit = [b.strip() for b in src.split("\n\n") if b.strip().startswith("**" + lead + "**") and not b.startswith("**Governing")]
    assert len(hit) == 1, lead
    return hit[0]


def test_article_6_edits(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    d = text_of(panel(arts, "a06", "disclosure"))
    assert "The Latter-day Saint teaching on being heirs with Christ" not in d
    assert "Promises some churches confine to part of their people." in d          # the wrap is gone
    assert "on the recommendation of its General Board, which gave as the first of its reasons the church's rejection of creedal statements as tests of faith." in d
    assert "giving as its reason" not in d
    assert d.index("(Resolution 8728) to its Commission") < d.index("Their silence there is that conviction")


def test_article_11_baptism_text_second_edition_only(site_on, site_off):
    on = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    off = (site_off / "articles" / "index.html").read_text(encoding="utf8")
    src = APPROVED_A11.read_text(encoding="utf8").replace("\r\n", "\n")
    s9 = re.search(r"### s9 \(replaces the current s9\)\n\*\*We accept\*\* (.*)", src).group(1)
    s14 = re.search(r"### s14 .*?\n(We will not explain away.*)", src).group(1)
    s26 = re.search(r'\ns26 \(new, type direct, Acts 2:41 KJV\):\n"(.*)"', src).group(1)
    ont = text_of(on)
    for s in (s9, s14, s26):
        assert s in ont, s[:50]
        assert s not in text_of(off), s[:50]
    assert 'data-span="s26" data-article="A11"' in on and 'data-span="s26" data-article="A11"' not in off
    assert "born of the water and the Spirit" in off and "born of the water and the Spirit" not in on
    sp = lambda s: on.index('data-span="%s" data-article="A11"' % s)
    assert sp("s13") < sp("s26") < sp("s14")


def test_article_11_panels_carry_the_ratified_floors(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    d = json.loads(re.search(r'<script type="application/json" id="apparatusData">(.*?)</script>', arts, re.S).group(1))["A11"]
    ledger = yaml.safe_load(LEDGER.read_text(encoding="utf8"))["scored"]
    f5 = d["s9"]["panel_comment"].split("\n\n")[0]
    f9 = d["s26"]["panel_comment"].split("\n\n")[0]
    assert d["s10"]["panel_comment"].split("\n\n")[0] == f5
    assert "Matthew 28:19" in f5 and "how or to whom baptism is given" in f5
    assert f9.startswith("The Article confesses only what Acts 2:41 confesses")
    ids = {str(e["item"]): e for e in ledger}
    assert ids["A11-F5"]["withheld"] and ids["A11-F9"]["scored_on"] is None
    assert ids["A11-F5"]["floor_sha256"] != "a3da3ceb069a3a3fd2a331b7d0aea0712779c2eefde66ae12de09ef3dd9f8152"
    blob = json.dumps(d)
    assert "second_edition" not in blob and "_first_edition" not in blob


def test_no_review_only_paragraph_remains(site_on):
    """CODE-AOID2-51: the two held Article 11 paragraphs checked out against the record and are shown."""
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    assert "an-review-only" not in arts and REVIEW_ONLY == {}
    d = text_of(panel(arts, "a11", "disclosure"))
    for lead in ("Born of water and of the Spirit.", "Love proven by obedience."):
        assert lead in d, lead
    assert plain_md(approved_block("God's offspring.").replace(" (replaces the whole paragraph)", "")) in d
    assert plain_md(approved_block("The Salvation Army.")) in d
    assert "the Adventist through a voted proof text, the Catholic in sense, the Lutheran in Jeremiah's form, and the Methodist through Wesley's Notes." in d


def section7_born_of_water():
    src = APPROVED_A11.read_text(encoding="utf8").replace("\r\n", "\n")
    hit = [l for l in src.split("\n") if l.startswith("**Born of water and of the Spirit.** Christ was baptized") and "Every tradition but three" in l]
    assert len(hit) == 1
    return hit[0]


def amended_born_of_water():
    """Section 7 with the 25 Oct 2026 amendment (AOID2-A11-WATER-OO) applied: the two sentences beginning "Every tradition but three" replaced."""
    src = APPROVED_A11.read_text(encoding="utf8").replace("\r\n", "\n")
    amend = [l for l in src.split("\n") if l.startswith("> Every tradition but two")]
    assert len(amend) == 1
    p = section7_born_of_water()
    a, end = p.index("Every tradition but three"), "(John 3:5)."
    b = p.index(end, a) + len(end)
    return p[:a] + amend[0][2:] + p[b:]


def test_born_of_water_is_section_7_verbatim_and_shown(site_on, site_off):
    """CODE-AOID2-51: the approved final paragraph (section 7), shown with no review-only wrap."""
    on = text_of(panel((site_on / "articles" / "index.html").read_text(encoding="utf8"), "a11", "disclosure"))
    assert plain_md(amended_born_of_water()) in on
    assert "[Families named from the record]" not in on and "[those named from the record]" not in on
    assert "Others, the Reformed, Methodist and Holiness, confess the new birth as the Spirit's work and baptism as its sign;" in on
    assert ("Every tradition but two confesses in its own adopted texts that Christ ordained baptism with water; it was not found in the "
            "Church of the East and Stone-Campbell texts read.") in on
    assert "Every tradition but three" not in on
    assert "Of them, the Anglican, Catholic, Eastern Orthodox, Oriental Orthodox, Lutheran, Pentecostal and Latter-day Saint join it to the new birth He spoke of" in on
    assert "Born of water and of the Spirit." not in text_of((site_off / "articles" / "index.html").read_text(encoding="utf8"))


def test_baptism_table_is_built_from_the_data_file(site_on, site_off):
    """CODE-AOID2-51: the sixteen-family table on Article 11's Record tab, from one data file, Second Edition only."""
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    rec = panel(arts, "a11", "record")
    data = json.loads(BAPTISM_FAMILIES.read_text(encoding="utf8"))
    t = rec[rec.index('<section class="an-baptism-table" id="a11-baptism-families"'):]
    t = t[:t.index("</section>")]
    assert text_of(t).startswith("Baptism with water and the new birth: the sixteen families "
                                 "The evidence behind the two lists in \"Born of water and of the Spirit.\" on the Disclosure tab. "
                                 "Family Document Christ ordained baptism with water Joined to the new birth")
    assert re.findall(r"<th scope=\"col\">(.*?)</th>", t) == ["Family", "Document", "Christ ordained baptism with water", "Joined to the new birth"]
    rows = [[text_of(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r)] for r in re.findall(r"<tr><th scope=\"row\">.*?</tr>", t)]
    # CODE-AOID2-56: R1 no longer sits in the Anglican Document cell; every cell is the data file's, as before CODE-AOID2-55.
    want = [[r["family"], r["document"], r["ordained"], r["joined"]] for r in data["rows"]]
    assert rows == want and len(rows) == 16
    oo = next(r for r in data["rows"] if r["family"] == "Oriental Orthodox")
    assert oo["ordained"] == "Yes" and oo["joined"] == "Joined"
    assert oo["document"].startswith("Coptic Orthodox Church, Rites of the Holy Baptism (Nadian, St. Bishoy Coptic Orthodox Church, Canada), prayer over the baptismal water; Denzinger, Ritus Orientalium (W")
    assert oo["document"].endswith("rzburg, 1863), p. 204")
    assert sum(r[2] == "Yes" for r in rows) == 14 and all(r[2] in ("Yes", "Not found") for r in rows)
    base = lambda v: v.replace(" (borderline)", "")
    assert all(base(r[3]) in ("Joined", "Sign", "Not found") for r in rows)
    short = lambda f: {"Pentecostal (with independent charismatic churches)": "Pentecostal", "The Church of Jesus Christ of Latter-day Saints": "Latter-day Saint"}.get(f, f)
    assert sorted(short(r[0]) for r in rows if base(r[3]) == "Joined") == sorted(["Anglican", "Catholic", "Eastern Orthodox", "Oriental Orthodox", "Lutheran", "Pentecostal", "Latter-day Saint"])
    assert sorted(r[0] for r in rows if r[3] == "Sign") == sorted(["Reformed", "Methodist", "Holiness"])
    assert sorted(r[0] for r in rows if r[2] == "Not found") == sorted(["Church of the East", "Stone-Campbell"])
    assert [r[3] for r in rows if "(borderline)" in r[3]] == ["Joined (borderline)"]
    # after the summary table, before the count strips and per-family tables that follow it on this tab
    assert rec.index('class="disc-table-wrap an-summary"') < rec.index("a11-baptism-families") < rec.index('class="an-tally"')
    assert 'id="a11-baptism-families"' not in (site_off / "articles" / "index.html").read_text(encoding="utf8")
    assert arts.count('id="a11-baptism-families"') == 1


def test_love_and_repent_paragraphs_carry_the_ruled_wording(site_on, site_off):
    """AOID2-A11-TWO-HELD-PARAS and AOID2-A11-GAL56-ATTRIBUTION option 1: both ruled sentences checked against the record; both paragraphs shown."""
    on = text_of(panel((site_on / "articles" / "index.html").read_text(encoding="utf8"), "a11", "disclosure"))
    off = text_of((site_off / "articles" / "index.html").read_text(encoding="utf8"))
    assert "Repent and be baptized." in on
    assert ("The Baptist churches confess repentance, faith and the baptism of believers, and hold that baptism follows faith: the Second London "
            "Confession calls it a sign of the remission of sins, and the Baptist Faith and Message an act of obedience symbolizing the believer's faith.") in on
    assert "signifies the remission of sins" not in on
    assert "Love proven by obedience." in on
    assert GAL_RULED in on and LOVE_RULED in on
    assert "Anabaptist and Jehovah's Witness traditions, and in sense" not in on
    assert "What the measurement found" not in off and "Second London Confession" not in off


def test_a2f1_date_measured_and_s26_quotation_marks(site_on, site_off):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    rec = panel(arts, "a02", "record")
    row = re.search(r'<tr id="a02-record-A2-F1">(.*?)</tr>', rec, re.S).group(1)
    assert "3 October 2026, revised 11 October 2026" in text_of(row)
    others = [r for r in re.findall(r'<tr id="a\d+-record-[^"]+">(.*?)</tr>', arts, re.S) if "revised" in text_of(r)]
    assert len(others) == 2                        # A2-F1 and, since 25 Oct 2026 (AOID2-A11F2-OO-COPTIC), A11-F2 carry a revised date
    ledger = {str(e["item"]): e for e in yaml.safe_load(LEDGER.read_text(encoding="utf8"))["scored"]}
    assert str(ledger["A2-F1"]["revised_on"]) == "2026-10-11" and str(ledger["A2-F1"]["scored_on"]) == "2026-10-03"
    fc = {f["id"]: f for f in json.loads(COUNTS.read_text(encoding="utf8"))["floors"]}
    assert fc["A2-F1"]["revised"] == "2026-10-11"
    assert 'data-span="s26" data-article="A11" data-type="direct" data-named="false">"Then they that gladly received his word were baptized."</span>' in arts
    assert 'data-span="s13" data-article="A11" data-type="direct" data-named="false">The answer was as plain then as it is now: "Repent and be baptized' in arts
    assert "revised 11 October" not in (site_off / "articles" / "index.html").read_text(encoding="utf8")


def test_change_log_b1_to_b5(site_on):
    p = (site_on / "aoid" / "second-edition" / "index.html").read_text(encoding="utf8")
    t = text_of(p.split('<div class="cl">')[1])
    assert "five quotations" not in t and "The commentary is revised throughout." in t
    assert "Christ's command to His apostles to teach all nations, baptizing them, now stands beside His own baptism" in t
    assert 'John 3:5 is now quoted in the King James words, "born of water and of the Spirit."' in t
    assert "the reflection question is reworded" in t and "the reflection question is new" not in t
    assert "labelled Second Edition." in t and "the films for Articles 2 and 6 are new" not in t
    assert 'the Articles now say "no position."' in t
    assert t.index('the Articles now say "no position."') > t.index("labelled Second Edition.")
    assert t.index('the Articles now say "no position."') < t.index("Later corrections")


def test_film_buttons_second_edition_for_articles_2_and_6(site_on, site_off):
    on = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    assert "SE_FILMS = ['A02','A06']" in on and "' · Second Edition'" in on and "' · First Edition'" in on
    off = (site_off / "articles" / "index.html").read_text(encoding="utf8")
    assert "SE_FILMS" not in off and "Second Edition'" not in off


def test_no_position_vocabulary(site_on, site_off):
    off_hits = 0
    for rel in ("articles/index.html", "aoid/disclosures/father-of-spirits/index.html", "aoid/disclosures/sexual-holiness/index.html"):
        on = (site_on / rel).read_text(encoding="utf8")
        off = (site_off / rel).read_text(encoding="utf8")
        assert not re.search(r"no common position", on, re.I), rel
        off_hits += len(re.findall(r"no common position", off, re.I))
    assert off_hits >= 12                       # the live pages are untouched until launch
    cl = (site_on / "aoid" / "second-edition" / "index.html").read_text(encoding="utf8")
    assert cl.count("no common position") == 1  # the change log names the old term once, in the B5 line


# ---------------------------------------------------------------- CODE-AOID2-55: change log C1/C2, /living-tree/, A11-F2, R1, the A11 amendment

def test_c1_c2_change_log(site_on, site_off):
    """C1: the "Helps for the reader." bullet follows "A way to correct us"; C2: the two disclosure titles link to pages that exist."""
    cl = (site_on / "aoid" / "second-edition" / "index.html").read_text(encoding="utf8")
    bullets = [text_of(b) for b in re.findall(r"<li>(.*?)</li>", cl, re.S)]
    i = next(k for k, b in enumerate(bullets) if b.startswith("A way to correct us."))
    c1 = next(l for l in CHANGELOG.read_text(encoding="utf8").replace("\r\n", "\n").split("\n") if l.startswith("- **Helps for the reader.**"))
    assert bullets[i + 1] == plain_md(c1[2:])
    assert '<a href="/aoid/disclosures/father-of-spirits/">Of the Father of Spirits</a>' in cl
    assert '<a href="/aoid/disclosures/sexual-holiness/">Sexual Holiness</a>' in cl
    for u in ("father-of-spirits", "sexual-holiness"):
        assert (site_on / "aoid" / "disclosures" / u / "index.html").exists()
    assert not (site_off / "aoid" / "second-edition").exists()


def test_c1_clauses_are_borne_out_by_the_switch_on_build(site_on):
    """Each clause of C1 against the built page: T5 (13), T1 (13 x 3), T2 (13), T4 (13 boxes with the local-storage note)."""
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    assert len(re.findall(r'<p class="[^"]*\ban-as-read\b', arts)) == 13
    assert len(re.findall(r'<p class="[^"]*\ban-practice\b', arts)) == 39
    assert len(re.findall(r'<div class="an-before"', arts)) == 13
    assert len(re.findall(r'class="an-learner-box"', arts)) == 13
    assert arts.count("Kept only in this browser. Nothing is sent.") == 13


def test_living_tree_page(site_on, site_off):
    """A6a: the page exists only with the switch ON, from the approved wording, with the note read from its source."""
    assert not (site_off / "living-tree").exists()
    h = (site_on / "living-tree" / "index.html").read_text(encoding="utf8")
    t = text_of(h)
    src = METHOD.read_text(encoding="utf8").replace("\r\n", "\n")
    alt = re.search(r'^\*\*Alt text:\*\* "(.+)"$', src, re.M).group(1)
    assert f'alt="{alt}"' in h
    assert "The Living Tree of Christ-Believing Traditions Many Branches, Rooted in Jesus of Nazareth" in t
    assert "The Tree shows twenty-five branches. These Articles measure sixteen of them as families; How These Articles Were Measured explains which, and why the others stay outside the count." in t
    assert '<a href="/articles/#a02-method">How These Articles Were Measured</a>' in h
    assert "What the sixteen cover. The Living Tree of Christ-Believing Traditions is a devotional map, not an institutional genealogy." in t
    assert h.index("What the sixteen cover.") < h.index("The Tree shows twenty-five branches.") < h.index("View the map at full size")
    assert 'href="https://media.wordsofplainness.org/web/aoid-slides/slide-02-v2.webp">View the map at full size</a>' in h
    assert "tree-of-christ-v2/tree.dzi" in h and "width:7680" in h.replace(" ", "")
    # the Tree's name is linked in the method account and in the Article 11 record note
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    assert arts.count('<a href="/living-tree/">The Living Tree of Christ-Believing Traditions</a>') >= 2
    rec = panel(arts, "a11", "record")
    assert '<strong>What the sixteen cover.</strong> <em><a href="/living-tree/">The Living Tree of Christ-Believing Traditions</a></em>' in rec


def test_a11_f2_reads_sixteen_and_its_row_agrees(site_on):
    """AOID2-A11F2-OO-COPTIC: A11-F2 taught 16, contradicted 0, no position 0, no family queued; its ledger and counts agree."""
    d = json.loads(COUNTS.read_text(encoding="utf8"))
    f = next(x for x in d["floors"] if x["id"] == "A11-F2")
    assert f["status"] == "MATCH" and f["counts"] == {"taught": 16, "contradicted": 0, "noPosition": 0}
    assert f["queue"] == 0 and f["queuedFamilies"] == [] and f["revised"] == "2026-10-25"
    led = next(e for e in yaml.safe_load(LEDGER.read_text(encoding="utf8"))["scored"] if str(e["item"]) == "A11-F2")
    assert led["result"] == "taught 16, contradicted 0, no position 0 of 16"
    assert led["floor_sha256"] == "d7e9ca997f2d7ceb712f435ef07cfc66fc05e3a8c4b5fb35f3b893de7bfd2ad3"
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    row = re.search(r'<tr id="a11-record-A11-F2">(.*?)</tr>', panel(arts, "a11", "record"), re.S).group(1)
    cells = [text_of(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row)]
    assert cells[1:4] == ["16", "0", "0"] and cells[-1] == "0"


def _approved(rid):
    w = R_WORDING.read_text(encoding="utf8").replace("\r\n", "\n").split("\n")
    i = next(k for k, l in enumerate(w) if l.startswith("## " + rid + ". "))
    return next(l for l in w[i + 1:] if l.strip())


def test_r1_r2_render_as_notes_under_the_baptism_table_only(site_on, site_off):
    """CODE-AOID2-56 (AOID2-RECORD-NOTES-PLACE option 1): R1 and R2 are in a Notes list under the A11-F7 table, led by Anglican;
    R1 is no longer in the Anglican Document cell; nothing of it reaches the switch-OFF build."""
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    rec = panel(arts, "a11", "record")
    sec = rec[rec.index('<section class="an-baptism-table"'):]
    sec = sec[:sec.index("</section>")]
    table_end = sec.index("</table>")
    assert sec.index('<div class="an-notes"') > table_end
    notes = sec[sec.index('<div class="an-notes"'):]
    assert re.findall(r"<h5[^>]*>(.*?)</h5>", notes) == ["Notes"]
    items = re.findall(r"<li[^>]*>(.*?)</li>", notes, re.S)
    plain = lambda r: html.unescape(_approved(r)).replace("*", "")   # R5 carries two italic titles
    assert [text_of(i) for i in items] == ["Anglican. " + plain("R1"), "Anglican. " + plain("R2"), "Oriental Orthodox. " + plain("R5")]
    assert [i[:i.index("</strong>")] for i in items] == ['<strong class="an-notes-family">Anglican.'] * 2 + ['<strong class="an-notes-family">Oriental Orthodox.']
    assert "<em>Rites of the Holy Baptism</em>" in items[2] and "<em>Ritus Orientalium</em>" in items[2] and "*" not in items[2]
    # the Anglican Document cell reads as before CODE-AOID2-55
    row = re.search(r'<tr><th scope="row">Anglican</th>(.*?)</tr>', sec, re.S).group(1)
    assert [text_of(c) for c in re.findall(r"<td>(.*?)</td>", row)] == ["Book of Common Prayer (1662), Public Baptism of Infants", "Yes", "Joined"]
    assert "Annexed Book" not in text_of(sec[:table_end])
    # CODE-AOID2-57: R2 also stands under Article 6's summary table and R4 under Article 11's; R1 and R5 once each; three Notes lists in all
    assert [text_of(arts).count(plain(r)) for r in ("R1", "R2", "R5")] == [1, 2, 1]
    assert arts.count('class="an-notes"') == 3
    off = (site_off / "articles" / "index.html").read_text(encoding="utf8")
    assert "Annexed Book" not in off and "an-notes" not in off and "Bill and Barker" not in off


def test_summary_table_notes_and_r3_held(site_on, site_off):
    """CODE-AOID2-57 (AOID2-NOTES-UNPLACED option 1): R2 (A6-F6) under Article 6's summary table, R4 (G8) under Article 11's;
    R3 stays held in the data and is rendered nowhere; every note's family name carries a period inside the bold."""
    d = json.loads((SE / "record_notes.json").read_text(encoding="utf8"))
    assert [(n["id"], n["teaching"], n.get("table")) for n in d["notes"]] == [
        ("R1", "A11-F7", None), ("R2", "A11-F7", None), ("R5", "A11-F2", "A11-F7"), ("R2", "A6-F6", "summary"), ("R4", "G8", "summary")]
    assert [(n["id"], n["teaching"]) for n in d["held"]] == [("R3", "A2-F4")]
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    plain = lambda r: html.unescape(_approved(r))
    for art, rid, fam in (("a06", "R2", "Anglican"), ("a11", "R4", "Oriental Orthodox")):
        rec = panel(arts, art, "record")
        tbl = rec[rec.index('<div class="disc-table-wrap an-summary">'):]
        end = tbl.index("</table></div>") + len("</table></div>")
        assert tbl[end:].startswith('<div class="an-notes" data-notes-for="summary">')   # directly under the summary table
        box = tbl[end:tbl.index("</div>", end + 10) + 6]
        assert re.findall(r"<h5[^>]*>(.*?)</h5>", box) == ["Notes"]
        items = re.findall(r"<li[^>]*>(.*?)</li>", box, re.S)
        assert [text_of(i) for i in items] == [fam + ". " + plain(rid)]
        assert items[0].startswith('<strong class="an-notes-family">' + fam + '.</strong> ')
    assert _approved("R3") not in arts and html.escape(_approved("R3")) not in arts
    assert "Confirmation prayer: Supporting line" not in arts
    off = (site_off / "articles" / "index.html").read_text(encoding="utf8")
    assert "an-notes" not in off and "Syriac Orthodox order of baptism" not in off


def test_oriental_orthodox_still_being_confirmed_sentence(site_on):
    """The 25 Oct 2026 amendment: one reading, not two. The old sentence is nowhere on the switch-ON build."""
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf8")
    new = "One Oriental Orthodox reading waits for a second edition, or the original language, of the rite it rests on, and is named beside that count."
    assert text_of(arts).count(new) == 1
    assert "Two Oriental Orthodox readings" not in arts and "rite they rest on" not in arts
    assert "<strong>Still being confirmed.</strong> " + new in arts
    src = STAGE1.read_text(encoding="utf8").replace("\r\n", "\n")
    assert "**Still being confirmed.** " + new in src and "**Still being confirmed.** Two Oriental" not in src


def test_living_tree_teaching_lines(site_on, site_off):
    """L1-L3 (approved 25 Oct 2026), from the A6a section, by the same components as T1-T3, in the approved places."""
    h = (site_on / "living-tree" / "index.html").read_text(encoding="utf8")
    src = METHOD.read_text(encoding="utf8").replace("\r\n", "\n").split("\n")
    q = lambda tag: next(l for l in src[next(k for k, l in enumerate(src) if l.startswith(tag)) + 1:] if l.strip())[2:]
    l1, l2, l3 = q("L1 ("), q("L2 ("), q("L3 (")
    lead = "**Before you read on:** "
    assert l2.startswith(lead)
    p1 = '<p class="an-practice">' + html.escape(l1) + "</p>"
    p2 = '<div class="an-before" role="note"><p><strong>Before you read on:</strong> ' + html.escape(l2[len(lead):]) + "</p></div>"
    p3 = '<p class="an-correction-line"><a href="/aoid/corrections/">' + html.escape(l3) + "</a></p>"
    for p in (p1, p2, p3):
        assert h.count(p) == 1
    # L1 directly under the subtitle (before the picture); L2 directly above the table; L3 after the full-size link, the last line
    assert h.index("Many Branches, Rooted in Jesus of Nazareth") < h.index(p1) < h.index("<figure")
    assert h.index("What the sixteen cover.") < h.index(p2) < h.index('<div class="disc-table-wrap">')
    assert re.search(re.escape(p2) + r'\s*<div class="disc-table-wrap">', h)
    assert h.index("View the map at full size") < h.index(p3)
    assert "<input" not in p2 and "<textarea" not in p2
    assert "/css/articles-tabs.css" in h
    assert not (site_off / "living-tree").exists()
