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
from . import rulings  # noqa: E402

# ---------------------------------------------------------------- authority tier rank
# The rank is READ from APP CONFIG `authority_tier_rank` (AUTHOR RATIFIED, v2.25). This module-level
# default is only the fallback for a workbook that predates the key; Registry() replaces it.
TIER_RANK_DEFAULT = ["CONCILIAR", "CONFESSIONAL", "CATECHETICAL", "OFFICIAL_EXPOSITION", "CURRENT_OFFICIAL_WITNESS"]
# R6-9 (session 7): the rank an unadopted or unverified exposition resolves to. It is an EXISTING rank, asserted from
# APP CONFIG to sit directly below CATECHETICAL (Registry.assert_second_tier_rank); APP CONFIG is never changed.
SECOND_TIER = "OFFICIAL_EXPOSITION"
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

# R6-10 (session 7): a DOGMATIC DEFINITION (horos) registered as a text. Canons and anathemas are excluded by the
# author's ruling, so a locator that names one is never a definition text however conciliar its row.
_DEFINITION_LOCATOR = re.compile(r"\b(definition of faith|horos|ὅρος|confession of faith)\b", re.I)
_DEFINITION_EXCLUDE = re.compile(r"\b(canon|anathema|anathematism|damnamus)\b", re.I)

# The floor for a phrase-level creed or definition match. "begotten, not made" (3 words, 17 characters) and
# "light of light" (3 words, 14) are the shortest clauses the author's own examples turn on, so the floor sits
# directly below them. Anything shorter is not a creed CLAUSE but a word or two that the Creed happens to contain.
# RATIFIED R6-21 (2026-09-16): this floor, exactly as implemented here and in resolve_registered_phrase's comparison,
# applies to all creed and definition phrase matching. It does not decide the Q-290 fallback (EO packet review).
CREED_PHRASE_MIN_WORDS = 3
CREED_PHRASE_MIN_CHARS = 12


def creed_resolution_tier(tier_text):
    """The tier a creed printed inside this row resolves to, per the row's own tier note
    ("… the Creed within resolves CONCILIAR", "Nicene and Athanasian resolve CONCILIAR"), or None."""
    m = re.search(r"resolves?\s+([A-Z_]+)", tier_text or "")
    return m.group(1).upper() if m else None


def _is_catechism_by_title(row):
    """R6-6 migration step 2: a row typed CONFESSIONAL or CONCILIAR is NOT_APPLICABLE mechanically UNLESS it is a
    catechism by title — the Westminster Shorter/Larger, the Heidelberg, the catechisms inside the Book of Concord."""
    t = s(row.get("standard_title")).casefold()
    return "catechism" in t or "catechisms" in t


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
        # Session 7 (R6-5): the registry OVERRIDE hook. A row the author has re-typed is re-typed here, in memory,
        # until the workbook says so — the same pattern as the retirement above. Once the workbook carries the value
        # it is read from the workbook and a disagreement fails loudly, exactly as R6-1's required-subject column does.
        self.registry_overrides = {}
        for rid, ov in rulings.registry_overrides().items():
            if rid not in by:
                raise SystemExit(f"author ruling {ov['ruling']} re-types {rid}, which is not a workbook registry row")
            applied, agreed = {}, {}
            for field, value in ov["fields"].items():
                wb_value = s(by[rid].get(field))
                if wb_value and field in ("same_work_as", "eo_ladder_tier", "creed_resolution"):
                    # a column the workbook has since grown: it wins, and must agree
                    if wb_value != value:
                        raise SystemExit(f"Branch Source Registry {rid} '{field}' disagrees with author ruling {ov['ruling']}: "
                                         f"{wb_value!r} vs {value!r}")
                    agreed[field] = wb_value
                    continue
                if wb_value == value:
                    agreed[field] = wb_value                  # the workbook already carries the re-type
                    continue
                applied[field] = {"workbook": by[rid].get(field), "ruled": value}
                by[rid][field] = value
            # session 13 (R6-44): several rulings on one row combine; each field names the ruling that set it
            by[rid]["_author_ruling_override"] = {"ruling": ov["ruling"], "applied": applied, "already_in_workbook": agreed,
                                                  "field_rulings": dict(ov["field_rulings"]),
                                                  "pending": "applied in memory; workbook not written"}
            self.registry_overrides[rid] = {"ruling": ov["ruling"], "applied": applied, "already_in_workbook": agreed,
                                            "field_rulings": dict(ov["field_rulings"])}
            if applied:
                self.rulings_applied.append({"registry_id": rid, "ruling": ov["ruling"], "status": "RE-TYPED",
                                             "fields": sorted(applied)})
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
        # ---- session 7 (R6-5 / R6-6 / R6-9 / R6-10)
        self.chunk_level_creed_rows = set(rulings.chunk_level_creed_rows())
        self.same_work_rows = rulings.same_work_rows()
        self.independence_groups = rulings.independence_groups()
        self.adoption_policy = rulings.adoption_policy()
        self.assert_second_tier_rank()
        self.adoption_map, self.adoption_migration = self._migrate_adoption(rulings.adoption_rows())
        self._adoption_guards = rulings.adoption_guards()               # session 11, R6-37
        for rid in self._adoption_guards:
            if rid not in self.by_id:
                raise SystemExit(f"author ruling {self._adoption_guards[rid]['ruling']} guards {rid}, which is not a ratified registry row")
        self._creed_index, self._definition_index = {}, {}
        self._sections = rulings.registered_sections()                  # session 13, R6-43
        self._section_keys = {(e["registry_id"], e["locator"]) for e in self._sections}

    # ---------------------------------------------------------------- R6-9: the second tier's rank
    def assert_second_tier_rank(self):
        """R6-9 asserts, from APP CONFIG, that OFFICIAL_EXPOSITION ranks DIRECTLY below CATECHETICAL. The rank is the
        ratified key; the harness never changes it, and it stops rather than resolve an unadopted exposition to a rank
        the workbook does not say is the next one down."""
        rank = list(self.tier_rank_list)
        for t in ("CATECHETICAL", SECOND_TIER):
            if t not in rank:
                raise SystemExit(f"APP CONFIG authority_tier_rank does not carry {t}: R6-9 cannot resolve an unadopted "
                                 f"exposition ({rank})")
        if rank.index(SECOND_TIER) != rank.index("CATECHETICAL") + 1:
            raise SystemExit(f"APP CONFIG authority_tier_rank does not rank {SECOND_TIER} directly below CATECHETICAL "
                             f"({rank}): R6-9's second tier is not the rank the author ratified — stopping")
        return {"rank": rank, "catechetical": rank.index("CATECHETICAL"), "second_tier": rank.index(SECOND_TIER),
                "ok": True}

    # ---------------------------------------------------------------- R6-6: the adoption field
    def _migrate_adoption(self, ruled):
        """The four adoption columns on every ratified row, in the author's migration order. The workbook wins where it
        already carries a column, and a disagreement with the ruling fails loudly. Returns (map, migration record)."""
        out, by_step = {}, {"WORKBOOK": [], "AUTHOR_RULING_R6-6": [], "NOT_APPLICABLE (mechanical)": [], "UNVERIFIED (default)": []}
        for r in self.rows:
            rid = r["registry_id"]
            wb = {c: s(r.get(c)) for c in rulings.ADOPTION_COLUMNS}
            ruled_row = ruled.get(rid)
            if wb.get("adoption_status"):
                if ruled_row and wb["adoption_status"] != ruled_row["adoption_status"]:
                    raise SystemExit(f"Branch Source Registry {rid} 'adoption_status' disagrees with author ruling R6-6: "
                                     f"{wb['adoption_status']!r} vs {ruled_row['adoption_status']!r}")
                rec, source = dict(wb), "WORKBOOK"
            elif ruled_row:
                rec, source = dict(ruled_row), "AUTHOR_RULING_R6-6"
            elif bare_tier(r.get("authority_tier")) in ("CONCILIAR", "CONFESSIONAL") and not _is_catechism_by_title(r):
                rec, source = {"adoption_status": "NOT_APPLICABLE", "adoption_act": "", "adoption_body_scope": "",
                               "adoption_verified": "mechanical: the bare tier is conciliar or confessional and the row is "
                                                    "not a catechism by title — clause 3 does not reach it"}, "NOT_APPLICABLE (mechanical)"
            else:
                rec, source = {"adoption_status": "UNVERIFIED", "adoption_act": "", "adoption_body_scope": "",
                               "adoption_verified": "not verified; R6-6 fails closed (resolved as ISSUED_UNADOPTED)"}, "UNVERIFIED (default)"
            rec["source"] = source
            rec["bare_tier"] = bare_tier(r.get("authority_tier"))
            rec["catechism_by_title"] = _is_catechism_by_title(r)
            out[rid] = rec
            by_step[source].append(rid)
        return out, {k: sorted(v) for k, v in by_step.items()}

    def adoption(self, rid):
        return self.adoption_map.get(rid) or {"adoption_status": "UNVERIFIED", "source": "not a ratified row"}

    def adoption_disclosure(self, rid, chunk=None):
        """R6-9: what the CARD must say about this row's adoption. None when there is nothing to disclose.

        Session 11 (R6-37..R6-40): an ADOPTED ONE_CHURCH / MULTILATERAL row names its body and reach; a row that carries a
        `translation_disclosure` shows it (B2(d)); a row with its own `disclosure_wording` (BSR-BA-03, R6-39) uses exactly that;
        a chunk the row's apparatus guard marks as publisher matter says it does not inherit the adoption (B2(b))."""
        a = self.adoption(rid)
        d = self.adoption_policy["disclosure"]
        st, scope = a.get("adoption_status"), (a.get("adoption_body_scope") or "")
        guard = self.apparatus_guard(rid, chunk) if chunk is not None else None
        if guard:
            return {"text": "publisher-added matter: it does not inherit the adoption of the text it accompanies",
                    "adoption_status": st, "apparatus_guard": guard, "resolves_to": SECOND_TIER}
        if st == "ADOPTED":
            translation = a.get("translation_disclosure") or ""
            if scope and scope != "WHOLE_BRANCH":
                body = a.get("adopting_body") or "the adopting body"
                reach = {"ONE_CHURCH": "one church", "MULTILATERAL": "several churches"}.get(scope, scope.casefold())
                text = f"approved by {body} ({reach})" + (f"; {translation}" if translation else "")
                return {"text": text, "adoption_status": st, "adoption_body_scope": scope,
                        "adoption_act": a.get("adoption_act"), "scope_rule": self.adoption_policy["scope_rule"],
                        "translation_disclosure": translation or None}
            if translation:
                return {"text": translation, "adoption_status": st, "adoption_body_scope": scope, "translation_disclosure": translation}
            return None
        if st == "NOT_APPLICABLE":
            return None
        if a.get("disclosure_wording"):
            return {"text": a["disclosure_wording"], "adoption_status": st, "adoption_verified": a.get("adoption_verified"),
                    "fails_closed": st == "UNVERIFIED"}
        text = d.get(st) or d.get("UNVERIFIED")
        if a.get("bare_tier") == "CATECHETICAL" or a.get("catechism_by_title"):
            text = f"{text} ({d.get('catechism_qualifier')})"
        return {"text": text, "adoption_status": st, "adoption_verified": a.get("adoption_verified"),
                "fails_closed": st == "UNVERIFIED"}

    # ---------------------------------------------------------------- R6-37: publisher apparatus never inherits adoption
    def apparatus_guard(self, rid, chunk):
        """Codex B2(b)/B2(d), ruled R6-37: is this stored chunk (wholly or partly) matter a publisher or editor added to the
        row's adopted text? Returns {ruling, reason} or None. Generic over rows: a row is guarded only when a ruling carries a
        guard for it (rulings.adoption_guards). Two tests, either sufficient, evaluated on the whitespace-normalised chunk text:
          - apparatus_markers: a marker (case-insensitive) in the text, locator or division — e.g. "The Central Thought";
          - integral_text_pattern: the text is NOT wholly the integral text (fullmatch). This is the fail-closed test for
            "any text that is not the catechism's own text", since no marker list can name every heading a publisher uses."""
        if chunk is None:
            return None
        g = self._adoption_guards.get(rid)
        if not g:
            return None
        text = " ".join((chunk.get("text") or "").split())
        where = " ".join([text, chunk.get("locator") or "", chunk.get("division") or ""]).casefold()
        for m in g.get("apparatus_markers") or []:
            if m.casefold() in where:
                return {"ruling": g["ruling"], "reason": f"apparatus marker {m!r}"}
        pat = g.get("integral_text_pattern")
        if pat and not re.fullmatch(pat, text, re.S):
            return {"ruling": g["ruling"], "reason": "the chunk is not wholly the row's integral text (integral_text_pattern)"}
        return None

    def exposition_tier(self, rid, tier=None, chunk=None):
        """R6-6 clause 3 / R6-9: the tier an EXPOSITION citation (not a verbatim creed or definition phrase) resolves to.

        Clause 3 reaches CATECHETICAL rows — the review's own statement of its scope ("clause 3 reaches only catechetical
        and expository rows"). A CONFESSIONAL row is not demoted: the confessional act that typed it IS its adoption, and
        demoting the Westminster Larger Catechism below the Shorter is not what the ruling says. Where such a row is left
        UNVERIFIED the card still discloses it (adoption_disclosure) and it is reported as an ADOPTED proposal.

        Session 11 (R6-37): a chunk the row's apparatus guard marks as publisher matter resolves to OFFICIAL_EXPOSITION
        whatever the row's adoption — the adoption belongs to the text, not to what a publisher added. It never raises a tier."""
        row = self.by_id.get(rid)
        if not row:
            return ""
        tier = tier if tier is not None else s(row.get("authority_tier"))
        if chunk is not None and tier_rank(tier) < tier_rank(SECOND_TIER) and self.apparatus_guard(rid, chunk):
            return f"{SECOND_TIER} (publisher matter, not the adopted text)"
        if bare_tier(tier) != "CATECHETICAL":
            return tier
        st = self.adoption(rid).get("adoption_status")
        if st in ("ADOPTED", "NOT_APPLICABLE"):
            return tier
        qualifier = self.adoption_policy["disclosure"].get("catechism_qualifier") or "not adopted"
        return f"{SECOND_TIER} ({qualifier})"

    # ---------------------------------------------------------------- R6-5 / R6-10: registered creed and definition texts
    def _registered_sections(self, branch, kind):
        """R6-43 (Codex B1(a), session 13): the registered SECTIONS of one kind in this branch, from the explicit list
        (rulings.registered_sections). Registration is by section, never by a locator pattern or a row's tier: a catechism's,
        confession's or commentary's treatment of a creed is not listed, whatever its row. The row-level gates stay as checks on
        the list and fail loudly, never silently: a listed creed must sit in a creed-carrying row (R6-5's allowed rows, or bare
        tier CONCILIAR / CONFESSIONAL; never CATECHETICAL, R6-22/R6-27), a listed definition in a CONCILIAR row, and neither may
        name a canon or an anathema (R6-10). A listed section must exist in the store (unless the row has no stored text at
        all), and its `text_through` marker, where given, must occur in the chunk: the registered key ends after it."""
        from . import store
        from .textutil import punct_key
        rows = {r["registry_id"]: r for r in self.for_branch(branch, citable_only=False)}
        out = []
        for e in self._sections:
            if e["kind"] != kind or e["registry_id"] not in rows:
                continue
            rid, tier = e["registry_id"], s(rows[e["registry_id"]].get("authority_tier"))
            where = f"registered section {rid} {e['locator']!r} (R6-43)"
            if kind == "CREED":
                if rid not in self.chunk_level_creed_rows and bare_tier(tier) not in ("CONCILIAR", "CONFESSIONAL"):
                    raise SystemExit(f"{where}: row tier {tier!r} is not a creed-carrying tier (R6-22/R6-27)")
                resolved = creed_resolution_tier(tier) or bare_tier(tier)
            else:
                if bare_tier(tier) != "CONCILIAR":
                    raise SystemExit(f"{where}: a definition text must sit in a CONCILIAR row, not {tier!r} (R6-10)")
                resolved = bare_tier(tier)
            if _DEFINITION_EXCLUDE.search(e["locator"]):
                raise SystemExit(f"{where}: a canon or anathema is never a registered text (R6-10)")
            chunks = store.load_chunks(rid)
            chunk = next((c for c in chunks if c.get("locator") == e["locator"]), None)
            if chunk is None:
                if chunks:
                    raise SystemExit(f"{where}: no stored chunk carries this locator — the list and the store disagree")
                continue                                  # the row has no stored text (e.g. never built): nothing to register
            text = chunk["text"]
            through = e.get("text_through")
            if through:
                i = text.find(through)
                if i < 0:
                    raise SystemExit(f"{where}: text_through {through!r} does not occur in the stored chunk")
                text = text[: i + len(through)]
            entry = {"registry_id": rid, "locator": e["locator"], "tier": resolved, "chars": len(text), "key": punct_key(text),
                     "section": e}
            if kind == "CREED":
                entry["language"] = chunk.get("language") or "en"
            out.append(entry)
        return out

    def is_registered_section(self, rid, locator):
        """R6-43: is (registry_id, locator) a listed registered creed or definition section?"""
        return (rid, locator) in self._section_keys

    def registered_creed_texts(self, branch):
        """The creed TEXTS this branch registers: sections that ARE a creed, never a catechism's exposition of one.

        Session 13 (R6-43, Codex B1(a)): the list in registered-sections.json decides, section by section (_registered_sections).
        Before session 13 a chunk qualified when its locator named a creed and its row was creed-carrying; that registered
        BSR-LU-01's Small and Large Catechism "Creed" sections, which R6-43 names as not registered texts.
        A CATECHETICAL row is never a registered creed text: RATIFIED R6-22 (2026-09-16), enforced by R6-27 and checked here."""
        if branch not in self._creed_index:
            self._creed_index[branch] = self._registered_sections(branch, "CREED")
        return self._creed_index[branch]

    def registered_definition_texts(self, branch):
        """R6-10: the dogmatic DEFINITIONS (horoi) this branch registers as texts; canons and anathemas never qualify.
        Session 13 (R6-43): read from the registered-sections list, section by section."""
        if branch not in self._definition_index:
            self._definition_index[branch] = self._registered_sections(branch, "DEFINITION")
        return self._definition_index[branch]

    def resolve_registered_phrase(self, branch, phrase):
        """R6-5 clause 1 and R6-10: does this phrase stand VERBATIM inside a registered creed or definition text of this
        branch? Returns the best (highest-ranking) hit — {kind, registry_id, locator, tier} — or None.

        The comparison is textutil.punct_key: NFKC, casefolded, punctuation stripped, whitespace collapsed. The same key
        R6-4's one-text-one-slot guard uses, so the two rules can never disagree about what "the same words" means."""
        hits = self.registered_phrase_hits(branch, phrase)
        return hits[0] if hits else None

    def registered_phrase_hits(self, branch, phrase):
        """Every registered creed or definition text of this branch the phrase stands in verbatim, best first (the list
        resolve_registered_phrase takes the head of). Session 12 (R6-41) needs all of them: the original that holds the seat
        may be any registered text carrying the phrase at the tier it raised the candidate to."""
        from .textutil import punct_key
        key = punct_key(phrase)
        if len(key.split()) < CREED_PHRASE_MIN_WORDS or len(key) < CREED_PHRASE_MIN_CHARS:
            return []
        hits = []
        for kind, texts in (("CREED", self.registered_creed_texts(branch)), ("DEFINITION", self.registered_definition_texts(branch))):
            for t in texts:
                if key and key in t["key"]:
                    hits.append({"kind": kind, "registry_id": t["registry_id"], "locator": t["locator"], "tier": t["tier"]})
        return sorted(hits, key=lambda h: (tier_rank(h["tier"]), h["registry_id"]))

    def raised_by(self, rid, chunk=None, phrase=None):
        """R6-41 (Codex B3(a)): the registered texts that RAISED this citation's tier by phrase-level resolution — every hit at
        the tier the citation resolves to, when that tier is above the host tier — excluding the citation's own chunk (a
        registered text resolves at its own tier; it does not quote itself). [] when phrase-level resolution raised nothing."""
        row = self.by_id.get(rid)
        if not row or not phrase:
            return []
        host = self.exposition_tier(rid, s(row.get("authority_tier")), chunk)
        eff = self.effective_tier(rid, chunk, phrase)
        if tier_rank(eff) >= tier_rank(host):
            return []
        own = (rid, (chunk or {}).get("locator"))
        return [h for h in self.registered_phrase_hits(row["branch"], phrase)
                if tier_rank(h["tier"]) == tier_rank(eff) and (h["registry_id"], h["locator"]) != own]

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
    def effective_tier(self, rid, chunk=None, phrase=None):
        """The tier a citation resolves to. Session 7 (R6-5 clause 1, R6-10, R6-6/R6-9), in this order:

          1. PHRASE-level creed and definition resolution. The citation resolves to the creed's (or the definition's)
             tier only when its phrase stands verbatim in a REGISTERED creed or definition TEXT of the same branch.
             This replaces chunk-locator creed resolution, which resolved all 159k characters of Hopko's exposition to
             CONCILIAR because all 19 BSR-EO-01 locators read "The Symbol of Faith — …".
          2. CHUNK-level creed resolution, kept ONLY for R6-5's chunk_level_creed_resolution_allowed_rows — rows whose
             creed chunk IS the creed and nothing else (BSR-EO-07, BSR-EO-14, BSR-RC-06, BSR-RC-08). Disabled
             everywhere else, including BSR-EO-04, BSR-AN-04, BSR-AN-05, BSR-LU-01, BSR-LU-03 and BSR-RP-04.
          3. Otherwise the HOST tier, as adjusted by the adoption field: an exposition citation from a row that is
             ISSUED_UNADOPTED or UNVERIFIED resolves to OFFICIAL_EXPOSITION (R6-9), with its display qualifier; and a chunk
             the row's apparatus guard marks as publisher matter resolves to OFFICIAL_EXPOSITION (R6-37).

        Resolution never LOWERS a citation below its host row's own tier."""
        row = self.by_id.get(rid)
        if not row:
            return ""
        tier = s(row.get("authority_tier"))
        host = self.exposition_tier(rid, tier, chunk)
        if phrase:
            hit = self.resolve_registered_phrase(row["branch"], phrase)
            if hit and tier_rank(hit["tier"]) < tier_rank(host):
                return hit["tier"]
        if self.creed_tier_resolution == "TIER_PER_CITED_DOCUMENT" and chunk is not None and rid in self.chunk_level_creed_rows:
            resolved = creed_resolution_tier(tier)
            loc = (chunk.get("locator") or "") + " " + (chunk.get("division") or "")
            # session 13 (R6-43): the chunk must also be a registered section, so there is one registration decision
            if (resolved and _CREED_LOCATOR.search(loc) and self.is_registered_section(rid, chunk.get("locator"))
                    and tier_rank(resolved) < tier_rank(host)):
                return resolved
        return host

    def tier_resolution(self, rid, chunk=None, phrase=None):
        """effective_tier with its reason, for the card and for the audit."""
        row = self.by_id.get(rid) or {}
        tier = s(row.get("authority_tier"))
        host = self.exposition_tier(rid, tier, chunk)
        eff = self.effective_tier(rid, chunk, phrase)
        hit = self.resolve_registered_phrase(row.get("branch", ""), phrase) if phrase else None
        guard = self.apparatus_guard(rid, chunk) if row else None
        if hit and eff == hit["tier"] and eff != host:
            why = (f"the phrase stands verbatim in a registered {hit['kind'].casefold()} text of this branch "
                   f"({hit['registry_id']} {hit['locator']})")
        elif guard and eff == host and eff != tier:
            why = f"the apparatus guard ({guard['ruling']}): {guard['reason']}"
        elif eff != tier:
            why = f"the adoption field (R6-6/R6-9): {self.adoption(rid).get('adoption_status')}"
        elif eff != host:
            why = "the row's own tier note (chunk-level creed resolution, R6-5 allowed row)"
        else:
            why = "the host row's tier"
        return {"registry_id": rid, "authority_tier": tier, "host_tier": host, "effective_tier": eff, "why": why,
                "registered_phrase_hit": hit, "raised_by": self.raised_by(rid, chunk, phrase) if row else [],
                "apparatus_guard": guard, "adoption_disclosure": self.adoption_disclosure(rid, chunk)}

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
    ruled = rulings.required_subjects()
    agency = rulings.agency_tags()
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
        # Session 7 (R6-8): the agency class the verifier's AGENCY line needs. Only a RATIFIED tag is carried —
        # the workbook's 'Agency class' column once it exists, the author's ruling until then. A family with no
        # ratified tag carries none and the line fails closed. Session 8 (R6-14): the ratified file is the source.
        wb_agency = s(r.get("Agency class")).upper()
        if wb_agency and pid in agency and wb_agency != agency[pid]:
            raise SystemExit(f"Inherited 57 'Agency class' for {pid} disagrees with author ruling R6-14: {wb_agency!r} vs {agency[pid]!r}")
        if wb_agency or pid in agency:
            out[pid]["agency_class"] = wb_agency or agency[pid]
            out[pid]["agency_class_source"] = "WORKBOOK" if wb_agency else "AUTHOR_RULING_R6-14 (spirit-family-agency-tags.json, ratified 2026-09-16; workbook delta pending)"
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


__all__ = ["Registry", "SECOND_TIER", "load_predicates", "load_comparators", "load_queue", "load_case_targets", "open_cells",
           "gate6_scope", "assert_gate6_scope", "released_cells", "reviewed_empty_cells", "TIER_RANK", "bare_tier", "tier_rank", "set_tier_rank",
           "refusal_reason", "citation_refusal"]
