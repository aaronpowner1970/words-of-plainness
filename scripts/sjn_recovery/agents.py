"""Locator → verifier → coder for one cell, with the guards applied in code, the fallback-tier
two-pass rule (APP CONFIG registry_fallback_only_rows), per-standard retrieval (cal-3, Fix 1) and
the verifier routing SONNET_WITH_OPUS_SLICE (APP CONFIG verifier_routing, Fix 6).

  pass one   non-fallback rows of the branch only
  pass two   run ONLY if pass one produced no surviving (verified) candidate; then, and only then,
             the fallback row is admitted. A fallback citation never renders alongside a non-fallback
             witness for the same cell.
  pass three EXHAUSTION (Task 2c, 2026-09-13): run ONLY if passes one and two left nothing surviving
             AND some consulted standard was only SAMPLED (coverage RETRIEVED). The locator continues
             over that standard's unretrieved chunks in further calls — in rounds of
             EXHAUST_CALLS_PER_ROUND batches per standard, each batch within the ordinary context
             budget — until the standard is exhausted or a candidate survives verification. An empty
             is declared only after that; a standard exhausted this way has coverage EXHAUSTED.

Per-standard locate. The locator is called ONCE PER STANDARD with that standard's own chunks (whole
when they fit the budget, otherwise the hybrid ranking within that standard). Every standard that
yields a candidate gets a GUARANTEED verification slot for its best candidate; the remaining
candidates compete for VERIFY_EXTRA_CANDIDATES further slots, ranked by authority tier and floor
claim. A phrase the locator cut too long (>15 words) is not repaired by code — the locator is asked to
re-cut it verbatim (up to three attempts, shortening each time; on the last it chooses among the legal
≤15-word spans enumerated in code), and the re-cut goes through the same guards. An EMPTY locator
reply carries a one-sentence silence_rationale per standard (prompt gate6-v1.4, Task 2d).

Routing. The primary verifier judges every slotted candidate. The adjudicator (opus) judges only the
slice: candidates on the caveated rows, on fallback-only rows, on the guarded Synodikon row, every
candidate of a cell where the primary rejected all candidates, and (Task 3, 2026-09-13) every
CAVEATED ACCEPT that would reach the author's card — primary verdict ACCEPT_WITH_CAVEAT at a PARTIAL
floor or raising SEMANTIC_FLOOR / SAME_WORD_DIFFERENT_MEANING — fired only on candidates the
allocation keeps (rejections never need it), and repeated when an overturn promotes another such
candidate into the card. Where the adjudicator ran, its verdict is FINAL; the primary's verdict is
kept beside it so overturns are visible in the report.

Every function is resumable: with the batch backend a call that is not yet answered returns None and
the cell state records where it stopped; re-running continues from the audit log."""
import json
import os

import re

import hashlib

from .config import (MAX_CANDIDATES, EMPTY_RESULT, VERIFY_EXTRA_CANDIDATES, PHRASE_MAX_WORDS, EXHAUST_CALLS_PER_ROUND,
                     CAVEAT_SLICE_HAZARDS, ROUTE_CAVEATED_ACCEPT, ROUTE_CAVEAT_SAMPLE, CAVEAT_SAMPLE_SHARE, ADJUDICATING_ROUTES,
                     HAZARD_IDIOM_OR_FORMULA, FORMULA_FLOOR_CAP, LOWER_FLOOR_RULE)

VERIFIER_REQUIRED = ("phrase_verbatim", "subject_is_required", "speech_act_is_assertion", "floor", "verdict")
CAP_NEIGHBOURING_PROPOSITION = "NEIGHBOURING_PROPOSITION"      # session 6, R6-2 (verifier gate6-v1.3)
NEIGHBOURING_FLOOR_CAP = "WORD_ONLY"

# ---------------------------------------------------------------- R6-7 (session 7): the Spirit-name code guard
# The author's rule: the enumerated form "the Father X, the Son X, the Holy Spirit X" satisfies a family typed THE HOLY
# SPIRIT only if the CITED PHRASE ITSELF carries the Spirit's name and the predicate; the collective form "one God,
# Father, Son and Holy Spirit, is X" does not. gate6-v1.4's JOINT PREDICATION line says so; this is the code half, so
# the rule does not depend on the model reading it. It fires ONLY where the required subject IS the Holy Spirit — never
# on R6-1's five families, whose required subject is the one God and may be asserted of the Father.
SPIRIT_NAME_TOKENS = ("holy spirit", "holy ghost", "spirit", "pneuma", "πνευμα")
SPIRIT_SUBJECT_GUARD = "R6-7_SPIRIT_NAME_NOT_IN_PHRASE"


def strip_accents(text):
    """NFKC-casefold, then drop combining marks, so πνεῦμα / πνεύματος fold to the πνευμα stem the guard matches."""
    import unicodedata
    t = unicodedata.normalize("NFD", unicodedata.normalize("NFKC", text or "").casefold())
    return unicodedata.normalize("NFC", "".join(c for c in t if not unicodedata.combining(c)))


def required_subject_is_the_spirit(pred):
    """True only where the family's required subject IS the Holy Spirit (RNR-H34, RNR-H35), not where it merely
    ADMITS the Spirit as one person of the one God (R6-1's five)."""
    return strip_accents(pred.get("subject_scope") or "").strip().startswith("the holy spirit")


def phrase_names_the_spirit(phrase):
    t = strip_accents(phrase)
    return any(tok in t for tok in SPIRIT_NAME_TOKENS)
from .registry import tier_rank
from .textutil import scrub_urls, phrase_word_count
from .allocation import allocate, translation_pairs, speaks_for_groups
from . import guards, prompts, retrieval, store


def legal_spans(phrase, limit=PHRASE_MAX_WORDS, cap=12):
    """The ≤limit-word sub-spans of an over-long phrase that start at its beginning or after a clause mark
    (, ; : —) and end at its end or at a clause mark — offered to the locator to CHOOSE from, shortest
    first. Every span is verbatim by construction (a contiguous run of the phrase's own words)."""
    ws = phrase.split()
    if not ws:
        return []
    starts = {0} | {i + 1 for i, w in enumerate(ws[:-1]) if re.search(r"[,;:—–]$", w)}
    ends = {len(ws)} | {i + 1 for i, w in enumerate(ws) if re.search(r"[,;:—–.]$", w)}
    out = []
    for a in sorted(starts):
        for b in sorted(ends):
            n = b - a
            if 2 <= n <= limit:
                out.append(" ".join(ws[a:b]))
    if len(ws) > limit:
        out.append(" ".join(ws[:limit])); out.append(" ".join(ws[-limit:]))
    seen, uniq = set(), []
    for sp in sorted(out, key=lambda x: (len(x.split()), x)):
        if sp not in seen:
            seen.add(sp); uniq.append(sp)
    return uniq[:cap]


ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
FLOOR_ORDER = {"FULL": 0, "PARTIAL": 1, "WORD_ONLY": 2}
EXHAUST_PASS = "3"


def caveat_slice_hit(rubric):
    """Session 3, Task 3 (now the ELIGIBILITY test for the 2c sample): does this PRIMARY rubric describe a
    caveated accept — ACCEPT_WITH_CAVEAT at a PARTIAL floor, or raising a CAVEAT_SLICE_HAZARDS flag?"""
    if not rubric or rubric.get("verdict") != "ACCEPT_WITH_CAVEAT":
        return False
    if rubric.get("floor") == "PARTIAL":
        return True
    return bool(set(rubric.get("hazard_flags") or []) & set(CAVEAT_SLICE_HAZARDS))


def sample_bucket(candidate_id):
    """Deterministic 0–99 bucket of a candidate id (sha256), so the 2c sample is reproducible across re-runs."""
    return int(hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:8], 16) % 100


def lower_floor(*floors):
    """2a: the LOWER of the floors returned (FULL > PARTIAL > WORD_ONLY); None-safe."""
    known = [f for f in floors if f in FLOOR_ORDER]
    return max(known, key=lambda f: FLOOR_ORDER[f]) if known else None


OUTSIDE_FORMULA_GUARD = "R6-18"


def outside_formula_guard_applies(rubric):
    """R6-18 (session 9): THE PHRASE CARRIES THE ASSERTION. A rubric from a guarded verifier version (gate6-v1.6 on) that
    answers asserted_outside_formula = Y says the passage asserts the predicate only OUTSIDE the quoted words, so the
    quoted phrase does not carry it. The rubric field is kept so this can be read."""
    return (str((rubric or {}).get("asserted_outside_formula")).upper() == "Y"
            and (rubric or {}).get("prompt_version") in prompts.OUTSIDE_FORMULA_GUARDED_VERSIONS)


def verdict_from_rubric(rubric, floor, lexical_floor=False):
    """The verdict recomputed in code from a DONE rubric's lines 1–3 and model verdict at the given floor —
    the one function both verify() and finalize() use, so a merged floor is judged by the same rule as a
    model's own floor. Returns (verdict, reason_code).

    R6-18: an accept whose rubric carries asserted_outside_formula = Y (guarded versions) is refused here, BELOW_FLOOR —
    in the one function, so a refinalisation can never re-admit it."""
    verdict, code = _verdict_from_rubric_lines(rubric, floor, lexical_floor)
    if verdict in ACCEPTS and outside_formula_guard_applies(rubric):
        return "REJECT", "BELOW_FLOOR"
    return verdict, code


def _verdict_from_rubric_lines(rubric, floor, lexical_floor=False):
    if not rubric or rubric.get("status") != "DONE":
        return "REJECT", "UNPARSEABLE"
    if str(rubric.get("phrase_verbatim")).upper() != "Y" or rubric.get("phrase_verbatim_code") == "N" \
            or rubric.get("reason_code_final") == "NOT_VERBATIM":
        return "REJECT", "NOT_VERBATIM"
    if str(rubric.get("subject_is_required")).upper() != "Y":
        return "REJECT", "WRONG_SUBJECT"
    if str(rubric.get("speech_act_is_assertion")).upper() != "Y":
        return "REJECT", "NOT_ASSERTION"
    if floor not in FLOOR_ORDER:
        return "REJECT", "UNPARSEABLE"          # session 6: no floor line, no verdict (a salvaged truncated reply)
    if floor == "WORD_ONLY" and not lexical_floor:
        return "REJECT", "BELOW_FLOOR"
    if rubric.get("verdict_model") == "REJECT":
        return "REJECT", rubric.get("reason_code") or "OTHER"
    if floor == "PARTIAL" or rubric.get("hazard_flags") or rubric.get("verdict_model") == "ACCEPT_WITH_CAVEAT":
        return "ACCEPT_WITH_CAVEAT", rubric.get("reason_code") or "OK"
    return "ACCEPT", "OK"


def _chunk_views(chunks):
    """Assign per-call keys c1..cN; return (views, key->chunk)."""
    views, by_key = [], {}
    for i, c in enumerate(chunks, 1):
        key = f"c{i}"
        views.append(guards.agent_view(c, key))
        by_key[key] = c
    return views, by_key


class CellRunner:
    def __init__(self, llm, registry, predicates, comparators, state_dir, locator_model, verifier_models, coder_model=None,
                 log=print, run_coder=True, exhaust=True):
        self.llm = llm
        self.reg = registry
        self.predicates = predicates
        self.comparators = comparators
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.locator_model = locator_model
        self.verifier_models = list(verifier_models)
        self.primary = self.verifier_models[0]
        self.adjudicator = self.verifier_models[1] if len(self.verifier_models) > 1 else None
        self.routing = registry.verifier_routing or "PRIMARY_ONLY"
        self.slice_rows = registry.opus_slice_rows() if (self.adjudicator and registry.routing_is_slice()) else set()
        self.coder_model = coder_model or locator_model
        self.log = log
        self.run_coder = run_coder
        self.exhaust = exhaust
        self._pairs = {}

    def pairs(self, branch):
        """Translation pairs of a branch (allocation.translation_pairs), derived once from the registry."""
        if branch not in self._pairs:
            try:
                self._pairs[branch] = translation_pairs(self.reg, branch)
            except Exception:
                self._pairs[branch] = {}
        return self._pairs[branch]

    # ---------------------------------------------------------------- state
    def _path(self, qid):
        return os.path.join(self.state_dir, f"{qid}.json")

    def load(self, qid):
        p = self._path(qid)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        return None

    def save(self, st):
        with open(self._path(st["queue_id"]), "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)

    # ---------------------------------------------------------------- calls with a ceiling retry
    RETRY_CEILING = 8000

    def _call(self, role, system, user, model, max_tokens, meta, required=()):
        """One call, parsed. A reply that came back unparseable (the JSON cut off at the token ceiling,
        as happens when the ceiling is spent before the text block) is re-sent ONCE with a larger
        ceiling under a distinct call identity (attempt=1). Returns (out, rec, parsed, attempt);
        out is None while a call is pending.
        Session 6: `required` keys — a truncated reply that parse_json SALVAGES (it closes the object after the last complete
        pair) but that lacks one of them is incomplete, not answered: it takes the same retry. (A verifier reply cut off before
        its `floor` line was salvaged and scored ACCEPT on two carded live-1 candidates, Q-081 and Q-099.)"""
        out, rec = self.llm.complete(role, system, user, model=model, max_tokens=max_tokens, meta=meta)
        if out is None:
            return None, rec, None, 0
        parsed = prompts.parse_json(out)
        if parsed is not None and all(parsed.get(k) not in (None, "") for k in required):
            return out, rec, parsed, 0
        out2, rec2 = self.llm.complete(role, system, user, model=model, max_tokens=max(self.RETRY_CEILING, max_tokens * 2),
                                       meta=meta, attempt=1)
        if out2 is None:
            return None, rec2, None, 1
        parsed2 = prompts.parse_json(out2)
        if parsed2 is not None and not all(parsed2.get(k) not in (None, "") for k in required):
            parsed2 = None                                  # still incomplete after the retry: UNPARSEABLE, never a verdict
        return out2, rec2, parsed2, 1

    # ---------------------------------------------------------------- locator (per standard)
    def standards_for_pass(self, branch, pass_no):
        standards = self.reg.for_branch(branch, include_fallback=True, citable_only=True)
        if pass_no == 1:
            return [r for r in standards if not self.reg.is_fallback(r["registry_id"])]
        return [r for r in standards if self.reg.is_fallback(r["registry_id"])]      # pass two: the fallback row(s) only

    RECUT_ATTEMPTS = 3

    def _recut(self, cell, pred, cand, chunk, key, rid, pass_no):
        """Re-cut an over-long phrase until it fits the ≤15-word rule (2026-09-12: shorten, don't give up).

        Up to RECUT_ATTEMPTS locator calls. Attempt 1 asks for the shortest span carrying the predicate;
        attempt 2 feeds back the re-cut that was still too long with its word count; attempt 3 also lists
        the legal ≤15-word spans of the original phrase (enumerated in code, chosen by the locator — code
        never writes a phrase). The candidate is dropped only when the locator returns NO_VALID_CUT or
        every attempt is still over the limit. Returns (status, candidate_or_None, raw, attempts)."""
        chunk_view = {"chunk_key": key, "registry_id": chunk["registry_id"], "locator": chunk["locator"], "text": scrub_urls(chunk["text"])}
        too_long, raws = [], []
        for attempt in range(self.RECUT_ATTEMPTS):
            spans = legal_spans(cand.get("phrase", "")) if attempt >= 2 else None
            user = prompts.recut_user(pred, chunk_view, cand, attempts=too_long or None, legal_spans=spans)
            guards.assert_no_urls({"u": user})
            out, rec, parsed, _ = self._call("recut", prompts.RECUT_SYSTEM, user, self.locator_model, 600,
                                             {"queue_id": cell["queue_id"], "branch": cell["branch"], "family_id": cell["family_id"],
                                              "pass": pass_no, "registry_id": rid, "recut_of": cand.get("phrase", "")[:80], "recut_attempt": attempt + 1})
            if out is None:
                return "PENDING", None, None, too_long
            raws.append(out[:600])
            parsed = parsed or {}
            phrase = (parsed.get("phrase") or "").strip()
            if not phrase:
                return "NO_VALID_CUT", None, " || ".join(raws), too_long
            if phrase_word_count(phrase) <= PHRASE_MAX_WORDS:
                new = dict(cand)
                new.update({"phrase": phrase, "rationale": parsed.get("rationale") or cand.get("rationale", ""),
                            "floor_claim": parsed.get("floor_claim") or cand.get("floor_claim"), "recut_from": cand.get("phrase"),
                            "recut_attempts": attempt + 1})
                return "DONE", new, " || ".join(raws), too_long
            too_long.append(phrase)
        return "STILL_TOO_LONG", None, " || ".join(raws), too_long

    def locate_standard(self, cell, pred, comp, row, pass_no, chunks=None, coverage=None, batch=None, n_batches=None):
        """Locator call for ONE standard. Returns the per-standard entry (status PENDING when a call
        is unanswered — the caller re-runs; answered calls are served from the audit log).
        `chunks` / `coverage` / `batch` are set by the exhaustion pass (Task 2c): the chunks are then the
        batch of not-yet-supplied chunks and the pass label says so; otherwise the ordinary per-standard
        retrieval (retrieval.select_for_standard) is used."""
        rid = row["registry_id"]
        include_fallback = pass_no >= 2 and self.reg.is_fallback(rid)
        if chunks is None:
            chunks, coverage = retrieval.select_for_standard(pred, row)
        if not chunks:
            return {"status": "NO_CORPUS", "candidates": [], "dropped": []}
        views, by_key = _chunk_views(chunks)
        sv = self.reg.public(rid)
        sv["coverage"] = coverage
        if batch is None:
            label = f"pass {pass_no}"
        else:
            label = (f"pass {pass_no} (exhaustion of {rid}: batch {batch} of {n_batches} — chunks of this standard "
                     f"not supplied in an earlier pass; the earlier passes found no surviving candidate)")
        user = prompts.locator_user(cell, pred, comp, views, [sv], label)
        guards.assert_no_urls({"u": user})
        meta = {"queue_id": cell["queue_id"], "branch": cell["branch"], "family_id": cell["family_id"], "pass": pass_no, "registry_id": rid}
        if batch is not None:
            meta["exhaustion_batch"] = batch
        out, rec, parsed, attempt = self._call("locator", prompts.LOCATOR_SYSTEM, user, self.locator_model, 3000, meta)
        entry = {"status": "PENDING", "call_id": rec["call_id"], "attempt": attempt, "coverage": coverage,
                 "supplied_chunks": [(rid, c["locator"]) for c in chunks], "supplied_chars": sum(len(c["text"]) for c in chunks),
                 "candidates": [], "dropped": [], "recuts": [], "batch": batch}
        if out is None:
            return entry
        entry["raw"] = out[:4000]
        if not parsed:
            entry["status"] = "UNPARSEABLE"           # retried on the next run
            return entry
        # a reply may carry an explicit `"result": null` beside its candidates (Methodist / Wesleyan, 2026-09-13): treat as absent
        if str(parsed.get("result") or "").startswith("NOT LOCATED") or not parsed.get("candidates"):
            entry["status"] = "EMPTY"
            entry["empty"] = True
            entry["silence_rationale"] = " ".join(str(parsed.get("silence_rationale") or "").split()[:40]) or None
            return entry
        seen = set()
        tag = f"p{pass_no}-{rid}" + (f"-b{batch}" if batch is not None else "")
        for cand in parsed.get("candidates", [])[:MAX_CANDIDATES * 2]:
            ok, why, chunk = guards.vet_candidate(cand, by_key, cell["branch"], self.reg, allow_fallback=include_fallback)
            if not ok and why.startswith("phrase exceeds") and chunk is not None:
                status, new, raw, too_long = self._recut(cell, pred, cand, chunk, cand.get("chunk_key"), rid, pass_no)
                if status == "PENDING":
                    entry["status"] = "PENDING"
                    return entry
                entry["recuts"].append({"from": cand.get("phrase"), "status": status, "to": (new or {}).get("phrase"),
                                        "attempts": len(too_long) + 1, "still_too_long": too_long, "raw": raw})
                if new is not None:
                    ok, why, chunk = guards.vet_candidate(new, by_key, cell["branch"], self.reg, allow_fallback=include_fallback)
                    cand = new
                    why = f"after re-cut: {why}" if not ok else why
                else:
                    why = f"{why}; re-cut returned {status}"
            if not ok:
                entry["dropped"].append({"candidate": cand, "reason": why})
                continue
            k = guards.dedupe_key({"registry_id": chunk["registry_id"], "locator": chunk["locator"], "phrase": cand["phrase"]})
            if k in seen:
                entry["dropped"].append({"candidate": cand, "reason": "duplicate locator+phrase"})
                continue
            seen.add(k)
            n = len(entry["candidates"]) + 1
            entry["candidates"].append({
                "candidate_id": f"{cell['queue_id']}-{tag}-{n}",
                "pass": pass_no, "registry_id": rid, "locator": chunk["locator"],
                "phrase": cand["phrase"], "rationale": cand.get("rationale", ""), "floor_claim": cand.get("floor_claim"),
                "chunk_text": scrub_urls(chunk["text"]), "chunk_hash": chunk["text_hash"], "division": chunk["division"],
                "fallback_tier": self.reg.is_fallback(rid), "witness": self.reg.is_witness(rid),
                "effective_tier": self.reg.effective_tier(rid, chunk, cand["phrase"]), "locator_rank": n,
                "recut_from": cand.get("recut_from"), "exhaustion_batch": batch,
            })
            if len(entry["candidates"]) >= MAX_CANDIDATES:
                break
        entry["status"] = "DONE"
        entry["empty"] = not entry["candidates"]
        return entry

    @staticmethod
    def _slot(entries_in_order):
        """One guaranteed slot per (standard) entry's best candidate, then the extras by tier, (1a) non-witness
        before witness within the tier, floor claim and locator rank. Returns (slotted, unslotted)."""
        slotted, extra = [], []
        for e in entries_in_order:
            cands = e.get("candidates") or []
            if cands:
                first = dict(cands[0]); first["slot"] = "GUARANTEED"
                slotted.append(first)
                extra.extend(dict(c, slot="EXTRA") for c in cands[1:])
        extra.sort(key=lambda c: (tier_rank(c.get("effective_tier")), 1 if c.get("witness") else 0,
                                  FLOOR_ORDER.get(c.get("floor_claim"), 9), c.get("locator_rank", 9)))
        slotted.extend(extra[:VERIFY_EXTRA_CANDIDATES])
        return slotted, [dict(c, slot="UNSLOTTED") for c in extra[VERIFY_EXTRA_CANDIDATES:]]

    def locate(self, cell, pass_no, st):
        pred = self.predicates[cell["family_id"]]
        comp = self.comparators.get(cell["family_id"], {})
        standards = self.standards_for_pass(cell["branch"], pass_no)
        prev = (st["passes"].get(str(pass_no)) or {})
        per = dict(prev.get("per_standard") or {})
        result = {"status": "DONE", "standards": [r["registry_id"] for r in standards], "per_standard": per,
                  "retrieval": "PER_STANDARD", "candidates": [], "unslotted": [], "dropped": [], "coverage": {}, "supplied_chunks": []}
        if not standards:
            result["status"] = "NO_CORPUS"
            return result
        pending = False
        for row in standards:
            rid = row["registry_id"]
            e = per.get(rid)
            if e and e.get("status") in ("DONE", "EMPTY", "NO_CORPUS"):
                continue
            e = self.locate_standard(cell, pred, comp, row, pass_no)
            per[rid] = e
            if e["status"] in ("PENDING", "UNPARSEABLE"):
                pending = True
        if pending:
            result["status"] = "PENDING"
            return result
        if all(per[r["registry_id"]].get("status") == "NO_CORPUS" for r in standards):
            result["status"] = "NO_CORPUS"
            return result
        # ---- slotting: one guaranteed slot per standard, then the extras by tier and floor
        entries = []
        for row in standards:
            e = per[row["registry_id"]]
            result["dropped"].extend([dict(d, registry_id=row["registry_id"]) for d in e.get("dropped", [])])
            result["coverage"][row["registry_id"]] = e.get("coverage")
            result["supplied_chunks"].extend(e.get("supplied_chunks", []))
            entries.append(e)
        slotted, unslotted = self._slot(entries)
        # Session 5 (supplementary single-standard passes): a re-locate over stored entries never un-slots a candidate that
        # was already slotted and verified — its verification is paid for and its verdict stands. In an ordinary run a pass
        # is re-located only while PENDING, before anything was slotted, so this changes nothing there.
        slotted_ids = {c["candidate_id"] for c in slotted}
        for c in prev.get("candidates") or []:
            v = (st.get("verifications") or {}).get(c["candidate_id"]) or {}
            if c["candidate_id"] not in slotted_ids and (v.get(self.primary) or {}).get("status") == "DONE":
                slotted.append(dict(c, kept_from_prior_slotting=True))
                slotted_ids.add(c["candidate_id"])
                unslotted = [u for u in unslotted if u["candidate_id"] != c["candidate_id"]]
        result["unslotted"] = unslotted
        result["candidates"] = slotted
        result["empty"] = not slotted
        result["standards_reviewed"] = [r["registry_id"] for r in standards if per[r["registry_id"]].get("status") != "NO_CORPUS"]
        result["silence_rationale"] = {r["registry_id"]: per[r["registry_id"]].get("silence_rationale") for r in standards
                                       if per[r["registry_id"]].get("status") == "EMPTY"}
        return result

    # ---------------------------------------------------------------- exhaustion (Task 2c)
    def sampled_standards(self, st):
        """Standards consulted in passes 1–2 whose coverage was RETRIEVED (sampled, not reviewed whole)."""
        out = []
        for pk in ("1", "2"):
            p = st["passes"].get(pk) or {}
            for rid, cov in (p.get("coverage") or {}).items():
                if cov and cov.get("coverage") == "RETRIEVED" and rid not in out:
                    out.append(rid)
        return out

    def _supplied_locators(self, st, rid):
        locs = set()
        for p in st["passes"].values():
            for r, loc in p.get("supplied_chunks", []):
                if r == rid:
                    locs.add(loc)
        return locs

    def locate_exhaust(self, cell, st):
        """Issue / ingest one ROUND of exhaustion calls. Returns "PENDING" (calls unanswered), "ROUND_DONE"
        (new candidates slotted into pass 3 — verify them; more batches remain), or "EXHAUSTED" (every
        sampled standard fully supplied). The batch plan (which chunks in which batch) is fixed on first
        use and stored, so a resumed run continues the same plan."""
        pred = self.predicates[cell["family_id"]]
        comp = self.comparators.get(cell["family_id"], {})
        p = st["passes"].get(EXHAUST_PASS) or {"status": "RUNNING", "retrieval": "EXHAUSTION", "standards": [], "per_standard": {},
                                                "batch_plan": {}, "progress": {}, "candidates": [], "unslotted": [], "dropped": [],
                                                "coverage": {}, "supplied_chunks": [], "rounds": 0}
        st["passes"][EXHAUST_PASS] = p
        rids = self.sampled_standards(st)
        p["standards"] = rids
        rows = {r["registry_id"]: r for r in self.reg.for_branch(cell["branch"], include_fallback=True, citable_only=True)}
        for rid in rids:
            if rid not in p["batch_plan"]:
                if rid not in rows:
                    continue
                batches, n_rem = retrieval.exhaustion_batches(pred, rows[rid], self._supplied_locators(st, rid))
                p["batch_plan"][rid] = [[c["locator"] for c in b] for b in batches]
                p["progress"][rid] = {"batches_total": len(batches), "chunks_remaining_at_start": n_rem, "batches_done": 0,
                                      "exhausted": len(batches) == 0, "stopped_early": False}
        # issue this round: up to EXHAUST_CALLS_PER_ROUND batches per standard that have no DONE/EMPTY entry yet
        pending, issued_any = False, False
        for rid in rids:
            plan = p["batch_plan"].get(rid) or []
            prog = p["progress"][rid]
            if prog["exhausted"] or prog["stopped_early"]:
                continue
            issued = 0
            chunks_all = {c["locator"]: c for c in retrieval.store.load_chunks(rid)}
            for k, locs in enumerate(plan, 1):
                key = f"{rid}#{k}"
                e = p["per_standard"].get(key)
                if e and e.get("status") in ("DONE", "EMPTY", "NO_CORPUS"):
                    continue
                if issued >= EXHAUST_CALLS_PER_ROUND:
                    break
                chunks = [chunks_all[l] for l in locs if l in chunks_all]
                cov = {"coverage": "EXHAUSTION_BATCH", "batch": k, "of_batches": len(plan), "supplied": len(chunks), "of": len(chunks_all)}
                e = self.locate_standard(cell, pred, comp, rows[rid], int(EXHAUST_PASS), chunks=chunks, coverage=cov, batch=k, n_batches=len(plan))
                p["per_standard"][key] = e
                issued += 1; issued_any = True
                if e["status"] in ("PENDING", "UNPARSEABLE"):
                    pending = True
        if pending:
            p["status"] = "PENDING"
            return "PENDING"
        p["rounds"] += 1 if issued_any else 0
        # ingest: every answered batch entry contributes; slot the round's candidates into the pass-3 list
        entries = []
        for rid in rids:
            plan = p["batch_plan"].get(rid) or []
            prog = p["progress"][rid]
            done = 0
            for k in range(1, len(plan) + 1):
                e = p["per_standard"].get(f"{rid}#{k}")
                if e and e.get("status") in ("DONE", "EMPTY"):
                    done += 1
                    for d in e.get("dropped", []):
                        rec = dict(d, registry_id=rid)
                        if rec not in p["dropped"]:
                            p["dropped"].append(rec)
                    for sc in e.get("supplied_chunks", []):
                        if list(sc) not in [list(x) for x in p["supplied_chunks"]]:
                            p["supplied_chunks"].append(sc)
                    entries.append(e)
            prog["batches_done"] = done
            prog["exhausted"] = done >= len(plan)
            supplied = len(self._supplied_locators(st, rid) | {loc for e in entries if e.get("supplied_chunks") for r, loc in e["supplied_chunks"] if r == rid})
            total = len(retrieval.store.load_chunks(rid))
            p["coverage"][rid] = {"coverage": "EXHAUSTED" if prog["exhausted"] else "RETRIEVED", "supplied": min(supplied, total), "of": total,
                                  "batches_done": done, "batches_total": len(plan)}
        known = {c["candidate_id"] for c in p["candidates"]}
        slotted, unslotted = self._slot(entries)
        for c in slotted:
            if c["candidate_id"] not in known:
                p["candidates"].append(c); known.add(c["candidate_id"])
        p["unslotted"] = [c for c in unslotted if c["candidate_id"] not in known]
        p["silence_rationale"] = {}
        for key, e in p["per_standard"].items():
            if e.get("status") == "EMPTY" and e.get("silence_rationale"):
                p["silence_rationale"].setdefault(key.split("#")[0], []).append(e["silence_rationale"])
        p["empty"] = not p["candidates"]
        all_exhausted = all(p["progress"][rid]["exhausted"] for rid in rids) if rids else True
        p["status"] = "EXHAUSTED" if all_exhausted else "ROUND_DONE"
        return p["status"]

    def coverage_final(self, st):
        """Per consulted standard, the coverage the cell ends with: FULL, EXHAUSTED (every chunk supplied
        across passes), or RETRIEVED supplied-of-total (sampled; with why exhaustion stopped, if it ran)."""
        out = {}
        for pk in ("1", "2"):
            p = st["passes"].get(pk) or {}
            for rid, cov in (p.get("coverage") or {}).items():
                if cov:
                    out[rid] = {"coverage": cov.get("coverage"), "supplied": cov.get("supplied"), "of": cov.get("of"), "pass": pk}
        p3 = st["passes"].get(EXHAUST_PASS) or {}
        for rid, cov in (p3.get("coverage") or {}).items():
            base = out.get(rid, {})
            prog = (p3.get("progress") or {}).get(rid) or {}
            out[rid] = {"coverage": cov["coverage"], "supplied": cov["supplied"], "of": cov["of"], "pass": base.get("pass"),
                        "exhaustion": {"batches_done": cov.get("batches_done"), "batches_total": cov.get("batches_total"),
                                       "stopped_early": prog.get("stopped_early", False),
                                       "reason": ("a candidate survived verification; the standard was not read to the end" if prog.get("stopped_early")
                                                  else ("every chunk supplied" if cov["coverage"] == "EXHAUSTED" else "exhaustion incomplete"))}}
        return out

    # ---------------------------------------------------------------- verifier
    def verify(self, cell, cand, model):
        pred = self.predicates[cell["family_id"]]
        chunk_view = {"registry_id": cand["registry_id"], "locator": cand["locator"], "text": cand["chunk_text"]}
        user = prompts.verifier_user(pred, cand, chunk_view)
        guards.assert_no_urls({"u": user})
        # Session 8 (R6-13): a scoped verifier version sends JOINT PREDICATION and AGENCY only to a Spirit family; the
        # variant sent is recorded on the call and on the rubric.
        variant = prompts.verifier_variant(pred)
        out, rec, parsed, attempt = self._call("verifier", prompts.verifier_system(pred), user, model, 2500,
                                               {"queue_id": cell["queue_id"], "branch": cell.get("branch"), "candidate_id": cand["candidate_id"],
                                                "verifier_model": model, "verifier_variant": variant},
                                               required=VERIFIER_REQUIRED)
        if out is None:
            return {"status": "PENDING", "call_id": rec["call_id"], "model": model, "prompt_variant": variant}
        parsed = parsed or {}
        rubric = {
            "model": model, "call_id": rec["call_id"], "attempt": attempt, "prompt_version": prompts.prompt_version("verifier"),
            "prompt_variant": variant,
            "phrase_verbatim": parsed.get("phrase_verbatim"), "subject_is_required": parsed.get("subject_is_required"),
            "grammatical_subject": parsed.get("grammatical_subject"), "speech_act_is_assertion": parsed.get("speech_act_is_assertion"),
            "speech_act_note": parsed.get("speech_act_note"), "floor": parsed.get("floor"), "floor_reason": parsed.get("floor_reason"),
            "hazard_flags": [h for h in (parsed.get("hazard_flags") or []) if h in prompts.HAZARD_TYPES],
            "asserted_outside_formula": parsed.get("asserted_outside_formula"),
            "partial_asserts_predicate": parsed.get("partial_asserts_predicate"),
            "verdict_model": parsed.get("verdict"), "reason_code": parsed.get("reason_code"), "reason": parsed.get("reason"),
            "status": "DONE" if parsed else "UNPARSEABLE", "raw": out[:2000],
        }
        # Task 3 (session 4): IDIOM_OR_FORMULA caps the floor at WORD_ONLY unless the passage separately asserts
        # the predicate outside the formula. The model's own floor is kept beside the capped one for the record.
        if parsed and HAZARD_IDIOM_OR_FORMULA in rubric["hazard_flags"] and str(rubric["asserted_outside_formula"]).upper() != "Y" \
                and FLOOR_ORDER.get(rubric["floor"], 9) < FLOOR_ORDER[FORMULA_FLOOR_CAP]:
            rubric["floor_model"] = rubric["floor"]
            rubric["floor"] = FORMULA_FLOOR_CAP
            rubric["floor_capped_by"] = HAZARD_IDIOM_OR_FORMULA
        # Session 6 (R6-2, verifier gate6-v1.3): PARTIAL is for the predicate asserted incompletely, never a neighbouring
        # proposition. A PARTIAL floor the verifier itself marks partial_asserts_predicate = N is capped at WORD_ONLY.
        if parsed and rubric["floor"] == "PARTIAL" and str(rubric.get("partial_asserts_predicate")).upper() == "N":
            rubric["floor_model"] = rubric["floor"]
            rubric["floor"] = NEIGHBOURING_FLOOR_CAP
            rubric["floor_capped_by"] = CAP_NEIGHBOURING_PROPOSITION
        # the verdict is recomputed in code from the rubric lines: any N on 1–3 is REJECT; WORD_ONLY is REJECT
        # (no lexical-floor family); the code-side phrase assertion overrides item 1.
        ok_phrase, _ = guards.check_phrase(cand["phrase"], cand["chunk_text"])
        rubric["phrase_verbatim_code"] = "Y" if ok_phrase else "N"
        verdict, code = verdict_from_rubric(rubric, rubric["floor"], bool(pred.get("lexical_floor")))
        # Session 9 (R6-18): record the refusal where the outside-formula guard is what turned an accept into REJECT
        before_guard = _verdict_from_rubric_lines(rubric, rubric["floor"], bool(pred.get("lexical_floor")))[0]
        if before_guard in ACCEPTS and verdict == "REJECT" and outside_formula_guard_applies(rubric):
            rubric["verdict_before_outside_formula_guard"] = before_guard
            rubric["refused_by"] = OUTSIDE_FORMULA_GUARD
        # Session 7 (R6-7): on a family whose required subject IS the Holy Spirit, an accept whose phrase does not name
        # the Spirit is refused in code. This is the collective form ("one God, Father, Son and Holy Spirit, is X" cut
        # so the Spirit's name falls outside the quoted ≤15 words) and the inference from the unity of the essence to
        # each person. Refused, not capped: the phrase does not assert the predicate OF THE SPIRIT at any floor.
        if required_subject_is_the_spirit(pred) and not phrase_names_the_spirit(cand["phrase"]):
            rubric["spirit_name_in_phrase"] = "N"
            if verdict in ACCEPTS:
                rubric["verdict_before_spirit_guard"] = verdict
                rubric["refused_by"] = SPIRIT_SUBJECT_GUARD
                verdict, code = "REJECT", "WRONG_SUBJECT"
        elif required_subject_is_the_spirit(pred):
            rubric["spirit_name_in_phrase"] = "Y"
        rubric["verdict"] = verdict
        rubric["reason_code_final"] = code
        return rubric

    def needs_adjudication(self, cand, all_rejected):
        if not self.adjudicator:
            return None
        if not self.reg.routing_is_slice():
            return "SECONDARY_ALL"          # a non-slice routing: the second model verifies everything
        if cand["registry_id"] in self.slice_rows:
            return "SLICE_ROW"
        if cand.get("fallback_tier"):
            return "FALLBACK_ROW"
        if all_rejected:
            return "PRIMARY_REJECTED_ALL"
        return None

    @staticmethod
    def finalize(v, primary, adjudicator):
        """Final verdict under the session-4 rulings (2a/2b/2c), recomputed in code from the stored rubrics:

          base rubric   the adjudicator's where it ran on an ADJUDICATING route (slice row, fallback row, the
                        primary rejected all, a secondary-verifies-all routing) — it still judges lines 1–3 and
                        can rescue a candidate refused for subject or speech act (2b); on every other route
                        that carries a second rubric (the retired CAVEATED_ACCEPT adjudication, the 2c sample,
                        a both-models planted run) the base is the PRIMARY's rubric and the second rubric is
                        disclosure only;
          floor         the LOWER of the two models' floors wherever both returned one (2a) — never averaged,
                        never the adjudicator's; the verdict is then recomputed at that floor by the same rule
                        verify() applies, so a merged WORD_ONLY refuses the candidate (BELOW_FLOOR).

        Overturns are recorded against the primary's own verdict, as before."""
        p = v.get(primary) or {}
        a = v.get(adjudicator) if adjudicator else None
        a_done = bool(a and a.get("status") == "DONE")
        route = v.get("_route")
        adjudicating = a_done and route in ADJUDICATING_ROUTES
        base_model = adjudicator if adjudicating else primary
        base = a if adjudicating else p
        floors = {primary: p.get("floor")}
        if a_done:
            floors[adjudicator] = a.get("floor")
        floor = lower_floor(*floors.values()) if a_done else p.get("floor")
        # Session 6 (R6-2): floor caps recorded on the verification record by an author ruling or by the hedged-PARTIAL audit
        # (partial_rule.py) — never a raise; they survive a rebuild and a later re-verification alike.
        caps = [c for c in (v.get("floor_rulings") or []) if c.get("floor_cap") in FLOOR_ORDER]
        floor_before_rulings = floor
        for c in caps:
            floor = lower_floor(floor, c["floor_cap"]) if floor in FLOOR_ORDER else c["floor_cap"]
        verdict, code = verdict_from_rubric(base, floor)
        fin = {"verdict": verdict, "reason_code_final": code, "adjudicated_by": base_model, "route": route,
               "primary_verdict": p.get("verdict"), "verdict_rule": LOWER_FLOOR_RULE,
               "floor_final": floor, "floor_by_model": floors,
               "floor_disagreement": bool(a_done and p.get("floor") != a.get("floor") and p.get("floor") in FLOOR_ORDER and a.get("floor") in FLOOR_ORDER),
               "lower_floor_applied": bool(a_done and floor != base.get("floor") and floor in FLOOR_ORDER),
               "second_rubric": (adjudicator if a_done else None),
               "second_rubric_role": ("ADJUDICATES_LINES_1_3" if adjudicating else ("DISCLOSURE_FLOOR_ONLY" if a_done else None))}
        if caps:
            fin["floor_rulings_applied"] = [c.get("by") for c in caps]
            fin["floor_before_rulings"] = floor_before_rulings
            fin["floor_capped_by_ruling"] = floor != floor_before_rulings
        if verdict == "REJECT" and outside_formula_guard_applies(base) and _verdict_from_rubric_lines(base, floor)[0] in ACCEPTS:
            fin["refused_by"] = OUTSIDE_FORMULA_GUARD
        if a_done:
            fin["adjudicator_verdict"] = a.get("verdict")
        # an overturn is the second model's doing; a floor ruling's refusal is recorded separately (floor_capped_by_ruling)
        pa, fa = p.get("verdict") in ACCEPTS, (verdict_from_rubric(base, floor_before_rulings)[0] if caps else verdict) in ACCEPTS
        fin["overturned"] = bool(a_done) and pa != fa
        fin["direction"] = ("RESCUED" if (fa and not pa) else "OVERRULED" if (pa and not fa) else None) if a_done else None
        v["final"] = fin
        return fin

    def _verify_pass(self, cell, st, pass_key):
        """Primary on every slotted candidate; the routed slice to the adjudicator; then (Task 3) the caveated
        accepts that the allocation would put on the card, repeated until the card is stable. Returns True
        while a call is pending."""
        p = st["passes"].get(pass_key) or {}
        cands = p.get("candidates", [])
        pending = False
        for cand in cands:
            v = st["verifications"].setdefault(cand["candidate_id"], {})
            if self.primary not in v or v[self.primary].get("status") in ("PENDING", "UNPARSEABLE"):
                v[self.primary] = self.verify(cell, cand, self.primary)
            if v[self.primary].get("status") == "PENDING":
                pending = True
        if pending:
            return True
        all_rejected = bool(cands) and all(st["verifications"][c["candidate_id"]][self.primary].get("verdict") not in ACCEPTS for c in cands)
        for cand in cands:
            v = st["verifications"][cand["candidate_id"]]
            route = self.needs_adjudication(cand, all_rejected)
            if route or not v.get("_route"):
                v["_route"] = route if route else v.get("_route")
            if route and (self.adjudicator not in v or v[self.adjudicator].get("status") in ("PENDING", "UNPARSEABLE")):
                v[self.adjudicator] = self.verify(cell, cand, self.adjudicator)
            if route and v[self.adjudicator].get("status") == "PENDING":
                pending = True
        if pending:
            return True
        for cand in cands:
            self.finalize(st["verifications"][cand["candidate_id"]], self.primary, self.adjudicator)
        # ---- 2c (session 4): caveated accepts are NOT routed for adjudication. A deterministic sample of at most
        # CAVEAT_SAMPLE_SHARE of the caveated accepts that reach a card is sent to the second model for information;
        # its rubric is disclosure on the card and, under 2a, can lower the floor but never raise the verdict.
        # Repeated until the card is stable (a lowered floor can promote another survivor onto the card).
        if self.adjudicator and self.reg.routing_is_slice():
            for _ in range(len(cands) + 1):
                survivors = [c for c in cands if self.final_verdict(st, c["candidate_id"]) in ACCEPTS]
                alloc = allocate(self.allocation_view(survivors), self.pairs(cell["branch"]), groups=self.groups(cell["branch"]))
                on_card = set(alloc["kept"]) | set(alloc["english_witness"].values())
                fired = False
                for cand in cands:
                    cid = cand["candidate_id"]
                    v = st["verifications"][cid]
                    adj = v.get(self.adjudicator)
                    if cid not in on_card or (adj and adj.get("status") == "DONE") or not caveat_slice_hit(v.get(self.primary)):
                        continue
                    rec = st.setdefault("caveat_sample", {}).get(cid)
                    if rec is None:
                        rec = self.sample_decision(cell["branch"], st, cid)
                        st["caveat_sample"][cid] = rec
                    if not rec["sampled"]:
                        continue
                    v["_route"] = ROUTE_CAVEAT_SAMPLE
                    v[self.adjudicator] = self.verify(cell, cand, self.adjudicator)
                    fired = True
                    if v[self.adjudicator].get("status") == "PENDING":
                        pending = True
                if pending:
                    return True
                if not fired:
                    break
                for cand in cands:
                    self.finalize(st["verifications"][cand["candidate_id"]], self.primary, self.adjudicator)
        return False

    # ---------------------------------------------------------------- 2c sample bookkeeping
    def sample_quota(self, branch, exclude_qid=None):
        """(eligible, sampled) so far on this branch, from the saved cell states, so the running share never
        exceeds CAVEAT_SAMPLE_SHARE across a branch however the cells are ordered or resumed."""
        eligible = sampled = 0
        for fn in os.listdir(self.state_dir):
            if not fn.endswith(".json") or fn[:-5] == exclude_qid:
                continue
            try:
                with open(os.path.join(self.state_dir, fn), encoding="utf-8") as fh:
                    st = json.load(fh)
            except Exception:
                continue
            if st.get("branch") != branch:
                continue
            for rec in (st.get("caveat_sample") or {}).values():
                eligible += 1
                sampled += 1 if rec.get("sampled") else 0
        return eligible, sampled

    def sample_decision(self, branch, st, cid):
        """Sample this eligible candidate? Deterministic by hash bucket, and bounded: the branch's running share
        (including this cell's earlier decisions) stays at or under CAVEAT_SAMPLE_SHARE after the draw."""
        eligible, sampled = self.sample_quota(branch, exclude_qid=st["queue_id"])
        for rec in (st.get("caveat_sample") or {}).values():
            eligible += 1; sampled += 1 if rec.get("sampled") else 0
        bucket = sample_bucket(cid)
        within_quota = (sampled + 1) <= CAVEAT_SAMPLE_SHARE * (eligible + 1)
        take = bucket < int(CAVEAT_SAMPLE_SHARE * 100) and within_quota
        return {"sampled": take, "bucket": bucket, "share_cap": CAVEAT_SAMPLE_SHARE,
                "branch_eligible_before": eligible, "branch_sampled_before": sampled,
                "reason": ("sampled for disclosure" if take else ("bucket outside the sample" if bucket >= int(CAVEAT_SAMPLE_SHARE * 100)
                                                                     else "branch sample share already at its cap"))}

    def groups(self, branch):
        """speaks_for groups of a branch (allocation.speaks_for_groups), derived once from the registry."""
        if not hasattr(self, "_groups"):
            self._groups = {}
        if branch not in self._groups:
            try:
                self._groups[branch] = speaks_for_groups(self.reg, branch)
            except Exception:
                self._groups[branch] = {}
        return self._groups[branch]

    def refinalize(self, st, cell_branch=None):
        """Deterministic rebuild of a DONE cell state under the current verdict rule and allocator — no model calls.
        Recomputes every `final` (2a/2b/2c from the stored rubrics), the survivors, the exhaustion outcome, the
        allocation and coder_skipped. Coder proposals are left as stored (they were written for the rubric of the
        time; a candidate that now reaches the card uncoded is marked on the card). Returns the change summary."""
        before = {}
        for cid, v in st.get("verifications", {}).items():
            if "final_at_run" not in v and v.get("final"):
                v["final_at_run"] = dict(v["final"])          # the verdict the live run finalised on; kept for the record
            before[cid] = (v.get("final_at_run") or v.get("final") or {}).get("verdict")
            self.finalize(v, self.primary, self.adjudicator)
        after = {cid: v["final"]["verdict"] for cid, v in st.get("verifications", {}).items()}
        changed = {cid: (before[cid], after[cid]) for cid in after if before.get(cid) != after[cid]}
        s1, s2, s3 = self.survivors(st, "1"), self.survivors(st, "2"), self.survivors(st, EXHAUST_PASS)
        st["survivors"] = self.all_survivors(st)
        st["fallback_used"] = bool(not s1 and s2)
        if st.get("exhaustion"):
            st["exhaustion"]["changed_outcome"] = bool(not s1 and not s2 and s3)
            p3 = st["passes"].get(EXHAUST_PASS) or {}
            if not s3 and any(pr.get("stopped_early") for pr in (p3.get("progress") or {}).values()):
                st["exhaustion"]["resumable"] = True
                st["exhaustion"]["note"] = ("exhaustion stopped early on a candidate the lower-floor rule later refused; the standard "
                                            "was not read to the end — re-running the branch would resume it")
        if "coverage_final" in st or st.get("passes"):
            st["coverage_final"] = self.coverage_final(st)
        branch = cell_branch or st.get("branch")
        alloc = allocate(self.allocation_view(st["survivors"]), self.pairs(branch), groups=self.groups(branch))
        st["allocation"] = {k: alloc[k] for k in ("kept", "roles", "english_witness", "dropped", "witness_only", "groups", "slot_order", "parallel_witnesses")}
        st["coder_skipped"] = dict(alloc["dropped"])
        st["empty"] = not st["survivors"]
        st["refinalized"] = {"rule": LOWER_FLOOR_RULE, "verdicts_changed": changed}
        return changed

    # ---------------------------------------------------------------- coder
    def code(self, cell, cand, rubric):
        pred = self.predicates[cell["family_id"]]
        comp = self.comparators.get(cell["family_id"], {})
        std = self.reg.public(cand["registry_id"])
        user = prompts.coder_user(cell, pred, comp, cand, {k: rubric.get(k) for k in ("floor", "floor_reason", "hazard_flags", "verdict", "grammatical_subject")}, std)
        guards.assert_no_urls({"u": user})
        out, rec = self.llm.complete("coder", prompts.CODER_SYSTEM, user, model=self.coder_model, max_tokens=1200,
                                     meta={"queue_id": cell["queue_id"], "branch": cell.get("branch"), "candidate_id": cand["candidate_id"]})
        if out is None:
            return {"status": "PENDING", "call_id": rec["call_id"]}
        parsed = prompts.parse_json(out) or {}
        note = parsed.get("source_note", "")
        ok, why = guards.vet_source_note(note)
        proposal = {"status": "DONE", "call_id": rec["call_id"], "rendered_state": parsed.get("rendered_state"),
                    "diverges_from_family_code": parsed.get("diverges_from_family_code"), "state_reason": parsed.get("state_reason"),
                    "source_note": note if ok else " ".join(note.split()[:40]), "source_note_guard": why,
                    "scope_caveat": std["scope_caveat"], "raw": out[:1500]}
        # Session 7, clause 4 (R6-11): a creed's silence is never a finding. A DIVERGENCE proposal whose only support
        # is that a creed does not contain the predicate is refused HERE, in code — the prompt's creedal-silence line
        # states the rule, this makes it a hard stop that does not depend on the model reading it. The proposal is kept
        # on the card with its refusal; the state falls back to the family's own code.
        stop = guards.creedal_silence_stop(proposal, rubric, self.predicates[cell["family_id"]].get("family_code"))
        if stop:
            proposal.update(stop)
        return proposal

    # ---------------------------------------------------------------- orchestration
    def run_cell(self, cell):
        """Advance one cell as far as the backend allows. Returns the state dict."""
        st = self.load(cell["queue_id"]) or {"queue_id": cell["queue_id"], "branch": cell["branch"], "family_id": cell["family_id"],
                                              "predicate": cell["predicate"], "passes": {}, "verifications": {}, "coding": {},
                                              "phase": "locate-1", "routing": self.routing, "primary": self.primary,
                                              "adjudicator": self.adjudicator, "slice_rows": sorted(self.slice_rows)}
        # pass 1
        if "1" not in st["passes"] or st["passes"]["1"].get("status") in ("PENDING", "UNPARSEABLE"):
            st["passes"]["1"] = self.locate(cell, 1, st)
            self.save(st)
            if st["passes"]["1"]["status"] == "PENDING":
                st["phase"] = "locate-1"; return st
        if self._verify_pass(cell, st, "1"):
            st["phase"] = "verify-1"; self.save(st); return st
        survivors1 = self.survivors(st, "1")
        # pass 2 only if pass 1 left nothing surviving and the branch has a fallback row
        has_fallback = any(self.reg.is_fallback(r["registry_id"]) for r in self.reg.for_branch(cell["branch"]))
        if not survivors1 and has_fallback:
            if "2" not in st["passes"] or st["passes"]["2"].get("status") in ("PENDING", "UNPARSEABLE"):
                st["passes"]["2"] = self.locate(cell, 2, st)
                self.save(st)
                if st["passes"]["2"]["status"] == "PENDING":
                    st["phase"] = "locate-2"; return st
            if self._verify_pass(cell, st, "2"):
                st["phase"] = "verify-2"; self.save(st); return st
        # pass 3 (Task 2c): exhaust every sampled standard before declaring an empty
        # (session 5) a cell whose earlier exhaustion already produced a survivor is not re-entered by a supplementary pass
        if (not (self.survivors(st, "1") or self.survivors(st, "2")) and self.exhaust and self.sampled_standards(st)
                and not (st.get("exhaustion") or {}).get("changed_outcome")):
            st.setdefault("exhaustion", {"entered": True, "changed_outcome": False})
            while True:
                status = self.locate_exhaust(cell, st)
                self.save(st)
                if status == "PENDING":
                    st["phase"] = "locate-3"; self.save(st); return st
                if self._verify_pass(cell, st, EXHAUST_PASS):
                    st["phase"] = "verify-3"; self.save(st); return st
                if self.survivors(st, EXHAUST_PASS):
                    p3 = st["passes"][EXHAUST_PASS]
                    for rid, prog in p3["progress"].items():
                        if not prog["exhausted"]:
                            prog["stopped_early"] = True
                    for rid in p3["coverage"]:
                        if p3["coverage"][rid]["coverage"] != "EXHAUSTED":
                            p3["coverage"][rid]["coverage"] = "RETRIEVED"
                    st["exhaustion"]["changed_outcome"] = True
                    break
                if status == "EXHAUSTED":
                    break
                # ROUND_DONE with no survivor: the next round is issued by the loop
            st["exhaustion"]["standards"] = st["passes"][EXHAUST_PASS]["progress"]
            st["exhaustion"]["rounds"] = st["passes"][EXHAUST_PASS].get("rounds")
        st["survivors"] = self.all_survivors(st)
        st["fallback_used"] = bool(not self.survivors(st, "1") and self.survivors(st, "2"))
        st["coverage_final"] = self.coverage_final(st)
        # 1c: allocate the card FIRST (allocation.py, the same allocator the packet builder uses), then code only
        # the candidates that will reach the card. Everything the allocation drops is recorded as coder_skipped.
        alloc = allocate(self.allocation_view(st["survivors"]), self.pairs(cell["branch"]), groups=self.groups(cell["branch"]))
        st["allocation"] = {k: alloc[k] for k in ("kept", "roles", "english_witness", "dropped", "witness_only", "groups", "slot_order", "parallel_witnesses")}
        st["coder_skipped"] = dict(alloc["dropped"])
        if self.run_coder:
            for cand in st["survivors"]:
                cid = cand["candidate_id"]
                if cid not in alloc["kept"]:
                    continue
                if cid not in st["coding"] or st["coding"][cid].get("status") == "PENDING":
                    st["coding"][cid] = self.code(cell, cand, self.final_rubric(st, cid))
            if any(v.get("status") == "PENDING" for v in st["coding"].values()):
                st["phase"] = "coding"; self.save(st); return st
        st["phase"] = "DONE"
        st["empty"] = not st["survivors"]
        self.save(st)
        return st

    def allocation_view(self, cands):
        """The minimal candidate dicts allocation.allocate needs (tier, witness flag, reception, locator)."""
        out = []
        for c in cands:
            try:
                std = self.reg.public(c["registry_id"])
            except Exception:
                std = {}
            # session 12 (R6-41): the registered texts that raised the candidate, so the cell runner seats as the packet does
            try:
                cache = self.__dict__.setdefault("_chunk_cache", {})
                if c["registry_id"] not in cache:
                    cache[c["registry_id"]] = {x.get("locator"): x for x in store.load_chunks(c["registry_id"])}
                chunk = cache[c["registry_id"]].get(c.get("locator"))
                raised = self.reg.raised_by(c["registry_id"], chunk, c.get("phrase"))
            except Exception:
                raised = []
            out.append(dict(c, authority_tier=std.get("authority_tier") or c.get("effective_tier"),
                            reception_scope=std.get("reception_scope"), witness=bool(c.get("witness") or std.get("witness_only")),
                            speaks_for=std.get("speaks_for"), raised_by_registered_text=raised))
        return out

    def primary_rubric(self, st, cid):
        return (st["verifications"].get(cid) or {}).get(self.primary, {})

    def final_rubric(self, st, cid):
        """The adjudicating model's rubric with the final verdict fields folded in."""
        v = st["verifications"].get(cid) or {}
        fin = v.get("final") or {}
        base = dict(v.get(fin.get("adjudicated_by") or self.primary) or {})
        base.update({k: fin.get(k) for k in ("verdict", "reason_code_final", "adjudicated_by", "route", "overturned", "direction", "primary_verdict")})
        return base

    def final_verdict(self, st, cid):
        v = st["verifications"].get(cid) or {}
        fin = v.get("final")
        if fin:
            return fin.get("verdict")
        return (v.get(self.primary) or {}).get("verdict")

    def all_survivors(self, st):
        """Survivors of every pass that ran, pass order. In an ordinary run pass 2 runs only when pass 1 left nothing and
        pass 3 only when passes 1–2 left nothing, so this equals `s1 or s2 or s3`. It differs only after a supplementary
        single-standard pass (session 5) fills pass 1 on a cell whose earlier exhaustion had already found survivors: those
        verified candidates stay in the running for the card instead of being discarded because pass 1 is no longer empty."""
        out, seen = [], set()
        for pk in ("1", "2", EXHAUST_PASS):
            for c in self.survivors(st, pk):
                if c["candidate_id"] not in seen:
                    out.append(c); seen.add(c["candidate_id"])
        return out

    def survivors(self, st, pass_key):
        """Candidates whose FINAL verdict (adjudicator where it ran, else primary) is ACCEPT / ACCEPT_WITH_CAVEAT."""
        out = []
        for cand in (st["passes"].get(pass_key) or {}).get("candidates", []):
            if self.final_verdict(st, cand["candidate_id"]) in ACCEPTS:
                out.append(cand)
        return out

    # ---------------------------------------------------------------- per-cell statistics for the report
    def caveat_slice_stats(self, st):
        """Caveated accepts that carried a second rubric in this cell: the retired session-3 adjudication route
        (CAVEATED_ACCEPT, stored branches) and the session-4 disclosure sample (CAVEATED_ACCEPT_SAMPLE), with the
        second model's outcome and whether the lower-floor rule changed anything."""
        out = []
        for cid, v in (st.get("verifications") or {}).items():
            if v.get("_route") not in (ROUTE_CAVEATED_ACCEPT, ROUTE_CAVEAT_SAMPLE):
                continue
            fin = v.get("final") or {}
            a = v.get(self.adjudicator) or {}
            out.append({"candidate_id": cid, "route": v.get("_route"), "call_id": a.get("call_id"),
                        "primary_verdict": (v.get(self.primary) or {}).get("verdict"),
                        "primary_floor": (v.get(self.primary) or {}).get("floor"), "primary_hazards": (v.get(self.primary) or {}).get("hazard_flags"),
                        "second_model": self.adjudicator, "second_verdict": a.get("verdict"), "second_floor": a.get("floor"),
                        "second_hazards": a.get("hazard_flags"), "adjudicator_verdict": a.get("verdict"),
                        "floor_final": fin.get("floor_final"), "lower_floor_applied": fin.get("lower_floor_applied"),
                        "final_verdict": fin.get("verdict"), "overturned": fin.get("overturned"), "direction": fin.get("direction"),
                        "reason_code_final": fin.get("reason_code_final"), "disclosure_only": v.get("_route") == ROUTE_CAVEAT_SAMPLE})
        return out

    def caveat_sample_stats(self, st):
        """2c: the sample decisions recorded in this cell (eligible caveated accepts on the card, sampled or not)."""
        return [dict(rec, candidate_id=cid) for cid, rec in (st.get("caveat_sample") or {}).items()]
