"""Gate 6 session 9, Task 2 (R6-18 step A): count the outside-formula rescues. NO model calls.

A "rescue" is an ACCEPT or ACCEPT_WITH_CAVEAT whose rubric carries asserted_outside_formula = Y.

Two instruments, reported side by side (independence by instrument, not by repetition):
  A. STORED RUBRICS — every JSON under recovery-runs/ and recovery-packets/ walked for a dict carrying the field
     (the rubric after code: caps, lower-floor rule, refinalisation).
  B. RAW VERIFIER REPLIES — every verifier call in every recovery-runs/*/calls.jsonl, parsed as the model returned it
     (before code).

Search space, enumerated: the seven finished branches (live-1 cell states + recovery-packets cards), tp-3, tp-4,
tp-4-v1.5, and the session 7 and session 8 measurement runs (s7-v13-control, s7-v14, s7-rep-*, s8-v15, s8-rep-*).
Any other run that turns up a Y (fa-3 planted near-misses) is listed as out of scope, not dropped silently.

For a finished-branch hit: the branch, the cell, the phrase, whether the candidate sits on the card, whether the card would
lose its LAST citation if the accept were refused, and the cell's workbook Public cell disposition.

  python data-sources/sjn/recovery-runs/session9/task2_rescues.py     # writes session9/task2-rescues.json
"""
import glob
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from sjn_recovery.config import RUNS_DIR, PACKETS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_queue  # noqa: E402
from sjn_recovery import prompts  # noqa: E402

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
IN_SCOPE_RUNS = ("live-1", "tp-3", "tp-4", "tp-4-v1.5", "s7-v13-control", "s7-v14", "s8-v15")
IN_SCOPE_PREFIXES = ("s7-rep-", "s8-rep-")
FINISHED = "live-1"
REPORT_THRESHOLD_CARD_ACCEPTS = 10


def in_scope(run_id):
    return run_id in IN_SCOPE_RUNS or run_id.startswith(IN_SCOPE_PREFIXES) or run_id in ("session7", "session8")


def walk(o, path, found):
    if isinstance(o, dict):
        if "asserted_outside_formula" in o:
            found.append((path, o))
        for k, v in o.items():
            walk(v, f"{path}/{k}", found)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f"{path}[{i}]", found)


def instrument_a():
    """Stored rubrics: (file, json path, rubric) for every Y, plus how many rubrics carry the field at all."""
    ys, carrying = [], Counter()
    files = glob.glob(os.path.join(RUNS_DIR, "**", "*.json"), recursive=True) + glob.glob(os.path.join(PACKETS_DIR, "*.json"))
    for f in sorted(files):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        found = []
        walk(d, "", found)
        rel = os.path.relpath(f, os.path.dirname(RUNS_DIR)).replace("\\", "/")
        for path, rub in found:
            carrying[rel] += 1
            if rub.get("asserted_outside_formula") == "Y":
                ys.append({"file": rel, "path": path, "verdict": rub.get("verdict"), "floor": rub.get("floor"),
                           "reason_code": rub.get("reason_code_final") or rub.get("reason_code"),
                           "prompt": rub.get("prompt_variant") or rub.get("prompt_version")})
    return ys, carrying


def instrument_b():
    """Raw verifier replies: every Y, per run, and the number of verifier replies read per run."""
    ys, read = [], Counter()
    for f in sorted(glob.glob(os.path.join(RUNS_DIR, "*", "calls.jsonl"))):
        run = os.path.basename(os.path.dirname(f))
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("role") != "verifier" or not r.get("output"):
                continue
            read[run] += 1
            o = prompts.parse_json(r["output"]) or {}
            if o.get("asserted_outside_formula") == "Y":
                ys.append({"run": run, "candidate_id": r["meta"].get("candidate_id"), "queue_id": r["meta"].get("queue_id"),
                           "model": r["model"], "prompt_version": r["prompt_version"], "call_id": r["call_id"],
                           "verdict_model": o.get("verdict"), "floor_model": o.get("floor"), "hazard_flags": o.get("hazard_flags"),
                           "floor_reason": o.get("floor_reason"), "reason": o.get("reason")})
    return ys, read


def packets_by_queue():
    out = {}
    for f in glob.glob(os.path.join(PACKETS_DIR, "*.json")):
        p = json.load(open(f, encoding="utf-8"))
        for card in p["cards"]:
            out[card["queue_id"]] = card
    return out


def card_citations(card):
    """The accepted citations a card carries (candidates; an English witness rides on its controlling entry)."""
    return [c["candidate_id"] for c in card.get("candidates", [])]


def finished_hit_detail(q, cid, cards, queue):
    cell = json.load(open(os.path.join(RUNS_DIR, FINISHED, "cells", f"{q}.json"), encoding="utf-8"))
    ver = cell["verifications"].get(cid, {})
    cand = None
    for p in cell["passes"].values():
        for c in p.get("candidates", []):
            if c["candidate_id"] == cid:
                cand = c
    card = cards.get(q)
    on_card = bool(card and cid in card_citations(card))
    others = [x for x in card_citations(card) if x != cid] if card else []
    final = ver.get("final") or {}
    # the rubric the final verdict RESTS ON: final.adjudicated_by names it (the final dict itself carries no rubric lines)
    resting = ver.get(final.get("adjudicated_by") or "", {}) if isinstance(ver.get(final.get("adjudicated_by") or ""), dict) else {}
    per_model = {m: {k: r.get(k) for k in ("verdict", "floor", "asserted_outside_formula", "hazard_flags", "reason_code_final",
                                             "prompt_version")}
                 for m, r in ver.items() if isinstance(r, dict) and "verdict" in r}
    qrow = next((r for r in queue if r["queue_id"] == q), {})
    return {"branch": cell["branch"], "queue_id": q, "family_id": cell["family_id"], "predicate": cell["predicate"],
            "candidate_id": cid, "registry_id": (cand or {}).get("registry_id"), "locator": (cand or {}).get("locator"),
            "phrase": (cand or {}).get("phrase"),
            "final_verdict": final.get("verdict"), "final_adjudicated_by": final.get("adjudicated_by"),
            "resting_rubric_asserted_outside_formula": resting.get("asserted_outside_formula"),
            "rubrics": per_model,
            "accepted_final": final.get("verdict") in ACCEPTS,
            "y_on_the_final_rubric": resting.get("asserted_outside_formula") == "Y",
            "on_card": on_card, "other_citations_on_card": others,
            "would_lose_last_citation": bool(on_card and not others),
            "public_cell_disposition": qrow.get("disposition"), "rendered_state": qrow.get("rendered_state"),
            "public_certified": (qrow.get("disposition") or "").startswith("PUBLIC-CERTIFIED")}


def main():
    reg = Registry()
    queue = load_queue(reg.wb)
    cards = packets_by_queue()
    a_ys, a_carrying = instrument_a()
    b_ys, b_read = instrument_b()

    finished = {}
    for y in b_ys:
        if y["run"] == FINISHED:
            finished[(y["queue_id"], y["candidate_id"])] = y
    for y in a_ys:
        if y["file"].startswith(f"recovery-runs/{FINISHED}/cells/"):
            q = os.path.basename(y["file"])[:-5]
            cid = y["path"].split("/")[2]
            finished.setdefault((q, cid), {"run": FINISHED, "queue_id": q, "candidate_id": cid, "found_by": "A only"})
    fin = [finished_hit_detail(q, cid, cards, queue) for (q, cid) in sorted(finished)]

    measured = [y for y in b_ys if y["run"] != FINISHED and in_scope(y["run"])]
    measured_accepts = [y for y in measured if y["verdict_model"] in ACCEPTS]
    out_of_scope = [y for y in b_ys if not in_scope(y["run"])]

    # stored accepts from the measurement results (post-code), to set beside the raw replies
    a_measured_accepts = [y for y in a_ys if y["verdict"] in ACCEPTS and not y["file"].startswith(f"recovery-runs/{FINISHED}/")
                          and not y["file"].startswith("recovery-packets/")]

    card_accepts = [x for x in fin if x["on_card"] and x["accepted_final"] and x["y_on_the_final_rubric"]]
    lose_last_pc = [x for x in fin if x["would_lose_last_citation"] and x["public_certified"]]
    # finished-branch rubrics that carry the field at all (the part of the space in which a rescue CAN be seen)
    live_raw_with_field = 0
    for line in open(os.path.join(RUNS_DIR, FINISHED, "calls.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r.get("role") == "verifier" and r.get("output") and "asserted_outside_formula" in (prompts.parse_json(r["output"]) or {}):
            live_raw_with_field += 1
    verifier_versions_live = Counter()
    for line in open(os.path.join(RUNS_DIR, FINISHED, "calls.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r.get("role") == "verifier":
            verifier_versions_live[r["prompt_version"]] += 1

    stop = len(card_accepts) > REPORT_THRESHOLD_CARD_ACCEPTS or bool(lose_last_pc)
    out = {
        "rule": "R6-18 step A: count ACCEPT / ACCEPT_WITH_CAVEAT with asserted_outside_formula = Y; no model calls",
        "search_space": {
            "instrument_A_stored_rubrics": {"files_with_the_field": dict(sorted(a_carrying.items()))},
            "instrument_B_raw_verifier_replies_read_per_run": dict(sorted(b_read.items())),
            "finished_branches_live1_verifier_calls_by_prompt_version": dict(verifier_versions_live),
            "finished_branches_live1_raw_replies_carrying_the_field": live_raw_with_field,
            "limit": ("the field exists from verifier gate6-v1.2 (session 4). A finished-branch rubric from gate6-v1.1 cannot show "
                      "a rescue: the flag and its cap did not exist, so an accepted formula there was accepted outright, not "
                      "rescued. Those accepts are outside this count by construction."),
        },
        "finished_branch_hits": fin,
        "finished_branch_card_accepts_relying_on_rescue": [x["candidate_id"] for x in card_accepts],
        "public_certified_cells_that_would_lose_last_citation": [x["queue_id"] for x in lose_last_pc],
        "measurement_run_hits_raw": measured,
        "measurement_run_accepts_raw": [{k: y[k] for k in ("run", "candidate_id", "prompt_version", "verdict_model", "floor_model")}
                                        for y in measured_accepts],
        "measurement_run_accepts_stored": a_measured_accepts,
        "out_of_scope_hits": out_of_scope,
        "stop_conditions": {"more_than_10_card_accepts": len(card_accepts) > REPORT_THRESHOLD_CARD_ACCEPTS,
                            "a_public_certified_cell_loses_its_last_citation": bool(lose_last_pc)},
        "stop": stop,
    }
    with open(os.path.join(HERE, "task2-rescues.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in ("finished_branch_card_accepts_relying_on_rescue",
                                          "public_certified_cells_that_would_lose_last_citation", "stop_conditions", "stop")},
                     ensure_ascii=False, indent=1))
    for x in fin:
        print(f"  {x['branch']} {x['queue_id']} {x['candidate_id']} \"{x['phrase']}\" final={x['final_verdict']} "
              f"Y_final={x['y_on_the_final_rubric']} on_card={x['on_card']} others={x['other_citations_on_card']} "
              f"lose_last={x['would_lose_last_citation']} disp={x['public_cell_disposition']!r}")
        for m, r in x["rubrics"].items():
            print(f"      {m}: {r}")
    print("  measurement accepts (raw):")
    for y in measured_accepts:
        print(f"      {y['run']} {y['candidate_id']} {y['prompt_version']} {y['verdict_model']} {y['floor_model']}")
    print("  out of scope:", [(y["run"], y["candidate_id"], y["verdict_model"]) for y in out_of_scope])
    print("  live-1 verifier calls by version:", dict(verifier_versions_live), "raw replies with field:", live_raw_with_field)
    return 0


if __name__ == "__main__":
    sys.exit(main())
