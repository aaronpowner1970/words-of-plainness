import json, sys, os, glob, re, subprocess
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\aaron\Documents\words-of-plainness"
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_recovery import store
from sjn_recovery.textutil import punct_key

pk_dir = sys.argv[1] if len(sys.argv) > 1 else "data-sources/sjn/recovery-packets"


def all_entries(pk):
    for c in pk["cards"]:
        for role, lst in (("KEPT", c.get("candidates", [])), ("WITNESS_ONLY", c.get("witness_only_candidates", [])), ("REJ", c.get("rejections", []))):
            for e in lst:
                rid = e.get("registry_id") or (e.get("candidate") or {}).get("registry_id")
                loc = e.get("locator") or (e.get("candidate") or {}).get("locator")
                yield c, role + (":" + str(e.get("stage")) if role == "REJ" else ""), e, rid, loc
                for pw in e.get("same_text_parallel_witnesses") or []:
                    yield c, "PARALLEL_WITNESS", pw, pw.get("registry_id"), pw.get("locator")

print("=== 3d AN-05 Q.1/Q.2/Q.3 citations; RC-07 Q.533; RP-05 Q&A 79 (packets in", pk_dir, ")")
for p in sorted(glob.glob(os.path.join(pk_dir, "*.json"))):
    pk = json.load(open(p, encoding="utf-8"))
    for c, role, e, rid, loc in all_entries(pk):
        if rid == "BSR-AN-05" and re.search(r"Q\.[123] —", loc or ""):
            print(" AN05", os.path.basename(p), c["queue_id"], role, loc[:40], "|", e.get("phrase") or (e.get("candidate") or {}).get("phrase"), "| tier", e.get("effective_tier"))
        if rid == "BSR-RC-07" and (loc or "").endswith("Q.533"):
            print(" RC07-Q533", os.path.basename(p), c["queue_id"], role, "|", e.get("phrase") or (e.get("candidate") or {}).get("phrase"))
        if rid == "BSR-RP-05" and (loc or "").startswith("Q&A 79"):
            print(" RP05-Q79", os.path.basename(p), c["queue_id"], role, "|", e.get("phrase") or (e.get("candidate") or {}).get("phrase"))

print("=== 3d other files mentioning To Be a Christian / AN-05 locators")
for f in glob.glob("src/_data/sjn/*.json") + glob.glob("data-sources/sjn/recovery-packets/extracts/*.json"):
    t = open(f, encoding="utf-8").read()
    for m in re.finditer(r"To Be a Christian, Q\.[123] —", t):
        print(" ", f, m.group(0))
    if "To-Be-a-Christian" in t or "To Be a Christian" in t:
        print("  mentions TBaC:", f, t.count("To Be a Christian"))

print("=== 3g LU-01 vs LU-03 same text")
lu3 = store.load_chunks("BSR-LU-03")[0]
k3 = punct_key(lu3["text"])
lu1 = store.load_chunks("BSR-LU-01")
same = [c for c in lu1 if punct_key(c["text"]) == k3]
print(" identical chunks:", len(same))
cont = [c for c in lu1 if k3 in punct_key(c["text"]) or punct_key(c["text"]) in k3]
print(" containment:", [(c["locator"], len(c["text"])) for c in cont][:5])
first = [c for c in lu1 if "Maker of heaven and earth" in c["text"] and "What does this mean" in c["text"]]
for c in first[:3]:
    print(" LU-01 candidate chunk:", c["locator"], c["source_url"])
    print("   ", c["text"][:900])
# sentence-level overlap
import difflib
s3 = [punct_key(x) for x in re.split(r"(?<=[.?!])\s+", lu3["text"]) if x.strip()]
for c in first[:1]:
    s1 = set(punct_key(x) for x in re.split(r"(?<=[.?!])\s+", c["text"]) if x.strip())
    print(" LU-03 sentences also verbatim in that LU-01 chunk:", sum(1 for x in s3 if x in s1), "of", len(s3))
    for x in s3:
        print("   ", "SAME" if x in s1 else "diff", x[:90])
print(" packets: LU-03 candidates and their parallel witnesses")
pk = json.load(open(os.path.join(pk_dir, "lutheran.json"), encoding="utf-8"))
for c in pk["cards"]:
    for e in c.get("candidates", []):
        if e["registry_id"] in ("BSR-LU-03",) or any(w.get("registry_id") == "BSR-LU-03" for w in e.get("same_text_parallel_witnesses") or []):
            print("  ", c["queue_id"], e["registry_id"], e["candidate_id"], repr(e["phrase"]), e.get("effective_tier"),
                  "PW:", [(w["registry_id"], w.get("rule")) for w in e.get("same_text_parallel_witnesses") or []])
    for e in c.get("rejections", []):
        if e.get("registry_id") == "BSR-LU-03":
            print("   rej", c["queue_id"], e["candidate_id"], repr(e.get("phrase")), e.get("stage"), e.get("dropped_reason"))

print("=== 3h Q-085 / Q-133 / Q-405 Anglican sources")
pk = json.load(open(os.path.join(pk_dir, "anglican.json"), encoding="utf-8"))
for c in pk["cards"]:
    if c["queue_id"] in ("Q-085", "Q-133", "Q-405"):
        print(" ", c["queue_id"], c["predicate"], "status", c["status"])
        for e in c.get("candidates", []):
            print("    KEPT", e["registry_id"], e["locator"][:50], "| tier", e.get("effective_tier"), "| disc", (e.get("adoption_disclosure") or {}).get("text"), "|", e["phrase"])
        for e in c.get("witness_only_candidates", []):
            print("    WIT ", e["registry_id"], e["locator"][:50], e.get("effective_tier"))
        for e in c.get("rejections", []):
            rid = e.get("registry_id") or (e.get("candidate") or {}).get("registry_id")
            print("    REJ ", rid, str(e.get("stage"))[:30], (e.get("locator") or (e.get("candidate") or {}).get("locator") or "")[:40], "| tier", e.get("effective_tier"), "|", (e.get("final_verdict") or {}).get("verdict"))
