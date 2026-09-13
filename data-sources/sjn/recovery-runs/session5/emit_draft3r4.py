"""Session 5 (2026-09-13): emit WoP_SJN_BranchSourceRegistries_Draft3r4_20260913.csv into wop-scratch.

All 47 Branch Source Registry rows exactly as the workbook v2.25r4 holds them, plus two columns: `r4_change` (the fields
this draft changes, ';'-separated; empty = unchanged) and `r4_change_note`. Only BSR-BA-02 and BSR-LU-02 change.
The workbook is read, never written."""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_recovery.registry import Registry  # noqa: E402

OUT = r"C:\Users\aaron\Documents\wop-scratch\WoP_SJN_BranchSourceRegistries_Draft3r4_20260913.csv"
HERE = os.path.dirname(os.path.abspath(__file__))

ba = json.load(open(os.path.join(HERE, "task1a-ba02-fetch.json"), encoding="utf-8"))
_lu_path = os.path.join(HERE, "task2a-lu02-pdf-audit.json")
# first emission (before the 2a audit exists) carries the URL change only; the script is re-run after the audit
lu = json.load(open(_lu_path, encoding="utf-8")) if os.path.exists(_lu_path) else {
    "fetch": {"status": "?", "final_url": "?", "bytes": 0, "magic": "?", "font_objects": "?"}, "pdf": {"pages": "?"},
    "extract": {"raw_chars": 0, "chunks": "?", "chars": 0}}
www = ba["https://www.the1689confession.com/1689/chapter-2"]
bare = ba["https://the1689confession.com/1689/chapter-2"]

CHANGES = {
    "BSR-BA-02": {
        "canonical_url": "https://www.the1689confession.com/1689/chapter-2",
        "fetch_mode": "HTML",
        "note": ("canonical_url moved to the www form. The prior URL https://the1689confession.com/1689/chapter-2 answers HTTP "
                 f"{bare['status']} to https://www.the1689confession.com/1689/chapter-2 — the same path on the same registrable domain "
                 "(the1689confession.com), a www-label-only redirect. fetch_mode stays HTML: verified 2026-09-13 by the Gate 6 strict "
                 f"fetcher (Code, requests), www URL HTTP {www['status']}, {www['body_bytes_utf8']:,} bytes of decoded body re-encoded UTF-8, "
                 f"'most pure spirit' in the raw body: {www['has_most_pure_spirit']}; adapter london_1689_ch2 extracts "
                 f"{ba['extract']['chunks']} paragraph chunks ({ba['extract']['chars']:,} chars). Independently observed by Cowork through "
                 "the in-app browser (HTTP 200, 108,906 bytes)."),
    },
    "BSR-LU-02": {
        "canonical_url": "https://files.lcms.org/dl/f/the-augsburg-confession",
        "fetch_mode": "PDF - text layer present (publisher Download href; same-host 302 to /api/download/file/the-augsburg-confession, served application/octet-stream)",
        "note": ("canonical_url moved from the document-library viewer page (files.lcms.org/file/preview/96D5ADA9-…, a React shell with "
                 "no text) to the viewer's own Download href, which serves the artifact. Not proposed for retirement. Verified "
                 f"2026-09-13 by the Gate 6 strict fetcher: HTTP {lu['fetch']['status']} after one same-host 302 to "
                 f"{lu['fetch']['final_url']}, {lu['fetch']['bytes']:,} bytes, magic {lu['fetch']['magic']}, {lu['fetch']['font_objects']} /Font "
                 f"objects, {lu['pdf']['pages']} pages; text layer {lu['extract']['raw_chars']:,} chars; adapter augsburg_confession_lcms "
                 f"{lu['extract']['chunks']} chunks ({lu['extract']['chars']:,} chars), Articles I–XXVIII intact, running header "
                 "'Page N of 27' stripped on all 27 pages, publisher address footer dropped, no furniture in any chunk (pdf audit "
                 "recovery-runs/session5/task2a-lu02-pdf-audit.json). The text is the Triglot translation also carried by BSR-LU-01's "
                 "Augsburg Confession pages; this row adds the LCMS as the body that publishes it. Independently observed by Cowork "
                 "(HTTP 200, 378,071 bytes, %PDF-1.6)."),
    },
}


def main():
    reg = Registry()
    fields = [k for k in reg.rows_all[0].keys() if k != "__row"]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields + ["r4_change", "r4_change_note"])
        w.writeheader()
        for r in reg.rows_all:
            row = {k: r.get(k, "") for k in fields}
            ch = CHANGES.get(r["registry_id"])
            if ch:
                changed = [f for f in ("canonical_url", "fetch_mode") if (row.get(f) or "") != ch[f]]
                row.update({f: ch[f] for f in ("canonical_url", "fetch_mode")})
                row["r4_change"] = ";".join(changed)
                row["r4_change_note"] = ch["note"]
            w.writerow(row)
    print(f"wrote {OUT}: {len(reg.rows_all)} rows; changed {sorted(CHANGES)}")


if __name__ == "__main__":
    main()
