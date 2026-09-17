"""Session 13, phase 2: enumerate every chunk registered as a creed or definition text, on every branch, with its row, locator,
resolved tier, the registered key's extent and the reason it qualifies. Read only: no model calls, no network, no writes but <out>.

  python data-sources/sjn/recovery-runs/session13/enumerate_registered.py <out.json>

Run once before the phase 2 change (the row-level test) and once after (the explicit section list); before_after.py tables them."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery.registry import Registry, bare_tier  # noqa: E402
from sjn_recovery.config import BRANCHES  # noqa: E402
from sjn_recovery import store  # noqa: E402


def reason(reg, kind, rid, t):
    row = reg.by_id[rid]
    if t.get("section"):
        return f"listed in registered-sections.json ({t['section'].get('what')}); row tier {bare_tier(row.get('authority_tier'))}"
    if kind == "CREED":
        via = ("R6-5 chunk_level_creed_resolution_allowed_rows" if rid in reg.chunk_level_creed_rows
               else f"row bare tier {bare_tier(row.get('authority_tier'))}")
        return f"row-level test: the locator/division names a creed (registry._CREED_LOCATOR) and the row qualifies by {via}"
    return "row-level test: row bare tier CONCILIAR and the locator names a definition, not a canon or anathema (R6-10)"


def main():
    out_path = sys.argv[1]
    reg = Registry()
    out = []
    for b in BRANCHES:
        for kind, texts in (("CREED", reg.registered_creed_texts(b)), ("DEFINITION", reg.registered_definition_texts(b))):
            for t in texts:
                chunk = next((c for c in store.load_chunks(t["registry_id"]) if c["locator"] == t["locator"]), None)
                out.append({"branch": b, "kind": kind, "registry_id": t["registry_id"], "locator": t["locator"], "tier": t["tier"],
                            "chunk_chars": len(chunk["text"]) if chunk else None, "registered_key_words": len(t["key"].split()),
                            "extent": (t.get("section") or {}).get("text_through"), "reason": reason(reg, kind, t["registry_id"], t)})
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"count": len(out), "entries": out}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"{len(out)} registered chunks written to {out_path}")


if __name__ == "__main__":
    main()
