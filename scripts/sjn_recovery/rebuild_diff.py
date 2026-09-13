"""Diff a rebuilt packet against its committed predecessor (session 4, 2026-09-13) — no model calls.

  python scripts/sjn_recovery/rebuild_diff.py --branches anglican,roman-catholic,lutheran,reformed-presbyterian \
         [--base HEAD] [--out data-sources/sjn/recovery-runs/live-1/rebuild-diff-20260913]

For every card it reports what the author asked for after the Lutheran / Reformed review:
  Task 1  cards whose LEAD changed (and whether the new lead is a different speaks_for body or the same body's other
          candidate), and cards that GAINED a body the cap had cut;
  Task 2  cells whose STATE changed under the lower-floor rule (filled -> empty, empty -> filled, all-rejected) and
          the candidates that dropped off a card (with both models' floors);
  Task 4a exhaustion-sourced candidates now marked on cards.
The predecessor is read from git (`git show <base>:<path>`), so the diff is against exactly what was committed."""
import argparse
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import PACKETS_DIR, ROOT, RUNS_DIR  # noqa: E402

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")


def git_show(base, relpath):
    p = subprocess.run(["git", "show", f"{base}:{relpath}"], capture_output=True, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit(f"git show {base}:{relpath} failed: {p.stderr.decode('utf-8', 'replace')[:200]}")
    return json.loads(p.stdout.decode("utf-8"))


def card_index(packet):
    return {c["queue_id"]: c for c in packet["cards"]}


def kept_ids(card):
    return [e["candidate_id"] for e in card.get("candidates", [])]


def lead(card):
    c = card.get("candidates") or []
    return (c[0]["registry_id"], c[0]["candidate_id"]) if c else None


def state_of(card):
    s = str(card.get("status"))
    if s == "DONE":
        return "FILLED" if card.get("candidates") else "EMPTY"
    if s.startswith("EMPTY"):
        return "EMPTY" if not any(r.get("stage") == "verifier" for r in card.get("rejections", [])) else "EMPTY(all-rejected)"
    return s


def group_of(entry, groups):
    return (groups.get(entry["registry_id"]) or {}).get("group") if isinstance(groups.get(entry["registry_id"]), dict) else entry.get("speaks_for_group") or entry["registry_id"]


def diff_branch(slug, base):
    rel = f"data-sources/sjn/recovery-packets/{slug}.json"
    old = git_show(base, rel)
    with open(os.path.join(PACKETS_DIR, f"{slug}.json"), encoding="utf-8") as fh:
        new = json.load(fh)
    oi, ni = card_index(old), card_index(new)
    groups = new.get("speaks_for_groups") or {}
    out = {"branch": new["branch"], "slug": slug, "base": base, "cells": len(ni),
           "lead_changed": [], "lead_changed_to_other_body": 0, "lead_changed_same_body": 0,
           "gained_cut_body": [], "lost_body": [], "state_changed": [], "candidates_dropped": [], "candidates_added": [],
           "exhaustion_marked": [], "chunk_repaired_after_run": new.get("chunk_repaired_after_run") or [],
           "old_counts": {k: old.get(k) for k in ("cells_with_candidates", "cells_empty", "cells_all_rejected")},
           "new_counts": {k: new.get(k) for k in ("cells_with_candidates", "cells_empty", "cells_all_rejected")},
           "uncoded_on_card": []}
    for qid, nc in ni.items():
        oc = oi.get(qid)
        if not oc:
            continue
        ol, nl = lead(oc), lead(nc)
        if ol != nl and (ol is None) == (nl is None) and nl is not None:
            og = group_of(oc["candidates"][0], groups); ng = group_of(nc["candidates"][0], groups)
            other = og != ng
            out["lead_changed"].append({"queue_id": qid, "from": ol[0], "to": nl[0], "from_group": og, "to_group": ng,
                                        "kind": "OTHER_BODY" if other else "SAME_BODY_OTHER_CANDIDATE"})
            out["lead_changed_to_other_body" if other else "lead_changed_same_body"] += 1
        ob = {group_of(e, groups) for e in oc.get("candidates", [])}
        nb = {group_of(e, groups) for e in nc.get("candidates", [])}
        ok, nk = set(kept_ids(oc)), set(kept_ids(nc))
        old_cut = {r.get("candidate_id"): r for r in oc.get("rejections", []) if str(r.get("stage", "")).startswith("tier allocation")}
        gained = sorted(nb - ob)
        if gained:
            out["gained_cut_body"].append({"queue_id": qid, "bodies": gained, "rids": sorted({e["registry_id"] for e in nc["candidates"] if group_of(e, groups) in gained}),
                                           "was_cut_by_cap": [cid for cid in nk - ok if cid in old_cut]})
        if nb - ob == set() and ob - nb:
            out["lost_body"].append({"queue_id": qid, "bodies": sorted(ob - nb)})
        os_, ns_ = state_of(oc), state_of(nc)
        if os_ != ns_:
            out["state_changed"].append({"queue_id": qid, "from": os_, "to": ns_, "predicate": nc.get("predicate")})
        for cid in sorted(ok - nk):
            e = next((x for x in oc["candidates"] if x["candidate_id"] == cid), {})
            nr = next((r for r in nc.get("rejections", []) if r.get("candidate_id") == cid), None)
            fin = (nr or {}).get("final_verdict") or {}
            out["candidates_dropped"].append({"queue_id": qid, "candidate_id": cid, "registry_id": e.get("registry_id"), "locator": e.get("locator"),
                                              "phrase": e.get("phrase"), "now": (nr or {}).get("stage") or "not on card",
                                              "reason": (nr or {}).get("dropped_reason") or (nr or {}).get("reason") or None,
                                              "floors": fin.get("floor_by_model"), "floor_final": fin.get("floor_final"),
                                              "route": fin.get("route"), "final_verdict": fin.get("verdict")})
        for cid in sorted(nk - ok):
            e = next(x for x in nc["candidates"] if x["candidate_id"] == cid)
            out["candidates_added"].append({"queue_id": qid, "candidate_id": cid, "registry_id": e["registry_id"], "locator": e.get("locator"),
                                            "coded": e.get("coder_proposal") is not None})
            if e.get("coder_proposal") is None:
                out["uncoded_on_card"].append(cid)
        for cid in nc.get("exhaustion_sourced_candidates") or []:
            out["exhaustion_marked"].append({"queue_id": qid, "candidate_id": cid})
    return out


def render(diffs):
    L = ["# Packet rebuild diff — session 4 (2026-09-13)", "",
         "Rebuilt from stored candidates and rubrics under the speaks_for candidate-slot diversity rule (Task 1), the lower-floor",
         "verdict rule 2a/2b/2c (Task 2) and the exhaustion mark (Task 4a). No model calls. Base = the committed packet.", "",
         "| branch | cells | lead changed | to another body | same body | gained a cut body | lost a body | state changed | dropped off a card | added to a card | uncoded on card | exhaustion-marked |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in diffs:
        L.append(f"| {d['branch']} | {d['cells']} | {len(d['lead_changed'])} | {d['lead_changed_to_other_body']} | {d['lead_changed_same_body']} | "
                 f"{len(d['gained_cut_body'])} | {len(d['lost_body'])} | {len(d['state_changed'])} | {len(d['candidates_dropped'])} | {len(d['candidates_added'])} | "
                 f"{len(d['uncoded_on_card'])} | {len(d['exhaustion_marked'])} |")
    for d in diffs:
        L += ["", f"## {d['branch']}", "",
              f"Counts before → after: filled {d['old_counts']['cells_with_candidates']} → {d['new_counts']['cells_with_candidates']}, "
              f"empty {d['old_counts']['cells_empty']} → {d['new_counts']['cells_empty']}, all-rejected {d['old_counts']['cells_all_rejected']} → {d['new_counts']['cells_all_rejected']}."]
        if d["state_changed"]:
            L += ["", "**Cells whose state changed (Task 2):**"] + [f"- {x['queue_id']} {x['predicate']}: {x['from']} → {x['to']}" for x in d["state_changed"]]
        if d["candidates_dropped"]:
            L += ["", "**Candidates dropped off a card:**"] + [
                f"- {x['queue_id']} {x['candidate_id']} ({x['registry_id']}, {x['locator']}): now {x['now']}; floors {x['floors']} → {x['floor_final']}; "
                f"route {x['route']}; {x['reason'] or ''}" for x in d["candidates_dropped"]]
        if d["lead_changed"]:
            L += ["", "**Cards whose lead changed (Task 1):**"] + [
                f"- {x['queue_id']}: {x['from']} → {x['to']} ({x['kind']}; {x['from_group']!r} → {x['to_group']!r})" for x in d["lead_changed"]]
        if d["gained_cut_body"]:
            L += ["", "**Cards that gained a body the cap had cut:**"] + [
                f"- {x['queue_id']}: {', '.join(x['rids'])} ({', '.join(x['bodies'])})" + (" — previously cut by the cap" if x["was_cut_by_cap"] else "") for x in d["gained_cut_body"]]
        if d["lost_body"]:
            L += ["", "**Cards that lost a body:**"] + [f"- {x['queue_id']}: {', '.join(x['bodies'])}" for x in d["lost_body"]]
        if d["uncoded_on_card"]:
            L += ["", f"**Now on a card without a coder proposal** ({len(d['uncoded_on_card'])}; the coder ran only on the old allocation): " + ", ".join(d["uncoded_on_card"])]
        if d["exhaustion_marked"]:
            L += ["", "**Exhaustion-sourced candidates marked on cards (Task 4a):** " + ", ".join(f"{x['queue_id']} {x['candidate_id']}" for x in d["exhaustion_marked"])]
        if d["chunk_repaired_after_run"]:
            L += ["", f"**Candidates on chunks repaired after the run** ({len(d['chunk_repaired_after_run'])}): phrase verbatim in both texts, kept with disclosure."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branches", default="anglican,roman-catholic,lutheran,reformed-presbyterian")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--out", default=os.path.join(RUNS_DIR, "live-1", "rebuild-diff-20260913"))
    a = ap.parse_args()
    diffs = [diff_branch(s.strip(), a.base) for s in a.branches.split(",") if s.strip()]
    with open(a.out + ".json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(diffs, fh, ensure_ascii=False, indent=1); fh.write("\n")
    md = render(diffs)
    with open(a.out + ".md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
