# Context Handoff: Main Editorial Project WoP

**From:** Ministry Development 2026 → Eleventy Migration Session  
**To:** Main Editorial Project WoP  
**Date:** January 29, 2026

---

## Project Status Summary

The Words of Plainness website has been **fully migrated to Eleventy** and is **live in production**.

### Live Site
```
https://words-of-plainness.vercel.app
```

### Repository
```
https://github.com/aaronpowner1970/words-of-plainness
Branch: main (production)
```

---

## What's Complete

### Architecture
- ✅ Eleventy static site generator with Nunjucks templating
- ✅ Modular CSS and JavaScript
- ✅ Content in Markdown with YAML frontmatter
- ✅ Automated deployments via Vercel (push to main → auto-deploy)

### Chapters
| Chapter | Status | Audio Sync | All Features |
|---------|--------|------------|--------------|
| 1: Introduction | ✅ Complete | ✅ Working | ✅ Yes |
| 2: Our Search for Meaning | ✅ Complete | ✅ Working | ✅ Yes |
| 3-10 | ⬜ Not started | — | — |

### Static Pages
- ✅ Homepage (hero, menu cards)
- ✅ Writings (dynamic chapter list)
- ✅ Music (full playlist player)
- ✅ Discipleship
- ✅ Connect
- ✅ About
- ✅ New Here

### Features Working
- Audio narration with sentence highlighting
- Click-to-seek (click sentence → audio jumps)
- Speed control (0.75x, 1x, 1.25x, 1.5x)
- Study resources (slides, PDF, podcast, musical testimony, infographic)
- Scripture auto-linking (opens churchofjesuschrist.org in new tab)
- Reflections with save button
- Bookmark/resume functionality
- Share button
- TOC sidebar (desktop) and mobile panel
- Responsive mobile layout with FAB
- Music page with full playlist (shuffle, repeat, volume, download)
- Auth UI (Sign In / Join Free buttons)

---

## For Editorial Work

### Chapter File Locations
```
src/chapters/01-introduction.md
src/chapters/02-our-search-for-meaning.md
```

### Chapter Frontmatter Structure
```yaml
---
title: "Chapter Title"
chapter: 1
layout: layouts/chapter.njk
scripture:
  text: "Scripture quote here"
  reference: "Book Chapter:Verse"
readingTime: "~15 min read"
audio:
  narration: /assets/audio/chapter-01-narration.mp3
  overview: /assets/audio/chapter-01-overview.mp3
  testimony:
    file: /assets/audio/01_1_Song_Title_-_Sacred_Americana_Testimony.mp3
    title: "Song Title"
    description: "One-line theme description"
pdf: /assets/pdf/WoP_Ch01_Title.pdf
infographic: /assets/images/chapter-01-infographic.png
slidesPath: "WoP_Ch01"
slidesCount: 9
toc:
  - id: section-id
    title: Section Title
navigation:
  prevChapter: null
  prevTitle: null
  nextChapter: "/chapters/02-our-search-for-meaning/"
  nextTitle: "Our Search for Meaning"
discordChannelId: "1234567890"
---
```

### Sentence Markup
Content uses sentence shortcodes for audio sync:
```markdown
{% sentence 0 %}First sentence of the chapter.{% endsentence %}
{% sentence 1 %}Second sentence continues here.{% endsentence %}
```

### Scripture References
Scriptures are auto-linked. Just write them naturally:
```markdown
As we read in 2 Nephi 31:3, the Lord works in plainness.
```

### Adding a New Chapter
1. Create `src/chapters/##-slug.md` with frontmatter
2. Wrap all sentences in `{% sentence N %}` shortcodes
3. Add timestamps to `src/_data/timestamps/chapter-##-slug.json`
4. Add audio files to `src/assets/audio/`
5. Add slides to `src/assets/slides/`
6. Update previous chapter's `nextChapter` navigation
7. Commit and push → auto-deploys

---

## Key Technical Notes

### Timestamps Format
Stored in `src/_data/timestamps/chapter-##-slug.json`:
```json
{
  "0": 0.0,
  "1": 2.8,
  "2": 5.4
}
```
Keys are sentence indices (as strings), values are start times in seconds.

### ElevenLabs Voice ID
```
As8zJaZyH4MAgaQ93FMc
```

### Brand Colors
| Name | Hex |
|------|-----|
| Gold Primary | #C4943A |
| Cream | #E8DCC4 |
| Deep Brown | #3D2B1F |
| Rich Brown | #2A1D14 |
| Burgundy | #6B3D3D |
| Teal Muted | #4A6B6B |

---

## Chapter Production Workflow Reference

See the uploaded document: **WOP-Chapter-Production-Workflow.docx**

Updated workflow for Eleventy:
1. **Editorial:** AI-assisted review with Church Style Guide
2. **Documents:** Final DOCX and PDF
3. **Media:** Audio (ElevenLabs), music (Suno), slides, infographic
4. **Website:** Create Markdown file with sentence shortcodes
5. **Testing:** Verify audio sync, all features
6. **Deployment:** `git push origin main` → auto-deploys

**Estimated time per chapter:** 2-4 hours (down from 8-13 hours pre-migration)

---

## Pending Tasks

- [ ] Chapters 3-10 production
- [ ] Update Chapter Production Workflow documentation for Eleventy process
- [ ] Gather development history from other projects

---

## Questions for Editorial Sessions

When working on chapter content, key questions:
1. Is the content finalized and reviewed per Church Style Guide?
2. Are all scripture references accurate? (Will be auto-linked)
3. Is the audio narration recorded and timestamped?
4. Are study materials ready (slides, infographic)?

---

*This handoff prepared by Claude on January 29, 2026*
