"""Chunk store: per-standard JSON under .cache (gitignored), committed corpus manifest with text_hash
per standard, and the ChromaDB collection `sjn_confessions` (internal only) with Ollama embeddings."""
import json
import os
import time

import requests

from .config import CHUNK_DIR, MANIFEST_PATH, CHROMA_PATH, CHROMA_COLLECTION, OLLAMA_URL, EMBED_MODEL, RUNS_DIR
from .textutil import sha, normalize


def chunk_id(rid, locator):
    return f"{rid}::{locator}"


def standard_hash(chunks):
    """Hash of the normalized chunk texts in order — the standard's text_hash for drift detection."""
    return sha("\n".join(normalize(c["text"]) for c in chunks))


def dedupe_locators(chunks):
    seen = {}
    for c in chunks:
        loc = c["locator"]
        n = seen.get(loc, 0)
        seen[loc] = n + 1
        if n:
            c["locator"] = f"{loc} [{n + 1}]"
    return chunks


def save_chunks(rid, chunks):
    os.makedirs(CHUNK_DIR, exist_ok=True)
    with open(os.path.join(CHUNK_DIR, f"{rid}.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(chunks, fh, ensure_ascii=False, indent=1)


def load_chunks(rid):
    p = os.path.join(CHUNK_DIR, f"{rid}.json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def load_all_chunks(rids=None):
    out = []
    for fn in sorted(os.listdir(CHUNK_DIR)) if os.path.isdir(CHUNK_DIR) else []:
        rid = fn[:-5]
        if rids is None or rid in rids:
            out.extend(load_chunks(rid))
    return out


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"standards": {}}


def save_manifest(m):
    os.makedirs(RUNS_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


# ------------------------------------------------------------------ embeddings / chroma
def embed(texts):
    out = []
    for i in range(0, len(texts), 16):
        batch = texts[i:i + 16]
        r = requests.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": batch}, timeout=300)
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    return out


def ollama_available():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.ok and any(EMBED_MODEL in m.get("name", "") for m in r.json().get("models", []))
    except Exception:
        return False


def chroma_collection():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=CHROMA_COLLECTION, metadata={"hnsw:space": "cosine",
                                                                              "purpose": "SJN Gate 6 registry corpus (internal only)"})


def upsert_standard(col, rid, chunks, log=print):
    """Replace the standard's chunks in Chroma (delete by registry_id, then add with embeddings)."""
    try:
        col.delete(where={"registry_id": rid})
    except Exception:
        pass
    if not chunks:
        return 0
    ids = [chunk_id(rid, c["locator"]) for c in chunks]
    docs = [c["text"] for c in chunks]
    metas = [{"registry_id": rid, "branch": c["branch"], "locator": c["locator"], "division": c["division"],
              "authority_tier": c["authority_tier"], "text_hash": c["text_hash"], "chars": len(c["text"])} for c in chunks]
    t0 = time.time()
    embs = embed([d[:8000] for d in docs])
    for i in range(0, len(ids), 200):
        col.add(ids=ids[i:i + 200], documents=docs[i:i + 200], metadatas=metas[i:i + 200], embeddings=embs[i:i + 200])
    log(f"   chroma: {rid} {len(ids)} chunks embedded in {time.time() - t0:.1f}s")
    return len(ids)
