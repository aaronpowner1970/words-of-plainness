"""
Align a lyric sheet to CACHED whisper words (no re-transcription).

wop_align_song.py always runs whisper. The audit (wop_audit_sung.py) already
caches word timestamps in tools/.mp3_cache/words/<stem>.<model>.json, so when
a sheet changes (e.g. after author validation) the VTT can be rebuilt from
those words with the same alignment code (align_lines_to_words,
interpolate_gaps, write_vtt) in seconds.

Usage:
    python tools/wop_align_cached.py <stem> --model medium [--out PATH] [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wop_align_song as A  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cache = A.CACHE_ROOT / "words" / f"{a.stem}.{a.model}.json"
    hyp = [(w[1], w[2], w[3]) for w in json.loads(cache.read_text(encoding="utf-8"))]
    lines = [l for l in (REPO / "tools" / "lyrics_txt" / f"{a.stem}.txt")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    spans = A.align_lines_to_words(lines, hyp, verbose=True)
    print(f"{a.stem} [{a.model}] {len(lines)} lines, {len(hyp)} heard words")
    if not a.dry_run:
        out = Path(a.out) if a.out else REPO / "src" / "assets" / "lyrics" / f"{a.stem}.vtt"
        A.write_vtt(spans, lines, out)
        print("wrote", out)


if __name__ == "__main__":
    main()
