"""Session 6, Task 4c: how the one-text-one-slot guard behaves on BSR-EO-07 (ACROD) and BSR-EO-14 (Archdiocese of Canada) —
one rite, the Divine Liturgy of St John Chrysostom, on two hosts in two translations. No model calls; reads the chunk store.

Instrument: every sentence / clause of each stored chunk (split on . ; : ! ? and line breaks), keyed by allocation.same_text_key
(the guard's own comparison), and every 5- to 15-word window of EO-07 tested for textual presence in EO-14 (the guard compares
whole phrases, so a phrase the locator could cut from EO-07 triggers the guard only if EO-14 has the identical phrase)."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sjn_recovery import store  # noqa: E402
from sjn_recovery.allocation import same_text_key, allocate  # noqa: E402
from sjn_recovery.rulings import same_text_rows  # noqa: E402

A, B = "BSR-EO-07", "BSR-EO-14"


def clauses(rid):
    out = []
    for c in store.load_chunks(rid):
        for s in re.split(r"[.;:!?\n]+", c["text"]):
            k = same_text_key(s)
            if len(k.split()) >= 4:
                out.append((c["locator"], s.strip(), k))
    return out


def windows(text, lo=5, hi=15):
    w = same_text_key(text).split()
    for n in range(lo, hi + 1):
        for i in range(0, max(0, len(w) - n + 1)):
            yield " ".join(w[i:i + n])


ca, cb = clauses(A), clauses(B)
kb = {k for _, _, k in cb}
ident = [(loc, s) for loc, s, k in ca if k in kb]
textb = " " + " ".join(same_text_key(c["text"]) for c in store.load_chunks(B)) + " "
tot = hit = 0
for c in store.load_chunks(A):
    for w in set(windows(c["text"])):
        tot += 1
        hit += 1 if f" {w} " in textb else 0
probes = ["begotten, not made", "the Lord, the Giver of Life", "to judge the living and the dead", "for us and for our salvation",
          "for us men and for our salvation", "inconceivable", "incomprehensible", "beyond comprehension", "beyond understanding",
          "invisible", "ineffable", "unchangeable", "Light of Light", "true God of true God", "of one essence with the Father"]
probe_rows = [{"probe": p, "in_EO-07": f" {same_text_key(p)} " in " " + " ".join(same_text_key(c["text"]) for c in store.load_chunks(A)) + " ",
               "in_EO-14": f" {same_text_key(p)} " in textb} for p in probes]
# the allocator on the case the EO launch prompt describes: both rows survive on one card with different wording
cands = [{"candidate_id": "eo14", "registry_id": B, "phrase": "beyond comprehension", "effective_tier": "CONFESSIONAL", "floor_claim": "FULL", "locator": "L"},
         {"candidate_id": "eo07", "registry_id": A, "phrase": "inconceivable", "effective_tier": "CONFESSIONAL", "floor_claim": "PARTIAL", "locator": "L"}]
textual_only = allocate(cands, groups={}, same_text_rows={})
with_declared = allocate(cands, groups={}, same_text_rows=same_text_rows())
res = {"rows": [A, B], "chunks": [len(store.load_chunks(A)), len(store.load_chunks(B))],
       "clauses_4plus_words": [len(ca), len(cb)], "EO-07_clauses_textually_identical_in_EO-14": len(ident),
       "share_of_EO-07_clauses_identical": round(len(ident) / len(ca), 3) if ca else None, "identical_examples": ident[:25],
       "EO-07_5to15_word_windows": tot, "windows_present_in_EO-14": hit, "window_share": round(hit / tot, 3) if tot else None,
       "probes": probe_rows,
       "allocator_textual_guard_only": {"kept": textual_only["kept"], "parallel_witnesses": textual_only["parallel_witnesses"]},
       "allocator_with_declared_same_text_row": {"kept": with_declared["kept"], "parallel_witnesses": with_declared["parallel_witnesses"]}}
out = os.path.join(os.path.dirname(__file__), "task4c-eo07-eo14.json")
json.dump(res, open(out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "identical_examples"}, ensure_ascii=False, indent=1))
for loc, s in ident[:25]:
    print("  IDENTICAL", loc[:40], "|", s[:120])
