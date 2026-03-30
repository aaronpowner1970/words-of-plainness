"""
Build paragraph-level timestamp JSON from ElevenLabs character-level alignment data.

Reads per-chunk alignment JSON files from the alignment/ directory, reconstructs
word-level timestamps, aligns each sentence to its first word, applies cumulative
chunk offsets, then extracts one timestamp per paragraph.

This script is self-contained — it does not depend on any previously written
timestamp JSON file.

Output: src/_data/timestamps/chapter-09-yehoshua-the-man.json
"""

import re
import json
import subprocess
import os

# ── Config ────────────────────────────────────────────────────────────────

CHUNKS_DIR    = r"C:\Users\aaron\Documents\working-folder\ch09-chunks"
ALIGNMENT_DIR = os.path.join(CHUNKS_DIR, "alignment")
CHAPTER_PATH  = r"C:\Users\aaron\Documents\words-of-plainness\src\chapters\09-yehoshua-the-man.md"
OUTPUT_PATH   = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"

# Chunk manifest: (chunk_id, first_sent, last_sent, is_cue, cue_idx)
CHUNKS = [
    ("01",  0,    27,   False, None),
    ("02",  28,   61,   False, None),
    ("03",  62,   85,   False, None),
    ("04",  None, None, True,  385),
    ("05",  86,   111,  False, None),
    ("06",  112,  150,  False, None),
    ("07",  None, None, True,  386),
    ("08",  151,  175,  False, None),
    ("09",  176,  199,  False, None),
    ("10",  None, None, True,  387),
    ("11",  200,  235,  False, None),
    ("12",  236,  277,  False, None),
    ("13",  278,  300,  False, None),
    ("14",  301,  330,  False, None),
    ("15",  331,  342,  False, None),
    ("16",  343,  384,  False, None),
    ("17",  None, None, True,  388),
]

# Paragraph map: paragraph_index -> first_sentence_index
PARAGRAPH_MAP = {
     0:   0,   1:   1,   2:   4,   3:  10,   4:  15,
     5:  23,   6:  30,   7:  33,   8:  36,   9:  38,
    10:  39,  11:  44,  12:  50,  13:  52,  14:  58,
    15:  59,  16:  60,  17:  62,  18:  63,  19:  66,
    20:  73,  21:  75,  22:  77,  23:  80,  24:  86,
    25:  87,  26:  90,  27:  94,  28:  99,  29: 103,
    30: 112,  31: 117,  32: 123,  33: 131,  34: 135,
    35: 137,  36: 138,  37: 140,  38: 141,  39: 144,
    40: 149,  41: 151,  42: 152,  43: 159,  44: 160,
    45: 163,  46: 166,  47: 168,  48: 169,  49: 170,
    50: 175,  51: 176,  52: 182,  53: 187,  54: 190,
    55: 195,  56: 200,  57: 201,  58: 214,  59: 222,
    60: 230,  61: 236,  62: 237,  63: 240,  64: 243,
    65: 246,  66: 247,  67: 250,  68: 254,  69: 255,
    70: 260,  71: 265,  72: 271,  73: 274,  74: 278,
    75: 279,  76: 281,  77: 285,  78: 288,  79: 291,
    80: 294,  81: 296,  82: 299,  83: 301,  84: 302,
    85: 303,  86: 312,  87: 313,  88: 319,  89: 325,
    90: 327,  91: 331,  92: 332,  93: 334,  94: 338,
    95: 340,  96: 343,  97: 344,  98: 350,  99: 352,
   100: 353, 101: 354, 102: 358, 103: 359, 104: 365,
   105: 366, 106: 369, 107: 370, 108: 372, 109: 373,
   110: 375, 111: 378, 112: 379, 113: 380, 114: 382,
   115: 384,
}

# ── Helpers ───────────────────────────────────────────────────────────────

def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def words_of(text):
    return normalize(text).split()

def alignment_to_word_times(alignment):
    """Convert character-level alignment to word-level start/end times."""
    chars  = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends   = alignment.get("character_end_times_seconds", [])

    words = []
    current_word = ""
    word_start = None
    word_end = None

    for i, ch in enumerate(chars):
        s = starts[i] if i < len(starts) else 0.0
        e = ends[i]   if i < len(ends)   else 0.0

        if ch in (" ", "\n", "\t"):
            if current_word.strip():
                words.append({"word": current_word.strip(),
                               "start": word_start, "end": word_end})
            current_word = ""
            word_start = None
        else:
            if word_start is None:
                word_start = s
            current_word += ch
            word_end = e

    if current_word.strip():
        words.append({"word": current_word.strip(),
                       "start": word_start, "end": word_end})
    return words

def find_sentence_start(sent_text, word_times, search_from=0):
    """Find start time of sent_text's first words in word_times."""
    sent_words = words_of(sent_text)
    if not sent_words:
        t = word_times[search_from]["start"] if search_from < len(word_times) else 0.0
        return t, search_from

    first = sent_words[0]
    check_len = min(3, len(sent_words))
    limit = min(search_from + 80, len(word_times))

    for i in range(search_from, limit):
        if normalize(word_times[i]["word"]) == first:
            matches = sum(
                1 for k in range(check_len)
                if i + k < len(word_times) and k < len(sent_words)
                and normalize(word_times[i + k]["word"]) == sent_words[k]
            )
            if matches >= min(2, check_len):
                next_ptr = i + max(len(sent_words) - 1, 1)
                return word_times[i]["start"], next_ptr

    t = word_times[search_from]["start"] if search_from < len(word_times) else 0.0
    return t, search_from + 1

# ── Step 1: Extract prose sentences ───────────────────────────────────────

print("=== Step 1: Extracting sentences from chapter markdown ===")
with open(CHAPTER_PATH, "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'\{%\s*sentence\s+(\d+)\s*%\}(.*?)\{%\s*endsentence\s*%\}'
sentences = {}
for idx_str, raw_text in re.findall(pattern, content, re.DOTALL):
    clean = re.sub(r'\{%.*?%\}', '', raw_text)
    clean = re.sub(r'\{\{.*?\}\}', '', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'[\*_]', '', clean)
    sentences[int(idx_str)] = clean

print(f"  {len(sentences)} sentences extracted")

# ── Step 2: Rebuild sentence timestamps from alignment files ──────────────

print("\n=== Step 2: Rebuilding sentence timestamps from alignment data ===")

sentence_timestamps = {}  # { sentence_idx: global_time_seconds }
cue_timestamps = {}       # { cue_idx: global_time_seconds }
cumulative_offset = 0.0

for chunk_id, first_sent, last_sent, is_cue, cue_idx in CHUNKS:
    chunk_filename = f"ch09_chunk_{chunk_id}.mp3"
    chunk_path = os.path.join(CHUNKS_DIR, chunk_filename)
    alignment_path = os.path.join(ALIGNMENT_DIR, f"chunk_{chunk_id}.json")

    chunk_dur = get_duration(chunk_path)

    if is_cue:
        # Place cue trigger near the END of the cue chunk, not the beginning.
        # The trigger fires when currentTime >= cue_time, then waits 1 second
        # before pausing. Placing it at offset + duration - 2s means the trigger
        # fires 2 seconds before the chunk ends, giving the listener time to hear
        # the cue complete before the panel opens.
        cue_time = round(cumulative_offset + chunk_dur - 2.0, 3)
        cue_timestamps[cue_idx] = cue_time
        print(f"  Chunk {chunk_id}: CUE {cue_idx} -> {cue_time}s (end of cue chunk)")
    else:
        with open(alignment_path, "r", encoding="utf-8") as f:
            alignment = json.load(f)

        word_times = alignment_to_word_times(alignment)
        word_ptr = 0

        for sent_idx in range(first_sent, last_sent + 1):
            sent_text = sentences.get(sent_idx, "")
            chunk_time, word_ptr = find_sentence_start(sent_text, word_times, word_ptr)
            global_time = round(chunk_time + cumulative_offset, 3)
            sentence_timestamps[sent_idx] = global_time

        print(f"  Chunk {chunk_id}: s{first_sent}={sentence_timestamps[first_sent]:.2f}s "
              f"s{last_sent}={sentence_timestamps[last_sent]:.2f}s "
              f"({len(word_times)} words)")

    cumulative_offset = round(cumulative_offset + chunk_dur, 3)

print(f"\n  {len(sentence_timestamps)} sentence timestamps rebuilt")
print(f"  {len(cue_timestamps)} cue timestamps: {cue_timestamps}")

# ── Step 3: Build paragraph timestamps ───────────────────────────────────

print("\n=== Step 3: Building paragraph timestamps ===")

para_timestamps = {}  # { para_idx: global_time_seconds }
missing = []

for para_idx in sorted(PARAGRAPH_MAP.keys()):
    first_sent = PARAGRAPH_MAP[para_idx]
    if first_sent in sentence_timestamps:
        para_timestamps[para_idx] = sentence_timestamps[first_sent]
    else:
        missing.append((para_idx, first_sent))

if missing:
    print(f"  WARNING: {len(missing)} paragraphs had no sentence timestamp")
    for para_idx, sent_idx in missing[:5]:
        print(f"    para {para_idx} -> s{sent_idx} not found")
else:
    print(f"  All {len(para_timestamps)} paragraph timestamps built cleanly")

# ── Step 4: Build sentence-to-paragraph lookup ────────────────────────────

print("\n=== Step 4: Building sentence-to-paragraph lookup ===")

sentence_to_para = {}
para_indices = sorted(PARAGRAPH_MAP.keys())

for i, para_idx in enumerate(para_indices):
    first_sent = PARAGRAPH_MAP[para_idx]
    next_first = PARAGRAPH_MAP[para_indices[i + 1]] if i + 1 < len(para_indices) else 9999
    for s in range(first_sent, next_first):
        sentence_to_para[s] = para_idx

print(f"  {len(sentence_to_para)} sentence-to-paragraph mappings built")

# ── Step 5: Assemble and write output JSON ────────────────────────────────

print("\n=== Step 5: Writing output JSON ===")

output = {}

# Paragraph timestamps: "p{N}" -> seconds
for para_idx, t in sorted(para_timestamps.items()):
    output[f"p{para_idx}"] = round(t, 3)

# Sentence-to-paragraph: "s{N}" -> paragraph_index
for sent_idx, para_idx in sorted(sentence_to_para.items()):
    output[f"s{sent_idx}"] = para_idx

# Cue timestamps: "cue{N}" -> seconds
for cue_idx, t in sorted(cue_timestamps.items()):
    output[f"cue{cue_idx}"] = round(t, 3)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"  {len([k for k in output if k.startswith('p')])} paragraph timestamps")
print(f"  {len([k for k in output if k.startswith('s')])} sentence-to-paragraph mappings")
print(f"  {len([k for k in output if k.startswith('cue')])} cue timestamps")
print(f"  Saved to {OUTPUT_PATH}")

# ── Step 6: Sanity check ──────────────────────────────────────────────────

print("\n=== Sanity Check ===")
checks = [
    ("p0",    "Invocation heading"),
    ("p1",    "By the time the first sandals"),
    ("p17",   "Mastery of Humility heading"),
    ("p23",   "My mother used to remind me"),
    ("p24",   "Mastery of Obedience heading"),
    ("p40",   "You do not lose yourself"),
    ("p41",   "Mastery of Compassion heading"),
    ("p48",   "Jesus wept"),
    ("p56",   "Mastery of Teaching heading"),
    ("p83",   "Mastery of Joy heading"),
    ("p96",   "Benediction heading"),
    ("p115",  "In the name of Jesus Christ"),
    ("cue385", "pause-humility"),
    ("cue386", "pause-obedience"),
    ("cue387", "pause-compassion"),
    ("cue388", "pause-closing"),
]

for key, label in checks:
    if key in output:
        val = output[key]
        if isinstance(val, float):
            mins = int(val // 60)
            secs = val % 60
            print(f"  {key:>8} = {val:>8.3f}s  ({mins}:{secs:06.3f})  {label}")
        else:
            print(f"  {key:>8} = para {val:<4}  {label}")
