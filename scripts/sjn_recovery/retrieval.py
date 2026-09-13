"""Chunk selection for one cell: which text the locator receives.

The locator gets the branch's registry chunks (spec §4) — but a branch corpus such as the Book of
Concord or the Catechism of the Catholic Church cannot fit one context. Policy:

  * every standard admitted for the pass is represented;
  * a standard whose chunks fit the per-standard share of the context budget is supplied WHOLE
    (coverage FULL) — the locator has genuinely reviewed the standard;
  * otherwise hybrid retrieval (BM25 over normalized text + Ollama nomic-embed-text cosine via
    ChromaDB when available) supplies the top-k chunks of that standard (coverage RETRIEVED k of n),
    and the audit records exactly which chunk keys were supplied.

Chunk keys (c1, c2, …) are per call; the mapping to registry_id + locator is kept in code, never in
the prompt beyond the chunk's own locator. URLs never enter."""
import math
import re
from collections import Counter

from .config import LOCATOR_CONTEXT_CHARS, RETRIEVAL_TOP_K_PER_STANDARD
from .textutil import normalize
from . import store

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return _TOKEN.findall(normalize(text))


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [_tokens(d) for d in docs]
        self.N = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / max(1, self.N)
        self.df = Counter()
        for d in self.docs:
            for t in set(d):
                self.df[t] += 1
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in self.docs]

    def score(self, query):
        q = _tokens(query)
        out = []
        for i, d in enumerate(self.docs):
            s = 0.0
            dl = len(d) or 1
            for t in q:
                if t not in self.tf[i]:
                    continue
                idf = math.log(1 + (self.N - self.df[t] + 0.5) / (self.df[t] + 0.5))
                f = self.tf[i][t]
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append(s)
        return out


def query_text(predicate):
    """The predicate term carries the signal. The floor note is analytic prose about the coding
    decision ("temporal succession", "classical theology") and, weighted equally, it pulls ranking
    toward long scholastic discussion and away from the terse creedal assertion that is the actual
    evidence. Repeat the term so the ranking follows the predicate."""
    return " ".join([predicate["predicate"]] * 3 + [predicate["definition"], predicate["floor_note"]])


def predicate_terms(predicate):
    """The words a confession would itself use for this predicate ("Eternal" -> eternal;
    "Almighty / omnipotent" -> almighty, omnipotent), for the lexical slice in select_chunks."""
    out = []
    for variant in re.split(r"[/|,]", predicate["predicate"]):
        for w in re.findall(r"[A-Za-z]{4,}", variant):
            w = w.casefold()
            if w not in out:
                out.append(w)
    return out


def has_term(text, terms):
    """True when the chunk literally uses one of the predicate's own words (any inflection)."""
    n = normalize(text)
    return any(re.search(r"\b" + re.escape(t) + r"\w*", n) for t in terms)


# A predicate term that appears in a large share of a standard's chunks carries no signal for that
# standard: "without" is in 48% of the Book of Concord and 55% of the Confession of Dositheus, so
# admitting chunks on the strength of it fills the lexical slice with noise and pushes the real
# evidence out. Terms above this document frequency are dropped for that standard; if every term is
# above it, the rarest one is kept so the slice is never empty for the wrong reason.
LEXICAL_DF_CEILING = 0.35


def discriminating_terms(terms, chunks):
    """The predicate terms that actually discriminate within THIS standard, by document frequency."""
    if len(terms) < 2 or not chunks:
        return terms
    df = {}
    for term in terms:
        rx = re.compile(r"\b" + re.escape(term) + r"\w*")
        df[term] = sum(1 for c in chunks if rx.search(normalize(c["text"]))) / len(chunks)
    keep = [term for term in terms if df[term] <= LEXICAL_DF_CEILING]
    return keep or [min(terms, key=lambda x: df[x])]


def division_of(locator):
    """The constituent work a chunk belongs to, read off the chunk's own locator.

    Several registry rows are composite volumes: BSR-LU-01 is the whole Book of Concord, BSR-RP-04
    the whole Book of Confessions. Their constituent documents differ enormously in length, so a
    flat ranking lets the longest book swallow the standard's whole allowance - the three Ecumenical
    Creeds are 3 chunks of BSR-LU-01's 738 and never surfaced, which is why Q-363 (Athanasian Creed)
    drew an EMPTY locator. Grouping by division lets every constituent work be represented.

    Locator shapes in this corpus:
      "Book of Confessions 1.1 (Nicene Creed)"    -> Nicene Creed       (trailing parenthetical)
      "Chapter 2.1 - Of God"                      -> Of God             (after the dash)
      "Ecumenical Creeds: The Athanasian Creed"   -> Ecumenical Creeds  (before the colon)
      "CCC 185"                                   -> CCC 185            (its own division, so the
                                                     round robin degenerates to plain rank order,
                                                     the correct no-op for a flat text)
    """
    loc = (locator or "").strip()
    m = re.search(r"\(([^()]+)\)\s*$", loc)
    if m:
        return m.group(1).strip()
    parts = re.split(r"\s[—–-]\s", loc, maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        return parts[1].strip()
    return re.split(r"[:,]", loc)[0].strip() or loc


def round_robin(chunks):
    """Reorder a ranked list so that each division contributes its best chunk before any division
    contributes its second. Order within a division, and the order in which divisions are first
    seen, both follow the incoming ranking, so this never promotes a division that ranked nowhere."""
    groups = {}
    for c in chunks:
        groups.setdefault(division_of(c["locator"]), []).append(c)
    queues = list(groups.values())
    order = []
    while queues:
        queues = [q for q in queues if q]
        for q in list(queues):
            order.append(q.pop(0))
    return order


def _vector_rank(chunks, query, rid):
    """Return {chunk_locator: rank} from Chroma cosine search, or None if unavailable."""
    try:
        if not store.ollama_available():
            return None
        col = store.chroma_collection()
        emb = store.embed([query])[0]
        res = col.query(query_embeddings=[emb], n_results=min(40, len(chunks)), where={"registry_id": rid},
                        include=["metadatas"])
        locs = [m["locator"] for m in res["metadatas"][0]]
        return {loc: i for i, loc in enumerate(locs)}
    except Exception:
        return None


def rank_within_standard(predicate, rid, ch, allowance, top_k=RETRIEVAL_TOP_K_PER_STANDARD, use_vectors=True):
    """Hybrid ranking of ONE standard's chunks into a character allowance. Returns (picked, coverage)."""
    q = query_text(predicate)
    bm = BM25([c["text"] for c in ch])
    scores = bm.score(q)
    order = sorted(range(len(ch)), key=lambda i: -scores[i])
    bm_rank = {ch[i]["locator"]: r for r, i in enumerate(order)}
    vec_rank = _vector_rank(ch, q, rid) if use_vectors else None

    def fused(c):
        r1 = bm_rank.get(c["locator"], len(ch))
        r2 = vec_rank.get(c["locator"], len(ch)) if vec_rank else r1
        return 1 / (60 + r1) + 1 / (60 + r2)
    ranked = sorted(ch, key=lambda c: -fused(c))
    terms = discriminating_terms(predicate_terms(predicate), ch)
    lex = [c for c in ranked if terms and has_term(c["text"], terms)]
    if lex:
        lscore = BM25([c["text"] for c in lex]).score(" ".join(terms))
        lex = [lex[i] for i in sorted(range(len(lex)), key=lambda i: -lscore[i])]
        lex = round_robin(lex)
        lex_keys, lex_allow, used_lex = set(), allowance * 0.7, 0
        for c in lex:
            if used_lex + len(c["text"]) > lex_allow:
                continue
            lex_keys.add(c["locator"]); used_lex += len(c["text"])
        ranked = ([c for c in lex if c["locator"] in lex_keys]
                  + [c for c in ranked if c["locator"] not in lex_keys])
    picked, used = [], 0
    for c in ranked:
        if used + len(c["text"]) > allowance:
            if len(picked) >= max(top_k, 3):
                break
            continue
        picked.append(c); used += len(c["text"])
    coverage = {"coverage": "RETRIEVED", "supplied": len(picked), "of": len(ch),
                "lexical": sum(1 for c in picked if terms and has_term(c["text"], terms)),
                "method": ("BM25+vector(RRF)" if vec_rank else "BM25") + "+lexical-slice"}
    return picked, coverage


def ranked_order(predicate, rid, ch, use_vectors=True):
    """The full ranked order of one standard's chunks — the same hybrid ranking rank_within_standard
    applies (BM25 + vector RRF, lexical slice first), without the allowance. Used to order the
    chunks a locator has NOT yet seen when a standard is exhausted (Task 2c)."""
    if not ch:
        return []
    q = query_text(predicate)
    bm = BM25([c["text"] for c in ch])
    scores = bm.score(q)
    order = sorted(range(len(ch)), key=lambda i: -scores[i])
    bm_rank = {ch[i]["locator"]: r for r, i in enumerate(order)}
    vec_rank = _vector_rank(ch, q, rid) if use_vectors else None

    def fused(c):
        r1 = bm_rank.get(c["locator"], len(ch))
        r2 = vec_rank.get(c["locator"], len(ch)) if vec_rank else r1
        return 1 / (60 + r1) + 1 / (60 + r2)
    ranked = sorted(ch, key=lambda c: -fused(c))
    terms = discriminating_terms(predicate_terms(predicate), ch)
    lex = [c for c in ranked if terms and has_term(c["text"], terms)]
    if lex:
        lscore = BM25([c["text"] for c in lex]).score(" ".join(terms))
        lex = round_robin([lex[i] for i in sorted(range(len(lex)), key=lambda i: -lscore[i])])
        keys = {c["locator"] for c in lex}
        ranked = lex + [c for c in ranked if c["locator"] not in keys]
    return ranked


def exhaustion_batches(predicate, row, supplied_locators, budget=LOCATOR_CONTEXT_CHARS, use_vectors=True):
    """Task 2c: the chunks of ONE standard the locator has not been given (their locators not in
    `supplied_locators`), in ranked order, packed into batches of at most `budget` characters (an
    oversized chunk gets a batch of its own). Returns (batches, n_remaining_chunks); each batch is a
    list of chunk dicts. Every chunk of the standard appears in exactly one batch, so running every
    batch EXHAUSTS the standard."""
    rid = row["registry_id"]
    ch = [c for c in store.load_chunks(rid) if c.get("text") and c["locator"] not in supplied_locators]
    ranked = ranked_order(predicate, rid, ch, use_vectors=use_vectors)
    batches, cur, used = [], [], 0
    for c in ranked:
        if cur and used + len(c["text"]) > budget:
            batches.append(cur); cur, used = [], 0
        cur.append(c); used += len(c["text"])
    if cur:
        batches.append(cur)
    return batches, len(ch)


def select_for_standard(predicate, row, budget=LOCATOR_CONTEXT_CHARS, top_k=RETRIEVAL_TOP_K_PER_STANDARD, use_vectors=True):
    """Retrieval PER STANDARD (cal-3, Fix 1). One standard, its own full budget: supplied WHOLE when
    it fits, otherwise the hybrid top ranking within that standard. Returns (chunks, coverage) or
    ([], None) when the standard has no corpus. Nothing from any other standard competes for the
    allowance, which is what gives a 2-chunk page and a 738-chunk volume the same guaranteed slot."""
    rid = row["registry_id"]
    ch = store.load_chunks(rid)
    ch = [c for c in ch if c.get("text")]
    if not ch:
        return [], None
    total = sum(len(c["text"]) for c in ch)
    if total <= budget:
        return ch, {"coverage": "FULL", "supplied": len(ch), "of": len(ch)}
    return rank_within_standard(predicate, rid, ch, budget, top_k=top_k, use_vectors=use_vectors)


def select_chunks(predicate, standards, budget=LOCATOR_CONTEXT_CHARS, top_k=RETRIEVAL_TOP_K_PER_STANDARD, use_vectors=True):
    """(cal-1/cal-2 pooled policy, kept for reference and for the old run reports.)
    standards: list of registry rows admitted for this pass. Returns (selected_chunks, coverage)."""
    per = {r["registry_id"]: store.load_chunks(r["registry_id"]) for r in standards}
    per = {rid: ch for rid, ch in per.items() if ch}
    if not per:
        return [], {}
    selected, coverage = [], {}
    q = query_text(predicate)
    total = sum(sum(len(c["text"]) for c in ch) for ch in per.values())
    if total <= budget:
        for rid, ch in per.items():
            selected.extend(ch)
            coverage[rid] = {"coverage": "FULL", "supplied": len(ch), "of": len(ch)}
        return selected, coverage
    # small standards first: each takes only what it needs; the remainder is shared by the large ones
    sizes = sorted(((sum(len(c["text"]) for c in ch), rid) for rid, ch in per.items()))
    remaining, n_left = budget, len(sizes)
    share = budget / len(per)
    for size, rid in sizes:
        fair = remaining / n_left
        if size <= fair:
            selected.extend(per[rid]); coverage[rid] = {"coverage": "FULL", "supplied": len(per[rid]), "of": len(per[rid])}
            remaining -= size
        n_left -= 1
    share = remaining / max(1, sum(1 for _, rid in sizes if rid not in coverage))
    leftover = 0.0
    big = [(rid, ch, sum(len(c["text"]) for c in ch)) for rid, ch in per.items() if rid not in coverage]
    # second pass: retrieval for big standards, sharing leftover budget
    for rid, ch, size in big:
        allowance = share + (leftover / len(big) if big else 0)
        bm = BM25([c["text"] for c in ch])
        scores = bm.score(q)
        order = sorted(range(len(ch)), key=lambda i: -scores[i])
        bm_rank = {ch[i]["locator"]: r for r, i in enumerate(order)}
        vec_rank = _vector_rank(ch, q, rid) if use_vectors else None
        def fused(c):
            r1 = bm_rank.get(c["locator"], len(ch))
            r2 = vec_rank.get(c["locator"], len(ch)) if vec_rank else r1
            return 1 / (60 + r1) + 1 / (60 + r2)
        ranked = sorted(ch, key=lambda c: -fused(c))
        # Lexical slice. A predicate such as "Eternal" is confessed in short creedal clauses that
        # lose on BM25 to long scholastic passages: the Athanasian Creed ranked 260th of 738 for
        # RNR-H46 although it says "the Father eternal, the Son eternal". Reserve most of the
        # allowance for chunks that actually use the predicate's own vocabulary, ranked among
        # themselves by the same fusion, then spend the remainder on the general ranking so that
        # evidence phrased without the term is still reachable.
        terms = discriminating_terms(predicate_terms(predicate), ch)
        lex = [c for c in ranked if terms and has_term(c["text"], terms)]
        if lex:
            # Inside the slice, rank on the predicate's own words alone. The full query still carries
            # the floor note, and blending the two ranks (RRF) was measurably worse than dropping the
            # general rank here: for RNR-H46 the Athanasian Creed sits at 139 of 157 on the full
            # query, 78 blended, 33 on the predicate term. The general ranking still governs the
            # remaining 30% of the allowance, so evidence phrased without the term is not lost.
            lscore = BM25([c["text"] for c in lex]).score(" ".join(terms))
            lex = [lex[i] for i in sorted(range(len(lex)), key=lambda i: -lscore[i])]
            lex = round_robin(lex)
            lex_keys, lex_allow, used_lex = set(), allowance * 0.7, 0
            for c in lex:
                if used_lex + len(c["text"]) > lex_allow:
                    continue
                lex_keys.add(c["locator"]); used_lex += len(c["text"])
            ranked = ([c for c in lex if c["locator"] in lex_keys]
                      + [c for c in ranked if c["locator"] not in lex_keys])
        # Fill the character allowance. An earlier version also capped the count at top_k*2, which
        # discarded most of the budget for standards whose divisions are short (the Book of Concord's
        # Athanasian Creed never reached the locator for Q-363 because of it). The allowance is the
        # only limit; top_k is the floor that guarantees a standard is represented at all.
        picked, used = [], 0
        for c in ranked:
            if used + len(c["text"]) > allowance:
                if len(picked) >= max(top_k, 3):
                    break
                continue          # oversized chunk early on: skip it, keep looking for the floor
            picked.append(c); used += len(c["text"])
        selected.extend(picked)
        coverage[rid] = {"coverage": "RETRIEVED", "supplied": len(picked), "of": len(ch),
                         "lexical": sum(1 for c in picked if terms and has_term(c["text"], terms)),
                         "method": ("BM25+vector(RRF)" if vec_rank else "BM25") + "+lexical-slice"}
    return selected, coverage
