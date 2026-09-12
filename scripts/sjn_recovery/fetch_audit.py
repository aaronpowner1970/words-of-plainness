"""Fetcher audit (cal-3, Fix 2): request every AUTHOR_RATIFIED canonical_url exactly as the registry
gives it, follow redirects one hop at a time WITHOUT crossing hosts, and record what the host answers.
Writes data-sources/sjn/recovery-runs/fetch-audit.json. No crawling: one request per ratified URL.
A retired host (config.RETIRED_HOSTS — goarch.org) is never requested. Never writes to the workbook.

  python scripts/sjn_recovery/fetch_audit.py [--workbook PATH]
"""
import argparse
import json
import os
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_pipeline.fetch import Fetcher  # noqa: E402
from sjn_recovery.config import FETCH_AUDIT_PATH  # noqa: E402
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery.sources import retired_host  # noqa: E402


def verdict_for(fr, url):
    if not url.startswith("http"):
        return "NO_URL: the registry names a host, not a page (text comes from the branch's other rows)"
    if fr.cross_host_redirect:
        return f"HOST: the ratified URL redirects onto another host ({fr.cross_host_redirect}); refused, not followed"
    if fr.status == 403:
        return "HOST: HTTP 403 to automated fetch (bot challenge)"
    if fr.status == 404:
        return "HOST: HTTP 404 on the ratified URL itself"
    if fr.ok:
        return "OK" + (f" (same-host redirects: {len(fr.redirects)})" if fr.redirects else "")
    return f"HOST: {fr.error or ('HTTP ' + str(fr.status))}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook")
    a = ap.parse_args()
    reg = Registry(a.workbook)
    tmp = tempfile.mkdtemp(prefix="sjn-fetch-audit-")
    fetcher = Fetcher(tmp, reuse_cache=False, strict_host=True, max_attempts=2, timeout=40)
    rows = []
    for r in reg.rows:
        url = (r.get("canonical_url") or "").strip()
        rec = {"registry_id": r["registry_id"], "branch": r["branch"], "canonical_url": url,
               "fetch_mode": r.get("fetch_mode"), "reception_scope": (r.get("reception_scope") or "").upper()}
        retired = retired_host(url)
        if retired:
            rec.update({"status": None, "verdict": f"HOST_RETIRED: not requested — {retired}"})
        elif not url.startswith("http"):
            rec.update({"status": None, "verdict": verdict_for(None, url)})
        else:
            fr = fetcher.get(url)
            rec.update({"status": fr.status, "final_url": fr.final_url, "redirects": fr.redirects,
                        "cross_host_redirect": fr.cross_host_redirect, "error": fr.error, "ok": fr.ok,
                        "content_type": fr.content_type, "bytes": len(fr.html or "") or len(fr.pdf_bytes or b""),
                        "verdict": verdict_for(fr, url)})
            time.sleep(0.5)
        print(f"{rec['registry_id']:10} {str(rec.get('status')):5} {rec['verdict'][:90]}", flush=True)
        rows.append(rec)
    fetcher.close()
    out = {"audited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "workbook": os.path.basename(reg.path),
           "policy": "ratified URL requested byte for byte; redirects followed one hop at a time on the same host only; "
                     "a cross-host redirect is recorded and refused; one request per URL; no crawling",
           "rows": rows}
    with open(FETCH_AUDIT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"-> {FETCH_AUDIT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
