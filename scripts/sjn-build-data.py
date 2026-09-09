#!/usr/bin/env python3
"""Seeking Jesus of Nazareth — Gate 2 data pipeline.

Reads the controlled workbook (formula mode), re-executes P001–P031 from raw
sheets, live-fetches every public URL, asserts every quoted phrase inside its
locator scope, and emits static JSON under src/_data/sjn/. Any BLOCK failure
exits non-zero and (by default) refuses to overwrite the emitted data.

Usage:
  python scripts/sjn-build-data.py                    # live run against newest workbook in data-sources/sjn/
  python scripts/sjn-build-data.py --reuse-cache      # dev: reuse cached fetches (fetch_policy=CACHE-REUSED)
  python scripts/sjn-build-data.py --workbook PATH --out src/_data/sjn
  python scripts/sjn-build-data.py --write-on-fail    # emit even when blocking rules fail (never for commit)
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from sjn_pipeline.model import load_context, recompute_author_workflow, ratification_decision  # noqa: E402
from sjn_pipeline.assertions import build_targets, collect_public_urls, Runner  # noqa: E402
from sjn_pipeline.fetch import Fetcher, is_rendered_host, HOST_WHITELIST, ROBOTS_EXCEPTIONS  # noqa: E402
from sjn_pipeline.rules import run_rules  # noqa: E402
from sjn_pipeline import emit  # noqa: E402
from sjn_pipeline.workbook import s  # noqa: E402
from sjn_pipeline.textnorm import style_flags  # noqa: E402

PIPELINE_VERSION = "1.0.0"
EMITTED_FILES = ["meta.json", "predicates.json", "cells.json", "inferences.json", "godhead.json",
                 "vectors.json", "clarifications.json", "glossary.json", "ranges.json"]


def log(msg):
    print(msg, flush=True)


def dump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook")
    ap.add_argument("--out", default=os.path.join(ROOT, "src", "_data", "sjn"))
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, ".cache", "sjn"))
    ap.add_argument("--reuse-cache", action="store_true", help="reuse cached fetches (dev only)")
    ap.add_argument("--write-on-fail", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    wb_path = args.workbook or sorted(glob.glob(os.path.join(ROOT, "data-sources", "sjn", "*.xlsx")))[-1]
    t0 = time.time()
    log(f"== SJN Gate 2 pipeline v{PIPELINE_VERSION}")
    log(f"   workbook: {wb_path}")
    ctx = load_context(wb_path)
    version = s(ctx.config.get("app_master_version"))
    log(f"   app_master_version: {version}; build_date: {s(ctx.config.get('build_date'))}")

    # ---- author workflow recompute (P027–P031, P015)
    decisions, gates = recompute_author_workflow(ctx)
    rat = {d["id"].replace("AUTH-RAT-", ""): ratification_decision(d) for d in decisions if d["id"].startswith("AUTH-RAT-")}
    all83 = {s(r["ID"]): r for r in ctx.all83}
    propagation_issues = []
    for pid, rd in rat.items():
        if rd["decision"] == "REVISE" and rd["custom_response"]:
            for part in [p.strip() for p in rd["custom_response"].split("|")]:
                if "→" not in part:
                    continue
                field, val = [x.strip() for x in part.split("→", 1)]
                f = field.casefold()
                target = None
                if f.startswith("summary"):
                    target = s(all83.get(pid, {}).get("Plain-language teaching summary"))
                elif f.startswith("caution"):
                    target = s(all83.get(pid, {}).get("Key caution / nuance"))
                if target is not None and target != val:
                    propagation_issues.append({"id": pid, "field": field, "custom": val, "all83": target})
    rat_counts = {"total": len(rat), "approve": sum(r["decision"] == "APPROVE" for r in rat.values()),
                  "revise": sum(r["decision"] == "REVISE" for r in rat.values()),
                  "hold": sum(r["decision"] == "HOLD" for r in rat.values()),
                  "pending": sum(r["decision"] == "PENDING" for r in rat.values()),
                  "auto_approved": sum(1 for r in rat.values() if r["decision"] != "PENDING" and not (r["initials"] and r["date"]))}
    log(f"   author workflow: {len(decisions)} decisions; ratification {rat_counts}")
    for g in gates:
        log(f"   gate {g['gate'].split(' — ')[0]}: {g['status']} (resolved {g['resolved']}/{g['ready']}, holds {g['holds']})")

    # ---- canonical hash (P014)
    h1, n1 = ctx.wb.canonical_hash(ctx.hash_recipe)
    h2, _ = ctx.wb.canonical_hash(ctx.hash_recipe)
    declared = ctx.build_metadata.get("declared_hash", "")
    coverage_gaps = []
    for label, sheet, rng, kind in ctx.hash_recipe:
        ws = ctx.wb.ws(sheet)
        last = int(rng.split(":")[1].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        if ws.max_row > last and any(ws.cell(r, 1).value for r in range(last + 1, ws.max_row + 1)):
            coverage_gaps.append(f"{sheet}: recipe rows end at {last}, sheet has content to row {ws.max_row}")
    canonical = {"hash": h1, "bytes": n1, "deterministic": h1 == h2, "declared": declared, "matches_declared": h1 == declared,
                 "recipe": [{"label": a, "sheet": b_, "range": c, "kind": d} for a, b_, c, d in ctx.hash_recipe],
                 "coverage_gaps": coverage_gaps,
                 "note": ("Declared hash is the v2.14 snapshot; Build Metadata v2.15/v2.16 rows instruct the pipeline to "
                          "recompute. Recomputed hash is stamped as canonical for this build." if h1 != declared else "matches declared")}
    log(f"   canonical hash: {h1} ({n1} bytes) declared={declared[:12]}… match={h1 == declared}")

    # ---- targets + fetch
    targets = build_targets(ctx)
    urls = collect_public_urls(ctx, targets)
    rendered_urls = {t.url for t in targets if t.extraction == "RENDERED"}
    log(f"   phrase targets: {len(targets)} ({sum(t.status == 'ASSERT' for t in targets)} ASSERT); distinct public URLs: {len(urls)}")
    fetcher = Fetcher(args.cache_dir, reuse_cache=args.reuse_cache)
    runner = Runner(fetcher, log)
    log("== P006 live fetch")
    runner.fetch_all(urls, rendered_urls, workers=args.workers)
    log("== phrase assertions (P018/P019/P020/P021/P025 + supplements)")
    for t in targets:
        runner.run_assertion(t)
        mark = {"PASS": "ok  ", "FAIL": "FAIL", "SKIP": "skip"}[t.result]
        log(f"  {mark} {t.kind:<13} {t.key:<8} {t.role:<12} {t.scope_mode:<20} {t.detail[:70]}")
    fetcher.close()

    # ---- clarification-source drop policy (handoff 2026-09-09): a source that cannot be confirmed
    # inside its cited locator is dropped from its case, never the case itself, and reported loudly.
    for t in targets:
        if t.kind == "CLARIFICATION" and t.result != "PASS" and (t.conditional or t.page_hit):
            t.dropped = True
            log(f"  DROP {t.key} from {t.role}: {t.detail}")

    # ---- emit objects
    cells, branches, lineage_ids = emit.build_cells(ctx, targets)
    predicates, style1 = emit.build_predicates(ctx, targets, decisions)
    inferences, inf_checks = emit.build_inferences(ctx, cells)
    godhead = emit.build_godhead(ctx, decisions)
    vectors = emit.build_vectors(ctx, cells)
    clar = emit.build_clarifications(ctx, decisions, targets)
    glossary, style2 = emit.build_glossary(ctx)
    ranges = emit.build_ranges(ctx, inferences, cells)
    style = style1 + style2
    for g in godhead:
        for f in ("proposition", "teaching_use", "caution"):
            for flag in style_flags(g[f]):
                style.append({"file": "godhead.json", "id": g["id"], "field": f, "flag": flag})
    for v in vectors:
        for flag in style_flags(v["caption"]):
            style.append({"file": "vectors.json", "id": v["family_id"], "field": "caption", "flag": flag})
    for i in inferences:
        for f in ("direct_observation", "defensible_inference", "alternative_interpretation", "does_not_support", "interactive_prompt"):
            for flag in style_flags(i[f]):
                style.append({"file": "inferences.json", "id": i["id"], "field": f, "flag": flag})
        for e in i["evidence_links"]:
            for f in ("why", "caveat"):
                for flag in style_flags(e[f]):
                    style.append({"file": "inferences.json", "id": e["id"], "field": f, "flag": flag})
    for p in predicates:
        if p["citation"]:
            for f in ("label", "source"):
                for flag in style_flags(p["citation"]["restoration"][f]):
                    style.append({"file": "predicates.json", "id": p["id"], "field": f"citation.restoration.{f}", "flag": flag})
            for flag in style_flags(p["citation"]["scope_note"]):
                style.append({"file": "predicates.json", "id": p["id"], "field": "citation.scope_note", "flag": flag})
        if p["restoration"]:
            for f in ("novelty_caution", "evidence_note"):
                for flag in style_flags(p["restoration"][f]):
                    style.append({"file": "predicates.json", "id": p["id"], "field": f"restoration.{f}", "flag": flag})
    for c in cells:
        if c["evidence"]:
            for f in ("scope_control", "source_note"):
                for flag in style_flags(c["evidence"][f]):
                    style.append({"file": "cells.json", "id": c["id"], "field": f"evidence.{f}", "flag": flag})
    for case in clar["cases"]:
        for f in ("learner_question", "key_distinction", "resolution_summary", "internal_variation", "interfaith_significance", "does_not_prove", "learner_cue_copy"):
            for flag in style_flags(case[f]):
                style.append({"file": "clarifications.json", "id": case["id"], "field": f, "flag": flag})
    emitted_counts = {"inference_checks": inf_checks, "branch_summary": branches, "lineage_only_ids": lineage_ids,
                      "ratification": rat_counts, "vector_cards": sum(p["card_mode"] == "VECTOR" for p in predicates)}

    # ---- rules
    results = run_rules(ctx, targets, runner, decisions, gates, canonical, propagation_issues, emitted_counts)
    blocking = [r for r in results if r["severity"] == "BLOCK" and r["status"] == "FAIL"]
    gates_open = [r for r in results if r["status"] == "GATE-OPEN"]
    supp = [t for t in targets if t.kind == "QUEUE-CELL"]
    supp_fail = [t for t in supp if t.status == "ASSERT" and t.result != "PASS"]
    results.append({"rule": "QUEUE-CELL", "severity": "BLOCK", "status": "FAIL" if supp_fail else "PASS",
                    "expected": "every released non-case-study queue-cell phrase target in Case Study Phrase Targets passes",
                    "actual": f"{len(supp) - len(supp_fail)}/{len(supp)} (" + ", ".join(f"{t.key} {t.role}" for t in supp) + ")",
                    "detail": str([(t.key, t.role, t.detail) for t in supp_fail])})
    if supp_fail:
        blocking.append(results[-1])
    replaced = [t for t in targets if t.kind == "RESTORATION" and "RECHECK" in t.note]
    results.append({"rule": "RECHECK-REPLACED", "severity": "BLOCK", "status": "PASS" if all(t.result == "PASS" for t in replaced) else "FAIL",
                    "expected": "all author-replaced Restoration phrases re-verified", "actual": f"{sum(t.result == 'PASS' for t in replaced)}/{len(replaced)}",
                    "detail": ", ".join(f"{t.key}={t.result}" for t in replaced)})
    if results[-1]["status"] == "FAIL":
        blocking.append(results[-1])
    mism = [t for t in targets if t.kind == "CLARIFICATION" and t.dropped and not t.conditional]
    results.append({"rule": "LOCATOR-MISMATCH", "severity": "WARN", "status": "PASS" if not mism else "WARN",
                    "expected": "every clarification source phrase sits inside its cited locator",
                    "actual": f"{len(mism)} source(s) dropped pending workbook locator correction",
                    "detail": "; ".join(f"{t.key} ({t.role}) locator {t.locator!r}: {t.detail}" for t in mism)})
    cond = [t for t in targets if t.kind == "CLARIFICATION" and t.conditional]
    results.append({"rule": "CONDITIONAL-SOURCES", "severity": "INFO", "status": "PASS" if all(t.result == "PASS" for t in cond) else "WARN",
                    "expected": "PENDING FETCH clarification sources confirmed by rendered fetch (else dropped from the case)",
                    "actual": ", ".join(f"{t.key}={t.result}" for t in cond) or "none",
                    "detail": "; ".join(f"{t.key}: {t.detail}" for t in cond)})

    log("== rule results")
    for r in results:
        log(f"  {r['status']:<10} {r['rule']:<16} expected={str(r['expected'])[:40]:<42} actual={str(r['actual'])[:70]}")
        if r["status"] in ("FAIL", "GATE-OPEN") and r["detail"]:
            log(f"             {r['detail'][:300]}")
    status = "PASS" if not blocking else "FAIL"
    log(f"== BUILD {status}: {len(blocking)} blocking failures; {len(gates_open)} gates open; style flags {len(style)}")

    meta = {
        "app": "Seeking Jesus of Nazareth",
        "pipeline_version": PIPELINE_VERSION,
        "app_master_version": version,
        "build_date": s(ctx.config.get("build_date")),
        "pipeline_run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - t0, 1),
        "workbook_file": os.path.basename(wb_path),
        "workbook_sha256": ctx.wb.file_sha256,
        "canonical_hash": canonical["hash"],
        "canonical": canonical,
        "status": status,
        "blocking_failures": len(blocking),
        "gates_open": [r["rule"] for r in gates_open],
        "fetch_policy": "CACHE-REUSED" if fetcher.cache_hits else "LIVE",
        "fetch_cache_hits": fetcher.cache_hits,
        "policies": {
            "canonical_research_source": s(ctx.config.get("canonical_research_source")),
            "runtime_database_policy": s(ctx.config.get("runtime_database_policy")),
            "full_branch_map_enabled": s(ctx.config.get("full_branch_map_enabled")).casefold() == "true",
            "external_validation": s(ctx.config.get("external_validation")),
            "missingness_visible": True,
            "vector_card_mode": s(ctx.config.get("vector_card_mode")),
            "clarification_runtime_mode": s(ctx.config.get("clarification_runtime_mode")),
            "h43_orthodox_status": s(ctx.config.get("h43_orthodox_status")),
            "h37_orthodox_status": s(ctx.config.get("h37_orthodox_status")),
            "row_ratification_status": s(ctx.config.get("row_ratification_status")),
            "style": "Latter-day Saint, never LDS/Mormon in learner-facing copy (flags below are reported, not rewritten)",
        },
        "counts": {
            "predicates": len(predicates), "inherited": sum(p["corpus"] == "inherited" for p in predicates),
            "restoration": sum(p["corpus"] == "restoration" for p in predicates),
            "cells": len(cells), "certified_cells": sum(c["certified"] for c in cells),
            "released_result_cells": sum(c["metric_class"] != "EXCLUDED" for c in cells),
            "lineage_only_cells": len(lineage_ids), "inferences": len(inferences), "godhead": len(godhead),
            "vectors": len(vectors), "clarification_cases": len(clar["cases"]),
            "phrase_assertions": {k: {"total": sum(1 for t in targets if t.kind == k and t.status == "ASSERT" and not t.dropped),
                                      "pass": sum(1 for t in targets if t.kind == k and t.result == "PASS" and not t.dropped),
                                      "dropped": sum(1 for t in targets if t.kind == k and t.dropped)}
                                  for k in ("HISTORICAL", "RESTORATION", "CASE-STUDY", "CLARIFICATION", "QUEUE-CELL")},
            "distinct_public_urls": len(urls),
        },
        "author_workflow": {"decisions": len(decisions), "gates": gates,
                            "needs_attention": sum(d["needs_attention"] for d in decisions),
                            "holds": [d["id"] for d in decisions if d["status"] == "HOLD"],
                            "future_blocked": [d["id"] for d in decisions if d["status"] == "BLOCKED"]},
        "rules": results,
        "assertions": [t.public() for t in targets],
        "fetch_log": runner.fetch_log(),
        "host_whitelist": HOST_WHITELIST,
        "robots_exceptions": ROBOTS_EXCEPTIONS,
        "propagation_issues": propagation_issues,
        "queue_cell_targets": [t.public() for t in targets if t.kind == "QUEUE-CELL"],
        "conditional_sources": [t.public() for t in targets if t.kind == "CLARIFICATION" and t.conditional],
        "dropped_sources": [t.public() for t in targets if t.kind == "CLARIFICATION" and t.dropped],
        "style_flags": style,
        "schema": {
            "predicates.json": "{predicates:[83 records: id, corpus, family, predicate, mode, code|authority_tier, lens, summary, caution, ratification, card_mode, vector, inherited, citation{historical,restoration}, restoration, sentence{clause,text,rule}, card{clauses[4],text}]}",
            "cells.json": "{cells:[456: id, family_id, branch, rendered_state, metric_class, institution_tag(+basis), certified, lineage_only, evidence|null, lineage|null, case_study_target, phrase_targets], branch_summary:[8 partition rows, counts only]}",
            "inferences.json": "{inferences:[13: id, theme, metric, stat{count,denominator,percent,range|null,provisional,badge}, texts, evidence_links]}",
            "godhead.json": "{panels:[GOD-01..04, not_counted:true]}",
            "vectors.json": "{families:[H07,H32,H56: caption, atomic_layer_summary, branch_layers]}",
            "clarifications.json": "{policy, cases[ICC-001, ICC-002: … sources, dropped_sources], triggers (deterministic), deferred_triggers, vocabulary, release_summary}",
            "glossary.json": "{terms, hazard_types(10), rendered_states}",
            "ranges.json": "{ranges{metric_key: stat from Sensitivity Ranges sheet}, inference_stats{INF-xx}, sjn_stat_contract, denominators, not_counted_layers}",
        },
    }

    if status == "FAIL" and not args.write_on_fail:
        log("!! blocking failures — emitted data NOT written (use --write-on-fail to inspect output)")
        rep = os.path.join(args.cache_dir, "last-run-meta.json")
        dump(rep, meta)
        log(f"   diagnostic meta written to {rep}")
        return 1

    os.makedirs(args.out, exist_ok=True)
    files = {
        "predicates.json": {"app_master_version": version, "canonical_hash": h1, "predicates": predicates},
        "cells.json": {"app_master_version": version, "canonical_hash": h1, "cells": cells, "branch_summary": branches},
        "inferences.json": {"app_master_version": version, "canonical_hash": h1, "inferences": inferences, "recompute_checks": inf_checks},
        "godhead.json": {"app_master_version": version, "canonical_hash": h1, "panels": godhead},
        "vectors.json": {"app_master_version": version, "canonical_hash": h1, "families": vectors},
        "clarifications.json": {"app_master_version": version, "canonical_hash": h1, **clar},
        "glossary.json": {"app_master_version": version, "canonical_hash": h1, **glossary},
        "ranges.json": {"app_master_version": version, "canonical_hash": h1, **ranges},
    }
    for name, obj in files.items():
        dump(os.path.join(args.out, name), obj)
    meta["files"] = {name: {"sha256": sha256_file(os.path.join(args.out, name)), "bytes": os.path.getsize(os.path.join(args.out, name))}
                     for name in files}
    dump(os.path.join(args.out, "meta.json"), meta)
    log(f"   wrote {len(files) + 1} files to {args.out}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
