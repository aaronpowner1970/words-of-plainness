"""Acceptance checks for the device-only journal (spec Part 7, checks 1-10), CODE-SITE-18, SITE step 27.

Runs in real browsers against locally served builds (Playwright Chromium and WebKit; the installed
Firefox through Selenium, because Playwright's own Firefox build does not start on this machine;
headed Chrome and Edge for the Document Picture-in-Picture pop-out). Forms are tested with the
API stubbed at the network layer: no real submission is ever sent.

Usage (local):
  python scripts/site_tests/journal_acceptance.py --site _site --site-on <switch-ON build>
      --baseline <baseline build> --baseline-on <baseline switch-ON build>
      --approved <WoP_SITE_UTH_Privacy_Wording_Approved_*.md> --spec <WoP_SITE_JournalDeviceOnly_Spec_*.md>
      --out <evidence dir> [--checks 1,2,...]
Usage (production, checks 1 and 9 only):
  python scripts/site_tests/journal_acceptance.py --prod https://www.wordsofplainness.org --out <dir> --checks 1,9
"""
import argparse
import functools
import html
import http.server
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from network_allowlist import classify_page_load, classify_action, is_api_host, host_of  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

API_PATTERN = re.compile(r"https://apowner\.pythonanywhere\.com/.*")
CHECK9_STRINGS = ["Join Free", "Sign In", "create an account", "across devices"]
CHECK9_EXCEPTION = "posts/2026-04-12-your-journal-is-ready/index.html"
NONASCII_SAMPLE = "Grace “received” — naïve café; Ἰησοῦς"
RESULTS = {}


# ---------------------------------------------------------------- serving
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass


def serve(directory):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def write(out, name, data):
    p = Path(out) / name
    if isinstance(data, (dict, list)):
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        p.write_text(str(data), encoding="utf-8")
    return p.name


def record(check, passed, summary, evidence):
    RESULTS[check] = {"pass": bool(passed), "summary": summary, "evidence": evidence}
    print(f"CHECK {check}: {'PASS' if passed else 'FAIL'} - {summary}", flush=True)


# ---------------------------------------------------------------- reader actions per page
def set_value(page, selector, text):
    """Type into a field the way a reader does (focus, value, input event)."""
    page.locator(selector).first.fill(text)


def open_panel(page):
    if page.locator("#wopReflectionsPanel").is_hidden():
        page.click(".wop-rp-tab")
    page.wait_for_selector("#wopReflectionsPanel:not([hidden])")


def close_panel(page):
    if page.locator("#wopReflectionsPanel").is_visible():
        page.click("#wopReflectionsPanel .wop-rp-close")


def write_question(page, text):
    open_panel(page)
    page.fill("#wopRpQuestion", text)
    page.wait_for_timeout(800)
    page.click("#wopReflectionsPanel >> text=Save question")


def download_all(page, out_dir, scope="page", prefix=""):
    files = []
    if page.locator("#wopReflectionsPanel").count():
        open_panel(page)
        page.check("#wopRpScopeAll" if scope == "all" else "#wopRpScopePage")
        container = "#wopReflectionsPanel"
    else:
        container = "#djActions"
    for fmt in ["md", "txt", "docx", "pdf"]:
        with page.expect_download(timeout=90000) as d:
            page.click(f'{container} [data-format="{fmt}"]')
        dl = d.value
        name = (prefix + dl.suggested_filename) if prefix else dl.suggested_filename
        path = Path(out_dir) / name
        dl.save_as(str(path))
        files.append(str(path))
        page.wait_for_timeout(300)
    return files


def confirm_clear(page):
    container = "#wopReflectionsPanel" if page.locator("#wopReflectionsPanel").count() else "#djActions"
    if container == "#wopReflectionsPanel":
        open_panel(page)
    page.click(f"{container} .wop-rp-clear")
    text = page.inner_text(f"{container} .wop-rp-confirm-text")
    page.click(f"{container} .wop-rp-btn--danger")
    page.wait_for_timeout(300)
    return text


def act_chapter_rjw(page, pause, edit_text):
    page.evaluate(f"RJW.openModal('{pause}', 'reflect')")
    set_value(page, "#reflect-ta", "Reflect: " + NONASCII_SAMPLE)
    page.evaluate("RJW.switchTab('journal')")
    set_value(page, "#journal-ta", "Journal: what I am carrying")
    page.evaluate("RJW.switchTab('witness')")
    set_value(page, "#witness-ta", "Witness: I knew He lives")
    page.check("#cb-document")
    page.evaluate("RJW.switchTab('journal')")
    set_value(page, "#journal-ta", edit_text)          # edit
    page.evaluate("RJW.closeModal()")
    page.wait_for_timeout(300)


def act_card(page, edit_text):
    # The commitment and the reflection sit on the card's "How Will You Practice?" tab.
    if not page.locator('.card-tab[data-card="1"][data-tab="personalize"].active').count():
        page.click('.card-tab[data-card="1"][data-tab="personalize"]')
    panel = '.card-panel[data-card="1"][data-panel="personalize"]'
    page.locator(panel + " .commitment-option").first.click()
    page.locator('.card-save-btn[data-card="1"]').click()
    set_value(page, panel + " .reflection-area", "Card reflection: " + NONASCII_SAMPLE)
    page.wait_for_timeout(800)
    set_value(page, panel + " .reflection-area", edit_text)      # edit
    page.wait_for_timeout(800)


def act_articles(page, edit_text):
    set_value(page, '.rjw-textarea[data-rjw-key="rjw-A01"]', "Article reflection: " + NONASCII_SAMPLE)
    page.wait_for_timeout(800)
    set_value(page, '.rjw-textarea[data-rjw-key="rjw-A01"]', edit_text)   # edit
    page.wait_for_timeout(800)


def act_sjn_selfcheck(page, edit_text):
    page.fill("#sj-goal-text", "Listen before I answer")
    page.click("#sj-goalform button[type=submit]")
    page.click("#sj-goals-journal")
    page.wait_for_timeout(300)
    write_question(page, edit_text)


# ---------------------------------------------------------------- check 1: network
def prep_scroll_to(selector, click_first=None):
    """Reading, not writing: bring the field into view the way a reader would, and let
    whatever the page loads for that part of the page (lazy images) finish first."""
    def prep(page):
        if click_first:
            page.click(click_first)
        page.locator(selector).first.scroll_into_view_if_needed()
        page.wait_for_timeout(2500)
    return prep


CHECK1_PAGES = [
    ("/chapters/11-the-living-christ/", "chapter with R·J·W pauses", None, lambda p: act_chapter_rjw(p, "pause-closing", "Journal (edited)")),
    ("/chapters/12-beatitudes/", "card chapter",
     prep_scroll_to('.card-panel[data-card="1"][data-panel="personalize"] .reflection-area', '.card-tab[data-card="1"][data-tab="personalize"]'),
     lambda p: act_card(p, "Card reflection (edited)")),
    ("/chapters/06-embrace-the-savior/", "Chapter 6", None, lambda p: act_chapter_rjw(p, "pause-skeptic", "Ch6 journal (edited)")),
    ("/articles/", "/articles/", prep_scroll_to('.rjw-textarea[data-rjw-key="rjw-A01"]'), lambda p: act_articles(p, "Article reflection (edited)")),
    ("/seeking-jesus/", "/seeking-jesus/", None, lambda p: write_question(p, "SJN question (edited)")),
    ("/seeking-jesus/self-check/", "/seeking-jesus/self-check/", prep_scroll_to("#sj-goal-text"), lambda p: act_sjn_selfcheck(p, "SJN self-check question")),
    ("/my-reflections/", "/my-reflections/", None, None),
]


def check1(pw, base, out, label="local"):
    browser = pw.chromium.launch()
    report = []
    ok_all = True
    dl_dir = Path(out) / f"check1_{label}_downloads"
    dl_dir.mkdir(exist_ok=True)
    for path, name, prepare, action in CHECK1_PAGES:
        ctx = browser.new_context(accept_downloads=True)
        reqs = []
        phase = {"v": "load"}

        def on_req(r, reqs=reqs, phase=phase):
            try:
                frame_url = r.frame.url if r.frame else ""
            except Exception:
                frame_url = ""
            try:
                post = r.post_data
            except Exception:
                post = None
            reqs.append({"phase": phase["v"], "url": r.url, "frame": frame_url, "post": post,
                         "main": bool(r.frame and r.frame.parent_frame is None) if r.frame else True})
        ctx.on("request", on_req)
        page = ctx.new_page()
        page.goto(base + path, wait_until="load", timeout=90000)
        # Load lazily loaded content during the load phase (scroll the whole page once).
        page.evaluate("async () => { const h = document.documentElement.scrollHeight; for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }")
        page.wait_for_timeout(3000)
        html_text = page.content()
        embeds_yt = ("youtube.com" in html_text) or ("youtube-nocookie" in html_text)
        uses_osd = "openseadragon" in html_text.lower()
        if path == "/my-reflections/":
            # Something to download and clear on this page: one entry written on another page first.
            page.goto(base + "/chapters/11-the-living-christ/", wait_until="load")
            page.wait_for_timeout(1500)
            phase["v"] = "action"
            act_chapter_rjw(page, "pause-closing", "Journal for My Reflections")
            phase["v"] = "load"
            page.goto(base + path, wait_until="load")
            page.wait_for_timeout(2000)
        if prepare:
            prepare(page)
        phase["v"] = "action"
        t0 = len(reqs)
        if action:
            action(page)
        files = download_all(page, dl_dir, prefix=path.strip("/").replace("/", "_") + "__")
        clear_text = confirm_clear(page)
        page.wait_for_timeout(1500)
        phase["v"] = "done"
        load_bad, action_bad, action_frames = [], [], []
        for r in reqs:
            if is_api_host(r["url"]):
                (load_bad if r["phase"] == "load" else action_bad).append(r["url"])
                continue
            if r["phase"] == "load":
                ok, why = classify_page_load(r["url"], base, r["frame"], embeds_yt, uses_osd, r.get("post"))
                if not ok:
                    load_bad.append(f"{r['url']} ({why})")
            elif r["phase"] == "action":
                if not r["main"] and host_of(r["frame"]) not in ("127.0.0.1", host_of(base)):
                    # inside a third-party iframe (YouTube): not caused by a reader action
                    ok, _ = classify_page_load(r["url"], base, r["frame"], embeds_yt, uses_osd)
                    action_frames.append(r["url"])
                    if not ok:
                        action_bad.append(f"{r['url']} (third-party frame, not on allow-list)")
                    continue
                ok, why = classify_action(r["url"], base)
                if not ok:
                    action_bad.append(f"{r['url']} ({why})")
        action_offsite = sorted({r["url"] for r in reqs if r["phase"] == "action" and not r["url"].startswith(base)
                                 and not r["url"].startswith(("data:", "blob:"))})
        load_hosts = sorted({host_of(r["url"]) for r in reqs if r["phase"] == "load" and not r["url"].startswith(base)
                             and not r["url"].startswith(("data:", "blob:"))})
        page_ok = not load_bad and not action_bad
        ok_all = ok_all and page_ok
        report.append({"page": path, "what": name, "pass": page_ok, "page_load_offsite_hosts": load_hosts,
                       "embeds_youtube": embeds_yt, "uses_openseadragon": uses_osd,
                       "action_offsite_requests": action_offsite, "action_requests_from_third_party_frames": action_frames,
                       "page_load_failures": load_bad, "action_failures": action_bad,
                       "downloads": [Path(f).name for f in files], "clear_confirmation": clear_text,
                       "api_host_requests": [r["url"] for r in reqs if is_api_host(r["url"])],
                       "total_requests": len(reqs)})
        ctx.close()
    browser.close()
    ev = write(out, f"check1_network_{label}.json", report)
    record(f"1-{label}", ok_all, f"{sum(1 for r in report if r['pass'])}/{len(report)} pages pass", [ev, dl_dir.name])
    return report


# ---------------------------------------------------------------- check 2: each download opens
def word_text(path):
    ps = (
        "$ErrorActionPreference='Stop'; $w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        f"$d = $w.Documents.Open('{path}', $false, $true); $t = $d.Content.Text; $n = $d.Paragraphs.Count; "
        "$d.Close($false); $w.Quit(); "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Output (\"PARAGRAPHS=\" + $n); Write-Output $t"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=180)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def pdf_text(path):
    import fitz
    doc = fitz.open(path)
    return doc.metadata.get("title", ""), "\n".join(p.get_text() for p in doc), doc.page_count


def check2(pw, base, out):
    browser = pw.chromium.launch()
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    dl_dir = Path(out) / "check2_downloads"
    dl_dir.mkdir(exist_ok=True)
    # A realistic journal: R·J·W answers with witness, a card commitment and reflection,
    # an Articles reflection, a Seeking Jesus journal entry and two questions.
    page.goto(base + "/chapters/11-the-living-christ/")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_timeout(800)
    act_chapter_rjw(page, "pause-closing", "Journal: “what I am carrying” — and hoping for")
    write_question(page, "Why did Peter answer three times — and what does “feed” mean?")
    page.goto(base + "/chapters/12-beatitudes/")
    page.wait_for_timeout(800)
    act_card(page, "Card reflection: meekness isn’t weakness — it’s strength under God’s hand")
    page.goto(base + "/articles/")
    page.wait_for_timeout(1500)
    act_articles(page, "Article reflection: what I inherited — and what I have witnessed")
    page.goto(base + "/chapters/11-the-living-christ/")
    page.wait_for_timeout(800)
    page_files = download_all(page, dl_dir, "page", prefix="page__")
    all_files = download_all(page, dl_dir, "all", prefix="all__")
    model = page.evaluate("JSON.stringify(WopReflectionsPanel.exportModel(true))")
    write(out, "check2_export_model_all.json", json.loads(model))
    entries = json.loads(page.evaluate("JSON.stringify(wopReflections.loadAll())"))
    write(out, "check2_entries.json", entries)
    browser.close()

    m = json.loads(model)
    expect_title = "My Reflections — Words of Plainness"
    expect_date = m["dateLine"]
    witness_words = "Witness: I knew He lives"
    must = [expect_title, expect_date, "Chapter 11: The Living Christ", witness_words,
            "Reflect: " + NONASCII_SAMPLE, "Journal: “what I am carrying” — and hoping for",
            "Why did Peter answer three times — and what does “feed” mean?", "My questions",
            "Witness · Closing Reflection", "Reflect · Closing Reflection", "Journal · Closing Reflection",
            "Which of those three movements spoke most directly", "Written "]
    must_all = must + ["Articles of Interfaith Discipleship", "Article reflection: what I inherited — and what I have witnessed",
                       "Card reflection: meekness isn’t weakness — it’s strength under God’s hand",
                       "Is there a conviction you hold about God or faith"]
    results = []
    ok = True
    for f in page_files + all_files:
        p = Path(f)
        need = must_all if p.name.startswith("all__") else must
        info = {"file": p.name}
        if p.suffix in (".md", ".txt"):
            raw = p.read_bytes()
            text = raw.decode("utf-8-sig")
            info["opened_as"] = "UTF-8 text"
        elif p.suffix == ".docx":
            rc, so, se = word_text(str(p))
            text = so.replace("\r", "\n")
            info["opened_as"] = "Microsoft Word (COM automation, read-only)"
            info["word_exit"] = rc
            if rc != 0:
                info["word_error"] = se[-500:]
        else:
            title, text, pages = pdf_text(str(p))
            info["opened_as"] = f"PyMuPDF {__import__('fitz').__doc__.split()[1] if __import__('fitz').__doc__ else ''} reader".strip()
            info["pdf_title"] = title
            info["pdf_pages"] = pages
        norm = re.sub(r"[ \t]*\n[ \t]*", " ", text)
        norm = re.sub(r"\s+", " ", norm)
        missing = [s for s in need if re.sub(r"\s+", " ", s) not in norm]
        # The PDF font (pdfmake's Roboto) has no polytonic Greek: report it, do not hide it.
        if p.suffix == ".pdf":
            greek = [s for s in missing if "Ἰησοῦς" in s]
            missing = [s for s in missing if "Ἰησοῦς" not in s]
            probe = "Reflect: Grace “received” — naïve café;"
            info["pdf_polytonic_greek_rendered"] = "Ἰησοῦς" in norm
            if probe not in norm:
                missing.append(probe)
            info["pdf_note"] = "polytonic Greek not in the PDF font" if greek else ""
        info["missing"] = missing
        info["witness_labeled_separately"] = ("Witness · Closing Reflection" in norm and "Reflect · Closing Reflection" in norm
                                              and norm.index("Witness · Closing Reflection") != norm.index("Reflect · Closing Reflection"))
        info["pass"] = not missing and info["witness_labeled_separately"] and info.get("word_exit", 0) == 0
        ok = ok and info["pass"]
        (dl_dir / (p.name + ".opened.txt")).write_text(text, encoding="utf-8")
        results.append(info)
    names_ok = all(re.match(r"^(page|all)__My-Reflections_(11-the-living-christ|all)_\d{4}-\d{2}-\d{2}\.(md|txt|docx|pdf)$", Path(f).name) for f in page_files + all_files)
    ev = write(out, "check2_downloads.json", {"files": results, "file_names_as_specified": names_ok})
    record("2", ok and names_ok, f"{sum(r['pass'] for r in results)}/{len(results)} files open with title, prompts, words, dates, non-ASCII; witness labeled separately", [ev, dl_dir.name])
    return results


# ---------------------------------------------------------------- check 3: pop-out
def check3(pw, base, out):
    ev = {}
    ok = True
    # Chrome and Edge, headed (Document Picture-in-Picture is not exposed headless)
    for channel in ["chrome", "msedge"]:
        info = {}
        try:
            b = pw.chromium.launch(channel=channel, headless=False, args=["--window-position=40,40"])
            ctx = b.new_context(viewport={"width": 1280, "height": 860})
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base + "/chapters/11-the-living-christ/")
            page.evaluate("localStorage.clear()")
            page.reload()
            page.wait_for_timeout(800)
            info["version"] = b.version
            info["api_present"] = page.evaluate("'documentPictureInPicture' in window")
            open_panel(page)
            info["button_visible"] = page.is_visible("#wopReflectionsPanel .wop-rp-popout")
            page.click("#wopReflectionsPanel .wop-rp-popout")
            page.wait_for_function("() => window.documentPictureInPicture && documentPictureInPicture.window && documentPictureInPicture.window.document.getElementById('wopReflectionsPanel')", timeout=15000)
            info["panel_in_pip"] = page.evaluate("!!documentPictureInPicture.window.document.getElementById('wopReflectionsPanel')")
            info["panel_left_page"] = page.evaluate("!document.getElementById('wopReflectionsPanel')")
            info["pip_size"] = page.evaluate("[documentPictureInPicture.window.innerWidth, documentPictureInPicture.window.innerHeight]")
            # write a question inside the pop-out window
            page.evaluate("""() => { const d = documentPictureInPicture.window.document; const t = d.getElementById('wopRpQuestion');
                t.value = 'Written in the pop-out window'; t.dispatchEvent(new Event('input', {bubbles: true})); }""")
            page.wait_for_timeout(900)
            page.evaluate("documentPictureInPicture.window.close()")
            page.wait_for_function("() => !!document.getElementById('wopReflectionsPanel')", timeout=10000)
            page.wait_for_timeout(300)
            info["panel_back_in_page"] = page.evaluate("!!document.getElementById('wopReflectionsPanel') && !document.getElementById('wopReflectionsPanel').hidden")
            info["question_kept"] = page.evaluate("wopReflections.loadAll().some(e => e.type === 'question' && e.content === 'Written in the pop-out window')")
            info["question_text_still_in_box"] = page.evaluate("document.getElementById('wopRpQuestion').value")
            page.screenshot(path=str(Path(out) / f"check3_{channel}_after_popout.png"))
            info["page_errors"] = errors
            info["pass"] = all([info["api_present"], info["button_visible"], info["panel_in_pip"], info["panel_left_page"],
                                info["panel_back_in_page"], info["question_kept"], not errors])
            b.close()
        except Exception as e:  # noqa: BLE001
            info["error"] = str(e)[:500]
            info["pass"] = False
        ev[channel] = info
        ok = ok and info["pass"]
    # Absent cleanly: WebKit (Safari engine) and headless Chromium (API absent)
    for name, launcher in [("webkit", lambda: pw.webkit.launch()), ("chromium-headless", lambda: pw.chromium.launch())]:
        info = {}
        b = launcher()
        page = b.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/chapters/11-the-living-christ/")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(800)
        info["version"] = b.version
        info["api_present"] = page.evaluate("'documentPictureInPicture' in window")
        open_panel(page)
        info["button_visible"] = page.is_visible("#wopReflectionsPanel .wop-rp-popout")
        write_question(page, "In-page panel question")
        info["in_page_panel_works"] = page.evaluate("wopReflections.loadAll().some(e => e.type === 'question' && e.content === 'In-page panel question')") \
            and "In-page panel question" in page.inner_text("#wopReflectionsPanel .wop-rp-list")
        info["page_errors"] = errors
        page.screenshot(path=str(Path(out) / f"check3_{name}_panel.png"))
        # The button shows exactly when the browser offers the API; the in-page panel always works.
        info["pass"] = (info["button_visible"] == info["api_present"]) and info["in_page_panel_works"] and not errors
        if name == "webkit":
            info["pass"] = info["pass"] and not info["api_present"] and not info["button_visible"]
        ev[name] = info
        ok = ok and info["pass"]
        b.close()
    # Firefox (installed), through Selenium
    info = {}
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.common.by import By
        for headless in [True, False]:
            o = Options()
            if headless:
                o.add_argument("-headless")
            o.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
            d = webdriver.Firefox(options=o)
            d.set_window_size(1280, 860)
            d.get(base + "/chapters/11-the-living-christ/")
            d.execute_script("localStorage.clear()")
            d.get(base + "/chapters/11-the-living-christ/")
            time.sleep(1.5)
            key = "headless" if headless else "headed"
            info[key + "_version"] = d.capabilities.get("browserVersion")
            info[key + "_api_present"] = d.execute_script("return 'documentPictureInPicture' in window")
            d.find_element(By.CSS_SELECTOR, ".wop-rp-tab").click()
            time.sleep(0.3)
            btn = d.find_element(By.CSS_SELECTOR, "#wopReflectionsPanel .wop-rp-popout")
            info[key + "_button_visible"] = btn.is_displayed()
            ta = d.find_element(By.ID, "wopRpQuestion")
            ta.send_keys("Firefox in-page question")
            time.sleep(1.0)
            d.find_element(By.XPATH, "//button[normalize-space()='Save question']").click()
            time.sleep(0.3)
            info[key + "_in_page_panel_works"] = d.execute_script("return wopReflections.loadAll().some(e => e.type === 'question' && e.content === 'Firefox in-page question')")
            if not headless and info[key + "_api_present"]:
                # Firefox 151+ offers Document Picture-in-Picture: try the pop-out for real.
                try:
                    d.find_element(By.CSS_SELECTOR, "#wopReflectionsPanel .wop-rp-popout").click()
                    time.sleep(2.0)
                    info["headed_panel_in_pip"] = d.execute_script("return !!(window.documentPictureInPicture && documentPictureInPicture.window && documentPictureInPicture.window.document.getElementById('wopReflectionsPanel'))")
                    info["headed_panel_left_page"] = d.execute_script("return !document.getElementById('wopReflectionsPanel')")
                    d.execute_script("documentPictureInPicture.window && documentPictureInPicture.window.close()")
                    time.sleep(1.0)
                    info["headed_panel_back_in_page"] = d.execute_script("return !!document.getElementById('wopReflectionsPanel')")
                except Exception as e:  # noqa: BLE001
                    info["headed_popout_error"] = str(e)[:300]
            if headless:
                d.save_screenshot(str(Path(out) / "check3_firefox_panel.png"))
            d.quit()
        fx_ok = info["headed_in_page_panel_works"] and info["headless_in_page_panel_works"]
        # Pop out shows exactly when the browser offers the API (spec: Firefox 151+ where supported).
        fx_ok = fx_ok and (info["headed_button_visible"] == info["headed_api_present"]) and (info["headless_button_visible"] == info["headless_api_present"])
        info["pass"] = bool(fx_ok)
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)[:500]
        info["pass"] = False
    ev["firefox"] = info
    ok = ok and info["pass"]
    name = write(out, "check3_popout.json", ev)
    record("3", ok, "pop-out works in Chrome and Edge; absent cleanly where the API is absent; in-page panel works in all", [name])
    return ev


# ---------------------------------------------------------------- check 4: phone width
def rects_overlap(a, b):
    return not (a["right"] <= b["left"] or b["right"] <= a["left"] or a["bottom"] <= b["top"] or b["bottom"] <= a["top"])


def check4(pw, base, out):
    ev = {}
    ok = True
    for name, launcher, dev in [("chromium", pw.chromium, pw.devices["Pixel 7"]), ("webkit", pw.webkit, pw.devices["iPhone 13"])]:
        b = launcher.launch()
        ctx = b.new_context(**dev)
        page = ctx.new_page()
        page.goto(base + "/chapters/11-the-living-christ/")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(1000)
        res = {"viewport": page.viewport_size}
        res["hscroll_before"] = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        act_chapter_rjw(page, "pause-closing", "Phone journal")
        page.evaluate("ChapterManager.showAudioPlayer()")
        page.wait_for_timeout(500)
        open_panel(page)
        page.wait_for_timeout(500)
        res["panel"] = page.evaluate("(() => { const r = document.getElementById('wopReflectionsPanel').getBoundingClientRect(); return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, height:r.height, width:r.width}; })()")
        res["viewport_h"] = page.evaluate("window.innerHeight")
        res["controls"] = page.evaluate("""() => {
            const out = [];
            ['#audioPlayer', '#floatingActionBar', '#bottomToolbar', '.bottom-toolbar', '#fabLantern', '.chat-bar'].forEach(sel => {
              document.querySelectorAll(sel).forEach(n => {
                const cs = getComputedStyle(n); const r = n.getBoundingClientRect();
                if (cs.display === 'none' || cs.visibility === 'hidden' || r.width === 0 || r.height === 0 || r.bottom <= 0 || r.top >= innerHeight) return;
                out.push({sel, left:r.left, right:r.right, top:r.top, bottom:r.bottom, position: cs.position, opacity: cs.opacity});
              });
            });
            return out; }""")
        res["is_bottom_sheet"] = abs(res["panel"]["width"] - page.viewport_size["width"]) <= 2 and res["panel"]["bottom"] <= res["viewport_h"] + 1
        res["sheet_height_fraction"] = round(res["panel"]["height"] / res["viewport_h"], 3)
        # Spec 3.1 / check 4: never cover the narration player's controls or the chat bar. The
        # bottom toolbar (Listen, text size) is held to the same rule; other floating buttons
        # (the Learning Tools lantern) are recorded but are not narration controls.
        keep_clear = ("#audioPlayer", "#bottomToolbar", ".bottom-toolbar", ".chat-bar")
        overlaps = [c for c in res["controls"] if c["sel"] in keep_clear and rects_overlap(res["panel"], c) and float(c.get("opacity", "1")) > 0]
        res["overlaps"] = overlaps
        res["other_floating_buttons_under_open_sheet"] = [c["sel"] for c in res["controls"] if c["sel"] not in keep_clear and rects_overlap(res["panel"], c)]
        res["hscroll_open"] = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        res["narration_controls_visible"] = any(c["sel"] == "#audioPlayer" for c in res["controls"])
        page.screenshot(path=str(Path(out) / f"check4_{name}_phone_panel_open.png"))
        res["pass"] = res["is_bottom_sheet"] and res["sheet_height_fraction"] <= 0.67 and not overlaps \
            and res["hscroll_before"] <= 0 and res["hscroll_open"] <= 0 and res["narration_controls_visible"]
        ok = ok and res["pass"]
        ev[name] = res
        b.close()
    # The chat bar exists only on /chat/ presentation pages, which ask nothing to be written: no panel there.
    b = pw.chromium.launch()
    page = b.new_page(**{k: v for k, v in pw.devices["Pixel 7"].items() if k in ("viewport", "user_agent", "device_scale_factor", "is_mobile", "has_touch")})
    page.goto(base + "/chat/video-01/")
    page.wait_for_timeout(800)
    ev["chat_page"] = {"chat_bar_present": page.locator(".chat-bar").count() > 0, "panel_present": page.locator(".wop-rp-tab").count() > 0}
    b.close()
    ok = ok and not ev["chat_page"]["panel_present"]
    name = write(out, "check4_phone.json", ev)
    record("4", ok, "bottom sheet ≤ 2/3 height, clear of narration controls, no horizontal scroll (Chromium Pixel 7, WebKit iPhone 13)", [name, "check4_chromium_phone_panel_open.png", "check4_webkit_phone_panel_open.png"])
    return ev


# ---------------------------------------------------------------- check 5: markers, dot, no Leave-site prompt, questions
def check5(pw, base, out, check2_results):
    b = pw.chromium.launch()
    ctx = b.new_context(accept_downloads=True)
    page = ctx.new_page()
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.type), d.dismiss()))
    page.goto(base + "/chapters/11-the-living-christ/")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_timeout(800)
    ev = {}
    act_chapter_rjw(page, "pause-closing", "Marker test journal")
    ev["dot_after_write"] = page.is_visible(".wop-rp-tab .wop-rp-dot")
    open_panel(page)
    ev["markers_after_write"] = page.locator("#wopReflectionsPanel .wop-rp-marker").count()
    ev["entries_after_write"] = page.locator("#wopReflectionsPanel .wop-rp-entry").count()
    ev["marker_text"] = page.inner_text("#wopReflectionsPanel .wop-rp-marker >> nth=0")
    page.screenshot(path=str(Path(out) / "check5_markers_before_download.png"))
    with page.expect_download() as d:
        page.click('#wopReflectionsPanel [data-format="md"]')
    d.value.save_as(str(Path(out) / "check5_download.md"))
    page.wait_for_timeout(400)
    ev["markers_after_download"] = page.locator("#wopReflectionsPanel .wop-rp-marker").count()
    ev["suggestion_after_download"] = page.inner_text("#wopReflectionsPanel .wop-rp-suggest") if page.is_visible("#wopReflectionsPanel .wop-rp-suggest") else ""
    close_panel(page)
    ev["dot_after_download"] = page.is_visible(".wop-rp-tab .wop-rp-dot")
    page.screenshot(path=str(Path(out) / "check5_tab_after_download.png"))
    # an edit after the download brings the marker back
    page.evaluate("RJW.openModal('pause-closing', 'journal')")
    set_value(page, "#journal-ta", "Marker test journal, edited after download")
    page.evaluate("RJW.closeModal()")
    page.wait_for_timeout(300)
    ev["dot_after_edit"] = page.is_visible(".wop-rp-tab .wop-rp-dot")
    # No "Leave site?" prompt, with an entry not yet downloaded: navigate away, then close with beforeunload
    page.goto(base + "/about/")
    page.wait_for_timeout(300)
    page.go_back()
    page.wait_for_timeout(500)
    page.close(run_before_unload=True)
    time.sleep(1.0)
    ev["dialogs_seen"] = dialogs
    # My questions: saved, listed, in every download format (from check 2's files)
    q = "Why did Peter answer three times — and what does “feed” mean?"
    ev["question_in_every_format"] = {r["file"]: (q not in " ".join(r.get("missing", []))) for r in (check2_results or [])}
    b.close()
    ok = ev["dot_after_write"] and ev["markers_after_write"] >= 1 and ev["markers_after_write"] == ev["entries_after_write"] \
        and ev["marker_text"] == "Not yet downloaded" and ev["markers_after_download"] == 0 and not ev["dot_after_download"] \
        and ev["dot_after_edit"] and not ev["dialogs_seen"] and ev["question_in_every_format"] and all(ev["question_in_every_format"].values())
    name = write(out, "check5_markers.json", ev)
    record("5", ok, "marker and dot shown, cleared by download; no Leave-site prompt; question in every format", [name, "check5_markers_before_download.png", "check5_tab_after_download.png"])
    return ev


# ---------------------------------------------------------------- check 6: Clear
def check6(pw, base, out):
    b = pw.chromium.launch()
    ctx = b.new_context()
    page = ctx.new_page()
    page.goto(base + "/seeking-jesus/self-check/")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_timeout(800)
    act_sjn_selfcheck(page, "A question on the self-check page")
    page.goto(base + "/chapters/11-the-living-christ/")
    page.wait_for_timeout(800)
    act_chapter_rjw(page, "pause-closing", "Journal before clear")
    # State that Clear must leave alone, and old answers not yet carried over (written after this load)
    page.evaluate("""() => {
      const keep = {
        'sjn:lens': '"other_christian"', 'sjn:codeit': '{"p1":{"pick":"A"}}', 'sjn:map': '{"corpus":"all"}',
        'wop-bookmark-chapter-11-the-living-christ': '{"position":900}', 'wop-bookmark-flag-chapter-11-the-living-christ': 'true',
        'wop-complete-chapter-11-the-living-christ': 'true', 'wop-progress-chapter-11-the-living-christ': '{"scroll_position":40}',
        'wop-narration-chapter': '11', 'wop-narration-position': '120', 'wop-narration-progress::11-the-living-christ::narration': '{"position_seconds":120}',
        'wop-font-size': '1.1', 'wop-migration-done': '1'
      };
      Object.keys(keep).forEach(k => localStorage.setItem(k, keep[k]));
      localStorage.setItem('sjn:journal-queue', '[{"card_id":"x","commitment_text":"queued"}]');
      localStorage.setItem('sjn:goals', '[{"text":"g1"},{"text":"g2"}]');
      localStorage.setItem('sjn:selfcheck-pre', '{"q1":3,"_at":"2026-11-18"}');
      localStorage.setItem('sjn:selfcheck-post', '{"q1":4,"_at":"2026-11-18"}');
      localStorage.setItem('wop-rjw-pause-humility::witness', 'not yet carried over');
      localStorage.setItem('wop-rjw-pause-humility::witness-include-document', 'true');
      localStorage.setItem('wop-rjw-pause-humility::witness-submit-community', 'false');
      localStorage.setItem('wop-rjw-A05', 'older Articles key not yet carried over');
    }""")
    before = page.evaluate("Object.keys(localStorage).sort()")
    expected_n = page.evaluate("wopReflections.countForClear()")
    entries_before = page.evaluate("wopReflections.loadAll().length")
    confirm = confirm_clear(page)
    after = page.evaluate("Object.keys(localStorage).sort()")
    removed = sorted(set(before) - set(after))
    kept = sorted(set(after))
    must_remove = [k for k in before if k.startswith("wop-reflection-") or k.startswith("wop-rjw-") or k in ("sjn:journal-queue", "sjn:goals") or k.startswith("sjn:selfcheck-")]
    must_keep = [k for k in before if k not in must_remove]
    ev = {"keys_before": before, "removed": removed, "kept": kept, "must_remove": must_remove, "must_keep": must_keep,
          "confirmation": confirm, "count_named": expected_n, "entries_before": entries_before,
          "textareas_after": page.evaluate("['reflect-ta','journal-ta','witness-ta'].map(id => document.getElementById(id).value)")}
    expected_text = f"Remove all {expected_n} answers from this browser? This cannot be undone."
    ok = sorted(must_remove) == removed and sorted(must_keep) == kept and confirm == expected_text and expected_n > 0 \
        and any(k.startswith("wop-rjw-") for k in removed) and "sjn:lens" in kept and "sjn:codeit" in kept
    b.close()
    name = write(out, "check6_clear.json", ev)
    record("6", ok, f"Clear removed {len(removed)} keys exactly as ruled and kept {len(kept)}; confirmation named {expected_n}", [name])
    return ev


# ---------------------------------------------------------------- check 7: forms behave as before
def run_forms(pw, base, include_corrections, signed_in=False):
    out = {}
    b = pw.chromium.launch()
    for form in (["contact", "newsletter-connect", "newsletter-footer"] + (["corrections"] if include_corrections else [])):
        ctx = b.new_context()
        sent = []

        def make_handler(sent):
            def handler(route):
                _stub(route, sent)
            return handler

        def _stub(route, sent):
            req = route.request
            sent.append({"url": req.url, "method": req.method,
                         "headers": {k: v for k, v in req.headers.items() if k.lower() in ("content-type", "authorization")},
                         "body": req.post_data})
            if req.method == "OPTIONS":
                route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "POST, OPTIONS"})
            else:
                route.fulfill(status=201, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"},
                              body=json.dumps({"message": "Thank you for reaching out! We will respond as soon as possible.", "status": "subscribed"}))
        ctx.route(API_PATTERN, make_handler(sent))
        page = ctx.new_page()
        if signed_in:
            page.goto(base + "/about/")
            page.evaluate("""() => { localStorage.setItem('wop_access_token','aaa.bbb.ccc'); localStorage.setItem('wop_refresh_token','r.r.r');
                localStorage.setItem('wop-user', JSON.stringify({name:'Former Member', email:'former@example.org'})); }""")
        if form == "contact":
            page.goto(base + "/connect/")
            page.wait_for_timeout(500)
            prefill = page.evaluate("[document.getElementById('contact-name').value, document.getElementById('contact-email').value]")
            page.fill("#contact-name", "Test Reader")
            page.fill("#contact-email", "reader@example.org")
            if page.locator("#contact-type").count():
                page.select_option("#contact-type", index=1)
            page.fill("#contact-subject", "A question — “about” the site")
            page.fill("#contact-message", "This is a stubbed test message. Nothing is sent.")
            page.click("#contactSubmit")
            page.wait_for_selector("#contactSuccess:not(.hidden)", timeout=10000)
            confirmation = page.inner_text("#contactSuccess")
            form_hidden = page.evaluate("document.getElementById('contactForm').classList.contains('hidden')")
            out[form] = {"prefill_before_typing": prefill, "confirmation": confirmation, "form_hidden_after": form_hidden}
        elif form.startswith("newsletter"):
            page.goto(base + "/connect/")
            page.wait_for_timeout(1200)
            fid, mid = ("#footerNewsletterForm", "#footerNlMessage") if form == "newsletter-footer" else ("#connectNewsletterForm", "#connectNlMessage")
            f = page.locator(fid)
            f.locator('input[name="name"]').fill("Test Reader")
            f.locator('input[name="email"]').fill("reader@example.org")
            prefill = None
            f.locator('button[type="submit"]').click()
            page.wait_for_timeout(1500)
            msg = page.locator(mid)
            out[form] = {"confirmation": msg.inner_text() if msg.count() else "",
                         "message_classes": msg.get_attribute("class") if msg.count() else "",
                         "form_hidden_after": f.evaluate("el => el.classList.contains('hidden')")}
        else:
            page.goto(base + "/aoid/corrections/?article=A06")
            page.wait_for_timeout(800)
            # The same valid entry as scripts/aoid_tests/test_corrections_form.py (fill_valid)
            page.select_option("#cf-tradition", "Lutheran")
            page.fill("#cf-church", "Lutheran Church–Missouri Synod")
            page.fill("#cf-citation", "Augsburg Confession, Article VII")
            page.fill("#cf-link", "https://example.org/augsburg")
            page.fill("#cf-note", "The text says X.\nSecond line.")
            page.fill("#cf-name", "A Reader")
            page.fill("#cf-email", "reader@example.org")
            page.evaluate("document.querySelector('#cfForm [name=loaded_at]').value = String(Date.now() - 10000)")
            page.click("#cfSubmit")
            page.wait_for_selector("#cfSuccess:not(.hidden)", timeout=10000)
            out[form] = {"confirmation": page.inner_text("#cfSuccess"),
                         "form_hidden_after": page.evaluate("document.getElementById('cfForm').classList.contains('hidden') || getComputedStyle(document.getElementById('cfForm')).display === 'none'")}
        out[form]["requests"] = sent
        ctx.close()
    b.close()
    return out


def normalise_body(body):
    try:
        d = json.loads(body or "{}")
    except Exception:  # noqa: BLE001
        return body
    if isinstance(d, dict) and "loaded_at" in d:
        d["loaded_at"] = "<timestamp>"
    return d


def check7(pw, base, base_on, baseline, baseline_on, out):
    new = run_forms(pw, base, False)
    new_on = run_forms(pw, base_on, True) if base_on else {}
    old = run_forms(pw, baseline, False)
    old_on = run_forms(pw, baseline_on, True) if baseline_on else {}
    signed = run_forms(pw, base, False, signed_in=True)
    comparisons = {}
    ok = True
    for form, a, b_ in [("contact", old.get("contact"), new.get("contact")),
                        ("newsletter-connect", old.get("newsletter-connect"), new.get("newsletter-connect")),
                        ("newsletter-footer", old.get("newsletter-footer"), new.get("newsletter-footer")),
                        ("corrections", old_on.get("corrections"), new_on.get("corrections"))]:
        if a is None or b_ is None:
            comparisons[form] = {"pass": False, "note": "not run"}
            ok = False
            continue
        ra = [r for r in a["requests"] if r["method"] != "OPTIONS"]
        rb = [r for r in b_["requests"] if r["method"] != "OPTIONS"]
        same_endpoint = [(r["method"], r["url"]) for r in ra] == [(r["method"], r["url"]) for r in rb]
        same_fields = [normalise_body(r["body"]) for r in ra] == [normalise_body(r["body"]) for r in rb]
        same_ct = [r["headers"].get("content-type") for r in ra] == [r["headers"].get("content-type") for r in rb]
        same_conf = a.get("confirmation") == b_.get("confirmation")
        c = {"same_endpoint": same_endpoint, "same_message_fields": same_fields, "same_content_type": same_ct,
             "same_confirmation": same_conf, "requests_sent": len(rb), "endpoint": [r["url"] for r in rb],
             "confirmation": b_.get("confirmation"), "authorization_header_new": [r["headers"].get("authorization") for r in rb]}
        c["pass"] = same_endpoint and same_fields and same_conf and len(rb) == 1 and not any(c["authorization_header_new"])
        comparisons[form] = c
        ok = ok and c["pass"]
    # A reader who was signed in before: same fields, endpoint and confirmation, no token (ruling SITE-JOURNAL-FORM-TOKEN)
    s = {}
    for form in ["contact", "newsletter-connect"]:
        rb = [r for r in signed[form]["requests"] if r["method"] != "OPTIONS"]
        s[form] = {"authorization_header": [r["headers"].get("authorization") for r in rb],
                   "same_fields_as_guest": [normalise_body(r["body"]) for r in rb] == [normalise_body(r["body"]) for r in new[form]["requests"] if r["method"] != "OPTIONS"],
                   "confirmation_same": signed[form].get("confirmation") == new[form].get("confirmation"),
                   "prefill": signed[form].get("prefill_before_typing")}
        s[form]["pass"] = not any(s[form]["authorization_header"]) and s[form]["same_fields_as_guest"] and s[form]["confirmation_same"]
        ok = ok and s[form]["pass"]
    comparisons["formerly_signed_in_reader"] = s
    name = write(out, "check7_forms.json", {"comparisons": comparisons, "baseline": old, "baseline_on": old_on, "new": new, "new_on": new_on, "signed_in_new": signed})
    record("7", ok, "contact, corrections and newsletter: same fields, endpoint and confirmation as the baseline build; no token", [name])
    return comparisons


# ---------------------------------------------------------------- check 8: old tokens gone
def check8(pw, base, out):
    b = pw.chromium.launch()
    ev = {}
    ok = True
    for path in ["/", "/about/", "/chapters/11-the-living-christ/"]:
        ctx = b.new_context()
        page = ctx.new_page()
        page.goto(base + "/robots.txt")
        page.evaluate("""() => { localStorage.setItem('wop_access_token','aaa.bbb.ccc'); localStorage.setItem('wop_refresh_token','r.r.r');
            localStorage.setItem('wop-auth-token','legacy'); localStorage.setItem('wop-user', JSON.stringify({name:'n', email:'e@example.org'}));
            localStorage.setItem('wop-engagement-queue', '[{"event_type":"page_view"}]'); localStorage.setItem('wop-font-size','1.1'); }""")
        page.goto(base + path)
        page.wait_for_timeout(500)
        keys = page.evaluate("Object.keys(localStorage).sort()")
        gone = not any(k in keys for k in ["wop_access_token", "wop_refresh_token", "wop-auth-token", "wop-user", "wop-engagement-queue"])
        ev[path] = {"keys_after_first_load": keys, "old_tokens_gone": gone, "unrelated_key_kept": "wop-font-size" in keys}
        ok = ok and gone and ("wop-font-size" in keys)
        ctx.close()
    b.close()
    name = write(out, "check8_tokens.json", ev)
    record("8", ok, "access, refresh and legacy tokens, cached user and engagement queue removed on first load", [name])
    return ev


# ---------------------------------------------------------------- check 9: no account wording
def check9_local(site, out):
    hits = {}
    for root, _dirs, files in os.walk(site):
        for fn in files:
            p = Path(root) / fn
            if p.suffix.lower() not in (".html", ".js", ".xml", ".json", ".css", ".txt", ".md", ".webmanifest", ".svg"):
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            for s in CHECK9_STRINGS:
                if s in t:
                    hits.setdefault(s, []).append(str(p.relative_to(site)).replace("\\", "/"))
    bad = {s: [f for f in fs if not (s == "create an account" and f == CHECK9_EXCEPTION)] for s, fs in hits.items()}
    bad = {s: fs for s, fs in bad.items() if fs}
    # The exception covers the post's original body only: the string must sit after the editor's note.
    post = (Path(site) / CHECK9_EXCEPTION).read_text(encoding="utf-8")
    note = "Update, November 2026: This site no longer offers accounts."
    exception_ok = note in post and post.index(note) < post.index("create an account")
    ev = {"counts": {s: len(hits.get(s, [])) for s in CHECK9_STRINGS}, "hits": hits, "outside_exception": bad,
          "exception_is_post_body_after_note": exception_ok}
    name = write(out, "check9_strings_local.json", ev)
    record("9-local", not bad and exception_ok, f"counts {ev['counts']} (exception: the 12 April post's original body)", [name])
    return ev


def check9_prod(prod, out):
    def get(u):
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible; wop-acceptance-check)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    sm = get(prod.rstrip("/") + "/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    extra = [prod.rstrip("/") + p for p in ["/posts/feed.xml", "/js/api.js", "/js/wop-reflections.js", "/js/wop-reflections-panel.js",
                                             "/js/wop-docx.js", "/js/wop-reflection-sources.js", "/js/chapter.js", "/js/my-reflections.js",
                                             "/my-reflections/", "/chat/video-01/"]]
    hits, errors = {}, {}
    for u in urls + extra:
        try:
            t = get(u)
        except Exception as e:  # noqa: BLE001
            errors[u] = str(e)[:200]
            continue
        for s in CHECK9_STRINGS:
            if s in t:
                hits.setdefault(s, []).append(u)
    exc = prod.rstrip("/") + "/" + CHECK9_EXCEPTION.replace("index.html", "")
    bad = {s: [u for u in us if not (s == "create an account" and u == exc)] for s, us in hits.items()}
    bad = {s: us for s, us in bad.items() if us}
    for gone in ["/js/auth-modal.js", "/js/engagement.js", "/css/auth-modal.css"]:
        try:
            get(prod.rstrip("/") + gone)
            errors["still_served:" + gone] = "200"
        except Exception as e:  # noqa: BLE001
            pass
    ev = {"pages_checked": len(urls) + len(extra), "hits": hits, "outside_exception": bad, "fetch_errors": errors}
    name = write(out, "check9_strings_prod.json", ev)
    record("9-prod", not bad and not any(k.startswith("still_served") for k in errors), f"{ev['pages_checked']} production URLs; hits {{{', '.join(f'{k}: {len(v)}' for k, v in hits.items())}}}", [name])
    return ev


# ---------------------------------------------------------------- check 10: approved wording
def page_text(path):
    raw = Path(path).read_text(encoding="utf-8")
    meta = re.findall(r'<meta name="description" content="([^"]*)"', raw)
    body = re.sub(r"<script\b[\s\S]*?</script>", " ", raw)
    body = re.sub(r"<style\b[\s\S]*?</style>", " ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    return norm(html.unescape(" ".join(meta) + " " + body))


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([.,;:?!)])", r"\1", s)
    s = re.sub(r"\(\s+", "(", s)
    return s.strip()


def fragments(quoted):
    q = quoted.strip()
    parts = [norm(p) for p in re.split(r"…", q)]
    return [p.strip(" ,;") for p in parts if p.strip(" ,;")]


def parse_approved(md):
    items = {}
    cur = None
    for line in md.splitlines():
        m = re.match(r"\*\*([UP]\d+)\.", line)
        if m:
            cur = m.group(1)
            items[cur] = []
            continue
        if cur and line.startswith(("-", "  ")):
            kind = "proposed" if "Proposed:" in line else ("now" if line.strip().startswith(("- Now:", "Now:")) else
                    ("delete" if line.strip().startswith("- Delete") else ("change" if line.strip().startswith("- Change") else
                     ("add" if line.strip().startswith("- Add") else "other"))))
            quotes = re.findall(r'"([^"]+)"', line)
            items[cur].append((kind, quotes, line.strip()))
    return items


def check10(site, approved_md, spec_md, out):
    md = Path(approved_md).read_text(encoding="utf-8")
    spec = Path(spec_md).read_text(encoding="utf-8")
    items = parse_approved(md)
    uth = page_text(Path(site) / "about" / "under-the-hood" / "index.html") if (Path(site) / "about" / "under-the-hood" / "index.html").exists() else page_text(Path(site) / "under-the-hood" / "index.html")
    priv = page_text(Path(site) / "privacy" / "index.html")
    uth_raw = (Path(site) / "about" / "under-the-hood" / "index.html")
    uth_raw = uth_raw.read_text(encoding="utf-8") if uth_raw.exists() else (Path(site) / "under-the-hood" / "index.html").read_text(encoding="utf-8")
    priv_raw = (Path(site) / "privacy" / "index.html").read_text(encoding="utf-8")
    res = {}

    def present(text, s):
        return all(f in text for f in fragments(s))

    def absent(text, s):
        fr = fragments(s)
        return not all(f in text for f in fr)

    for item, lines in items.items():
        text = uth if item.startswith("U") else priv
        r = {"present": [], "absent": [], "pass": True}
        for kind, quotes, line in lines:
            if kind == "proposed" and quotes:
                for q in quotes[:1]:
                    ok = present(text, q)
                    r["present"].append([q, ok])
                    r["pass"] &= ok
            if kind == "now" and quotes:
                for q in quotes[:1]:
                    ok = absent(text, q)
                    r["absent"].append([q, ok])
                    r["pass"] &= ok
            if kind == "delete" and quotes:
                for q in quotes:
                    ok = absent(text, q)
                    r["absent"].append([q, ok])
                    r["pass"] &= ok
            if kind == "change" and len(quotes) == 2:
                ok1, ok2 = absent(text, quotes[0]) or quotes[0] in quotes[1], present(text, quotes[1])
                r["absent"].append([quotes[0], ok1])
                r["present"].append([quotes[1], ok2])
                r["pass"] &= ok1 and ok2
            if kind == "add" and quotes:
                ok = present(text, quotes[0])
                r["present"].append([quotes[0], ok])
                r["pass"] &= ok
        res[item] = r
    # Items whose instruction is not a quoted text
    special = {}
    special["U8_anchor_and_toc"] = ('id="accounts-api"' in uth_raw) and ("Forms and the API backend" in uth) and ("Accounts and the API backend" not in uth)
    special["U10_row_deleted"] = "Sign-in and registration" not in uth
    special["U11_row_deleted"] = '<th scope="row">My Discipleship Journal</th>' not in uth_raw
    special["U3_U4_both_diagrams"] = uth_raw.count("PythonAnywhere: forms, newsletter") == 2 and uth_raw.count("JSON form submissions") == 2
    sec = spec.split("### 6.1")[1].split("### 6.2")[0]
    paras = [re.sub(r"^>\s?", "", l).strip() for l in sec.splitlines() if l.startswith(">")]
    paras = [p for p in paras if p]
    heading = paras[0].strip("*")
    p1, p2, held, kmc = paras[1], paras[2], paras[3], paras[4].replace("*Keep My Commandments*", "Keep My Commandments")
    special["P4_heading"] = norm(heading) in priv
    special["P4_para1"] = norm(p1) in priv
    special["P4_para2"] = norm(p2) in priv
    special["P4_kmc_para"] = norm(kmc) in priv
    special["P4_held_paragraph_not_published"] = norm(held)[:60] not in priv and "This site no longer has user accounts" not in priv
    special["P4_old_section_gone"] = "Information We Collect from Registered Members" not in priv
    special["P4_anchor_kept"] = 'id="privacy-members"' in priv_raw
    special["P5_after_section"] = priv.find(norm(kmc)) < priv.find("Accounts created while this site was being tested remain on our server until they are deleted. Nothing new is added to them.") < priv.find("Information We Collect from Forms")
    special["P15_item_deleted"] = "Active accounts and their associated data" not in priv
    special["anchors_unchanged"] = all(a in priv_raw for a in ['id="privacy-opening"', 'id="privacy-visitors"', 'id="privacy-members"', 'id="privacy-forms"', 'id="privacy-use"',
                                                              'id="privacy-security"', 'id="privacy-third-parties"', 'id="privacy-cookies"', 'id="privacy-children"',
                                                              'id="privacy-rights"', 'id="privacy-retention"', 'id="privacy-changes"', 'id="privacy-contact"', 'id="privacy-brother-aaron"'])
    ok = all(r["pass"] for r in res.values()) and all(special.values())
    name = write(out, "check10_wording.json", {"items": res, "special": special})
    record("10", ok, f"{sum(r['pass'] for r in res.values())}/{len(res)} quoted items and {sum(special.values())}/{len(special)} structural checks match", [name])
    return res, special


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site")
    ap.add_argument("--site-on")
    ap.add_argument("--baseline")
    ap.add_argument("--baseline-on")
    ap.add_argument("--approved")
    ap.add_argument("--spec")
    ap.add_argument("--prod")
    ap.add_argument("--out", required=True)
    ap.add_argument("--checks", default="1,2,3,4,5,6,7,8,9,10")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    checks = {c.strip() for c in a.checks.split(",")}
    servers = []
    with sync_playwright() as pw:
        if a.prod:
            if "1" in checks:
                check1(pw, a.prod.rstrip("/"), a.out, label="prod")
            if "9" in checks:
                check9_prod(a.prod, a.out)
        else:
            srv, base = serve(a.site)
            servers.append(srv)
            base_on = baseline = baseline_on = None
            if a.site_on:
                s2, base_on = serve(a.site_on)
                servers.append(s2)
            if a.baseline:
                s3, baseline = serve(a.baseline)
                servers.append(s3)
            if a.baseline_on:
                s4, baseline_on = serve(a.baseline_on)
                servers.append(s4)
            c2 = None
            steps = [("1", lambda: check1(pw, base, a.out)), ("2", lambda: check2(pw, base, a.out)),
                     ("3", lambda: check3(pw, base, a.out)), ("4", lambda: check4(pw, base, a.out))]
            for k, fn in steps:
                if k in checks:
                    try:
                        r = fn()
                        if k == "2":
                            c2 = r
                    except Exception as e:  # noqa: BLE001
                        record(k, False, f"error: {str(e)[:300]}", [])
            for k, fn in [("5", lambda: check5(pw, base, a.out, c2)), ("6", lambda: check6(pw, base, a.out)),
                          ("7", lambda: check7(pw, base, base_on, baseline, baseline_on, a.out)), ("8", lambda: check8(pw, base, a.out)),
                          ("9", lambda: check9_local(a.site, a.out)), ("10", lambda: check10(a.site, a.approved, a.spec, a.out))]:
                if k in checks:
                    try:
                        fn()
                    except Exception as e:  # noqa: BLE001
                        record(k, False, f"error: {str(e)[:300]}", [])
    for s in servers:
        s.shutdown()
    write(a.out, "acceptance_summary" + ("_prod" if a.prod else "") + ".json", RESULTS)
    print(json.dumps({k: v["pass"] for k, v in RESULTS.items()}))


if __name__ == "__main__":
    main()
