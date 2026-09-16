"""Gate 6 session 8, Task 5: measure verifier gate6-v1.5 against gate6-v1.3 under the R6-13 replicate rule.

The standing rule (docs/gate6/WoP_SJN_Gate6_MeasurementRule.md):
  - each measured set runs ONCE per version;
  - an item whose verdict (accept vs reject) differs between baseline and candidate gets 3 replicates under EACH version;
  - the gate reads the replicate MAJORITY for those items. Q-160 is replicated under both versions regardless.

Baseline gate6-v1.3: tp-3 (the 60 true positives), s7-v13-control (the 16 IDIOM / Q-277 candidates), and session 7's
three v1.3 replicates of TP-049 and TP-050 (session7/replicate-tp049-tp050.json), which are reused, not re-run.

  1. python scripts/sjn_recovery/truepos.py run --run-id tp-4-v1.5 --fixture-from tp-4 --verifier-version gate6-v1.5
  2. python data-sources/sjn/recovery-runs/session8/measure_v15.py       # writes pending jobs, prints run ids (exit 10)
     python scripts/sjn_recovery/api_executor.py --run-id <id> --workers 6 --max-cost-usd <n> --key-file <.env>
     ... repeat 2 until it exits 0; it writes measure-v15.json with the five checks and the gate decision.

NOTHING here touches a stored cell state, a packet, PROMPT_VERSIONS or the workbook. The gate decision is written to the
artifact; putting a version in force is a separate, reviewed edit.
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

BASE, CAND = "gate6-v1.3", "gate6-v1.5"
TP_BASE_RUN, TP_CAND_RUN = "tp-3", "tp-4-v1.5"
C_BASE_RUN, C_CAND_RUN = "s7-v13-control", "s8-v15"
REPLICATES = 3
RECALL_FLOOR_ACCEPTED = 58            # 58/60 = 0.967 as tp-3 reports it; the floor is ">= 0.967"
ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
Q160 = "Q-160-p1-BSR-MA-01-1"
Q161 = s7m.CREEDAL_IDIOM
S7_REPLICATES = os.path.join(HERE, "..", "session7", "replicate-tp049-tp050.json")


def acc(v):
    return v in ACCEPTS


def _primary_only(reg):
    return s7m._PrimaryOnly(reg)


def run_candidates_single(reg, preds):
    """The 16 candidates, once, under v1.5 (run s8-v15)."""
    prompts.set_verifier_version(CAND)
    items = s7m.targets()
    llm = LLM(C_CAND_RUN, backend="batch", model="sonnet", log=lambda m: None)
    runner = CellRunner(llm, _primary_only(reg), preds, {}, os.path.join(HERE, f"state-{C_CAND_RUN}"), "sonnet", ["sonnet"],
                        log=lambda m: None, run_coder=False)
    path = os.path.join(HERE, f"measure-results-{C_CAND_RUN}.json")
    results = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    pending = 0
    for it in items:
        r = results.setdefault(it["candidate_id"], {})
        if (r.get("rubric") or {}).get("status") != "DONE":
            r["rubric"] = runner.verify(_cell(it), _cand(it), "sonnet")
        if r["rubric"].get("status") == "PENDING":
            pending += 1
            continue
        r.update({k: it[k] for k in ("kinds", "branch", "queue_id", "predicate", "family_id", "where", "registry_id", "locator", "phrase", "before")})
        r["after"] = {k: r["rubric"].get(k) for k in ("subject_is_required", "grammatical_subject", "speech_act_is_assertion",
                                                      "floor", "floor_model", "floor_capped_by", "floor_reason", "hazard_flags",
                                                      "asserted_outside_formula", "partial_asserts_predicate",
                                                      "spirit_name_in_phrase", "refused_by", "verdict", "reason_code_final",
                                                      "reason", "prompt_version", "prompt_variant")}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    return results, items, pending


def _cell(it):
    return {"queue_id": it["queue_id"], "family_id": it["family_id"], "branch": it["branch"], "predicate": it["predicate"]}


def _cand(it, suffix=""):
    return {"candidate_id": it["candidate_id"] + suffix, "registry_id": it["registry_id"], "locator": it["locator"],
            "phrase": it["phrase"], "floor_claim": it.get("floor_claim") or "FULL", "chunk_text": it["chunk_text"], "rationale": ""}


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


def tp_single(run_id):
    p = os.path.join(RUNS_DIR, run_id, "tp-results.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    if any(r.get("status") != "DONE" for r in d.values()) or len(d) != 60:
        return None
    return {k: {"verdict": r["verdicts"]["final"]["verdict"], "reason_code": r["verdicts"]["final"].get("reason_code_final"),
                "variant": r["verdicts"]["sonnet"].get("prompt_variant"), "floor": r["verdicts"]["sonnet"].get("floor"),
                "hazard_flags": r["verdicts"]["sonnet"].get("hazard_flags"), "reason": r["verdicts"]["sonnet"].get("reason")}
            for k, r in d.items()}


def main():
    reg = Registry()
    preds = load_predicates(reg.wb)
    tp_base, tp_cand = tp_single(TP_BASE_RUN), tp_single(TP_CAND_RUN)
    if tp_cand is None:
        print(f"== {TP_CAND_RUN} not complete: python scripts/sjn_recovery/truepos.py run --run-id {TP_CAND_RUN} "
              f"--fixture-from tp-4 --verifier-version {CAND}")
        return 10
    c_cand, c_items, c_pending = run_candidates_single(reg, preds)
    if c_pending:
        print(f"== {C_CAND_RUN}: {c_pending} pending under {CAND}")
        return 10
    c_base = json.load(open(os.path.join(HERE, "..", "session7", f"measure-results-{C_BASE_RUN}.json"), encoding="utf-8"))

    # ---- which items differ, and so get replicates
    tp_diff = sorted(k for k in tp_cand if acc(tp_cand[k]["verdict"]) != acc(tp_base[k]["verdict"]))
    c_diff = sorted(k for k in c_cand if acc(c_cand[k]["after"]["verdict"]) != acc(c_base[k]["after"]["verdict"]))
    rep_items = {}
    tps = tp_items()
    by_cid = {it["candidate_id"]: it for it in c_items}
    for k in tp_diff:
        rep_items[k] = tps[k]
    for k in sorted(set(c_diff) | {Q160}):
        rep_items[k] = by_cid[k]

    # ---- replicates: 3 per version per item; TP-049/TP-050 under v1.3 reuse session 7's
    s7rep = json.load(open(S7_REPLICATES, encoding="utf-8"))
    rep_path = os.path.join(HERE, "replicates.json")
    reps = json.load(open(rep_path, encoding="utf-8")) if os.path.exists(rep_path) else {}
    pending_runs = set()
    for version in (BASE, CAND):
        prompts.set_verifier_version(version)
        for n in range(1, REPLICATES + 1):
            run_id = f"s8-rep-{version.replace('gate6-', '')}-{n}"
            llm = runner = None
            for k, it in rep_items.items():
                key = f"{k}|{version}|{n}"
                if (reps.get(key) or {}).get("status") == "DONE":
                    continue
                s7k = f"{k}|{version}|{n}"
                if version == BASE and s7k in s7rep:
                    x = s7rep[s7k]
                    reps[key] = {"status": "DONE", "item": k, "version": version, "replicate": n, "source": "session7 replicate",
                                 "verdict": x["verdict"], "reason_code_final": x["reason_code_final"], "floor": x["floor"],
                                 "hazard_flags": x["hazard_flags"], "subject_is_required": x["subject_is_required"],
                                 "reason": x["reason"], "prompt_variant": version}
                    continue
                if runner is None:
                    llm = LLM(run_id, backend="batch", model="sonnet", log=lambda m: None)
                    runner = CellRunner(llm, _primary_only(reg), preds, {}, os.path.join(HERE, "rep-state", run_id), "sonnet",
                                        ["sonnet"], log=lambda m: None, run_coder=False)
                rub = runner.verify(_cell(it), _cand(it, f"-{run_id}"), "sonnet")
                if rub.get("status") == "PENDING":
                    pending_runs.add(run_id)
                    continue
                reps[key] = {"status": "DONE", "item": k, "version": version, "replicate": n, "source": run_id,
                             **{f: rub.get(f) for f in ("verdict", "reason_code_final", "floor", "floor_model", "floor_capped_by",
                                                        "hazard_flags", "subject_is_required", "speech_act_is_assertion",
                                                        "asserted_outside_formula", "spirit_name_in_phrase", "refused_by",
                                                        "reason", "prompt_variant")}}
    with open(rep_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reps, fh, ensure_ascii=False, indent=1)
    if pending_runs:
        print(f"== replicates pending in: {sorted(pending_runs)}  (items: {sorted(rep_items)})")
        return 10

    def majority(k, version):
        vs = [reps[f"{k}|{version}|{n}"]["verdict"] for n in range(1, REPLICATES + 1)]
        return {"accepts": sum(acc(v) for v in vs), "of": len(vs), "accept_majority": sum(acc(v) for v in vs) * 2 > len(vs), "verdicts": vs}

    def read(k, version, single):
        """What the gate reads for an item: the replicate majority where it was replicated, else the single run."""
        if k in rep_items:
            return majority(k, version)["accept_majority"]
        return acc(single)

    # ---- (1) tp-4 recall, majority-read
    tp_read = {k: read(k, CAND, tp_cand[k]["verdict"]) for k in tp_cand}
    accepted = sum(tp_read.values())
    chk1 = {"single_run_accepted": sum(acc(v["verdict"]) for v in tp_cand.values()), "items": 60,
            "baseline_tp3_accepted": sum(acc(v["verdict"]) for v in tp_base.values()),
            "differing_items": tp_diff, "majority_read_accepted": accepted, "majority_read_recall": round(accepted / 60, 3),
            "refused_majority_read": sorted(k for k, v in tp_read.items() if not v),
            "ok": accepted >= RECALL_FLOOR_ACCEPTED}
    # ---- (2) Q-161
    q161 = read(Q161, CAND, c_cand[Q161]["after"]["verdict"])
    chk2 = {"single_v15": c_cand[Q161]["after"]["verdict"], "single_v13_control": c_base[Q161]["after"]["verdict"],
            "replicated": Q161 in rep_items, "accept_majority_v15": q161, "ok": q161}
    # ---- (3) the 12 non-creedal IDIOM rejections
    nc = sorted(k for k, r in c_cand.items() if "IDIOM_NON_CREEDAL_REJECTION" in r["kinds"])
    attributable = []
    for k in nc:
        a15 = read(k, CAND, c_cand[k]["after"]["verdict"])
        a13 = read(k, BASE, c_base[k]["after"]["verdict"])
        if a15 and not a13:
            attributable.append(k)
    chk3 = {"n": len(nc), "accept_under_v15_read": sorted(k for k in nc if read(k, CAND, c_cand[k]["after"]["verdict"])),
            "accept_under_v13_read": sorted(k for k in nc if read(k, BASE, c_base[k]["after"]["verdict"])),
            "flips_attributable_to_v15": attributable, "ok": not attributable}
    # ---- (4) Q-277
    q277 = {k: read(k, CAND, c_cand[k]["after"]["verdict"]) for k in s7m.Q277}
    chk4 = {"accept_read_v15": q277, "agree": len(set(q277.values())) == 1, "ok": len(set(q277.values())) == 1}
    # ---- (5) Q-160
    m15, m13 = majority(Q160, CAND), majority(Q160, BASE)
    implicated = m15["accept_majority"] and not m13["accept_majority"]
    chk5 = {"v15": m15, "v13": m13, "creed_carve_out_implicated": implicated, "ok": not implicated}

    checks = {"1_tp4_recall": chk1, "2_Q161": chk2, "3_non_creedal_idiom": chk3, "4_Q277": chk4, "5_Q160": chk5}
    if implicated:
        decision = "STOP: Q-160 accept-majority under v1.5 and reject-majority under v1.3 — the creed carve-out is implicated; v1.3 stays in force"
    elif all(c["ok"] for c in checks.values()):
        decision = "ALL FIVE PASS: gate6-v1.5 may be made the version in force"
    else:
        decision = "FAIL: " + ", ".join(k for k, c in checks.items() if not c["ok"]) + " — v1.3 stays in force"
    q290 = {k: tp_cand[k] for k in ("TP-059", "TP-060")}
    rep_table = {k: {"v1.3": majority(k, BASE), "v1.5": majority(k, CAND)} for k in rep_items}
    variants = Counter(v["variant"] for v in tp_cand.values())
    out = {"rule": "R6-13 replicate measurement rule (docs/gate6/WoP_SJN_Gate6_MeasurementRule.md)",
           "baseline": {"version": BASE, "tp": TP_BASE_RUN, "candidates": C_BASE_RUN, "tp049_tp050_v13_replicates": "session7"},
           "candidate": {"version": CAND, "tp": TP_CAND_RUN, "candidates": C_CAND_RUN},
           "differs_means": "accept (ACCEPT or ACCEPT_WITH_CAVEAT) versus REJECT",
           "replicated_items": sorted(rep_items), "replicate_table": rep_table, "checks": checks, "decision": decision,
           "tp_variants_sent": dict(variants),
           "candidate_variants_sent": dict(Counter(r["after"]["prompt_variant"] for r in c_cand.values())),
           "q290_refusals_v15": q290,
           "tp_single_diff_detail": {k: {"tp3": tp_base[k], "v15": tp_cand[k]} for k in tp_diff},
           "candidate_single_diff_detail": {k: {"v13": c_base[k]["after"], "v15": c_cand[k]["after"]} for k in c_diff},
           "replicate_rubrics": reps}
    with open(os.path.join(HERE, "measure-v15.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("replicate_rubrics", "tp_single_diff_detail",
                                                              "candidate_single_diff_detail", "q290_refusals_v15")},
                     ensure_ascii=False, indent=1))
    for k, v in q290.items():
        print(f"   {k}: {v['verdict']} / {v['reason_code']} ({v['variant']}) — {(v['reason'] or '')[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
