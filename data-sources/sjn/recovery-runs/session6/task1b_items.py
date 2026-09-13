"""Session 6, Ruling 1b: the candidates to re-verify, read from the cell states (and cross-checked against the packets at HEAD).

  R6-1   every verifier-stage rejection whose FINAL reason code is WRONG_SUBJECT in the five retyped families (Judge, Life-giving,
         Savior, Not made, Lord) across the seven finished branches — re-verified by the models that verified it before
  TRUNC  every live-1 rubric whose reply was truncated before its floor line and salvaged (Q-081, Q-099, Q-115)"""
import glob
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_recovery import rulings  # noqa: E402

FAMS = set(rulings.required_subjects())
CELLS = os.path.join(ROOT, "data-sources", "sjn", "recovery-runs", "live-1", "cells")
R61 = "session 6 R6-1: required_subject admits the Son or the Holy Spirit as divine (Judge, Life-giving, Savior, Not made, Lord); WRONG_SUBJECT rejection re-verified"
TRUNC = "session 6: the stored reply was truncated before its floor line and salvaged as a verdict; re-verified (ceiling retry)"

items, seen = [], set()
for f in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    st = json.load(open(f, encoding="utf-8"))
    if st.get("family_id") not in FAMS or st.get("branch") == "Eastern Orthodox":
        continue
    for cid, v in st["verifications"].items():
        if (v.get("final") or {}).get("reason_code_final") == "WRONG_SUBJECT":
            items.append({"queue_id": st["queue_id"], "candidate_id": cid, "branch": st["branch"], "predicate": st["predicate"],
                          "models": [m for m in ("sonnet", "opus") if isinstance(v.get(m), dict)], "reason": R61})
            seen.add(cid)
# cross-check against the packets as committed (the count the author verified: 49)
packet_ids = set()
for slug in ("roman-catholic", "anglican", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "mennonite-anabaptist"):
    pk = json.loads(subprocess.run(["git", "show", f"HEAD:data-sources/sjn/recovery-packets/{slug}.json"], capture_output=True, cwd=ROOT).stdout.decode("utf-8"))
    for c in pk["cards"]:
        if c["family_id"] in FAMS:
            packet_ids |= {r["candidate_id"] for r in c["rejections"] if r.get("stage") == "verifier" and r.get("reason_code") == "WRONG_SUBJECT"}
trunc = []
for f in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    st = json.load(open(f, encoding="utf-8"))
    for cid, v in st["verifications"].items():
        for m in ("sonnet", "opus"):
            r = v.get(m)
            if isinstance(r, dict) and r.get("status") == "DONE" and r.get("floor") not in ("FULL", "PARTIAL", "WORD_ONLY"):
                trunc.append({"queue_id": st["queue_id"], "candidate_id": cid, "branch": st["branch"], "predicate": st["predicate"],
                              "models": [m], "reason": TRUNC})
out = {"R6-1": items, "TRUNC": trunc, "check": {"cell_states": len(items), "packets_at_HEAD": len(packet_ids),
                                                 "only_in_states": sorted(seen - packet_ids), "only_in_packets": sorted(packet_ids - seen)}}
d = os.path.dirname(__file__)
json.dump(items + trunc, open(os.path.join(d, "task1b-reverify-items.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(json.dumps(out["check"], indent=1))
print("R6-1 models:", {k: sum(1 for i in items if i["models"] == k.split("+")) for k in ("sonnet", "sonnet+opus")}, "TRUNC:", [(t["queue_id"], t["candidate_id"], t["models"]) for t in trunc])
