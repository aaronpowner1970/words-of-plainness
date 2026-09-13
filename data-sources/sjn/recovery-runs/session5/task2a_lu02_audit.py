"""Session 5 Task 2a: BSR-LU-02 through the session-3 pdf-audit discipline — no model calls.

Fetches https://files.lcms.org/dl/f/the-augsburg-confession LIVE with the Gate 6 strict fetcher, records the fetch facts,
runs scripts/sjn_recovery/pdf_audit.py's audit_row on the row (LEGACY vs REPAIRED chunkings, furniture detection and
splices, intra-word split candidates) with the Draft3r4 delta applied in memory, and adds the checks Task 2a asks for:
text length, chunk count, whether Articles I–XXVIII are intact, and whether any page header / footer reaches a chunk.
Writes task2a-lu02-pdf-audit.json beside this script."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_pipeline.fetch import Fetcher, pdf_text  # noqa: E402
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery import pdf_audit, sources, store  # noqa: E402
from sjn_recovery.config import FETCH_CACHE  # noqa: E402

DELTA = r"C:\Users\aaron\Documents\wop-scratch\WoP_SJN_BranchSourceRegistries_Draft3r4_20260913.csv"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII",
         "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII"]
# one sentence per article opening, as printed; each must stand verbatim (normalised) in exactly the article's chunk(s)
SPOT = {"I": "eternal, without body, without parts, of infinite power, wisdom, and goodness",
        "III": "the Word, that is, the Son of God, did assume the human nature",
        "IV": "men cannot be justified before God by their own strength, merits, or works",
        "VII": "one holy Church is to continue forever",
        "XVII": "Christ will appear for judgment",
        "XXVIII": "There has been great controversy concerning the Power of Bishops"}
FURNITURE = [r"\bPage \d+ of 27\b", r"Back to top", r"©", r"Kirkwood", r"infocenter@lcms\.org", r"www\.lcms\.org", chr(0x2029), chr(0x2028),
             r"(?:^|\s)\d{1,3}\]"]


def main():
    reg = Registry(registry_delta=DELTA)
    row = reg.by_id["BSR-LU-02"]
    fetcher = Fetcher(FETCH_CACHE, reuse_cache=False, strict_host=True)
    fr = fetcher.get(row["canonical_url"])
    b = fr.pdf_bytes or b""
    import fitz
    doc = fitz.open(stream=b, filetype="pdf") if b else None
    raw = pdf_text(b) if b else ""
    rec = {"registry_id": "BSR-LU-02", "registry_delta": row.get("_registry_delta"),
           "fetch": {"url": row["canonical_url"], "status": fr.status, "ok": fr.ok, "error": fr.error, "final_url": fr.final_url,
                     "redirects": fr.redirects, "cross_host_redirect": fr.cross_host_redirect, "content_type": fr.content_type,
                     "robots": fr.robots, "bytes": len(b), "magic": b[:8].decode("latin-1"), "font_objects": b.count(b"/Font"),
                     "fetched_at": fr.fetched_at, "instrument": "Code: sjn_pipeline.fetch.Fetcher (python requests), strict_host"},
           "pdf": {"pages": len(doc) if doc else 0, "metadata": dict(doc.metadata) if doc else None,
                   "u2029_separators_in_text_layer": raw.count(chr(0x2029))}}
    if not (fr.ok and b[:5] == b"%PDF-" and raw.strip()):
        rec["verdict"] = "STOP: the text layer did not extract"
        json.dump(rec, open(os.path.join(HERE, "task2a-lu02-pdf-audit.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(rec["verdict"]); return 1
    # the session-3 instrument (fetch cache now holds the live fetch above)
    cached = Fetcher(FETCH_CACHE, reuse_cache=True, strict_host=True)
    audit = pdf_audit.audit_row(reg, "BSR-LU-02", cached, store.load_manifest())
    chunks, notes, ctx = pdf_audit.chunk_row(reg, row, cached, sources.Ctx)
    text_all = "\n".join(c["text"] for c in chunks)
    articles = {}
    for r in ROMAN:
        locs = [c["locator"] for c in chunks if re.match(rf"Augsburg Confession: Article {r}: ", c["locator"])]
        articles[r] = {"chunks": len(locs), "locators": locs}
    spot = {}
    for r, phrase in SPOT.items():
        hits = [c["locator"] for c in chunks if phrase in " ".join(c["text"].split())]
        spot[r] = {"phrase": phrase, "found_in": hits, "in_the_right_article": bool(hits) and all(f"Article {r}: " in h for h in hits)}
    contamination = []
    for c in chunks:
        for pat in FURNITURE:
            for m in re.finditer(pat, c["text"]):
                contamination.append({"locator": c["locator"], "pattern": pat, "context": c["text"][max(0, m.start() - 50):m.end() + 30]})
    lu01 = {c["locator"]: " ".join(c["text"].split()) for c in store.load_chunks("BSR-LU-01") if c["locator"].startswith("Augsburg Confession")}
    same_text = 0
    for c in chunks:
        t = " ".join(c["text"].split())
        if any(t[:120] in v for v in lu01.values()):
            same_text += 1
    rec.update({
        "extract": {"raw_chars": len(raw), "chunks": len(chunks), "chars": sum(len(c["text"]) for c in chunks),
                    "adapter_notes": notes, "extraction_notes": ctx.extraction_notes(),
                    "divisions": sorted({c["locator"].split(",")[0] for c in chunks}, key=lambda x: x)},
        "articles_I_to_XXVIII": {"present": sum(1 for r in ROMAN if articles[r]["chunks"]), "of": len(ROMAN),
                                 "missing": [r for r in ROMAN if not articles[r]["chunks"]], "per_article": articles},
        "article_spot_checks": spot,
        "furniture_or_footer_in_chunks": contamination,
        "session3_audit": {k: audit.get(k) for k in ("verdict", "source_kind", "pdf", "legacy", "repaired", "legacy_to_repaired")},
        "overlap_with_BSR_LU_01": {"lu02_chunks_whose_opening_120_chars_stand_in_an_LU01_augsburg_chunk": same_text, "of": len(chunks),
                                   "lu01_augsburg_chunks": len(lu01),
                                   "reading": "the same Triglot translation: LU-02 adds the LCMS as the publishing body, not new wording"},
    })
    ok = (rec["articles_I_to_XXVIII"]["present"] == 28 and all(v["in_the_right_article"] for v in spot.values()) and not contamination)
    rec["verdict"] = "EXTRACTS: text layer intact, Articles I–XXVIII present, no header or footer in any chunk" if ok else "REVIEW: see failures"
    json.dump(rec, open(os.path.join(HERE, "task2a-lu02-pdf-audit.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: rec[k] for k in ("fetch", "verdict")}, indent=1, ensure_ascii=False))
    print("pages", rec["pdf"]["pages"], "| raw chars", len(raw), "| chunks", len(chunks), "| chars", rec["extract"]["chars"],
          "| articles", rec["articles_I_to_XXVIII"]["present"], "/28 | spot", {k: v["in_the_right_article"] for k, v in spot.items()},
          "| contamination", len(contamination), "| same-text-as-LU-01", same_text, "/", len(chunks))
    print("session-3 audit verdict", audit.get("verdict"), "| legacy furniture-in-text", (audit.get("legacy") or {}).get("chunks_with_furniture_inside_text"),
          "| repaired furniture-in-text", (audit.get("repaired") or {}).get("chunks_with_furniture_inside_text"),
          "| residual intraword", len((audit.get("repaired") or {}).get("residual_intraword_candidates") or []),
          "| joins", len((audit.get("repaired") or {}).get("intraword_joins") or []))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
