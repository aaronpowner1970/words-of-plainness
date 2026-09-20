"""Re-verify stored candidates under the current verifier prompt (Gate 6 session 5, Task 6: Q-003; session 6: R6-1 and
truncated replies).

  python scripts/sjn_recovery/reverify.py --run-id live-1 --queue-id Q-003 --candidate-id Q-003-p3-BSR-LU-01-b22-1   # issues the two calls
  python scripts/sjn_recovery/api_executor.py --run-id live-1 --workers 2 --max-cost-usd 1 --key-file <.env>
  python scripts/sjn_recovery/reverify.py --run-id live-1 --queue-id Q-003 --candidate-id Q-003-p3-BSR-LU-01-b22-1   # ingests, finalises
  python scripts/sjn_recovery/run.py --run-id live-1 --branch Lutheran --verifier-models sonnet,opus --rebuild-packet-only

  python scripts/sjn_recovery/reverify.py --run-id live-1 --candidates-file <json>     # many: [{queue_id, candidate_id, models, reason}]

The stored rubrics are moved, not deleted, to `superseded_rubrics` (with their prompt version and the final verdict they
gave); the named models then verify the candidate afresh under the current prompt and the current predicate record (session 6:
the R6-1 required_subject), and the verdict is finalised by the ordinary rule (agents.finalize: the candidate's stored route,
the lower floor, any floor ruling). A candidate is re-verified by the models that verified it before (a candidate that carried
an opus rubric gets both again), so its route is unchanged. No other candidate is touched; the cell's allocation and coder
state are recomputed by the rebuild. Nothing writes to the workbook.

Session 14 (R6-48, Codex F.10): a re-verification after a CORPUS REPAIR is re-pointed at the text the repair left.

  verify() builds its chunk view from the candidate as stored -- `cand["chunk_text"]`, `cand["registry_id"]` and
  `cand["locator"]` -- so a re-verification of a repaired citation would have sent the verifier the very text the repair
  replaced. On the AN-04 / AN-06 split that is the Quicunque Vult cut at "one Almighty.": the re-read would have measured
  the instrument change and nothing else, and would have certified a stump. repoint() follows the same chunk-id mapping
  the packet builder follows (packets.relocate, composing every mapping in config.CHUNK_ID_MAPPINGS) and hands verify()
  the row, locator and text the store holds NOW. It fails closed: where no current chunk carries the phrase verbatim, the
  candidate is NOT verified and is reported, never quietly judged against stale text."""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, open_cells, assert_gate6_scope  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import prompts, packets, store, guards  # noqa: E402

MODELS = ("sonnet", "opus")


def chunk_index(rows=None):
    """{(registry_id, locator): chunk} over every stored row (or the named ones)."""
    from sjn_recovery.registry import Registry
    rids = rows or [r["registry_id"] for r in Registry().rows]
    return {(c["registry_id"], c["locator"]): c for rid in rids for c in store.load_chunks(rid)}


def repoint(cand, index=None, moves=None):
    """The candidate as the CURRENT store holds it, and a record of what moved. Returns (cand_now, repointed | None,
    problem | None).

    Codex F.10 / R6-48: a citation whose chunk was repaired is re-verified against the repaired chunk, in the row that
    holds it now -- never against the stored text the repair replaced. Fails closed: `problem` is set and cand_now is
    None where no current chunk carries the phrase verbatim."""
    index = chunk_index() if index is None else index
    moves = packets.relocations() if moves is None else moves
    chunk, rel = packets.relocate(cand, index, moves)
    if chunk is None:
        return None, None, f"no stored chunk for {cand['registry_id']} {cand['locator']!r}, and none mapped carries the phrase"
    ok, why = guards.check_phrase(cand["phrase"], chunk["text"])
    if not ok:
        return None, None, f"the phrase is not verbatim in the chunk the store holds now: {why}"
    changed = (chunk["registry_id"], chunk["locator"], chunk["text_hash"]) != (
        cand["registry_id"], cand["locator"], cand.get("chunk_hash"))
    cand_now = dict(cand, registry_id=chunk["registry_id"], locator=chunk["locator"],
                    chunk_text=chunk["text"], chunk_hash=chunk["text_hash"])
    if not changed:
        return cand_now, None, None
    rec = {"registry_id_at_run": cand["registry_id"], "registry_id_now": chunk["registry_id"],
           "locator_at_run": cand["locator"], "locator_now": chunk["locator"],
           "chunk_hash_at_run": cand.get("chunk_hash"), "chunk_hash_now": chunk["text_hash"],
           "chars_at_run": len(cand.get("chunk_text") or ""), "chars_now": len(chunk["text"]),
           "cross_row": bool(rel and rel.get("cross_row")),
           "mapping_file": (rel or {}).get("mapping_file"),
           "why": "Codex F.10 corpus repair: the verifier judges the text the store holds now, in the row that holds it "
                  "now, never the text the repair replaced (R6-48)"}
    return cand_now, rec, None


def reverify_one(runner, cells, item, log=print, index=None, moves=None):
    """Returns (status, summary) — status PENDING while a call is unanswered, REFUSED where the candidate cannot be
    re-pointed at a current chunk that carries its phrase."""
    qid, cid, reason = item["queue_id"], item["candidate_id"], item["reason"]
    cell = cells[qid]
    st = runner.load(qid)
    cand = next(c for p in st["passes"].values() for c in p.get("candidates", []) if c["candidate_id"] == cid)
    # session 14 (R6-48): judge the text the store holds NOW, in the row that holds it now
    cand_now, repointed, problem = repoint(cand, index, moves)
    if problem:
        log(f"!! {qid} {cid}: NOT re-verified — {problem}")
        return "REFUSED", {"queue_id": qid, "candidate_id": cid, "refused": problem}
    v = st["verifications"][cid]
    vmodels = item.get("models") or [m for m in MODELS if isinstance(v.get(m), dict)] or ["sonnet"]
    if "superseded_rubrics" not in v or v["superseded_rubrics"].get("reason") != reason:
        prior = v.get("superseded_rubrics")
        v["superseded_rubrics"] = {"moved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "reason": reason,
                                   "rubrics": {m: v.pop(m) for m in vmodels if m in v},
                                   "final": v.get("final"), "final_at_run": v.get("final_at_run")}
        if prior:
            v["superseded_rubrics"]["earlier"] = prior
    if repointed:
        v["repointed"] = repointed
    pending = False
    for m in vmodels:
        if m not in v or v[m].get("status") in ("PENDING", "UNPARSEABLE"):
            # R6-54: a re-verification is a production read, so it votes exactly as a branch run does
            v[m] = runner.verify_voted(cell, cand_now, m)
        if v[m].get("status") == "PENDING":
            pending = True
    if pending:
        runner.save(st)
        return "PENDING", None
    fin = runner.finalize(v, runner.primary, runner.adjudicator)
    v["reverified"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "prompt_version": prompts.prompt_version("verifier"),
                       "models": vmodels, "route_kept": v.get("_route"), "reason": reason,
                       "votes_per_candidate": runner.votes_per_candidate, "repointed": repointed,
                       "required_subject": runner.predicates[cell["family_id"]]["subject_scope"]}
    runner.save(st)
    old = (v["superseded_rubrics"].get("final") or {})
    return "DONE", {"queue_id": qid, "candidate_id": cid, "models": vmodels, "route": fin.get("route"),
                    "before": {"verdict": old.get("verdict"), "reason_code": old.get("reason_code_final"), "floor": old.get("floor_final")},
                    "after": {"verdict": fin["verdict"], "reason_code": fin["reason_code_final"], "floor": fin["floor_final"],
                              "floor_by_model": fin.get("floor_by_model")},
                    "rubrics": {m: {k: v[m].get(k) for k in ("subject_is_required", "grammatical_subject", "speech_act_is_assertion", "floor",
                                                             "floor_reason", "hazard_flags", "verdict", "reason_code_final", "call_id")} for m in vmodels}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--queue-id")
    ap.add_argument("--candidate-id")
    ap.add_argument("--candidates-file")
    ap.add_argument("--out")
    ap.add_argument("--verifier-models", default="sonnet,opus")
    ap.add_argument("--reason", default="session 5 Task 6: let IDIOM_OR_FORMULA (verifier gate6-v1.2) decide the candidate that motivated it")
    a = ap.parse_args()
    reg = Registry()
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    assert_gate6_scope(reg, queue, print)
    cells = {c["queue_id"]: c for c in open_cells(queue)}
    llm = LLM(a.run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, a.run_id, "cells"), "sonnet", ["sonnet", "opus"], log=print, run_coder=False)
    if a.candidates_file:
        items = json.load(open(a.candidates_file, encoding="utf-8"))
    else:
        items = [{"queue_id": a.queue_id, "candidate_id": a.candidate_id, "models": a.verifier_models.split(","), "reason": a.reason}]
    index, moves = chunk_index(), packets.relocations()      # read once: one run is one view of the store
    done, pending, refused = [], 0, []
    for it in items:
        status, summary = reverify_one(runner, cells, it, index=index, moves=moves)
        if status == "PENDING":
            pending += 1
        elif status == "REFUSED":
            refused.append(summary)
        else:
            done.append(summary)
    if refused:
        print(f"!! {len(refused)} candidate(s) REFUSED (no current chunk carries the phrase): "
              + ", ".join(f"{r['candidate_id']}" for r in refused))
    if pending:
        print(f"== {pending} of {len(items)} candidate(s) have verifier call(s) pending under {prompts.prompt_version('verifier')}")
        return 10
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"done": done, "refused": refused}, fh, ensure_ascii=False, indent=1)
    for d in done:
        print(f"-- {d['queue_id']} {d['candidate_id']}: {d['before']['verdict']}/{d['before']['reason_code']} -> {d['after']['verdict']}/{d['after']['reason_code']} "
              f"at {d['after']['floor']} (floors {d['after']['floor_by_model']}; route {d['route']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
