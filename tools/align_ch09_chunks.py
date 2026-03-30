"""
Chunk-based alignment for Ch. 9 narration.

Instead of running Whisper on the 38-minute assembled file (which runs
out of word budget), this script runs Whisper on each original chunk MP3
individually, accumulates time offsets between chunks, and merges the
results into a single timestamp JSON.

Chunk order matches concat_list.txt exactly.
Each chunk's timestamps are offset by the cumulative duration of all
preceding chunks so they map correctly into the assembled file.

Cue chunks (04, 07, 10, 17) are aligned as narration-only sentences
385-388 respectively.
"""

import re
import json
import subprocess
import stable_whisper

# ── Chunk manifest ────────────────────────────────────────────────────────
# (filename, first_sentence_index, last_sentence_index, is_cue, cue_sentence_index)
# Sentence indices match the chapter markdown exactly.
# is_cue=True means this chunk contains a pause-point cue line, not prose.

CHUNKS_DIR = r"C:\Users\aaron\Documents\working-folder\ch09-chunks"

CHUNKS = [
    # filename                            first  last   cue    cue_idx
    ("tts_By_th_20260313_212610.mp3",     0,     27,    False, None),   # 01 Invocation pt1
    ("tts_If_He_20260313_212701.mp3",     28,    61,    False, None),   # 02 Invocation pt2
    ("tts_Yehos_20260313_212752.mp3",     62,    85,    False, None),   # 03 Humility
    ("tts_This__20260313_212836.mp3",     None,  None,  True,  385),    # 04 Cue: pause-humility
    ("tts_Many__20260313_212912.mp3",     86,    111,   False, None),   # 05 Obedience pt1
    ("tts_I_rem_20260313_213004.mp3",     112,   150,   False, None),   # 06 Obedience pt2
    ("tts_Pause_20260313_213102.mp3",     None,  None,  True,  386),    # 07 Cue: pause-obedience
    ("tts_In_th_20260313_213138.mp3",     151,   175,   False, None),   # 08 Compassion pt1
    ("tts_This__20260313_213228.mp3",     176,   199,   False, None),   # 09 Compassion pt2
    ("tts_Take__20260313_213339.mp3",     None,  None,  True,  387),    # 10 Cue: pause-compassion
    ("tts_A_sol_20260313_213413.mp3",     200,   235,   False, None),   # 11 Teaching
    ("tts_The_s_20260313_213526.mp3",     236,   277,   False, None),   # 12 Meekness & Courage
    ("tts_The_P_20260313_213653.mp3",     278,   300,   False, None),   # 13 Justice & Mercy
    ("tts_Contr_20260313_213810.mp3",     301,   330,   False, None),   # 14 Joy
    ("tts_This__20260313_213926.mp3",     331,   342,   False, None),   # 15 Beatitudes self-portrait
    ("tts_Youv__20260313_214047.mp3",     343,   384,   False, None),   # 16 Benediction
    ("tts_Befor_20260313_214213.mp3",     None,  None,  True,  388),    # 17 Cue: pause-closing
]

# ── Chapter markdown for sentence extraction ──────────────────────────────
CHAPTER_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\chapters\09-yehoshua-the-man.md"
OUTPUT_PATH  = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"
MODEL_SIZE   = "medium"

# ── Step 1: Extract prose sentences from markdown ─────────────────────────
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

# Cue sentences (narration-only, not in shortcodes)
CUE_SENTENCES = {
    385: "This is a good moment to pause the reflection tabs in the margin invite you to sit with what you just read before we continue free registration saves all your reflection work to a personal report you can return to anytime from the user menu",
    386: "Pause here what you just read is worth more than a passing thought the reflection tabs in the margin are waiting for you free registration saves everything you write to a personal report in your user menu",
    387: "Take a moment here before moving on use the reflection tabs in the margin to sit with this the chapter will wait free registration saves all your reflection work to a personal report you can find in the user menu",
    388: "Before we close the reflection tabs in the margin are waiting what you just read deserves more than a moment free registration saves all your reflection work to a personal report in your user menu",
}

# ── Step 2: Get chunk durations via ffprobe ───────────────────────────────
print("\n=== Step 2: Getting chunk durations via ffprobe ===")

def get_duration(filepath):
    """Return duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

chunk_durations = []
for filename, *_ in CHUNKS:
    path = f"{CHUNKS_DIR}\\{filename}"
    dur = get_duration(path)
    chunk_durations.append(dur)
    print(f"  {filename}: {dur:.2f}s")

# ── Step 3: Load Whisper model once ───────────────────────────────────────
print(f"\n=== Step 3: Loading stable-ts '{MODEL_SIZE}' model ===")
model = stable_whisper.load_model(MODEL_SIZE)
print("  Model loaded.")

# ── Helper: normalize text for matching ───────────────────────────────────
def normalize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_words(text):
    return normalize(text).split()

def align_sentences_to_words(sentence_range, chunk_sentences, whisper_word_times):
    """
    Align a range of sentence indices to Whisper word timestamps.
    Returns dict of {sentence_idx: start_time_in_chunk}.
    """
    result = {}
    whisper_idx = 0

    for sent_idx in sorted(sentence_range):
        sent_text = chunk_sentences.get(sent_idx, "")
        sent_words = get_words(sent_text)

        if not sent_words:
            t = whisper_word_times[whisper_idx]["start"] if whisper_idx < len(whisper_word_times) else 0.0
            result[sent_idx] = round(t, 1)
            continue

        first_word = sent_words[0]
        search_limit = min(whisper_idx + 80, len(whisper_word_times))
        best_pos = whisper_idx
        found = False

        for candidate in range(whisper_idx, search_limit):
            if candidate >= len(whisper_word_times):
                break
            if normalize(whisper_word_times[candidate]["text"]) == first_word:
                match_count = 0
                check_len = min(3, len(sent_words))
                for k in range(check_len):
                    if candidate + k < len(whisper_word_times) and k < len(sent_words):
                        if normalize(whisper_word_times[candidate + k]["text"]) == sent_words[k]:
                            match_count += 1
                if match_count >= min(2, check_len):
                    best_pos = candidate
                    found = True
                    break

        if not found:
            best_pos = whisper_idx

        if best_pos < len(whisper_word_times):
            result[sent_idx] = round(whisper_word_times[best_pos]["start"], 1)
        else:
            last = result.get(sent_idx - 1, 0.0)
            result[sent_idx] = last

        whisper_idx = best_pos + max(len(sent_words) - 1, 1)

    return result

# ── Step 4: Process each chunk ────────────────────────────────────────────
print("\n=== Step 4: Aligning chunks ===")

timestamps = {}
cumulative_offset = 0.0

for chunk_idx, (filename, first_sent, last_sent, is_cue, cue_idx) in enumerate(CHUNKS):
    chunk_path = f"{CHUNKS_DIR}\\{filename}"
    chunk_dur  = chunk_durations[chunk_idx]
    chunk_num  = chunk_idx + 1

    print(f"\n  Chunk {chunk_num:02d}: {filename}")
    print(f"    Offset: {cumulative_offset:.2f}s | Duration: {chunk_dur:.2f}s")

    if is_cue:
        # Cue chunks: timestamp = cumulative offset + 0.5s
        # (half a second in so the cue has started playing before trigger fires)
        cue_time = round(cumulative_offset + 0.5, 1)
        timestamps[str(cue_idx)] = cue_time
        print(f"    Cue sentence {cue_idx} -> {cue_time}s")
    else:
        # Prose chunks: run Whisper and align sentences
        print(f"    Sentences {first_sent}-{last_sent} | Transcribing...")
        result = model.transcribe(chunk_path, language="en")

        whisper_word_times = []
        for segment in result.segments:
            for word in segment.words:
                norm = normalize(word.word)
                if norm:
                    whisper_word_times.append({
                        "text": word.word.strip(),
                        "start": round(word.start, 3),
                        "end": round(word.end, 3)
                    })

        print(f"    Got {len(whisper_word_times)} words from Whisper")

        sentence_range = range(first_sent, last_sent + 1)
        chunk_sentences = {i: sentences.get(i, "") for i in sentence_range}

        chunk_ts = align_sentences_to_words(sentence_range, chunk_sentences, whisper_word_times)

        # Apply cumulative offset and store
        for sent_idx, chunk_time in chunk_ts.items():
            global_time = round(chunk_time + cumulative_offset, 1)
            timestamps[str(sent_idx)] = global_time

        # Sanity: print first and last sentence of this chunk
        first_key = str(first_sent)
        last_key  = str(last_sent)
        print(f"    s{first_sent}: {timestamps.get(first_key, '?')}s | s{last_sent}: {timestamps.get(last_key, '?')}s")

    cumulative_offset = round(cumulative_offset + chunk_dur, 3)

# ── Step 5: Sort and save ─────────────────────────────────────────────────
print("\n=== Step 5: Saving timestamps ===")
ts_sorted = {str(k): timestamps[str(k)] for k in sorted(int(k) for k in timestamps.keys())}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(ts_sorted, f, indent=2)

print(f"  Saved {len(ts_sorted)} timestamps to {OUTPUT_PATH}")

# ── Step 6: Sanity check ──────────────────────────────────────────────────
print("\n=== Sanity Check ===")
checks = [0, 1, 50, 85, 385, 100, 150, 386, 199, 387, 200, 250, 300, 330, 342, 384, 388]
for i in checks:
    key = str(i)
    if key in ts_sorted:
        mins = int(ts_sorted[key] // 60)
        secs = ts_sorted[key] % 60
        preview = sentences.get(i, CUE_SENTENCES.get(i, ""))[:50]
        print(f"  [{key:>3}] {ts_sorted[key]:>8.1f}s ({mins}:{secs:05.2f}) -- {preview}")
