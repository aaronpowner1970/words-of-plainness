#!/usr/bin/env python3
"""
Convert Whisper word-level timestamps to sentence-level timestamps.
Matches sentences from chapter-02-sentences.txt to Whisper transcription.
"""

import json
import re
import sys
from difflib import SequenceMatcher

def normalize_text(text):
    """Normalize text for comparison: lowercase, remove punctuation, collapse spaces."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_sentences(filepath):
    """Load sentences from the extracted sentence file."""
    sentences = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '|' in line:
                idx, text = line.split('|', 1)
                sentences.append({
                    'index': int(idx),
                    'text': text,
                    'normalized': normalize_text(text)
                })
    return sentences

def load_whisper_words(filepath):
    """Load all words with timestamps from Whisper JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_words = []
    for segment in data['segments']:
        if 'words' in segment:
            for word in segment['words']:
                all_words.append({
                    'word': word['word'].strip(),
                    'normalized': normalize_text(word['word']),
                    'start': word['start'],
                    'end': word['end']
                })
    return all_words

def find_sentence_in_words(sentence_normalized, words, start_idx=0, window_size=50):
    """
    Find where a sentence starts and ends in the word list.
    Uses fuzzy matching to handle transcription differences.
    """
    sentence_words = sentence_normalized.split()
    if not sentence_words:
        return None, None, start_idx

    best_match_start = None
    best_match_end = None
    best_score = 0
    best_end_idx = start_idx

    # Search within a window from start_idx
    search_end = min(start_idx + window_size + len(sentence_words) * 2, len(words))

    for i in range(start_idx, search_end):
        # Try matching from this position
        for length in range(len(sentence_words) - 2, len(sentence_words) + 5):
            if i + length > len(words):
                break

            candidate_words = ' '.join(w['normalized'] for w in words[i:i+length])

            # Calculate similarity
            matcher = SequenceMatcher(None, sentence_normalized, candidate_words)
            score = matcher.ratio()

            if score > best_score and score > 0.7:
                best_score = score
                best_match_start = i
                best_match_end = i + length
                best_end_idx = best_match_end

    if best_match_start is not None:
        return (
            words[best_match_start]['start'],
            words[best_match_end - 1]['end'],
            best_end_idx
        )

    return None, None, start_idx

def main():
    sentences_file = 'assets/audio/chapter-02-sentences.txt'
    whisper_file = '/tmp/whisper-ch02/WoP_Ch02_Our_Search_Narration.json'
    output_file = 'assets/audio/chapter-02-timestamps-new.js'

    print("Loading sentences...")
    sentences = load_sentences(sentences_file)
    print(f"  Loaded {len(sentences)} sentences")

    print("Loading Whisper words...")
    words = load_whisper_words(whisper_file)
    print(f"  Loaded {len(words)} words")

    print("\nMatching sentences to timestamps...")
    timestamps = []
    word_idx = 0
    failed_matches = []

    for i, sent in enumerate(sentences):
        start_time, end_time, new_idx = find_sentence_in_words(
            sent['normalized'],
            words,
            start_idx=word_idx,
            window_size=100
        )

        if start_time is not None:
            timestamps.append({
                'index': sent['index'],
                'start': round(start_time, 3),
                'end': round(end_time, 3)
            })
            word_idx = new_idx
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(sentences)} sentences...")
        else:
            # Use previous end time as start, estimate duration
            if timestamps:
                prev_end = timestamps[-1]['end']
                # Estimate ~0.1 seconds per word
                est_duration = max(1.0, len(sent['text'].split()) * 0.15)
                timestamps.append({
                    'index': sent['index'],
                    'start': round(prev_end, 3),
                    'end': round(prev_end + est_duration, 3)
                })
            else:
                timestamps.append({
                    'index': sent['index'],
                    'start': 0.0,
                    'end': 1.0
                })
            failed_matches.append((sent['index'], sent['text'][:50]))

    print(f"\nMatched {len(timestamps) - len(failed_matches)}/{len(sentences)} sentences")

    if failed_matches:
        print(f"\nWarning: {len(failed_matches)} sentences couldn't be matched:")
        for idx, text in failed_matches[:10]:
            print(f"  Index {idx}: {text}...")

    # Generate JavaScript output
    print(f"\nWriting timestamps to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("        const sentenceTimestamps = [\n")
        for ts in timestamps:
            f.write(f"            {{ index: {ts['index']}, start: {ts['start']}, end: {ts['end']} }},\n")
        f.write("        ];\n")

    print(f"Done! Generated {len(timestamps)} timestamp entries")

    # Show some samples
    print("\nSample timestamps:")
    for idx in [0, 10, 11, 50, 100, 150, 200, 250, 293]:
        if idx < len(timestamps):
            ts = timestamps[idx]
            sent = sentences[idx]['text'][:40]
            print(f"  Index {ts['index']:3d}: {ts['start']:8.3f} - {ts['end']:8.3f} | {sent}...")

if __name__ == '__main__':
    main()
