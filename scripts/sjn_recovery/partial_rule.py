"""The hedged-PARTIAL rule (Gate 6 session 6, author ruling R6-2): audit a sample before applying it.

  python scripts/sjn_recovery/partial_rule.py sample  --run-id pr-1 --seed 20260913 --base HEAD      # no model calls: draws the sample
  python scripts/sjn_recovery/partial_rule.py verify  --run-id pr-1                                   # writes sonnet v1.3 jobs (exit 10)
  python scripts/sjn_recovery/api_executor.py --run-id pr-1 --workers 6 --max-cost-usd 1 --key-file <.env>
  python scripts/sjn_recovery/partial_rule.py verify  --run-id pr-1                                   # ingests
  python scripts/sjn_recovery/partial_rule.py report  --run-id pr-1                                   # leak rate, misclassifications
  python scripts/sjn_recovery/partial_rule.py refuse  --cells-run-id live-1                            # 2c: the three Baptist cells
  python scripts/sjn_recovery/partial_rule.py frame   --run-id pr-2 --base packets                     # apply-across frame (if >= 0.5)
  python scripts/sjn_recovery/partial_rule.py apply   --run-id pr-2 --cells-run-id live-1               # write the caps into the cells

THE RULE (R6-2): if the verifier's own floor_reason states that the passage does not assert the predicate, the floor is WORD_ONLY.
PARTIAL is for a passage that asserts the predicate INCOMPLETELY, never for one that asserts a NEIGHBOURING proposition.

Frame. Every CARDED candidate whose final floor is PARTIAL, read from the packets at --base (git HEAD = the session-5 packets
the author's scan counted: 145), minus the five candidates of the three cells refused either way (Q-382, Q-390, Q-454).

Sample. Stratified by branch — 5 from each of the two largest frames (Anglican, Mennonite / Anabaptist: 25), 4 from each other
branch — 30 in all. Within a branch candidates are ordered by sha256("<seed>|<candidate_id>"); the draw goes round by round over
the branches in a fixed order and takes, for each, the first candidate in hash order whose predicate family the sample does
not yet hold, falling back to the first not yet drawn. Deterministic: the seed and the frame reproduce it.

Re-ruling. SONNET ONLY, verifier gate6-v1.3 (prompts.VERIFIER_SYSTEM_V13: line 4 states the rule and adds the companion
line partial_asserts_predicate; PARTIAL with N is capped at WORD_ONLY in code). The candidate is judged afresh on its stored
chunk under the required_subject its card carried (not the session-6 retyping, so R6-1 cannot confound R6-2).

Classes (classify(): read from the rubric LINES, never from a regex over prose): LEAK = lines 1–3 Y and the re-ruled floor is
WORD_ONLY (directly, or a PARTIAL the verifier marked partial_asserts_predicate N), not by the formula cap; FORMULA; REFUSED_LINE_2_3;
HOLDS (PARTIAL); MOVED_UP (FULL); UNPARSEABLE. `control` re-sends each item as an independent gate6-v1.2 replicate (same prompt,
distinct identity) so the report can separate the rule's effect from resampling noise. The report ranks three figures:
A the floor-leak rate (the decision figure), B inclusive of line-2/3 refusals that also floor at WORD_ONLY, C net of the replicate.

The stored rubrics are never overwritten. `apply` / `refuse` record a floor cap on the verification record
(`floor_rulings`), which agents.finalize applies as a lower floor on every rebuild. Nothing writes to the workbook."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, PACKETS_DIR, ROOT  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import prompts, rulings  # noqa: E402

SLUGS = ["roman-catholic", "anglican", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "mennonite-anabaptist"]
QUOTA_LARGE, QUOTA = 5, 4
VERSION = "gate6-v1.3"
RULE_CAP_AUDIT = "R6-2_HEDGED_PARTIAL_AUDIT"
# the hedge shape the author's scan looked for (a regex over floor_reason; the addendum's own pattern was not published, so this
# is a stated reconstruction — it finds 110 of 145 at HEAD against the addendum's 113)
HEDGE = [r"\bdoes not (explicitly |specifically |directly |fully )?(address|assert|state|frame|name|mention|say|affirm|use|speak|attribute|predicate|claim|describe|cover|articulate|define|identify|express|invoke)",
         r"\bnot (explicitly|specifically|directly)\b", r"\bnarrower\b", r"\badjacent\b", r"\bcognate\b"]


def _dir(run_id):
    d = os.path.join(RUNS_DIR, run_id)
    os.makedirs(d, exist_ok=True)
    return d


def load_packet(base, slug):
    if base == "packets":
        with open(os.path.join(PACKETS_DIR, f"{slug}.json"), encoding="utf-8") as fh:
            return json.load(fh)
    p = subprocess.run(["git", "show", f"{base}:data-sources/sjn/recovery-packets/{slug}.json"], capture_output=True, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit(f"git show {base} {slug} failed")
    return json.loads(p.stdout.decode("utf-8"))


def hedged(entry):
    return any(re.search(h, (r.get("floor_reason") or ""), re.I) for r in (entry.get("verifier_rubrics") or {}).values() for h in HEDGE)


def carded_partial(base, exclude=()):
    frame = []
    for slug in SLUGS:
        pk = load_packet(base, slug)
        for c in pk["cards"]:
            for e in c["candidates"]:
                if (e.get("final_verdict") or {}).get("floor_final") == "PARTIAL" and e["candidate_id"] not in exclude:
                    frame.append({"branch": pk["branch"], "queue_id": c["queue_id"], "family_id": c["family_id"], "predicate": c["predicate"],
                                  "required_subject_on_card": c.get("required_subject"), "candidate_id": e["candidate_id"],
                                  "registry_id": e["registry_id"], "phrase": e["phrase"], "hedge_shaped": hedged(e),
                                  "card_size": len(c["candidates"]),
                                  "card_all_partial": all((x.get("final_verdict") or {}).get("floor_final") == "PARTIAL" for x in c["candidates"]),
                                  "stored_floor_reasons": {m: r.get("floor_reason") for m, r in (e.get("verifier_rubrics") or {}).items()},
                                  "stored_floors": (e.get("final_verdict") or {}).get("floor_by_model")})
    return frame


def cmd_sample(a):
    refused = set(rulings.refused_candidates())
    frame = carded_partial(a.base, exclude=refused)
    by_branch = {}
    for x in frame:
        by_branch.setdefault(x["branch"], []).append(x)
    sizes = Counter({b: len(v) for b, v in by_branch.items()})
    large = [b for b, _ in sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))[:2]]
    quota = {b: (QUOTA_LARGE if b in large else QUOTA) for b in by_branch}
    order = sorted(by_branch)
    for b in order:
        by_branch[b].sort(key=lambda x: hashlib.sha256(f"{a.seed}|{x['candidate_id']}".encode()).hexdigest())
    chosen, fams = [], set()
    for _ in range(max(quota.values())):
        for b in order:
            if sum(1 for x in chosen if x["branch"] == b) >= quota[b]:
                continue
            rest = [x for x in by_branch[b] if x not in chosen]
            pick = next((x for x in rest if x["family_id"] not in fams), rest[0] if rest else None)
            if pick:
                chosen.append(pick); fams.add(pick["family_id"])
    for n, x in enumerate(chosen, 1):
        x["sample_id"] = f"PR-{n:02d}"
    out = {"run_id": a.run_id, "drawn_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": a.seed, "base": a.base,
           "frame": {"carded_partial_at_base": len(frame) + sum(1 for b in SLUGS for c in load_packet(a.base, b)["cards"] for e in c["candidates"]
                                                                  if e["candidate_id"] in refused and (e.get("final_verdict") or {}).get("floor_final") == "PARTIAL"),
                     "excluded_refused_either_way": sorted(refused), "frame_size": len(frame), "by_branch": dict(sizes),
                     "hedge_shaped_in_frame": sum(1 for x in frame if x["hedge_shaped"])},
           "quota": quota, "families_in_sample": len(fams), "items": chosen}
    with open(os.path.join(_dir(a.run_id), "sample.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"== sample {a.run_id}: seed {a.seed}; frame {len(frame)} (by branch {dict(sizes)}); quota {quota}; {len(chosen)} drawn, "
          f"{len(fams)} families; hedge-shaped {sum(1 for x in chosen if x['hedge_shaped'])} of {len(chosen)}")
    for x in chosen:
        print(f"   {x['sample_id']} {x['branch'][:12]:12s} {x['queue_id']} {x['predicate'][:26]:26s} {x['registry_id']} hedge={'Y' if x['hedge_shaped'] else 'N'} \"{x['phrase']}\"")
    return 0


def _runner(run_id, cells_run_id="live-1"):
    prompts.set_verifier_version(VERSION)
    reg = Registry()
    preds = load_predicates(reg.wb)
    llm = LLM(run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, {}, os.path.join(RUNS_DIR, cells_run_id, "cells"), "sonnet", ["sonnet"], log=print, run_coder=False)
    return reg, preds, runner


def _stored_candidate(runner, qid, cid):
    st = runner.load(qid)
    return st, next(c for p in st["passes"].values() for c in p.get("candidates", []) if c["candidate_id"] == cid)


def cmd_verify(a):
    d = _dir(a.run_id)
    sample = json.load(open(os.path.join(d, a.items_file or "sample.json"), encoding="utf-8"))
    reg, preds, runner = _runner(a.run_id, a.cells_run_id)
    res_path = os.path.join(d, "results.json")
    results = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {}
    pending = 0
    for it in sample["items"]:
        st, cand = _stored_candidate(runner, it["queue_id"], it["candidate_id"])
        pred = dict(preds[it["family_id"]])
        if it.get("required_subject_on_card"):
            pred["subject_scope"] = it["required_subject_on_card"]          # isolate R6-2 from the R6-1 retyping
        runner.predicates = dict(runner.predicates, **{it["family_id"]: pred})
        r = results.get(it["candidate_id"])
        if not r or r.get("status") != "DONE":
            r = runner.verify({"queue_id": it["queue_id"], "family_id": it["family_id"], "branch": it["branch"]}, cand, "sonnet")
            results[it["candidate_id"]] = r
        if r.get("status") == "PENDING":
            pending += 1
    with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    if pending:
        print(f"== {a.run_id}: {pending} sonnet verifier call(s) pending under {VERSION}")
        return 10
    print(f"== {a.run_id}: all {len(sample['items'])} re-ruled under {VERSION}")
    return 0


def classify(r):
    """Mechanical, from the rubric LINES — never from a regex over the prose (the instrument the audit exists to replace):
      UNPARSEABLE     the reply has no floor line
      LEAK            lines 1–3 are Y and the re-ruled floor is WORD_ONLY (the verifier floored it directly, or capped a PARTIAL it
                      marked partial_asserts_predicate N) — not by the IDIOM_OR_FORMULA cap
      FORMULA         WORD_ONLY by the IDIOM_OR_FORMULA cap, lines 1–3 Y
      REFUSED_LINE_2_3 subject or speech act N (floor recorded beside it; a refusal, but not on the floor)
      HOLDS           PARTIAL, partial_asserts_predicate Y (or not N)
      MOVED_UP        FULL"""
    floor = r.get("floor")
    if r.get("status") != "DONE" or floor not in ("FULL", "PARTIAL", "WORD_ONLY"):
        return "UNPARSEABLE"
    lines_ok = all(str(r.get(k)).upper() == "Y" for k in ("phrase_verbatim", "subject_is_required", "speech_act_is_assertion"))
    if not lines_ok:
        return "REFUSED_LINE_2_3"
    if floor == "WORD_ONLY":
        return "FORMULA" if r.get("floor_capped_by") == "IDIOM_OR_FORMULA" else "LEAK"
    return "MOVED_UP" if floor == "FULL" else "HOLDS"


class _ReplicateLLM(LLM):
    """The same call re-sent as an independent replicate: the prompt is byte-identical, only the identity carries
    `attempt=100+` (llm.call_id), so the stored answer is not served back."""

    def call_id(self, role, system, user, model=None, attempt=0):
        return super().call_id(role, system, user, model, attempt + 100)


def cmd_control(a):
    """A fresh gate6-v1.2 sonnet replicate of the same items: what the CURRENT verifier does on a second draw, without the rule."""
    d = _dir(a.run_id)
    sample = json.load(open(os.path.join(d, "sample.json"), encoding="utf-8"))
    prompts.set_verifier_version("gate6-v1.2")
    reg = Registry()
    preds = load_predicates(reg.wb)
    llm = _ReplicateLLM(a.run_id, backend="batch", model="sonnet", log=print)
    runner = CellRunner(llm, reg, preds, {}, os.path.join(RUNS_DIR, a.cells_run_id, "cells"), "sonnet", ["sonnet"], log=print, run_coder=False)
    res_path = os.path.join(d, "control-v12.json")
    results = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {}
    pending = 0
    for it in sample["items"]:
        st, cand = _stored_candidate(runner, it["queue_id"], it["candidate_id"])
        pred = dict(preds[it["family_id"]])
        if it.get("required_subject_on_card"):
            pred["subject_scope"] = it["required_subject_on_card"]
        runner.predicates = dict(runner.predicates, **{it["family_id"]: pred})
        r = results.get(it["candidate_id"])
        if not r or r.get("status") != "DONE":
            r = runner.verify({"queue_id": it["queue_id"], "family_id": it["family_id"], "branch": it["branch"]}, cand, "sonnet")
            results[it["candidate_id"]] = r
        if r.get("status") == "PENDING":
            pending += 1
    with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    print(f"== {a.run_id} control: {pending} v1.2 replicate call(s) pending" if pending else f"== {a.run_id} control: all answered")
    return 10 if pending else 0


def cmd_report(a):
    d = _dir(a.run_id)
    sample = json.load(open(os.path.join(d, "sample.json"), encoding="utf-8"))
    results = json.load(open(os.path.join(d, "results.json"), encoding="utf-8"))
    ctl_path = os.path.join(d, "control-v12.json")
    control = json.load(open(ctl_path, encoding="utf-8")) if os.path.exists(ctl_path) else {}
    r61 = set(rulings.required_subjects())
    rows = []
    for it in sample["items"]:
        r = results[it["candidate_id"]]
        cls = classify(r)
        c = control.get(it["candidate_id"]) or {}
        ccls = classify(c) if c else None
        rows.append({"sample_id": it["sample_id"], "branch": it["branch"], "queue_id": it["queue_id"], "predicate": it["predicate"],
                     "family_retyped_by_R6_1": it["family_id"] in r61,
                     "candidate_id": it["candidate_id"], "registry_id": it["registry_id"], "phrase": it["phrase"],
                     "hedge_shaped_stored_reason": it["hedge_shaped"], "card_all_partial": it["card_all_partial"], "card_size": it["card_size"],
                     "class": cls, "leak": cls == "LEAK", "control_v12_class": ccls,
                     "rule_effect": cls == "LEAK" and ccls in ("HOLDS", "MOVED_UP"),
                     "regex_misclassified": ("FALSE_POSITIVE (hedge-shaped, holds)" if it["hedge_shaped"] and cls != "LEAK" else
                                             "FALSE_NEGATIVE (not hedge-shaped, leaks)" if (not it["hedge_shaped"]) and cls == "LEAK" else None),
                     "v13": {k: r.get(k) for k in ("floor", "floor_model", "floor_capped_by", "partial_asserts_predicate", "floor_reason",
                                                 "grammatical_subject", "subject_is_required", "speech_act_is_assertion", "hazard_flags", "verdict",
                                                 "reason_code_final", "call_id", "attempt")},
                     "control_v12": {k: c.get(k) for k in ("floor", "floor_reason", "subject_is_required", "verdict", "reason_code_final", "call_id")},
                     "stored_floor_reasons": it["stored_floor_reasons"], "stored_floors": it["stored_floors"]})
    n = len(rows)
    leaks = [x for x in rows if x["leak"]]
    hed = [x for x in rows if x["hedge_shaped_stored_reason"]]
    inclusive = [x for x in rows if x["leak"] or (x["class"] == "REFUSED_LINE_2_3" and not x["family_retyped_by_R6_1"]
                                                  and (x["v13"]["floor"] == "WORD_ONLY" or str(x["v13"]["partial_asserts_predicate"]).upper() == "N"))]
    net = [x for x in rows if x["rule_effect"]]
    summary = {"run_id": a.run_id, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": sample["seed"], "verifier": f"sonnet only, {VERSION}",
               "sample": n, "leaks": len(leaks), "leak_rate": round(len(leaks) / n, 3) if n else None,
               "figures_ranked": [
                   {"figure": "A_floor_leak", "count": len(leaks), "rate": round(len(leaks) / n, 3),
                    "definition": "lines 1–3 Y and the v1.3 re-ruling floors the candidate at WORD_ONLY (not by the formula cap)",
                    "weakness": "one draw of one model: counts resampling noise as leak; the control below measures that noise"},
                   {"figure": "B_inclusive", "count": len(inclusive), "rate": round(len(inclusive) / n, 3),
                    "definition": "A plus refusals on subject/speech act whose v1.3 floor is also WORD_ONLY (or PARTIAL marked N), outside the five R6-1 families",
                    "weakness": "mixes a line-2 refusal into a floor-rule rate; those candidates would fall for their subject line, not under R6-2"},
                   {"figure": "C_rule_effect_net_of_noise", "count": len(net), "rate": round(len(net) / n, 3),
                    "definition": "A, and a fresh gate6-v1.2 replicate of the same call (no rule) still accepts at PARTIAL or FULL",
                    "weakness": "one replicate per item: an item near the boundary can land either side on either draw"}],
               "control_v12_classes": dict(Counter(x["control_v12_class"] for x in rows)),
               "classes": dict(Counter(x["class"] for x in rows)),
               "by_branch": {b: {"n": sum(1 for x in rows if x["branch"] == b), "leaks": sum(1 for x in rows if x["branch"] == b and x["leak"])}
                             for b in sorted({x["branch"] for x in rows})},
               "regex": {"hedge_shaped_in_sample": len(hed), "hedge_shaped_and_leak": sum(1 for x in hed if x["leak"]),
                         "hedge_shaped_but_holds_FALSE_POSITIVE": [x["sample_id"] for x in hed if not x["leak"]],
                         "not_hedge_shaped": n - len(hed), "not_hedge_shaped_but_leak_FALSE_NEGATIVE": [x["sample_id"] for x in rows if not x["hedge_shaped_stored_reason"] and x["leak"]],
                         "precision": round(sum(1 for x in hed if x["leak"]) / len(hed), 3) if hed else None,
                         "recall": round(sum(1 for x in hed if x["leak"]) / len(leaks), 3) if leaks else None},
               "frame": sample["frame"],
               "estimate_frame_leaks": {"stratified": round(sum(sample["frame"]["by_branch"][b] * (v["leaks"] / v["n"]) for b, v in
                                                                 {b: {"n": sum(1 for x in rows if x["branch"] == b), "leaks": sum(1 for x in rows if x["branch"] == b and x["leak"])}
                                                                  for b in sample["frame"]["by_branch"]}.items() if v["n"]), 1)},
               "decision_rule": "leak rate >= 0.5: apply the rule across all seven branches; below 0.5: apply to nothing but the three refused Baptist cells",
               "items": rows}
    summary["decision"] = "APPLY_ACROSS_SEVEN_BRANCHES" if summary["leak_rate"] is not None and summary["leak_rate"] >= 0.5 else "REFUSED_CELLS_ONLY"
    with open(os.path.join(d, "report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "items"}, ensure_ascii=False, indent=1))
    for x in rows:
        print(f"   {x['sample_id']} {x['branch'][:10]:10s} {x['queue_id']} {x['predicate'][:24]:24s} hedge={'Y' if x['hedge_shaped_stored_reason'] else 'N'} "
              f"v1.3 {x['class']:17s} pap={x['v13']['partial_asserts_predicate']!s:4s} v1.2-replicate {x['control_v12_class']!s:17s} "
              f"{'RULE' if x['rule_effect'] else '    '} \"{x['phrase'][:60]}\"\n        v1.3: {(x['v13']['floor_reason'] or '')[:230]}"
              f"\n        v1.2r: {x['control_v12']['floor']} {(x['control_v12']['floor_reason'] or '')[:200]}")
    return 0


def _add_cap(v, rec):
    caps = v.setdefault("floor_rulings", [])
    if not any(c.get("by") == rec["by"] for c in caps):
        caps.append(rec)


def cmd_refuse(a):
    """2c: Q-382, Q-390 and Q-454 refused either way — a WORD_ONLY floor cap on every candidate the ruling names."""
    state_dir = os.path.join(RUNS_DIR, a.cells_run_id, "cells")
    r = rulings.load()
    ru = r["rulings"]["R6-2_hedged_partial"]
    done = []
    for cid, info in rulings.refused_candidates(r).items():
        p = os.path.join(state_dir, f"{info['queue_id']}.json")
        st = json.load(open(p, encoding="utf-8"))
        v = st["verifications"][cid]
        _add_cap(v, {"by": rulings.AUTHOR_RULING_FLOOR_CAP, "floor_cap": "WORD_ONLY", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "rule": ru["rule"], "note": ru["refused_cells"]["note"], "source": r.get("_path")})
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
        done.append((info["queue_id"], cid))
    print(f"== refused {len(done)} candidate(s) by {rulings.AUTHOR_RULING_FLOOR_CAP}: {done}")
    return 0


def cmd_frame(a):
    """The apply-across frame: every carded PARTIAL at --base not already re-ruled in --sample-run-id and not refused."""
    refused = set(rulings.refused_candidates())
    ruled = set(json.load(open(os.path.join(RUNS_DIR, a.sample_run_id, "results.json"), encoding="utf-8"))) if a.sample_run_id else set()
    frame = [dict(x, sample_id=f"PA-{n:03d}") for n, x in enumerate((x for x in carded_partial(a.base, exclude=refused) if x["candidate_id"] not in ruled), 1)]
    with open(os.path.join(_dir(a.run_id), "sample.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"run_id": a.run_id, "seed": None, "base": a.base, "frame": {"frame_size": len(frame)}, "items": frame}, fh, ensure_ascii=False, indent=1)
    print(f"== apply frame {a.run_id}: {len(frame)} carded PARTIAL candidate(s) not yet re-ruled")
    return 0


def cmd_apply(a):
    """Write a WORD_ONLY floor cap (R6-2 audit) onto every re-ruled candidate classed LEAK, in every --run-id given."""
    state_dir = os.path.join(RUNS_DIR, a.cells_run_id, "cells")
    n = 0
    for rid in a.run_id.split(","):
        d = os.path.join(RUNS_DIR, rid)
        sample = json.load(open(os.path.join(d, "sample.json"), encoding="utf-8"))
        results = json.load(open(os.path.join(d, "results.json"), encoding="utf-8"))
        for it in sample["items"]:
            r = results[it["candidate_id"]]
            if classify(r) != "LEAK":
                continue
            p = os.path.join(state_dir, f"{it['queue_id']}.json")
            st = json.load(open(p, encoding="utf-8"))
            _add_cap(st["verifications"][it["candidate_id"]],
                     {"by": RULE_CAP_AUDIT, "floor_cap": "WORD_ONLY", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "audit_run": rid, "rubric": {k: r.get(k) for k in ("model", "call_id", "prompt_version", "floor", "floor_model", "floor_capped_by",
                                                                          "partial_asserts_predicate", "floor_reason", "verdict")}})
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(st, fh, ensure_ascii=False, indent=1)
            n += 1
    print(f"== applied the R6-2 cap to {n} candidate(s)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--run-id", required=True); s.add_argument("--seed", type=int, default=20260913); s.add_argument("--base", default="HEAD")
    v = sub.add_parser("verify"); v.add_argument("--run-id", required=True); v.add_argument("--cells-run-id", default="live-1"); v.add_argument("--items-file")
    r = sub.add_parser("report"); r.add_argument("--run-id", required=True)
    f = sub.add_parser("refuse"); f.add_argument("--cells-run-id", default="live-1")
    fr = sub.add_parser("frame"); fr.add_argument("--run-id", required=True); fr.add_argument("--base", default="packets"); fr.add_argument("--sample-run-id")
    c = sub.add_parser("control"); c.add_argument("--run-id", required=True); c.add_argument("--cells-run-id", default="live-1")
    p = sub.add_parser("apply"); p.add_argument("--run-id", required=True); p.add_argument("--cells-run-id", default="live-1")
    a = ap.parse_args()
    return {"sample": cmd_sample, "verify": cmd_verify, "report": cmd_report, "refuse": cmd_refuse, "frame": cmd_frame, "apply": cmd_apply, "control": cmd_control}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
