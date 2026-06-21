# Block-Level Audio Sync — Clean-Paragraph Chapters

How audio ↔ text highlighting works for chapters whose markdown body is kept
**clean** (plain paragraphs, no `{% sentence %}` / `{% para %}` shortcodes).
Chapter 1 (`src/chapters/01-introduction.md`) is the reference implementation.

Highlighting is at **block granularity**: every spoken block — section headings,
bold group-labels, prose paragraphs, and list items — is indexed and highlighted.

## The pieces

| Concern | Where | Notes |
|---|---|---|
| Block hooks | `.eleventy.js` → `paragraphSync` transform | Adds `data-paragraph="N"` + `class="sync-para"` to every `<h2>/<h3>/<p>/<li>` at build time |
| Highlight + click-to-seek | `src/js/audio-sync.js` | `_highlightParagraph` / `_onParagraphClick` target `[data-paragraph]` |
| Timestamps | `src/_data/timestamps/chapter-<slug>.json` | Format C: `p{N}` keys |
| Generator | `tools/build_clean_paragraph_timestamps.py` | Reads built HTML → emits `p{N}` JSON |
| Highlight styling | `src/css/chapter.css` → `.sync-para.highlighted` | Shared with `{% para %}` chapters |

The markdown body stays clean. The only audio-sync shortcode that remains in a
clean chapter is the closing `{% pausePoint %}`.

## Indexing convention (authoritative)

The `paragraphSync` transform stamps a sequential index onto each narrated
block **at build time**. The audio/timestamp pipeline MUST produce `p{N}` keys
that match this exact set:

- **Scope:** only `<h2>`, `<h3>`, `<p>`, and `<li>` **inside**
  `<article class="chapter-content">`. Nothing outside the prose article (RJW
  modal, citation panel, study/learning tools, discord, nav) is ever indexed.
- **Indexed elements:** every narrated block — `<h2>`, `<h3>`, `<p>`, and `<li>` —
  in document order, **0-based** (`p0`, `p1`, … `pN`). This includes section
  headings, the bold group-label paragraphs (`<p><strong>…</strong></p>`), and
  every `<li>` bullet (each gets its own index).
- **Never indexed:** the `<style>` block and non-prose UI (`pause-point`, tab
  pills, `section-gap`) — none of which use the four indexed tags.
- Paragraphs inside narrated wrappers (e.g. `.statement-callout`) **are** indexed
  — they are read aloud.
- Putting `data-paragraph` directly on the `<h2>/<h3>` element (not a span inside
  it) is highlighted correctly: `audio-sync.js`'s heading guard only skips a
  `<span>` *inside* a heading, never a bare heading element.

### Safety guard

The transform applies **only** to clean chapters — those whose prose contains
neither `class="sentence"` nor any pre-existing `data-paragraph`. Chapters 2–10
use `{% sentence %}` and/or `{% para %}` and are left byte-for-byte unchanged.

### All-zero placeholder is safe to ship

`audio-sync.js` disables sync (no highlight, no seek) when every timestamp is
`0`. So a placeholder `p{N}: 0.0` file ships safely **before** the audio exists;
Read Aloud still plays. Sync activates automatically the moment real values land.

## Pipeline (per clean chapter)

```sh
# 1. Build so the HTML carries data-paragraph hooks
npm run build

# 2. (a) Placeholder file — count comes straight from the built HTML:
python tools/build_clean_paragraph_timestamps.py 01-introduction

#    (b) Real values from an ElevenLabs character-alignment JSON:
python tools/build_clean_paragraph_timestamps.py 01-introduction \
    --alignment path/to/alignment.json
```

The generator reads `data-paragraph` straight from `_site/.../index.html`, so its
`p{N}` set is guaranteed to match the DOM. For a chunked narration, align each
chunk and add cumulative offsets exactly as `tools/build_paragraph_timestamps.py`
does for Chapter 9.

> The narration text is authored content. Never drop the closing line
> **"In the name of Jesus Christ, amen."** when preparing transcripts.

## Chapter 1 facts (current)

- **81 blocks** indexed: `p0`–`p80` = 14 headings (`<h2>`/`<h3>`) + 2 bold
  group-labels + 51 prose `<p>` (incl. the 2 inside `.statement-callout`) + 14
  `<li>` bullets, in document order. The block layout:

  | Range | Block(s) |
  |---|---|
  | `p0` / `p1`–`p3` | h2 *The Human Condition* / 3 ¶ |
  | `p4` / `p5`–`p10` | h2 *Origin of Our Writings* / 6 ¶ |
  | `p11` / `p12`–`p18` | h2 *Relevance of Our Writings* / 7 ¶ |
  | `p19` / `p20`–`p27` | h2 *Are We Christians?* / 8 ¶ |
  | `p28` / `p29` / `p30` / `p31`–`p37` / `p38` / `p39`–`p45` / `p46` | h2 *What We Hold in Common…* / intro ¶ / label / 7 bullets / label / 7 bullets / outro ¶ |
  | `p47` / `p48` | h2 *Our Credentials…* / 1 ¶ |
  | `p49` / `p50` | h3 *Our Conversion and Upbringing* / 1 ¶ |
  | `p51` / `p52`–`p54` | h3 *Priesthood and Service* / 3 ¶ |
  | `p55` / `p56`–`p57` | h3 *Our Lives as Latter-day Saints* / 2 ¶ |
  | `p58` / `p59`–`p60` | h2 *Christ-Centered Plainness* / 2 ¶ (in statement-callout) |
  | `p61` / `p62`–`p64` | h2 *Kinship with All Believers* / 3 ¶ |
  | `p65` / `p66`–`p70` | h2 *When Faith Is Tried* / 5 ¶ |
  | `p71` / `p72`–`p75` | h2 *Finding Your Way…* / 4 ¶ |
  | `p76` / `p77`–`p80` | h2 *Our Plea to You* / 4 ¶ |

- Timestamp file: `src/_data/timestamps/chapter-01-introduction.json` (placeholder
  zeros until the re-record lands — segment the recording into 81 block cues).
- Closing pause: `{% pausePoint "pause-closing" %}` → cue `NR_01_CUE_01_Closing.mp3`
  → RJW `pause-closing`, fired on narration end by the legacy init path.
