"""
WoP Batch Aligner — align every song in the manifest, in one process, using a
single loaded whisper model (huge speedup vs. one process per song).

Usage:
    python tools/wop_align_batch.py [--model base] [--force] [--limit N]
                                    [--only-missing]

Default behavior: skips songs whose .vtt already exists under
src/assets/lyrics/. Pass --force to re-align regardless.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import whisper

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wop_align_song import (
    DEFAULT_LYRICS_DIR,
    DEFAULT_VTT_DIR,
    align_lines_to_words,
    fetch_mp3,
    write_vtt,
    normalize_token,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "tools" / "lyrics_txt" / "manifest.json"


def align_one(mp3_file, lyrics_path, out_path, model, verbose=False):
    """Run one alignment against a preloaded whisper model."""
    lines = [ln for ln in lyrics_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None, 0, 0

    mp3_path = fetch_mp3(mp3_file)
    result = model.transcribe(
        str(mp3_path),
        language="en",
        word_timestamps=True,
        fp16=False,
        condition_on_previous_text=True,
        verbose=False,
    )
    hyp = []
    for seg in result["segments"]:
        for w in seg.get("words", []) or []:
            tok = normalize_token(w.get("word") or "")
            if tok:
                hyp.append((tok, float(w["start"]), float(w["end"])))
    if not hyp:
        return None, len(lines), 0

    spans = align_lines_to_words(lines, hyp, verbose=verbose)
    matched = sum(1 for s in spans if s is not None)
    write_vtt(spans, lines, out_path)
    return out_path, len(lines), matched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="base")
    ap.add_argument("--force", action="store_true",
                    help="Re-align even when a .vtt already exists.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after this many alignments (0 = no limit).")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    if not MANIFEST_PATH.exists():
        sys.exit(f"No manifest at {MANIFEST_PATH}. Run wop_lyrics_extract.py first.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    DEFAULT_VTT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading whisper model={args.model} (once)...")
    model = whisper.load_model(args.model)

    todo = []
    for mp3, entry in manifest.items():
        if not entry.get("lines"):
            continue
        stem = Path(mp3).stem
        vtt_path = DEFAULT_VTT_DIR / f"{stem}.vtt"
        if vtt_path.exists() and not args.force:
            continue
        lyrics_path = DEFAULT_LYRICS_DIR / f"{stem}.txt"
        if not lyrics_path.exists():
            print(f"  ! missing lyrics for {mp3}, skip")
            continue
        todo.append((mp3, lyrics_path, vtt_path))

    if args.limit:
        todo = todo[: args.limit]

    print(f"Aligning {len(todo)} song(s). Existing VTTs under {DEFAULT_VTT_DIR} are kept.")
    t0 = time.time()
    ok = 0
    fail = 0
    for i, (mp3, lyrics_path, vtt_path) in enumerate(todo, 1):
        print(f"[{i:02d}/{len(todo)}] {mp3}")
        try:
            out, total, matched = align_one(mp3, lyrics_path, vtt_path, model,
                                            verbose=args.verbose)
            if out:
                print(f"         wrote {out.name}  ({matched}/{total} lines timed)")
                ok += 1
            else:
                print(f"         SKIP  (no lines or no hyp words)")
                fail += 1
        except Exception as e:
            print(f"         FAIL  {e!r}")
            fail += 1

    dt = time.time() - t0
    print("-" * 72)
    print(f"  done: {ok} aligned, {fail} skipped/failed  in  {dt/60:.1f} min")


if __name__ == "__main__":
    main()
