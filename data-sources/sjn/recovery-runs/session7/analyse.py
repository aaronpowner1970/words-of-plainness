"""Gate 6 session 7 (2026-09-16): the read-only measurements the repair prompt asks for. No model calls, no writes to
the workbook, no packet released.

  python data-sources/sjn/recovery-runs/session7/analyse.py

Writes, beside this file:
  task1d-hopko-creed-match.json     Task 1d  — do Hopko's Creed quotations match a registered creed text verbatim?
  task2-registered-texts.json       Task 2a/2b — the registered creed and definition texts, per branch
  task2d-card-changes.json          Task 2d/3 — every card on the seven finished branches whose tier, order or slot moves
  task3-adoption.json               Task 3   — the migration, the rank assertion, the UNVERIFIED count, the proposals
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

from sjn_recovery.registry import Registry, bare_tier, tier_rank, SECOND_TIER  # noqa: E402
from sjn_recovery.allocation import allocate, translation_pairs, speaks_for_groups  # noqa: E402
from sjn_recovery.textutil import punct_key  # noqa: E402
from sjn_recovery.config import PACKETS_DIR  # noqa: E402
from sjn_recovery import store, rulings  # noqa: E402

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")

# The 27 Creed clauses in the OCA wording, exactly as the session-6 review's own script used them
# (wop-scratch/zz_main_20260915.py). Reusing that list is deliberate: the "38 creed-bearing sentences" this task must
# count is that script's figure, so the instrument must be the same one.
CREED_CLAUSES = [
    "i believe in one god", "maker of heaven and earth", "of all things visible and invisible", "only-begotten son of god",
    "begotten of the father before all ages", "light of light", "true god of true god", "begotten, not made",
    "of one essence with the father", "by whom all things were made", "for us men and for our salvation",
    "came down from heaven", "incarnate of the holy spirit and the virgin mary", "was crucified also for us under pontius pilate",
    "rose again on the third day", "ascended into heaven", "sits at the right hand of the father",
    "to judge the living and the dead", "whose kingdom shall have no end", "the lord, the giver of life",
    "who proceeds from the father", "who with the father and the son together is worshipped and glorified",
    "who spoke by the prophets", "one holy catholic and apostolic church", "one baptism for the remission of sins",
    "the resurrection of the dead", "the life of the world to come"]


def norm(t):
    return re.sub(r"\s+", " ", (t or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip().casefold()


def nearest(key, texts, n=90):
    """The registered wording nearest a miss: the longest common word-run between the clause and each registered text,
    with the window of the registered text around it. Evidence for the author, not a judgement."""
    best = None
    words = key.split()
    for t in texts:
        tw = t["key"].split()
        for size in range(len(words), 0, -1):
            if best and size <= best["shared_words"]:
                break
            for i in range(len(words) - size + 1):
                run = " ".join(words[i:i + size])
                pos = t["key"].find(run)
                if pos >= 0:
                    lo, hi = max(0, pos - n), min(len(t["key"]), pos + len(run) + n)
                    best = {"registry_id": t["registry_id"], "locator": t["locator"], "shared_words": size,
                            "shared_run": run, "registered_wording": ("…" if lo else "") + t["key"][lo:hi] + ("…" if hi < len(t["key"]) else "")}
                    break
            if best and best["shared_words"] == size:
                break
    return best


# ---------------------------------------------------------------- Task 1d
def task1d(reg):
    creeds = [t for t in reg.registered_creed_texts("Eastern Orthodox")]
    chunks = store.load_chunks("BSR-EO-01")
    sentences, bearing = 0, []
    for c in chunks:
        sents = [x for x in re.split(r"(?<=[.!?])\s+", c["text"]) if len(x.strip()) > 3]
        sentences += len(sents)
        for x in sents:
            hits = [k for k in CREED_CLAUSES if k in norm(x)]
            if hits:
                bearing.append({"locator": c["locator"], "sentence": x.strip(), "clauses": hits})
    matched, missed = [], []
    for b in bearing:
        ok = []
        for clause in b["clauses"]:
            # the clause AS IT STANDS in Hopko's sentence (his punctuation and case), which is what a locator would quote
            m = re.search(re.escape(clause).replace(r"\ ", r"\s+"), b["sentence"], re.I)
            quoted = m.group(0) if m else clause
            key = punct_key(quoted)
            hit = next((t for t in creeds if key and key in t["key"]), None)
            ok.append({"clause": clause, "quoted": quoted, "matched": bool(hit),
                       "registered_in": f"{hit['registry_id']} {hit['locator']}" if hit else None,
                       "nearest": None if hit else nearest(key, creeds)})
        b["clause_results"] = ok
        (matched if any(o["matched"] for o in ok) else missed).append(b)
    per_clause = {}
    for clause in CREED_CLAUSES:
        key = punct_key(clause)
        hit = next((t for t in creeds if key in t["key"]), None)
        per_clause[clause] = {"matched": bool(hit), "registered_in": f"{hit['registry_id']} {hit['locator']}" if hit else None,
                             "nearest": None if hit else nearest(key, creeds)}
    # The clause list is the review's own wording, so "does the sentence carry a listed clause" cannot by itself say
    # whether HOPKO's wording matches the registered text — it is the same list on both sides. This second measurement is
    # not circular: for each creed-bearing sentence, the LONGEST contiguous word-run of the sentence that stands verbatim
    # in a registered creed text. That is what a locator cutting ≤15 words from the sentence would actually have to hit.
    runs = []
    for b in bearing:
        w, best = punct_key(b["sentence"]).split(), ("", None)
        for size in range(len(w), 2, -1):
            for i in range(len(w) - size + 1):
                run = " ".join(w[i:i + size])
                t = next((t for t in creeds if run in t["key"]), None)
                if t:
                    best = (run, f"{t['registry_id']} {t['locator']}")
                    break
            if best[1]:
                break
        runs.append({"locator": b["locator"], "sentence": b["sentence"][:220], "longest_run": best[0],
                     "words": len(best[0].split()) if best[0] else 0, "registered_in": best[1]})
    share = len(missed) / len(bearing) if bearing else 0
    return {"longest_registered_run_per_sentence": runs,
            "longest_run_word_counts": dict(sorted(Counter(r["words"] for r in runs).items())),
            "sentences_with_a_run_of_3_or_more_words": sum(1 for r in runs if r["words"] >= 3),
            "sentences_with_no_run_of_3_or_more_words": sum(1 for r in runs if r["words"] < 3),
            "instrument": "the session-6 review's own 27-clause OCA-wording list (wop-scratch/zz_main_20260915.py), "
                          "re-run against the registered creed texts of the Eastern Orthodox branch under textutil.punct_key",
            "registered_creed_texts_searched": [f"{t['registry_id']} {t['locator']}" for t in creeds],
            "eo01_chunks": len(chunks), "eo01_sentences": sentences, "creed_bearing_sentences": len(bearing),
            "sentences_with_a_verbatim_registered_match": len(matched), "sentences_with_none": len(missed),
            "miss_share": round(share, 3),
            "trigger_fired": share >= 0.5,
            "trigger_rule": "R6-5 conditional_trigger: if a MEANINGFUL SHARE fail for translation differences, stop and "
                            "propose registering oca.org/orthodoxy/prayers/symbol-of-faith as a new CONCILIAR creed row",
            "per_clause": per_clause,
            "clauses_matched": sum(1 for v in per_clause.values() if v["matched"]), "clauses_total": len(CREED_CLAUSES),
            "misses": [{"locator": b["locator"], "sentence": b["sentence"][:300],
                        "clauses": [{k: o[k] for k in ("clause", "quoted", "nearest")} for o in b["clause_results"]]}
                       for b in missed],
            "matches": [{"locator": b["locator"], "sentence": b["sentence"][:200],
                         "matched": [o["registered_in"] for o in b["clause_results"] if o["matched"]]} for b in matched]}


# ---------------------------------------------------------------- Task 2a / 2b
def task2_texts(reg):
    out = {}
    for b in sorted({r["branch"] for r in reg.rows}):
        creeds, defs = reg.registered_creed_texts(b), reg.registered_definition_texts(b)
        out[b] = {
            "registered_creed_texts": [{"registry_id": t["registry_id"], "locator": t["locator"], "resolves_to": t["tier"],
                                        "chars": t["chars"]} for t in creeds],
            "registered_definition_texts": [{"registry_id": t["registry_id"], "locator": t["locator"], "resolves_to": t["tier"],
                                             "chars": t["chars"]} for t in defs],
            "chunk_level_creed_rows_in_this_branch": sorted(reg.chunk_level_creed_rows & {r["registry_id"] for r in reg.for_branch(b, citable_only=False)}),
            "chunk_level_creed_resolution_now_disabled_on": sorted(
                r["registry_id"] for r in reg.for_branch(b, citable_only=False)
                if r["registry_id"] not in reg.chunk_level_creed_rows
                and any(re.search(r"\b(creed|symbol of faith|nicene|athanasian|quicunque)\b", (c.get("locator") or ""), re.I)
                        for c in store.load_chunks(r["registry_id"]))),
        }
    return {"rule": "a citation resolves to the creed's (or the definition's) tier only when its phrase stands verbatim, "
                    "under textutil.punct_key, in a REGISTERED creed or definition TEXT of the SAME branch",
            "creed_text_rule": "the chunk's locator names a creed AND its row is either one of R6-5's "
                               "chunk_level_creed_resolution_allowed_rows or a row whose bare tier is CONCILIAR or "
                               "CONFESSIONAL (the creed printed as a text inside a conciliar or confessional standard). "
                               "A CATECHETICAL row is never a registered creed text — that is what clause 3 forbids.",
            "definition_text_rule": "the chunk's locator names a definition of faith / horos / confession of faith AND its "
                                    "row's bare tier is CONCILIAR, and the locator names no canon or anathema (R6-10)",
            "phrase_floor": {"min_words": 3, "min_chars": 12,
                             "why": "'begotten, not made' (3 words, 17 chars) and 'light of light' (3 words, 14) are the "
                                    "shortest clauses the author's own examples turn on"},
            "by_branch": out}


# ---------------------------------------------------------------- Task 2d / 3
def _slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def task2d(reg):
    """Re-resolve every stored candidate on the seven finished packets, and re-run the allocator on the new tiers."""
    changes, by_branch = [], {}
    for fn in sorted(os.listdir(PACKETS_DIR)):
        if not fn.endswith(".json"):
            continue
        pk = json.load(open(os.path.join(PACKETS_DIR, fn), encoding="utf-8"))
        branch = pk["branch"]
        pairs, groups = translation_pairs(reg, branch), speaks_for_groups(reg, branch)
        chunk_index = {}
        for r in reg.for_branch(branch, citable_only=False):
            for c in store.load_chunks(r["registry_id"]):
                chunk_index[(c["registry_id"], c["locator"])] = c
        b = by_branch.setdefault(branch, {"cards": len(pk["cards"]), "cards_changed": 0, "tier_changes": 0,
                                          "order_changes": 0, "slot_changes": 0})
        for card in pk["cards"]:
            seated = [e for e in card["candidates"]]
            if not seated:
                continue
            fresh, tier_moves = [], []
            for e in seated:
                ch = chunk_index.get((e["registry_id"], e["locator"]))
                res = reg.tier_resolution(e["registry_id"], ch, e["phrase"])
                if res["effective_tier"] != e.get("effective_tier"):
                    tier_moves.append({"candidate_id": e["candidate_id"], "registry_id": e["registry_id"],
                                       "from": e.get("effective_tier"), "to": res["effective_tier"], "why": res["why"],
                                       "adoption_disclosure": (res["adoption_disclosure"] or {}).get("text")})
                fresh.append(dict(e, effective_tier=res["effective_tier"]))
            before = [e["candidate_id"] for e in seated]
            alloc = allocate(fresh, pairs, groups=groups, same_text_rows=rulings.same_text_rows())
            after = list(alloc["kept"])
            order_changed = before != after
            slots_before = {e["candidate_id"]: e.get("role") for e in seated}
            slots_after = {cid: alloc["roles"][cid] for cid in after}
            slot_changed = any(slots_before.get(cid) != slots_after.get(cid) for cid in set(before) | set(after))
            if tier_moves or order_changed or slot_changed:
                b["cards_changed"] += 1
                b["tier_changes"] += len(tier_moves)
                b["order_changes"] += 1 if order_changed else 0
                b["slot_changes"] += 1 if slot_changed else 0
                changes.append({"branch": branch, "queue_id": card["queue_id"], "predicate": card["predicate"],
                                "tier_moves": tier_moves,
                                "order_before": before if order_changed else None, "order_after": after if order_changed else None,
                                "roles_before": slots_before if slot_changed else None,
                                "roles_after": slots_after if slot_changed else None})
    return {"note": "IN-MEMORY re-resolution for the author's review. No packet was rebuilt and nothing was released. "
                    "Model calls: none — the tier is a pure function of the registry, the rulings and the phrase.",
            "by_branch": by_branch, "cards_changed": len(changes), "changes": changes}


# ---------------------------------------------------------------- Task 3
CATECHETICAL_ROWS_PROPOSED_ADOPTED = {
    "BSR-RC-07": ("Compendium of the Catechism of the Catholic Church: approved by Benedict XVI, motu proprio, 28 June 2005",
                  "NOT VERIFIED THIS SESSION — proposed from the document's own front matter as printed on vatican.va; the "
                  "author ratifies, and the act must be cited before it is set"),
    "BSR-AN-02": ("BCP 1662 Catechism: the Book of Common Prayer 1662 annexed to the Act of Uniformity 1662",
                  "NOT VERIFIED THIS SESSION — proposed; a statute, not a synodal act, and whether that is 'the institution' "
                  "for this branch is itself a ruling"),
    "BSR-AN-04": ("An Outline of the Faith: the BCP 1979 adopted by the General Convention of The Episcopal Church",
                  "NOT VERIFIED THIS SESSION — proposed"),
    "BSR-AN-05": ("'To Be a Christian' (2020 approved edition): approved by the ACNA College of Bishops",
                  "NOT VERIFIED THIS SESSION — proposed; 'approved edition' is the row's own title, not a cited act"),
    "BSR-LU-03": ("Luther's Small Catechism, Creed First Article: the Small Catechism is a confession of the Book of Concord",
                  "NOT VERIFIED THIS SESSION — proposed; the CPH file is a publisher's edition of a confessional text"),
    "BSR-RP-03": ("Westminster Larger Catechism: adopted by the confessional act that types it CONFESSIONAL (OPC), the same "
                  "act the author named for BSR-RP-02",
                  "PROPOSED — the author named the Shorter Catechism and Luther's catechism material but not the Larger; it "
                  "is the same act. Clause 3 does not reach a CONFESSIONAL row, so its tier is unaffected either way."),
    "BSR-RP-05": ("Heidelberg Catechism (CRC/RCA 2011 joint translation): adopted by the CRC and RCA as a doctrinal standard",
                  "PROPOSED — as BSR-RP-03. Clause 3 does not reach a CONFESSIONAL row, so its tier is unaffected either way."),
}


def task3(reg):
    rows = []
    for r in sorted(reg.rows, key=lambda x: x["registry_id"]):
        rid = r["registry_id"]
        a = reg.adoption(rid)
        rows.append({"registry_id": rid, "branch": r["branch"], "authority_tier": r["authority_tier"],
                     "adoption_status": a["adoption_status"], "adoption_body_scope": a.get("adoption_body_scope") or None,
                     "adoption_act": a.get("adoption_act") or None, "source": a["source"],
                     "exposition_tier": reg.exposition_tier(rid),
                     "tier_moves": reg.exposition_tier(rid) != r["authority_tier"],
                     "card_disclosure": (reg.adoption_disclosure(rid) or {}).get("text")})
    unverified = [x["registry_id"] for x in rows if x["adoption_status"] == "UNVERIFIED"]
    return {"rank_assertion": reg.assert_second_tier_rank(),
            "rank_assertion_statement": f"APP CONFIG authority_tier_rank ranks {SECOND_TIER} directly below CATECHETICAL "
                                        f"({' | '.join(reg.tier_rank_list)}); APP CONFIG was not changed",
            "policy": reg.adoption_policy, "migration": reg.adoption_migration,
            "scope_note": "clause 3 reaches CATECHETICAL rows. A CONFESSIONAL row left UNVERIFIED is NOT demoted: the "
                          "confessional act that typed it is its adoption, and the session-6 review states clause 3's reach "
                          "as 'catechetical and expository rows'. Such rows are listed as ADOPTED proposals instead.",
            "unverified_count": len(unverified), "unverified": unverified,
            "rows_whose_tier_moves": [x for x in rows if x["tier_moves"]],
            "eastern_orthodox_catechetical_rows": [x for x in rows if x["branch"] == "Eastern Orthodox"
                                                   and bare_tier(x["authority_tier"]) == "CATECHETICAL"],
            "adopted_proposals": [{"registry_id": rid, "current": reg.adoption(rid)["adoption_status"],
                                   "proposed_adoption_act": act, "caveat": caveat,
                                   "effect_if_ratified": (f"{reg.exposition_tier(rid)} -> {reg.by_id[rid]['authority_tier']}"
                                                          if reg.exposition_tier(rid) != reg.by_id[rid]["authority_tier"]
                                                          else "no tier change (clause 3 does not reach this row)")}
                                  for rid, (act, caveat) in CATECHETICAL_ROWS_PROPOSED_ADOPTED.items() if rid in reg.by_id],
            "rows": rows}


def main():
    reg = Registry()
    for name, fn in (("task1d-hopko-creed-match", task1d), ("task2-registered-texts", task2_texts),
                     ("task2d-card-changes", task2d), ("task3-adoption", task3)):
        d = fn(reg)
        p = os.path.join(HERE, f"{name}.json")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"== {name}: {p}")
        if name == "task1d-hopko-creed-match":
            print(f"   EO-01 {d['eo01_sentences']} sentences, {d['creed_bearing_sentences']} creed-bearing; "
                  f"{d['sentences_with_a_verbatim_registered_match']} match a registered creed text verbatim, "
                  f"{d['sentences_with_none']} do not ({d['miss_share']:.0%}); clauses {d['clauses_matched']}/{d['clauses_total']}; "
                  f"TRIGGER {'FIRED' if d['trigger_fired'] else 'did not fire'}")
            print(f"   longest registered run per creed-bearing sentence: {d['longest_run_word_counts']}; "
                  f"{d['sentences_with_a_run_of_3_or_more_words']} of {d['creed_bearing_sentences']} carry a run of 3+ words")
        if name == "task2d-card-changes":
            print(f"   {d['cards_changed']} card(s) changed: " + json.dumps(d["by_branch"], ensure_ascii=False))
        if name == "task3-adoption":
            print(f"   UNVERIFIED {d['unverified_count']}: {d['unverified']}")
            for x in d["rows_whose_tier_moves"]:
                print(f"   tier moves {x['registry_id']} [{x['branch']}]: {x['authority_tier']} -> {x['exposition_tier']} "
                      f"({x['adoption_status']}) — card says \"{x['card_disclosure']}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
