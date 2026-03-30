"""
Align narration MP3 to sentence boundaries using stable-ts (Whisper forced alignment).
Produces chapter-09-yehoshua-the-man.json with sentence-index -> start-time mapping.
Updated March 2026: new MP3 path, correct chapter path, cue sentences 385-388 added.
"""

import re
import json
import sys
import stable_whisper

# --- Config ---
MP3_PATH = r"C:\Users\aaron\Documents\working-folder\ch09-chunks\NR_09_01_Yehoshua_the_Man.mp3"
CHAPTER_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\chapters\09-yehoshua-the-man.md"
OUTPUT_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"
MODEL_SIZE = "medium"  # balance of accuracy and speed

# --- Narration-only cue sentences (not in sentence shortcodes) ---
# These are the four pause-point cue lines read aloud by Jonathan Livingston.
# Text must match the narration script exactly for alignment to work.
NARRATION_ONLY_SENTENCES = {
    385: "This is a good moment to pause. The reflection tabs in the margin invite you to sit with what you just read before we continue. Free registration saves all your reflection work to a personal report you can return to anytime from the user menu.",
    386: "Pause here. What you just read is worth more than a passing thought the reflection tabs in the margin are waiting for you. Free registration saves everything you write to a personal report in your user menu.",
    387: "Take a moment here before moving on. Use the reflection tabs in the margin to sit with this the chapter will wait. Free registration saves all your reflection work to a personal report you can find in the user menu.",
    388: "Before we close the reflection tabs in the margin are waiting. What you just read deserves more than a moment. Free registration saves all your reflection work to a personal report in your user menu.",
}

# --- Step 1: Extract sentence texts from markdown ---
print("=== Step 1: Extracting sentences from chapter markdown ===")
with open(CHAPTER_PATH, "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'\{%\s*sentence\s+(\d+)\s*%\}(.*?)\{%\s*endsentence\s*%\}'
matches = re.findall(pattern, content, re.DOTALL)

sentences = {}
for idx_str, raw_text in matches:
    # Strip Nunjucks tags, HTML tags, and normalize whitespace
    clean = re.sub(r'\{%.*?%\}', '', raw_text)
    clean = re.sub(r'\{\{.*?\}\}', '', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)  # HTML entities
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Remove markdown formatting
    clean = re.sub(r'\*+', '', clean)
    clean = re.sub(r'_+', '', clean)
    sentences[int(idx_str)] = clean

print(f"  Extracted {len(sentences)} sentences (indices {min(sentences.keys())}-{max(sentences.keys())})")

# Add narration-only cue sentences
for idx, text in NARRATION_ONLY_SENTENCES.items():
    sentences[idx] = text
print(f"  Added {len(NARRATION_ONLY_SENTENCES)} narration-only cue sentences (indices 385-388)")
print(f"  Total sentences to align: {len(sentences)}")

# --- Step 2: Run stable-ts transcription with word-level timestamps ---
print(f"\n=== Step 2: Running stable-ts with '{MODEL_SIZE}' model ===")
print(f"  Loading model...")
model = stable_whisper.load_model(MODEL_SIZE)
print(f"  Transcribing (this may take several minutes for a 38-minute file)...")
result = model.transcribe(MP3_PATH, language="en")

# Collect all words with timestamps
all_words = []
for segment in result.segments:
    for word in segment.words:
        all_words.append({
            "text": word.word.strip(),
            "start": round(word.start, 3),
            "end": round(word.end, 3)
        })

print(f"  Got {len(all_words)} words from transcription")

# --- Step 3: Align sentences to word-level output ---
print("\n=== Step 3: Aligning sentences to word timestamps ===")


def normalize_for_matching(text):
    """Normalize text for fuzzy matching."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_sentence_words(sentence_text):
    """Split sentence into normalized words."""
    normalized = normalize_for_matching(sentence_text)
    return normalized.split()


# Build flat list of whisper words (normalized)
whisper_words_norm = [normalize_for_matching(w["text"]) for w in all_words]
whisper_words_norm = [w for w in whisper_words_norm if w]  # remove empty

# Map normalized whisper words back to their timestamps
whisper_word_times = []
for w in all_words:
    norm = normalize_for_matching(w["text"])
    if norm:
        whisper_word_times.append(w)

print(f"  {len(whisper_word_times)} normalized whisper words")

# Sequential alignment: walk through whisper words matching sentence words
timestamps = {}
whisper_idx = 0

for sent_idx in sorted(sentences.keys()):
    sent_text = sentences[sent_idx]
    sent_words = get_sentence_words(sent_text)

    if not sent_words:
        # Empty sentence (e.g., just a heading tag)
        if whisper_idx < len(whisper_word_times):
            timestamps[str(sent_idx)] = round(whisper_word_times[whisper_idx]["start"], 1)
        else:
            timestamps[str(sent_idx)] = timestamps.get(str(sent_idx - 1), 0.0)
        continue

    # Find best match starting from current whisper position
    best_pos = whisper_idx
    first_word = sent_words[0]

    # Look ahead up to 100 words for the first word match
    search_limit = min(whisper_idx + 100, len(whisper_word_times))
    found = False

    for candidate in range(whisper_idx, search_limit):
        if candidate >= len(whisper_word_times):
            break
        candidate_word = normalize_for_matching(whisper_word_times[candidate]["text"])
        if candidate_word == first_word:
            # Check if next few words also match
            match_count = 0
            check_len = min(3, len(sent_words))
            for k in range(check_len):
                if (candidate + k < len(whisper_word_times) and
                        k < len(sent_words)):
                    w_norm = normalize_for_matching(whisper_word_times[candidate + k]["text"])
                    if w_norm == sent_words[k]:
                        match_count += 1
            if match_count >= min(2, check_len):
                best_pos = candidate
                found = True
                break

    if not found and whisper_idx < len(whisper_word_times):
        # Fallback: just use current position
        best_pos = whisper_idx

    if best_pos < len(whisper_word_times):
        timestamps[str(sent_idx)] = round(whisper_word_times[best_pos]["start"], 1)
    else:
        timestamps[str(sent_idx)] = timestamps.get(str(sent_idx - 1), 0.0)

    # Advance whisper pointer past this sentence's approximate word count
    whisper_idx = best_pos + max(len(sent_words) - 1, 1)

print(f"  Aligned {len(timestamps)} sentences")

# --- Step 4: Save output ---
print(f"\n=== Step 4: Saving to {OUTPUT_PATH} ===")
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(timestamps, f, indent=2)

print(f"  Done! {len(timestamps)} timestamps written.")

# Quick sanity check
print("\n=== Sanity Check ===")
for i in [0, 1, 2, 50, 100, 200, 300, 384, 385, 386, 387, 388]:
    key = str(i)
    if key in timestamps:
        preview = sentences.get(i, "")[:60]
        print(f"  [{key}] {timestamps[key]}s -- {preview}...")
