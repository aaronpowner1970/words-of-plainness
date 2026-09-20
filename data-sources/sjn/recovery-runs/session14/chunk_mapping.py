"""Session 14, phase 4: the chunk-id mapping for the AN-04 / AN-06 split (Codex F.10; R6-48, R6-51). Derived from the
session 13 script, with one change that the split forces: a mapped new chunk may sit in ANOTHER ROW.

Every earlier re-chunk moved text within one row, so the mapping's row id was the row id on both sides. Here the
Chalcedonian Definition and the Quicunque Vult leave BSR-AN-04 for BSR-AN-06, and a stored candidate located in them
must follow its text rather than be dropped as a vanished chunk: the evidence is unchanged; the row holding it is not.
packets.relocate reads the new ids' own row ids and the packet builder re-reads tier, adoption, speaks_for and witness
status from the row that holds the text now (which is how R6-47's witness treatment reaches these citations at all).

No model calls, no network.

  python data-sources/sjn/recovery-runs/session14/chunk_mapping.py <dir holding the pre-split BSR-AN-04.json>

Writes session14/chunk-id-mapping.json, in the shape config.CHUNK_ID_MAPPINGS expects:
  rows.<rid>.mapping    old chunk id -> {new ids (possibly in another row), rule}
  candidates            every stored candidate on a chunk that is not SAME, with the phrase checked verbatim in the
                        chunk judged at run, in the new chunk of the same id, and in every new chunk of either row
"""
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

OLD_ROWS = ["BSR-AN-04"]                       # the rows whose stored chunks are being re-read
NEW_ROWS = ["BSR-AN-04", "BSR-AN-06"]          # the rows a chunk's text may land in after the split


def shingles(text, n=8):
    w = punct_key(text).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))} or ({" ".join(w)} if w else set())


def main():
    before_dir = sys.argv[1]
    new = {rid: store.load_chunks(rid) for rid in NEW_ROWS}
    new_by = {(rid, c["locator"]): c for rid in NEW_ROWS for c in new[rid]}
    new_sh = {k: shingles(c["text"]) for k, c in new_by.items()}
    out = {"what": __doc__.split("\n\n")[0], "ruling": "R6-48 / R6-51 (Comparison Principles Codex v0.8, F.10)",
           "rows": {}, "candidates": []}
    changed = {}
    for rid in OLD_ROWS:
        old = json.load(open(os.path.join(before_dir, f"{rid}.json"), encoding="utf-8"))
        mapping, used = {}, set()
        for c in old:
            key = (rid, c["locator"])
            oid = store.chunk_id(rid, c["locator"])
            if key in new_by and new_by[key]["text"] == c["text"]:
                mapping[oid] = {"new": [oid], "rule": "SAME"}
                used.add(key)
                continue
            sh = shingles(c["text"])
            holders = [k for k in new_by if k == key or
                       (sh and new_sh[k] and (len(sh & new_sh[k]) / len(new_sh[k]) >= 0.5 or len(sh & new_sh[k]) / len(sh) >= 0.5))]
            used.update(holders)
            rule = "TEXT_CHANGED" if key in new_by else ("MOVED_TO_ANOTHER_ROW" if any(k[0] != rid for k in holders) else "RELOCATED")
            rec = {"new": [store.chunk_id(*k) for k in holders], "rule": rule, "old_text_hash": c["text_hash"],
                   "old_chars": len(c["text"]), "moved_to_rows": sorted({k[0] for k in holders if k[0] != rid})}
            if key in new_by:
                rec["new_text_hash"] = new_by[key]["text_hash"]
                rec["new_chars"] = len(new_by[key]["text"])
            mapping[oid] = rec
            changed[key] = rec
        added = [store.chunk_id(*k) for k in new_by if k not in used]
        n_rule = {}
        for v in mapping.values():
            n_rule[v["rule"]] = n_rule.get(v["rule"], 0) + 1
        out["rows"][rid] = {"old_chunks": len(old), "new_chunks": len(new[rid]), "by_rule": n_rule,
                            "mapping": {k: v for k, v in mapping.items() if v["rule"] != "SAME"},
                            "same_ids": sum(1 for v in mapping.values() if v["rule"] == "SAME"), "added": added}
    for f in sorted(glob.glob(os.path.join(ROOT, "data-sources", "sjn", "recovery-runs", "live-1", "cells", "*.json"))):
        st = json.load(open(f, encoding="utf-8"))
        for pk, p in (st.get("passes") or {}).items():
            for kind in ("candidates", "unslotted"):
                for cand in p.get(kind) or []:
                    key = (cand.get("registry_id"), cand.get("locator"))
                    if key not in changed:
                        continue
                    rid, loc = key
                    same_id = new_by.get(key)
                    ok_old = guards.check_phrase(cand["phrase"], cand.get("chunk_text") or "")[0] if cand.get("chunk_text") else None
                    ok_same = guards.check_phrase(cand["phrase"], same_id["text"])[0] if same_id else False
                    now_in = [store.chunk_id(*k) for k, c in new_by.items() if guards.check_phrase(cand["phrase"], c["text"])[0]]
                    fin = ((st.get("verifications") or {}).get(cand.get("candidate_id")) or {}).get("final") or {}
                    out["candidates"].append({"queue_id": st.get("queue_id"), "pass": pk, "kind": kind,
                                              "candidate_id": cand.get("candidate_id"), "registry_id": rid, "old_locator": loc,
                                              "phrase": cand["phrase"], "final_verdict": fin.get("verdict"),
                                              "stored_route": fin.get("route"),
                                              "models": sorted(m for m, r in ((st.get("verifications") or {}).get(cand.get("candidate_id")) or {}).items()
                                                               if isinstance(r, dict) and m not in ("final", "_route", "final_at_run",
                                                                                                    "superseded_rubrics", "reverified")),
                                              "chunk_rule": changed[key]["rule"],
                                              "verbatim_in_chunk_judged_at_run": ok_old,
                                              "verbatim_in_new_chunk_same_id": ok_same, "verbatim_in_new_chunks": now_in})
    path = os.path.join(HERE, "chunk-id-mapping.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for rid, r in out["rows"].items():
        print(rid, r["old_chunks"], "->", r["new_chunks"], r["by_rule"], "added", len(r["added"]))
        for k, v in r["mapping"].items():
            print("   ", v["rule"], k, "->", v["new"][:4], ("... +%d" % (len(v["new"]) - 4)) if len(v["new"]) > 4 else "")
        for a in r["added"]:
            print("    ADDED", a)
    print("candidates on changed chunks:", len(out["candidates"]))
    for c in out["candidates"]:
        print("   ", c["queue_id"], c["candidate_id"], c["kind"], c["final_verdict"], c["chunk_rule"],
              "| same-id:", c["verbatim_in_new_chunk_same_id"], "| now in:", c["verbatim_in_new_chunks"], "|", c["phrase"])
    print(path)


if __name__ == "__main__":
    main()
