"""Tests for the AoID reader corrections form, /aoid/corrections/ (CODE-AOID2-47, step 88).

Switch OFF: the page and every link to it are absent. Switch ON: the page shows the approved wording and the
eight fields, pre-fills field 3 from ?article= and ?floor=, blocks a filled honeypot, and builds the request
body in the fixed layout. The API client is stubbed in the browser and every request to the live API host is
aborted, so no submission is ever sent.

Run: python -m pytest scripts/aoid_tests/test_corrections_form.py
"""
import functools
import http.server
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "data-sources" / "aoid" / "second-edition" / "WoP_AOID2_Step88_CorrectionsForm_Spec_Draft_v1_20261019.md"
API_HOST = "pythonanywhere.com"
LINK_TEXT = "Has your church's text been misread or missed? Tell us."


def build(out, on):
    env = {k: v for k, v in os.environ.items() if k != "WOP_AOID2_SECOND_EDITION"}
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


@pytest.fixture
def page(browser, server):
    ctx = browser.new_context(service_workers="block")
    attempted = []

    def guard(route):
        if API_HOST in route.request.url:
            attempted.append(route.request.url)
            route.abort()
        else:
            route.continue_()

    ctx.route("**/*", guard)
    pg = ctx.new_page()
    pg.attempted = attempted
    yield pg
    ctx.close()


def part1():
    text = SPEC.read_text(encoding="utf-8").replace("\r\n", "\n")
    return text.split("## Part 2")[0].split("## Part 1")[1]


def stub_api(pg):
    pg.evaluate("window.__sent = []; window.API.submitContact = async (d) => { window.__sent.push(d); return {}; }; 0")


def fill_valid(pg):
    pg.select_option("#cf-tradition", "Lutheran")
    pg.fill("#cf-church", "Lutheran Church–Missouri Synod")
    pg.fill("#cf-citation", "Augsburg Confession, Article VII")
    pg.fill("#cf-link", "https://example.org/augsburg")
    pg.fill("#cf-note", "The text says X.\nSecond line.")
    pg.fill("#cf-name", "A Reader")
    pg.fill("#cf-email", "reader@example.org")


def submit_after_delay(pg):
    pg.evaluate("document.querySelector('[name=loaded_at]').value = String(Date.now() - 10000)")
    pg.click("#cfSubmit")


# ---- switch OFF --------------------------------------------------------------------------

def test_switch_off_has_no_page_and_no_link(site_off):
    assert not (site_off / "aoid" / "corrections").exists()
    for f in site_off.rglob("*.html"):
        s = f.read_text(encoding="utf-8", errors="replace")
        assert "/aoid/corrections" not in s, f
        assert LINK_TEXT not in s, f


# ---- switch ON ---------------------------------------------------------------------------

def test_every_article_and_disclosure_page_links_to_the_form(site_on):
    arts = (site_on / "articles" / "index.html").read_text(encoding="utf-8")
    for n in range(1, 14):
        assert len(re.findall(rf'href="/aoid/corrections/\?article={n}(?:"|&amp;)', arts)) == 2, n  # Disclosure tab and Record tab
    assert 'href="/aoid/corrections/?article=2&amp;floor=A2-F1"' in arts
    assert 'href="/aoid/corrections/?article=11&amp;floor=29a,29b"' in arts
    assert arts.count(LINK_TEXT.replace("'", "&#39;")) + arts.count(LINK_TEXT) == 26
    for slug, n in (("father-of-spirits", 2), ("sexual-holiness", 11)):
        s = (site_on / "aoid" / "disclosures" / slug / "index.html").read_text(encoding="utf-8")
        assert f'href="/aoid/corrections/?article={n}"' in s


def test_page_shows_the_approved_wording_and_eight_fields(page, server):
    page.goto(server + "/aoid/corrections/")
    body = page.inner_text("body")
    p1 = part1()
    for key in ("Page title: ", "Privacy line (above the button): ", "Success message: ", "Failure message: ", "Button: "):
        want = re.search("^" + re.escape(key) + "(.+)$", p1, re.M).group(1)
        assert want in page.content().replace("&#39;", "'").replace("&quot;", '"') or want in body, want
    for head in ("Intro:", "What happens next:", "What we can weigh:"):
        want = p1.split(head)[1].strip().split("\n")[0]
        assert want in body, want
    fields = re.findall(r"^\d\. (.+)$", p1.split("Fields")[1].split("Privacy line")[0], re.M)
    assert len(fields) == 8
    for f in fields:
        left, _, helper = f.partition(" / ")
        label = left.split(" (")[0]
        assert label in body, label
        if helper:
            assert helper in body, helper
    ids = ["cf-tradition", "cf-church", "cf-teaching", "cf-citation", "cf-link", "cf-note", "cf-name", "cf-email"]
    assert page.eval_on_selector_all("#cfForm [id^=cf-]:not([id$=hint])", "els => els.map(e => e.id)") == ids
    for i in ids:
        assert page.query_selector(f'label[for="{i}"]')
    req = {i: page.get_attribute("#" + i, "required") is not None for i in ids}
    assert req == {"cf-tradition": True, "cf-church": False, "cf-teaching": False, "cf-citation": True,
                   "cf-link": False, "cf-note": True, "cf-name": False, "cf-email": False}
    opts = page.eval_on_selector_all("#cf-tradition option", "os => os.map(o => o.textContent)")
    assert len(opts) == 1 + 16 + 1 and opts[-1] == "Another tradition"
    assert "Eastern Orthodox" in opts and "Holiness" in opts and "Jehovah's Witnesses" in opts


def test_prefill_from_query(page, server):
    page.goto(server + "/aoid/corrections/?article=11&floor=29a,29b")
    v = page.input_value("#cf-teaching")
    assert v.startswith("Article 11: ") and "(29a)" in v and "(29b)" in v
    page.goto(server + "/aoid/corrections/?article=2&floor=A2-F1")
    assert page.input_value("#cf-teaching") == "Article 2: Father of our spirits (A2-F1)"
    page.goto(server + "/aoid/corrections/?article=4")
    assert page.input_value("#cf-teaching") == "Article 4"
    for bad in ("?article=99", "?article=x", "?floor=A2-F1", "?article=<b>", "?article=4&floor=A2-F1"):
        page.goto(server + "/aoid/corrections/" + bad)
        assert page.input_value("#cf-teaching") in ("", "Article 4"), bad
    page.goto(server + "/aoid/corrections/")
    assert page.input_value("#cf-teaching") == ""


def test_filled_honeypot_blocks_sending(page, server):
    page.goto(server + "/aoid/corrections/")
    stub_api(page)
    fill_valid(page)
    page.evaluate("document.querySelector('[name=website]').value = 'http://spam.example'")
    submit_after_delay(page)
    assert page.evaluate("window.__sent.length") == 0
    assert page.is_visible("#cfForm") and not page.is_visible("#cfSuccess") and not page.is_visible("#cfFailure")


def test_too_fast_submission_is_blocked(page, server):
    page.goto(server + "/aoid/corrections/")
    stub_api(page)
    fill_valid(page)
    page.click("#cfSubmit")
    assert page.evaluate("window.__sent.length") == 0


def test_required_fields_block_sending(page, server):
    page.goto(server + "/aoid/corrections/")
    stub_api(page)
    submit_after_delay(page)
    assert page.evaluate("window.__sent.length") == 0
    assert page.evaluate("document.activeElement.id") == "cf-tradition"


def test_request_body_layout_and_success(page, server):
    page.goto(server + "/aoid/corrections/?article=2&floor=A2-F1")
    stub_api(page)
    fill_valid(page)
    submit_after_delay(page)
    sent = page.evaluate("window.__sent")
    assert len(sent) == 1
    assert sent[0] == {
        "name": "A Reader",
        "email": "reader@example.org",
        "submission_type": "general",
        "subject": "AoID correction: Lutheran",
        "message": "Tradition: Lutheran\n"
                   "Church: Lutheran Church–Missouri Synod\n"
                   "Teaching: Article 2: Father of our spirits (A2-F1)\n"
                   "Citation: Augsburg Confession, Article VII\n"
                   "Link: https://example.org/augsburg\n"
                   "Note: The text says X.\nSecond line.",
    }
    assert page.is_visible("#cfSuccess") and not page.is_visible("#cfForm")
    assert page.attempted == []


def test_optional_fields_empty(page, server):
    page.goto(server + "/aoid/corrections/")
    stub_api(page)
    page.select_option("#cf-tradition", "Another tradition")
    page.fill("#cf-citation", "Some Confession 3")
    page.fill("#cf-note", "It says Y.")
    submit_after_delay(page)
    sent = page.evaluate("window.__sent")[0]
    assert sent["subject"] == "AoID correction: Another tradition"
    assert sent["name"] == "Anonymous" and sent["email"].endswith("@aoid.invalid")
    assert sent["message"].split("\n") == [
        "Tradition: Another tradition", "Church: (not given)", "Teaching: (not given)",
        "Citation: Some Confession 3", "Link: (not given)", "Note: It says Y."]


def test_failure_message_when_api_rejects_or_is_missing(page, server):
    page.goto(server + "/aoid/corrections/")
    fill_valid(page)
    page.evaluate("window.API.submitContact = async () => { throw new Error('boom'); }; 0")
    submit_after_delay(page)
    assert page.is_visible("#cfFailure") and page.is_visible("#cfForm") and not page.is_visible("#cfSuccess")
    assert page.input_value("#cf-citation") == "Augsburg Confession, Article VII"
    page.evaluate("document.getElementById('cfFailure').classList.add('hidden'); delete window.API.submitContact")
    submit_after_delay(page)
    assert page.is_visible("#cfFailure")
    assert page.attempted == []


def test_nothing_stored_on_the_device(page, server):
    page.goto(server + "/aoid/corrections/")
    stub_api(page)
    before = page.evaluate("JSON.stringify(Object.entries(localStorage))")
    fill_valid(page)
    submit_after_delay(page)
    assert page.evaluate("JSON.stringify(Object.entries(localStorage))") == before
