"""Fetch layer: HTTP GET with retry/backoff and robots checks, Playwright-rendered
fetch for JavaScript-only hosts, PDF text extraction, on-disk cache.

P006: accept final HTTP status 200–399 after redirects; retry transient errors
(429, 5xx, timeouts); explicit whitelist only for access-controlled hosts.

Host discipline (Gate 6 cal-3 audit, 2026-09-11). The fetcher never rewrites a hostname: no
`www.` is added or stripped anywhere in this module (the only www-stripping in the pipeline is
`registry.normalize_host`, which is used for R001 domain MATCHING and never for fetching). What the
fetcher did do was follow every HTTP redirect the host issued, including a redirect onto a
DIFFERENT host — which is how the ratified apex URL of BSR-MW-03 (globalmethodist.org) came back as
the www site's 404. Redirects are now followed one hop at a time and recorded in
`FetchResult.redirects`; with `strict_host=True` (the Gate 6 corpus builder) a redirect that changes
the host is refused and reported as REDIRECT-CROSS-HOST, so the ratified URL is fetched exactly as
the registry gives it. The Gate 2 cell-assertion pipeline keeps following (a released cell's own
URL is what it is) but the hops are now logged so a cross-host redirect is visible in the audit.
"""
import base64
import hashlib
import json
import os
import time
import urllib.robotparser
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse, urljoin

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.9"}

# Hosts whose content is rendered client-side; assertions use Playwright.
RENDERED_HOSTS = {"www.churchofjesuschrist.org", "churchofjesuschrist.org", "www.josephsmithpapers.org"}

# P006 explicit whitelist: access-controlled hosts. Reachability failure is logged, not fatal.
HOST_WHITELIST = {
    "gameo.org": "Cloudflare bot verification blocks automated fetch (HTTP 403). Only lineage-only "
                 "retired rows Q-056/Q-344 and the unreleased case-study record Q-344 point here; "
                 "no phrase assertion depends on this host.",
}

# Robots exceptions: host -> reason. Robots disallow on these hosts does not block the build.
ROBOTS_EXCEPTIONS = {
    "www.the1689confession.com": "robots.txt endpoint rate-limits (HTTP 429); pages are public and "
                                 "fetched with backoff at low volume (2 URLs).",
}

RETRY_STATUSES = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    url: str
    kind: str = ""               # html | pdf | rendered
    status: int = 0
    final_url: str = ""
    content_type: str = ""
    ok: bool = False
    error: str = ""
    attempts: int = 0
    elapsed_ms: int = 0
    from_cache: bool = False
    robots: str = ""             # allowed | disallowed | unavailable | skipped
    whitelisted: bool = False
    fetched_at: str = ""
    redirects: list = field(default_factory=list)   # [(status, from_url, location)] hop by hop
    cross_host_redirect: str = ""                    # the first Location that changed the host, if any
    www_label_redirects: list = field(default_factory=list)  # hops followed under the www-label exception (session 5)
    # payloads (not serialized into meta)
    html: str = field(default="", repr=False)
    pdf_bytes: bytes = field(default=b"", repr=False)
    rendered: dict = field(default_factory=dict, repr=False)

    def log_entry(self):
        d = asdict(self)
        for k in ("html", "pdf_bytes", "rendered"):
            d.pop(k, None)
        return d


class RobotsCache:
    def __init__(self, session):
        self.session = session
        self.cache = {}

    def check(self, url):
        host = urlparse(url).netloc
        if host not in self.cache:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{host}/robots.txt"
            state = "unavailable"
            for attempt in range(4):
                try:
                    r = self.session.get(robots_url, headers=HEADERS, timeout=20)
                    if r.status_code == 429:
                        time.sleep(2 ** attempt)
                        continue
                    if r.status_code >= 400:
                        state = "unavailable"
                        rp = None
                    else:
                        rp.parse(r.text.splitlines())
                        state = "parsed"
                    break
                except requests.RequestException:
                    time.sleep(2 ** attempt)
            self.cache[host] = (state, rp)
        state, rp = self.cache[host]
        if state != "parsed" or rp is None:
            return "unavailable"
        return "allowed" if rp.can_fetch("*", url) else "disallowed"


MAX_REDIRECT_HOPS = 8

# R001 redirect rule, as amended 2026-09-13 (Gate 6 session 5, after the Baptist packet review). Quoted verbatim in
# docs/gate6/WoP_SJN_Gate6_Session5_Report_20260913.md; www_label_only() below is its only implementation.
STRICT_HOST_REDIRECT_RULE = (
    "Under strict_host a redirect that changes the host is refused and reported as REDIRECT-CROSS-HOST, with one "
    "exception: a hop whose target differs from the URL requested ONLY by the leading \"www.\" label is not a "
    "cross-host redirect and is followed. It qualifies only when all of these hold: one host is exactly the other with "
    "\"www.\" prefixed (so the registrable domain, every other label and the port are the same); the path is the same; "
    "the query is the same; and the scheme is the same or the hop is an http-to-https upgrade. Such a hop is recorded "
    "in FetchResult.www_label_redirects as well as in redirects. Every other cross-host redirect stays refused: another "
    "subdomain, another registrable domain, a changed path or query, an https-to-http downgrade, or a hop onto a "
    "storage or CDN host.")


def same_host(a, b):
    """Exact host comparison. `www.example.org` and `example.org` are DIFFERENT hosts here."""
    return urlparse(a).netloc.casefold() == urlparse(b).netloc.casefold()


def www_label_only(a, b):
    """True when the hop a -> b changes the host ONLY by the leading "www." label (STRICT_HOST_REDIRECT_RULE)."""
    pa, pb = urlparse(a), urlparse(b)
    ha, hb = pa.netloc.casefold(), pb.netloc.casefold()
    if ha == hb or not (ha == "www." + hb or hb == "www." + ha):
        return False
    if (pa.path or "/") != (pb.path or "/") or pa.query != pb.query or pa.params != pb.params:
        return False
    return pa.scheme.casefold() == pb.scheme.casefold() or (pa.scheme.casefold(), pb.scheme.casefold()) == ("http", "https")


class Fetcher:
    def __init__(self, cache_dir, reuse_cache=False, timeout=45, max_attempts=4, strict_host=False):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.reuse_cache = reuse_cache
        self.timeout = timeout
        self.max_attempts = max_attempts
        # strict_host: refuse to follow a redirect onto another host (registry fetches, Gate 6).
        self.strict_host = strict_host
        self.session = requests.Session()
        self.robots = RobotsCache(self.session)
        self._pw = None
        self._browser = None
        self._context = None
        self.cache_hits = 0

    # ---------- cache ----------
    def _cache_path(self, url, kind):
        return os.path.join(self.cache_dir, hashlib.sha1(f"{kind}|{url}".encode()).hexdigest() + ".json")

    def _load_cache(self, url, kind):
        if not self.reuse_cache:
            return None
        p = self._cache_path(url, kind)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        known = {f.name for f in FetchResult.__dataclass_fields__.values()}
        fr = FetchResult(**{k: v for k, v in d.items() if k not in ("html_b64", "pdf_b64", "rendered") and k in known})
        fr.html = base64.b64decode(d.get("html_b64", "")).decode("utf-8", "replace") if d.get("html_b64") else ""
        fr.pdf_bytes = base64.b64decode(d.get("pdf_b64", "")) if d.get("pdf_b64") else b""
        fr.rendered = d.get("rendered", {})
        fr.from_cache = True
        self.cache_hits += 1
        return fr

    def _save_cache(self, fr, kind):
        d = fr.log_entry()
        d["html_b64"] = base64.b64encode(fr.html.encode("utf-8")).decode() if fr.html else ""
        d["pdf_b64"] = base64.b64encode(fr.pdf_bytes).decode() if fr.pdf_bytes else ""
        d["rendered"] = fr.rendered
        with open(self._cache_path(fr.url, kind), "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)

    # ---------- HTTP ----------
    def get(self, url):
        cached = self._load_cache(url, "http")
        if cached:
            return cached
        fr = FetchResult(url=url, kind="html", fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        host = urlparse(url).netloc
        fr.robots = self.robots.check(url)
        if fr.robots == "disallowed" and host not in ROBOTS_EXCEPTIONS:
            fr.error = "ROBOTS-DISALLOWED"
            return fr
        t0 = time.time()
        for attempt in range(1, self.max_attempts + 1):
            fr.attempts = attempt
            try:
                r = self._get_following(url, fr)
                if r is None:          # cross-host redirect refused (strict_host)
                    break
                fr.status = r.status_code
                fr.final_url = r.url
                fr.content_type = r.headers.get("content-type", "")
                if r.status_code in RETRY_STATUSES and attempt < self.max_attempts:
                    ra = r.headers.get("Retry-After")
                    time.sleep(min(30, float(ra)) if ra and ra.isdigit() else 2 ** attempt)
                    continue
                # A PDF is recognised by its magic bytes as well as by content-type / suffix: files.lcms.org
                # serves the Augsburg Confession as application/octet-stream from a suffixless download route
                # (session 5, 2026-09-13), which was otherwise decoded as HTML text and yielded no bytes.
                if ("pdf" in fr.content_type.casefold() or url.casefold().endswith(".pdf")
                        or r.content[:5] == b"%PDF-"):
                    fr.kind = "pdf"
                    fr.pdf_bytes = r.content
                else:
                    fr.html = r.text
                fr.ok = 200 <= r.status_code < 400 and not (300 <= r.status_code < 400)
                fr.error = "" if fr.ok else f"HTTP {r.status_code}"
                break
            except requests.RequestException as e:
                fr.error = f"{type(e).__name__}: {str(e)[:120]}"
                if attempt < self.max_attempts:
                    time.sleep(2 ** attempt)
        fr.elapsed_ms = int((time.time() - t0) * 1000)
        if not fr.ok and host in HOST_WHITELIST:
            fr.whitelisted = True
        self._save_cache(fr, "http")
        return fr

    def _get_following(self, url, fr):
        """GET with redirects followed ONE HOP AT A TIME and recorded. The requested URL is sent
        byte for byte. A hop that changes the host is recorded in fr.cross_host_redirect; under
        strict_host it is refused (returns None with fr.error set) instead of being followed."""
        cur = url
        r = None
        for hop in range(MAX_REDIRECT_HOPS + 1):
            r = self.session.get(cur, headers=HEADERS, timeout=self.timeout, allow_redirects=False)
            if r.status_code not in (301, 302, 303, 307, 308):
                return r
            loc = r.headers.get("location", "")
            if not loc:
                return r
            nxt = urljoin(cur, loc)
            fr.redirects.append((r.status_code, cur, nxt))
            if not same_host(cur, nxt) and www_label_only(cur, nxt):
                fr.www_label_redirects.append((r.status_code, cur, nxt))       # not a cross-host redirect: followed
            elif not same_host(cur, nxt):
                if not fr.cross_host_redirect:
                    fr.cross_host_redirect = nxt
                if self.strict_host:
                    fr.status = r.status_code
                    fr.final_url = cur
                    fr.ok = False
                    fr.error = f"REDIRECT-CROSS-HOST: {urlparse(cur).netloc} -> {urlparse(nxt).netloc} ({r.status_code} {nxt})"
                    return None
            cur = nxt
        fr.error = f"too many redirects (> {MAX_REDIRECT_HOPS})"
        return r

    # ---------- Playwright ----------
    def _ensure_browser(self):
        if self._context is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._context = self._browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
        return self._context

    def rendered(self, url):
        """Playwright-rendered fetch. Returns FetchResult with .rendered = {main, body, pids}."""
        cached = self._load_cache(url, "rendered")
        if cached:
            return cached
        fr = FetchResult(url=url, kind="rendered", fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        fr.robots = self.robots.check(url)
        host = urlparse(url).netloc
        if fr.robots == "disallowed" and host not in ROBOTS_EXCEPTIONS:
            fr.error = "ROBOTS-DISALLOWED"
            return fr
        ctx = self._ensure_browser()
        t0 = time.time()
        for attempt in range(1, self.max_attempts + 1):
            fr.attempts = attempt
            page = ctx.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                fr.status = resp.status if resp else 0
                fr.final_url = page.url
                if not same_host(url, page.url) and www_label_only(url, page.url):
                    fr.www_label_redirects.append((fr.status, url, page.url))
                    fr.redirects.append((fr.status, url, page.url))
                elif not same_host(url, page.url):
                    fr.cross_host_redirect = page.url
                    fr.redirects.append((fr.status, url, page.url))
                    if self.strict_host:
                        fr.ok = False
                        fr.error = f"REDIRECT-CROSS-HOST: {urlparse(url).netloc} -> {urlparse(page.url).netloc}"
                        page.close()
                        break
                try:
                    page.wait_for_selector("p[id^='p'], article, main, .body", timeout=30000)
                except Exception:
                    pass
                page.wait_for_timeout(1200)
                data = page.evaluate("""() => {
                    const pick = document.querySelector('article') || document.querySelector('main')
                                 || document.querySelector('.body') || document.body;
                    const pids = {};
                    document.querySelectorAll('[id]').forEach(e => {
                        if (/^p\\d+$/.test(e.id)) pids[e.id] = e.innerText;
                    });
                    const blocks = [];
                    pick.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,blockquote').forEach(e => {
                        const t = (e.innerText || '').trim();
                        if (t) blocks.push({tag: e.tagName.toLowerCase(), id: e.id || '', text: t});
                    });
                    return {main: pick.innerText, body: document.body.innerText, pids, blocks};
                }""")
                fr.rendered = data
                fr.ok = 200 <= fr.status < 400 and len(data.get("body", "")) > 200
                fr.error = "" if fr.ok else f"HTTP {fr.status} / body {len(data.get('body',''))} chars"
                if fr.status in RETRY_STATUSES and attempt < self.max_attempts:
                    page.close(); time.sleep(2 ** attempt); continue
                page.close()
                break
            except Exception as e:
                fr.error = f"{type(e).__name__}: {str(e)[:120]}"
                page.close()
                if attempt < self.max_attempts:
                    time.sleep(2 ** attempt)
        fr.elapsed_ms = int((time.time() - t0) * 1000)
        if not fr.ok and host in HOST_WHITELIST:
            fr.whitelisted = True
        self._save_cache(fr, "rendered")
        return fr

    def close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass


def pdf_text(pdf_bytes):
    """Extract text from PDF bytes with PyMuPDF; pages joined with form feeds."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = [page.get_text() for page in doc]
    return "\f".join(parts)


def is_rendered_host(url):
    return urlparse(url).netloc in RENDERED_HOSTS
