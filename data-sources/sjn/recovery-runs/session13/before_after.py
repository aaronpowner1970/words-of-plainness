"""Session 13, phase 2: the before/after registration table (markdown) from registered-before.json and registered-after.json.
  python before_after.py > registration-before-after.md"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8")
b = json.load(open(os.path.join(HERE, "registered-before.json"), encoding="utf-8"))["entries"]
a = json.load(open(os.path.join(HERE, "registered-after.json"), encoding="utf-8"))["entries"]
lst = json.load(open(os.path.join(HERE, "..", "registered-sections.json"), encoding="utf-8"))
notes = {(e["registry_id"], e["locator"]): e for e in lst["sections"]}
why_not = {(e["registry_id"], e["locator"]): e["why"] for e in lst["not_registered"]}
bk = {(e["registry_id"], e["locator"]): e for e in b}
ak = {(e["registry_id"], e["locator"]): e for e in a}
print("| branch | kind | row | locator | tier | before | after | registered extent / reason |")
print("|---|---|---|---|---|---|---|---|")
for k in list(bk) + [k for k in ak if k not in bk]:
    e = bk.get(k) or ak.get(k)
    after = k in ak
    if after:
        n = notes[k]
        why = (f"extent ends after \"{n['text_through']}\" ({ak[k]['registered_key_words']} of the chunk's words registered); " if n.get("text_through") else "")
        why += n.get("note") or n.get("what")
        if n.get("section_spans_chunks"):
            why += f"; section spans chunks: {n['section_spans_chunks']}"
    else:
        why = "LEFT OUT: " + why_not.get(k, "?")
    print(f"| {e['branch']} | {e['kind']} | {k[0]} | {k[1]} | {e['tier']} | {'yes' if k in bk else 'no'} | {'yes' if after else 'no'} | {why} |")
print(f"\nBefore: {len(b)} registered chunks. After: {len(a)}. Left out: {len(set(bk) - set(ak))}. Added: {len(set(ak) - set(bk))}.")
