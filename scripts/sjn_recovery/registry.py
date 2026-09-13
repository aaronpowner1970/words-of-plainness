"""Ratified Branch Source Registry rows, read from the workbook, plus the pipeline context
pieces the agents need (predicate definitions, released cells, Restoration comparators).

The workbook is read only. Nothing here writes to it.

v2.25 (RECEPTION AXIS): the registry sheet carries `reception_scope` and `reception_note`, and the
APP CONFIG keys below govern the harness. They are READ from the workbook, never hard-coded:

  gate6_threshold_metric      SAME_STANDARD            the gated recall metric
  authority_tier_rank         CONCILIAR|CONFESSIONAL|…  descending authority rank (ungated diagnostics)
  reception_scope_vocabulary  UNIVERSAL|MULTILATERAL|…  the closed vocabulary of reception_scope
  reception_axis              ADOPT_BOTH               both columns are live
  creed_tier_resolution       TIER_PER_CITED_DOCUMENT  a creed cited from a lower-tier row resolves CONCILIAR
  lateran_iv_scope            EXTEND_TO_CONSTITUTION_2 BSR-RC-04 ratifies constitutions 1–2
  verifier_routing            SONNET_WITH_OPUS_SLICE   primary verifier + adjudication slice
  dialogue_text_policy        DIALOGUE_ONLY_NEVER_CITED
  encyclical_1848_status      RECORD_STANDING_ONLY
  registry_fallback_only_rows BSR-AN-05                fallback-tier rows (pass two only)
"""
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sjn_pipeline.workbook import Workbook, s  # noqa: E402
from sjn_pipeline.registry import (load_registry, ratified, fallback_only_ids, admitted_domains, admission, config_list,  # noqa: E402
                                   reception_scope, is_dialogue_only, is_translation_witness, is_witness_row,
                                   citation_refusal, refusal_reason)

from .config import newest_workbook, OPUS_SLICE_ROWS_DEFAULT, ROUTING_SONNET_WITH_OPUS_SLICE  # noqa: E402

# ---------------------------------------------------------------- authority tier rank
# The rank is READ from APP CONFIG `authority_tier_rank` (AUTHOR RATIFIED, v2.25). This module-level
# default is only the fallback for a workbook that predates the key; Registry() replaces it.
TIER_RANK_DEFAULT = ["CONCILIAR", "CONFESSIONAL", "CATECHETICAL", "OFFICIAL_EXPOSITION", "CURRENT_OFFICIAL_WITNESS"]
TIER_RANK = list(TIER_RANK_DEFAULT)


def set_tier_rank(rank):
    global TIER_RANK
    TIER_RANK[:] = list(rank)


def bare_tier(tier):
    """Rank on the bare tier. Parenthetical qualifiers - "CONCILIAR (translation)", "CATECHETICAL
    (historic)", "CONFESSIONAL (liturgically confessed; the Creed within resolves CONCILIAR)" - are
    disclosure, not rank, and are stripped here."""
    return re.split(r"\s*\(", (tier or "").strip())[0].strip().upper()


def tier_rank(tier):
    """0 is the highest authority. An unknown tier sorts below every known one."""
    b = bare_tier(tier)
    return TIER_RANK.index(b) if b in TIER_RANK else len(TIER_RANK)


_CREED_LOCATOR = re.compile(r"\b(creed|symbol of faith|nicene|niceno|athanasian|apostles'? creed|quicunque)\b", re.I)


def creed_resolution_tier(tier_text):
    """The tier a creed printed inside this row resolves to, per the row's own tier note
    ("… the Creed within resolves CONCILIAR", "Nicene and Athanasian resolve CONCILIAR"), or None."""
    m = re.search(r"resolves?\s+([A-Z_]+)", tier_text or "")
    return m.group(1).upper() if m else None


DELTA_FIELDS = ("canonical_url", "fetch_mode")


def load_registry_delta(path):
    """A registry draft CSV (wop-scratch WoP_SJN_BranchSourceRegistries_Draft3rN_*.csv) read as a DELTA: only rows whose
    `r4_change` column names fields are applied, and only the fields in DELTA_FIELDS. Returns (changes, provenance)."""
    import csv
    import hashlib
    raw = open(path, "rb").read()
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    changes = {}
    for r in rows:
        fields = [f.strip() for f in (r.get("r4_change") or "").split(";") if f.strip()]
        bad = [f for f in fields if f not in DELTA_FIELDS]
        if bad:
            raise SystemExit(f"registry delta {os.path.basename(path)}: {r.get('registry_id')} names fields outside {DELTA_FIELDS}: {bad}")
        if fields:
            changes[r["registry_id"]] = {f: r.get(f) for f in fields}
    return changes, {"file": os.path.basename(path), "sha256": hashlib.sha256(raw).hexdigest(), "rows": sorted(changes)}


class Registry:
    def __init__(self, workbook_path=None, registry_delta=None):
        """registry_delta (session 5, 2026-09-13): the path of a draft registry CSV whose marked URL changes are applied
        IN MEMORY for a corpus build the author has authorized before ratifying them. The workbook is never written; every
        row so changed carries `_registry_delta` (old value, new value, file, sha256) and the corpus manifest records it."""
        self.path = workbook_path or newest_workbook()
        self.wb = Workbook(self.path)
        _, cfg, _ = self.wb.table("APP CONFIG", "Key")
        self.config = {s(r.get("Key")): r.get("Value") for r in cfg if s(r.get("Key"))}
        self.rows_all = load_registry(self.wb)
        self.delta = None
        if registry_delta:
            changes, prov = load_registry_delta(registry_delta)
            by = {r["registry_id"]: r for r in self.rows_all}
            for rid, ch in changes.items():
                if rid not in by:
                    raise SystemExit(f"registry delta names {rid}, which is not a workbook registry row")
                by[rid]["_registry_delta"] = {**prov, "fields": {f: {"workbook": by[rid].get(f), "draft": v} for f, v in ch.items()},
                                              "status": "PENDING AUTHOR RATIFICATION"}
                by[rid].update(ch)
            self.delta = prov
        # Session 6 (R6-3): a row the author has retired is retired here, in memory, until the workbook says so.
        from . import rulings
        self.rulings_applied = []
        by = {r["registry_id"]: r for r in self.rows_all}
        for rid, ru in rulings.retirements().items():
            if rid not in by:
                raise SystemExit(f"author ruling {ru['ruling']} retires {rid}, which is not a workbook registry row")
            if by[rid].get("status") == "RETIRED":
                continue                                  # the workbook already carries it
            by[rid]["_author_ruling"] = {"ruling": ru["ruling"], "workbook_status": by[rid].get("status"), "status": "RETIRED",
                                         "reason_code": ru.get("reason_code"), "reason": ru.get("reason"),
                                         "pending": "applied in memory; workbook not written"}
            by[rid]["status"] = "RETIRED"
            self.rulings_applied.append({"registry_id": rid, "ruling": ru["ruling"], "status": "RETIRED", "reason_code": ru.get("reason_code")})
        self.rows = ratified(self.rows_all)
        self.fallback_ids = set(fallback_only_ids(self.config))
        self.by_id = {r["registry_id"]: r for r in self.rows}
        self.app_master_version = s(self.config.get("app_master_version"))
        # ---- ratified APP CONFIG keys (v2.25). Read, never hard-coded.
        self.gate_metric = s(self.config.get("gate6_threshold_metric")).upper() or "TIER_RESPECTING"
        self.tier_rank_list = config_list(self.config, "authority_tier_rank", TIER_RANK_DEFAULT)
        set_tier_rank(self.tier_rank_list)
        self.reception_vocabulary = config_list(self.config, "reception_scope_vocabulary", [])
        self.reception_axis = s(self.config.get("reception_axis")).upper()
        self.creed_tier_resolution = s(self.config.get("creed_tier_resolution")).upper()
        self.lateran_iv_scope = s(self.config.get("lateran_iv_scope")).upper()
        self.verifier_routing = s(self.config.get("verifier_routing")).upper()
        self.dialogue_text_policy = s(self.config.get("dialogue_text_policy")).upper()
        self.encyclical_1848_status = s(self.config.get("encyclical_1848_status")).upper()
        self.vocabulary_violations = [(r["registry_id"], reception_scope(r)) for r in self.rows
                                      if self.reception_vocabulary and reception_scope(r) not in self.reception_vocabulary]

    # ---------------------------------------------------------------- row selection
    def for_branch(self, branch, include_fallback=True, citable_only=True):
        """AUTHOR_RATIFIED rows of a branch. citable_only drops rows the policies refuse as citations
        (DIALOGUE_ONLY, named refusals): they stay registered for provenance but never reach an agent."""
        out = [r for r in self.rows if r["branch"] == branch]
        if not include_fallback:
            out = [r for r in out if r["registry_id"] not in self.fallback_ids]
        if citable_only:
            out = [r for r in out if not self.citation_refusal(r["registry_id"])]
        return out

    def is_fallback(self, rid):
        return rid in self.fallback_ids

    def is_witness(self, rid):
        row = self.by_id.get(rid)
        return bool(row) and is_witness_row(row)

    def is_translation_witness(self, rid):
        row = self.by_id.get(rid)
        return bool(row) and is_translation_witness(row)

    def is_dialogue_only(self, rid):
        row = self.by_id.get(rid)
        return bool(row) and is_dialogue_only(row)

    def citation_refusal(self, rid):
        return citation_refusal(self.by_id.get(rid))

    def reception(self, rid):
        return reception_scope(self.by_id.get(rid, {}))

    def opus_slice_rows(self):
        """Rows whose candidates the adjudicating verifier always sees: the caveated rows (CONTESTED
        reception, or a historic catechism), the guarded Synodikon, and every fallback-only row."""
        out = set(OPUS_SLICE_ROWS_DEFAULT) & set(self.by_id)
        for r in self.rows:
            if reception_scope(r) == "CONTESTED" or "(historic)" in s(r.get("authority_tier")).casefold():
                out.add(r["registry_id"])
            if "BLOCKING GUARD" in s(r.get("fetch_mode")).upper() or "BLOCKING GUARD" in s(r.get("reception_note")).upper():
                out.add(r["registry_id"])
        return out | (self.fallback_ids & set(self.by_id))

    def routing_is_slice(self):
        return self.verifier_routing == ROUTING_SONNET_WITH_OPUS_SLICE

    # ---------------------------------------------------------------- tiers
    def effective_tier(self, rid, chunk=None):
        """The tier a citation resolves to. Under creed_tier_resolution = TIER_PER_CITED_DOCUMENT a
        creed printed inside a lower-tier row (BSR-RC-06, BSR-EO-07) resolves to the tier the row's
        note names, when the cited chunk is the creed itself."""
        row = self.by_id.get(rid)
        if not row:
            return ""
        tier = s(row.get("authority_tier"))
        if self.creed_tier_resolution == "TIER_PER_CITED_DOCUMENT" and chunk is not None:
            resolved = creed_resolution_tier(tier)
            loc = (chunk.get("locator") or "") + " " + (chunk.get("division") or "")
            if resolved and _CREED_LOCATOR.search(loc):
                return resolved
        return tier

    def public(self, rid):
        """Fields an agent may see about a standard: never a URL. Every text field is scrubbed — a
        reception_note may legitimately carry one (BSR-MW-03's opens `LINKED FROM: https://…`, AC-15)."""
        from .textutil import scrub_urls
        r = self.by_id[rid]
        return {"registry_id": rid, "branch": r["branch"], "standard_title": scrub_urls(r["standard_title"]),
                "authority_tier": r["authority_tier"], "speaks_for": scrub_urls(r["speaks_for"]),
                "reception_scope": reception_scope(r), "reception_note": scrub_urls(s(r.get("reception_note"))),
                "scope_caveat": scrub_urls(r["scope_caveat"]), "fallback_only": rid in self.fallback_ids,
                "witness_only": is_witness_row(r)}

    def domains(self, rid):
        """Hosts the row admits under R001 (publisher_domain; plus the AC-15 official domain). Empty for a
        refused row."""
        primary, extra = admitted_domains(self.by_id[rid], self.config)
        return [d for d in [primary] + extra if d]

    def admission(self, rid):
        return admission(self.by_id[rid], self.config)


def load_predicates(wb):
    """Inherited 57 rows keyed by Predicate ID with the fields the agents receive."""
    _, rows, _ = wb.table("Inherited 57", "Predicate ID")
    from . import rulings
    ruled = rulings.required_subjects()
    out = {}
    for r in rows:
        pid = s(r["Predicate ID"])
        definition = s(r.get("Historical source-report definition"))
        mode = s(r.get("Original mode"))
        # Session 6 (R6-1): the workbook carries no required-subject column; the harness derives it (subject_scope) except
        # where the author has ruled. A workbook column, once added, wins — and must agree with the ruling.
        wb_subject = s(r.get("Required subject"))
        if wb_subject and pid in ruled and wb_subject != ruled[pid]:
            raise SystemExit(f"Inherited 57 'Required subject' for {pid} disagrees with author ruling R6-1: {wb_subject!r} vs {ruled[pid]!r}")
        if wb_subject:
            scope, source = wb_subject, "WORKBOOK"
        elif pid in ruled:
            scope, source = ruled[pid], "AUTHOR_RULING_R6-1 (2026-09-13; workbook delta pending)"
        else:
            scope, source = subject_scope(pid, definition, mode), "HARNESS_DERIVED (registry.subject_scope)"
        out[pid] = {
            "family_id": pid,
            "predicate": s(r.get("Normalized predicate family")),
            "mode": mode,
            "teaching_family": s(r.get("Teaching family (editorial)")),
            "definition": definition,
            "floor_note": s(r.get("Accepted comparison / semantic-floor note")),
            "family_code": s(r.get("Current A/Q/D/U")),
            "lens": s(r.get("Teaching lens")),
            "subject_scope": scope,
            "subject_scope_source": source,
            # The Predicate sheet carries no lexical-floor marker, so no family is lexical:
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
    """The cells Gate 6 runs. APP CONFIG `gate6_open_cell_rule` (v2.25r4, author-ratified 2026-09-13):
    OPEN = Rendered State (app-safe) begins "NOT LOCATED" AND Historical Witness Retired is not TRUE;
    everything else is closed. gate6_scope() checks this predicate against the workbook's own statement
    of the rule and against `gate6_open_cell_count`, and run.py refuses to start on a mismatch."""
    return [c for c in queue if c["rendered_state"].startswith("NOT LOCATED") and not c["retired"]]


def gate6_scope(registry, queue):
    """The Gate 6 denominator, READ from APP CONFIG and checked, never re-derived by judgement:
      gate6_open_cell_rule     the predicate open_cells() implements — the text must name both columns
      gate6_closed_states      OUT OF SCOPE | VECTOR PENDING | VECTOR COMPLETE | PENDING REVIEW | retired = TRUE
      gate6_open_cell_count    the ratified count (291); the computed count must equal it
    Returns a dict with the counts and the checks; `ok` is False on any mismatch, with `problems`."""
    cfg = registry.config
    rule = s(cfg.get("gate6_open_cell_rule"))
    closed_states = [x.strip() for x in s(cfg.get("gate6_closed_states")).split("|") if x.strip()]
    ratified = cfg.get("gate6_open_cell_count")
    try:
        ratified_n = int(float(ratified)) if ratified not in (None, "") else None
    except (TypeError, ValueError):
        ratified_n = None
    opened = open_cells(queue)
    released = released_cells(queue)
    open_ids, rel_ids = {c["queue_id"] for c in opened}, {c["queue_id"] for c in released}
    closed = [c for c in queue if c["queue_id"] not in open_ids and c["queue_id"] not in rel_ids]
    problems = []
    if "NOT LOCATED" not in rule or "Historical Witness Retired" not in rule:
        problems.append("APP CONFIG gate6_open_cell_rule is missing or does not name the two columns the harness reads "
                        f"(Rendered State begins 'NOT LOCATED'; Historical Witness Retired not TRUE): {rule!r}")
    if ratified_n is None:
        problems.append("APP CONFIG gate6_open_cell_count is missing: the open count cannot be asserted")
    elif len(opened) != ratified_n:
        problems.append(f"computed open cells {len(opened)} != APP CONFIG gate6_open_cell_count {ratified_n}")
    if open_ids & rel_ids:
        problems.append(f"open and released sets overlap: {sorted(open_ids & rel_ids)[:10]}")
    state_names = [x for x in closed_states if not x.upper().startswith("HISTORICAL WITNESS RETIRED")]
    unexplained = [c["queue_id"] for c in closed
                   if not (c["retired"] or any(c["rendered_state"].upper().startswith(x.upper()) for x in state_names))]
    if unexplained:
        problems.append(f"{len(unexplained)} closed cell(s) carry a state outside gate6_closed_states: {unexplained[:12]}")
    by_state = {}
    for c in closed:
        k = "Historical Witness Retired = TRUE" if c["retired"] else c["rendered_state"]
        by_state[k] = by_state.get(k, 0) + 1
    return {"rule": rule, "closed_states": closed_states, "ratified_open_count": ratified_n, "computed_open": len(opened),
            "released": len(released), "closed": len(closed), "total": len(queue), "closed_by_state": by_state,
            "closed_ratified": s(cfg.get("gate6_closed_ratified")), "out_of_scope_cells": s(cfg.get("gate6_out_of_scope_cells")),
            "identity": f"{len(queue)} = {len(opened)} open + {len(closed)} closed + {len(released)} released",
            "ok": not problems, "problems": problems}


def assert_gate6_scope(registry, queue, log=print):
    """Fail loudly (SystemExit) when the harness's open set is not the workbook's ratified open set."""
    sc = gate6_scope(registry, queue)
    log(f"== Gate 6 scope (APP CONFIG): {sc['identity']}; ratified open count {sc['ratified_open_count']}; "
        f"closed by state {sc['closed_by_state']}")
    if not sc["ok"]:
        for p in sc["problems"]:
            log(f"!! GATE 6 SCOPE MISMATCH: {p}")
        raise SystemExit("Gate 6 scope assertion failed — the harness's open-cell set is not the workbook's ratified set; "
                         "nothing runs until the workbook (APP CONFIG gate6_*) and the harness agree")
    return sc


def released_cells(queue):
    return [c for c in queue if c["rendered_state"] in ("A", "A-SF", "Q", "D")]


def reviewed_empty_cells(queue):
    return [c for c in queue if c["rendered_state"] == "NOT LOCATED — CURRENT STANDARD REVIEWED"]


__all__ = ["Registry", "load_predicates", "load_comparators", "load_queue", "load_case_targets", "open_cells",
           "gate6_scope", "assert_gate6_scope", "released_cells", "reviewed_empty_cells", "TIER_RANK", "bare_tier", "tier_rank", "set_tier_rank",
           "refusal_reason", "citation_refusal"]
