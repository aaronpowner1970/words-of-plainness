"""Locator → verifier → coder for one cell, with the guards applied in code, the fallback-tier
two-pass rule (APP CONFIG registry_fallback_only_rows), per-standard retrieval (cal-3, Fix 1) and
the verifier routing SONNET_WITH_OPUS_SLICE (APP CONFIG verifier_routing, Fix 6).

  pass one   non-fallback rows of the branch only
  pass two   run ONLY if pass one produced no surviving (verified) candidate; then, and only then,
             the fallback row is admitted. A fallback citation never renders alongside a non-fallback
             witness for the same cell.

Per-standard locate. The locator is called ONCE PER STANDARD with that standard's own chunks (whole
when they fit the budget, otherwise the hybrid ranking within that standard). Every standard that
yields a candidate gets a GUARANTEED verification slot for its best candidate; the remaining
candidates compete for VERIFY_EXTRA_CANDIDATES further slots, ranked by authority tier and floor
claim. A phrase the locator cut too long (>15 words) is not repaired by code — the locator is asked to
re-cut it verbatim (up to three attempts, shortening each time; on the last it chooses among the legal
≤15-word spans enumerated in code), and the re-cut goes through the same guards.

Routing. The primary verifier judges every slotted candidate. The adjudicator (opus) judges only the
slice: candidates on the caveated rows, on fallback-only rows, on the guarded Synodikon row, and
every candidate of a cell where the primary rejected all candidates. Where the adjudicator ran, its
verdict is FINAL; the primary's verdict is kept beside it so overturns are visible in the report.

Every function is resumable: with the batch backend a call that is not yet answered returns None and
the cell state records where it stopped; re-running continues from the audit log."""
import json
import os

import re

from .config import MAX_CANDIDATES, EMPTY_RESULT, VERIFY_EXTRA_CANDIDATES, PHRASE_MAX_WORDS
from .registry import tier_rank
from .textutil import scrub_urls, phrase_word_count
from . import guards, prompts, retrieval


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
                 log=print, run_coder=True):
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

    def _call(self, role, system, user, model, max_tokens, meta):
        """One call, parsed. A reply that came back unparseable (the JSON cut off at the token ceiling,
        as happens when the ceiling is spent before the text block) is re-sent ONCE with a larger
        ceiling under a distinct call identity (attempt=1). Returns (out, rec, parsed, attempt);
        out is None while a call is pending."""
        out, rec = self.llm.complete(role, system, user, model=model, max_tokens=max_tokens, meta=meta)
        if out is None:
            return None, rec, None, 0
        parsed = prompts.parse_json(out)
        if parsed is not None:
            return out, rec, parsed, 0
        out2, rec2 = self.llm.complete(role, system, user, model=model, max_tokens=max(self.RETRY_CEILING, max_tokens * 2),
                                       meta=meta, attempt=1)
        if out2 is None:
            return None, rec2, None, 1
        return out2, rec2, prompts.parse_json(out2), 1

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

    def locate_standard(self, cell, pred, comp, row, pass_no):
        """Locator call for ONE standard. Returns the per-standard entry (status PENDING when a call
        is unanswered — the caller re-runs; answered calls are served from the audit log)."""
        rid = row["registry_id"]
        include_fallback = pass_no == 2
        chunks, coverage = retrieval.select_for_standard(pred, row)
        if not chunks:
            return {"status": "NO_CORPUS", "candidates": [], "dropped": []}
        views, by_key = _chunk_views(chunks)
        sv = self.reg.public(rid)
        sv["coverage"] = coverage
        user = prompts.locator_user(cell, pred, comp, views, [sv], f"pass {pass_no}")
        guards.assert_no_urls({"u": user})
        out, rec, parsed, attempt = self._call("locator", prompts.LOCATOR_SYSTEM, user, self.locator_model, 3000,
                                               {"queue_id": cell["queue_id"], "branch": cell["branch"], "family_id": cell["family_id"],
                                                "pass": pass_no, "registry_id": rid})
        entry = {"status": "PENDING", "call_id": rec["call_id"], "attempt": attempt, "coverage": coverage,
                 "supplied_chunks": [(rid, c["locator"]) for c in chunks], "supplied_chars": sum(len(c["text"]) for c in chunks),
                 "candidates": [], "dropped": [], "recuts": []}
        if out is None:
            return entry
        entry["raw"] = out[:4000]
        if not parsed:
            entry["status"] = "UNPARSEABLE"           # retried on the next run
            return entry
        if parsed.get("result", "").startswith("NOT LOCATED") or not parsed.get("candidates"):
            entry["status"] = "EMPTY"
            entry["empty"] = True
            return entry
        seen = set()
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
                "candidate_id": f"{cell['queue_id']}-p{pass_no}-{rid}-{n}",
                "pass": pass_no, "registry_id": rid, "locator": chunk["locator"],
                "phrase": cand["phrase"], "rationale": cand.get("rationale", ""), "floor_claim": cand.get("floor_claim"),
                "chunk_text": scrub_urls(chunk["text"]), "chunk_hash": chunk["text_hash"], "division": chunk["division"],
                "fallback_tier": self.reg.is_fallback(rid), "witness": self.reg.is_witness(rid),
                "effective_tier": self.reg.effective_tier(rid, chunk), "locator_rank": n,
                "recut_from": cand.get("recut_from"),
            })
            if len(entry["candidates"]) >= MAX_CANDIDATES:
                break
        entry["status"] = "DONE"
        entry["empty"] = not entry["candidates"]
        return entry

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
        slotted, extra = [], []
        for row in standards:
            e = per[row["registry_id"]]
            cands = e.get("candidates") or []
            result["dropped"].extend([dict(d, registry_id=row["registry_id"]) for d in e.get("dropped", [])])
            result["coverage"][row["registry_id"]] = e.get("coverage")
            result["supplied_chunks"].extend(e.get("supplied_chunks", []))
            if cands:
                first = dict(cands[0]); first["slot"] = "GUARANTEED"
                slotted.append(first)
                extra.extend(dict(c, slot="EXTRA") for c in cands[1:])
        extra.sort(key=lambda c: (tier_rank(c.get("effective_tier")), FLOOR_ORDER.get(c.get("floor_claim"), 9), c.get("locator_rank", 9)))
        slotted.extend(extra[:VERIFY_EXTRA_CANDIDATES])
        result["unslotted"] = [dict(c, slot="UNSLOTTED") for c in extra[VERIFY_EXTRA_CANDIDATES:]]
        result["candidates"] = slotted
        result["empty"] = not slotted
        result["standards_reviewed"] = [r["registry_id"] for r in standards if per[r["registry_id"]].get("status") != "NO_CORPUS"]
        return result

    # ---------------------------------------------------------------- verifier
    def verify(self, cell, cand, model):
        pred = self.predicates[cell["family_id"]]
        chunk_view = {"registry_id": cand["registry_id"], "locator": cand["locator"], "text": cand["chunk_text"]}
        user = prompts.verifier_user(pred, cand, chunk_view)
        guards.assert_no_urls({"u": user})
        out, rec, parsed, attempt = self._call("verifier", prompts.VERIFIER_SYSTEM, user, model, 2500,
                                               {"queue_id": cell["queue_id"], "candidate_id": cand["candidate_id"], "verifier_model": model})
        if out is None:
            return {"status": "PENDING", "call_id": rec["call_id"], "model": model}
        parsed = parsed or {}
        rubric = {
            "model": model, "call_id": rec["call_id"], "attempt": attempt,
            "phrase_verbatim": parsed.get("phrase_verbatim"), "subject_is_required": parsed.get("subject_is_required"),
            "grammatical_subject": parsed.get("grammatical_subject"), "speech_act_is_assertion": parsed.get("speech_act_is_assertion"),
            "speech_act_note": parsed.get("speech_act_note"), "floor": parsed.get("floor"), "floor_reason": parsed.get("floor_reason"),
            "hazard_flags": [h for h in (parsed.get("hazard_flags") or []) if h in prompts.HAZARD_TYPES],
            "verdict_model": parsed.get("verdict"), "reason_code": parsed.get("reason_code"), "reason": parsed.get("reason"),
            "status": "DONE" if parsed else "UNPARSEABLE", "raw": out[:2000],
        }
        # the verdict is recomputed in code from the rubric lines: any N on 1–3 is REJECT; WORD_ONLY is REJECT
        # (no lexical-floor family); the code-side phrase assertion overrides item 1.
        ok_phrase, _ = guards.check_phrase(cand["phrase"], cand["chunk_text"])
        if not parsed:
            verdict = "REJECT"; code = "UNPARSEABLE"
        elif not ok_phrase or str(rubric["phrase_verbatim"]).upper() != "Y":
            verdict, code = "REJECT", "NOT_VERBATIM"
        elif str(rubric["subject_is_required"]).upper() != "Y":
            verdict, code = "REJECT", "WRONG_SUBJECT"
        elif str(rubric["speech_act_is_assertion"]).upper() != "Y":
            verdict, code = "REJECT", "NOT_ASSERTION"
        elif rubric["floor"] == "WORD_ONLY" and not pred.get("lexical_floor"):
            verdict, code = "REJECT", "BELOW_FLOOR"
        elif rubric["verdict_model"] == "REJECT":
            verdict, code = "REJECT", rubric["reason_code"] or "OTHER"
        elif rubric["floor"] == "PARTIAL" or rubric["hazard_flags"] or rubric["verdict_model"] == "ACCEPT_WITH_CAVEAT":
            verdict, code = "ACCEPT_WITH_CAVEAT", rubric["reason_code"] or "OK"
        else:
            verdict, code = "ACCEPT", "OK"
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
        """Final verdict = the adjudicator's where it ran, else the primary's. Overturns recorded."""
        p = v.get(primary) or {}
        a = v.get(adjudicator) if adjudicator else None
        if a and a.get("status") == "DONE":
            fin = {"verdict": a["verdict"], "reason_code_final": a.get("reason_code_final"), "adjudicated_by": adjudicator,
                   "route": v.get("_route"), "primary_verdict": p.get("verdict")}
            pa, aa = p.get("verdict") in ACCEPTS, a["verdict"] in ACCEPTS
            fin["overturned"] = pa != aa
            fin["direction"] = ("RESCUED" if (aa and not pa) else "OVERRULED" if (pa and not aa) else None)
        else:
            fin = {"verdict": p.get("verdict"), "reason_code_final": p.get("reason_code_final"), "adjudicated_by": primary,
                   "route": v.get("_route"), "primary_verdict": p.get("verdict"), "overturned": False, "direction": None}
        v["final"] = fin
        return fin

    def _verify_pass(self, cell, st, pass_key):
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
            v["_route"] = route
            if route and (self.adjudicator not in v or v[self.adjudicator].get("status") in ("PENDING", "UNPARSEABLE")):
                v[self.adjudicator] = self.verify(cell, cand, self.adjudicator)
            if route and v[self.adjudicator].get("status") == "PENDING":
                pending = True
        if pending:
            return True
        for cand in cands:
            self.finalize(st["verifications"][cand["candidate_id"]], self.primary, self.adjudicator)
        return False

    # ---------------------------------------------------------------- coder
    def code(self, cell, cand, rubric):
        pred = self.predicates[cell["family_id"]]
        comp = self.comparators.get(cell["family_id"], {})
        std = self.reg.public(cand["registry_id"])
        user = prompts.coder_user(cell, pred, comp, cand, {k: rubric.get(k) for k in ("floor", "floor_reason", "hazard_flags", "verdict", "grammatical_subject")}, std)
        guards.assert_no_urls({"u": user})
        out, rec = self.llm.complete("coder", prompts.CODER_SYSTEM, user, model=self.coder_model, max_tokens=1200,
                                     meta={"queue_id": cell["queue_id"], "candidate_id": cand["candidate_id"]})
        if out is None:
            return {"status": "PENDING", "call_id": rec["call_id"]}
        parsed = prompts.parse_json(out) or {}
        note = parsed.get("source_note", "")
        ok, why = guards.vet_source_note(note)
        return {"status": "DONE", "call_id": rec["call_id"], "rendered_state": parsed.get("rendered_state"),
                "diverges_from_family_code": parsed.get("diverges_from_family_code"), "state_reason": parsed.get("state_reason"),
                "source_note": note if ok else " ".join(note.split()[:40]), "source_note_guard": why,
                "scope_caveat": std["scope_caveat"], "raw": out[:1500]}

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
        st["survivors"] = self.survivors(st, "1") or self.survivors(st, "2")
        st["fallback_used"] = bool(not self.survivors(st, "1") and self.survivors(st, "2"))
        # coder for survivors
        if self.run_coder:
            for cand in st["survivors"]:
                cid = cand["candidate_id"]
                if cid not in st["coding"] or st["coding"][cid].get("status") == "PENDING":
                    st["coding"][cid] = self.code(cell, cand, self.final_rubric(st, cid))
            if any(v.get("status") == "PENDING" for v in st["coding"].values()):
                st["phase"] = "coding"; self.save(st); return st
        st["phase"] = "DONE"
        st["empty"] = not st["survivors"]
        self.save(st)
        return st

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

    def survivors(self, st, pass_key):
        """Candidates whose FINAL verdict (adjudicator where it ran, else primary) is ACCEPT / ACCEPT_WITH_CAVEAT."""
        out = []
        for cand in (st["passes"].get(pass_key) or {}).get("candidates", []):
            if self.final_verdict(st, cand["candidate_id"]) in ACCEPTS:
                out.append(cand)
        return out
