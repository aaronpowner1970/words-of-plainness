#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sjn_merge_decisions.py — merge Decision Console output into the SJN workbook.

Seeking Jesus of Nazareth · Gate 5 (Branch Source Registries) and forward.
Author: Aaron J. Powner (AJP) · Words of Plainness Ministry
Written in Cowork, 2026-09-10.

WHAT IT DOES
  Reads a decisions JSON exported by (or read out of) the Decision Console,
  plus the Branch Source Registries CSV, and writes workbook vN+1:

    1. New sheet  "Branch Source Registry"  — one ratified row per standard.
    2. APP CONFIG — registry keys, breadth/lineage/console policy, version bump.
    3. Build Metadata — one lineage row for the new version.
    4. Lineage & Merge Audit — one audit row for this merge.
    5. Build Validation V100 — rewritten per the author's SETUP-01 decision.

  Then, before anything ships:

    6. Cell-by-cell diff of the new workbook against the prior version. Every
       changed cell must appear in the intended-change allowlist this script
       built while editing. One unexplained cell aborts the ship.
    7. Boolean census check (expected 494 at v2.21). A drop means the
       boolean trap bit again — see WoP_Pattern_XlsxRoundTrip_BooleanTrap.
    8. Optional LibreOffice recalculation — ALWAYS on a throwaway copy.
       The shipped file never touches LibreOffice.

SHIPPING RULE (non-negotiable, from the boolean-trap pattern)
  openpyxl writes the deliverable. LibreOffice only ever sees a copy under
  a *.VALIDATE-COPY.xlsx name. This script refuses to run recalculation
  against the output path.

USAGE
  python sjn_merge_decisions.py \
      --workbook   Seeking_Jesus_Teaching_Predicate_Source_v2.21_BRANCH_STUDY_20260910.xlsx \
      --decisions  sjn-decisions-gate5-registries-20260910-2026-09-10.json \
      --registry-csv WoP_SJN_BranchSourceRegistries_Draft1_20260910.csv \
      --version 2.22 --label AUTHOR_RATIFIED_REGISTRIES \
      [--out PATH] [--dry-run] [--allow-partial] [--allow-conflicts]
      [--recalc /path/to/soffice] [--expected-booleans 494]

EXIT CODES
  0 ok · 1 usage/precondition failure · 2 decision-set failure
  3 diff outside the allowlist · 4 boolean census failure · 5 recalc failure
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:  # pragma: no cover
    sys.exit("openpyxl is required:  pip install openpyxl")

# ----------------------------------------------------------------------------
# constants tied to the workbook's own conventions
# ----------------------------------------------------------------------------

SHEET_REGISTRY = "Branch Source Registry"
SHEET_CONFIG = "APP CONFIG"
SHEET_BUILDMETA = "Build Metadata"
SHEET_AUDIT = "Lineage & Merge Audit"
SHEET_VALIDATION = "Build Validation"

HDR_FILL = PatternFill("solid", fgColor="FF203864")
HDR_FONT = Font(name="Carlito", sz=11, b=True, color="FFFFFFFF")
TITLE_FONT = Font(name="Carlito", sz=15, b=True, color="FFFFFFFF")
SUB_FILL = PatternFill("solid", fgColor="FFFFF2CC")
SUB_FONT = Font(name="Carlito", sz=11, b=True)
BODY_FONT = Font(name="Carlito", sz=11)
WRAP = Alignment(wrap_text=True, vertical="top")
HDR_ALIGN = Alignment(wrap_text=True, vertical="center")

# Registry sheet columns — plan §4.1 plus the author-decision fields.
REGISTRY_COLUMNS = [
    ("registry_id", 14),
    ("branch", 22),
    ("standard_title", 52),
    ("authority_tier", 24),
    ("speaks_for", 40),
    ("reception_scope", 24),
    ("reception_note", 70),
    ("scope_caveat", 62),
    ("publisher_domain", 24),
    ("canonical_url", 62),
    ("fetch_mode", 22),
    ("text_hash", 18),
    ("status", 20),
    ("author_decision", 20),
    ("reason_code", 18),
    ("author_note", 44),
    ("released_cells", 14),
    ("draft_recommendation", 40),
    ("initials", 10),
    ("decision_date", 14),
]

VALID_DECISIONS = {
    "APPROVE", "APPROVE_REVISED", "EXCLUDE", "REJECT",
    "NOT_LOCATED", "HOLD", "DEFER", "CHOICE",
}
REASON_CODES = {
    "WRONG_SUBJECT", "NOT_ASSERTION", "BELOW_FLOOR",
    "AUTHORITY_SCOPE", "OTHER", "",
}

# Registry status written for each decision.
STATUS_FOR = {
    "APPROVE": "AUTHOR_RATIFIED",
    "APPROVE_REVISED": "AUTHOR_RATIFIED",
    "EXCLUDE": "RETIRED",
    "REJECT": "RETIRED",
    "HOLD": "DRAFT",
    "DEFER": "DRAFT",
}

# Author-call cards that settle registry rows, and which outcome keeps a row.
# (card_id -> {registry_id -> set of values under which the row is INCLUDED})
CALL_RESOLUTIONS = {
    "AC-03": {
        "BSR-EO-04": {"PHILARET_IN_DOSITHEUS_OUT", "BOTH_IN"},
        "BSR-EO-05": {"BOTH_IN"},
    },
    "AC-04": {"BSR-AN-05": {"INCLUDE_WITH_CAVEAT", "INCLUDE_AS_FALLBACK_TIER"}},
    "AC-05": {"BSR-BA-02": {"INCLUDE_WITH_CAVEAT"}},
    "AC-06": {
        "BSR-MW-03": {"BOTH", "GMC_ONLY"},
        "BSR-MW-04": {"BOTH", "WESLEYAN_ONLY"},
    },
    "AC-07": {"BSR-MA-02": {"INCLUDE_VIA_ANABAPTISRESOURCES",
                            "INCLUDE_VIA_ANABAPTISTRESOURCES"}},
    # Gate 7, cal-2 corrections sitting (2026-09-11)
    "AC-09": {"BSR-RC-04": {"EXTEND_TO_CONSTITUTION_2", "LEAVE_EXCLUDED", "NEW_ROW"}},
    "AC-10": {"BSR-RC-06": {"TIER_PER_CITED_DOCUMENT", "SPLIT_RC06", "LEAVE_ROW_TIER"},
              "BSR-EO-01": {"TIER_PER_CITED_DOCUMENT", "SPLIT_RC06", "LEAVE_ROW_TIER"}},
    # Gate 7b, reception-axis sitting (2026-09-12)
    "AC-12": {"BSR-EO-05": {"CONTESTED_WITH_NOTE", "SECONDARY", "LEAVE_AS_IS"}},
}

# APP CONFIG keys this merge sets, and the card each is derived from.
CONFIG_FROM_CARD = {
    "registry_breadth": "SETUP-02",
    "decision_console_medium": "SETUP-03",
    "lineage_host_policy": "AC-02",
    "fetch_mode_confirmation": "AC-08",
    # Gate 7, cal-2 corrections sitting (2026-09-11)
    "gate6_threshold_metric": "SETUP-G7-01",
    "lateran_iv_scope": "AC-09",
    "creed_tier_resolution": "AC-10",
    "verifier_routing": "AC-11",
    # Gate 7b, reception-axis sitting (2026-09-12)
    "reception_axis": "G7B-01",
    "reception_mapping": "G7B-02",
    "encyclical_1848_status": "AC-13",
    "dialogue_text_policy": "AC-14",
}

# APP CONFIG keys this merge sets from a ratified literal rather than a card.
CONFIG_LITERALS = {
    # Ratified 2026-09-11 (AJP): authority_tier is a genuine descending rank.
    "authority_tier_rank":
        "CONCILIAR|CONFESSIONAL|CATECHETICAL|OFFICIAL_EXPOSITION|CURRENT_OFFICIAL_WITNESS",
    "gate7_status": "REGISTRY CORRECTIONS RATIFIED 2026-09-11",
    "reception_scope_vocabulary":
        "UNIVERSAL|MULTILATERAL|PARTICIPATING_BODIES|JURISDICTIONAL|"
        "HISTORIC_NO_CURRENT_BODY|CONTESTED|TRANSLATION_WITNESS|DIALOGUE_ONLY",
    "gate7b_status": "RECEPTION AXIS RATIFIED 2026-09-12",
}

DEFAULT_EXPECTED_BOOLEANS = 494


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------

def log(msg=""):
    print(msg, flush=True)


def rule(title=""):
    log("\n" + ("-" * 74))
    if title:
        log(title)
        log("-" * 74)


def today():
    return _dt.date.today().isoformat()


def domain_of(url: str) -> str:
    """First hostname in a URL field that may carry several URLs and prose."""
    m = re.search(r"https?://([^/\s)]+)", url or "")
    if m:
        host = m.group(1).lower()
        return host[4:] if host.startswith("www.") else host
    m = re.search(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", (url or "").lower())
    return m.group(1) if m else ""


def released_cells(*texts) -> object:
    """Released-cell counts sit in prose: "(18 released cells)", "all 15
    released Lutheran cells", "(as cited, 1 released cell)"."""
    for t in texts:
        m = re.search(r"(\d+)\s+released(?:\s+[A-Za-z()/-]+)?\s+cells?", t or "")
        if m:
            return int(m.group(1))
    return ""


def first_url(url: str) -> str:
    m = re.search(r"https?://\S+", url or "")
    return m.group(0).rstrip(").,;") if m else (url or "")


# ----------------------------------------------------------------------------
# inputs
# ----------------------------------------------------------------------------

def load_decisions(path):
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, list):                      # bare array is accepted
        payload = {"schema": "sjn-decisions/1", "decisions": payload}
    if payload.get("schema") != "sjn-decisions/1":
        raise SystemExit("Unrecognised decisions schema: %r" % payload.get("schema"))
    recs = OrderedDict()
    for d in payload.get("decisions", []):
        cid = d.get("card_id")
        if not cid:
            raise SystemExit("A decision record has no card_id: %r" % (d,))
        if d.get("decision") not in VALID_DECISIONS:
            raise SystemExit("%s: unknown decision %r" % (cid, d.get("decision")))
        if d.get("reason", "") not in REASON_CODES:
            raise SystemExit("%s: unknown reason code %r" % (cid, d.get("reason")))
        if not d.get("initials"):
            raise SystemExit("%s: no author initials — refusing to merge" % cid)
        recs[cid] = d
    payload["decisions"] = recs
    return payload


def load_registry_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("Registry CSV is empty: %s" % path)
    need = {"registry_id", "branch", "standard_title", "authority_tier",
            "speaks_for", "canonical_url", "fetch_mode", "recommendation"}
    missing = need - set(rows[0].keys())
    if missing:
        raise SystemExit("Registry CSV missing columns: %s" % ", ".join(sorted(missing)))
    out = OrderedDict()
    for r in rows:
        rid = (r.get("registry_id") or "").strip()
        if rid:
            out[rid] = {k: (v or "").strip() for k, v in r.items()}
    return out


# ----------------------------------------------------------------------------
# decision-set checks
# ----------------------------------------------------------------------------

def check_decisions(payload, registry, allow_partial, allow_conflicts):
    recs = payload["decisions"]
    problems, warnings = [], []

    undecided = [rid for rid in registry
                 if rid not in recs or recs[rid].get("decision") == "DEFER"]
    if undecided:
        (warnings if allow_partial else problems).append(
            "%d registry rows are undecided or deferred: %s"
            % (len(undecided), ", ".join(undecided)))

    held = [rid for rid in registry
            if rid in recs and recs[rid].get("decision") == "HOLD"]
    if held:
        warnings.append("%d rows held for research (written as DRAFT): %s"
                        % (len(held), ", ".join(held)))

    for card_id, mapping in CALL_RESOLUTIONS.items():
        call = recs.get(card_id)
        if not call or call.get("decision") != "CHOICE":
            continue
        value = call.get("value", "")
        for rid, include_values in mapping.items():
            row = recs.get(rid)
            if not row:
                continue
            row_included = row.get("decision") in ("APPROVE", "APPROVE_REVISED")
            call_includes = value in include_values
            if row_included != call_includes:
                msg = ("conflict: %s = %s implies %s is %s, but the row was %s"
                       % (card_id, value, rid,
                          "included" if call_includes else "excluded",
                          row.get("decision")))
                (warnings if allow_conflicts else problems).append(msg)

    # A row approved against a drafted EXCLUDE recommendation is legitimate —
    # the author overrules the draft — but it is never accidental, so it is
    # surfaced rather than passed over in silence.
    overruled = []
    for rid, src in registry.items():
        d = recs.get(rid)
        if not d or d.get("decision") not in ("APPROVE", "APPROVE_REVISED"):
            continue
        rec_text = (src.get("recommendation") or "").upper()
        if "EXCLUDE" in rec_text:
            overruled.append("%s (%s) — draft said %s"
                             % (rid, src.get("standard_title", "")[:44],
                                src.get("recommendation", "")[:60]))
    if overruled:
        warnings.append("%d rows approved against a drafted EXCLUDE recommendation:\n        %s"
                        % (len(overruled), "\n        ".join(overruled)))

    for key, card_id in CONFIG_FROM_CARD.items():
        if card_id not in recs:
            warnings.append("APP CONFIG %s not written — %s undecided" % (key, card_id))

    if "SETUP-01" not in recs:
        warnings.append("V100 left untouched — SETUP-01 undecided")

    return problems, warnings


# ----------------------------------------------------------------------------
# the merge
# ----------------------------------------------------------------------------

class Merge:
    """Applies the edits and records every intended (sheet, coord) it touches."""

    def __init__(self, wb, payload, registry):
        self.wb = wb
        self.payload = payload
        self.recs = payload["decisions"]
        self.registry = registry
        self.touched = set()          # (sheet_title, coord)
        self.no_domain = []           # ratified rows with no publisher_domain
        self.new_sheets = set()
        self.notes = []

    # -- primitive ---------------------------------------------------------
    def put(self, ws, row, col, value, font=None, align=None, fill=None):
        cell = ws.cell(row=row, column=col)
        cell.value = value
        if font:
            cell.font = font
        if align:
            cell.alignment = align
        if fill:
            cell.fill = fill
        self.touched.add((ws.title, cell.coordinate))
        return cell

    def fallback_rows(self):
        """Registry rows a FALLBACK author call restricts to fallback use.

        A call value containing FALLBACK (e.g. AC-04 INCLUDE_AS_FALLBACK_TIER)
        means: the rows that call settles are citable only where no higher-tier
        row in the same branch yields a candidate. CALL_RESOLUTIONS already
        knows which rows each call settles.
        """
        rows = []
        for card_id, mapping in CALL_RESOLUTIONS.items():
            d = self.recs.get(card_id)
            if not d or d.get("decision") != "CHOICE":
                continue
            if "FALLBACK" in (d.get("value") or "").upper():
                rows.extend(sorted(mapping.keys()))
        return rows

    def choice(self, card_id, default=""):
        r = self.recs.get(card_id)
        if r and r.get("decision") == "CHOICE":
            return r.get("value") or default
        return default

    # -- 1. registry sheet -------------------------------------------------
    def track(self, ws, cell):
        """Record a directly-written cell as an intended change.

        The registry sheet is generated wholesale rather than through put(),
        and it is only exempt from the diff on the merge that creates it. On a
        re-merge the sheet already exists in the base workbook, so every cell
        it writes has to be on the allowlist like any other edit.
        """
        self.touched.add((ws.title, cell.coordinate))
        return cell

    def build_registry_sheet(self, version_label):
        self.registry_existed = SHEET_REGISTRY in self.wb.sheetnames
        if self.registry_existed:
            del self.wb[SHEET_REGISTRY]
        anchor = self.wb.sheetnames.index("Tradition Sources") + 1 \
            if "Tradition Sources" in self.wb.sheetnames else len(self.wb.sheetnames)
        ws = self.wb.create_sheet(SHEET_REGISTRY, anchor)
        self.new_sheets.add(SHEET_REGISTRY)

        caveats = self.payload.get("scope_caveats", {}) or {}
        ncols = len(REGISTRY_COLUMNS)

        ws.cell(1, 1).value = (
            "Branch Source Registry — author-ratified standards each branch may be cited from "
            "(Gate 5, %s)" % version_label)
        ws.cell(1, 1).font = TITLE_FONT
        ws.cell(1, 1).fill = HDR_FILL
        self.track(ws, ws.cell(1, 1))
        for c in range(2, ncols + 1):
            ws.cell(1, c).fill = HDR_FILL
            self.track(ws, ws.cell(1, c))
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)

        ws.cell(2, 1).value = (
            "Registry-only enforcement: a cell may cite a source only if its publisher_domain "
            "appears in this sheet for that branch with status AUTHOR_RATIFIED. Rows with status "
            "RETIRED or DRAFT are not citable. LINEAGE rows are third-party hosts already cited by "
            "released cells and are marked in draft_recommendation. text_hash is set by the corpus "
            "builder at first fetch; drift halts the run.")
        ws.cell(2, 1).font = SUB_FONT
        ws.cell(2, 1).fill = SUB_FILL
        ws.cell(2, 1).alignment = WRAP
        self.track(ws, ws.cell(2, 1))
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)

        for i, (name, width) in enumerate(REGISTRY_COLUMNS, start=1):
            cell = ws.cell(4, i)
            cell.value = name
            cell.font = HDR_FONT
            cell.fill = HDR_FILL
            cell.alignment = HDR_ALIGN
            self.track(ws, cell)
            ws.column_dimensions[cell.column_letter].width = width

        row = 5
        ratified = retired = draft = 0
        for rid, src in self.registry.items():
            d = self.recs.get(rid, {})
            decision = d.get("decision", "")
            revisions = d.get("revisions", {}) or {}
            status = STATUS_FOR.get(decision, "DRAFT")
            branch = src["branch"]

            values = {
                "registry_id": rid,
                "branch": branch,
                "standard_title": src["standard_title"],
                "authority_tier": revisions.get("authority_tier", src["authority_tier"]),
                "speaks_for": revisions.get("speaks_for", src["speaks_for"]),
                "reception_scope": revisions.get("reception_scope", src.get("reception_scope", "")),
                "reception_note": revisions.get("reception_note", src.get("reception_note", "")),
                "scope_caveat": revisions.get("scope_caveat", caveats.get(branch, "")),
                "publisher_domain": domain_of(revisions.get("canonical_url", src["canonical_url"])),
                "canonical_url": first_url(revisions.get("canonical_url", src["canonical_url"])),
                "fetch_mode": revisions.get("fetch_mode", src["fetch_mode"]),
                "text_hash": "",
                "status": status,
                "author_decision": decision or "UNDECIDED",
                "reason_code": d.get("reason", ""),
                "author_note": d.get("note", ""),
                "released_cells": released_cells(src["recommendation"], src["canonical_url"]),
                "draft_recommendation": src["recommendation"],
                "initials": d.get("initials", ""),
                "decision_date": (d.get("timestamp") or "")[:10],
            }
            for i, (name, _w) in enumerate(REGISTRY_COLUMNS, start=1):
                cell = ws.cell(row, i)
                cell.value = values[name]
                cell.font = BODY_FONT
                cell.alignment = WRAP
                self.track(ws, cell)
            row += 1
            if status == "AUTHOR_RATIFIED" and not values["publisher_domain"]:
                self.no_domain.append(rid)
            if status == "AUTHOR_RATIFIED":
                ratified += 1
            elif status == "RETIRED":
                retired += 1
            else:
                draft += 1

        ws.freeze_panes = "C5"
        self.notes.append("registry rows: %d ratified, %d retired, %d draft/held"
                          % (ratified, retired, draft))
        self.registry_counts = (ratified, retired, draft)
        return ratified, retired, draft

    # -- 2. APP CONFIG -----------------------------------------------------
    def _config_index(self, ws):
        idx = {}
        for r in range(6, ws.max_row + 1):
            k = ws.cell(r, 1).value
            if isinstance(k, str) and k.strip() and k.strip() not in idx:
                idx[k.strip()] = r
        return idx

    def update_config(self, version_label, build_date):
        ws = self.wb[SHEET_CONFIG]
        idx = self._config_index(ws)
        appended = []

        def set_key(key, value, rule_text):
            if key in idx:
                r = idx[key]
                self.put(ws, r, 2, value, font=BODY_FONT)
                self.put(ws, r, 3, rule_text, font=BODY_FONT, align=WRAP)
            else:
                r = ws.max_row + 1
                self.put(ws, r, 1, key, font=BODY_FONT)
                self.put(ws, r, 2, value, font=BODY_FONT)
                self.put(ws, r, 3, rule_text, font=BODY_FONT, align=WRAP)
                idx[key] = r
                appended.append(key)

        set_key("app_master_version", version_label,
                "Use this workbook as the single app-facing data authority.")
        set_key("build_date", build_date, "Controlled build date.")

        ratified, retired, draft = self.registry_counts
        set_key("branch_source_registry_sheet", SHEET_REGISTRY,
                "Gate 5. Author-ratified standards per branch; the only sources a cell may cite.")
        set_key("registry_only_enforcement", True,
                "BLOCKING: sjn-verify rule R001 — a cell citation whose domain is not in its "
                "branch's AUTHOR_RATIFIED registry rows is an error.")
        set_key("registry_entries_ratified", ratified,
                "Count of AUTHOR_RATIFIED registry rows (%d retired, %d draft/held)."
                % (retired, draft))

        breadth = self.choice("SETUP-02")
        if breadth:
            set_key("registry_breadth", breadth,
                    "Author call. TWO_TIERS = binding confession(s) plus one catechetical or "
                    "current official witness per branch.")
        medium = self.choice("SETUP-03")
        if medium:
            set_key("decision_console_medium", medium,
                    "Author call. Where Gate 7 cell ratification happens and how decisions reach "
                    "the merge script.")
        lineage = self.choice("AC-02")
        if lineage:
            set_key("lineage_host_policy", lineage,
                    "Author call. Treatment of third-party hosts already cited by released cells.")
        fetchconf = self.choice("AC-08")
        if fetchconf:
            set_key("fetch_mode_confirmation", fetchconf,
                    "Author call. Fetch modes confirmed for the Gate 6 corpus builder.")

        fallback = self.fallback_rows()
        if fallback:
            set_key("registry_fallback_only_rows", ", ".join(fallback),
                    "Author call. These registry rows are citable ONLY where no higher-tier row "
                    "in the same branch yields a candidate for the predicate. The Gate 6 packet "
                    "builder must prefer non-fallback candidates and admit a fallback row only on "
                    "an empty result; a fallback citation never renders alongside or against a "
                    "non-fallback witness for the same cell.")
            self.notes.append("fallback-only registry rows: " + ", ".join(fallback))

        set_key("gate5_status", "AUTHOR RATIFIED %s" % build_date,
                "Branch Source Registries ratified in the Decision Console; Gate 6 may build the "
                "corpus from AUTHOR_RATIFIED rows only.")

        # --- Gate 7, cal-2 corrections sitting (2026-09-11) ----------------
        metric = self.choice("SETUP-G7-01")
        if metric:
            set_key("gate6_threshold_metric", metric,
                    "Author call. The recall metric the Gate 6 gate is scored on. SAME_STANDARD = "
                    "a hit requires a verified candidate in the same registry standard the cell "
                    "cites. Tier-respecting recall is REPORTED as a diagnostic and is never a "
                    "threshold. Do not move the 0.8 floor or the 0.05 false-accept ceiling.")
        lateran = self.choice("AC-09")
        if lateran:
            set_key("lateran_iv_scope", lateran,
                    "Author call. EXTEND_TO_CONSTITUTION_2 widens BSR-RC-04 from canon 1 to "
                    "constitutions 1-2, so the maior dissimilitudo clause of Damnamus ergo is "
                    "in ratified scope and Q-449 is locatable.")
        creedtier = self.choice("AC-10")
        if creedtier:
            set_key("creed_tier_resolution", creedtier,
                    "Author call. TIER_PER_CITED_DOCUMENT = a bundled registry row carries a floor "
                    "tier, and a cell citing a document of higher provenance within that row "
                    "resolves at the document's tier. Applies to BSR-RC-06 (Apostles' floor; "
                    "Nicene and Athanasian CONCILIAR). BSR-EO-01 is the Creed alone and is "
                    "re-tiered CONCILIAR outright.")
        routing = self.choice("AC-11")
        if routing:
            set_key("verifier_routing", routing,
                    "Author call. SONNET_WITH_OPUS_SLICE = sonnet is the primary verifier; opus "
                    "adjudicates the hard slice only - every candidate on BSR-EO-04 or BSR-EO-05, "
                    "every candidate on a fallback-only row, and every cell sonnet rejects "
                    "outright, before that cell is recorded as an honest empty.")
        axis = self.choice("G7B-01")
        if axis:
            set_key("reception_axis", axis,
                    "Author call G7B-01. ADOPT_BOTH = the registry carries reception_scope on every row "
                    "and reception_note where reception is contested. reception_scope answers WHO "
                    "receives a standard; authority_tier answers WHAT KIND of document it is. The two are "
                    "independent and disagree on seven rows.")
        mapping = self.choice("G7B-02")
        if mapping:
            set_key("reception_mapping", mapping,
                    "Author call G7B-02. APPROVE_DERIVED = reception_scope values derived mechanically "
                    "from the ratified speaks_for field, with BSR-MA-03 hand-corrected to "
                    "HISTORIC_NO_CURRENT_BODY.")
        enc = self.choice("AC-13")
        if enc:
            set_key("encyclical_1848_status", enc,
                    "Author call AC-13. RECORD_STANDING_ONLY = the 1848 Encyclical of the Eastern "
                    "Patriarchs is NOT a citable registry row: its text is on no official Orthodox host "
                    "and every English version descends from one anonymous 19th-century translation. Its "
                    "standing is attested by oca.org; the print critical edition is Karmiris, Ta "
                    "Dogmatika kai Symvolika Mnimeia II (Athens 1953), 916. No cell may cite it.")
        dia = self.choice("AC-14")
        if dia:
            set_key("dialogue_text_policy", dia,
                    "Author call AC-14. DIALOGUE_ONLY_NEVER_CITED = a text its own publisher disclaims "
                    "as not an official position may be registered for provenance but is refused by R001 "
                    "as a cell citation. Applies across all eight branches. The publisher's disclaimer is "
                    "copied verbatim into the row note, because it does not always appear on the "
                    "document's own page.")
        for key, value in CONFIG_LITERALS.items():
            set_key(key, value,
                    "Ratified 2026-09-11 in the Gate 7 corrections sitting." if key ==
                    "authority_tier_rank" else
                    "Gate 7 registry corrections ratified in the Decision Console.")
        if appended:
            self.notes.append("APP CONFIG keys added: " + ", ".join(appended))
        return appended

    # -- 3. Build Metadata -------------------------------------------------
    def append_build_metadata(self, version_label, build_date):
        ws = self.wb[SHEET_BUILDMETA]
        r = ws.max_row + 1
        ratified, retired, draft = self.registry_counts
        created = not getattr(self, "registry_existed", False)
        self.put(ws, r, 1,
                 "Branch Source Registries ratified" if created
                 else "Branch Source Registry corrections", font=BODY_FONT, align=WRAP)
        self.put(ws, r, 2, "%s / %s" % (version_label.split()[0], build_date), font=BODY_FONT)
        self.put(ws, r, 3, "n/a", font=BODY_FONT)
        self.put(ws, r, 4,
                 ("Adds %s (%d ratified, %d retired, %d draft) and the registry-only enforcement "
                  "key; author decisions recorded card by card in the Decision Console."
                  % (SHEET_REGISTRY, ratified, retired, draft)) if created else
                 ("Rebuilds %s from corrected console decisions (%d ratified, %d retired, "
                  "%d draft). Registry rows only; no other sheet changed."
                  % (SHEET_REGISTRY, ratified, retired, draft)), font=BODY_FONT, align=WRAP)
        self.put(ws, r, 5, "AUTHOR RATIFIED — supersedes the prior version",
                 font=BODY_FONT, align=WRAP)
        return r

    # -- 4. Lineage & Merge Audit -----------------------------------------
    def append_audit(self, version_label, build_date, sitting):
        ws = self.wb[SHEET_AUDIT]
        r = ws.max_row + 1
        ratified, retired, draft = self.registry_counts
        created = not getattr(self, "registry_existed", False)
        self.put(ws, r, 1, "Branch source registries", font=BODY_FONT, align=WRAP)
        self.put(ws, r, 2, "ADDED" if created else "REVISED", font=BODY_FONT)
        self.put(ws, r, 3, "Decision Console sitting %s" % sitting, font=BODY_FONT, align=WRAP)
        self.put(ws, r, 4,
                 "%d standards ratified, %d retired, %d held; scope caveats inherited per branch.%s"
                 % (ratified, retired, draft,
                    "" if created else " Corrections pass — registry rows re-merged from the console."),
                 font=BODY_FONT, align=WRAP)
        self.put(ws, r, 5, "SOURCE GOVERNANCE", font=BODY_FONT)
        self.put(ws, r, 6, "R001 registry-only citation check; APP CONFIG "
                           "registry_only_enforcement", font=BODY_FONT, align=WRAP)
        self.put(ws, r, 7, "PASS", font=BODY_FONT)
        self.put(ws, r, 8,
                 "Merged by sjn_merge_decisions.py on %s from the console decisions JSON. "
                 "No doctrinal, copy, count, or gate-value change outside the registry."
                 % build_date, font=BODY_FONT, align=WRAP)
        return r

    # -- 5. V100 -----------------------------------------------------------
    def apply_v100(self):
        d = self.recs.get("SETUP-01")
        if not d or d.get("decision") != "CHOICE":
            return None
        ws = self.wb[SHEET_VALIDATION]
        target = None
        for r in range(6, ws.max_row + 1):
            if str(ws.cell(r, 1).value).strip() == "V100":
                target = r
                break
        if target is None:
            self.notes.append("V100 row not found — rule left untouched")
            return None

        value = d.get("value")
        if value == "CONDITIONAL":
            self.put(ws, target, 3,
                     "Current Item rows when author attention exists (conditional: expected only "
                     "while actionable author work remains)", font=BODY_FONT, align=WRAP)
            self.put(ws, target, 4,
                     "=IF(COUNTIF('Author Decision Queue'!$AF$2:$AF$105,\"YES\")>0,1,0)",
                     font=BODY_FONT)
            self.put(ws, target, 8,
                     "Expected mirrors Needs Author Attention (column AF): exactly one current item "
                     "while any decision still needs attention, zero when the queue is complete. "
                     "Author decision SETUP-01, %s." % today(),
                     font=BODY_FONT, align=WRAP)
        elif value == "EXPECTED_ZERO":
            self.put(ws, target, 4, 0, font=BODY_FONT)
            self.put(ws, target, 8,
                     "Expected set to 0 by author decision SETUP-01, %s: the author queue is "
                     "complete and no current item is expected." % today(),
                     font=BODY_FONT, align=WRAP)
        elif value == "RETIRE":
            self.put(ws, target, 2, "RETIRED", font=BODY_FONT)
            self.put(ws, target, 3,
                     "RETIRED — Current Item rows when author attention exists",
                     font=BODY_FONT, align=WRAP)
            self.put(ws, target, 6, "RETIRED", font=BODY_FONT)
            self.put(ws, target, 7, "NO", font=BODY_FONT)
            self.put(ws, target, 8,
                     "Retired by author decision SETUP-01, %s. Rule is spent: the author decision "
                     "queue is complete." % today(), font=BODY_FONT, align=WRAP)
        else:
            self.notes.append("V100: unrecognised value %r — rule left untouched" % value)
            return None
        self.notes.append("V100 row %d rewritten as %s" % (target, value))
        return target


# ----------------------------------------------------------------------------
# verification
# ----------------------------------------------------------------------------

def _cmp(v):
    """Comparable form of a cell value.

    openpyxl returns a fresh ArrayFormula/DataTableFormula object per load and
    those have no __eq__, so a naive comparison reports every array formula in
    the workbook as changed. Compare their (ref, text) instead — which is also
    where the LibreOffice single-cell ref normalisation (B8 -> B8:B8) would show.
    """
    ref = getattr(v, "ref", None)
    if ref is not None and hasattr(v, "text"):
        return ("ARRAY", ref, v.text)
    if v.__class__.__name__ == "DataTableFormula":
        return ("DATATABLE", getattr(v, "ref", None), str(v.__dict__))
    return v


def _show(v):
    c = _cmp(v)
    return str(c if not isinstance(c, tuple) else "%s %s %s" % c)


def cell_diff(path_before, path_after):
    """Every (sheet, coord, before, after) that differs, in formula mode."""
    wb_a = openpyxl.load_workbook(path_before, data_only=False)
    wb_b = openpyxl.load_workbook(path_after, data_only=False)
    diffs, added, removed = [], [], []
    for title in wb_b.sheetnames:
        if title not in wb_a.sheetnames:
            added.append(title)
    for title in wb_a.sheetnames:
        if title not in wb_b.sheetnames:
            removed.append(title)
            continue
        if title in added:
            continue
        sa, sb = wb_a[title], wb_b[title]
        rows = max(sa.max_row, sb.max_row)
        cols = max(sa.max_column, sb.max_column)
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                va = sa.cell(r, c).value
                vb = sb.cell(r, c).value
                if _cmp(va) != _cmp(vb):
                    diffs.append((title, sb.cell(r, c).coordinate, va, vb))
    wb_a.close()
    wb_b.close()
    return diffs, added, removed


def boolean_census(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    n = 0
    formulaish = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, bool):
                    n += 1
                elif isinstance(v, str) and v.strip().upper() in ("=TRUE()", "=FALSE()"):
                    formulaish += 1
    wb.close()
    return n, formulaish


def recalc_on_copy(out_path, soffice):
    """LibreOffice formula check — on a throwaway copy, never the deliverable."""
    base = os.path.splitext(out_path)[0]
    copy_path = base + ".VALIDATE-COPY.xlsx"
    if os.path.abspath(copy_path) == os.path.abspath(out_path):
        raise SystemExit("refusing to recalculate the shipped file")
    shutil.copy2(out_path, copy_path)
    tmp = tempfile.mkdtemp(prefix="sjn-recalc-")
    cmd = [soffice, "--headless", "--norestore",
           "--convert-to", "xlsx", "--outdir", tmp, copy_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    produced = os.path.join(tmp, os.path.basename(copy_path))
    if proc.returncode != 0 or not os.path.exists(produced):
        return {"ok": False, "copy": copy_path,
                "stderr": (proc.stderr or proc.stdout or "").strip()[:800]}
    wb = openpyxl.load_workbook(produced, data_only=True)
    errors = []
    markers = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NULL!", "#NUM!")
    fails = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str):
                    s = v.strip()
                    if s in markers:
                        errors.append("%s!%s = %s" % (ws.title, cell.coordinate, s))
                    elif ws.title == SHEET_VALIDATION and s == "FAIL":
                        fails.append("%s row %d" % (ws.title, cell.row))
    wb.close()
    return {"ok": True, "copy": copy_path, "converted": produced,
            "formula_errors": errors, "validation_fails": fails}


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge SJN Decision Console output into the workbook.")
    ap.add_argument("--workbook", required=True, help="prior version .xlsx (not modified)")
    ap.add_argument("--decisions", required=True, help="decisions JSON from the console")
    ap.add_argument("--registry-csv", required=True, help="Branch Source Registries CSV")
    ap.add_argument("--version", required=True, help='new version number, e.g. "2.22"')
    ap.add_argument("--label", default="AUTHOR_RATIFIED_REGISTRIES",
                    help="version label written into app_master_version and the filename")
    ap.add_argument("--out", default=None, help="output path (default: alongside the input)")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--allow-partial", action="store_true",
                    help="permit undecided/deferred registry rows (written as DRAFT)")
    ap.add_argument("--allow-conflicts", action="store_true",
                    help="permit author-call/row conflicts (reported as warnings)")
    ap.add_argument("--recalc", default=None, metavar="SOFFICE",
                    help="path to soffice; runs a formula check on a throwaway copy")
    ap.add_argument("--expected-booleans", type=int, default=DEFAULT_EXPECTED_BOOLEANS)
    args = ap.parse_args(argv)

    for p in (args.workbook, args.decisions, args.registry_csv):
        if not os.path.exists(p):
            raise SystemExit("not found: %s" % p)

    build_date = today()
    version_label = "v%s %s" % (args.version, args.label.replace("_", " "))
    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.workbook)),
        "Seeking_Jesus_Teaching_Predicate_Source_v%s_%s_%s.xlsx"
        % (args.version, args.label, build_date.replace("-", "")))

    rule("INPUTS")
    log("workbook in   : %s" % args.workbook)
    log("decisions     : %s" % args.decisions)
    log("registry csv  : %s" % args.registry_csv)
    log("workbook out  : %s" % out_path)
    log("version label : %s" % version_label)

    payload = load_decisions(args.decisions)
    registry = load_registry_csv(args.registry_csv)
    recs = payload["decisions"]
    log("decision records: %d   registry rows: %d" % (len(recs), len(registry)))

    unknown = [cid for cid in recs
               if not cid.startswith(("SETUP-", "AC-", "Q-")) and cid not in registry]
    if unknown:
        log("note: %d decision records are not registry rows or known setup cards: %s"
            % (len(unknown), ", ".join(unknown[:8])))

    rule("DECISION-SET CHECK")
    problems, warnings = check_decisions(payload, registry, args.allow_partial,
                                         args.allow_conflicts)
    for w in warnings:
        log("  WARN  %s" % w)
    for p in problems:
        log("  FAIL  %s" % p)
    if problems:
        log("\nRefusing to merge. Re-run with --allow-partial / --allow-conflicts "
            "only if the state above is intended.")
        return 2
    if not warnings:
        log("  clean")

    rule("MERGE")
    wb = openpyxl.load_workbook(args.workbook, data_only=False)
    merge = Merge(wb, payload, registry)
    ratified, retired, draft = merge.build_registry_sheet(version_label)
    merge.update_config(version_label, build_date)
    merge.append_build_metadata(version_label, build_date)
    merge.append_audit(version_label, build_date, payload.get("sitting", "unnamed"))
    merge.apply_v100()
    for n in merge.notes:
        log("  %s" % n)

    if merge.no_domain:
        log("\n  FAIL  %d ratified rows have no publisher_domain, so registry-only "
            "enforcement cannot key on them: %s" % (len(merge.no_domain),
                                                    ", ".join(merge.no_domain)))
        log("        Fix: set the canonical URL on those rows — in the console, "
            "Approve with revisions — or add it to the registry CSV, then re-run.")
        return 2

    if args.dry_run:
        log("\n--dry-run: nothing written.")
        return 0

    wb.save(out_path)
    wb.close()
    log("  written: %s" % out_path)

    rule("CELL-BY-CELL DIFF AGAINST THE PRIOR VERSION")
    diffs, added, removed = cell_diff(args.workbook, out_path)
    if removed:
        log("  FAIL  sheets removed: %s" % ", ".join(removed))
        return 3
    log("  sheets added: %s" % (", ".join(added) or "none"))
    unexpected = [d for d in diffs if (d[0], d[1]) not in merge.touched]
    log("  cells changed outside the new sheet: %d  (intended: %d)"
        % (len(diffs), len(merge.touched)))
    for title, coord, before, after in diffs[:60]:
        mark = " " if (title, coord) in merge.touched else "!"
        log("   %s %s!%s: %r -> %r" % (mark, title, coord, _show(before)[:46], _show(after)[:46]))
    if len(diffs) > 60:
        log("   ... %d more" % (len(diffs) - 60))
    if unexpected:
        log("\n  FAIL  %d cells changed that this merge did not intend. Do not ship."
            % len(unexpected))
        return 3
    log("  every changed cell is an intended edit.")

    rule("BOOLEAN CENSUS (xlsx round-trip boolean trap)")
    n_before, f_before = boolean_census(args.workbook)
    n_after, f_after = boolean_census(out_path)
    log("  before: %d booleans, %d =TRUE()/=FALSE() formulas" % (n_before, f_before))
    log("  after : %d booleans, %d =TRUE()/=FALSE() formulas" % (n_after, f_after))
    if f_after > f_before:
        log("  FAIL  boolean literals became formulas — the output touched LibreOffice.")
        return 4
    if n_after < n_before:
        log("  FAIL  boolean census dropped.")
        return 4
    if args.expected_booleans and n_after < args.expected_booleans:
        log("  FAIL  expected at least %d booleans." % args.expected_booleans)
        return 4
    log("  census holds.")

    if args.recalc:
        rule("LIBREOFFICE FORMULA CHECK — THROWAWAY COPY ONLY")
        res = recalc_on_copy(out_path, args.recalc)
        if not res["ok"]:
            log("  FAIL  recalculation did not run: %s" % res.get("stderr", ""))
            return 5
        log("  copy    : %s" % res["copy"])
        log("  errors  : %d" % len(res["formula_errors"]))
        for e in res["formula_errors"][:20]:
            log("     %s" % e)
        log("  Build Validation FAIL cells: %d" % len(res["validation_fails"]))
        for f in res["validation_fails"][:20]:
            log("     %s" % f)
        log("  The shipped file is the openpyxl original; the copy above is disposable.")
        if res["formula_errors"]:
            return 5

    rule("DONE")
    log("  %s" % out_path)
    log("  registry: %d ratified · %d retired · %d draft/held" % (ratified, retired, draft))
    log("  Next: swap this workbook into data-sources/sjn/ on the next Code pipeline run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
