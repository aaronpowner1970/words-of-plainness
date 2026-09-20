"""The author review queue and its publication bar — Codex C3 / C3(a), ruled R6-54 (session 14).

Codex C3: "When the verifier accepts but the vote or its own rubric signals doubt, the item goes to the author's
review queue rather than being refused automatically. A queued item cannot be published until the author rules on it."
Codex C3(a) (R6-54) fixes the shape: doubt is ANY DISSENTING VOTE, or ACCEPT_WITH_CAVEAT AT PARTIAL; the queue is a
COMMITTED FILE; and both the packet builder and the emit step refuse to pass a queued item until the author has ruled.

Two things this module deliberately does NOT do:

  * it never refuses on a model self-report (Codex C3). A queued item is HELD for the author, never rejected by code.
    The verdict the verifier gave is kept on the item exactly as it was given;
  * it never writes to the workbook or to src/_data/sjn.

The file lives at data-sources/sjn/recovery-runs/author-review-queue.json and is committed, so every run.py /
reverify.py / packet build / emit reads the same queue, and a queued item cannot be lost between sessions.

An item is HELD until it carries an `author_ruling` block:

  {"decision": "ADMIT" | "REFUSE", "ruled": "YYYY-MM-DD", "why": "...", "recorded_by": "..."}

  ADMIT   the author has ruled the citation sound; it passes the packet builder and the emit step like any other.
  REFUSE  the author has ruled against it; it never seats and never publishes, with the author's reason on record.

Anything else — a missing block, an unknown decision — is HELD (fail closed)."""
import json
import os

from .config import RUNS_DIR, ROOT

QUEUE_PATH = os.environ.get("SJN_REVIEW_QUEUE_PATH") or os.path.join(RUNS_DIR, "author-review-queue.json")
SCHEMA = "sjn-gate6-author-review-queue/1"
RULING = "R6-54_production_voting_and_review_queue"
DECISIONS = ("ADMIT", "REFUSE")

# The two reasons Codex C3(a) names. Nothing else puts an item in the queue.
REASON_DISSENT = "DISSENTING_VOTE"
REASON_CAVEAT_AT_PARTIAL = "ACCEPT_WITH_CAVEAT_AT_PARTIAL"
REASONS = (REASON_DISSENT, REASON_CAVEAT_AT_PARTIAL)

ITEM_REQUIRED = ("queue_id", "candidate_id", "reasons")


def _empty():
    return {
        "schema": SCHEMA,
        "what": ("The author review queue (Comparison Principles Codex C3, shaped by C3(a) / R6-54). A verifier ACCEPT that "
                 "carries doubt — any dissenting vote among its replicates, or ACCEPT_WITH_CAVEAT at a PARTIAL floor — is "
                 "recorded here instead of being refused by code. A queued item is HELD: the packet builder gives it no seat "
                 "and the emit step refuses to publish it, until the author records an author_ruling of ADMIT or REFUSE."),
        "ruling": RULING,
        "doubt": {REASON_DISSENT: "any replicate whose verdict class differs from the majority's",
                  REASON_CAVEAT_AT_PARTIAL: "the final verdict is ACCEPT_WITH_CAVEAT and the final floor is PARTIAL"},
        "author_ruling_shape": {"decision": list(DECISIONS), "ruled": "YYYY-MM-DD", "why": "the author's reason",
                                "recorded_by": "the session that recorded it"},
        "items": [],
    }


def load(path=None):
    """The queue as stored. A missing file is an EMPTY queue, not a hard stop: the queue is a record of doubt, and an
    empty one is the honest state before any voted run. A malformed one IS a hard stop — a queue that cannot be read
    cannot bar anything, and silently passing every item would be exactly the failure C3 exists to prevent."""
    p = path or QUEUE_PATH
    if not os.path.exists(p):
        return dict(_empty(), _path=os.path.relpath(p, ROOT).replace("\\", "/"), _missing=True)
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    if d.get("schema") != SCHEMA:
        raise SystemExit(f"author review queue {p}: schema {d.get('schema')!r}, expected {SCHEMA!r}")
    if not isinstance(d.get("items"), list):
        raise SystemExit(f"author review queue {p}: `items` must be a list")
    seen = set()
    for it in d["items"]:
        missing = [f for f in ITEM_REQUIRED if not it.get(f)]
        if missing:
            raise SystemExit(f"author review queue {p}: an item lacks {missing}: {str(it)[:160]}")
        bad = [r for r in it["reasons"] if r not in REASONS]
        if bad:
            raise SystemExit(f"author review queue {p}: {it['candidate_id']} carries reasons outside {REASONS}: {bad}")
        if it["candidate_id"] in seen:
            raise SystemExit(f"author review queue {p}: {it['candidate_id']} is queued twice")
        seen.add(it["candidate_id"])
        ar = it.get("author_ruling")
        if ar is not None and (not isinstance(ar, dict) or ar.get("decision") not in DECISIONS):
            raise SystemExit(f"author review queue {p}: {it['candidate_id']} carries an author_ruling whose decision is not "
                             f"one of {DECISIONS}: {ar}")
    d["_path"] = os.path.relpath(p, ROOT).replace("\\", "/")
    return d


def items(q=None):
    return list((q or load()).get("items") or [])


def by_candidate(q=None):
    return {it["candidate_id"]: it for it in items(q)}


def decision(item):
    """ADMIT / REFUSE / None (held). Anything unrecognised is held — fail closed."""
    ar = item.get("author_ruling")
    if not isinstance(ar, dict):
        return None
    return ar["decision"] if ar.get("decision") in DECISIONS else None


def hold(candidate_id, q=None):
    """The reason this candidate may NOT pass, or None. A queued item the author has not ruled on is HELD; one the author
    has REFUSED stays barred, with the author's own reason; one the author has ADMITTED passes."""
    it = by_candidate(q).get(candidate_id)
    if it is None:
        return None
    dec = decision(it)
    if dec == "ADMIT":
        return None
    return {"candidate_id": candidate_id, "queue_id": it.get("queue_id"), "reasons": list(it["reasons"]),
            "detail": it.get("detail"), "entered": it.get("entered"), "ruling": RULING,
            "state": "REFUSED_BY_AUTHOR" if dec == "REFUSE" else "AWAITING_AUTHOR_RULING",
            "author_ruling": it.get("author_ruling"),
            "bar": ("the author ruled REFUSE on this item (Codex C3(a), R6-54)" if dec == "REFUSE" else
                    "queued for the author's review and not yet ruled on: it takes no seat and is never published "
                    "(Codex C3, C3(a); R6-54)")}


def held_candidates(q=None):
    """{candidate_id: hold} for every item that may not pass right now."""
    q = q or load()
    return {cid: hold(cid, q) for cid in by_candidate(q) if hold(cid, q)}


def held_queue_ids(q=None):
    """The queue_ids (cells) that carry at least one held item — what the emit bar checks against."""
    q = q or load()
    return sorted({h["queue_id"] for h in held_candidates(q).values() if h.get("queue_id")})


def summary(q=None):
    q = q or load()
    its = items(q)
    return {"file": q.get("_path"), "items": len(its),
            "held": len(held_candidates(q)),
            "admitted": sum(1 for it in its if decision(it) == "ADMIT"),
            "refused": sum(1 for it in its if decision(it) == "REFUSE"),
            "by_reason": {r: sum(1 for it in its if r in it["reasons"]) for r in REASONS},
            "ruling": RULING}


# ---------------------------------------------------------------- writing (a run's own record)
def add(entries, path=None, log=None):
    """Record doubtful accepts in the committed queue file. Idempotent by candidate_id: an item already queued keeps its
    author_ruling and its original `entered`, and only its reasons and detail are refreshed. Returns (added, updated)."""
    p = path or QUEUE_PATH
    q = load(p)
    q.pop("_missing", None)
    q.pop("_path", None)
    by = {it["candidate_id"]: it for it in q["items"]}
    added = updated = 0
    for e in entries:
        missing = [f for f in ITEM_REQUIRED if not e.get(f)]
        if missing:
            raise SystemExit(f"review_queue.add: an entry lacks {missing}: {str(e)[:160]}")
        bad = [r for r in e["reasons"] if r not in REASONS]
        if bad:
            raise SystemExit(f"review_queue.add: {e['candidate_id']} carries reasons outside {REASONS}: {bad}")
        old = by.get(e["candidate_id"])
        if old is None:
            by[e["candidate_id"]] = dict(e)
            added += 1
        else:
            old.update({k: v for k, v in e.items() if k not in ("author_ruling", "entered")})
            updated += 1
    q["items"] = [by[cid] for cid in sorted(by)]
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(q, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    if log:
        log(f"   author review queue: {added} added, {updated} updated, {len(q['items'])} item(s) in {p}")
    return added, updated


# ---------------------------------------------------------------- the publication bar (Codex C3(a))
class QueuedItemWouldPublish(SystemExit):
    """A queued item reached a publishable payload. This is the stop condition, not a warning."""


def assert_nothing_held_publishes(payload, where, q=None):
    """The emit-step half of the publication bar. `payload` is anything about to be written to src/_data/sjn (or any
    other publishable output): it is searched, whole, for every held candidate_id and for the cells they belong to.

    A held candidate_id anywhere in the payload, or a CERTIFIED cell whose id carries a held item, is a hard stop. The
    check is over the serialised payload, so it cannot be evaded by a field this module does not know about."""
    q = q or load()
    held = held_candidates(q)
    if not held:
        return {"held": 0, "checked": where, "hits": []}
    blob = json.dumps(payload, ensure_ascii=False, default=str)
    hits = [h for cid, h in held.items() if cid in blob]
    qids = {h["queue_id"] for h in held.values() if h.get("queue_id")}
    certified = []
    for c in (payload.get("cells") if isinstance(payload, dict) else None) or []:
        if isinstance(c, dict) and c.get("certified") and c.get("id") in qids:
            certified.append(c["id"])
    if hits or certified:
        raise QueuedItemWouldPublish(
            f"STOP (Codex C3(a), R6-54): the author review queue bars this publication. {where}: "
            f"held candidate(s) in the payload {[h['candidate_id'] for h in hits]}; "
            f"certified cell(s) carrying a held item {certified}. "
            f"Nothing publishes until the author records an ADMIT or REFUSE on each in {q.get('_path') or QUEUE_PATH}.")
    return {"held": len(held), "checked": where, "hits": []}
