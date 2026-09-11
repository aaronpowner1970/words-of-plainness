"""Locator → verifier → coder for one cell, with the guards applied in code and the fallback-tier
two-pass rule (APP CONFIG registry_fallback_only_rows):

  pass one   non-fallback rows of the branch only
  pass two   run ONLY if pass one produced no surviving (verified) candidate; then, and only then,
             the fallback row is admitted. A fallback citation never renders alongside a non-fallback
             witness for the same cell.

Every function is resumable: with the batch backend a call that is not yet answered returns None and
the cell state records where it stopped; re-running continues from the audit log."""
import json
import os

from .config import MAX_CANDIDATES, EMPTY_RESULT
from . import guards, prompts, retrieval


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
                 log=print, run_coder=True, secondary_cells=None):
        # secondary_cells: when set, verifier models after the primary run only on these queue ids
        # (calibration cost control; the report scopes each model's recall to the cells it verified)
        self.secondary_cells = secondary_cells
        self.llm = llm
        self.reg = registry
        self.predicates = predicates
        self.comparators = comparators
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.locator_model = locator_model
        self.verifier_models = verifier_models
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

    # ---------------------------------------------------------------- locator
    def locate(self, cell, pass_no, st):
        pred = self.predicates[cell["family_id"]]
        comp = self.comparators.get(cell["family_id"], {})
        include_fallback = pass_no == 2
        standards = self.reg.for_branch(cell["branch"], include_fallback=True)
        if pass_no == 1:
            standards = [r for r in standards if not self.reg.is_fallback(r["registry_id"])]
        else:
            standards = [r for r in standards if self.reg.is_fallback(r["registry_id"])]  # pass two: the fallback row only
        chunks, coverage = retrieval.select_chunks(pred, standards)
        if not chunks:
            return {"status": "NO_CORPUS", "candidates": [], "coverage": coverage, "standards": [r["registry_id"] for r in standards]}
        views, by_key = _chunk_views(chunks)
        standards_view = [self.reg.public(r["registry_id"]) for r in standards if r["registry_id"] in coverage]
        for sv in standards_view:
            sv["coverage"] = coverage[sv["registry_id"]]
        user = prompts.locator_user(cell, pred, comp, views, standards_view, f"pass {pass_no}")
        guards.assert_no_urls({"u": user})
        out, rec = self.llm.complete("locator", prompts.LOCATOR_SYSTEM, user, model=self.locator_model, max_tokens=1500,
                                     meta={"queue_id": cell["queue_id"], "branch": cell["branch"], "family_id": cell["family_id"], "pass": pass_no})
        if out is None:
            return {"status": "PENDING", "call_id": rec["call_id"]}
        parsed = prompts.parse_json(out)
        result = {"status": "DONE", "call_id": rec["call_id"], "coverage": coverage, "supplied_chunks": [(c["registry_id"], c["locator"]) for c in chunks],
                  "standards": [r["registry_id"] for r in standards], "raw": out[:4000], "candidates": [], "dropped": []}
        if not parsed:
            result["status"] = "UNPARSEABLE"
            return result
        if parsed.get("result", "").startswith("NOT LOCATED") or not parsed.get("candidates"):
            result["empty"] = True
            result["standards_reviewed"] = parsed.get("standards_reviewed", [r["registry_id"] for r in standards])
            return result
        seen = set()
        for cand in parsed.get("candidates", [])[:MAX_CANDIDATES * 2]:
            ok, why, chunk = guards.vet_candidate(cand, by_key, cell["branch"], self.reg, allow_fallback=include_fallback)
            if not ok:
                result["dropped"].append({"candidate": cand, "reason": why})
                continue
            k = guards.dedupe_key({"registry_id": chunk["registry_id"], "locator": chunk["locator"], "phrase": cand["phrase"]})
            if k in seen:
                result["dropped"].append({"candidate": cand, "reason": "duplicate locator+phrase"})
                continue
            seen.add(k)
            result["candidates"].append({
                "candidate_id": f"{cell['queue_id']}-p{pass_no}-{len(result['candidates']) + 1}",
                "pass": pass_no, "registry_id": chunk["registry_id"], "locator": chunk["locator"],
                "phrase": cand["phrase"], "rationale": cand.get("rationale", ""), "floor_claim": cand.get("floor_claim"),
                "chunk_text": chunk["text"], "chunk_hash": chunk["text_hash"], "division": chunk["division"],
                "fallback_tier": self.reg.is_fallback(chunk["registry_id"]),
            })
            if len(result["candidates"]) >= MAX_CANDIDATES:
                break
        return result

    # ---------------------------------------------------------------- verifier
    def verify(self, cell, cand, model):
        pred = self.predicates[cell["family_id"]]
        chunk_view = {"registry_id": cand["registry_id"], "locator": cand["locator"], "text": cand["chunk_text"]}
        user = prompts.verifier_user(pred, cand, chunk_view)
        guards.assert_no_urls({"u": user})
        out, rec = self.llm.complete("verifier", prompts.VERIFIER_SYSTEM, user, model=model, max_tokens=900,
                                     meta={"queue_id": cell["queue_id"], "candidate_id": cand["candidate_id"], "verifier_model": model})
        if out is None:
            return {"status": "PENDING", "call_id": rec["call_id"], "model": model}
        parsed = prompts.parse_json(out) or {}
        rubric = {
            "model": model, "call_id": rec["call_id"],
            "phrase_verbatim": parsed.get("phrase_verbatim"), "subject_is_required": parsed.get("subject_is_required"),
            "grammatical_subject": parsed.get("grammatical_subject"), "speech_act_is_assertion": parsed.get("speech_act_is_assertion"),
            "speech_act_note": parsed.get("speech_act_note"), "floor": parsed.get("floor"), "floor_reason": parsed.get("floor_reason"),
            "hazard_flags": [h for h in (parsed.get("hazard_flags") or []) if h in prompts.HAZARD_TYPES],
            "verdict_model": parsed.get("verdict"), "reason_code": parsed.get("reason_code"), "reason": parsed.get("reason"),
            "status": "DONE" if parsed else "UNPARSEABLE", "raw": out[:2000],
        }
        # the verdict is recomputed in code from the rubric lines: any N on 1–3 is REJECT; WORD_ONLY is REJECT
        # (no lexical-floor family in v2.23); the code-side phrase assertion overrides item 1.
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

    # ---------------------------------------------------------------- coder
    def code(self, cell, cand, rubric):
        pred = self.predicates[cell["family_id"]]
        comp = self.comparators.get(cell["family_id"], {})
        std = self.reg.public(cand["registry_id"])
        user = prompts.coder_user(cell, pred, comp, cand, {k: rubric.get(k) for k in ("floor", "floor_reason", "hazard_flags", "verdict", "grammatical_subject")}, std)
        guards.assert_no_urls({"u": user})
        out, rec = self.llm.complete("coder", prompts.CODER_SYSTEM, user, model=self.coder_model, max_tokens=700,
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
    def run_cell(self, cell, verify_all_models=True):
        """Advance one cell as far as the backend allows. Returns the state dict."""
        st = self.load(cell["queue_id"]) or {"queue_id": cell["queue_id"], "branch": cell["branch"], "family_id": cell["family_id"],
                                              "predicate": cell["predicate"], "passes": {}, "verifications": {}, "coding": {}, "phase": "locate-1"}
        # pass 1
        if "1" not in st["passes"] or st["passes"]["1"].get("status") == "PENDING":
            r = self.locate(cell, 1, st)
            st["passes"]["1"] = r
            self.save(st)
            if r["status"] == "PENDING":
                return st
        # verify pass-1 candidates
        pending = self._verify_pass(cell, st, "1")
        if pending:
            self.save(st); return st
        survivors1 = self.survivors(st, "1")
        # pass 2 only if pass 1 left nothing surviving and the branch has a fallback row
        has_fallback = any(self.reg.is_fallback(r["registry_id"]) for r in self.reg.for_branch(cell["branch"]))
        if not survivors1 and has_fallback:
            if "2" not in st["passes"] or st["passes"]["2"].get("status") == "PENDING":
                r = self.locate(cell, 2, st)
                st["passes"]["2"] = r
                self.save(st)
                if r["status"] == "PENDING":
                    return st
            pending = self._verify_pass(cell, st, "2")
            if pending:
                self.save(st); return st
        st["survivors"] = self.survivors(st, "1") or self.survivors(st, "2")
        st["fallback_used"] = bool(not self.survivors(st, "1") and self.survivors(st, "2"))
        # coder for survivors
        if self.run_coder:
            for cand in st["survivors"]:
                cid = cand["candidate_id"]
                if cid not in st["coding"] or st["coding"][cid].get("status") == "PENDING":
                    rub = self.primary_rubric(st, cid)
                    st["coding"][cid] = self.code(cell, cand, rub)
            if any(v.get("status") == "PENDING" for v in st["coding"].values()):
                st["phase"] = "coding"; self.save(st); return st
        st["phase"] = "DONE"
        st["empty"] = not st["survivors"]
        self.save(st)
        return st

    def _verify_pass(self, cell, st, pass_key):
        p = st["passes"].get(pass_key) or {}
        pending = False
        for cand in p.get("candidates", []):
            cid = cand["candidate_id"]
            v = st["verifications"].setdefault(cid, {})
            for i, m in enumerate(self.verifier_models):
                if i > 0 and self.secondary_cells is not None and cell["queue_id"] not in self.secondary_cells:
                    v.setdefault(m, {"status": "SKIPPED_SAMPLE", "model": m})
                    continue
                if m not in v or v[m].get("status") in ("PENDING", "SKIPPED_SAMPLE"):
                    v[m] = self.verify(cell, cand, m)
                if v[m].get("status") == "PENDING":
                    pending = True
        return pending

    def primary_rubric(self, st, cid):
        v = st["verifications"].get(cid, {})
        return v.get(self.verifier_models[0], {})

    def survivors(self, st, pass_key):
        """Candidates whose PRIMARY verifier verdict is ACCEPT / ACCEPT_WITH_CAVEAT."""
        out = []
        for cand in (st["passes"].get(pass_key) or {}).get("candidates", []):
            rub = self.primary_rubric(st, cand["candidate_id"])
            if rub.get("verdict") in ("ACCEPT", "ACCEPT_WITH_CAVEAT"):
                out.append(cand)
        return out
