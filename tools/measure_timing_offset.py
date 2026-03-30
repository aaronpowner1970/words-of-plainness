"""
Measure the actual offset between ElevenLabs alignment timestamps and the
assembled MP3 audio.

Approach: ElevenLabs reports that the first word "By" in chunk_01 starts at
a specific time within the chunk. After assembly with ffmpeg loudnorm, we need
to know the actual offset of that chunk's start in the assembled file.

We also measure the cumulative chunk durations as reported by ffprobe to
calculate expected positions, then compare to observed playback positions.

Run this and paste output to diagnose the timing offset.
"""

import json
import subprocess
import os

CHUNKS_DIR    = r"C:\Users\aaron\Documents\working-folder\ch09-chunks"
ALIGNMENT_DIR = os.path.join(CHUNKS_DIR, "alignment")

CHUNKS = [
    ("ch09_chunk_01.mp3", False),
    ("ch09_chunk_02.mp3", False),
    ("ch09_chunk_03.mp3", False),
    ("ch09_chunk_04.mp3", True),   # cue
    ("ch09_chunk_05.mp3", False),
    ("ch09_chunk_06.mp3", False),
    ("ch09_chunk_07.mp3", True),   # cue
    ("ch09_chunk_08.mp3", False),
    ("ch09_chunk_09.mp3", False),
    ("ch09_chunk_10.mp3", True),   # cue
    ("ch09_chunk_11.mp3", False),
    ("ch09_chunk_12.mp3", False),
    ("ch09_chunk_13.mp3", False),
    ("ch09_chunk_14.mp3", False),
    ("ch09_chunk_15.mp3", False),
    ("ch09_chunk_16.mp3", False),
    ("ch09_chunk_17.mp3", True),   # cue
]

def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def get_first_word_time(chunk_num):
    """Return the start time of the first character in the alignment data."""
    path = os.path.join(ALIGNMENT_DIR, f"chunk_{chunk_num:02d}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    starts = data.get("character_start_times_seconds", [])
    return starts[0] if starts else 0.0

def get_last_char_time(chunk_num):
    """Return the end time of the last character in the alignment data."""
    path = os.path.join(ALIGNMENT_DIR, f"chunk_{chunk_num:02d}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ends = data.get("character_end_times_seconds", [])
    return ends[-1] if ends else 0.0

print("=== Chunk timing analysis ===\n")
print(f"{'Chunk':<8} {'ffprobe_dur':>12} {'first_char':>12} {'last_char':>12} {'gap_start':>10} {'gap_end':>10}")
print("-" * 70)

cumulative = 0.0
for i, (filename, is_cue) in enumerate(CHUNKS):
    chunk_num = i + 1
    path = os.path.join(CHUNKS_DIR, filename)
    dur = get_duration(path)
    first = get_first_word_time(chunk_num)
    last = get_last_char_time(chunk_num)
    gap_start = first          # silence before first word
    gap_end = dur - last       # silence after last word

    label = f"{chunk_num:02d}{'(cue)' if is_cue else ''}"
    print(f"{label:<8} {dur:>12.3f} {first:>12.3f} {last:>12.3f} {gap_start:>10.3f} {gap_end:>10.3f}")
    cumulative += dur

print(f"\nTotal assembled duration: {cumulative:.3f}s ({int(cumulative//60)}:{cumulative%60:.3f})")

print("\n=== Key insight ===")
print("gap_start = silence before first spoken word in each chunk")
print("gap_end   = silence after last spoken word in each chunk")
print("These silences accumulate across chunks after assembly.")
print("\nFor chunk 01 specifically:")
first_01 = get_first_word_time(1)
dur_01 = get_duration(os.path.join(CHUNKS_DIR, "ch09_chunk_01.mp3"))
print(f"  First word starts at: {first_01:.3f}s within chunk")
print(f"  Chunk duration:       {dur_01:.3f}s")
print(f"  This means s1 timestamp in JSON = {first_01:.3f}s")
print(f"  But audio player shows s1 starting at ~10.4s")
print(f"  Implied offset: {10.391 - first_01:.3f}s")
