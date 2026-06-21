# Narration Production & Deploy Runbook (clean-paragraph chapters)

Operational companion to `docs/NARRATION.md` (which covers the sync architecture
and the authoritative block-indexing convention + Ch 1 block map). This file
covers **producing the audio and shipping it live**. Chapter 1
(`01-introduction`, 81 blocks `p0`–`p80`) is the worked example. The pipeline
generalizes to any future clean-paragraph chapter.

## What is already in place (sync infrastructure — done)

- `paragraphSync` transform in `.eleventy.js` — stamps `data-paragraph="0..N"` +
  `class="sync-para"` on every `<h2>/<h3>/<p>/<li>` inside
  `<article class="chapter-content">` at build time, for clean chapters only
  (guarded off for Chs 2–10). ✓
- `[data-paragraph]` highlight + click-to-seek in `src/js/audio-sync.js`
  (`_highlightParagraph` / `_onParagraphClick`); bare heading elements highlight
  correctly. ✓
- Placeholder `src/_data/timestamps/chapter-01-introduction.json` — `p0`–`p80`,
  all `0.0` (all-zero guard keeps sync disabled, page safe). ✓
- Builder `tools/build_clean_paragraph_timestamps.py` — reads `data-paragraph`
  from built HTML → emits Format-C `p{N}` JSON; placeholder and `--alignment`
  modes. ✓

So the only remaining work is the **audio**: record → align → assemble → ship.

## Credential boundaries (read before automating)

- **ElevenLabs API key** — NOT in the repo or an env var. `regen_ch09_*` prompts
  interactively (`getpass`). To run a generation script unattended (e.g. from
  Claude Code), export `ELEVENLABS_API_KEY` in the shell first and have the
  script read `os.environ`.
- **R2 S3 keys** — in `tools/wop_r2_config.json` (bucket `wop-media`, prefix
  `web`). boto3 upload runs unattended.
- **Cloudflare purge token** — NOT in the repo (lives in the Claude Desktop
  `wop-shell` env block). Purge runs from Claude Desktop
  (`wop-shell:cloudflare_purge`) or Aaron's terminal — never from a repo-only
  script.

## Source of truth for spoken text

Pull the 81 blocks' spoken text from the **built HTML** via `extract_paragraphs()`
in `build_clean_paragraph_timestamps.py`. This guarantees
generation text == highlighted blocks == timestamp `p{N}` keys (no drift).
Rendered behaviour: cite daggers are empty `<span class="cite-mark">` (no spoken
text); markdown links keep their visible text; the `<style>` block and RJW/UI are
outside the prose article and never picked up.

> **Never drop the closing line "In the name of Jesus Christ, amen."** — it is the
> tail of `p80` (the final Plea paragraph) and is authored content.

## Voice & model

- Voice: **Aaron Powner `As8zJaZyH4MAgaQ93FMc`** for all prose narration.
  (Jonathan `PIGsltMj3gFMR34aFDI3` is only for spoken RJW cues — not used in the
  Ch 1 main narration; the closing cue `NR_01_CUE_01_Closing.mp3` already exists
  and is unchanged.)
- Model `eleven_multilingual_v2`. Settings: **stability 0.65, similarity_boost
  0.80, style 0.15, speaker_boost true.** (The Ch 9 script used 0.62 / 0.18 — for
  Ch 1 prose use the canonical 0.65 / 0.15.)
- Endpoint `/v1/text-to-speech/{voice}/with-timestamps`, `output_format`
  `mp3_44100_128` (intermediate). Chunk ~1000 chars **on block boundaries** so no
  block straddles a chunk seam; save each chunk's `alignment` JSON.

## Assemble — TWO-PASS loudnorm (the Ch 9 single-pass command is the OLD bug)

1. Concatenate chunk MP3s → one **WAV** (lossless intermediate).
2. loudnorm **measure** pass → read `measured_I / measured_TP / measured_LRA /
   measured_thresh / offset`.
3. loudnorm **apply** pass + encode WAV → **MP3 with `-write_xing 1`** (seek
   table). Targets **I = -16, TP = -1.5, LRA = 11**.
   - Single-pass straight-to-MP3 omits the Xing header → browser seeking breaks.
     The WAV intermediate + explicit Xing exist to prevent that.
4. `ffprobe` the final MP3 for duration → frontmatter `audio.narrationDuration`.

Runs fine in a real terminal (Claude Code or PowerShell). The 4-minute wop-shell
MCP timeout does not apply to a real terminal.

## Timestamps

- Merge per-chunk alignments into one stream with cumulative offsets = running
  sum of each prior chunk's last `character_end_time` (NOT ffprobe durations —
  avoids drift; matches the canonical pipeline and `build_paragraph_timestamps.py`).
- `python tools/build_clean_paragraph_timestamps.py 01-introduction --alignment <merged_alignment.json>`
  → overwrites the placeholder with real `p0`–`p80`.
- Sanity: 81 keys, monotonically increasing, `p0` ≈ 0.0, last ≤ MP3 duration.

## Ship

1. R2 upload (boto3, `tools/wop_r2_config.json`): bucket `wop-media`, key
   `web/NR_01_01_Introduction_to_Plainness.mp3`, `put_object` with
   `ContentType="audio/mpeg"`; verify with `head_object` (size + content-type).
2. **Purge** `https://media.wordsofplainness.org/web/NR_01_01_Introduction_to_Plainness.mp3`
   — Desktop `wop-shell:cloudflare_purge` (zone
   `74df6ad2bc59df52c41843c64116dd9d`) or Aaron's terminal. The filename is
   reused, so purge is mandatory or the CDN serves the stale file.
3. Commit `src/_data/timestamps/chapter-01-introduction.json` + frontmatter
   `narrationDuration` (+ the clean Ch 1 `.md` if not yet pushed); push to `main`;
   Vercel deploys.

## Verify live (Playwright)

- CDN 403s to curl / web_fetch (WAF) → use `page.request.get()` on the MP3 →
  expect `200` + correct `content-length`.
- On the deployed chapter: Read Aloud plays; highlight steps through all 81 blocks
  (headings, group-labels, bullets included); clicking a block seeks audio; cite
  daggers and links click without seeking; closing cue → RJW `pause-closing`
  fires on narration end.

## Listen-gate (recommended — the one production gate worth keeping)

Audition the assembled MP3 **before** R2 upload / purge. ElevenLabs mispronounces
proper nouns and coined terms (e.g. "merognosticism"), some scripture names, and
can mis-pace em-dashes; R2 + purge is immediately live to all visitors and the
file is Aaron's own voice reading his testimony. Worth one listen even when the
rest of the pipeline is automated.
