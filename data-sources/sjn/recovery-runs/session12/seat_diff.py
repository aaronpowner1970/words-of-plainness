"""Session 12: compare two directories of branch packets card by card — seats in card order (candidate id, row, effective tier),
the lead, parallel witnesses (with their rule), candidates moved between card and rejections, tier and disclosure changes, the card
status. No model calls.

  python data-sources/sjn/recovery-runs/session12/seat_diff.py <old_dir> <new_dir> [--json out.json]"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SLUGS = ["roman-catholic", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "anglican", "mennonite-anabaptist"]


def card_view(c):
    seats = [(e["candidate_id"], e["registry_id"], e.get("effective_tier"), e.get("locator")) for e in c.get("candidates", [])]
    pws = {e["candidate_id"]: sorted((w["candidate_id"], w.get("rule")) for w in e.get("same_text_parallel_witnesses") or [])
           for e in c.get("candidates", []) if e.get("same_text_parallel_witnesses")}
    rej = {r["candidate_id"]: (r.get("stage"), r.get("effective_tier")) for r in c.get("rejections", []) if r.get("candidate_id")}
    tiers = {e["candidate_id"]: e.get("effective_tier") for lst in (c.get("candidates", []), c.get("rejections", []), c.get("witness_only_candidates", []))
             for e in lst if e.get("candidate_id")}
    disc = {e["candidate_id"]: (e.get("adoption_disclosure") or {}).get("text") for lst in (c.get("candidates", []), c.get("rejections", []))
            for e in lst if e.get("candidate_id")}
    loc = {e["candidate_id"]: e.get("locator") for lst in (c.get("candidates", []), c.get("rejections", [])) for e in lst if e.get("candidate_id")}
    return {"status": c.get("status"), "seats": seats, "parallel": pws, "rejections": rej, "tiers": tiers, "disclosure": disc,
            "locators": loc, "offered": (c.get("empty_result_option") or {}).get("offered")}


def diff(old_dir, new_dir):
    out = []
    for slug in SLUGS:
        po, pn = (os.path.join(d, f"{slug}.json") for d in (old_dir, new_dir))
        if not (os.path.exists(po) and os.path.exists(pn)):
            continue
        old = {c["queue_id"]: card_view(c) for c in json.load(open(po, encoding="utf-8"))["cards"]}
        new = {c["queue_id"]: card_view(c) for c in json.load(open(pn, encoding="utf-8"))["cards"]}
        for q in sorted(set(old) | set(new)):
            o, n = old.get(q), new.get(q)
            if o is None or n is None:
                out.append({"branch": slug, "queue_id": q, "change": "card present in only one"}); continue
            ch = {}
            if o["status"] != n["status"]:
                ch["status"] = [o["status"], n["status"]]
            if o["offered"] != n["offered"]:
                ch["reviewed_offered"] = [o["offered"], n["offered"]]
            if [s[0] for s in o["seats"]] != [s[0] for s in n["seats"]]:
                ch["seats"] = [o["seats"], n["seats"]]
                if (o["seats"][:1] or [None])[0] != (n["seats"][:1] or [None])[0]:
                    ch["lead"] = [(o["seats"][:1] or [None])[0], (n["seats"][:1] or [None])[0]]
            if o["parallel"] != n["parallel"]:
                ch["parallel"] = [o["parallel"], n["parallel"]]
            t = {cid: [o["tiers"].get(cid), n["tiers"].get(cid)] for cid in set(o["tiers"]) | set(n["tiers"]) if o["tiers"].get(cid) != n["tiers"].get(cid)}
            if t:
                ch["tiers"] = t
            d = {cid: [o["disclosure"].get(cid), n["disclosure"].get(cid)] for cid in set(o["disclosure"]) & set(n["disclosure"])
                 if o["disclosure"].get(cid) != n["disclosure"].get(cid)}
            if d:
                ch["disclosure"] = d
            lc = {cid: [o["locators"].get(cid), n["locators"].get(cid)] for cid in set(o["locators"]) & set(n["locators"])
                  if o["locators"].get(cid) != n["locators"].get(cid)}
            if lc:
                ch["locators"] = lc
            r = {cid: [o["rejections"].get(cid), n["rejections"].get(cid)] for cid in set(o["rejections"]) | set(n["rejections"])
                 if o["rejections"].get(cid) != n["rejections"].get(cid)}
            if r:
                ch["rejections"] = r
            if ch:
                out.append(dict(branch=slug, queue_id=q, **ch))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old_dir")
    ap.add_argument("new_dir")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = diff(a.old_dir, a.new_dir)
    for x in out:
        print(json.dumps(x, ensure_ascii=False))
    print(f"cards changed: {len(out)}")
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1); fh.write("\n")


if __name__ == "__main__":
    main()
