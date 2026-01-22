# Audio Narration Workflow Guide
## Words of Plainness - Chapter 1: Introduction

This guide walks you through generating narration audio with synchronized text highlighting using your cloned voice from ElevenLabs or Kits.ai.

---

## Overview

| Item | Value |
|------|-------|
| Total sentences | 175 |
| Estimated duration | 18-22 minutes |
| Output filename | `chapter-01-narration.mp3` |
| Timestamps file | `chapter-01-timestamps.json` |

---

## Option A: ElevenLabs (Recommended)

ElevenLabs provides character-level timestamps that can be converted to sentence timestamps.

### Step 1: Prepare Your Text

1. Open `chapter-01-narration-script.txt`
2. Copy everything below the header line (`============`)
3. This is your narration text

### Step 2: Generate Audio in ElevenLabs

1. Go to [ElevenLabs Speech Synthesis](https://elevenlabs.io/speech-synthesis)
2. Select your cloned voice
3. Paste the chapter text
4. Adjust settings:
   - **Stability**: 50-70% (for consistent narration)
   - **Clarity + Similarity Enhancement**: 75%
   - **Style**: 0% (natural reading)
5. Click **Generate**

### Step 3: Export with Timestamps

**Method A: Projects API (Best Quality)**

1. Create a new Project in ElevenLabs
2. Add the chapter text
3. Generate with your cloned voice
4. Use the API to export with timestamps:

```python
import requests
import json

API_KEY = "your-api-key-here"
PROJECT_ID = "your-project-id"

# Get project with timestamps
response = requests.get(
    f"https://api.elevenlabs.io/v1/projects/{PROJECT_ID}/snapshots",
    headers={"xi-api-key": API_KEY}
)

# The response includes character-level timestamps
data = response.json()
print(json.dumps(data, indent=2))
```

**Method B: Text-to-Speech API with Timestamps**

```python
import requests
import json

API_KEY = "your-api-key-here"
VOICE_ID = "your-voice-id"

# Read the narration text
with open("chapter-01-narration-script.txt", "r") as f:
    text = f.read().split("============")[1].strip()

response = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps",
    headers={
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.75
        }
    }
)

# Save audio
audio_data = response.json()
with open("chapter-01-narration.mp3", "wb") as f:
    f.write(base64.b64decode(audio_data["audio_base64"]))

# Save timestamps
with open("elevenlabs-raw-timestamps.json", "w") as f:
    json.dump(audio_data["alignment"], f, indent=2)
```

### Step 4: Convert Timestamps

Run the provided `convert-timestamps.py` script:

```bash
python convert-timestamps.py elevenlabs-raw-timestamps.json chapter-01-timestamps.json
```

---

## Option B: Kits.ai

Kits.ai doesn't provide automatic timestamps, so you'll need to generate them using audio analysis.

### Step 1: Generate Audio

1. Go to [Kits.ai](https://kits.ai)
2. Select your cloned voice
3. Upload or paste the narration text
4. Generate the audio
5. Download as MP3

### Step 2: Generate Timestamps with Whisper

Use OpenAI's Whisper to transcribe with word-level timestamps:

```bash
# Install whisper
pip install openai-whisper

# Transcribe with timestamps
whisper chapter-01-narration.mp3 --model medium --output_format json --word_timestamps True
```

This creates `chapter-01-narration.json` with word-level timestamps.

### Step 3: Convert to Sentence Timestamps

Run the conversion script:

```bash
python convert-whisper-timestamps.py chapter-01-narration.json chapter-01-timestamps.json
```

---

## Timestamp Conversion Scripts

### For ElevenLabs: `convert-timestamps.py`

```python
#!/usr/bin/env python3
"""
Convert ElevenLabs character-level timestamps to sentence-level timestamps.
"""

import json
import sys
import re

def load_sentences():
    """Load the 175 sentences from the chapter."""
    sentences = []
    with open("chapter-01-sentences.txt", "r") as f:
        for line in f:
            sentences.append(line.strip())
    return sentences

def convert_elevenlabs_timestamps(raw_timestamps, sentences):
    """
    Convert ElevenLabs character timestamps to sentence timestamps.
    
    ElevenLabs format:
    {
        "characters": ["W", "e", " ", "a", "r", "e", ...],
        "character_start_times_seconds": [0.0, 0.05, 0.1, ...],
        "character_end_times_seconds": [0.05, 0.1, 0.15, ...]
    }
    """
    chars = raw_timestamps.get("characters", [])
    starts = raw_timestamps.get("character_start_times_seconds", [])
    ends = raw_timestamps.get("character_end_times_seconds", [])
    
    # Reconstruct full text with character positions
    full_text = "".join(chars)
    
    sentence_timestamps = []
    current_pos = 0
    
    for idx, sentence in enumerate(sentences):
        # Find sentence in full text
        sentence_start = full_text.find(sentence, current_pos)
        if sentence_start == -1:
            # Try fuzzy match (punctuation differences)
            clean_sentence = re.sub(r'[^\w\s]', '', sentence)
            for i in range(current_pos, len(full_text) - len(clean_sentence)):
                chunk = re.sub(r'[^\w\s]', '', full_text[i:i+len(sentence)+20])
                if clean_sentence in chunk:
                    sentence_start = i
                    break
        
        if sentence_start == -1:
            print(f"Warning: Could not find sentence {idx}: {sentence[:50]}...")
            continue
            
        sentence_end = sentence_start + len(sentence)
        
        # Get timestamps for this character range
        start_time = starts[sentence_start] if sentence_start < len(starts) else starts[-1]
        end_time = ends[min(sentence_end - 1, len(ends) - 1)]
        
        sentence_timestamps.append({
            "index": idx,
            "start": round(start_time, 3),
            "end": round(end_time, 3)
        })
        
        current_pos = sentence_end
    
    return sentence_timestamps

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert-timestamps.py <input.json> <output.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(input_file, "r") as f:
        raw_timestamps = json.load(f)
    
    sentences = load_sentences()
    
    timestamps = convert_elevenlabs_timestamps(raw_timestamps, sentences)
    
    with open(output_file, "w") as f:
        json.dump(timestamps, f, indent=2)
    
    print(f"Converted {len(timestamps)} sentence timestamps")
    print(f"Total duration: {timestamps[-1]['end']:.1f} seconds")

if __name__ == "__main__":
    main()
```

### For Kits.ai/Whisper: `convert-whisper-timestamps.py`

```python
#!/usr/bin/env python3
"""
Convert Whisper word-level timestamps to sentence-level timestamps.
"""

import json
import sys
import re

def load_sentences():
    """Load the 175 sentences from the chapter."""
    sentences = []
    with open("chapter-01-sentences.txt", "r") as f:
        for line in f:
            sentences.append(line.strip())
    return sentences

def convert_whisper_timestamps(whisper_data, sentences):
    """
    Convert Whisper word timestamps to sentence timestamps.
    
    Whisper format:
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
    # Flatten all words
    all_words = []
    for segment in whisper_data.get("segments", []):
        for word_data in segment.get("words", []):
            all_words.append(word_data)
    
    # Build full transcription
    full_text = " ".join(w["word"].strip() for w in all_words)
    
    sentence_timestamps = []
    word_index = 0
    
    for idx, sentence in enumerate(sentences):
        # Clean sentence for matching
        sentence_words = sentence.split()
        
        # Find starting word
        start_time = None
        end_time = None
        words_matched = 0
        
        for i in range(word_index, len(all_words)):
            word = all_words[i]["word"].strip().lower()
            word_clean = re.sub(r'[^\w]', '', word)
            
            if words_matched < len(sentence_words):
                target_word = re.sub(r'[^\w]', '', sentence_words[words_matched].lower())
                
                if word_clean == target_word or target_word in word_clean:
                    if start_time is None:
                        start_time = all_words[i]["start"]
                    end_time = all_words[i]["end"]
                    words_matched += 1
                    
                    if words_matched == len(sentence_words):
                        word_index = i + 1
                        break
        
        if start_time is not None:
            sentence_timestamps.append({
                "index": idx,
                "start": round(start_time, 3),
                "end": round(end_time, 3)
            })
        else:
            print(f"Warning: Could not match sentence {idx}: {sentence[:50]}...")
    
    return sentence_timestamps

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert-whisper-timestamps.py <whisper.json> <output.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(input_file, "r") as f:
        whisper_data = json.load(f)
    
    sentences = load_sentences()
    
    timestamps = convert_whisper_timestamps(whisper_data, sentences)
    
    with open(output_file, "w") as f:
        json.dump(timestamps, f, indent=2)
    
    print(f"Converted {len(timestamps)} sentence timestamps")
    if timestamps:
        print(f"Total duration: {timestamps[-1]['end']:.1f} seconds")

if __name__ == "__main__":
    main()
```

---

## Step 5: Integrate into Website

Once you have:
- `chapter-01-narration.mp3` (the audio file)
- `chapter-01-timestamps.json` (the timestamps)

### A. Place Files

```
words-of-plainness/
└── assets/
    └── audio/
        ├── chapter-01-narration.mp3      ← Audio file
        └── chapter-01-timestamps.json    ← Timestamps
```

### B. Update the HTML

In `chapter-01-introduction.html`, find and update the audio source (around line 2132):

**Before:**
```html
<!-- <source src="../../assets/audio/chapter-01.mp3" type="audio/mpeg"> -->
```

**After:**
```html
<source src="../../assets/audio/chapter-01-narration.mp3" type="audio/mpeg">
```

### C. Add Timestamps

Find the `sentenceTimestamps` array (around line 2162) and replace it with your data:

**Before:**
```javascript
const sentenceTimestamps = [
    // Example format - replace with actual timestamps
    // { index: 0, start: 0.0, end: 2.5 },
    // { index: 1, start: 2.5, end: 6.8 },
    // ...
];
```

**After:**
```javascript
const sentenceTimestamps = [
    { index: 0, start: 0.0, end: 2.1 },
    { index: 1, start: 2.1, end: 5.8 },
    { index: 2, start: 5.8, end: 8.4 },
    // ... paste all 175 entries from chapter-01-timestamps.json
];
```

You can paste the entire contents of `chapter-01-timestamps.json` directly into the array.

---

## Quick Method: Manual Timestamp Generation

If API access is limited, you can generate timestamps by:

1. **Recording timestamps manually** while listening to the audio
2. **Using Audacity** with labels:
   - Import audio
   - Press `Ctrl+B` at each sentence break
   - Export labels as text
   - Convert to JSON format

### Audacity Label Format to JSON

```python
#!/usr/bin/env python3
"""Convert Audacity labels to sentence timestamps."""

import json
import sys

def convert_audacity_labels(label_file, output_file):
    timestamps = []
    
    with open(label_file, "r") as f:
        lines = f.readlines()
    
    for idx, line in enumerate(lines):
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            start = float(parts[0])
            end = float(parts[1]) if parts[1] != parts[0] else None
            
            if end is None and idx + 1 < len(lines):
                next_parts = lines[idx + 1].strip().split("\t")
                end = float(next_parts[0])
            
            if end:
                timestamps.append({
                    "index": idx,
                    "start": round(start, 3),
                    "end": round(end, 3)
                })
    
    with open(output_file, "w") as f:
        json.dump(timestamps, f, indent=2)
    
    print(f"Converted {len(timestamps)} timestamps")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python audacity-to-json.py <labels.txt> <output.json>")
    else:
        convert_audacity_labels(sys.argv[1], sys.argv[2])
```

---

## Testing

After integration, test the synchronization:

1. Deploy to Vercel: `vercel --prod`
2. Open the chapter page
3. Click "🎧 Listen to Chapter"
4. Verify:
   - Audio plays
   - Text highlights in sync
   - Autoscroll follows (if enabled)
   - Clicking a sentence jumps to that point in audio

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Audio doesn't play | Check file path, ensure MP3 is in `/assets/audio/` |
| Highlighting doesn't work | Verify `sentenceTimestamps` array is populated |
| Sync is off | Adjust start/end times in timestamps |
| Some sentences skipped | Check for missing index numbers in timestamps |

---

## Files Included

| File | Description |
|------|-------------|
| `chapter-01-narration-script.txt` | Plain text for TTS generation |
| `chapter-01-sentences.txt` | Individual sentences (for timestamp matching) |
| `convert-timestamps.py` | ElevenLabs timestamp converter |
| `convert-whisper-timestamps.py` | Whisper timestamp converter |
| `audacity-to-json.py` | Audacity label converter |

---

**Questions?** Let me know if you need help with any step of this process!
