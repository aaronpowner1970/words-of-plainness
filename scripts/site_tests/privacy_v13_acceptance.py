"""Acceptance checks for Privacy Policy v1.3 and the contact form's retirement for email
(CODE-SITE-28 and CODE-SITE-29, SITE step 61, ruling SITE-CONTACT-NO-EMAIL option 1; G1-G3 are the
additions approved after the CODE-SITE-28 review).

Checks, each runnable against a locally served build or production:
  wording    every sentence quoted in sections 1-8 of the approved file sits word for word on the
             page the section names (Connect, Privacy, Under the Hood, Community Guidelines,
             Disclaimer), with typeset apostrophes and quotation marks; the Privacy footer and the
             "What changed" heading read v1.3 with the ship date; the section 9a newsletter line
             is on no page; and the six G2 passages (P-a, P-b, P-c on Privacy; U-a, U-b, U-c on
             Under the Hood), each on its page.
  passages   the words "contact form" no longer appear in the eight changed passages, apart from
             the approved sentence that announces the retirement ("The contact form is retired.");
             and on the whole text of each of the five pages they appear only in that sentence and
             the G1 notice sentence (any other "contact form" or "contact and newsletter forms"
             fails).
  box        G3: the "What changed" box reads, in order, the v1.3 heading, the one item "The
             contact form is retired.", the italic lead-in "Earlier, on 18 November 2026
             (version 1.2):" word for word, then the three v1.2 items identical to the baseline's.
  banner-wording  G1: the site-wide notice reads the approved v1.3 sentence word for word (ship
             date in place of {{ privacyPolicy.date }}) on the five pages, its link is
             /privacy/#what-changed, and the v1.2 sentence is gone (CODE-SITE-29).
  noform     no built page contains the contact form, loads /js/contact-form.js or calls the
             contact route (/api/v1/contact/ through submitContact), and the build has no
             js/contact-form.js. With the Second Edition switch ON, the AoID corrections page
             (/aoid/corrections/) is the one allowed caller and is listed as such.
  mailto     the Connect page's email link reads
             mailto:host@brotheraaron.org?subject=Message%20for%20Brother%20Aaron, Privacy's
             Contact link reads mailto:host@brotheraaron.org?subject=Privacy, /connect/ keeps
             id="contact" and every link to /connect/#contact lands on it.
  connect-live  in a browser: /connect/ has only the two newsletter forms, no ContactForm script,
             and loading it sends no request to the contact route or for contact-form.js.
  banner, behaviour, forms  privacy_v12_acceptance.py's checks with the v1.3 dismissal key and
             date window (shows from the ship date for 30 days).

Usage:
  python scripts/site_tests/privacy_v13_acceptance.py --site <build dir> | --prod https://www.wordsofplainness.org
      --baseline <baseline build dir> --approved <WoP_SITE_ContactEmail_ApprovedWording_*.md> --out <evidence dir>
      [--ship-date 2026-11-21] [--switch-on] [--checks wording,passages,box,banner-wording,noform,mailto,connect-live,banner,behaviour,forms]
"""
import argparse
import html as htmlmod
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import journal_acceptance as ja  # noqa: E402
import privacy_v12_acceptance as pa  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

PAGES = {"connect": "/connect/", "privacy": "/privacy/", "uth": "/about/under-the-hood/",
         "cg": "/community-guidelines/", "disclaimer": "/disclaimer/"}
SECTION_PAGE = {1: "connect", 2: "privacy", 3: "privacy", 4: "privacy", 5: "privacy", 6: "uth", 7: "cg", 8: "disclaimer"}
CONNECT_MAILTO = "mailto:host@brotheraaron.org?subject=Message%20for%20Brother%20Aaron"
PRIVACY_MAILTO = "mailto:host@brotheraaron.org?subject=Privacy"
RETIREMENT_SENTENCE = "The contact form is retired."
G2_LABELS = ("P-a", "P-b", "P-c", "U-a", "U-b", "U-c")   # order of the G2 quotes in the approved file
G2_PAGE = {"P": "privacy", "U": "uth"}
CORRECTIONS_PAGE = "aoid/corrections/index.html"
RESULTS = pa.RESULTS


def record(name, ok, summary, evidence):
    pa.record(name, ok, summary, evidence)


def typeset(t):
    """Approved-file rule: apostrophes U+2019, quotation marks U+201C / U+201D."""
    t = re.sub(r'"([^"]*)"', "“\\1”", t)
    return t.replace("'", "’")


def approved_sections(md):
    """{section number: [expected sentence or paragraph, ...]} from the '>' quotes of sections 1-8."""
    out = {}
    parts = re.split(r"(?m)^## (\d+)\. ", md)
    for i in range(1, len(parts) - 1, 2):
        n = int(parts[i])
        if n not in SECTION_PAGE:
            continue
        body = parts[i + 1]
        quotes = []
        for line in body.splitlines():
            m = re.match(r"^\s*>\s?(.*)$", line)
            if m and m.group(1).strip():
                quotes.append(typeset(m.group(1).strip().replace("**", "")))
        out[n] = quotes
    return out


def newsletter_line(md):
    i = md.index("### 9a.")
    for line in md[i:].splitlines():
        m = re.match(r"^\s*>\s?(.*)$", line)
        if m and m.group(1).strip():
            return typeset(m.group(1).strip().replace("**", ""))
    raise ValueError("9a")


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def blocks(page_src):
    """Text of every <p>, <li>, <td> and the #contact section inside <main>."""
    m = re.search(r"(?s)<main\b[^>]*>(.*)</main>", page_src)
    main = m.group(1) if m else page_src
    out = [pa.text_of(b) for b in re.findall(r"(?is)<(?:p|li|td)\b[^>]*>.*?</(?:p|li|td)>", main)]
    sec = re.search(r'(?is)<section[^>]*id="contact"[^>]*>(.*?)</section>', main)
    return out, (pa.text_of(sec.group(1)) if sec else None)


# ------------------------------------------------------------------ wording
def check_wording(base, site_dir, approved_md, ship_iso, out):
    md = Path(approved_md).read_text(encoding="utf-8")
    secs = approved_sections(md)
    src = {k: pa.page_html(base, p, site_dir) for k, p in PAGES.items()}
    txt = {k: pa.main_text(v) for k, v in src.items()}
    rows, ok = [], True
    for n in sorted(secs):
        for q in secs[n]:
            hit = q in txt[SECTION_PAGE[n]]
            rows.append({"section": n, "page": PAGES[SECTION_PAGE[n]], "expected": q, "pass": hit})
            ok = ok and hit
    # G2 (CODE-SITE-29): the six passages, each on its page. A leading or trailing "…" in the approved
    # file marks the unchanged rest of the paragraph; "A | B" is a table row (row header | cell).
    for label, q in zip(G2_LABELS, addition_quotes(md, "G2")):
        key = G2_PAGE[label[0]]
        if " | " in q:
            th, td = q.split(" | ")
            row_rx = rf'(?is)<tr>\s*<th scope="row">{re.escape(th)}</th>\s*<td>{re.escape(td)}</td>\s*</tr>'
            hit = bool(re.search(row_rx, src[key]))
        else:
            hit = q.strip("…") in txt[key]
        rows.append({"section": f"G2 {label}", "page": PAGES[key], "expected": q, "pass": hit})
        ok = ok and hit
    when = long_date(ship_iso)
    extra = {
        "sections_with_quotes": {n: len(q) for n, q in secs.items()},
        "footer_v1_3": f"Words of Plainness Privacy Policy v1.3 — Aaron Powner Publishing — {when}." in txt["privacy"],
        "what_changed_heading_v1_3": f"What changed on {when} (version 1.3)" in txt["privacy"],
        "v1_2_contact_item_gone": "Contact form messages." not in txt["privacy"],
        "two_forms_line_gone": "Two forms on this site accept information:" not in txt["privacy"],
    }
    nl = newsletter_line(md)
    extra["newsletter_9a_on_no_checked_page"] = all(nl not in t and "A small privacy change." not in t for t in txt.values())
    if site_dir:
        hits = [str(p.relative_to(site_dir)) for p in Path(site_dir).rglob("*.html")
                if "A small privacy change." in p.read_text(encoding="utf-8", errors="replace")]
        extra["newsletter_9a_pages_in_build"] = hits
        extra["newsletter_9a_on_no_checked_page"] = extra["newsletter_9a_on_no_checked_page"] and not hits
    ok = ok and all(v for k, v in extra.items() if isinstance(v, bool))
    name = pa.write(out, "v13_wording.json", {"items": rows, "checks": extra})
    record("wording", ok, f"{sum(r['pass'] for r in rows)}/{len(rows)} approved sentences in place; {extra}", [name])


# ------------------------------------------------------------------ "contact form" gone from the eight passages
def check_passages(base, site_dir, approved_md, ship_iso, out):
    md = Path(approved_md).read_text(encoding="utf-8")
    secs = approved_sections(md)
    src = {k: pa.page_html(base, p, site_dir) for k, p in PAGES.items()}
    rows, ok = [], True
    for n in sorted(secs):
        key = SECTION_PAGE[n]
        bl, contact_sec = blocks(src[key])
        if n == 1:
            containers = [contact_sec] if contact_sec else []
        else:
            containers = [b for b in bl if any(q in b for q in secs[n])]
            # the shortest block holding each sentence (a <p> inside an <li> is counted once)
            containers = sorted(set(containers), key=len)
            keep = []
            for c in containers:
                if not any(k in c for k in keep):
                    keep.append(c)
            containers = keep
        remainder = []
        for c in containers:
            r = c
            for q in secs[n]:
                r = r.replace(q, " ")
            remainder.append(r)
        found = [m for r in remainder for m in re.findall(r"contact form", r, re.I)]
        in_approved = [q for q in secs[n] if re.search(r"contact form", q, re.I)]
        row = {"section": n, "page": PAGES[key], "passages": containers, "contact_form_outside_approved_text": found,
               "approved_sentences_that_say_contact_form": in_approved, "pass": bool(containers) and not found}
        rows.append(row)
        ok = ok and row["pass"]
    # Listed: other mentions of the form in the <p>/<li>/<td> blocks of the five pages.
    others = {}
    for key, s in src.items():
        bl, _ = blocks(s)
        hits = [b for b in bl if re.search(r"contact form|contact and newsletter forms|contact messages", b, re.I)
                and RETIREMENT_SENTENCE not in b]
        if hits:
            others[PAGES[key]] = hits
    # G2 (CODE-SITE-29): on the whole text of each of the five pages (notice, header, main, footer), the
    # words "contact form" (and "contact and newsletter forms") appear only in "The contact form is
    # retired." and the G1 notice sentence. Fails on any other occurrence.
    g1 = addition_quotes(md, "G1")[0].replace("{{ privacyPolicy.date }}", long_date(ship_iso))
    sweep = {}
    for key, s in src.items():
        t = pa.text_of(s)
        allowed = {"retirement sentence": t.count(RETIREMENT_SENTENCE), "G1 notice sentence": t.count(g1)}
        r = t.replace(g1, " ").replace(RETIREMENT_SENTENCE, " ")
        stray = [r[max(0, m.start() - 80):m.end() + 80]
                 for m in re.finditer(r"contact form|contact and newsletter forms", r, re.I)]
        sweep[PAGES[key]] = {"allowed_occurrences": allowed, "stray": stray, "pass": not stray}
        ok = ok and not stray
    ok = ok and not others
    name = pa.write(out, "v13_passages.json", {"passages": rows, "other_mentions": others, "whole_page_sweep": sweep})
    record("passages", ok, f"{sum(r['pass'] for r in rows)}/{len(rows)} changed passages free of \"contact form\" outside "
           f"the approved text; other mentions: {sum(len(v) for v in others.values())}; whole-page sweep: "
           f"{sum(v['pass'] for v in sweep.values())}/{len(sweep)} pages say \"contact form\" only in the retirement "
           f"sentence and the G1 notice", [name])


# ------------------------------------------------------------------ G3: the "What changed" box
def check_box(base, site_dir, baseline_base, approved_md, ship_iso, out):
    """The box carries, in order: the data-driven v1.3 heading; one item, "The contact form is retired.";
    the italic lead-in (G3) word for word; then the three v1.2 items, each identical to the baseline
    build's (journal, page-view counts, Cloudflare's role)."""
    md = Path(approved_md).read_text(encoding="utf-8")
    (lead,) = addition_quotes(md, "G3")

    def box(s):
        m = re.search(r'(?is)<div class="wop-what-changed" id="what-changed">(.*?)</div>', s)
        return m.group(1) if m else ""

    new = box(pa.page_html(base, "/privacy/", site_dir))
    old = box(pa.page_html(baseline_base, "/privacy/", None))
    seq = [(tag.lower(), attrs, pa.text_of(body))
           for tag, attrs, body in re.findall(r"(?is)<(h2|li|p)\b([^>]*)>(.*?)</\1>", new)]
    old_items = [pa.text_of(b) for b in re.findall(r"(?is)<li\b[^>]*>(.*?)</li>", old)]
    v12_starts = ("Your journal stays with you.", "Page-view counts.", "Cloudflare’s role")
    old_v12 = [next((i for i in old_items if i.startswith(st)), None) for st in v12_starts]
    when = long_date(ship_iso)
    expected = ([("h2", f"What changed on {when} (version 1.3)")] +
                [("li", None)] + [("p", lead)] + [("li", t) for t in old_v12])
    got = [(t, x) for t, _, x in seq]
    lead_attrs = next((a for t, a, x in seq if t == "p" and x == lead), "")
    lead_italic = bool(re.search(r"font-style:\s*italic", lead_attrs)) or bool(
        re.search(rf"(?is)<p\b[^>]*>\s*<(em|i)>\s*{re.escape(lead)}\s*</\1>\s*</p>", new))
    checks = {
        "order_and_text": len(got) == len(expected) and all(
            g[0] == e[0] and (e[1] is None or g[1] == e[1]) for g, e in zip(got, expected)),
        "v1_3_item_is_retirement_only": len(got) > 1 and got[1][0] == "li" and got[1][1].startswith(RETIREMENT_SENTENCE),
        "lead_in_word_for_word": lead in [x for t, x in got if t == "p"],
        "lead_in_italic": lead_italic,
        "v1_2_items_found_in_baseline": all(old_v12),
        "v1_2_items_unchanged": [x for t, x in got[3:]] == old_v12,
    }
    ok = all(checks.values())
    name = pa.write(out, "v13_box.json", {"lead_in": lead, "sequence": got, "expected": expected, "checks": checks})
    record("box", ok, f"{checks}", [name])


# ------------------------------------------------------------------ notice wording (G1)
def addition_quotes(md, tag):
    """The '>' quotes under '### <tag>.' in the approved file's additions (G1, G2, G3), in order."""
    m = re.search(rf"(?ms)^### {tag}\.(.*?)(?=^### |\Z)", md)
    if not m:
        raise ValueError(tag)
    out = []
    for line in m.group(1).splitlines():
        q = re.match(r"^\s*>\s?(.*)$", line)
        if q and q.group(1).strip():
            out.append(typeset(q.group(1).strip().replace("**", "")))
    return out


def check_banner_wording(base, site_dir, approved_md, ship_iso, out):
    """G1: the notice reads the approved v1.3 sentence word for word, with the ship date in place of
    {{ privacyPolicy.date }}, on every checked page; the v1.2 sentence is gone."""
    md = Path(approved_md).read_text(encoding="utf-8")
    (g1,) = addition_quotes(md, "G1")
    expected = g1.replace("{{ privacyPolicy.date }}", long_date(ship_iso))
    v12 = "your journal stays on your device, and we now count page views without cookies"
    rows, ok = [], True
    for key, path in PAGES.items():
        s = pa.page_html(base, path, site_dir)
        found = pa.banner_text(s)
        link = re.search(r'(?s)<p class="wop-privacy-notice-text"[^>]*>.*?<a\b[^>]*href="([^"]*)"', s)
        row = {"page": path, "notice_text": found, "pass": found == expected and v12 not in s,
               "link": link.group(1) if link else None}
        row["pass"] = row["pass"] and row["link"] == "/privacy/#what-changed"
        rows.append(row)
        ok = ok and row["pass"]
    name = pa.write(out, "v13_banner_wording.json", {"approved_g1": g1, "expected": expected, "pages": rows})
    record("banner-wording", ok, f"{sum(r['pass'] for r in rows)}/{len(rows)} pages show the approved G1 notice "
           f"sentence {expected!r} linking to /privacy/#what-changed", [name])


# ------------------------------------------------------------------ the form is gone
def check_noform(base, site_dir, switch_on, out):
    pat = {
        "contact-form.js": re.compile(r"contact-form\.js"),
        "contactForm id": re.compile(r'id="contactForm'),
        "contact-form class": re.compile(r'class="[^"]*\bcontact-form\b'),
        "form posting to contact": re.compile(r"(?is)<form\b[^>]*action=\"[^\"]*contact"),
        "submitContact": re.compile(r"submitContact"),
        "/api/v1/contact/": re.compile(r"/api/v1/contact/"),
    }
    hits, n_pages = {}, 0
    if site_dir:
        files = sorted(Path(site_dir).rglob("*.html"))
        srcs = ((str(f.relative_to(site_dir)).replace("\\", "/"), f.read_text(encoding="utf-8", errors="replace")) for f in files)
    else:
        srcs = ((p, pa.page_html(base, p, None)) for p in list(PAGES.values()) + ["/", "/articles/"])
    for rel, s in srcs:
        n_pages += 1
        for label, rx in pat.items():
            if rx.search(s):
                hits.setdefault(rel, []).append(label)
    allowed = {k: v for k, v in hits.items() if switch_on and k == CORRECTIONS_PAGE and set(v) <= {"submitContact"}}
    bad = {k: v for k, v in hits.items() if k not in allowed}
    script_file = (Path(site_dir) / "js" / "contact-form.js").exists() if site_dir else None
    ok = not bad and not script_file and (not switch_on or CORRECTIONS_PAGE in allowed)
    ev = {"pages_scanned": n_pages, "violations": bad, "allowed": allowed, "js_contact_form_js_in_build": script_file,
          "switch_on": switch_on}
    name = pa.write(out, f"v13_noform_{'on' if switch_on else 'off'}.json", ev)
    record(f"noform{'-on' if switch_on else ''}", ok, f"{n_pages} pages scanned; violations {bad}; allowed {list(allowed)}; "
           f"contact-form.js in build: {script_file}", [name])


# ------------------------------------------------------------------ mailto and the #contact anchor
def check_mailto(base, site_dir, out):
    con = pa.page_html(base, "/connect/", site_dir)
    priv = pa.page_html(base, "/privacy/", site_dir)
    sec = re.search(r'(?is)<section[^>]*id="contact"[^>]*>(.*?)</section>', con)
    links = re.findall(r'(?is)<a\b[^>]*href="(mailto:[^"]*)"[^>]*>(.*?)</a>', sec.group(1)) if sec else []
    pc = re.search(r'(?is)<section[^>]*id="privacy-contact"[^>]*>(.*?)</section>', priv)
    plinks = re.findall(r'(?is)<a\b[^>]*href="(mailto:[^"]*)"[^>]*>(.*?)</a>', pc.group(1)) if pc else []
    ev = {"connect_contact_mailto_links": [(h, pa.text_of(t)) for h, t in links],
          "privacy_contact_mailto_links": [(h, pa.text_of(t)) for h, t in plinks],
          "connect_has_id_contact": bool(sec)}
    ok = ev["connect_has_id_contact"] and [h for h, _ in links] == [CONNECT_MAILTO] and \
        pa.text_of(links[0][1]) == "host@brotheraaron.org" and [h for h, _ in plinks] == [PRIVACY_MAILTO]
    if site_dir:
        linking = sorted(str(p.relative_to(site_dir)).replace("\\", "/") for p in Path(site_dir).rglob("*.html")
                         if "/connect/#contact" in p.read_text(encoding="utf-8", errors="replace"))
        ev["pages_linking_to_connect_contact"] = linking
        ok = ok and len(linking) > 0
    name = pa.write(out, "v13_mailto.json", ev)
    record("mailto", ok, f"Connect {ev['connect_contact_mailto_links']}; Privacy {ev['privacy_contact_mailto_links']}; "
           f"#contact kept: {ev['connect_has_id_contact']}; pages linking to it: {len(ev.get('pages_linking_to_connect_contact', []))}", [name])


def check_connect_live(pw, base, out, label):
    browser = pw.chromium.launch()
    ctx = browser.new_context()
    reqs = []
    ctx.on("request", lambda r: reqs.append(r.url))
    ctx.route(ja.API_PATTERN, lambda r: r.fulfill(status=200, body="{}", content_type="application/json"))
    page = ctx.new_page()
    page.goto(base + "/connect/#contact", wait_until="load", timeout=90000)
    page.wait_for_timeout(1500)
    ev = page.evaluate("""() => ({
        forms: [...document.querySelectorAll('form')].map(f => f.id),
        contactFormDefined: typeof window.ContactForm !== 'undefined',
        contactAnchor: !!document.getElementById('contact'),
        mailto: [...document.querySelectorAll('#contact a[href^="mailto:"]')].map(a => [a.getAttribute('href'), a.textContent.trim()]),
        contactInView: (() => { const b = document.getElementById('contact').getBoundingClientRect(); return b.top < innerHeight && b.bottom > 0; })()
    })""")
    ev["requests_to_contact_route_or_script"] = [u for u in reqs if "/contact/" in u or "contact-form.js" in u]
    ctx.close()
    browser.close()
    ok = sorted(ev["forms"]) == ["connectNewsletterForm", "footerNewsletterForm"] and not ev["contactFormDefined"] and \
        ev["contactAnchor"] and ev["mailto"] == [[CONNECT_MAILTO, "host@brotheraaron.org"]] and ev["contactInView"] and \
        not ev["requests_to_contact_route_or_script"]
    name = pa.write(out, f"v13_connect_live_{label}.json", ev)
    record(f"connect-live-{label}", ok, f"forms {ev['forms']}; ContactForm defined {ev['contactFormDefined']}; mailto {ev['mailto']}; "
           f"contact requests {ev['requests_to_contact_route_or_script']}", [name])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site")
    ap.add_argument("--prod")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--approved", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ship-date", default=date.today().isoformat())
    ap.add_argument("--switch-on", action="store_true")
    ap.add_argument("--insights-script")
    ap.add_argument("--checks", default="wording,passages,box,banner-wording,noform,mailto,connect-live,banner,behaviour,forms")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    checks = set(a.checks.split(","))
    ship = date.fromisoformat(a.ship_date)
    until = ship + timedelta(days=30)
    pa.NOTICE_KEY = "wop-privacy-notice-v1.3-dismissed"
    dt = lambda d, t: datetime.fromisoformat(f"{d.isoformat()}T{t}").isoformat()
    pa.DATE_WINDOW = ((dt(ship - timedelta(days=1), "23:59:00"), False), (dt(ship, "00:00:30"), True),
                      (dt(ship + timedelta(days=10), "12:00:00"), True), (dt(until - timedelta(days=1), "23:59:00"), True),
                      (dt(until, "00:00:30"), False), (dt(until + timedelta(days=70), "12:00:00"), False))
    srv_b, baseline_base = ja.serve(a.baseline)
    if a.prod:
        base, site_dir, label = a.prod.rstrip("/"), None, "prod"
    else:
        srv, base = ja.serve(a.site)
        site_dir, label = a.site, "local"
    if "wording" in checks:
        check_wording(base, site_dir, a.approved, a.ship_date, a.out)
    if "passages" in checks:
        check_passages(base, site_dir, a.approved, a.ship_date, a.out)
    if "box" in checks:
        check_box(base, site_dir, baseline_base, a.approved, a.ship_date, a.out)
    if "banner-wording" in checks:
        check_banner_wording(base, site_dir, a.approved, a.ship_date, a.out)
    if "noform" in checks:
        check_noform(base, site_dir, a.switch_on, a.out)
    if "mailto" in checks:
        check_mailto(base, site_dir, a.out)
    with sync_playwright() as pw:
        if "connect-live" in checks:
            check_connect_live(pw, base, a.out, label)
        if "banner" in checks:
            pa.check_banner(pw, base, baseline_base, a.out, label)
        if "behaviour" in checks:
            pa.check_banner_behaviour(pw, base, baseline_base, a.out, label, a.insights_script)
        if "forms" in checks:
            pa.check_forms(pw, base, baseline_base, a.out, label)
    pa.write(a.out, f"v13_summary_{label}.json", RESULTS)
    print("ALL PASS" if all(r["pass"] for r in RESULTS.values()) else "SOME FAILED")


if __name__ == "__main__":
    main()
