"""Session 5 Task 3: every Branch Source Registry row (all 47, ratified and retired) against the artifact URL rule
(WoP Source Verification Standard rule 7) — REPORT ONLY, no registry change, no model calls.

For each row the workbook's canonical_url is requested LIVE exactly as written (the Gate 6 strict fetcher; a retired
host is never requested; the rendered fetch is used where the row's adapter needs it) and the body is tested against
the row's OWN stored chunks: EVERY stored chunk, a 48-character normalised window from the middle
of each, counted present or absent in the normalised body. Separately, the corpus manifest says which URLs the adapter
actually read and how many chunks each one sourced.

Classes (measured, then named):
  SERVES_ARTIFACT        the URL's own bytes carry the standard's text and the corpus is sourced from it
  SERVES_PART            the URL's bytes carry part of the text; the adapter reads the rest from sibling pages / an index
  WRAPPER_NO_TEXT        the URL answers but its bytes carry none of the standard's text (viewer, landing, library or
                         details page, index) — the rule-7 defect
  NOT_A_URL              the field is not a single fetchable URL (prose, a bare domain)
  NOT_REQUESTED          retired host (never requested) — no observation
  FETCH_FAILED           the URL did not answer 2xx under the strict fetcher (the status is reported)
  NO_TEXT_TO_TEST        the URL answers but the row has no stored chunks to test against (classified by inspection)
Writes task3-artifact-url-audit.json beside this script (the table is in the session-5 report)."""
import json
import os
import re
import sys
import time
from collections import Counter
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_pipeline.fetch import Fetcher, pdf_text  # noqa: E402
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery import sources, store  # noqa: E402
from sjn_recovery.textutil import normalize, segments  # noqa: E402

SCRATCH_CACHE = os.path.join(os.environ.get("TEMP", HERE), "sjn-task3-fetch")
WINDOW = 48


def first_url(field):
    m = re.search(r"https?://\S+", field or "")
    return m.group(0).rstrip(").,;") if m else None


def body_text(fr, mode):
    if mode == "rendered":
        r = fr.rendered or {}
        return (r.get("body") or "") + "\n" + (r.get("main") or "")
    if fr.pdf_bytes:
        return pdf_text(fr.pdf_bytes)
    return " ".join(t for _, t in segments(fr.html or "")) if fr.html else ""


def windows(chunks):
    """one window per stored chunk (every chunk is tested; the test is a substring search)"""
    out = []
    for c in chunks:
        t = normalize(c["text"])
        if len(t) < WINDOW + 10:
            out.append((c["locator"], t[: min(len(t), WINDOW)]))
        else:
            mid = len(t) // 2
            out.append((c["locator"], t[mid: mid + WINDOW]))
    return out


def page_signals(fr, text):
    html = fr.html or ""
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return {"title": re.sub(r"\s+", " ", title.group(1)).strip()[:120] if title else None,
            "body_chars": len(text), "pdf": bool(fr.pdf_bytes),
            "pdf_links": len(re.findall(r"href=[\"'][^\"']+\.pdf", html, re.I)),
            "download_links": len(re.findall(r">\s*download\s*<", html, re.I)),
            "iframes": len(re.findall(r"<iframe", html, re.I)),
            "needs_javascript": bool(re.search(r"enable JavaScript", html, re.I))}


def main():
    reg = Registry()
    manifest = store.load_manifest().get("standards", {})
    fetcher = Fetcher(SCRATCH_CACHE, reuse_cache="--reuse" in sys.argv, strict_host=True)
    out = []
    for row in reg.rows_all:
        rid = row["registry_id"]
        field = row.get("canonical_url") or ""
        url = first_url(field)
        m = manifest.get(rid) or {}
        chunks = store.load_chunks(rid)
        src = Counter(c.get("source_url") for c in chunks)
        rec = {"registry_id": rid, "branch": row["branch"], "status": row["status"], "fetch_mode": row.get("fetch_mode"),
               "canonical_url_field": field, "manifest_status": m.get("status"), "stored_chunks": len(chunks),
               "adapter_urls_read": len(m.get("urls") or []), "adapter_modes": sorted({u.get("mode") for u in (m.get("urls") or [])}),
               "chunks_sourced_from_canonical_url": src.get(url, 0) if url else 0,
               "chunk_source_urls": len(src)}
        if not url or field.strip() != url:
            rec["field_is_single_url"] = False
        if not url:
            rec["class"] = "NOT_A_URL"; out.append(rec); print(rid, rec["class"]); continue
        if sources.retired_host(url):
            rec["class"] = "NOT_REQUESTED"; rec["note"] = sources.retired_host(url)[:160]; out.append(rec); print(rid, rec["class"]); continue
        mode = "rendered" if "rendered" in rec["adapter_modes"] and "http" not in rec["adapter_modes"] else "http"
        try:
            fr = fetcher.rendered(url) if mode == "rendered" else fetcher.get(url)
        except Exception as e:                                   # noqa: BLE001 — the audit records, it does not stop
            rec["class"] = "FETCH_FAILED"; rec["error"] = f"{type(e).__name__}: {str(e)[:160]}"; out.append(rec); print(rid, rec["class"]); continue
        rec["fetch"] = {"mode": mode, "status": fr.status, "ok": fr.ok, "error": fr.error, "final_url": fr.final_url,
                        "redirects": fr.redirects, "www_label_redirects": getattr(fr, "www_label_redirects", []),
                        "content_type": fr.content_type, "bytes": len(fr.pdf_bytes) if fr.pdf_bytes else len((fr.html or "").encode("utf-8"))}
        if not fr.ok:
            rec["class"] = "FETCH_FAILED"; out.append(rec); print(rid, rec["class"], fr.status, fr.error); continue
        text = body_text(fr, mode)
        rec["signals"] = page_signals(fr, text)
        nbody = normalize(text)
        ws = windows(chunks)
        hits = [loc for loc, w in ws if w and w in nbody]
        rec["text_test"] = {"windows": len(ws), "present": len(hits), "absent_locators": [loc for loc, w in ws if loc not in hits][:6]}
        share = len(hits) / len(ws) if ws else 0
        rec["text_test"]["share"] = round(share, 3)
        # A window can miss on a page that does serve the text: the stored chunk is the REPAIRED extraction (joined
        # hyphens, stripped furniture, folded quotes), the body here is the raw one. So a single-source row whose body
        # carries at least half of its chunks' windows serves the artifact; a body carrying some but under half, with the
        # corpus read from several URLs, is one page of a multi-page artifact.
        if not chunks:
            rec["class"] = "NO_TEXT_TO_TEST"
        elif not hits:
            rec["class"] = "WRAPPER_NO_TEXT"
        elif rec["chunk_source_urls"] <= 1 and share >= 0.5:
            rec["class"] = "SERVES_ARTIFACT"
        else:
            rec["class"] = "SERVES_PART"
        out.append(rec)
        print(rid, rec["class"], {k: rec["text_test"][k] for k in ("windows", "present", "share")}, "sources", rec["chunk_source_urls"],
              "from-canonical", rec["chunks_sourced_from_canonical_url"], rec["fetch"]["status"], rec["signals"]["title"])
        if "--reuse" not in sys.argv:
            time.sleep(0.5)
    fetcher.close()
    rep = {"audited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "workbook": os.path.basename(reg.path), "rows": len(out),
           "instrument": "Code: sjn_pipeline.fetch.Fetcher strict_host (python requests; Playwright for rendered rows); bodies fetched live "
                         "once this session, re-tested from that session cache" if "--reuse" in sys.argv else "Code: sjn_pipeline.fetch.Fetcher strict_host, live",
           "by_class": dict(Counter(r["class"] for r in out)), "per_row": out}
    json.dump(rep, open(os.path.join(HERE, "task3-artifact-url-audit.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(rep["by_class"]))


if __name__ == "__main__":
    main()
