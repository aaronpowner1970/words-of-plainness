# Chapter Authoring — Traps and Rules

Loads when Claude Code works in `src/chapters/`. These are the errors that produce
404s and broken rendering. **Canonical rule: match the frontmatter of the most
recently deployed working chapter of the same type.** When in doubt, read a live
deployed chapter, not this file's examples.

## Prose chapters vs. card-chapters
- **Prose chapters** — `##-slug.md`. Markdown body with `{% sentence N %}`
  shortcodes for audio sync. Layout `layouts/chapter.njk`.
- **Card-chapters** — `##-slug.njk`. **All content lives in YAML frontmatter**
  (cards array); there is no Markdown body. Layout `layouts/card-chapter.njk`.
  Piped through `| safe` as raw HTML, so the `{% scripture %}` shortcode does NOT
  fire — use hardcoded `<a class="scripture-link" href="…">` tags in card HTML.

## Frontmatter traps (these cause 404s)
- **Filenames only, never full paths.** The template prepends the directory. Write
  `narration: chapter-06-narration.mp3`, not `/assets/audio/chapter-06-...`.
  Full paths produce doubled URLs like `/assets/audio//assets/audio/...` that 404.
- **`readingTime` is a bare number**, not a string. `readingTime: 12`, not
  `"~12 min read"` (the template adds "min read"; a string yields "min read min read").
- **`slug` and `chapterId` are required.** `slug: "06-embrace-the-savior"`,
  `chapterId: "chapter-06-embrace-the-savior"`. Missing `chapterId` breaks the
  timestamp-file lookup.
- **`slides` is nested**, not flat: `slides.count` and `slides.path`, not
  `slidesCount`/`slidesPath`. Path convention is `"chapter-06/"` (not `WoP_Ch06/`).
- **`prevChapter`/`nextChapter` are flat top-level keys**, not nested under
  `navigation:`. Include the chapter number in the title: `title: "Chapter 5:
  Sincere Prayer"`.
- **Testimony and PDF filenames must match disk byte-for-byte** — hyphens vs.
  underscores matter, spaces and dots matter. Verify with
  `Get-ChildItem "src\assets\audio\*##*"` and `…\pdf\*##*"` before writing.
- **`discordChannelId`** must hold the actual ID string, or the discussion button
  won't render.

## Heading IDs — Nunjucks conflict
Do **not** use Markdown heading-ID syntax `## Title {#section-name}` in `.md`
files — the `{#…}` collides with Nunjucks comment syntax. Use HTML instead:
`<h2 id="section-name">{% sentence 0 %}Section Title{% endsentence %}</h2>`.

## Sentence shortcodes (prose chapters, audio sync)
- Indices sequential (0, 1, 2, …) and **never restart at section boundaries.**
- Headings read aloud in narration get their own shortcode. Headings not narrated
  still get a shortcode but share the nearest narrated sentence's timestamp.

## Card-chapter content discipline
See the Card-Chapter Authoring Guide (+ Addendum 1) in project knowledge for the
full standard. Load-bearing points:
- Three tabs: **How We Practice** (first-person plural, heaviest scripture density),
  **How It Blesses** (scriptural promise + concrete personal witness + bridge text),
  **How Will You Practice?** (three commitment tiers — covenant, seeker, explore —
  in that order; silent, not narrated).
- 3–5 cards per chapter. Draft and deploy as a complete unit; never a half-built
  chapter.
- Readiness check after the governing frame, before the first card. Overflow /
  prerequisite depth goes to a companion appendix, not into the cards.
- Every card drives toward commitment and character formation, not information.

## Slug & asset naming (standing ruling, Aug 7 2026)

The dividing line is "already published," not "which volume."

- **Vol 1 Ch 1-16 (published).** Numbered slugs
  (`/chapters/15-repentance-as-a-lifestyle/`) and the current asset scheme:
  `NR_##_`, `PO_##_`, `CC_##_`, `IG_##_`, `slides_path: "chapter-##/"`.
  Never retrofit. Renaming a published permalink costs 301s, R2 object
  renames, and a Cloudflare purge, for zero reader benefit.
- **Vol 1 Ch 17-31 (unwritten).** Unnumbered slugs from birth:
  `/chapters/searching-the-scriptures/`. Filenames keep their numbers so the
  directory sorts in reading order; only permalink and slug drop it.
- **Vol 2 (all).** Unnumbered slugs plus volume-tokened assets: `V2_NR_`,
  `V2_CC_`, `slides_path: "v2-chapter-01/"`. Required, not optional —
  `slides_path: "chapter-15/"` collides between Vol 1 Ch 15 (Repentance) and
  Vol 2 Ch 15 (Atonement), and R2 is a flat bucket with no namespacing.

Volumes are **not** continuously numbered. Cite chapters as "Vol 1 Ch 15" /
"Vol 2 Ch 15" everywhere — handoffs, RAG summaries, Discord channels, prose.

`chapterId` is always `chapter-` + slug, and lives in the chapter's `.njk`
frontmatter, never in `chapter-status.yaml`.

**Corollary:** no asset filename receives a chapter number until that
chapter's position is final. Assets stay deferred to the back end of a
drafting batch.
