"""Session 12, phase 3: the chunk-id mapping for the five re-chunked rows, and every stored candidate located on a changed chunk.
No model calls, no network.

  python data-sources/sjn/recovery-runs/session12/chunk_mapping.py <dir holding the pre-re-chunk <rid>.json files>

Writes session12/chunk-id-mapping.json:
  rows.<rid>.mapping      old chunk id -> {new ids, rule}: SAME (locator and text unchanged), TEXT_CHANGED (locator kept, text
                          changed), RELOCATED (locator gone; the new chunks holding its text, by shared 8-word shingles)
  rows.<rid>.added        new chunk ids that hold no old chunk's text (text the store never had, or re-labelled front matter)
  candidates              every candidate in live-1 cell states (any pass, slotted or not) on a chunk that is not SAME:
                          the phrase checked verbatim in the old chunk, in the new chunk of the same id, and in every new chunk
Chunk id = store.chunk_id(rid, locator)."""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery import store, guards  # noqa: E402
from sjn_recovery.textutil import punct_key  # noqa: E402

ROWS = ["BSR-RC-07", "BSR-AN-04", "BSR-AN-05", "BSR-RP-05", "BSR-LU-01"]


def shingles(text, n=8):
    w = punct_key(text).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))} or ({" ".join(w)} if w else set())


def main():
    before_dir = sys.argv[1]
    out = {"what": __doc__.split("\n\n")[0], "rows": {}, "candidates": []}
    changed_ids = {}
    for rid in ROWS:
        old = json.load(open(os.path.join(before_dir, f"{rid}.json"), encoding="utf-8"))
        new = store.load_chunks(rid)
        new_by = {c["locator"]: c for c in new}
        new_sh = {c["locator"]: shingles(c["text"]) for c in new}
        mapping, used = {}, set()
        for c in old:
            oid = store.chunk_id(rid, c["locator"])
            if c["locator"] in new_by and new_by[c["locator"]]["text"] == c["text"]:
                mapping[oid] = {"new": [oid], "rule": "SAME"}
                used.add(c["locator"])
                continue
            sh = shingles(c["text"])
            # a new chunk holds this old chunk's text when most of one's 8-word shingles are in the other (a phrase repeated
            # elsewhere in the book is not enough); the new chunk of the same id is always listed
            holders = [l for l in new_by if l == c["locator"] or
                       (sh and new_sh[l] and (len(sh & new_sh[l]) / len(new_sh[l]) >= 0.5 or len(sh & new_sh[l]) / len(sh) >= 0.5))]
            if len(holders) <= (1 if c["locator"] in new_by else 0) and len(c["text"]) < 400:
                # an old chunk that held almost no text (LU-01's "-Answer:" markers) maps to the new chunks cut from the same page
                holders = [l for l in new_by if l == c["locator"] or new_by[l].get("source_url") == c.get("source_url")]
            used.update(holders)
            rule = "TEXT_CHANGED" if c["locator"] in new_by else "RELOCATED"
            rec = {"new": [store.chunk_id(rid, l) for l in holders], "rule": rule, "old_text_hash": c["text_hash"],
                   "old_chars": len(c["text"])}
            if c["locator"] in new_by:
                rec["new_text_hash"] = new_by[c["locator"]]["text_hash"]
                rec["new_chars"] = len(new_by[c["locator"]]["text"])
            mapping[oid] = rec
            changed_ids[(rid, c["locator"])] = rec
        added = [store.chunk_id(rid, l) for l in new_by if l not in used]
        n_rule = {}
        for v in mapping.values():
            n_rule[v["rule"]] = n_rule.get(v["rule"], 0) + 1
        out["rows"][rid] = {"old_chunks": len(old), "new_chunks": len(new), "by_rule": n_rule,
                            "mapping": {k: v for k, v in mapping.items() if v["rule"] != "SAME"},
                            "same_ids": sum(1 for v in mapping.values() if v["rule"] == "SAME"), "added": added}
    all_new = {rid: store.load_chunks(rid) for rid in ROWS}
    for f in sorted(glob.glob(os.path.join(ROOT, "data-sources", "sjn", "recovery-runs", "live-1", "cells", "*.json"))):
        st = json.load(open(f, encoding="utf-8"))
        for pk, p in (st.get("passes") or {}).items():
            for kind in ("candidates", "unslotted"):
                for cand in p.get(kind) or []:
                    key = (cand.get("registry_id"), cand.get("locator"))
                    if key not in changed_ids:
                        continue
                    rid, loc = key
                    same_id = next((c for c in all_new[rid] if c["locator"] == loc), None)
                    ok_old = guards.check_phrase(cand["phrase"], cand.get("chunk_text") or "")[0] if cand.get("chunk_text") else None
                    ok_same = guards.check_phrase(cand["phrase"], same_id["text"])[0] if same_id else False
                    now_in = [store.chunk_id(rid, c["locator"]) for c in all_new[rid] if guards.check_phrase(cand["phrase"], c["text"])[0]]
                    fin = ((st.get("verifications") or {}).get(cand.get("candidate_id")) or {}).get("final") or {}
                    out["candidates"].append({"queue_id": st.get("queue_id"), "pass": pk, "kind": kind,
                                              "candidate_id": cand.get("candidate_id"), "registry_id": rid, "old_locator": loc,
                                              "phrase": cand["phrase"], "final_verdict": fin.get("verdict"),
                                              "chunk_rule": changed_ids[key]["rule"],
                                              "verbatim_in_chunk_judged_at_run": ok_old,
                                              "verbatim_in_new_chunk_same_id": ok_same, "verbatim_in_new_chunks": now_in})
    path = os.path.join(HERE, "chunk-id-mapping.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1); fh.write("\n")
    for rid, r in out["rows"].items():
        print(rid, r["old_chunks"], "->", r["new_chunks"], r["by_rule"], "added", len(r["added"]))
        for k, v in r["mapping"].items():
            print("   ", v["rule"], k, "->", v["new"][:6], ("… +%d" % (len(v["new"]) - 6)) if len(v["new"]) > 6 else "")
    print("candidates on changed chunks:", len(out["candidates"]))
    for c in out["candidates"]:
        print("   ", c["queue_id"], c["candidate_id"], c["kind"], c["final_verdict"], c["chunk_rule"], "| same-id:", c["verbatim_in_new_chunk_same_id"],
              "| now in:", c["verbatim_in_new_chunks"], "|", c["phrase"])
    print(path)


if __name__ == "__main__":
    main()
