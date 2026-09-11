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
    return " ".join([predicate["predicate"], predicate["definition"], predicate["floor_note"]])


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


def select_chunks(predicate, standards, budget=LOCATOR_CONTEXT_CHARS, top_k=RETRIEVAL_TOP_K_PER_STANDARD, use_vectors=True):
    """standards: list of registry rows admitted for this pass. Returns (selected_chunks, coverage)."""
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
        picked, used = [], 0
        for c in ranked:
            if len(picked) >= max(top_k, 3) and used + len(c["text"]) > allowance:
                break
            if used + len(c["text"]) > allowance and picked:
                continue
            picked.append(c); used += len(c["text"])
            if len(picked) >= top_k * 2:
                break
        selected.extend(picked)
        coverage[rid] = {"coverage": "RETRIEVED", "supplied": len(picked), "of": len(ch),
                         "method": "BM25+vector(RRF)" if vec_rank else "BM25"}
    return selected, coverage
