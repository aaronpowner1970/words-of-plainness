"""Corpus builder CLI (Gate 6 §3) — deterministic, idempotent, drift-halting.

  python scripts/sjn_recovery/corpus.py build [--reuse-cache] [--only BSR-XX-NN,...] [--accept-drift] [--no-chroma]
  python scripts/sjn_recovery/corpus.py status

Reads the AUTHOR_RATIFIED rows of the Branch Source Registry, fetches each standard once, splits it by
its own divisions, stores chunk JSON (.cache, gitignored) and the ChromaDB collection `sjn_confessions`
(internal only), and commits the manifest with one text_hash per standard. A changed text_hash halts
the run and reports which standard drifted. The Dositheus provenance diff runs once at build.
Never writes to the workbook."""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_pipeline.fetch import Fetcher  # noqa: E402
from sjn_recovery.config import FETCH_CACHE, ensure_dirs, CHROMA_COLLECTION, EMBED_MODEL, CHROMA_PATH  # noqa: E402
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery import sources, provenance, store  # noqa: E402


def log(msg):
    print(msg, flush=True)


def build(args):
    ensure_dirs()
    reg = Registry(args.workbook)
    manifest = store.load_manifest()
    prev = manifest.get("standards", {})
    fetcher = Fetcher(FETCH_CACHE, reuse_cache=args.reuse_cache)
    only = set(args.only.split(",")) if args.only else None
    results, drift, halted = {}, [], False
    log(f"== SJN Gate 6 corpus build — workbook {os.path.basename(reg.path)} ({reg.app_master_version}); "
        f"{len(reg.rows)} AUTHOR_RATIFIED rows; fetch cache {'REUSED' if args.reuse_cache else 'LIVE'}")
    for row in reg.rows:
        rid = row["registry_id"]
        if only and rid not in only:
            results[rid] = prev.get(rid, {"status": "SKIPPED"})
            continue
        t0 = time.time()
        if rid in sources.NO_TEXT:
            kind, note = sources.NO_TEXT[rid]
            results[rid] = {"status": kind, "branch": row["branch"], "standard_title": row["standard_title"],
                            "canonical_url": row["canonical_url"], "n_chunks": 0, "text_hash": None, "notes": [note]}
            log(f"-- {rid} {kind}: {note[:110]}")
            continue
        fn = sources.ADAPTERS.get(rid)
        if not fn:
            results[rid] = {"status": "NO_ADAPTER", "branch": row["branch"], "n_chunks": 0, "text_hash": None, "notes": []}
            log(f"-- {rid} NO_ADAPTER"); continue
        ctx = sources.Ctx(row, fetcher, log)
        log(f"-- {rid} {row['branch']} — {row['standard_title'][:70]}")
        try:
            chunks, notes = fn(ctx)
        except sources.BlockedError as e:
            results[rid] = {"status": "FETCH_BLOCKED", "branch": row["branch"], "standard_title": row["standard_title"],
                            "canonical_url": row["canonical_url"], "n_chunks": 0, "text_hash": None,
                            "notes": [str(e)], "urls": ctx.urls}
            log(f"   BLOCKED: {e}"); continue
        except sources.FetchError as e:
            results[rid] = {"status": "FETCH_FAILED", "branch": row["branch"], "standard_title": row["standard_title"],
                            "canonical_url": row["canonical_url"], "n_chunks": 0, "text_hash": None,
                            "notes": [str(e)], "urls": ctx.urls}
            log(f"   FAILED: {e}"); continue
        chunks = store.dedupe_locators(chunks)
        h = store.standard_hash(chunks)
        old = prev.get(rid, {})
        status = "BUILT"
        if old.get("text_hash") and old["text_hash"] != h:
            drift.append((rid, old["text_hash"][:12], h[:12], old.get("n_chunks"), len(chunks)))
            status = "REBUILT (drift accepted)" if args.accept_drift else "DRIFT"
        elif old.get("text_hash") == h:
            status = "UNCHANGED"
        chars = sum(len(c["text"]) for c in chunks)
        results[rid] = {"status": status, "branch": row["branch"], "standard_title": row["standard_title"],
                        "canonical_url": row["canonical_url"], "fetch_mode": row["fetch_mode"],
                        "fallback_only": reg.is_fallback(rid), "n_chunks": len(chunks), "chars": chars,
                        "text_hash": h, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "urls": ctx.urls, "notes": notes, "_chunks": chunks}
        log(f"   {status}: {len(chunks)} chunks, {chars:,} chars, {len(ctx.urls)} fetch(es), {time.time() - t0:.1f}s; {notes[0] if notes else ''}")
        if rid == "BSR-EO-05":
            log("   provenance: diffing decrees against the Robertson 1899 edition (archive.org OCR)")
            fr = fetcher.get(provenance.ROBERTSON_DJVU)
            if not fr.ok:
                results[rid]["provenance"] = {"verdict": "HALT", "note": f"archive.org OCR fetch failed: {fr.error}"}
            else:
                decrees = [(c["locator"], c["text"]) for c in chunks if c["division"] == "decree"]
                results[rid]["provenance"] = provenance.check(decrees, fr.html)
            pv = results[rid]["provenance"]
            log(f"   provenance verdict: {pv['verdict']} — matched {pv.get('matched')} / checked {pv.get('decrees_checked')}, "
                f"divergent {pv.get('divergent')}, unanchored {pv.get('unanchored')}")
            for d in pv.get("per_decree", []):
                if d["status"] != "MATCH":
                    log(f"      {d['locator']}: {d['status']} ratio={d.get('ratio')}")
            if pv["verdict"] != "PASS":
                halted = True
    fetcher.close()

    if drift and not args.accept_drift:
        log("!! TEXT DRIFT — run halted, nothing written (re-run with --accept-drift after review):")
        for rid, a, b, n0, n1 in drift:
            log(f"   {rid}: {a}… -> {b}… (chunks {n0} -> {n1})")
        report = {"halted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "drift": drift}
        with open(os.path.join(os.path.dirname(store.MANIFEST_PATH), "corpus-drift-report.json"), "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
        return 2
    if halted:
        log("!! Dositheus provenance check did not pass — run halted, nothing written")
        return 3

    # write chunks + chroma
    col = None
    if not args.no_chroma:
        if store.ollama_available():
            col = store.chroma_collection()
        else:
            log(f"!! Ollama/{EMBED_MODEL} unavailable — chunk JSON written, Chroma skipped (retrieval falls back to BM25)")
    n_total = 0
    for rid, r in results.items():
        chunks = r.pop("_chunks", None)
        if chunks is None:
            continue
        if r["status"] == "UNCHANGED" and not args.force_embed and os.path.exists(os.path.join(store.CHUNK_DIR, f"{rid}.json")):
            n_total += len(chunks)
            continue
        store.save_chunks(rid, chunks)
        n_total += len(chunks)
        if col is not None:
            store.upsert_standard(col, rid, chunks, log)
    manifest = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workbook": os.path.basename(reg.path), "app_master_version": reg.app_master_version,
        "registry_ratified": len(reg.rows), "fallback_only_rows": sorted(reg.fallback_ids),
        "chroma": {"path": CHROMA_PATH, "collection": CHROMA_COLLECTION, "embedding_model": EMBED_MODEL,
                   "written": col is not None},
        "policy": "Chunks are internal only (never emitted to the site). URLs live in the manifest and chunk store; "
                  "agents receive text and locators only. text_hash drift halts the build.",
        "standards": results, "total_chunks": sum(r.get("n_chunks") or 0 for r in results.values()),
    }
    store.save_manifest(manifest)
    log(f"== corpus: {n_total} chunks across {sum(1 for r in results.values() if r.get('n_chunks'))} standards; manifest -> {store.MANIFEST_PATH}")
    by_status = {}
    for r in results.values():
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    log(f"   statuses: {by_status}")
    return 0


def status(args):
    m = store.load_manifest()
    print(f"built_at={m.get('built_at')} workbook={m.get('workbook')} total_chunks={m.get('total_chunks')}")
    for rid, r in m.get("standards", {}).items():
        print(f"  {rid:<10} {r.get('status'):<32} chunks={r.get('n_chunks', 0):<5} {r.get('branch', '')}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--workbook")
    b.add_argument("--reuse-cache", action="store_true")
    b.add_argument("--only")
    b.add_argument("--accept-drift", action="store_true")
    b.add_argument("--no-chroma", action="store_true")
    b.add_argument("--force-embed", action="store_true")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "build":
        return build(args)
    return status(args)


if __name__ == "__main__":
    sys.exit(main())
