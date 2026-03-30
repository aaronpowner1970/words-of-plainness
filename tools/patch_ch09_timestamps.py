"""
Patch chapter-09-yehoshua-the-man.json.

The stable-ts aligner ran out of words at sentence 326 (2292.7s).
Sentences 327-384 need proportional interpolation based on known anchors.
Sentences 385-388 (narration-only cue lines) need manual placement
derived from the chunk structure of the assembled audio.

Anchor points from the sanity check and known chunk timing:
  [300] 2141.2s  -- Mastery of Joy begins
  [326] 2292.7s  -- last reliably aligned sentence (Joy section end)
  
Known from chunk structure (approximate, based on cumulative chunk durations):
  Chunk 14 (Joy section)      ends ~  2292s
  Chunk 15 (Beatitudes)   starts ~  2292s, ends ~ 2390s  (approx 98s)
  Chunk 16 (Benediction)  starts ~  2390s, ends ~ 2535s  (approx 145s)
  Pause cue 4 (Chunk 17)  starts ~  2535s, ends ~ 2564s  (file end ~2564s)
  
  However ffmpeg output showed total duration 38:23 = 2303s.
  Recalibrating: the 2292.7s ceiling IS near the true file end.
  
  Looking at sentence counts per section from the chapter:
    Joy section (Ch14):         sentences 301-330  (30 sentences, ~120s)
    Beatitudes (Ch15):          sentences 331-342  (12 sentences, ~60s)  
    Benediction (Ch16):         sentences 343-384  (42 sentences, ~180s)
    Cue 1 after Humility:       sentence  385       pause after s85
    Cue 2 after Obedience:      sentence  386       pause after s150
    Cue 3 after Compassion:     sentence  387       pause after s199
    Cue 4 after Benediction:    sentence  388       pause after s384

The file total is 2303.82s. The aligner hit 2292.7 at sentence 326,
which means it was already very near the end of the Joy section.
Sentences 327-384 span from ~2292s to ~2303s — only ~11 seconds of
real remaining audio. That collapse is real: the aligner ran out of
audio words because the Joy + Beatitudes + Benediction chunks produced
fewer Whisper words than the sentence count expected.

Strategy:
  - Sentences 327-384: interpolate linearly from 2292.7s to 2298.0s
    (leaving ~6s before the file end for the final cue)
  - Sentence 385 (Cue 1, Humility): this fires after sentence 85.
    We know sentence 85 is somewhere around 530s from the alignment.
    The cue is INSERTED after s85 in the audio stream — so its timestamp
    must come from the actual audio position, not the prose position.
    Use the known chunk boundary: Chunk 04 (cue 1) follows Chunk 03.
    Chunk 03 ends around s85's audio position. We'll anchor from s85 + 3s gap.
  - Similarly for 386, 387, 388.

Better approach: read the actual aligned timestamps for the sentinel
sentences just before each cue in the prose, then add estimated cue offsets.
"""

import json

TIMESTAMP_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"

with open(TIMESTAMP_PATH, "r", encoding="utf-8") as f:
    ts = json.load(f)

# Convert all values to float
ts = {k: float(v) for k, v in ts.items()}

# ── 1. Interpolate sentences 327-384 ───────────────────────────────────────
# Known good anchor: sentence 326 = 2292.7s
# File end: 2303.82s
# Reserve ~5s for final cue after s384 -> target end for prose = 2298.0s
anchor_start_idx = 326
anchor_start_time = ts["326"]
anchor_end_idx = 384
anchor_end_time = 2298.0

span = anchor_end_idx - anchor_start_idx  # 58 sentences
step = (anchor_end_time - anchor_start_time) / span

print(f"Interpolating sentences 327-384:")
print(f"  From {anchor_start_time}s to {anchor_end_time}s over {span} sentences")
print(f"  Step: {step:.3f}s per sentence")

for i in range(anchor_start_idx + 1, anchor_end_idx + 1):
    new_time = round(anchor_start_time + step * (i - anchor_start_idx), 1)
    ts[str(i)] = new_time

print(f"  Done. Sentence 384 now at {ts['384']}s")

# ── 2. Place the four narration-only cue timestamps ────────────────────────
# These cues are physically inserted into the audio BETWEEN sections.
# Their timestamps must reflect where they actually appear in the assembled MP3.
#
# From the narration script chunk order:
#   Chunk 03 = Humility prose  -> ends after sentence 85
#   Chunk 04 = Cue 1 (pause-humility)
#   Chunk 05 = Obedience prose (sentences 86-111)
#   ...
#   Chunk 06 = Obedience prose cont. (sentences 112-150)
#   Chunk 07 = Cue 2 (pause-obedience)
#   Chunk 08 = Compassion prose (sentences 151-175)
#   Chunk 09 = Compassion prose cont. (sentences 176-199)
#   Chunk 10 = Cue 3 (pause-compassion)
#   ...
#   Chunk 16 = Benediction prose (sentences 343-384)
#   Chunk 17 = Cue 4 (pause-closing)
#
# Each cue is ~12-15 seconds of audio (3 sentences at calm pace).
# Place each cue timestamp = timestamp of the last prose sentence before it + 1s
# (the +1s gives the audio player a beat before the cue fires).

# Cue 1 (index 385): fires after sentence 85
cue1_anchor = ts.get("85", 0.0)
ts["385"] = round(cue1_anchor + 1.0, 1)

# Cue 2 (index 386): fires after sentence 150
cue2_anchor = ts.get("150", 0.0)
ts["386"] = round(cue2_anchor + 1.0, 1)

# Cue 3 (index 387): fires after sentence 199
cue3_anchor = ts.get("199", 0.0)
ts["387"] = round(cue3_anchor + 1.0, 1)

# Cue 4 (index 388): fires after sentence 384 (end of Benediction)
cue4_anchor = ts.get("384", 0.0)
ts["388"] = round(cue4_anchor + 1.0, 1)

print(f"\nCue timestamps placed:")
print(f"  [385] pause-humility  after s85  ({ts['85']}s) -> {ts['385']}s")
print(f"  [386] pause-obedience after s150 ({ts['150']}s) -> {ts['386']}s")
print(f"  [387] pause-compassion after s199 ({ts['199']}s) -> {ts['387']}s")
print(f"  [388] pause-closing   after s384 ({ts['384']}s) -> {ts['388']}s")

# ── 3. Sort and save ────────────────────────────────────────────────────────
ts_sorted = {str(k): ts[str(k)] for k in sorted(int(k) for k in ts.keys())}

with open(TIMESTAMP_PATH, "w", encoding="utf-8") as f:
    json.dump(ts_sorted, f, indent=2)

print(f"\nSaved {len(ts_sorted)} timestamps to {TIMESTAMP_PATH}")

# ── 4. Sanity check ─────────────────────────────────────────────────────────
print("\n=== Sanity Check ===")
for i in [83, 84, 85, 386, 148, 149, 150, 387, 197, 198, 199, 388, 380, 382, 384, 385, 386, 387, 388]:
    key = str(i)
    if key in ts_sorted:
        print(f"  [{key:>3}] {ts_sorted[key]}s")
