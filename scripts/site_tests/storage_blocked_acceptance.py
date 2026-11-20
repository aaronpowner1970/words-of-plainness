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

Usage:
  python scripts/site_tests/storage_blocked_acceptance.py --site _site [--all] --out <dir>
  python scripts/site_tests/storage_blocked_acceptance.py --prod https://www.wordsofplainness.org --out <dir>
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site"); ap.add_argument("--prod")
    ap.add_argument("--all", action="store_true", help="load check on every page of the build (local only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--checks", default="load,controls,honest")
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
                         ("honest", lambda: check_honest(pw, browser, base, a.out))):
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
