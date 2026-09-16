"""Gate 6 session 8 (2026-09-16): the no-model-call analyses.

  task3-creed-match-conciliar-only.json   Task 3a/3b — Task 1d re-run against BSR-EO-07, BSR-EO-14 and BSR-EO-12 ONLY
  task4-card-changes-rerun.json           Task 4    — session 7's Task 2d re-resolution re-run, and its difference from
                                                      session7/task2d-card-changes.json

  python data-sources/sjn/recovery-runs/session8/analyse.py

The instruments are session 7's, imported rather than copied (session7/analyse.py): the same 27-clause list, the same
sentence split, the same punct_key. The only change in 3a is the text set searched. Nothing is written anywhere else.
"""
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "session7"))

from sjn_recovery.registry import Registry  # noqa: E402
from sjn_recovery.textutil import punct_key  # noqa: E402
from sjn_recovery import store  # noqa: E402
import analyse as s7  # noqa: E402

CONCILIAR_TEXTS = ("BSR-EO-07", "BSR-EO-14", "BSR-EO-12")
EO09 = "BSR-EO-09"
SIDE_BY_SIDE_MARGIN = 6


def longest_run(sentence_key, texts):
    """The longest contiguous word-run of the sentence standing verbatim in any of `texts`, with the text it stands in
    and a window of that text around it. Runs of 1 word are kept, so a near-total miss is visible as what it is."""
    w = sentence_key.split()
    for size in range(len(w), 0, -1):
        for i in range(len(w) - size + 1):
            run = " ".join(w[i:i + size])
            for t in texts:
                pos = (" " + t["key"] + " ").find(" " + run + " ")
                if pos >= 0:
                    lo, hi = max(0, pos - 80), min(len(t["key"]), pos + len(run) + 80)
                    return {"words": size, "run": run, "registry_id": t["registry_id"], "locator": t["locator"],
                            "window": ("…" if lo else "") + t["key"][lo:hi] + ("…" if hi < len(t["key"]) else "")}
    return {"words": 0, "run": "", "registry_id": None, "locator": None, "window": None}


def task3(reg):
    all_texts = reg.registered_creed_texts("Eastern Orthodox")
    conciliar = [t for t in all_texts if t["registry_id"] in CONCILIAR_TEXTS]
    eo09 = [t for t in all_texts if t["registry_id"] == EO09]
    assert {t["registry_id"] for t in conciliar} == set(CONCILIAR_TEXTS), "a named conciliar creed text is not registered"
    chunks = store.load_chunks("BSR-EO-01")
    bearing, n_sent = [], 0
    for c in chunks:
        sents = [x for x in re.split(r"(?<=[.!?])\s+", c["text"]) if len(x.strip()) > 3]
        n_sent += len(sents)
        for x in sents:
            hits = [k for k in s7.CREED_CLAUSES if k in s7.norm(x)]
            if hits:
                bearing.append({"locator": c["locator"], "sentence": x.strip(), "clauses": hits})

    # instrument 1: the clause list, against the three conciliar texts only
    per_sentence = []
    for i, b in enumerate(bearing, 1):
        res = []
        for clause in b["clauses"]:
            m = re.search(re.escape(clause).replace(r"\ ", r"\s+"), b["sentence"], re.I)
            key = punct_key(m.group(0) if m else clause)
            hit = next((t for t in conciliar if key in t["key"]), None)
            hit09 = next((t for t in eo09 if key in t["key"]), None)
            res.append({"clause": clause, "in_conciliar": f"{hit['registry_id']} {hit['locator']}" if hit else None,
                        "in_eo09": bool(hit09)})
        b.update(n=i, clause_results=res, clause_matched=any(r["in_conciliar"] for r in res))
        # instrument 2: the longest verbatim run, against the three texts, and against EO-09 alone for the comparison
        key = punct_key(b["sentence"])
        b["run_conciliar"] = longest_run(key, conciliar)
        b["run_eo09"] = longest_run(key, eo09)
        per_sentence.append(b)
    per_clause = {}
    for clause in s7.CREED_CLAUSES:
        key = punct_key(clause)
        hit = next((t for t in conciliar if key in t["key"]), None)
        per_clause[clause] = {"in_conciliar": f"{hit['registry_id']} {hit['locator']}" if hit else None,
                              "in_eo09": any(key in t["key"] for t in eo09),
                              "nearest_conciliar": None if hit else s7.nearest(key, conciliar)}
    dist = dict(sorted(Counter(b["run_conciliar"]["words"] for b in per_sentence).items()))
    dist09 = dict(sorted(Counter(b["run_eo09"]["words"] for b in per_sentence).items()))
    under4 = [{"n": b["n"], "locator": b["locator"], "sentence": b["sentence"], "clauses": b["clauses"],
               "longest_conciliar_run": b["run_conciliar"], "eo09_run": {k: b["run_eo09"][k] for k in ("words", "run")}}
              for b in per_sentence if b["run_conciliar"]["words"] < 4]
    side = [{"n": b["n"], "locator": b["locator"], "sentence": b["sentence"],
             "eo09": b["run_eo09"], "best_conciliar": b["run_conciliar"],
             "margin_words": b["run_eo09"]["words"] - b["run_conciliar"]["words"]}
            for b in per_sentence if b["run_eo09"]["words"] - b["run_conciliar"]["words"] >= SIDE_BY_SIDE_MARGIN]
    clause_missed = [b for b in per_sentence if not b["clause_matched"]]
    return {
        "texts_searched": sorted({f"{t['registry_id']} ({t['language']})" for t in conciliar}),
        "eo12_note": "BSR-EO-12 is the Greek text. An English sentence cannot match it verbatim, so in practice the English "
                     "sentences are measured against BSR-EO-07 and BSR-EO-14 alone.",
        "excluded": "BSR-EO-09 (Synodikon §2) — measured separately for the side-by-side only, never counted as a match",
        "eo01_chunks": len(chunks), "eo01_sentences": n_sent, "creed_bearing_sentences": len(per_sentence),
        "instrument_1_clause_list": {
            "sentences_with_a_listed_clause_verbatim_in_EO07_EO14_EO12": len(per_sentence) - len(clause_missed),
            "sentences_with_none": len(clause_missed),
            "clauses_matched": sum(1 for v in per_clause.values() if v["in_conciliar"]), "clauses_total": len(per_clause),
            "per_clause": per_clause,
            "sentences_with_none_detail": [{"n": b["n"], "locator": b["locator"], "sentence": b["sentence"],
                                            "clauses": b["clause_results"]} for b in clause_missed]},
        "instrument_2_longest_run": {
            "distribution_conciliar": dist, "distribution_eo09_alone": dist09,
            "sentences_under_4_words": len(under4), "under_4_detail": under4,
            "median_conciliar": sorted(b["run_conciliar"]["words"] for b in per_sentence)[len(per_sentence) // 2]},
        f"eo09_at_least_{SIDE_BY_SIDE_MARGIN}_words_longer": side,
        "per_sentence": [{"n": b["n"], "locator": b["locator"], "sentence": b["sentence"][:260],
                          "clause_matched": b["clause_matched"], "run_conciliar_words": b["run_conciliar"]["words"],
                          "run_conciliar": b["run_conciliar"]["run"], "run_conciliar_in": b["run_conciliar"]["registry_id"],
                          "run_eo09_words": b["run_eo09"]["words"]} for b in per_sentence],
    }


def _index(changes):
    out = {}
    for c in changes:
        out[(c["branch"], c["queue_id"])] = c
    return out


def task4(reg):
    new = s7.task2d(reg)
    old = json.load(open(os.path.join(HERE, "..", "session7", "task2d-card-changes.json"), encoding="utf-8"))
    oi, ni = _index(old["changes"]), _index(new["changes"])
    diff = []
    for k in sorted(set(oi) | set(ni)):
        a, b = oi.get(k), ni.get(k)
        if a != b:
            diff.append({"branch": k[0], "queue_id": k[1], "session7": a, "session8": b})
    return {"note": "IN MEMORY. session7/analyse.task2d re-run under R6-15's precedence; no packet rebuilt, no model call.",
            "by_branch_session7": old["by_branch"], "by_branch_session8": new["by_branch"],
            "cards_changed_session7": old["cards_changed"], "cards_changed_session8": new["cards_changed"],
            "cards_that_differ": len(diff), "differences": diff, "session8": new}


def main():
    reg = Registry()
    for name, fn in (("task3-creed-match-conciliar-only", task3), ("task4-card-changes-rerun", task4)):
        d = fn(reg)
        with open(os.path.join(HERE, f"{name}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        if name.startswith("task3"):
            i1, i2 = d["instrument_1_clause_list"], d["instrument_2_longest_run"]
            print(f"== Task 3: {d['creed_bearing_sentences']} creed-bearing sentences of {d['eo01_sentences']}")
            print(f"   clause list: {i1['sentences_with_a_listed_clause_verbatim_in_EO07_EO14_EO12']} matched, "
                  f"{i1['sentences_with_none']} not; clauses {i1['clauses_matched']}/{i1['clauses_total']}")
            print(f"   longest run (07/14/12): {i2['distribution_conciliar']}  median {i2['median_conciliar']}")
            print(f"   longest run (EO-09 alone): {i2['distribution_eo09_alone']}")
            print(f"   under 4 words: {i2['sentences_under_4_words']}; EO-09 >= 6 longer: {len(d['eo09_at_least_6_words_longer'])}")
        else:
            print(f"== Task 4: cards changed s7 {d['cards_changed_session7']} / s8 {d['cards_changed_session8']}; "
                  f"cards that differ: {d['cards_that_differ']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
