"""Locator-scoped extraction (P020 / Citation Selection Rule 10).

Every phrase assertion is checked INSIDE the cited article/section/verse block.
Resolvers are keyed by host (+ path fragment). A resolver returns a ScopeResult
or raises ScopeError; there is never a silent whole-page fallback. The only
document-level modes are explicit and named:
  DOCUMENT-IS-LOCATOR   the cited unit is the whole page (a resolution, a
                        transcript page, a single-article page, a catechetical
                        article, a proclamation without paragraph anchors)
  SECTION-SCOPED        a named section of the page (creed within a creed page,
                        chapter within a constitution, article within a
                        confession page)
  VERSE-SCOPED          the verse ids named in the URL's id= parameter
  PARAGRAPH-SCOPED      a numbered paragraph/canon/question
"""
import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, NavigableString

from .textnorm import normalize, pdf_repair


class ScopeError(Exception):
    pass


@dataclass
class ScopeResult:
    text: str
    mode: str
    note: str = ""
    start: int = -1
    end: int = -1


# ---------------------------------------------------------------- segmentation
_DROP = ["script", "style", "noscript", "svg", "nav", "footer", "header", "head", "form", "button"]


def html_segments(html):
    """Linear (tag, text) segments in document order (direct text per element)."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(_DROP):
        t.decompose()
    out = []

    def walk(el):
        for ch in el.children:
            if isinstance(ch, NavigableString):
                st = str(ch).strip()
                if st:
                    out.append((el.name, st))
            else:
                walk(ch)

    walk(soup.body or soup)
    return out


def _join(segs, a, b):
    return "\n".join(t for _, t in segs[a:b])


def _find(segs, pattern, start=0, tags=None, flags=re.I):
    rx = re.compile(pattern, flags)
    for i in range(start, len(segs)):
        tag, text = segs[i]
        if tags and tag not in tags:
            continue
        if rx.search(text):
            return i
    return -1


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
         "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18}
ROMAN_INV = {v: k for k, v in ROMAN.items()}


def _roman_in(locator):
    m = re.search(r"\b(Article|Chapter|Articles)\s+([IVX]+)\b", locator)
    if m:
        return m.group(2)
    m = re.search(r"\b([IVX]+)\.", locator)
    return m.group(1) if m else None


def _arabic_in(locator, word):
    m = re.search(rf"\b{word}\s+(\d+)", locator, re.I)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- resolvers
def r_church_of_england(loc, doc, segs, url):
    rn = _roman_in(loc) or "I"
    i = _find(segs, rf"^{rn}\. Of ", tags={"a", "h1", "h2", "h3", "h4", "strong", "p"})
    if i < 0:
        raise ScopeError(f"Article {rn} heading not found")
    j = _find(segs, r"^[IVX]+\. Of |^His Majesty", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", f"Article {rn}", i, j)


def r_opc_wcf(loc, doc, segs, url):
    m = re.search(r"Chapter\s+([IVX]+)\.(\d+)", loc)
    if not m:
        raise ScopeError("locator lacks Chapter N.k")
    ch, para = ROMAN[m.group(1)], int(m.group(2))
    i = _find(segs, rf"^CHAPTER {ch}$", tags={"h3"})
    if i < 0:
        raise ScopeError(f"CHAPTER {ch} heading not found")
    j = _find(segs, r"^CHAPTER \d+$", i + 1, tags={"h3"})
    j = j if j > 0 else len(segs)
    k = _find(segs, rf"^{para}\. ", i, tags={"p"})
    if k < 0 or k >= j:
        raise ScopeError(f"paragraph {para} not found in chapter {ch}")
    k2 = _find(segs, rf"^{para + 1}\. ", k + 1, tags={"p"})
    k2 = k2 if 0 < k2 < j else j
    return ScopeResult(_join(segs, k, k2), "PARAGRAPH-SCOPED", f"WCF {m.group(1)}.{para}", k, k2)


def r_opc_sc(loc, doc, segs, url):
    q = _arabic_in(loc, r"Q\.?") or int(re.search(r"(\d+)", loc).group(1))
    i = _find(segs, rf"^Q\.\s*{q}\.?$")
    if i < 0:
        raise ScopeError(f"Q. {q} not found")
    j = _find(segs, r"^Q\.\s*\d+\.?$", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "PARAGRAPH-SCOPED", f"WSC Q.{q}", i, j)


def r_bfm(loc, doc, segs, url):
    rn = _roman_in(loc)
    if not rn:
        raise ScopeError("locator lacks roman article number")
    letter = None
    m = re.search(rf"\b{rn}\.([A-D])\.", loc)
    if m:
        letter = m.group(1)
    i = _find(segs, rf"^{rn}\. ", tags={"h2"})
    if i < 0:
        raise ScopeError(f"Article {rn} h2 not found")
    j = _find(segs, r"^[IVX]+\. ", i + 1, tags={"h2"})
    j = j if j > 0 else len(segs)
    if letter:
        k = _find(segs, rf"^{letter}\. ", i, tags={"strong", "b", "h3"})
        if k < 0 or k >= j:
            raise ScopeError(f"subsection {letter} not found in article {rn}")
        k2 = _find(segs, r"^[A-D]\. ", k + 1, tags={"strong", "b", "h3"})
        k2 = k2 if 0 < k2 < j else j
        return ScopeResult(_join(segs, k, k2), "SECTION-SCOPED", f"BF&M {rn}.{letter}", k, k2)
    return ScopeResult(_join(segs, i, j), "SECTION-SCOPED", f"BF&M {rn}", i, j)


_ATHANASIAN_CLAUSES = {  # named clause -> standard verse numbers of the Athanasian Creed
    "almighty": (13, 14), "uncreated": (8, 8), "eternal": (10, 11),
    "trinity unity/distinction": (3, 4), "unity/distinction": (3, 4),
}


def r_ccel_athanasian(loc, doc, segs, url):
    key = None
    ll = loc.casefold()
    for k in _ATHANASIAN_CLAUSES:
        if k in ll:
            key = k
            break
    if key is None:
        raise ScopeError(f"unknown Athanasian clause locator {loc!r}")
    v1, v2 = _ATHANASIAN_CLAUSES[key]
    i = _find(segs, rf"^{v1}\.\s")
    j = _find(segs, rf"^{v2 + 1}\.\s")
    if i < 0 or j < 0:
        raise ScopeError(f"verses {v1}-{v2} not found")
    return ScopeResult(_join(segs, i, j), "PARAGRAPH-SCOPED", f"Athanasian Creed vv. {v1}-{v2}", i, j)


def r_vatican_ccc(loc, doc, segs, url):
    m = re.search(r"CCC\s*(\d+)", loc)
    if not m:
        raise ScopeError("locator lacks CCC paragraph number")
    n = int(m.group(1))
    i = _find(segs, rf"^{n}\s", tags={"p"})
    if i < 0:
        raise ScopeError(f"CCC paragraph {n} not found")
    j = -1
    for k in range(i + 1, len(segs)):
        mm = re.match(r"^(\d{1,4})\s", segs[k][1])
        if segs[k][0] == "p" and mm and int(mm.group(1)) > n:
            j = k
            break
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "PARAGRAPH-SCOPED", f"CCC {n}", i, j)


def r_vatican_credo(loc, doc, segs, url):
    creed = "Nicene" if ("nicene" in (doc or "").casefold() or "light from light" in loc.casefold()
                         or "holy spirit" in loc.casefold() or "son clause" in loc.casefold()) else "Apostles"
    if "apostles" in (doc or "").casefold() and "nicene" not in (doc or "").casefold():
        creed = "Apostles"
    i = _find(segs, rf"^The {creed} Creed$")
    if i < 0:
        raise ScopeError(f"{creed} Creed section not found")
    j = _find(segs, r"^The (Apostles|Nicene) Creed$|^END textimage", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", f"CCC Credo — {creed} Creed", i, j)


def r_compendium(loc, doc, segs, url):
    q = _arabic_in(loc, r"Q\.?") or int(re.search(r"(\d+)", loc).group(1))
    i = _find(segs, rf"^{q}\. ", tags={"b", "strong", "p"})
    if i < 0:
        raise ScopeError(f"Compendium question {q} not found")
    j = _find(segs, rf"^{q + 1}\. ", i + 1, tags={"b", "strong", "p"})
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "PARAGRAPH-SCOPED", f"Compendium Q.{q}", i, j)


def r_lateran4(loc, doc, segs, url):
    n = _arabic_in(loc, "Canon") or _arabic_in(loc, "Constitution") or 1
    i = _find(segs, rf"^CANON {n}$")
    if i < 0:
        raise ScopeError(f"CANON {n} not found")
    j = _find(segs, rf"^CANON {n + 1}$", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "PARAGRAPH-SCOPED", f"Lateran IV Canon {n}", i, j)


def r_ewtn_dei_filius(loc, doc, segs, url):
    # EWTN renders Dei Filius without chapter headings; chapter 1 ("God the creator of all things")
    # runs from the title to the opening sentence of chapter 2 ("The same Holy Mother Church…").
    rn = _roman_in(loc) or "I"
    if rn != "I":
        raise ScopeError("only Chapter I is scoped on the EWTN witness")
    i = _find(segs, r"^First Vatican Council: Dogmatic Constitution")
    if i < 0:
        raise ScopeError("Dei Filius title block not found")
    j = _find(segs, r"^The same Holy Mother Church|^The same holy mother church", i + 1)
    if j < 0:
        # The EWTN witness is an excerpt page ("Excerpts From Church Documents") carrying Chapter I only.
        body = [k for k in range(i + 1, len(segs)) if segs[k][0] == "p"]
        if not body or "one true and living God" not in segs[body[0]][1]:
            raise ScopeError("Chapter I opening ('one true and living God') not found after title")
        j = body[-1] + 1
        return ScopeResult(_join(segs, i, j), "SECTION-SCOPED",
                           "Dei Filius Chapter I (EWTN excerpt page carries Chapter I only; no chapter 2 present)", i, j)
    return ScopeResult(_join(segs, i, j), "SECTION-SCOPED", "Dei Filius Chapter I (bounded by chapter 2 opening)", i, j)


def r_vaticannews_credo(loc, doc, segs, url):
    d = (doc or "").casefold()
    creed = "Nicene" if "nicene" in d else "Apostles"
    if creed == "Apostles":
        i = _find(segs, r"^I believe in God the Father almighty", tags={"p"})
        j = _find(segs, r"^I believe in one God", i + 1, tags={"p"})
    else:
        i = _find(segs, r"^I believe in one God", tags={"p"})
        j = _find(segs, r"^Amen\.?$", i + 1, tags={"p"})
        j = j + 1 if j > 0 else -1
    if i < 0:
        raise ScopeError(f"{creed} Creed block not found")
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", f"Credo page — {creed} Creed", i, j)


def r_bookofconcord_nicene(loc, doc, segs, url):
    i = _find(segs, r"^The Nicene Creed$", tags={"h2"})
    if i < 0:
        raise ScopeError("Nicene Creed heading not found")
    j = _find(segs, r"^<<|^>>|^The Athanasian Creed", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", "Nicene Creed", i, j)


def r_bookofconcord_article(loc, doc, segs, url):
    i = _find(segs, r"^Article [IVX]+\. ", tags={"h2", "h1"})
    if i < 0:
        raise ScopeError("Article heading not found")
    j = -1
    for k in range(i + 1, len(segs)):
        if segs[k][0] == "a" and ("<<" in segs[k][1] or ">>" in segs[k][1]):
            j = k
            break
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", segs[i][1], i, j)


def r_umc(loc, doc, segs, url):
    rn = _roman_in(loc)
    if not rn:
        raise ScopeError("locator lacks roman article number")
    i = _find(segs, rf"^Article {rn}\b", tags={"h4", "h3", "h2"})
    if i < 0:
        raise ScopeError(f"Article {rn} heading not found")
    j = _find(segs, r"^Article [IVX]+\b|^Related Tags", i + 1, tags={"h4", "h3", "h2"})
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", f"Article {rn}", i, j)


def r_crcna_belgic(loc, doc, segs, url):
    n = _arabic_in(loc, "Article")
    if not n:
        raise ScopeError("locator lacks article number")
    i = _find(segs, rf"^Article {n}:", tags={"h3"})
    if i < 0:
        raise ScopeError(f"Article {n} heading not found")
    j = _find(segs, r"^Article \d+:|^Background", i + 1, tags={"h3"})
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", f"Belgic Article {n}", i, j)


def r_mennonite(loc, doc, segs, url):
    i = _find(segs, r"^Article \d+\. ", tags={"h1"})
    if i < 0:
        raise ScopeError("Article h1 not found")
    j = _find(segs, r"^Commentary$", i + 1)
    if j < 0:
        raise ScopeError("Commentary boundary not found")
    return ScopeResult(_join(segs, i, j), "SECTION-SCOPED", segs[i][1] + " (article text, not commentary)", i, j)


def r_newadvent(loc, doc, segs, url):
    i = _find(segs, r"^The Definition of Faith$", tags={"h2"})
    if i < 0:
        raise ScopeError("Definition of Faith heading not found")
    j = _find(segs, r".+", i + 1, tags={"h2"})
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", "Definition of Faith", i, j)


def r_oca_article(loc, doc, segs, url):
    i = _find(segs, r".+", tags={"h1"})
    if i < 0:
        raise ScopeError("article h1 not found")
    j = -1
    for k in range(i + 1, len(segs)):
        if segs[k][0] in ("h1", "h2", "h3") and segs[k][1] in ("Previous", "Next", "The Orthodox Faith", "The Orthodox Church in America"):
            j = k
            break
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "DOCUMENT-IS-LOCATOR", f"OCA article “{segs[i][1]}”", i, j)


def r_1689(loc, doc, segs, url):
    n = _arabic_in(loc, "paragraph")
    if not n:
        raise ScopeError("locator lacks paragraph number")
    i = _find(segs, rf"^Paragraph {n}$", tags={"h2"})
    if i < 0:
        raise ScopeError(f"Paragraph {n} heading not found")
    j = _find(segs, r"^Paragraph \d+$|^Back to Chapter Index", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "PARAGRAPH-SCOPED", f"1689 paragraph {n}", i, j)


def r_sbc_resolution(loc, doc, segs, url):
    i = _find(segs, r"^(WHEREAS|RESOLVED)\b", tags={"p"})
    if i < 0:
        raise ScopeError("resolution body (WHEREAS/RESOLVED clauses) not found")
    j = _find(segs, r"^EN ESPANOL|^Resource Categories", i + 1)
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "DOCUMENT-IS-LOCATOR",
                       "resolution body (WHEREAS/RESOLVED clauses)", i, j)


def r_nafwb(loc, doc, segs, url):
    i = _find(segs, rf"^{re.escape(loc.strip())}$", tags={"strong", "b", "h3", "h4"})
    if i < 0:
        raise ScopeError(f"heading {loc!r} not found")
    j = _find(segs, r".+", i + 1, tags={"strong", "b", "h3", "h4"})
    return ScopeResult(_join(segs, i, j if j > 0 else len(segs)), "SECTION-SCOPED", loc, i, j)


HOST_RESOLVERS = [
    ("churchofengland.org", r_church_of_england),
    ("opc.org/wcf", r_opc_wcf),
    ("opc.org/sc", r_opc_sc),
    ("bfm.sbc.net", r_bfm),
    ("ccel.org/ccel/creeds/athanasian", r_ccel_athanasian),
    ("vatican.va/content/catechism/en/part_one/section_one/chapter_three/article_2/the_credo", r_vatican_credo),
    ("vatican.va/content/catechism", r_vatican_ccc),
    ("vatican.va/archive/compendium_ccc", r_compendium),
    ("fordham.edu/basis/lateran4", r_lateran4),
    ("ewtn.com", r_ewtn_dei_filius),
    ("vaticannews.va/en/prayers", r_vaticannews_credo),
    ("bookofconcord.org/ecumenical-creeds/nicene-creed", r_bookofconcord_nicene),
    ("bookofconcord.org/augsburg-confession", r_bookofconcord_article),
    ("umc.org/en/content", r_umc),
    ("crcna.org/welcome/beliefs/confessions/belgic-confession", r_crcna_belgic),
    ("mennoniteusa.org", r_mennonite),
    ("newadvent.org/fathers/3813", r_newadvent),
    ("oca.org/orthodoxy", r_oca_article),
    ("the1689confession.com", r_1689),
    ("sbc.net/resource-library/resolutions", r_sbc_resolution),
    ("nafwb.org", r_nafwb),
]


def resolve_html(url, locator, document, html):
    segs = html_segments(html)
    key = url.split("//", 1)[-1]
    for frag, fn in HOST_RESOLVERS:
        if frag in key:
            return fn(locator or "", document or "", segs, url)
    raise ScopeError(f"no scope resolver registered for {url}")


# ---------------------------------------------------------------- PDF
def resolve_pdf(url, locator, document, pdf_txt):
    """PC(USA) Book of Confessions: confessional numbering (1.2, 2.1, 3.01) appears
    on its own line before each numbered paragraph."""
    m = re.match(r"\s*(\d+\.\d+)", locator or "")
    if not m:
        raise ScopeError("PDF locator lacks confessional number")
    num = m.group(1)
    txt = pdf_repair(pdf_txt.replace("\f", "\n"))
    lines = txt.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == num), -1)
    if start < 0:
        raise ScopeError(f"confessional number {num} not found on its own line")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.fullmatch(r"\d+\.\d+", lines[i].strip()) and lines[i].strip() != num:
            end = i
            break
    return ScopeResult("\n".join(lines[start:end]), "PARAGRAPH-SCOPED", f"Book of Confessions {num}", start, end)


# ---------------------------------------------------------------- rendered (Playwright)
def resolve_rendered(url, locator, document, rendered):
    pids = rendered.get("pids", {}) or {}
    qs = parse_qs(urlparse(url).query)
    idp = (qs.get("id") or [""])[0]
    if idp:
        ids = []
        for part in idp.split(","):
            mm = re.fullmatch(r"p(\d+)(?:-p(\d+))?", part.strip())
            if not mm:
                raise ScopeError(f"unrecognized id parameter {idp!r}")
            a = int(mm.group(1)); bb = int(mm.group(2) or a)
            ids.extend(f"p{k}" for k in range(a, bb + 1))
        missing = [i for i in ids if i not in pids]
        if missing:
            raise ScopeError(f"verse ids not rendered: {missing}")
        return ScopeResult("\n".join(pids[i] for i in ids), "VERSE-SCOPED", idp)
    mm = re.match(r"\s*Paragraph\s+(\d+)", locator or "", re.I)
    if mm:
        pid = f"p{mm.group(1)}"
        if pid not in pids:
            raise ScopeError(f"paragraph anchor {pid} not rendered")
        return ScopeResult(pids[pid], "PARAGRAPH-SCOPED", pid)
    main = rendered.get("main") or ""
    if len(main) < 200:
        raise ScopeError("rendered main content too short")
    return ScopeResult(main, "DOCUMENT-IS-LOCATOR", "rendered article body")
