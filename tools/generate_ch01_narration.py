"""
Generate Chapter 1 narration audio + word-level alignment, chunk by chunk.

Single source of truth for spoken text: extract_paragraphs() in
build_clean_paragraph_timestamps.py reads the data-paragraph blocks straight
from the BUILT HTML, so the generation text == the highlighted blocks == the
p{N} timestamp keys. The text is NEVER hand-transcribed.

For each chunk this calls ElevenLabs
/v1/text-to-speech/{voice}/with-timestamps (Aaron's voice, eleven_multilingual_v2,
canonical prose settings) and saves:
  - chunk MP3            -> CHUNKS_DIR/ch01_chunk_NN.mp3
  - per-chunk alignment  -> CHUNKS_DIR/alignment/chunk_NN.json
  - manifest            -> CHUNKS_DIR/manifest.json  (chunk -> block indices, order)

Assembly (two-pass loudnorm) and timestamp merge are SEPARATE steps; this
script only produces the chunk audio + alignment.

Prereq: ELEVENLABS_API_KEY must be set in the environment. The script never
prompts interactively — if the key is missing it exits with an error.

Usage:
    python tools/generate_ch01_narration.py
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_clean_paragraph_timestamps import extract_paragraphs

# ── Config ────────────────────────────────────────────────────────────────

REPO         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILT_HTML   = os.path.join(REPO, "_site", "chapters", "01-introduction", "index.html")
CHUNKS_DIR   = r"C:\Users\aaron\Documents\working-folder\ch01-chunks"
ALIGNMENT_DIR = os.path.join(CHUNKS_DIR, "alignment")

EL_API_BASE  = "https://api.elevenlabs.io"
VOICE_AARON  = "As8zJaZyH4MAgaQ93FMc"
MODEL_ID     = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"

# Canonical Aaron prose settings (NARRATION_PRODUCTION_RUNBOOK §Voice & model).
# Not the Ch 9 values (0.62 / 0.18) — Ch 1 prose uses 0.65 / 0.15.
AARON_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.80,
    "style": 0.15,
    "use_speaker_boost": True,
}

TARGET_CHARS = 1000   # chunk size budget; blocks are NEVER split across a seam

# ── Chunking — group whole blocks up to ~TARGET_CHARS, never split a block ──

def build_chunks(blocks):
    """blocks: [(idx, text), ...] in document order.
    Returns [ {"indices": [...], "text": "block\n\nblock..."} , ... ]."""
    chunks = []
    cur_idx, cur_parts, cur_len = [], [], 0
    for idx, text in blocks:
        sep = 2 if cur_parts else 0           # "\n\n" between blocks
        if cur_parts and cur_len + sep + len(text) > TARGET_CHARS:
            chunks.append({"indices": cur_idx, "text": "\n\n".join(cur_parts)})
            cur_idx, cur_parts, cur_len = [], [], 0
            sep = 0
        cur_idx.append(idx)
        cur_parts.append(text)
        cur_len += sep + len(text)
    if cur_parts:
        chunks.append({"indices": cur_idx, "text": "\n\n".join(cur_parts)})
    return chunks

# ── ElevenLabs call ─────────────────────────────────────────────────────────

def call_tts_with_timestamps(api_key, voice_id, settings, text):
    url = f"{EL_API_BASE}/v1/text-to-speech/{voice_id}/with-timestamps"
    payload = json.dumps({
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": settings,
        "output_format": OUTPUT_FORMAT,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    audio_bytes = base64.b64decode(data["audio_base64"])
    alignment   = data.get("alignment", {})
    return audio_bytes, alignment

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        sys.exit("ERROR: ELEVENLABS_API_KEY is not set. Export it in the shell "
                 "before running (never prompted interactively).")

    if not os.path.exists(BUILT_HTML):
        sys.exit(f"ERROR: built HTML not found: {BUILT_HTML}\nRun `npm run build` first.")

    blocks = extract_paragraphs(BUILT_HTML)
    if not blocks:
        sys.exit("ERROR: no data-paragraph blocks found in built HTML.")
    print(f"Extracted {len(blocks)} blocks (p{blocks[0][0]}..p{blocks[-1][0]}).")

    # Guard: the closing line must be present in the final block (authored content).
    last_text = blocks[-1][1].lower()
    if "in the name of jesus christ" not in last_text:
        sys.exit("ERROR: closing line 'In the name of Jesus Christ' missing from "
                 "final block — refusing to generate.")

    chunks = build_chunks(blocks)
    print(f"Grouped into {len(chunks)} chunks (~{TARGET_CHARS} chars, block-aligned):")
    for i, c in enumerate(chunks, 1):
        print(f"  chunk {i:02d}: blocks p{c['indices'][0]}..p{c['indices'][-1]}"
              f"  ({len(c['indices'])} blocks, {len(c['text'])} chars)")

    os.makedirs(ALIGNMENT_DIR, exist_ok=True)

    manifest = {"order": [], "chunks": {}}
    for i, c in enumerate(chunks, 1):
        cid = f"{i:02d}"
        mp3_path = os.path.join(CHUNKS_DIR, f"ch01_chunk_{cid}.mp3")
        align_path = os.path.join(ALIGNMENT_DIR, f"chunk_{cid}.json")
        print(f"\nChunk {cid}: blocks p{c['indices'][0]}..p{c['indices'][-1]} "
              f"({len(c['text'])} chars) -> ElevenLabs ...")
        try:
            audio_bytes, alignment = call_tts_with_timestamps(
                api_key, VOICE_AARON, AARON_SETTINGS, c["text"])
        except urllib.error.HTTPError as e:
            sys.exit(f"  HTTP ERROR {e.code}: {e.read()[:300]}")
        except Exception as e:
            sys.exit(f"  ERROR: {e}")

        with open(mp3_path, "wb") as f:
            f.write(audio_bytes)
        with open(align_path, "w", encoding="utf-8") as f:
            json.dump(alignment, f, indent=2)

        nchars = len(alignment.get("characters", []))
        print(f"  saved {os.path.basename(mp3_path)} ({len(audio_bytes):,} bytes), "
              f"alignment chars={nchars}")

        manifest["order"].append(cid)
        manifest["chunks"][cid] = {
            "indices": c["indices"],
            "mp3": os.path.basename(mp3_path),
            "alignment": os.path.join("alignment", os.path.basename(align_path)),
            "char_count": nchars,
        }

    with open(os.path.join(CHUNKS_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {len(chunks)} chunks + alignments written to:\n  {CHUNKS_DIR}")
    print("Next: assemble (two-pass loudnorm) and merge alignments for timestamps.")


if __name__ == "__main__":
    main()
