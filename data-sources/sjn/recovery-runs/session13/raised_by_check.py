"""Session 13 stop check (after phase 2): every registered-text hit and every raised_by_registered_text entry in a packet directory
must be a listed registered section (R6-43), and none may be a catechism's, confession's or commentary's section.
  python raised_by_check.py <packets_dir>      exits 1 on any violation"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREATMENT = re.compile(r"catechism|commentary|exposition|explanation|introduction|preface|\bQ\.|Q&A|question", re.I)
SLUGS = ["roman-catholic", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "anglican", "mennonite-anabaptist"]


def main():
    d = sys.argv[1]
    listed = {(e["registry_id"], e["locator"]) for e in json.load(open(os.path.join(HERE, "..", "registered-sections.json"), encoding="utf-8"))["sections"]}
    bad, n_hits, n_raised = [], 0, 0
    for slug in SLUGS:
        for c in json.load(open(os.path.join(d, f"{slug}.json"), encoding="utf-8"))["cards"]:
            for lst in ("candidates", "rejections", "witness_only_candidates"):
                for e in c.get(lst) or []:
                    hits = [("hit", e.get("registered_phrase_hit"))] + [("raised_by", h) for h in e.get("raised_by_registered_text") or []]
                    for what, h in hits:
                        if not h:
                            continue
                        n_hits += what == "hit"; n_raised += what == "raised_by"
                        key = (h["registry_id"], h["locator"])
                        if key not in listed or TREATMENT.search(h["locator"] or ""):
                            bad.append((slug, c["queue_id"], e.get("candidate_id"), what, key))
    print(json.dumps({"registered_phrase_hits": n_hits, "raised_by_entries": n_raised, "violations": bad}, ensure_ascii=False))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
