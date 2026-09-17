"""Author rulings the harness applies in memory until the workbook carries them (Gate 6 sessions 6 and 7).

The rulings live in data-sources/sjn/recovery-runs/author-rulings-pending-workbook.json — committed, so every run.py /
reverify.py / truepos.py start reads the same rulings and the Eastern Orthodox launch cannot run without them. Nothing
here writes to the workbook. Each ruling says which workbook change supersedes it; when the workbook already holds that
change it is read from the workbook and checked against the ruling (a disagreement fails loudly).

  R6-1  required_subject for Lord / Life-giving / Judge / Savior / Not made admits the Son or the Spirit AS DIVINE
  R6-2  the hedged-PARTIAL floor rule; the three refused Baptist cells
  R6-3  BSR-EO-03 RETIRED (HOST_RETIRED)
  R6-4  one text, one slot: the textual guard lives in allocation.py; declared same-text rows (different wording) here

Session 7 (2026-09-16):

  R6-5  BSR-EO-01 re-typed as the Hopko row it is (registry_overrides); EO-01 and EO-02 are one work, one observation
  R6-6  the adoption field (adoption_status / adoption_act / adoption_body_scope / adoption_verified), UNVERIFIED fails closed
  R6-7  compound Spirit predication: the cited phrase must itself carry the Spirit's name and the predicate
  R6-8  passive agency: an ACTION/ATTRIBUTE class per Spirit family; only RNR-H35 (ATTRIBUTE) is ratified, the rest fail closed
  R6-9  unadopted or unverified exposition resolves to OFFICIAL_EXPOSITION, with a display qualifier
  R6-10 phrase-level resolution reaches dogmatic definitions (horoi) registered as texts in the same branch
  R6-11 verifier gate6-v1.4; the pending inference line becomes gate6-v1.5
  R6-12 Q-290 stays PUBLIC-CERTIFIED, flagged REVIEW_AT_EO_PACKET with its single-source disclosure

Session 8 (2026-09-16, second set):

  R6-13 verifier gate6-v1.5 (v1.4 minus the JOINT PREDICATION doxology sentence), JOINT PREDICATION and AGENCY scoped to
        Spirit families; the replicate measurement rule; the inference line becomes gate6-v1.6
  R6-14 all seven Spirit-family agency tags ratified (H27 = ATTRIBUTE); read from spirit-family-agency-tags.json
  R6-15 highest-tier precedence among matching registered texts; EO-09's eligibility as a creed text awaits the author
  R6-16 the CATECHETICAL-only fail-closed boundary ratified; adoption proposals verified in Cowork; packet rebuild held

Session 9 (2026-09-16, third and fourth sets):

  R6-17 TP-049's fixture phrase replaced, IF an asserting sentence stands verbatim in its chunk — condition NOT met; no tp-5
  R6-18 THE PHRASE CARRIES THE ASSERTION: verifier gate6-v1.6 + the code guard on asserted_outside_formula = Y (refused_by
        R6-18); the inference line becomes gate6-v1.7
  R6-19 BSR-EO-09 is a registered creed text at its own CONFESSIONAL tier (EO blocker (e) discharged)
  R6-20 an item triggering a stop condition gets 5 replicates per version before the stop holds
  R6-21 RATIFIED: the session 7 phrase floor (registry.CREED_PHRASE_MIN_WORDS = 3 / CREED_PHRASE_MIN_CHARS = 12)
  R6-22 RATIFIED: a CATECHETICAL row is never a registered creed text (registry.registered_creed_texts)
  R6-23 RATIFIED: the EO consultation ladder stays in config.EO_CONSULTATION_LADDER

Session 11 (2026-09-17, adoption ratification; Comparison Principles Codex B2(a)-(e)):

  R6-35 BSR-AN-02 ADOPTED (Convocations; a civil statute is context only; a book's adoption covers its integral texts)
  R6-36 BSR-AN-05 ADOPTED (ACNA College of Bishops, 2018); the 2017-18 canons stay on the QA track
  R6-37 BSR-LU-03 ADOPTED with its translator disclosed; publisher apparatus never inherits it (adoption_guards)
  R6-38 scope is the verified reach of the named body: BSR-RP-03 added, BSR-RP-02 and BSR-LU-01 amended
  R6-39 BSR-BA-03 ISSUED_UNADOPTED with its own disclosure wording
  R6-40 BSR-RC-07, BSR-AN-04, BSR-RP-05 ADOPTED as proposed

Session 13 (2026-09-17, Codex v0.6):

  R6-43 registration is by section: registered-sections.json is the only list of registered creed and definition texts
  R6-44 confessed catechisms: BSR-LU-03 CONFESSIONAL (registry_overrides; several rulings on one row combine)
  R6-45 the AN-04 Historical Documents chunks await a scope ruling and are not registered texts
  R6-46 session 12 confirmations (the AN-05 guard narrowed to the front matter before Part I; RP-05 notes guarded)"""
import json
import os

from .config import RUNS_DIR, ROOT

RULINGS_PATH = os.environ.get("SJN_RULINGS_PATH") or os.path.join(RUNS_DIR, "author-rulings-pending-workbook.json")
AUTHOR_RULING_FLOOR_CAP = "AUTHOR_RULING_R6-2"

# R6-6 vocabularies, and the two rows the author named as published-but-unadopted.
ADOPTION_STATUSES = ("ADOPTED", "ISSUED_UNADOPTED", "NOT_APPLICABLE", "UNVERIFIED")
ADOPTION_SCOPES = ("ONE_CHURCH", "MULTILATERAL", "WHOLE_BRANCH")
ADOPTION_COLUMNS = ("adoption_status", "adoption_act", "adoption_body_scope", "adoption_verified")


def load(path=None):
    p = path or RULINGS_PATH
    if not os.path.exists(p):
        # the rulings are part of the harness from session 6 on: a run without them is not the run the author ratified
        raise SystemExit(f"author rulings file missing: {p} — nothing runs without the session-6 rulings")
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    d["_path"] = os.path.relpath(p, ROOT).replace("\\", "/")
    return d


def _ruling(r, key):
    return ((r or load()).get("rulings") or {}).get(key) or {}


def required_subjects(r=None):
    """{family_id: required_subject} retyped by R6-1."""
    r = r or load()
    fams = ((r.get("rulings") or {}).get("R6-1_required_subject") or {}).get("families") or {}
    return {pid: f["required_subject"] for pid, f in fams.items()}


def retirements(r=None):
    """{registry_id: ruling} for rows the author retired before the workbook records it."""
    r = r or load()
    out = {}
    for key, ru in (r.get("rulings") or {}).items():
        if ru.get("registry_id") and ru.get("status") == "RETIRED":
            out[ru["registry_id"]] = dict(ru, ruling=key)
    return out


def refused_candidates(r=None):
    """{candidate_id: {queue_id, predicate}} refused by R6-2 (2c)."""
    r = r or load()
    cells = ((r.get("rulings") or {}).get("R6-2_hedged_partial") or {}).get("refused_cells") or {}
    return {cid: {"queue_id": qid, "predicate": c.get("predicate")} for qid, c in cells.items() if isinstance(c, dict)
            for cid in c.get("candidates") or []}


def same_text_rows(r=None):
    """{alternate_registry_id: controlling_registry_id} declared by R6-4 (one text, different wording)."""
    r = r or load()
    rows = ((r.get("rulings") or {}).get("R6-4_one_text_one_slot") or {}).get("same_text_rows") or {}
    return {rid: v["same_text_as"] for rid, v in rows.items() if isinstance(v, dict) and v.get("same_text_as")}


# ---------------------------------------------------------------- R6-5 registry overrides
# The registry override hook. A ruling that carries `registry_id` and an `overrides` block re-types that
# row IN MEMORY, exactly as `retirements()` retires one: Registry() applies it, records the workbook value
# beside the ruled value, and — once the workbook carries the change — reads the workbook and fails loudly
# on any disagreement. Only these fields may be overridden; anything else in the block is a hard error.
OVERRIDABLE = ("standard_title", "authority_tier", "speaks_for", "reception_scope", "scope_caveat",
               "same_work_as", "eo_ladder_tier", "creed_resolution",
               # session 11 (goal 3a/3e/3f): registry-note and host-note corrections the author asked for, pending the workbook
               "canonical_url", "draft_recommendation")


def registry_overrides(r=None):
    """{registry_id: {"ruling": "key[; key]", "rulings": [key, ...], "fields": {...}, "field_rulings": {field: key}}} for rows the
    author re-typed before the workbook records it.

    Session 13 (R6-44): several rulings on ONE row COMBINE. Before, the dict was keyed by registry_id and the last ruling read
    silently replaced every earlier one (BSR-LU-03 carries R6-37's draft_recommendation and R6-44's authority_tier). Each field
    keeps the ruling that set it; two rulings that set the same field to different values fail loudly — never last-one-wins."""
    r = r or load()
    out = {}
    for key, ru in (r.get("rulings") or {}).items():
        rid, fields = ru.get("registry_id"), ru.get("overrides")
        if not rid or not isinstance(fields, dict):
            continue
        bad = [f for f in fields if f not in OVERRIDABLE]
        if bad:
            raise SystemExit(f"author ruling {key} overrides fields outside {OVERRIDABLE}: {bad}")
        ov = out.setdefault(rid, {"rulings": [], "fields": {}, "field_rulings": {}})
        for f, v in fields.items():
            if f in ov["fields"] and ov["fields"][f] != v:
                raise SystemExit(f"author rulings {ov['field_rulings'][f]} and {key} override {rid} '{f}' with different values: "
                                 f"{ov['fields'][f]!r} vs {v!r}")
            ov["fields"][f] = v
            ov["field_rulings"][f] = ov["field_rulings"].get(f) or key
        ov["rulings"].append(key)
        ov["ruling"] = "; ".join(ov["rulings"])
    return out


def same_work_rows(r=None):
    """{registry_id: registry_id} — rows that are ONE work and count as one observation (R6-5, HOPKO-OF-VOL1).

    Distinct from same_text_rows (R6-4), which is about one TEXT competing for one card slot. This is about
    independence: two rows of one work are one observation whatever they quote."""
    out = {}
    for rid, ov in registry_overrides(r).items():
        if ov["fields"].get("same_work_as"):
            out[rid] = ov["fields"]["same_work_as"]
    return out


def independence_groups(r=None):
    """{group_name: [registry_id, ...]} as the author declared them (R6-5)."""
    r = r or load()
    out = {}
    for ru in (r.get("rulings") or {}).values():
        for name, ids in (ru.get("independence_group") or {}).items():
            out[name] = list(ids)
    return out


def chunk_level_creed_rows(r=None):
    """The ONLY rows where a creed still resolves by chunk locator (R6-5). Everywhere else it resolves by phrase."""
    return list(_ruling(r, "R6-5_bsr_eo_01_retype").get("chunk_level_creed_resolution_allowed_rows") or [])


# ---------------------------------------------------------------- R6-6 / R6-9 adoption
def adoption_rows(r=None):
    """{registry_id: {adoption_status, adoption_act, adoption_body_scope, adoption_verified, adopting_body}} (R6-6)."""
    rows = _ruling(r, "R6-6_adoption_field").get("rows") or {}
    for rid, v in rows.items():
        st = v.get("adoption_status")
        if st not in ADOPTION_STATUSES:
            raise SystemExit(f"author ruling R6-6: {rid} carries adoption_status {st!r}, outside {ADOPTION_STATUSES}")
        sc = v.get("adoption_body_scope") or ""
        if sc and sc not in ADOPTION_SCOPES:
            raise SystemExit(f"author ruling R6-6: {rid} carries adoption_body_scope {sc!r}, outside {ADOPTION_SCOPES}")
    return {rid: dict(v) for rid, v in rows.items()}


APPARATUS_GUARD_KINDS = ("PUBLISHER_APPARATUS",)


def adoption_guards(r=None):
    """{registry_id: guard} — R6-37 / Codex B2(b), B2(d): matter a publisher or editor added to an adopted text never inherits
    the text's adoption. A guard lives on the ruling that ratified the row (a `guard` object carrying `registry_id`), so any row
    with a translation or publisher apparatus can carry one; only the rows a ruling names are guarded."""
    r = r or load()
    out = {}
    for key, ru in (r.get("rulings") or {}).items():
        g = ru.get("guard")
        if not isinstance(g, dict):
            continue
        rid = g.get("registry_id")
        if not rid or g.get("kind") not in APPARATUS_GUARD_KINDS:
            raise SystemExit(f"author ruling {key}: guard needs registry_id and kind in {APPARATUS_GUARD_KINDS}")
        if not g.get("apparatus_markers") and not g.get("integral_text_pattern"):
            raise SystemExit(f"author ruling {key}: guard for {rid} names neither apparatus_markers nor integral_text_pattern")
        if g.get("resolves_to") != "OFFICIAL_EXPOSITION":
            raise SystemExit(f"author ruling {key}: guard for {rid} must resolve to OFFICIAL_EXPOSITION, not {g.get('resolves_to')!r}")
        out[rid] = dict(g, ruling=key)
    return out


def adoption_policy(r=None):
    """The R6-6 scope and fail-closed policy, and the R6-9 card disclosure strings."""
    a, n = _ruling(r, "R6-6_adoption_field"), _ruling(r, "R6-9_second_tier_rank")
    return {"scope_rule": a.get("scope_rule"), "scope_rule_meaning": a.get("scope_rule_meaning"),
            "department_imprint_counts_as_adoption": bool(a.get("department_imprint_counts_as_adoption")),
            "department_imprint_exception": a.get("department_imprint_exception"),
            "unverified_behavior": a.get("unverified_behavior"), "exposition_resolution": a.get("exposition_resolution"),
            "migration_order": a.get("migration_order") or [],
            "second_tier": "OFFICIAL_EXPOSITION", "assert": n.get("assert"), "disclosure": n.get("card_disclosure") or {}}


# ---------------------------------------------------------------- R6-43 registered sections
REGISTERED_SECTIONS_PATH = os.environ.get("SJN_REGISTERED_SECTIONS_PATH") or os.path.join(RUNS_DIR, "registered-sections.json")
SECTION_KINDS = ("CREED", "DEFINITION")


def registered_sections(path=None):
    """[{registry_id, locator, kind, what, text_through?, ...}] — Codex B1(a), ruled R6-43 (session 13): the explicit list of
    registered creed and definition SECTIONS. A chunk is a registered text only if its (registry_id, locator) is listed; nothing
    is registered by a locator pattern or a row tier any more. A missing file is a hard stop, never an empty registration."""
    p = path or REGISTERED_SECTIONS_PATH
    if not os.path.exists(p):
        raise SystemExit(f"registered sections file missing: {p} — R6-43 names it as the only source of registered creed and "
                         f"definition texts")
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    out, seen = [], set()
    for e in d.get("sections") or []:
        if not e.get("registry_id") or not e.get("locator") or e.get("kind") not in SECTION_KINDS:
            raise SystemExit(f"registered sections file: an entry needs registry_id, locator and kind in {SECTION_KINDS}: {e}")
        key = (e["registry_id"], e["locator"])
        if key in seen:
            raise SystemExit(f"registered sections file lists {key} twice")
        seen.add(key)
        out.append(dict(e))
    return out


# ---------------------------------------------------------------- R6-45 scope markers
SCOPE_MARKERS = ("AWAITING_SCOPE_RULING",)


def scope_markers(r=None):
    """{registry_id: [marker]} — R6-45 (session 13): chunks of a row that a ruling marks as awaiting a scope ruling. A marker lives on
    the ruling as `scope_marker` {registry_id, locator_prefix, marker, text}; a chunk whose locator starts with locator_prefix carries
    it. Marked chunks keep their locators and tiers, the packets show the marker on every entry located in them, and they are never
    registered creed or definition texts (Registry._registered_sections refuses a listed section that carries one)."""
    r = r or load()
    out = {}
    for key, ru in (r.get("rulings") or {}).items():
        m = ru.get("scope_marker")
        if not isinstance(m, dict):
            continue
        if not m.get("registry_id") or not m.get("locator_prefix") or m.get("marker") not in SCOPE_MARKERS or not m.get("text"):
            raise SystemExit(f"author ruling {key}: scope_marker needs registry_id, locator_prefix, text and marker in {SCOPE_MARKERS}")
        out.setdefault(m["registry_id"], []).append(dict(m, ruling=key))
    return out


# ---------------------------------------------------------------- R6-8 agency
AGENCY_TAGS_PATH = os.environ.get("SJN_AGENCY_TAGS_PATH") or os.path.join(RUNS_DIR, "spirit-family-agency-tags.json")
AGENCY_CLASSES = ("ACTION", "ATTRIBUTE")


def agency_tags(r=None, path=None):
    """{family_id: ACTION|ATTRIBUTE} the author has RATIFIED — read from the ratified tags file (R6-14, session 8).

    Only an entry marked `ratified: true` is carried. A family absent from the file, or not ratified, gets NO class, so
    the verifier's AGENCY line fails closed for it. Every carried tag must agree with the tags R6-14 records in the
    rulings file (and R6-8's own RNR-H35); a disagreement, or a ratified family the rulings never named, fails loudly."""
    r = r or load()
    p = path or AGENCY_TAGS_PATH
    if not os.path.exists(p):
        raise SystemExit(f"ratified agency tags file missing: {p} — R6-14 names it as the source of every agency class")
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    ruled = dict(_ruling(r, "R6-8_passive_agency").get("ratified_tags") or {})
    ruled.update(_ruling(r, "R6-14_agency_tags_ratified").get("tags") or {})
    out = {}
    for fid, e in (d.get("families") or {}).items():
        if e.get("ratified") is not True:
            continue
        cls = str(e.get("agency_class") or "").upper()
        if cls not in AGENCY_CLASSES:
            raise SystemExit(f"agency tags file: {fid} carries agency_class {cls!r}, outside {AGENCY_CLASSES}")
        if ruled.get(fid) != cls:
            raise SystemExit(f"agency tags file: {fid} = {cls} disagrees with the author's rulings ({ruled.get(fid)!r})")
        out[fid] = cls
    return out


def agency_blocks_eo(r=None):
    """R6-8 blocked the EO launch until the tags were ratified; R6-14 discharges it."""
    if _ruling(r, "R6-14_agency_tags_ratified"):
        return False
    return _ruling(r, "R6-8_passive_agency").get("blocks") == "EASTERN_ORTHODOX_LAUNCH"


# ---------------------------------------------------------------- R6-12 cell flags
def cell_flags(r=None):
    """{queue_id: {flag, card_disclosure, ...}} for cells the author flagged (R6-12)."""
    r = r or load()
    out = {}
    for key, ru in (r.get("rulings") or {}).items():
        if ru.get("queue_id") and ru.get("flag"):
            out[ru["queue_id"]] = dict(ru, ruling=key)
    return out


def summary(r=None):
    """What the harness applied, for run logs and packet headers."""
    r = r or load()
    return {"file": r.get("_path"), "required_subject_retyped": sorted(required_subjects(r)),
            "registry_retired": sorted(retirements(r)), "refused_candidates": sorted(refused_candidates(r)),
            "same_text_rows": same_text_rows(r),
            "registry_overrides": {rid: ov["fields"] for rid, ov in registry_overrides(r).items()},
            "same_work_rows": same_work_rows(r), "independence_groups": independence_groups(r),
            "chunk_level_creed_rows": chunk_level_creed_rows(r),
            "adoption_rows": {rid: v.get("adoption_status") for rid, v in adoption_rows(r).items()},
            "adoption_guards": sorted(adoption_guards(r)),
            "adoption_scope_rule": adoption_policy(r)["scope_rule"],
            "agency_tags_ratified": agency_tags(r), "cell_flags": sorted(cell_flags(r)),
            "status": "AUTHOR RULED 2026-09-13 (R6-1..R6-4), 2026-09-16 (R6-5..R6-23) and 2026-09-17 (R6-35..R6-40); applied in memory; "
                      "workbook not written (deltas pending ratification)"}
