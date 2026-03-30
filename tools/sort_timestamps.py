"""
Rebuild chapter-09-yehoshua-the-man.json with all entries in chronological
order. Cue sentences (385-388) are currently appended at the end with
mid-chapter timestamps, which causes confusion. This script reads the
existing JSON, sorts all entries by timestamp value, and rewrites the file
in correct chronological order.
"""
import json

INPUT_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    ts = json.load(f)

# Sort by timestamp value (float), preserving integer key identity
sorted_items = sorted(ts.items(), key=lambda x: float(x[1]))
ts_sorted = {k: v for k, v in sorted_items}

with open(INPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(ts_sorted, f, indent=2)

print(f"Rewritten with {len(ts_sorted)} entries in chronological order.")

# Verify cue positions
for key in ["385", "386", "387", "388"]:
    if key in ts_sorted:
        t = float(ts_sorted[key])
        mins = int(t // 60)
        secs = t % 60
        print(f"  Cue {key}: {t}s ({mins}:{secs:05.2f})")
