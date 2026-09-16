"""Gate 6 session 7: WHY tp-4 lost recall. Three replicates of TP-049 and TP-050 under gate6-v1.3 and gate6-v1.4.

tp-3 (v1.3) accepted both; tp-4 (v1.4) refused both, and that is the whole of the 0.967 -> 0.933 fall. Both are family
RNR-H05 (Son), and TP-049's phrase — "the Father, the Son, and the Holy Ghost" — is a bare enumeration of the persons,
which is exactly the shape gate6-v1.4's JOINT PREDICATION line tells the verifier does NOT assert the property. That
line is written for THE HOLY SPIRIT; the question this measures is whether it leaks onto other families.

One call each way is not a measurement. This is three, per item per version, with the fixture's own chunk and phrase.

  python .../replicate_tp049_tp050.py            # writes the pending jobs (exit 10)
  python scripts/sjn_recovery/api_executor.py --run-id s7-rep-<v>-<n> ...   (the script prints each run id)
  python .../replicate_tp049_tp050.py            # ingests and writes replicate-tp049-tp050.json
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from sjn_recovery.config import RUNS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_predicates  # noqa: E402
from sjn_recovery.llm import LLM  # noqa: E402
from sjn_recovery.agents import CellRunner  # noqa: E402
from sjn_recovery import store, prompts  # noqa: E402

ITEMS = ("TP-049", "TP-050")
VERSIONS = ("gate6-v1.3", "gate6-v1.4")
REPLICATES = 3
ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")


class _PrimaryOnly:
    verifier_routing = "PRIMARY_ONLY"
    fallback_ids = set()

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return False


def main():
    reg = Registry()
    preds = load_predicates(reg.wb)
    fixture = json.load(open(os.path.join(RUNS_DIR, "tp-4", "fixture.json"), encoding="utf-8"))
    items = [i for i in fixture["items"] if i["id"] in ITEMS]
    out_path = os.path.join(HERE, "replicate-tp049-tp050.json")
    results = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    pending = []
    for version in VERSIONS:
        prompts.set_verifier_version(version)
        for n in range(1, REPLICATES + 1):
            run_id = f"s7-rep-{version.replace('gate6-', '')}-{n}"
            llm = LLM(run_id, backend="batch", model="sonnet", log=lambda m: None)
            runner = CellRunner(llm, _PrimaryOnly(), preds, {}, os.path.join(HERE, "rep-state", run_id), "sonnet",
                                ["sonnet"], log=lambda m: None, run_coder=False)
            for it in items:
                chunk = next(c for c in store.load_chunks(it["registry_id"]) if c["locator"] == it["locator"])
                cand = {"candidate_id": f'{it["id"]}-{run_id}', "registry_id": it["registry_id"], "locator": it["locator"],
                        "phrase": it["phrase"], "floor_claim": "FULL", "chunk_text": chunk["text"], "rationale": ""}
                cell = {"queue_id": it["id"], "family_id": it["family_id"], "branch": it["registry_branch"],
                        "predicate": it["predicate"]}
                key = f'{it["id"]}|{version}|{n}'
                r = results.get(key) or {}
                if r.get("status") != "DONE":
                    rub = runner.verify(cell, cand, "sonnet")
                    if rub.get("status") == "PENDING":
                        pending.append(run_id)
                        continue
                    results[key] = {"status": "DONE", "item": it["id"], "version": version, "replicate": n,
                                    "family_id": it["family_id"], "predicate": it["predicate"], "phrase": it["phrase"],
                                    **{k: rub.get(k) for k in ("subject_is_required", "grammatical_subject",
                                                               "speech_act_is_assertion", "floor", "hazard_flags",
                                                               "verdict", "reason_code_final", "reason")}}
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    if pending:
        print(f"== {len(pending)} call(s) pending across run id(s): {sorted(set(pending))}")
        for r in sorted(set(pending)):
            print(f"   python scripts/sjn_recovery/api_executor.py --run-id {r} --workers 4 --max-cost-usd 1 --key-file <.env>")
        return 10
    tally = {}
    for r in results.values():
        tally.setdefault((r["item"], r["version"]), Counter())[r["verdict"] in ACCEPTS] += 1
    print(f'{"item":8} {"version":12} accepted/replicates   verdicts')
    for (item, version), t in sorted(tally.items()):
        vs = [r["verdict"] for r in results.values() if r["item"] == item and r["version"] == version]
        print(f"{item:8} {version:12} {t[True]}/{sum(t.values())}                 {vs}")
    for r in sorted(results.values(), key=lambda x: (x["item"], x["version"], x["replicate"])):
        print(f'   {r["item"]} {r["version"]} #{r["replicate"]}: {r["verdict"]}/{r["reason_code_final"]} '
              f'subj={r["subject_is_required"]} floor={r["floor"]} hz={r["hazard_flags"]}')
        print(f'      {(r["reason"] or "")[:200]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
