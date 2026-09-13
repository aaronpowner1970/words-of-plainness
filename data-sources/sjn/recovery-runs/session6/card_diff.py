"""Session 6: card-by-card diff of the seven packets between two snapshots (no model calls).

  python data-sources/sjn/recovery-runs/session6/card_diff.py --before git:HEAD --after packets --label r4 --out <json>
  python data-sources/sjn/recovery-runs/session6/card_diff.py --before dir:<snapshot dir> --after packets --label r1 --out <json>

Per card: filled/empty before and after, the kept candidate ids, candidates that joined or left the card (with registry
row, phrase, final floor/verdict, and — for a leaver — why: verifier verdict, same-text guard, cap), lead changes, the
REVIEWED offer, and R6-4 parallel witnesses (seated id, parallel id, row, rule)."""
import argparse
import glob
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
PK = os.path.join(ROOT, "data-sources", "sjn", "recovery-packets")
SLUGS = ["roman-catholic", "anglican", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "mennonite-anabaptist"]


def load(spec, slug):
    kind, _, where = spec.partition(":")
    if spec == "packets":
        path = os.path.join(PK, f"{slug}.json")
        return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    if kind == "git":
        p = subprocess.run(["git", "show", f"{where}:data-sources/sjn/recovery-packets/{slug}.json"], capture_output=True, cwd=ROOT)
        return json.loads(p.stdout.decode("utf-8")) if p.returncode == 0 else None
    if kind == "dir":
        path = os.path.join(where, f"{slug}.json")
        return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    raise SystemExit(f"bad snapshot spec {spec}")


def entry_brief(e):
    fv = e.get("final_verdict") or {}
    return {"candidate_id": e.get("candidate_id"), "registry_id": e.get("registry_id"), "speaks_for_group": e.get("speaks_for_group"),
            "phrase": e.get("phrase"), "verdict": fv.get("verdict"), "floor_final": fv.get("floor_final")}


def all_entries(card):
    out = {}
    for e in card.get("candidates") or []:
        out[e["candidate_id"]] = ("CARD", e)
        for w in e.get("same_text_parallel_witnesses") or []:
            out[w["candidate_id"]] = ("PARALLEL_WITNESS_OF " + e["candidate_id"], w)
    for r in card.get("rejections") or []:
        if r.get("candidate_id"):
            out.setdefault(r["candidate_id"], (f"REJECTION:{r.get('stage')}:{r.get('reason_code') or (r.get('dropped_reason') or '')[:80]}", r))
    return out


def diff_branch(b, a):
    cards_b = {c["queue_id"]: c for c in b["cards"]}
    out = []
    for ca in a["cards"]:
        cb = cards_b.get(ca["queue_id"])
        kb = [e["candidate_id"] for e in (cb or {}).get("candidates") or []]
        ka = [e["candidate_id"] for e in ca.get("candidates") or []]
        pw = [{"seated": e["candidate_id"], "parallel": w["candidate_id"], "registry_id": w["registry_id"], "rule": w.get("rule"), "phrase": w.get("phrase")}
              for e in ca.get("candidates") or [] for w in e.get("same_text_parallel_witnesses") or []]
        ob = ((cb or {}).get("empty_result_option") or {}).get("offered")
        oa = (ca.get("empty_result_option") or {}).get("offered")
        if kb == ka and not pw and ob == oa and (cb or {}).get("required_subject") == ca.get("required_subject"):
            continue
        ea, eb = all_entries(ca), all_entries(cb or {"candidates": [], "rejections": []})
        joined = [dict(entry_brief(ea[i][1]), before=(eb.get(i, ("NOT PRESENT",))[0])) for i in ka if i not in kb]
        left = [dict(entry_brief(eb[i][1]), now=(ea.get(i, ("NOT PRESENT",))[0])) for i in kb if i not in ka]
        out.append({"queue_id": ca["queue_id"], "predicate": ca["predicate"],
                    "state": f"{'FILLED' if kb else 'EMPTY'} -> {'FILLED' if ka else 'EMPTY'}",
                    "lead": [kb[0] if kb else None, ka[0] if ka else None], "kept_before": kb, "kept_after": ka,
                    "joined": joined, "left": left, "parallel_witnesses": pw,
                    "reviewed_offered": [ob, oa], "required_subject_changed": (cb or {}).get("required_subject") != ca.get("required_subject")})
    head = {k: [b.get(k), a.get(k)] for k in ("cells_with_candidates", "cells_empty", "cells_empty_reviewed_offered", "cells_empty_review_incomplete",
                                             "cells_all_rejected", "rejections_kept")}
    return {"branch": a["branch"], "header": head, "cards_changed": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", default="packets")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {"label": a.label, "before": a.before, "after": a.after, "branches": []}
    for slug in SLUGS:
        b, af = load(a.before, slug), load(a.after, slug)
        if not (b and af):
            continue
        d = diff_branch(b, af)
        res["branches"].append(d)
        moved = [c for c in d["cards_changed"] if c["kept_before"] != c["kept_after"] or c["parallel_witnesses"] or c["reviewed_offered"][0] != c["reviewed_offered"][1]]
        print(f"== {d['branch']}: {d['header']}; cards with slot/offer/parallel changes {len(moved)}")
        for c in moved:
            print(f"   {c['queue_id']} {c['predicate']}: {c['state']} kept {c['kept_before']} -> {c['kept_after']} offered {c['reviewed_offered']}")
            for j in c["joined"]:
                print(f"      + {j['candidate_id']} [{j['registry_id']} {j['floor_final']}] \"{j['phrase']}\" (was {j['before'][:70]})")
            for l in c["left"]:
                print(f"      - {l['candidate_id']} [{l['registry_id']} {l['floor_final']}] \"{l['phrase']}\" (now {l['now'][:90]})")
            for p in c["parallel_witnesses"]:
                print(f"      = parallel {p['parallel']} [{p['registry_id']} {p['rule']}] of seated {p['seated']}: \"{p['phrase']}\"")
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
