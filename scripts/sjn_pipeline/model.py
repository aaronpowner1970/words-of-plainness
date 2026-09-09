"""Load every workbook sheet the pipeline needs into a Context of plain dicts."""
import re
from dataclasses import dataclass, field

from .workbook import Workbook, s, b


BRANCHES = ["Roman Catholic", "Eastern Orthodox", "Lutheran", "Reformed / Presbyterian",
            "Anglican", "Baptist", "Methodist / Wesleyan", "Mennonite / Anabaptist"]


@dataclass
class Context:
    wb: Workbook
    config: dict = field(default_factory=dict)          # APP CONFIG key -> value
    config_rules: dict = field(default_factory=dict)    # APP CONFIG key -> app rule
    state_vocab: list = field(default_factory=list)     # rows of State Vocabulary (states)
    enums: dict = field(default_factory=dict)           # enumeration name -> allowed list
    all83: list = field(default_factory=list)
    inherited57: list = field(default_factory=list)
    restoration26: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    queue: list = field(default_factory=list)
    final24: list = field(default_factory=list)
    pass2: list = field(default_factory=list)
    inference: list = field(default_factory=list)
    evidence_map: list = field(default_factory=list)
    case_studies: list = field(default_factory=list)
    ratification: list = field(default_factory=list)
    godhead: list = field(default_factory=list)
    current_source: list = field(default_factory=list)
    tradition_sources: list = field(default_factory=list)
    glossary: list = field(default_factory=list)
    antecedents: list = field(default_factory=list)
    cta: list = field(default_factory=list)
    readiness: list = field(default_factory=list)
    build_validation: list = field(default_factory=list)
    selection_rules: list = field(default_factory=list)
    url_snapshot: list = field(default_factory=list)
    pipeline_spec: list = field(default_factory=list)
    hist_targets: list = field(default_factory=list)
    rest_targets: list = field(default_factory=list)
    case_targets: list = field(default_factory=list)
    vectors: list = field(default_factory=list)
    clar_vocab: list = field(default_factory=list)
    clar_cases: list = field(default_factory=list)
    clar_triggers: list = field(default_factory=list)
    clar_sources: list = field(default_factory=list)
    adq: list = field(default_factory=list)
    gate_dashboard: list = field(default_factory=list)
    are: list = field(default_factory=list)
    build_metadata: dict = field(default_factory=dict)
    hash_recipe: list = field(default_factory=list)
    family_summary: list = field(default_factory=list)


def load_context(path):
    wb = Workbook(path)
    ctx = Context(wb=wb)

    # APP CONFIG (duplicate keys: last wins, earlier kept in list)
    _, rows, _ = wb.table("APP CONFIG", "Key")
    for r in rows:
        k = s(r.get("Key"))
        if k:
            ctx.config[k] = r.get("Value")
            ctx.config_rules[k] = s(r.get("App rule"))

    # State Vocabulary: states + enumerations
    _, states, _ = wb.table("State Vocabulary", "Rendered State")
    ctx.state_vocab = states
    _, enums, _ = wb.table("State Vocabulary", "Enumeration")
    for r in enums:
        ctx.enums[s(r.get("Enumeration"))] = [x.strip() for x in s(r.get("Allowed values")).split("|")]

    def load(attr, sheet, first, stop=True):
        _, rows, _ = wb.table(sheet, first, stop_on_blank_first=stop)
        setattr(ctx, attr, rows)

    load("all83", "All 83", "Corpus")
    load("inherited57", "Inherited 57", "Predicate ID")
    load("restoration26", "Restoration 26", "Addition ID")
    load("citations", "Inherited Public Citations", "Predicate ID")
    load("queue", "Evidence-First Cell Queue", "Queue ID")
    load("final24", "Final 24 Reconciliation", "Queue ID")
    load("pass2", "Reconciliation Pass 2", "Queue ID")
    load("inference", "Inference Support", "Inference ID")
    load("evidence_map", "Inference Evidence Map", "Evidence Link ID")
    load("case_studies", "Matrix Case Studies", "Case")
    load("ratification", "Row Ratification", "ID")
    load("godhead", "Godhead Context", "Panel ID")
    load("current_source", "Current Source Recovery", "Branch teaching label")
    load("tradition_sources", "Tradition Sources", "Tradition family")
    load("glossary", "Glossary", "Term")
    load("antecedents", "Antecedent Examples", "Predicate link")
    load("cta", "Related CTA Topics", "CTA parent")
    load("readiness", "Public Readiness", "Gate")
    load("build_validation", "Build Validation", "Rule ID")
    load("selection_rules", "Citation Selection Rules", "Priority")
    load("url_snapshot", "URL Validation Snapshot", "URL")
    load("pipeline_spec", "Pipeline Validation Spec", "Rule ID")
    load("hist_targets", "Citation Phrase Targets", "Predicate ID")
    load("rest_targets", "Restoration Phrase Targets", "Predicate ID")
    load("case_targets", "Case Study Phrase Targets", "Queue ID")
    load("vectors", "Vector Family Captions", "Family ID")
    load("clar_vocab", "Clarification Vocabulary", "Vocabulary")
    load("clar_cases", "Interpretive Clarifications", "Case ID")
    load("clar_triggers", "Clarification Trigger Map", "Trigger ID")
    load("clar_sources", "Clarification Sources", "Source ID")
    load("adq", "Author Decision Queue", "Sequence")
    load("gate_dashboard", "Author Gate Dashboard", "Gate")
    load("are", "Author Response Entry", "Sequence")
    load("family_summary", "Family Summary", "Core teaching lens")

    # Build Metadata: artifact rows + canonical hash recipe rows
    ws = wb.ws("Build Metadata")
    for r in range(1, ws.max_row + 1):
        a = s(ws.cell(r, 1).value)
        if a in ("Artifact", "Canonical data/governance hash recipe", "Author workflow snapshot", "Artifact policy", ""):
            continue
        row = [s(ws.cell(r, c).value) for c in range(1, 7)]
        if a.startswith("Canonical object"):
            ctx.build_metadata["canonical_object"] = row
            ctx.build_metadata["declared_hash"] = row[4]
        elif a in ("Canonical hardened app data",):
            ctx.build_metadata["declared_hash_row"] = row
        m = re.match(r"^(.+?) ([A-Z]{1,3}:[A-Z]{1,3}) rows (\d+):(\d+)$", row[1])
        if m and row[2] in ("JSON array-of-arrays", "[address,formula] sorted by address"):
            sheet, cols, r1, r2 = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
            c1, c2 = cols.split(":")
            kind = "values" if row[2].startswith("JSON") else "formulas"
            ctx.hash_recipe.append((a, sheet, f"{c1}{r1}:{c2}{r2}", kind))
        ctx.build_metadata.setdefault("rows", []).append(row)
    return ctx


# --------------------------------------------------------------- author workflow recompute
OPTION_MENU = {"OPTION 1": "Suggested Option 1", "OPTION 2": "Suggested Option 2",
               "OPTION 3": "Suggested Option 3", "OPTION 4": "Suggested Option 4"}


def recompute_author_workflow(ctx):
    """Re-derive Author Decision Queue statuses from the Author Response Entry inputs
    using the workbook's own formula semantics (T..AH columns)."""
    are_by_seq = {int(s(r["Sequence"])): r for r in ctx.are}
    decisions = []
    for r in ctx.adq:
        seq = int(s(r["Sequence"]))
        inp = are_by_seq.get(seq, {})
        menu = s(inp.get("Response Menu"))
        custom = s(inp.get("Custom Response"))
        notes = s(inp.get("Author Notes"))
        initials = s(inp.get("Author Initials"))
        date = s(inp.get("Decision Date"))
        custom_required = [x.strip() for x in s(r.get("Custom Required For")).split("|") if x.strip()]
        actionability = s(r.get("Actionability"))

        def meta(state):
            return state if (initials and date) else f"{state} — ADD INITIALS/DATE"

        if actionability == "BLOCKED":
            status = "BLOCKED"
        elif menu == "":
            status = "OPEN"
        elif menu == "CUSTOM RESPONSE":
            status = "OPEN — CUSTOM TEXT REQUIRED" if not custom else meta("RESOLVED")
        elif menu == "HOLD — NEEDS RESEARCH":
            status = meta("HOLD")
        elif menu == "DEFER — NOT YET":
            status = meta("DEFERRED")
        elif menu in OPTION_MENU:
            status = "OPEN — CUSTOM TEXT REQUIRED" if (menu in custom_required and not custom) else meta("RESOLVED")
        else:
            status = f"UNKNOWN MENU {menu}"
        if menu == "CUSTOM RESPONSE":
            resolved = custom
        elif menu in OPTION_MENU:
            resolved = custom if (menu in custom_required) else s(r.get(OPTION_MENU[menu]))
        elif menu.startswith("HOLD") or menu.startswith("DEFER"):
            resolved = custom or menu
        else:
            resolved = ""
        needs_attention = actionability == "READY" and (status == "OPEN" or status.startswith("OPEN —") or "ADD INITIALS/DATE" in status)
        decisions.append({
            "sequence": seq, "id": s(r["Decision ID"]), "gate": s(r.get("Gate")), "category": s(r.get("Category")),
            "actionability": actionability, "menu": menu, "custom": custom, "notes": notes,
            "initials": initials, "date": date, "resolved_response": resolved, "status": status,
            "needs_attention": needs_attention, "source_sheet": s(r.get("Source Sheet")),
            "title": s(r.get("Decision Title")), "review_batch": s(r.get("Review Batch")),
            "gate_blocking": s(r.get("Gate Blocking?")),
        })
    first_attn = next((d["sequence"] for d in decisions if d["needs_attention"]), None)
    for d in decisions:
        d["current_item"] = d["needs_attention"] and d["sequence"] == first_attn
    gates = []
    for g in ctx.gate_dashboard:
        name = s(g["Gate"])
        rows = [d for d in decisions if d["gate"] == name]
        total = len(rows); ready = sum(d["actionability"] == "READY" for d in rows)
        resolved = sum(d["status"] == "RESOLVED" for d in rows)
        attn = sum(d["needs_attention"] for d in rows)
        holds = sum(d["status"] == "HOLD" for d in rows)
        deferred = sum(d["status"] == "DEFERRED" for d in rows)
        blocked = sum(d["status"] == "BLOCKED" for d in rows)
        if attn > 0:
            status = "AUTHOR ACTION REQUIRED"
        elif holds > 0:
            status = "HOLD"
        elif deferred > 0:
            status = "DEFERRED"
        elif ready == 0:
            status = "WAITING ON DEPENDENCY" if blocked > 0 else "CHECK"
        elif resolved == ready:
            status = "READY PORTION CLEAR — WAITING DEPENDENCY" if blocked > 0 else "AUTHOR CLEAR"
        else:
            status = "CHECK"
        gates.append({"gate": name, "purpose": s(g.get("Purpose")), "total": total, "ready": ready,
                      "resolved": resolved, "needs_attention": attn, "holds": holds, "deferred": deferred,
                      "blocked_future": blocked, "status": status, "clearance_condition": s(g.get("Clearance Condition"))})
    return decisions, gates


def ratification_decision(decision):
    """Row Ratification K/L/M/N derivation from a G6 decision dict."""
    st = decision["status"]
    if st == "RESOLVED":
        menu = decision["menu"]
        k = "APPROVE" if menu == "OPTION 1" else "REVISE" if menu in ("OPTION 2", "CUSTOM RESPONSE") else "HOLD"
    elif st == "HOLD":
        k = "HOLD"
    else:
        k = "PENDING"
    initials = decision["initials"] if k != "PENDING" else ""
    date = decision["date"] if k != "PENDING" else ""
    notes = decision["custom"] if k == "REVISE" else decision["resolved_response"] if k == "HOLD" else decision["notes"]
    return {"decision": k, "initials": initials, "date": date, "revision_notes": notes,
            "response_menu": decision["menu"], "custom_response": decision["custom"], "author_notes": decision["notes"]}
