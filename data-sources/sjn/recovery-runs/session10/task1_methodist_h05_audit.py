"""Gate 6 session 10, Task 1 (R6-28): the Methodist RNR-H05 audit. NO model calls.

Question 1. Every citation on a BSR-MW-01 row (any article) attached to family RNR-H05, whatever its verdict: branch,
cell, phrase, locator, verdict, on a card, cell PUBLIC-CERTIFIED, would the cell lose its last citation without it.
Question 2. Every RNR-H05 citation, on any row, whose phrase lacks an assertion of eternal generation or eternal
sonship, where the stored rubric says so.

Search space, enumerated (a negative claim needs one):
  S1  the seven finished-branch recovery packets (recovery-packets/*.json): every citation-bearing list on every card
      (candidates, rejections, witness_only_candidates, caveat_slice, caveat_sample, exhaustion_sourced_candidates)
      and the packet-level dropped_at_build.
  S2  the finished-branch cell states (recovery-runs/live-1/cells/*.json: passes and verifications) and the raw
      live-1 audit log (live-1/calls.jsonl, every call's meta).
  S3  the canonical workbook (latest in data-sources/sjn/): Evidence-First Cell Queue, Case Study Phrase Targets,
      Inherited Public Citations, Citation Phrase Targets.
  S4  the committed public app data file src/_data/sjn/cells.json (the pipeline's emitted cells).
  S5  measurement and calibration rubrics: cal-1..cal-3 cells, every tp-* fixture run, and the session 7/8/9
      replicate files.
The live site is a sixth instrument, read in the browser and recorded in the artifact by hand (see LIVE_SITE).

  python data-sources/sjn/recovery-runs/session10/task1_methodist_h05_audit.py   # writes session10/task1-methodist-h05-audit.json
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from sjn_recovery.config import RUNS_DIR, PACKETS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_queue, load_case_targets  # noqa: E402
from sjn_pipeline.workbook import s  # noqa: E402

FAM, ROW = "RNR-H05", "BSR-MW-01"
ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
MW01_URL = "umc.org/en/content/articles-of-religion"
CARD_LISTS = ("candidates", "rejections", "witness_only_candidates", "caveat_slice", "caveat_sample",
              "exhaustion_sourced_candidates")
# Recorded by hand from the browser (session 10, 16 Sep 2026): fetch() of the five /seeking-jesus/ pages on the live
# origin, counting the Q-039 phrase and reading RNR-H05's rendered historical citation; cells.json requested directly.
LIVE_SITE = {
    "origin": "https://www.wordsofplainness.org (words-of-plainness.vercel.app redirects there; "
              "commandments.brotheraaron.org/seeking-jesus/ returns 404)",
    "pages": ["/seeking-jesus/", "/seeking-jesus/map/", "/seeking-jesus/code-it/", "/seeking-jesus/conversation/",
              "/seeking-jesus/self-check/"],
    "all_status": 200,
    "Q-039_string_on_any_page": 0,
    "q039_phrase_rendered_as_a_citation": False,
    "note_on_phrase_hits": "the index page contains 'the Father, the Son, and the Holy Ghost' twice, both in the "
                           "Latter-day Saint Godhead diagram text (aria-label and caption), not as a Methodist citation",
    "RNR-H05_rendered_historical_citation": {"branch": "Baptist", "document": "Baptist Faith and Message 2000",
                                             "locator": "II.B. God the Son", "phrase": "Christ is the eternal Son of God"},
    "cells_json_served": "404 at /_data/sjn/cells.json, /sjn/cells.json, /seeking-jesus/cells.json",
    "only_articles_of_religion_citation_rendered": "RNR-H42 'without body or parts' (Article I)",
}
# Question 2: phrases in a stored rubric's reason that say the passage does not assert eternal generation / sonship.
LACK_PATTERNS = [r"not (?:itself )?(?:assert|state|address|name|establish|predicate)", r"does not", r"only (?:names|lists|mentions)",
                 r"neighbou?ring", r"partial", r"list", r"generation", r"filial", r"begotten", r"sonship"]


def cells_json():
    d = json.load(open(os.path.join(ROOT, "src", "_data", "sjn", "cells.json"), encoding="utf-8"))
    return d["app_master_version"], [c for c in d["cells"] if c["family_id"] == FAM]


def s1_packets():
    """Every citation on every card of the seven packets for family H05, plus dropped_at_build."""
    rows, cards_h05, n_cards, n_cites = [], [], 0, 0
    for f in sorted(glob.glob(os.path.join(PACKETS_DIR, "*.json"))):
        p = json.load(open(f, encoding="utf-8"))
        for card in p["cards"]:
            n_cards += 1
            for lst in CARD_LISTS:
                for c in card.get(lst) or []:
                    if not isinstance(c, dict):
                        continue
                    n_cites += 1
                    if card["family_id"] == FAM or c.get("registry_id") == ROW and card["family_id"] == FAM:
                        rows.append({"packet": os.path.basename(f), "queue_id": card["queue_id"], "list": lst,
                                     "registry_id": c.get("registry_id"), "phrase": c.get("phrase")})
            if card["family_id"] == FAM:
                cards_h05.append(card["queue_id"])
        for c in p.get("dropped_at_build") or []:
            if isinstance(c, dict) and (c.get("family_id") == FAM or FAM in json.dumps(c)):
                rows.append({"packet": os.path.basename(f), "list": "dropped_at_build", "item": c})
    return {"packets": 7, "cards_read": n_cards, "card_citations_read": n_cites, "h05_cards": cards_h05, "h05_citations": rows}


def s2_live1():
    cells = sorted(glob.glob(os.path.join(RUNS_DIR, "live-1", "cells", "*.json")))
    h05 = []
    for f in cells:
        c = json.load(open(f, encoding="utf-8"))
        if c["family_id"] == FAM:
            h05.append(c["queue_id"])
    calls, h05_calls, mw01_h05_calls = 0, 0, 0
    for line in open(os.path.join(RUNS_DIR, "live-1", "calls.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        calls += 1
        m = json.dumps(r.get("meta") or {})
        if FAM in m:
            h05_calls += 1
            if ROW in m:
                mw01_h05_calls += 1
    return {"cells_read": len(cells), "h05_cells": h05, "calls_read": calls, "calls_with_h05_meta": h05_calls,
            "calls_with_h05_and_mw01_meta": mw01_h05_calls}


def s3_workbook(reg):
    queue = [r for r in load_queue(reg.wb) if r["family_id"] == FAM]
    targets = load_case_targets(reg.wb)
    _, ipc, _ = reg.wb.table("Inherited Public Citations", "Predicate ID")
    _, cpt, _ = reg.wb.table("Citation Phrase Targets", "Predicate ID")
    ipc_h05 = [{k: v for k, v in r.items() if v not in (None, "")} for r in ipc if s(r["Predicate ID"]) == FAM]
    cpt_h05 = [{k: v for k, v in r.items() if v not in (None, "")} for r in cpt if s(r["Predicate ID"]) == FAM]
    return {"workbook": os.path.basename(reg.path),
            "queue_h05": [dict(q, case_study_targets=targets.get(q["queue_id"], [])) for q in queue],
            "inherited_public_citation_h05": ipc_h05, "citation_phrase_targets_h05": cpt_h05}


def rubric_view(r):
    return {k: r.get(k) for k in ("verdict", "verdict_model", "floor", "floor_model", "floor_reason", "partial_asserts_predicate",
                                  "hazard_flags", "asserted_outside_formula", "reason_code_final", "reason_code", "reason",
                                  "prompt_version", "prompt_variant", "call_id", "source")}


def s5_rubrics():
    """Every stored H05 rubric: calibration cells, tp runs, replicate files."""
    out = []
    for run in ("cal-1", "cal-2", "cal-3"):
        for f in sorted(glob.glob(os.path.join(RUNS_DIR, run, "cells", "*.json"))):
            c = json.load(open(f, encoding="utf-8"))
            if c.get("family_id") != FAM:
                continue
            cands = {x["candidate_id"]: x for p in c["passes"].values() for x in p.get("candidates", [])}
            for cid, v in (c.get("verifications") or {}).items():
                x = cands.get(cid, {})
                for model, r in v.items():
                    if isinstance(r, dict) and "floor" in r:
                        out.append({"source": f"{run}/cells/{c['queue_id']}.json", "queue_id": c["queue_id"], "branch": c["branch"],
                                    "candidate_id": cid, "model": model, "registry_id": x.get("registry_id"),
                                    "locator": x.get("locator"), "phrase": x.get("phrase"),
                                    "final_verdict": (v.get("final") or {}).get("verdict"),
                                    **{k2: v2 for k2, v2 in rubric_view(r).items() if k2 != "source"}})
    for f in sorted(glob.glob(os.path.join(RUNS_DIR, "tp-*", "tp-results.json"))):
        run = os.path.basename(os.path.dirname(f))
        fx = {i["id"]: i for i in json.load(open(os.path.join(os.path.dirname(f), "fixture.json"), encoding="utf-8"))["items"]}
        for k, r in json.load(open(f, encoding="utf-8")).items():
            if r.get("status") != "DONE" or r.get("family_id") != FAM:
                continue
            out.append({"source": f"{run}/tp-results.json", "queue_id": fx[k].get("queue_id"), "branch": r["branch"], "candidate_id": k,
                        "model": "sonnet", "registry_id": r["registry_id"], "locator": r["locator"], "phrase": r["phrase"],
                        "final_verdict": r["verdicts"]["final"]["verdict"],
                        **{k2: v2 for k2, v2 in rubric_view(r["verdicts"]["sonnet"]).items() if k2 != "source"}})
    tp4 = {i["id"]: i for i in json.load(open(os.path.join(RUNS_DIR, "tp-4", "fixture.json"), encoding="utf-8"))["items"]}
    for f in (os.path.join(RUNS_DIR, "session7", "replicate-tp049-tp050.json"), os.path.join(RUNS_DIR, "session8", "replicates.json"),
              os.path.join(RUNS_DIR, "session9", "replicates.json")):
        for key, x in json.load(open(f, encoding="utf-8")).items():
            item = key.split("|")[0]
            if x.get("source") and not str(x["source"]).startswith(("s7-", "s8-", "s9-")):
                continue                     # reused from an earlier session's file (e.g. "session7 replicate"): already read there
            if item in tp4 and tp4[item]["family_id"] == FAM and x.get("status", "DONE") == "DONE":
                i = tp4[item]
                out.append({**rubric_view(x), "source": os.path.relpath(f, RUNS_DIR).replace("\\", "/") + "#" + key,
                            "queue_id": i.get("queue_id"), "branch": i["registry_branch"], "candidate_id": item, "model": "sonnet",
                            "registry_id": i["registry_id"], "locator": i["locator"], "phrase": i["phrase"],
                            "final_verdict": x.get("verdict"), "prompt_version": key.split("|")[1]})
    for r in out:
        # cal-1 / cal-2 store no final verdict: read the rubric's own (post-code) verdict there
        r["verdict_read"] = r.get("final_verdict") or r.get("verdict") or r.get("verdict_model")
    # ONE MODEL CALL IS ONE OBSERVATION. cal-2 and cal-3 re-serve cal-1's cached calls, tp-2 was seeded from tp-1, and
    # session 8's v1.3 replicates of TP-049 are session 7's, reused. Keep the first record of each call.
    seen, distinct = set(), []
    for r in out:
        if "#" in r["source"] and "replicate" in str(r.get("source_reused") or ""):
            continue
        key = r.get("call_id") or r["source"]
        if key in seen:
            r["duplicate_of_call"] = key
            continue
        seen.add(key)
        distinct.append(r)
    return distinct


def lacks_assertion(r):
    """The stored rubric says the phrase does not assert eternal generation / sonship: a non-FULL floor, a REJECT, or a
    reason naming the gap. Flagged for reading, never decided by pattern alone (the report reads each one)."""
    text = " ".join(str(r.get(k) or "") for k in ("floor_reason", "reason")).casefold()
    hits = [p for p in LACK_PATTERNS if re.search(p, text)]
    non_full = r.get("floor") not in ("FULL", None)
    rejected = r.get("verdict_read") not in ACCEPTS
    return {"non_full_floor": non_full, "rejected": rejected, "reason_patterns": hits, "flag": non_full or rejected}


def main():
    reg = Registry()
    s1, s2, s3 = s1_packets(), s2_live1(), s3_workbook(reg)
    app_version, s4 = cells_json()
    s5 = s5_rubrics()

    # ---- Question 1: every BSR-MW-01 citation attached to RNR-H05, in every space
    q1 = []
    for c in s1["h05_citations"]:
        if c.get("registry_id") == ROW:
            q1.append({"space": "S1 packets", **c})
    for q in s3["queue_h05"]:
        if q["branch"] != "Methodist / Wesleyan" and MW01_URL not in q["text_url"]:
            continue
        for t in q["case_study_targets"] or [{}]:
            if MW01_URL in (t.get("url") or q["text_url"]):
                others = [x for x in q["case_study_targets"] if x is not t]
                q1.append({"space": "S3 workbook (queue + Case Study Phrase Targets)", "branch": q["branch"], "cell": q["queue_id"],
                           "phrase": t.get("phrase"), "locator": f"{q['document']}, {q['locator']} (target locator: {t.get('locator')})",
                           "registry_row": ROW + " (by URL)", "verdict": f"author-ratified target status {t.get('status')}; "
                           f"reviewer status {q['reviewer_status']}", "rendered_state": q["rendered_state"],
                           "on_a_card": "workbook cell card (case study), not a Gate 6 recovery packet card",
                           "public_certified": q["disposition"].startswith("PUBLIC-CERTIFIED"), "disposition": q["disposition"],
                           "would_lose_last_citation": not others, "other_citations_on_cell": others})
    for c in s4:
        cs = c.get("case_study_target") or {}
        ev = c.get("evidence") or {}
        if MW01_URL in (cs.get("text_url") or "") or MW01_URL in (ev.get("text_url") or ""):
            q1.append({"space": f"S4 src/_data/sjn/cells.json ({app_version})", "branch": c["branch"], "cell": c["id"],
                       "phrase": cs.get("phrase"), "locator": f"{ev.get('document')}, {ev.get('locator')}",
                       "verdict": f"case_study_target status {cs.get('status')}; validation {(cs.get('validation') or {}).get('result')}; "
                                  f"reviewer_status {ev.get('reviewer_status')}",
                       "rendered_state": c["rendered_state"], "public_certified": c["disposition"] == "PUBLIC-CERTIFIED",
                       "disposition": c["disposition"], "would_lose_last_citation": True})
    mw01_rubrics = [r for r in s5 if r["registry_id"] == ROW]
    for r in mw01_rubrics:
        q1.append({"space": "S5 measurement/calibration rubric", **{k: r[k] for k in ("source", "queue_id", "branch", "candidate_id", "model",
                                                                                  "locator", "phrase", "verdict_read", "floor",
                                                                                  "prompt_version", "prompt_variant")},
                   "on_a_card": False, "public_certified": None})

    # ---- Question 2: H05 rubrics on any row that say the phrase lacks the assertion
    q2 = []
    for r in s5:
        lk = lacks_assertion(r)
        if lk["flag"]:
            q2.append({**{k: r[k] for k in ("source", "queue_id", "branch", "candidate_id", "model", "registry_id", "locator", "phrase",
                                             "verdict_read", "floor", "floor_reason", "reason", "partial_asserts_predicate",
                                             "prompt_version", "prompt_variant")}, "why_flagged": lk})

    # keyed on (phrase, branch): the same words on another branch's row are not that cell's citation
    public_phrases = {((t.get("phrase") or "").casefold(), q["branch"]): q["queue_id"] for q in s3["queue_h05"] for t in q["case_study_targets"]}
    for r in s3["inherited_public_citation_h05"]:
        public_phrases.setdefault((s(r.get("Historical quoted phrase (≤15 words)")).casefold(), s(r.get("Historical teaching branch"))),
                                  "IPC " + FAM)
    groups = {}
    for r in s5:
        g = groups.setdefault((r["registry_id"], r["locator"], r["phrase"]), {"registry_id": r["registry_id"], "locator": r["locator"],
                                                                              "phrase": r["phrase"], "rubrics": 0, "accepts": 0,
                                                                              "non_full_or_reject": 0, "sources": []})
        g["rubrics"] += 1
        g["accepts"] += r["verdict_read"] in ACCEPTS
        g["non_full_or_reject"] += lacks_assertion(r)["flag"]
        g["sources"].append(f"{r['source']}:{r['candidate_id']}:{r['model']}:{r['verdict_read']}/{r['floor']}")
        g["public_cell"] = public_phrases.get(((r["phrase"] or "").rstrip(".").casefold(), r["branch"]))
    q2_by_citation = sorted((g for g in groups.values() if g["non_full_or_reject"]), key=lambda g: (g["public_cell"] is None, g["registry_id"]))
    public_without_rubric = sorted(set(public_phrases.values()) - {g["public_cell"] for g in groups.values() if g["public_cell"]})
    packet_card_accepts = [c for c in q1 if c["space"] == "S1 packets"]
    certified_mw01 = [c for c in q1 if c["space"].startswith("S3") and c.get("public_certified")]
    out = {
        "rule": "R6-28: before any model calls, audit the finished branches for BSR-MW-01 citations on RNR-H05; stop if any is accepted on a card",
        "search_space": {"S1_recovery_packets": {k: v for k, v in s1.items() if k != "h05_citations"},
                         "S1_h05_citations": s1["h05_citations"], "S2_live1": s2,
                         "S3_workbook": s3["workbook"], "S4_cells_json_app_master_version": app_version,
                         "S4_h05_cells": [c["id"] for c in s4], "S5_h05_distinct_calls_read": len(s5),
                         "S5_dedup_rule": "one model call is one observation: records re-served from a cache or seed (same call_id) and replicates reused from an earlier session's file are counted once",
                         "S6_live_site": LIVE_SITE,
                         "why_the_packets_hold_no_h05": ("Gate 6 runs only OPEN cells (registry.open_cells: Rendered State begins "
                                                         "'NOT LOCATED'). All eight RNR-H05 cells (Q-033..Q-040) were already "
                                                         "rendered A and PUBLIC-CERTIFIED before Gate 6, so none entered live-1 or a packet.")},
        "workbook_h05_cells": s3["queue_h05"], "inherited_public_citation_h05": s3["inherited_public_citation_h05"],
        "citation_phrase_targets_h05": s3["citation_phrase_targets_h05"],
        "q1_mw01_h05_citations": q1,
        "q2_h05_rubrics_flagged": q2,
        "q2_by_citation": q2_by_citation, "q2_public_cells_with_no_stored_rubric_on_their_phrase": public_without_rubric,
        "counts": {"S1_packet_cards_h05": len(s1["h05_cards"]), "S1_packet_mw01_h05_citations": len(packet_card_accepts),
                   "S2_live1_h05_cells": len(s2["h05_cells"]), "S3_workbook_mw01_h05_cells_public_certified": len(certified_mw01),
                   "S5_mw01_h05_rubrics": len(mw01_rubrics),
                   "S5_mw01_h05_rubric_accepts": sum(1 for r in mw01_rubrics if r["verdict_read"] in ACCEPTS),
                   "q2_rubrics_flagged": len(q2), "q2_citations_flagged": len(q2_by_citation),
                   "q2_public_citations_flagged": sum(1 for g in q2_by_citation if g["public_cell"])},
        "stop_letter": {"any_mw01_h05_accept_on_a_finished_branch_recovery_packet_card": bool(packet_card_accepts)},
        "stop_purpose": {"a_finished_methodist_cell_certifies_mw01_article_I_or_II_for_h05": bool(certified_mw01),
                         "cells": [c["cell"] for c in certified_mw01]},
    }
    with open(os.path.join(HERE, "task1-methodist-h05-audit.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in ("counts", "stop_letter", "stop_purpose")}, ensure_ascii=False, indent=1))
    print("search space:", json.dumps({k: v for k, v in out["search_space"].items() if k not in ("S1_h05_citations", "S6_live_site")},
                                      ensure_ascii=False))
    print("\nQ1 — BSR-MW-01 citations on RNR-H05:")
    for c in q1:
        print("  ", json.dumps(c, ensure_ascii=False))
    print("\nQ2 — RNR-H05 rubrics flagged:")
    for r in q2:
        print(f"   {r['source']} {r['candidate_id']} {r['registry_id']} [{(r['locator'] or '')[:45]}] \"{r['phrase']}\" "
              f"{r['verdict_read']}/{r['floor']} ({r['prompt_variant'] or r['prompt_version']}) — {(r['floor_reason'] or '')[:260]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
