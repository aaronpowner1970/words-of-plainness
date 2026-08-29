# lyrics-src — authored lyric sheets

These are the author's canonical lyric sheets, in the form written for
production. One file per song. They are kept verbatim and are never
machine-edited.

## How the three layers relate

- **`lyrics-src/`** (this directory) — the authored source of record. Written
  by hand, edited only by the author. Includes the production markers
  (`[Verse 1]`, `[Bridge]`, performance notes in parentheses) as they were
  written for the recording session.
- **`src/assets/lyrics/*.vtt`** — the display artifact. This is what ships and
  what the player renders in the lyrics drawer. Each arrangement has its own
  VTT because the cue timings differ per arrangement, even when the words are
  identical. VTTs are checked against the sheets in this directory.
- **`tools/lyrics_txt/`** — a regenerated intermediate that feeds the forced
  aligner, produced by `tools/wop_lyrics_extract.py`. It is gitignored and
  should never carry hand edits; anything in it can be thrown away and rebuilt.

## Working rule

When lyrics change, the sheet in this directory changes first. The VTTs are
then brought into line with it, per arrangement, and the intermediate is
regenerated rather than edited.
