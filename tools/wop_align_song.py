"""
WoP Song Aligner — mp3 + known lyrics → line-level WebVTT.

Pipeline:
  1. Fetch the mp3 (from the R2 CDN by default; cached under scratchpad).
  2. Run openai-whisper with word_timestamps=True to get per-word timings.
     Whisper is ASR — it may mishear a word here or there, but the timings
     it emits are grounded in acoustic evidence.
  3. Align whisper's word stream to our known-lyric words via
     difflib.SequenceMatcher. Known-truth alignment sidesteps ASR errors
     cleanly: mishearings become gaps in the match, not wrong cue text.
  4. For each known line, compute cue start/end from the matched hyp words;
     interpolate through gaps for unmatched lines (rare, repeated choruses
     usually all match).
  5. Emit WebVTT — one cue per known line, cue text = the known line.

Design notes:
  - aeneas was the handoff's default but requires a Windows C toolchain
    (build_ext error: 'You must install numpy before installing aeneas').
    Not worth the install cost for a batch of ~54 songs; whisper (already
    installed) covers the same ground.
  - Model choice: 'base' (74 MB) is fast and accurate enough for clearly-
    sung studio recordings. Override with --model.
  - crossorigin CORS: not a concern here — we ship VTTs same-origin under
    src/assets/lyrics/ (see wop-player.js attachVttTrack for the pivot).

Usage:
  python tools/wop_align_song.py --mp3-file <name.mp3> \
      [--lyrics tools/lyrics_txt/<stem>.txt] \
      [--out src/assets/lyrics/<stem>.vtt] \
      [--model base|small|medium] [--force] [--verbose]

  Defaults derive --lyrics and --out from the mp3 stem, so:
      python tools/wop_align_song.py --mp3-file 11_01_Panteles_Sacred_Ballad.mp3
"""

import argparse
import os
import re
import sys
import time
import unicodedata
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

import whisper


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LYRICS_DIR = REPO_ROOT / "tools" / "lyrics_txt"
DEFAULT_VTT_DIR = REPO_ROOT / "src" / "assets" / "lyrics"
CDN_BASE = "https://media.wordsofplainness.org/web/"

# Scratch cache — mp3s are large-ish (~5 MB each) and not needed in the repo.
CACHE_ROOT = Path(os.environ.get(
    "WOP_MP3_CACHE",
    r"C:\Users\aaron\AppData\Local\Temp\claude\C--Users-aaron-Documents-meridian-invest\6c4d3322-2f64-4a65-a53c-75cf5fdba9f4\scratchpad\wop_mp3_cache",
))


WORD_TOKEN_RE = re.compile(r"[a-z0-9']+", re.IGNORECASE)


def normalize_token(s):
    """Lowercase + strip punctuation + drop diacritics — for word matching only.
    The VTT cue text uses the ORIGINAL lyric line unmodified."""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    m = WORD_TOKEN_RE.findall(s)
    return "".join(m)


def fetch_mp3(mp3_file):
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    dst = CACHE_ROOT / mp3_file
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    url = CDN_BASE + mp3_file
    print(f"  fetching {url}")
    # Cloudflare 403s the default urllib User-Agent; a browser UA passes fine.
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                      " (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    })
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as fh:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    return dst


def whisper_words(mp3_path, model_name, verbose=False):
    """Return a list of (norm_token, start_sec, end_sec) from whisper."""
    print(f"  loading whisper model={model_name}")
    model = whisper.load_model(model_name)
    print(f"  transcribing (this takes a bit)…")
    t0 = time.time()
    # fp16 off on Windows CPU (avoid noisy warning), condition_on_previous_text
    # keeps whisper coherent across repeated choruses.
    result = model.transcribe(
        str(mp3_path),
        language="en",
        word_timestamps=True,
        fp16=False,
        condition_on_previous_text=True,
        verbose=False,
    )
    dt = time.time() - t0
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []) or []:
            token = normalize_token(w.get("word") or "")
            if not token:
                continue
            words.append((token, float(w["start"]), float(w["end"])))
    if verbose:
        print(f"  transcribed {len(words)} words in {dt:.1f}s")
        if words:
            print(f"  first 8 hyp words: {[w[0] for w in words[:8]]}")
    return words


def align_lines_to_words(known_lines, hyp_words, verbose=False):
    """
    Returns a list parallel to known_lines: [(start, end)] per line, with
    None for lines that had no words matched (caller interpolates).
    """
    # Flatten known lines to a token stream, remembering each token's line.
    known_tokens = []
    line_of = []
    for i, line in enumerate(known_lines):
        toks = [normalize_token(w) for w in line.split()]
        toks = [t for t in toks if t]
        for t in toks:
            known_tokens.append(t)
            line_of.append(i)

    hyp_tokens = [w[0] for w in hyp_words]

    matcher = SequenceMatcher(a=known_tokens, b=hyp_tokens, autojunk=False)

    # Collect matched hyp-word indices per known-line.
    per_line_hyps = [[] for _ in known_lines]
    for a_start, b_start, size in matcher.get_matching_blocks():
        for k in range(size):
            ki = a_start + k
            hi = b_start + k
            per_line_hyps[line_of[ki]].append(hi)

    spans = []
    for i, hyps in enumerate(per_line_hyps):
        if hyps:
            starts = [hyp_words[j][1] for j in hyps]
            ends   = [hyp_words[j][2] for j in hyps]
            spans.append((min(starts), max(ends)))
        else:
            spans.append(None)

    matched = sum(1 for s in spans if s is not None)
    if verbose:
        print(f"  matched {matched}/{len(known_lines)} lines directly")

    # Interpolate through unmatched lines using neighbors.
    spans = interpolate_gaps(spans)
    return spans


def interpolate_gaps(spans):
    """
    Fill None entries in spans by linear interpolation between the nearest
    matched neighbors on either side. Head/tail gaps take their nearest
    matched neighbor's time as both endpoints (degenerate cues get a small
    default duration).
    """
    n = len(spans)
    if not any(s for s in spans):
        return spans
    filled = list(spans)

    # Forward-scan to find prev matched index for each position; back-scan for next.
    prev_idx = [None] * n
    last = None
    for i in range(n):
        prev_idx[i] = last
        if filled[i] is not None:
            last = i
    next_idx = [None] * n
    nxt = None
    for i in range(n - 1, -1, -1):
        next_idx[i] = nxt
        if filled[i] is not None:
            nxt = i

    for i in range(n):
        if filled[i] is not None:
            continue
        p, q = prev_idx[i], next_idx[i]
        if p is None and q is None:
            continue
        if p is None:
            # head gap — before the first match; give a short cue ending at q's start
            t = filled[q][0]
            filled[i] = (max(0.0, t - 0.6), t)
        elif q is None:
            # tail gap — after the last match; give a short cue starting at p's end
            t = filled[p][1]
            filled[i] = (t, t + 0.6)
        else:
            # interior gap — split the p→q interval evenly among the missing lines
            gap_start = filled[p][1]
            gap_end   = filled[q][0]
            # count how many nones sit between p (exclusive) and q (exclusive)
            missing = [j for j in range(p + 1, q) if filled[j] is None or j == i]
            # Recompute the missing list only once per contiguous run, but
            # per-iteration is fine (few lines, tiny cost).
            slot = missing.index(i)
            n_missing = len(missing)
            step = (gap_end - gap_start) / n_missing
            s = gap_start + slot * step
            e = s + step
            filled[i] = (s, e)

    # Guarantee non-decreasing cue starts (rare inversions after interpolation).
    for i in range(1, n):
        if filled[i] and filled[i - 1]:
            if filled[i][0] < filled[i - 1][0]:
                s = filled[i - 1][0]
                e = max(filled[i][1], s + 0.4)
                filled[i] = (s, e)
    return filled


def fmt_ts(seconds):
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def write_vtt(spans, lines, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    parts = ["WEBVTT", ""]
    for i, (span, line) in enumerate(zip(spans, lines), 1):
        if not span:
            continue
        s, e = span
        if e <= s:
            e = s + 0.4
        parts.append(str(i))
        parts.append(f"{fmt_ts(s)} --> {fmt_ts(e)}")
        parts.append(line)
        parts.append("")
    out_path.write_text("\n".join(parts), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp3-file", required=True,
                    help="Bare mp3 filename (fetched from CDN if not local)")
    ap.add_argument("--lyrics",
                    help="Path to lyric txt (default: tools/lyrics_txt/<stem>.txt)")
    ap.add_argument("--out",
                    help="VTT output path (default: src/assets/lyrics/<stem>.vtt)")
    ap.add_argument("--model", default="base",
                    help="whisper model name (tiny|base|small|medium|large)")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite an existing VTT")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    stem = Path(args.mp3_file).stem
    lyrics_path = Path(args.lyrics) if args.lyrics else DEFAULT_LYRICS_DIR / f"{stem}.txt"
    out_path    = Path(args.out)    if args.out    else DEFAULT_VTT_DIR    / f"{stem}.vtt"

    if not lyrics_path.exists():
        sys.exit(f"Lyrics file not found: {lyrics_path}")
    if out_path.exists() and not args.force:
        sys.exit(f"Refusing to overwrite {out_path} (pass --force)")

    lines = [ln for ln in lyrics_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        sys.exit(f"Empty lyrics file: {lyrics_path}")
    print(f"Aligning: {args.mp3_file}  ({len(lines)} lines)")

    mp3_path = fetch_mp3(args.mp3_file)
    hyp = whisper_words(mp3_path, args.model, verbose=args.verbose)
    if not hyp:
        sys.exit("Whisper produced zero timestamped words — cannot align.")

    spans = align_lines_to_words(lines, hyp, verbose=args.verbose)
    write_vtt(spans, lines, out_path)

    matched = sum(1 for s in spans if s is not None)
    print(f"  wrote {out_path}  ({matched}/{len(lines)} lines timed)")


if __name__ == "__main__":
    main()
