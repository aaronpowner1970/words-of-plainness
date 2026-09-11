"""Ratified Branch Source Registry rows, read from the workbook, plus the pipeline context
pieces the agents need (predicate definitions, released cells, Restoration comparators).

The workbook is read only. Nothing here writes to it."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sjn_pipeline.workbook import Workbook, s  # noqa: E402
from sjn_pipeline.registry import load_registry, ratified, fallback_only_ids, admitted_domains  # noqa: E402

from .config import newest_workbook  # noqa: E402


class Registry:
    def __init__(self, workbook_path=None):
        self.path = workbook_path or newest_workbook()
        self.wb = Workbook(self.path)
        _, cfg, _ = self.wb.table("APP CONFIG", "Key")
        self.config = {s(r.get("Key")): r.get("Value") for r in cfg if s(r.get("Key"))}
        self.rows_all = load_registry(self.wb)
        self.rows = ratified(self.rows_all)
        self.fallback_ids = set(fallback_only_ids(self.config))
        self.by_id = {r["registry_id"]: r for r in self.rows}
        self.app_master_version = s(self.config.get("app_master_version"))

    def for_branch(self, branch, include_fallback=True):
        out = [r for r in self.rows if r["branch"] == branch]
        if not include_fallback:
            out = [r for r in out if r["registry_id"] not in self.fallback_ids]
        return out

    def is_fallback(self, rid):
        return rid in self.fallback_ids

    def public(self, rid):
        """Fields an agent may see about a standard: never the URL."""
        r = self.by_id[rid]
        return {"registry_id": rid, "branch": r["branch"], "standard_title": r["standard_title"],
                "authority_tier": r["authority_tier"], "speaks_for": r["speaks_for"],
                "scope_caveat": r["scope_caveat"], "fallback_only": rid in self.fallback_ids}

    def domains(self, rid):
        primary, extra = admitted_domains(self.by_id[rid])
        return [primary] + extra


def load_predicates(wb):
    """Inherited 57 rows keyed by Predicate ID with the fields the agents receive."""
    _, rows, _ = wb.table("Inherited 57", "Predicate ID")
    out = {}
    for r in rows:
        pid = s(r["Predicate ID"])
        definition = s(r.get("Historical source-report definition"))
        mode = s(r.get("Original mode"))
        out[pid] = {
            "family_id": pid,
            "predicate": s(r.get("Normalized predicate family")),
            "mode": mode,
            "teaching_family": s(r.get("Teaching family (editorial)")),
            "definition": definition,
            "floor_note": s(r.get("Accepted comparison / semantic-floor note")),
            "family_code": s(r.get("Current A/Q/D/U")),
            "lens": s(r.get("Teaching lens")),
            "subject_scope": subject_scope(pid, definition, mode),
            # The Predicate sheet carries no lexical-floor marker in v2.23, so no family is lexical:
            # WORD_ONLY is always REJECT (spec §4, Verifier).
            "lexical_floor": False,
        }
    return out


def subject_scope(pid, definition, mode):
    d = definition.casefold()
    if "christological" in mode.casefold():
        return "CHRIST (the two natures of the incarnate Son; the predicate is a delimiter on their union)"
    if "trinitarian" in mode.casefold():
        return "GOD AS TRINITY (the predicate delimits how the three persons are described)"
    if "holy spirit" in d or "spirit's" in d:
        return "THE HOLY SPIRIT"
    if "the son" in d or "logos" in d or "christ" in d or "filial" in d:
        return "THE SON (the eternal Son / Logos, as divine)"
    return "GOD (the one God, or the Father; not the Church, not humanity, not Christ's human nature)"


def load_comparators(wb):
    """Restoration comparator per family from Inherited Public Citations (label, source, locator, phrase)."""
    _, rows, _ = wb.table("Inherited Public Citations", "Predicate ID")
    out = {}
    for r in rows:
        pid = s(r["Predicate ID"])
        out[pid] = {
            "label": s(r.get("Restoration comparator label")),
            "source": s(r.get("Restoration source")),
            "locator": s(r.get("Restoration locator")),
            "phrase": s(r.get("Restoration quoted phrase (primary, ≤15 words)")),
            "url": s(r.get("Restoration primary URL")),
            "scope_note": s(r.get("Accepted scope note")),
            "master_code": s(r.get("Current master code")),
            "historical_branch": s(r.get("Historical teaching branch")),
            "historical_document": s(r.get("Historical document")),
            "historical_locator": s(r.get("Historical locator")),
            "historical_phrase": s(r.get("Historical quoted phrase (≤15 words)")),
        }
    return out


def load_queue(wb):
    _, rows, _ = wb.table("Evidence-First Cell Queue", "Queue ID")
    out = []
    for r in rows:
        out.append({
            "queue_id": s(r["Queue ID"]), "family_id": s(r.get("Family ID")), "predicate": s(r.get("Predicate")),
            "family_code": s(r.get("Current family code")), "branch": s(r.get("Teaching branch")),
            "collapse_rule": s(r.get("Collapse rule")), "recovery_state": s(r.get("Recovery state")),
            "disposition": s(r.get("Public cell disposition")), "institution": s(r.get("Institution / jurisdiction")),
            "document": s(r.get("Document")), "locator": s(r.get("Proposition locator")),
            "authority_url": s(r.get("Authority / adoption URL")), "text_url": s(r.get("Text URL")),
            "confidence": s(r.get("Evidence confidence")), "scope_control": s(r.get("Scope control")),
            "source_note": s(r.get("Source note")), "reviewer_status": s(r.get("Reviewer status")),
            "reviewer_notes": s(r.get("Reviewer notes")),
            "rendered_state": s(r.get("Rendered State (app-safe)")), "metric_class": s(r.get("Metric Class (future branch analytics)")),
            "retired": s(r.get("Historical Witness Retired")).casefold() == "true",
            "display_role": s(r.get("Evidence Display Role")),
        })
    return out


def load_case_targets(wb):
    _, rows, _ = wb.table("Case Study Phrase Targets", "Queue ID")
    out = {}
    for r in rows:
        out.setdefault(s(r["Queue ID"]), []).append({
            "document": s(r.get("Document")), "locator": s(r.get("Locator")), "url": s(r.get("Assertion Text URL")),
            "phrase": s(r.get("Quoted phrase")), "status": s(r.get("Target Status")),
        })
    return out


def open_cells(queue):
    """The 315 cells Gate 6 will eventually run: not released, not out of scope, not lineage-only."""
    return [c for c in queue if c["rendered_state"].startswith("NOT LOCATED") and not c["retired"]]


def released_cells(queue):
    return [c for c in queue if c["rendered_state"] in ("A", "A-SF", "Q", "D")]


def reviewed_empty_cells(queue):
    return [c for c in queue if c["rendered_state"] == "NOT LOCATED — CURRENT STANDARD REVIEWED"]
