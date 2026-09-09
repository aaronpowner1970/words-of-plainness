"""Build and execute phrase-containment assertions (P018/P019/P020/P021/P025 + supplements)."""
import concurrent.futures as cf
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

from .fetch import Fetcher, is_rendered_host, pdf_text, HOST_WHITELIST
from .scope import resolve_html, resolve_pdf, resolve_rendered, ScopeError
from .textnorm import contains, normalize, phrase_word_count, pdf_repair
from .workbook import s

# Pipeline-side supplement: targets the workbook instructs the pipeline to add
# (Build Metadata v2.16 row: "pipeline must add a phrase target for this cell and rerun
# P006/P020 on the two OCA URLs"). Carried here until incorporated in the next workbook version.
SUPPLEMENT_TARGETS = [
    {
        "kind": "QUEUE-CELL", "key": "Q-290", "role": "PRIMARY", "predicate_id": "RNR-H37",
        "url": "https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/the-holy-trinity/one-god-one-father",
        "locator": "One God, One Father (OCA official catechesis, The Orthodox Faith Vol. I)",
        "document": "The Orthodox Faith, Vol. I — The Holy Trinity: One God, One Father",
        "phrase": "There is only one God because there is only one Father",
        "extraction": "HTML", "status": "ASSERT",
        "provenance": "Pipeline supplement per Build Metadata v2.16 (H37 Eastern Orthodox source strengthening); "
                      "phrase and locator from Evidence-First Cell Queue Q-290 Source note.",
    },
    {
        "kind": "QUEUE-CELL", "key": "Q-290", "role": "SUPPLEMENTAL", "predicate_id": "RNR-H37",
        "url": "https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/the-symbol-of-faith/son-of-god",
        "locator": "Symbol of Faith — Son of God (OCA official catechesis)",
        "document": "The Orthodox Faith, Vol. I — The Symbol of Faith: Son of God",
        "phrase": "God is an eternal Father by nature",
        "extraction": "HTML", "status": "ASSERT",
        "provenance": "Pipeline supplement per Build Metadata v2.16; supplemental witness named in Q-290 Source note.",
    },
]


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
    for r in ctx.case_targets:
        qid = s(r["Queue ID"])
        st = s(r.get("Target Status"))
        url = s(r.get("Assertion Text URL"))
        ext = "RENDERED" if is_rendered_host(url) else ("PDF" if s(r.get("Extraction type")) == "PDF" else "HTML")
        targets.append(Target("CASE-STUDY", qid, "", url, s(r.get("Locator")), s(r.get("Document")),
                              s(r.get("Quoted phrase")), ext, "ASSERT" if st == "ASSERT" else st,
                              predicate_id=s(r.get("Family ID"))))
    for r in ctx.clar_sources:
        url = s(r.get("URL"))
        targets.append(Target("CLARIFICATION", s(r["Source ID"]), s(r.get("Case ID")), url, s(r.get("Locator")),
                              s(r.get("Document / statement")), s(r.get("Quoted phrase (≤15 words)")),
                              "RENDERED" if is_rendered_host(url) else "HTML", "ASSERT"))
    for d in SUPPLEMENT_TARGETS:
        targets.append(Target(d["kind"], d["key"], d["role"], d["url"], d["locator"], d["document"], d["phrase"],
                              d["extraction"], d["status"], predicate_id=d["predicate_id"], note=d["provenance"]))
    return targets


def apply_overrides(targets, overrides_path):
    """Apply scripts/sjn-phrase-overrides.json. Returns the list of applied override records
    (each with 'applied' True/False and a mismatch note when the workbook value drifted)."""
    import json, os
    if not os.path.exists(overrides_path):
        return []
    with open(overrides_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    applied = []
    by = {(t.kind, t.key, t.role): t for t in targets}
    for o in data.get("overrides", []):
        rec = dict(o)
        t = by.get((o["kind"], o["key"], o.get("role", "")))
        if t is None:
            rec["applied"] = False; rec["note"] = "target not found"
        elif getattr(t, o["field"]) != o["workbook_value"]:
            rec["applied"] = False
            rec["note"] = f"workbook value changed to {getattr(t, o['field'])!r}; override is stale — delete it"
        else:
            setattr(t, o["field"], o["override_value"])
            t.note = (t.note + " | " if t.note else "") + "PHRASE OVERRIDE applied (see meta.phrase_overrides)"
            rec["applied"] = True
        applied.append(rec)
    return applied


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
            t.result = "FAIL"; t.detail = f"scope resolution failed: {e}"; return t
        t.scope_mode, t.scope_note, t.scoped_chars = sr.mode, sr.note, len(sr.text)
        if contains(sr.text, t.phrase):
            t.result = "PASS"
            t.detail = "phrase found inside locator scope"
        else:
            t.result = "FAIL"
            page_hit = False
            if t.extraction == "HTML":
                page_hit = contains(self.http[t.url].html, t.phrase)
            elif t.extraction == "RENDERED":
                page_hit = contains(self.rendered[t.url].rendered.get("body", ""), t.phrase)
            elif t.extraction == "PDF":
                page_hit = contains(pdf_repair(self.pdf_texts[t.url]), t.phrase)
            t.detail = ("phrase NOT in locator scope" + (" (present elsewhere on page — locator/phrase mismatch)"
                                                          if page_hit else " (absent from whole page)"))
        return t
