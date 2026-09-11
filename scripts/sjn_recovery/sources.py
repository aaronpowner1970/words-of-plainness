"""Deterministic per-standard fetch + split adapters.

Every adapter splits by the document's OWN divisions (article, question, paragraph number, canon,
decree, chapter.paragraph) — never by character count. The locator a learner eventually sees is that
division. Where a division is long (Book of Concord articles), consecutive numbered paragraphs are
grouped and the locator names the real paragraph range.

Adapters return (chunks, notes). Chunk fields: registry_id, branch, standard_title, authority_tier,
scope_caveat, locator, division, text, text_hash, source_url (internal: never passed to an agent),
language. Fetch modes follow the registry (AC-08): RENDERED hosts use Playwright; files.lcms.org is
registered as an authority URL only and nothing is chunked."""
import os
import re
import sys
import time
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sjn_pipeline.fetch import pdf_text  # noqa: E402

from .textutil import segments, join, clean, strip_footnote_digits, sha, pdf_repair, fix_mojibake  # noqa: E402

ROMAN = r"(?:[IVXLC]+)"
ROMAN_MAP = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11,
             "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
             "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25, "XXVI": 26, "XXVII": 27, "XXVIII": 28,
             "XXIX": 29, "XXX": 30, "XXXI": 31, "XXXII": 32, "XXXIII": 33, "XXXIV": 34, "XXXV": 35, "XXXVI": 36,
             "XXXVII": 37, "XXXVIII": 38, "XXXIX": 39}


class Ctx:
    def __init__(self, row, fetcher, log=print):
        self.row = row
        self.rid = row["registry_id"]
        self.fetcher = fetcher
        self.log = log
        self.urls = []

    def html(self, url):
        fr = self.fetcher.get(url)
        self.urls.append({"url": url, "mode": "http", "status": fr.status, "ok": fr.ok, "error": fr.error})
        if not fr.ok or not fr.html:
            raise FetchError(f"{url}: {fr.error or 'empty body'}")
        return fr.html

    def pdf(self, url):
        fr = self.fetcher.get(url)
        self.urls.append({"url": url, "mode": "pdf", "status": fr.status, "ok": fr.ok, "error": fr.error})
        if not fr.ok or not fr.pdf_bytes:
            raise FetchError(f"{url}: {fr.error or 'no PDF bytes'}")
        return pdf_text(fr.pdf_bytes)

    def rendered(self, url):
        fr = self.fetcher.rendered(url)
        self.urls.append({"url": url, "mode": "rendered", "status": fr.status, "ok": fr.ok, "error": fr.error})
        if not fr.ok:
            raise FetchError(f"{url}: {fr.error}")
        return fr.rendered

    def chunk(self, locator, text, division, url, language="en"):
        text = clean(text)
        if not text:
            return None
        r = self.row
        return {"registry_id": self.rid, "branch": r["branch"], "standard_title": r["standard_title"],
                "authority_tier": r["authority_tier"], "scope_caveat": r["scope_caveat"],
                "locator": locator, "division": division, "text": text, "text_hash": sha(text),
                "source_url": url, "language": language}


class FetchError(Exception):
    pass


class BlockedError(FetchError):
    pass


def _emit(ctx, out, locator, parts, division, url, language="en"):
    c = ctx.chunk(locator, join(parts), division, url, language)
    if c:
        out.append(c)


# =============================================================== Roman Catholic
CCC_BASE = "https://www.vatican.va"


def ccc_section_two(ctx):
    """BSR-RC-01 — CCC Part One, Section Two: crawl the section index, split every page by paragraph number."""
    index_url = "https://www.vatican.va/content/catechism/en/part_one/section_two.html"
    html = ctx.html(index_url)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "/part_one/section_two/" in h and h not in links:
            links.append(h)
    from urllib.parse import quote
    pages = [index_url] + [urljoin(CCC_BASE, quote(h, safe="/%")) for h in links]
    out, seen = [], set()
    for url in pages:
        try:
            page = ctx.html(url)
        except FetchError as e:
            ctx.log(f"   ! {e}")
            continue
        cur, buf = None, []
        for tag, text in segments(page):
            if tag == "p":
                m = re.match(r"^(\d{1,4})\s+(\S.*)$", text, re.S)
                if m and int(m.group(1)) <= 2865 and (cur is None or int(m.group(1)) > cur):
                    if cur is not None and cur not in seen:
                        _emit(ctx, out, f"CCC {cur}", buf, "paragraph", url); seen.add(cur)
                    cur, buf = int(m.group(1)), [m.group(2)]
                elif cur is not None and not re.match(r"^\d+$", text):
                    buf.append(text)
        if cur is not None and cur not in seen:
            _emit(ctx, out, f"CCC {cur}", buf, "paragraph", url); seen.add(cur)
    return out, [f"{len(pages)} pages under Part One, Section Two; {len(out)} numbered paragraphs"]


def dei_filius_latin(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out = []
    i = 0
    chapter = None; title = ""; buf = []
    in_canons = False; canon_ch = None
    for tag, text in segs:
        t = text.strip()
        if tag == "p" and re.match(r"^CAPUT\s+" + ROMAN + r"$", t):
            if chapter and buf:
                _emit(ctx, out, f"Caput {chapter} — {title}", buf, "chapter", url, "la")
            chapter, buf, title = t.split()[1], [], ""
            continue
        if tag == "b" and t == "CANONES":
            if chapter and buf:
                _emit(ctx, out, f"Caput {chapter} — {title}", buf, "chapter", url, "la")
            chapter, buf = None, []
            in_canons = True
            continue
        if in_canons:
            m = re.match(r"^(" + ROMAN + r")\.\s+(.+)$", t)
            if tag == "b" and m:
                canon_ch, title = m.group(1), m.group(2).title()
                continue
            m = re.match(r"^(\d{1,2})\.\s+(Si quis.+)$", t, re.S)
            if tag == "p" and m and canon_ch:
                _emit(ctx, out, f"Canon {canon_ch}.{m.group(1)} — {title}", [m.group(2)], "canon", url, "la")
            continue
        if chapter:
            if tag == "b" and not title:
                title = t.title()
            elif tag == "p":
                buf.append(t)
    return out, ["Latin official text; chapters (Caput I–IV) and canons"]


def dei_filius_ewtn(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    start = next((i for i, (t, x) in enumerate(segs) if t == "strong" and x.startswith("First Vatican Council")), -1)
    if start < 0:
        raise FetchError("EWTN Dei Filius title block not found")
    out, n = [], 0
    for tag, text in segs[start + 1:]:
        if tag != "p":
            if tag in ("h2", "h3", "h4"):
                break
            continue
        if text.startswith("The same Holy Mother Church") or text.startswith("The same holy mother"):
            break
        n += 1
        _emit(ctx, out, f"Chapter I (English witness), paragraph {n}", [text], "paragraph", url)
    return out, [f"EWTN excerpt page carries Chapter I only ({n} paragraphs); Latin controls (BSR-RC-02)"]


def lateran_canon1(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    idx = [i for i, (t, x) in enumerate(segs) if t == "strong" and x.strip() == "Confession of Faith"]
    if not idx:
        raise FetchError("Lateran IV 'Confession of Faith' heading not found")
    out, n = [], 0
    for tag, text in segs[idx[-1] + 1:]:
        if tag == "strong" or (tag == "a" and text.strip().upper() == "TOP"):
            break
        if tag == "p":
            n += 1
            _emit(ctx, out, f"Canon 1 (Confession of Faith), paragraph {n}", [text], "paragraph", url)
    return out, ["Canon 1 only, as ratified (Tanner translation, unattributed on page)"]


def vatican_creeds(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    start = next((i for i, (t, x) in enumerate(segs) if t == "b" and x.strip() == "The Credo"), -1)
    if start < 0:
        raise FetchError("'The Credo' heading not found")
    out, cur, buf = [], None, []
    for tag, text in segs[start + 1:]:
        t = clean(text)
        if tag == "a" and t in ("Previous", "Next"):
            continue
        if re.match(r"^The Apostles'? Creed$", t, re.I):
            cur, buf = "Apostles' Creed", []; continue
        if re.match(r"^The Nicene Creed$", t, re.I):
            if cur and buf:
                _emit(ctx, out, cur, buf, "creed", url)
            cur, buf = "Nicene Creed", []; continue
        if cur and tag == "p":
            buf.append(t)
    if cur and buf:
        _emit(ctx, out, cur, buf, "creed", url)
    return out, ["Creeds as received (CCC Credo page): Apostles' and Nicene"]


def compendium(ctx):
    url = "https://www.vatican.va/archive/compendium_ccc/documents/archive_2005_compendium-ccc_en.html"
    segs = segments(ctx.html(url))
    out, cur, buf, expect = [], None, [], 1
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^(\d{1,3})\.\s+(.+)$", t)
        if tag == "b" and m and int(m.group(1)) == expect:
            if cur:
                _emit(ctx, out, f"Compendium Q.{cur}", buf, "question", url)
            cur, buf, expect = int(m.group(1)), [t], expect + 1
            continue
        if cur and tag in ("p", "i", "em"):
            if re.fullmatch(r"[\d\-–, ]+", t):
                continue
            buf.append(t)
        if cur and tag == "b" and re.match(r"^(APPENDIX|A\. Common Prayers)", t):
            break
    if cur:
        _emit(ctx, out, f"Compendium Q.{cur}", buf, "question", url)
    return out, [f"registry canonical_url is a host note; text fetched from the cited compendium page; {len(out)} questions"]


# =============================================================== Eastern Orthodox
OCA = "https://www.oca.org"


def _oca_page(ctx, url, section):
    segs = segments(ctx.html(url))
    h1 = next((i for i, (t, x) in enumerate(segs) if t == "h1"), -1)
    if h1 < 0:
        raise FetchError(f"{url}: h1 not found")
    title = clean(segs[h1][1])
    buf = []
    for tag, text in segs[h1 + 1:]:
        if tag in ("h2", "h3") and clean(text) in ("Previous", "Next", "The Orthodox Faith", "The Orthodox Church in America"):
            break
        if tag in ("h1",):
            break
        if tag in ("p", "em", "strong", "blockquote", "li", "i", "b", "h2", "h3", "h4"):
            buf.append(clean(text))
    return title, buf


def _oca_section(ctx, index_url, section_label, prefix):
    from bs4 import BeautifulSoup
    html = ctx.html(index_url)
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.startswith(prefix) and h != prefix and h not in links:
            links.append(h)
    out = []
    for h in links:
        url = urljoin(OCA, h)
        try:
            title, buf = _oca_page(ctx, url, section_label)
        except FetchError as e:
            ctx.log(f"   ! {e}"); continue
        _emit(ctx, out, f'{section_label} — "{title}"', buf, "article", url)
    return out, [f"{len(links)} pages in section '{section_label}' (each page is one division)"]


def oca_symbol_of_faith(ctx):
    return _oca_section(ctx, f"{OCA}/orthodoxy/the-orthodox-faith/doctrine-scripture/the-symbol-of-faith",
                        "The Symbol of Faith", "/orthodoxy/the-orthodox-faith/doctrine-scripture/the-symbol-of-faith/")


def oca_holy_trinity(ctx):
    return _oca_section(ctx, f"{OCA}/orthodoxy/the-orthodox-faith/doctrine-scripture/the-holy-trinity",
                        "The Holy Trinity", "/orthodoxy/the-orthodox-faith/doctrine-scripture/the-holy-trinity/")


def oca_councils(ctx):
    pages = [(f"{OCA}/orthodoxy/the-orthodox-faith/church-history/fifth-century/the-fourth-ecumenical-council", "Church History — Fifth Century"),
             (f"{OCA}/orthodoxy/the-orthodox-faith/church-history/seventh-century/the-sixth-ecumenical-council", "Church History — Seventh Century")]
    out = []
    for url, sec in pages:
        title, buf = _oca_page(ctx, url, sec)
        _emit(ctx, out, f'{sec} — "{title}"', buf, "article", url)
    return out, ["OCA history pages for Chalcedon and Constantinople III as cited by released cells; newadvent.org is lineage only"]


def goarch(ctx):
    """RENDERED, 403-prone (Cloudflare bot check). Playwright with backoff; headed browser as last resort."""
    url = ctx.row["canonical_url"]
    from playwright.sync_api import sync_playwright
    last = ""
    with sync_playwright() as p:
        for attempt, (headless, wait) in enumerate([(True, 8000), (True, 20000), (False, 30000)], 1):
            try:
                b = p.chromium.launch(headless=headless)
                pg = b.new_page()
                resp = pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(wait)
                body = pg.evaluate("() => document.body.innerText")
                status = resp.status if resp else 0
                last = f"attempt {attempt} headless={headless}: HTTP {status}, body {len(body)} chars"
                ctx.log("   " + last)
                if status == 200 and len(body) > 2000 and "security verification" not in body.casefold():
                    blocks = pg.evaluate("""() => { const out=[]; const pick=document.querySelector('article')||document.querySelector('main')||document.body;
                        pick.querySelectorAll('h1,h2,h3,h4,p,li,blockquote').forEach(e=>{const t=(e.innerText||'').trim(); if(t) out.push([e.tagName.toLowerCase(), t]);}); return out; }""")
                    b.close()
                    ctx.urls.append({"url": url, "mode": "rendered", "status": status, "ok": True, "error": ""})
                    out, cur, buf = [], None, []
                    for tag, text in blocks:
                        if tag in ("h1", "h2", "h3"):
                            if cur and buf:
                                _emit(ctx, out, f'"{cur}"', buf, "section", url)
                            cur, buf = clean(text), []
                        elif cur:
                            buf.append(clean(text))
                    if cur and buf:
                        _emit(ctx, out, f'"{cur}"', buf, "section", url)
                    return out, ["rendered after bot check"]
                b.close()
                time.sleep(2 ** attempt)
            except Exception as e:
                last = f"attempt {attempt}: {type(e).__name__}: {str(e)[:120]}"
                ctx.log("   " + last)
                try:
                    b.close()
                except Exception:
                    pass
    ctx.urls.append({"url": url, "mode": "rendered", "status": 403, "ok": False, "error": "Cloudflare bot verification"})
    raise BlockedError(f"goarch.org blocked all rendered attempts ({last})")


def philaret(ctx):
    """Longer Catechism of St Philaret: 611 numbered questions in one page.

    The page changes shape partway through — questions 1-306 lead with a <p> carrying "N. text", from
    307 they move into <b> with the text inline, and elsewhere a bare "N." in <b> precedes the question
    in the next <p>. Splitting is therefore driven by the QUESTION SEQUENCE, not by tag shape: collect
    every segment that opens with a number, then walk them in document order taking the strict successor,
    resynchronising only when the wanted number never appears again (the page omits 288)."""
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    cands = []          # (segment index, question number, inline text after the number)
    for i, (tag, text) in enumerate(segs):
        if tag not in ("p", "b", "strong"):
            continue
        m = re.match(r"^(\d{1,3})\.\s*(.*)$", clean(text), re.S)
        if m:
            cands.append((i, int(m.group(1)), clean(m.group(2))))
    starts, want, ahead = {}, 1, [n for _, n, _ in cands]
    for k, (i, n, inline) in enumerate(cands):
        if n == want:
            starts[i] = (n, inline); want = n + 1
        elif n > want and want not in ahead[k:]:
            starts[i] = (n, inline); want = n + 1       # the page skips a number; resynchronise
    section, out, cur, buf = "", [], None, []
    order = sorted(starts)
    bounds = {s: (order[j + 1] if j + 1 < len(order) else len(segs)) for j, s in enumerate(order)}
    for i, (tag, text) in enumerate(segs):
        t_ = clean(text)
        if tag in ("h2", "h3", "h4") and i not in starts:
            section = t_.rstrip(".")
        if i in starts:
            if cur is not None:
                _emit(ctx, out, f"Q.{cur} ({cur_sec})", buf, "question", url)
            n, inline = starts[i]
            cur, buf, cur_sec = n, ([f"{n}. {inline}"] if inline else [f"{n}."]), section
            continue
        if cur is not None and tag in ("p", "i", "em", "a", "b", "strong", "blockquote", "li"):
            if t_ in (".", ";", ",", ")", "(", ";.") or not t_:
                continue
            buf.append(t_)
    if cur is not None:
        _emit(ctx, out, f"Q.{cur} ({cur_sec})", buf, "question", url)
    return out, [f"{len(out)} numbered questions of the 611 in the catechism; split by question sequence, "
                 f"tolerant of the page's mid-document change from <p> to <b> question headings"]


def dositheus(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf, div = [], None, [], None
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^Decree\s+(\d{1,2})\.?$", t)
        q = re.match(r"^Q\.\s*(\d)\.\s+(.+)$", t)
        if tag == "strong" and m:
            if cur:
                _emit(ctx, out, cur, buf, div, url)
            cur, buf, div = f"Decree {m.group(1)}", [], "decree"; continue
        if tag == "em" and q:
            if cur:
                _emit(ctx, out, cur, buf, div, url)
            cur, buf, div = f"Question {q.group(1)}", [t], "question"; continue
        if tag == "strong" and t.startswith("Epilogue"):
            if cur:
                _emit(ctx, out, cur, buf, div, url)
            cur = None
            break
        if cur and tag in ("p", "em", "i"):
            buf.append(t)
    if cur:
        _emit(ctx, out, cur, buf, div, url)
    return out, ["Decree 1–18 and Question 1–4 (Robertson 1899 translation, uncredited on page); provenance-checked at build"]


# =============================================================== Lutheran
BOC = "https://bookofconcord.org"
BOC_DOCS = {"ecumenical-creeds": "Ecumenical Creeds", "augsburg-confession": "Augsburg Confession",
            "defense": "Apology of the Augsburg Confession", "smalcald-articles": "Smalcald Articles",
            "power-and-primacy": "Treatise on the Power and Primacy of the Pope", "small-catechism": "Small Catechism",
            "large-catechism": "Large Catechism", "epitome": "Formula of Concord, Epitome",
            "solid-declaration": "Formula of Concord, Solid Declaration"}
BOC_GROUP_CHARS = 2600


def book_of_concord(ctx):
    from bs4 import BeautifulSoup
    home = ctx.html(BOC + "/")
    soup = BeautifulSoup(home, "lxml")
    paths = []
    for a in soup.find_all("a", href=True):
        h = a["href"].replace(BOC, "")
        parts = [p for p in h.split("/") if p]
        if len(parts) >= 2 and parts[0] in BOC_DOCS and h not in paths:
            paths.append(h)
    out, notes = [], []
    for h in paths:
        url = urljoin(BOC + "/", h)
        doc = BOC_DOCS[[p for p in h.split("/") if p][0]]
        try:
            segs = segments(ctx.html(url))
        except FetchError as e:
            notes.append(str(e)); ctx.log(f"   ! {e}"); continue
        title = next((clean(x) for t, x in segs if t in ("h2", "h1") and "Original Home" not in x and "BookOfConcord" not in x), "")
        if not title:
            continue
        # numbered paragraphs: <span>n</span><p>...</p>; unnumbered pages (creeds): plain p's
        paras, num = [], None
        for tag, text in segs:
            t = clean(text)
            if tag == "span" and re.fullmatch(r"\d{1,3}", t):
                num = int(t); continue
            if tag == "p" and t and not t.startswith("<<") and not t.startswith(">>"):
                paras.append((num, t)); num = None
        if not paras:
            continue
        loc_base = f"{doc}: {title.rstrip('.')}"
        if all(n is None for n, _ in paras):
            _emit(ctx, out, loc_base, [t for _, t in paras], "section", url)
            continue
        group, a, b, size = [], None, None, 0
        for n, t in paras:
            if n is None and not group:
                continue
            if group and size + len(t) > BOC_GROUP_CHARS and n is not None:
                _emit(ctx, out, f"{loc_base}, ¶{a}" + (f"–{b}" if b != a else ""), group, "paragraph-range", url)
                group, a, b, size = [], None, None, 0
            if n is not None:
                a = a if a is not None else n
                b = n
            group.append(t); size += len(t)
        if group:
            _emit(ctx, out, f"{loc_base}, ¶{a}" + (f"–{b}" if b != a else ""), group, "paragraph-range", url)
    notes.insert(0, f"{len(paths)} document pages crawled from the site index; numbered-paragraph ranges (≤{BOC_GROUP_CHARS} chars) inside each article")
    return out, notes


def small_catechism_cph(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    start = next((i for i, (t, x) in enumerate(segs) if t == "h4"), -1)
    if start < 0:
        raise FetchError("creed article h4 not found")
    buf = []
    for tag, text in segs[start:]:
        t = clean(text)
        if tag in ("h3", "h2") and t != "The First Article (Part 1)":
            break
        if tag in ("h4", "em", "strong", "p"):
            buf.append(t)
    out = []
    _emit(ctx, out, "Small Catechism, The Creed — First Article (Part 1), explanation", buf, "article", url)
    return out, ["single page (2017 explanation edition; CPH, linked by LCMS)"]


# =============================================================== Reformed / Presbyterian
def wcf_opc(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, ch, title, cur, buf = [], None, "", None, []
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^CHAPTER\s+(\d{1,2})$", t)
        if tag == "h3" and m:
            if cur:
                _emit(ctx, out, f"Chapter {ch}.{cur} — {title}", buf, "paragraph", url)
            ch, title, cur, buf = int(m.group(1)), "", None, []
            continue
        if ch and tag == "i" and not title:
            title = t; continue
        if ch and tag == "p":
            pm = re.match(r"^(\d{1,2})\.\s+(.+)$", t, re.S)
            if pm:
                if cur:
                    _emit(ctx, out, f"Chapter {ch}.{cur} — {title}", buf, "paragraph", url)
                cur, buf = int(pm.group(1)), [pm.group(2)]
            elif cur:
                buf.append(t)
    if cur:
        _emit(ctx, out, f"Chapter {ch}.{cur} — {title}", buf, "paragraph", url)
    return out, ["Westminster Confession (OPC edition), chapter.paragraph"]


def _opc_catechism(ctx, label):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf = [], None, []
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^Q\.\s*(\d{1,3})\.?$", t)
        if tag == "p" and m:
            if cur:
                _emit(ctx, out, f"{label} Q.{cur}", buf, "question", url)
            cur, buf = int(m.group(1)), []
            continue
        if cur and tag in ("i", "p"):
            buf.append(t)
    if cur:
        _emit(ctx, out, f"{label} Q.{cur}", buf, "question", url)
    return out, [f"{len(out)} questions"]


def wsc_opc(ctx):
    return _opc_catechism(ctx, "Shorter Catechism")


def wlc_opc(ctx):
    return _opc_catechism(ctx, "Larger Catechism")


PCUSA_SECTIONS = {1: "Nicene Creed", 2: "Apostles' Creed", 3: "Scots Confession", 4: "Heidelberg Catechism",
                  5: "Second Helvetic Confession", 6: "Westminster Confession of Faith",
                  7: "Westminster Shorter Catechism", 8: "Theological Declaration of Barmen", 9: "Confession of 1967",
                  10: "Confession of Belhar", 11: "A Brief Statement of Faith"}


def pcusa_book_of_confessions(ctx):
    url = ctx.row["canonical_url"]
    txt = pdf_repair(ctx.pdf(url).replace("\f", "\n"))
    lines = [l.rstrip() for l in txt.split("\n")]
    out, cur, buf, last = [], None, [], (0, 0)
    for l in lines:
        m = re.fullmatch(r"\s*(\d{1,2})\.(\d{1,3})\s*", l)
        if m:
            key = (int(m.group(1)), int(m.group(2)))
            if key <= last:
                if key[0] < last[0]:
                    break  # index region
                continue
            if cur:
                _emit(ctx, out, cur, buf, "confessional-number", url)
            major = key[0]
            sec = PCUSA_SECTIONS.get(major, f"section {major}")
            if major == 7 and key[1] >= 111:
                sec = "Westminster Larger Catechism"
            cur, buf, last = f"Book of Confessions {m.group(1)}.{m.group(2)} ({sec})", [], key
            continue
        if cur:
            s_ = l.strip()
            if not s_ or re.fullmatch(r"\d{1,3}", s_) or re.fullmatch(r"\d{1,2}\.\d{1,3}[–-]\.\d{1,3}", s_) \
               or re.fullmatch(r"(THE )?[A-Z][A-Z’' ,]+(CONFESSION|CREED|CATECHISM|DECLARATION|STATEMENT)\d?", s_) \
               or s_ in ("BOOK OF CONFESSIONS",):
                continue
            buf.append(strip_footnote_digits(s_))
    if cur:
        _emit(ctx, out, cur, buf, "confessional-number", url)
    return out, [f"PDF normalized; {len(out)} confessional numbers across {len(PCUSA_SECTIONS)} constituent documents"]


def heidelberg_crcna(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf, lords_day = [], None, [], ""
    for tag, text in segs:
        t = clean(text)
        if tag == "h4" and t.startswith("Lord"):
            lords_day = t; continue
        m = re.match(r"^Q & A (\d{1,3})$", t)
        if tag == "div" and m:
            if cur:
                _emit(ctx, out, cur, buf, "question", url)
            cur, buf = f"Q&A {m.group(1)} ({lords_day})", []
            continue
        if cur and tag in ("p", "em", "i"):
            if re.match(r"^\d{1,2}\s", t) or re.fullmatch(r"[\d\s,;:.\-–]+", t):
                continue   # footnote scripture lists
            buf.append(strip_footnote_digits(t))
        if cur and tag in ("h2", "h3") and t.startswith(("Part", "God", "Introduction")):
            pass
    if cur:
        _emit(ctx, out, cur, buf, "question", url)
    return out, [f"{len(out)} Q&A (CRC/RCA 2011 translation)"]


def belgic_crcna(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf = [], None, []
    for tag, text in segs:
        t = clean(text)
        if tag == "h3" and re.match(r"^Article \d{1,2}:", t):
            if cur:
                _emit(ctx, out, cur, buf, "article", url)
            cur, buf = t, []
            continue
        if tag in ("h2", "h3") and cur and not re.match(r"^Article", t):
            _emit(ctx, out, cur, buf, "article", url); cur = None
            continue
        if cur and tag in ("p", "em", "i"):
            buf.append(strip_footnote_digits(t))
    if cur:
        _emit(ctx, out, cur, buf, "article", url)
    return out, [f"{len(out)} articles (CRC/RCA 2011); Article 36 in two forms as published"]


# =============================================================== Anglican
def thirty_nine_articles(ctx):
    url = ctx.row["canonical_url"]
    blocks = ctx.rendered(url).get("blocks") or []
    out, cur, buf = [], None, []
    for b_ in blocks:
        t = clean(b_["text"])
        m = re.match(r"^(" + ROMAN + r")\.\s+OF\s+(.+)$", t)
        if m and b_["tag"] in ("p", "h2", "h3"):
            if cur:
                _emit(ctx, out, cur, buf, "article", url)
            n = ROMAN_MAP[m.group(1)]
            cur, buf = f"Article {m.group(1)} ({n}) — Of {m.group(2).title()}", []
            continue
        if cur and t.startswith("The Ratification"):
            _emit(ctx, out, cur, buf, "article", url); cur = None
            continue
        if cur and b_["tag"] in ("p", "li", "blockquote"):
            buf.append(t)
    if cur:
        _emit(ctx, out, cur, buf, "article", url)
    return out, [f"{len(out)} articles (rendered page)"]


def bcp_catechism_1662(ctx):
    url = ctx.row["canonical_url"]
    blocks = ctx.rendered(url).get("blocks") or []
    out, n, q, a = [], 0, None, []
    for b_ in blocks:
        t = b_["text"].strip()
        if b_["tag"] != "p":
            continue
        m = re.match(r"^(Question|Catechist)\.\s*(.+)$", t, re.S)
        if m:
            if q is not None:
                n += 1
                _emit(ctx, out, f'Catechism, Q.{n} — "{clean(q)[:70]}"', [q] + a, "question", url)
            q, a = clean(m.group(2)), []
            continue
        m = re.match(r"^Answer\.\s*(.+)$", t, re.S)
        if m and q is not None:
            a.append(clean(m.group(1))); continue
        if q is not None:
            a.append(clean(t))
    if q is not None:
        n += 1
        _emit(ctx, out, f'Catechism, Q.{n} — "{clean(q)[:70]}"', [q] + a, "question", url)
    return out, [f"{len(out)} question/answer pairs (unnumbered in the book; numbered here in order)"]


def athanasian_creed_cofe(ctx):
    url = "https://www.churchofengland.org/prayer-and-worship/worship-texts-and-resources/book-common-prayer/creed-s-athanasius"
    blocks = ctx.rendered(url).get("blocks") or []
    start = next((i for i, b_ in enumerate(blocks) if b_["text"].strip().upper().startswith("QUICUNQUE VULT")), -1)
    if start < 0:
        raise FetchError("QUICUNQUE VULT heading not found")
    verses = []
    for b_ in blocks[start + 1:]:
        if b_["tag"].startswith("h"):
            break
        if b_["tag"] == "p":
            verses.append(clean(b_["text"]))
    out = []
    _emit(ctx, out, "Quicunque Vult (Creed of S. Athanasius), At Morning Prayer", verses, "creed", url)
    return out, ["official host churchofengland.org (registry lists ccel.org as lineage for 1 released cell)", f"{len(verses)} verses"]


def tec_outline_of_faith(ctx):
    url = ctx.row["canonical_url"]
    pages = ctx.pdf(url).split("\f")
    start = next((i for i, p in enumerate(pages) if "An Outline of the Faith" in p and "commonly called the Catechism" in p), -1)
    if start < 0:
        raise FetchError("Outline of the Faith not found in PDF")
    out, section, q, a, state = [], "", None, [], None
    for pi in range(start, min(len(pages), start + 20)):
        page_no = pi + 1
        if pi > start and "Concerning the Catechism" in pages[pi] and "Outline" not in pages[pi]:
            pass
        for raw in pdf_repair(pages[pi]).split("\n"):
            l = raw.strip()
            if not l or re.fullmatch(r"\d{3}", l) or l.startswith("Catechism") and re.search(r"\d{3}$", l):
                continue
            if l in ("An Outline of the Faith", "commonly called the Catechism"):
                continue
            if l == "Q.":
                if q is not None:
                    _emit(ctx, out, f"Outline of the Faith (BCP p. {q_page}) — {q_section}: Q. {clean(' '.join(q))[:80]}", q + a, "question", url)
                q, a, state, q_page, q_section = [], [], "Q", page_no, section
                continue
            if l == "A.":
                state = "A"; continue
            if state is None or (state == "A" and re.fullmatch(r"[A-Z][A-Za-z’' ]{2,40}", l) and not l.endswith(".")):
                # section heading (Human Nature, God the Father, ...)
                if l.startswith("Historical Documents"):
                    break
                section = l
                if state == "A":
                    pass
                continue
            if state == "Q":
                q.append(strip_footnote_digits(l))
            elif state == "A":
                a.append(strip_footnote_digits(l))
        if "Historical Documents" in pages[pi] and pi > start + 10:
            break
    if q is not None:
        _emit(ctx, out, f"Outline of the Faith (BCP p. {q_page}) — {q_section}: Q. {clean(' '.join(q))[:80]}", q + a, "question", url)
    return out, [f"PDF pages {start + 1}–{start + 20} region; {len(out)} Q/A pairs"]


def acna_to_be_a_christian(ctx):
    url = ctx.row["canonical_url"]
    txt = pdf_repair(ctx.pdf(url).replace("\f", "\n"))
    lines = [l.strip() for l in txt.split("\n")]
    out, cur, buf, expect, qtext, in_q = [], None, [], 1, [], False
    for l in lines:
        m = re.match(r"^(\d{1,3})\.\s*(.*)$", l)
        if m and int(m.group(1)) == expect:
            if cur:
                _emit(ctx, out, f"To Be a Christian, Q.{cur} — {clean(' '.join(qtext))[:70]}", qtext + buf, "question", url)
            cur, expect, qtext, buf, in_q = int(m.group(1)), expect + 1, [m.group(2)] if m.group(2) else [], [], True
            if qtext and qtext[0].endswith("?"):
                in_q = False
            continue
        if cur is None:
            continue
        if not l or re.fullmatch(r"\d{1,3}", l) or re.fullmatch(r"[A-Z ]{6,}", l):
            continue
        if in_q:
            qtext.append(l)
            if l.endswith("?"):
                in_q = False
        else:
            buf.append(l)
    if cur:
        _emit(ctx, out, f"To Be a Christian, Q.{cur} — {clean(' '.join(qtext))[:70]}", qtext + buf, "question", url)
    return out, [f"{len(out)} numbered questions (fallback tier: registry_fallback_only_rows)"]


# =============================================================== Baptist
def bfm2000(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, art, sub, buf, in_body = [], None, None, [], False
    def flush():
        if art and buf:
            loc = art if not sub else f"{art.split('.')[0]}.{sub}"
            _emit(ctx, out, loc, buf, "article" if not sub else "subsection", url)
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^(" + ROMAN + r")\.\s+(.+)$", t)
        if tag == "h2" and m:
            flush(); art, sub, buf, in_body = f"{m.group(1)}. {m.group(2)}", None, [], True; continue
        if not in_body:
            continue
        sm = re.match(r"^([A-D])\.\s+(.+)$", t)
        if tag in ("strong", "b", "h3") and sm:
            flush(); sub, buf = f"{sm.group(1)}. {sm.group(2)}", []; continue
        if tag in ("p", "em", "i") and t and not t.startswith("**Note"):
            buf.append(t)
        if tag in ("h3", "h2") and not m and t.startswith(("Table", "Share")):
            flush(); art = None
    flush()
    return out, [f"{len(out)} articles/subsections"]


def london_1689_ch2(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf = [], None, []
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^Paragraph (\d{1,2})$", t)
        if tag == "h2" and m:
            if cur:
                _emit(ctx, out, cur, buf, "paragraph", url)
            cur, buf = f"Chapter 2 (Of God and the Holy Trinity), paragraph {m.group(1)}", []
            continue
        if cur and (t.startswith("Back to Chapter Index") or tag == "h2"):
            _emit(ctx, out, cur, buf, "paragraph", url); cur = None; continue
        if cur and tag == "p":
            buf.append(t)
    if cur:
        _emit(ctx, out, cur, buf, "paragraph", url)
    return out, ["chapter 2 only, as ratified (the1689confession.com, single-congregation host)"]


def abc_usa_10facts(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf = [], None, []
    for tag, text in segs:
        t = clean(text)
        m = re.match(r"^(\d{1,2})\.\s+(.+)$", t)
        if tag == "h2" and m:
            if cur:
                _emit(ctx, out, cur, buf, "fact", url)
            cur, buf = f"Fact {m.group(1)}", [t]
            continue
        if cur and tag in ("h4", "h3"):
            _emit(ctx, out, cur, buf, "fact", url); cur = None; continue
        if cur and tag == "p":
            buf.append(t)
    if cur:
        _emit(ctx, out, cur, buf, "fact", url)
    return out, [f"{len(out)} numbered facts (descriptive, non-binding)"]


# =============================================================== Methodist / Wesleyan
def _umc(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf = [], None, []
    for tag, text in segs:
        t = clean(text)
        if tag == "h4" and re.match(r"^Article " + ROMAN + r"\b", t):
            if cur:
                _emit(ctx, out, cur, buf, "article", url)
            cur, buf = t, []
            continue
        if cur and tag in ("h3", "h2", "h4"):
            _emit(ctx, out, cur, buf, "article", url); cur = None; continue
        if cur and tag == "p":
            buf.append(t)
    if cur:
        _emit(ctx, out, cur, buf, "article", url)
    return out, [f"{len(out)} articles"]


def umc_articles(ctx):
    return _umc(ctx)


def umc_eub_confession(ctx):
    return _umc(ctx)


def wesleyan_articles(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, art, para, buf, started = [], None, None, [], False
    for tag, text in segs:
        t = clean(text)
        if tag == "h2" and t == "Articles of Religion":
            started = True; continue
        if not started:
            continue
        m = re.match(r"^(\d{1,2})\.\s+([A-Z].+)$", t)
        if tag in ("strong", "em") and m:
            if para:
                _emit(ctx, out, f"Article {art}, ¶{para}", buf, "paragraph", url)
            art, para, buf = t, None, []
            continue
        if tag in ("strong", "em") and art and para is None and not re.fullmatch(r"\d{3}\.", t):
            art = art + " " + t; continue
        pm = re.fullmatch(r"(\d{3})\.", t)
        if tag in ("strong", "em") and pm:
            if para:
                _emit(ctx, out, f"Article {art}, ¶{para}", buf, "paragraph", url)
            para, buf = pm.group(1), []
            continue
        if para and tag == "p":
            buf.append(t)
        if tag == "h2" and t != "Articles of Religion" and para:
            _emit(ctx, out, f"Article {art}, ¶{para}", buf, "paragraph", url); para = None; break
    if para:
        _emit(ctx, out, f"Article {art}, ¶{para}", buf, "paragraph", url)
    return out, [f"{len(out)} numbered paragraphs"]


# =============================================================== Mennonite / Anabaptist
MENN = "https://www.mennoniteusa.org/who-are-mennonites/what-we-believe/confession-of-faith/"


def mennonite_1995(ctx):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(ctx.html(MENN), "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.startswith(MENN) and h != MENN and h not in links:
            links.append(h)
    out = []
    for url in links:
        try:
            segs = segments(ctx.html(url))
        except FetchError as e:
            ctx.log(f"   ! {e}"); continue
        h1 = next((i for i, (t, x) in enumerate(segs) if t == "h1" and re.match(r"^Article \d", clean(x))), -1)
        if h1 < 0:
            continue
        buf = []
        for tag, text in segs[h1 + 1:]:
            t = clean(text)
            if tag == "h3" and t == "Commentary":
                break
            if tag in ("h2", "h3") and t in ("In This Section",):
                break
            if tag in ("p", "li", "blockquote"):
                buf.append(t)
        _emit(ctx, out, clean(segs[h1][1]), buf, "article", url)
    return out, [f"{len(links)} article pages; article text only (commentary excluded)"]


def dordrecht(ctx):
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf = [], None, []
    for tag, text in segs:
        t = clean(text)
        if tag == "h3" and re.match(r"^" + ROMAN + r"\.\s+", t):
            if cur:
                _emit(ctx, out, cur, buf, "article", url)
            cur, buf = f"Article {t}", []
            continue
        if cur and tag in ("strong", "h2", "h3"):
            _emit(ctx, out, cur, buf, "article", url); cur = None; continue
        if cur and tag == "p":
            buf.append(t)
    if cur:
        _emit(ctx, out, cur, buf, "article", url)
    return out, [f"{len(out)} articles"]


# =============================================================== dispatch
ADAPTERS = {
    "BSR-RC-01": ccc_section_two, "BSR-RC-02": dei_filius_latin, "BSR-RC-03": dei_filius_ewtn,
    "BSR-RC-04": lateran_canon1, "BSR-RC-06": vatican_creeds, "BSR-RC-07": compendium,
    "BSR-EO-01": oca_symbol_of_faith, "BSR-EO-02": oca_holy_trinity, "BSR-EO-03": goarch,
    "BSR-EO-04": philaret, "BSR-EO-05": dositheus, "BSR-EO-06": oca_councils,
    "BSR-LU-01": book_of_concord, "BSR-LU-03": small_catechism_cph,
    "BSR-RP-01": wcf_opc, "BSR-RP-02": wsc_opc, "BSR-RP-03": wlc_opc, "BSR-RP-04": pcusa_book_of_confessions,
    "BSR-RP-05": heidelberg_crcna, "BSR-RP-06": belgic_crcna,
    "BSR-AN-01": thirty_nine_articles, "BSR-AN-02": bcp_catechism_1662, "BSR-AN-03": athanasian_creed_cofe,
    "BSR-AN-04": tec_outline_of_faith, "BSR-AN-05": acna_to_be_a_christian,
    "BSR-BA-01": bfm2000, "BSR-BA-02": london_1689_ch2, "BSR-BA-03": abc_usa_10facts,
    "BSR-MW-01": umc_articles, "BSR-MW-02": umc_eub_confession, "BSR-MW-04": wesleyan_articles,
    "BSR-MA-01": mennonite_1995, "BSR-MA-02": dordrecht,
}

# Rows with no text corpus by policy or by the state of the host (recorded in the manifest, never chunked).
NO_TEXT = {
    "BSR-RC-05": ("LINEAGE", "Fordham sourcebook is a lineage host for 4 released cells; text corpus for Lateran IV canon 1 is BSR-RC-04"),
    "BSR-LU-02": ("AUTHORITY_URL_ONLY", "files.lcms.org is a client-side viewer (AC-08): registered as the LCMS adoption URL; no text extraction"),
    "BSR-MW-03": ("UNAVAILABLE_ON_RATIFIED_DOMAIN", "canonical_url returns HTTP 404; the current 'Book of Doctrines & Discipline' page on globalmethodist.org carries no doctrinal text in HTML and links the BDD only as a PDF on irp.cdn-website.com (not a ratified domain). Needs an author registry correction before any text can be admitted"),
}
