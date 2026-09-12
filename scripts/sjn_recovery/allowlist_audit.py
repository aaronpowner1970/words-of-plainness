"""R001 allowlist audit (Gate 6, 2026-09-12) — no model calls.

  python scripts/sjn_recovery/allowlist_audit.py [--workbook PATH] [--run-id cal-3]

1. States the parser rule R001 uses to build its allowlist (sjn_pipeline.registry.admission) and dumps the
   effective allowlist per branch under the RETIRED all-tokens parser and under the current rule
   (publisher_domain only; AC-15 controlled storage with the `LINKED FROM: ` prefix), listing every row
   where the two disagree and the prose that admitted the extra host.
2. Sweeps a calibration run's cell states for accepted candidates whose chunk was fetched from a host that
   is not the row's publisher_domain (the chunk store's source_url; the audit log itself carries no URLs).
   Also lists every registry row whose corpus was fetched from a host outside its publisher_domain.
3. Re-evaluates the Gate 2 R001 citation check over the queue under both parsers and lists the cells whose
   admission flips.

Writes data-sources/sjn/recovery-runs/allowlist-audit.md and .json. Never writes to the workbook."""
import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_pipeline.registry import (admission, legacy_admitted_domains, normalize_host, host_matches, _DOMAIN_RE,  # noqa: E402
                                   ratified, resolve_row, branch_domain_index)
from sjn_pipeline.workbook import s  # noqa: E402
from sjn_recovery.config import RUNS_DIR, BRANCHES  # noqa: E402
from sjn_recovery.registry import Registry, load_queue  # noqa: E402
from sjn_recovery import store  # noqa: E402

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")

PARSER_RULE = (
    "RETIRED rule (cal-1 … cal-3): allowlist = publisher_domain + the host of canonical_url + EVERY domain-shaped "
    "token found by regex in canonical_url and standard_title, prose included (sjn_pipeline.registry.admitted_domains, "
    "now legacy_admitted_domains). The merge script's domain_of() takes only the first hostname, so the workbook's "
    "publisher_domain column and R001's effective allowlist disagreed on every row whose URL field carried prose. "
    "CURRENT rule (2026-09-12, registry.admission): allowlist = publisher_domain ONLY; no host is read from prose. "
    "AC-15 exception: a row whose publisher_domain is a controlled-storage host is admitted only when its note opens "
    "with `LINKED FROM: <url on the official domain>` and APP CONFIG controlled_storage_policy = "
    "ADMIT_IF_LINKED_FROM_OFFICIAL_DOMAIN; that official domain is admitted beside it. Absent the prefix, refused."
)


def legacy_index(rows):
    idx = {}
    for r in ratified(rows):
        primary, extra = legacy_admitted_domains(r)
        bucket = idx.setdefault(r.get("branch", ""), {})
        if primary and primary not in bucket:
            bucket[primary] = {"registry_id": r["registry_id"], "kind": "primary", "row": r}
        for d in extra:
            bucket.setdefault(d, {"registry_id": r["registry_id"], "kind": "lineage", "row": r})
    return idx


def prose_context(row, host):
    """Where in the row's URL/title fields the retired parser found `host`."""
    out = []
    for field in ("canonical_url", "standard_title"):
        text = s(row.get(field))
        for m in _DOMAIN_RE.finditer(text):
            if normalize_host(m.group(1)) == host:
                a, b = max(0, m.start() - 45), min(len(text), m.end() + 45)
                out.append(f"{field}: “…{text[a:b]}…”")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook")
    ap.add_argument("--run-id", default="cal-3")
    a = ap.parse_args()
    reg = Registry(a.workbook)
    rows = reg.rows_all
    queue = load_queue(reg.wb)
    manifest = store.load_manifest()
    old_idx = legacy_index(rows)
    new_idx = branch_domain_index(rows, reg.config)

    # ---- 1. allowlists per branch and disagreements
    per_branch, disagreements, refused = {}, [], []
    for br in BRANCHES:
        o = old_idx.get(br, {}); n = new_idx.get(br, {})
        per_branch[br] = {"retired_parser": {d: v["registry_id"] + ("" if v["kind"] == "primary" else f" ({v['kind']})") for d, v in sorted(o.items())},
                          "current_rule": {d: v["registry_id"] + ("" if v["kind"] == "primary" else f" ({v['kind']})") for d, v in sorted(n.items())}}
    for r in ratified(rows):
        lp, le = legacy_admitted_domains(r)
        adm = admission(r, reg.config)
        if adm["refused"]:
            refused.append({"registry_id": r["registry_id"], "branch": r["branch"], "publisher_domain": s(r.get("publisher_domain")), "reason": adm["reason"]})
        for host in le:
            # a host the retired parser admitted that the current rule does not admit FOR THIS ROW
            if host == adm["primary"] or host in adm["extra"]:
                continue
            still_admitted_elsewhere = any(host_matches(host, d) for d in new_idx.get(r["branch"], {}))
            disagreements.append({"registry_id": r["registry_id"], "branch": r["branch"], "publisher_domain": lp,
                                  "extra_host_under_retired_parser": host, "prose": prose_context(r, host),
                                  "still_admitted_for_branch_via_other_row": still_admitted_elsewhere,
                                  "inverted": bool(re.search(r"not on|403|convenience copy|reading only|returns", " ".join(prose_context(r, host)), re.I))})
        if adm["extra"]:
            disagreements.append({"registry_id": r["registry_id"], "branch": r["branch"], "publisher_domain": lp,
                                  "extra_host_under_current_rule": adm["extra"], "reason": adm["reason"], "linked_from": adm["linked_from"]})
    # rows whose canonical_url host differs from publisher_domain (the corpus adapter's natural fetch host)
    url_host_mismatch = []
    for r in ratified(rows):
        url = s(r.get("canonical_url"))
        if url.startswith("http"):
            h = normalize_host(urlparse(url).netloc)
            if not host_matches(h, s(r.get("publisher_domain"))):
                url_host_mismatch.append({"registry_id": r["registry_id"], "publisher_domain": s(r.get("publisher_domain")), "canonical_url_host": h})

    # ---- 2. sweep: accepted candidates whose chunk host is not the row's publisher_domain
    run_dir = os.path.join(RUNS_DIR, a.run_id, "cells")
    sweep = {"run_id": a.run_id, "manifest_built_at": manifest.get("built_at"), "manifest_workbook": manifest.get("workbook"),
             "cells_scanned": 0, "accepted_candidates": 0, "accepted_off_publisher_domain": [], "chunk_not_found": [],
             "primary_accepted_off_publisher_domain": []}
    chunk_host = {}
    for r in reg.rows:
        for c in store.load_chunks(r["registry_id"]):
            chunk_host[(c["registry_id"], c["locator"])] = normalize_host(urlparse(c.get("source_url") or "").netloc)
    for fn in sorted(os.listdir(run_dir)) if os.path.isdir(run_dir) else []:
        st = json.load(open(os.path.join(run_dir, fn), encoding="utf-8"))
        sweep["cells_scanned"] += 1
        primary = st.get("primary", "sonnet")
        for pk, p in st.get("passes", {}).items():
            for cd in p.get("candidates", []):
                v = st.get("verifications", {}).get(cd["candidate_id"], {})
                fin = (v.get("final") or {}).get("verdict")
                prim = (v.get(primary) or {}).get("verdict")
                if fin not in ACCEPTS and prim not in ACCEPTS:
                    continue
                row = reg.by_id.get(cd["registry_id"])
                pub = s(row.get("publisher_domain")) if row else ""
                host = chunk_host.get((cd["registry_id"], cd["locator"]))
                if host is None:
                    sweep["chunk_not_found"].append((st["queue_id"], cd["candidate_id"]))
                    continue
                rec = {"queue_id": st["queue_id"], "candidate_id": cd["candidate_id"], "registry_id": cd["registry_id"],
                       "locator": cd["locator"], "chunk_host": host, "publisher_domain": pub, "final": fin, "primary": prim}
                if fin in ACCEPTS:
                    sweep["accepted_candidates"] += 1
                    if not host_matches(host, pub):
                        sweep["accepted_off_publisher_domain"].append(rec)
                elif prim in ACCEPTS and not host_matches(host, pub):
                    sweep["primary_accepted_off_publisher_domain"].append(rec)
    # corpus rows fetched from a host outside publisher_domain (manifest urls)
    corpus_off_host = []
    for rid, m in manifest.get("standards", {}).items():
        row = reg.by_id.get(rid)
        if not row:
            continue
        pub = s(row.get("publisher_domain"))
        hosts = sorted({normalize_host(urlparse(u.get("url", "")).netloc) for u in m.get("urls", []) if u.get("url", "").startswith("http")})
        off = [h for h in hosts if not host_matches(h, pub)]
        if off:
            corpus_off_host.append({"registry_id": rid, "publisher_domain": pub, "fetched_hosts": hosts, "off_publisher_domain": off, "n_chunks": m.get("n_chunks")})

    # ---- 3. Gate 2 R001 re-evaluation over the queue
    flips, checked = [], 0
    for c in queue:
        urls = [u for u in (c["authority_url"], c["text_url"]) if u.startswith("http")]
        if not urls or c["retired"] or c["display_role"] == "LINEAGE ONLY":
            continue
        for u in urls:
            checked += 1
            ko, ro, _ = resolve_row(old_idx, c["branch"], u)
            kn, rn, _ = resolve_row(new_idx, c["branch"], u)
            if (ko is None) != (kn is None) or ro != rn:
                flips.append({"queue_id": c["queue_id"], "branch": c["branch"], "rendered_state": c["rendered_state"], "url": u,
                              "retired_parser": f"{ko}:{ro}" if ko else "REFUSED", "current_rule": f"{kn}:{rn}" if kn else "REFUSED"})
    r001 = {"citation_urls_checked": checked, "flips": flips,
            "refused_under_current_rule": [f for f in flips if f["current_rule"] == "REFUSED"],
            "newly_admitted_under_current_rule": [f for f in flips if f["retired_parser"] == "REFUSED"]}

    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "workbook": os.path.basename(reg.path),
              "app_master_version": reg.app_master_version, "controlled_storage_policy": s(reg.config.get("controlled_storage_policy")),
              "parser_rule": PARSER_RULE, "allowlist_per_branch": per_branch, "disagreements": disagreements, "refused_rows": refused,
              "canonical_url_host_not_publisher_domain": url_host_mismatch, "sweep": sweep, "corpus_fetched_off_publisher_domain": corpus_off_host,
              "gate2_r001": r001}
    os.makedirs(RUNS_DIR, exist_ok=True)
    with open(os.path.join(RUNS_DIR, "allowlist-audit.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1); fh.write("\n")
    md = render(report)
    with open(os.path.join(RUNS_DIR, "allowlist-audit.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    print(md)
    return 0


def render(rep):
    L = [f"# R001 allowlist audit — {rep['workbook']} ({rep['app_master_version']}) · {rep['generated_at']}\n",
         "No model calls. Nothing here writes to the workbook.\n", "## 1. Parser rule\n", rep["parser_rule"] + "\n",
         f"APP CONFIG `controlled_storage_policy` = {rep['controlled_storage_policy'] or 'unset'}.\n",
         "## 2. Effective allowlist per branch — retired parser vs current rule\n"]
    for br, v in rep["allowlist_per_branch"].items():
        L.append(f"### {br}\n")
        L.append("| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |")
        L.append("|---|---|---|")
        for d in sorted(set(v["retired_parser"]) | set(v["current_rule"])):
            L.append(f"| {d} | {v['retired_parser'].get(d, '—')} | {v['current_rule'].get(d, '—')} |")
        L.append("")
    L.append("## 3. Rows where the two rules disagree\n")
    L.append("| row | branch | publisher_domain | host the retired parser also admitted | the prose that admitted it | inverted (prose disqualifies the host) | still admitted for the branch via another row |")
    L.append("|---|---|---|---|---|---|---|")
    for d in rep["disagreements"]:
        if "extra_host_under_retired_parser" in d:
            L.append(f"| {d['registry_id']} | {d['branch']} | {d['publisher_domain']} | **{d['extra_host_under_retired_parser']}** | {'; '.join(d['prose']) or '(URL host)'} | "
                     f"{'YES' if d['inverted'] else 'no'} | {'yes' if d['still_admitted_for_branch_via_other_row'] else 'no'} |")
    L.append("")
    ac15 = [d for d in rep["disagreements"] if "extra_host_under_current_rule" in d]
    L.append("AC-15 admissions under the current rule: " + ("; ".join(f"{d['registry_id']} → {', '.join(d['extra_host_under_current_rule'])} ({d['reason']})" for d in ac15) or "none") + ".\n")
    L.append("Rows REFUSED under the current rule: " + ("; ".join(f"{r['registry_id']} ({r['publisher_domain']}): {r['reason']}" for r in rep["refused_rows"]) or "none") + ".\n")
    L.append("Rows whose canonical_url host is not their publisher_domain: " + ("; ".join(f"{r['registry_id']} ({r['publisher_domain']} vs {r['canonical_url_host']})" for r in rep["canonical_url_host_not_publisher_domain"]) or "none") + ".\n")
    sw = rep["sweep"]
    L.append(f"## 4. Sweep of {sw['run_id']} — accepted candidates whose chunk host is not the row's publisher_domain\n")
    L.append(f"Chunk store: manifest built {sw['manifest_built_at']} from {sw['manifest_workbook']}. Cells scanned {sw['cells_scanned']}; candidates with a final ACCEPT/ACCEPT_WITH_CAVEAT {sw['accepted_candidates']}; "
             f"**off publisher_domain: {len(sw['accepted_off_publisher_domain'])}** (cells: {', '.join(sorted({x['queue_id'] for x in sw['accepted_off_publisher_domain']})) or 'none'}); "
             f"primary-accepted but finally rejected and off-domain: {len(sw['primary_accepted_off_publisher_domain'])}; chunk not found: {len(sw['chunk_not_found'])}.\n")
    if sw["accepted_off_publisher_domain"]:
        L.append("| cell | candidate | row | locator | chunk host | publisher_domain | final |")
        L.append("|---|---|---|---|---|---|---|")
        for x in sw["accepted_off_publisher_domain"]:
            L.append(f"| {x['queue_id']} | {x['candidate_id']} | {x['registry_id']} | {x['locator'][:50]} | {x['chunk_host']} | {x['publisher_domain']} | {x['final']} |")
        L.append("")
    L.append("Registry rows whose corpus was fetched from a host outside their publisher_domain (manifest fetch log): "
             + ("; ".join(f"{r['registry_id']} ({r['publisher_domain']}; fetched {', '.join(r['off_publisher_domain'])}; {r['n_chunks']} chunks)" for r in rep["corpus_fetched_off_publisher_domain"]) or "none") + ".\n")
    g = rep["gate2_r001"]
    L.append("## 5. Gate 2 R001 over the queue — admission flips between the two rules\n")
    L.append(f"{g['citation_urls_checked']} citation URLs checked (non-retired rows with a URL). Flips: {len(g['flips'])}; refused under the current rule: {len(g['refused_under_current_rule'])}; newly admitted: {len(g['newly_admitted_under_current_rule'])}.\n")
    if g["flips"]:
        L.append("| cell | branch | state | url | retired parser | current rule |")
        L.append("|---|---|---|---|---|---|")
        for f in g["flips"]:
            L.append(f"| {f['queue_id']} | {f['branch']} | {f['rendered_state']} | {f['url'][:80]} | {f['retired_parser']} | {f['current_rule']} |")
        L.append("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
