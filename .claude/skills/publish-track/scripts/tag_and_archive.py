#!/usr/bin/env python3
"""
WoP Publish Skill — Tag & Archive
===================================
Tags audio files with ID3v2.4 metadata and creates the three-tier
archive structure (Archive WAV, Distribution WAV, Web MP3).

Called by the /publish skill pipeline at Steps 3–4.

USAGE (called by Claude Code, not typically run standalone):
    python tag_and_archive.py \
        --source mastered.wav \
        --filename "04_2_When_God_Becomes_Real_Soul_Worship" \
        --title "When God Becomes Real" \
        --style "Soul Worship" \
        --prefix "##" \
        --chapter 4 \
        --version 2 \
        --track-num 7 \
        --archive-dir ./WoP-Audio/01-Archive-Masters \
        --distro-dir ./WoP-Audio/02-Distribution-WAVs \
        --web-dir ./WoP-Audio/03-Web-MP3s \
        [--art cover_3000x3000.jpg] \
        [--dry-run]

DEPENDENCIES:
    pip install mutagen Pillow
    ffmpeg (system)
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.id3 import (
        TIT2, TPE1, TPE2, TALB, TRCK, TDRC, TCON,
        COMM, TCOM, TCOP, TXXX, APIC
    )
    MUTAGEN_OK = True
except ImportError:
    MUTAGEN_OK = False

try:
    from PIL import Image
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False


# ── DEFAULTS (from reference/id3-defaults.md) ──────────────────────
DEFAULTS = {
    "artist": "Words of Plainness",
    "album_artist": "Words of Plainness",
    "album": "Words of Plainness: Musical Testimonies",
    "year": "2026",
    "genre": "Christian / Sacred",
    "composer": "Aaron J Powner",
    "copyright": "© 2026 Aaron J Powner",
    "comment": "A Christ-Centered Ministry — words-of-plainness.vercel.app",
}


def check_ffmpeg():
    """Verify ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def load_album_art(art_path):
    """Load and validate album art. Returns (bytes, mime_type) or (None, None)."""
    if not art_path or not os.path.exists(art_path):
        return None, None

    if PILLOW_OK:
        img = Image.open(art_path)
        w, h = img.size
        if w < 3000 or h < 3000:
            print(f"  ⚠  Album art is {w}×{h}px — 3000×3000 recommended")
        if w != h:
            print(f"  ⚠  Album art is not square ({w}×{h}) — may display cropped")

    with open(art_path, "rb") as f:
        art_data = f.read()

    mime = "image/png" if art_path.lower().endswith(".png") else "image/jpeg"
    return art_data, mime


def apply_id3_tags(filepath, metadata, art_data=None, art_mime=None):
    """Apply ID3v2.4 tags to MP3 or WAV file."""
    ext = Path(filepath).suffix.lower()

    if ext == ".mp3":
        audio = MP3(filepath)
    elif ext == ".wav":
        audio = WAVE(filepath)
    else:
        print(f"  ⚠  Unsupported format: {ext}")
        return False

    try:
        audio.add_tags()
    except Exception:
        pass  # Tags already exist

    tags = audio.tags

    # Core tags
    tags.add(TIT2(encoding=3, text=metadata["title"]))
    tags.add(TPE1(encoding=3, text=metadata.get("artist", DEFAULTS["artist"])))
    tags.add(TPE2(encoding=3, text=DEFAULTS["album_artist"]))
    tags.add(TALB(encoding=3, text=metadata.get("album", DEFAULTS["album"])))
    tags.add(TCON(encoding=3, text=metadata.get("genre", DEFAULTS["genre"])))
    tags.add(TCOM(encoding=3, text=metadata.get("composer", DEFAULTS["composer"])))
    tags.add(TCOP(encoding=3, text=metadata.get("copyright", DEFAULTS["copyright"])))

    if metadata.get("track_num"):
        tags.add(TRCK(encoding=3, text=str(metadata["track_num"])))
    tags.add(TDRC(encoding=3, text=metadata.get("year", DEFAULTS["year"])))

    # Comment
    tags.add(COMM(
        encoding=3, lang="eng", desc="",
        text=metadata.get("comment", DEFAULTS["comment"])
    ))

    # ISRC placeholder
    isrc = metadata.get("isrc", "")
    if isrc:
        tags.add(TXXX(encoding=3, desc="ISRC", text=isrc))

    # Album art
    if art_data:
        tags.add(APIC(
            encoding=3,
            mime=art_mime or "image/jpeg",
            type=3,  # Cover (front)
            desc="Cover",
            data=art_data,
        ))

    audio.save()
    return True


def create_three_tiers(source_wav, filename, archive_dir, distro_dir, web_dir, dry_run=False):
    """
    Create the three-tier archive from a mastered WAV.
    Returns dict of {tier: filepath} for successfully created files.
    """
    results = {}

    archive_path = os.path.join(archive_dir, f"{filename}.wav")
    distro_path = os.path.join(distro_dir, f"{filename}.wav")
    web_path = os.path.join(web_dir, f"{filename}.mp3")

    # Tier 1: Archive Master (copy original resolution)
    if dry_run:
        print(f"  🔍 Would copy → {archive_path}")
    else:
        os.makedirs(archive_dir, exist_ok=True)
        shutil.copy2(source_wav, archive_path)
        print(f"  ✓  Archive Master: {archive_path}")
    results["archive"] = archive_path

    # Tier 2: Distribution Master (16-bit 44.1kHz WAV)
    if dry_run:
        print(f"  🔍 Would convert → {distro_path}")
    else:
        os.makedirs(distro_dir, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-y", "-i", source_wav,
            "-ar", "44100", "-sample_fmt", "s16", "-c:a", "pcm_s16le",
            distro_path
        ], capture_output=True, check=True)
        print(f"  ✓  Distribution WAV: {distro_path}")
    results["distro"] = distro_path

    # Tier 3: Web Master (320kbps MP3)
    if dry_run:
        print(f"  🔍 Would encode → {web_path}")
    else:
        os.makedirs(web_dir, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-y", "-i", source_wav,
            "-codec:a", "libmp3lame", "-b:a", "320k",
            web_path
        ], capture_output=True, check=True)
        print(f"  ✓  Web MP3: {web_path}")
    results["web"] = web_path

    return results


def measure_duration(filepath):
    """Measure audio duration via ffprobe. Returns M:SS string."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", filepath],
            capture_output=True, text=True, check=True
        )
        seconds = float(result.stdout.strip())
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    except Exception as e:
        print(f"  ⚠  Could not measure duration: {e}")
        return "—"


def main():
    parser = argparse.ArgumentParser(
        description="WoP Publish Skill — Tag & Archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--source", required=True, help="Path to mastered WAV")
    parser.add_argument("--filename", required=True, help="Canonical filename (no extension)")
    parser.add_argument("--title", required=True, help="Song title")
    parser.add_argument("--style", default="", help="Style descriptor")
    parser.add_argument("--prefix", default="##", help="Track type prefix")
    parser.add_argument("--chapter", type=int, default=0, help="Chapter number (if applicable)")
    parser.add_argument("--version", type=int, default=1, help="Version number")
    parser.add_argument("--track-num", type=int, default=0, help="Track number in album")
    parser.add_argument("--album", default=DEFAULTS["album"], help="Album name")
    parser.add_argument("--isrc", default="", help="ISRC code (if known)")
    parser.add_argument("--art", default=None, help="Path to album art (JPEG/PNG)")
    parser.add_argument("--archive-dir", default="WoP-Audio/01-Archive-Masters")
    parser.add_argument("--distro-dir", default="WoP-Audio/02-Distribution-WAVs")
    parser.add_argument("--web-dir", default="WoP-Audio/03-Web-MP3s")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()

    # ── Dependency checks ──
    if not MUTAGEN_OK:
        print("ERROR: mutagen not installed. Run: pip install mutagen")
        sys.exit(1)
    if not check_ffmpeg():
        print("ERROR: ffmpeg not found. Install ffmpeg.")
        sys.exit(1)
    if not os.path.exists(args.source):
        print(f"ERROR: Source file not found: {args.source}")
        sys.exit(1)

    print(f"\n{'═' * 60}")
    print(f"  WoP Publish — Tag & Archive")
    print(f"{'═' * 60}")
    print(f"  Source:   {args.source}")
    print(f"  Filename: {args.filename}")
    print(f"  Title:    {args.title}")
    print(f"  Style:    {args.style or '(none)'}")
    print(f"  Dry run:  {args.dry_run}")
    print(f"{'═' * 60}\n")

    # ── Load album art ──
    art_data, art_mime = load_album_art(args.art)
    if art_data:
        print(f"✓ Album art loaded: {args.art}\n")

    # ── Step 3: Create three-tier archive ──
    print("── Creating Three-Tier Archive ──")
    tiers = create_three_tiers(
        args.source, args.filename,
        args.archive_dir, args.distro_dir, args.web_dir,
        dry_run=args.dry_run
    )

    # ── Step 4: Tag all three tiers ──
    metadata = {
        "title": args.title,
        "artist": DEFAULTS["artist"],
        "album": args.album,
        "genre": DEFAULTS["genre"],
        "composer": DEFAULTS["composer"],
        "copyright": DEFAULTS["copyright"],
        "year": DEFAULTS["year"],
        "comment": DEFAULTS["comment"],
        "track_num": args.track_num if args.track_num else "",
        "isrc": args.isrc,
    }

    if not args.dry_run:
        print("\n── Embedding ID3 Tags ──")
        for tier_name, filepath in tiers.items():
            if os.path.exists(filepath):
                ok = apply_id3_tags(filepath, metadata, art_data, art_mime)
                status = "✓" if ok else "✗"
                print(f"  {status}  Tagged {tier_name}: {os.path.basename(filepath)}")
    else:
        print("\n── Would Tag ──")
        for tier_name, filepath in tiers.items():
            print(f"  🔍 Would tag {tier_name}: {os.path.basename(filepath)}")
        print(f"       Artist:    {metadata['artist']}")
        print(f"       Album:     {metadata['album']}")
        print(f"       Genre:     {metadata['genre']}")
        print(f"       Composer:  {metadata['composer']}")
        print(f"       Art:       {'Yes' if art_data else 'No'}")

    # ── Measure duration ──
    web_path = tiers.get("web")
    if web_path and os.path.exists(web_path):
        duration = measure_duration(web_path)
        print(f"\n  Duration: {duration}")
    else:
        duration = "—"

    # ── Summary ──
    print(f"\n{'═' * 60}")
    print(f"  COMPLETE")
    print(f"{'═' * 60}")
    for tier_name, filepath in tiers.items():
        exists = os.path.exists(filepath) if not args.dry_run else "(dry run)"
        size = ""
        if not args.dry_run and os.path.exists(filepath):
            mb = os.path.getsize(filepath) / (1024 * 1024)
            size = f" ({mb:.1f} MB)"
        print(f"  {tier_name:12s}: {filepath}{size}")
    print(f"  Duration:     {duration}")
    print(f"{'═' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
