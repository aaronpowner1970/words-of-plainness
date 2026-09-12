"""Branch Source Registry (workbook sheet, Gate 5) — shared helpers.

Used by the Gate 2 pipeline (rule R001, branches.json) and by the Gate 6 recovery
team (scripts/sjn_recovery). The registry is the only list of sources a cell may
cite; enforcement keys on `publisher_domain` (APP CONFIG `registry_only_enforcement`).

Lineage admission: some AUTHOR_RATIFIED rows are LINEAGE rows whose text lives on a
third-party host already cited by released cells (EWTN, Fordham, ccel, newadvent). Where
the row names that host in `publisher_domain`, `canonical_url` or `standard_title`, the
host is admitted for that branch and reported as lineage-admitted so the Gate 7
migration (APP CONFIG `lineage_host_policy = MIGRATE_WHERE_OFFICIAL`) can find it.
"""
import re
from urllib.parse import urlparse

from .workbook import s

_DOMAIN_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+(?:org|net|com|edu|va|uk|ca|info))\b", re.I)


def load_registry(wb):
    """Return list of dict rows from the Branch Source Registry sheet (all statuses)."""
    if "Branch Source Registry" not in wb.wb.sheetnames:
        return []
    _, rows, _ = wb.table("Branch Source Registry", "registry_id")
    out = []
    for r in rows:
        d = {k: s(v) for k, v in r.items() if k != "__row"}
        d["__row"] = r["__row"]
        out.append(d)
    return out


def ratified(rows):
    return [r for r in rows if r.get("status") == "AUTHOR_RATIFIED"]


def normalize_host(host):
    host = (host or "").casefold().strip()
    return host[4:] if host.startswith("www.") else host


def registrable(host):
    """Organization-level domain: the last two labels (bfm.sbc.net -> sbc.net; files.lcms.org -> lcms.org).
    The registry's publisher_domain names the publishing body; its other hosts (www., files., bfm.) are the
    same publisher. No public-suffix cases (co.uk etc.) occur in the registry."""
    parts = normalize_host(host).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else normalize_host(host)


def host_matches(host, domain):
    h, d = normalize_host(host), normalize_host(domain)
    if not (h and d):
        return False
    return h == d or h.endswith("." + d) or registrable(h) == registrable(d)


def admitted_domains(row):
    """publisher_domain plus any host the row itself names (canonical_url, standard_title,
    draft_recommendation). Returns (primary, lineage_extra) — both normalized."""
    primary = normalize_host(row.get("publisher_domain", ""))
    extra = set()
    url = row.get("canonical_url", "")
    if url.startswith("http"):
        extra.add(normalize_host(urlparse(url).netloc))
    for field in ("canonical_url", "standard_title"):
        for m in _DOMAIN_RE.finditer(row.get(field, "") or ""):
            extra.add(normalize_host(m.group(1)))
    extra.discard(primary)
    extra.discard("")
    return primary, sorted(extra)


def branch_domain_index(rows):
    """branch -> {domain: {"registry_id", "kind": "primary"|"lineage", "row"}} over AUTHOR_RATIFIED rows."""
    idx = {}
    for r in ratified(rows):
        br = r.get("branch", "")
        primary, extra = admitted_domains(r)
        bucket = idx.setdefault(br, {})
        if primary and primary not in bucket:
            bucket[primary] = {"registry_id": r["registry_id"], "kind": "primary", "row": r}
        for d in extra:
            bucket.setdefault(d, {"registry_id": r["registry_id"], "kind": "lineage", "row": r})
    return idx


def resolve_row(idx, branch, url):
    """Like resolve_host but returns (kind, registry_id, row)."""
    host = normalize_host(urlparse(url).netloc)
    for d, info in (idx.get(branch) or {}).items():
        if host_matches(host, d):
            return info["kind"], info["registry_id"], info.get("row")
    return None, None, None


def resolve_host(idx, branch, url):
    """Return (kind, registry_id) for a cited URL in a branch, or (None, None) if not admitted."""
    host = normalize_host(urlparse(url).netloc)
    for d, info in (idx.get(branch) or {}).items():
        if host_matches(host, d):
            return info["kind"], info["registry_id"]
    return None, None


def fallback_only_ids(config):
    v = s(config.get("registry_fallback_only_rows"))
    return [x.strip() for x in re.split(r"[;,|\s]+", v) if x.strip()]


def enforcement_on(config):
    return s(config.get("registry_only_enforcement")).casefold() in ("true", "1", "yes")


def config_list(config, key, default=None):
    """A pipe-separated APP CONFIG value as a list (authority_tier_rank, reception_scope_vocabulary)."""
    v = s(config.get(key))
    if not v:
        return list(default or [])
    return [x.strip() for x in v.split("|") if x.strip()]


# ---------------------------------------------------------------- reception axis (v2.25, ADOPT_BOTH)
def reception_scope(row):
    return s(row.get("reception_scope")).upper()


def is_dialogue_only(row):
    """APP CONFIG dialogue_text_policy = DIALOGUE_ONLY_NEVER_CITED: such a row may be registered for
    provenance but is refused as a cell citation. No such row exists in v2.25; the refusal is live."""
    return reception_scope(row) == "DIALOGUE_ONLY"


def is_translation_witness(row):
    """A reading witness, not an independent source: a cell may not rest on it alone."""
    return reception_scope(row) == "TRANSLATION_WITNESS"


def is_witness_row(row):
    """TRANSLATION_WITNESS rows (BSR-RC-03, BSR-RC-05) and rows whose tier is qualified as a witness
    (BSR-EO-11, `CONCILIAR (witness; translation)`). Never the controlling text for a cell."""
    return is_translation_witness(row) or "witness" in s(row.get("authority_tier")).casefold()


# ---------------------------------------------------------------- documents refused by name
# APP CONFIG encyclical_1848_status = RECORD_STANDING_ONLY. The 1848 Encyclical of the Eastern
# Patriarchs is genuinely authoritative (the OCA calls it the most authoritative doctrinal statement
# in modern Orthodox history), which is exactly why an agent may find it compelling. Its text is on
# no official Orthodox host and every English version descends from one anonymous 19th-century
# translation, so under R001 and the verbatim-assertion rule it cannot be cited. No registry row
# exists for it; the refusal is made explicit here with a named reason rather than a generic domain
# miss. Standing is recorded (Karmiris, Τά Δογματικά καί Συμβολικά Μνημεῖα, II, 916); text is not.
NON_CITABLE_DOCUMENTS = [
    {
        "name": "1848 Encyclical of the Eastern Patriarchs",
        "reason": "ENCYCLICAL_1848_NOT_CITABLE — APP CONFIG encyclical_1848_status = RECORD_STANDING_ONLY: "
                  "text on no official Orthodox host; every English version descends from one anonymous "
                  "19th-century translation; standing recorded, text never cited",
        "patterns": [
            r"\b1848\b.{0,40}\b(encyclical|epistle|patriarchs?)\b",
            r"\b(encyclical|epistle)\b.{0,40}\b(eastern|orthodox)\s+patriarchs\b.{0,40}\b1848\b",
            r"\bencyclical\s+of\s+the\s+(eastern|orthodox)\s+patriarchs\b",
            r"\breply\s+of\s+the\s+orthodox\s+patriarchs\b.{0,30}\bpius\b",
            r"\bpius\s+ix\b.{0,60}\b(eastern|orthodox)\s+patriarchs\b",
        ],
    },
]


def refusal_reason(*texts):
    """Named refusal for a document that must never be cited, matched on any of the given strings
    (document title, locator, URL, standard title). Returns the reason string or None."""
    blob = " ".join(s(t) for t in texts if t).casefold()
    if not blob:
        return None
    for doc in NON_CITABLE_DOCUMENTS:
        for p in doc["patterns"]:
            if re.search(p, blob, re.I | re.S):
                return doc["reason"]
    return None


def citation_refusal(row):
    """Why an otherwise-admitted registry row may not be cited for a cell, or None."""
    if row is None:
        return None
    if is_dialogue_only(row):
        return ("DIALOGUE_ONLY_NEVER_CITED — APP CONFIG dialogue_text_policy: the publisher disclaims the text as "
                "an official position, and the disclaimer frequently does not appear on the document's own page")
    return refusal_reason(row.get("standard_title"), row.get("canonical_url"))
