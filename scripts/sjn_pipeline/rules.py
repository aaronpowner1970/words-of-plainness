"""P001–P031 validation rules (Pipeline Validation Spec). Each rule returns a dict:
{rule, severity, status, expected, actual, detail}. status in PASS | FAIL | GATE-CLEAR | GATE-OPEN | INFO.
BLOCK rules with FAIL make the build fail. GATE rules report but only block the gated surface.
"""
import re
from collections import Counter

from .model import BRANCHES, ratification_decision
from .workbook import s, b
from .textnorm import phrase_word_count

STATE_TO_METRIC = {"A": "A", "A-SF": "A", "Q": "Q", "D": "D"}
PCUSA_TEXT_URL = "https://pcusa.org/sites/default/files/boc2016.pdf"
RETIRED_EXPECTED = {"Q-056", "Q-342", "Q-344"}


def R(rule, severity, status, expected, actual, detail=""):
    return {"rule": rule, "severity": severity, "status": status, "expected": expected,
            "actual": actual, "detail": detail}


def _spec(ctx, rule):
    for r in ctx.pipeline_spec:
        if s(r["Rule ID"]) == rule:
            return s(r.get("Severity")), s(r.get("Check"))
    return "BLOCK", ""


def run_rules(ctx, targets, runner, decisions, gates, canonical, propagation_issues, emitted_counts):
    out = []
    q = ctx.queue
    qids = [s(r["Queue ID"]) for r in q]
    by_qid = {s(r["Queue ID"]): r for r in q}
    expected_n = int(s(ctx.config.get("queue_expected_rows", 456)))

    def add(rule, ok, expected, actual, detail="", gate=False):
        sev, _ = _spec(ctx, rule)
        if gate or sev == "GATE":
            status = "GATE-CLEAR" if ok else "GATE-OPEN"
        else:
            status = "PASS" if ok else "FAIL"
        out.append(R(rule, sev, status, expected, actual, detail))

    # P001 row count
    add("P001", len(q) == expected_n, expected_n, len(q))
    # P002 exact id set
    exp_ids = {f"Q-{i:03d}" for i in range(1, expected_n + 1)}
    missing = sorted(exp_ids - set(qids)); dup = [k for k, v in Counter(qids).items() if v > 1]
    add("P002", not missing and not dup and len(qids) == expected_n, "exact Q-001…Q-456",
        f"{len(set(qids))} unique; missing {len(missing)}; duplicates {len(dup)}", f"missing={missing[:5]} dup={dup[:5]}")
    # P003 rendered state
    states = {s(r["Rendered State"]) for r in ctx.state_vocab}
    bad = [(s(r["Queue ID"]), s(r.get("Rendered State (app-safe)"))) for r in q
           if s(r.get("Rendered State (app-safe)")) not in states or not s(r.get("Rendered State (app-safe)"))]
    add("P003", not bad, "456 valid", f"{len(q) - len(bad)} valid", f"bad={bad[:5]}")
    # P004 metric class consistency + confidence enum
    metric_ok = ctx.enums.get("Metric Class", ["A", "Q", "D", "EXCLUDED"])
    conf_ok = ctx.enums.get("Evidence confidence", [])
    bad = []
    for r in q:
        st, mc = s(r.get("Rendered State (app-safe)")), s(r.get("Metric Class (future branch analytics)"))
        exp = STATE_TO_METRIC.get(st, "EXCLUDED")
        if mc not in metric_ok or mc != exp:
            bad.append((s(r["Queue ID"]), st, mc))
        cf_ = s(r.get("Evidence confidence"))
        if cf_ and conf_ok and cf_ not in conf_ok:
            bad.append((s(r["Queue ID"]), "confidence", cf_))
    add("P004", not bad, "456 valid", f"{len(q) - len(bad)} valid", f"bad={bad[:5]}")
    # P005 truncated URLs
    trunc = []
    for r in q:
        for k in ("Authority / adoption URL", "Text URL"):
            v = s(r.get(k))
            if v.endswith("...") or v.endswith("…"):
                trunc.append((s(r["Queue ID"]), k))
    for c in ctx.citations:
        for k in ("Historical authority URL", "Historical text URL", "Restoration primary URL", "Restoration supplemental URL"):
            v = s(c.get(k))
            if v.endswith("...") or v.endswith("…"):
                trunc.append((s(c["Predicate ID"]), k))
    add("P005", not trunc, 0, len(trunc), str(trunc[:5]))
    # P006 live fetch
    fails = runner.unresolved_failures()
    n_urls = len(runner.http) + len(runner.rendered)
    wl = [u for d in (runner.http, runner.rendered) for u, fr in d.items() if fr.whitelisted]
    add("P006", not fails, "0 unresolved failures", f"{len(fails)} unresolved of {n_urls} distinct URLs",
        f"failures={fails[:5]}; whitelisted={wl}")
    # P007 PC(USA)
    bad = []
    for r in q:
        inst = s(r.get("Institution / jurisdiction"))
        for k in ("Authority / adoption URL", "Text URL"):
            v = s(r.get(k))
            if "pcusa.org" in v and v.endswith(".pdf") and v != PCUSA_TEXT_URL:
                bad.append((s(r["Queue ID"]), v))
        if "Presbyterian Church (U.S.A.)" in inst and s(r.get("Text URL")) and s(r.get("Text URL")) != PCUSA_TEXT_URL:
            bad.append((s(r["Queue ID"]), s(r.get("Text URL"))))
    for c in ctx.citations:
        if "Presbyterian Church (U.S.A.)" in s(c.get("Historical institution / scope")) and s(c.get("Historical text URL")) != PCUSA_TEXT_URL:
            bad.append((s(c["Predicate ID"]), s(c.get("Historical text URL"))))
    add("P007", not bad, "No old/dead URL", f"{len(bad)} bad", str(bad[:5]))
    # P008 case-study distributions
    def dist(fid):
        return Counter(s(r.get("Rendered State (app-safe)")) for r in q if s(r.get("Family ID")) == fid)
    d05, d22, d43 = dist("RNR-H05"), dist("RNR-H22"), dist("RNR-H43")
    ok = d05.get("A") == 8 and d22.get("Q") == 8 and d43.get("D") == 5 and d43.get("PENDING REVIEW") == 1 \
        and d43.get("NOT LOCATED — CURRENT SOURCE") == 2
    add("P008", ok, "H05 8A; H22 8Q; H43 5D+1 pending+2 gaps", f"H05={dict(d05)} H22={dict(d22)} H43={dict(d43)}")
    # P009 inference recomputation: workbook formulas (evaluated from raw sheets) vs independent Python recount
    inf = emitted_counts.get("inference_checks", [])
    bad = [i for i in inf if not i["match"]]
    add("P009", len(inf) == 13 and not bad, "13 exact matches (formula vs independent recount)",
        f"{len(inf) - len(bad)} of {len(inf)} match", str(bad[:3]))
    drift = [i for i in inf if i.get("narrative_match") is False]
    out.append(R("P009-NARRATIVE", "WARN", "PASS" if not drift else "WARN",
                 "Inference Evidence Map measure text equals recomputed values",
                 f"{len(inf) - len(drift)} of {len(inf)} narrative measures current",
                 "stale narrative (workbook prose to update): " + "; ".join(
                     f"{i['id']}: map says {i['evidence_map']}, recomputed {i['recomputed']}" for i in drift)))
    # P010 branch partition
    bs = emitted_counts.get("branch_summary", [])
    add("P010", len(bs) == 8 and all(x["total_states"] == 57 for x in bs), "8 MATCH",
        f"{sum(1 for x in bs if x['total_states'] == 57)} MATCH", str([(x['branch'], x['total_states']) for x in bs if x['total_states'] != 57]))
    # P011 reconciliation keys
    f24 = [s(r["Queue ID"]) for r in ctx.final24]; p2 = [s(r["Queue ID"]) for r in ctx.pass2]
    drift = []
    for r in ctx.final24 + ctx.pass2:
        qr = by_qid.get(s(r["Queue ID"]))
        if qr and s(r.get("Rendered State")) != s(qr.get("Rendered State (app-safe)")):
            drift.append((s(r["Queue ID"]), s(r.get("Rendered State")), s(qr.get("Rendered State (app-safe)"))))
    ok = len(set(f24)) == 24 and len(f24) == 24 and all(x in by_qid for x in f24) and len(set(p2)) == 16 and all(x in by_qid for x in p2) and not drift
    add("P011", ok, "24 + 16 valid", f"final24={len(set(f24))} pass2={len(set(p2))} drift={len(drift)}", str(drift[:5]))
    # P012 citations integrity
    cits = ctx.citations
    h50 = next((c for c in cits if s(c["Predicate ID"]) == "RNR-H50"), {})
    issues = []
    if len(cits) != 57:
        issues.append(f"rows={len(cits)}")
    for c in cits:
        pid = s(c["Predicate ID"])
        if not s(c.get("Restoration primary URL")):
            issues.append(f"{pid}: no comparator URL")
        if "LOCATOR REVIEW REQUIRED" in s(c.get("Historical locator")):
            issues.append(f"{pid}: locator review")
        tu = s(c.get("Historical text URL"))
        if "dei-filius_la.html" in tu or "creed-s-athanasius" in tu or "constitutio-dogmatica-dei-filius" in tu:
            issues.append(f"{pid}: non-English/non-rendering text URL")
        ready = s(c.get("Public citation readiness"))
        ph = s(c.get("Historical quoted phrase (≤15 words)"))
        if ready == "READY" and (not ph or phrase_word_count(ph) > 15):
            issues.append(f"{pid}: READY without valid phrase")
    if s(h50.get("Public citation readiness")) != "NOT READY — HISTORICAL PACKET" or s(h50.get("Historical quoted phrase (≤15 words)")):
        issues.append("H50 readiness/phrase")
    add("P012", not issues, "57 rows; 57 comparator URLs; H50 packet", f"{len(issues)} issues", str(issues[:5]))
    # P013 retired rows lineage-only
    retired = {s(r["Queue ID"]) for r in q if b(r.get("Historical Witness Retired"))}
    bad = []
    for qid in retired:
        r = by_qid[qid]
        if s(r.get("Evidence Display Role")) != "LINEAGE ONLY" or s(r.get("Metric Class (future branch analytics)")) != "EXCLUDED" \
           or s(r.get("Public cell disposition")).startswith("PUBLIC-CERTIFIED"):
            bad.append(qid)
    emitted_lineage = set(emitted_counts.get("lineage_only_ids", []))
    add("P013", retired == RETIRED_EXPECTED and not bad and emitted_lineage == retired, "Q-056/Q-342/Q-344 lineage only",
        f"retired={sorted(retired)} emitted_lineage={sorted(emitted_lineage)}", str(bad))
    # P014 canonical hash
    add("P014", canonical["deterministic"], "reproducible SHA-256 per Build Metadata recipe",
        canonical["hash"], f"declared(v2.14)={canonical['declared']}; matches_declared={canonical['matches_declared']}; "
        f"{canonical['note']}")
    # P015 row ratification (GATE)
    rat = emitted_counts.get("ratification", {})
    pend = rat.get("pending", 0); auto = rat.get("auto_approved", 0)
    add("P015", pend == 0 and auto == 0 and rat.get("total") == 83 and not propagation_issues,
        "83 explicit author decisions; 0 pending; 0 auto-approved; wording propagated",
        f"total={rat.get('total')} approve={rat.get('approve')} revise={rat.get('revise')} hold={rat.get('hold')} pending={pend}",
        f"propagation_issues={propagation_issues[:3]}", gate=True)
    # P016 / P017
    add("P016", s(ctx.config.get("full_branch_map_enabled")).casefold() == "false", "FALSE",
        s(ctx.config.get("full_branch_map_enabled")), gate=True)
    add("P017", s(ctx.config.get("external_validation")) == "PENDING", "PENDING",
        s(ctx.config.get("external_validation")), gate=True)
    # P018 historical phrase assertions
    hist = [t for t in targets if t.kind == "HISTORICAL" and t.status == "ASSERT"]
    hp = [t for t in hist if t.result == "PASS"]
    add("P018", len(hist) == 56 and len(hp) == 56, "56/56", f"{len(hp)}/{len(hist)}",
        str([(t.key, t.detail) for t in hist if t.result != "PASS"][:5]))
    # P019 restoration
    rest = [t for t in targets if t.kind == "RESTORATION"]
    rp = [t for t in rest if t.result == "PASS"]
    prim = sum(1 for t in rest if t.role == "PRIMARY"); supp = sum(1 for t in rest if t.role == "SUPPLEMENTAL")
    # citation sheet phrase must equal target sheet phrase (V058)
    mism = []
    rt_by = {(t.key, t.role): t for t in rest}
    for c in cits:
        pid = s(c["Predicate ID"])
        t = rt_by.get((pid, "PRIMARY"))
        if t and s(c.get("Restoration quoted phrase (primary, ≤15 words)")) != t.phrase:
            mism.append(pid)
        t2 = rt_by.get((pid, "SUPPLEMENTAL"))
        if t2 and s(c.get("Restoration supplemental quoted phrase")) != t2.phrase:
            mism.append(pid + "/supp")
    add("P019", len(rest) == 63 and len(rp) == 63 and prim == 57 and supp == 6 and not mism, "63/63 (57 primary + 6 supplemental)",
        f"{len(rp)}/{len(rest)} pass; primary={prim} supplemental={supp}; citation/target phrase mismatches={mism}",
        str([(t.key, t.role, t.detail) for t in rest if t.result != "PASS"][:5]))
    # P020 scoped extraction — workbook v2.19 (V074) counts the released queue-cell targets that live in
    # Case Study Phrase Targets (the two Q-290 rows) as content assertions: 56 + 63 + 21 + 2 = 142.
    core = [t for t in targets if t.kind in ("HISTORICAL", "RESTORATION", "CASE-STUDY", "QUEUE-CELL") and t.status == "ASSERT"]
    scoped = [t for t in core if t.scope_mode]
    doc_level = [t for t in core if t.scope_mode == "DOCUMENT-IS-LOCATOR"]
    pdf_rows = [t for t in core if t.extraction == "PDF"]
    n_queue_cell = sum(1 for t in core if t.kind == "QUEUE-CELL")
    add("P020", len(core) == 142 and len(scoped) == 142 and len(pdf_rows) == 3 and n_queue_cell == 2,
        "142 scoped assertions executable (56+63+21+2 queue-cell); 3 PDF rows",
        f"{len(scoped)}/{len(core)} scoped (queue-cell={n_queue_cell}); PDF rows={len(pdf_rows)}; document-is-locator={len(doc_level)}",
        "document-is-locator keys=" + str([t.key for t in doc_level]))
    # P021 Case Study Phrase Targets sheet — every row (V063: 24 case-study + 2 queue-cell = 26)
    cs = [t for t in targets if t.kind == "CASE-STUDY"]
    qc = [t for t in targets if t.kind == "QUEUE-CELL"]
    rows = cs + qc
    by_fam = Counter((t.predicate_id, t.status) for t in cs)
    state_mism = []
    for r in ctx.case_targets:
        qr = by_qid.get(s(r["Queue ID"]))
        if not qr or s(r.get("Rendered State")) != s(qr.get("Rendered State (app-safe)")):
            state_mism.append(s(r["Queue ID"]))
    asserts = [t for t in rows if t.status == "ASSERT"]; ap = [t for t in asserts if t.result == "PASS"]
    ok = (len(rows) == 26 and len(cs) == 24 and len(qc) == 2
          and by_fam[("RNR-H05", "ASSERT")] == 8 and by_fam[("RNR-H22", "ASSERT")] == 8
          and by_fam[("RNR-H43", "ASSERT")] == 5 and by_fam[("RNR-H43", "NO TARGET — UNRELEASED")] == 3
          and all(t.status == "ASSERT" for t in qc)
          and not state_mism and len(ap) == 23 and len(asserts) == 23)
    add("P021", ok, "26 rows (24 case-study + 2 queue-cell); 23 assertions; 3 unreleased no-target",
        f"rows={len(rows)} (case-study={len(cs)} queue-cell={len(qc)}) pass={len(ap)}/{len(asserts)} state_mismatch={state_mism} dist={dict(by_fam)}",
        str([(t.key, t.detail) for t in asserts if t.result != "PASS"][:5]))
    # BUILD-VALIDATION — the workbook's own Build Validation sheet (V063 / V074 / V089) must agree with the
    # pipeline's counts. This is the reconciliation guard: if the author-owned sheet and the code diverge
    # again on how the queue-cell rows are counted, the build fails instead of passing on two different numbers.
    bv = {s(r.get("Rule ID")): r for r in ctx.build_validation}
    cl_all = [t for t in targets if t.kind == "CLARIFICATION"]
    pipeline_actual = {"V063": len(rows), "V074": len(core), "V089": len(core) + len(cl_all)}
    bv_mism = []
    for rid, actual in pipeline_actual.items():
        exp = s(bv.get(rid, {}).get("Expected"))
        if not exp:
            bv_mism.append((rid, "missing in Build Validation", actual))
        elif str(exp) != str(actual):
            bv_mism.append((rid, f"workbook expects {exp}", actual))
    add("BUILD-VALIDATION", not bv_mism, "workbook V063/V074/V089 expected values equal pipeline counts (26 / 142 / 162)",
        "; ".join(f"{k}: workbook={s(bv.get(k, {}).get('Expected'))} pipeline={v}" for k, v in pipeline_actual.items()),
        str(bv_mism))
    # P022 vector captions
    v = ctx.vectors
    ok = {s(r["Family ID"]) for r in v} == {"RNR-H07", "RNR-H32", "RNR-H56"} and all(s(r.get("Card mode")) == "VECTOR" and s(r.get("Learner-facing caption")) for r in v) \
        and emitted_counts.get("vector_cards") == 3
    add("P022", ok, "3/3 VECTOR captions", f"{len(v)} rows; emitted VECTOR cards={emitted_counts.get('vector_cards')}")
    # P023 clarifications not counted
    bad = [s(c["Case ID"]) for c in ctx.clar_cases if b(c.get("Counted?")) or s(c.get("Quantitative impact")) != "NONE — NOT COUNTED"]
    add("P023", not bad, "100% NOT COUNTED", f"{len(ctx.clar_cases) - len(bad)}/{len(ctx.clar_cases)}", str(bad))
    # P024 trigger policy
    case_ids = {s(c["Case ID"]) for c in ctx.clar_cases}
    case_by = {s(c["Case ID"]): c for c in ctx.clar_cases}
    viol = []
    for t in ctx.clar_triggers:
        cid = s(t.get("Case ID"))
        if cid not in case_ids:
            viol.append((s(t["Trigger ID"]), "FK"))
        if s(t.get("Trigger type")) == "TRADITION" and s(t.get("Auto-cue eligible?")) == "YES":
            viol.append((s(t["Trigger ID"]), "tradition-only auto-cue"))
        if s(t.get("Auto-cue eligible?")) == "YES" and s(t.get("Priority")) != "HIGH":
            viol.append((s(t["Trigger ID"]), "auto-cue without HIGH"))
        if s(t.get("Match mode")) == "SEMANTIC" and s(t.get("Active?")) != "DEFERRED":
            viol.append((s(t["Trigger ID"]), "semantic trigger not DEFERRED (AUTH-ARCH-002)"))
    for src in ctx.clar_sources:
        if s(src.get("Case ID")) not in case_ids:
            viol.append((s(src["Source ID"]), "FK"))
    for c in ctx.clar_cases:
        if int(s(c.get("Max auto cues")) or 0) > int(s(ctx.config.get("clarification_max_auto_cues_per_view")) or 1):
            viol.append((s(c["Case ID"]), "max auto cues"))
    add("P024", not viol, "0 FK/policy violations", len(viol), str(viol[:5]))
    # P025 clarification sources (PENDING FETCH sources are conditional: failure drops the source, not the build)
    cl = [t for t in targets if t.kind == "CLARIFICATION"]
    active = [t for t in cl if not t.dropped]
    dropped = [t for t in cl if t.dropped]
    ap_ = [t for t in active if t.result == "PASS"]
    add("P025", len(cl) == len(ctx.clar_sources) and len(ap_) == len(active),
        f"{len(active)}/{len(active)} emitted sources pass locator-scoped containment",
        f"{len(ap_)}/{len(active)} pass; dropped from cases: " + (", ".join(t.key for t in dropped) or "none"),
        str([(t.key, t.detail) for t in active if t.result != "PASS"][:5]))
    # P026 answer authority
    viol = []
    for c in ctx.clar_cases:
        rs = s(c.get("Review state"))
        if s(c.get("Answer authority")) == "APPROVED_CASE" and rs != "APPROVED":
            viol.append((s(c["Case ID"]), "authority without approval"))
        if rs != "APPROVED" and s(c.get("Display mode")) == "AUTO_CUE_MANUAL_EXPANSION" and s(c.get("App availability")).startswith("PUBLIC"):
            viol.append((s(c["Case ID"]), "public auto-cue without approval"))
    add("P026", not viol, "0 authority-state violations", len(viol), str(viol))
    # P027 ADQ inventory
    ids = [d["id"] for d in decisions]
    ready = sum(d["actionability"] == "READY" for d in decisions); blocked = sum(d["actionability"] == "BLOCKED" for d in decisions)
    add("P027", len(ids) == 104 and len(set(ids)) == 104 and ready == 101 and blocked == 3, "104 unique / 101 READY / 3 BLOCKED",
        f"{len(ids)} rows / {len(set(ids))} unique / {ready} READY / {blocked} BLOCKED")
    # P028 current item + gate consistency
    attn = sum(d["needs_attention"] for d in decisions); cur = sum(d["current_item"] for d in decisions)
    contradictions = [g["gate"] for g in gates if g["status"] == "AUTHOR CLEAR" and (g["needs_attention"] or g["holds"] or g["deferred"])]
    ok = ((attn > 0 and cur == 1) or (attn == 0 and cur == 0)) and not contradictions
    add("P028", ok, "0 gate-clearance contradictions", f"needs_attention={attn} current={cur} contradictions={contradictions}",
        "gates=" + "; ".join(f"{g['gate'].split(' — ')[0]}={g['status']}" for g in gates))
    # P029 complete dispositions
    incomplete = [d["id"] for d in decisions if d["actionability"] == "READY" and d["status"] not in ("RESOLVED", "HOLD", "DEFERRED")]
    add("P029", not incomplete, "0 incomplete author dispositions", len(incomplete), str(incomplete[:5]))
    # P030 no silent research-code mutation
    code83 = {s(r["ID"]): s(r.get("Comparison / authority")) for r in ctx.all83}
    mut = []
    for r in ctx.inherited57:
        pid = s(r["Predicate ID"])
        if code83.get(pid) != s(r.get("Current A/Q/D/U")):
            mut.append((pid, "All83 vs Inherited57"))
    for c in cits:
        pid = s(c["Predicate ID"])
        if code83.get(pid) != s(c.get("Current master code")):
            mut.append((pid, "All83 vs citations"))
    for r in ctx.restoration26:
        pid = s(r["Addition ID"])
        if code83.get(pid) != s(r.get("Current authority tier")):
            mut.append((pid, "All83 vs Restoration26 tier"))
    for r in ctx.ratification:
        pid = s(r["ID"])
        if code83.get(pid) != s(r.get("Current code / tier")):
            mut.append((pid, "All83 vs Row Ratification"))
    for d in decisions:
        if d["id"].startswith("AUTH-RAT-") and re.search(r"\b(code|tier)\s*→", d["custom"], re.I):
            mut.append((d["id"], "custom response attempts code/tier change"))
    add("P030", not mut, "0 silent research-code mutations", len(mut), str(mut[:5]))
    # P031 future gates
    fut = [d for d in decisions if d["id"].startswith("AUTH-FUTURE-")]
    add("P031", len(fut) == 3 and all(d["status"] == "BLOCKED" for d in fut), "3 future decisions registered BLOCKED",
        f"{len(fut)} registered; statuses={[d['status'] for d in fut]}")
    return out
