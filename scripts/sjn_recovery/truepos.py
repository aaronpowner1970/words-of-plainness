"""tp-1 — the true-positive fixture (Gate 6 session 5, 2026-09-13): does the CURRENT verifier still accept what the
author has already ratified? The recall counterpart of the planted near-miss fixture (fa-3), which holds no true
positives and so could not measure the lower-floor rule's recall cost.

  python scripts/sjn_recovery/truepos.py build --run-id tp-1          # no model calls: writes recovery-runs/tp-1/fixture.json
  python scripts/sjn_recovery/truepos.py run   --run-id tp-1          # writes sonnet verifier jobs (exit 10 while pending)
  python scripts/sjn_recovery/api_executor.py --run-id tp-1 --workers 6 --max-cost-usd 3 --key-file <.env>
  python scripts/sjn_recovery/truepos.py run   --run-id tp-1          # ingests, finalises, writes tp-summary.json

Items. Every AUTHOR-RATIFIED phrase in the workbook that names its source: the "Citation Phrase Targets" sheet (the
released historical citation of each predicate family, phrase + text URL + locator; its branch read from "Inherited Public
Citations") and the "Case Study Phrase Targets" sheet (phrase + assertion URL + branch). An item enters the fixture only
when the ratified phrase stands verbatim (guards.check_phrase, the packet builder's own test) in a stored chunk of the
registry row its URL maps to (calibrate.equivalent_registry_ids); otherwise it is listed as excluded with the reason.
Every ratified phrase is a true positive by the author's ratification: a verdict below ACCEPT_WITH_CAVEAT is a recall miss.

Verifier: SONNET ONLY, prompt gate6-v1.2 (IDIOM_OR_FORMULA live). Under the lower-floor rule (2a) sonnet's floor is the
ceiling of every final verdict — opus can agree or be overruled downward, never raise a floor — so the sonnet verdict is
the upper bound of the routed outcome's recall. Finalised by agents.finalize with no second model.
Nothing writes to the workbook."""
import argparse
import json
import os
import sys
import time
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_pipeline.workbook import s  # noqa: E402
from sjn_recovery.config import RUNS_DIR, HAZARD_IDIOM_OR_FORMULA  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery.calibrate import equivalent_registry_ids  # noqa: E402
from sjn_recovery import store, guards, prompts  # noqa: E402

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
RECALL_STOP = 0.90


def _dir(run_id):
    d = os.path.join(RUNS_DIR, run_id)
    os.makedirs(d, exist_ok=True)
    return d


def ratified_phrases(reg):
    wb = reg.wb
    _, ipc, _ = wb.table("Inherited Public Citations", "Predicate ID")
    branch_of = {s(r["Predicate ID"]): s(r.get("Historical teaching branch")) for r in ipc}
    doc_of = {s(r["Predicate ID"]): s(r.get("Historical document")) for r in ipc}
    out = []
    _, cpt, _ = wb.table("Citation Phrase Targets", "Predicate ID")
    for r in cpt:
        pid = s(r["Predicate ID"])
        if not s(r.get("Quoted phrase")):
            continue
        out.append({"source_sheet": "Citation Phrase Targets", "ratified_row": r["__row"], "family_id": pid, "branch": branch_of.get(pid, ""),
                    "document": doc_of.get(pid, ""), "locator_ratified": s(r.get("Historical locator")), "url": s(r.get("Historical text URL")),
                    "phrase": s(r.get("Quoted phrase")), "review_state": s(r.get("Current review state"))})
    _, cst, _ = wb.table("Case Study Phrase Targets", "Queue ID")
    for r in cst:
        if not s(r.get("Quoted phrase")):
            continue
        out.append({"source_sheet": "Case Study Phrase Targets", "ratified_row": r["__row"], "queue_id": s(r.get("Queue ID")),
                    "family_id": s(r.get("Family ID")), "branch": s(r.get("Teaching branch")), "document": s(r.get("Document")),
                    "locator_ratified": s(r.get("Locator")), "url": s(r.get("Assertion Text URL")), "phrase": s(r.get("Quoted phrase")),
                    "review_state": s(r.get("Target Status"))})
    return out


def cmd_build(a):
    reg = Registry()
    preds = load_predicates(reg.wb)
    items, excluded, seen = [], [], set()
    for x in ratified_phrases(reg):
        key = (x["family_id"], x["phrase"].casefold())
        if key in seen:
            excluded.append(dict(x, reason="duplicate of an earlier ratified phrase for the same family")); continue
        seen.add(key)
        if x["family_id"] not in preds:
            excluded.append(dict(x, reason="family id not in Inherited 57")); continue
        rids = sorted(equivalent_registry_ids({"text_url": x["url"], "authority_url": ""}))
        rids = [r for r in rids if r in reg.by_id]
        if not rids:
            excluded.append(dict(x, reason=f"the URL maps to no ratified registry row with a corpus ({x['url'][:80]})")); continue
        hit = None
        for rid in rids:
            for c in store.load_chunks(rid):
                ok, _ = guards.check_phrase(x["phrase"], c["text"])
                if ok:
                    hit = (rid, c); break
            if hit:
                break
        if not hit:
            excluded.append(dict(x, rows_searched=rids, reason="the ratified phrase is not verbatim in any stored chunk of the mapped row(s)")); continue
        rid, c = hit
        row = reg.by_id[rid]
        items.append({"id": f"TP-{len(items) + 1:03d}", **x, "registry_id": rid, "registry_branch": row["branch"],
                      "authority_tier": row["authority_tier"], "locator": c["locator"], "chunk_hash": c["text_hash"],
                      "predicate": preds[x["family_id"]]["predicate"]})
    # cap (the instruction is 40–60 items): trim only the most represented branch, round-robin across its registry rows
    # from the end of each row's list, so every row it holds keeps as many items as it can
    while len(items) > a.max_items:
        top = Counter(i["registry_branch"] for i in items).most_common(1)[0][0]
        per_row = Counter(i["registry_id"] for i in items if i["registry_branch"] == top)
        rid = per_row.most_common(1)[0][0]
        victim = [i for i in items if i["registry_id"] == rid][-1]
        items.remove(victim)
        excluded.append(dict(victim, reason=f"trimmed to the {a.max_items}-item cap ({top} the most represented branch, {rid} its most represented row)"))
    for n, i in enumerate(items, 1):
        i["id"] = f"TP-{n:03d}"
    fixture = {"run_id": a.run_id, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "workbook": os.path.basename(reg.path),
               "kind": "TRUE_POSITIVES (author-ratified phrases, verbatim in the stored chunk of their mapped row)",
               "items": items, "excluded": excluded,
               "by_branch": dict(Counter(i["registry_branch"] for i in items)), "by_tier": dict(Counter(i["authority_tier"].split(" (")[0] for i in items)),
               "by_sheet": dict(Counter(i["source_sheet"] for i in items))}
    with open(os.path.join(_dir(a.run_id), "fixture.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=1)
    print(f"== tp fixture {a.run_id}: {len(items)} items, {len(excluded)} excluded; by branch {fixture['by_branch']}; by tier {fixture['by_tier']}; by sheet {fixture['by_sheet']}")
    for e in excluded:
        print(f"   excluded {e['source_sheet']} row {e['ratified_row']} {e['family_id']} {e['branch']}: {e['reason'][:110]}")
    return 0


def cmd_run(a):
    reg = Registry()
    preds = load_predicates(reg.wb)
    d = _dir(a.run_id)
    fixture = json.load(open(os.path.join(d, "fixture.json"), encoding="utf-8"))
    llm = LLM(a.run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, {}, os.path.join(d, "state"), "sonnet", ["sonnet"], log=print, run_coder=False)
    res_path = os.path.join(d, "tp-results.json")
    results = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {}
    pending = 0
    for it in fixture["items"]:
        chunk = next((c for c in store.load_chunks(it["registry_id"]) if c["locator"] == it["locator"]), None)
        if not chunk or chunk["text_hash"] != it["chunk_hash"]:
            results[it["id"]] = {"status": "CHUNK_CHANGED_SINCE_BUILD"}; continue
        cand = {"candidate_id": it["id"], "registry_id": it["registry_id"], "locator": it["locator"], "phrase": it["phrase"],
                "floor_claim": "FULL", "chunk_text": chunk["text"], "rationale": ""}
        cell = {"queue_id": it["id"], "family_id": it["family_id"], "branch": it["registry_branch"], "predicate": it["predicate"]}
        r = results.setdefault(it["id"], {"verdicts": {}})
        v = r["verdicts"]
        if (v.get("sonnet") or {}).get("status") != "DONE":
            v["sonnet"] = runner.verify(cell, cand, "sonnet")
        if v["sonnet"].get("status") == "PENDING":
            pending += 1; continue
        runner.finalize(v, "sonnet", None)
        r.update({"status": "DONE", "family_id": it["family_id"], "predicate": it["predicate"], "branch": it["registry_branch"],
                  "registry_id": it["registry_id"], "authority_tier": it["authority_tier"], "phrase": it["phrase"], "locator": it["locator"]})
    with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    if pending:
        print(f"== {a.run_id}: {pending} sonnet verifier call(s) pending ({prompts.prompt_version('verifier')})")
        return 10
    done = [(k, r) for k, r in results.items() if r.get("status") == "DONE"]
    acc = [(k, r) for k, r in done if r["verdicts"]["final"]["verdict"] in ACCEPTS]
    idiom = [(k, r) for k, r in done if HAZARD_IDIOM_OR_FORMULA in (r["verdicts"]["sonnet"].get("hazard_flags") or [])]
    idiom_acc = [(k, r) for k, r in idiom if r["verdicts"]["final"]["verdict"] in ACCEPTS]
    refused = [{"id": k, "branch": r["branch"], "family_id": r["family_id"], "predicate": r["predicate"], "registry_id": r["registry_id"],
                "locator": r["locator"], "phrase": r["phrase"], "floor": r["verdicts"]["sonnet"].get("floor"),
                "floor_model": r["verdicts"]["sonnet"].get("floor_model"), "floor_capped_by": r["verdicts"]["sonnet"].get("floor_capped_by"),
                "hazard_flags": r["verdicts"]["sonnet"].get("hazard_flags"), "asserted_outside_formula": r["verdicts"]["sonnet"].get("asserted_outside_formula"),
                "subject_is_required": r["verdicts"]["sonnet"].get("subject_is_required"), "speech_act_is_assertion": r["verdicts"]["sonnet"].get("speech_act_is_assertion"),
                "reason_code": r["verdicts"]["final"].get("reason_code_final"), "reason": r["verdicts"]["sonnet"].get("reason")}
               for k, r in done if r["verdicts"]["final"]["verdict"] not in ACCEPTS]
    by_branch = {}
    for k, r in done:
        b = by_branch.setdefault(r["branch"], {"items": 0, "accepted": 0})
        b["items"] += 1; b["accepted"] += 1 if r["verdicts"]["final"]["verdict"] in ACCEPTS else 0
    recall = len(acc) / len(done) if done else None
    summary = {"run_id": a.run_id, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "verifier": "sonnet only", "prompt_version": prompts.prompt_version("verifier"),
               "items": len(done), "accepted": len(acc), "recall": round(recall, 3) if recall is not None else None,
               "verdicts": dict(Counter(r["verdicts"]["final"]["verdict"] for _, r in done)),
               "floors": dict(Counter(r["verdicts"]["sonnet"].get("floor") for _, r in done)),
               "idiom_or_formula_raised": len(idiom), "idiom_or_formula_accepted": len(idiom_acc),
               "recall_on_idiom_cells": round(len(idiom_acc) / len(idiom), 3) if idiom else None,
               "idiom_items": [{"id": k, "predicate": r["predicate"], "phrase": r["phrase"], "verdict": r["verdicts"]["final"]["verdict"],
                                "asserted_outside_formula": r["verdicts"]["sonnet"].get("asserted_outside_formula"),
                                "floor_capped_by": r["verdicts"]["sonnet"].get("floor_capped_by")} for k, r in idiom],
               "by_branch": by_branch, "ratified_accepts_now_refused": refused,
               "stop_rule": f"recall below {RECALL_STOP} stops the session before Task 8",
               "stop": bool(recall is not None and recall < RECALL_STOP)}
    with open(os.path.join(d, "tp-summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("ratified_accepts_now_refused", "idiom_items")}, ensure_ascii=False, indent=1))
    for x in refused:
        print(f"   REFUSED {x['id']} {x['branch']} {x['predicate']} [{x['registry_id']} {x['locator'][:40]}] \"{x['phrase']}\" floor {x['floor']} "
              f"hazards {x['hazard_flags']} {x['reason_code']}: {(x['reason'] or '')[:220]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "run"):
        p = sub.add_parser(name)
        p.add_argument("--run-id", required=True)
        p.add_argument("--max-items", type=int, default=60)
    a = ap.parse_args()
    return cmd_build(a) if a.cmd == "build" else cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
