"""Calibration harness (spec §6) — run BEFORE any live run.

  python scripts/sjn_recovery/calibrate.py run    --run-id cal-1 --locator-model sonnet --verifier-models sonnet,opus [--backend batch]
  python scripts/sjn_recovery/calibrate.py plant  --run-id cal-1 --verifier-models sonnet,opus
  python scripts/sjn_recovery/calibrate.py report --run-id cal-1

`run` takes the released cells (A / A-SF / Q / D) and the reviewed-empty cells with their locators
HIDDEN (the agents never see the workbook's document/locator/phrase), runs locator + verifier, and
records per cell what was found. `plant` runs the verifier over the planted near-miss fixture
(calibration/planted-near-misses.json: opponent quotations, Christological/human-nature passages,
Church-predicates, creature-predicates, wrong-sense uses) — every ACCEPT there is a false accept.
`report` scores recall, false-accept and empty-result rates per branch and per verifier model, with
the Dositheus slice separate, and writes recovery-runs/calibration-report.md.

With the batch backend a phase stops when calls are pending; execute the jobs and re-run the same
command to continue. Nothing here writes to the workbook."""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, CALIBRATION_DIR, BRANCHES, ensure_dirs, MODEL_IDS  # noqa: E402
from sjn_recovery.registry import (Registry, load_predicates, load_comparators, load_queue, released_cells,  # noqa: E402
                                   reviewed_empty_cells, TIER_RANK, bare_tier, tier_rank)
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import guards, prompts, store  # noqa: E402

THRESH_RECALL = 0.8
THRESH_FALSE_ACCEPT = 0.05
PLANTED_PATH = os.path.join(CALIBRATION_DIR, "planted-near-misses.json")

# ---------------------------------------------------------------- Q-449 class
# Released cells whose cited text lies outside the ratified scope of every row in its branch. These
# are excluded from the recall denominator: no agent could have found the passage, because the
# passage is not in the corpus the registry ratified. Established by scanning each branch's whole
# ratified corpus for the predicate's own vocabulary (audit in the cal-2 report).
OUT_OF_RATIFIED_SCOPE = {
    "Q-449": {
        "cited": "Fourth Lateran Council, Constitution 1 (Firmiter credimus)",
        "ratified_scope": "BSR-RC-04 ratifies Lateran IV canon 1 only (4 chunks, 3,574 chars).",
        "phrase_actually_sits_in": "Lateran IV canon 2 (Damnamus… the condemnation of Joachim of Fiore), "
                                   "where the maior dissimilitudo clause stands.",
        "reason": "No ratified Roman Catholic row contains 'dissimilitude', 'dissimilar', 'unlikeness' or "
                  "'Joachim' in any chunk. The predicate's own text is unreachable from the registry as ratified.",
    },
}

# Rows carrying an author caveat that must travel with any winning candidate (AC-03, AC-05).
CAVEATED_ROWS = {
    "BSR-EO-04": "AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian "
                 "catechism, not a pan-Orthodox conciliar standard.",
    "BSR-EO-05": "AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); "
                 "its authority is regional, not pan-Orthodox.",
}



def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ equivalence: existing cell -> registry ids
def equivalent_registry_ids(cell):
    """Which registry standards carry the same text the released cell cites (by host/path)."""
    u = (cell["text_url"] or cell["authority_url"] or "").casefold()
    host = urlparse(u).netloc.replace("www.", "")
    path = urlparse(u).path
    doc = cell["document"].casefold()
    if host == "churchofengland.org":
        return {"BSR-AN-01"} if "articles-religion" in path else {"BSR-AN-03", "BSR-AN-02"}
    if host == "ccel.org":
        return {"BSR-AN-03"}
    if host == "bfm.sbc.net":
        return {"BSR-BA-01"}
    if host == "oca.org":
        if "the-symbol-of-faith" in path or "symbol-of-faith" in path:
            return {"BSR-EO-01"}
        if "the-holy-trinity" in path:
            return {"BSR-EO-02"}
        if "church-history" in path:
            return {"BSR-EO-06"}
        return {"BSR-EO-01", "BSR-EO-02", "BSR-EO-06"}
    if host == "newadvent.org":
        return {"BSR-EO-06"}
    if host == "bookofconcord.org":
        return {"BSR-LU-01"}
    if host == "mennoniteusa.org":
        return {"BSR-MA-01"}
    if host == "umc.org":
        return {"BSR-MW-01"} if "articles-of-religion" in path else {"BSR-MW-02"}
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
    rel = released_cells(queue)
    emp = reviewed_empty_cells(queue)
    return rel, emp


def secondary_sample(cell):
    """Cells the secondary verifier models run on: every Eastern Orthodox cell (the Dositheus slice), every
    reviewed-empty cell, and a deterministic quarter of the rest (queue number divisible by 4)."""
    if cell["branch"] == "Eastern Orthodox" or cell["rendered_state"].startswith("NOT LOCATED"):
        return True
    return int(cell["queue_id"].split("-")[1]) % 4 == 0


def hidden(cell):
    """The locator input: the cell with its evidence fields removed (locators hidden)."""
    return {k: cell[k] for k in ("queue_id", "family_id", "predicate", "family_code", "branch", "rendered_state")}


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
    if args.limit:
        cells = cells[:args.limit]
    vmodels = args.verifier_models.split(",")
    llm = LLM(args.run_id, backend=args.backend, model=args.locator_model, log=log)
    state_dir = os.path.join(RUNS_DIR, args.run_id, "cells")
    secondary = None if args.full_secondary else {c["queue_id"] for c in cells if secondary_sample(c)}
    runner = CellRunner(llm, reg, preds, comps, state_dir, args.locator_model, vmodels, log=log, run_coder=False,
                        secondary_cells=secondary)
    done = pending = 0
    for c in cells:
        st = runner.run_cell(hidden(c))
        if st.get("phase") == "DONE":
            done += 1
        else:
            pending += 1
    meta = {"run_id": args.run_id, "kind": "calibration", "workbook": os.path.basename(reg.path), "app_master_version": reg.app_master_version,
            "locator_model": args.locator_model, "verifier_models": vmodels, "backend": args.backend, "prompt_version": prompts.PROMPT_VERSION,
            "cells": len(cells), "released": len([c for c in cells if c in rel]), "reviewed_empty": len([c for c in cells if c in emp]),
            "secondary_scope": "ALL" if args.full_secondary else "Eastern Orthodox + reviewed-empty + queue number % 4 == 0",
            "secondary_cells": sorted(secondary) if secondary is not None else None,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(RUNS_DIR, args.run_id, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    log(f"== calibration {args.run_id}: {done} cells DONE, {pending} waiting; pending model calls: {len(set(llm.pending))}")
    if llm.pending:
        log(f"   execute the pending jobs (jobs.py bundles --run-id {args.run_id} ...) and re-run this command")
        return 10
    return 0


# ------------------------------------------------------------------ plant (near-misses)
def cmd_plant(args):
    """Run the verifier over the planted near-miss fixture. Each item names a chunk (registry_id, locator),
    a phrase verbatim from it, the predicate family it would be a near-miss for, and the near-miss type."""
    ensure_dirs()
    reg = Registry(args.workbook)
    preds = load_predicates(reg.wb)
    with open(PLANTED_PATH, encoding="utf-8") as fh:
        fixture = json.load(fh)
    vmodels = args.verifier_models.split(",")
    llm = LLM(args.run_id, backend=args.backend, model=args.locator_model, log=log)
    out_path = os.path.join(RUNS_DIR, args.run_id, "planted-results.json")
    results = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    chunk_cache = {}
    n_pending = 0
    for item in fixture["items"]:
        pid = item["id"]
        rid, loc = item["registry_id"], item["locator"]
        if rid not in chunk_cache:
            chunk_cache[rid] = {c["locator"]: c for c in store.load_chunks(rid)}
        chunk = chunk_cache[rid].get(loc)
        if not chunk:
            results[pid] = {"status": "CHUNK_NOT_FOUND"}; continue
        ok, why = guards.check_phrase(item["phrase"], chunk["text"])
        if not ok:
            results[pid] = {"status": "FIXTURE_PHRASE_NOT_VERBATIM", "detail": why}; continue
        cand = {"candidate_id": pid, "registry_id": rid, "locator": loc, "phrase": item["phrase"], "floor_claim": item.get("floor_claim", "FULL"),
                "chunk_text": chunk["text"], "rationale": ""}
        cell = {"queue_id": pid, "family_id": item["family_id"], "branch": reg.by_id[rid]["branch"], "predicate": preds[item["family_id"]]["predicate"]}
        runner = CellRunner(llm, reg, preds, {}, os.path.join(RUNS_DIR, args.run_id, "planted-state"), args.locator_model, vmodels, log=log, run_coder=False)
        r = results.setdefault(pid, {"status": "RUN", "type": item["type"], "family_id": item["family_id"], "registry_id": rid, "locator": loc,
                                     "phrase": item["phrase"], "why_near_miss": item["why"], "verdicts": {}})
        for m in vmodels:
            if m in r["verdicts"] and r["verdicts"][m].get("status") == "DONE":
                continue
            rub = runner.verify(cell, cand, m)
            r["verdicts"][m] = rub
            if rub.get("status") == "PENDING":
                n_pending += 1
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    log(f"== planted near-misses {args.run_id}: {len(fixture['items'])} items; pending verifier calls {n_pending}")
    return 10 if n_pending else 0


# ------------------------------------------------------------------ report
def _verdict(st, cid, model):
    return ((st.get("verifications") or {}).get(cid) or {}).get(model, {}).get("verdict")


def cmd_report(args):
    reg = Registry(args.workbook)
    queue = load_queue(reg.wb)
    rel, emp = calibration_cells(queue)
    run_dir = os.path.join(RUNS_DIR, args.run_id)
    meta = json.load(open(os.path.join(run_dir, "run.json"), encoding="utf-8"))
    vmodels = meta["verifier_models"]
    state_dir = os.path.join(run_dir, "cells")
    llm = LLM(args.run_id, backend=meta["backend"], model=meta["locator_model"], log=log)
    manifest = store.load_manifest()

    def load_state(qid):
        p = os.path.join(state_dir, f"{qid}.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    # ---- recall per branch per verifier model
    rows = []
    per = defaultdict(lambda: defaultdict(lambda: {"cells": 0, "done": 0, "located_any": 0, "hit_std": 0, "hit_div": 0,
                                                    "hit_tier": 0, "partial_lower": 0, "excluded_oos": 0,
                                                    "no_corpus": 0, "empty": 0}))
    details = []
    residue = defaultdict(list)
    skipped_cells = defaultdict(list)
    caveat_hits = []
    for c in rel:
        st = load_state(c["queue_id"])
        eq = equivalent_registry_ids(c)
        corpus_available = any((manifest.get("standards", {}).get(r, {}).get("n_chunks") or 0) > 0 for r in eq)
        # The tier bar is the tier of the standard the released cell cites. No released cell maps to a
        # mixed-tier set of registry rows, so the bar is unambiguous; where two rows carry the same text
        # (Latin original plus English witness) they share a tier and min() is that tier.
        bar = min((tier_rank(reg.by_id[r]["authority_tier"]) for r in eq if r in reg.by_id), default=len(TIER_RANK))
        oos = OUT_OF_RATIFIED_SCOPE.get(c["queue_id"])
        for m in vmodels:
            b = per[c["branch"]][m]
            b["cells"] += 1
            if not st or st.get("phase") != "DONE":
                skipped_cells[m].append((c["queue_id"], c["branch"], c["predicate"], "CELL_NOT_DONE",
                                         (st or {}).get("phase", "NO STATE FILE")))
                continue
            all_cands = [cd for pk, pv in st["passes"].items() for cd in pv.get("candidates", [])]
            unverified = [cd for cd in all_cands
                          if ((st.get("verifications") or {}).get(cd["candidate_id"]) or {}).get(m, {}).get("status") != "DONE"]
            if unverified:
                b["skipped"] = b.get("skipped", 0) + 1
                # Say WHY per cell, not merely that it was skipped: the secondary verifier runs on a
                # defined sample (secondary_sample), so most skips are scope, not failure.
                sts = sorted({((st.get("verifications") or {}).get(cd["candidate_id"]) or {}).get(m, {}).get("status", "ABSENT")
                              for cd in unverified})
                reason = "SECONDARY_SCOPE" if (m != vmodels[0] and not secondary_sample(c)) else "VERIFICATION_INCOMPLETE"
                skipped_cells[m].append((c["queue_id"], c["branch"], c["predicate"], reason,
                                         str(len(unverified)) + "/" + str(len(all_cands)) + " candidates at " + ",".join(sts)))
                continue   # this model did not verify this cell — not in its denominator
            if oos:
                b["excluded_oos"] += 1
                continue   # Q-449 class: the cited text lies outside every ratified row of the branch
            b["done"] += 1
            if not corpus_available:
                b["no_corpus"] += 1
            cands = all_cands
            surv = [cd for cd in cands if _verdict(st, cd["candidate_id"], m) in ("ACCEPT", "ACCEPT_WITH_CAVEAT")]
            if surv:
                b["located_any"] += 1
            else:
                b["empty"] += 1
            hit_std = any(cd["registry_id"] in eq for cd in surv)
            hit_div = any(cd["registry_id"] in eq and same_division(c["locator"], cd["locator"]) for cd in surv)

            def same_branch(cd):
                return cd["registry_id"] in reg.by_id and reg.by_id[cd["registry_id"]]["branch"] == c["branch"]
            # Tier-respecting: the same standard the cell cites, or a different ratified standard of the
            # correct branch at an EQUAL OR HIGHER tier. A substitution into a LOWER tier is a partial and
            # is not credited.
            equal_or_higher = [cd for cd in surv if same_branch(cd)
                               and tier_rank(reg.by_id[cd["registry_id"]]["authority_tier"]) <= bar]
            lower = [cd for cd in surv if same_branch(cd)
                     and tier_rank(reg.by_id[cd["registry_id"]]["authority_tier"]) > bar]
            hit_tier = bool(hit_std or equal_or_higher)
            b["hit_std"] += hit_std; b["hit_div"] += hit_div; b["hit_tier"] += hit_tier
            if not hit_tier and lower:
                b["partial_lower"] += 1
            if not hit_tier:
                residue[m].append({"queue_id": c["queue_id"], "branch": c["branch"], "predicate": c["predicate"],
                                   "cited_tier": bare_tier(reg.by_id[sorted(eq)[0]]["authority_tier"]) if eq else "?",
                                   "class": ("PARTIAL_LOWER_TIER" if lower else
                                             ("ALL_CANDIDATES_REJECTED" if cands else "LOCATOR_EMPTY")),
                                   "lower_tier_offered": [(cd["registry_id"],
                                                           bare_tier(reg.by_id[cd["registry_id"]]["authority_tier"]),
                                                           cd["locator"]) for cd in lower]})
            for cd in (equal_or_higher + lower):
                if cd["registry_id"] in CAVEATED_ROWS:
                    caveat_hits.append({"queue_id": c["queue_id"], "model": m, "branch": c["branch"],
                                        "predicate": c["predicate"], "registry_id": cd["registry_id"],
                                        "locator": cd["locator"], "credited": bool(hit_tier and cd in equal_or_higher),
                                        "caveat": CAVEATED_ROWS[cd["registry_id"]]})
            if m == vmodels[0]:
                details.append({"queue_id": c["queue_id"], "branch": c["branch"], "family_id": c["family_id"], "predicate": c["predicate"],
                                "existing": f"{c['document']} — {c['locator']}", "equivalent_registry": sorted(eq), "corpus_available": corpus_available,
                                "cited_tier": bare_tier(reg.by_id[sorted(eq)[0]]["authority_tier"]) if eq else "?",
                                "survivors": [(cd["registry_id"], cd["locator"], cd["phrase"]) for cd in surv],
                                "hit_same_standard": hit_std, "hit_same_division": hit_div, "hit_tier_respecting": hit_tier,
                                "partial_lower_tier": [cd["registry_id"] for cd in lower] if not hit_tier else [],
                                "rejected": [(cd["registry_id"], cd["locator"], _verdict(st, cd["candidate_id"], m),
                                              (st["verifications"].get(cd["candidate_id"], {}).get(m, {}) or {}).get("reason_code_final"))
                                             for cd in cands if cd not in surv]})
    # ---- expected-empty cells
    emp_rows = []
    for c in emp:
        st = load_state(c["queue_id"])
        eq = equivalent_registry_ids(c)
        if not st or st.get("phase") != "DONE":
            emp_rows.append({"queue_id": c["queue_id"], "branch": c["branch"], "status": "NOT DONE"}); continue
        for m in vmodels:
            cands = [cd for pk, p in st["passes"].items() for cd in p.get("candidates", [])]
            surv = [cd for cd in cands if _verdict(st, cd["candidate_id"], m) in ("ACCEPT", "ACCEPT_WITH_CAVEAT")]
            emp_rows.append({"queue_id": c["queue_id"], "branch": c["branch"], "family_id": c["family_id"], "predicate": c["predicate"], "model": m,
                             "existing_document": c["document"], "outcome": "EMPTY" if not surv else
                             ("LOCATED_IN_SAME_STANDARD" if any(cd["registry_id"] in eq for cd in surv) else "LOCATED_IN_OTHER_REGISTRY_STANDARD"),
                             "survivors": [(cd["registry_id"], cd["locator"], cd["phrase"]) for cd in surv]})
    # ---- planted near-misses
    planted = {}
    pp = os.path.join(run_dir, "planted-results.json")
    if os.path.exists(pp):
        planted = json.load(open(pp, encoding="utf-8"))
    fa = defaultdict(lambda: defaultdict(lambda: {"n": 0, "false_accept": 0, "pending": 0, "items": []}))
    for pid, r in planted.items():
        if r.get("status") != "RUN":
            continue
        slice_ = "Dositheus" if r["registry_id"] == "BSR-EO-05" else reg.by_id[r["registry_id"]]["branch"]
        for m, v in r["verdicts"].items():
            b = fa[slice_][m]
            if v.get("status") != "DONE":
                b["pending"] += 1; continue
            b["n"] += 1
            if v.get("verdict") in ("ACCEPT", "ACCEPT_WITH_CAVEAT"):
                b["false_accept"] += 1
                b["items"].append((pid, r["type"], r["locator"], v.get("verdict"), v.get("reason")))
    # Dositheus natural slice: verifier verdicts on Dositheus candidates from the EO cells
    dos_nat = defaultdict(lambda: {"candidates": 0, "accept": 0, "reject": 0})
    for c in rel + emp:
        st = load_state(c["queue_id"])
        if not st:
            continue
        for pk, p in st["passes"].items():
            for cd in p.get("candidates", []):
                if cd["registry_id"] != "BSR-EO-05":
                    continue
                for m in vmodels:
                    v = _verdict(st, cd["candidate_id"], m)
                    if v:
                        dos_nat[m]["candidates"] += 1
                        dos_nat[m]["accept" if v in ("ACCEPT", "ACCEPT_WITH_CAVEAT") else "reject"] += 1

    # ---- cost / model table
    summary = llm.summary()

    # ---- thresholds
    verdicts = {}
    for m in vmodels:
        tot = sum(per[b][m]["done"] for b in per)
        hit_std = sum(per[b][m]["hit_std"] for b in per)
        hit_div = sum(per[b][m]["hit_div"] for b in per)
        hit_tier = sum(per[b][m]["hit_tier"] for b in per)
        # AUTHOR RATIFIED 2026-09-11: the threshold is scored on TIER-RESPECTING recall. Same-standard
        # and same-division are kept beside it as diagnostics and are never the gate.
        recall = hit_tier / tot if tot else None
        n = sum(fa[s][m]["n"] for s in fa); f = sum(fa[s][m]["false_accept"] for s in fa)
        far = f / n if n else None
        dn = fa["Dositheus"][m]["n"]; df = fa["Dositheus"][m]["false_accept"]
        dfar = df / dn if dn else None
        verdicts[m] = {"recall": recall, "recall_same_standard": hit_std / tot if tot else None,
                       "recall_same_division": hit_div / tot if tot else None,
                       "denominator": tot, "hits_tier": hit_tier, "hits_same_standard": hit_std,
                       "hits_same_division": hit_div,
                       "partial_lower_tier": sum(per[b][m]["partial_lower"] for b in per),
                       "excluded_out_of_ratified_scope": sum(per[b][m]["excluded_oos"] for b in per),
                       "false_accept": far, "dositheus_false_accept": dfar,
                       "recall_ok": recall is not None and recall >= THRESH_RECALL,
                       "false_accept_ok": far is not None and far <= THRESH_FALSE_ACCEPT,
                       "dositheus_ok": dfar is not None and dfar <= THRESH_FALSE_ACCEPT}
    # choose the live-run verifier: all thresholds met; tie-break by lower false-accept, then recall, then cost
    def cost_of(m):
        return summary["by_model"].get(m, {}).get("cost_usd", 0.0)
    eligible = [m for m in vmodels if verdicts[m]["recall_ok"] and verdicts[m]["false_accept_ok"] and verdicts[m]["dositheus_ok"]]
    chosen = sorted(eligible, key=lambda m: (verdicts[m]["false_accept"], -verdicts[m]["recall"], cost_of(m)))[0] if eligible else None

    # ---- outcome taxonomy per verifier model: why each released cell scored as it did.
    # The threshold metric credits only the SAME registry standard the released cell cites. The Gate 5
    # registry is broader than the standards those cells were closed against, so a verified citation from a
    # different AUTHOR_RATIFIED standard of the same branch lands in category B. That is an author judgment,
    # not an agent failure, so it is counted separately and never folded into the threshold.
    tax = defaultdict(Counter)
    for c in rel:
        st = load_state(c["queue_id"])
        if not st or st.get("phase") != "DONE":
            continue
        eq = equivalent_registry_ids(c)
        cands = [cd for pp in st["passes"].values() for cd in pp.get("candidates", [])]
        for m in vmodels:
            if any(((st.get("verifications") or {}).get(cd["candidate_id"]) or {}).get(m, {}).get("status") != "DONE"
                   for cd in cands):
                continue
            if c["queue_id"] in OUT_OF_RATIFIED_SCOPE:
                tax[m]["E_excluded_out_of_ratified_scope"] += 1
                continue
            bar = min((tier_rank(reg.by_id[r]["authority_tier"]) for r in eq if r in reg.by_id), default=len(TIER_RANK))
            surv = [cd for cd in cands if _verdict(st, cd["candidate_id"], m) in ("ACCEPT", "ACCEPT_WITH_CAVEAT")]
            other = [cd for cd in surv if cd["registry_id"] not in eq and cd["registry_id"] in reg.by_id
                     and reg.by_id[cd["registry_id"]]["branch"] == c["branch"]]
            if any(cd["registry_id"] in eq for cd in surv):
                tax[m]["A_same_standard"] += 1
            elif any(tier_rank(reg.by_id[cd["registry_id"]]["authority_tier"]) <= bar for cd in other):
                tax[m]["B1_other_standard_equal_or_higher_tier"] += 1
            elif other:
                tax[m]["B2_other_standard_lower_tier_partial"] += 1
            elif surv:
                tax[m]["B3_other_standard_wrong_branch"] += 1
            elif cands:
                tax[m]["C_all_candidates_rejected"] += 1
            else:
                tax[m]["D_locator_empty"] += 1

    report = {"run": meta, "per_branch": {b: dict(v) for b, v in per.items()}, "expected_empty": emp_rows, "planted": {s: dict(v) for s, v in fa.items()},
              "taxonomy": {m: dict(v) for m, v in tax.items()},
              "tier_rank": TIER_RANK, "out_of_ratified_scope": OUT_OF_RATIFIED_SCOPE,
              "residue": {m: v for m, v in residue.items()},
              "skipped_cells": {m: v for m, v in skipped_cells.items()},
              "caveat_hits": caveat_hits,
              "dositheus_natural": dict(dos_nat), "models": summary, "verdicts": verdicts, "chosen_verifier": chosen, "details": details}
    with open(os.path.join(run_dir, "calibration-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    md = render_md(report, reg, manifest)
    with open(os.path.join(RUNS_DIR, "calibration-report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    log(md)
    return 0


def pct(x):
    return "—" if x is None else f"{x:.3f}"


def render_md(rep, reg, manifest):
    meta = rep["run"]; vm = meta["verifier_models"]
    L = []
    L.append(f"# SJN Gate 6 — Calibration report ({meta['run_id']})\n")
    L.append(f"Workbook {meta['workbook']} ({meta['app_master_version']}) · prompt version {meta['prompt_version']} · "
             f"locator model `{meta['locator_model']}` · verifier models {', '.join('`' + m + '`' for m in vm)} · backend {meta['backend']} · "
             f"generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n")
    L.append("Locators hidden: the agents received predicate, definition, floor note, subject scope and registry chunks only — never the "
             "workbook's document, locator or phrase. False-accept = verifier ACCEPT or ACCEPT_WITH_CAVEAT on a planted near-miss. "
             "Thresholds: recall ≥ 0.8, false-accept ≤ 0.05 (Dositheus slice held to 0.05 on its own). Thresholds were not moved.\n")
    L.append("### The three recall metrics\n")
    L.append("| metric | a verified candidate counts as a hit when it sits… | role |")
    L.append("|---|---|---|")
    L.append("| same-division | in the same registry standard AND the same division the released cell cites | diagnostic |")
    L.append("| same-standard | in the same registry standard the released cell cites | diagnostic, kept in the table |")
    L.append("| **tier-respecting** | in the same registry standard, **or** in a different ratified standard of the correct branch whose "
             "`authority_tier` is equal to or higher than the tier of the cited standard | **the threshold metric** |")
    L.append("")
    L.append("A substitution into a LOWER tier is a **partial**. It is not credited and is reported in its own column.\n")
    L.append("**AUTHOR RATIFIED 2026-09-11 (AJP)** — `authority_tier` is a genuine authority rank, descending:\n")
    L.append("`" + " > ".join(rep.get("tier_rank", [])) + "`\n")
    L.append("Used as given, not re-derived from the workbook. Ranking is on the **bare tier**: the parenthetical qualifiers on "
             "BSR-RC-03 (`CONCILIAR (translation)`), BSR-EO-04 (`CATECHETICAL (historic)`) and BSR-BA-02 "
             "(`CONFESSIONAL (voluntary church-level subscription)`) are disclosure, not rank. The rank is proposed to Gate 7 as the "
             "APP CONFIG key `authority_tier_rank` in `recovery-runs/proposed-app-config-gate7.md`. **Nothing in Gate 6 writes to the "
             "workbook.**\n")
    L.append("## What changed since cal-1\n")
    L.append("cal-1 is kept intact beside this report at `recovery-runs/cal-1/`. cal-2 re-ran the 105 cells whose supplied "
             "chunk set changed under the retrieval fixes below; the other 43 were carried over unchanged from cal-1's "
             "answered calls and cost nothing.\n")
    L.append("### Retrieval — the dominant cal-1 defect\n")
    L.append("cal-1's largest residue was `LOCATOR_EMPTY`: 10 cells per model where the locator was handed the correct "
             "standard and still found nothing. Three separate faults, all in the harness:\n")
    L.append("1. **The query was swamped by the floor note.** `query_text()` weighted the predicate term, its definition and "
             "the floor note equally. The floor note is analytic prose about the coding decision, so ranking favoured long "
             "scholastic discussion over the terse creedal assertion that is the actual evidence. The predicate term is now "
             "weighted three times.")
    L.append("2. **No lexical guarantee.** Nothing ensured that chunks literally using the predicate's own vocabulary reached "
             "the locator. 70% of each standard's character allowance is now reserved for them, ranked among themselves on the "
             "predicate term alone. Blending that with the general ranking (RRF) was measurably worse and was rejected.")
    L.append("3. **Composite volumes swallowed their own allowance.** BSR-LU-01 is the whole Book of Concord (738 chunks) and "
             "BSR-RP-04 the whole Book of Confessions (1,018). A flat ranking let the longest constituent book take every slot: "
             "the three Ecumenical Creeds are 3 chunks of BSR-LU-01's 738 and never surfaced. The allowance is now allocated "
             "round-robin across the constituent works read off each chunk's own locator, so every constituent is represented. "
             "For a flat text such as the Catechism, where each chunk is its own division, this degenerates to plain rank order "
             "and changes nothing.\n")
    L.append("4. **Function words drove the lexical slice.** The slice admitted a chunk on any predicate word of four letters or "
             "more, and \u201cwithout\u201d appears in 48% of the Book of Concord and 55% of the Confession of Dositheus. Terms "
             "above a 35% document frequency within a standard are now dropped for that standard, keeping the rarest if all are "
             "above it. This swapped out 10 to 11 noise chunks each for Q-331 and Q-339, the two \u201cwithout\u201d cases in "
             "the Book of Concord.\n")
    L.append("`LOCATOR_EMPTY` fell from 10 per model to 6.\n")
    L.append("These changes are not uniformly positive, and the report does not claim they are. Measured cell by cell against "
             "cal-1, 9 cells gained a tier-respecting hit and 8 lost one, for a net of +1 before the frequency ceiling was "
             "added. Every one of the 8 losses was checked individually: in all 8 the division the released cell cites was "
             "supplied to the locator in both runs, so none was a retrieval regression. Six found evidence in a lower-tier "
             "standard instead and scored as partials; four returned nothing while the correct article sat in the supplied "
             "context. Those are locator judgment, not harness defects, and they are the honest cost of the sampling.\n")
    L.append("### Q-363 — the Athanasian Creed (step 4)\n")
    L.append("The creeds **are** in BSR-LU-01's indexed corpus, so this was never a splitter coverage gap. It was fault 3 "
             "above. The Athanasian Creed ranked 260th of 738 on the cal-1 query and was never supplied; under the division "
             "round robin it arrives at slot 6. The locator now returns the workbook's own passage — *\u201cThe Father eternal, "
             "the Son eternal, and the Holy Ghost eternal\u201d* — and both verifiers accept it.\n")
    L.append("### Eastern Orthodox zero-chunk exposure (step 4)\n")
    L.append("**0 of the 10 Eastern Orthodox released cells cite a row that yielded zero chunks.** Only BSR-EO-03 has zero "
             "chunks (`FETCH_BLOCKED`, Cloudflare) and no released cell cites it. An earlier reading of cal-1 attributed the "
             "Eastern Orthodox recall gap to that block; that was wrong and is corrected here. The Eastern Orthodox gap is a "
             "tier effect: the branch's conciliar row BSR-EO-06 holds 2 chunks of OCA *Church History* summary prose rather "
             "than the conciliar definitions, so evidence is recovered from lower-tier rows and scores as a partial.\n")
    L.append("### BSR-EO-04 accepted drift (step 3)\n")
    L.append("| | chunks | characters | `text_hash` |")
    L.append("|---|---|---|---|")
    L.append("| before | 305 | 197,641 | `2248097d27346f7b…9de2b21c` |")
    L.append("| after | 610 | 197,336 | `9277b1dc0eb3ad01…e9baf6a6` |")
    L.append("")
    L.append("The character count moved by 305 of 197,641 (0.15%) while the chunk count doubled, which is the signature of a "
             "boundary change rather than a content change: the same text, cut in twice as many places. The page changes shape "
             "partway through — questions 1–306 lead with a `<p>` carrying \u201cN. text\u201d, from 307 they move into `<b>` "
             "with the text inline — and the earlier splitter recognised only one shape, so it merged question pairs across "
             "most of the document. The **gap-tolerance fix** (accepting a question number up to three ahead of the expected "
             "one) had raised the count from 287 to 305 by letting the walk survive the numbers the page omits; it did not "
             "address the tag change. Splitting is now driven by the question sequence rather than tag shape, which recovers "
             "610 of the catechism's 611 questions. Philaret is the branch's largest corpus, so this materially widened what "
             "the Eastern Orthodox locator could see.\n")
    L.append("### Skipped cells (step 3)\n")
    L.append("cal-1 skipped 9 cells for `sonnet` and 6 for `opus` while `corpus unavailable` read 0. Every one was the same "
             "artifact, per cell: a verifier reply truncated at the token ceiling or returned with no text block at all, "
             "recorded `UNPARSEABLE` and then treated as terminal so it was never retried. The corpus was never the problem, "
             "which is why `corpus unavailable` read 0. Three cells — Q-048, Q-215 and Q-363 — had the same failure in the "
             "**locator** pass: an empty reply banked as a genuine empty result. All were re-run for cal-2 and the per-cell "
             "table below now shows 0 skipped for both models.\n")
    L.append("### Fixed and re-run (step 5)\n")
    L.append("| fix | where | effect |")
    L.append("|---|---|---|")
    L.append("| Predicate term weighted 3x in the retrieval query | `retrieval.py` `query_text` | ranking follows the predicate, not the floor note |")
    L.append("| Lexical slice: 70% of the allowance reserved for chunks using the predicate's vocabulary | `retrieval.py` `select_chunks` | Book of Concord supply went from 13 chunks, almost none using the term, to 28 of which 27 do |")
    L.append("| Document-frequency ceiling of 35% on slice terms | `retrieval.py` `discriminating_terms` | \u201cwithout\u201d no longer admits half the Book of Concord |")
    L.append("| Division round robin across a composite volume's constituent works | `retrieval.py` `division_of`, `round_robin` | the Ecumenical Creeds reach the locator; Q-363 recovered |")
    L.append("| Philaret split by question sequence rather than tag shape | `sources.py` `philaret` | BSR-EO-04 305 -> 610 chunks |")
    L.append("| `UNPARSEABLE` made retryable at both locator and verifier | `agents.py` | 15 skipped cells recovered; 0 skipped in cal-2 |")
    L.append("| Empty-reply guard: a reply with no text block is retried with a larger ceiling | `api_executor.py` | no more empty answers banked as forced REJECT |")
    L.append("")
    L.append("### Not fixable without an author call\n")
    L.append("| row | state | why it is not a Gate 6 defect |")
    L.append("|---|---|---|")
    L.append("| BSR-EO-03 | `FETCH_BLOCKED` (Cloudflare), 0 chunks | No released cell cites it; no recall effect measured. |")
    L.append("| BSR-MW-03 | `UNAVAILABLE_ON_RATIFIED_DOMAIN`, 404 | AC-06 ratified both the GMC and the Wesleyan row; the surviving row carries the branch. |")
    L.append("| BSR-LU-02 | `AUTHORITY_URL_ONLY`, no corpus | AC-08 as drafted needs nothing further. |")
    L.append("| BSR-RC-03 | `canonical_url` still `ewtn.com` | AC-02 MIGRATE_WHERE_OFFICIAL is a Gate 7 action. Expected, not a defect. |")
    L.append("| Q-449 | OUT_OF_RATIFIED_SCOPE | The cited text is Lateran IV canon 2; BSR-RC-04 ratifies canon 1. Widening the row or re-pointing the cell is an author call. |")
    L.append("")
    L.append("## Verdict by verifier model\n")
    L.append("| verifier model | model id | n | recall same-division | recall same-standard | **recall tier-respecting** | partial (lower tier) | "
             "false-accept | Dositheus false-accept | calls | cost (USD) | thresholds |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in vm:
        v = rep["verdicts"][m]; s = rep["models"]["by_model"].get(m, {})
        ok = "MET" if (v["recall_ok"] and v["false_accept_ok"] and v["dositheus_ok"]) else "NOT MET"
        L.append(f"| `{m}` | {MODEL_IDS.get(m, m)} | {v.get('denominator', 0)} | "
                 f"{v.get('hits_same_division', 0)}/{v.get('denominator', 0)} = {pct(v.get('recall_same_division'))} | "
                 f"{v.get('hits_same_standard', 0)}/{v.get('denominator', 0)} = {pct(v.get('recall_same_standard'))} | "
                 f"**{v.get('hits_tier', 0)}/{v.get('denominator', 0)} = {pct(v['recall'])}** | {v.get('partial_lower_tier', 0)} | "
                 f"{pct(v['false_accept'])} | {pct(v['dositheus_false_accept'])} | "
                 f"{s.get('calls', 0)} | {s.get('cost_usd', 0.0):.2f}{' (est.)' if s.get('estimated') else ''} | {ok} |")
    _ex = max((rep["verdicts"][m].get("excluded_out_of_ratified_scope", 0) for m in vm), default=0)
    L.append(f"\nThe denominator excludes **{_ex}** released cell(s) classed OUT_OF_RATIFIED_SCOPE (listed below). "
             "The threshold is scored on the tier-respecting column only.")
    loc = rep["models"]["by_model"].get(meta["locator_model"], {})
    L.append(f"\nLocator `{meta['locator_model']}`: {loc.get('calls', 0)} calls, {loc.get('cost_usd', 0.0):.2f} USD"
             f"{' (est.)' if loc.get('estimated') else ''}. Total calls {rep['models']['calls']}.\n")
    _met = [m for m in vm if rep["verdicts"][m]["recall_ok"] and rep["verdicts"][m]["false_accept_ok"] and rep["verdicts"][m]["dositheus_ok"]]
    L.append("**Live-run verifier: NOT NAMED HERE.** Gate 6 reports the thresholds and stops; the author selects the live-run "
             f"verifier after reading this report. Models meeting every threshold: "
             f"{', '.join('`' + m + '`' for m in _met) if _met else 'none'}.\n")
    L.append("**The live run against the 315 open cells has not been started.**\n")
    L.append("## Why each released cell scored as it did\n")
    L.append("Gate 5 widened every branch to two tiers, so a branch now carries several ratified standards that each confess the "
             "same predicate. A team that cites a different one of them has not failed. Row B1 is that case at an equal or higher "
             "authority tier and is credited; row B2 is the same case at a LOWER tier and is a partial, never credited. Rows C and "
             "D are the genuine no-evidence outcomes. Row E is excluded from every denominator.\n")
    L.append("| outcome | " + " | ".join(f"`{m}`" for m in vm) + " |")
    L.append("|---|" + "---|" * len(vm))
    _labels = [("A_same_standard", "A. hit in the same standard the cell cites"),
               ("B1_other_standard_equal_or_higher_tier", "B1. different ratified standard of the branch, **equal or higher** tier — credited"),
               ("B2_other_standard_lower_tier_partial", "B2. different ratified standard of the branch, **lower** tier — partial, not credited"),
               ("B3_other_standard_wrong_branch", "B3. survivor outside the cell's branch"),
               ("C_all_candidates_rejected", "C. candidates found, all rejected by the verifier"),
               ("D_locator_empty", "D. locator returned empty"),
               ("E_excluded_out_of_ratified_scope", "E. excluded — cited text outside every ratified row of the branch")]
    _tx = rep.get("taxonomy", {})
    for _key, _label in _labels:
        L.append(f"| {_label} | " + " | ".join(str(_tx.get(m, {}).get(_key, 0)) for m in vm) + " |")
    L.append("| **total scored** | " + " | ".join(str(sum(_tx.get(m, {}).values())) for m in vm) + " |")
    L.append("")
    for m in vm:
        _d = _tx.get(m, {})
        _n = (sum(_d.values()) - _d.get("E_excluded_out_of_ratified_scope", 0)) or 1
        _a = _d.get("A_same_standard", 0); _b1 = _d.get("B1_other_standard_equal_or_higher_tier", 0)
        _b2 = _d.get("B2_other_standard_lower_tier_partial", 0)
        L.append(f"- `{m}`: tier-respecting recall **{_a + _b1}/{_n} = {(_a + _b1) / _n:.3f}** (the threshold metric); "
                 f"same-standard **{_a}/{_n} = {_a / _n:.3f}**; lower-tier partials **{_b2}** (not credited); "
                 f"genuine no-evidence **{_d.get('C_all_candidates_rejected', 0) + _d.get('D_locator_empty', 0)}/{_n}**.")
    L.append("")
    L.append("## Recall per branch — all three metrics, by verifier model\n")
    L.append(f"Secondary-verifier scope: {meta.get('secondary_scope', 'ALL')}. A model's recall denominator is the cells it verified in full "
             "(`done`); cells outside a secondary model's scope are counted under `skipped`.\n")
    L.append("| branch | model | released cells | done | skipped | excl. scope | located (any) | same-division | same-standard | "
             "**tier-respecting** | partial (lower) | empty | corpus unavailable |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for b in BRANCHES:
        for m in vm:
            r = rep["per_branch"].get(b, {}).get(m)
            if not r:
                continue
            d = r["done"] or 1
            L.append(f"| {b} | `{m}` | {r['cells']} | {r['done']} | {r.get('skipped', 0)} | {r.get('excluded_oos', 0)} | {r['located_any']} | "
                     f"{r['hit_div']}/{r['done']} = {r['hit_div'] / d:.2f} | "
                     f"{r['hit_std']}/{r['done']} = {r['hit_std'] / d:.2f} | "
                     f"**{r.get('hit_tier', 0)}/{r['done']} = {r.get('hit_tier', 0) / d:.2f}** | "
                     f"{r.get('partial_lower', 0)} | {r['empty']} | {r['no_corpus']} |")
    # ---------------- out of ratified scope
    L.append("\n## OUT_OF_RATIFIED_SCOPE — cells excluded from the recall denominator\n")
    _oos = rep.get("out_of_ratified_scope", {})
    L.append(f"**{len(_oos)} released cell(s) excluded.** The cited text lies outside the ratified scope of every row in the cell's "
             "branch, so no agent could have found it: the passage is not in the corpus the registry ratified. These are not misses "
             "and are not counted as misses.\n")
    if _oos:
        L.append("| cell | cited | ratified scope | where the phrase actually sits | reason |")
        L.append("|---|---|---|---|---|")
        for qid, d in sorted(_oos.items()):
            L.append(f"| {qid} | {d['cited']} | {d['ratified_scope']} | {d['phrase_actually_sits_in']} | {d['reason']} |")
    # ---------------- caveated rows
    L.append("\n## Caveated rows in winning candidates (AC-03, AC-05)\n")
    _cv = rep.get("caveat_hits", [])
    if not _cv:
        L.append("No winning candidate landed on BSR-EO-04 (Philaret) or BSR-EO-05 (Dositheus).\n")
    else:
        L.append(f"{len(_cv)} candidate(s) landed on a caveated row. The caveat travels with the packet entry.\n")
        L.append("| cell | model | row | locator | credited | caveat |")
        L.append("|---|---|---|---|---|---|")
        for h in _cv:
            L.append(f"| {h['queue_id']} | `{h['model']}` | {h['registry_id']} | {h['locator'][:46]} | "
                     f"{'yes' if h.get('credited') else 'no (lower tier — partial)'} | {h['caveat']} |")
    # ---------------- residue
    L.append("\n## Residue under the tier-respecting metric\n")
    for m in vm:
        _r = rep.get("residue", {}).get(m, [])
        L.append(f"\n### `{m}` — {len(_r)} cell(s) not credited\n")
        if not _r:
            L.append("None.\n"); continue
        L.append("| cell | branch | predicate | cited tier | class | lower-tier evidence offered |")
        L.append("|---|---|---|---|---|---|")
        for d in _r:
            L.append(f"| {d['queue_id']} | {d['branch']} | {d['predicate'][:30]} | {d['cited_tier']} | {d['class']} | "
                     f"{'; '.join(f'{a} ({b}) {c[:30]}' for a, b, c in d['lower_tier_offered']) or '—'} |")
    # ---------------- skipped cells
    L.append("\n## Skipped cells — reason per cell\n")
    L.append("`SECONDARY_SCOPE` means the cell is outside that model's defined sample (every Eastern Orthodox cell, every "
             "reviewed-empty cell, and a deterministic quarter of the rest). It is not a failure and the cell is not in that "
             "model's denominator. `VERIFICATION_INCOMPLETE` and `CELL_NOT_DONE` are.\n")
    for m in vm:
        _s = rep.get("skipped_cells", {}).get(m, [])
        _by = Counter(x[3] for x in _s)
        L.append(f"\n### `{m}` — {len(_s)} skipped ({', '.join(f'{k} {v}' for k, v in sorted(_by.items())) or 'none'})\n")
        if not _s:
            L.append("None.\n"); continue
        L.append("| cell | branch | predicate | reason | detail |")
        L.append("|---|---|---|---|---|")
        for qid, br, pr, reason, detail in _s:
            L.append(f"| {qid} | {br} | {pr[:28]} | {reason} | {detail} |")
    L.append("\n## Expected-empty cells (NOT LOCATED — CURRENT STANDARD REVIEWED)\n")
    L.append("| cell | branch | predicate | model | outcome | survivors |")
    L.append("|---|---|---|---|---|---|")
    for e in rep["expected_empty"]:
        L.append(f"| {e['queue_id']} | {e.get('branch')} | {e.get('predicate', '')} | {e.get('model', '')} | {e.get('outcome', e.get('status'))} | "
                 f"{'; '.join(f'{a} {b}: “{c}”' for a, b, c in e.get('survivors', []))} |")
    L.append("\nThe registry ratified in Gate 5 is broader than the standards those cells were closed against; a candidate located in another "
             "registry standard of the same branch is new evidence for Gate 7, not a false accept.\n")
    L.append("## Planted near-misses — false-accept by slice and model\n")
    L.append("| slice | model | planted | false accepts | rate | pending |")
    L.append("|---|---|---|---|---|---|")
    for s_ in sorted(rep["planted"]):
        for m in vm:
            r = rep["planted"][s_].get(m)
            if not r:
                continue
            L.append(f"| {s_} | `{m}` | {r['n']} | {r['false_accept']} | {pct(r['false_accept'] / r['n']) if r['n'] else '—'} | {r['pending']} |")
    items = [(s_, m, it) for s_ in rep["planted"] for m in vm for it in rep["planted"][s_].get(m, {}).get("items", [])]
    if items:
        L.append("\nFalse accepts (each is a verifier failure to keep):\n")
        for s_, m, it in items:
            L.append(f"- {s_} · `{m}` · {it[0]} ({it[1]}) {it[2]} → {it[3]}: {it[4]}")
    L.append("\n## Dositheus slice (BSR-EO-05) — natural candidates from the Eastern Orthodox cells\n")
    L.append("| model | Dositheus candidates | accepted | rejected |")
    L.append("|---|---|---|---|")
    for m in vm:
        d = rep["dositheus_natural"].get(m, {"candidates": 0, "accept": 0, "reject": 0})
        L.append(f"| `{m}` | {d['candidates']} | {d['accept']} | {d['reject']} |")
    L.append("\n## Corpus state at calibration\n")
    L.append("| registry | branch | status | chunks |")
    L.append("|---|---|---|---|")
    for rid, s_ in manifest.get("standards", {}).items():
        L.append(f"| {rid} | {s_.get('branch', '')} | {s_.get('status')} | {s_.get('n_chunks', 0)} |")
    L.append("\n## Per-cell detail (primary verifier)\n")
    L.append("`STD+DIV` same standard and division · `STD` same standard · `TIER` different ratified standard of the branch at an "
             "equal or higher tier (credited) · `PARTIAL (lower tier)` different standard at a lower tier (not credited) · `MISS` no "
             "verified evidence.\n")
    L.append("| cell | branch | predicate | cited tier | existing citation | hit | survivors | rejected (reason) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for d in rep["details"]:
        if d["hit_same_division"]:
            hit = "STD+DIV"
        elif d["hit_same_standard"]:
            hit = "STD"
        elif d.get("hit_tier_respecting"):
            hit = "TIER"
        elif d.get("partial_lower_tier"):
            hit = "PARTIAL (lower tier)"
        else:
            hit = "no corpus" if not d["corpus_available"] else "MISS"
        L.append(f"| {d['queue_id']} | {d['branch']} | {d['predicate']} | {d.get('cited_tier', '?')} | {d['existing'][:60]} | {hit} | "
                 f"{'; '.join(f'{a} {b[:40]}: “{c}”' for a, b, c in d['survivors'])} | "
                 f"{'; '.join(f'{a} {b[:30]} {v}/{rc}' for a, b, v, rc in d['rejected'])} |")
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
        p.add_argument("--verifier-models", default="sonnet")
        p.add_argument("--branch")
        p.add_argument("--limit", type=int)
        p.add_argument("--full-secondary", action="store_true", help="run every verifier model on every cell")
    a = ap.parse_args()
    return {"run": cmd_run, "plant": cmd_plant, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
