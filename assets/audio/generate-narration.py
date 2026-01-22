#!/usr/bin/env python3
"""
Words of Plainness - Chapter 1 Narration Generator
Uses ElevenLabs API to generate audio with synchronized timestamps.

SETUP:
1. Install required package:  pip install requests
2. Edit the configuration below with your API key and Voice ID
3. Run:  python generate-narration.py
"""

import requests
import json
import os
import sys
import time

# ============================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================

API_KEY = "your-api-key-here"  # Paste your ElevenLabs API key
VOICE_ID = "your-voice-id-here"  # Paste your Voice ID

# Voice settings (adjust to taste)
STABILITY = 0.6  # 0.0-1.0: Lower = more expressive, Higher = more consistent
SIMILARITY_BOOST = 0.75  # 0.0-1.0: How closely to match your voice
STYLE = 0.0  # 0.0-1.0: Style exaggeration (0 for narration)

# Output files
OUTPUT_AUDIO = "chapter-01-narration.mp3"
OUTPUT_TIMESTAMPS = "chapter-01-timestamps.json"

# ============================================================
# DO NOT EDIT BELOW THIS LINE
# ============================================================

def load_narration_text():
    """Load the narration script."""
    script_file = "chapter-01-narration-script.txt"
    
    if not os.path.exists(script_file):
        print(f"ERROR: Cannot find {script_file}")
        print("Make sure this file is in the same folder as this script.")
        sys.exit(1)
    
    with open(script_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract text after the header line
    if "============" in content:
        text = content.split("============")[1].strip()
    else:
        text = content.strip()
    
    print(f"Loaded narration text: {len(text):,} characters")
    return text

def load_sentences():
    """Load individual sentences for timestamp matching."""
    sentences_file = "chapter-01-sentences.txt"
    
    if not os.path.exists(sentences_file):
        print(f"ERROR: Cannot find {sentences_file}")
        print("Make sure this file is in the same folder as this script.")
        sys.exit(1)
    
    sentences = []
    with open(sentences_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                sentences.append(stripped)
    
    print(f"Loaded {len(sentences)} sentences")
    return sentences

def generate_audio_with_timestamps(text):
    """Generate audio using ElevenLabs API with timestamps."""
    
    print("\nGenerating audio with ElevenLabs...")
    print("This may take a few minutes for a long text...")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"
    
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": STABILITY,
            "similarity_boost": SIMILARITY_BOOST,
            "style": STYLE,
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=600)
        
        if response.status_code == 401:
            print("ERROR: Invalid API key. Check your API_KEY value.")
            sys.exit(1)
        elif response.status_code == 404:
            print("ERROR: Voice not found. Check your VOICE_ID value.")
            sys.exit(1)
        elif response.status_code != 200:
            print(f"ERROR: API request failed with status {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        result = response.json()
        return result
        
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out. The text may be too long.")
        print("Try breaking it into smaller sections.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        sys.exit(1)

def save_audio(audio_base64):
    """Save the audio file from base64."""
    import base64
    
    audio_bytes = base64.b64decode(audio_base64)
    
    with open(OUTPUT_AUDIO, "wb") as f:
        f.write(audio_bytes)
    
    size_mb = len(audio_bytes) / (1024 * 1024)
    print(f"Saved audio: {OUTPUT_AUDIO} ({size_mb:.1f} MB)")

def convert_to_sentence_timestamps(alignment, sentences):
    """Convert character-level timestamps to sentence timestamps."""
    
    print("\nConverting timestamps to sentence level...")
    
    characters = alignment.get("characters", [])
    char_starts = alignment.get("character_start_times_seconds", [])
    char_ends = alignment.get("character_end_times_seconds", [])
    
    if not characters or not char_starts:
        print("WARNING: No timestamp data in API response")
        return []
    
    # Reconstruct full text
    full_text = "".join(characters)
    
    sentence_timestamps = []
    current_pos = 0
    
    for idx, sentence in enumerate(sentences):
        # Find sentence in the full text
        pos = full_text.lower().find(sentence.lower(), current_pos)
        
        if pos == -1:
            # Try finding first few words
            words = sentence.split()[:4]
            search_text = " ".join(words).lower()
            pos = full_text.lower().find(search_text, current_pos)
        
        if pos == -1:
            print(f"  Warning: Could not locate sentence {idx}: '{sentence[:40]}...'")
            # Estimate based on previous
            if sentence_timestamps:
                prev = sentence_timestamps[-1]
                sentence_timestamps.append({
                    "index": idx,
                    "start": round(prev["end"], 3),
                    "end": round(prev["end"] + 3.0, 3)
                })
            continue
        
        # Get timestamps
        start_char = min(pos, len(char_starts) - 1)
        end_char = min(pos + len(sentence) - 1, len(char_ends) - 1)
        
        start_time = char_starts[start_char]
        end_time = char_ends[end_char]
        
        sentence_timestamps.append({
            "index": idx,
            "start": round(start_time, 3),
            "end": round(end_time, 3)
        })
        
        current_pos = pos + len(sentence)
        
        # Progress
        if (idx + 1) % 25 == 0:
            print(f"  Processed {idx + 1}/{len(sentences)} sentences...")
    
    return sentence_timestamps

def save_timestamps(timestamps):
    """Save timestamps as JSON."""
    with open(OUTPUT_TIMESTAMPS, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=2)
    
    print(f"Saved timestamps: {OUTPUT_TIMESTAMPS}")

def generate_js_code(timestamps):
    """Generate JavaScript code for pasting into HTML."""
    js_file = "chapter-01-timestamps-js.txt"
    
    lines = ["const sentenceTimestamps = ["]
    for ts in timestamps:
        lines.append(f'    {{ index: {ts["index"]}, start: {ts["start"]}, end: {ts["end"]} }},')
    lines.append("];")
    
    js_code = "\n".join(lines)
    
    with open(js_file, "w", encoding="utf-8") as f:
        f.write(js_code)
    
    print(f"Saved JS code: {js_file}")
    print("\n" + "=" * 50)
    print("Copy the contents of this file into your HTML")
    print("(Replace the sentenceTimestamps array around line 2162)")
    print("=" * 50)

def main():
    print("=" * 50)
    print("Words of Plainness - Narration Generator")
    print("=" * 50)
    
    # Check configuration
    if API_KEY == "your-api-key-here":
        print("\nERROR: Please edit this script and add your API key.")
        print("Open this file and replace 'your-api-key-here' with your actual key.")
        sys.exit(1)
    
    if VOICE_ID == "your-voice-id-here":
        print("\nERROR: Please edit this script and add your Voice ID.")
        print("Open this file and replace 'your-voice-id-here' with your actual Voice ID.")
        sys.exit(1)
    
    # Load files
    narration_text = load_narration_text()
    sentences = load_sentences()
    
    # Estimate credits
    print(f"\nThis will use approximately {len(narration_text):,} credits.")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Generate audio
    start_time = time.time()
    result = generate_audio_with_timestamps(narration_text)
    
    # Save audio
    if "audio_base64" in result:
        save_audio(result["audio_base64"])
    else:
        print("ERROR: No audio in response")
        print(json.dumps(result, indent=2))
        sys.exit(1)
    
    # Process timestamps
    if "alignment" in result:
        timestamps = convert_to_sentence_timestamps(result["alignment"], sentences)
        save_timestamps(timestamps)
        generate_js_code(timestamps)
        
        # Summary
        elapsed = time.time() - start_time
        duration = timestamps[-1]["end"] if timestamps else 0
        
        print(f"\n" + "=" * 50)
        print("COMPLETE!")
        print(f"=" * 50)
        print(f"Audio duration: {duration/60:.1f} minutes")
        print(f"Processing time: {elapsed/60:.1f} minutes")
        print(f"Sentences matched: {len(timestamps)}/{len(sentences)}")
        print(f"\nFiles created:")
        print(f"  - {OUTPUT_AUDIO}")
        print(f"  - {OUTPUT_TIMESTAMPS}")
        print(f"  - chapter-01-timestamps-js.txt")
    else:
        print("\nWARNING: No alignment data in response.")
        print("Audio was saved, but you'll need to generate timestamps separately.")
        print("Use Whisper: whisper chapter-01-narration.mp3 --word_timestamps True")

if __name__ == "__main__":
    main()
