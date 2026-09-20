"""Session 14, phase 4: the AN-04 / AN-06 split, cell by cell — every seat, tier, lead, witness and disclosure change.

Reads two sandbox packet directories (before and after the split) and reports, for every card that mentions a
Historical Documents citation, exactly what happened to it. Also verifies the seven seated Anglican entries the
session 13 report names (Q-237, Q-277, Q-413, Q-421, Q-429, Q-437, Q-453) and reports each one's outcome.

No model calls, no network.

  python data-sources/sjn/recovery-runs/session14/an06_effects.py <before_dir> <after_dir>
      writes session14/an06-cell-by-cell.json and prints the table
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEATED_PER_SESSION13 = ["Q-237", "Q-277", "Q-413", "Q-421", "Q-429", "Q-437", "Q-453"]
HD = "Historical Documents"


def entries(card):
    """(role, entry) for every place a candidate can sit on a card, parallel witnesses included."""
    for e in card.get("candidates") or []:
        yield "seat", e
        for w in e.get("same_text_parallel_witnesses") or []:
            yield "parallel_witness", w
        if e.get("english_witness"):
            yield "english_witness", e["english_witness"]
    for e in card.get("rejections") or []:
        yield "rejection", e
    for e in card.get("witness_only_candidates") or []:
        yield "witness_only", e
    for e in card.get("review_queue_held") or []:
        yield "review_queue_held", e


def view(card):
    out = {}
    for role, e in entries(card):
        cid = e.get("candidate_id")
        if not cid:
            continue
        out[cid] = {"role": role, "registry_id": e.get("registry_id"), "locator": e.get("locator"),
                    "effective_tier": e.get("effective_tier"),
                    "seat_index": ([x["candidate_id"] for x in card.get("candidates") or []].index(cid) + 1
                                   if role == "seat" else None),
                    "stage": e.get("stage"), "rule": e.get("rule"),
                    "disclosure": (e.get("adoption_disclosure") or {}).get("text"),
                    "awaits_scope_ruling": bool(e.get("awaits_scope_ruling"))}
    return out


def main():
    before_dir, after_dir = sys.argv[1], sys.argv[2]
    ob = json.load(open(os.path.join(before_dir, "anglican.json"), encoding="utf-8"))
    na = json.load(open(os.path.join(after_dir, "anglican.json"), encoding="utf-8"))
    obc = {c["queue_id"]: c for c in ob["cards"]}
    nac = {c["queue_id"]: c for c in na["cards"]}
    rows = []
    for qid in sorted(set(obc) | set(nac)):
        o, n = view(obc[qid]), view(nac[qid])
        touched = {cid for cid, v in list(o.items()) + list(n.items()) if HD in str(v.get("locator") or "")}
        if not touched:
            continue
        lead_o = ([e["candidate_id"] for e in obc[qid].get("candidates") or []] or [None])[0]
        lead_n = ([e["candidate_id"] for e in nac[qid].get("candidates") or []] or [None])[0]
        rows.append({
            "queue_id": qid,
            "predicate": nac[qid].get("predicate"),
            "seats_before": [e["candidate_id"] for e in obc[qid].get("candidates") or []],
            "seats_after": [e["candidate_id"] for e in nac[qid].get("candidates") or []],
            "seats_changed": [e["candidate_id"] for e in obc[qid].get("candidates") or []]
                             != [e["candidate_id"] for e in nac[qid].get("candidates") or []],
            "lead_before": lead_o, "lead_after": lead_n, "lead_changed": lead_o != lead_n,
            "card_status": [obc[qid].get("status"), nac[qid].get("status")],
            "reviewed_offered": [(obc[qid].get("empty_result_option") or {}).get("offered"),
                                 (nac[qid].get("empty_result_option") or {}).get("offered")],
            "historical_document_entries": {
                cid: {"before": o.get(cid), "after": n.get(cid)} for cid in sorted(touched)},
        })
    summary = {"cards_touched": len(rows),
               "seats_changed": sorted(r["queue_id"] for r in rows if r["seats_changed"]),
               "leads_changed": sorted(r["queue_id"] for r in rows if r["lead_changed"]),
               "session13_seated_list": SEATED_PER_SESSION13,
               "session13_seated_verified": {}}
    for qid in SEATED_PER_SESSION13:
        r = next((x for x in rows if x["queue_id"] == qid), None)
        if r is None:
            summary["session13_seated_verified"][qid] = "NOT FOUND among the cards this split touched"
            continue
        seated_before = [cid for cid, v in r["historical_document_entries"].items() if (v["before"] or {}).get("role") == "seat"]
        after = {cid: (v["after"] or {}).get("role") for cid, v in r["historical_document_entries"].items() if cid in seated_before}
        summary["session13_seated_verified"][qid] = {"was_seated": seated_before, "outcome": after}
    out = {"what": __doc__.split("\n\n")[0], "before": before_dir, "after": after_dir,
           "chunk_moved_to_another_row": na.get("chunk_moved_to_another_row"),
           "summary": summary, "cards": rows}
    with open(os.path.join(HERE, "an06-cell-by-cell.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"cards mentioning a Historical Documents citation: {len(rows)}")
    print(f"seats changed: {summary['seats_changed']}")
    print(f"leads changed: {summary['leads_changed']}")
    for r in rows:
        print(f"\n{r['queue_id']} {r['predicate']}  status {r['card_status'][0]} -> {r['card_status'][1]}"
              f"  reviewed_offered {r['reviewed_offered'][0]} -> {r['reviewed_offered'][1]}")
        if r["seats_changed"]:
            print(f"   SEATS {r['seats_before']} -> {r['seats_after']}")
        if r["lead_changed"]:
            print(f"   LEAD  {r['lead_before']} -> {r['lead_after']}")
        for cid, v in r["historical_document_entries"].items():
            b, a = v["before"] or {}, v["after"] or {}
            print(f"   {cid}")
            print(f"      role  {b.get('role')} (seat {b.get('seat_index')}) -> {a.get('role')} (seat {a.get('seat_index')})"
                  + (f" [{a.get('rule')}]" if a.get("rule") else ""))
            print(f"      row   {b.get('registry_id')} -> {a.get('registry_id')}")
            print(f"      tier  {b.get('effective_tier')} -> {a.get('effective_tier')}")
            if b.get("awaits_scope_ruling") != a.get("awaits_scope_ruling"):
                print(f"      awaits_scope_ruling {b.get('awaits_scope_ruling')} -> {a.get('awaits_scope_ruling')}")
            if (b.get("disclosure") or "")[:40] != (a.get("disclosure") or "")[:40]:
                print(f"      disc  {(b.get('disclosure') or '')[:70]!r}\n         ->  {(a.get('disclosure') or '')[:70]!r}")
    print("\n--- the seven session 13 seats ---")
    for qid, v in summary["session13_seated_verified"].items():
        print(" ", qid, json.dumps(v, ensure_ascii=False))


if __name__ == "__main__":
    main()
