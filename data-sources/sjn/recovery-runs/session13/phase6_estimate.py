"""Session 13, phase 6: the verifier cost estimate for Track R (repair) and Track B (BSR-BA-04), before any model call.
No model calls, no network. Unit costs are read from every recovery-runs/*/calls.jsonl; cell lists from the session 13 chunk-id
mapping and the live-1 cell states.

  python data-sources/sjn/recovery-runs/session13/phase6_estimate.py      writes session13/phase6-estimate.json"""
import glob
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, ".."))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VOTES = 3            # Codex C1: items read by majority; verdict-differ items 3 replicates (5 only for a stop-triggering item)
CAPS = {"R": 30.0, "B": 30.0}


def unit_costs():
    son, op, loc, cod = [], [], [], []
    for f in glob.glob(os.path.join(RUNS, "*", "calls.jsonl")):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("cost_usd") is None:
                continue
            if r["role"] == "verifier" and str(r.get("prompt_version", "")).startswith("gate6-v1.3") and r["model"] == "sonnet":
                son.append(r["cost_usd"])
            elif r["role"] == "verifier" and r["model"] == "opus":
                op.append(r["cost_usd"])
            elif r["role"] == "locator" and (r.get("meta") or {}).get("branch") == "Baptist":
                loc.append(r["cost_usd"])
            elif r["role"] == "coder":
                cod.append(r["cost_usd"])
    q = lambda xs, p: sorted(xs)[int(len(xs) * p)]
    return {k: {"n": len(v), "mean": round(st.mean(v), 4), "p90": round(q(v, .9), 4), "max": round(max(v), 4)}
            for k, v in (("sonnet_verifier_v1.3", son), ("opus_verifier_all_versions", op), ("baptist_locator", loc), ("coder", cod))}


def main():
    u = unit_costs()
    s_mean, s_p90 = u["sonnet_verifier_v1.3"]["mean"], u["sonnet_verifier_v1.3"]["p90"]
    o_mean, o_p90 = u["opus_verifier_all_versions"]["mean"], u["opus_verifier_all_versions"]["p90"]
    mapping = json.load(open(os.path.join(HERE, "chunk-id-mapping.json"), encoding="utf-8"))
    track_r, never_verified = [], []
    for c in mapping["candidates"]:
        stt = json.load(open(os.path.join(RUNS, "live-1", "cells", f"{c['queue_id']}.json"), encoding="utf-8"))
        v = (stt.get("verifications") or {}).get(c["candidate_id"]) or {}
        models = [m for m in ("sonnet", "opus") if isinstance(v.get(m), dict)]
        rec = {"queue_id": c["queue_id"], "candidate_id": c["candidate_id"], "old_locator": c["old_locator"],
               "new_locator": (c["verbatim_in_new_chunks"] or [None])[0], "stored_verdict": (v.get("final") or {}).get("verdict"),
               "stored_route": (v.get("final") or {}).get("route"), "models": models}
        (track_r if models else never_verified).append(rec)
    r_cells = sorted({x["queue_id"] for x in track_r})
    n_son_r = VOTES * sum("sonnet" in x["models"] for x in track_r)
    n_op_r = VOTES * sum("opus" in x["models"] for x in track_r)
    n_op_r_bound = VOTES * len(r_cells)                             # every Track R cell routed to opus on reject-all
    R = {"cells": r_cells, "candidates": track_r, "not_in_track_never_verified": never_verified,
         "calls_expected": {"sonnet": n_son_r, "opus": n_op_r}, "calls_bound": {"sonnet": n_son_r, "opus": n_op_r_bound},
         "usd_expected": round(n_son_r * s_mean + n_op_r * o_mean, 2), "usd_bound": round(n_son_r * s_p90 + n_op_r_bound * o_p90, 2)}

    bap = [json.load(open(f, encoding="utf-8")) for f in glob.glob(os.path.join(RUNS, "live-1", "cells", "*.json"))]
    bap = sorted((x for x in bap if x.get("branch") == "Baptist"), key=lambda x: x["queue_id"])
    packet = json.load(open(os.path.join(RUNS, "..", "recovery-packets", "baptist.json"), encoding="utf-8"))
    empty = sorted(c["queue_id"] for c in packet["cards"] if not c["candidates"])
    b_cells = [x["queue_id"] for x in bap]
    exp_cands, bound_cands = 20, 3 * len(b_cells)                   # expected ~0.5 per cell (BA-03 gave 1 in 37); bound: the locator cap
    n_son_b, n_son_b_bound = VOTES * exp_cands, VOTES * bound_cands
    n_op_b, n_op_b_bound = VOTES * 3, VOTES * 3 * len(empty)        # reject-all can fire only where no other candidate survives
    loc_exp = round(len(b_cells) * 0.0153, 2)                       # BA-03's 37 locator calls averaged $0.0153 on an 8.8k-character page
    loc_bound = round(len(b_cells) * u["baptist_locator"]["p90"], 2)
    cod_exp, cod_bound = round(exp_cands * u["coder"]["mean"], 2), round(bound_cands * u["coder"]["p90"], 2)
    B = {"cells": b_cells, "empty_cards_now": empty,
         "eligibility": ("all 37 Baptist open cells: the Baptist branch has no consultation ladder (config.CONSULTATION_LADDERS names only "
                         "Eastern Orthodox), BSR-BA-04 is not a fallback-only row (APP CONFIG registry_fallback_only_rows = BSR-AN-05), not a "
                         "witness row, not refused (citation_refusal None), admitted host abc-usa.org; every cell is DONE and consulted "
                         "BA-01..03 only in pass 1. R6-2's three refused Baptist cells (Q-382, Q-390, Q-454) refuse named candidates, not "
                         "the cell. Its 19 chunks (5,703 characters) fit one locator call per cell (coverage FULL, no exhaustion)"),
         "calls_expected": {"locator": len(b_cells), "sonnet_verifier": n_son_b, "opus_verifier": n_op_b, "coder": exp_cands},
         "calls_bound": {"locator": len(b_cells), "sonnet_verifier": n_son_b_bound, "opus_verifier": n_op_b_bound, "coder": bound_cands},
         "verifier_usd_expected": round(n_son_b * s_mean + n_op_b * o_mean, 2),
         "verifier_usd_bound": round(n_son_b_bound * s_p90 + n_op_b_bound * o_p90, 2),
         "all_in_usd_expected": None, "all_in_usd_bound": None}
    B["all_in_usd_expected"] = round(B["verifier_usd_expected"] + loc_exp + cod_exp, 2)
    B["all_in_usd_bound"] = round(B["verifier_usd_bound"] + loc_bound + cod_bound, 2)
    out = {"what": __doc__.split("\n\n")[0], "votes_per_item": VOTES, "verifier_version": "gate6-v1.3", "unit_costs": u, "caps_usd": CAPS,
           "track_R": R, "track_B": B,
           "gate": {"R_expected_share": round(R["usd_expected"] / CAPS["R"], 3), "R_bound_share": round(R["usd_bound"] / CAPS["R"], 3),
                    "B_verifier_expected_share": round(B["verifier_usd_expected"] / CAPS["B"], 3),
                    "B_verifier_bound_share": round(B["verifier_usd_bound"] / CAPS["B"], 3),
                    "B_all_in_bound_share": round(B["all_in_usd_bound"] / CAPS["B"], 3),
                    "rule": "continue only if both estimates <= 80% of their caps"}}
    with open(os.path.join(HERE, "phase6-estimate.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({"unit_costs": u, "R": {k: R[k] for k in ("calls_expected", "calls_bound", "usd_expected", "usd_bound")},
                      "R_cells": len(r_cells), "R_candidates": len(track_r),
                      "B": {k: B[k] for k in ("calls_expected", "calls_bound", "verifier_usd_expected", "verifier_usd_bound",
                                              "all_in_usd_expected", "all_in_usd_bound")}, "gate": out["gate"]}, indent=1))


if __name__ == "__main__":
    main()
