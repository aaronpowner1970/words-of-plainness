# Lantern Post render script

Turns one small spec plus three input files (background image, narration, music bed) into the approved 9:16 video, a cover image and a check report. It runs headless, on Aaron's PC and on a GitHub Actions `ubuntu-latest` runner. It does not post, generate images or touch the Approve page.

```
pip install -r tools/lantern/render/requirements.txt      # Pillow, pocketsphinx; ffmpeg and ffprobe must be on PATH
python tools/lantern/render/render.py SPEC.json --out OUT_DIR [--media-dir DIR] [--keep-work]
```

Writes `OUT_DIR/out.mp4`, `cover_9x16.png`, `check.json` and `check.md`. File names in the spec are looked up in `--media-dir` (default: the spec's own folder). Exit code 0 only when every standard check passes; 2 means it stopped (bad spec, or timing it could not show was right).

Tests (no real media needed): `python -m pytest tools/lantern/render/tests` (use `requirements-dev.txt`).

## The spec (JSON)

Only `lines`, `image`, `narration` and `bed` are required.

```json
{
  "title": "What the Mirror Reveals",
  "image": "fool-blind-wise-9x16-modern.jpg",
  "narration": "ElevenLabs_narration.mp3",
  "bed": "What the Mirror Reveals.mp3",
  "lines": [
    "Fools mock and condemn.",
    "The blind ignore and withdraw.",
    { "text": "The wise empathize and engage.", "gold": true },
    "Response reflects character.",
    { "text": "What does your mirror reveal?", "gold": true }
  ],
  "screens": [[0, 1, 2], [3, 4]],
  "hook": ["What does your", "mirror reveal?"],
  "url_text": ["wordsofplainness.org"],
  "text_zone": "lower",
  "end_card_seconds": 2.4
}
```

| Key | Meaning | Default |
|---|---|---|
| `lines` | The spoken lines, in order. A string, or `{text, gold, italic, ref, spoken}`. `\n` in `text` is a visible line break. `ref` is a scripture reference shown under the screen. `spoken` overrides the words used for alignment. | required |
| `screens` | How lines group into screens (a partition of the line numbers, in order). | groups of three |
| `hook` | One or two rows shown in the first 0.8 s; the second row is gold. | the last line, split in two |
| `url_text` | One or two rows for the URL screen (second row gold); the first row is also on the end card. | `["wordsofplainness.org"]` |
| `url_spoken` | The narration ends by speaking the URL: the URL screen starts when that speech starts. | false |
| `text_zone` | `top` (y 760), `middle` (960), `lower` (1440) or a y value 400 to 1700. | `middle` |
| `credit` | Credit line at the foot. | `Aaron Powner · Words of Plainness Ministry` |
| `hook_seconds`, `url_seconds`, `url_gap`, `end_card_seconds` | 0.8, 3.0, 1.4 (pause after the last line when the URL is not spoken), 3.0 (end card including the 0.6 s crossfade). | as shown |
| `bed_under_voice_lu` | How far under the voice the bed sits before the final normalise. | 12.5 |
| `timing` | `auto`, `pause` or `align`. | `auto` |

Specs for the two reference posts are in `specs/`. They hold file names only, never paths or media.

## How timing is chosen

1. **Pause detection** (`silencedetect`). It is tried over noise -40 to -30 dB and minimum silence 0.30, 0.35, 0.40 s. It is used only if at least one setting gives exactly one speech segment per spoken line (plus one, when `url_spoken`) and every setting that does agrees on where the lines start to within 0.25 s. The setting closest to -35 dB / 0.35 s wins.
2. **Forced alignment** (pocketsphinx, the Part A method), when the count never matches. The spoken text is the line text with punctuation removed and dashes treated as spaces; it must return exactly the expected words.
3. Neither works: the script stops (exit 2) and says why. It never guesses.

Either way each line onset must fall in audible speech. The method and every onset go in `check.md`.

## What is derived, not fixed

Narration delay (hook length minus the first onset, never negative), URL screen time, text end, total length (text end plus the end card), zoom frame count, crossfade offset, body/hook/URL font size (largest that fits the widest line in 960 px as libass draws it, capped at 92/92/96), the scrim size, the voice and bed gains (from measured loudness: voice to -16 LUFS, bed `bed_under_voice_lu` under it) and the two-pass loudnorm (I -16, TP -1.5, LRA 11).

## Fonts

EB Garamond Medium, SemiBold and Medium Italic (Latin subset) are committed as TTF in `fonts/`, converted from `@fontsource/eb-garamond` 5.3.0 woff2 with fontTools, under the SIL Open Font License 1.1 (`fonts/OFL-EBGaramond.txt`). Committing them keeps the render offline and byte-for-byte repeatable on the runner.

## Manual comparison with a posted video

`compare_posted.py` (needs numpy) checks a render against the video that was actually posted: size, length, loudness, header and logo, and each line's onset judged from the pixels of both videos. It also writes a frame strip. The posted video is Aaron's media and stays out of the repo.

```
python tools/lantern/render/compare_posted.py SPEC.json --render OUT_DIR --posted POSTED.mp4 --report DIR --name A
```
