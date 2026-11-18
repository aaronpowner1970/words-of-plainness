"""Acceptance checks for Privacy Policy v1.2 (CODE-SITE-22, SITE step 33).

Checks, each runnable against a locally served build or production:
  wording    the Privacy and Under the Hood passages match the approved file (with its
             AMENDMENT section) word for word, apostrophes and dashes included; "corrections
             form" appears nowhere on /privacy/; the footer reads v1.2 with the go-live date;
             everything else on the two pages is unchanged from the baseline build.
  banner     the N2 notice at 375, 768 and 1440 px on a set of pages: shown, covers nothing
             (nothing sits over it, the header sits below it, page content and the chat bar
             are pushed down by exactly its height), keyboard reachable, accessible names,
             dismiss + remembered on reload, blocked storage raises no error, the date window.
  analytics  page views go to /_vercel/insights/view on the site's own origin; the page
             address and referrer carry no query string or fragment (loaded with ?test=1#x
             and a referrer carrying ?q=...#...); no custom events; no cookies.
  quiet      typing and saving in the R·J·W journal modal, the Reflections panel and a
             card-chapter reflection cause no request of any kind (analytics included).
  forms      contact and newsletter: same fields, endpoint, content type and confirmation
             as the baseline build, with the API stubbed so nothing is sent.

Usage:
  python scripts/site_tests/privacy_v12_acceptance.py --site <build dir> | --prod https://www.wordsofplainness.org
      --baseline <baseline build dir> --approved <approved wording .md> --out <evidence dir>
      [--insights-script <copy of /_vercel/insights/script.js, for local runs>] [--checks wording,banner,...]
"""
import argparse
import html as htmlmod
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import journal_acceptance as ja  # noqa: E402
from network_allowlist import classify_page_load, classify_action, is_analytics, analytics_payload_problems  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

GO_LIVE = "18 November 2026"
WIDTHS = [375, 768, 1440]
BANNER_PAGES = ["/", "/privacy/", "/about/under-the-hood/", "/connect/", "/chapters/11-the-living-christ/",
                "/chapters/12-beatitudes/", "/articles/", "/seeking-jesus/", "/my-reflections/", "/music/",
                "/chat/", "/chat/video-01/"]
REAL_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Chrome/148.0.0.0 Safari/537.36")
# The analytics script does nothing under automation (navigator.webdriver, "Headless" in the
# user agent). To see what a real reader's browser sends, the analytics checks present as a
# normal browser. Nothing else about the page is changed.
NOT_AUTOMATED = "Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => false, configurable: true });"
BLOCK_STORAGE = """(() => {
  const thrower = { get() { throw new DOMException('The operation is insecure.', 'SecurityError'); }, configurable: true };
  try { Object.defineProperty(window, 'localStorage', thrower); } catch (e) {}
  try { Object.defineProperty(window, 'sessionStorage', thrower); } catch (e) {}
})();"""
RESULTS = {}


def record(name, ok, summary, evidence):
    RESULTS[name] = {"pass": bool(ok), "summary": summary, "evidence": evidence}
    print(f"CHECK {name}: {'PASS' if ok else 'FAIL'} - {summary}", flush=True)


def write(out, name, data):
    return ja.write(out, name, data)


# ------------------------------------------------------------------ text helpers
def page_html(base, path, site_dir=None):
    if site_dir:
        p = Path(site_dir) / path.strip("/") / "index.html"
        return p.read_text(encoding="utf-8")
    req = urllib.request.Request(base + path, headers={"User-Agent": "WoP-acceptance-check (CODE-SITE-22)",
                                                       "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def text_of(fragment):
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment)
    s = re.sub(r"(?s)<!--.*?-->", " ", s)
    s = re.sub(r"(?i)</t[hd]>", " ", s)   # table cells read as separate words
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def main_text(page_src):
    m = re.search(r"(?s)<main\b[^>]*>(.*)</main>", page_src)
    return text_of(m.group(1) if m else page_src)


def banner_text(page_src):
    m = re.search(r'(?s)<p class="wop-privacy-notice-text"[^>]*>(.*?)</p>', page_src)
    return text_of(m.group(1)) if m else None


def line_after(md, marker):
    i = md.index(marker) + len(marker)
    for line in md[i:].splitlines()[1:] if not md[i:].startswith("\n") else md[i:].splitlines():
        if line.strip():
            return line.strip()
    raise ValueError(marker)


def lines_after(md, marker, n):
    i = md.index(marker) + len(marker)
    out = []
    for line in md[i:].splitlines()[1:]:
        if line.strip():
            out.append(line.strip())
            if len(out) == n:
                return out
    raise ValueError(marker)


def approved_items(md):
    """(page, label, expected text) from the approved file, the AMENDMENT winning."""
    amend = md[md.index("## AMENDMENT"):]
    n1 = md[md.index("**N1."):md.index("**N2.")]
    n1_bullets = [l[2:].strip() for l in n1.splitlines() if l.startswith("- ")]
    a1_before = lines_after(md, "Replace the paragraph before the list with:", 2)
    items = [
        ("privacy", "C1 (no change)", "Two forms on this site accept information:"),
        ("privacy", "C2 (amended)", line_after(amend, "**C2 (superseding)**")),
        ("privacy", "C3 (amended)", line_after(amend, "**C3 (superseding)**")),
        ("privacy", "S1/S2", "Submissions from the contact and newsletter forms pass through a"),
        ("privacy", "S1/S2", "receives submissions from the contact and newsletter forms."),
        ("privacy", "A1 before list (1)", a1_before[0]),
        ("privacy", "A1 before list (2)", a1_before[1]),
        ("privacy", "A1 after list", line_after(md, "Replace the paragraph after the list with:")),
        ("privacy", "A2", line_after(md, "**A2. Cloudflare (lines 204-209)**")),
        ("privacy", "A3", line_after(md, "**A3. Vercel (lines 212-216)**")),
        ("privacy", "A5", line_after(md, "**A5. Retention bullet (lines 385-388)**")),
        ("privacy", "N1 heading", line_after(md, "**N1. \"What changed\" box at the top of the Privacy page (give it a stable anchor id for the banner link)**")),
        ("privacy", "N1 bullet 1", n1_bullets[0]),
        ("privacy", "N1 bullet 2 (amended)", line_after(amend, "**N1 bullet 2 (superseding)**")),
        ("privacy", "N1 bullet 3", n1_bullets[2]),
        ("privacy", "N1 bullet 4", n1_bullets[3]),
        ("privacy", "Footer v1.2", "Words of Plainness Privacy Policy v1.2 &mdash; Aaron Powner Publishing &mdash; [date]. "
                                   "This policy is reviewed periodically and updated as the ministry&rsquo;s scope and the services we rely on change."),
        ("uth", "S3", "The few things that must be dynamic—the contact and newsletter forms—talk"),
        ("uth", "U-A", line_after(md, "**U-A. Line 60, the closing clause from \"and no tracking scripts\" to the end of the sentence, becomes:**").lstrip(".")),
        ("uth", "U-B", line_after(md, "**U-B. Line 463**")),
        ("uth", "U-C", "Do you track visitors? " + line_after(md, "**U-C. Line 531, the Quick answer to \"Do you track visitors?\"**")),
        ("uth", "API row (unchanged)", "Contact and newsletter Contact messages, Articles corrections and newsletter sign-up"),
        ("banner", "N2", lines_after(md, "**N2.", 1)[0]),
    ]
    out = []
    for page, label, raw in items:
        t = text_of(raw.replace("[date]", GO_LIVE))
        if page in ("privacy", "banner"):
            # Approved-file rule: apostrophes are U+2019 on the Privacy page (entities there).
            t = t.replace("'", "’")
        out.append((page, label, t))
    return out


# ------------------------------------------------------------------ wording
def check_wording(base, site_dir, baseline_dir, approved_md, out):
    md = Path(approved_md).read_text(encoding="utf-8")
    pages = {"privacy": page_html(base, "/privacy/", site_dir), "uth": page_html(base, "/about/under-the-hood/", site_dir)}
    texts = {"privacy": main_text(pages["privacy"]), "uth": main_text(pages["uth"])}
    rows, ok = [], True
    for page, label, expected in approved_items(md):
        if page == "banner":
            found = [banner_text(pages["privacy"]), banner_text(pages["uth"])]
            hit = all(f == expected for f in found)
            rows.append({"page": "banner (on /privacy/ and /under-the-hood/)", "item": label, "expected": expected,
                         "found": found[0], "pass": hit})
        else:
            hit = expected in texts[page]
            rows.append({"page": page, "item": label, "expected": expected, "pass": hit})
        ok = ok and hit
    priv = texts["privacy"]
    extra = {
        "corrections_form_count_privacy": len(re.findall(r"corrections form", priv, re.I)),
        "corrections_form_count_privacy_whole_html": len(re.findall(r"corrections form", text_of(pages["privacy"]), re.I)),
        "corrections_word_count_privacy": len(re.findall(r"corrections", priv, re.I)),
        "old_cloudflare_analytics_phrase_gone": "Cloudflare Web Analytics" not in priv,
        "old_contact_claim_gone": "not stored in any other location" not in priv,
        "v1_1_gone": "v1.1" not in priv,
        "anchor_present": 'id="what-changed"' in pages["privacy"],
        "box_first_in_opening": priv.find("What changed on") < priv.find("A companion to our"),
    }
    ok = ok and extra["corrections_form_count_privacy"] == 0 and extra["corrections_form_count_privacy_whole_html"] == 0 \
        and extra["old_cloudflare_analytics_phrase_gone"] and extra["old_contact_claim_gone"] and extra["v1_1_gone"] \
        and extra["anchor_present"] and extra["box_first_in_opening"]
    # A4 and the A1 five-item list: unchanged from the baseline build.
    base_priv = main_text((Path(baseline_dir) / "privacy" / "index.html").read_text(encoding="utf-8"))
    a4 = ("To operate the website. Analytics help us understand which chapters and pages are reaching people, "
          "so we can improve them and prioritize what to write next.")
    extra["A4_unchanged"] = a4 in base_priv and a4 in priv
    lst = lambda t: t[t.find("Page views —"):t.find("This analytics data is anonymized")]
    extra["A1_list_unchanged"] = lst(base_priv) == lst(priv) and len(lst(priv)) > 100
    ok = ok and extra["A4_unchanged"] and extra["A1_list_unchanged"]
    # Sentence-level diff against the baseline: everything that changed must be accounted for.
    def sentences(t):
        return [s.strip() for s in re.split(r"(?<=[.:!?])\s+", t) if s.strip()]
    diff = {}
    for key, path in (("privacy", "privacy"), ("uth", "about/under-the-hood")):
        old = sentences(main_text((Path(baseline_dir) / path / "index.html").read_text(encoding="utf-8")))
        new = sentences(texts[key])
        diff[key] = {"removed": [s for s in old if s not in new], "added": [s for s in new if s not in old]}
    name = write(out, "wording.json", {"items": rows, "checks": extra, "sentence_diff_vs_baseline": diff})
    record("wording", ok, f"{sum(r['pass'] for r in rows)}/{len(rows)} approved items match; extra checks {extra}", [name])


# ------------------------------------------------------------------ banner
GEOM_JS = """() => {
  const r = el => { if (!el) return null; const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
     return {top: b.top, bottom: b.bottom, left: b.left, right: b.right, height: b.height,
             visible: cs.display !== 'none' && cs.visibility !== 'hidden' && b.height > 0, position: cs.position}; };
  const banner = document.getElementById('wopPrivacyNotice');
  const header = document.querySelector('.header');
  const main = document.getElementById('main-content');
  const chatBar = document.querySelector('.chat-bar');
  let firstContent = null;
  if (main) { const w = document.createTreeWalker(main, NodeFilter.SHOW_ELEMENT);
    while (w.nextNode()) { const n = w.currentNode; const b = n.getBoundingClientRect();
      if (!(b.height > 0 && b.width > 0 && b.left < innerWidth && b.right > 0 && n.children.length === 0 && n.textContent.trim())) continue;
      let a = n, pinned = false;
      while (a && a !== main) { const p = getComputedStyle(a).position; if (p === 'fixed' || p === 'sticky' || p === 'absolute') { pinned = true; break; } a = a.parentElement; }
      if (!pinned) { firstContent = n; break; } } }
  const out = {scrollY: window.scrollY, innerWidth: window.innerWidth, scrollWidth: document.documentElement.scrollWidth,
     banner: r(banner), header: r(header), main: r(main), chatBar: r(chatBar), firstContent: r(firstContent),
     firstContentText: firstContent ? firstContent.textContent.trim().slice(0, 60) : null, coveredPoints: []};
  if (banner && out.banner.visible) {
     const b = out.banner;
     for (const fx of [0.05, 0.25, 0.5, 0.75, 0.95]) for (const fy of [0.2, 0.5, 0.8]) {
        const x = b.left + (b.right - b.left) * fx, y = b.top + b.height * fy;
        if (y < 0 || y > innerHeight) continue;
        const top = document.elementFromPoint(x, y);
        if (top && !banner.contains(top)) out.coveredPoints.push({x, y, by: top.tagName + '.' + (top.className || '') + '#' + (top.id || '')});
     } }
  if (chatBar && out.chatBar.visible) {
     const c = out.chatBar; const top = document.elementFromPoint(c.left + 10, c.top + c.height / 2);
     out.chatBarTopmostIsChatBar = !!(top && chatBar.contains(top));
  }
  return out; }"""


def check_banner(pw, base, baseline_base, out, label):
    shots = Path(out) / f"banner_{label}_screens"
    shots.mkdir(exist_ok=True)
    browser = pw.chromium.launch()
    rows, ok = [], True
    for width in WIDTHS:
        height = 812 if width == 375 else (1024 if width == 768 else 900)
        for path in BANNER_PAGES:
            res = {"width": width, "page": path}
            for which, b in (("new", base), ("baseline", baseline_base)):
                ctx = browser.new_context(viewport={"width": width, "height": height})
                page = ctx.new_page()
                page.goto(b + path, wait_until="load", timeout=90000)
                page.wait_for_timeout(1500)
                # Chat film pages open behind a full-screen entry dialog that covers the whole
                # page (banner and chat bar included) until the host enters. Measure the page
                # beneath it, in both builds alike.
                page.evaluate("(() => { const e = document.getElementById('aoidEntry'); if (e) e.remove(); })()")
                g = page.evaluate(GEOM_JS)
                if which == "new":
                    page.screenshot(path=str(shots / f"{width}_{path.strip('/').replace('/', '_') or 'home'}.png"))
                    page.evaluate("window.scrollTo(0, 25)")
                    page.wait_for_timeout(300)
                    g["after_scroll_25"] = page.evaluate(GEOM_JS)
                    page.evaluate("window.scrollTo(0, 600)")
                    page.wait_for_timeout(300)
                    g["after_scroll_600"] = page.evaluate(GEOM_JS)
                res[which] = g
                ctx.close()
            n, o = res["new"], res["baseline"]
            bh = n["banner"]["height"] if n["banner"] and n["banner"]["visible"] else None
            c = {}
            c["banner_shown"] = bool(bh)
            c["banner_in_flow"] = bool(n["banner"]) and n["banner"]["position"] in ("relative", "static")
            c["nothing_over_banner"] = not n["coveredPoints"]
            if n["header"] and n["header"]["visible"]:
                c["header_below_banner"] = n["header"]["top"] >= n["banner"]["bottom"] - 1
                s25 = n["after_scroll_25"]
                c["header_follows_banner_on_scroll"] = abs(s25["header"]["top"] - max(0, s25["banner"]["bottom"])) <= 1
                c["header_at_top_after_banner_gone"] = abs(n["after_scroll_600"]["header"]["top"]) <= 1 \
                    if n["after_scroll_600"]["scrollY"] >= bh else True
            if n["main"] and o["main"]:
                c["content_pushed_down_by_banner_height"] = abs((n["main"]["top"] - o["main"]["top"]) - bh) <= 1.5
            if n["firstContent"] and o["firstContent"] and n["firstContentText"] == o["firstContentText"]:
                c["first_content_pushed_down_by_banner_height"] = abs((n["firstContent"]["top"] - o["firstContent"]["top"]) - bh) <= 1.5
                if n["header"] and n["header"]["visible"]:
                    gap_new = n["firstContent"]["top"] - n["header"]["bottom"]
                    gap_old = o["firstContent"]["top"] - o["header"]["bottom"]
                    c["header_to_content_gap_unchanged"] = abs(gap_new - gap_old) <= 1.5
            if n["chatBar"] and n["chatBar"]["visible"]:
                c["chat_bar_below_banner"] = n["chatBar"]["top"] >= n["banner"]["bottom"] - 1
                c["chat_bar_pushed_down_by_banner_height"] = abs((n["chatBar"]["top"] - o["chatBar"]["top"]) - bh) <= 1.5
                c["chat_bar_uncovered"] = n.get("chatBarTopmostIsChatBar", False)
            c["no_new_horizontal_scroll"] = not (n["scrollWidth"] > n["innerWidth"] and o["scrollWidth"] <= o["innerWidth"])
            res["banner_height"] = bh
            res["checks"] = c
            res["pass"] = all(c.values())
            ok = ok and res["pass"]
            rows.append(res)
    browser.close()
    name = write(out, f"banner_geometry_{label}.json", rows)
    record(f"banner-geometry-{label}", ok, f"{sum(r['pass'] for r in rows)}/{len(rows)} page x width cases pass", [name, shots.name])


def serve_insights(ctx, insights_script):
    if insights_script:
        body = Path(insights_script).read_bytes()

        def script_handler(route):
            route.fulfill(status=200, content_type="application/javascript", body=body)
        ctx.route("**/_vercel/insights/script.js", script_handler)
        ctx.route("**/_vercel/insights/view", lambda r: r.fulfill(status=200, body="OK"))


def check_banner_behaviour(pw, base, baseline_base, out, label, insights_script=None):
    ev, ok = {}, True
    browser = pw.chromium.launch()
    # Accessible names and keyboard order
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(base + "/about/", wait_until="load")
    page.wait_for_timeout(800)
    region = page.get_by_role("region", name=re.compile(r"^Our Privacy Policy changed on"))
    link = page.get_by_role("link", name="See what changed")
    button = page.get_by_role("button", name="Dismiss")
    a = {"region_by_name": region.count(), "link_by_name": link.count(), "link_href": link.first.get_attribute("href") if link.count() else None,
         "button_by_name": button.count()}
    order = []
    for _ in range(3):
        page.keyboard.press("Tab")
        order.append(page.evaluate("(() => { const e = document.activeElement; return (e.tagName + ' ' + (e.textContent || '').trim()).slice(0, 60); })()"))
    a["tab_order_first_three"] = order
    a["keyboard_ok"] = order[1].startswith("A See what changed") and order[2] == "BUTTON Dismiss"
    page.keyboard.press("Enter")   # Dismiss by keyboard
    page.wait_for_timeout(300)
    a["dismissed_by_keyboard"] = page.locator("#wopPrivacyNotice").count() == 0
    a["focus_after_dismiss"] = page.evaluate("(() => { const e = document.activeElement; return e.tagName + ' ' + (e.className || ''); })()")
    a["stored_flag"] = page.evaluate("localStorage.getItem('wop-privacy-notice-v1.2-dismissed')")
    a["header_top_after_dismiss"] = page.evaluate("document.querySelector('.header').getBoundingClientRect().top")
    page.reload(wait_until="load")
    page.wait_for_timeout(800)
    a["absent_after_reload"] = page.locator("#wopPrivacyNotice").count() == 0
    page.goto(base + "/privacy/", wait_until="load")
    page.wait_for_timeout(500)
    a["absent_on_other_page"] = page.locator("#wopPrivacyNotice").count() == 0
    ctx.close()
    a["pass"] = a["region_by_name"] == 1 and a["link_by_name"] == 1 and a["link_href"] == "/privacy/#what-changed" and \
        a["button_by_name"] == 1 and a["keyboard_ok"] and a["dismissed_by_keyboard"] and a["stored_flag"] == "1" and \
        abs(a["header_top_after_dismiss"]) <= 1 and a["absent_after_reload"] and a["absent_on_other_page"]
    ev["a11y_keyboard_dismiss_persist"] = a
    ok = ok and a["pass"]

    # Mouse dismiss, and the link lands on the N1 box
    ctx = browser.new_context(viewport={"width": 375, "height": 812})
    page = ctx.new_page()
    page.goto(base + "/", wait_until="load")
    page.wait_for_timeout(800)
    page.click("#wopPrivacyNotice a")
    page.wait_for_load_state("load")
    page.wait_for_timeout(1200)
    m = {"url_after_link": page.url.replace(base, ""),
         "box_in_view": page.evaluate("(() => { const b = document.getElementById('what-changed').getBoundingClientRect(); return b.top >= 0 && b.top < innerHeight; })()"),
         "box_heading_not_under_header": page.evaluate("(() => { const h = document.querySelector('#what-changed h2').getBoundingClientRect(); const hd = document.querySelector('.header').getBoundingClientRect(); return h.top >= hd.bottom - 1; })()")}
    page.screenshot(path=str(Path(out) / f"banner_{label}_link_lands_375.png"))
    page.click("#wopPrivacyNoticeDismiss")
    page.wait_for_timeout(300)
    m["dismissed_by_click"] = page.locator("#wopPrivacyNotice").count() == 0
    page.reload(wait_until="load")
    m["absent_after_reload"] = page.locator("#wopPrivacyNotice").count() == 0
    m["pass"] = m["url_after_link"] == "/privacy/#what-changed" and m["box_in_view"] and m["box_heading_not_under_header"] and m["dismissed_by_click"] and m["absent_after_reload"]
    ev["mouse_link_and_dismiss"] = m
    ok = ok and m["pass"]
    ctx.close()

    # Storage blocked: the banner shows, dismisses for the page, raises no error of its own.
    pages = ["/", "/privacy/", "/chapters/11-the-living-christ/"]
    s = {}
    for which, b in (("new", base), ("baseline", baseline_base)):
        ctx = browser.new_context(viewport={"width": 768, "height": 1024})
        ctx.add_init_script(BLOCK_STORAGE)
        serve_insights(ctx, insights_script)
        errs = {}
        cur = {"p": None}
        page = ctx.new_page()
        page.on("console", lambda m, errs=errs, cur=cur: errs.setdefault(cur["p"], []).append("console." + m.type + ": " + m.text + " @ " + str(m.location.get("url"))) if m.type == "error" else None)
        page.on("pageerror", lambda e, errs=errs, cur=cur: errs.setdefault(cur["p"], []).append("pageerror: " + str(e) + " | " + (e.stack or "").splitlines()[1:2].__str__()))
        shown = {}
        for p in pages:
            cur["p"] = p
            page.goto(b + p, wait_until="load")
            page.wait_for_timeout(1200)
            shown[p] = page.locator("#wopPrivacyNotice:not([hidden])").count() == 1
        if which == "new":
            cur["p"] = "dismiss and reload"
            page.click("#wopPrivacyNoticeDismiss")
            page.wait_for_timeout(300)
            shown["dismissed_on_page"] = page.locator("#wopPrivacyNotice").count() == 0
            page.reload(wait_until="load")
            page.wait_for_timeout(800)
            shown["shows_again_after_reload"] = page.locator("#wopPrivacyNotice:not([hidden])").count() == 1
        s[which] = {"shown": shown, "errors": errs}
        ctx.close()
    def strip_port(e):
        return re.sub(r"127\.0\.0\.1:\d+", "HOST", e)
    new_errs = {}
    for p in pages:
        old_list = [strip_port(e) for e in s["baseline"]["errors"].get(p, [])]
        new_list = [strip_port(e) for e in s["new"]["errors"].get(p, [])]
        extra = list(new_list)
        for e in old_list:
            if e in extra:
                extra.remove(e)
        if extra:
            new_errs[p] = extra
    s["errors_not_in_baseline_per_page"] = new_errs
    all_new = [e for v in s["new"]["errors"].values() for e in v]
    s["banner_errors"] = [e for e in all_new if "privacy" in e.lower() or "notice" in e.lower() or "wopPrivacy" in e]
    s["errors_after_dismiss_and_reload"] = s["new"]["errors"].get("dismiss and reload", [])
    s["pass"] = all(s["new"]["shown"].values()) and not new_errs and not s["banner_errors"]
    ev["storage_blocked"] = s
    ok = ok and s["pass"]

    # Date window (reader's local date): shows 18 Nov - 17 Dec 2026, gone from 18 Dec 2026.
    d = {}
    for when, expect in (("2026-11-17T23:59:00", False), ("2026-11-18T00:00:30", True), ("2026-12-01T12:00:00", True),
                         ("2026-12-17T23:59:00", True), ("2026-12-18T00:00:30", False), ("2027-03-01T12:00:00", False)):
        ctx = browser.new_context()
        page = ctx.new_page()
        page.clock.set_fixed_time(datetime.fromisoformat(when))
        page.goto(base + "/", wait_until="load")
        page.wait_for_timeout(500)
        got = page.locator("#wopPrivacyNotice:not([hidden])").count() == 1
        d[when] = {"shown": got, "expected": expect, "pass": got == expect}
        ctx.close()
    d["pass"] = all(v["pass"] for v in d.values() if isinstance(v, dict))
    ev["date_window"] = d
    ok = ok and d["pass"]
    browser.close()
    name = write(out, f"banner_behaviour_{label}.json", ev)
    record(f"banner-behaviour-{label}", ok, "names, keyboard, dismiss and reload, link target, blocked storage, date window", [name])


# ------------------------------------------------------------------ analytics
def check_analytics(pw, base, out, label, insights_script=None):
    browser = pw.chromium.launch()
    ctx = browser.new_context(user_agent=REAL_UA, viewport={"width": 1440, "height": 900})
    ctx.add_init_script(NOT_AUTOMATED)
    seen = []
    if insights_script:   # local build: serve Vercel's script and accept page views, as Vercel would
        body = Path(insights_script).read_bytes()
        ctx.route("**/_vercel/insights/script.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=body))
        ctx.route("**/_vercel/insights/view", lambda r: r.fulfill(status=200, body="OK"))
    all_reqs = []

    def on_req(r):
        all_reqs.append(r.url)
        if "/_vercel/insights/" in r.url:
            seen.append({"url": r.url, "method": r.method, "post": r.post_data, "headers": {k: v for k, v in r.headers.items()
                         if k.lower() in ("content-type", "cookie", "referer")}})
    responses = []

    def on_resp(r):
        if "/_vercel/insights/" in r.url:
            try:
                h = r.all_headers()
            except Exception:  # noqa: BLE001
                h = {}
            responses.append({"url": r.url, "status": r.status, "set_cookie": h.get("set-cookie")})
    ctx.on("request", on_req)
    ctx.on("response", on_resp)
    page = ctx.new_page()
    loads = [("/about/?test=1#x", "https://example.com/some/path?q=secret-words#frag"),
             ("/privacy/?utm_source=check&x=1#what-changed", None),
             ("/chapters/11-the-living-christ/?test=2", None)]
    for path, ref in loads:
        page.goto(base + path, wait_until="load", referer=ref) if ref else page.goto(base + path, wait_until="load")
        page.wait_for_timeout(3500)
    doc_cookie = page.evaluate("document.cookie")
    cookies = ctx.cookies()
    views = [s for s in seen if s["url"].endswith("/_vercel/insights/view")]
    payloads = []
    for v in views:
        try:
            payloads.append(json.loads(v["post"] or "{}"))
        except ValueError:
            payloads.append({"unparsed": v["post"]})
    site = base.rstrip("/")
    expected_o = [site + "/about/", site + "/privacy/", site + "/chapters/11-the-living-christ/"]
    c = {
        "script_from_own_origin": any(s["url"] == site + "/_vercel/insights/script.js" for s in seen),
        "page_views_to_own_origin": len(views) == 3 and all(v["url"] == site + "/_vercel/insights/view" for v in views),
        "page_addresses": [p.get("o") for p in payloads],
        "page_addresses_as_expected": [p.get("o") for p in payloads] == expected_o,
        "referrers": [p.get("r") for p in payloads],
        "referrer_cut_to_origin": payloads[0].get("r") == "https://example.com/" if payloads else False,
        "no_query_or_fragment_anywhere": all(not analytics_payload_problems(v["post"]) for v in views),
        "allow_list_verdicts": [classify_page_load(s["url"], site, post_data=s["post"]) for s in seen],
        "other_insights_endpoints": [s["url"] for s in seen if not s["url"].endswith(("/script.js", "/view"))],
        "document_cookie": doc_cookie,
        "browser_cookies": [{"name": k["name"], "domain": k["domain"]} for k in cookies],
        "set_cookie_on_insights_responses": [r for r in responses if r["set_cookie"]],
        "insights_responses": responses,
    }
    c["allow_list_all_ok"] = all(v[0] for v in c["allow_list_verdicts"])
    ok = c["script_from_own_origin"] and c["page_views_to_own_origin"] and c["page_addresses_as_expected"] and \
        c["referrer_cut_to_origin"] and c["no_query_or_fragment_anywhere"] and c["allow_list_all_ok"] and \
        not c["other_insights_endpoints"] and not doc_cookie and not cookies and not c["set_cookie_on_insights_responses"]
    name = write(out, f"analytics_{label}.json", {"checks": c, "requests": seen, "payloads": payloads})
    record(f"analytics-{label}", ok, f"views={len(views)} o={c['page_addresses']} r={c['referrers']} cookies={len(cookies)}", [name])
    ctx.close()
    browser.close()


# ------------------------------------------------------------------ quiet: no request while writing
def check_quiet(pw, base, out, label, insights_script=None):
    browser = pw.chromium.launch()
    rows, ok = [], True
    cases = [
        ("/chapters/11-the-living-christ/", "Discipleship Journal: R·J·W Reflect, Journal and Witness (typing, saving on close)",
         None, lambda p: ja.act_chapter_rjw(p, "pause-closing", "Journal (edited) — CODE-SITE-22")),
        ("/chapters/11-the-living-christ/", "Reflections panel: My questions (typing, Save question)",
         None, lambda p: ja.write_question(p, "A question — “kept” here; Ἰησοῦς")),
        ("/chapters/12-beatitudes/", "Card-chapter reflection and commitment (typing, Save)",
         ja.prep_scroll_to('.card-panel[data-card="1"][data-panel="personalize"] .reflection-area',
                           '.card-tab[data-card="1"][data-tab="personalize"]'),
         lambda p: ja.act_card(p, "Card reflection (edited) — CODE-SITE-22")),
        ("/articles/", "Articles reflection (typing)",
         ja.prep_scroll_to('.rjw-textarea[data-rjw-key="rjw-A01"]'), lambda p: ja.act_articles(p, "Article reflection (edited)")),
    ]
    for path, what, prep, action in cases:
        ctx = browser.new_context(user_agent=REAL_UA)
        ctx.add_init_script(NOT_AUTOMATED)   # analytics live, as for a real reader
        serve_insights(ctx, insights_script)
        reqs, phase = [], {"v": "load"}
        ctx.on("request", lambda r, reqs=reqs, phase=phase: reqs.append({"phase": phase["v"], "url": r.url, "method": r.method}))
        page = ctx.new_page()
        page.goto(base + path, wait_until="load", timeout=90000)
        page.wait_for_timeout(4000)
        if prep:
            prep(page)
        page.wait_for_timeout(1500)
        phase["v"] = "action"
        action(page)
        page.wait_for_timeout(2500)
        phase["v"] = "done"
        during = [r for r in reqs if r["phase"] == "action"]
        load_views = [r["url"] for r in reqs if r["phase"] == "load" and r["url"].endswith("/_vercel/insights/view")]
        stored = page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('wop-reflection') || k.startsWith('wop-rjw')).length")
        verdicts = [classify_action(r["url"], base) for r in during]
        row = {"page": path, "what": what, "requests_during_typing_and_saving": during,
               "analytics_page_view_at_load": load_views, "entries_in_store_after": stored, "allow_list_verdicts": verdicts,
               "pass": len(during) == 0 and stored > 0}
        ok = ok and row["pass"]
        rows.append(row)
        ctx.close()
    browser.close()
    name = write(out, f"quiet_{label}.json", rows)
    record(f"quiet-{label}", ok, f"{sum(r['pass'] for r in rows)}/{len(rows)} writing cases sent no request at all", [name])


# ------------------------------------------------------------------ forms
def check_forms(pw, base, baseline_base, out, label):
    new = ja.run_forms(pw, base, False)
    old = ja.run_forms(pw, baseline_base, False)
    comp, ok = {}, True
    for form in ("contact", "newsletter-connect", "newsletter-footer"):
        a, b = old[form], new[form]
        ra = [r for r in a["requests"] if r["method"] != "OPTIONS"]
        rb = [r for r in b["requests"] if r["method"] != "OPTIONS"]
        c = {"same_endpoint": [(r["method"], r["url"]) for r in ra] == [(r["method"], r["url"]) for r in rb],
             "same_fields": [ja.normalise_body(r["body"]) for r in ra] == [ja.normalise_body(r["body"]) for r in rb],
             "same_content_type": [r["headers"].get("content-type") for r in ra] == [r["headers"].get("content-type") for r in rb],
             "same_confirmation": a.get("confirmation") == b.get("confirmation"),
             "requests_sent_new": len(rb), "endpoint": [r["url"] for r in rb], "content_type": [r["headers"].get("content-type") for r in rb],
             "fields": [sorted((ja.normalise_body(r["body"]) or {}).keys()) for r in rb], "confirmation": b.get("confirmation")}
        c["pass"] = c["same_endpoint"] and c["same_fields"] and c["same_content_type"] and c["same_confirmation"] and len(rb) == 1
        comp[form] = c
        ok = ok and c["pass"]
    name = write(out, f"forms_{label}.json", {"comparisons": comp, "baseline": old, "new": new})
    record(f"forms-{label}", ok, "contact and newsletter (Connect and footer) unchanged against the baseline build; API stubbed", [name])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site")
    ap.add_argument("--prod")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--approved", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--insights-script")
    ap.add_argument("--checks", default="wording,banner,behaviour,analytics,quiet,forms")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    checks = set(a.checks.split(","))
    srv_b, baseline_base = ja.serve(a.baseline)
    if a.prod:
        base, site_dir, label, insights = a.prod.rstrip("/"), None, "prod", None
    else:
        srv, base = ja.serve(a.site)
        site_dir, label, insights = a.site, "local", a.insights_script
    if "wording" in checks:
        check_wording(base, site_dir, a.baseline, a.approved, a.out)
    with sync_playwright() as pw:
        if "banner" in checks:
            check_banner(pw, base, baseline_base, a.out, label)
        if "behaviour" in checks:
            check_banner_behaviour(pw, base, baseline_base, a.out, label, insights)
        if "analytics" in checks:
            check_analytics(pw, base, a.out, label, insights)
        if "quiet" in checks:
            check_quiet(pw, base, a.out, label, insights)
        if "forms" in checks:
            check_forms(pw, base, baseline_base, a.out, label)
    write(a.out, f"summary_{label}.json", RESULTS)
    print("ALL PASS" if all(r["pass"] for r in RESULTS.values()) else "SOME FAILED")


if __name__ == "__main__":
    main()
