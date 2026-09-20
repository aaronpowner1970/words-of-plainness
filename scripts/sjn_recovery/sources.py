"""Deterministic per-standard fetch + split adapters.

Every adapter splits by the document's OWN divisions (article, question, paragraph number, canon,
decree, chapter.paragraph) — never by character count. The locator a learner eventually sees is that
division. Where a division is long (Book of Concord articles), consecutive numbered paragraphs are
grouped and the locator names the real paragraph range.

Adapters return (chunks, notes). Chunk fields: registry_id, branch, standard_title, authority_tier,
scope_caveat, locator, division, text, text_hash, source_url (internal: never passed to an agent),
language. Fetch modes follow the registry (AC-08): RENDERED hosts use Playwright. files.lcms.org was registered as
an authority URL only until session 5, when the publisher's Download href was found to serve the PDF itself."""
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
                       nfc, has_polytonic, strip_foreign_parentheticals, normalize, dehyphenate, hyphenation_residue, contains,
                       join_soft_hyphens, strip_page_furniture, repair_intraword_splits)

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
               "final_url": fr.final_url, "redirects": list(fr.redirects or []), "cross_host_redirect": fr.cross_host_redirect,
               "www_label_redirects": list(getattr(fr, "www_label_redirects", None) or []),
               "content_type": getattr(fr, "content_type", ""),
               "bytes": len(getattr(fr, "pdf_bytes", b"") or b"") or len((getattr(fr, "html", "") or "").encode("utf-8"))}
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
        """PDF text, repaired at extraction — before any adapter splits it, so no adapter can carry a
        defect into a chunk. In order (2026-09-13, after the Anglican packet review):
          1. soft-hyphen line breaks joined ("cove<U+00AD><newline>nantal" -> "covenantal"; textutil.join_soft_hyphens);
          2. page furniture stripped: a short line recurring at the top or the bottom of many pages is a
             running header / footer and is removed from that zone BEFORE the pages are joined
             (textutil.strip_page_furniture; every removed line is reported in `self.furniture`);
          3. line-break hyphenation joined with the whole document's vocabulary as evidence (dehyphenate);
          4. residual intra-word splits repaired only on vocabulary evidence, every join logged
             (textutil.repair_intraword_splits -> `self.intraword_joins`).
        The page separators (form feeds) survive, so adapters that split by page still can."""
        self._check_host(url)
        fr = self.fetcher.get(url)
        self._log_fetch(url, "pdf", fr)
        if fr.status == 403:
            raise BlockedError(f"{url}: HTTP 403")
        if not fr.ok or not fr.pdf_bytes:
            raise FetchError(f"{url}: {fr.error or 'no PDF bytes'}")
        return self.repair_pdf_text(pdf_text(fr.pdf_bytes))

    def repair_pdf_text(self, raw):
        """The extraction repairs above, on already-extracted page text (form-feed separated). Kept
        separate so the audit (pdf_audit.py) can run the same path over the cached bytes."""
        self.hyphenation = getattr(self, "hyphenation", {})
        self.furniture = getattr(self, "furniture", {"top": {}, "bottom": {}, "lines_removed": 0})
        self.intraword_joins = getattr(self, "intraword_joins", [])
        # 0. Unicode line / paragraph separators (U+2028, U+2029) are spacing: the LCMS Augsburg Confession PDF separates
        #    every word with U+2029 (session 5). No stored chunk carried either character before this fold was added.
        raw = (raw or "").replace(chr(0x2029), " ").replace(chr(0x2028), " ")
        text = join_soft_hyphens(raw, stats=self.hyphenation)
        rep = {}
        text = strip_page_furniture(text, rep)
        for z in ("top", "bottom"):
            for k, n in rep.get(z, {}).items():
                self.furniture[z][k] = self.furniture[z].get(k, 0) + n
        self.furniture["lines_removed"] += rep.get("lines_removed", 0)
        text = dehyphenate(text, stats=self.hyphenation)
        return repair_intraword_splits(text, joins=self.intraword_joins, corpus_vocab=self.corpus_vocabulary())

    def corpus_vocabulary(self):
        """Casefolded tokens of every OTHER standard's stored chunks — closed-form evidence for an
        intra-word join ("cove nant" is "covenant" because the corpus knows the word), never a source
        of text. Computed once per Ctx."""
        if getattr(self, "_corpus_vocab", None) is None:
            from . import store
            words = set()
            for c in store.load_all_chunks():
                if c.get("registry_id") == self.rid:
                    continue
                words.update(w.casefold() for w in re.findall(r"[A-Za-z]+", c.get("text", "")))
            self._corpus_vocab = words
        return self._corpus_vocab

    def extraction_notes(self):
        """Manifest notes for what the PDF path repaired (empty for an HTML row)."""
        out = []
        if getattr(self, "hyphenation", None):
            out.append(f"hyphenation at extraction: {self.hyphenation}")
        f = getattr(self, "furniture", None)
        if f and f.get("lines_removed"):
            top = sorted(f["top"].items(), key=lambda kv: -kv[1])
            bot = sorted(f["bottom"].items(), key=lambda kv: -kv[1])
            out.append(f"page furniture stripped at extraction: {f['lines_removed']} zone line(s); "
                       f"top {top[:12]}; bottom {bot[:12]}")
        j = getattr(self, "intraword_joins", None)
        if j:
            out.append(f"intra-word splits repaired on vocabulary evidence: {len(j)} join(s): "
                       + "; ".join(f"{x['from']!r}->{x['to']!r} [{x['evidence']}{' of ' + x['stem'] if x.get('stem') else ''}]" for x in j[:24]))
        return out

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
    """Session 12 (Codex F.10): two defects fixed. (1) From Part Four the page sets the number and the question in SEPARATE bold tags
    (`<b>534.</b>&nbsp;<b>What is prayer?</b>`); the one-tag match recognised no heading after 533, so Q.534-598 ran on inside
    "Compendium Q.533". A bare "<n>." bold tag now opens question n and the next bold tag supplies its question text. (2) The
    Appendix is an anchor (`<a name="APPENDIX">`), never the bold tag the old stop looked for, so its prayers and formulas ran on too.
    It is part of the promulgated book (B2(b)), so it is chunked, not dropped: A) Common Prayers one chunk per prayer and column
    (English; the Latin column as its own chunk, language "la"), B) Formulas of Catholic Doctrine one chunk per formula.
    Q.1-532 are chunked exactly as before."""
    url = "https://www.vatican.va/archive/compendium_ccc/documents/archive_2005_compendium-ccc_en.html"
    html = ctx.html(url)
    segs = segments(html)
    out, cur, buf, expect, pending = [], None, [], 1, None
    appendix_at = None
    for n_seg, (tag, text) in enumerate(segs):
        t = clean(text)
        if tag == "a" and t == "APPENDIX" and cur:           # the table of contents links "APPENDIX" too, before Q.1
            appendix_at = n_seg
            break
        if pending is not None:                          # a bare "<n>." bold tag: the next bold tag is its question
            if not re.sub(r"[\s.]", "", t):              # Q.568 is set "<b>568</b>." — the stray full stop is skipped
                continue
            if tag == "b" and t:
                if cur:
                    _emit(ctx, out, f"Compendium Q.{cur}", buf, "question", url)
                cur, buf, expect, pending = pending, [f"{pending}. {t}"], pending + 1, None
                continue
            pending = None
        m = re.match(r"^(\d{1,3})\.\s+(.+)$", t)
        if tag == "b" and m and int(m.group(1)) == expect:
            if cur:
                _emit(ctx, out, f"Compendium Q.{cur}", buf, "question", url)
            cur, buf, expect = int(m.group(1)), [t], expect + 1
            continue
        mb = re.fullmatch(r"(\d{1,3})\.?", t)
        if tag == "b" and mb and int(mb.group(1)) == expect:
            pending = int(mb.group(1))
            continue
        if cur and tag in ("p", "i", "em"):
            if re.fullmatch(r"[\d\-–, ]+", t):
                continue
            buf.append(t)
        if cur and tag == "b" and re.match(r"^(APPENDIX|A\. Common Prayers)", t):
            break
    if cur:
        _emit(ctx, out, f"Compendium Q.{cur}", buf, "question", url)
    n_questions = len(out)
    notes = [f"registry canonical_url is a host note; text fetched from the cited compendium page; {n_questions} questions"]
    if appendix_at is None:
        return out, notes
    # ---- Appendix A: the Common Prayers table, one row per prayer, English | Latin
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fix_mojibake(html), "lxml")
    anchor = soup.find("a", attrs={"name": "APPENDIX"})
    table = anchor.find_parent("table") if anchor else None
    n_a = 0
    if table is not None:
        body = table.find("tbody") or table
        for tr in body.find_all("tr", recursive=False):
            for col, td in enumerate(tr.find_all("td", recursive=False)):
                parts = [(tg, clean(x)) for tg, x in segments(str(td)) if clean(x)]
                if not parts or parts[0][0] != "b" or parts[0][1] == "APPENDIX":
                    continue
                titles = [parts[0][1]]                   # the prayer's title; later bold lines (the Rosary's mysteries) are its text
                lines = [x for tg, x in parts[1:] if tg in ("p", "i", "em", "b", "font")]
                if not lines:
                    continue
                latin = col == 1
                loc = f"Compendium Appendix A (Common Prayers) — {titles[0]}" + (" (Latin)" if latin else "")
                c = ctx.chunk(loc, join([titles[0]] + lines), "appendix prayer", url, "la" if latin else "en")
                if c:
                    out.append(c); n_a += 1
    # ---- Appendix B: Formulas of Catholic Doctrine, one chunk per formula
    n_b, in_b, title, items = 0, False, [], []

    def flush_b():
        nonlocal n_b
        if title and items:
            head = clean(" ".join(title)).replace("( ", "(").replace(" )", ")")
            c = ctx.chunk(f"Compendium Appendix B (Formulas of Catholic Doctrine) — {head.rstrip(':')}", join([head] + items),
                          "appendix formula", url)
            if c:
                out.append(c); n_b += 1

    for tag, text in segs[appendix_at:]:
        t = clean(text)
        if tag == "a" and t.startswith("B) FORMULAS"):
            in_b = True
            continue
        if not in_b or not t:
            continue
        if tag in ("b", "i") and (not items or tag == "b"):
            if items:
                flush_b(); title, items = [], []
            title.append(t)
            continue
        if tag == "p":
            items.append(t)
    flush_b()
    notes.append(f"Appendix chunked (session 12; integral to the promulgated book, B2(b)): A) Common Prayers {n_a} chunk(s) "
                 f"(English and Latin columns separately), B) Formulas of Catholic Doctrine {n_b} chunk(s)")
    return out, notes


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
    n_forcespan_pages = [0]
    for h in paths:
        url = urljoin(BOC + "/", h)
        doc = BOC_DOCS[[p for p in h.split("/") if p][0]]
        try:
            page_html = ctx.html(url)
            segs = segments(page_html)
        except FetchError as e:
            notes.append(str(e)); ctx.log(f"   ! {e}"); continue
        title = next((clean(x) for t, x in segs if t in ("h2", "h1") and "Original Home" not in x and "BookOfConcord" not in x), "")
        if not title:
            continue
        if BOC_FORCESPAN in page_html:
            # session 12 (Codex F.10): the Small Catechism pages set their text inside <span class="forcespan"> within <h4>/<p>
            paras = _boc_forcespan_paras(page_html)
            n_forcespan_pages[0] += 1
        else:
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
    if n_forcespan_pages[0]:
        notes.append(f"session 12: {n_forcespan_pages[0]} page(s) set in <span class=\"forcespan\"> (the Small Catechism) read by element, "
                     f"<h4> and <p>, whole text (sources._boc_forcespan_paras)")
    return out, notes


BOC_FORCESPAN = 'class="forcespan"'


def _boc_forcespan_paras(html):
    """Session 12 (Codex F.10, BSR-LU-01): the Small Catechism pages on bookofconcord.org set the catechism's text inside
    <span class="forcespan"> within <h4> (the commandment, article or petition) and <p> ("What does this mean?" in <em>, "-Answer:"
    then the answer in a forcespan). The segment reader keeps only an element's DIRECT text, so every question and answer was lost and
    only the "-Answer:" markers were stored ("II. The Creed, ¶1-3" was 30 characters). Here each <h4> and <p> that is a direct child of
    <main> is read whole, in order; a bare-number anchor ("1") starts paragraph 1, a lettered one ("1b", "11c") continues it, and the
    anchors themselves are removed from the text. Unnumbered elements before the first number (Luther's rubric, the first
    commandment's heading) belong to the first paragraph rather than being dropped. The page title (<h2>) and the navigation boxes are
    not paragraphs. Returns [(number or None, text)] for the grouping the other pages use."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fix_mojibake(html), "lxml")
    main = soup.find("main") or soup
    paras, leading = [], []
    for el in main.find_all(["h4", "p"], recursive=False):
        anchors = el.find_all("span", class_="bocanchor-content")
        m = re.fullmatch(r"\s*(\d{1,3})\s*", anchors[0].get_text()) if anchors else None   # "1b" / "11c" continue paragraph 1 / 11
        for sp in el.find_all("span", class_="bocanchor"):
            sp.decompose()
        t = clean(el.get_text(""))
        if not t or t.startswith(("<<", ">>")):
            continue
        n = int(m.group(1)) if m else None
        if n is None and not paras:
            leading.append(t); continue
        if n is not None and not paras and leading:
            paras.extend((n, x) for x in leading)
            leading = []
            paras.append((None, t))
            continue
        paras.append((n, t))
    if leading and not paras:
        paras = [(None, x) for x in leading]
    return paras


AC_LCMS_HEADING = re.compile(r"^(Preface to the Emperor Charles V\.|Article [IVXL]+: .+|Articles In Which Are Reviewed|Conclusion\.)$")
AC_LCMS_PARA = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\]\s*")
AC_LCMS_FOOTER = "©The Lutheran Church"
FF_CHAR, NL_CHAR = chr(12), chr(10)


def augsburg_confession_lcms(ctx):
    """BSR-LU-02 — the Augsburg Confession as the LCMS publishes it (files.lcms.org Download href, a text-layer PDF;
    session 5, 2026-09-13). Split by the document's own divisions — the Preface, Articles I–XXVIII, the introduction to
    the abuses corrected, the Conclusion — and inside a long division by the printed paragraph numbers ("12]"), grouped
    like the Book of Concord adapter (≤ BOC_GROUP_CHARS). The paragraph markers are removed from the text (they fall
    mid-sentence and would break a verbatim phrase) and named in the locator. Dropped: the table of contents and title
    page before the Preface, every "Back to top" link line, and the publisher's address block after the final one
    (it opens "©The Lutheran Church—Missouri Synod"); the running "Page N of 27" header is removed by the extraction
    repair (page furniture)."""
    url = ctx.row["canonical_url"]
    text = ctx.pdf(url)
    lines = [clean(l) for l in text.replace(FF_CHAR, NL_CHAR).split(NL_CHAR)]
    divisions, cur, started, footer_at, back_links = [], None, False, None, 0
    for i, t in enumerate(lines):
        if not t:
            continue
        if t.startswith(AC_LCMS_FOOTER):
            footer_at = i
            break
        if t == "Back to top":
            back_links += 1
            continue
        m = AC_LCMS_HEADING.match(t)
        if m and (started or t.startswith("Preface to the Emperor")):
            started = True
            cur = {"title": t.rstrip("."), "lines": []}
            divisions.append(cur)
            continue
        if not started:
            continue
        if cur["title"] == "Articles In Which Are Reviewed" and not cur["lines"] and t.startswith("The Abuses"):
            cur["title"] = f"{cur['title']} {t}"
            continue
        if t == "Chief Articles of Faith":
            continue
        cur["lines"].append(t)
    if footer_at is None:
        raise FetchError(f"{url}: publisher footer not found — the PDF layout changed; nothing chunked")
    out = []
    for d in divisions:
        body = join(d["lines"])
        parts = [p for p in AC_LCMS_PARA.split(body)]
        paras, num = [], None
        if parts and parts[0].strip():
            paras.append((None, parts[0].strip()))
        for k in range(1, len(parts) - 1, 2):
            paras.append((int(parts[k]), parts[k + 1].strip()))
        loc_base = f"Augsburg Confession: {d['title']}"
        group, a, b, size = [], None, None, 0
        for n, t in paras:
            if not t:
                continue
            if group and size + len(t) > BOC_GROUP_CHARS and n is not None:
                _emit(ctx, out, f"{loc_base}, ¶{a}" + (f"–{b}" if b != a else ""), group, "paragraph-range", url)
                group, a, b, size = [], None, None, 0
            if n is not None:
                a = a if a is not None else n
                b = n
            group.append(t); size += len(t)
        if group and a is None:
            _emit(ctx, out, loc_base, group, "section", url)             # an article printed without paragraph numbers (XIV, XIX)
        elif group:
            _emit(ctx, out, f"{loc_base}, ¶{a}" + (f"–{b}" if b != a else ""), group, "paragraph-range", url)
    return out, [f"{len(divisions)} divisions (Preface, Articles I–XXVIII, abuses introduction, Conclusion) in {len(out)} paragraph-range chunks; "
                 f"{back_links} 'Back to top' link line(s) and the publisher address block after the last dropped; table of contents and title page skipped"]


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


CRC_EDITORIAL_NOTE = "publisher apparatus (CRC editorial note)"


def heidelberg_crcna(ctx):
    """Session 12 (Codex F.10, B2(b)): the CRC's editorial footnotes — paragraphs opening "*" or "**" (on the editions of Q&A 80 and the
    Synod 2004/2006 brackets; on "broken" in Q&A 77; on the NRSV Lord's Prayer in Q&A 119) — are publisher matter, not the catechism's
    text. Each Q&A's notes are held out of its chunk and emitted after it as "<Q&A locator> — CRC editorial note(s)", division
    CRC_EDITORIAL_NOTE, which the R6-40 apparatus guard reads. The note markers inside the Q&A text ("80*", "]**") are the page's own."""
    url = ctx.row["canonical_url"]
    segs = segments(ctx.html(url))
    out, cur, buf, notes_buf, lords_day = [], None, [], [], ""
    n_notes = 0

    def flush():
        nonlocal n_notes
        if cur:
            _emit(ctx, out, cur, buf, "question", url)
            if notes_buf:
                c = ctx.chunk(f"{cur} — CRC editorial note(s)", join(notes_buf), CRC_EDITORIAL_NOTE, url)
                if c:
                    out.append(c); n_notes += 1

    for tag, text in segs:
        t = clean(text)
        if tag == "h4" and t.startswith("Lord"):
            lords_day = t; continue
        # session 11: crcna.org heads one entry "Q & A 80*" (the asterisk points to its edition footnote); an exact-number match
        # dropped the heading, so Q&A 80's text ran on inside the Q&A 79 chunk
        m = re.match(r"^Q & A (\d{1,3})\*{0,2}$", t)
        if tag == "div" and m:
            flush()
            cur, buf, notes_buf = f"Q&A {m.group(1)} ({lords_day})", [], []
            continue
        if cur and tag in ("p", "em", "i"):
            if re.match(r"^\d{1,2}\s", t) or re.fullmatch(r"[\d\s,;:.\-–]+", t):
                continue   # footnote scripture lists
            if t.startswith("*") or notes_buf:            # a note runs to the next Q&A (Q&A 80's ** note has a second paragraph)
                notes_buf.append(t); continue
            buf.append(strip_footnote_digits(t))
        if cur and tag in ("h2", "h3") and t.startswith(("Part", "God", "Introduction")):
            pass
    flush()
    return out, [f"{len(out) - n_notes} Q&A (CRC/RCA 2011 translation)",
                 f"session 12: {n_notes} CRC editorial-note chunk(s) held out of the Q&A text (division {CRC_EDITORIAL_NOTE!r}; apparatus guard R6-40)"]


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


_HISTORICAL_DOCS_TITLE = re.compile(r"^\s*Historical\s+Documents\s+of\s+the\s+Church\s*$", re.I)


def _historical_heading_blocks(lines):
    """Split one page of the BCP's Historical Documents into (heading, body lines) blocks. A heading is a run of short lines
    (<= 45 characters) with no terminal punctuation that starts the page or follows a line ending a sentence — on BCP p. 864
    "Definition of the Union of the Divine / and Human Natures in the Person of Christ / Council of Chalcedon, 451 A.D., Act V"
    and "Quicunque Vult / commonly called / The Creed of Saint Athanasius". Body lines are the rest."""
    blocks, head, body, prev_end = [], [], [], True
    for l in lines:
        short = len(l) <= 45 and not re.search(r"[.;:,?!]$", l)
        if short and (prev_end or (head and not body)):
            if body:
                blocks.append((head, body)); head, body = [], []
            head.append(l)
            prev_end = False
            continue
        body.append(l)
        prev_end = bool(re.search(r"[.;:?!]$", l))
    if head or body:
        blocks.append((head, body))
    return blocks


TEC_P844_RUBRIC_DIVISION = "rubric (integral text)"          # R6-51: stored with its locator, never registered


def tec_outline_of_faith(ctx):
    """BSR-AN-04 — the Outline of the Faith as the BCP 1979 prints it: BCP pp. 844–862 (R6-51).

    Session 12 (Codex F.10) found the Outline running on past its own end: the printed title page "Historical Documents of the
    Church" (BCP p. 863) sets its title over three lines, so the old stop (a line starting "Historical Documents") never fired and
    the last question's chunk ("What, then, is our assurance as Christians?", p. 862) ran on through p. 864. Session 12 stopped the
    Outline at that title page and chunked the pages after it ON THIS ROW, marked as awaiting a scope ruling (R6-45).

    Session 14 (R6-48, R6-51) finishes the split. This row now holds BCP pp. 844–862 and nothing after p. 862: the Historical
    Documents are BSR-AN-06 (tec_historical_documents below). Holding them here had left the Quicunque Vult stored CUT at "one
    Almighty.", because the creed runs across the page break into p. 865 and p. 865 lay outside this adapter's 20-page window.
    Two changes:

      * the p. 844 rubric "Concerning the Catechism" is stored, with its own locator and division. It is integral text of the
        adopted book (B2(b)) and it is NOT a registered section: it is a rubric ABOUT the catechism, not the catechism, and not a
        creed or definition (R6-51);
      * the Historical Documents pages are no longer chunked here."""
    url = ctx.row["canonical_url"]
    pages = ctx.pdf(url).split("\f")
    start = next((i for i, p in enumerate(pages) if "An Outline of the Faith" in p and "commonly called the Catechism" in p), -1)
    if start < 0:
        raise FetchError("Outline of the Faith not found in PDF")
    out, section, q, a, state = [], "", None, [], None
    historical_at = None
    # R6-51: the p. 844 rubric, the page before the Outline's own first page, stored as integral text with its locator.
    rubric_lines = [l.strip() for l in pdf_repair(pages[start - 1]).split("\n")
                    if l.strip() and not re.fullmatch(r"\d{3}", l.strip())] if start > 0 else []
    if rubric_lines[:1] == ["Concerning the Catechism"]:
        _emit(ctx, out, f"Outline of the Faith (BCP p. {start}) — Concerning the Catechism (rubric)",
              rubric_lines[1:], TEC_P844_RUBRIC_DIVISION, url)
    else:
        raise FetchError(f"BSR-AN-04: BCP p. {start} does not open with the rubric 'Concerning the Catechism', which R6-51 names "
                         f"as this row's first page; got {rubric_lines[:1]}")
    for pi in range(start, min(len(pages), start + 20)):
        page_no = pi + 1
        if pi > start and _HISTORICAL_DOCS_TITLE.match(" ".join(pdf_repair(pages[pi]).split())):
            historical_at = pi
            break
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
    n_qa = sum(1 for c in out if c.get("division") == "question")
    notes = [f"PDF pages {start}–{start + 20} region; {n_qa} Q/A pairs; 1 rubric chunk (BCP p. {start}, R6-51)"]
    if historical_at is None:
        raise FetchError("BSR-AN-04: the 'Historical Documents of the Church' title page was not found, so the Outline's end "
                         "(R6-51, BCP p. 862) cannot be located; refusing to chunk rather than run on again (Codex F.10)")
    notes.append(f"R6-51: this row is BCP pp. {start}–{historical_at} — the rubric 'Concerning the Catechism' (p. {start}), then "
                 f"the Outline itself, stopping at the 'Historical Documents of the Church' title page (p. {historical_at + 1}). "
                 f"The Historical Documents are BSR-AN-06 (R6-48), not this row; session 13 held them here under R6-45's marker")
    return out, notes


TEC_HISTORICAL_LAST_SENTENCE = "This is the Catholic Faith, which except a man believe faithfully, he cannot be saved."
TEC_HISTORICAL_STOP_HEADINGS = ("Preface", "Articles of Religion", "Chicago-Lambeth")   # R6-48 / R6-49: never fetched


def tec_historical_documents(ctx):
    """BSR-AN-06 — the TEC BCP 1979 "Historical Documents of the Church", BCP pp. 863–865 (R6-48).

    The row R6-48 created out of BSR-AN-04. Codex F.10's repair: split at p. 862/863. What this row holds, and only this:

      p. 863        the printed title page "Historical Documents of the Church", stored with its own locator so the
                    section's extent is visible in the store, as R6-51 stores AN-04's p. 844 rubric;
      p. 864        the Chalcedonian Definition ("Definition of the Union of the Divine and Human Natures in the
                    Person of Christ, Council of Chalcedon, 451 A.D., Act V");
      pp. 864–865    the Quicunque Vult, commonly called The Creed of Saint Athanasius, JOINED ACROSS THE PAGE BREAK.

    The join is the defect being fixed. The creed begins on p. 864 and ends on p. 865; the old AN-04 adapter's 20-page
    window ended at p. 864, so the stored chunk broke off at "And yet they are not three Almighties, but one Almighty."
    — a third of the way in, mid-argument, before a word of the Incarnation half. Nothing was wrong with the text: the
    window was. A document here is therefore accumulated ACROSS pages until the next printed heading, and the adapter
    refuses to return a Quicunque Vult that does not end at its last sentence.

    R6-48 also names what is NOT fetched for SJN: the 1549 Preface (p. 866 on), the Articles of Religion (p. 867 on,
    held by R6-49 for the F.9 adoption QA) and the Chicago-Lambeth Quadrilateral. The walk stops at the first of them.

    R6-47 governs what these chunks ARE: adopted within the Prayer Book (1979-A133) but not confessed, so they are
    witness sections and none of them is a registered creed or definition text. That is the row's tier and the
    registered-sections list, not this adapter."""
    url = ctx.row["canonical_url"]
    pages = ctx.pdf(url).split("\f")
    title_at = next((i for i, pg in enumerate(pages) if _HISTORICAL_DOCS_TITLE.match(" ".join(pdf_repair(pg).split()))), -1)
    if title_at < 0:
        raise FetchError("BSR-AN-06: the 'Historical Documents of the Church' title page was not found in the PDF")
    out = [ctx.chunk(f"Historical Documents of the Church (BCP p. {title_at + 1}) — title page",
                     " ".join(pdf_repair(pages[title_at]).split()), "title page", url)]
    docs, stopped_at = [], None
    for pi in range(title_at + 1, len(pages)):
        lines = [l.strip() for l in pdf_repair(pages[pi]).split("\n") if l.strip() and not re.fullmatch(r"\d{3}", l.strip())]
        if not lines:
            continue
        blocks = _historical_heading_blocks(lines)
        first_heading = clean(" ".join(blocks[0][0])) if blocks and blocks[0][0] else ""
        if first_heading.startswith(TEC_HISTORICAL_STOP_HEADINGS):
            stopped_at = (pi + 1, first_heading)
            break
        for head, body in blocks:
            if head:
                heading = clean(" ".join(head))
                if heading.startswith(TEC_HISTORICAL_STOP_HEADINGS):
                    stopped_at = (pi + 1, heading)
                    break
                docs.append({"heading": heading, "pages": [pi + 1], "lines": list(body)})
            elif docs:                                  # no heading: this page continues the document above it
                docs[-1]["lines"].extend(body)
                if pi + 1 not in docs[-1]["pages"]:
                    docs[-1]["pages"].append(pi + 1)
            elif body:
                raise FetchError(f"BSR-AN-06: BCP p. {pi + 1} carries text under no heading and follows no document")
        if stopped_at:
            break
    if not stopped_at:
        raise FetchError("BSR-AN-06: no stop heading was reached, so the row's extent (R6-48, BCP pp. 863\u2013865) is not "
                         "bounded by the text; refusing to chunk")
    for d in docs:
        pp = d["pages"]
        where = f"p. {pp[0]}" if len(pp) == 1 else f"pp. {pp[0]}–{pp[-1]}"
        c = ctx.chunk(f"Historical Documents of the Church (BCP {where}) — {d['heading']}", join(d["lines"]),
                      "historical document", url)
        if c:
            out.append(c)
    out = [c for c in out if c]
    quicunque = [c for c in out if "Quicunque Vult" in c["locator"]]
    if len(quicunque) != 1:
        raise FetchError(f"BSR-AN-06: expected exactly one Quicunque Vult chunk, got {len(quicunque)} "
                         f"({[c['locator'] for c in quicunque]})")
    if not quicunque[0]["text"].rstrip().endswith(TEC_HISTORICAL_LAST_SENTENCE):
        raise FetchError("BSR-AN-06: the Quicunque Vult chunk does not end at its last sentence "
                         f"({TEC_HISTORICAL_LAST_SENTENCE!r}); it ends {quicunque[0]['text'][-60:]!r}. This is the "
                         "session 12/13 defect (the creed cut at 'one Almighty.') and the chunk is refused, not stored")
    last_page = max(pp for c in out for pp in [int(re.search(r"pp?\. (?:\d+–)?(\d+)", c["locator"]).group(1))])
    if last_page > title_at + 3:
        raise FetchError(f"BSR-AN-06: a chunk runs to BCP p. {last_page}, past the row's extent (R6-48: pp. "
                         f"{title_at + 1}–{title_at + 3})")
    notes = [f"R6-48: BCP pp. {title_at + 1}–{last_page}; {len(out)} chunk(s) — the title page, then "
             + "; ".join(f"{c['locator'].split(' — ', 1)[1]} ({c['locator'].split('(BCP ', 1)[1].split(')', 1)[0]})" for c in out[1:]),
             f"the Quicunque Vult is JOINED across the BCP p. 864/865 page break and ends at its last sentence "
             f"({TEC_HISTORICAL_LAST_SENTENCE!r}); the session 12/13 store held it cut at 'one Almighty.'",
             f"stopped at BCP p. {stopped_at[0]} ({stopped_at[1]!r}): R6-48 does not fetch the 1549 Preface, and R6-49 "
             f"holds the Articles of Religion for the Codex F.9 adoption QA",
             "R6-47 / Codex B1(c): adopted within the Prayer Book but not confessed — these are witness sections and "
             "none is a registered creed or definition text"]
    return out, notes


ACNA_FRONT_MATTER = "front matter (publisher/editor apparatus)"
# session 13 (R6-46.1): Part I's introductory matter before Q.1 is integral text, not front matter; its own division, never guarded
ACNA_PART_I_INTRO = "Part I introductory matter (integral text)"


def _acna_question_follows(lines, i, first):
    """True when the numbered line lines[i] opens a question: its own text, or one of the next four non-empty lines before another
    numbered line, carries a question mark. The drafting guidelines in the front matter ("1. Everything taught should be ...") do not."""
    seen = [first] if first else []
    for l in lines[i + 1:i + 12]:
        if not l:
            continue
        if re.match(r"^\d{1,3}\.(\s|$)", l):
            break
        seen.append(l)
        if len(seen) >= 5:
            break
    return any("?" in x for x in seen)


def acna_to_be_a_christian(ctx):
    """Session 12 (Codex F.10): the front matter no longer takes question numbers. The drafting guidelines are numbered "1."-"3.", so
    the counter spent Q.1-Q.3 on them: "Q.1" and "Q.2" were guidelines and "Q.3" held the third guideline, the Committee's sign-off,
    the note on Scripture references, the collect, Part I's introductory matter and then the real Q.1-3. Before the first question, a
    numbered line opens a question only when a question follows it (_acna_question_follows). The text the store held before the first
    question is kept in two chunks split at "part i": the front matter (guidelines, sign-off, Scripture references, collect), division
    ACNA_FRONT_MATTER, which the R6-36 apparatus guard reads (B2(b): publisher/editor matter does not inherit the adoption); and Part I's
    introductory matter before Q.1. Session 13 (R6-46.1): that Part I chunk is integral text, carries division ACNA_PART_I_INTRO and is
    never guarded. From the first real question on, nothing changes."""
    url = ctx.row["canonical_url"]
    txt = pdf_repair(ctx.pdf(url).replace("\f", "\n"))
    lines = [l.strip() for l in txt.split("\n")]
    out, cur, buf, expect, qtext, in_q = [], None, [], 1, [], False
    front, front_started = [[]], False
    for i, l in enumerate(lines):
        m = re.match(r"^(\d{1,3})\.\s*(.*)$", l)
        if m and int(m.group(1)) == expect and (cur is not None or _acna_question_follows(lines, i, m.group(2))):
            if cur:
                _emit(ctx, out, f"To Be a Christian, Q.{cur} — {clean(' '.join(qtext))[:70]}", qtext + buf, "question", url)
            cur, expect, qtext, buf, in_q = int(m.group(1)), expect + 1, [m.group(2)] if m.group(2) else [], [], True
            if qtext and qtext[0].endswith("?"):
                in_q = False
            continue
        if cur is None:
            if m and int(m.group(1)) == 1:
                front_started = True                     # the store's text began at the first "1." line, as before
            if not front_started:
                continue
            if not l or re.fullmatch(r"\d{1,3}", l) or re.fullmatch(r"[A-Z ]{6,}", l):
                continue
            if l.casefold() == "part i" and front[-1]:
                front.append([])
            front[-1].append(l)
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
    fm = []
    labels = ["To Be a Christian, front matter — introduction: drafting guidelines, the Committee's sign-off, Scripture references, collect",
              "To Be a Christian, Part I, Beginning with Christ — introductory matter before Q.1"]
    for n, part in enumerate(x for x in front if x):
        division = ACNA_FRONT_MATTER if n == 0 else ACNA_PART_I_INTRO          # session 13, R6-46.1: only the chunk before "Part I"
        c = ctx.chunk(labels[min(n, len(labels) - 1)] + (f" [{n + 1}]" if n >= len(labels) else ""), join(part), division, url)
        if c:
            fm.append(c)
    n_front = sum(1 for c in fm if c["division"] == ACNA_FRONT_MATTER)
    return fm + out, [f"{len(out)} numbered questions (fallback tier: registry_fallback_only_rows)",
                      f"session 13: {n_front} front-matter chunk before Part I (division {ACNA_FRONT_MATTER!r}; apparatus guard R6-36, "
                      f"narrowed by R6-46.1) and {len(fm) - n_front} Part I introductory chunk (division {ACNA_PART_I_INTRO!r}; integral, not guarded)"]


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


BA04_FIRST = "American Baptists worship the triune God"
BA04_LAST = "That Jesus shall reign for ever and ever."
BA04_HEAD_NOTE = "adopted by the covenanting partners"


def _utf8_read_as_latin1(html):
    """The page declares UTF-8 but the fetcher decoded it as ISO-8859-1 (no charset header): "God\u2019s" arrives as "Godâ\x80\x99s".
    textutil.fix_mojibake repairs cp1252 mojibake and, here, DROPS the C1 bytes (\x80, \x99), so apostrophes and quotation marks
    would be lost ("Gods"). Re-decode strictly: latin-1 is byte-transparent, so this recovers the page's own UTF-8 text or fails."""
    if not re.search(r"[\xc2-\xf4][\x80-\xbf]", html):
        return html, False
    try:
        return html.encode("latin-1").decode("utf-8"), True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return html, False


def abc_usa_we_are_american_baptists(ctx):
    """BSR-BA-04, added by author ruling R6-42 (session 13): "We Are American Baptists" (ABCUSA Identity Statement, Standing Rules
    Addendum #1). The statement is read from the page's content section, from its first sentence ("American Baptists worship the
    triune God ...") to its last ("That Jesus shall reign for ever and ever."). EXCLUDED (R6-42 chunking guards): the title heading,
    the italic head note ("... adopted by the covenanting partners ... Standing Rules, under Addendum #1"), images, links and everything
    after the last sentence (print-ready and brochure links), and all site chrome. KEPT: the "A Redeemed People / A Biblical People ..."
    lists, integral to the statement (B2(b)). Chunks: each opening paragraph; the "THEREFORE ... we believe" list; the two lead-in
    paragraphs; one chunk per "... People" list; the "We further believe" list. Fails closed (FetchError) when the first or last
    sentence is missing, when the head note cannot be identified and excluded, or when any chunk would carry it."""
    from bs4 import BeautifulSoup
    url = ctx.row["canonical_url"]
    raw = ctx.html(url)
    html, redecoded = _utf8_read_as_latin1(raw)
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one("div.content-section")
    if body is None:
        raise FetchError(f"{url}: no div.content-section")
    text_of = lambda el: clean(el.get_text(" "))
    children = [el for el in body.children if getattr(el, "name", None)]
    head_notes = [el for el in children if el.name == "p" and el.find("em") and BA04_HEAD_NOTE in text_of(el)]
    if len(head_notes) != 1:
        raise FetchError(f"{url}: the head note ('{BA04_HEAD_NOTE} ...') was found {len(head_notes)} times, not once; it cannot be excluded")
    start = next((i for i, el in enumerate(children) if el.name == "p" and text_of(el).startswith(BA04_FIRST)), None)
    end = next((i for i, el in enumerate(children) if el.name == "ul" and text_of(el).endswith(BA04_LAST)), None)
    if start is None or end is None or end < start:
        raise FetchError(f"{url}: the statement's first sentence ({BA04_FIRST!r}) or last ({BA04_LAST!r}) is not on the page")
    if children.index(head_notes[0]) > start:
        raise FetchError(f"{url}: the head note is not before the statement")
    out, para_n, heading, pending = [], 0, None, []
    li_text = lambda ul: " ".join(clean(li.get_text(" ")) for li in ul.find_all("li", recursive=False))
    seq = children[start:end + 1]
    i = 0
    while i < len(seq):
        el = seq[i]
        t = text_of(el)
        if el.name == "p" and ("content-img" in (el.get("class") or []) or not t):
            i += 1; continue
        strong = el.find("strong") if el.name == "p" else None
        if el.name == "p" and strong and clean(strong.get_text(" ")) == t and i + 1 < len(seq) and seq[i + 1].name == "ul":
            c = ctx.chunk(f"We Are American Baptists — {t}", join([t, li_text(seq[i + 1])]), "statement list", url)
            if c:
                out.append(c)
            i += 2; continue
        if el.name == "p" and t.startswith("THEREFORE") and i + 1 < len(seq) and seq[i + 1].name == "ul":
            c = ctx.chunk("We Are American Baptists — Therefore, with Baptists around the world, we believe", join([t, li_text(seq[i + 1])]),
                          "statement list", url)
            if c:
                out.append(c)
            i += 2; continue
        if el.name == "p" and (t.startswith("Within the larger Baptist family") or t.startswith("We affirm that God through Jesus Christ calls us")):
            pending.append(t)
            if t.startswith("We affirm that God through Jesus Christ calls us"):
                c = ctx.chunk("We Are American Baptists — American Baptist convictions (introduction to the lists)", join(pending), "statement", url)
                if c:
                    out.append(c)
                pending = []
            i += 1; continue
        if el.name == "p":
            para_n += 1
            c = ctx.chunk(f"We Are American Baptists, ¶{para_n}", t, "statement paragraph", url)
            if c:
                out.append(c)
            i += 1; continue
        raise FetchError(f"{url}: unexpected <{el.name}> inside the statement: {t[:80]!r}")
    if pending:
        raise FetchError(f"{url}: the lead-in paragraphs were not followed by the lists")
    if not out or not out[0]["text"].startswith(BA04_FIRST) or not out[-1]["text"].endswith(BA04_LAST):
        raise FetchError(f"{url}: the chunks do not run from the first sentence to the last")
    if any(BA04_HEAD_NOTE in c["text"] or "Standing Rules" in c["text"] for c in out):
        raise FetchError(f"{url}: the head note reached a chunk")
    return out, [f"{len(out)} chunks: statement from {BA04_FIRST!r} to {BA04_LAST!r}; head note, title, images and links excluded "
                 f"(R6-42 chunking guards); page text {'re-decoded as UTF-8 (fetched as ISO-8859-1)' if redecoded else 'as fetched'}"]


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
    "BSR-LU-01": book_of_concord, "BSR-LU-02": augsburg_confession_lcms, "BSR-LU-03": small_catechism_cph,
    "BSR-RP-01": wcf_opc, "BSR-RP-02": wsc_opc, "BSR-RP-03": wlc_opc, "BSR-RP-04": pcusa_book_of_confessions,
    "BSR-RP-05": heidelberg_crcna, "BSR-RP-06": belgic_crcna,
    "BSR-AN-01": thirty_nine_articles, "BSR-AN-02": bcp_catechism_1662, "BSR-AN-03": athanasian_creed_cofe,
    "BSR-AN-04": tec_outline_of_faith, "BSR-AN-05": acna_to_be_a_christian,
    "BSR-AN-06": tec_historical_documents,                  # session 14: a row added by author ruling R6-48
    "BSR-BA-01": bfm2000, "BSR-BA-02": london_1689_ch2, "BSR-BA-03": abc_usa_10facts,
    "BSR-BA-04": abc_usa_we_are_american_baptists,           # session 13: a row added by author ruling R6-42
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
    # BSR-LU-02 left this list in session 5 (2026-09-13): the viewer page was a wrapper; the publisher's own Download href
    # (files.lcms.org/dl/f/the-augsburg-confession, Draft3r4, pending ratification) serves the text-layer PDF itself.
}
