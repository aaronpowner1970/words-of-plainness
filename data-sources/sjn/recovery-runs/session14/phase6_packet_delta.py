"""Session 14, phase 6 (CODE-SJN-19): every seat, lead, tier and witness change a packet rebuild made,
against a named git baseline.

The baseline is a GIT REF, not a copy on disk, so the comparison cannot drift: the packets committed at that
ref are read with `git show`. The author's baseline for this run is the packet state he last saw -- the seven
packets rebuilt ONCE in session 11 (77895e1) and untouched by sessions 12, 13 and 14 phases 0-5.

  python .../phase6_packet_delta.py --baseline <ref> --out <json>
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PACKETS = "data-sources/sjn/recovery-packets"


def at(ref, path):
    p = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True,
                       encoding="utf-8", cwd=ROOT)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def view(pkt):
    """{queue_id: {seats, lead, lead_registry_id, tiers, witnesses, status}} for one packet."""
    out = {}
    for c in (pkt or {}).get("cards", []):
        ents = c.get("candidates", [])
        out[c["queue_id"]] = {
            "seats": [e["candidate_id"] for e in ents],
            "seat_rows": [e.get("registry_id") for e in ents],
            "lead": ents[0]["candidate_id"] if ents else None,
            "lead_registry_id": ents[0].get("registry_id") if ents else None,
            "tiers": {e["candidate_id"]: e.get("authority_tier") or e.get("effective_tier") for e in ents},
            "witnesses": sorted(e.get("candidate_id") for e in c.get("witness_only_candidates", []) or []),
            "status": c.get("status"),
            "held": sorted(e.get("candidate_id") for e in c.get("review_queue_held", []) or []),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    report = {"baseline_ref": a.baseline,
              "baseline_sha": subprocess.run(["git", "rev-parse", a.baseline], capture_output=True, text=True,
                                             encoding="utf-8", cwd=ROOT).stdout.strip(),
              "packets": {}}
    for f in sorted(glob.glob(os.path.join(ROOT, PACKETS, "*.json"))):
        name = os.path.basename(f)
        rel = f"{PACKETS}/{name}"
        b, n = view(at(a.baseline, rel)), view(json.load(open(f, encoding="utf-8")))
        if not n:
            continue
        ch = {}
        for qid in sorted(set(b) | set(n)):
            ob, on = b.get(qid), n.get(qid)
            if ob is None or on is None or ob == on:
                continue
            d = {}
            if ob["seats"] != on["seats"]:
                d["seats"] = {"before": ob["seats"], "after": on["seats"],
                              "membership_changed": sorted(ob["seats"]) != sorted(on["seats"]),
                              "gained": [x for x in on["seats"] if x not in ob["seats"]],
                              "lost": [x for x in ob["seats"] if x not in on["seats"]]}
            if ob["lead"] != on["lead"]:
                d["lead"] = {"before": ob["lead"], "before_row": ob["lead_registry_id"],
                             "after": on["lead"], "after_row": on["lead_registry_id"]}
            tier_ch = {k: [ob["tiers"].get(k), on["tiers"].get(k)] for k in set(ob["tiers"]) | set(on["tiers"])
                       if ob["tiers"].get(k) != on["tiers"].get(k)}
            if tier_ch:
                d["tiers"] = tier_ch
            if ob["witnesses"] != on["witnesses"]:
                d["witnesses"] = {"before": ob["witnesses"], "after": on["witnesses"]}
            if ob["status"] != on["status"]:
                d["status"] = {"before": ob["status"], "after": on["status"]}
            if ob["held"] != on["held"]:
                d["review_queue_held"] = {"before": ob["held"], "after": on["held"]}
            if d:
                ch[qid] = d
        report["packets"][name] = {"cards": len(n), "cards_changed": len(ch), "changes": ch}
    tot = sum(v["cards_changed"] for v in report["packets"].values())
    report["cards_changed_total"] = tot
    print(f"== baseline {a.baseline} ({report['baseline_sha'][:7]}): {tot} card(s) changed")
    for name, v in report["packets"].items():
        if v["cards_changed"]:
            print(f"   {name}: {v['cards_changed']} of {v['cards']}")
            for qid, d in v["changes"].items():
                print(f"      {qid}: {', '.join(sorted(d))}")
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
