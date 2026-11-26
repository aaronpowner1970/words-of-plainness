"""Blocked browser storage: no page breaks, and nothing claims to have saved (CODE-SITE-26, SITE step 43).

A reader may block storage (strict privacy settings, some private modes, some embedded browsers). Then
reading window.localStorage or window.sessionStorage throws a SecurityError. Every page must still load
and every control must still respond; nothing may say "Saved" when nothing could be kept. With storage
available the same controls must still say "Saved" exactly as before.

Storage modes (Playwright Chromium):
  ls_only     init script: reading window.localStorage throws SecurityError
  all_script  init script: localStorage, sessionStorage and indexedDB all throw SecurityError
  chromium    Chromium's own "block all cookies and site data" setting (profile preference
              default_content_setting_values.cookies = 2, new headless); Chromium itself refuses storage
  available   normal storage (the "honest" check's control case)

Checks:
  load      every page (--all) or the key pages: no storage error at load, in each blocked mode
  controls  the key pages: every button, [onclick], tab, radio, checkbox and select is clicked and every
            text box typed into; no storage error, in each blocked mode
  honest    card-chapter Save, Seeking Jesus starting point, Code It Save and Save to journal, Articles
            reflection status: no "Saved" when blocked; the usual "Saved" when available
  message   (SITE step 81, CODE-SITE-41; rulings SITE-STORAGE-BLOCKED-MESSAGE and SITE-BLOCKED-MSG-APPROACHES)
            in each blocked mode, in each place where a reader writes: the approved sentence W1 (W4 on
            /my-reflections/) is shown and matches the approved file's bytes; the lines saying words are kept
            are not shown; no "Saved"; Copy puts the typed answers (with Greek and curly quotes) on the
            clipboard and the button reads W7; with the clipboard refused the W3 box holds them; all four
            download formats contain them; W5 is closed, opens by mouse and by keyboard and matches the file;
            the W6 links go to the makers' help pages in a new tab; typed words survive closing and opening
            the window or panel; no storage or page error; no "Leave this page?" prompt; no request carries
            the typed words. Approaches to Belief: W1 replaces the one sentence and nothing else; the page's
            own "Download my reflections" still holds what was typed.
  available with storage working: no blocked-storage class, element or request on any of those pages, and the
            lines that say words are kept are shown as before

Usage:
  python scripts/site_tests/storage_blocked_acceptance.py --site _site [--all] --out <dir>
  python scripts/site_tests/storage_blocked_acceptance.py --prod https://www.wordsofplainness.org --out <dir>
  [--wording <approved wording .md>]  (default: data-sources/site/WoP_SITE_BlockedStorage_Wording_Approved_20261120.md)
Exit status 0 when every check passes.
"""
import argparse
import functools
import http.server
import json
import re
import sys
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

KEY_PAGES = ["/articles/", "/chapters/11-the-living-christ/", "/chapters/12-beatitudes/", "/my-reflections/",
             "/seeking-jesus/code-it/", "/studies/approaches-to-belief/", "/privacy/", "/", "/narrations/",
             "/chapters/06-embrace-the-savior/", "/seeking-jesus/", "/seeking-jesus/self-check/"]
BLOCKED = ["ls_only", "all_script", "chromium"]
LS_ONLY = "Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked', 'SecurityError'); }, configurable: true });"
ALL_SCRIPT = """['localStorage','sessionStorage','indexedDB'].forEach(function (n) {
  Object.defineProperty(window, n, { get() { throw new DOMException('blocked', 'SecurityError'); }, configurable: true }); });"""
NO_NAV = """document.addEventListener('click', function (e) { var a = e.target && e.target.closest && e.target.closest('a[href]'); if (a) e.preventDefault(); }, true);
document.addEventListener('submit', function (e) { e.preventDefault(); }, true); window.print = function () {};"""
CLICK_ALL = """async () => {
  const els = Array.from(document.querySelectorAll('button, [role=button], [onclick], .tab-pill, input[type=radio], input[type=checkbox], select, summary')).slice(0, 220);
  let n = 0;
  for (const el of els) {
    if (!el.isConnected || el.id === 'sj-wipe') continue;
    try { if (el.tagName === 'SELECT') { if (el.options.length > 1) { el.selectedIndex = 1; el.dispatchEvent(new Event('change', {bubbles: true})); } } else { el.click(); } n++; } catch (e) {}
    await new Promise(r => setTimeout(r, 15));
    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
  }
  for (const t of Array.from(document.querySelectorAll('textarea, input[type=text], input:not([type])')).slice(0, 80)) {
    try { t.value = 'typed'; t.dispatchEvent(new Event('input', {bubbles: true})); n++; } catch (e) {}
  }
  return n; }"""
TOAST = "() => { const t = document.querySelector('.sj-toast'); return t && t.classList.contains('is-on') ? t.textContent : ''; }"


def storage_error(text):
    return bool(re.search(r"SecurityError|localStorage|sessionStorage|indexedDB|^blocked$|Access is denied", text))


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass


def serve(directory):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def site_pages(site):
    return sorted("/" + str(p.parent.relative_to(site)).replace("\\", "/").strip(".") + ("/" if p.parent != Path(site) else "")
                  for p in Path(site).rglob("index.html") if "admin" not in p.parts and "pagefind" not in p.parts)


def make_context(pw, browser, mode):
    if mode == "chromium":
        ud = tempfile.mkdtemp(prefix="wop_storage_blocked_")
        (Path(ud) / "Default").mkdir(parents=True, exist_ok=True)
        (Path(ud) / "Default" / "Preferences").write_text(json.dumps({"profile": {"default_content_setting_values": {"cookies": 2}}}), encoding="utf-8")
        return pw.chromium.launch_persistent_context(ud, headless=True, channel="chromium")
    ctx = browser.new_context()
    if mode == "ls_only":
        ctx.add_init_script(LS_ONLY)
    elif mode == "all_script":
        ctx.add_init_script(ALL_SCRIPT)
    return ctx


def open_page(ctx, base, path, errs):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append({"page": path, "text": str(e), "stack": (getattr(e, "stack", "") or "")[:400]}))
    pg.on("dialog", lambda d: d.dismiss())
    # Nothing goes to other hosts, and no test page view is counted by the site's analytics.
    pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) and "/_vercel/insights/" not in r.request.url else r.abort())
    pg.goto(base + path, wait_until="load")
    pg.wait_for_timeout(600)
    return pg


def check_storage_really_blocked(ctx, base):
    errs = []
    pg = open_page(ctx, base, "/", errs)
    st = pg.evaluate("() => { const o = {}; for (const n of ['localStorage','sessionStorage']) { try { window[n].getItem('x'); o[n] = 'ok'; } catch (e) { o[n] = e.name; } } return o; }")
    pg.close()
    return st


def check_load(pw, browser, base, pages, out):
    res, ok = {}, True
    for mode in BLOCKED:
        ctx = make_context(pw, browser, mode)
        res[mode] = {"storage": check_storage_really_blocked(ctx, base), "pages_with_storage_errors": {}}
        for path in pages:
            errs = []
            try:
                open_page(ctx, base, path, errs).close()
            except Exception as e:
                errs.append({"page": path, "text": "load failed: " + str(e)[:200]})
            bad = [e for e in errs if storage_error(e["text"]) or e["text"].startswith("load failed")]
            if bad:
                res[mode]["pages_with_storage_errors"][path] = bad
        ctx.close()
        ok = ok and not res[mode]["pages_with_storage_errors"] and res[mode]["storage"].get("localStorage") == "SecurityError"
    (Path(out) / "load.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    counts = {m: len(r["pages_with_storage_errors"]) for m, r in res.items()}
    return ok, f"{len(pages)} pages x {len(BLOCKED)} blocked modes; pages with a storage error: {counts}"


def check_controls(pw, browser, base, pages, out):
    res, ok = {}, True
    for mode in BLOCKED:
        ctx = make_context(pw, browser, mode)
        res[mode] = {}
        for path in pages:
            errs = []
            pg = open_page(ctx, base, path, errs)
            pg.add_init_script(NO_NAV); pg.evaluate(NO_NAV)
            try:
                n = pg.evaluate(CLICK_ALL)
                pg.wait_for_timeout(2600)            # debounced autosaves run (the longest waits 2 s)
            except Exception as e:
                n = "interrupted: " + str(e)[:120]
            pg.close()
            bad = [e for e in errs if storage_error(e["text"])]
            res[mode][path] = {"controls": n, "storage_errors": bad}
            ok = ok and not bad
        # Seeking Jesus "Erase" (confirm accepted; the page reloads)
        errs = []
        pg = open_page(ctx, base, "/seeking-jesus/self-check/", errs)
        pg.evaluate("() => { window.confirm = () => true; }")   # the reader answers OK
        try:
            with pg.expect_navigation(timeout=5000):
                pg.evaluate("() => document.getElementById('sj-wipe').click()")
            wipe = "reloaded"
        except Exception as e:
            wipe = "no reload: " + str(e)[:100]
        pg.close()
        bad = [e for e in errs if storage_error(e["text"])]
        res[mode]["Erase"] = {"result": wipe, "storage_errors": bad}
        ok = ok and not bad and wipe == "reloaded"
        ctx.close()
    (Path(out) / "controls.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    counts = {m: sum(len(v["storage_errors"]) for v in r.values()) for m, r in res.items()}
    return ok, f"{len(pages)} pages + Erase x {len(BLOCKED)} blocked modes; storage errors: {counts}"


def feedback(ctx, base, errs):
    """What the reader is told after each save, in this context."""
    seen = {}
    pg = open_page(ctx, base, "/chapters/12-beatitudes/", errs)
    pg.evaluate("() => { document.querySelector('#card-1 .commitment-option').click(); const a = document.querySelector('#card-1 .reflection-area'); a.value = 'words'; a.dispatchEvent(new Event('input', {bubbles: true})); }")
    pg.wait_for_timeout(800)
    seen["card Save (choice)"] = pg.evaluate("() => { const b = document.querySelector('.card-save-btn[data-card=\"1\"]'); b.click(); return b.textContent.trim(); }")
    seen["card Save (no choice)"] = pg.evaluate("() => { const b = document.querySelector('.card-save-btn[data-card=\"2\"]'); b.click(); return b.textContent.trim(); }")
    seen["card summary line"] = pg.evaluate("() => { const f = document.querySelector('.save-feedback[data-card=\"1\"]'); return f && f.classList.contains('show') ? f.textContent.trim() : ''; }")
    pg.close()
    pg = open_page(ctx, base, "/seeking-jesus/", errs)
    pg.evaluate("() => document.querySelector('.sj-lensbtn').click()"); pg.wait_for_timeout(150)
    seen["SJN starting point"] = pg.evaluate(TOAST)
    pg.close()
    pg = open_page(ctx, base, "/seeking-jesus/code-it/", errs)
    pg.evaluate("() => { document.querySelector('.sj-exercise .sj-choice').click(); document.querySelector('.sj-exercise .sj-save-note').click(); }"); pg.wait_for_timeout(150)
    seen["SJN Code It Save"] = pg.evaluate(TOAST)
    pg.evaluate("() => { const t = document.querySelector('.sj-toast'); if (t) t.classList.remove('is-on'); document.querySelector('.sj-exercise .sj-to-journal').click(); }"); pg.wait_for_timeout(150)
    seen["SJN Save to journal"] = pg.evaluate(TOAST)
    pg.close()
    pg = open_page(ctx, base, "/articles/", errs)
    pg.locator(".rjw-textarea").first.fill("words"); pg.wait_for_timeout(1000)
    seen["Articles reflection status"] = pg.evaluate("() => { const s = document.querySelector('.rjw-status'); return s ? s.textContent : ''; }")
    pg.close()
    return seen


def check_honest(pw, browser, base, out):
    res, ok = {}, True
    for mode in ["available"] + BLOCKED:
        ctx = make_context(pw, browser, mode)
        errs = []
        try:
            seen = feedback(ctx, base, errs)
        except Exception as e:
            seen = {"failed": str(e)[:300]}
        ctx.close()
        claims = {k: v for k, v in seen.items() if "aved" in (v or "")}
        if mode == "available":
            good = len(claims) == len(seen)                  # every control says "Saved" as before
        else:
            good = not claims and "failed" not in seen       # none says "Saved"
        good = good and not [e for e in errs if storage_error(e["text"])]
        res[mode] = {"seen": seen, "pass": good, "storage_errors": [e for e in errs if storage_error(e["text"])]}
        ok = ok and good
    (Path(out) / "honest.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return ok, "; ".join(f"{m}: {'PASS' if r['pass'] else 'FAIL'}" for m, r in res.items())


# ------------------------------------------------------------------ SITE step 81: the blocked-storage message
REPO = Path(__file__).resolve().parents[2]
WORDING = REPO / "data-sources" / "site" / "WoP_SITE_BlockedStorage_Wording_Approved_20261120.md"
# W5 browser lines: which step is shown, and the help links (checked 26 Nov 2026, CODE-SITE-41)
HELP = [("Chrome or Edge:", False, ["https://support.google.com/chrome/answer/95647",
                                    "https://support.microsoft.com/en-us/edge/manage-cookies-in-microsoft-edge-view-allow-block-delete-and-use"]),
        ("Safari (iPhone, iPad or Mac):", True, ["https://support.apple.com/en-us/105082"]),
        ("Firefox:", False, ["https://support.mozilla.org/en-US/kb/storage"]),
        ("Opened from Facebook, Instagram or another app?", True, [])]
# Lines that tell the reader their words are kept: never shown when storage is blocked
UNTRUE = ["Responses are saved to your browser", "Your answers stay on this device", "Kept only on this device",
          "Journal entries are automatically included in your portable document", "Your codings stay in this browser",
          "Your choice is stored only in this browser", "Your choices are saved here", "Kept only in this browser",
          "Everything you wrote is saved only in this browser", "Open Your reflections to download them"]
SAVED = ["✓ Saved", "Saved ✓", "Saved on this device", "Starting point saved", "Saved in this browser",
         "Saved to My Discipleship Journal", "Choice saved to your summary below"]
TYPED = "Ἰησοῦς said “love one another” — ‘abide’"


def read_wording(path):
    """The approved file, parsed here independently of the site's own build-time parser."""
    lines = [l for l in Path(path).read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")]

    def sec(prefix):
        i = next(n for n, l in enumerate(lines) if l.startswith(prefix))
        j = i + 1
        while j < len(lines) and not re.match(r"^#{1,2} ", lines[j]):
            j += 1
        return [l for l in lines[i + 1:j] if l.strip()]
    w5 = sec("## W5.")
    body = w5[w5.index("Body:") + 1:]
    bullets = [re.match(r"^- \*\*(.+?)\*\*(.*)$", l).groups() for l in body if l.startswith("- ")]
    warn = re.match(r"^\*\*(.+?)\*\*(.*)$", next(l for l in body if l.startswith("**Before"))).groups()
    fb = re.search(r'show only "([^"]+)"', " ".join(sec("## Condition on W5"))).group(1)
    w6 = sec("## W6.")
    return {"w1": sec("## W1.")[0], "w2": sec("## W2.")[:2], "w3": sec("## W3.")[0], "w4": sec("## W4.")[0],
            "summary": next(l for l in w5 if l.startswith("Summary (the toggle): ")).split(": ", 1)[1],
            "intro": body[0], "bullets": bullets, "warn": warn[0] + warn[1], "fallback": fb, "w6": w6,
            "w7": sec("## W7.")[0]}


def expected_help(W):
    """The W5 body as a reader should see it, line by line, after the file's condition is applied."""
    out = []
    for (label, step), (hlabel, confirmed, links) in zip(W["bullets"], HELP):
        assert label == hlabel, (label, hlabel)
        text = label + step if confirmed else label + " " + W["fallback"]
        out.append({"text": text, "links": links})
    return out


VISIBLE_TEXT = """() => { const out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; while ((n = w.nextNode())) { const p = n.parentElement; if (!p || !n.nodeValue.trim()) continue;
    const cs = getComputedStyle(p); if (cs.visibility === 'hidden' || cs.display === 'none' || !p.getClientRects().length) continue;
    let a = p, hide = false; while (a) { const s = getComputedStyle(a); if (s.display === 'none' || a.hidden || parseFloat(s.opacity) === 0) { hide = true; break; } a = a.parentElement; }
    if (!hide) out.push(n.nodeValue); }
  return out.join(' ').replace(/\\s+/g, ' '); }"""

BLOCK_STATE = """(sel) => { const b = document.querySelector(sel); if (!b) return null;
  const det = b.querySelector('details');
  return { msg: (b.querySelector('.wop-sb-msg') || {}).textContent,
    buttons: [...b.querySelectorAll('.wop-sb-actions > button')].map(x => x.textContent),
    formatsHidden: (b.querySelector('.wop-sb-formats') || {}).hidden,
    formats: [...b.querySelectorAll('.wop-sb-formats button')].map(x => x.textContent),
    detailsOpen: det ? det.open : null, summary: det ? det.querySelector('summary').textContent : null,
    paras: det ? [...det.querySelectorAll('.wop-sb-para')].map(x => x.textContent) : [],
    lines: det ? [...det.querySelectorAll('.wop-sb-lines li')].map(li => ({ text: [...li.childNodes].filter(c => !(c.classList && c.classList.contains('wop-sb-links'))).map(c => c.textContent).join(''),
      links: [...li.querySelectorAll('a')].map(a => ({ href: a.href, text: a.textContent, target: a.target, rel: a.rel })) })) : [],
    names: [...b.querySelectorAll('button')].map(x => x.textContent.trim()).filter(t => !t).length };
}"""


def check_block(pg, sel, W, typed, out_dir, tag, need_typed=True):
    """W1, the buttons, Copy (granted and refused), the four downloads and the help, in one block. Returns (ok, details)."""
    r = {}
    pg.evaluate("(s) => { const b = document.querySelector(s); if (b) b.scrollIntoView({block: 'center'}); }", sel)
    st = pg.evaluate(BLOCK_STATE, sel)
    if st is None:
        return False, {"error": "no block " + sel}
    r["state"] = st
    eh = expected_help(W)
    words_ok = (st["msg"] == W["w1"] and st["buttons"] == W["w2"] and st["formatsHidden"] is True
                and st["detailsOpen"] is False and st["summary"] == W["summary"]
                and st["paras"] == [W["intro"], W["warn"]] and [l["text"] for l in st["lines"]] == [e["text"] for e in eh]
                and [[a["href"] for a in l["links"]] for l in st["lines"]] == [e["links"] for e in eh]
                and all(a["target"] == "_blank" and "noopener" in a["rel"] for l in st["lines"] for a in l["links"])
                and len(st["formats"]) == 4 and st["names"] == 0)
    texts = [a["text"] for l in st["lines"] for a in l["links"]]
    words_ok = words_ok and all(t in W["w6"] or t == W["fallback"] for t in texts)
    r["words_ok"] = words_ok
    # W5 opens by mouse, closes, then opens by keyboard
    pg.click(sel + " details > summary")
    by_mouse = pg.evaluate("(s) => document.querySelector(s + ' details').open", sel)
    pg.click(sel + " details > summary")
    pg.focus(sel + " details > summary"); pg.keyboard.press("Enter")
    by_key = pg.evaluate("(s) => document.querySelector(s + ' details').open", sel)
    pg.click(sel + " details > summary")
    r["help_mouse_keyboard"] = by_mouse and by_key
    # Copy, clipboard granted
    pg.evaluate("() => navigator.clipboard.writeText('-')")
    pg.click(sel + " .wop-sb-copy")
    pg.wait_for_timeout(300)
    label_now = pg.evaluate("(s) => document.querySelector(s + ' .wop-sb-copy').textContent", sel)
    clip = pg.evaluate("() => navigator.clipboard.readText()")
    pg.wait_for_timeout(2100)
    label_after = pg.evaluate("(s) => document.querySelector(s + ' .wop-sb-copy').textContent", sel)
    r["copy"] = {"label": label_now, "label_after": label_after, "has_typed": all(t in clip for t in typed), "chars": len(clip)}
    copy_ok = label_now == W["w7"] and label_after == W["w2"][0] and r["copy"]["has_typed"]
    # Copy, clipboard refused: the W3 box
    pg.evaluate("() => { window.__wopClip = navigator.clipboard.writeText; navigator.clipboard.writeText = () => Promise.reject(new DOMException('refused', 'NotAllowedError')); }")
    pg.click(sel + " .wop-sb-copy")
    pg.wait_for_timeout(300)
    fb = pg.evaluate("""(s) => { const f = document.querySelector(s + ' .wop-sb-fallback'); const t = f.querySelector('textarea');
        return { shown: !f.hidden && f.getClientRects().length > 0, head: f.querySelector('label').textContent, value: t.value,
                 selected: t.selectionEnd - t.selectionStart, focused: document.activeElement === t,
                 label: document.querySelector(s + ' .wop-sb-copy').textContent }; }""", sel)
    pg.evaluate("() => { navigator.clipboard.writeText = window.__wopClip; }")
    r["fallback"] = {k: v for k, v in fb.items() if k != "value"}
    r["fallback"]["has_typed"] = all(t in fb["value"] for t in typed)
    fb_ok = fb["shown"] and fb["head"] == W["w3"] and r["fallback"]["has_typed"] and fb["focused"] and fb["label"] == W["w2"][0]
    r["fallback"]["same_as_copy"] = fb["value"].replace("\r\n", "\n") == clip.replace("\r\n", "\n")
    fb_ok = fb_ok and r["fallback"]["same_as_copy"]
    # Download: the four formats of the journal's own download tool
    pg.click(sel + " .wop-sb-download")
    dl = {}
    for fmt in ("md", "txt", "docx", "pdf"):
        try:
            with pg.expect_download(timeout=60000) as d:
                pg.click(f"{sel} .wop-sb-formats button[data-format='{fmt}']")
            f = Path(out_dir) / f"{tag}.{fmt}"
            d.value.save_as(str(f))
            body = file_text(f, fmt)
            flat = re.sub(r"\s+", " ", body)
            dl[fmt] = {"name": d.value.suggested_filename, "has_typed": all(re.sub(r"\s+", " ", t) in flat for t in typed)}
            if fmt == "txt":
                # the clipboard and a text box give line breaks as \n; the text file keeps the tool's \r\n
                dl[fmt]["same_as_copy"] = body.replace("﻿", "", 1).replace("\r\n", "\n") == clip.replace("\r\n", "\n")
        except Exception as e:
            dl[fmt] = {"error": str(e)[:200]}
        pg.wait_for_timeout(300)
    r["downloads"] = dl
    dl_ok = all(v.get("has_typed") for v in dl.values()) and dl.get("txt", {}).get("same_as_copy")
    ok = words_ok and r["help_mouse_keyboard"] and (copy_ok and fb_ok and dl_ok if need_typed else True)
    return bool(ok), r


def file_text(path, fmt):
    if fmt in ("md", "txt"):
        return Path(path).read_text(encoding="utf-8")
    if fmt == "docx":
        import zipfile
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        import html as h
        return "\n".join(h.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S))) for p in paras)
    if fmt == "pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    return ""


def no_untrue(pg):
    vis = pg.evaluate(VISIBLE_TEXT)
    return [u for u in UNTRUE if u in vis], [s for s in SAVED if s in vis]


def place_rjw(pg, W, out, tag):
    """Place 1: the Reflect · Journal · Witness window (Chapter 11, and Chapter 6's)."""
    pid = pg.evaluate("() => (window.WOP_PAUSES || [])[0].id")
    pg.evaluate(f"() => RJW.openModal({json.dumps(pid)}, 'reflect')")
    pg.fill("#reflect-ta", TYPED + " R")
    pg.evaluate("() => RJW.saveResponse('reflect')")
    pg.wait_for_timeout(300)
    indicator = pg.evaluate("() => { const i = document.getElementById('save-reflect'); return getComputedStyle(i).display !== 'none' && getComputedStyle(i).opacity !== '0'; }")
    placeholder = pg.evaluate("() => document.getElementById('reflect-ta').placeholder")
    pg.evaluate("() => RJW.switchTab('journal')")
    pg.fill("#journal-ta", "Journal — Χριστός")
    pg.evaluate("() => RJW.closeModal()")
    pg.wait_for_timeout(200)
    pg.evaluate(f"() => RJW.openModal({json.dumps(pid)}, 'journal')")
    kept_j = pg.evaluate("() => document.getElementById('journal-ta').value")
    pg.evaluate("() => RJW.switchTab('reflect')")
    kept_r = pg.evaluate("() => document.getElementById('reflect-ta').value")
    untrue, saved = no_untrue(pg)
    ok_b, det = check_block(pg, "#rjwPanel .wop-sb", W, [TYPED + " R", "Journal — Χριστός"], out, tag)
    pg.evaluate("() => RJW.closeModal()")
    res = {"survives_close_reopen": kept_r == TYPED + " R" and kept_j == "Journal — Χριστός", "saved_indicator_shown": indicator,
           "placeholder": placeholder, "untrue_shown": untrue, "saved_shown": saved, "block": det}
    ok = ok_b and res["survives_close_reopen"] and not indicator and "stay on this device" not in placeholder and not untrue and not saved
    return ok, res


def place_panel(pg, W, out, tag):
    """Place 2: the Reflections panel (My questions)."""
    pg.click(".wop-rp-tab")
    pg.fill("#wopRpQuestion", TYPED + " Q")
    pg.click(".wop-rp-questions .wop-rp-btn")              # its Save
    pg.wait_for_timeout(800)
    after_save = pg.evaluate("() => document.getElementById('wopRpQuestion').value")
    pg.click("#wopReflectionsPanel .wop-rp-close"); pg.wait_for_timeout(200); pg.click(".wop-rp-tab"); pg.wait_for_timeout(200)
    kept = pg.evaluate("() => document.getElementById('wopRpQuestion').value")
    untrue, saved = no_untrue(pg)
    ok_b, det = check_block(pg, "#wopReflectionsPanel .wop-sb", W, [TYPED + " Q"], out, tag)
    pg.click("#wopReflectionsPanel .wop-rp-close")
    res = {"kept_after_save": after_save == TYPED + " Q", "survives_close_reopen": kept == TYPED + " Q",
           "untrue_shown": untrue, "saved_shown": saved, "block": det}
    return ok_b and res["kept_after_save"] and res["survives_close_reopen"] and not untrue and not saved, res


def place_cards(pg, W, out, tag):
    """Place 4: the card-chapter Save (Chapter 12). The block follows the card being written in."""
    first_parent = pg.evaluate("() => { const b = document.querySelector('.card-panel .wop-sb'); return b ? b.parentElement.dataset.card : null; }")
    pg.click(".card-tab[data-card='2'][data-tab='personalize']")
    pg.click("#card-2 .commitment-option >> nth=0")
    pg.fill("#card-2 .reflection-area", TYPED + " C")
    moved = pg.evaluate("() => { const b = document.querySelector('.card-panel .wop-sb'); return b ? b.parentElement.dataset.card : null; }")
    choice = pg.evaluate("() => { const t = document.querySelector('#card-2 .commitment-option .option-text').cloneNode(true); const g = t.querySelector('.option-tag'); if (g) g.remove(); return t.textContent.trim(); }")
    pg.click(".card-save-btn[data-card='2']")
    pg.wait_for_timeout(300)
    btn = pg.evaluate("() => document.querySelector('.card-save-btn[data-card=\"2\"]').textContent.trim()")
    untrue, saved = no_untrue(pg)
    ok_b, det = check_block(pg, ".card-panel .wop-sb", W, [TYPED + " C", choice[:77]], out, tag)
    res = {"first_at_card": first_parent, "moved_to_card": moved, "save_label": btn, "untrue_shown": untrue, "saved_shown": saved, "block": det}
    return ok_b and first_parent == "1" and moved == "2" and "Saved" not in btn and not untrue and not saved, res


def place_sjn(pg, path, W, out, tag):
    """Place 5: Seeking Jesus (starting point, Code It, conversation builder, self-check and goals)."""
    typed = []
    if path == "/seeking-jesus/":
        pg.click(".sj-lensbtn >> nth=0"); pg.wait_for_timeout(200)
        badge = pg.evaluate("() => document.getElementById('sj-lensbadge-v').textContent")
        typed = ["Latter-day Saint background"]
        extra = {"badge_after_choice": badge}
    elif path == "/seeking-jesus/code-it/":
        pg.click(".sj-exercise >> nth=1 >> .sj-choice >> nth=0")
        pg.fill(".sj-exercise >> nth=1 >> textarea", TYPED + " N")
        pg.click(".sj-exercise >> nth=1 >> .sj-save-note"); pg.wait_for_timeout(200)
        typed = [TYPED + " N"]
        extra = {"block_in_exercise": pg.evaluate("() => { const b = document.querySelector('#sj-app div.wop-sb'); const e = b && b.closest('.sj-exercise'); return e ? e.dataset.id : null; }"),
                 "second_exercise": pg.evaluate("() => document.querySelectorAll('.sj-exercise')[1].dataset.id")}
    elif path == "/seeking-jesus/self-check/":
        pg.evaluate("() => document.querySelector(\".sj-scale[data-phase='pre'] input[value='2']\").click()")
        pg.fill("#sj-goal-text", TYPED + " G"); pg.click("#sj-goalform button[type=submit]")
        pg.fill("#sj-goal-text", "Second goal, still being written")
        pg.click("#sj-goals-journal"); pg.wait_for_timeout(200)
        typed = [TYPED + " G", "Second goal, still being written", ": before 2, after —"]
        extra = {"compare_shows_choice": pg.evaluate("() => document.querySelector('.sj-compare .c-pre').textContent")}
    else:  # conversation
        pg.select_option("#sj-build-pick", index=1)
        script = pg.evaluate("() => document.getElementById('sj-build-script').textContent")
        typed = [script]
        extra = {}
    untrue, saved = no_untrue(pg)
    toast = pg.evaluate("() => { const t = document.querySelector('.sj-toast'); return t && t.classList.contains('is-on') ? t.textContent : ''; }")
    ok_b, det = check_block(pg, "#sj-app div.wop-sb", W, typed, out, tag)
    res = dict(extra, untrue_shown=untrue, saved_shown=saved, toast=toast, block=det)
    ok = ok_b and not untrue and not saved and not toast
    if "badge_after_choice" in extra:
        ok = ok and extra["badge_after_choice"] == "Latter-day Saint background"
    if "block_in_exercise" in extra:
        ok = ok and extra["block_in_exercise"] == extra["second_exercise"]
    return ok, res


def place_articles(pg, W, out, tag):
    """Place 7: the Articles reflection boxes, and the switch-ON own-question box (T4)."""
    pg.fill(".rjw-textarea >> nth=0", TYPED + " A1")
    pg.fill(".rjw-textarea >> nth=4", TYPED + " A5")
    pg.wait_for_timeout(900)
    near = pg.evaluate("() => { const b = document.querySelector('.article-body > div.wop-sb, div.wop-sb:not(.wop-sb--panel)'); const p = b && b.previousElementSibling; const t = p && p.querySelector('.rjw-textarea'); return t ? t.dataset.rjwKey : null; }")
    typed = [TYPED + " A1", TYPED + " A5"]
    expect_near = pg.evaluate("() => document.querySelectorAll('.rjw-textarea')[4].dataset.rjwKey")   # the box last typed in
    t4 = pg.evaluate("() => document.querySelectorAll('.an-learner').length")
    extra = {"block_after": near, "expected_after": expect_near, "t4_boxes": t4}
    if t4:
        pg.evaluate("(t) => { const b = document.querySelector('.an-learner-box'); b.value = t; b.dispatchEvent(new Event('input', {bubbles: true})); }", TYPED + " T4")
        typed.append(TYPED + " T4")
        extra["t4_notes"] = pg.evaluate("() => [...new Set([...document.querySelectorAll('.an-learner-note')].map(n => n.textContent))]")
    untrue, saved = no_untrue(pg)
    ok_b, det = check_block(pg, "div.wop-sb:not(.wop-sb--panel)", W, typed, out, tag)
    res = dict(extra, untrue_shown=untrue, saved_shown=saved, block=det)
    ok = ok_b and near == expect_near and not untrue and not saved
    if t4:
        ok = ok and extra["t4_notes"] == ["Nothing is sent."]
    return ok, res


def place_journal(pg, W):
    """Place 3: /my-reflections/: W4 in place of the empty journal, W5 beneath it, no Copy or Download."""
    st = pg.evaluate("""() => { const b = document.querySelector('div.wop-sb--journal'); if (!b) return null;
        const det = b.querySelector('details');
        return { msg: b.querySelector('.wop-sb-msg').textContent, buttons: b.querySelectorAll('.wop-sb-actions').length,
                 open: det.open, summary: det.querySelector('summary').textContent,
                 lines: [...det.querySelectorAll('.wop-sb-lines li')].map(li => [...li.childNodes].filter(c => !(c.classList && c.classList.contains('wop-sb-links'))).map(c => c.textContent).join('')),
                 links: [...det.querySelectorAll('a')].map(a => a.href),
                 emptyShown: getComputedStyle(document.getElementById('djEmpty')).display !== 'none' };}""")
    if not st:
        return False, {"error": "no W4 block"}
    eh = expected_help(W)
    pg.click("div.wop-sb--journal details > summary")
    opened = pg.evaluate("() => document.querySelector('div.wop-sb--journal details').open")
    ok = (st["msg"] == W["w4"] and st["buttons"] == 0 and st["open"] is False and st["summary"] == W["summary"]
          and st["lines"] == [e["text"] for e in eh] and st["links"] == [h for e in eh for h in e["links"]]
          and not st["emptyShown"] and opened)
    return ok, st


def place_approaches(pg, W, out, tag):
    """Place 8: Approaches to Belief: W1 replaces one sentence on the card; nothing else; the page's own download works."""
    st = pg.evaluate("""() => { const p = document.getElementById('ab-dl').parentNode.querySelector('p');
        return { text: p.textContent, blocks: document.querySelectorAll('div.wop-sb').length,
                 buttons: [...document.getElementById('ab-dl').parentNode.querySelectorAll('button')].map(b => b.textContent) }; }""")
    expect = W["w1"] + " Nothing was sent anywhere and no one has seen it. Download it, print it, or keep it here for next time."
    filled = pg.evaluate("""(t) => { const ta = [...document.querySelectorAll('textarea')][0]; if (!ta) return null;
        ta.value = t; ta.dispatchEvent(new Event('input', {bubbles: true})); ta.dispatchEvent(new Event('change', {bubbles: true})); return ta.id || ta.name || 'textarea'; }""", TYPED + " AB")
    pg.wait_for_timeout(300)
    try:
        with pg.expect_download(timeout=20000) as d:
            pg.evaluate("() => document.getElementById('ab-dl').click()")
        f = Path(out) / f"{tag}.txt"; d.value.save_as(str(f))
        has = (TYPED + " AB") in f.read_text(encoding="utf-8")
    except Exception as e:
        has = "error: " + str(e)[:150]
    res = dict(st, field=filled, own_download_has_typed=has)
    ok = st["text"] == expect and st["blocks"] == 0 and st["buttons"] == ["Download my reflections", "Print", "Erase everything"] and has is True
    return ok, res


MSG_PAGES = [("/chapters/11-the-living-christ/", "rjw"), ("/chapters/11-the-living-christ/", "panel"),
             ("/chapters/06-embrace-the-savior/", "rjw"), ("/chapters/12-beatitudes/", "cards"),
             ("/seeking-jesus/", "sjn"), ("/seeking-jesus/code-it/", "sjn"), ("/seeking-jesus/conversation/", "sjn"),
             ("/seeking-jesus/self-check/", "sjn"), ("/articles/", "articles"), ("/my-reflections/", "journal"),
             ("/studies/approaches-to-belief/", "approaches")]


def run_place(ctx, base, path, kind, W, out, tag, errs, reqs):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append({"page": path, "text": str(e), "stack": (getattr(e, "stack", "") or "")[:300]}))
    leave = []
    pg.on("dialog", lambda d: (leave.append(d.type), d.dismiss()))
    pg.on("request", lambda r: reqs.append({"url": r.url, "post": r.post_data or ""}))
    pg.route("**/*", lambda r: r.continue_() if (r.request.url.startswith(base) and "/_vercel/insights/" not in r.request.url)
             or "cdnjs.cloudflare.com/ajax/libs/pdfmake/" in r.request.url else r.abort())
    pg.goto(base + path, wait_until="load")
    pg.wait_for_timeout(700)
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
    try:
        if kind == "rjw": ok, res = place_rjw(pg, W, out, tag)
        elif kind == "panel": ok, res = place_panel(pg, W, out, tag)
        elif kind == "cards": ok, res = place_cards(pg, W, out, tag)
        elif kind == "sjn": ok, res = place_sjn(pg, path, W, out, tag)
        elif kind == "articles": ok, res = place_articles(pg, W, out, tag)
        elif kind == "journal": ok, res = place_journal(pg, W)
        else: ok, res = place_approaches(pg, W, out, tag)
    except Exception as e:
        ok, res = False, {"error": str(e)[:400]}
    pg.close(run_before_unload=True)
    time.sleep(0.3)
    res["leave_prompt"] = [t for t in leave if t == "beforeunload"]
    return ok and not res["leave_prompt"], res


def check_message(pw, browser, base, out, wording):
    W = read_wording(wording)
    res, ok = {}, True
    for mode in BLOCKED:
        ctx = make_context(pw, browser, mode)
        res[mode] = {}
        errs, reqs = [], []
        for i, (path, kind) in enumerate(MSG_PAGES):
            tag = f"{mode}_{i:02d}_{kind}"
            p_ok, r = run_place(ctx, base, path, kind, W, out, tag, errs, reqs)
            res[mode][f"{path} [{kind}]"] = {"pass": p_ok, **r}
            ok = ok and p_ok
        # nothing the reader typed leaves the device
        leaks = [r["url"] for r in reqs if any(s in (r["url"] + r["post"]) for s in ("Ἰησοῦς", "%E1%BC%B8", "love one another", "love%20one"))]
        bad_errs = [e for e in errs]
        res[mode]["_network"] = {"requests": len(reqs), "carrying_typed_words": leaks,
                                 "other_hosts": sorted({re.match(r"https?://[^/]+", r["url"]).group(0) for r in reqs if not r["url"].startswith(base)})}
        res[mode]["_page_errors"] = bad_errs
        ok = ok and not leaks and not bad_errs
        ctx.close()
    (Path(out) / "message.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = {m: sum(1 for k, v in r.items() if not k.startswith("_") and v["pass"]) for m, r in res.items()}
    return ok, f"places passing per blocked mode (of {len(MSG_PAGES)}): {summary}; page errors: " + str({m: len(r['_page_errors']) for m, r in res.items()}) \
        + "; requests carrying typed words: " + str({m: len(r['_network']['carrying_typed_words']) for m, r in res.items()})


def check_available(pw, browser, base, out):
    """With storage working, nothing of the blocked-storage message reaches the page."""
    res, ok = {}, True
    ctx = make_context(pw, browser, "available")
    for path in sorted({p for p, _ in MSG_PAGES}):
        reqs, errs = [], []
        pg = ctx.new_page()
        pg.on("request", lambda r: reqs.append(r.url))
        pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) and "/_vercel/insights/" not in r.request.url else r.abort())
        pg.goto(base + path, wait_until="load"); pg.wait_for_timeout(600)
        st = pg.evaluate("""() => ({ cls: document.documentElement.className, blocks: document.querySelectorAll('div.wop-sb').length,
            ph: (document.getElementById('reflect-ta') || {}).placeholder || null,
            notices: [...document.querySelectorAll('.rjw-auth-notice, .wop-rp-sub, .summary-subtitle, #lens .sj-mute, [data-module="code-it"] .sj-note, #goals .sj-note')].map(n => n.textContent.trim().slice(0, 40)) })""")
        if "/rjw" in path or path.startswith("/chapters/11"):
            pg.evaluate("() => RJW.openModal(window.WOP_PAUSES[0].id, 'reflect')"); pg.wait_for_timeout(200)
            st["rjw_notice_visible"] = pg.evaluate("() => getComputedStyle(document.querySelector('#tab-reflect .rjw-auth-notice')).display !== 'none'")
        st["blocked_files_requested"] = [u for u in reqs if "wop-storage-blocked" in u]
        p_ok = "wop-storage-blocked" not in st["cls"] and st["blocks"] == 0 and not st["blocked_files_requested"] \
            and (st["ph"] is None or "Your answers stay on this device." in st["ph"]) and st.get("rjw_notice_visible", True)
        res[path] = {"pass": p_ok, **st}
        ok = ok and p_ok
        pg.close()
    ctx.close()
    (Path(out) / "available.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return ok, f"{sum(1 for v in res.values() if v['pass'])}/{len(res)} pages show nothing new and request no blocked-storage file"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site"); ap.add_argument("--prod")
    ap.add_argument("--all", action="store_true", help="load check on every page of the build (local only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--checks", default="load,controls,honest,message,available")
    ap.add_argument("--wording", default=str(WORDING))
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    srv = None
    if a.prod:
        base = a.prod.rstrip("/")
        pages = KEY_PAGES
    else:
        srv, base = serve(a.site)
        pages = site_pages(a.site) if a.all else KEY_PAGES
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, fn in (("load", lambda: check_load(pw, browser, base, pages, a.out)),
                         ("controls", lambda: check_controls(pw, browser, base, KEY_PAGES, a.out)),
                         ("honest", lambda: check_honest(pw, browser, base, a.out)),
                         ("message", lambda: check_message(pw, browser, base, a.out, a.wording)),
                         ("available", lambda: check_available(pw, browser, base, a.out))):
            if name not in a.checks.split(","):
                continue
            passed, summary = fn()
            results[name] = {"pass": passed, "summary": summary}
            print(f"CHECK {name}: {'PASS' if passed else 'FAIL'} - {summary}", flush=True)
        browser.close()
    if srv:
        srv.shutdown()
    (Path(a.out) / "summary.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    all_ok = all(r["pass"] for r in results.values())
    print("ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
