"""Session 11 rebuild diff (2026-09-17) — no model calls. Per candidate: tier moves and adoption-disclosure changes; per card:
lead / state / seat changes (rebuild_diff.diff_branch). Base = the committed packets (git HEAD), i.e. the session 6 build.

  python data-sources/sjn/recovery-runs/session11/rebuild_diff_s11.py [--base HEAD]
writes data-sources/sjn/recovery-runs/live-1/rebuild-diff-20260917.{json,md}

Each change is attributed. A tier move whose new effective_tier_why is a registered-phrase hit is R6-5/R6-10 (session 7 phrase-level
creed resolution, first reflected in a packet now); a move on an R6-35..R6-40 row that returns it to its host tier is the adoption
ruling; a disclosure change on an R6-6 row is R6-9 as completed by R6-35..R6-40."""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery.rebuild_diff import git_show, diff_branch  # noqa: E402
from sjn_recovery.config import PACKETS_DIR, RUNS_DIR  # noqa: E402

SLUGS = ["roman-catholic", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "anglican", "mennonite-anabaptist"]
RULED = {"BSR-RC-07": "R6-40", "BSR-AN-02": "R6-35", "BSR-AN-04": "R6-40", "BSR-AN-05": "R6-36", "BSR-LU-03": "R6-37",
         "BSR-RP-02": "R6-38", "BSR-RP-03": "R6-38", "BSR-RP-05": "R6-40", "BSR-LU-01": "R6-38", "BSR-BA-03": "R6-39"}


def entries(pk):
    for c in pk["cards"]:
        for place, lst in (("card", c.get("candidates", [])), ("witness_only", c.get("witness_only_candidates", [])),
                           ("rejection", c.get("rejections", []))):
            for e in lst:
                if e.get("candidate_id"):
                    yield c["queue_id"], place + (f" ({e.get('stage')})" if place == "rejection" else ""), e


def cand_diff(old, new):
    oi = {cid: (q, p, e) for q, p, e in entries(old) for cid in [e["candidate_id"]]}
    ni = {cid: (q, p, e) for q, p, e in entries(new) for cid in [e["candidate_id"]]}
    tier, disc, seat = [], [], []
    for cid in sorted(set(oi) & set(ni)):
        (q, po, eo), (_, pn, en) = oi[cid], ni[cid]
        rid = en["registry_id"]
        if eo.get("effective_tier") != en.get("effective_tier"):
            hit = en.get("registered_phrase_hit")
            cause = (f"R6-5/R6-10 phrase-level creed resolution (phrase verbatim in {hit['registry_id']} {hit['locator']})" if hit and en["effective_tier"] == hit["tier"]
                     else f"{RULED.get(rid, '?')} adoption" if rid in RULED else "UNEXPLAINED")
            tier.append({"queue_id": q, "candidate_id": cid, "registry_id": rid, "place": pn, "from": eo.get("effective_tier"),
                         "to": en.get("effective_tier"), "phrase": en.get("phrase"), "cause": cause})
        do, dn = (eo.get("adoption_disclosure") or {}).get("text"), (en.get("adoption_disclosure") or {}).get("text")
        if do != dn:
            disc.append({"queue_id": q, "candidate_id": cid, "registry_id": rid, "place": pn, "from": do, "to": dn,
                         "cause": f"{RULED[rid]} (R6-9 card disclosure)" if rid in RULED else "UNEXPLAINED"})
        if po.split(" (")[0] != pn.split(" (")[0] or (po.startswith("rejection") and po != pn):
            seat.append({"queue_id": q, "candidate_id": cid, "registry_id": rid, "from": po, "to": pn,
                         "tier": en.get("effective_tier"), "reason": en.get("dropped_reason")})
    return tier, disc, seat, sorted(set(oi) ^ set(ni))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--out", default=os.path.join(RUNS_DIR, "live-1", "rebuild-diff-20260917"))
    a = ap.parse_args()
    out = []
    for slug in SLUGS:
        old = git_show(a.base, f"data-sources/sjn/recovery-packets/{slug}.json")
        with open(os.path.join(PACKETS_DIR, f"{slug}.json"), encoding="utf-8") as fh:
            new = json.load(fh)
        d = diff_branch(slug, a.base)
        tier, disc, seat, presence = cand_diff(old, new)
        d.update({"tier_moves": tier, "disclosure_changes": disc, "seat_changes": seat, "candidates_present_in_only_one": presence,
                  "public_certified_cards": [c["queue_id"] for c in new["cards"] if "CERTIFIED" in str(c.get("current_rendered_state"))]})
        out.append(d)
    with open(a.out + ".json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1); fh.write("\n")
    L = ["# Packet rebuild diff — session 11 (2026-09-17)", "",
         "The ONE rebuild R6-16 held for, after the author ratified the adoption verification (R6-35 to R6-40). No model calls.",
         "Base = the committed packets (session 6 build, 2026-09-13). This is the first build since session 6, so the session 7-9",
         "resolution rules appear here for the first time beside the session 11 rulings; every change is attributed below.", "",
         "| branch | cells | tier moves | disclosure changes | seat changes | lead changed | state changed | dropped off a card | added to a card | unexplained |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for d in out:
        unexpl = sum(1 for x in d["tier_moves"] + d["disclosure_changes"] if x["cause"] == "UNEXPLAINED") + len(d["candidates_present_in_only_one"])
        L.append(f"| {d['branch']} | {d['cells']} | {len(d['tier_moves'])} | {len(d['disclosure_changes'])} | {len(d['seat_changes'])} | "
                 f"{len(d['lead_changed'])} | {len(d['state_changed'])} | {len(d['candidates_dropped'])} | {len(d['candidates_added'])} | {unexpl} |")
    L += ["", "## Tier moves by row and move", "", "| row | from → to | cause | candidates |", "|---|---|---|---|"]
    agg = collections.Counter((x["registry_id"], x["from"], x["to"], x["cause"].split(" (")[0]) for d in out for x in d["tier_moves"])
    for (rid, f, t, c), n in sorted(agg.items()):
        L.append(f"| {rid} | {f} → {t} | {c} | {n} |")
    L += ["", "## Disclosure changes by row", "", "| row | from | to | candidates |", "|---|---|---|---|"]
    agg = collections.Counter((x["registry_id"], x["from"], x["to"]) for d in out for x in d["disclosure_changes"])
    for (rid, f, t), n in sorted(agg.items()):
        L.append(f"| {rid} | {f or '—'} | {t or '—'} | {n} |")
    for d in out:
        if not (d["tier_moves"] or d["seat_changes"] or d["lead_changed"] or d["state_changed"]):
            continue
        L += ["", f"## {d['branch']}", ""]
        for x in d["tier_moves"]:
            L.append(f"- tier {x['queue_id']} {x['candidate_id']} [{x['place']}]: {x['from']} → {x['to']} — {x['cause']}; phrase “{x['phrase']}”")
        for x in d["seat_changes"]:
            L.append(f"- seat {x['queue_id']} {x['candidate_id']}: {x['from']} → {x['to']} (now {x['tier']}){'; ' + x['reason'] if x['reason'] else ''}")
        for x in d["lead_changed"]:
            L.append(f"- lead {x['queue_id']}: {x['from']} → {x['to']} ({x['kind']})")
        for x in d["state_changed"]:
            L.append(f"- state {x['queue_id']}: {x['from']} → {x['to']}")
    certified = ", ".join(q for d in out for q in d["public_certified_cards"])
    L += ["", "PUBLIC-CERTIFIED cards in any packet: " + (certified or "none (Gate 6 runs only open cells).")]
    with open(a.out + ".md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
