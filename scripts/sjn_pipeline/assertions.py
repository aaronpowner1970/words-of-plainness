"""Build and execute phrase-containment assertions (P018/P019/P020/P021/P025 + supplements)."""
import concurrent.futures as cf
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

from .fetch import Fetcher, is_rendered_host, pdf_text, HOST_WHITELIST
from .scope import resolve_html, resolve_pdf, resolve_rendered, ScopeError
from .textnorm import contains, normalize, phrase_word_count, pdf_repair
from .workbook import s

# Workbook v2.18 carries every phrase target; the pipeline no longer supplements or overrides
# workbook phrases. Case Study Phrase Targets rows whose family is NOT one of the Matrix Case
# Studies (H05/H22/H43) are released non-case-study queue-cell targets (e.g. Q-290) and are
# validated under their own rule so P020/P021 keep the workbook's 140/24/21 expectations.
CONDITIONAL_REVIEW_PREFIX = "PENDING FETCH"   # Clarification Sources awaiting rendered-fetch verification


@dataclass
class Target:
    kind: str            # HISTORICAL | RESTORATION | CASE-STUDY | CLARIFICATION | QUEUE-CELL
    key: str             # predicate id / queue id / source id
    role: str            # PRIMARY | SUPPLEMENTAL | ''
    url: str
    locator: str
    document: str
    phrase: str
    extraction: str      # HTML | PDF | RENDERED
    status: str          # ASSERT | NO TARGET — UNRELEASED | NO PUBLIC TARGET
    predicate_id: str = ""
    note: str = ""
    conditional: bool = False   # PENDING FETCH source: failure drops the source, not the build
    review_status: str = ""
    dropped: bool = False       # clarification source excluded from the emitted case (see drop policy)
    page_hit: bool = False      # phrase present somewhere on the fetched page (diagnostic only)
    # results
    result: str = ""     # PASS | FAIL | SKIP
    scope_mode: str = ""
    scope_note: str = ""
    scoped_chars: int = 0
    fetch_status: int = 0
    detail: str = ""
    word_count: int = 0

    def public(self):
        d = asdict(self)
        return d


def build_targets(ctx):
    targets = []
    cit_by_id = {s(c["Predicate ID"]): c for c in ctx.citations}
    for r in ctx.hist_targets:
        pid = s(r["Predicate ID"])
        ready = s(r.get("Citation readiness"))
        ext = s(r.get("Source extraction type"))
        c = cit_by_id.get(pid, {})
        targets.append(Target("HISTORICAL", pid, "", s(r.get("Historical text URL")), s(r.get("Historical locator")),
                              s(c.get("Historical document")), s(r.get("Quoted phrase")),
                              "PDF" if ext == "PDF" else "HTML",
                              "ASSERT" if ready == "READY" else "NO PUBLIC TARGET", predicate_id=pid))
    for r in ctx.rest_targets:
        pid = s(r["Predicate ID"])
        url = s(r.get("Source URL"))
        fm = s(r.get("Fetch mode"))
        ext = "RENDERED" if (is_rendered_host(url) or "PLAYWRIGHT" in fm or "RENDERED" in fm) else "HTML"
        targets.append(Target("RESTORATION", pid, s(r.get("Target Role")), url, s(r.get("Locator")),
                              s(r.get("Source label")), s(r.get("Quoted phrase")), ext, "ASSERT",
                              predicate_id=pid, note=s(r.get("QA status"))))
    case_families = {s(r.get("Predicate ID")) for r in ctx.case_studies}
    seen_qids = {}
    for r in ctx.case_targets:
        qid = s(r["Queue ID"])
        st = s(r.get("Target Status"))
        url = s(r.get("Assertion Text URL"))
        fam = s(r.get("Family ID"))
        ext = "RENDERED" if is_rendered_host(url) else ("PDF" if s(r.get("Extraction type")) == "PDF" else "HTML")
        kind = "CASE-STUDY" if fam in case_families else "QUEUE-CELL"
        n = seen_qids.get(qid, 0); seen_qids[qid] = n + 1
        role = "" if kind == "CASE-STUDY" else ("PRIMARY" if n == 0 else "SUPPLEMENTAL")
        targets.append(Target(kind, qid, role, url, s(r.get("Locator")), s(r.get("Document")),
                              s(r.get("Quoted phrase")), ext, "ASSERT" if st == "ASSERT" else st,
                              predicate_id=fam, note=s(r.get("Notes"))))
    for r in ctx.clar_sources:
        url = s(r.get("URL"))
        review = s(r.get("Review status"))
        targets.append(Target("CLARIFICATION", s(r["Source ID"]), s(r.get("Case ID")), url, s(r.get("Locator")),
                              s(r.get("Document / statement")), s(r.get("Quoted phrase (≤15 words)")),
                              "RENDERED" if is_rendered_host(url) else "HTML", "ASSERT",
                              conditional=review.upper().startswith(CONDITIONAL_REVIEW_PREFIX), review_status=review))
    return targets


def collect_public_urls(ctx, targets):
    urls = set()

    def add(v):
        v = s(v)
        if ";" in v:
            for part in v.split(";"):
                add(part)
        elif v.startswith("http"):
            urls.add(v)

    for q in ctx.queue:
        add(q.get("Authority / adoption URL")); add(q.get("Text URL"))
    for c in ctx.citations:
        for k in ("Historical authority URL", "Historical text URL", "Restoration primary URL", "Restoration supplemental URL"):
            add(c.get(k))
    for r in ctx.godhead:
        add(r.get("Historic source URL")); add(r.get("LDS URL"))
    for r in ctx.restoration26:
        add(r.get("Official / primary source URL"))
    for r in ctx.pass2:
        add(r.get("Authority URL"))
    for r in ctx.current_source:
        add(r.get("Official URL"))
    for t in targets:
        add(t.url)
    return sorted(urls)


class Runner:
    def __init__(self, fetcher: Fetcher, log):
        self.fetcher = fetcher
        self.log = log
        self.http = {}       # url -> FetchResult (plain GET)
        self.rendered = {}   # url -> FetchResult (Playwright)
        self.pdf_texts = {}

    def fetch_all(self, urls, rendered_urls, workers=6):
        plain = [u for u in urls if u not in rendered_urls]
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for fr in ex.map(self.fetcher.get, plain):
                self.http[fr.url] = fr
                self.log(f"  GET {fr.status or fr.error:<14} {fr.url[:100]}")
        for u in sorted(rendered_urls):
            fr = self.fetcher.rendered(u)
            self.rendered[u] = fr
            self.log(f"  PW  {fr.status or fr.error:<14} {u[:100]}")

    def fetch_log(self):
        out = []
        for d in (self.http, self.rendered):
            for u in sorted(d):
                out.append(d[u].log_entry())
        return out

    def unresolved_failures(self):
        bad = []
        for d in (self.http, self.rendered):
            for u, fr in d.items():
                if not fr.ok and not fr.whitelisted:
                    bad.append({"url": u, "status": fr.status, "error": fr.error})
        return bad

    def run_assertion(self, t: Target):
        t.word_count = phrase_word_count(t.phrase)
        if t.status != "ASSERT":
            t.result = "SKIP"
            t.detail = f"explicit {t.status}; no assertion executed"
            return t
        if not t.phrase:
            t.result = "FAIL"; t.detail = "ASSERT target with blank phrase"; return t
        if t.word_count > 15:
            t.result = "FAIL"; t.detail = f"phrase exceeds 15 words ({t.word_count})"; return t
        try:
            if t.extraction == "RENDERED":
                fr = self.rendered.get(t.url) or self.fetcher.rendered(t.url)
                self.rendered[t.url] = fr
                t.fetch_status = fr.status
                if not fr.ok:
                    t.result = "FAIL"; t.detail = f"fetch failed: {fr.error}"; return t
                sr = resolve_rendered(t.url, t.locator, t.document, fr.rendered)
            elif t.extraction == "PDF":
                fr = self.http.get(t.url) or self.fetcher.get(t.url)
                self.http[t.url] = fr
                t.fetch_status = fr.status
                if not fr.ok or not fr.pdf_bytes:
                    t.result = "FAIL"; t.detail = f"fetch failed: {fr.error or 'no PDF bytes'}"; return t
                if t.url not in self.pdf_texts:
                    self.pdf_texts[t.url] = pdf_text(fr.pdf_bytes)
                sr = resolve_pdf(t.url, t.locator, t.document, self.pdf_texts[t.url])
            else:
                fr = self.http.get(t.url) or self.fetcher.get(t.url)
                self.http[t.url] = fr
                t.fetch_status = fr.status
                if not fr.ok or not fr.html:
                    t.result = "FAIL"; t.detail = f"fetch failed: {fr.error or 'empty body'}"; return t
                sr = resolve_html(t.url, t.locator, t.document, fr.html)
        except ScopeError as e:
            t.result = "FAIL"; t.detail = f"scope resolution failed: {e}"
            t.page_hit = self._page_hit(t)
            if t.page_hit:
                t.detail += " (phrase present elsewhere on page)"
            return t
        t.scope_mode, t.scope_note, t.scoped_chars = sr.mode, sr.note, len(sr.text)
        if contains(sr.text, t.phrase):
            t.result = "PASS"
            t.detail = "phrase found inside locator scope"
        else:
            t.result = "FAIL"
            t.page_hit = self._page_hit(t)
            t.detail = ("phrase NOT in locator scope" + (" (present elsewhere on page — locator/phrase mismatch)"
                                                          if t.page_hit else " (absent from whole page)"))
            if t.page_hit and t.extraction == "RENDERED":
                t.detail += self._rendered_location(t)
        return t

    def _page_hit(self, t):
        try:
            if t.extraction == "HTML":
                return contains(self.http[t.url].html, t.phrase)
            if t.extraction == "RENDERED":
                return contains(self.rendered[t.url].rendered.get("body", ""), t.phrase)
            if t.extraction == "PDF":
                return contains(pdf_repair(self.pdf_texts[t.url]), t.phrase)
        except KeyError:
            return False
        return False

    def _rendered_location(self, t):
        """Name the heading under which the phrase actually sits (diagnostic for workbook correction)."""
        blocks = self.rendered[t.url].rendered.get("blocks") or []
        heading = ""
        for b_ in blocks:
            if b_["tag"].startswith("h"):
                heading = b_["text"]
            elif contains(b_["text"], t.phrase):
                return f"; actual location: under heading “{heading}”" + (f" ({b_['id']})" if b_.get("id") else "")
        return ""
