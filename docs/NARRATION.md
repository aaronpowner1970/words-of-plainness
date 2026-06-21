# Paragraph-Level Audio Sync — Clean-Paragraph Chapters

How audio ↔ text highlighting works for chapters whose markdown body is kept
**clean** (plain paragraphs, no `{% sentence %}` / `{% para %}` shortcodes).
Chapter 1 (`src/chapters/01-introduction.md`) is the reference implementation.

## The pieces

| Concern | Where | Notes |
|---|---|---|
| Paragraph hooks | `.eleventy.js` → `paragraphSync` transform | Adds `data-paragraph="N"` + `class="sync-para"` at build time |
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

- **Scope:** only `<p>` and `<li>` **inside** `<article class="chapter-content">`.
  Nothing outside the prose article (RJW modal, citation panel, study/learning
  tools, discord, nav) is ever indexed.
- **Indexed elements:** `<p>` and `<li>` **only**, in document order, **0-based**
  (`p0`, `p1`, … `pN`). `<li>` bullets each get their own index.
- **Never indexed:** `<h2>`/`<h3>` headings, the `<style>` block, and non-prose
  UI (`pause-point`, tab pills, `section-gap`).
- Paragraphs inside narrated wrappers (e.g. `.statement-callout`) **are** indexed
  — they are read aloud.

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

- **67 paragraphs** indexed: `p0`–`p66` (53 `<p>` + 14 `<li>`).
- Timestamp file: `src/_data/timestamps/chapter-01-introduction.json` (placeholder
  zeros until the re-record lands — segment the recording into 67 paragraph cues).
- Closing pause: `{% pausePoint "pause-closing" %}` → cue `NR_01_CUE_01_Closing.mp3`
  → RJW `pause-closing`, fired on narration end by the legacy init path.
