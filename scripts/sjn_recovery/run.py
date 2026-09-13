"""Live run driver (spec §7) — BUILT IN GATE 6, NOT EXECUTED UNTIL THE AUTHOR DECIDES after calibration.

  python scripts/sjn_recovery/run.py --run-id live-1 --branch "Roman Catholic" --locator-model sonnet --verifier-models <chosen> [--backend batch]
  python scripts/sjn_recovery/run.py --run-id live-1 --all-branches ...
  python scripts/sjn_recovery/run.py --run-id live-1 --branch "Roman Catholic" --verifier-models sonnet,opus --rebuild-packet-only
        (no model calls: the packet is rebuilt from the stored cell states under the current allocator)

Per branch, in the §7 order (Roman Catholic → Lutheran → Reformed/Presbyterian → Baptist → Methodist/Wesleyan
→ Anglican → Mennonite/Anabaptist → Eastern Orthodox): every OPEN cell — APP CONFIG gate6_open_cell_rule,
asserted against gate6_open_cell_count at start-up — runs locator (two-pass where a fallback row exists,
plus the exhaustion pass where a sampled standard would otherwise be declared empty) → verifier → coder,
and the packet builder writes recovery-packets/<branch>.json. Nothing writes to the workbook."""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, BRANCHES, ensure_dirs, ROUTE_CAVEATED_ACCEPT, ROUTE_CAVEAT_SAMPLE, LOWER_FLOOR_RULE, CAVEAT_SAMPLE_SHARE  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, open_cells, assert_gate6_scope  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner, EXHAUST_PASS  # noqa: E402
from sjn_recovery.packets import build_branch_packet  # noqa: E402
from sjn_recovery import prompts, coststate  # noqa: E402


def log(msg):
    print(msg, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--workbook")
    ap.add_argument("--backend", default="batch")
    ap.add_argument("--locator-model", default="sonnet")
    ap.add_argument("--verifier-models", required=True, help="primary verifier first (the calibration-chosen model)")
    ap.add_argument("--coder-model")
    ap.add_argument("--branch")
    ap.add_argument("--all-branches", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--i-have-author-authorization", action="store_true",
                    help="required: the live run starts only after the author reviews the calibration report")
    ap.add_argument("--projection-per-cell-usd", type=float, default=0.336,
                    help="the per-cell cost the branch is measured against (Anglican, 2026-09-12: 0.336 USD per cell; cal-3 projected 0.405)")
    ap.add_argument("--branch-cost-cap-usd", type=float, default=None,
                    help="recorded per branch; the executor (api_executor.py --max-cost-usd) is what enforces it")
    ap.add_argument("--no-exhaust", action="store_true", help="disable the Task 2c exhaustion pass (sampled standards are then reported as sampled)")
    ap.add_argument("--rebuild-packet-only", action="store_true",
                    help="no model calls: rebuild the branch packet from the stored cell states (every cell must be DONE)")
    ap.add_argument("--rebuild-note", help="the note recorded in packets_rebuilt / the packet header for this rebuild")
    ap.add_argument("--write-partial-packet", action="store_true",
                    help="no model calls, no cells run: write the branch packet as PARTIAL (partial true, cap_state populated) because "
                         "the run failed — used by branch_loop.py after a non-zero run.py exit (session 5, Task 8b)")
    ap.add_argument("--failure-exit-code", type=int, default=None)
    ap.add_argument("--failure-reason", default="")
    a = ap.parse_args()
    if not a.i_have_author_authorization and not a.rebuild_packet_only and not a.write_partial_packet:
        log("Refusing to start the live run: pass --i-have-author-authorization after the author has reviewed "
            "data-sources/sjn/recovery-runs/calibration-report.md (Gate 6 spec §6, launch constraint 2).")
        return 2
    ensure_dirs()
    reg = Registry(a.workbook)
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    scope = assert_gate6_scope(reg, queue, log)          # fails loudly when the harness and APP CONFIG disagree
    cells = open_cells(queue)
    branches = BRANCHES if a.all_branches else [a.branch]
    vmodels = a.verifier_models.split(",")
    llm = LLM(a.run_id, backend=a.backend, model=a.locator_model, log=log)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, a.run_id, "cells"), a.locator_model, vmodels,
                        coder_model=a.coder_model, log=log, run_coder=True, exhaust=not a.no_exhaust)
    run_path = os.path.join(RUNS_DIR, a.run_id, "run.json")
    prior = {}
    if os.path.exists(run_path):
        with open(run_path, encoding="utf-8") as fh:
            prior = json.load(fh)
    branch_cost = dict(prior.get("branch_spend") or {})
    rebuilt = dict(prior.get("packets_rebuilt") or {})

    if a.rebuild_packet_only:
        for br in branches:
            bc = [c for c in cells if c["branch"] == br]
            not_done = [c["queue_id"] for c in bc if (runner.load(c["queue_id"]) or {}).get("phase") != "DONE"]
            if not_done:
                log(f"!! {br}: {len(not_done)} open cell(s) have no DONE state under run {a.run_id}: {not_done[:8]} — nothing rebuilt")
                return 3
            # Session 4: every stored verdict is re-finalised under the lower-floor rule (2a/2b/2c) and every cell re-allocated
            # under the speaks_for group rule, from the stored rubrics — no model calls. The cell states are saved so that
            # survivors / allocation / coder_skipped agree with the packet.
            verdict_changes, cells_changed = {}, 0
            for c in bc:
                st = runner.load(c["queue_id"])
                changed = runner.refinalize(st, br)
                runner.save(st)
                if changed:
                    verdict_changes[c["queue_id"]] = changed; cells_changed += 1
            note = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "from": "stored cell states (candidates, rubrics, coder proposals)",
                    "model_calls": 0, "workbook": os.path.basename(reg.path), "cells": len(bc),
                    "verdict_rule": LOWER_FLOOR_RULE, "cells_with_verdict_changes": cells_changed, "verdict_changes": verdict_changes,
                    "note": a.rebuild_note or ("rebuilt 2026-09-13 (session 4) under the speaks_for candidate-slot diversity rule (Task 1), the lower-floor "
                             "verdict rule 2a/2b/2c (Task 2) and the exhaustion mark (Task 4a); the IDIOM_OR_FORMULA hazard (Task 3) applies "
                             "only to verifier calls made from session 4 on and is not reflected in these stored verdicts")}
            log(f"== {br}: rebuilding the packet from {len(bc)} stored cell states (no model calls); verdicts changed in {cells_changed} cell(s)")
            for qid, ch in verdict_changes.items():
                for cid, (b0, b1) in ch.items():
                    log(f"   {qid} {cid}: {b0} -> {b1}")
            build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log, rebuilt_from=note)
            rebuilt[br] = note
        prior["packets_rebuilt"] = rebuilt
        prior["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(run_path, "w", encoding="utf-8") as fh:
            json.dump(prior, fh, indent=1)
        return 0

    # 1d: the per-branch cap lives in recovery-runs/<run>/cost-state.json and survives every invocation of
    # run.py and api_executor.py. Registered here before the first cell; enforced by the executor; reconciled below.
    state = coststate.load(a.run_id)
    if a.write_partial_packet:
        for br in branches:
            bc = [c for c in cells if c["branch"] == br]
            write_failed_partial(br, bc, runner, reg, preds, comps, a, state, a.failure_exit_code, a.failure_reason or "run.py exited non-zero")
        return 0
    for br in branches:
        bc = [c for c in cells if c["branch"] == br]
        if a.limit:
            bc = bc[:a.limit]
        b = coststate.register_branch(state, br, a.branch_cost_cap_usd, [c["queue_id"] for c in bc])
        coststate.save(state)
        cap_hit = coststate.over_cap(b)
        if cap_hit:
            log(f"!! {br}: cost cap already reached ({b['spent_usd']:.2f} of {b['cap_usd']} USD, status {b['status']}); "
                f"running no further cells; the partial packet is written below. Raise --branch-cost-cap-usd to continue.")
        else:
            try:
                for c in bc:
                    runner.run_cell(c)
            except BaseException as e:                     # session 5, Task 8b: a crash leaves a PARTIAL packet, then fails loudly
                import traceback
                reason = f"{type(e).__name__}: {e} (while running cells; {traceback.format_exc().strip().splitlines()[-3][:200]})"
                log(f"!! {br}: run.py FAILED — {reason}; writing the PARTIAL packet before exiting non-zero")
                try:
                    write_failed_partial(br, bc, runner, reg, preds, comps, a, coststate.load(a.run_id), 1, reason)
                except Exception as e2:                    # the partial writer must never mask the original failure
                    log(f"!! {br}: the partial packet could not be written either: {type(e2).__name__}: {e2}")
                raise
        done = sum(1 for c in bc if (runner.load(c["queue_id"]) or {}).get("phase") == "DONE")
        log(f"== {br}: {done}/{len(bc)} open cells DONE; pending calls {len(set(llm.pending))}")
        spend = branch_spend(llm, bc, a.projection_per_cell_usd, a.branch_cost_cap_usd)
        coststate.reconcile(state, br, spend["cost_usd"], spend["calls"])
        b = state["branches"][br]
        cap_hit = coststate.over_cap(b)
        spend["cap_state"] = {k: b.get(k) for k in ("cap_usd", "spent_usd", "calls", "status", "cap_hit_at")}
        spend["coder"] = coder_savings(llm, runner, bc)
        spend["exhaustion"] = exhaustion_report(llm, runner, bc)
        spend["caveat_slice"] = caveat_slice_report(llm, runner, bc)
        spend["lower_floor"] = lower_floor_report(runner, bc)
        log(f"   spend so far: {spend['calls']} metered calls, {spend['cost_usd']:.2f} USD "
            f"({spend['cost_per_cell_usd']:.3f}/cell vs projection {a.projection_per_cell_usd:.3f}; "
            f"projected {spend['projected_usd']:.2f}; cap {b['cap_usd']}; cost-state {b['spent_usd']:.2f} {b['status']})")
        if spend["coder"]["survivors"]:
            cs = spend["coder"]
            log(f"   coder (1c): {cs['coded']} coded of {cs['survivors']} survivors; {cs['skipped_by_allocation']} skipped by allocation "
                f"= {cs['usd_avoided_measured']:.2f} USD at the measured {cs['mean_coder_call_usd']:.4f}/call")
        ex = spend["exhaustion"]
        if ex["cells_entered"]:
            log(f"   exhaustion (2c): {ex['cells_entered']} cell(s) entered, {ex['cells_changed']} changed from empty to filled; "
                f"{ex['locator_calls']} locator calls + {ex['verifier_calls']} verifier calls = {ex['cost_usd']:.2f} USD "
                f"({ex['cost_per_entered_cell_usd']:.3f}/entered cell); standards exhausted {ex['standards_exhausted']}, stopped early {ex['standards_stopped_early']}")
        cv = spend["caveat_slice"]
        if cv["candidates"]:
            log(f"   caveat second rubrics: {cv['candidates']} candidate(s) ({cv['sampled']} by the 2c sample of {cv['eligible']} eligible, share "
                f"{cv['share_actual']}); {cv['calls']} calls, {cv['cost_usd']:.2f} USD; {cv['lower_floor_applied']} lower-floor applied, "
                f"{cv['overturned']} overturned")
        lf = spend["lower_floor"]
        if lf["disagreements"]:
            log(f"   lower-floor rule (2a): {lf['disagreements']} floor disagreement(s) between the models; {lf['applied']} lowered the final floor, "
                f"{lf['refused']} candidate(s) refused by it (of which {lf['rescues_refused']} would have been opus rescues)")
        if done == len(bc):
            b["status"] = "DONE"
            build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log)
        elif cap_hit:
            b["status"] = "CAP_HIT"
            log(f"!! {br}: STOPPED by the cost cap ({b['spent_usd']:.2f} of {b['cap_usd']} USD) with {len(bc) - done} cell(s) unfinished — "
                f"writing the PARTIAL packet")
            build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log, partial=spend["cap_state"])
        coststate.save(state)
        branch_cost[br] = spend
    all_branches = [x for x in BRANCHES if x in set(prior.get("branches") or []) | set(branches)]
    with open(run_path, "w", encoding="utf-8") as fh:
        json.dump({"run_id": a.run_id, "kind": "live", "workbook": os.path.basename(reg.path), "app_master_version": reg.app_master_version,
                   "gate6_scope": {k: scope[k] for k in ("identity", "ratified_open_count", "computed_open", "closed_by_state")},
                   "locator_model": a.locator_model, "verifier_models": vmodels, "coder_model": a.coder_model or a.locator_model,
                   "backend": a.backend, "prompt_version": prompts.PROMPT_VERSION, "prompt_versions": prompts.PROMPT_VERSIONS, "branches": all_branches,
                   "retrieval": "PER_STANDARD", "exhaustion": not a.no_exhaust, "routing": runner.routing, "slice_rows": sorted(runner.slice_rows),
                   "caveat_slice_route": ROUTE_CAVEATED_ACCEPT, "caveat_sample_route": ROUTE_CAVEAT_SAMPLE, "caveat_sample_share": CAVEAT_SAMPLE_SHARE,
                   "verdict_rule": LOWER_FLOOR_RULE,
                   "projection_per_cell_usd": a.projection_per_cell_usd, "branch_cost_cap_usd": a.branch_cost_cap_usd,
                   "cost_state_file": os.path.relpath(coststate.path_for(a.run_id), os.path.dirname(os.path.dirname(RUNS_DIR))).replace("\\", "/"),
                   "branch_spend": branch_cost, "packets_rebuilt": rebuilt,
                   "workbooks": sorted(set((prior.get("workbooks") or [prior.get("workbook")] if prior else []) + [os.path.basename(reg.path)]) - {None}),
                   "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh, indent=1)
    return 10 if llm.pending else 0


def write_failed_partial(br, bc, runner, reg, preds, comps, a, state, exit_code, reason):
    """Task 8b (session 5): a branch that ends on a non-zero exit gets its packet written with partial true and cap_state
    populated — the cost-state figures plus what stopped it — so a partial packet can never be mistaken for a finished one.
    Also marks the branch RUN_FAILED in cost-state.json. No model calls."""
    b = coststate.register_branch(state, br, a.branch_cost_cap_usd, [c["queue_id"] for c in bc])
    done = sum(1 for c in bc if (runner.load(c["queue_id"]) or {}).get("phase") == "DONE")
    b["status"] = "RUN_FAILED"
    b["failed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    coststate.save(state)
    cap_state = {k: b.get(k) for k in ("cap_usd", "spent_usd", "calls", "status", "cap_hit_at")}
    cap_state.update({"stopped_by": "RUN_FAILED", "exit_code": exit_code, "reason": reason[:600], "failed_at": b["failed_at"],
                      "cells_done": done, "cells": len(bc)})
    log(f"!! {br}: writing the PARTIAL packet (RUN_FAILED, exit {exit_code}): {done}/{len(bc)} cells DONE")
    try:
        build_branch_packet(br, bc, runner, reg, preds, comps, a.run_id, log, partial=cap_state)
    except Exception as e:
        # The failure may lie in a cell state the builder itself cannot read. Then the packet is a minimal FAILURE record —
        # never left as whatever finished packet stood before (that one stays in git history).
        from sjn_recovery.config import PACKETS_DIR
        cap_state["packet_builder_error"] = f"{type(e).__name__}: {e}"[:400]
        phases = {}
        for c in bc:
            try:
                phases[c["queue_id"]] = (runner.load(c["queue_id"]) or {}).get("phase") or "NOT_RUN"
            except Exception as e3:
                phases[c["queue_id"]] = f"UNREADABLE ({type(e3).__name__})"
        stub = {"branch": br, "run_id": a.run_id, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "partial": True, "cap_state": cap_state, "failure_record_only": True, "cells": len(bc), "cells_with_candidates": None,
                "cells_not_finished": sum(1 for p in phases.values() if p != "DONE") or len(bc),
                "note": "RUN FAILED and the packet builder could not read the cell states: this is a failure record, not a packet",
                "cards": [{"queue_id": q, "status": (f"NOT_FINISHED ({p}): branch stopped by a run failure" if p != "DONE" else
                                                     "UNREVIEWABLE (cell DONE, but no card was built): branch stopped by a run failure")}
                          for q, p in phases.items()]}
        path = os.path.join(PACKETS_DIR, f"{br.casefold().replace(' / ', '-').replace(' ', '-')}.json")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(stub, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        log(f"!! {br}: packet builder failed too ({cap_state['packet_builder_error'][:160]}); wrote a minimal FAILURE record to {path}")


def _call_cost(llm, call_id):
    rec = llm._cache.get(call_id) if call_id else None
    return (rec or {}).get("cost_usd") or 0.0


def coder_savings(llm, runner, cells):
    """1c, MEASURED on this branch: survivors vs coder calls actually made vs candidates the allocation
    dropped before the coder ran; USD avoided = skipped × this branch's own mean metered coder-call cost."""
    survivors = coded = skipped = 0
    for c in cells:
        st = runner.load(c["queue_id"]) or {}
        survivors += len(st.get("survivors") or [])
        coded += sum(1 for v in (st.get("coding") or {}).values() if v.get("status") == "DONE")
        skipped += len(st.get("coder_skipped") or {})
    qids = {c["queue_id"] for c in cells}
    costs = [r.get("cost_usd") or 0.0 for r in llm._cache.values()
             if r.get("run_id") == llm.run_id and r.get("role") == "coder" and (r.get("meta") or {}).get("queue_id") in qids]
    mean = (sum(costs) / len(costs)) if costs else 0.0
    return {"survivors": survivors, "coded": coded, "skipped_by_allocation": skipped, "mean_coder_call_usd": round(mean, 5),
            "usd_avoided_measured": round(skipped * mean, 4),
            "basis": "skipped = survivors the allocator dropped before coding (measured); USD = skipped x this branch's mean metered coder call"}


def exhaustion_report(llm, runner, cells):
    """Task 2c, MEASURED: the cells that entered exhaustion, what it cost (locator batch calls + the verifier
    calls on the candidates those batches produced) and how many empties it changed into filled cells."""
    entered = changed = loc_calls = ver_calls = 0
    cost = 0.0
    exhausted = stopped = 0
    per_cell = []
    for c in cells:
        st = runner.load(c["queue_id"]) or {}
        ex = st.get("exhaustion")
        p3 = (st.get("passes") or {}).get(EXHAUST_PASS)
        if not ex or not p3:
            continue
        entered += 1
        cell_cost, cell_loc, cell_ver = 0.0, 0, 0
        for e in (p3.get("per_standard") or {}).values():
            if e.get("call_id"):
                cell_loc += 1; cell_cost += _call_cost(llm, e["call_id"])
        for cand in p3.get("candidates", []):
            for m, v in (st.get("verifications", {}).get(cand["candidate_id"]) or {}).items():
                if isinstance(v, dict) and v.get("call_id"):
                    cell_ver += 1; cell_cost += _call_cost(llm, v["call_id"])
        for rid, prog in (p3.get("progress") or {}).items():
            exhausted += 1 if prog.get("exhausted") else 0
            stopped += 1 if prog.get("stopped_early") else 0
        if ex.get("changed_outcome"):
            changed += 1
        loc_calls += cell_loc; ver_calls += cell_ver; cost += cell_cost
        per_cell.append({"queue_id": c["queue_id"], "locator_calls": cell_loc, "verifier_calls": cell_ver, "cost_usd": round(cell_cost, 4),
                         "changed_outcome": bool(ex.get("changed_outcome")), "standards": p3.get("progress")})
    return {"cells_entered": entered, "cells_changed": changed, "locator_calls": loc_calls, "verifier_calls": ver_calls,
            "cost_usd": round(cost, 4), "cost_per_entered_cell_usd": round(cost / entered, 4) if entered else 0.0,
            "standards_exhausted": exhausted, "standards_stopped_early": stopped, "per_cell": per_cell}


def caveat_slice_report(llm, runner, cells):
    """MEASURED: caveated accepts that carried a second rubric — the session-3 adjudication route on stored branches,
    the session-4 disclosure sample (2c) on new ones — with calls, cost, the sample's eligible/sampled counts and
    how often the lower-floor rule (2a) changed the final floor."""
    items, decisions = [], []
    for c in cells:
        st = runner.load(c["queue_id"]) or {}
        for x in runner.caveat_slice_stats(st):
            x["queue_id"] = c["queue_id"]; x["cost_usd"] = round(_call_cost(llm, x.get("call_id")), 4)
            items.append(x)
        decisions.extend(runner.caveat_sample_stats(st))
    calls = sum(1 for x in items if x.get("call_id"))
    over = sum(1 for x in items if x.get("overturned"))
    sampled = sum(1 for d in decisions if d.get("sampled"))
    return {"adjudicator": runner.adjudicator, "candidates": len(items), "calls": calls, "cost_usd": round(sum(x["cost_usd"] for x in items), 4),
            "overturned": over, "overturn_rate": round(over / len(items), 3) if items else 0.0,
            "lower_floor_applied": sum(1 for x in items if x.get("lower_floor_applied")),
            "eligible": len(decisions), "sampled": sampled, "share_cap": CAVEAT_SAMPLE_SHARE,
            "share_actual": round(sampled / len(decisions), 3) if decisions else None, "items": items}


def lower_floor_report(runner, cells):
    """2a, MEASURED on this branch: floor disagreements between the two models, how many lowered the final floor,
    and how many candidates the lower floor refused (of which how many the adjudicator alone would have rescued)."""
    dis = applied = refused = rescues_refused = 0
    items = []
    for c in cells:
        st = runner.load(c["queue_id"]) or {}
        for cid, v in (st.get("verifications") or {}).items():
            fin = v.get("final") or {}
            if not fin.get("floor_disagreement"):
                continue
            dis += 1
            applied += 1 if fin.get("lower_floor_applied") else 0
            adj = fin.get("adjudicator_verdict") in ("ACCEPT", "ACCEPT_WITH_CAVEAT")
            gone = fin.get("lower_floor_applied") and fin.get("verdict") == "REJECT" and fin.get("reason_code_final") == "BELOW_FLOOR"
            if gone:
                refused += 1
                if adj and fin.get("primary_verdict") == "REJECT":
                    rescues_refused += 1
            items.append({"queue_id": c["queue_id"], "candidate_id": cid, "route": fin.get("route"), "floors": fin.get("floor_by_model"),
                          "floor_final": fin.get("floor_final"), "verdict": fin.get("verdict"), "refused_by_lower_floor": bool(gone)})
    return {"disagreements": dis, "applied": applied, "refused": refused, "rescues_refused": rescues_refused, "items": items}


def branch_spend(llm, cells, projection_per_cell, cap):
    """Metered spend of this run on one branch's cells, from the audit log (calls whose meta names one of
    the branch's queue ids), against the calibrated projection and the per-branch cap."""
    qids = {c["queue_id"] for c in cells}
    recs = [r for r in llm._cache.values() if r.get("run_id") == llm.run_id and (r.get("meta") or {}).get("queue_id") in qids]
    cost = sum(r.get("cost_usd") or 0.0 for r in recs)
    by_role = {}
    for r in recs:
        k = f"{r.get('role')}/{r.get('executor_model') or r.get('model')}"
        b = by_role.setdefault(k, {"calls": 0, "cost_usd": 0.0})
        b["calls"] += 1; b["cost_usd"] += r.get("cost_usd") or 0.0
    return {"cells": len(cells), "calls": len(recs), "cost_usd": round(cost, 4), "calls_per_cell": round(len(recs) / max(1, len(cells)), 2),
            "cost_per_cell_usd": round(cost / max(1, len(cells)), 4), "projection_per_cell_usd": projection_per_cell,
            "projected_usd": round(projection_per_cell * len(cells), 2), "cap_usd": cap, "over_cap": bool(cap and cost > cap),
            "estimated": any((r.get("usage") or {}).get("estimated") for r in recs), "by_role": by_role}


if __name__ == "__main__":
    sys.exit(main())
