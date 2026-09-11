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
from collections import defaultdict
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, CALIBRATION_DIR, BRANCHES, ensure_dirs, MODEL_IDS  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, released_cells, reviewed_empty_cells  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import guards, prompts, store  # noqa: E402

THRESH_RECALL = 0.8
THRESH_FALSE_ACCEPT = 0.05
PLANTED_PATH = os.path.join(CALIBRATION_DIR, "planted-near-misses.json")


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
                                                    "hit_phrase": 0, "no_corpus": 0, "empty": 0}))
    details = []
    for c in rel:
        st = load_state(c["queue_id"])
        eq = equivalent_registry_ids(c)
        corpus_available = any((manifest.get("standards", {}).get(r, {}).get("n_chunks") or 0) > 0 for r in eq)
        for m in vmodels:
            b = per[c["branch"]][m]
            b["cells"] += 1
            if not st or st.get("phase") != "DONE":
                continue
            all_cands = [cd for pk, p in st["passes"].items() for cd in p.get("candidates", [])]
            if any(((st.get("verifications") or {}).get(cd["candidate_id"]) or {}).get(m, {}).get("status") != "DONE" for cd in all_cands):
                b["skipped"] = b.get("skipped", 0) + 1
                continue   # this model did not verify this cell (secondary scope) — not in its denominator
            b["done"] += 1
            if not corpus_available:
                b["no_corpus"] += 1
            cands = [cd for pk, p in st["passes"].items() for cd in p.get("candidates", [])]
            surv = [cd for cd in cands if _verdict(st, cd["candidate_id"], m) in ("ACCEPT", "ACCEPT_WITH_CAVEAT")]
            if surv:
                b["located_any"] += 1
            else:
                b["empty"] += 1
            hit_std = any(cd["registry_id"] in eq for cd in surv)
            hit_div = any(cd["registry_id"] in eq and same_division(c["locator"], cd["locator"]) for cd in surv)
            hit_phrase = False
            known = c.get("_phrase")
            b["hit_std"] += hit_std; b["hit_div"] += hit_div
            if m == vmodels[0]:
                details.append({"queue_id": c["queue_id"], "branch": c["branch"], "family_id": c["family_id"], "predicate": c["predicate"],
                                "existing": f"{c['document']} — {c['locator']}", "equivalent_registry": sorted(eq), "corpus_available": corpus_available,
                                "survivors": [(cd["registry_id"], cd["locator"], cd["phrase"]) for cd in surv],
                                "hit_same_standard": hit_std, "hit_same_division": hit_div,
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
        tot = sum(per[b][m]["done"] for b in per); hit = sum(per[b][m]["hit_std"] for b in per)
        recall = hit / tot if tot else None
        n = sum(fa[s][m]["n"] for s in fa); f = sum(fa[s][m]["false_accept"] for s in fa)
        far = f / n if n else None
        dn = fa["Dositheus"][m]["n"]; df = fa["Dositheus"][m]["false_accept"]
        dfar = df / dn if dn else None
        verdicts[m] = {"recall": recall, "false_accept": far, "dositheus_false_accept": dfar,
                       "recall_ok": recall is not None and recall >= THRESH_RECALL,
                       "false_accept_ok": far is not None and far <= THRESH_FALSE_ACCEPT,
                       "dositheus_ok": dfar is not None and dfar <= THRESH_FALSE_ACCEPT}
    # choose the live-run verifier: all thresholds met; tie-break by lower false-accept, then recall, then cost
    def cost_of(m):
        return summary["by_model"].get(m, {}).get("cost_usd", 0.0)
    eligible = [m for m in vmodels if verdicts[m]["recall_ok"] and verdicts[m]["false_accept_ok"] and verdicts[m]["dositheus_ok"]]
    chosen = sorted(eligible, key=lambda m: (verdicts[m]["false_accept"], -verdicts[m]["recall"], cost_of(m)))[0] if eligible else None

    report = {"run": meta, "per_branch": {b: dict(v) for b, v in per.items()}, "expected_empty": emp_rows, "planted": {s: dict(v) for s, v in fa.items()},
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
             "workbook's document, locator or phrase. Recall = a verified candidate in the same registry standard the released cell cites "
             "(or an equivalent passage in that standard); same-division recall is reported alongside. False-accept = verifier ACCEPT or "
             "ACCEPT_WITH_CAVEAT on a planted near-miss. Thresholds: recall ≥ 0.8, false-accept ≤ 0.05 (Dositheus slice held to 0.05 on its own).\n")
    L.append("## Verdict by verifier model\n")
    L.append("| verifier model | model id | recall | false-accept | Dositheus false-accept | calls | cost (USD) | thresholds |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in vm:
        v = rep["verdicts"][m]; s = rep["models"]["by_model"].get(m, {})
        ok = "MET" if (v["recall_ok"] and v["false_accept_ok"] and v["dositheus_ok"]) else "NOT MET"
        L.append(f"| `{m}` | {MODEL_IDS.get(m, m)} | {pct(v['recall'])} | {pct(v['false_accept'])} | {pct(v['dositheus_false_accept'])} | "
                 f"{s.get('calls', 0)} | {s.get('cost_usd', 0.0):.2f}{' (est.)' if s.get('estimated') else ''} | {ok} |")
    loc = rep["models"]["by_model"].get(meta["locator_model"], {})
    L.append(f"\nLocator `{meta['locator_model']}`: {loc.get('calls', 0)} calls, {loc.get('cost_usd', 0.0):.2f} USD"
             f"{' (est.)' if loc.get('estimated') else ''}. Total calls {rep['models']['calls']}.\n")
    L.append(f"**Verifier chosen for the live run: {('`' + rep['chosen_verifier'] + '`') if rep['chosen_verifier'] else 'NONE — thresholds not met'}.**\n")
    L.append("## Recall per branch (same standard / same division), by verifier model\n")
    L.append(f"Secondary-verifier scope: {meta.get('secondary_scope', 'ALL')}. A model's recall denominator is the cells it verified in full "
             "(`done`); cells outside a secondary model's scope are counted under `skipped`.\n")
    L.append("| branch | model | released cells | done | skipped | located (any) | recall same-standard | recall same-division | empty | corpus unavailable |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for b in BRANCHES:
        for m in vm:
            r = rep["per_branch"].get(b, {}).get(m)
            if not r:
                continue
            d = r["done"] or 1
            L.append(f"| {b} | `{m}` | {r['cells']} | {r['done']} | {r.get('skipped', 0)} | {r['located_any']} | {r['hit_std']}/{r['done']} = {r['hit_std'] / d:.2f} | "
                     f"{r['hit_div']}/{r['done']} = {r['hit_div'] / d:.2f} | {r['empty']} | {r['no_corpus']} |")
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
    L.append("| cell | branch | predicate | existing citation | hit | survivors | rejected (reason) |")
    L.append("|---|---|---|---|---|---|---|")
    for d in rep["details"]:
        hit = "STD+DIV" if d["hit_same_division"] else ("STD" if d["hit_same_standard"] else ("no corpus" if not d["corpus_available"] else "MISS"))
        L.append(f"| {d['queue_id']} | {d['branch']} | {d['predicate']} | {d['existing'][:60]} | {hit} | "
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
