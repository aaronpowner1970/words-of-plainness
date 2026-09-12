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
from sjn_pipeline.scope import html_segments  # noqa: E402

from urllib.parse import urlparse  # noqa: E402

from sjn_pipeline.registry import host_matches, normalize_host  # noqa: E402

from .config import ARCHIVE_DIR, RETIRED_HOSTS  # noqa: E402
from .textutil import (segments, join, clean, strip_footnote_digits, sha, pdf_repair, fix_mojibake,  # noqa: E402
                       nfc, has_polytonic, strip_foreign_parentheticals, normalize, dehyphenate, hyphenation_residue, contains)

ROMAN = r"(?:[IVXLC]+)"
ROMAN_MAP = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11,
             "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
             "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25, "XXVI": 26, "XXVII": 27, "XXVIII": 28,
             "XXIX": 29, "XXX": 30, "XXXI": 31, "XXXII": 32, "XXXIII": 33, "XXXIV": 34, "XXXV": 35, "XXXVI": 36,
             "XXXVII": 37, "XXXVIII": 38, "XXXIX": 39}


def retired_host(url):
    """The retirement reason if `url` sits on a retired registry host (config.RETIRED_HOSTS), else None.
    A retired host is never requested, for any purpose."""
    host = normalize_host(urlparse(url or "").netloc) if str(url or "").startswith("http") else normalize_host(str(url or "").split("/")[0])
    for h, reason in RETIRED_HOSTS.items():
        if host and host_matches(host, h):
            return reason
    return None


class Ctx:
    def __init__(self, row, fetcher, log=print, config=None, admitted_hosts=None):
        self.row = row
        self.rid = row["registry_id"]
        self.fetcher = fetcher
        self.log = log
        self.config = config or {}
        self.urls = []
        # Host guard (2026-09-12): every URL an adapter requests must sit on a host the row admits under
        # R001 — its publisher_domain, plus the AC-15 official domain for a controlled-storage row. A
        # corpus fetched from any other host would put text in front of the agents that the registry
        # never ratified for that row (cal-3 built BSR-AN-03 from churchofengland.org while its
        # publisher_domain was ccel.org). None = no guard (tests only).
        self.admitted_hosts = list(admitted_hosts) if admitted_hosts is not None else None

    def _check_host(self, url):
        reason = retired_host(url)
        if reason:
            raise RetiredHostError(f"{url}: host retired — {reason}")
        if self.admitted_hosts is None:
            return
        host = normalize_host(urlparse(url).netloc)
        if not any(host_matches(host, d) for d in self.admitted_hosts):
            raise HostNotAdmittedError(f"{url}: host {host} is not admitted for {self.rid} (publisher_domain "
                                       f"{self.row.get('publisher_domain')!r}; admitted {self.admitted_hosts})")

    def _log_fetch(self, url, mode, fr):
        rec = {"url": url, "mode": mode, "status": fr.status, "ok": fr.ok, "error": fr.error,
               "final_url": fr.final_url, "redirects": list(fr.redirects or []), "cross_host_redirect": fr.cross_host_redirect}
        self.urls.append(rec)
        if fr.cross_host_redirect:
            raise RedirectError(f"{url}: host redirected onto a different site ({fr.error or fr.cross_host_redirect}); "
                                f"the ratified URL is fetched byte for byte and cross-host redirects are refused")
        return rec

    def html(self, url):
        self._check_host(url)
        fr = self.fetcher.get(url)
        self._log_fetch(url, "http", fr)
        if fr.status == 403:
            raise BlockedError(f"{url}: HTTP 403 (host refuses automated fetch; Cloudflare challenge where the host is behind Cloudflare)")
        if not fr.ok or not fr.html:
            raise FetchError(f"{url}: {fr.error or 'empty body'}")
        return fr.html

    def pdf(self, url):
        """PDF text with line-break hyphenation joined at extraction (textutil.dehyphenate, whole-document
        vocabulary as evidence) — before any adapter splits it, so no adapter can carry "na-\nture" into a chunk."""
        self._check_host(url)
        fr = self.fetcher.get(url)
        self._log_fetch(url, "pdf", fr)
        if fr.status == 403:
            raise BlockedError(f"{url}: HTTP 403")
        if not fr.ok or not fr.pdf_bytes:
            raise FetchError(f"{url}: {fr.error or 'no PDF bytes'}")
        raw = pdf_text(fr.pdf_bytes)
        self.hyphenation = getattr(self, "hyphenation", {})
        return dehyphenate(raw, stats=self.hyphenation)

    def archived(self, url, kind="html"):
        """A one-time archived fetch committed under recovery-runs/archived-fetches/<rid>.<ext> with a
        <rid>.provenance.json beside it (url, fetched_at, method, sha256). Returns the payload or None."""
        import hashlib
        import json as _json
        self._check_host(url)
        ext = "pdf" if kind == "pdf" else "html"
        p = os.path.join(ARCHIVE_DIR, f"{self.rid}.{ext}")
        prov = os.path.join(ARCHIVE_DIR, f"{self.rid}.provenance.json")
        if not (os.path.exists(p) and os.path.exists(prov)):
            return None
        with open(prov, encoding="utf-8") as fh:
            meta = _json.load(fh)
        raw = open(p, "rb").read()
        digest = hashlib.sha256(raw).hexdigest()
        if meta.get("sha256") and meta["sha256"] != digest:
            raise FetchError(f"archived fetch for {self.rid} does not match its provenance sha256")
        self.urls.append({"url": url, "mode": "archived", "status": 200, "ok": True, "error": "",
                          "archived_at": meta.get("fetched_at"), "archive_method": meta.get("method"), "sha256": digest})
        return raw if kind == "pdf" else raw.decode(meta.get("encoding", "utf-8"), "replace")

    def rendered(self, url):
        self._check_host(url)
        fr = self.fetcher.rendered(url)
        self.urls.append({"url": url, "mode": "rendered", "status": fr.status, "ok": fr.ok, "error": fr.error})
        if not fr.ok:
            raise FetchError(f"{url}: {fr.error}")
        return fr.rendered

    def chunk(self, locator, text, division, url, language="en", **extra):
        text = clean(text)
        if not text:
            return None
        r = self.row
        c = {"registry_id": self.rid, "branch": r["branch"], "standard_title": r["standard_title"],
             "authority_tier": r["authority_tier"], "scope_caveat": r["scope_caveat"],
             "reception_scope": (r.get("reception_scope") or "").upper(),
             "locator": locator, "division": division, "text": text, "text_hash": sha(text),
             "source_url": url, "language": language}
        c.update(extra)
        return c


class FetchError(Exception):
    pass


class BlockedError(FetchError):
    """The host refused the fetch (403 / bot challenge). Verdict: host."""


class RedirectError(FetchError):
    """The host redirected the ratified URL onto a different host. Verdict: host (the fetcher no
    longer follows it)."""


class RetiredHostError(FetchError):
    """The URL sits on a retired registry host (config.RETIRED_HOSTS). Never requested."""


class HostNotAdmittedError(FetchError):
    """An adapter asked for a URL on a host the row does not admit under R001 (publisher_domain / AC-15)."""


def dehyphenate_chunks(chunks):
    """Post-extraction pass over one standard's chunks: join words split across a line break in every
    chunk text (and in the Synodikon's full_text / withheld spans, so the non-citable check keeps
    matching), using the standard's whole vocabulary as evidence, and recompute text_hash. Returns
    {"stats": per-rule counts, "residue": splits still present, "changed": n_chunks_changed}."""
    vocab_text = "\n".join([c.get("text", "") for c in chunks] + [c.get("full_text", "") for c in chunks if c.get("full_text")])
    stats, residue, changed = {}, [], 0
    for c in chunks:
        new = dehyphenate(c["text"], vocab_text, stats)
        if new != c["text"]:
            c["text"], c["text_hash"] = new, sha(new)
            changed += 1
        if c.get("full_text"):
            c["full_text"] = dehyphenate(c["full_text"], vocab_text, {})
        for sp in c.get("noncitable_spans") or []:
            if isinstance(sp, dict) and sp.get("text"):
                sp["text"] = dehyphenate(sp["text"], vocab_text, {})
        residue.extend(hyphenation_residue(c["text"]))
    return {"stats": stats, "residue": residue, "changed": changed}


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


def lateran_constitutions(ctx):
    """BSR-RC-04 — Fourth Lateran constitutions 1–2 (APP CONFIG lateran_iv_scope = EXTEND_TO_CONSTITUTION_2):
    'Confession of Faith' (Firmiter credimus) and 'On the error of abbot Joachim' (Damnamus ergo), the latter
    carrying the maior dissimilitudo clause. Under any other value only constitution 1 is chunked."""
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    idx = [i for i, (t, x) in enumerate(segs) if t == "strong" and x.strip() == "Confession of Faith"]
    if not idx:
        raise FetchError("Lateran IV 'Confession of Faith' heading not found")
    extend = str(ctx.config.get("lateran_iv_scope") or "").upper() == "EXTEND_TO_CONSTITUTION_2"
    out, n = [], 0
    i = idx[-1] + 1
    while i < len(segs):
        tag, text = segs[i]
        if tag == "strong" or (tag == "a" and text.strip().upper() == "TOP"):
            break
        if tag == "p":
            n += 1
            _emit(ctx, out, f"Constitution 1 (Confession of Faith — Firmiter credimus), paragraph {n}", [text], "paragraph", url)
        i += 1
    notes = ["Constitution 1 (Confession of Faith), Tanner translation, unattributed on page"]
    if extend:
        # the page continues: <a>TOP</a>, <p>2.</p>, <strong>On the error of abbot Joachim</strong>, paragraphs, <a>TOP</a>
        j = next((k for k in range(i, min(i + 6, len(segs))) if segs[k][0] == "strong" and segs[k][1].strip().startswith("On the error of abbot Joachim")), -1)
        if j < 0:
            raise FetchError("Lateran IV constitution 2 heading 'On the error of abbot Joachim' not found")
        m = 0
        for tag, text in segs[j + 1:]:
            if tag == "strong" or (tag == "a" and text.strip().upper() == "TOP"):
                break
            if tag == "p" and not re.fullmatch(r"\d+\.", text.strip()):
                m += 1
                _emit(ctx, out, f"Constitution 2 (On the error of abbot Joachim — Damnamus ergo), paragraph {m}", [text], "paragraph", url)
        notes.append(f"Constitution 2 (Damnamus ergo) chunked as ratified: {m} paragraphs; maior dissimilitudo clause "
                     f"{'present' if any('dissimilitude' in c['text'] or 'unlikeness' in c['text'] or 'dissimilar' in c['text'] for c in out) else 'NOT FOUND'}")
    else:
        notes.append("lateran_iv_scope is not EXTEND_TO_CONSTITUTION_2: constitution 1 only")
    return out, notes


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


RC08_ASSERT = "begotten, not made, consubstantial with the Father"


def vaticannews_creeds(ctx):
    """BSR-RC-08 (NEW in v2.25r3, 2026-09-12): the Apostles' and Nicene Creeds on vaticannews.va, a second Holy
    See publishing outlet distinct from vatican.va (its own row; not folded into BSR-RC-06, not AC-15).
    LOCATOR CAUTION (from the row): the URL slug names the Apostles' Creed but the page carries BOTH creeds under
    one "Credo" heading, and "judge the living and the dead" appears in both — so each creed is its OWN chunk
    with its own locator ("Apostles' Creed" / "Nicene Creed"), and a phrase is asserted only against the named
    creed's chunk, never against the page. The build asserts RC08_ASSERT inside the Nicene chunk alone."""
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    start = next((i for i, (t, x) in enumerate(segs) if t == "h1" and clean(x) == "Credo"), -1)
    if start < 0:
        raise FetchError("vaticannews.va: 'Credo' heading not found")
    out, cur, buf = [], None, []
    for tag, text in segs[start + 1:]:
        t = clean(text)
        if tag == "b" and re.match(r"^The Apostles'? Creed$", t, re.I):
            cur, buf = "Apostles' Creed", []; continue
        if tag == "b" and re.match(r"^The Nicene Creed$", t, re.I):
            if cur and buf:
                _emit(ctx, out, cur, buf, "creed", url)
            cur, buf = "Nicene Creed", []; continue
        if cur and tag == "p":
            buf.append(t)
            if t == "Amen.":
                _emit(ctx, out, cur, buf, "creed", url); cur, buf = None, []
        elif cur and tag not in ("p", "b") and buf:
            break
    if cur and buf:
        _emit(ctx, out, cur, buf, "creed", url)
    locs = {c["locator"]: c for c in out}
    if set(locs) != {"Apostles' Creed", "Nicene Creed"}:
        raise FetchError(f"vaticannews.va Credo: expected exactly the Apostles' and Nicene Creed blocks, got {sorted(locs)}")
    if not contains(locs["Nicene Creed"]["text"], RC08_ASSERT):
        raise FetchError(f"vaticannews.va: assertion {RC08_ASSERT!r} not found in the Nicene Creed block")
    if contains(locs["Apostles' Creed"]["text"], RC08_ASSERT):
        raise FetchError("vaticannews.va: the Nicene assertion phrase leaked into the Apostles' Creed block (segmentation wrong)")
    return out, ["vaticannews.va (publisher_domain) Credo page: Apostles' and Nicene Creeds as two chunks with their own locators; "
                 f"asserted {RC08_ASSERT!r} in the Nicene block only"]


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
    """(cal-1/cal-2 source of BSR-EO-06: OCA church-history summaries. Superseded in v2.25 by ccel_definitions.)"""
    pages = [(f"{OCA}/orthodoxy/the-orthodox-faith/church-history/fifth-century/the-fourth-ecumenical-council", "Church History — Fifth Century"),
             (f"{OCA}/orthodoxy/the-orthodox-faith/church-history/seventh-century/the-sixth-ecumenical-council", "Church History — Seventh Century")]
    out = []
    for url, sec in pages:
        title, buf = _oca_page(ctx, url, sec)
        _emit(ctx, out, f'{sec} — "{title}"', buf, "article", url)
    return out, ["OCA history pages for Chalcedon and Constantinople III as cited by released cells; newadvent.org is lineage only"]


CCEL_C3 = "https://www.ccel.org/ccel/schaff/npnf214.xiii.x.html"


def ccel_definitions(ctx):
    """BSR-EO-06 (v2.25) — the Definitions of Faith of Chalcedon (451) and Constantinople III (680–681),
    NPNF2-14 (Percival) on ccel.org. The ratified canonical_url is the Chalcedon chapter page; the
    Constantinople III definition is the sibling chapter page named in the standard title.

    Hazard (Gate 7 host verification): each page interleaves Percival's editorial apparatus — page-number
    anchors, footnote markers, marginal notes, and a 'Notes.' section (Anatolius, Hefele) — with the
    conciliar text. Everything under the Notes heading and every footnote/marginal block is EXCLUDED; the
    inline Greek glosses are moved to a parallel witness so no chunk mixes languages."""
    from bs4 import BeautifulSoup
    pages = [(ctx.row["canonical_url"], "Definition of Faith, Council of Chalcedon (451)"),
             (CCEL_C3, "Definition of Faith, Third Council of Constantinople (680–681)")]
    out, notes = [], []
    for url, title in pages:
        html = ctx.html(url)
        soup = BeautifulSoup(html, "lxml")
        content = soup.find("div", class_="book-content") or soup
        removed = 0
        for junk in content.select("sup.Note, span.mnote, span.pb, a.page, span.Footnote, div.footnotes, a.Note, a.NoteRef"):
            junk.decompose(); removed += 1
        greek_removed = []
        n = 0
        for p in content.find_all("p"):
            txt = clean(p.get_text(" "))
            if not txt:
                continue
            low = txt.casefold()
            if low in ("notes.", "notes"):
                break                       # editorial notes follow: excluded
            if txt.startswith("(") and ("Concilia" in txt or "Labbe" in txt or "Found in the Acts" in txt or "col." in txt):
                continue                    # Percival's source reference line, not the council's text
            if low.startswith("the definition of faith") and len(txt) < 80:
                continue                    # the chapter title
            if p.find_parent(class_="footnotes") is not None:
                continue
            eng, foreign = strip_foreign_parentheticals(txt)
            greek_removed.extend(foreign)
            n += 1
            c = ctx.chunk(f"{title}, paragraph {n}", eng, "paragraph", url,
                          parallel_witness=({"language": "grc", "glosses": foreign} if foreign else None))
            if c:
                out.append(c)
        notes.append(f"{title}: {n} paragraphs; {removed} editorial/footnote/page blocks excluded; {len(greek_removed)} Greek glosses moved to parallel witness")
    return out, notes


def _html_sections(ctx, html, url, label_prefix=""):
    """Generic h1/h2/h3-sectioned page → one chunk per section."""
    out, cur, buf = [], None, []
    for tag, text in segments(html):
        t = clean(text)
        if tag in ("h1", "h2", "h3"):
            if cur and buf:
                _emit(ctx, out, f'{label_prefix}"{cur}"', buf, "section", url)
            cur, buf = t, []
        elif cur and tag in ("p", "li", "blockquote", "em", "strong", "b", "i", "h4"):
            buf.append(t)
    if cur and buf:
        _emit(ctx, out, f'{label_prefix}"{cur}"', buf, "section", url)
    return out


def goarch_single(ctx):
    """(RETIRED 2026-09-12 with the host: goarch.org is never requested — config.RETIRED_HOSTS; BSR-EO-03 now
    builds as HOST_RETIRED and BSR-EO-07 moved to acrod.org. Kept for the record.)
    BSR-EO-07 / BSR-EO-03 — ONE ratified URL on goarch.org, never crawled. The host answers automated
    fetches with a Cloudflare managed challenge (HTTP 403, cf-mitigated: challenge) on every route tried
    in cal-3 (plain requests under five user agents, Playwright headless and headed, the desktop app's
    own Chromium), so the order is: (1) a committed one-time archived fetch with provenance, if present;
    (2) one plain fetch of the ratified URL; (3) one headless rendered attempt; then BLOCKED. No other
    path on the host is ever requested."""
    url = ctx.row["canonical_url"]
    html = ctx.archived(url)
    mode = "archived"
    if html is None:
        try:
            html = ctx.html(url)
            mode = "http"
        except BlockedError as e:
            ctx.log(f"   plain fetch blocked ({str(e)[:80]}); one rendered attempt")
            fr = ctx.fetcher.rendered(url)
            ctx.urls.append({"url": url, "mode": "rendered", "status": fr.status, "ok": fr.ok, "error": fr.error})
            body = (fr.rendered or {}).get("body", "")
            if not fr.ok or "security verification" in body.casefold() or "just a moment" in body.casefold():
                raise BlockedError(f"goarch.org: Cloudflare managed challenge on the ratified URL (plain HTTP 403; rendered "
                                   f"HTTP {fr.status}, body {len(body)} chars). Verdict: HOST. No crawl attempted.")
            blocks = fr.rendered.get("blocks") or []
            html = "".join(f"<{b['tag']}>{b['text']}</{b['tag']}>" for b in blocks)
            mode = "rendered"
    out = _html_sections(ctx, html, url)
    if ctx.rid == "BSR-EO-07":
        creed = [c for c in out if "creed" in c["locator"].casefold() or "symbol" in c["locator"].casefold()]
        anaph = [c for c in out if "anaphora" in c["locator"].casefold()]
        notes = [f"fetched via {mode}; {len(out)} sections; anaphora sections {len(anaph)}; creed sections {len(creed)}",
                 "Creed on this page reads 'Creator of heaven and earth' where OCA/Antiochian read 'Maker' — phrases are cut from this file"
                 if any("Creator of heaven and earth" in c["text"] for c in out) else "'Creator of heaven and earth' NOT found on page — check the split"]
    else:
        notes = [f"fetched via {mode}; {len(out)} sections"]
    return out, notes


# ------------------------------------------------------------------ Synodikon guard (BSR-EO-09, FIX 0)
# The marker must not itself carry the word (or the belt-and-braces rule would re-match it).
ANATHEMA_MARKER = "[withheld: condemnation formula, non-citable]"
_ANATHEMA_SPANS = [
    # "To those who dare to say that … are not one God: ANATHEMA!" — the anathematised proposition and its verdict
    re.compile(r"To those (?:who|that)\b(?:(?!To those (?:who|that)).)*?\bANATHEMA!", re.S),
    # the people's response
    re.compile(r"People:\s*(?:Anathema!\s*)+", re.I),
    # belt and braces: any remaining sentence that still carries the word in any form (anathematize …)
    re.compile(r"[^.!?\[\]]*\banathema\w*[^.!?\[\]]*[.!?]?", re.I),
]


def synodikon_guard(text):
    """Withhold every anathema-framed span from the agent-visible text. Returns (visible, withheld).
    An anathema names a proposition ONLY to condemn it; quoting its inner clause alone inverts the
    doctrine ("the Son of God … [is] not one in essence with the Father"). The visible text keeps a
    marker where each span stood so the locator can see that something was withheld; the withheld
    spans travel with the chunk under `noncitable_spans` and guards.check_noncitable refuses any
    phrase that lies inside one, even if an agent reconstructed it from memory."""
    withheld = []
    visible = clean(text)

    def take(m):
        span = clean(m.group(0))
        if span and span != ANATHEMA_MARKER:
            withheld.append({"kind": "anathema", "text": span})
            return f" {ANATHEMA_MARKER} "
        return m.group(0)
    for rx in _ANATHEMA_SPANS:
        visible = rx.sub(take, visible)
    visible = re.sub(r"(\s*" + re.escape(ANATHEMA_MARKER) + r"\s*){2,}", f" {ANATHEMA_MARKER} ", visible)
    return clean(visible), withheld


def _pdf_pages_text(ctx, url, pages_filter=None):
    """PDF → list of page texts (running headers and bare page numbers dropped, hyphenation repaired)."""
    raw = ctx.pdf(url)
    pages = raw.split("\f")
    out = []
    for i, p in enumerate(pages):
        if pages_filter and not pages_filter(i):
            continue
        lines = []
        for l in p.split("\n"):
            s_ = l.strip()
            if not s_:
                lines.append("")
                continue
            if re.fullmatch(r"\d{1,3}", s_) or re.match(r"^(APPENDIX|ANEXA) [IVX]+", s_):
                continue
            lines.append(s_)
        out.append(pdf_repair("\n".join(lines)))
    return out


def roea_synodikon(ctx):
    """BSR-EO-09 — the Synodikon of Orthodoxy, ROEA text-layer PDF, six numbered sections (one per page),
    section 2 titled 'The Symbol of Faith'. BLOCKING GUARD applied per section: anathema-framed spans are
    withheld from the citable text (see synodikon_guard). Section 2, the Creed, carries no anathema and is
    the safe region."""
    url = ctx.row["canonical_url"]
    pages = _pdf_pages_text(ctx, url)
    out, n_spans, notes = [], 0, []
    for i, page in enumerate(pages, 1):
        body = re.sub(r"^\s*\d\s*\n", "", page, count=1)            # the section number that opens each page
        paras = [clean(x) for x in re.split(r"\n\s*\n", body) if clean(x)]
        if not paras:
            continue
        title = None
        if paras and len(paras[0].split()) <= 6 and not paras[0].endswith((".", "!", ":")):
            title = paras[0]
            paras = paras[1:]
        full = " ".join(paras)
        visible, withheld = synodikon_guard(full)
        n_spans += len(withheld)
        loc = f"Synodikon §{i}" + (f" — {title}" if title else "")
        c = ctx.chunk(loc, visible, "section", url, full_text=full, noncitable_spans=withheld,
                      guard=("anathema-framed spans withheld" if withheld else "no anathema in this section"))
        if c:
            out.append(c)
    creed = [c for c in out if "Symbol of Faith" in c["locator"]]
    notes.append(f"{len(out)} sections; {n_spans} anathema-framed spans withheld as non-citable; "
                 f"section 2 'The Symbol of Faith' {'present, no spans withheld' if creed and not creed[0]['noncitable_spans'] else 'CHECK'}")
    if any("anathema" in c["text"].casefold().replace(ANATHEMA_MARKER.casefold(), "") for c in out):
        raise FetchError("Synodikon guard failed: the word 'anathema' survives in a citable text")
    return out, notes


def roea_basil(ctx):
    """BSR-EO-08 — Prayers of the Liturgy of St Basil (ROEA, Appendix VII), bilingual PDF: English on the
    odd-numbered pages, Romanian ('Anexa VII') on the even. English pages only; divisions are the prayer
    headings the book itself uses (a heading is followed by its '(See page N)' cross-reference); long
    prayers are split into parts at paragraph boundaries. This translation reads 'unseen' and 'immutable'."""
    url = ctx.row["canonical_url"]
    pages = _pdf_pages_text(ctx, url, pages_filter=lambda i: i % 2 == 0)
    text = "\n".join(pages)
    lines = text.split("\n")
    divisions, cur, buf = [], "Prayers of the Liturgy of St Basil — opening rubrics", []
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        m = re.match(r"^(.*?)\s*\(See page \d+\)\s*$", l)
        if m and m.group(1):
            divisions.append((cur, buf)); cur, buf = m.group(1).strip(), []; i += 1; continue
        if nxt.startswith("(See page") and l and not l.endswith((".", ",", ";", ":")) and len(l.split()) <= 12:
            divisions.append((cur, buf)); cur, buf = l, []; i += 2; continue
        buf.append(l)
        i += 1
    divisions.append((cur, buf))
    out = []
    for title, blines in divisions:
        paras = [clean(x) for x in re.split(r"\n\s*\n", "\n".join(blines)) if clean(x)]
        if not paras:
            continue
        parts, part, size = [], [], 0
        for p in paras:
            if part and size + len(p) > 2200:
                parts.append(part); part, size = [], 0
            part.append(p); size += len(p)
        if part:
            parts.append(part)
        for k, part in enumerate(parts, 1):
            loc = title if len(parts) == 1 else f"{title}, part {k}"
            _emit(ctx, out, loc, part, "prayer", url)
    words = {w: sum(len(re.findall(r"\b" + w + r"\b", c["text"], re.I)) for c in out)
             for w in ("unseen", "immutable", "invisible", "ineffable", "unchangeable", "incomprehensible", "infinite")}
    notes = [f"{len(pages)} English pages; {len(out)} prayer chunks across {len(divisions)} headings",
             "word check: " + ", ".join(f"{w}={n}" for w, n in words.items())]
    return out, notes


HOLYCOUNCIL = "https://www.holycouncil.org"


def _crete_rest(soup):
    ol = soup.find("ol")
    return [clean(li.get_text(" ", strip=True)) for li in ol.find_all("li", recursive=False)] if ol else []


def _crete_encyclical(soup):
    """(section, paragraph number, text) triples: sections from roman-numeral <strong> headings,
    paragraphs from 'N.' leads; unnumbered paragraphs continue the current number; the preamble and the
    closing doxology are their own divisions."""
    items, section, num, buf = [], "Preamble", None, []
    started = False
    for p in soup.find_all("p"):
        t = clean(p.get_text(" ", strip=True))
        if not t:
            continue
        if not started:
            if re.match(r"^(ENCYCLICAL|ΕΓΚΥΚΛΙΟΣ)", t, re.I):
                started = True
            continue
        if t == "***":
            continue
        m = re.match(r"^([IVX]+)\.\s+(.+)$", t)
        if m and len(t) < 120:
            if buf:
                items.append((section, num, " ".join(buf))); buf = []
            section, num = f"{m.group(1)}. {m.group(2)}", None
            continue
        m = re.match(r"^(\d{1,2})\.\s+(.+)$", t, re.S)
        if m:
            if buf:
                items.append((section, num, " ".join(buf))); buf = []
            num = int(m.group(1)); buf.append(m.group(2))
            continue
        if t.startswith("†") or re.match(r"^Delegation of", t):
            break
        buf.append(t)
    if buf:
        items.append((section, num, " ".join(buf)))
    return items


def crete_2016(ctx):
    """BSR-EO-10 — Holy and Great Council of Crete (2016): 'Relations of the Orthodox Church with the Rest
    of the Christian World' (flat ¶1–24) and the Encyclical (sections I–VII, ¶1–20, plus preamble and closing
    doxology). The English text is chunked for citation; the Greek text (the '_el' page of each document)
    is fetched separately and kept beside each chunk as a parallel witness — never in the same chunk."""
    from bs4 import BeautifulSoup
    rest_url = ctx.row["canonical_url"]
    enc_url = f"{HOLYCOUNCIL}/encyclical-holy-council"
    out, notes = [], []
    en = BeautifulSoup(ctx.html(rest_url), "lxml")
    try:
        el = BeautifulSoup(nfc(ctx.html(rest_url + "_el")), "lxml")
        el_paras = _crete_rest(el)
    except FetchError as e:
        el_paras = []; notes.append(f"Greek parallel for the Relations document unavailable: {e}")
    paras = _crete_rest(en)
    for i, t in enumerate(paras, 1):
        c = ctx.chunk(f"Relations of the Orthodox Church with the Rest of the Christian World, ¶{i}", t, "paragraph", rest_url,
                      parallel_witness=({"language": "el", "text": el_paras[i - 1]} if i - 1 < len(el_paras) else None))
        if c:
            out.append(c)
    notes.append(f"Relations document: {len(paras)} numbered paragraphs (English); Greek parallel for {min(len(paras), len(el_paras))}")
    en2 = BeautifulSoup(ctx.html(enc_url), "lxml")
    try:
        el2 = BeautifulSoup(nfc(ctx.html(enc_url + "_el")), "lxml")
        el_items = {n: t for _, n, t in _crete_encyclical(el2) if n is not None}
    except FetchError as e:
        el_items = {}; notes.append(f"Greek parallel for the Encyclical unavailable: {e}")
    items = _crete_encyclical(en2)
    for section, num, t in items:
        if num is None:
            loc = f"Encyclical, {section}" if section == "Preamble" else f"Encyclical, {section} (closing)"
        else:
            loc = f"Encyclical, {section}, ¶{num}"
        c = ctx.chunk(loc, t, "paragraph", enc_url,
                      parallel_witness=({"language": "el", "text": el_items[num]} if num in el_items else None))
        if c:
            out.append(c)
    notes.append(f"Encyclical: {len(items)} divisions; sections {sorted({s_.split('.')[0] for s_, _, _ in items})}")
    return out, notes


def antioch_witness(ctx):
    """BSR-EO-11 — WITNESS ONLY. An unsigned article on antiochpatriarchate.org quoting the Chalcedon clause in
    English with the Greek and the Latin inline in the same sentence. The quotation is chunked as English
    only; the Greek and Latin groups are moved to a parallel witness so no candidate mixes languages. The
    row is flagged witness in the registry (tier 'CONCILIAR (witness; translation)') and never controls."""
    from bs4 import BeautifulSoup
    url = ctx.row["canonical_url"]
    soup = BeautifulSoup(ctx.html(url), "lxml")
    title = soup.find("strong", string=re.compile(r"Whose goings forth"))
    if title is None:
        raise FetchError("Antioch article title not found")
    paras = []
    for sib in title.find_all_next():
        if sib.name == "div" and "more" in (sib.get("class") or []):
            break
        if sib.name == "p":
            t = clean(sib.get_text(""))          # inline spans continue mid-word ('a' + 'nd assumed')
            if t:
                paras.append(t)
    quote = [p for p in paras if "Council of Chalcedon" in p or p.startswith("“") or "inconfusedly" in p]
    body = [p for p in paras if p not in quote]
    out = []
    _emit(ctx, out, "Article (English), paragraphs 1–%d" % len(body), body, "article", url)
    for p in quote:
        if "inconfusedly" in p or p.startswith("“"):
            eng, foreign = strip_foreign_parentheticals(p)
            c = ctx.chunk("Chalcedon clause as quoted (English)", eng, "quotation", url,
                          parallel_witness={"language": "grc+la", "glosses": foreign}, witness=True)
            if c:
                out.append(c)
    for c in out:
        c["witness"] = True
    mixed = [c["locator"] for c in out if re.search(r"[Ͱ-Ͽἀ-῿]", c["text"])]
    return out, [f"{len(out)} chunks; witness only; Greek/Latin groups moved out of the citable text; mixed-language chunks: {mixed or 'none'}"]


def sparta_creed_greek(ctx):
    """BSR-EO-12 — the Nicene-Constantinopolitan Creed in polytonic Greek, twelve numbered articles, on
    immspartis.gr. Normalised to NFC exactly once, here, at fetch; the twelve articles are the divisions.
    The page also carries the Creed in fourteen other languages; only the Greek is chunked."""
    url = ctx.row["canonical_url"]
    html = nfc(ctx.html(url))
    segs = [(t, clean(x)) for t, x in html_segments(html)]
    start = next((i for i, (t, x) in enumerate(segs) if "ΤΟ ΣΥΜΒΟΛΟΝ ΤΗΣ ΠΙΣΤΕΩΣ" in x), -1)
    if start < 0:
        raise FetchError("Greek Creed heading 'ΤΟ ΣΥΜΒΟΛΟΝ ΤΗΣ ΠΙΣΤΕΩΣ' not found")
    out, expect = [], 1
    for tag, x in segs[start + 1:]:
        if "THE CREED" in x or "Αγγλικά" in x:
            break
        m = re.match(r"^(\d{1,2})\.\s*(.+)$", x, re.S)
        if m and int(m.group(1)) == expect:
            art = m.group(2).strip()
            c = ctx.chunk(f"Σύμβολον τῆς Πίστεως, ἄρθρον {expect} (Symbol of Faith, article {expect})", art, "article", url, language="el",
                          polytonic=has_polytonic(art))
            if c:
                out.append(c)
            expect += 1
    article_segs = [x for _, x in segs[start + 1:start + 14] if re.match(r"^\d{1,2}\.\s", x)]
    poly_in = len(re.findall(r"[ἀ-῿]", "".join(article_segs)))
    poly_out = len(re.findall(r"[ἀ-῿]", "".join(c["text"] for c in out)))
    import unicodedata
    nfc_ok = all(unicodedata.normalize("NFC", c["text"]) == c["text"] for c in out)
    notes = [f"{len(out)} of 12 articles; polytonic code points in source region {poly_in}, in stored chunks {poly_out}; "
             f"stored text is NFC: {nfc_ok}; every article polytonic: {all(c.get('polytonic') for c in out)}"]
    if len(out) != 12:
        raise FetchError(f"expected 12 Greek articles, found {len(out)}")
    return out, notes


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


AN03_ASSERT = "Whosoever will be saved: before all things it is necessary"


def athanasian_creed_cofe(ctx):
    """BSR-AN-03 (v2.25r3, MIGRATED 2026-09-12 under AC-02 MIGRATE_WHERE_OFFICIAL): the Athanasian Creed on
    the Church of England's own BCP page, publisher_domain churchofengland.org; ccel.org is RETIRED for this
    row. fetch_mode is RENDERED — a plain fetch of the URL returns navigation chrome with no creed text
    (verified 2026-09-12), so the page is rendered with Playwright and only the verse paragraphs between the
    QUICUNQUE VULT heading and the Gloria's "Amen." are chunked: the "At Morning Prayer" rubric above the
    heading and the Crown/CUP provenance line below the Gloria are not creed text and never enter the chunk.
    The build asserts the row's opening words (AN03_ASSERT) against the chunk under the pipeline's own
    normalisation (the page prints WHOSOEVER in capitals). The churchofengland.org BCP 1662 PDF is disallowed
    by robots.txt and is NOT a fallback: a failure here is an honest empty for the row."""
    url = ctx.row["canonical_url"]
    blocks = ctx.rendered(url).get("blocks") or []
    start = next((i for i, b_ in enumerate(blocks) if b_["text"].strip().upper().startswith("QUICUNQUE VULT")), -1)
    if start < 0:
        raise FetchError("churchofengland.org Athanasian Creed: QUICUNQUE VULT heading not found in the rendered page "
                         f"({len(blocks)} blocks) — chrome only?")
    verses = []
    for b_ in blocks[start + 1:]:
        t = clean(b_["text"])
        if b_["tag"].startswith("h") or t.startswith("Text from The Book of Common Prayer"):
            break
        if b_["tag"] == "p" and t:
            verses.append(t)
        if t.endswith("world without end. Amen."):
            break
    if len(verses) < 40:
        raise FetchError(f"churchofengland.org Athanasian Creed: expected ~44 verse paragraphs plus the Gloria, found {len(verses)}")
    text = join(verses)
    if not contains(text, AN03_ASSERT):
        raise FetchError(f"churchofengland.org Athanasian Creed: assertion {AN03_ASSERT!r} not found in the rendered creed text")
    out = []
    # the page prints the creed as unnumbered paragraphs (some carry two traditional verses), so the locator names the
    # creed and its BCP place, never a verse count the page does not give
    _emit(ctx, out, "Athanasian Creed (Quicunque Vult), At Morning Prayer, BCP", verses, "creed", url)
    return out, [f"churchofengland.org (publisher_domain; RENDERED) — {len(verses)} verse paragraphs incl. the Gloria; rubric and provenance line excluded; "
                 f"asserted {AN03_ASSERT!r} (normalised: the page prints WHOSOEVER)"]


CCEL_ATHANASIAN = "https://ccel.org/ccel/creeds/athanasian.creed.html"


def athanasian_creed_ccel(ctx):
    """(v2.25r2 adapter for BSR-AN-03 — the Athanasian Creed on ccel.org. RETIRED 2026-09-12 with the row's
    migration to churchofengland.org (v2.25r3, AC-02): ccel.org is no longer the row's host and the host guard
    refuses it. Kept for the record; not dispatched.)"""
    url = str(ctx.config.get("athanasian_text_witness") or CCEL_ATHANASIAN)
    segs = segments(ctx.html(url))
    verses = [clean(x) for tag, x in segs if tag == "p" and re.match(r"^\d{1,2}\.\s+\S", clean(x))]
    if len(verses) < 40:
        raise FetchError(f"ccel Athanasian Creed: expected ~44 numbered verses, found {len(verses)}")
    out = []
    _emit(ctx, out, f"Athanasian Creed (Quicunque Vult), verses 1–{len(verses)}", verses, "creed", url)
    return out, [f"ccel.org (publisher_domain) — {len(verses)} numbered verses in one division; the churchofengland.org text is the Gate 7 migration target, not fetched"]


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


def gmc_what_we_believe(ctx):
    """BSR-MW-03 — Global Methodist Church, 'What We Believe' on the APEX host globalmethodist.org. The
    ratified URL is fetched byte for byte; the fetcher no longer follows the host's redirect onto
    www.globalmethodist.org (a different site, which 404s). Articles are split on their headings."""
    from bs4 import BeautifulSoup
    url = ctx.row["canonical_url"]
    html = ctx.html(url)
    soup = BeautifulSoup(html, "lxml")
    out, cur, buf = [], None, []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li", "blockquote"]):
        t = clean(el.get_text(" ", strip=True))
        if not t:
            continue
        if el.name.startswith("h") and re.match(r"^(Article\s+[IVXLC0-9]+|[IVX]+\.)\b", t):
            if cur and buf:
                _emit(ctx, out, cur, buf, "article", url)
            cur, buf = t, []
        elif el.name.startswith("h"):
            if cur and buf:
                _emit(ctx, out, cur, buf, "article", url)
            cur, buf = t, []
        elif cur:
            buf.append(t)
    if cur and buf:
        _emit(ctx, out, cur, buf, "article", url)
    good = sum(1 for c in out if "infinite power, wisdom, and good" in c["text"])
    return out, [f"{len(out)} sections; Article I 'of infinite power, wisdom, and good' (not 'goodness') found in {good} chunk(s)"]


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


# =============================================================== 2026-09-12 re-hosted / new rows
def _caps_heading(t):
    return bool(re.fullmatch(r"[A-Z][A-Z'’\-]*(?:\s+[A-Z][A-Z'’\-]*){0,7}", t)) and len(t) <= 60


def _liturgy_notes(rid, out, four=("ineffable", "inconceivable", "invisible", "incomprehensible")):
    anaph = [c for c in out if "anaphora" in c["locator"].casefold()]
    creed = [c for c in out if re.search(r"creed|symbol of faith", c["locator"], re.I)]
    notes = [f"{len(out)} divisions (the page's own capitalised headings); anaphora divisions {len(anaph)}; creed divisions {len(creed)}"]
    if anaph:
        present = [w for w in four if any(re.search(r"\b" + w + r"\b", c["text"], re.I) for c in anaph)]
        notes.append(f"anaphora adjectives present: {', '.join(present) or 'none'}")
    if creed:
        notes.append("Creed reads 'Creator of heaven and earth'" if any("Creator of heaven and earth" in c["text"] for c in creed)
                     else "Creed: 'Creator of heaven and earth' NOT found — check the split")
    return notes


def acrod_liturgy(ctx):
    """BSR-EO-07 (v2.25r2) — the Divine Liturgy of St John Chrysostom on acrod.org (American Carpatho-Russian
    Orthodox Diocese). Plain HTML, no challenge. The page's own capitalised headings (THE SYMBOL OF FAITH,
    THE ANAPHORA, …) are the divisions; priest/people lines are inline in the paragraphs. Replaces the
    retired goarch.org host, which is never requested."""
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    start = next((i for i, (tag, x) in enumerate(segs) if tag == "strong" and "Divine Liturgy of St. John Chrysostom" in clean(x)), -1)
    if start < 0:
        raise FetchError("ACROD: 'The Divine Liturgy of St. John Chrysostom' title not found")
    out, cur, buf = [], None, []
    for tag, text in segs[start + 1:]:
        t = clean(text)
        if not t:
            continue
        if tag == "p" and _caps_heading(t):
            if cur and buf:
                _emit(ctx, out, cur, buf, "division", url)
            cur, buf = t, []
            continue
        if cur and tag in ("p", "em", "strong", "i", "b", "li", "blockquote"):
            buf.append(t)
    if cur and buf:
        _emit(ctx, out, cur, buf, "division", url)
    return out, ["fetched via http (acrod.org, publisher_domain)"] + _liturgy_notes(ctx.rid, out)


def goarchdiocese_liturgy(ctx):
    """BSR-EO-14 (v2.25r2, NEW) — the Divine Liturgy of St John Chrysostom on goarchdiocese.ca (Greek Orthodox
    Archdiocese of Canada; its own WordPress, not the GOARCH platform). Divisions are the page's capitalised
    <span> headings (THE CREED, THE HOLY ANAPHORA, …); the <strong> speaker labels (Priest:, People:) are
    folded into the paragraph that follows them. The text-layer PDF the row names is fetched once as the
    durability witness and compared on the anaphora wording; it is not chunked (same text, second locator
    would only split the locator's attention). Wording differs from BSR-EO-07 ('beyond comprehension',
    'beyond understanding'); a cell quotes whichever file it cites."""
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf, label = [], None, [], None
    for tag, text in segs:
        t = clean(text)
        if not t:
            continue
        if tag == "span" and _caps_heading(t):
            if cur and buf:
                _emit(ctx, out, cur, buf, "division", url)
            cur, buf, label = t, [], None
            continue
        if not cur:
            continue
        if tag == "strong" and re.match(r"^(Priest|People|Deacon|Reader|Choir|Bishop|Celebrant)\b.*:$", t):
            label = t
            continue
        if tag in ("p", "em", "i", "b", "li", "blockquote", "strong"):
            buf.append(f"{label} {t}" if label else t)
            label = None
    if cur and buf:
        _emit(ctx, out, cur, buf, "division", url)
    notes = ["fetched via http (goarchdiocese.ca, publisher_domain)"] + _liturgy_notes(ctx.rid, out, four=("ineffable", "beyond comprehension", "invisible", "beyond understanding"))
    m = re.search(r"(/wp-content/\S+?\.pdf)", ctx.row.get("fetch_mode", ""))
    if m:
        pdf_url = urljoin(url, m.group(1))
        try:
            pdf = ctx.pdf(pdf_url)
            key = "beyond comprehension, invisible, beyond understanding"
            notes.append(f"text-layer PDF fetched as durability witness ({pdf.count(chr(12)) + 1} pages): anaphora wording "
                         f"{'matches the page' if normalize(key) in normalize(pdf) else 'NOT found in the PDF'}; not chunked")
        except FetchError as e:
            notes.append(f"text-layer PDF witness unavailable: {e}")
    return out, notes


def newadvent_constantinople_iii(ctx):
    """BSR-EO-13 (v2.25r2, NEW, LINEAGE / TRANSLATION_WITNESS) — the Third Council of Constantinople on
    newadvent.org (Percival's NPNF2-14 text, transcribed). Only 'The Definition of Faith' (Session XVIII)
    is chunked, paragraph by paragraph; the letters, session extracts and the sentence are not the
    council's definition. Greek glosses in parentheses move to a parallel witness. The row is a witness
    (never controls a cell); it repairs released cell Q-034."""
    from bs4 import BeautifulSoup
    url = ctx.row["canonical_url"]
    soup = BeautifulSoup(ctx.html(url), "lxml")
    h2 = next((h for h in soup.find_all("h2") if clean(h.get_text(" ")) == "The Definition of Faith"), None)
    if h2 is None:
        raise FetchError("newadvent 3813: 'The Definition of Faith' heading not found")
    out, n, greek = [], 0, []
    for el in h2.find_all_next():
        if el.name in ("h1", "h2"):
            break
        if el.name != "p":
            continue
        txt = clean(el.get_text(""))
        if not txt or (txt.startswith("(") and ("Concilia" in txt or "Found in the Acts" in txt or "col." in txt)):
            continue
        if re.fullmatch(r"[.,;:\s]+", txt):
            continue
        eng, foreign = strip_foreign_parentheticals(txt)
        greek.extend(foreign)
        if not eng:
            continue
        n += 1
        c = ctx.chunk(f"Definition of Faith (Session XVIII), paragraph {n}", eng, "paragraph", url,
                      parallel_witness=({"language": "grc", "glosses": foreign} if foreign else None), witness=True)
        if c:
            out.append(c)
    for c in out:
        c["witness"] = True
    return out, [f"Definition of Faith only: {n} paragraphs; {len(greek)} Greek glosses moved to parallel witness; witness row (TRANSLATION_WITNESS) — never controls a cell"]


GMC_HEAD = re.compile(r"^Article\s+([IVXL]+)\s+[-–—]\s+(.+)$")
GMC_UNNUMBERED = ("Of Sanctification (from the Methodist Protestant Discipline)", "Of the Duty of Christians to the Civil Authority")


def gmc_bdd_2024(ctx):
    """BSR-MW-03 (v2.25r2) — the Global Methodist Church's 2024 Book of Doctrines and Discipline, a text-layer
    PDF on the church's controlled storage (irp.cdn-website.com/1876eae9/, admitted under AC-15: the row note
    opens `LINKED FROM: https://www.globalmethodist.org/our-beliefs---governance`). Chunked as ratified —
    'Articles of Religion, Article I onward' (¶106.1, the Twenty-Five Articles plus the two 1939 additions)
    and ¶106.2, the Confession of Faith of the Evangelical United Brethren Church, sixteen articles — one
    chunk per article, headings as printed ('Article I - Of Faith in the Holy Trinity'). The creeds of ¶105
    are not in the ratified scope. Article I reads 'of infinite power, wisdom, and good' (not 'goodness')."""
    url = ctx.row["canonical_url"]
    pages = ctx.pdf(url).split("\f")
    start = next((i for i, p in enumerate(pages) if re.search(r"1\.\s+THE ARTICLES OF RELIGION", p)), -1)
    if start < 0:
        raise FetchError("GMC BDD 2024: '1. THE ARTICLES OF RELIGION' not found")
    end = next((i for i in range(start + 1, len(pages)) if re.search(r"¶\s*107\.", pages[i])), len(pages) - 1)
    lines = []
    for p in pages[start:end + 1]:
        for l in p.split("\n"):
            s_ = l.strip()
            if not s_ or re.fullmatch(r"\d{1,3}", s_) or s_.startswith("2024 Book of Doctrines and Discipline") or s_ == "Go to Previous Page":
                continue
            lines.append(s_)
    out, doc, cur, buf = [], None, None, []

    def flush():
        if doc and cur and buf:
            _emit(ctx, out, f"{doc}, {cur}", buf, "article", url)
    for l in lines:
        if re.match(r"^1\.\s+THE ARTICLES OF RELIGION", l):
            flush(); doc, cur, buf = "Articles of Religion", None, []; continue
        if re.match(r"^2\.\s+THE CONFESSION OF FAITH", l):
            flush(); doc, cur, buf = "Confession of Faith (Evangelical United Brethren)", None, []; continue
        if re.match(r"^¶\s*107\.", l):
            flush(); cur = None; break
        if l.startswith("["):                       # the Uniting Conference notes: not article text
            flush(); cur, buf = None, []; continue
        m = GMC_HEAD.match(l)
        if m or l in GMC_UNNUMBERED:
            flush(); cur, buf = l, []; continue
        if cur:
            buf.append(l)
    flush()
    good = sum(1 for c in out if "infinite power, wisdom, and good;" in c["text"] or "infinite power, wisdom, and good " in c["text"])
    goodness = sum(1 for c in out if "wisdom, and goodness" in c["text"])
    aor = sum(1 for c in out if c["locator"].startswith("Articles of Religion"))
    return out, [f"PDF pages {start + 1}–{end + 1}: {aor} Articles of Religion chunks (incl. the two 1939 additions) and {len(out) - aor} Confession of Faith chunks",
                 f"Article I 'of infinite power, wisdom, and good' found in {good} chunk(s); 'wisdom, and goodness' in {goodness} chunk(s) (must be 0)",
                 f"hyphenation at extraction: {getattr(ctx, 'hyphenation', {})}"]


# =============================================================== dispatch
ADAPTERS = {
    "BSR-RC-01": ccc_section_two, "BSR-RC-02": dei_filius_latin, "BSR-RC-03": dei_filius_ewtn,
    "BSR-RC-04": lateran_constitutions, "BSR-RC-06": vatican_creeds, "BSR-RC-07": compendium, "BSR-RC-08": vaticannews_creeds,
    "BSR-EO-01": oca_symbol_of_faith, "BSR-EO-02": oca_holy_trinity, "BSR-EO-03": goarch_single,
    "BSR-EO-04": philaret, "BSR-EO-05": dositheus, "BSR-EO-06": ccel_definitions,
    "BSR-EO-07": acrod_liturgy, "BSR-EO-08": roea_basil, "BSR-EO-09": roea_synodikon,
    "BSR-EO-10": crete_2016, "BSR-EO-11": antioch_witness, "BSR-EO-12": sparta_creed_greek,
    "BSR-EO-13": newadvent_constantinople_iii, "BSR-EO-14": goarchdiocese_liturgy,
    "BSR-LU-01": book_of_concord, "BSR-LU-03": small_catechism_cph,
    "BSR-RP-01": wcf_opc, "BSR-RP-02": wsc_opc, "BSR-RP-03": wlc_opc, "BSR-RP-04": pcusa_book_of_confessions,
    "BSR-RP-05": heidelberg_crcna, "BSR-RP-06": belgic_crcna,
    "BSR-AN-01": thirty_nine_articles, "BSR-AN-02": bcp_catechism_1662, "BSR-AN-03": athanasian_creed_cofe,
    "BSR-AN-04": tec_outline_of_faith, "BSR-AN-05": acna_to_be_a_christian,
    "BSR-BA-01": bfm2000, "BSR-BA-02": london_1689_ch2, "BSR-BA-03": abc_usa_10facts,
    "BSR-MW-01": umc_articles, "BSR-MW-02": umc_eub_confession, "BSR-MW-03": gmc_bdd_2024, "BSR-MW-04": wesleyan_articles,
    "BSR-MA-01": mennonite_1995, "BSR-MA-02": dordrecht,
}

# Rows with no text corpus BY POLICY (recorded in the manifest, never chunked). A row whose host is
# unavailable is no longer listed here: cal-1/cal-2 carried BSR-MW-03 as a hard-coded
# UNAVAILABLE_ON_RATIFIED_DOMAIN entry, so the ratified URL was never actually requested at build
# time — the self-inflicted half of that row's problem. Every row now goes through its adapter and
# the manifest records what the host actually answered.
NO_TEXT = {
    "BSR-RC-05": ("LINEAGE", "Fordham sourcebook is a TRANSLATION_WITNESS / lineage host for 4 released cells; the text corpus for Lateran IV constitutions 1–2 is BSR-RC-04"),
    "BSR-LU-02": ("AUTHORITY_URL_ONLY", "files.lcms.org is a client-side viewer (AC-08): registered as the LCMS adoption URL; no text extraction"),
}
