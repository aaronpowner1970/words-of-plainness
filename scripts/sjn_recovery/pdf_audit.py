"""PDF extraction audit (Task 1c, 2026-09-13) — NO MODEL CALLS.

  python scripts/sjn_recovery/pdf_audit.py [--rows BSR-AN-04,BSR-AN-05,...] [--all-pdf] [--live-fetch]

Three chunkings of every audited row are compared, all through the row's own adapter and the same
fetch cache (nothing is fetched anew unless --live-fetch):

  LEGACY    the extraction path the Roman Catholic and Anglican branches ran on: PyMuPDF text, line-break
            de-hyphenation only — what the agents actually saw;
  REPAIRED  the path since 2026-09-13 (sources.Ctx.repair_pdf_text): soft-hyphen line breaks joined,
            page furniture stripped per page before joining, de-hyphenation, intra-word splits repaired
            on vocabulary evidence;
  STORED    the chunk store as it stands now (what the next branch will run on).

Per row the report gives: how the corpus is actually sourced (the registry's fetch_mode says "PDF" for
two rows whose adapters read HTML pages — measured, not read); the raw PDF facts (pages, soft-hyphen
and hard-hyphen line breaks, the running headers / footers the detector finds with page counts); the
LEGACY chunks' defects (intra-word split candidates, furniture lines spliced inside chunk text);
LEGACY -> REPAIRED diff (chunks changed, added, removed, before/after samples — the effect of the
fixes); REPAIRED vs STORED (must be identical once the row is re-chunked); every intra-word join made,
with its evidence; and for BSR-MW-03 the author's own check that Article I reads "of infinite power,
wisdom, and good".

Verdicts: AFFECTED (LEGACY and REPAIRED differ — the row needed re-chunking; STORE_MATCHES says
whether it has been), CLEAN (identical), NO_TEXT (no corpus by policy), HTML_SOURCED (not a PDF text
layer; scanned anyway, unchanged by the PDF fixes).
Writes data-sources/sjn/recovery-runs/pdf-audit.json and pdf-audit.md. Nothing here writes to the workbook."""
import argparse
import difflib
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_pipeline.fetch import Fetcher, pdf_text  # noqa: E402
from sjn_recovery.config import FETCH_CACHE, RUNS_DIR  # noqa: E402
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery import sources, store  # noqa: E402
from sjn_recovery.textutil import (intraword_split_candidates, page_furniture_lines, _furniture_key, dehyphenate)  # noqa: E402

DEFAULT_ROWS = ["BSR-AN-04", "BSR-AN-05", "BSR-LU-02", "BSR-RP-04", "BSR-MW-03", "BSR-MA-01", "BSR-MA-02"]
ALL_PDF_EXTRA = ["BSR-EO-08", "BSR-EO-09"]
MW03_ARTICLE_I = "of infinite power, wisdom, and good"
NL = chr(10)


def log(m):
    print(m, flush=True)


class LegacyCtx(sources.Ctx):
    """The extraction path before 2026-09-13: de-hyphenation only (no soft-hyphen join, no furniture
    stripping, no intra-word repair). Reproduces what the earlier branch runs were chunked from."""

    def repair_pdf_text(self, raw):
        self.hyphenation = getattr(self, "hyphenation", {})
        return dehyphenate(raw, stats=self.hyphenation)

    def extraction_notes(self):
        return []


def _snip(text, needle, width=70):
    i = text.casefold().find(needle.casefold())
    if i < 0:
        return None
    return text[max(0, i - width):i + len(needle) + width]


def furniture_splices(chunks, furniture_keys):
    """Chunks whose text carries a detected running header / footer INSIDE it (not as its opening
    heading). Prose that merely repeats a heading's words is counted too — the diff is the decisive
    measure; this is the symptom count."""
    out = []
    for c in chunks:
        folded = _furniture_key(c["text"])
        for k in furniture_keys:
            if k == "#" or len(k) < 4:
                continue
            j = folded.find(k)
            if j > 0:
                out.append({"locator": c["locator"], "furniture": k, "context": _snip(c["text"], k.replace("#", "").strip(), 60) or c["text"][:160]})
                break
    return out


def chunk_row(reg, row, fetcher, ctx_cls):
    rid = row["registry_id"]
    fn = sources.ADAPTERS.get(rid)
    ctx = ctx_cls(row, fetcher, log=lambda m: None, config=reg.config, admitted_hosts=reg.domains(rid))
    chunks, notes = fn(ctx)
    chunks = store.dedupe_locators(chunks)
    sources.dehyphenate_chunks(chunks)
    return chunks, notes, ctx


def diff_chunks(old, new, samples_max=8):
    o = {c["locator"]: c["text"] for c in old}
    n = {c["locator"]: c["text"] for c in new}
    changed, samples = [], []
    for loc in n:
        if loc in o and o[loc] != n[loc]:
            changed.append(loc)
            if len(samples) < samples_max:
                sm = difflib.SequenceMatcher(None, o[loc], n[loc])
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != "equal":
                        samples.append({"locator": loc, "before": o[loc][max(0, i1 - 45):i2 + 45], "after": n[loc][max(0, j1 - 45):j2 + 45]})
                        break
    return {"chunks_old": len(old), "chunks_new": len(new), "changed": len(changed), "changed_locators": changed[:60],
            "added": [l for l in n if l not in o][:20], "removed": [l for l in o if l not in n][:20],
            "text_hash_old": store.standard_hash(old) if old else None, "text_hash_new": store.standard_hash(new) if new else None,
            "samples": samples}


def audit_row(reg, rid, fetcher, manifest):
    row = reg.by_id.get(rid)
    rec = {"registry_id": rid, "branch": row["branch"] if row else None, "standard_title": row["standard_title"][:90] if row else None,
           "fetch_mode_in_registry": row.get("fetch_mode") if row else None, "canonical_url": row["canonical_url"] if row else None,
           "manifest_status": (manifest.get("standards", {}).get(rid) or {}).get("status")}
    if not row:
        rec["verdict"] = "NOT_RATIFIED"; return rec
    if rid in sources.NO_TEXT:
        rec["source_kind"] = "NO_TEXT_BY_POLICY"; rec["policy"] = sources.NO_TEXT[rid][1]
        rec["verdict"] = "NO_TEXT"
        rec["note"] = "no PDF text is extracted for this row: nothing to splice, nothing to audit beyond the policy"
        return rec
    stored = store.load_chunks(rid)
    rec["stored_chunks"] = len(stored)
    urls = (manifest.get("standards", {}).get(rid) or {}).get("urls") or []
    modes = sorted({u.get("mode") for u in urls})
    rec["fetch_modes_recorded"] = modes
    is_pdf = "pdf" in modes
    rec["source_kind"] = "PDF_TEXT_LAYER" if is_pdf else ("HTML" if modes else "UNKNOWN")
    furniture_keys = []
    if is_pdf:
        fr = fetcher.get(row["canonical_url"])
        rec["pdf_fetch"] = {"status": fr.status, "ok": fr.ok, "from_cache": bool(getattr(fr, "from_cache", False)), "error": fr.error}
        if fr.ok and fr.pdf_bytes:
            raw = pdf_text(fr.pdf_bytes)
            pages = raw.split(chr(12))
            found, _ = page_furniture_lines(pages)
            rec["pdf"] = {"pages": len(pages), "chars": len(raw),
                          "soft_hyphens_total": raw.count(chr(0xAD)),
                          "soft_hyphen_line_breaks": len(re.findall(chr(0xAD) + r"[ \t]*\r?\n", raw)),
                          "hard_hyphen_line_breaks": len(re.findall(r"[A-Za-z]-[ \t]*\r?\n[ \t]*[a-z]", raw)),
                          "furniture_top_first_pass": dict(sorted(found["top"].items(), key=lambda kv: -kv[1])),
                          "furniture_bottom_first_pass": dict(sorted(found["bottom"].items(), key=lambda kv: -kv[1]))}
            furniture_keys = list(found["top"]) + list(found["bottom"])
    try:
        legacy, _, _ = chunk_row(reg, row, fetcher, LegacyCtx)
        repaired, notes, ctx = chunk_row(reg, row, fetcher, sources.Ctx)
    except sources.FetchError as e:
        rec["error"] = str(e); rec["verdict"] = "REBUILD_FAILED"
        return rec
    cv = ctx.corpus_vocabulary() if is_pdf else set()
    if is_pdf:
        # the stacked-furniture keys the repaired path actually removed (all peeling rounds), for the splice scan
        furniture_keys = sorted(set(furniture_keys) | set(ctx.furniture.get("top", {})) | set(ctx.furniture.get("bottom", {})))
    rec["legacy"] = {"chunks": len(legacy), "text_hash": store.standard_hash(legacy) if legacy else None,
                     "intraword_split_candidates": intraword_split_candidates(NL.join(c["text"] for c in legacy), corpus_vocab=cv),
                     "furniture_splices": furniture_splices(legacy, furniture_keys)}
    rec["legacy"]["chunks_with_furniture_inside_text"] = len(rec["legacy"]["furniture_splices"])
    rec["legacy"]["furniture_splice_samples"] = rec["legacy"]["furniture_splices"][:8]
    del rec["legacy"]["furniture_splices"]
    rec["repaired"] = {"chunks": len(repaired), "text_hash": store.standard_hash(repaired) if repaired else None,
                       "extraction_notes": ctx.extraction_notes(), "adapter_notes": notes,
                       "intraword_joins": getattr(ctx, "intraword_joins", []),
                       "furniture_removed": getattr(ctx, "furniture", None),
                       "residual_intraword_candidates": intraword_split_candidates(NL.join(c["text"] for c in repaired), corpus_vocab=cv),
                       "chunks_with_furniture_inside_text": len(furniture_splices(repaired, furniture_keys))}
    rec["legacy_to_repaired"] = diff_chunks(legacy, repaired)
    rec["repaired_vs_stored"] = diff_chunks(repaired, stored, samples_max=2)
    rec["store_matches_repaired"] = (rec["repaired_vs_stored"]["changed"] == 0 and not rec["repaired_vs_stored"]["added"]
                                     and not rec["repaired_vs_stored"]["removed"] and len(stored) == len(repaired))
    if rid == "BSR-MW-03":
        rec["mw03_article_i"] = {"phrase": MW03_ARTICLE_I,
                                 "in_legacy_chunks": [c["locator"] for c in legacy if MW03_ARTICLE_I in c["text"]],
                                 "in_repaired_chunks": [c["locator"] for c in repaired if MW03_ARTICLE_I in c["text"]],
                                 "in_stored_chunks": [c["locator"] for c in stored if MW03_ARTICLE_I in c["text"]],
                                 "goodness_variant_in_repaired": sum(1 for c in repaired if "wisdom, and goodness" in c["text"]),
                                 "article_i_text": next((c["text"] for c in repaired if c["locator"].startswith("Articles of Religion, Article I ")), None)}
    d = rec["legacy_to_repaired"]
    if d["changed"] or d["added"] or d["removed"]:
        rec["verdict"] = "AFFECTED"
    else:
        rec["verdict"] = "CLEAN" if is_pdf else "HTML_SOURCED"
    return rec


def write_md(report, path):
    L = ["# PDF extraction audit (Task 1c) — " + report["audited_at"], "",
         f"Workbook {report['workbook']}; rows {', '.join(report['rows'])}; fetch cache {'REUSED' if not report['live_fetch'] else 'LIVE'}. No model calls.",
         "LEGACY = the extraction path the earlier branches ran on; REPAIRED = the path since 2026-09-13; STORED = the chunk store now.", "",
         "| row | measured source | verdict | chunks | LEGACY intra-word splits | LEGACY chunks with furniture inside text | LEGACY→REPAIRED chunks changed | intra-word joins made | store matches REPAIRED |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in report["per_row"]:
        lg, rp, d = r.get("legacy") or {}, r.get("repaired") or {}, r.get("legacy_to_repaired") or {}
        L.append(f"| {r['registry_id']} | {r.get('source_kind', '')} | **{r['verdict']}** | {lg.get('chunks', 0)} | "
                 f"{len(lg.get('intraword_split_candidates', []))} | {lg.get('chunks_with_furniture_inside_text', 0)} | "
                 f"{d.get('changed', '—')} (+{len(d.get('added', []))}/−{len(d.get('removed', []))} locators) | {len(rp.get('intraword_joins', []))} | "
                 f"{'yes' if r.get('store_matches_repaired') else ('n/a' if 'store_matches_repaired' not in r else 'NO')} |")
    L.append("")
    for r in report["per_row"]:
        L.append(f"## {r['registry_id']} — {r.get('standard_title')}")
        L.append(f"- registry fetch_mode: `{r.get('fetch_mode_in_registry')}`; measured source: **{r.get('source_kind')}**; manifest status {r.get('manifest_status')}")
        if r.get("policy"):
            L.append(f"- policy: {r['policy']}")
        if r.get("pdf"):
            p = r["pdf"]
            L.append(f"- PDF: {p['pages']} pages, {p['chars']:,} chars; soft-hyphen line breaks {p['soft_hyphen_line_breaks']} "
                     f"(soft hyphens total {p['soft_hyphens_total']}); hard-hyphen line breaks {p['hard_hyphen_line_breaks']}")
            L.append(f"- furniture detected (first pass) — top: {p['furniture_top_first_pass']}")
            L.append(f"- furniture detected (first pass) — bottom: {p['furniture_bottom_first_pass']}")
        lg = r.get("legacy")
        if lg:
            L.append(f"- LEGACY chunks: {len(lg['intraword_split_candidates'])} intra-word split candidate(s) "
                     f"{[(x['a'], x['b'], x['pairs'], x['evidence']) for x in lg['intraword_split_candidates']][:16]}; "
                     f"{lg['chunks_with_furniture_inside_text']} chunk(s) carry a furniture line inside their text")
            for sp in lg["furniture_splice_samples"][:5]:
                L.append(f"    - {sp['locator'][:60]}: …{sp['context']}…")
        rp = r.get("repaired")
        if rp:
            for n in rp.get("extraction_notes", []):
                L.append(f"- REPAIRED: {n[:700]}")
            if rp.get("residual_intraword_candidates"):
                L.append(f"- residual intra-word candidates after repair: {rp['residual_intraword_candidates']}")
            L.append(f"- REPAIRED chunks with a furniture line inside their text: {rp['chunks_with_furniture_inside_text']} (prose mentions of a heading's words count here too)")
        d = r.get("legacy_to_repaired")
        if d:
            L.append(f"- LEGACY → REPAIRED: {d['chunks_old']} -> {d['chunks_new']} chunks; {d['changed']} changed, {len(d['added'])} locator(s) added, "
                     f"{len(d['removed'])} removed; text_hash {str(d['text_hash_old'])[:12]} -> {str(d['text_hash_new'])[:12]}")
            for smp in d["samples"][:6]:
                L.append(f"    - {smp['locator'][:50]}: `{smp['before'][:130]}` → `{smp['after'][:130]}`")
            L.append(f"- REPAIRED vs STORED: {'identical' if r.get('store_matches_repaired') else 'DIFFERENT — re-chunk needed'}")
        if r.get("mw03_article_i"):
            m = r["mw03_article_i"]
            L.append(f"- **Article I check**: '{m['phrase']}' in LEGACY {m['in_legacy_chunks']}; in REPAIRED {m['in_repaired_chunks']}; in STORED {m['in_stored_chunks']}; "
                     f"'wisdom, and goodness' in REPAIRED: {m['goodness_variant_in_repaired']} (must be 0)")
        if r.get("error"):
            L.append(f"- rebuild FAILED: {r['error']}")
        L.append(f"- verdict: **{r['verdict']}**")
        L.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=",".join(DEFAULT_ROWS))
    ap.add_argument("--all-pdf", action="store_true", help="also audit the other PDF rows (BSR-EO-08, BSR-EO-09)")
    ap.add_argument("--live-fetch", action="store_true", help="fetch the ratified URLs anew instead of reusing the fetch cache")
    ap.add_argument("--workbook")
    a = ap.parse_args()
    rows = [r.strip() for r in a.rows.split(",") if r.strip()]
    if a.all_pdf:
        rows += [r for r in ALL_PDF_EXTRA if r not in rows]
    reg = Registry(a.workbook)
    manifest = store.load_manifest()
    fetcher = Fetcher(FETCH_CACHE, reuse_cache=not a.live_fetch, strict_host=True)
    report = {"audited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "workbook": os.path.basename(reg.path),
              "rows": rows, "live_fetch": a.live_fetch, "model_calls": 0, "per_row": []}
    for rid in rows:
        log(f"-- auditing {rid}")
        rec = audit_row(reg, rid, fetcher, manifest)
        report["per_row"].append(rec)
        d = rec.get("legacy_to_repaired") or {}
        lg = rec.get("legacy") or {}
        log(f"   {rec['verdict']}: source {rec.get('source_kind')}; LEGACY splits {len(lg.get('intraword_split_candidates', []))}, "
            f"furniture-in-text {lg.get('chunks_with_furniture_inside_text', 0)}; LEGACY->REPAIRED changed {d.get('changed', '—')}; "
            f"store matches {rec.get('store_matches_repaired', 'n/a')}")
    fetcher.close()
    report["affected_rows"] = [r["registry_id"] for r in report["per_row"] if r["verdict"] == "AFFECTED"]
    report["rows_needing_rechunk"] = [r["registry_id"] for r in report["per_row"] if r.get("store_matches_repaired") is False]
    os.makedirs(RUNS_DIR, exist_ok=True)
    jp = os.path.join(RUNS_DIR, "pdf-audit.json")
    with open(jp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    write_md(report, os.path.join(RUNS_DIR, "pdf-audit.md"))
    log(f"== affected rows: {report['affected_rows']}; store still differs for: {report['rows_needing_rechunk']}; report -> {jp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
