"""Calibration harness (spec §6) — run BEFORE any live run.

  python scripts/sjn_recovery/calibrate.py run    --run-id cal-3 --locator-model sonnet --verifier-models sonnet,opus [--seed-from cal-2]
  python scripts/sjn_recovery/calibrate.py plant  --run-id cal-3 --verifier-models sonnet,opus [--seed-from cal-2]
  python scripts/sjn_recovery/calibrate.py report --run-id cal-3 [--compare cal-2]

`run` takes the released cells (A / A-SF / Q / D) and the reviewed-empty cells with their locators
HIDDEN (the agents never see the workbook's document/locator/phrase), runs locator + verifier, and
records per cell what was found. `plant` runs the verifier over the planted near-miss fixture
(calibration/planted-near-misses.json) — every ACCEPT there is a false accept. `report` scores the
three recall metrics per branch and per verifier model, gates on the metric APP CONFIG names
(`gate6_threshold_metric`), scores false-accept with the Dositheus slice separate, and writes
recovery-runs/calibration-report.md.

cal-3 (v2.25): retrieval is per standard (agents.py), the verifier routing is SONNET_WITH_OPUS_SLICE
(the primary judges every candidate; the adjudicator judges the slice and every cell the primary
rejected outright), and the report scores the PRIMARY alone and the ROUTED outcome side by side.

With the batch backend a phase stops when calls are pending; execute the jobs and re-run the same
command to continue. Nothing here writes to the workbook."""
import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, CALIBRATION_DIR, BRANCHES, ensure_dirs, MODEL_IDS, FETCH_AUDIT_PATH  # noqa: E402
from sjn_recovery.registry import (Registry, load_predicates, load_comparators, load_queue, released_cells,  # noqa: E402
                                   reviewed_empty_cells, TIER_RANK, bare_tier, tier_rank)
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner, ACCEPTS  # noqa: E402
from sjn_recovery import guards, prompts, store  # noqa: E402

THRESH_RECALL = 0.8
THRESH_FALSE_ACCEPT = 0.05
PLANTED_PATH = os.path.join(CALIBRATION_DIR, "planted-near-misses.json")
ROUTED = "routed"

# Released cells whose cited text lies outside the ratified scope of every row in its branch are excluded
# from the recall denominator. cal-2 excluded Q-449 (Lateran IV canon 2); APP CONFIG lateran_iv_scope =
# EXTEND_TO_CONSTITUTION_2 (v2.25) brings it back into scope, so the set is empty and n = 141.
OUT_OF_RATIFIED_SCOPE = {}

# Rows carrying an author caveat that must travel with any winning candidate (AC-03, AC-05).
CAVEATED_ROWS = {
    "BSR-EO-04": "AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian "
                 "catechism, not a pan-Orthodox conciliar standard.",
    "BSR-EO-05": "AC-05 / AC-12 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod), "
                 "reception CONTESTED between Orthodox jurisdictions; the disagreement is recorded, not resolved.",
}

# FIX 7 — flagged, not fixed. The released cell's asserted phrase came from the old OCA page and exists in
# neither ratified source; the author chooses the wording in Gate 7.
PHRASE_REQUIRES_RECUT = {
    "Q-434": {
        "released_phrase": "without change, without confusion, without division, without separation",
        "released_source": "OCA church-history page (the pre-v2.25 BSR-EO-06 source)",
        "options": [
            {"registry_id": "BSR-EO-06", "wording": "unconfusedly, immutably, indivisibly, inseparably", "translation": "Percival, NPNF2-14 (controlling conciliar text)"},
            {"registry_id": "BSR-EO-11", "wording": "inconfusedly, unchangeably, indivisibly, inseparably", "translation": "Patriarchate of Antioch page (WITNESS only)"},
        ],
    },
}

FIX1_CELLS = ["Q-291", "Q-331", "Q-339", "Q-333", "Q-341", "Q-349"]
PER_STANDARD_ROWS = ["BSR-LU-01", "BSR-AN-01", "BSR-AN-05"]


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ equivalence: existing cell -> registry ids
def equivalent_registry_ids(cell):
    """Which registry standards carry the same text the released cell cites (by host/path)."""
    u = (cell["text_url"] or cell["authority_url"] or "").casefold()
    host = urlparse(u).netloc.replace("www.", "")
    path = urlparse(u).path
    if host == "churchofengland.org":
        return {"BSR-AN-01"} if "articles-religion" in path else {"BSR-AN-03", "BSR-AN-02"}
    if host == "ccel.org":
        return {"BSR-EO-06"} if "npnf214" in path else {"BSR-AN-03"}
    if host == "bfm.sbc.net":
        return {"BSR-BA-01"}
    if host == "oca.org":
        if "the-symbol-of-faith" in path or "symbol-of-faith" in path:
            return {"BSR-EO-01"}
        if "the-holy-trinity" in path:
            return {"BSR-EO-02"}
        if "church-history" in path:
            return {"BSR-EO-06"}          # the councils' definitions: v2.25 re-sourced BSR-EO-06 to Percival
        return {"BSR-EO-01", "BSR-EO-02", "BSR-EO-06"}
    if host == "newadvent.org":
        return {"BSR-EO-13"}                # v2.25r2: its own LINEAGE row (Q-034); no longer prose inside BSR-EO-06
    if host == "goarch.org":
        return set()                        # host retired 2026-09-12: no ratified corpus stands behind the citation
    if host == "acrod.org":
        return {"BSR-EO-07"}
    if host == "goarchdiocese.ca":
        return {"BSR-EO-14"}
    if host == "irp.cdn-website.com":
        return {"BSR-MW-03"}
    if host == "roea.org":
        return {"BSR-EO-09"} if "synodikon" in path.casefold() else {"BSR-EO-08"}
    if host == "holycouncil.org":
        return {"BSR-EO-10"}
    if host == "antiochpatriarchate.org":
        return {"BSR-EO-11"}
    if host == "immspartis.gr":
        return {"BSR-EO-12"}
    if host == "bookofconcord.org":
        return {"BSR-LU-01"}
    if host == "mennoniteusa.org":
        return {"BSR-MA-01"}
    if host == "umc.org":
        return {"BSR-MW-01"} if "articles-of-religion" in path else {"BSR-MW-02"}
    if host == "globalmethodist.org":
        return {"BSR-MW-03"}
    if host == "opc.org":
        return {"BSR-RP-01"} if "wcf" in path else {"BSR-RP-02"} if "/sc" in path else {"BSR-RP-03"}
    if host == "pcusa.org":
        return {"BSR-RP-04"}
    if host == "crcna.org":
        return {"BSR-RP-06"} if "belgic" in path else {"BSR-RP-05"}
    if host == "vatican.va":
        if "compendium" in path:
            return {"BSR-RC-07"}
        if "the_credo" in path:
            return {"BSR-RC-06"}
        return {"BSR-RC-01"}
    if host == "vaticannews.va":
        return {"BSR-RC-06"}
    if host == "ewtn.com":
        return {"BSR-RC-03", "BSR-RC-02"}
    if host == "sourcebooks.web.fordham.edu":
        return {"BSR-RC-04"}
    if host == "papalencyclicals.net":
        return {"BSR-RC-04"}
    return set()


def _nums(s_):
    out = set(re.findall(r"\b\d{1,4}\b", s_))
    for m in re.findall(r"\b([IVXL]{1,7})\b", s_):
        out.add(m)
    return out


def same_division(cell_locator, cand_locator):
    """Loose test: the candidate's division shares a numeral or a key title word with the cell's locator."""
    a, b = cell_locator.casefold(), cand_locator.casefold()
    na, nb = _nums(cell_locator), _nums(cand_locator)
    if na & nb:
        return True
    words_a = {w for w in re.findall(r"[a-z]{5,}", a) if w not in ("article", "articles", "chapter", "clause", "clauses", "section", "paragraph")}
    words_b = set(re.findall(r"[a-z]{5,}", b))
    return bool(words_a & words_b)


# ------------------------------------------------------------------ cell selection
def calibration_cells(queue):
    return released_cells(queue), reviewed_empty_cells(queue)


def hidden(cell):
    """The locator input: the cell with its evidence fields removed (locators hidden)."""
    return {k: cell[k] for k in ("queue_id", "family_id", "predicate", "family_code", "branch", "rendered_state")}


def _llm(args, reg):
    llm = LLM(args.run_id, backend=args.backend, model=args.locator_model, log=log)
    if getattr(args, "seed_from", None):
        llm.seed_from(args.seed_from, log)
    return llm


# ------------------------------------------------------------------ run
def cmd_run(args):
    ensure_dirs()
    reg = Registry(args.workbook)
    preds = load_predicates(reg.wb)
    comps = load_comparators(reg.wb)
    queue = load_queue(reg.wb)
    rel, emp = calibration_cells(queue)
    cells = rel + emp
    if args.branch:
        cells = [c for c in cells if c["branch"] == args.branch]
    if args.only:
        keep = set(args.only.split(","))
        cells = [c for c in cells if c["queue_id"] in keep]
    if args.limit:
        cells = cells[:args.limit]
    vmodels = args.verifier_models.split(",")
    llm = _llm(args, reg)
    state_dir = os.path.join(RUNS_DIR, args.run_id, "cells")
    runner = CellRunner(llm, reg, preds, comps, state_dir, args.locator_model, vmodels, log=log, run_coder=False)
    done = pending = 0
    for c in cells:
        st = runner.run_cell(hidden(c))
        if st.get("phase") == "DONE":
            done += 1
        else:
            pending += 1
    meta = {"run_id": args.run_id, "kind": "calibration", "workbook": os.path.basename(reg.path), "app_master_version": reg.app_master_version,
            "locator_model": args.locator_model, "verifier_models": vmodels, "primary": runner.primary, "adjudicator": runner.adjudicator,
            "routing": runner.routing, "slice_rows": sorted(runner.slice_rows), "gate_metric": reg.gate_metric,
            "tier_rank": reg.tier_rank_list, "lateran_iv_scope": reg.lateran_iv_scope, "creed_tier_resolution": reg.creed_tier_resolution,
            "backend": args.backend, "prompt_version": prompts.PROMPT_VERSION, "prompt_versions": prompts.PROMPT_VERSIONS,
            "seed_from": getattr(args, "seed_from", None), "retrieval": "PER_STANDARD",
            "cells": len(cells), "released": len([c for c in cells if c in rel]), "reviewed_empty": len([c for c in cells if c in emp]),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(RUNS_DIR, args.run_id, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    log(f"== calibration {args.run_id}: {done} cells DONE, {pending} waiting; pending model calls: {len(set(llm.pending))}")
    if llm.pending:
        log(f"   execute the pending jobs (api_executor.py --run-id {args.run_id} ...) and re-run this command")
        return 10
    return 0


# ------------------------------------------------------------------ plant (near-misses)
def cmd_plant(args):
    """Run the verifier over the planted near-miss fixture with the same routing as the cells: the primary
    on every item; the adjudicator on slice-row items and on every item the primary rejected (a planted
    item is a one-candidate cell, so a primary REJECT is the 'rejected all' route). Final verdict as in
    agents.finalize. Every final ACCEPT is a false accept."""
    ensure_dirs()
    reg = Registry(args.workbook)
    preds = load_predicates(reg.wb)
    with open(PLANTED_PATH, encoding="utf-8") as fh:
        fixture = json.load(fh)
    vmodels = args.verifier_models.split(",")
    llm = _llm(args, reg)
    out_path = os.path.join(RUNS_DIR, args.run_id, "planted-results.json")
    results = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    runner = CellRunner(llm, reg, preds, {}, os.path.join(RUNS_DIR, args.run_id, "planted-state"), args.locator_model, vmodels, log=log, run_coder=False)
    chunk_cache = {}
    n_pending = 0
    for item in fixture["items"]:
        pid = item["id"]
        rid, loc = item["registry_id"], item["locator"]
        if rid not in chunk_cache:
            chunk_cache[rid] = {c["locator"]: c for c in store.load_chunks(rid)}
        chunk = chunk_cache[rid].get(loc)
        if not chunk:
            results[pid] = {"status": "CHUNK_NOT_FOUND", "registry_id": rid, "locator": loc}; continue
        ok, why = guards.check_phrase(item["phrase"], chunk["text"])
        if not ok:
            results[pid] = {"status": "FIXTURE_PHRASE_NOT_VERBATIM", "detail": why, "registry_id": rid, "locator": loc}; continue
        cand = {"candidate_id": pid, "registry_id": rid, "locator": loc, "phrase": item["phrase"], "floor_claim": item.get("floor_claim", "FULL"),
                "chunk_text": chunk["text"], "rationale": "", "fallback_tier": reg.is_fallback(rid)}
        cell = {"queue_id": pid, "family_id": item["family_id"], "branch": reg.by_id[rid]["branch"], "predicate": preds[item["family_id"]]["predicate"]}
        r = results.setdefault(pid, {"status": "RUN", "type": item["type"], "family_id": item["family_id"], "registry_id": rid, "locator": loc,
                                     "phrase": item["phrase"], "why_near_miss": item["why"], "verdicts": {}})
        r["status"] = "RUN"
        v = r["verdicts"]
        if v.get(runner.primary, {}).get("status") != "DONE":
            v[runner.primary] = runner.verify(cell, cand, runner.primary)
        if v[runner.primary].get("status") == "PENDING":
            n_pending += 1; continue
        route = runner.needs_adjudication(cand, all_rejected=v[runner.primary].get("verdict") not in ACCEPTS)
        v["_route"] = route
        if route and runner.adjudicator and v.get(runner.adjudicator, {}).get("status") != "DONE":
            v[runner.adjudicator] = runner.verify(cell, cand, runner.adjudicator)
        if route and runner.adjudicator and v[runner.adjudicator].get("status") == "PENDING":
            n_pending += 1; continue
        runner.finalize(v, runner.primary, runner.adjudicator)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    log(f"== planted near-misses {args.run_id}: {len(fixture['items'])} items; pending verifier calls {n_pending}")
    return 10 if n_pending else 0


# ------------------------------------------------------------------ report helpers
def _verdict(st, cid, model):
    v = (st.get("verifications") or {}).get(cid) or {}
    if model == ROUTED:
        return (v.get("final") or {}).get("verdict")
    m = v.get(model) or {}
    return m.get("verdict") if m.get("status") == "DONE" else None


def _reason(st, cid, model):
    v = (st.get("verifications") or {}).get(cid) or {}
    if model == ROUTED:
        return (v.get("final") or {}).get("reason_code_final")
    return (v.get(model) or {}).get("reason_code_final")


def _all_cands(st):
    return [cd for pk, pv in st["passes"].items() for cd in pv.get("candidates", [])]


def _survivors(st, model):
    return [cd for cd in _all_cands(st) if _verdict(st, cd["candidate_id"], model) in ACCEPTS]


def _cited_outcome(st, eq, cell, reg, primary, adjudicator):
    """What the locator and verifiers did on the standard(s) the released cell cites — the per-standard
    entries — so a loss can be explained by what was returned, not merely by what was supplied."""
    out = {}
    for pk, p in st["passes"].items():
        for rid in sorted(eq):
            e = (p.get("per_standard") or {}).get(rid)
            if not e:
                continue
            supplied = [loc for r_, loc in e.get("supplied_chunks", [])]
            cands = e.get("candidates") or []
            slotted_ids = {c["candidate_id"] for c in p.get("candidates", [])}
            rec = {"pass": pk, "status": e.get("status"), "coverage": e.get("coverage"),
                   "cited_division_supplied": any(same_division(cell["locator"], loc) for loc in supplied),
                   "n_supplied": len(supplied), "supplied_chars": e.get("supplied_chars"),
                   "candidates": [], "dropped": [{"phrase": d["candidate"].get("phrase"), "reason": d["reason"]} for d in e.get("dropped", [])],
                   "recuts": [{"from": r_.get("from"), "to": r_.get("to"), "status": r_.get("status")} for r_ in e.get("recuts", [])]}
            for c in cands:
                v = (st.get("verifications") or {}).get(c["candidate_id"]) or {}
                rec["candidates"].append({
                    "locator": c["locator"], "phrase": c["phrase"], "slotted": c["candidate_id"] in slotted_ids,
                    "primary": (v.get(primary) or {}).get("verdict"), "primary_reason": (v.get(primary) or {}).get("reason_code_final"),
                    "adjudicator": (v.get(adjudicator) or {}).get("verdict") if adjudicator else None,
                    "final": (v.get("final") or {}).get("verdict"), "route": v.get("_route"),
                    "same_division": same_division(cell["locator"], c["locator"])})
            out[rid] = rec
    return out


def _classify(cited, surv_all, witness_only):
    """Why the gate metric was missed, from the cited standard's own outcome."""
    if witness_only:
        return "WITNESS_ONLY_SURVIVOR"
    if not cited:
        return "CITED_STANDARD_NOT_IN_PASS"
    statuses = {rid: r["status"] for rid, r in cited.items()}
    if all(s_ == "NO_CORPUS" for s_ in statuses.values()):
        return "CITED_STANDARD_NO_CORPUS"
    if any(r["candidates"] for r in cited.values()):
        if any(c["slotted"] and c["final"] not in ACCEPTS for r in cited.values() for c in r["candidates"]):
            return "CITED_STANDARD_CANDIDATES_REJECTED"
        return "CITED_STANDARD_CANDIDATES_UNSLOTTED"
    if any(r["dropped"] for r in cited.values()):
        return "CITED_STANDARD_CANDIDATES_DROPPED_BY_GUARD"
    if any(s_ == "EMPTY" for s_ in statuses.values()):
        return "CITED_STANDARD_LOCATOR_EMPTY"
    return "CITED_STANDARD_" + "/".join(sorted(set(statuses.values())))


def _load_compare(run_id):
    p = os.path.join(RUNS_DIR, run_id, "calibration-report.json")
    if not os.path.exists(p):
        return None, {}
    rep = json.load(open(p, encoding="utf-8"))
    return rep, {d["queue_id"]: d for d in rep.get("details", [])}


# ------------------------------------------------------------------ report
def cmd_report(args):
    reg = Registry(args.workbook)
    queue = load_queue(reg.wb)
    rel, emp = calibration_cells(queue)
    run_dir = os.path.join(RUNS_DIR, args.run_id)
    meta = json.load(open(os.path.join(run_dir, "run.json"), encoding="utf-8"))
    vmodels = meta["verifier_models"]
    primary, adjudicator = meta.get("primary", vmodels[0]), meta.get("adjudicator")
    scored_models = [primary, ROUTED] if adjudicator else [primary]
    state_dir = os.path.join(run_dir, "cells")
    llm = LLM(args.run_id, backend=meta["backend"], model=meta["locator_model"], log=log)
    manifest = store.load_manifest()
    gate = reg.gate_metric
    compare_id = args.compare
    cmp_rep, cmp_details = _load_compare(compare_id) if compare_id else (None, {})
    cal1_rep, cal1_details = _load_compare("cal-1")

    def load_state(qid):
        p = os.path.join(state_dir, f"{qid}.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    per = defaultdict(lambda: defaultdict(lambda: {"cells": 0, "done": 0, "located_any": 0, "hit_std": 0, "hit_div": 0,
                                                    "hit_tier": 0, "partial_lower": 0, "excluded_oos": 0, "witness_only": 0,
                                                    "no_corpus": 0, "empty": 0, "skipped": 0}))
    details, residue, skipped_cells, caveat_hits = [], defaultdict(list), defaultdict(list), []
    delta = {m: {"gained": [], "lost": [], "unchanged_hit": [], "unchanged_miss": [], "new": []} for m in scored_models}
    per_standard = defaultdict(lambda: {"cells_citing": 0, "hit_before": 0, "hit_primary": 0, "hit_routed": 0,
                                        "yield_cells": 0, "accepted_cells": 0, "candidates": 0})
    fix1 = {}
    tax = defaultdict(Counter)
    for c in rel:
        st = load_state(c["queue_id"])
        eq = equivalent_registry_ids(c)
        corpus_available = any((manifest.get("standards", {}).get(r, {}).get("n_chunks") or 0) > 0 for r in eq)
        bar = min((tier_rank(reg.by_id[r]["authority_tier"]) for r in eq if r in reg.by_id), default=len(TIER_RANK))
        oos = OUT_OF_RATIFIED_SCOPE.get(c["queue_id"])
        cmp_hit = cmp_details.get(c["queue_id"], {}).get("hit_same_standard") if compare_id else None
        cmp_hit_tier = cmp_details.get(c["queue_id"], {}).get("hit_tier_respecting") if compare_id else None
        for r in eq:
            per_standard[r]["cells_citing"] += 1
            if cmp_hit and r in (cmp_details.get(c["queue_id"], {}).get("equivalent_registry") or []):
                per_standard[r]["hit_before"] += 1
        cited = _cited_outcome(st, eq, c, reg, primary, adjudicator) if st else {}
        for m in scored_models:
            b = per[c["branch"]][m]
            b["cells"] += 1
            if not st or st.get("phase") != "DONE":
                b["skipped"] += 1
                skipped_cells[m].append((c["queue_id"], c["branch"], c["predicate"], "CELL_NOT_DONE", (st or {}).get("phase", "NO STATE FILE")))
                continue
            cands = _all_cands(st)
            if oos:
                b["excluded_oos"] += 1
                continue
            b["done"] += 1
            if not corpus_available:
                b["no_corpus"] += 1
            surv_all = _survivors(st, m)
            witness_only = bool(surv_all) and all(cd.get("witness") for cd in surv_all)
            surv = [] if witness_only else surv_all
            if surv:
                b["located_any"] += 1
            else:
                b["empty"] += 1
            if witness_only:
                b["witness_only"] += 1
            hit_std = any(cd["registry_id"] in eq for cd in surv)
            hit_div = any(cd["registry_id"] in eq and same_division(c["locator"], cd["locator"]) for cd in surv)

            def same_branch(cd):
                return cd["registry_id"] in reg.by_id and reg.by_id[cd["registry_id"]]["branch"] == c["branch"]
            equal_or_higher = [cd for cd in surv if same_branch(cd) and tier_rank(cd.get("effective_tier") or reg.by_id[cd["registry_id"]]["authority_tier"]) <= bar]
            lower = [cd for cd in surv if same_branch(cd) and tier_rank(cd.get("effective_tier") or reg.by_id[cd["registry_id"]]["authority_tier"]) > bar]
            hit_tier = bool(hit_std or equal_or_higher)
            b["hit_std"] += hit_std; b["hit_div"] += hit_div; b["hit_tier"] += hit_tier
            if not hit_tier and lower:
                b["partial_lower"] += 1
            gate_hit = hit_std if gate == "SAME_STANDARD" else hit_tier
            # taxonomy
            other = [cd for cd in surv if cd["registry_id"] not in eq and same_branch(cd)]
            if hit_std:
                tax[m]["A_same_standard"] += 1
            elif any(tier_rank(cd.get("effective_tier") or reg.by_id[cd["registry_id"]]["authority_tier"]) <= bar for cd in other):
                tax[m]["B1_other_standard_equal_or_higher_tier"] += 1
            elif other:
                tax[m]["B2_other_standard_lower_tier"] += 1
            elif witness_only:
                tax[m]["B4_witness_row_only"] += 1
            elif surv:
                tax[m]["B3_other_standard_wrong_branch"] += 1
            elif cands:
                tax[m]["C_all_candidates_rejected"] += 1
            else:
                tax[m]["D_locator_empty"] += 1
            if not gate_hit:
                residue[m].append({"queue_id": c["queue_id"], "branch": c["branch"], "predicate": c["predicate"],
                                   "cited": sorted(eq), "cited_tier": bare_tier(reg.by_id[sorted(eq)[0]]["authority_tier"]) if eq else "?",
                                   "class": _classify(cited, surv_all, witness_only), "hit_tier_respecting": hit_tier,
                                   "other_evidence": [(cd["registry_id"], bare_tier(cd.get("effective_tier") or reg.by_id[cd["registry_id"]]["authority_tier"]), cd["locator"][:40]) for cd in surv],
                                   "cited_outcome": cited})
            for cd in surv_all:
                if cd["registry_id"] in CAVEATED_ROWS:
                    caveat_hits.append({"queue_id": c["queue_id"], "model": m, "branch": c["branch"], "predicate": c["predicate"],
                                        "registry_id": cd["registry_id"], "locator": cd["locator"],
                                        "credited": bool(gate_hit and cd["registry_id"] in eq) if gate == "SAME_STANDARD" else bool(hit_tier and cd in equal_or_higher),
                                        "caveat": CAVEATED_ROWS[cd["registry_id"]]})
            # per-standard recall / yield
            if m == primary:
                for r in eq:
                    per_standard[r]["hit_primary"] += hit_std
            if m == ROUTED:
                for r in eq:
                    per_standard[r]["hit_routed"] += hit_std
            # delta vs the comparison run (on the gate metric: same-standard)
            if compare_id:
                if c["queue_id"] not in cmp_details:
                    delta[m]["new"].append(c["queue_id"])
                elif cmp_hit and not hit_std:
                    delta[m]["lost"].append(c["queue_id"])
                elif not cmp_hit and hit_std:
                    delta[m]["gained"].append(c["queue_id"])
                elif hit_std:
                    delta[m]["unchanged_hit"].append(c["queue_id"])
                else:
                    delta[m]["unchanged_miss"].append(c["queue_id"])
            if m == primary:
                for rid in {cd["registry_id"] for cd in cands}:
                    per_standard[rid]["yield_cells"] += 1
                for rid in {cd["registry_id"] for cd in _survivors(st, ROUTED if adjudicator else primary)}:
                    per_standard[rid]["accepted_cells"] += 1
                for cd in cands:
                    per_standard[cd["registry_id"]]["candidates"] += 1
                details.append({"queue_id": c["queue_id"], "branch": c["branch"], "family_id": c["family_id"], "predicate": c["predicate"],
                                "existing": f"{c['document']} — {c['locator']}", "equivalent_registry": sorted(eq), "corpus_available": corpus_available,
                                "cited_tier": bare_tier(reg.by_id[sorted(eq)[0]]["authority_tier"]) if eq else "?",
                                "survivors": [(cd["registry_id"], cd["locator"], cd["phrase"]) for cd in surv_all],
                                "survivors_routed": [(cd["registry_id"], cd["locator"], cd["phrase"]) for cd in _survivors(st, ROUTED)] if adjudicator else None,
                                "witness_only": witness_only,
                                "hit_same_standard": hit_std, "hit_same_division": hit_div, "hit_tier_respecting": hit_tier,
                                "hit_same_standard_routed": (any(cd["registry_id"] in eq for cd in _survivors(st, ROUTED)) if adjudicator else None),
                                "partial_lower_tier": [cd["registry_id"] for cd in lower] if not hit_tier else [],
                                "compare_hit_same_standard": cmp_hit, "compare_hit_tier": cmp_hit_tier,
                                "cited_outcome": cited,
                                "rejected": [(cd["registry_id"], cd["locator"], _verdict(st, cd["candidate_id"], m), _reason(st, cd["candidate_id"], m))
                                             for cd in cands if cd not in surv_all]})
            if c["queue_id"] in FIX1_CELLS:
                fix1.setdefault(c["queue_id"], {"predicate": c["predicate"], "branch": c["branch"], "cited": sorted(eq), "existing": f"{c['document']} — {c['locator']}",
                                                "cal_1": (cal1_details.get(c["queue_id"], {}).get("hit_same_standard"), cal1_details.get(c["queue_id"], {}).get("survivors", [])[:1]),
                                                "cal_2": (cmp_details.get(c["queue_id"], {}).get("hit_same_standard"), cmp_details.get(c["queue_id"], {}).get("survivors", [])[:1]),
                                                "cited_outcome": cited})[m] = {"hit_same_standard": hit_std, "hit_same_division": hit_div,
                                                                              "survivors": [(cd["registry_id"], cd["locator"][:50], cd["phrase"]) for cd in surv_all]}
    # ---- expected-empty cells
    emp_rows = []
    for c in emp:
        st = load_state(c["queue_id"])
        eq = equivalent_registry_ids(c)
        if not st or st.get("phase") != "DONE":
            emp_rows.append({"queue_id": c["queue_id"], "branch": c["branch"], "status": "NOT DONE"}); continue
        for m in scored_models:
            surv = _survivors(st, m)
            emp_rows.append({"queue_id": c["queue_id"], "branch": c["branch"], "family_id": c["family_id"], "predicate": c["predicate"], "model": m,
                             "existing_document": c["document"], "outcome": "EMPTY" if not surv else
                             ("LOCATED_IN_SAME_STANDARD" if any(cd["registry_id"] in eq for cd in surv) else "LOCATED_IN_OTHER_REGISTRY_STANDARD"),
                             "survivors": [(cd["registry_id"], cd["locator"], cd["phrase"]) for cd in surv]})
    # ---- planted near-misses
    planted = {}
    pp = os.path.join(run_dir, "planted-results.json")
    if os.path.exists(pp):
        planted = json.load(open(pp, encoding="utf-8"))
    planted_models = [primary] + ([adjudicator] if adjudicator else []) + ([ROUTED] if adjudicator else [])
    fa = defaultdict(lambda: defaultdict(lambda: {"n": 0, "false_accept": 0, "pending": 0, "items": []}))
    planted_status = Counter(r.get("status") for r in planted.values())
    planted_overturns = Counter()
    for pid, r in planted.items():
        if r.get("status") != "RUN":
            continue
        slice_ = "Dositheus" if r["registry_id"] == "BSR-EO-05" else reg.by_id[r["registry_id"]]["branch"]
        v = r["verdicts"]
        for m in planted_models:
            b = fa[slice_][m]
            if m == ROUTED:
                fin = v.get("final")
                if not fin:
                    b["pending"] += 1; continue
                b["n"] += 1
                if fin.get("verdict") in ACCEPTS:
                    b["false_accept"] += 1
                    b["items"].append((pid, r["type"], r["locator"], fin.get("verdict"), f"by {fin.get('adjudicated_by')} ({fin.get('route')})"))
                if fin.get("overturned"):
                    planted_overturns[fin.get("direction")] += 1
                continue
            mv = v.get(m)
            if not mv:
                continue           # the adjudicator did not run on this item (outside its slice)
            if mv.get("status") != "DONE":
                b["pending"] += 1; continue
            b["n"] += 1
            if mv.get("verdict") in ACCEPTS:
                b["false_accept"] += 1
                b["items"].append((pid, r["type"], r["locator"], mv.get("verdict"), mv.get("reason")))
    # Dositheus natural slice: verdicts on Dositheus candidates from the EO cells
    dos_nat = defaultdict(lambda: {"candidates": 0, "accept": 0, "reject": 0})
    for c in rel + emp:
        st = load_state(c["queue_id"])
        if not st:
            continue
        for cd in _all_cands(st):
            if cd["registry_id"] != "BSR-EO-05":
                continue
            for m in [primary, adjudicator, ROUTED] if adjudicator else [primary]:
                v = _verdict(st, cd["candidate_id"], m)
                if v:
                    dos_nat[m]["candidates"] += 1
                    dos_nat[m]["accept" if v in ACCEPTS else "reject"] += 1
    # ---- adjudication (opus slice) statistics
    adj = {"calls_new": 0, "calls_reused": 0, "cost_new": 0.0, "cost_reused": 0.0, "candidates": 0, "by_route": Counter(),
           "overturned": Counter(), "overturns": [], "cells_escalated_all_rejected": 0, "cells_rescued": 0}
    if adjudicator:
        for rec in llm._cache.values():
            if rec.get("role") == "verifier" and (rec.get("executor_model") or rec.get("model")) == adjudicator:
                if rec.get("run_id") == args.run_id:
                    adj["calls_new"] += 1; adj["cost_new"] += rec.get("cost_usd") or 0.0
                else:
                    adj["calls_reused"] += 1; adj["cost_reused"] += rec.get("cost_usd") or 0.0
        for c in rel + emp:
            st = load_state(c["queue_id"])
            if not st:
                continue
            esc = False; rescued = False
            for cd in _all_cands(st):
                v = st["verifications"].get(cd["candidate_id"]) or {}
                fin = v.get("final") or {}
                if fin.get("adjudicated_by") == adjudicator:
                    adj["candidates"] += 1
                    adj["by_route"][fin.get("route")] += 1
                    if fin.get("route") == "PRIMARY_REJECTED_ALL":
                        esc = True
                    if fin.get("overturned"):
                        adj["overturned"][fin.get("direction")] += 1
                        adj["overturns"].append({"queue_id": c["queue_id"], "candidate_id": cd["candidate_id"], "registry_id": cd["registry_id"],
                                                 "locator": cd["locator"][:50], "phrase": cd["phrase"], "route": fin.get("route"),
                                                 "primary": fin.get("primary_verdict"), "adjudicator": fin.get("verdict"), "direction": fin.get("direction"),
                                                 "adjudicator_reason": (v.get(adjudicator) or {}).get("reason")})
                        if fin.get("direction") == "RESCUED":
                            rescued = True
            adj["cells_escalated_all_rejected"] += esc
            adj["cells_rescued"] += (esc and rescued)
    # ---- cost / model table. Reuse is counted from the call ids the cell and planted states actually
    # reference: those answered under another run id were served from the seeded cache at no cost.
    summary = llm.summary()
    seeded = {}
    if meta.get("seed_from"):
        sp = os.path.join(RUNS_DIR, meta["seed_from"], "calls.jsonl")
        if os.path.exists(sp):
            for line in open(sp, encoding="utf-8"):
                try:
                    r_ = json.loads(line); seeded[r_["call_id"]] = r_
                except Exception:
                    pass
    referenced = set()
    for c in rel + emp:
        st = load_state(c["queue_id"])
        if not st:
            continue
        for p in st["passes"].values():
            for e in (p.get("per_standard") or {}).values():
                if e.get("call_id"):
                    referenced.add(e["call_id"])
        for v in st["verifications"].values():
            for m, r_ in v.items():
                if isinstance(r_, dict) and r_.get("call_id"):
                    referenced.add(r_["call_id"])
    for r_ in planted.values():
        for m, v in (r_.get("verdicts") or {}).items():
            if isinstance(v, dict) and v.get("call_id"):
                referenced.add(v["call_id"])
    reused = [seeded[cid] for cid in referenced if cid in seeded and cid not in llm._cache]
    summary["reused"] = {"calls": len(reused), "by_role_model": dict(Counter(f"{r_.get('role')}/{r_.get('executor_model') or r_.get('model')}" for r_ in reused)),
                         "original_cost_usd": sum(r_.get("cost_usd") or 0.0 for r_ in reused), "from_run": meta.get("seed_from")}
    summary["this_run"]["reused_calls"] = len(reused)
    # ---- thresholds per scored model
    verdicts = {}
    for m in scored_models:
        tot = sum(per[b][m]["done"] for b in per)
        hit_std = sum(per[b][m]["hit_std"] for b in per)
        hit_div = sum(per[b][m]["hit_div"] for b in per)
        hit_tier = sum(per[b][m]["hit_tier"] for b in per)
        recall_std = hit_std / tot if tot else None
        recall_tier = hit_tier / tot if tot else None
        gated = recall_std if gate == "SAME_STANDARD" else recall_tier
        n = sum(fa[s][m]["n"] for s in fa); f = sum(fa[s][m]["false_accept"] for s in fa)
        far = f / n if n else None
        dn = fa["Dositheus"][m]["n"]; df = fa["Dositheus"][m]["false_accept"]
        dfar = df / dn if dn else None
        verdicts[m] = {"gate_metric": gate, "recall_gated": gated, "recall_same_standard": recall_std, "recall_same_division": hit_div / tot if tot else None,
                       "recall_tier_respecting": recall_tier, "denominator": tot, "hits_same_standard": hit_std, "hits_same_division": hit_div,
                       "hits_tier": hit_tier, "partial_lower_tier": sum(per[b][m]["partial_lower"] for b in per),
                       "witness_only_cells": sum(per[b][m]["witness_only"] for b in per),
                       "excluded_out_of_ratified_scope": sum(per[b][m]["excluded_oos"] for b in per),
                       "false_accept": far, "false_accept_n": n, "dositheus_false_accept": dfar, "dositheus_n": dn,
                       "recall_ok": gated is not None and gated >= THRESH_RECALL,
                       "false_accept_ok": far is not None and far <= THRESH_FALSE_ACCEPT,
                       "dositheus_ok": dfar is not None and dfar <= THRESH_FALSE_ACCEPT}
    # ---- corpus facts for the report
    new_rows = ["BSR-EO-07", "BSR-EO-08", "BSR-EO-09", "BSR-EO-10", "BSR-EO-11", "BSR-EO-12", "BSR-EO-13", "BSR-EO-14"]
    changed_rows = ["BSR-RC-04", "BSR-EO-06", "BSR-MW-03", "BSR-EO-03", "BSR-AN-03"]
    fetch_audit = json.load(open(FETCH_AUDIT_PATH, encoding="utf-8")) if os.path.exists(FETCH_AUDIT_PATH) else {}
    guard_tests = open(os.path.join(run_dir, "guard-tests.txt"), encoding="utf-8").read() if os.path.exists(os.path.join(run_dir, "guard-tests.txt")) else ""
    goarch_probe = json.load(open(os.path.join(run_dir, "goarch-probe.json"), encoding="utf-8")) if os.path.exists(os.path.join(run_dir, "goarch-probe.json")) else {}
    recut = {}
    for qid, spec in PHRASE_REQUIRES_RECUT.items():
        opts = []
        for o in spec["options"]:
            hit = [c["locator"] for c in store.load_chunks(o["registry_id"]) if o["wording"].casefold() in c["text"].casefold()]
            opts.append({**o, "present_in_corpus": bool(hit), "chunk": hit[0] if hit else None})
        recut[qid] = {**spec, "options": opts}
    q449 = next((d for d in details if d["queue_id"] == "Q-449"), None)
    rc04 = manifest.get("standards", {}).get("BSR-RC-04", {})
    q449_chunks = [c["locator"] for c in store.load_chunks("BSR-RC-04") if re.search(r"dissimilitude|unlikeness|dissimilar", c["text"], re.I)]

    report = {"run": meta, "gate_metric": gate, "scored_models": scored_models, "per_branch": {b: {m: dict(v) for m, v in mv.items()} for b, mv in per.items()},
              "expected_empty": emp_rows, "planted": {s: {m: dict(v) for m, v in mv.items()} for s, mv in fa.items()},
              "planted_status": dict(planted_status), "planted_overturns": dict(planted_overturns),
              "taxonomy": {m: dict(v) for m, v in tax.items()}, "tier_rank": reg.tier_rank_list, "out_of_ratified_scope": OUT_OF_RATIFIED_SCOPE,
              "residue": {m: v for m, v in residue.items()}, "skipped_cells": {m: v for m, v in skipped_cells.items()},
              "caveat_hits": caveat_hits, "dositheus_natural": dict(dos_nat), "adjudication": {**adj, "by_route": dict(adj["by_route"]), "overturned": dict(adj["overturned"])},
              "models": summary, "verdicts": verdicts, "delta": delta, "compare_run": compare_id,
              "per_standard": {k: dict(v) for k, v in per_standard.items()}, "fix1": fix1, "phrase_requires_recut": recut,
              "q449": {"detail": q449, "rc04_status": rc04.get("status"), "rc04_chunks": rc04.get("n_chunks"), "rc04_notes": rc04.get("notes"),
                       "dissimilitudo_chunks": q449_chunks},
              "new_rows": {r: manifest.get("standards", {}).get(r) for r in new_rows}, "changed_rows": {r: manifest.get("standards", {}).get(r) for r in changed_rows},
              "fetch_audit": fetch_audit, "guard_tests": guard_tests, "goarch_probe": goarch_probe,
              "chosen_verifier": None, "details": details}
    with open(os.path.join(run_dir, "calibration-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    md_path = os.path.join(RUNS_DIR, "calibration-report.md")
    if os.path.exists(md_path):
        first = open(md_path, encoding="utf-8").readline()
        m_ = re.search(r"\((cal-\d+)\)", first)
        if m_ and m_.group(1) != args.run_id:
            shutil.copyfile(md_path, os.path.join(RUNS_DIR, m_.group(1), "calibration-report.md"))
    md = render_md(report, reg, manifest)
    with open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    log(md)
    return 0


def pct(x):
    return "—" if x is None else f"{x:.3f}"


def _yn(x):
    return "yes" if x else "no"


def render_md(rep, reg, manifest):
    meta = rep["run"]; models = rep["scored_models"]; gate = rep["gate_metric"]
    primary = meta.get("primary", models[0]); adj = meta.get("adjudicator")
    L = []
    L.append(f"# SJN Gate 6 — Calibration report ({meta['run_id']})\n")
    L.append(f"Workbook {meta['workbook']} ({meta['app_master_version']}) · prompt versions {meta.get('prompt_versions')} · "
             f"locator model `{meta['locator_model']}` · verifier routing **{meta.get('routing')}** (primary `{primary}`"
             + (f", adjudicator `{adj}` on the slice {meta.get('slice_rows')}" if adj else "") + f") · retrieval {meta.get('retrieval')} · "
             f"backend {meta['backend']} · generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n")
    L.append("Locators hidden: the agents received predicate, definition, floor note, subject scope and registry chunks only — never the "
             "workbook's document, locator or phrase. False-accept = a final verifier ACCEPT or ACCEPT_WITH_CAVEAT on a planted near-miss. "
             f"**The gate is {gate} recall ≥ {THRESH_RECALL}** (APP CONFIG `gate6_threshold_metric`, read from the workbook), false-accept ≤ "
             f"{THRESH_FALSE_ACCEPT} with the Dositheus slice held to {THRESH_FALSE_ACCEPT} on its own. Tier-respecting and same-division are reported, ungated. "
             "Thresholds were not moved.\n")
    L.append("APP CONFIG keys honoured (read, not hard-coded): " + "; ".join(
        f"`{k}` = {v}" for k, v in manifest.get("app_config", {}).items()) + ".\n")
    L.append("**Nothing in this run wrote to the workbook. The live run against the open cells has not been started.**\n")
    # ---------------- 1. verdict
    L.append("## 1. Verdict by verifier model (n = %d released cells)\n" % max(v["denominator"] for v in rep["verdicts"].values()))
    L.append(f"`{primary}` is the primary verifier on every candidate. `{ROUTED}` is the ratified routing outcome: the primary's verdict except "
             f"where `{adj}` adjudicated (caveated rows, fallback-only rows, the guarded Synodikon, and every cell the primary rejected outright), "
             "where the adjudicator's verdict is final.\n" if adj else "")
    L.append("| model | n | **same-standard (gated)** | same-division | tier-respecting | partial (lower tier) | witness-only cells | false-accept (planted) | Dositheus false-accept | thresholds |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for m in models:
        v = rep["verdicts"][m]
        ok = "MET" if (v["recall_ok"] and v["false_accept_ok"] and v["dositheus_ok"]) else "NOT MET"
        L.append(f"| `{m}` | {v['denominator']} | **{v['hits_same_standard']}/{v['denominator']} = {pct(v['recall_same_standard'])}** | "
                 f"{v['hits_same_division']}/{v['denominator']} = {pct(v['recall_same_division'])} | "
                 f"{v['hits_tier']}/{v['denominator']} = {pct(v['recall_tier_respecting'])} | {v['partial_lower_tier']} | {v['witness_only_cells']} | "
                 f"{pct(v['false_accept'])} (n={v['false_accept_n']}) | {pct(v['dositheus_false_accept'])} (n={v['dositheus_n']}) | {ok} |")
    L.append("")
    L.append("### Per branch, all three metrics\n")
    L.append("| branch | model | released | done | skipped | located (any) | same-division | **same-standard** | tier-respecting | partial (lower) | witness-only | empty | corpus unavailable |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for b in BRANCHES:
        for m in models:
            r = rep["per_branch"].get(b, {}).get(m)
            if not r:
                continue
            d = r["done"] or 1
            L.append(f"| {b} | `{m}` | {r['cells']} | {r['done']} | {r.get('skipped', 0)} | {r['located_any']} | "
                     f"{r['hit_div']}/{r['done']} = {r['hit_div'] / d:.2f} | **{r['hit_std']}/{r['done']} = {r['hit_std'] / d:.2f}** | "
                     f"{r['hit_tier']}/{r['done']} = {r['hit_tier'] / d:.2f} | {r['partial_lower']} | {r['witness_only']} | {r['empty']} | {r['no_corpus']} |")
    L.append("")
    L.append("### Why each released cell scored as it did\n")
    L.append("| outcome | " + " | ".join(f"`{m}`" for m in models) + " |")
    L.append("|---|" + "---|" * len(models))
    for key, label in [("A_same_standard", "A. hit in the same standard the cell cites (gated)"),
                       ("B1_other_standard_equal_or_higher_tier", "B1. different ratified standard of the branch, equal or higher tier"),
                       ("B2_other_standard_lower_tier", "B2. different ratified standard of the branch, lower tier"),
                       ("B4_witness_row_only", "B4. survivors only on witness rows (a cell may not rest on them alone)"),
                       ("B3_other_standard_wrong_branch", "B3. survivor outside the cell's branch"),
                       ("C_all_candidates_rejected", "C. candidates found, all rejected by the verifier"),
                       ("D_locator_empty", "D. no candidate slotted (locator empty or every candidate dropped by a guard)")]:
        L.append(f"| {label} | " + " | ".join(str(rep['taxonomy'].get(m, {}).get(key, 0)) for m in models) + " |")
    L.append("")
    # ---------------- 2. Synodikon guard
    eo09 = rep["new_rows"].get("BSR-EO-09") or {}
    L.append("## 2. FIX 0 — the Synodikon guard (BSR-EO-09)\n")
    L.append(f"Status: **{eo09.get('status', 'NOT BUILT')}** — {eo09.get('n_chunks', 0)} sections, {eo09.get('noncitable_spans', 0)} anathema-framed spans withheld as non-citable; "
             f"notes: {'; '.join(eo09.get('notes') or [])}.\n")
    L.append("How it works: the corpus builder (`sources.synodikon_guard`) withholds every span of the form *To those who … : ANATHEMA!*, "
             "every *People: Anathema!* response, and any remaining sentence carrying the word, from the chunk's agent-visible text, leaving a "
             "marker where the span stood; the withheld spans travel with the chunk as `noncitable_spans`. Two guards then apply in code: the "
             "verbatim phrase check runs against the visible text (which no longer contains the clause), and `guards.check_noncitable` refuses "
             "any phrase lying inside a withheld span by name (`ANATHEMA_SPAN`), so even a phrase reconstructed from memory cannot become a "
             "candidate. Section 2, *The Symbol of Faith*, carries no anathema and is the safe region. Candidates from this row are always "
             "adjudicated by the second verifier.\n")
    L.append("Test (`scripts/sjn_recovery/tests/test_synodikon_guard.py`): the known sentence — *To those who dare to say that the Son of God, "
             "and likewise the Holy Spirit, are not one in essence with the Father, and confess that the Father, and the Son, and the Holy Spirit "
             "are not one God: ANATHEMA!* — is fed through the guard and through `vet_candidate`; the tests assert that it is withheld whole, "
             "that four inner clauses cannot become candidates, that the built corpus contains no anathema wording in any citable text, and that "
             "the Creed section is citable.\n")
    L.append("```\n" + (rep.get("guard_tests") or "(test output not recorded)").strip() + "\n```\n")
    # ---------------- 3. Fix 1
    L.append("## 3. FIX 1 — retrieval per standard: the six cal-2 LOCATOR_EMPTY cells\n")
    L.append("The locator is now called once per AUTHOR_RATIFIED standard with that standard's own chunks (whole when they fit 60,000 characters, "
             "else the hybrid ranking within that standard), and the best candidate of every standard has a guaranteed verification slot. "
             "cal-2 reported these six as `LOCATOR_EMPTY`; the per-standard record now shows what the locator actually returned on the cited standard.\n")
    L.append("| cell | branch | predicate | cal-1 | cal-2 | " + " | ".join(f"cal-3 `{m}`" for m in models) + " | what the locator returned on the cited standard in cal-3 |")
    L.append("|---|---|---|---|---|" + "---|" * len(models) + "---|")
    for qid in FIX1_CELLS:
        f = rep["fix1"].get(qid)
        if not f:
            L.append(f"| {qid} | | | | | " + " | ".join("not run" for _ in models) + " | |"); continue
        c1 = f["cal_1"]; c2 = f["cal_2"]

        def fmt(x):
            hit, surv = x
            return ("STD " if hit else "MISS ") + (f"({surv[0][0]} {surv[0][1][:28]})" if surv else "")
        what = []
        for rid, o in f["cited_outcome"].items():
            cand_txt = "; ".join(f"“{c['phrase'][:60]}” → {c['primary']}" + (f"/{c['adjudicator']}" if c.get('adjudicator') else "") for c in o["candidates"]) or "no candidate"
            drop_txt = "; ".join(f"dropped: {d['reason'][:60]}" for d in o["dropped"])
            recut_txt = "; ".join(f"re-cut {r['status']}" for r in o["recuts"])
            what.append(f"{rid} {o['status']} (cited division supplied: {_yn(o['cited_division_supplied'])}, {o['n_supplied']} chunks): {cand_txt} {drop_txt} {recut_txt}".strip())
        cols = " | ".join(("STD+DIV" if f[m]["hit_same_division"] else "STD" if f[m]["hit_same_standard"] else "MISS") + (f" ({f[m]['survivors'][0][0]} {f[m]['survivors'][0][1][:28]})" if f[m]["survivors"] else "") for m in models if m in f)
        L.append(f"| {qid} | {f['branch']} | {f['predicate'][:26]} | {fmt(c1)} | {fmt(c2)} | {cols} | {' // '.join(what)[:600]} |")
    L.append("")
    L.append("### Per-standard recall — before (cal-2) and after (cal-3)\n")
    L.append("`cells citing` is the number of released cells whose citation maps to the row; `hit` counts same-standard hits among them. "
             "Rows no released cell cites cannot have a recall; for them the yield columns say how many released cells produced a slotted "
             "candidate on the row and how many of those candidates survived the routed verdict — coverage the open cells will inherit.\n")
    L.append("| row | tier | reception | cells citing | hit cal-2 | hit cal-3 primary | hit cal-3 routed | yield: cells with a candidate | cells with an accepted candidate | candidates |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    rows = PER_STANDARD_ROWS + [r["registry_id"] for r in reg.rows if r["branch"] == "Eastern Orthodox"]
    for rid in rows:
        p = rep["per_standard"].get(rid, {})
        row = reg.by_id.get(rid, {})
        n = p.get("cells_citing", 0)
        L.append(f"| {rid} | {bare_tier(row.get('authority_tier'))} | {reg.reception(rid)} | {n} | {p.get('hit_before', 0)}/{n} | {p.get('hit_primary', 0)}/{n} | "
                 f"{p.get('hit_routed', 0)}/{n} | {p.get('yield_cells', 0)} | {p.get('accepted_cells', 0)} | {p.get('candidates', 0)} |")
    L.append("")
    eo = {m: rep["per_branch"].get("Eastern Orthodox", {}).get(m) for m in models}
    L.append("Expectation stated before the run: the six Eastern Orthodox rows are additions; released Eastern Orthodox cells still cite the rows they "
             "always cited, so the new rows should raise coverage and tier-respecting recall and were not expected to move same-standard recall much. "
             + " ".join(f"Eastern Orthodox same-standard recall, `{m}`: {eo[m]['hit_std']}/{eo[m]['done']} = {eo[m]['hit_std'] / (eo[m]['done'] or 1):.2f} (cal-2: 0.50)." for m in models if eo.get(m))
             + "\n")
    # ---------------- 4. fetcher audit
    L.append("## 4. FIX 2 — fetcher audit\n")
    L.append("**Finding.** The fetcher never rewrote a hostname: no code path adds or strips `www.` (the only www-stripping in the pipeline is "
             "`registry.normalize_host`, used for R001 domain matching, never for fetching). Two things were wrong instead. (1) BSR-MW-03 was carried "
             "in `sources.NO_TEXT` as a hard-coded UNAVAILABLE entry, so cal-1 and cal-2 never requested the ratified URL at build time — that half "
             "was self-inflicted. (2) The fetcher followed every redirect the host issued, including onto a different host, which is how the apex URL "
             "came back as the www site's 404. Fix: redirects are followed one hop at a time and logged; the corpus builder runs `strict_host`, "
             "refusing any hop that changes the host, so the ratified URL is fetched byte for byte.\n")
    fa = rep.get("fetch_audit") or {}
    L.append(f"Audit ({fa.get('audited_at', 'not run')}): every AUTHOR_RATIFIED canonical_url requested once, as written, no cross-host hops.\n")
    L.append("| row | status | verdict | redirects seen |")
    L.append("|---|---|---|---|")
    for r in fa.get("rows", []):
        if r.get("verdict", "").startswith("OK") and not r.get("redirects"):
            continue
        L.append(f"| {r['registry_id']} | {r.get('status')} | {r.get('verdict', '')[:120]} | {'; '.join(f'{s_} {a[:40]} → {b[:60]}' for s_, a, b in (r.get('redirects') or [])) or '—'} |")
    ok_rows = [r["registry_id"] for r in fa.get("rows", []) if r.get("verdict", "").startswith("OK") and not r.get("redirects")]
    L.append(f"\n{len(ok_rows)} rows answered 200 on the ratified URL with no redirect: {', '.join(ok_rows)}.\n")
    L.append("### Verdict per row the corpus manifest marks unavailable, blocked or zero-chunk\n")
    L.append("| row | manifest status | chunks | cause | detail |")
    L.append("|---|---|---|---|---|")
    for rid, s_ in manifest.get("standards", {}).items():
        if (s_.get("n_chunks") or 0) == 0:
            L.append(f"| {rid} | {s_.get('status')} | 0 | {s_.get('fetch_verdict', '?')} | {'; '.join(s_.get('notes') or [])[:220]} |")
    L.append("")
    mw = rep["changed_rows"].get("BSR-MW-03") or {}
    L.append(f"BSR-MW-03 this run: **{mw.get('status')}** — {'; '.join(mw.get('notes') or [])[:400]}. Corrected sample phrase for any cell citing this row: "
             "*of infinite power, wisdom, and good* (not *goodness*).\n")
    # ---------------- 5. corpus stats
    L.append("## 5. FIX 3 — the six new Eastern Orthodox rows\n")
    L.append("| row | status | chunks | chars | languages | non-citable spans | polytonic chunks | notes |")
    L.append("|---|---|---|---|---|---|---|---|")
    for rid, s_ in rep["new_rows"].items():
        s_ = s_ or {}
        L.append(f"| {rid} | {s_.get('status', 'NOT BUILT')} | {s_.get('n_chunks', 0)} | {s_.get('chars', 0):,} | {','.join(s_.get('languages') or [])} | "
                 f"{s_.get('noncitable_spans', 0)} | {s_.get('polytonic_chunks', 0)} | {'; '.join(s_.get('notes') or [])[:260]} |")
    L.append("")
    L.append("Changed rows (re-scoped or re-sourced by the author):\n")
    L.append("| row | status | chunks | chars | notes |")
    L.append("|---|---|---|---|---|")
    for rid, s_ in rep["changed_rows"].items():
        s_ = s_ or {}
        L.append(f"| {rid} | {s_.get('status', 'NOT BUILT')} | {s_.get('n_chunks', 0)} | {s_.get('chars', 0):,} | {'; '.join(s_.get('notes') or [])[:260]} |")
    L.append("")
    # ---------------- 6. Q-449
    q = rep["q449"]
    L.append("## 6. FIX 4 — Lateran IV scope and Q-449\n")
    L.append(f"BSR-RC-04 is chunked as constitutions 1–2 under `lateran_iv_scope = EXTEND_TO_CONSTITUTION_2`: status {q.get('rc04_status')}, "
             f"{q.get('rc04_chunks')} chunks; {'; '.join(q.get('rc04_notes') or [])}. The maior dissimilitudo clause sits in: {', '.join(q.get('dissimilitudo_chunks') or []) or 'NOT FOUND'}.\n")
    d = q.get("detail")
    if d:
        hit = "STD+DIV" if d["hit_same_division"] else "STD" if d["hit_same_standard"] else "MISS"
        L.append(f"Q-449 ({d['predicate']}) is in the denominator (n = {rep['verdicts'][primary]['denominator']}). Outcome, `{primary}`: **{hit}**; "
                 f"`{ROUTED}`: **{'STD' if d.get('hit_same_standard_routed') else 'MISS'}**. Survivors: "
                 + ("; ".join(f"{a} {b[:50]}: “{c}”" for a, b, c in d["survivors"]) or "none") + ". Rejected: "
                 + ("; ".join(f"{a} {b[:30]} {v}/{rc}" for a, b, v, rc in d["rejected"]) or "none") + ".\n")
    # ---------------- 7. Q-434
    L.append("## 7. FIX 7 — Q-434: PHRASE_REQUIRES_RECUT\n")
    for qid, spec in rep["phrase_requires_recut"].items():
        L.append(f"**{qid}** — released phrase *“{spec['released_phrase']}”* came from the {spec['released_source']} and exists in neither ratified source. "
                 "Author decision in Gate 7; Gate 6 does not choose.\n")
        L.append("| option | row | wording as printed | translation | present in the built corpus |")
        L.append("|---|---|---|---|---|")
        for i, o in enumerate(spec["options"], 1):
            L.append(f"| {i} | {o['registry_id']} | “{o['wording']}” | {o['translation']} | {_yn(o['present_in_corpus'])}{(' — ' + o['chunk'][:50]) if o.get('chunk') else ''} |")
        dd = next((x for x in rep["details"] if x["queue_id"] == qid), None)
        if dd:
            L.append(f"\nWhat cal-3 found for {qid}: " + ("; ".join(f"{a} {b[:45]}: “{c}”" for a, b, c in dd["survivors"]) or "no survivor") + ".\n")
    # ---------------- 8. opus slice
    a = rep["adjudication"]
    L.append(f"## 8. FIX 6 — the `{adj}` slice\n" if adj else "## 8. Adjudication\n")
    if adj:
        L.append(f"Slice rows: {meta.get('slice_rows')}; plus every cell where `{primary}` rejected all candidates.\n")
        L.append(f"- Candidates adjudicated: **{a['candidates']}** (by route: {a['by_route']}); cells escalated because the primary rejected everything: "
                 f"{a['cells_escalated_all_rejected']}, of which rescued by the adjudicator: {a['cells_rescued']}.")
        L.append(f"- `{adj}` verifier calls this run: **{a['calls_new']}** metered at **{a['cost_new']:.2f} USD**; reused from the seeded run: {a['calls_reused']} "
                 f"({a['cost_reused']:.2f} USD when they were first made).")
        ov = a["overturned"]
        if not ov:
            L.append(f"- **`{adj}` never overturned `{primary}`** on any adjudicated candidate, in either direction.")
        else:
            L.append(f"- Overturns: {ov} (RESCUED = primary rejected, adjudicator accepted; OVERRULED = primary accepted, adjudicator rejected).")
            L.append("\n| cell | row | locator | phrase | route | primary | adjudicator | adjudicator's reason |")
            L.append("|---|---|---|---|---|---|---|---|")
            for o in a["overturns"]:
                L.append(f"| {o['queue_id']} | {o['registry_id']} | {o['locator'][:36]} | “{o['phrase'][:50]}” | {o['route']} | {o['primary']} | {o['adjudicator']} | {(o.get('adjudicator_reason') or '')[:120]} |")
        po = rep.get("planted_overturns") or {}
        L.append(f"- Planted near-misses: adjudicator overturns {po or 'none'}.")
        L.append("")
    # ---------------- 9. goarch
    L.append("## 9. FIX 7 — goarch.org and the dogmatic-tradition page\n")
    gp = rep.get("goarch_probe") or {}
    if gp:
        for k, v in gp.items():
            if isinstance(v, dict):
                L.append(f"- **{k}**: {v.get('result', v)}")
            else:
                L.append(f"- **{k}**: {v}")
    else:
        L.append("(probe not recorded)")
    L.append("")
    # ---------------- 10. cost
    s = rep["models"]; tr = s.get("this_run", {})
    L.append("## 10. Cost\n")
    L.append(f"This run (`{meta['run_id']}`): **{tr.get('calls', 0)} calls, {tr.get('cost_usd', 0.0):.2f} USD metered** "
             f"({', '.join(f'{k}: {v['calls']} calls {v['cost_usd']:.2f} USD' for k, v in sorted(tr.get('by_model', {}).items()))}). "
             f"Reused answered calls from {meta.get('seed_from') or 'no seed'} (served from the seeded audit log, not re-sent): {tr.get('reused_calls', 0)} "
             f"{s.get('reused', {}).get('by_role_model', {})}. By role this run: "
             + ", ".join(f"{k} {v['calls']} ({v['cost_usd']:.2f})" for k, v in sorted(tr.get('by_role', {}).items())) + ".\n")
    L.append("| model | calls (all cached) | cost USD (all) | estimated? |")
    L.append("|---|---|---|---|")
    for k, v in sorted(s.get("by_model", {}).items()):
        L.append(f"| `{k}` ({MODEL_IDS.get(k, k)}) | {v['calls']} | {v['cost_usd']:.2f} | {_yn(v.get('estimated'))} |")
    L.append("")
    # ---------------- 11. delta
    if rep.get("compare_run"):
        L.append(f"## 11. Cell-by-cell delta against {rep['compare_run']} (same-standard hit)\n")
        for m in models:
            dl = rep["delta"][m]
            L.append(f"### `{m}` — gained {len(dl['gained'])}, lost {len(dl['lost'])}, unchanged hit {len(dl['unchanged_hit'])}, unchanged miss {len(dl['unchanged_miss'])}, "
                     f"new to the denominator {len(dl['new'])}\n")
            L.append(f"Gained: {', '.join(dl['gained']) or 'none'}.  \nLost: {', '.join(dl['lost']) or 'none'}.  \nNew: {', '.join(dl['new']) or 'none'}.  \n"
                     f"Unchanged miss: {', '.join(dl['unchanged_miss']) or 'none'}.\n")
            if dl["lost"]:
                L.append("Every loss, by what the locator returned on the cited standard (not merely whether the chunk was supplied):\n")
                L.append("| cell | cited | cited division supplied | locator on cited standard | candidates and verdicts | dropped by guard | cal-3 survivors elsewhere |")
                L.append("|---|---|---|---|---|---|---|")
                for qid in dl["lost"]:
                    d = next((x for x in rep["details"] if x["queue_id"] == qid), {})
                    for rid, o in (d.get("cited_outcome") or {}).items():
                        L.append(f"| {qid} | {rid} | {_yn(o['cited_division_supplied'])} ({o['n_supplied']} chunks, {o.get('supplied_chars') or 0:,} chars) | {o['status']} | "
                                 + ("; ".join(f"“{c['phrase'][:50]}” → {c['primary']}" + (f"/{c['adjudicator']}" if c.get('adjudicator') else "") + f" [{c['primary_reason']}]" for c in o["candidates"]) or "—")
                                 + " | " + ("; ".join(f"“{x['phrase'][:40]}”: {x['reason'][:70]}" for x in o["dropped"]) or "—")
                                 + " | " + ("; ".join(f"{a} {b[:30]}" for a, b, c in d.get("survivors", [])) or "none") + " |")
            L.append("")
    # ---------------- residue
    L.append(f"## 12. Residue under the gate metric ({gate})\n")
    for m in models:
        _r = rep.get("residue", {}).get(m, [])
        L.append(f"\n### `{m}` — {len(_r)} cell(s) not credited\n")
        if not _r:
            L.append("None.\n"); continue
        L.append("| cell | branch | predicate | cited | class | tier-respecting hit | evidence elsewhere | cited standard: what the locator returned |")
        L.append("|---|---|---|---|---|---|---|---|")
        for d in _r:
            what = "; ".join(f"{rid}: {o['status']}, division supplied {_yn(o['cited_division_supplied'])}, "
                             + (", ".join(f"“{c['phrase'][:35]}”→{c['final'] or c['primary']}[{c['primary_reason']}]" for c in o["candidates"]) or "no candidate")
                             + ("; dropped: " + "; ".join(x["reason"][:45] for x in o["dropped"]) if o["dropped"] else "")
                             for rid, o in d["cited_outcome"].items())
            L.append(f"| {d['queue_id']} | {d['branch']} | {d['predicate'][:26]} | {','.join(d['cited'])} | {d['class']} | {_yn(d['hit_tier_respecting'])} | "
                     f"{'; '.join(f'{a} ({b}) {c}' for a, b, c in d['other_evidence']) or '—'} | {what[:400]} |")
    # ---------------- caveats
    L.append("\n## 13. Caveated rows in surviving candidates (AC-03, AC-05/AC-12)\n")
    _cv = rep.get("caveat_hits", [])
    if not _cv:
        L.append("No surviving candidate landed on BSR-EO-04 (Philaret) or BSR-EO-05 (Dositheus).\n")
    else:
        L.append(f"{len(_cv)} candidate(s) landed on a caveated row. The caveat and the reception note travel with the packet entry.\n")
        L.append("| cell | model | row | locator | credited under the gate | caveat |")
        L.append("|---|---|---|---|---|---|")
        for h in _cv:
            L.append(f"| {h['queue_id']} | `{h['model']}` | {h['registry_id']} | {h['locator'][:46]} | {_yn(h.get('credited'))} | {h['caveat'][:120]} |")
    # ---------------- skipped
    L.append("\n## 14. Skipped cells\n")
    for m in models:
        _s = rep.get("skipped_cells", {}).get(m, [])
        L.append(f"`{m}`: {len(_s)} skipped" + (" — " + "; ".join(f"{q_} {reason} ({detail})" for q_, br, pr, reason, detail in _s) if _s else "") + ".  ")
    L.append("\n## 15. Expected-empty cells (NOT LOCATED — CURRENT STANDARD REVIEWED)\n")
    L.append("| cell | branch | predicate | model | outcome | survivors |")
    L.append("|---|---|---|---|---|---|")
    for e in rep["expected_empty"]:
        L.append(f"| {e['queue_id']} | {e.get('branch')} | {e.get('predicate', '')} | {e.get('model', '')} | {e.get('outcome', e.get('status'))} | "
                 f"{'; '.join(f'{a} {b[:40]}: “{c}”' for a, b, c in e.get('survivors', []))} |")
    L.append("\nThe registry is broader than the standards those cells were closed against; a candidate located in another registry standard of the "
             "same branch is new evidence for Gate 7, not a false accept.\n")
    # ---------------- planted
    L.append("## 16. Planted near-misses — false-accept by slice and model\n")
    L.append(f"Fixture status: {rep.get('planted_status')}. PNM-074 was re-cut from the OCA paraphrase to the Percival wording when BSR-EO-06 was "
             "re-sourced (same row, family and near-miss type); the other 73 items are unchanged from cal-1/cal-2. The adjudicator column counts only "
             "the items it ran on (slice rows, and every item the primary rejected); `routed` is the final verdict on all items.\n")
    L.append("| slice | model | planted | false accepts | rate | pending |")
    L.append("|---|---|---|---|---|---|")
    pm = [primary] + ([adj, ROUTED] if adj else [])
    for s_ in sorted(rep["planted"]):
        for m in pm:
            r = rep["planted"][s_].get(m)
            if not r or not (r["n"] or r["pending"]):
                continue
            L.append(f"| {s_} | `{m}` | {r['n']} | {r['false_accept']} | {pct(r['false_accept'] / r['n']) if r['n'] else '—'} | {r['pending']} |")
    items = [(s_, m, it) for s_ in rep["planted"] for m in pm for it in rep["planted"][s_].get(m, {}).get("items", [])]
    if items:
        L.append("\nFalse accepts (each is a verifier failure to keep):\n")
        for s_, m, it in items:
            L.append(f"- {s_} · `{m}` · {it[0]} ({it[1]}) {it[2]} → {it[3]}: {it[4]}")
    L.append("\n## 17. Dositheus slice (BSR-EO-05) — natural candidates from the Eastern Orthodox cells\n")
    L.append("| model | Dositheus candidates | accepted | rejected |")
    L.append("|---|---|---|---|")
    for m, d in rep["dositheus_natural"].items():
        L.append(f"| `{m}` | {d['candidates']} | {d['accept']} | {d['reject']} |")
    # ---------------- corpus state
    L.append("\n## 18. Corpus state at calibration\n")
    L.append("| registry | branch | tier | reception | status | chunks | witness | refusal |")
    L.append("|---|---|---|---|---|---|---|---|")
    for rid, s_ in manifest.get("standards", {}).items():
        L.append(f"| {rid} | {s_.get('branch', '')} | {bare_tier(s_.get('authority_tier'))} | {s_.get('reception_scope', '')} | {s_.get('status')} | {s_.get('n_chunks', 0)} | "
                 f"{_yn(s_.get('witness_only'))} | {(s_.get('citation_refusal') or '—')[:40]} |")
    # ---------------- per cell
    L.append("\n## 19. Per-cell detail (primary verifier; routed hit in the last column)\n")
    L.append("`STD+DIV` same standard and division · `STD` same standard · `TIER` different ratified standard of the branch at an equal or higher tier "
             "· `LOWER` different standard at a lower tier · `WITNESS` survivors only on witness rows · `MISS` no verified evidence.\n")
    L.append("| cell | branch | predicate | cited | existing citation | hit | routed STD | survivors | rejected (reason) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for d in rep["details"]:
        if d["hit_same_division"]:
            hit = "STD+DIV"
        elif d["hit_same_standard"]:
            hit = "STD"
        elif d.get("hit_tier_respecting"):
            hit = "TIER"
        elif d.get("partial_lower_tier"):
            hit = "LOWER"
        elif d.get("witness_only"):
            hit = "WITNESS"
        else:
            hit = "no corpus" if not d["corpus_available"] else "MISS"
        L.append(f"| {d['queue_id']} | {d['branch']} | {d['predicate'][:24]} | {','.join(d['equivalent_registry'])} | {d['existing'][:50]} | {hit} | "
                 f"{_yn(d.get('hit_same_standard_routed')) if d.get('hit_same_standard_routed') is not None else '—'} | "
                 f"{'; '.join(f'{a} {b[:32]}: “{c[:60]}”' for a, b, c in d['survivors'])} | "
                 f"{'; '.join(f'{a} {b[:24]} {v}/{rc}' for a, b, v, rc in d['rejected'])} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    for name in ("run", "plant", "report"):
        p = sub.add_parser(name)
        p.add_argument("--run-id", required=True)
        p.add_argument("--workbook")
        p.add_argument("--backend", default="batch")
        p.add_argument("--locator-model", default="sonnet")
        p.add_argument("--verifier-models", default="sonnet,opus")
        p.add_argument("--branch")
        p.add_argument("--only", help="comma-separated queue ids")
        p.add_argument("--limit", type=int)
        p.add_argument("--seed-from", help="reuse answered calls from another run id (identical calls are not re-sent)")
        p.add_argument("--compare", default="cal-2", help="run id to compute the cell-by-cell delta against")
    a = ap.parse_args()
    return {"run": cmd_run, "plant": cmd_plant, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
