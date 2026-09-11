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
    """branch -> {domain: {"registry_id", "kind": "primary"|"lineage"}} over AUTHOR_RATIFIED rows."""
    idx = {}
    for r in ratified(rows):
        br = r.get("branch", "")
        primary, extra = admitted_domains(r)
        bucket = idx.setdefault(br, {})
        if primary and primary not in bucket:
            bucket[primary] = {"registry_id": r["registry_id"], "kind": "primary"}
        for d in extra:
            bucket.setdefault(d, {"registry_id": r["registry_id"], "kind": "lineage"})
    return idx


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
