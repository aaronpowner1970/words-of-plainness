"""Gate 6 session 9, Task 5: measure verifier gate6-v1.6 against gate6-v1.3 under the standing rule as amended by R6-20.

The rule (docs/gate6/WoP_SJN_Gate6_MeasurementRule.md):
  - each measured set runs ONCE per version;
  - an item whose verdict (accept vs reject) differs between baseline and candidate gets 3 replicates under EACH version,
    and the gate reads the majority;
  - R6-20: an item that triggers a STOP condition gets 5 replicates per version before the stop holds, and the stop reads
    the majority of those 5. Q-160 is the stop item here: 5 replicates under v1.6 always (as ruled); v1.3 is topped up
    from its 3 on record to 5 only if the v1.6 majority would trigger the stop.

Baseline gate6-v1.3, from existing results: tp-3; s7-v13-control; session 7's v1.3 replicates of TP-049 / TP-050; session 8's
v1.3 replicates of Q-160 / Q-161 / Q-213 (all reused, never re-run, and named in the artifact).

R6-17's condition did NOT hold (TP-049's chunk is BSR-MW-01 Article I; "the Son is eternally begotten of the Father" is not
in it), so there is no tp-5. Measurement (1) is therefore run on tp-4 under v1.6 and reported, but check (1) as ruled —
tp-5 recall >= 0.967 — cannot be evaluated, and the gate cannot put v1.6 in force on it. The three ranked in-chunk
candidates for TP-049 are measured once under v1.3 and once under v1.6 for the author's information; they are not fixture
items.

  1. python scripts/sjn_recovery/truepos.py run --run-id tp-4-v1.6 --fixture-from tp-4 --verifier-version gate6-v1.6
  2. python data-sources/sjn/recovery-runs/session9/measure_v16.py      # writes pending jobs, prints run ids (exit 10)
     python scripts/sjn_recovery/api_executor.py --run-id <id> --workers 6 --max-cost-usd <n> --key-file <.env>
     ... repeat 2 until it exits 0; it writes measure-v16.json.

NOTHING here touches a stored cell state, a packet, PROMPT_VERSIONS or the workbook.
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "session7"))

from sjn_recovery.config import RUNS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import prompts, store  # noqa: E402
import measure_v14 as s7m  # noqa: E402

BASE, CAND = "gate6-v1.3", "gate6-v1.6"
TP_BASE_RUN, TP_CAND_RUN = "tp-3", "tp-4-v1.6"
C_BASE_RUN, C_CAND_RUN = "s7-v13-control", "s9-v16"
INFO_BASE_RUN = "s9-v13-info"                  # TP-049 in-chunk candidates under v1.3 (information only)
REPLICATES, STOP_REPLICATES = 3, 5
RECALL_FLOOR_ACCEPTED = 58
ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
Q160 = "Q-160-p1-BSR-MA-01-1"
Q161 = s7m.CREEDAL_IDIOM
Q297 = "Q-297-p1-BSR-RC-01-1"                  # Task 2: the one finished-branch card accept resting on a Y rubric
S7_REPLICATES = os.path.join(HERE, "..", "session7", "replicate-tp049-tp050.json")
S8_REPLICATES = os.path.join(HERE, "..", "session8", "replicates.json")

# Task 1 (R6-17 condition failed): the three ranked in-chunk candidates, verbatim in BSR-MW-01 Article I
TP049_CANDIDATES = [
    ("TP-049-C1", "three persons, of one substance, power, and eternity—the Father, the Son, and the Holy Ghost"),
    ("TP-049-C2", "of one substance, power, and eternity—the Father, the Son"),
    ("TP-049-C3", "And in unity of this Godhead there are three persons"),
]


def acc(v):
    return v in ACCEPTS


def _cell(it):
    return {"queue_id": it["queue_id"], "family_id": it["family_id"], "branch": it["branch"], "predicate": it["predicate"]}


def _cand(it, suffix=""):
    return {"candidate_id": it["candidate_id"] + suffix, "registry_id": it["registry_id"], "locator": it["locator"],
            "phrase": it["phrase"], "floor_claim": it.get("floor_claim") or "FULL", "chunk_text": it["chunk_text"], "rationale": ""}


AFTER_FIELDS = ("subject_is_required", "grammatical_subject", "speech_act_is_assertion", "floor", "floor_model", "floor_capped_by",
                "floor_reason", "hazard_flags", "asserted_outside_formula", "partial_asserts_predicate", "spirit_name_in_phrase",
                "refused_by", "verdict_before_outside_formula_guard", "verdict", "reason_code_final", "reason", "prompt_version",
                "prompt_variant")


def tp_items():
    fixture = json.load(open(os.path.join(RUNS_DIR, "tp-4", "fixture.json"), encoding="utf-8"))
    out = {}
    for it in fixture["items"]:
        chunk = next(c for c in store.load_chunks(it["registry_id"]) if c["locator"] == it["locator"])
        assert chunk["text_hash"] == it["chunk_hash"], it["id"]
        out[it["id"]] = {"candidate_id": it["id"], "queue_id": it["id"], "family_id": it["family_id"],
                         "branch": it["registry_branch"], "predicate": it["predicate"], "registry_id": it["registry_id"],
                         "locator": it["locator"], "phrase": it["phrase"], "floor_claim": "FULL", "chunk_text": chunk["text"]}
    return out


def q297_item():
    cell = json.load(open(os.path.join(RUNS_DIR, "live-1", "cells", "Q-297.json"), encoding="utf-8"))
    c = next(x for p in cell["passes"].values() for x in p.get("candidates", []) if x["candidate_id"] == Q297)
    v = cell["verifications"][Q297]
    return {"kinds": ["TASK2_CARD_RESCUE"], "candidate_id": Q297, "queue_id": "Q-297", "family_id": cell["family_id"],
            "branch": cell["branch"], "predicate": cell["predicate"], "registry_id": c["registry_id"], "locator": c["locator"],
            "phrase": c["phrase"], "floor_claim": c.get("floor_claim") or "FULL", "chunk_text": c["chunk_text"],
            "where": "card",
            "before": {"verdict": v["final"]["verdict"], "adjudicated_by": v["final"]["adjudicated_by"],
                       "asserted_outside_formula": v["sonnet"].get("asserted_outside_formula"),
                       "prompt_version": v["sonnet"].get("prompt_version")}}


def tp049_candidate_items(tps):
    base = tps["TP-049"]
    out = []
    for cid, phrase in TP049_CANDIDATES:
        from sjn_recovery import guards
        assert guards.check_phrase(phrase, base["chunk_text"])[0], cid
        out.append(dict(base, candidate_id=cid, queue_id=cid, phrase=phrase, kinds=["TP049_CANDIDATE_INFO"], where="info",
                        before=None))
    return out


def run_single(run_id, version, reg, preds, items):
    prompts.set_verifier_version(version)
    llm = LLM(run_id, backend="batch", model="sonnet", log=lambda m: None)
    runner = CellRunner(llm, s7m._PrimaryOnly(reg), preds, {}, os.path.join(HERE, "state", run_id), "sonnet", ["sonnet"],
                        log=lambda m: None, run_coder=False)
    path = os.path.join(HERE, f"measure-results-{run_id}.json")
    results = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    pending = 0
    for it in items:
        r = results.setdefault(it["candidate_id"], {})
        if (r.get("rubric") or {}).get("status") != "DONE":
            r["rubric"] = runner.verify(_cell(it), _cand(it), "sonnet")
        if r["rubric"].get("status") == "PENDING":
            pending += 1
            continue
        r.update({k: it.get(k) for k in ("kinds", "branch", "queue_id", "predicate", "family_id", "where", "registry_id",
                                         "locator", "phrase", "before")})
        r["after"] = {k: r["rubric"].get(k) for k in AFTER_FIELDS}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    return results, pending


def tp_single(run_id):
    p = os.path.join(RUNS_DIR, run_id, "tp-results.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    if any(r.get("status") != "DONE" for r in d.values()) or len(d) != 60:
        return None
    return {k: {"verdict": r["verdicts"]["final"]["verdict"], "reason_code": r["verdicts"]["final"].get("reason_code_final"),
                "refused_by": r["verdicts"]["final"].get("refused_by") or r["verdicts"]["sonnet"].get("refused_by"),
                "variant": r["verdicts"]["sonnet"].get("prompt_variant"), "floor": r["verdicts"]["sonnet"].get("floor"),
                "hazard_flags": r["verdicts"]["sonnet"].get("hazard_flags"),
                "asserted_outside_formula": r["verdicts"]["sonnet"].get("asserted_outside_formula"),
                "reason": r["verdicts"]["sonnet"].get("reason")}
            for k, r in d.items()}


def main():
    reg = Registry()
    preds = load_predicates(reg.wb)
    tp_base, tp_cand = tp_single(TP_BASE_RUN), tp_single(TP_CAND_RUN)
    if tp_cand is None:
        print(f"== {TP_CAND_RUN} not complete: python scripts/sjn_recovery/truepos.py run --run-id {TP_CAND_RUN} "
              f"--fixture-from tp-4 --verifier-version {CAND}")
        return 10
    tps = tp_items()
    c_items = s7m.targets()
    info_items = tp049_candidate_items(tps)
    extra = [q297_item()] + info_items
    c_cand, pend_c = run_single(C_CAND_RUN, CAND, reg, preds, c_items + extra)
    info_base, pend_i = run_single(INFO_BASE_RUN, BASE, reg, preds, info_items)
    if pend_c or pend_i:
        print(f"== pending: {C_CAND_RUN} {pend_c} under {CAND}; {INFO_BASE_RUN} {pend_i} under {BASE}")
        return 10
    c_base = json.load(open(os.path.join(HERE, "..", "session7", f"measure-results-{C_BASE_RUN}.json"), encoding="utf-8"))

    # ---- which items differ (the gate sets only: the 60 true positives and the 16 session 7 candidates)
    tp_diff = sorted(k for k in tp_cand if acc(tp_cand[k]["verdict"]) != acc(tp_base[k]["verdict"]))
    c_diff = sorted(k for k in c_base if acc(c_cand[k]["after"]["verdict"]) != acc(c_base[k]["after"]["verdict"]))
    by_cid = {it["candidate_id"]: it for it in c_items}
    rep_items = {k: tps[k] for k in tp_diff}
    rep_items.update({k: by_cid[k] for k in c_diff})
    rep_items[Q160] = by_cid[Q160]
    n_reps = {k: (STOP_REPLICATES if k == Q160 else REPLICATES) for k in rep_items}

    # ---- replicates on record under v1.3 (reused, never re-run)
    on_record = {}
    for path, label in ((S7_REPLICATES, "session7 replicate"), (S8_REPLICATES, None)):
        for key, x in json.load(open(path, encoding="utf-8")).items():
            item, version, n = key.split("|")
            if version != BASE or x.get("status", "DONE") != "DONE":
                continue
            on_record[key] = {"status": "DONE", "item": item, "version": version, "replicate": int(n),
                              "source": label or x.get("source"), **{f: x.get(f) for f in (
                                  "verdict", "reason_code_final", "floor", "hazard_flags", "subject_is_required",
                                  "speech_act_is_assertion", "asserted_outside_formula", "refused_by", "reason")},
                              "prompt_variant": BASE}
    rep_path = os.path.join(HERE, "replicates.json")
    reps = json.load(open(rep_path, encoding="utf-8")) if os.path.exists(rep_path) else {}

    def majority(k, version, n=None):
        n = n or n_reps[k]
        keys = [f"{k}|{version}|{i}" for i in range(1, n + 1)]
        vs = [reps[x]["verdict"] for x in keys if x in reps]
        a = sum(acc(v) for v in vs)
        return {"accepts": a, "of": len(vs), "accept_majority": a * 2 > len(vs), "verdicts": vs, "complete": len(vs) == n}

    def ensure(version, k, n_from, n_to, pending_runs):
        it = rep_items[k]
        prompts.set_verifier_version(version)
        for n in range(n_from, n_to + 1):
            key = f"{k}|{version}|{n}"
            if (reps.get(key) or {}).get("status") == "DONE":
                continue
            if key in on_record:
                reps[key] = on_record[key]
                continue
            run_id = f"s9-rep-{version.replace('gate6-', '')}-{n}"
            llm = LLM(run_id, backend="batch", model="sonnet", log=lambda m: None)
            runner = CellRunner(llm, s7m._PrimaryOnly(reg), preds, {}, os.path.join(HERE, "rep-state", run_id), "sonnet",
                                ["sonnet"], log=lambda m: None, run_coder=False)
            rub = runner.verify(_cell(it), _cand(it, f"-{run_id}"), "sonnet")
            if rub.get("status") == "PENDING":
                pending_runs.add(run_id)
                continue
            reps[key] = {"status": "DONE", "item": k, "version": version, "replicate": n, "source": run_id,
                         **{f: rub.get(f) for f in ("verdict", "reason_code_final", "floor", "floor_model", "floor_capped_by",
                                                    "hazard_flags", "subject_is_required", "speech_act_is_assertion",
                                                    "asserted_outside_formula", "spirit_name_in_phrase", "refused_by",
                                                    "verdict_before_outside_formula_guard", "reason", "prompt_variant")}}

    pending_runs = set()
    for k in rep_items:
        base_n = REPLICATES if k == Q160 else n_reps[k]       # Q-160 under v1.3: its 3 on record, topped up only on a stop
        ensure(BASE, k, 1, base_n, pending_runs)
        ensure(CAND, k, 1, n_reps[k], pending_runs)
    q160_stop_triggered = False
    if not pending_runs and majority(Q160, CAND)["accept_majority"]:
        q160_stop_triggered = True
        ensure(BASE, Q160, REPLICATES + 1, STOP_REPLICATES, pending_runs)   # R6-20: 5 per version before the stop holds
    with open(rep_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reps, fh, ensure_ascii=False, indent=1)
    if pending_runs:
        print(f"== replicates pending in: {sorted(pending_runs)}  (items: {sorted(rep_items)})")
        return 10

    def read(k, version, single):
        if k in rep_items:
            n = n_reps[k] if (version == CAND or k != Q160 or q160_stop_triggered) else REPLICATES
            return majority(k, version, n)["accept_majority"]
        return acc(single)

    # ---- (1) recall: tp-5 does not exist; tp-4 under v1.6, majority-read, reported
    tp_read = {k: read(k, CAND, tp_cand[k]["verdict"]) for k in tp_cand}
    accepted = sum(tp_read.values())
    chk1 = {"fixture_ruled": "tp-5", "fixture_measured": "tp-4 (tp-5 not built: R6-17's condition did not hold)",
            "single_run_accepted": sum(acc(v["verdict"]) for v in tp_cand.values()), "items": 60,
            "baseline_tp3_accepted": sum(acc(v["verdict"]) for v in tp_base.values()),
            "differing_items": tp_diff, "majority_read_accepted": accepted, "majority_read_recall": round(accepted / 60, 3),
            "refused_majority_read": sorted(k for k, v in tp_read.items() if not v),
            "without_TP049": {"accepted": sum(v for k, v in tp_read.items() if k != "TP-049"), "items": 59},
            "meets_58_of_60_on_tp4": accepted >= RECALL_FLOOR_ACCEPTED,
            "ok": None, "evaluable": False,
            "why_not_evaluable": "check (1) is ruled on tp-5, which R6-17 builds only from a verbatim asserting phrase in TP-049's chunk; none exists"}
    # ---- (2) Q-161
    q161 = read(Q161, CAND, c_cand[Q161]["after"]["verdict"])
    chk2 = {"single_v16": c_cand[Q161]["after"]["verdict"], "single_v13_control": c_base[Q161]["after"]["verdict"],
            "replicated": Q161 in rep_items, "accept_majority_v16": q161, "ok": q161}
    # ---- (3) the 12 non-creedal IDIOM rejections: none may accept by majority under v1.6
    nc = sorted(k for k, r in c_base.items() if "IDIOM_NON_CREEDAL_REJECTION" in r["kinds"])
    acc16 = sorted(k for k in nc if read(k, CAND, c_cand[k]["after"]["verdict"]))
    acc13 = sorted(k for k in nc if read(k, BASE, c_base[k]["after"]["verdict"]))
    chk3 = {"n": len(nc), "accept_under_v16_read": acc16, "accept_under_v13_read": acc13, "ok": not acc16}
    # ---- (4) Q-277
    q277 = {k: read(k, CAND, c_cand[k]["after"]["verdict"]) for k in s7m.Q277}
    chk4 = {"accept_read_v16": q277, "verdicts_single_v16": {k: c_cand[k]["after"]["verdict"] for k in s7m.Q277},
            "ok": len(set(q277.values())) == 1}
    # ---- (5) Q-160: 5 under v1.6; the stop reads the majority of 5 (R6-20)
    m16 = majority(Q160, CAND, STOP_REPLICATES)
    m13 = majority(Q160, BASE, STOP_REPLICATES if q160_stop_triggered else REPLICATES)
    chk5 = {"v16_5_replicates": m16, "v13": m13, "v13_topped_up_to_5": q160_stop_triggered,
            "stop": m16["accept_majority"], "ok": not m16["accept_majority"]}
    # ---- (6) N-TP-049, the old phrase, once under v1.6 (reported, not a stop)
    chk6 = {"single_v16": tp_cand["TP-049"], "expected": "REJECT", "as_expected": not acc(tp_cand["TP-049"]["verdict"]),
            "replicates_v16_if_differing": majority("TP-049", CAND) if "TP-049" in rep_items else None}
    # ---- (7) the Task 2 card rescue, once under v1.6
    chk7 = {Q297: {"before": c_cand[Q297]["before"], "after_v16": c_cand[Q297]["after"],
                   "now_refused": not acc(c_cand[Q297]["after"]["verdict"])}}
    info = {cid: {"phrase": ph, "v13": info_base[cid]["after"], "v16": c_cand[cid]["after"]} for cid, ph in TP049_CANDIDATES}

    gate = {k: c for k, c in (("2_Q161", chk2), ("3_non_creedal_idiom", chk3), ("4_Q277", chk4), ("5_Q160", chk5))}
    if chk5["stop"]:
        decision = "STOP (5): Q-160 accepts by majority of 5 under v1.6 — the rescue is not closed; v1.3 stays in force"
    elif not all(c["ok"] for c in gate.values()):
        decision = "FAIL: " + ", ".join(k for k, c in gate.items() if not c["ok"]) + " — v1.3 stays in force"
    else:
        decision = ("CHECKS (2)-(5) PASS; CHECK (1) NOT EVALUABLE (no tp-5) — v1.6 is NOT put in force; v1.3 stays in force "
                    "pending the author's ruling on TP-049")
    rep_table = {k: {"v1.3": majority(k, BASE, n_reps[k] if (k != Q160 or q160_stop_triggered) else REPLICATES),
                     "v1.6": majority(k, CAND)} for k in rep_items}
    out = {"rule": "standing replicate rule as amended by R6-20 (docs/gate6/WoP_SJN_Gate6_MeasurementRule.md)",
           "baseline": {"version": BASE, "tp": TP_BASE_RUN, "candidates": C_BASE_RUN,
                        "replicates_reused": "session7 (TP-049, TP-050) and session8 (Q-160, Q-161, Q-213) v1.3 replicates"},
           "candidate": {"version": CAND, "tp": TP_CAND_RUN, "candidates": C_CAND_RUN},
           "differs_means": "accept (ACCEPT or ACCEPT_WITH_CAVEAT) versus REJECT",
           "replicated_items": {k: n_reps[k] for k in sorted(rep_items)}, "replicate_table": rep_table,
           "checks": {"1_recall": chk1, **gate, "6_N-TP-049": chk6, "7_task2_card_rescues": chk7},
           "decision": decision,
           "tp_variants_sent": dict(Counter(v["variant"] for v in tp_cand.values())),
           "tp_refused_by_R6_18": sorted(k for k, v in tp_cand.items() if v.get("refused_by") == "R6-18"),
           "q290_v16": {k: tp_cand[k] for k in ("TP-059", "TP-060")},
           "tp049_in_chunk_candidates_info": info,
           "tp_single_diff_detail": {k: {"tp3": tp_base[k], "v16": tp_cand[k]} for k in tp_diff},
           "candidate_single_diff_detail": {k: {"v13": c_base[k]["after"], "v16": c_cand[k]["after"]} for k in c_diff},
           "replicate_rubrics": {k: v for k, v in reps.items()}}
    with open(os.path.join(HERE, "measure-v16.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in ("replicated_items", "replicate_table", "checks", "decision", "tp_variants_sent",
                                          "tp_refused_by_R6_18")}, ensure_ascii=False, indent=1))
    for k, v in out["q290_v16"].items():
        print(f"   {k}: {v['verdict']} / {v['reason_code']} ({v['variant']}) — {(v['reason'] or '')[:200]}")
    for cid, v in info.items():
        print(f"   {cid} \"{v['phrase']}\": v1.3 {v['v13']['verdict']}/{v['v13']['reason_code_final']}  "
              f"v1.6 {v['v16']['verdict']}/{v['v16']['reason_code_final']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
