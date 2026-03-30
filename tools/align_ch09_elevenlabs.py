"""
Ch. 9 timestamp alignment using ElevenLabs Speech-to-Text API directly.

Uses the /v1/speech-to-text endpoint with word-level timestamps.
Processes each chunk individually, accumulates time offsets, and writes
the final timestamp JSON to the correct location.

Usage:
    python tools/align_ch09_elevenlabs.py

You will be prompted for your ElevenLabs API key. It is never written
to disk or logged anywhere in this script.
"""

import re
import json
import getpass
import subprocess
import requests

# ── Config ────────────────────────────────────────────────────────────────

CHUNKS_DIR   = r"C:\Users\aaron\Documents\working-folder\ch09-chunks"
CHAPTER_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\chapters\09-yehoshua-the-man.md"
OUTPUT_PATH  = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# ── Chunk manifest ────────────────────────────────────────────────────────
# (filename, first_sentence_idx, last_sentence_idx, is_cue, cue_sentence_idx)

CHUNKS = [
    ("tts_By_th_20260313_212610.mp3",  0,    27,   False, None),  # 01 Invocation pt1
    ("tts_If_He_20260313_212701.mp3",  28,   61,   False, None),  # 02 Invocation pt2
    ("tts_Yehos_20260313_212752.mp3",  62,   85,   False, None),  # 03 Humility
    ("tts_This__20260313_212836.mp3",  None, None, True,  385),   # 04 Cue: pause-humility
    ("tts_Many__20260313_212912.mp3",  86,   111,  False, None),  # 05 Obedience pt1
    ("tts_I_rem_20260313_213004.mp3",  112,  150,  False, None),  # 06 Obedience pt2
    ("tts_Pause_20260313_213102.mp3",  None, None, True,  386),   # 07 Cue: pause-obedience
    ("tts_In_th_20260313_213138.mp3",  151,  175,  False, None),  # 08 Compassion pt1
    ("tts_This__20260313_213228.mp3",  176,  199,  False, None),  # 09 Compassion pt2
    ("tts_Take__20260313_213339.mp3",  None, None, True,  387),   # 10 Cue: pause-compassion
    ("tts_A_sol_20260313_213413.mp3",  200,  235,  False, None),  # 11 Teaching
    ("tts_The_s_20260313_213526.mp3",  236,  277,  False, None),  # 12 Meekness & Courage
    ("tts_The_P_20260313_213653.mp3",  278,  300,  False, None),  # 13 Justice & Mercy
    ("tts_Contr_20260313_213810.mp3",  301,  330,  False, None),  # 14 Joy
    ("tts_This__20260313_213926.mp3",  331,  342,  False, None),  # 15 Beatitudes
    ("tts_Youv__20260313_214047.mp3",  343,  384,  False, None),  # 16 Benediction
    ("tts_Befor_20260313_214213.mp3",  None, None, True,  388),   # 17 Cue: pause-closing
]

# ── Helper: get mp3 duration via ffprobe ──────────────────────────────────

def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

# ── Helper: normalize text for word matching ──────────────────────────────

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_words(text):
    return normalize(text).split()

# ── Helper: align sentence list to ElevenLabs word timestamps ────────────

def align_sentences(sentence_range, sentences, el_words):
    """
    el_words: list of {"text": str, "start": float, "end": float}
    Returns: {sentence_idx: global_start_time}
    """
    result = {}
    word_idx = 0

    for sent_idx in sorted(sentence_range):
        sent_text = sentences.get(sent_idx, "")
        sent_words = get_words(sent_text)

        if not sent_words:
            t = el_words[word_idx]["start"] if word_idx < len(el_words) else 0.0
            result[sent_idx] = round(t, 2)
            continue

        first_word = sent_words[0]
        search_limit = min(word_idx + 80, len(el_words))
        best_pos = word_idx
        found = False

        for candidate in range(word_idx, search_limit):
            if candidate >= len(el_words):
                break
            if normalize(el_words[candidate]["text"]) == first_word:
                # Verify next 1-2 words also match
                match_count = 0
                check_len = min(3, len(sent_words))
                for k in range(check_len):
                    if candidate + k < len(el_words) and k < len(sent_words):
                        if normalize(el_words[candidate + k]["text"]) == sent_words[k]:
                            match_count += 1
                if match_count >= min(2, check_len):
                    best_pos = candidate
                    found = True
                    break

        if not found:
            best_pos = word_idx

        if best_pos < len(el_words):
            result[sent_idx] = round(el_words[best_pos]["start"], 2)
        else:
            prev = result.get(sent_idx - 1, 0.0)
            result[sent_idx] = prev

        word_idx = best_pos + max(len(sent_words) - 1, 1)

    return result

# ── Step 1: Extract prose sentences from chapter markdown ─────────────────

print("=== Step 1: Extracting sentences from chapter markdown ===")
with open(CHAPTER_PATH, "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'\{%\s*sentence\s+(\d+)\s*%\}(.*?)\{%\s*endsentence\s*%\}'
matches = re.findall(pattern, content, re.DOTALL)

sentences = {}
for idx_str, raw_text in matches:
    clean = re.sub(r'\{%.*?%\}', '', raw_text)
    clean = re.sub(r'\{\{.*?\}\}', '', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'\*+', '', clean)
    clean = re.sub(r'_+', '', clean)
    sentences[int(idx_str)] = clean

print(f"  Extracted {len(sentences)} prose sentences")

# ── Step 2: Get API key ───────────────────────────────────────────────────

print("\n=== Step 2: ElevenLabs API key ===")
api_key = getpass.getpass("  Enter your ElevenLabs API key (input hidden): ").strip()
if not api_key:
    print("  ERROR: No API key entered. Exiting.")
    exit(1)
print("  Key received.")

# ── Step 3: Process chunks ────────────────────────────────────────────────

print("\n=== Step 3: Processing chunks ===")

timestamps = {}
cumulative_offset = 0.0

for chunk_num, (filename, first_sent, last_sent, is_cue, cue_idx) in enumerate(CHUNKS, 1):
    chunk_path = f"{CHUNKS_DIR}\\{filename}"
    chunk_dur  = get_duration(chunk_path)

    print(f"\n  Chunk {chunk_num:02d}/{len(CHUNKS)}: {filename}")
    print(f"    Offset: {cumulative_offset:.3f}s | Duration: {chunk_dur:.3f}s")

    if is_cue:
        # Place cue timestamp at offset + 0.5s so the trigger fires
        # after the cue has begun playing.
        cue_time = round(cumulative_offset + 0.5, 2)
        timestamps[str(cue_idx)] = cue_time
        print(f"    CUE sentence {cue_idx} -> {cue_time}s")

    else:
        # Call ElevenLabs STT API with word-level timestamps
        print(f"    Sentences {first_sent}-{last_sent} | Calling ElevenLabs STT...")

        with open(chunk_path, "rb") as audio_file:
            response = requests.post(
                API_URL,
                headers={"xi-api-key": api_key},
                data={
                    "model_id": "scribe_v1",
                    "timestamps_granularity": "word",
                    "language_code": "en",
                },
                files={"file": (filename, audio_file, "audio/mpeg")},
                timeout=120,
            )

        if response.status_code != 200:
            print(f"    ERROR {response.status_code}: {response.text[:200]}")
            print(f"    Falling back to cumulative offset for sentences {first_sent}-{last_sent}")
            for i in range(first_sent, last_sent + 1):
                timestamps[str(i)] = round(cumulative_offset, 2)
        else:
            data = response.json()

            # Extract word list with timestamps
            el_words = []
            words_data = data.get("words", [])
            for w in words_data:
                # ElevenLabs returns type "word" or "spacing" — keep words only
                if w.get("type") == "word" or "start" in w:
                    text = w.get("text", "").strip()
                    start = w.get("start", 0.0)
                    end   = w.get("end", 0.0)
                    if text and start is not None:
                        el_words.append({"text": text, "start": start, "end": end})

            print(f"    Got {len(el_words)} words from ElevenLabs")

            if not el_words:
                print(f"    WARNING: No words returned. Using cumulative offset fallback.")
                for i in range(first_sent, last_sent + 1):
                    timestamps[str(i)] = round(cumulative_offset, 2)
            else:
                sentence_range = range(first_sent, last_sent + 1)
                chunk_sentences = {i: sentences.get(i, "") for i in sentence_range}

                chunk_ts = align_sentences(sentence_range, chunk_sentences, el_words)

                # Apply cumulative offset and store
                for sent_idx, chunk_time in chunk_ts.items():
                    global_time = round(chunk_time + cumulative_offset, 2)
                    timestamps[str(sent_idx)] = global_time

                first_key = str(first_sent)
                last_key  = str(last_sent)
                print(f"    s{first_sent}: {timestamps.get(first_key, '?')}s  |  s{last_sent}: {timestamps.get(last_key, '?')}s")

    cumulative_offset = round(cumulative_offset + chunk_dur, 3)

# ── Step 4: Sort and save ─────────────────────────────────────────────────

print("\n=== Step 4: Saving timestamps ===")
ts_sorted = {str(k): timestamps[str(k)] for k in sorted(int(k) for k in timestamps.keys())}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(ts_sorted, f, indent=2)

print(f"  Saved {len(ts_sorted)} timestamps to:")
print(f"  {OUTPUT_PATH}")

# ── Step 5: Sanity check ──────────────────────────────────────────────────

print("\n=== Sanity Check ===")
checks = [0, 1, 27, 28, 61, 62, 85, 385, 86, 111, 112, 150, 386,
          151, 175, 176, 199, 387, 200, 235, 236, 277, 278, 300,
          301, 330, 331, 342, 343, 384, 388]

for i in checks:
    key = str(i)
    if key in ts_sorted:
        t = ts_sorted[key]
        mins = int(t // 60)
        secs = t % 60
        preview = sentences.get(i, f"[CUE {i}]")[:45]
        print(f"  [{key:>3}] {t:>8.2f}s  ({mins}:{secs:05.2f})  {preview}")

print("\nDone. Commit src/_data/timestamps/chapter-09-yehoshua-the-man.json to deploy.")
