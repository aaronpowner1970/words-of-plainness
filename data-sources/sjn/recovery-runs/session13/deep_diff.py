"""Session 13: field-level diff of two packet directories (every card field, not only seats), ignoring build timestamps and paths.
No model calls.   python deep_diff.py <old_dir> <new_dir> [--json out.json]"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SLUGS = ["roman-catholic", "lutheran", "reformed-presbyterian", "baptist", "methodist-wesleyan", "anglican", "mennonite-anabaptist"]
IGNORE = {"built_at", "generated_at", "rebuilt_from", "packet_path", "extract_path", "built", "timestamp"}


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in IGNORE:
                continue
            walk(a.get(k), b.get(k), f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            key = (x.get("candidate_id") if isinstance(x, dict) else None) or i
            walk(x, y, f"{path}[{key}]", out)
    elif a != b:
        out.append({"path": path, "old": a, "new": b})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old_dir")
    ap.add_argument("new_dir")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = {}
    for slug in SLUGS:
        o = json.load(open(os.path.join(a.old_dir, f"{slug}.json"), encoding="utf-8"))
        n = json.load(open(os.path.join(a.new_dir, f"{slug}.json"), encoding="utf-8"))
        oc = {c["queue_id"]: c for c in o.pop("cards")}
        nc = {c["queue_id"]: c for c in n.pop("cards")}
        out = []
        walk(o, n, "header", out)
        for q in sorted(set(oc) | set(nc)):
            walk(oc.get(q), nc.get(q), q, out)
        res[slug] = out
        print(slug, len(out))
        for x in out[:60]:
            print("  ", x["path"], "|", json.dumps(x["old"], ensure_ascii=False)[:160], "->", json.dumps(x["new"], ensure_ascii=False)[:160])
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1); fh.write("\n")


if __name__ == "__main__":
    main()
