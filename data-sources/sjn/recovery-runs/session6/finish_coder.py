"""Session 6: code the card entries that have no coder proposal — and nothing else (no locator, no exhaustion, no re-routing).

  python data-sources/sjn/recovery-runs/session6/finish_coder.py --count             # no model calls: what is uncoded, and why
  python data-sources/sjn/recovery-runs/session6/finish_coder.py --run               # writes coder jobs (and the 2c sample, see below)
  python scripts/sjn_recovery/api_executor.py --run-id live-1 --role coder ... ; then --run again to ingest

Why not the ordinary loop: re-entering run.py on a finished branch also resumes stopped exhaustion (Q-380: 13 locator batches over
BSR-RP-04), enters exhaustion on branches that ran before it existed (Anglican: crashed on the URL guard at a BSR-AN-05 chunk), and
sends old caveated accepts to the 2c sample (4 Roman Catholic). None of that is in the session's rulings; it was reverted.

Scope: every candidate the current allocation keeps on a card (allocation.kept, after the R6-4 guard) with no stored coder proposal.
Each is labelled JOINED_THIS_SESSION (it reached the card through R6-1 re-verification or an R6-4 freed slot) or BACKLOG (it was
already on the card uncoded, left by an earlier no-call rebuild). The 2c disclosure sample runs ONLY on candidates re-verified this
session (verification record `reverified.reason` starting "session 6") that reach a card as caveated accepts — the ordinary rule for
new verdicts; older caveated accepts are not sampled here."""
import argparse
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_recovery.config import RUNS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates, load_comparators, load_queue, open_cells  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner, caveat_slice_hit  # noqa: E402
from sjn_recovery.allocation import allocate  # noqa: E402

BRANCHES = ["Roman Catholic", "Anglican", "Lutheran", "Reformed / Presbyterian", "Baptist", "Methodist / Wesleyan", "Mennonite / Anabaptist"]


_HEAD_CARDS = {}


def head_kept(qid):
    """The candidates on this cell's card in the packets as committed at HEAD (what the author last saw)."""
    if not _HEAD_CARDS:
        for slug in ("roman-catholic", "anglican", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "mennonite-anabaptist"):
            p = subprocess.run(["git", "show", f"HEAD:data-sources/sjn/recovery-packets/{slug}.json"], capture_output=True, cwd=ROOT)
            for c in json.loads(p.stdout.decode("utf-8"))["cards"]:
                _HEAD_CARDS[c["queue_id"]] = {e["candidate_id"] for e in c["candidates"]}
    return _HEAD_CARDS.get(qid, set())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    reg = Registry()
    preds, comps, queue = load_predicates(reg.wb), load_comparators(reg.wb), load_queue(reg.wb)
    cells = [c for c in open_cells(queue) if c["branch"] in BRANCHES]
    llm = LLM("live-1", backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, comps, os.path.join(RUNS_DIR, "live-1", "cells"), "sonnet", ["sonnet", "opus"], log=print,
                        run_coder=True, exhaust=False)
    rows, pending = [], 0
    for c in cells:
        st = runner.load(c["queue_id"])
        if not st or st.get("phase") != "DONE":
            raise SystemExit(f"{c['queue_id']} is not DONE")
        runner.refinalize(st, c["branch"])
        alloc = allocate(runner.allocation_view(st["survivors"]), runner.pairs(c["branch"]), groups=runner.groups(c["branch"]))
        before = head_kept(c["queue_id"])
        by = {x["candidate_id"]: x for x in st["survivors"]}
        for cid in alloc["kept"]:
            v = st["verifications"].get(cid) or {}
            s6 = str((v.get("reverified") or {}).get("reason") or "").startswith("session 6")
            if a.run and s6 and runner.adjudicator and caveat_slice_hit(v.get(runner.primary)) and not (v.get(runner.adjudicator) or {}).get("status") == "DONE":
                rec = st.setdefault("caveat_sample", {}).get(cid) or runner.sample_decision(c["branch"], st, cid)
                st["caveat_sample"][cid] = rec
                if rec["sampled"]:
                    v["_route"] = "CAVEATED_ACCEPT_SAMPLE"
                    v[runner.adjudicator] = runner.verify(c, by[cid], runner.adjudicator)
                    if v[runner.adjudicator].get("status") == "PENDING":
                        pending += 1
                    else:
                        runner.finalize(v, runner.primary, runner.adjudicator)
            coded = (st.get("coding") or {}).get(cid)
            if coded and coded.get("status") == "DONE":
                continue
            label = "JOINED_THIS_SESSION" if cid not in before else "BACKLOG (on the HEAD card, never coded)"
            rows.append({"branch": c["branch"], "queue_id": c["queue_id"], "candidate_id": cid, "label": label, "reverified_s6": s6})
            if a.run:
                st.setdefault("coding", {})[cid] = runner.code(c, by[cid], runner.final_rubric(st, cid))
                if st["coding"][cid].get("status") == "PENDING":
                    pending += 1
        if a.run:
            st["allocation"] = {k: alloc[k] for k in ("kept", "roles", "english_witness", "dropped", "witness_only", "groups", "slot_order", "parallel_witnesses")}
            st["coder_skipped"] = dict(alloc["dropped"])
            runner.save(st)
    from collections import Counter
    print(f"== uncoded card entries: {len(rows)}; by label {dict(Counter(r['label'] for r in rows))}; by branch {dict(Counter(r['branch'] for r in rows))}")
    for r in rows:
        print(f"   {r['branch'][:12]:12s} {r['queue_id']} {r['candidate_id']:34s} {r['label']}{' (re-verified s6)' if r['reverified_s6'] else ''}")
    out = os.path.join(os.path.dirname(__file__), "finish-coder-items.json")
    json.dump(rows, open(out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    if a.run and pending:
        print(f"== {pending} call(s) pending")
        return 10
    return 0


if __name__ == "__main__":
    sys.exit(main())
