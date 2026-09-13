"""Card allocation — the ONE place that decides which surviving candidates a cell's card carries
(2026-09-12, packet-shape fixes 1a–1c adopted by the author after the Roman Catholic packet).

Used by the packet builder (packets.py) and, since fix 1c, by the cell runner BEFORE the coder
runs, so the coder is spent only on candidates that will actually reach the card. Both callers
pass the same minimal candidate dicts, so the two allocations cannot diverge.

Order of operations on a cell's surviving (verifier-accepted) candidates:

  1. fallback guard      a fallback-tier citation never renders beside a non-fallback witness
  2. translation pairing (1b) a witness row that is the English translation of a controlling
                         row on the same document does not compete for a slot: its candidate is
                         attached to the controlling candidate (same chapter where the locators
                         say so, else the controlling row's best) as `english_witness`, and the
                         controlling entry is named CONTROLLING
  3. witness-only guard  a cell may not rest on witness rows alone
  4. tier allocation     higher effective tier first; the cap is filled tier by tier so a second
                         candidate from the winning tier never displaces the only witness from
                         another tier; WITHIN a tier every non-witness row sorts before any
                         witness row (1a: reception TRANSLATION_WITNESS, or an authority_tier
                         marked "(translation)" or "witness")
  5. cap                 MAX_CANDIDATES kept; lower-tier survivors marked corroborating

The function is pure: it returns which candidate ids are kept, paired, suppressed or cut, with
the reason for each, and never touches model calls or files."""
import re

from .config import MAX_CANDIDATES
from .registry import tier_rank

_ROMAN = re.compile(r"\b(?:caput|chapter|canon|cap\.|ch\.)\s+([IVXLC]+|\d+)", re.I)
_DOC_STOP = {"the", "and", "of", "on", "in", "as", "by", "to", "a", "an", "witness", "translation", "english", "latin",
             "official", "text", "lineage", "transcription", "hosted", "vatican", "sourcebook", "creed", "creeds",
             "council", "councils", "definition", "definitions", "faith", "received", "witnessed", "clause", "page",
             "new", "advent", "fordham", "ewtn", "npnf2", "percival", "row", "floor", "resolves", "conciliar", "confessional"}
_RID = re.compile(r"\bBSR-[A-Z]{2}-\d{2}\b")


def is_witness_like(entry):
    """1a: the sort-last flag. True for a candidate flagged WITNESS (registry.is_witness), for reception
    TRANSLATION_WITNESS, or for an authority_tier marked "(translation)" / "witness"."""
    tier = (entry.get("authority_tier") or entry.get("effective_tier") or "").casefold()
    return bool(entry.get("witness")) or (entry.get("reception_scope") or "").upper() == "TRANSLATION_WITNESS" \
        or "(translation)" in tier or "translation)" in tier or "witness" in tier


def _doc_tokens(title):
    t = re.sub(r"[^A-Za-z0-9 ]", " ", (title or "").casefold())
    return {w for w in t.split() if len(w) >= 4 and w not in _DOC_STOP}


def translation_pairs(registry, branch):
    """{witness_rid: controlling_rid} for one branch, DERIVED from the registry (never hard-coded):
      (1) a witness row whose reception_note / author_note / draft_recommendation names one non-witness
          registry_id of the same branch pairs with it (BSR-EO-11 -> BSR-EO-06: "BSR-EO-06 remains the
          controlling conciliar text");
      (2) else the non-witness row of the same branch whose standard_title shares a document-name token
          with the witness row's title (BSR-RC-03 "*Dei Filius* English (EWTN)" -> BSR-RC-02 "Vatican I,
          *Dei Filius* (Latin, official)"; BSR-RC-05 "Fourth Lateran (Fordham)" -> BSR-RC-04).
    A witness row with no such controlling row is left unpaired and keeps the plain witness rules."""
    rows = registry.for_branch(branch, include_fallback=True, citable_only=False)
    controlling = [r for r in rows if not registry.is_witness(r["registry_id"])]
    out = {}
    for w in rows:
        wid = w["registry_id"]
        if not registry.is_witness(wid):
            continue
        blob = " ".join(str(w.get(k) or "") for k in ("reception_note", "author_note", "draft_recommendation", "standard_title"))
        named = [rid for rid in _RID.findall(blob) if rid != wid and any(c["registry_id"] == rid for c in controlling)]
        if named:
            out[wid] = named[0]
            continue
        wt = _doc_tokens(w.get("standard_title"))
        best, best_n = None, 0
        for c in controlling:
            n = len(wt & _doc_tokens(c.get("standard_title")))
            if n > best_n:
                best, best_n = c["registry_id"], n
        if best:
            out[wid] = best
    return out


def translation_pair_evidence(registry, branch):
    """The same derivation as translation_pairs(), with the evidence each pair rests on, for the author
    to ratify pair by pair (2026-09-13): rule NAMED_IN_NOTE (the witness row's own note / author note /
    draft recommendation names the controlling row) or SHARED_TITLE_TOKEN (the only link is a document
    name shared by the two standard_titles — the weaker evidence; BSR-EO-13 -> BSR-EO-06 is this kind)."""
    rows = registry.for_branch(branch, include_fallback=True, citable_only=False)
    by_id = {r["registry_id"]: r for r in rows}
    controlling = [r for r in rows if not registry.is_witness(r["registry_id"])]
    out = []
    for w in rows:
        wid = w["registry_id"]
        if not registry.is_witness(wid):
            continue
        rec = {"branch": branch, "witness": wid, "witness_title": w.get("standard_title"), "witness_tier": w.get("authority_tier"),
               "witness_reception": w.get("reception_scope"), "controlling": None, "rule": None, "evidence": None}
        blob_fields = [("reception_note", w.get("reception_note")), ("author_note", w.get("author_note")),
                       ("draft_recommendation", w.get("draft_recommendation")), ("standard_title", w.get("standard_title"))]
        named = None
        for field, text in blob_fields:
            for rid in _RID.findall(str(text or "")):
                if rid != wid and any(c["registry_id"] == rid for c in controlling):
                    named = (rid, field, str(text)); break
            if named:
                break
        if named:
            rid, field, text = named
            i = text.find(rid)
            rec.update({"controlling": rid, "controlling_title": by_id[rid].get("standard_title"), "controlling_tier": by_id[rid].get("authority_tier"),
                        "rule": "NAMED_IN_NOTE", "evidence": f"{field}: …{text[max(0, i - 90):i + 110]}…"})
            out.append(rec); continue
        wt = _doc_tokens(w.get("standard_title"))
        best, best_n, best_tokens = None, 0, set()
        for c in controlling:
            shared = wt & _doc_tokens(c.get("standard_title"))
            if len(shared) > best_n:
                best, best_n, best_tokens = c["registry_id"], len(shared), shared
        if best:
            rec.update({"controlling": best, "controlling_title": by_id[best].get("standard_title"), "controlling_tier": by_id[best].get("authority_tier"),
                        "rule": "SHARED_TITLE_TOKEN", "shared_tokens": sorted(best_tokens),
                        "evidence": f"standard_title tokens shared: {sorted(best_tokens)} — witness {w.get('standard_title')!r} / controlling {by_id[best].get('standard_title')!r}",
                        "weakness": "a shared document name in two titles is the only link; nothing in the row text names the controlling row"})
        else:
            rec.update({"rule": "UNPAIRED", "evidence": "no controlling row named and no shared document-name token"})
        out.append(rec)
    return out


def _division_key(locator):
    m = _ROMAN.search(locator or "")
    return m.group(1).upper() if m else None


def allocate(cands, pairs=None, cap=MAX_CANDIDATES):
    """cands: surviving candidates as dicts carrying candidate_id, registry_id, fallback_tier, witness,
    effective_tier, authority_tier, reception_scope, locator (and anything else; untouched).
    Returns {"kept": [ids in card order], "roles": {id: "CONTROLLING"|"CORROBORATING"|"PRIMARY"},
             "english_witness": {controlling_id: witness_id}, "dropped": {id: reason}, "witness_only": [ids],
             "corroborating_lower_tier": {id: bool}}"""
    pairs = pairs or {}
    by_id = {c["candidate_id"]: c for c in cands}
    order = [c["candidate_id"] for c in cands]
    dropped, witness_link = {}, {}
    live = list(order)
    # 1. fallback guard
    if any(not by_id[i].get("fallback_tier") for i in live):
        for i in list(live):
            if by_id[i].get("fallback_tier"):
                dropped[i] = "fallback-tier witness suppressed: a non-fallback standard yielded a candidate"
                live.remove(i)
    # 2. translation pairing (1b)
    for i in list(live):
        w = by_id[i]
        ctrl_rid = pairs.get(w["registry_id"])
        if not ctrl_rid or not is_witness_like(w):
            continue
        ctrls = [j for j in live if by_id[j]["registry_id"] == ctrl_rid and j != i]
        if not ctrls:
            continue
        wk = _division_key(w.get("locator"))
        same = [j for j in ctrls if wk and _division_key(by_id[j].get("locator")) == wk]
        target = (same or ctrls)[0]
        if target in witness_link:            # one English witness per controlling entry; a second stays a plain witness
            continue
        witness_link[target] = i
        dropped[i] = f"paired as the English witness of {target} (controlling {ctrl_rid}); shown on that card, not as a competing candidate"
        live.remove(i)
    # 3. witness-only guard
    witness_only = []
    if live and all(is_witness_like(by_id[i]) for i in live):
        witness_only = list(live)
        for i in live:
            dropped[i] = "WITNESS_ONLY: a cell may not rest on a translation/witness row alone (no controlling text survived)"
        live = []
    # 4. tier allocation, witness rows last within a tier (1a), then the cap tier by tier

    def rank(i):
        c = by_id[i]
        return tier_rank(c.get("effective_tier") or c.get("authority_tier"))

    def sort_key(i):
        return (rank(i), 1 if is_witness_like(by_id[i]) else 0, order.index(i))

    ranked = sorted(live, key=sort_key)
    seen = {}
    for i in ranked:
        seen.setdefault(rank(i), []).append(i)
    queues = [seen[k] for k in sorted(seen)]
    by_tier = []
    while queues:
        queues = [q for q in queues if q]
        for q in list(queues):
            by_tier.append(q.pop(0))
    kept = sorted(by_tier[:cap], key=sort_key)
    for i in by_tier[cap:]:
        dropped[i] = "candidate cap reached after tier allocation"
    top = rank(kept[0]) if kept else None
    corr = {i: bool(top is not None and rank(i) > top) for i in kept}
    roles = {}
    for i in kept:
        roles[i] = "CONTROLLING" if i in witness_link else ("CORROBORATING" if corr[i] else "PRIMARY")
    # a paired witness whose controlling entry was then cut by the cap goes back to being a cut witness
    for ctrl, w in list(witness_link.items()):
        if ctrl not in kept:
            dropped[w] = f"paired witness of {ctrl}, which the candidate cap cut"
    return {"kept": kept, "roles": roles, "english_witness": {c: w for c, w in witness_link.items() if c in kept},
            "dropped": dropped, "witness_only": witness_only, "corroborating_lower_tier": corr}
