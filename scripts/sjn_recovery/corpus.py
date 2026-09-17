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
from sjn_recovery.config import FETCH_CACHE, ensure_dirs, CHROMA_COLLECTION, EMBED_MODEL, CHROMA_PATH, RETIRED_HOSTS  # noqa: E402
from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery import sources, provenance, store  # noqa: E402


def log(msg):
    print(msg, flush=True)


def keep_unyielded_entries(results, prev, only):
    """Session 13: on a --only build, copy into `results` (unchanged) every previous manifest entry whose row the registry did not
    yield this time — e.g. BSR-EO-03, which R6-3 retires in memory. Returns the ids kept. A full build (only is None) keeps none."""
    if not only:
        return []
    kept = [rid for rid in prev if rid not in results]
    merged = {rid: (results[rid] if rid in results else prev[rid]) for rid in prev}      # the manifest keeps its order
    merged.update({rid: r for rid, r in results.items() if rid not in merged})
    results.clear()
    results.update(merged)
    return kept


def build(args):
    ensure_dirs()
    reg = Registry(args.workbook, registry_delta=args.registry_delta)
    manifest = store.load_manifest()
    prev = manifest.get("standards", {})
    # strict_host: the ratified URL is fetched byte for byte; a redirect onto another host is refused.
    fetcher = Fetcher(FETCH_CACHE, reuse_cache=args.reuse_cache, strict_host=True)
    only = set(args.only.split(",")) if args.only else None
    results, drift, halted, dropped = {}, [], False, []
    log(f"== SJN Gate 6 corpus build — workbook {os.path.basename(reg.path)} ({reg.app_master_version}); "
        f"{len(reg.rows)} AUTHOR_RATIFIED rows; fetch cache {'REUSED' if args.reuse_cache else 'LIVE'}; "
        f"gate metric {reg.gate_metric}; routing {reg.verifier_routing}; lateran scope {reg.lateran_iv_scope}")
    if reg.delta:
        log(f"!! registry delta applied in memory (workbook NOT written): {reg.delta['file']} sha256 {reg.delta['sha256'][:12]} rows {reg.delta['rows']}")
    if reg.vocabulary_violations:
        log(f"!! reception_scope outside the ratified vocabulary: {reg.vocabulary_violations}")
    for row in reg.rows:
        rid = row["registry_id"]
        base = {"branch": row["branch"], "standard_title": row["standard_title"], "canonical_url": row["canonical_url"],
                "authority_tier": row["authority_tier"], "reception_scope": (row.get("reception_scope") or "").upper(),
                "witness_only": reg.is_witness(rid), "citation_refusal": reg.citation_refusal(rid)}
        if row.get("_registry_delta"):
            base["registry_delta"] = row["_registry_delta"]      # built on a draft URL pending the author's ratification (session 5)
        if only and rid not in only:
            results[rid] = prev.get(rid, {"status": "SKIPPED"})
            continue
        t0 = time.time()
        if rid in sources.NO_TEXT:
            kind, note = sources.NO_TEXT[rid]
            results[rid] = {"status": kind, **base, "n_chunks": 0, "text_hash": None, "notes": [note],
                            "fetch_verdict": "NO_TEXT_BY_POLICY"}
            log(f"-- {rid} {kind}: {note[:110]}")
            continue
        retired = sources.retired_host(row.get("canonical_url", ""))
        if retired:
            results[rid] = {"status": "HOST_RETIRED", **base, "n_chunks": 0, "text_hash": None, "notes": [retired],
                            "fetch_verdict": "HOST_RETIRED: never requested"}
            dropped.append(rid)
            log(f"-- {rid} HOST_RETIRED: {retired[:100]}")
            continue
        adm = reg.admission(rid)
        if adm["refused"]:
            results[rid] = {"status": "ROW_REFUSED_R001", **base, "n_chunks": 0, "text_hash": None, "notes": [adm["reason"]],
                            "fetch_verdict": "R001: row admits no host"}
            dropped.append(rid)
            log(f"-- {rid} ROW_REFUSED_R001: {adm['reason'][:110]}")
            continue
        fn = sources.ADAPTERS.get(rid)
        if not fn:
            results[rid] = {"status": "NO_ADAPTER", **base, "n_chunks": 0, "text_hash": None, "notes": [], "fetch_verdict": "FETCHER (no adapter)"}
            log(f"-- {rid} NO_ADAPTER"); continue
        ctx = sources.Ctx(row, fetcher, log, config=reg.config, admitted_hosts=reg.domains(rid))
        log(f"-- {rid} {row['branch']} — {row['standard_title'][:70]}  [admitted hosts: {', '.join(reg.domains(rid))}]")
        try:
            chunks, notes = fn(ctx)
        except sources.RetiredHostError as e:
            results[rid] = {"status": "HOST_RETIRED", **base, "n_chunks": 0, "text_hash": None, "notes": [str(e)], "urls": ctx.urls,
                            "fetch_verdict": "HOST_RETIRED: never requested"}
            dropped.append(rid)
            log(f"   RETIRED HOST (refused): {e}"); continue
        except sources.HostNotAdmittedError as e:
            results[rid] = {"status": "HOST_NOT_ADMITTED", **base, "n_chunks": 0, "text_hash": None, "notes": [str(e)], "urls": ctx.urls,
                            "fetch_verdict": "R001: the adapter asked for a host the row does not admit; refused, nothing chunked"}
            dropped.append(rid)
            log(f"   HOST NOT ADMITTED (refused): {e}"); continue
        except sources.RedirectError as e:
            results[rid] = {"status": "HOST_REDIRECTS_CROSS_HOST", **base, "n_chunks": 0, "text_hash": None,
                            "notes": [str(e)], "urls": ctx.urls, "fetch_verdict": "HOST: the ratified URL answers with a redirect onto a different host"}
            log(f"   REDIRECT (refused): {e}"); continue
        except sources.BlockedError as e:
            results[rid] = {"status": "FETCH_BLOCKED", **base, "n_chunks": 0, "text_hash": None,
                            "notes": [str(e)], "urls": ctx.urls, "fetch_verdict": "HOST: refuses automated fetch (403 / bot challenge)"}
            log(f"   BLOCKED: {e}"); continue
        except sources.FetchError as e:
            results[rid] = {"status": "FETCH_FAILED", **base, "n_chunks": 0, "text_hash": None,
                            "notes": [str(e)], "urls": ctx.urls, "fetch_verdict": "see notes"}
            log(f"   FAILED: {e}"); continue
        chunks = store.dedupe_locators(chunks)
        notes.extend(n for n in ctx.extraction_notes() if n not in notes)
        hyph = sources.dehyphenate_chunks(chunks)
        if hyph["changed"] or hyph["residue"]:
            notes.append(f"de-hyphenation at extraction: {hyph['stats']} in {hyph['changed']} chunk(s); "
                         f"residue (suspended hyphens, left as printed): {hyph['residue'][:8]}")
        h = store.standard_hash(chunks)
        old = prev.get(rid, {})
        status = "BUILT"
        if old.get("text_hash") and old["text_hash"] != h:
            drift.append((rid, old["text_hash"][:12], h[:12], old.get("n_chunks"), len(chunks)))
            status = "REBUILT (drift accepted)" if args.accept_drift else "DRIFT"
        elif old.get("text_hash") == h:
            status = "UNCHANGED"
        chars = sum(len(c["text"]) for c in chunks)
        results[rid] = {"status": status, **base, "fetch_mode": row["fetch_mode"],
                        "fallback_only": reg.is_fallback(rid), "n_chunks": len(chunks), "chars": chars,
                        "text_hash": h, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "urls": ctx.urls, "notes": notes, "fetch_verdict": "OK",
                        "noncitable_spans": sum(len(c.get("noncitable_spans") or []) for c in chunks),
                        "languages": sorted({c.get("language", "en") for c in chunks}),
                        "polytonic_chunks": sum(1 for c in chunks if c.get("polytonic")),
                        "_chunks": chunks}
        log(f"   {status}: {len(chunks)} chunks, {chars:,} chars, {len(ctx.urls)} fetch(es), {time.time() - t0:.1f}s; {notes[0] if notes else ''}")
        if rid == "BSR-EO-05":
            log("   provenance: diffing decrees against the Robertson 1899 edition (archive.org OCR)")
            # The archive.org edition is an AUTHORITY REFERENCE only (never chunked, not a registry row):
            # archive.org/download answers with a 302 onto its own CDN host (dnNNN.eu.archive.org), which
            # the strict registry fetcher rightly refuses. The reference is fetched with hops allowed and
            # every hop recorded here, so the provenance record says exactly where the OCR came from.
            prov_fetcher = Fetcher(os.path.join(FETCH_CACHE, "provenance"), reuse_cache=False, strict_host=False)
            fr = prov_fetcher.get(provenance.ROBERTSON_DJVU)
            prov_fetcher.close()
            if not fr.ok:
                results[rid]["provenance"] = {"verdict": "HALT", "note": f"archive.org OCR fetch failed: {fr.error}",
                                              "redirects": list(fr.redirects or [])}
            else:
                decrees = [(c["locator"], c["text"]) for c in chunks if c["division"] == "decree"]
                results[rid]["provenance"] = provenance.check(decrees, fr.html)
                results[rid]["provenance"]["fetched_from"] = fr.final_url
                results[rid]["provenance"]["redirects"] = list(fr.redirects or [])
            pv = results[rid]["provenance"]
            log(f"   provenance verdict: {pv['verdict']} — matched {pv.get('matched')} / checked {pv.get('decrees_checked')}, "
                f"divergent {pv.get('divergent')}, unanchored {pv.get('unanchored')}")
            for d in pv.get("per_decree", []):
                if d["status"] != "MATCH":
                    log(f"      {d['locator']}: {d['status']} ratio={d.get('ratio')}")
            if pv["verdict"] != "PASS":
                halted = True
    fetcher.close()
    # session 13 (Codex F.10; session 12 report section 4.7): a --only build rewrites the manifest from the rows the registry
    # yields, so a row the registry now filters out (BSR-EO-03, retired in memory by R6-3) silently lost its entry. Such rows keep
    # their previous manifest entry, unchanged; a full build still writes only the rows the registry yields.
    kept_from_manifest = keep_unyielded_entries(results, prev, only)
    if kept_from_manifest:
        log(f"   --only: kept the manifest entries of rows the registry no longer yields: {sorted(kept_from_manifest)}")

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
    for rid in dropped:                    # retired / refused rows: no chunk file, no embeddings
        p_ = os.path.join(store.CHUNK_DIR, f"{rid}.json")
        if os.path.exists(p_):
            os.remove(p_); log(f"   dropped cached chunks for {rid}")
        if col is not None:
            try:
                col.delete(where={"registry_id": rid})
            except Exception:
                pass
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
        "app_config": {k: str(reg.config.get(k)) for k in ("gate6_threshold_metric", "authority_tier_rank", "reception_scope_vocabulary",
                                                          "reception_axis", "creed_tier_resolution", "lateran_iv_scope", "verifier_routing",
                                                          "dialogue_text_policy", "encyclical_1848_status", "registry_fallback_only_rows",
                                                          "controlled_storage_policy")},
        "opus_slice_rows": sorted(reg.opus_slice_rows()),
        "fetch_policy": "strict_host: ratified URLs fetched byte for byte; cross-host redirects refused except a www-label-only hop "
                        "(sjn_pipeline.fetch.STRICT_HOST_REDIRECT_RULE, session 5); every requested URL must sit on a "
                        "host the row admits under R001 (publisher_domain / AC-15); retired hosts are never requested",
        "retired_hosts": dict(RETIRED_HOSTS),
        "controlled_storage_policy": str(reg.config.get("controlled_storage_policy") or ""),
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
    b.add_argument("--registry-delta", help="draft registry CSV whose r4_change rows are applied in memory (never written to the workbook)")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "build":
        return build(args)
    return status(args)


if __name__ == "__main__":
    sys.exit(main())
