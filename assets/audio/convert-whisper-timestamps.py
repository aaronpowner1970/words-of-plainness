#!/usr/bin/env python3
"""
Convert Whisper word-level timestamps to sentence-level timestamps.
Use this after generating audio with Kits.ai and transcribing with Whisper.

Usage:
    # First, transcribe your audio with Whisper:
    whisper chapter-01-narration.mp3 --model medium --output_format json --word_timestamps True
    
    # Then convert to sentence timestamps:
    python convert-whisper-timestamps.py chapter-01-narration.json chapter-01-timestamps.json

Whisper JSON format:
{
    "segments": [
        {
            "words": [
                {"word": "We", "start": 0.0, "end": 0.2},
                {"word": "are", "start": 0.2, "end": 0.4},
                ...
            ]
        }
    ]
}
"""

import json
import sys
import os
import re

def load_sentences(sentences_file="chapter-01-sentences.txt"):
    """Load the sentences from the chapter file."""
    sentences = []
    
    paths_to_try = [
        sentences_file,
        os.path.join(os.path.dirname(__file__), sentences_file),
        os.path.join(os.path.dirname(__file__), "chapter-01-sentences.txt"),
    ]
    
    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        sentences.append(stripped)
            print(f"Loaded {len(sentences)} sentences from {path}")
            return sentences
    
    raise FileNotFoundError(f"Could not find sentences file. Tried: {paths_to_try}")

def normalize_word(word):
    """Normalize a word for comparison."""
    return re.sub(r'[^\w]', '', word.lower())

def extract_words_from_sentence(sentence):
    """Extract normalized words from a sentence."""
    return [normalize_word(w) for w in sentence.split() if normalize_word(w)]

def convert_whisper_timestamps(whisper_data, sentences):
    """
    Convert Whisper word timestamps to sentence timestamps.
    """
    # Flatten all words from all segments
    all_words = []
    for segment in whisper_data.get("segments", []):
        words = segment.get("words", [])
        if words:
            all_words.extend(words)
    
    if not all_words:
        print("Error: No word-level timestamps found in Whisper output")
        print("Make sure you used --word_timestamps True when running Whisper")
        return []
    
    print(f"Found {len(all_words)} words in transcription")
    
    sentence_timestamps = []
    word_index = 0
    
    for sent_idx, sentence in enumerate(sentences):
        sentence_words = extract_words_from_sentence(sentence)
        
        if not sentence_words:
            print(f"Warning: Empty sentence at index {sent_idx}")
            continue
        
        # Find the start of this sentence in the word list
        start_time = None
        end_time = None
        matched_count = 0
        match_start_idx = None
        
        # Search for sentence words in transcription
        search_start = max(0, word_index - 5)  # Allow some backtracking
        
        for i in range(search_start, len(all_words)):
            word_data = all_words[i]
            whisper_word = normalize_word(word_data.get("word", ""))
            
            if matched_count < len(sentence_words):
                target_word = sentence_words[matched_count]
                
                # Check for match (allow partial matches for hyphenated words, etc.)
                if whisper_word == target_word or target_word.startswith(whisper_word) or whisper_word.startswith(target_word):
                    if match_start_idx is None:
                        match_start_idx = i
                        start_time = word_data.get("start")
                    
                    end_time = word_data.get("end")
                    matched_count += 1
                    
                    # Check if we matched enough words (at least 60% or first 3)
                    match_threshold = max(3, len(sentence_words) * 0.6)
                    if matched_count >= match_threshold:
                        # Continue to find the rest
                        pass
                    
                    if matched_count == len(sentence_words):
                        # Found complete sentence
                        word_index = i + 1
                        break
                else:
                    # Reset if we had a partial match that failed
                    if matched_count > 0 and matched_count < 3:
                        matched_count = 0
                        match_start_idx = None
                        start_time = None
        
        if start_time is not None and end_time is not None:
            sentence_timestamps.append({
                "index": sent_idx,
                "start": round(start_time, 3),
                "end": round(end_time, 3)
            })
        else:
            print(f"Warning: Could not match sentence {sent_idx}: '{sentence[:50]}...'")
            # Estimate based on previous sentence
            if sentence_timestamps:
                prev = sentence_timestamps[-1]
                avg_duration = prev["end"] / (len(sentence_timestamps)) if sentence_timestamps else 3.0
                sentence_timestamps.append({
                    "index": sent_idx,
                    "start": round(prev["end"], 3),
                    "end": round(prev["end"] + avg_duration, 3)
                })
        
        # Progress indicator
        if (sent_idx + 1) % 25 == 0:
            print(f"Processed {sent_idx + 1}/{len(sentences)} sentences...")
    
    return sentence_timestamps

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert-whisper-timestamps.py <whisper-output.json> <output.json>")
        print("\nFirst transcribe your audio with Whisper:")
        print("  whisper chapter-01-narration.mp3 --model medium --output_format json --word_timestamps True")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Loading Whisper transcription from: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        whisper_data = json.load(f)
    
    print("Loading sentences...")
    sentences = load_sentences()
    
    print("Converting timestamps...")
    timestamps = convert_whisper_timestamps(whisper_data, sentences)
    
    print(f"Writing {len(timestamps)} timestamps to: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=2)
    
    if timestamps:
        print(f"\nSummary:")
        print(f"  Total sentences: {len(timestamps)}")
        print(f"  Duration: {timestamps[-1]['end']:.1f} seconds ({timestamps[-1]['end']/60:.1f} minutes)")
        print(f"  Average sentence: {timestamps[-1]['end']/len(timestamps):.2f} seconds")
    
    print("\nDone! Copy the contents of the output file into your HTML.")

if __name__ == "__main__":
    main()
