"""Build the emitted JSON objects from the Context + assertion results."""
import re
from collections import Counter, OrderedDict

from .model import BRANCHES, ratification_decision
from .workbook import s, b
from .textnorm import style_flags

H_KEY = "Historical quoted phrase (≤15 words)"
R_KEY = "Restoration quoted phrase (primary, ≤15 words)"


def stat(count, denominator, low=None, high=None, basis="", label=""):
    """One uncertainty-carrying statistic: count + percentage + sensitivity range + provisional flag.
    Rendered only through the sjn-stat component; never a tradition-level percentage."""
    pct = round(100.0 * count / denominator, 1) if denominator else None
    low = count if low is None else low
    high = count if high is None else high
    return {
        "label": label, "count": count, "denominator": denominator, "percent": pct,
        "range": {"low": low, "high": high,
                  "low_percent": round(100.0 * low / denominator, 1) if denominator else None,
                  "high_percent": round(100.0 * high / denominator, 1) if denominator else None,
                  "basis": basis},
        "provisional": True, "external_validation": "PENDING",
        "display_rule": "count + percentage + range through one sjn-stat component; never rendered as a bare percentage",
    }


def _num(v):
    return int(v) if isinstance(v, float) and v.is_integer() else v


def _ratified_map(decisions):
    return {d["id"].replace("AUTH-RAT-", ""): ratification_decision(d) for d in decisions if d["id"].startswith("AUTH-RAT-")}


# ------------------------------------------------------------------ predicates
def build_predicates(ctx, targets, decisions):
    rat = _ratified_map(decisions)
    inh = {s(r["Predicate ID"]): r for r in ctx.inherited57}
    res = {s(r["Addition ID"]): r for r in ctx.restoration26}
    cit = {s(r["Predicate ID"]): r for r in ctx.citations}
    vec = {s(r["Family ID"]): r for r in ctx.vectors}
    ht = {(t.kind, t.key, t.role): t for t in targets}
    out = []
    style = []
    for r in ctx.all83:
        pid = s(r["ID"])
        corpus = "inherited" if pid.startswith("RNR-H") else "restoration"
        rec = OrderedDict()
        rec["id"] = pid
        rec["corpus"] = corpus
        rec["family"] = s(r.get("Teaching family"))
        rec["predicate"] = s(r.get("Predicate family"))
        rec["mode"] = s(r.get("Family / mode"))
        code = s(r.get("Comparison / authority"))
        rec["code"] = code if corpus == "inherited" else None
        rec["authority_tier"] = code if corpus == "restoration" else None
        rec["lens"] = s(r.get("Teaching lens"))
        rec["summary"] = s(r.get("Plain-language teaching summary"))
        rec["caution"] = s(r.get("Key caution / nuance"))
        rec["source_pointer"] = s(r.get("Source pointer"))
        rec["ratification"] = rat.get(pid, {"decision": "PENDING"})
        for f in ("summary", "caution"):
            for flag in style_flags(rec[f]):
                style.append({"file": "predicates.json", "id": pid, "field": f, "flag": flag})
        v = vec.get(pid)
        rec["card_mode"] = "VECTOR" if v else "STANDARD"
        rec["vector"] = None if not v else {
            "caption": s(v.get("Learner-facing caption")),
            "atomic_layer_summary": s(v.get("Atomic-layer summary")),
            "citation_display_rule": s(v.get("Citation display rule")),
            "master_family_code": s(v.get("Master family code")),
        }
        if corpus == "inherited":
            i = inh[pid]
            rec["inherited"] = {
                "source_definition": s(i.get("Historical source-report definition")),
                "semantic_floor_note": s(i.get("Accepted comparison / semantic-floor note")),
                "coding_provenance": s(i.get("Coding provenance")),
                "confidence": s(i.get("Confidence")),
                "source_record": s(i.get("Historical source record")),
                "source_locator": s(i.get("Source locator")),
            }
            c = cit[pid]
            h_t = ht.get(("HISTORICAL", pid, ""))
            rp_t = ht.get(("RESTORATION", pid, "PRIMARY"))
            rs_t = ht.get(("RESTORATION", pid, "SUPPLEMENTAL"))
            rec["citation"] = {
                "readiness": s(c.get("Public citation readiness")),
                "selection_basis": s(c.get("Citation selection basis")),
                "qa_status": s(c.get("Citation QA status")),
                "scope_note": s(c.get("Accepted scope note")),
                "historical": {
                    "status": s(c.get("Historical citation status")),
                    "branch": s(c.get("Historical teaching branch")),
                    "institution": s(c.get("Historical institution / scope")),
                    "document": s(c.get("Historical document")),
                    "locator": s(c.get("Historical locator")),
                    "authority_url": s(c.get("Historical authority URL")) or None,
                    "text_url": s(c.get("Historical text URL")) or None,
                    "phrase": s(c.get(H_KEY)) or None,
                    "witness_retired": b(c.get("Historical witness retired?")),
                    "validation": _val(h_t),
                },
                "restoration": {
                    "label": s(c.get("Restoration comparator label")),
                    "source": s(c.get("Restoration source")),
                    "locator": s(c.get("Restoration locator")),
                    "primary_url": s(c.get("Restoration primary URL")),
                    "supplemental_url": s(c.get("Restoration supplemental URL")) or None,
                    "phrase": s(c.get(R_KEY)),
                    "supplemental_phrase": s(c.get("Restoration supplemental quoted phrase")) or None,
                    "fetch_mode": s(c.get("Restoration fetch mode")),
                    "phrase_qa": s(c.get("Restoration phrase QA")),
                    "author_review_flag": s(c.get("Comparator author-review flag")) or None,
                    "validation": _val(rp_t),
                    "supplemental_validation": _val(rs_t),
                },
            }
            rec["restoration"] = None
        else:
            a = res[pid]
            rec["inherited"] = None
            rec["citation"] = None
            rec["restoration"] = {
                "domain": s(a.get("Domain / family")),
                "normalized_family": s(a.get("Normalized Restoration-addition family")),
                "authority_role": s(a.get("Authority role")),
                "source_url": s(a.get("Official / primary source URL")),
                "locator": s(a.get("Locator")),
                "evidence_note": s(a.get("Evidence note")),
                "confidence": s(a.get("Confidence")),
                "novelty_caution": s(a.get("Historical-novelty caution")),
            }
        rec["sentence"] = _four_clause(rec)
        out.append(rec)
    return out, style


def _val(t):
    if t is None:
        return None
    return {"result": t.result, "scope_mode": t.scope_mode, "scope_note": t.scope_note,
            "scoped_chars": t.scoped_chars, "http_status": t.fetch_status, "detail": t.detail,
            "phrase_word_count": t.word_count}


def _four_clause(rec):
    """Four-clause sentence: predicate+lens | historical witness | Restoration witness | ratified scope.
    (Structure inferred in the Gate-2 session; Gate-0 brief unavailable to Code — see handoff.)"""
    if rec["corpus"] == "inherited":
        c = rec["citation"]; h = c["historical"]; r = c["restoration"]
        c1 = f"{rec['predicate']} — {rec['lens']} ({rec['code']})."
        c2 = (f"{h['institution']}, {h['document']} ({h['locator']}): “{h['phrase']}”." if h["phrase"]
              else f"{h['institution']}: historical source packet required; no public text witness.")
        c3 = f"{r['label']}: “{r['phrase']}”."
        c4 = rec["caution"]
    else:
        a = rec["restoration"]
        c1 = f"{rec['predicate']} — {rec['lens']} ({rec['authority_tier']})."
        c2 = "Absent as a substantive positive doctrine from the admitted historical creed/confession corpus."
        c3 = f"{a['locator']} ({a['authority_role']})."
        c4 = rec["caution"]
    return {"clauses": [c1, c2, c3, c4], "text": " ".join(x for x in (c1, c2, c3, c4) if x)}


# ------------------------------------------------------------------ cells
def build_cells(ctx, targets):
    anchors = {}
    for r in ctx.tradition_sources:
        anchors[s(r["Tradition family"])] = s(r.get("Institution / scope anchor"))
    for r in ctx.current_source:
        anchors[s(r["Branch teaching label"])] = s(r.get("Current institution"))
    ct = {t.key: t for t in targets if t.kind == "CASE-STUDY"}
    supp = [t for t in targets if t.kind == "QUEUE-CELL"]
    cells = []
    lineage_ids = []
    vocab = {s(v["Rendered State"]): v for v in ctx.state_vocab}
    for r in ctx.queue:
        qid = s(r["Queue ID"])
        state = s(r.get("Rendered State (app-safe)"))
        disp = s(r.get("Public cell disposition"))
        certified = disp.startswith("PUBLIC-CERTIFIED")
        lineage = b(r.get("Historical Witness Retired")) or s(r.get("Evidence Display Role")) == "LINEAGE ONLY"
        branch = s(r.get("Teaching branch"))
        inst = s(r.get("Institution / jurisdiction"))
        v = vocab.get(state, {})
        rec = OrderedDict()
        rec["id"] = qid
        rec["family_id"] = s(r.get("Family ID"))
        rec["predicate"] = s(r.get("Predicate"))
        rec["family_code"] = s(r.get("Current family code"))
        rec["branch"] = branch
        rec["rendered_state"] = state
        rec["metric_class"] = s(r.get("Metric Class (future branch analytics)"))
        rec["state_meaning"] = s(v.get("Public meaning"))
        rec["rendering_rule"] = s(v.get("App rendering rule"))
        rec["counts_as_result"] = s(v.get("Counts as theological result?")) == "YES"
        rec["institution_tag"] = (inst if (certified and inst) else anchors.get(branch, branch))
        rec["institution_tag_basis"] = "recovered source institution" if (certified and inst) else "branch institutional anchor (no certified source for this cell)"
        rec["display_role"] = s(r.get("Evidence Display Role"))
        rec["disposition"] = disp
        rec["collapse_rule"] = s(r.get("Collapse rule"))
        rec["certified"] = certified
        rec["lineage_only"] = lineage
        if certified:
            rec["evidence"] = {
                "institution": inst,
                "document": s(r.get("Document")),
                "locator": s(r.get("Proposition locator")),
                "authority_url": s(r.get("Authority / adoption URL")) or None,
                "text_url": s(r.get("Text URL")) or None,
                "atomic_units": s(r.get("Atomic unit(s) recovered")) or None,
                "confidence": s(r.get("Evidence confidence")),
                "scope_control": s(r.get("Scope control")),
                "reconciliation": s(r.get("Current-family reconciliation")),
                "recovery_state": s(r.get("Recovery state")),
                "reviewer_status": s(r.get("Reviewer status")),
                "source_note": s(r.get("Source note")),
            }
        else:
            rec["evidence"] = None
        if lineage:
            lineage_ids.append(qid)
            rec["lineage"] = {
                "document": s(r.get("Document")),
                "institution_label": inst,
                "note": "Historical witness retired; lineage only, never current branch evidence.",
                "reviewer_note": s(r.get("Reviewer notes")),
            }
        else:
            rec["lineage"] = None
        t = ct.get(qid)
        rec["case_study_target"] = None if not t else {"status": t.status, "phrase": t.phrase or None,
                                                       "text_url": t.url, "locator": t.locator, "validation": _val(t) if t.status == "ASSERT" else None}
        st = [x for x in supp if x.key == qid]
        rec["phrase_targets"] = [{"role": x.role, "phrase": x.phrase, "url": x.url, "locator": x.locator,
                                  "provenance": x.note, "validation": _val(x)} for x in st] or None
        cells.append(rec)
    # branch summary (partition check only; counts, never percentages)
    branches = []
    for br in BRANCHES:
        rows = [c for c in cells if c["branch"] == br]
        cnt = Counter(c["rendered_state"] for c in rows)
        branches.append({
            "branch": br, "institution_anchor": anchors.get(br, ""),
            "state_counts": dict(cnt), "total_states": sum(cnt.values()),
            "released_results": sum(1 for c in rows if c["metric_class"] != "EXCLUDED"),
            "not_located": sum(v for k, v in cnt.items() if k.startswith("NOT LOCATED")),
            "partition_check": "MATCH" if sum(cnt.values()) == 57 else "REVIEW",
            "percentages_forbidden": True,
        })
    return cells, branches, lineage_ids


# ------------------------------------------------------------------ inferences
_EXPECT = {  # from Inference Evidence Map "Measure contributed" (numerator, denominator)
    "INF-01": (52, 57), "INF-02": (35, 35), "INF-03": (18, 22), "INF-04": (5, 57), "INF-05": (140, 456),
    "INF-06": (28, 57), "INF-07": (294, 456), "INF-08": (8, 8), "INF-09": (8, 8), "INF-10": (5, 8),
    "INF-11": (15, 26), "INF-12": (22, 26), "INF-13": (42, 47),
}
_RANGE_BASIS = {
    "INF-01": ("A only (Q excluded from the floor)", "A + Q"),
    "INF-02": ("A only", "A + Q"),
    "INF-03": ("D only", "Q + D"),
    "INF-04": ("D only", "D + Q treated as divergence"),
    "INF-05": ("released A/Q/D metric cells", "released cells + VECTOR COMPLETE families"),
    "INF-06": ("released-result spread (max − min)", "released-result spread (max − min)"),
    "INF-07": ("explicit NOT LOCATED states", "NOT LOCATED + PENDING/HOLD/VECTOR PENDING"),
    "INF-08": ("certified A cells", "certified A cells"),
    "INF-09": ("certified Q cells", "certified Q cells"),
    "INF-10": ("certified D cells", "certified D cells (3 unresolved cells are NOT projected)"),
    "INF-11": ("kinship/premortality only", "kinship/premortality + exaltation/family/progression"),
    "INF-12": ("Tier I only", "Tier I + Tier II"),
    "INF-13": ("Q only vs D (additions excluded)", "Q + additions vs D"),
}


def build_inferences(ctx, cells):
    wb = ctx.wb
    inh = ctx.inherited57
    res = ctx.restoration26
    codes = Counter(s(r.get("Current A/Q/D/U")) for r in inh)
    kat = [r for r in inh if s(r.get("Original mode")) == "Kataphatic"]
    apo = [r for r in inh if s(r.get("Original mode")) != "Kataphatic"]
    kA = sum(s(r.get("Current A/Q/D/U")) == "A" for r in kat); kQ = sum(s(r.get("Current A/Q/D/U")) == "Q" for r in kat)
    aA = sum(s(r.get("Current A/Q/D/U")) == "A" for r in apo); aQ = sum(s(r.get("Current A/Q/D/U")) == "Q" for r in apo); aD = sum(s(r.get("Current A/Q/D/U")) == "D" for r in apo)
    released = sum(1 for c in cells if c["metric_class"] != "EXCLUDED")
    vec_complete = sum(1 for c in cells if c["rendered_state"] == "VECTOR COMPLETE")
    not_located = sum(1 for c in cells if c["rendered_state"].startswith("NOT LOCATED"))
    unresolved = sum(1 for c in cells if c["rendered_state"] in ("PENDING REVIEW", "VECTOR PENDING", "RECONCILIATION HOLD", "RECONCILIATION HOLD — SOURCE ROLE"))
    per_branch = Counter(c["branch"] for c in cells if c["metric_class"] != "EXCLUDED")
    spread = max(per_branch.values()) - min(per_branch.values())
    tiers = Counter(s(r.get("Current authority tier")) for r in res)
    dom = Counter(s(r.get("Domain / family")) for r in res)
    kin = dom.get("Divine-human kinship / premortality", 0); exa = dom.get("Exaltation / eternal family / progression", 0)
    low_high = {
        "INF-01": (codes["A"], codes["A"] + codes["Q"]),
        "INF-02": (kA, kA + kQ),
        "INF-03": (aD, aQ + aD),
        "INF-04": (codes["D"], codes["D"] + codes["Q"]),
        "INF-05": (released, released + vec_complete),
        "INF-06": (spread, spread),
        "INF-07": (not_located, not_located + unresolved),
        "INF-08": (8, 8), "INF-09": (8, 8), "INF-10": (5, 5),
        "INF-11": (kin, kin + exa),
        "INF-12": (tiers.get("Tier I", 0), tiers.get("Tier I", 0) + tiers.get("Tier II", 0)),
        "INF-13": (codes["Q"], codes["Q"] + len(res)),
    }
    # independent Python recount (never trusts the workbook formulas)
    h05 = Counter(c["rendered_state"] for c in cells if c["family_id"] == "RNR-H05")
    h22 = Counter(c["rendered_state"] for c in cells if c["family_id"] == "RNR-H22")
    h43 = Counter(c["rendered_state"] for c in cells if c["family_id"] == "RNR-H43")
    independent = {
        "INF-01": (codes["A"] + codes["Q"], len(inh)),
        "INF-02": (kA + kQ, len(kat)),
        "INF-03": (aQ + aD, len(apo)),
        "INF-04": (codes["D"], len(inh)),
        "INF-05": (released, len(cells)),
        "INF-06": (spread, 57),
        "INF-07": (not_located, len(cells)),
        "INF-08": (h05.get("A", 0), 8),
        "INF-09": (h22.get("Q", 0), 8),
        "INF-10": (h43.get("D", 0), 8),
        "INF-11": (kin + exa, len(res)),
        "INF-12": (tiers.get("Tier I", 0) + tiers.get("Tier II", 0), len(res)),
        "INF-13": (codes["Q"] + len(res), codes["Q"] + codes["D"] + len(res)),
    }
    out, checks = [], []
    for r in ctx.inference:
        iid = s(r["Inference ID"])
        row = r["__row"]
        num = wb.eval_cell("Inference Support", f"E{row}")
        den = wb.eval_cell("Inference Support", f"F{row}")
        rate = wb.eval_cell("Inference Support", f"G{row}")
        num, den = int(round(num)), int(round(den))
        exp = _EXPECT.get(iid)
        ind = independent.get(iid)
        checks.append({"id": iid, "recomputed": [num, den], "independent_recount": list(ind) if ind else None,
                       "match": ind == (num, den), "evidence_map": list(exp) if exp else None,
                       "narrative_match": (exp == (num, den)) if exp else None,
                       "formula_numerator": s(r.get("Numerator")), "formula_denominator": s(r.get("Denominator"))})
        lo, hi = low_high.get(iid, (num, num))
        basis = _RANGE_BASIS.get(iid, ("", ""))
        st = stat(num, den, lo, hi, f"low = {basis[0]}; high = {basis[1]}", s(r.get("Metric")))
        if iid == "INF-13":
            st["range"]["denominator_note"] = "denominator changes with basis: Q vs D only = 21; Q + additions vs D = 47"
        out.append(OrderedDict([
            ("id", iid), ("theme", s(r.get("Theme"))), ("evidence_layer", s(r.get("Evidence layer"))),
            ("metric", s(r.get("Metric"))), ("stat", st), ("rate_recomputed", round(float(rate), 4)),
            ("direct_observation", s(r.get("Direct observation"))), ("defensible_inference", s(r.get("Defensible inference"))),
            ("alternative_interpretation", s(r.get("Alternative interpretation / challenge"))),
            ("does_not_support", s(r.get("What the data DO NOT support"))), ("drill_down_key", s(r.get("Drill-down key"))),
            ("evidence_status", s(r.get("Evidence status"))), ("teaching_priority", s(r.get("Teaching priority"))),
            ("reasoning_move", s(r.get("Reasoning move"))), ("confidence", s(r.get("Confidence"))),
            ("interactive_prompt", s(r.get("Interactive prompt"))), ("public_use_status", s(r.get("Public use status"))),
            ("evidence_links", [{"id": s(e["Evidence Link ID"]), "type": s(e.get("Evidence type")), "source_sheet": s(e.get("Source sheet")),
                                 "filter": s(e.get("Source subset / filter")), "rows": s(e.get("Predicate IDs / rows")),
                                 "measure": s(e.get("Measure contributed")), "why": s(e.get("Why relevant")),
                                 "provenance_grade": s(e.get("Provenance grade")), "caveat": s(e.get("Reconstruction caveat"))}
                                for e in ctx.evidence_map if s(e.get("Inference ID")) == iid]),
        ]))
    return out, checks


# ------------------------------------------------------------------ godhead / vectors / clarifications / glossary / ranges
def build_godhead(ctx, decisions):
    by = {d["id"]: d for d in decisions}
    out = []
    for r in ctx.godhead:
        pid = s(r["Panel ID"])
        d = by.get("AUTH-" + pid.replace("GOD-", "GOD-"), {})
        dec = "PENDING"
        if d.get("status") == "RESOLVED":
            dec = "APPROVE" if d["menu"] == "OPTION 1" else "REVISE"
        elif d.get("status") == "HOLD":
            dec = "HOLD"
        out.append(OrderedDict([
            ("id", pid), ("proposition", s(r.get("Context proposition"))),
            ("historic_source", s(r.get("Historic-Christian source/example"))), ("historic_url", s(r.get("Historic source URL")) or None),
            ("restoration_source", s(r.get("LDS source/example"))), ("restoration_url", s(r.get("LDS URL")) or None),
            ("relationship_to_counted_predicates", s(r.get("Relationship to counted predicates"))),
            ("not_counted", True), ("quantitative_status", s(r.get("Quantitative status"))),
            ("teaching_use", s(r.get("Teaching use"))), ("caution", s(r.get("Caution"))),
            ("author_decision", {"decision": dec, "initials": d.get("initials", ""), "date": d.get("date", ""),
                                 "notes": d.get("custom") or d.get("notes", "")}),
        ]))
    return out


def build_vectors(ctx, cells):
    out = []
    for v in ctx.vectors:
        fid = s(v["Family ID"])
        layers = [c for c in cells if c["family_id"] == fid]
        out.append(OrderedDict([
            ("family_id", fid), ("predicate", s(v.get("Predicate"))), ("master_family_code", s(v.get("Master family code"))),
            ("card_mode", s(v.get("Card mode"))), ("atomic_layer_summary", s(v.get("Atomic-layer summary"))),
            ("caption", s(v.get("Learner-facing caption"))), ("citation_display_rule", s(v.get("Citation display rule"))),
            ("pipeline_requirement", s(v.get("Pipeline requirement"))),
            ("branch_layers", [{"cell_id": c["id"], "branch": c["branch"], "rendered_state": c["rendered_state"],
                                "atomic_units": (c["evidence"] or {}).get("atomic_units"), "institution_tag": c["institution_tag"]}
                               for c in layers]),
        ]))
    return out


def build_clarifications(ctx, decisions, targets):
    by = {d["id"]: d for d in decisions}
    cases = []
    for c in ctx.clar_cases:
        cid = s(c["Case ID"])
        review = s(c.get("Review state"))
        avail = s(c.get("App availability"))
        cases.append(OrderedDict([
            ("id", cid), ("public_title", s(c.get("Public title"))), ("short_label", s(c.get("Short label"))),
            ("case_type", s(c.get("Case type"))), ("primary_tradition_family", s(c.get("Primary tradition family"))),
            ("subtradition_scope", s(c.get("Subtradition scope"))), ("counted", False),
            ("quantitative_impact", s(c.get("Quantitative impact"))), ("primary_hazard", s(c.get("Primary hazard"))),
            ("additional_hazards", [x.strip() for x in s(c.get("Additional hazards")).split("|") if x.strip()]),
            ("auto_priority", s(c.get("Auto priority"))), ("display_mode", s(c.get("Display mode"))),
            ("max_auto_cues", int(s(c.get("Max auto cues")) or 1)), ("review_state", review),
            ("app_availability", avail), ("answer_authority", s(c.get("Answer authority"))),
            ("public_release", review == "APPROVED" and avail.upper().startswith("PUBLIC")),
            ("release_hold_reason", None if avail.upper().startswith("PUBLIC") else avail),
            ("learner_question", s(c.get("Learner question / apparent tension"))), ("key_distinction", s(c.get("Key distinction"))),
            ("resolution_summary", s(c.get("Resolution summary"))), ("internal_variation", s(c.get("Internal variation"))),
            ("interfaith_significance", s(c.get("Interfaith significance"))), ("does_not_prove", s(c.get("What this case does NOT prove"))),
            ("learner_cue_copy", s(c.get("Learner cue copy"))), ("explorer_category", s(c.get("Manual explorer category"))),
            ("anchor", {"type": "explorer_category", "value": s(c.get("Manual explorer category")),
                        "related_predicate_ids": [x.strip() for x in s(c.get("Related current predicate IDs")).split(",") if x.strip()]}),
            ("author", {"case": by.get("AUTH-" + cid + "-CASE", {}).get("status"), "cue": by.get("AUTH-" + cid + "-CUE", {}).get("status"),
                        "notes": s(c.get("Author notes"))}),
            ("sources", [t.public() | {"claim_supported": s(src.get("Claim supported")), "source_role": s(src.get("Source role")),
                                       "institution": s(src.get("Tradition / institution")), "subtradition_scope": s(src.get("Subtradition scope")),
                                       "authority_note": s(src.get("Authority note")), "current": s(src.get("Current?")),
                                       "period": s(src.get("Source date / historical period"))}
                         for src in ctx.clar_sources if s(src.get("Case ID")) == cid
                         for t in targets if t.kind == "CLARIFICATION" and t.key == s(src["Source ID"])]),
        ]))
    triggers, deferred = [], []
    for t in ctx.clar_triggers:
        rec = {"id": s(t["Trigger ID"]), "case_id": s(t.get("Case ID")), "type": s(t.get("Trigger type")),
               "value": s(t.get("Trigger value")), "match_mode": s(t.get("Match mode")),
               "required_tradition": s(t.get("Required tradition context")) or None,
               "required_topic": s(t.get("Required topic context")) or None,
               "auto_cue_eligible": s(t.get("Auto-cue eligible?")) == "YES", "priority": s(t.get("Priority")),
               "relevance_weight": _num(t.get("Relevance weight")), "manual_explorer": s(t.get("Manual explorer?")) == "YES",
               "note": s(t.get("Trigger note")), "active": s(t.get("Active?"))}
        if rec["match_mode"] == "SEMANTIC" or rec["type"] == "QUESTION_PATTERN" or rec["active"] == "DEFERRED":
            rec["deferred_reason"] = "AUTH-ARCH-002: SEMANTIC / QUESTION_PATTERN triggers deferred; v1 deterministic only"
            deferred.append(rec)
        else:
            triggers.append(rec)
    vocab = {}
    for v in ctx.clar_vocab:
        vocab.setdefault(s(v["Vocabulary"]), []).append({"value": s(v.get("Allowed value")), "meaning": s(v.get("Meaning")), "rule": s(v.get("App / research rule"))})
    policy = {k: (_num(ctx.config.get(k)) if not isinstance(ctx.config.get(k), str) else s(ctx.config.get(k)))
              for k in ctx.config if k.startswith("clarification_")}
    policy["enabled"] = s(ctx.config.get("clarification_layer_enabled")).casefold() == "true"
    return {"policy": policy, "cases": cases, "triggers": triggers, "deferred_triggers": deferred, "vocabulary": vocab,
            "release_summary": {"approved_cases": [c["id"] for c in cases if c["review_state"] == "APPROVED"],
                                "publicly_released_cases": [c["id"] for c in cases if c["public_release"]],
                                "held_cases": {c["id"]: c["release_hold_reason"] for c in cases if not c["public_release"]}}}


def build_glossary(ctx):
    terms = [{"term": s(r["Term"]), "definition": s(r.get("Working definition"))} for r in ctx.glossary]
    hazards = [{"type": s(v.get("Allowed value")), "plain_language": s(v.get("Meaning")), "app_rule": s(v.get("App / research rule"))}
               for v in ctx.clar_vocab if s(v["Vocabulary"]) == "Hazard Type"]
    states = [{"state": s(v["Rendered State"]), "metric_class": s(v.get("Metric Class")), "public_meaning": s(v.get("Public meaning")),
               "rendering_rule": s(v.get("App rendering rule")), "counts_as_result": s(v.get("Counts as theological result?"))}
              for v in ctx.state_vocab]
    style = []
    for t in terms:
        for f in style_flags(t["definition"]):
            style.append({"file": "glossary.json", "id": t["term"], "field": "definition", "flag": f})
    return {"terms": terms, "hazard_types": hazards, "hazard_type_count": len(hazards), "rendered_states": states,
            "orientation_rule": ctx.config_rules.get("clarification_hazards_in_orientation", "")}, style


def build_ranges(ctx, inferences, cells):
    """Structural sensitivity ranges computed from the workbook. The paper's Section 14 ranges were
    not available to this session; Cowork should reconcile these against the paper."""
    by = {i["id"]: i for i in inferences}
    out = {
        "source": "Computed from workbook v2.16 raw sheets by the Gate 2 pipeline. "
                  "Paper section 14 sensitivity ranges NOT available in the Code session — reconcile before publication.",
        "policy": "Every number renders as count + percentage + sensitivity range through one sjn-stat component. "
                  "No tradition-level percentages anywhere (full_branch_map_enabled = False).",
        "ranges": {k: by[k]["stat"] for k in by},
        "denominators": {"inherited": 57, "restoration_additions": 26, "teaching_universe": 83, "branch_cells": 456, "branches": 8, "cells_per_branch": 57},
        "not_counted_layers": ["Godhead Context (GOD-01–GOD-04)", "Interpretive Clarifications", "Related CTA Topics", "Antecedent Examples"],
        "h43_note": "H43 shows 5 certified D cells, 1 PENDING REVIEW (Eastern Orthodox; essence–energies learner note pending), "
                    "2 NOT LOCATED — CURRENT SOURCE (Baptist, Mennonite). Unresolved cells are never projected as D.",
        "family_summary": [{"lens": s(r["Core teaching lens"]), "count": _num(r.get("Count")),
                            "share_of_83": round(float(r.get("Share of 83") or 0), 4) if not (isinstance(r.get("Share of 83"), str) and str(r.get("Share of 83")).startswith("=")) else None}
                           for r in ctx.family_summary if s(r.get("Core teaching lens"))],
    }
    return out
