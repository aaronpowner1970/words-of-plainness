"""Gate 6 session 7, Task 4d: the four regression measurements verifier gate6-v1.4 must pass before it goes into force.

  python data-sources/sjn/recovery-runs/session7/measure_v14.py            # writes the pending verifier jobs (exit 10)
  python scripts/sjn_recovery/api_executor.py --run-id s7-v14 --workers 6 --max-cost-usd 2 --key-file <.env>
  python data-sources/sjn/recovery-runs/session7/measure_v14.py            # ingests and writes measure-v14.json

  (2) Q-161 RC-01-3, the one creedal IDIOM rejection at HEAD — it should now be re-opened by the creed carve-out
  (3) the 13 non-creedal IDIOM rejections at HEAD — none may flip to accept
  (4) both Q-277 Athanasian candidates, BSR-AN-03 and BSR-AN-04 — they must now AGREE

  (1) tp-4 is measured by truepos.py itself: `truepos run --run-id tp-4 --verifier-version gate6-v1.4`.

NOTHING here touches a stored cell state, a packet or the workbook. The candidates are read out of the committed packets
and verified afresh in a scratch state directory, so the seven finished branches are not mutated and nothing is released.
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from sjn_recovery.config import PACKETS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import prompts  # noqa: E402

RUN_ID = "s7-v14"
VERSION = "gate6-v1.4"
# The CONTROL. A flip on a NON-creedal rejection is only evidence against v1.4 if v1.3 does not flip it too: these are
# single sonnet calls, and the HEAD rubrics were single calls under earlier prompts. `--control` re-runs the same
# candidates under gate6-v1.3 in a separate run id, so the creed lines' effect is separated from run-to-run variance.
CONTROL_RUN_ID = "s7-v13-control"
CONTROL_VERSION = "gate6-v1.3"
ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
Q277 = ("Q-277-p1-BSR-AN-03-1", "Q-277-p1-BSR-AN-04-1")
CREEDAL_IDIOM = "Q-161-p1-BSR-RC-01-3"


class _PrimaryOnly:
    """The routing for a measurement: sonnet only, exactly as tp-* runs. Under the lower-floor rule the primary's
    floor is the ceiling of any routed outcome, so the sonnet verdict is the upper bound of what the branch would do."""
    def __init__(self, reg):
        self.reg = reg
        self.verifier_routing = "PRIMARY_ONLY"
        self.fallback_ids = set()

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return False

    def public(self, rid):
        return self.reg.public(rid)


def targets():
    """Every IDIOM_OR_FORMULA-flagged candidate at HEAD, plus the two Q-277 Athanasian candidates, read from the
    committed packets with the chunk text the verifier judged."""
    out, seen = [], set()
    for fn in sorted(os.listdir(PACKETS_DIR)):
        if not fn.endswith(".json"):
            continue
        pk = json.load(open(os.path.join(PACKETS_DIR, fn), encoding="utf-8"))
        for card in pk["cards"]:
            for where, lst in (("card", card["candidates"]), ("rejection", card["rejections"]),
                               ("witness_only", card["witness_only_candidates"])):
                for e in lst:
                    cid = e.get("candidate_id")
                    if not cid or cid in seen:
                        continue
                    rubs = e.get("verifier_rubrics") or {}
                    flags = {f for r in rubs.values() for f in (r.get("hazard_flags") or [])}
                    kinds = []
                    if "IDIOM_OR_FORMULA" in flags:
                        kinds.append("IDIOM_CREEDAL" if cid == CREEDAL_IDIOM else
                                     ("IDIOM_ON_CARD" if where == "card" else "IDIOM_NON_CREEDAL_REJECTION"))
                    if cid in Q277:
                        kinds.append("Q277_ATHANASIAN")
                    if not kinds:
                        continue
                    seen.add(cid)
                    out.append({"kinds": kinds, "branch": pk["branch"], "queue_id": card["queue_id"],
                                "family_id": card["family_id"], "predicate": card["predicate"], "where": where,
                                "candidate_id": cid, "registry_id": e["registry_id"], "locator": e["locator"],
                                "phrase": e["phrase"], "chunk_text": e.get("chunk_context"),
                                "floor_claim": e.get("locator_floor_claim") or e.get("floor_claim") or "FULL",
                                "before": {"verdict": (e.get("final_verdict") or {}).get("verdict"),
                                           "reason_code": (e.get("final_verdict") or {}).get("reason_code_final"),
                                           "floor": (e.get("final_verdict") or {}).get("floor_final"),
                                           "prompt_version": sorted({r.get("prompt_version") for r in rubs.values() if r.get("prompt_version")}),
                                           "hazard_flags": sorted(flags)}})
    return out


def main():
    control = "--control" in sys.argv
    run_id, version = (CONTROL_RUN_ID, CONTROL_VERSION) if control else (RUN_ID, VERSION)
    prompts.set_verifier_version(version)
    reg = Registry()
    preds = load_predicates(reg.wb)
    items = targets()
    llm = LLM(run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, _PrimaryOnly(reg), preds, {}, os.path.join(HERE, f"measure-state-{run_id}"), "sonnet", ["sonnet"],
                        log=print, run_coder=False)
    res_path = os.path.join(HERE, f"measure-results-{run_id}.json")
    results = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {}
    pending = 0
    for it in items:
        cand = {"candidate_id": it["candidate_id"], "registry_id": it["registry_id"], "locator": it["locator"],
                "phrase": it["phrase"], "floor_claim": it["floor_claim"], "chunk_text": it["chunk_text"], "rationale": ""}
        cell = {"queue_id": it["queue_id"], "family_id": it["family_id"], "branch": it["branch"], "predicate": it["predicate"]}
        r = results.setdefault(it["candidate_id"], {})
        if (r.get("rubric") or {}).get("status") != "DONE":
            r["rubric"] = runner.verify(cell, cand, "sonnet")
        if r["rubric"].get("status") == "PENDING":
            pending += 1
            continue
        r.update({k: it[k] for k in ("kinds", "branch", "queue_id", "predicate", "where", "registry_id", "locator", "phrase", "before")})
        r["after"] = {k: r["rubric"].get(k) for k in ("subject_is_required", "grammatical_subject", "speech_act_is_assertion",
                                                      "floor", "floor_model", "floor_capped_by", "floor_reason", "hazard_flags",
                                                      "asserted_outside_formula", "partial_asserts_predicate",
                                                      "spirit_name_in_phrase", "refused_by", "verdict", "reason_code_final",
                                                      "reason", "prompt_version")}
    with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    if pending:
        print(f"== {run_id}: {pending} sonnet verifier call(s) pending under {prompts.prompt_version('verifier')}")
        print(f"   run: python scripts/sjn_recovery/api_executor.py --run-id {run_id} --workers 6 --max-cost-usd 2 --key-file <.env>")
        return 10

    done = [r for r in results.values() if r.get("after")]
    by_kind = Counter(k for r in done for k in r["kinds"])
    creedal = [r for r in done if "IDIOM_CREEDAL" in r["kinds"]]
    non_creedal = [r for r in done if "IDIOM_NON_CREEDAL_REJECTION" in r["kinds"]]
    on_card = [r for r in done if "IDIOM_ON_CARD" in r["kinds"]]
    q277 = [r for r in done if "Q277_ATHANASIAN" in r["kinds"]]
    flips = [{"candidate_id": cid, **{k: r[k] for k in ("queue_id", "branch", "predicate", "phrase")},
              "before": r["before"]["verdict"], "after": r["after"]["verdict"], "reason": r["after"]["reason"]}
             for cid, r in results.items() if r.get("after")
             and "IDIOM_NON_CREEDAL_REJECTION" in r["kinds"] and r["after"]["verdict"] in ACCEPTS]
    q277_agree = len({r["after"]["verdict"] in ACCEPTS for r in q277}) == 1 if q277 else None
    summary = {
        "run_id": run_id, "verifier": f"sonnet only, {version}", "items": len(done), "by_kind": dict(by_kind),
        "check_2_Q161_creedal_idiom": [{"candidate_id": cid, "before": r["before"], "after": r["after"]}
                                       for cid, r in results.items() if r.get("after") and "IDIOM_CREEDAL" in r["kinds"]],
        "check_3_non_creedal_idiom_rejections": {
            "n": len(non_creedal), "still_rejected": sum(1 for r in non_creedal if r["after"]["verdict"] not in ACCEPTS),
            "new_false_accepts": flips, "ok": not flips},
        "check_4_Q277_athanasian": {
            "candidates": [{"candidate_id": cid, "registry_id": r["registry_id"], "phrase": r["phrase"],
                            "before": r["before"]["verdict"], "after": r["after"]["verdict"],
                            "rubric": r["after"]} for cid, r in results.items() if r.get("after") and "Q277_ATHANASIAN" in r["kinds"]],
            "agree": q277_agree, "ok": bool(q277_agree)},
        "idiom_candidate_already_on_a_card": [{"candidate_id": cid, "before": r["before"]["verdict"], "after": r["after"]["verdict"]}
                                              for cid, r in results.items() if r.get("after") and "IDIOM_ON_CARD" in r["kinds"]],
        "note": "sonnet only; no stored cell state, packet or workbook was touched",
    }
    summary["ok"] = summary["check_3_non_creedal_idiom_rejections"]["ok"] and summary["check_4_Q277_athanasian"]["ok"]
    with open(os.path.join(HERE, f"measure-{run_id}.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "check_4_Q277_athanasian"}, ensure_ascii=False, indent=1)[:2600])
    for c in summary["check_4_Q277_athanasian"]["candidates"]:
        print(f"-- Q-277 {c['registry_id']} {c['before']} -> {c['after']} ({c['rubric']['reason_code_final']}): "
              f"subj={c['rubric']['subject_is_required']} floor={c['rubric']['floor']} hz={c['rubric']['hazard_flags']} "
              f"spirit_in_phrase={c['rubric'].get('spirit_name_in_phrase')}")
        print(f"   {(c['rubric']['reason'] or '')[:240]}")
    print(f"== Q-277 candidates AGREE: {summary['check_4_Q277_athanasian']['agree']}; overall ok: {summary['ok']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
