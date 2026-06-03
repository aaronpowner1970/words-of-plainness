"""
generate_card_audio.py — ElevenLabs Card-Tab Narration Pipeline
================================================================

Generates pre-cached TTS audio for card-chapter Practice and Blesses
tabs using Aaron's ElevenLabs voice. Produces individual MP3 files per
tab and a combined timing manifest for the frontend Read Aloud player.

This replaces browser-native TTS with high-quality, consistent audio
using the ministry's own voice.

WHAT IT DOES
============
1. Reads a card-chapter .njk file and extracts YAML frontmatter.
2. For each card, extracts the 'practice' and 'blesses' HTML content.
3. Strips HTML to clean prose suitable for narration.
4. Calls ElevenLabs /v1/text-to-speech/{voice_id}/with-timestamps
   for each tab (one API call per tab).
5. Runs two-pass loudnorm on each MP3 (mandatory for browser seeking).
6. Saves final MP3s with naming convention:
     CC_{chapter}_{card}_{tab}.mp3
     e.g., CC_12_01_practice.mp3, CC_12_01_blesses.mp3
7. Outputs a timing manifest JSON for word-level highlighting:
     card-audio-{chapter}-{slug}.json

USAGE
=====
    python tools/generate_card_audio.py <chapter-file.njk>

    Example:
    python tools/generate_card_audio.py src/chapters/12-beatitudes.njk

    Options:
    --card N        Generate only card N (1-indexed)
    --tab practice  Generate only the practice tab (or blesses)
    --dry-run       Show what would be generated without calling API
    --output-dir    Override output directory (default: working-folder/card-audio/)

OUTPUT
======
    MP3 files   -> {output_dir}/CC_{ch}_{card}_{tab}.mp3
    Manifest    -> {output_dir}/card-audio-manifest.json
    Alignment   -> {output_dir}/alignment/CC_{ch}_{card}_{tab}.json

COST ESTIMATE
=============
    Typical card tab: ~250 words / ~1,500 characters
    ElevenLabs Multilingual v2: ~$0.12 per 1K characters
    One card (2 tabs): ~$0.36
    One chapter (5 cards): ~$1.80
    All 17 card-chapters: ~$30 total

FFMPEG REQUIREMENT
==================
    ffmpeg and ffprobe must be on PATH for two-pass loudnorm.

Words of Plainness — Aaron Powner Publishing
"""

import json
import base64
import getpass
import urllib.request
import urllib.error
import subprocess
import re
import os
import sys
import html
import tempfile

# ── Config ────────────────────────────────────────────────────────────────

EL_API_BASE = "https://api.elevenlabs.io"
VOICE_AARON = "As8zJaZyH4MAgaQ93FMc"
MODEL_ID = "eleven_multilingual_v2"

# Voice settings — Aaron prose narration (card-chapter tabs)
# Slightly warmer than standard prose for the shorter, more intimate
# card-tab format. Stability raised slightly for consistency across
# short segments.
VOICE_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.80,
    "style": 0.15,
    "use_speaker_boost": True,
}

# Loudnorm target (matches all WoP audio)
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"

DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.expanduser("~"), "Documents", "working-folder", "card-audio"
)

# ── YAML Frontmatter Parser ──────────────────────────────────────────────
# Card-chapter .njk files use YAML frontmatter with complex nested
# structures including multiline HTML in pipe blocks. We need a parser
# that handles this correctly without requiring PyYAML (keeping the
# stdlib-only pattern).

def parse_njk_frontmatter(filepath):
    """
    Extract YAML frontmatter from a .njk file and parse it.
    Returns the raw YAML string between --- delimiters.
    We use PyYAML for this since the frontmatter contains complex
    nested structures with pipe blocks.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract between first and second ---
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"ERROR: Could not find YAML frontmatter in {filepath}")
        sys.exit(1)

    yaml_text = parts[1]

    try:
        import yaml
        data = yaml.safe_load(yaml_text)
        return data
    except ImportError:
        print("ERROR: PyYAML is required for parsing card-chapter frontmatter.")
        print("  Install with: pip install pyyaml --break-system-packages")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to parse YAML frontmatter: {e}")
        sys.exit(1)


# ── HTML to Narration Text ───────────────────────────────────────────────

def html_to_narration_text(html_content):
    """
    Convert card tab HTML to clean narration text.

    Handles:
    - Strips all HTML tags
    - Decodes HTML entities
    - Removes scripture citation parentheticals for narration
      (per Gate 2 rule: strip citation references from spoken audio)
    - Preserves em-dashes and typographic punctuation
    - Collapses whitespace
    - Strips bridge-text paragraphs (these are transitional UI text,
      not narrated content)
    """
    text = html_content

    # Remove bridge-text paragraphs entirely (UI transition text)
    text = re.sub(r'<p\s+class="bridge-text"[^>]*>.*?</p>', '', text, flags=re.DOTALL)

    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    text = html.unescape(text)

    # Remove parenthetical scripture citations like (Matthew 5:3–4)
    # But keep quoted scripture text that's woven into prose
    text = re.sub(r'\s*\([A-Z0-9][^)]*\d+:\d+[^)]*\)', '', text)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove any leftover empty parentheses
    text = re.sub(r'\(\s*\)', '', text)

    return text


# ── ElevenLabs API ───────────────────────────────────────────────────────

def call_tts_with_timestamps(api_key, text):
    """
    Call ElevenLabs /v1/text-to-speech/{voice_id}/with-timestamps.
    Returns (audio_bytes, alignment_data).
    
    Note: output_format is a query parameter, not a body parameter.
    """
    url = f"{EL_API_BASE}/v1/text-to-speech/{VOICE_AARON}/with-timestamps?output_format=mp3_44100_128"
    payload = json.dumps({
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": VOICE_SETTINGS,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=180) as resp:
        response_data = json.loads(resp.read())

    audio_bytes = base64.b64decode(response_data["audio_base64"])
    alignment = response_data.get("alignment", {})
    return audio_bytes, alignment


def alignment_to_word_times(alignment):
    """
    Convert character-level alignment to word-level timing data.
    Returns list of {"word": str, "start": float, "end": float}
    """
    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])

    if not chars:
        return []

    words = []
    current_word = ""
    word_start = None
    word_end = None

    for i, ch in enumerate(chars):
        s = starts[i] if i < len(starts) else 0.0
        e = ends[i] if i < len(ends) else 0.0

        if ch in (" ", "\n", "\t"):
            if current_word.strip():
                words.append({
                    "word": current_word.strip(),
                    "start": round(word_start, 4),
                    "end": round(word_end, 4)
                })
            current_word = ""
            word_start = None
        else:
            if word_start is None:
                word_start = s
            current_word += ch
            word_end = e

    if current_word.strip():
        words.append({
            "word": current_word.strip(),
            "start": round(word_start, 4),
            "end": round(word_end, 4)
        })

    return words


# ── ffmpeg Two-Pass Loudnorm ─────────────────────────────────────────────

def two_pass_loudnorm(input_path, output_path):
    """
    Two-pass loudnorm processing (mandatory for all WoP audio).
    Pass 1: decode to WAV with loudnorm
    Pass 2: encode to MP3 with proper Xing seek header
    """
    # Create temp WAV in same directory
    temp_wav = input_path.replace(".mp3", "_intermediate.wav")

    try:
        # Pass 1: loudnorm to WAV
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-af", LOUDNORM,
            temp_wav
        ], capture_output=True, check=True)

        # Pass 2: WAV to MP3 with proper headers
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_wav,
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            "-id3v2_version", "3",
            output_path
        ], capture_output=True, check=True)

    finally:
        # Clean up intermediate WAV
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


def get_duration(path):
    """Get MP3 duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ── Main Pipeline ────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate ElevenLabs narration for card-chapter tabs"
    )
    parser.add_argument("njk_file", help="Path to card-chapter .njk file")
    parser.add_argument("--card", type=int, default=None,
                        help="Generate only this card number (1-indexed)")
    parser.add_argument("--tab", choices=["practice", "blesses"], default=None,
                        help="Generate only this tab")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be generated without calling API")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for MP3 and manifest files")

    args = parser.parse_args()

    # ── Parse frontmatter ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  WoP Card-Tab Narration Pipeline")
    print(f"{'='*60}")
    print(f"\n  Source: {args.njk_file}")

    frontmatter = parse_njk_frontmatter(args.njk_file)
    chapter_num = frontmatter.get("chapter", 0)
    chapter_slug = frontmatter.get("slug", f"{chapter_num}-unknown")
    chapter_title = frontmatter.get("title", "Unknown")
    cards = frontmatter.get("cards", [])

    print(f"  Chapter {chapter_num}: {chapter_title}")
    print(f"  Cards: {len(cards)}")

    # ── Set up output directories ────────────────────────────────────────
    output_dir = args.output_dir
    alignment_dir = os.path.join(output_dir, "alignment")
    os.makedirs(alignment_dir, exist_ok=True)
    print(f"  Output: {output_dir}")

    # ── Build work list ──────────────────────────────────────────────────
    tabs_to_process = ["practice", "blesses"]
    work = []

    for card_idx, card in enumerate(cards, 1):
        if args.card and card_idx != args.card:
            continue

        card_title = card.get("title", f"Card {card_idx}")

        for tab in tabs_to_process:
            if args.tab and tab != args.tab:
                continue

            html_content = card.get(tab, "")
            if not html_content:
                print(f"  WARNING: Card {card_idx} has no '{tab}' content — skipping")
                continue

            narration_text = html_to_narration_text(html_content)
            char_count = len(narration_text)
            word_count = len(narration_text.split())

            file_prefix = f"CC_{chapter_num:02d}_{card_idx:02d}_{tab}"

            work.append({
                "card_idx": card_idx,
                "card_title": card_title,
                "tab": tab,
                "narration_text": narration_text,
                "char_count": char_count,
                "word_count": word_count,
                "file_prefix": file_prefix,
            })

    # ── Summary ──────────────────────────────────────────────────────────
    total_chars = sum(w["char_count"] for w in work)
    total_words = sum(w["word_count"] for w in work)
    est_cost = (total_chars / 1000) * 0.12

    print(f"\n  Work items: {len(work)} tabs to narrate")
    print(f"  Total: {total_words:,} words / {total_chars:,} characters")
    print(f"  Estimated cost: ${est_cost:.2f}")

    print(f"\n  {'Card':<5} {'Tab':<10} {'Words':<8} {'Chars':<8} {'File'}")
    print(f"  {'-'*5} {'-'*10} {'-'*8} {'-'*8} {'-'*30}")
    for w in work:
        print(f"  {w['card_idx']:<5} {w['tab']:<10} {w['word_count']:<8} "
              f"{w['char_count']:<8} {w['file_prefix']}.mp3")

    if args.dry_run:
        print(f"\n  DRY RUN — no API calls made.")
        print(f"\n  Narration text preview:")
        for w in work:
            print(f"\n  --- {w['file_prefix']} ({w['card_title']}, {w['tab']}) ---")
            preview = w["narration_text"][:300]
            if len(w["narration_text"]) > 300:
                preview += "..."
            print(f"  {preview}")
        return

    # ── Get API key ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    api_key = getpass.getpass("  Enter your ElevenLabs API key (hidden): ").strip()
    if not api_key:
        print("  No key entered. Exiting.")
        sys.exit(1)

    # ── Confirm ──────────────────────────────────────────────────────────
    confirm = input(f"\n  Generate {len(work)} audio files (~${est_cost:.2f})? [y/N]: ").strip()
    if confirm.lower() != 'y':
        print("  Cancelled.")
        return

    # ── Generate ─────────────────────────────────────────────────────────
    manifest = {
        "chapter": chapter_num,
        "slug": chapter_slug,
        "title": chapter_title,
        "generated": None,
        "tabs": {}
    }

    from datetime import datetime
    manifest["generated"] = datetime.now().isoformat()

    for i, w in enumerate(work, 1):
        print(f"\n  [{i}/{len(work)}] {w['file_prefix']} "
              f"({w['card_title']}, {w['tab']}) — {w['word_count']} words")

        # Call ElevenLabs
        try:
            audio_bytes, alignment = call_tts_with_timestamps(
                api_key, w["narration_text"]
            )
        except urllib.error.HTTPError as e:
            body = b''
            try:
                body = e.read()
            except:
                pass
            print(f"    HTTP ERROR {e.code}")
            print(f"    Response: {body[:500]}")
            print(f"    URL: {e.url if hasattr(e, 'url') else 'unknown'}")
            print(f"    Text length: {len(w['narration_text'])} chars")
            print(f"    Text preview: {w['narration_text'][:100]}...")
            print(f"    Stopping. Previous files are preserved.")
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"    URL ERROR: {e.reason}")
            print(f"    This is likely a network/firewall issue.")
            sys.exit(1)
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            sys.exit(1)

        # Save raw MP3
        raw_path = os.path.join(output_dir, f"{w['file_prefix']}_raw.mp3")
        with open(raw_path, "wb") as f:
            f.write(audio_bytes)

        raw_size = len(audio_bytes)
        print(f"    Raw audio: {raw_size:,} bytes")

        # Save alignment JSON
        align_path = os.path.join(alignment_dir, f"{w['file_prefix']}.json")
        with open(align_path, "w", encoding="utf-8") as f:
            json.dump(alignment, f, indent=2)

        # Two-pass loudnorm
        final_path = os.path.join(output_dir, f"{w['file_prefix']}.mp3")
        print(f"    Running two-pass loudnorm...")
        two_pass_loudnorm(raw_path, final_path)

        # Get final duration
        duration = get_duration(final_path)
        final_size = os.path.getsize(final_path)
        print(f"    Final: {duration:.2f}s, {final_size:,} bytes")

        # Build word-level timing from alignment
        word_times = alignment_to_word_times(alignment)

        # Calculate loudnorm time scaling factor
        # The alignment data is from the raw audio; loudnorm changes duration
        raw_duration = get_duration(raw_path)
        time_scale = duration / raw_duration if raw_duration > 0 else 1.0

        # Apply scaling to word times
        scaled_words = []
        for wt in word_times:
            scaled_words.append({
                "word": wt["word"],
                "start": round(wt["start"] * time_scale, 4),
                "end": round(wt["end"] * time_scale, 4),
            })

        # Add to manifest
        tab_key = f"card{w['card_idx']}_{w['tab']}"
        manifest["tabs"][tab_key] = {
            "card": w["card_idx"],
            "cardTitle": w["card_title"],
            "tab": w["tab"],
            "file": f"{w['file_prefix']}.mp3",
            "duration": round(duration, 3),
            "wordCount": w["word_count"],
            "charCount": w["char_count"],
            "words": scaled_words,
        }

        # Clean up raw file
        os.remove(raw_path)
        print(f"    ✓ Complete")

    # ── Save manifest ────────────────────────────────────────────────────
    manifest_path = os.path.join(output_dir, f"card-audio-{chapter_slug}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"{'='*60}")
    print(f"\n  Generated {len(work)} audio files:")
    total_duration = sum(t["duration"] for t in manifest["tabs"].values())
    for key, tab_data in manifest["tabs"].items():
        print(f"    {tab_data['file']}  ({tab_data['duration']:.1f}s)")
    print(f"\n  Total audio: {total_duration:.1f}s")
    print(f"  Manifest: {manifest_path}")

    # ── Next steps ───────────────────────────────────────────────────────
    print(f"\n  NEXT STEPS:")
    print(f"  1. Review audio files in: {output_dir}")
    print(f"  2. Upload MP3s to R2:")
    for key, tab_data in manifest["tabs"].items():
        mp3 = tab_data["file"]
        print(f"       npx wrangler r2 object put wop-media/web/{mp3} "
              f"--file=\"{os.path.join(output_dir, mp3)}\" "
              f"--content-type=\"audio/mpeg\"")
    print(f"  3. Upload manifest to R2:")
    manifest_name = f"card-audio-{chapter_slug}.json"
    print(f"       npx wrangler r2 object put wop-media/web/{manifest_name} "
          f"--file=\"{manifest_path}\" "
          f"--content-type=\"application/json\"")
    print(f"  4. Update read-aloud.js to check for pre-generated audio")
    print(f"       (fetch manifest from CDN, use cached audio + word times")
    print(f"        when available, fall back to browser TTS otherwise)")


if __name__ == "__main__":
    main()
