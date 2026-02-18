# Words of Plainness — Card-Chapter Template Handoff

**Session Date:** February 16, 2026  
**Next Session Objective:** Develop a Card-Chapter Authoring Guide  
**Prepared for:** Aaron Powner

---

## 1. What Was Built This Session

A **Learning Tools** feature was added to the card-chapter template, modeled after the existing Learning Tools on the standard chapter template and the Ch6 interactive gateway. Three files were modified:

| File | What Changed |
|------|-------------|
| `src/_includes/layouts/card-chapter.njk` | Added collapsible accordion section + three conditional modals (Musical Testimony with lyrics, Infographic lightbox, Study Slides carousel). Placed between cumulative summary and Discord section. |
| `src/css/card-chapter.css` | Added ~270 lines: accordion toggle/panel, modal backdrop/container/header/body, lyrics details toggle, infographic image, slide carousel nav. Responsive rules for 480px breakpoint. |
| `src/js/card-chapter.js` | Added accordion toggle logic, `openCcModal()`/`closeCcModals()` (global scope), backdrop click + Escape key dismissal, audio pause on close, slide carousel with wrapping navigation. |

All new classes use the `cc-` prefix (card-chapter) to avoid collision with the `gw-` prefix used by Ch6 interactive modals and the unprefixed classes used by the standard chapter floating action bar.

### Learning Tools Menu Items

| Item | Behavior | Conditional on |
|------|----------|---------------|
| Musical Testimony | Opens modal with audio player + lyrics `<details>` dropdown | `audio.testimony` in frontmatter |
| Visual Summary | Opens lightbox modal with full-width image | `infographic` in frontmatter |
| Study Slides | Opens carousel modal with prev/next navigation | `slides` in frontmatter |
| Download PDF | Direct download link | `pdf` in frontmatter |
| Search All Chapters | Link to `/search/` | Always shown |
| How to Use This Website | Link to `/how-to-use/` | Always shown |

### Lyrics Include Pattern

The layout uses a dynamic Nunjucks include for lyrics:
```nunjucks
{% set lyricsPath = "lyrics/chapter-" + chapterId + ".njk" %}
{% include lyricsPath %}
```
This requires a corresponding `src/_includes/lyrics/chapter-XX.njk` file. Currently only `chapter-06.njk` exists. Each new card-chapter that includes a musical testimony will need its own lyrics partial.

---

## 2. Current Card-Chapter Architecture

### Files

```
src/
├── _includes/
│   ├── layouts/
│   │   └── card-chapter.njk          ← Layout template (THE file to study)
│   └── lyrics/
│       └── chapter-06.njk            ← Only existing lyrics partial
├── css/
│   └── card-chapter.css              ← All card-chapter styles
├── js/
│   └── card-chapter.js               ← All card-chapter interactivity
```

### Page Sections (top to bottom)

1. **Hero** — Chapter number, title, scripture quote
2. **How This Chapter Works** — Three-column explainer with icons
3. **Discipleship Cards** — Data-driven from `cards` array in frontmatter
   - Card header (number badge, title, scripture references)
   - Three tabs: How We Practice / How It Blesses / How Will You Practice?
   - Commitment radio options with tier tags (covenant/seeker/explore)
   - Custom input option + N/A option
   - Optional reflection textarea
   - Save button with localStorage persistence
4. **Cumulative Summary** — Auto-updating list of saved commitments + 5-star confidence rating
5. **Learning Tools** — Collapsible accordion (NEW this session)
6. **Modals** — Musical Testimony, Infographic, Study Slides (NEW this session)
7. **Discord Section** — Community link (shared component)
8. **Chapter Navigation** — Prev/Next links (shared component)
9. **Back to Top** — Scroll button (shared component)

### CSS Dependencies

The card-chapter layout loads **two** stylesheets:
```html
<link rel="stylesheet" href="/css/chapter.css">      ← Base chapter styles (dropdowns, nav, discord, etc.)
<link rel="stylesheet" href="/css/card-chapter.css">  ← Card-specific styles + learning tools/modals
```

### JS Dependencies

```html
<script src="/js/card-chapter.js"></script>
```
Contains tab switching, commitment save/restore, star rating, learning tools accordion, modal management, and slide carousel — all in one file.

---

## 3. Complete Frontmatter Schema for Card-Chapters

This is the full set of frontmatter fields the card-chapter layout consumes. The authoring guide should document each field with examples.

```yaml
---
title: "Chapter Title"
chapter: 7
slug: "07-chapter-slug"
chapterId: "07"                        # Used for lyrics include path + localStorage key
layout: layouts/card-chapter.njk

scripture:
  text: "Scripture quote text"
  reference: "Book Chapter:Verse"
  url: "nt/gal/3?lang=eng&id=p26#p26"  # Path after /study/scriptures/

# Audio assets
audio:
  testimony:
    title: "Song Title"
    description: "Brief thematic description"
    file: "07.1 Song Title - Genre.mp3"    # Filename only, template prepends /assets/audio/

lyrics: true                               # Set true if lyrics/chapter-{chapterId}.njk exists

# Visual assets
infographic: "chapter-07-infographic.png"  # Filename only, template prepends /assets/images/

slides:
  path: "WoP_Ch07/"                        # Folder under /assets/slides/ (include trailing slash)
  count: 9                                 # Total number of slide PNGs (slide-01.png through slide-XX.png)

pdf: "WoP_Ch07_Title.pdf"                 # Filename only, template prepends /assets/pdf/

# Navigation
prevChapter:
  url: "/chapters/06-embrace-the-savior/"
  title: "Chapter 6: Embrace the Savior"
nextChapter:
  url: "/chapters/08-next-slug/"
  title: "Chapter 8: Next Title"

discordChannelId: "1234567890123456789"

# ============================================================
# DISCIPLESHIP CARDS — The core content
# ============================================================
cards:
  - title: "Card Title (Discipleship Practice)"
    scriptures:
      - display: "Matthew 5:44"
        url: "nt/matt/5?lang=eng&id=p44#p44"
      - display: "3 Nephi 12:44"
        url: "bofm/3-ne/12?lang=eng&id=p44#p44"
    practice: |
      <h4>Teaching Subheading</h4>
      <p>Latter-day Saint doctrinal teaching on this practice. HTML is rendered
      via the <code>| safe</code> filter. Multiple paragraphs allowed.</p>
      <p>Scripture references will be auto-linked by the scripture linker
      if present on the page.</p>
    blesses: |
      <p>Personal witness and testimony about how this practice blesses lives.
      Written in Aaron's pastoral voice.</p>
      <p class="bridge-text">A transitional statement connecting doctrine to
      personal application.</p>
    commitments:
      - text: "Full covenant-level commitment description"
        tier: covenant
      - text: "Moderate seeker-level commitment description"
        tier: seeker
      - text: "Entry-level exploration commitment description"
        tier: explore
    reflection: "Optional reflection prompt — appears as italic text above a textarea"

  - title: "Second Card Title"
    scriptures:
      - display: "John 3:16"
        url: "nt/john/3?lang=eng&id=p16#p16"
    practice: |
      <p>Content for second card...</p>
    blesses: |
      <p>Content for second card...</p>
    commitments:
      - text: "Covenant commitment"
        tier: covenant
      - text: "Seeker commitment"
        tier: seeker
      - text: "Explore commitment"
        tier: explore
    reflection: ""
---
```

---

## 4. Key Differences: Card-Chapter vs. Standard Chapter

| Feature | Standard Chapter (`chapter.njk`) | Card-Chapter (`card-chapter.njk`) |
|---------|----------------------------------|-----------------------------------|
| Content source | Markdown body with sentence shortcodes | YAML frontmatter `cards` array with inline HTML |
| Audio narration | Full chapter narration with sentence-level timestamps | None (no narration audio sync) |
| Reading experience | Linear scroll with floating action bar | Tabbed cards with save-as-you-go |
| Learning Tools | Floating action bar dropdown + bottom duplicate | Collapsible accordion below summary |
| Personalization | Reflection journal modal | Per-card commitments + reflection textareas |
| Persistence | Django API (reading progress, reflections) | localStorage only (client-side) |
| Table of Contents | TOC sidebar + mobile TOC | None (cards serve as implicit structure) |
| Podcast / Overview | Audio modal with transcript | Not included |

### What the card-chapter does NOT have (by design)

- No sentence shortcodes or audio timestamp sync
- No floating action bar (no narration to control)
- No TOC (card structure replaces it)
- No `readingTime` field
- No `toc` array in frontmatter
- No `podcastTranscript` field
- No `audio.narration` or `audio.overview` fields

---

## 5. Decisions Needed for the Authoring Guide

These are open questions or ambiguities the next session should resolve:

### Content Authoring

1. **How many cards per chapter?** Is there a target range (3–5? 5–7?) or does it vary by topic?

2. **Commitment tier definitions:** The three tiers (covenant/seeker/explore) need clear authoring guidance. What distinguishes each tier? How specific should commitments be?

3. **HTML in frontmatter:** The `practice` and `blesses` fields use raw HTML piped through `| safe`. Should the guide recommend specific HTML patterns (e.g., always start with `<h4>`, use `<p class="bridge-text">` for transitions)?

4. **Scripture URL format:** Card-chapter scripture URLs use the full path format (`nt/matt/5?lang=eng&id=p44#p44`) rather than the simplified reference format used in chapter body text. The guide needs to document URL construction rules or provide a lookup table.

5. **Reflection prompts:** Should every card have one, or are they optional? The current template conditionally renders them.

### Asset Production

6. **Musical testimony scope:** Aaron specified the testimony should "reflect upon the 3 to 5 main discipleship practices" in the chapter. Does this mean one song per card-chapter covering all cards, not one song per card?

7. **Slides path convention:** The standard chapter uses `chapter-##/` folder naming for slides (per the frontmatter reference doc), but the card-chapter template currently has `WoP_Ch##/` in the example. Which convention should card-chapters follow?

8. **Lyrics partial naming:** Currently keyed to `chapterId` field. If `chapterId: "07"`, the include resolves to `lyrics/chapter-07.njk`. Is this correct, or should it match the full slug pattern?

### Template Evolution

9. **"How This Chapter Works" section:** Currently hardcoded in the layout with specific icon images (`lds_faith.png`, `blessings.png`, `shield_of_faith.png`). Should this be configurable per chapter, or is it intentionally consistent across all card-chapters?

10. **Summary export:** The cumulative summary currently lives in localStorage only. Is there a planned feature to export or sync commitments to the Django API (similar to how standard chapters sync reading progress)?

---

## 6. Existing Documentation to Update

When the Card-Chapter Authoring Guide is complete, these existing project documents should be cross-referenced or updated:

| Document | What Needs Updating |
|----------|-------------------|
| `WoP-Eleventy-Frontmatter-Reference.md` | Add card-chapter frontmatter schema (currently only documents standard chapter fields) |
| `WoP-Eleventy-Content-Workflow-updated-01292026.md` | Add card-chapter production workflow variant (currently only documents standard chapter pipeline) |
| `WOP-Development-Handoff-Feb2026.docx` | Chapter status table needs updating (Ch4–5 deployed, Ch6 interactive deployed, Ch7+ as card-chapters) |
| Memory / `recent_updates` | Confirm card-chapter Learning Tools feature is captured |

---

## 7. Verification Before Next Session

The Learning Tools feature has not been tested on a live page because no card-chapter content file exists yet. Before or during the next session:

- [ ] Create a minimal test card-chapter `.njk` file with dummy frontmatter to verify the layout renders
- [ ] Confirm the accordion toggle opens/closes
- [ ] Confirm modals open, close on backdrop click, and close on Escape
- [ ] Confirm slide carousel wraps correctly
- [ ] Confirm audio player loads and lyrics toggle works
- [ ] Confirm graceful degradation when optional frontmatter fields are omitted

### Quick Test Frontmatter

```yaml
---
title: "Test Card Chapter"
chapter: 99
slug: "99-test"
chapterId: "99"
layout: layouts/card-chapter.njk
scripture:
  text: "Test scripture"
  reference: "Test 1:1"
  url: "nt/matt/1?lang=eng&id=p1#p1"
cards:
  - title: "Test Card"
    scriptures:
      - display: "Test 1:1"
        url: "nt/matt/1?lang=eng&id=p1#p1"
    practice: "<p>Test practice content.</p>"
    blesses: "<p>Test blessing content.</p>"
    commitments:
      - text: "Covenant test"
        tier: covenant
      - text: "Seeker test"
        tier: seeker
    reflection: "Test reflection prompt"
prevChapter:
  url: "/chapters/06-embrace-the-savior/"
  title: "Chapter 6: Embrace the Savior"
---
```

---

*— End of Handoff Note —*
