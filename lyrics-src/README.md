# lyrics-src — authored lyric sheets

These are the author's canonical lyric sheets, in the form written for
production. One file per song. They are kept verbatim and are never
machine-edited.

## The pipeline

```
lyrics-src/*.md                  authored lyric sheet — canonical text
        ↓
src/chapters/*.md  frontmatter `lyrics:` block
                                 pipeline source — must match the sheet
        ↓  tools/wop_lyrics_extract.py
tools/lyrics_txt/*.txt           regenerated intermediate — gitignored
        ↓  forced aligner
src/assets/lyrics/*.vtt          display artifact — what ships
```

- **`lyrics-src/`** (this directory) — the authored source of record. Written
  by hand, edited only by the author. Includes the production markers
  (`[Verse 1]`, `[Bridge]`, performance notes in parentheses) as they were
  written for the recording session.
- **Chapter frontmatter `lyrics:`** — the block the pipeline actually reads. It
  is HTML (`<p class="verse">`, `<p class="chorus">`, …) and must agree with
  the sheet on every sung line. It is also served as `lyricsHtml` in the music
  catalog, so it is display copy as well as pipeline input.
- **`tools/lyrics_txt/`** — a regenerated intermediate that feeds the forced
  aligner. Gitignored. It should never carry hand edits; anything in it can be
  thrown away and rebuilt.
- **`src/assets/lyrics/*.vtt`** — the display artifact, and what the player
  renders in the lyrics drawer. Each arrangement has its own VTT because the
  cue timings differ per arrangement, even when the words are identical.

## Working rule

A lyric change is made to the sheet first, then to the frontmatter block, then
the intermediate is regenerated and the VTTs are realigned or hand-patched.
The sheet, the frontmatter block, and every VTT must agree on sung text.

## Gotcha: only `verse` and `chorus` are extracted

`tools/wop_lyrics_extract.py` treats a paragraph as sung only when its class is
`verse` or `chorus`. Lines inside any other class — `bridge`, for instance — are
silently dropped from the intermediate, so they never reach the aligner and
never appear in a VTT, even though they still render on the page. If a section
of a song is missing from the VTTs but visible in the chapter, check the
paragraph class first.
