"""Session 14, phase 5: the phase 7 cost estimate after the AN-04 / AN-06 repair, at THREE gate6-v1.3 calls per
candidate (R6-54 / Codex C1(a)). No model calls, no network.

The session 13 method (session13/phase6_estimate.py) is kept and re-run, because a like-for-like figure beside its
predecessor is worth more than a better one alone. A second, tighter instrument is added: the actual verifier payload
for each Track R candidate is BUILT and measured, so the estimate prices the calls this run will really make rather
than the average of every v1.3 call ever made. That matters here — the repair changed the chunks the verifier sees:
the Quicunque Vult goes from a 2,720-character run-on chunk to the whole 3,633-character creed, and Compendium Q.533's
49,667-character chunk becomes a 466-character Q.586.

The Track R cell set is RECOMPUTED, not reused: it is derived from the composed chunk-id mapping (session 13's and
session 14's, chained) against the live-1 cell states.

  python data-sources/sjn/recovery-runs/session14/phase5_estimate.py     writes session14/phase5-estimate.json
"""
import glob
import json
import os
import statistics as stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RUNS, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery import packets, prompts, store  # noqa: E402
from sjn_recovery.agents import VOTES_PER_CANDIDATE  # noqa: E402
from sjn_recovery.llm import LIST_PRICES  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates  # noqa: E402

CAPS = {"R": 30.0, "B": 30.0}
CHARS_PER_TOKEN = 3.6                      # llm.py's own estimator, kept so the two instruments are comparable
SONNET, OPUS = "claude-sonnet-5", "claude-opus-5"


def unit_costs():
    """Instrument 1 (session 13's): the measured per-call cost of every logged call, by role and model."""
    son, op, loc, cod, son_out = [], [], [], [], []
    for f in glob.glob(os.path.join(RUNS, "*", "calls.jsonl")):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("cost_usd") is None:
                continue
            if r["role"] == "verifier" and str(r.get("prompt_version", "")).startswith("gate6-v1.3") and r["model"] == "sonnet":
                son.append(r["cost_usd"])
                if (r.get("usage") or {}).get("output_tokens"):
                    son_out.append(r["usage"]["output_tokens"])
            elif r["role"] == "verifier" and r["model"] == "opus":
                op.append(r["cost_usd"])
                if (r.get("usage") or {}).get("output_tokens"):
                    son_out.append(r["usage"]["output_tokens"]) if False else None
            elif r["role"] == "locator" and (r.get("meta") or {}).get("branch") == "Baptist":
                loc.append(r["cost_usd"])
            elif r["role"] == "coder":
                cod.append(r["cost_usd"])
    q = lambda xs, p: sorted(xs)[min(int(len(xs) * p), len(xs) - 1)]
    out = {k: {"n": len(v), "mean": round(stat.mean(v), 4), "p90": round(q(v, .9), 4), "max": round(max(v), 4)}
           for k, v in (("sonnet_verifier_v1.3", son), ("opus_verifier_all_versions", op),
                        ("baptist_locator", loc), ("coder", cod)) if v}
    out["verifier_output_tokens"] = {"n": len(son_out), "mean": round(stat.mean(son_out)) if son_out else None,
                                     "p90": q(son_out, .9) if son_out else None}
    return out


def price(model_id, in_tok, out_tok):
    pin, pout = LIST_PRICES[model_id]
    return (in_tok * pin + out_tok * pout) / 1e6


def track_r_candidates():
    """RECOMPUTED: every stored verdict whose chunk the repair changed, re-pointed at the chunk the store holds now."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("rv", os.path.join(ROOT, "scripts", "sjn_recovery", "reverify.py"))
    rv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rv)
    index, moves = rv.chunk_index(), packets.relocations()
    out, refused = [], []
    for f in sorted(glob.glob(os.path.join(RUNS, "live-1", "cells", "*.json"))):
        st = json.load(open(f, encoding="utf-8"))
        for pk, p in (st.get("passes") or {}).items():
            for cand in p.get("candidates", []):
                cid = cand["candidate_id"]
                v = (st.get("verifications") or {}).get(cid) or {}
                models = [m for m in ("sonnet", "opus") if isinstance(v.get(m), dict) and v[m].get("status") == "DONE"]
                if not models:
                    continue
                now, rep, problem = rv.repoint(cand, index, moves)
                if problem:
                    refused.append({"queue_id": st["queue_id"], "candidate_id": cid, "why": problem})
                    continue
                if not rep:
                    continue                       # the chunk the verifier judged is still the chunk the store holds
                fin = v.get("final") or {}
                out.append({"queue_id": st["queue_id"], "candidate_id": cid, "branch": st.get("branch"),
                            "family_id": st.get("family_id"), "models": models, "phrase": cand["phrase"],
                            "stored_verdict": fin.get("verdict"), "stored_route": fin.get("route"),
                            "stored_instrument": {m: v[m].get("prompt_version") for m in models},
                            "registry_id_at_run": rep["registry_id_at_run"], "registry_id_now": rep["registry_id_now"],
                            "locator_now": rep["locator_now"], "cross_row": rep["cross_row"],
                            "chunk_chars_at_run": rep["chars_at_run"], "chunk_chars_now": rep["chars_now"],
                            "_cand_now": now})
    return out, refused


def payload_tokens(reg, preds, rec):
    """Instrument 2: the ACTUAL verifier payload this run will send for one candidate, in tokens."""
    pred = preds[rec["family_id"]]
    cand = rec["_cand_now"]
    user = prompts.verifier_user(pred, cand, {"registry_id": cand["registry_id"], "locator": cand["locator"],
                                              "text": cand["chunk_text"]})
    system = prompts.verifier_system(pred)
    return int((len(system) + len(user)) / CHARS_PER_TOKEN)


def main():
    u = unit_costs()
    s_mean, s_p90 = u["sonnet_verifier_v1.3"]["mean"], u["sonnet_verifier_v1.3"]["p90"]
    o_mean, o_p90 = u["opus_verifier_all_versions"]["mean"], u["opus_verifier_all_versions"]["p90"]
    out_mean = u["verifier_output_tokens"]["mean"] or 700
    out_p90 = u["verifier_output_tokens"]["p90"] or 1200

    reg = Registry()
    preds = load_predicates(reg.wb)
    cands, refused = track_r_candidates()
    cells = sorted({c["queue_id"] for c in cands})
    for c in cands:
        c["payload_tokens"] = payload_tokens(reg, preds, c)
        c.pop("_cand_now", None)

    n_son = VOTES_PER_CANDIDATE * sum(1 for c in cands if "sonnet" in c["models"])
    n_op = VOTES_PER_CANDIDATE * sum(1 for c in cands if "opus" in c["models"])
    n_op_bound = VOTES_PER_CANDIDATE * len(cands)          # every candidate routed to opus on a reject-all cell

    # instrument 1: the session 13 method, at three calls per candidate
    r_exp_1 = n_son * s_mean + n_op * o_mean
    r_bound_1 = n_son * s_p90 + n_op_bound * o_p90
    # instrument 2: the real payloads
    tok = sum(c["payload_tokens"] for c in cands)
    tok_son = sum(c["payload_tokens"] for c in cands if "sonnet" in c["models"])
    tok_op = sum(c["payload_tokens"] for c in cands if "opus" in c["models"])
    r_exp_2 = VOTES_PER_CANDIDATE * (price(SONNET, tok_son, out_mean * sum(1 for c in cands if "sonnet" in c["models"]))
                                     + price(OPUS, tok_op, out_mean * sum(1 for c in cands if "opus" in c["models"])))
    r_bound_2 = VOTES_PER_CANDIDATE * (price(SONNET, tok_son, out_p90 * sum(1 for c in cands if "sonnet" in c["models"]))
                                       + price(OPUS, tok, out_p90 * len(cands)))
    coder_exp = u["coder"]["mean"]                          # Q-179 LU-02-2: the one coder call the session 13 report names

    R = {"cells": cells, "n_candidates": len(cands), "refused": refused,
         "recomputed_from": "the composed chunk-id mapping (session 13 + session 14) against the live-1 cell states",
         "candidates": cands,
         "coder_calls": {"n": 1, "why": "Q-179 LU-02-2 was newly seated by R6-44 and has no coder proposal "
                                        "(session 13 report section 4.3)", "usd": round(coder_exp, 4)},
         "calls_expected": {"sonnet": n_son, "opus": n_op, "coder": 1},
         "calls_bound": {"sonnet": n_son, "opus": n_op_bound, "coder": 1},
         "instrument_1_measured_call_means": {"usd_expected": round(r_exp_1, 2), "usd_bound": round(r_bound_1, 2)},
         "instrument_2_actual_payloads": {"input_tokens_per_draw": tok, "usd_expected": round(r_exp_2, 2),
                                          "usd_bound": round(r_bound_2, 2)},
         "usd_expected": round(max(r_exp_1, r_exp_2) + coder_exp, 2),
         "usd_bound": round(max(r_bound_1, r_bound_2) + coder_exp, 2),
         "verifier_only_expected": round(max(r_exp_1, r_exp_2), 2),
         "verifier_only_bound": round(max(r_bound_1, r_bound_2), 2)}

    # ---- Track B: the BSR-BA-04 row across its cells (unchanged by the repair; re-derived, not copied)
    bap = [json.load(open(f, encoding="utf-8")) for f in glob.glob(os.path.join(RUNS, "live-1", "cells", "*.json"))]
    b_cells = sorted(x["queue_id"] for x in bap if x.get("branch") == "Baptist")
    packet = json.load(open(os.path.join(RUNS, "..", "recovery-packets", "baptist.json"), encoding="utf-8"))
    empty = sorted(c["queue_id"] for c in packet["cards"] if not c["candidates"])
    ba04 = store.load_chunks("BSR-BA-04")
    exp_cands, bound_cands = 20, 3 * len(b_cells)
    n_son_b, n_son_b_bound = VOTES_PER_CANDIDATE * exp_cands, VOTES_PER_CANDIDATE * bound_cands
    n_op_b, n_op_b_bound = VOTES_PER_CANDIDATE * 3, VOTES_PER_CANDIDATE * 3 * len(empty)
    loc_exp = round(len(b_cells) * 0.0153, 2)
    loc_bound = round(len(b_cells) * u["baptist_locator"]["p90"], 2)
    cod_exp, cod_bound = round(exp_cands * u["coder"]["mean"], 2), round(bound_cands * u["coder"]["p90"], 2)
    B = {"cells": b_cells, "empty_cards_now": empty, "ba04_chunks": len(ba04),
         "ba04_chars": sum(len(c["text"]) for c in ba04),
         "assumption": "about 0.5 candidates per cell (BSR-BA-03's similar page yielded 1 in 37); the bound is the "
                       "locator cap, 3 candidates per cell",
         "calls_expected": {"locator": len(b_cells), "sonnet_verifier": n_son_b, "opus_verifier": n_op_b, "coder": exp_cands},
         "calls_bound": {"locator": len(b_cells), "sonnet_verifier": n_son_b_bound, "opus_verifier": n_op_b_bound, "coder": bound_cands},
         "verifier_only_expected": round(n_son_b * s_mean + n_op_b * o_mean, 2),
         "verifier_only_bound": round(n_son_b_bound * s_p90 + n_op_b_bound * o_p90, 2),
         "all_in_expected": round(n_son_b * s_mean + n_op_b * o_mean + loc_exp + cod_exp, 2),
         "all_in_bound": round(n_son_b_bound * s_p90 + n_op_b_bound * o_p90 + loc_bound + cod_bound, 2)}

    gate = {}
    for name, track, keys in (("R", R, ("verifier_only_expected", "verifier_only_bound", "usd_expected", "usd_bound")),
                              ("B", B, ("verifier_only_expected", "verifier_only_bound", "all_in_expected", "all_in_bound"))):
        gate[name] = {k: {"usd": track[k], "share_of_cap": round(track[k] / CAPS[name], 3),
                          "at_or_under_80pct": track[k] <= 0.8 * CAPS[name]} for k in keys}

    out = {"what": __doc__.split("\n\n")[0], "votes_per_candidate": VOTES_PER_CANDIDATE, "caps_usd": CAPS,
           "verifier_version": prompts.prompt_version("verifier"), "unit_costs": u,
           "track_R": R, "track_B": B, "gate": gate}
    with open(os.path.join(HERE, "phase5-estimate.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({"track_R": {k: R[k] for k in ("cells", "n_candidates", "calls_expected", "calls_bound",
                                                    "instrument_1_measured_call_means", "instrument_2_actual_payloads",
                                                    "verifier_only_expected", "verifier_only_bound",
                                                    "usd_expected", "usd_bound")},
                      "track_B": {k: B[k] for k in ("calls_expected", "calls_bound", "verifier_only_expected",
                                                    "verifier_only_bound", "all_in_expected", "all_in_bound")},
                      "gate": gate}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
