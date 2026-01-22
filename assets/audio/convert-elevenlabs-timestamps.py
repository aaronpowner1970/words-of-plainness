#!/usr/bin/env python3
"""
Convert ElevenLabs character-level timestamps to sentence-level timestamps.

Usage:
    python convert-elevenlabs-timestamps.py <elevenlabs-output.json> <output-timestamps.json>

ElevenLabs alignment format:
{
    "characters": ["W", "e", " ", "a", "r", "e", ...],
    "character_start_times_seconds": [0.0, 0.05, 0.1, ...],
    "character_end_times_seconds": [0.05, 0.1, 0.15, ...]
}
"""

import json
import sys
import os
import re

def load_sentences(sentences_file="chapter-01-sentences.txt"):
    """Load the sentences from the chapter file."""
    sentences = []
    
    # Try multiple paths
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

def normalize_text(text):
    """Normalize text for comparison."""
    # Convert to lowercase, remove extra whitespace
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def find_sentence_in_text(sentence, full_text, start_pos=0):
    """
    Find a sentence in the full text, allowing for minor variations.
    Returns (start_pos, end_pos) or (-1, -1) if not found.
    """
    sentence_norm = normalize_text(sentence)
    full_text_norm = normalize_text(full_text)
    
    # Try exact match first
    idx = full_text_norm.find(sentence_norm, start_pos)
    if idx != -1:
        return idx, idx + len(sentence_norm)
    
    # Try matching without punctuation
    sentence_words = re.findall(r'\w+', sentence_norm)
    if not sentence_words:
        return -1, -1
    
    # Look for the first few words
    first_words = ' '.join(sentence_words[:5])
    idx = full_text_norm.find(first_words, start_pos)
    
    if idx != -1:
        # Find where this sentence likely ends
        last_words = ' '.join(sentence_words[-3:])
        end_search_start = idx + len(first_words)
        end_idx = full_text_norm.find(last_words, end_search_start)
        
        if end_idx != -1:
            return idx, end_idx + len(last_words)
        else:
            # Estimate end based on sentence length
            return idx, idx + len(sentence_norm)
    
    return -1, -1

def convert_elevenlabs_timestamps(raw_timestamps, sentences):
    """
    Convert ElevenLabs character timestamps to sentence timestamps.
    """
    chars = raw_timestamps.get("characters", [])
    starts = raw_timestamps.get("character_start_times_seconds", [])
    ends = raw_timestamps.get("character_end_times_seconds", [])
    
    if not chars or not starts or not ends:
        print("Error: Missing timestamp data in input file")
        print(f"Keys found: {list(raw_timestamps.keys())}")
        return []
    
    # Reconstruct full text
    full_text = "".join(chars)
    print(f"Full text length: {len(full_text)} characters")
    print(f"Timestamp entries: {len(starts)}")
    
    sentence_timestamps = []
    current_pos = 0
    
    for idx, sentence in enumerate(sentences):
        start_idx, end_idx = find_sentence_in_text(sentence, full_text, current_pos)
        
        if start_idx == -1:
            print(f"Warning: Could not find sentence {idx}: '{sentence[:60]}...'")
            # Try to estimate based on previous sentence
            if sentence_timestamps:
                prev = sentence_timestamps[-1]
                estimated_duration = 3.0  # Default estimate
                sentence_timestamps.append({
                    "index": idx,
                    "start": round(prev["end"], 3),
                    "end": round(prev["end"] + estimated_duration, 3),
                    "estimated": True
                })
            continue
        
        # Get timestamps for character range
        # Clamp indices to valid range
        start_char_idx = min(start_idx, len(starts) - 1)
        end_char_idx = min(end_idx - 1, len(ends) - 1)
        
        start_time = starts[start_char_idx]
        end_time = ends[end_char_idx]
        
        sentence_timestamps.append({
            "index": idx,
            "start": round(start_time, 3),
            "end": round(end_time, 3)
        })
        
        current_pos = end_idx
        
        # Progress indicator
        if (idx + 1) % 25 == 0:
            print(f"Processed {idx + 1}/{len(sentences)} sentences...")
    
    return sentence_timestamps

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert-elevenlabs-timestamps.py <input.json> <output.json>")
        print("\nInput file should be the ElevenLabs alignment/timestamps JSON")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Loading timestamps from: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        raw_timestamps = json.load(f)
    
    print("Loading sentences...")
    sentences = load_sentences()
    
    print("Converting timestamps...")
    timestamps = convert_elevenlabs_timestamps(raw_timestamps, sentences)
    
    # Remove 'estimated' flag before saving
    for ts in timestamps:
        ts.pop("estimated", None)
    
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
