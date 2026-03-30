# Words of Plainness — Session Handoff
## Citation Panel Retrofit · All Deployed Chapters
### Authored: March 28, 2026 · Ministry Development WoP Project

---

## Environment Check (do this first)

At session open, confirm:
- Which interface: Claude Desktop or claude.ai?
- Are MCPs loading correctly?

---

## Citation System Standard — Read Before Starting Any Work

The citation panel is now the **canonical scripture citation system for the
entire Words of Plainness website**, both volumes, all chapters. This is a
site-wide architectural standard established March 28, 2026.

**The rule:** No chapter may use inline parenthetical citations or bare
`{% scripture %}` shortcode links in prose. All scripture citations must
live in the `citations:` YAML frontmatter array and be triggered in prose
by `{% cite "entry-id" %}` shortcodes.

**This applies to:**
- All currently deployed chapters (retrofit task below)
- All future chapters (author with `citations:` frontmatter from day one)
- Card-chapters (Movement 3): scripture citations in card content use the
  same panel system via the `scriptureUrl` filter in Nunjucks loops

**Spec:** `docs/WoP_CitationPanel_Spec_Mar2026.md` — treat all decisions
in this document as constraints unless Aaron authorizes revision.

---

## Current Deployment Status (authoritative)

| Ch | Title | Citations Status |
|---|---|---|
| 9 | Yehoshua the Man | ✅ Complete — 71 entries, all shortcodes deployed |
| 7 | Prophecies, Birth, and Youth | ❌ Uses `{% scripture %}` inline — needs retrofit |
| 8 | Baptism, Temptations, and Ministry | ❌ Uses `{% scripture %}` inline — needs retrofit |
| 10 | Suffering, Trial, Crucifixion, Resurrection | ❌ Uses `{% scripture %}` inline — needs retrofit |
| 1 | Introduction | ❌ Mix of plain text parentheticals + inline patterns — needs retrofit |
| 2–6 | Finding Faith (Movement 1) | ❌ Various inline patterns — needs retrofit |

**10 chapters total are live. Only Ch. 9 has the citation panel.**

---

## Retrofit Sequence

Do chapters in this order. One chapter per Claude Code session.
One commit per chapter. Do not batch.

1. **Ch. 7** — Prophecies, Birth, and Youth (highest priority — Movement 2
   chapter already deployed, needs citations to match Ch. 9 standard)
2. **Ch. 8** — Baptism, Temptations, and Ministry
3. **Ch. 10** — Suffering, Trial, Crucifixion, Resurrection
4. **Ch. 1** — Introduction
5. **Ch. 2** — Our Search
6. **Ch. 3** — Academic Knowledge
7. **Ch. 4** — Spiritual Knowledge
8. **Ch. 5** — Sincere Prayer
9. **Ch. 6** — Embrace the Savior (interactive — card-chapter, special handling)

---

## Critical Prerequisite: /about/sources/ Page

**This page does not exist yet. Every citation panel header across the site
links to `/about/sources/` — it is currently a 404.**

Build this page BEFORE or IN PARALLEL WITH the first retrofit chapter.
Do not retrofit Ch. 7 and leave the 404 sitting in Ch. 9's panel any longer
than necessary.

**What the page must cover:**
- What Bible translations are used and why
- What Restoration scriptures are and how they function as additional
  witnesses (not as primary sources — they deepen and confirm)
- Aaron's authorial relationship to these sources
- No external links to third-party sites about LDS theology

**Workflow:** Draft editorial content here in claude.ai, then Claude Code
deploys as a new page at `src/pages/about-sources.njk` with
permalink `/about/sources/`.

---

## What Each Retrofit Session Looks Like

For each chapter, come to **claude.ai first** to produce:
1. The complete `citations:` YAML frontmatter block
2. A prose replacement map (which shortcode replaces which inline citation)
3. The filled-in Claude Code prompt

Then execute in **Claude Code**.

### Two Different Retrofit Patterns

**Ch. 7, 8, 10 use `{% scripture "ref" %}` shortcodes inline:**
```
...He walked into the river {% scripture "Matthew 3:16" %} and the
heavens opened.
```
The retrofit replaces each `{% scripture "ref" %}` with `{% cite "entry-id" %}`.
The scripture URL is still generated — now via the `scriptureUrl` filter in
the panel template rather than inline.

**Ch. 1–6 use plain text parentheticals:**
```
...He said this (Matthew 5:22; Proverbs 3:30)
```
The retrofit removes the parenthetical and inserts `{% cite "entry-id" %}`.
Some Ch. 1 sentences also use `{% scripture %}` — treat those the same
as the Ch. 7/8/10 pattern.

### Claude Code Prompt Template (per chapter)

```
Implement the citation panel retrofit for Chapter [N] ([Title]) per
docs/WoP_CitationPanel_Spec_Mar2026.md.

Step 0: git checkout main && git pull origin main
Confirm local is synced before any edits.

Tasks:
1. Add `citations:` frontmatter array to `src/chapters/[slug].md`
   using the YAML data below.
2. Replace all inline scripture citations in the chapter prose:
   - Replace `{% scripture "ref" %}` shortcodes with `{% cite "entry-id" %}`
   - Replace plain text parentheticals (ref) with `{% cite "entry-id" %}`
   Use the replacement map below.
3. Confirm `{% cite %}` shortcode, `scriptureUrl` filter, panel HTML,
   panel CSS, and panel JS are already present (deployed in Ch. 9 session).
   Do NOT re-add them if present — only verify.
4. Run npx @11ty/eleventy --dryrun — confirm no build errors.

[PASTE YAML FRONTMATTER BLOCK HERE]

[PASTE PROSE REPLACEMENT MAP HERE]

Commit message: feat: citation panel — Chapter [N] ([Title])
Push this commit directly to main. Do not create a PR.
```

---

## Technical Reference (locked decisions — do not re-litigate)

### Citation panel architecture
- Left-side slide-out, 360px desktop / 100vw mobile
- z-index 1100 — above audio player bar (z-index 1000), all fixed elements
- Triggered by `†` `.cite-mark` superscript spans via `{% cite "entry-id" %}`
- `citations:` YAML array in frontmatter, grouped by section heading
- Panel guarded by `{% if citations %}` — only emits on pages with data
- Panel HTML and JS in `src/_includes/layouts/chapter.njk`
- CSS in `src/css/chapter.css`

### Highlight behavior
- Active citation: permanent gold left border `#C4943A` +
  `rgba(196,148,58,0.2)` background. No timeout — stays until next `†`
  click or panel closes.

### Audio behavior
- Panel open: checks `!audio.paused` on `#chapterAudio` element directly
  (NOT `ChapterManager.isPlaying`). Pauses if playing. Disables
  `AudioSync.autoScrollEnabled`.
- Panel close: restores auto-scroll, resumes audio if was playing.

### Click isolation
- `.cite-mark` click handler calls `e.stopPropagation()` — prevents
  bubbling to sentence span audio seek handler.
- `AudioSync._isPlayerActive()` guard: sentence clicks do nothing if
  player is not visible and audio is not playing (silent reading mode).

### YAML structure
```yaml
citations:
  - section: "Section Heading"
    entries:
      - id: "ce-[book][chapter][verse]"
        ref: "Book Chapter:Verse"
        type: "ot|nt|bom|dc"
        note: "Context note for this citation."
```

### ID naming convention
- Format: `ce-[abbreviated-book][chapter][verse]`
- Examples: `ce-matt316`, `ce-john114`, `ce-alma711`
- Duplicate refs (same verse cited twice): suffix `-a`, `-b`
- Examples: `ce-alma711-a`, `ce-alma711-b`

### Type values
- `ot` = Old Testament (gold-pale badge)
- `nt` = New Testament (gold badge)
- `bom` = Book of Mormon (teal badge)
- `dc` = D&C / Pearl of Great Price (burgundy badge)

---

## Worktree Sync Rule (non-negotiable — recurring bug)

Every Claude Code session must begin with:
```
git checkout main
git pull origin main
```

Claude Code commits to worktree sandboxes and pushes to remote without
updating local source files. Local is NOT reliable after any Claude Code
session unless you manually pull. Always verify with filesystem MCP after
any Claude Code session.

---

## Key File Paths

| File | Path |
|---|---|
| Citation panel spec | `docs/WoP_CitationPanel_Spec_Mar2026.md` |
| Ch. 9 (reference implementation) | `src/chapters/09-yehoshua-the-man.md` |
| Chapter base layout | `src/_includes/layouts/chapter.njk` |
| Chapter CSS | `src/css/chapter.css` |
| Eleventy config | `.eleventy.js` |
| About/Sources page (to build) | `src/pages/about-sources.njk` (not yet created) |

---

## Session Close Protocol (required before ending any session)

1. Store session summary to ministry-rag (`store_session_summary`)
2. Store key decisions to memory knowledge graph
3. Remind Aaron: kill all Claude processes in Task Manager,
   then delete `.claude\worktrees\` folders

---

*Words of Plainness · Aaron Powner Publishing*
*Handoff authored: March 28, 2026*
