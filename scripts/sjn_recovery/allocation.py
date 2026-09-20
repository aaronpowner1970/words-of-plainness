"""Card allocation — the ONE place that decides which surviving candidates a cell's card carries
(2026-09-12, packet-shape fixes 1a–1c adopted by the author after the Roman Catholic packet;
2026-09-13 session 4, the candidate-slot diversity rule adopted after the Reformed packet).

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
                         another tier. WITHIN a tier (session 4, RATIFIED): candidates are grouped
                         by the body the row speaks for (`speaks_for`, resolved — see
                         speaks_for_groups), and NO GROUP TAKES A SECOND SLOT UNTIL EVERY GROUP WITH
                         A SURVIVING CANDIDATE HAS TAKEN A FIRST. Groups are ranked for their first
                         slot by the existing keys — non-witness before witness (1a), then the
                         locator's floor claim (FULL before PARTIAL), and only as the last resort by
                         registry row order, which orders presentation but never decides which body
                         is heard. Then each group's second candidate, in the same group order, etc.
  5. one text, one slot  (session 6, R6-4, RATIFIED) walking the slot order, a candidate whose phrase is
                         textually identical — casefolded, whitespace and punctuation normalised
                         (same_text_key) — to a candidate ALREADY SEATED takes no slot, whatever its
                         speaks_for group or row (Q-243: one row twice), and is recorded on the seated
                         entry as a parallel witness with its own registry_id. A row declared to
                         publish the same text in DIFFERENT wording (rulings.same_text_rows:
                         BSR-EO-14 -> BSR-EO-07) is a parallel witness of the declared row's seated
                         candidate whatever its wording, and yields the slot to it whatever the order
     5a. the original holds the seat (session 12, R6-41, Codex B3(a); applied to the tier sequences before the cap)
                         a candidate RAISED by phrase-level resolution (R6-5/R6-10) because its phrase is verbatim
                         in a registered text that is itself a candidate of the cell (same registry_id and locator,
                         same tier) yields: the original takes the quoting candidate's place (the seat and the lead)
                         where that is earlier than its own, and the quoting candidate takes no slot and is recorded on
                         the original as a parallel witness (rule ORIGINAL_HOLDS_SEAT). Where no candidate of the cell
                         sits in the registered text the quoting candidate keeps its seat at the raised tier. The
                         candidate carries the texts that raised it as `raised_by_registered_text` (Registry.raised_by)
  6. cap                 MAX_CANDIDATES kept; lower-tier survivors marked corroborating

The function is pure: it returns which candidate ids are kept, paired, suppressed or cut, with
the reason for each, and never touches model calls or files."""
import re
import unicodedata

from .config import MAX_CANDIDATES
from .registry import tier_rank

_ROMAN = re.compile(r"\b(?:caput|chapter|canon|cap\.|ch\.)\s+([IVXLC]+|\d+)", re.I)
_DOC_STOP = {"the", "and", "of", "on", "in", "as", "by", "to", "a", "an", "witness", "translation", "english", "latin",
             "official", "text", "lineage", "transcription", "hosted", "vatican", "sourcebook", "creed", "creeds",
             "council", "councils", "definition", "definitions", "faith", "received", "witnessed", "clause", "page",
             "new", "advent", "fordham", "ewtn", "npnf2", "percival", "row", "floor", "resolves", "conciliar", "confessional"}
_RID = re.compile(r"\bBSR-[A-Z]{2}-\d{2}\b")
FLOOR_ORDER = {"FULL": 0, "PARTIAL": 1, "WORD_ONLY": 2}
_AS_ABOVE = re.compile(r"^\s*(as above|same as above|ditto|idem|\"|″|〃)\s*\.?\s*$", re.I)
_NO_BODY = re.compile(r"^\s*[-—–]?\s*$")


def is_witness_like(entry):
    """1a: the sort-last flag. True for a candidate flagged WITNESS (registry.is_witness), for reception
    TRANSLATION_WITNESS, or for an authority_tier marked "(translation)" / "witness"."""
    tier = (entry.get("authority_tier") or entry.get("effective_tier") or "").casefold()
    return bool(entry.get("witness")) or (entry.get("reception_scope") or "").upper() == "TRANSLATION_WITNESS" \
        or "(translation)" in tier or "translation)" in tier or "witness" in tier


def _doc_tokens(title):
    t = re.sub(r"[^A-Za-z0-9 ]", " ", (title or "").casefold())
    return {w for w in t.split() if len(w) >= 4 and w not in _DOC_STOP}


# ---------------------------------------------------------------- speaks_for groups (session 4)
def normalize_body(text):
    """The body a `speaks_for` value names, for grouping: the text before the first semicolon (what follows
    is a qualification — "CRCNA and RCA; Dort required subscription", "Universal Church; published by the Holy
    See's Dicastery …"), parentheticals stripped ("Church of England (appointed in the BCP)"), casefolded,
    trailing punctuation dropped."""
    t = (text or "").split(";")[0]
    t = re.sub(r"\s+\([^)]*\)", " ", t)          # a parenthetical after whitespace is a qualification; "PC(USA)" is a name
    t = re.sub(r"[\s.,:]+$", "", re.sub(r"\s+", " ", t)).strip().casefold()
    return t


def speaks_for_groups(registry, branch):
    """{registry_id: {"raw", "group", "rule"}} for one branch, derived from the registry sheet in row order:
      AS_ABOVE_PREVIOUS_ROW   "as above" (and the like) resolves to the group of the nearest preceding row of the
                              branch that names a body (BSR-RP-02 / BSR-RP-03 -> BSR-RP-01's "OPC and Westminster churches")
      BODY_BEFORE_SEMICOLON   the value carried a qualification after a semicolon; the body before it is the group
      PARENTHETICAL_STRIPPED  a parenthetical qualification was stripped
      VERBATIM                the casefolded value is the group as written
      WITNESS_OF_CONTROLLING_ROW  a translation witness speaks for the body its controlling row speaks for (BSR-RC-03 ->
                              BSR-RC-02's "Universal Church"): it is the same body read in English, so it never takes a
                              slot as a "second body" ahead of that body's own second candidate (the pairs come from
                              translation_pairs — derived, and listed in every packet header for ratification)
      WITNESS_ROW_OWN_GROUP   a witness row with no controlling row and no body ("—"): its own group; it sorts last (1a)
      NO_BODY_OWN_GROUP       an empty / dash value on a non-witness row: its own group, reported for the author"""
    rows = registry.for_branch(branch, include_fallback=True, citable_only=False)
    try:
        pairs = translation_pairs(registry, branch)
    except Exception:
        pairs = {}
    out, prev_group = {}, None
    for r in rows:
        rid, raw = r["registry_id"], str(r.get("speaks_for") or "")
        rec = {"raw": raw, "group": None, "rule": None}
        if registry.is_witness(rid) and pairs.get(rid):
            ctrl = pairs[rid]
            ctrl_group = out.get(ctrl, {}).get("group") or normalize_body(str(next((x.get("speaks_for") for x in rows if x["registry_id"] == ctrl), "") or "")) or ctrl
            rec.update(group=ctrl_group, rule="WITNESS_OF_CONTROLLING_ROW", controlling=ctrl)
        elif registry.is_witness(rid) and (_NO_BODY.match(raw) or _AS_ABOVE.match(raw)):
            rec.update(group=rid, rule="WITNESS_ROW_OWN_GROUP")
        elif _AS_ABOVE.match(raw):
            if prev_group:
                rec.update(group=prev_group, rule="AS_ABOVE_PREVIOUS_ROW")
            else:
                rec.update(group=rid, rule="NO_BODY_OWN_GROUP")
        elif _NO_BODY.match(raw):
            rec.update(group=rid, rule="NO_BODY_OWN_GROUP")
        else:
            body = normalize_body(raw)
            if ";" in raw:
                rule = "BODY_BEFORE_SEMICOLON"
            elif re.search(r"\s+\(", raw):
                rule = "PARENTHETICAL_STRIPPED"
            else:
                rule = "VERBATIM"
            rec.update(group=body or rid, rule=rule if body else "NO_BODY_OWN_GROUP")
        out[rid] = rec
        if rec["rule"] not in ("WITNESS_ROW_OWN_GROUP", "NO_BODY_OWN_GROUP", "WITNESS_OF_CONTROLLING_ROW"):
            prev_group = rec["group"]
    return out


def group_map(groups):
    """{registry_id: group} from speaks_for_groups() output (or an already flat map)."""
    if not groups:
        return {}
    return {rid: (g["group"] if isinstance(g, dict) else g) for rid, g in groups.items()}


def declared_same_text_alternate(rid):
    """Session 14 (R6-50): is this row DECLARED the same text as another (rulings.same_text_rows)?

    One row, one relationship. A declared same-text alternate relates to its controlling row under the R6-4 guard —
    one text, one slot, the alternate recorded as a parallel witness — and must not ALSO be pulled into rule 1b's
    English-translation pairing, which would make it someone's "English witness" and pair it with a different row
    again. BSR-AN-06 is the first row where the two rules would have collided: R6-50 declares it one text with
    BSR-AN-03, while its title shares "The Episcopal Church BCP 1979" with BSR-AN-04, the row it was split out of."""
    from . import rulings
    try:
        return rid in rulings.same_text_rows()
    except SystemExit:
        raise
    except Exception:
        return False


def translation_pairs(registry, branch):
    """{witness_rid: controlling_rid} for one branch, DERIVED from the registry (never hard-coded):
      (1) a witness row whose reception_note / author_note / draft_recommendation names one non-witness
          registry_id of the same branch pairs with it (BSR-EO-11 -> BSR-EO-06: "BSR-EO-06 remains the
          controlling conciliar text");
      (2) else the non-witness row of the same branch whose standard_title shares a document-name token
          with the witness row's title (BSR-RC-03 "*Dei Filius* English (EWTN)" -> BSR-RC-02 "Vatican I,
          *Dei Filius* (Latin, official)"; BSR-RC-05 "Fourth Lateran (Fordham)" -> BSR-RC-04).
    A witness row with no such controlling row is left unpaired and keeps the plain witness rules.
    Session 14 (R6-50): a witness row DECLARED the same text as another is never paired here (see
    declared_same_text_alternate above); BSR-AN-06 relates to BSR-AN-03 as one TEXT under the R6-4 same-text guard,
    not as a translation of BSR-AN-04, whose title it shares three words with."""
    rows = registry.for_branch(branch, include_fallback=True, citable_only=False)
    controlling = [r for r in rows if not registry.is_witness(r["registry_id"])]
    out = {}
    for w in rows:
        wid = w["registry_id"]
        if not registry.is_witness(wid) or declared_same_text_alternate(wid):
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
        if declared_same_text_alternate(wid):
            out.append({"branch": branch, "witness": wid, "witness_title": w.get("standard_title"),
                        "witness_tier": w.get("authority_tier"), "witness_reception": w.get("reception_scope"),
                        "controlling": None, "rule": "DECLARED_SAME_TEXT_ALTERNATE",
                        "evidence": "an author ruling declares this row the same TEXT as another (R6-4's guard, declared by "
                                    "R6-50 for BSR-AN-06 -> BSR-AN-03). One row, one relationship: it takes no slot beside "
                                    "its controlling row and is recorded as a parallel witness, so rule 1b's "
                                    "English-translation pairing does not also claim it"})
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


def same_text_key(phrase):
    """R6-4: the phrase as compared by the one-text-one-slot guard — NFKC, casefolded, every punctuation and symbol
    character (any quote or dash style) removed, whitespace collapsed. Nothing else: a different word, a different word
    order or a spelling variant is a different text.

    Session 7: the implementation moved to textutil.punct_key, so R6-4's guard and R6-5/R6-10's phrase-level creed and
    definition resolution compare on ONE key. The behaviour is unchanged."""
    from .textutil import punct_key
    return punct_key(phrase)


def allocate(cands, pairs=None, cap=MAX_CANDIDATES, groups=None, same_text_rows=None):
    """cands: surviving candidates as dicts carrying candidate_id, registry_id, fallback_tier, witness,
    effective_tier, authority_tier, reception_scope, locator, floor_claim, phrase (and anything else; untouched).
    groups: {registry_id: group} (speaks_for_groups / group_map); a row absent from it is its own group.
    same_text_rows: {alternate_rid: controlling_rid} (rulings.same_text_rows); None reads the rulings file.
    Returns {"kept": [ids in card order], "roles": {id: "CONTROLLING"|"CORROBORATING"|"PRIMARY"},
             "english_witness": {controlling_id: witness_id}, "dropped": {id: reason}, "witness_only": [ids],
             "corroborating_lower_tier": {id: bool}, "groups": {id: group}, "slot_order": {id: n},
             "parallel_witnesses": {seated_id: [{"candidate_id", "registry_id", "rule"}]}}"""
    if same_text_rows is None:
        from .rulings import same_text_declarations
        declarations = same_text_declarations()
        same_text_rows = {rid: d["same_text_as"] for rid, d in declarations.items()}
    else:
        declarations = {alt: {"same_text_as": ctrl} for alt, ctrl in same_text_rows.items()}
    pairs = pairs or {}
    gmap = group_map(groups)
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
    # 4. tier allocation; within a tier, the speaks_for group rule (session 4), then the cap tier by tier

    def rank(i):
        c = by_id[i]
        return tier_rank(c.get("effective_tier") or c.get("authority_tier"))

    def group_of(i):
        rid = by_id[i]["registry_id"]
        return gmap.get(rid, rid)

    def member_key(i):
        """The existing keys, inside a tier: non-witness before witness (1a), floor claim, registry/slot order last."""
        return (1 if is_witness_like(by_id[i]) else 0, FLOOR_ORDER.get(by_id[i].get("floor_claim"), 9), order.index(i))

    tiers = {}
    for i in live:
        tiers.setdefault(rank(i), []).append(i)
    tier_sequences = []
    for rk in sorted(tiers):
        members = sorted(tiers[rk], key=member_key)
        grouped = {}
        for i in members:                       # members already sorted: each group's list is in member_key order
            grouped.setdefault(group_of(i), []).append(i)
        group_order = sorted(grouped, key=lambda g: member_key(grouped[g][0]))
        seq = []
        depth = 0
        while True:                             # round 1: every group's first; round 2: every group's second; …
            got = False
            for g in group_order:
                if depth < len(grouped[g]):
                    seq.append(grouped[g][depth]); got = True
            if not got:
                break
            depth += 1
        tier_sequences.append(seq)
    # 5a. the original holds the seat (session 12, R6-41, Codex B3(a)). A candidate RAISED by phrase-level resolution
    # (`raised_by_registered_text`: the registered texts, {registry_id, locator}, whose tier it resolved to) yields to a live
    # candidate located IN one of those texts at the same tier: the original takes the quoting candidate's place in the
    # tier sequence if that is earlier than its own (the seat and the lead), and the quoting candidate takes no slot and is
    # recorded on the original as a parallel witness. Where no candidate of the cell sits in the registered text, nothing
    # changes: the quoting candidate keeps its seat at the raised tier.
    original_of = {}
    loc_index = {}
    for i in live:
        loc_index.setdefault((by_id[i]["registry_id"], by_id[i].get("locator")), []).append(i)
    for seq in tier_sequences:
        for i in list(seq):
            if i not in seq:
                continue
            hits = [h for h in by_id[i].get("raised_by_registered_text") or [] if tier_rank(h.get("tier")) == rank(i)]
            found = []                                    # (original candidate, the registered text it sits in)
            for h in hits:
                for j in loc_index.get((h.get("registry_id"), h.get("locator")), []):
                    while j in original_of:               # that candidate itself yielded to an earlier original
                        j = original_of[j]["original"]
                    if j != i and j in seq and rank(j) == rank(i):
                        found.append((j, h))
            if not found:
                continue
            qk = same_text_key(by_id[i].get("phrase"))

            def overlap(j):                               # prefer the original whose own phrase is (or contains, or is in) the quoted words
                jk = same_text_key(by_id[j].get("phrase"))
                return 0 if qk and jk and (qk in jk or jk in qk) else 1
            j, h = min(found, key=lambda x: (overlap(x[0]), seq.index(x[0])))
            pi, pj = seq.index(i), seq.index(j)
            if pj > pi:
                seq[pi] = j
                del seq[pj]
            else:
                del seq[pi]
            original_of[i] = {"original": j, "registered_text": {"registry_id": h.get("registry_id"), "locator": h.get("locator"),
                                                                 "tier": h.get("tier")}}
    queues = [list(q) for q in tier_sequences]
    by_tier = []
    while queues:
        queues = [q for q in queues if q]
        for q in list(queues):
            by_tier.append(q.pop(0))
    slot_pos = {}
    for seq in tier_sequences:
        for n, i in enumerate(seq):
            slot_pos[i] = n

    # 5. one text, one slot (R6-4). Declared same-text rows first: while the declared row has a live candidate, its
    # alternate's candidates are held out of the slot order, so the declared row takes the slot whatever the order; if
    # none of the declared row's candidates is then seated, the alternates compete as ordinary candidates.
    def seat(sequence):
        seated, parallel, cut, by_key = [], {}, [], {}
        for i in sequence:
            k = same_text_key(by_id[i].get("phrase"))
            if k and k in by_key:
                parallel.setdefault(by_key[k], []).append({"candidate_id": i, "registry_id": by_id[i]["registry_id"], "rule": "SAME_TEXT"})
                continue
            if len(seated) < cap:
                seated.append(i)
                if k:
                    by_key[k] = i
            else:
                cut.append(i)
        return seated, parallel, cut

    # R6-4 as extended by R6-50: a DECLARED same-text alternate takes no slot beside its controlling row. A declaration
    # scoped to a section (`locator_contains`) applies only to candidates located in it: BSR-AN-06's Quicunque Vult is
    # one text with BSR-AN-03's, but its Chalcedonian Definition is not, and competes for its own slot.
    declared = {alt: d["same_text_as"] for alt, d in (declarations or {}).items()}
    scope = {alt: d.get("locator_contains") for alt, d in (declarations or {}).items()}

    def _declared(i):
        rid = by_id[i]["registry_id"]
        if rid not in declared:
            return False
        want = scope.get(rid)
        return not want or want in str(by_id[i].get("locator") or "")

    held = [i for i in by_tier if _declared(i)
            and any(by_id[j]["registry_id"] == declared[by_id[i]["registry_id"]] for j in by_tier)]
    seated, parallel, cut = seat([i for i in by_tier if i not in held])
    for i in held:
        ctrl = next((j for j in seated if by_id[j]["registry_id"] == declared[by_id[i]["registry_id"]]), None)
        if ctrl is None:                                  # the declared row seated nothing: compete as usual
            seated, parallel, cut = seat(by_tier)
            break
        parallel.setdefault(ctrl, []).append({"candidate_id": i, "registry_id": by_id[i]["registry_id"], "rule": "SAME_TEXT_ROW",
                                              "same_text_as": declared[by_id[i]["registry_id"]]})
    # 5a, continued: each quoting candidate is recorded on the seat its original holds — the original's own, or, where the
    # original is itself a same-text parallel witness (R6-4), the entry it is recorded on.
    cut_quoting = {}
    for i, rec in original_of.items():
        j = rec["original"]
        holder = j if j in seated else next((k for k, ws in parallel.items() if any(w["candidate_id"] == j for w in ws)), None)
        if holder is None:
            cut_quoting[i] = j
            continue
        parallel.setdefault(holder, []).append({"candidate_id": i, "registry_id": by_id[i]["registry_id"], "rule": "ORIGINAL_HOLDS_SEAT",
                                                "original": j, "registered_text": rec["registered_text"]})
    for ctrl, ws in parallel.items():
        for w in ws:
            if w["rule"] == "ORIGINAL_HOLDS_SEAT":
                rt = w["registered_text"]
                dropped[w["candidate_id"]] = (f"ORIGINAL_HOLDS_SEAT parallel witness of {ctrl}: its phrase is verbatim in the registered text "
                                              f"{rt['registry_id']} {rt['locator']}, which is itself a candidate for this cell ({w['original']}); "
                                              f"the original takes the seat and the lead, the quotation takes no slot (Codex B3(a), R6-41)")
                continue
            dropped[w["candidate_id"]] = (f"SAME_TEXT parallel witness of {ctrl}: its phrase is textually identical to the seated phrase; takes no slot"
                                          if w["rule"] == "SAME_TEXT" else
                                          f"SAME_TEXT_ROW parallel witness of {ctrl}: {w['registry_id']} publishes the same text as "
                                          f"{w['same_text_as']} (declared, different wording); takes no slot")
    kept = sorted(seated, key=lambda i: (rank(i), slot_pos[i]))
    for i in cut:
        holders = sorted({group_of(j) for j in kept if rank(j) == rank(i)})
        dropped[i] = ("candidate cap reached after tier allocation" +
                      (f" (speaks_for group rule: its group {group_of(i)!r} already holds a slot" if group_of(i) in holders else
                       f" (speaks_for group rule: the cap was filled by groups {holders}") + ")")
    for i, j in cut_quoting.items():
        dropped[i] = (f"candidate cap reached after tier allocation (ORIGINAL_HOLDS_SEAT: its phrase is verbatim in the registered text of "
                      f"{j}, which took its place and was then cut by the cap; R6-41)")
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
            "dropped": dropped, "witness_only": witness_only, "corroborating_lower_tier": corr,
            "groups": {i: group_of(i) for i in order}, "slot_order": {i: slot_pos[i] for i in kept},
            "parallel_witnesses": {c: ws for c, ws in parallel.items() if c in kept}}
