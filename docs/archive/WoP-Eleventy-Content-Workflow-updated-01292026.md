# Words of Plainness — Content & Administration Workflow

**Eleventy Architecture Edition**  
**Version 2.0 — January 29, 2026**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Quick Reference](#2-quick-reference)
3. [Chapter Production Workflow](#3-chapter-production-workflow)
4. [Static Page Management](#4-static-page-management)
5. [Music Page Management](#5-music-page-management)
6. [Asset Management](#6-asset-management)
7. [Styling & Design Updates](#7-styling--design-updates)
8. [JavaScript & Interactivity](#8-javascript--interactivity)
9. [Authentication & User Features](#9-authentication--user-features)
10. [Testing Procedures](#10-testing-procedures)
11. [Deployment](#11-deployment)
12. [Troubleshooting](#12-troubleshooting)
13. [Appendices](#13-appendices)

---

## 1. Architecture Overview

### Directory Structure

```
words-of-plainness/
├── src/
│   ├── _data/                    # Global data files
│   │   ├── navigation.json       # Site navigation menu
│   │   ├── site.json             # Site metadata
│   │   └── timestamps/           # Audio timestamp files
│   │       ├── chapter-01-introduction.json
│   │       └── chapter-02-our-search-for-meaning.json
│   │
│   ├── _includes/
│   │   ├── layouts/              # Page templates
│   │   │   ├── base.njk          # Master template (header, footer)
│   │   │   ├── chapter.njk       # Chapter page template
│   │   │   └── page.njk          # Generic page template
│   │   │
│   │   ├── components/           # Reusable UI components
│   │   │   ├── floating-action-bar.njk
│   │   │   ├── modals.njk
│   │   │   ├── study-resources.njk
│   │   │   └── toc-mobile.njk
│   │   │
│   │   └── partials/             # Page sections
│   │       ├── header.njk
│   │       └── footer.njk
│   │
│   ├── assets/                   # Static assets
│   │   ├── audio/                # Audio files
│   │   ├── images/               # Images and graphics
│   │   ├── pdf/                  # Downloadable PDFs
│   │   ├── slides/               # Study slide images
│   │   └── favicons/             # Favicon files
│   │
│   ├── chapters/                 # Chapter content (Markdown)
│   │   ├── 01-introduction.md
│   │   └── 02-our-search-for-meaning.md
│   │
│   ├── css/                      # Stylesheets
│   │   ├── styles.css            # Main styles
│   │   ├── chapter.css           # Chapter-specific styles
│   │   ├── music.css             # Music page styles
│   │   └── auth-modal.css        # Authentication modal styles
│   │
│   ├── js/                       # JavaScript files
│   │   ├── chapter.js            # Chapter functionality
│   │   ├── audio-sync.js         # Audio synchronization
│   │   ├── music-player.js       # Music page player
│   │   ├── api.js                # API communication
│   │   └── auth-modal.js         # Authentication modals
│   │
│   └── pages/                    # Static pages (Nunjucks)
│       ├── index.njk             # Homepage
│       ├── writings.njk          # Writings/chapters listing
│       ├── music.njk             # Music playlist page
│       ├── discipleship.njk
│       ├── connect.njk
│       ├── about.njk
│       └── new-here.njk
│
├── _site/                        # Built output (auto-generated)
├── .eleventy.js                  # Eleventy configuration
├── package.json                  # Node dependencies
└── vercel.json                   # Vercel deployment config
```

### Build Pipeline

```
Source Files (src/) 
    ↓ 
Eleventy Build (npm run build)
    ↓
Output (_site/)
    ↓
Git Push (main branch)
    ↓
Vercel Auto-Deploy
    ↓
Production (words-of-plainness.vercel.app)
```

### Key Technologies

| Component | Technology |
|-----------|------------|
| Static Site Generator | Eleventy (11ty) |
| Templating | Nunjucks (.njk) |
| Content | Markdown with YAML frontmatter |
| Styling | CSS (no preprocessor) |
| Interactivity | Vanilla JavaScript |
| Hosting | Vercel |
| API Backend | Django on PythonAnywhere |
| Audio Generation | ElevenLabs |
| Music Generation | Suno AI |

---

## 2. Quick Reference

### Common Commands

```bash
# Start development server
npm run serve
# → Opens at http://localhost:8080 (or next available port)

# Build for production
npm run build

# Check build output
ls -la _site/

# Deploy (auto-deploys on push to main)
git add .
git commit -m "Description of changes"
git push origin main
```

### File Locations Quick Reference

| Content Type | Location |
|--------------|----------|
| Chapter content | `src/chapters/##-slug.md` |
| Chapter timestamps | `src/_data/timestamps/chapter-##-slug.json` |
| Static pages | `src/pages/pagename.njk` |
| Navigation menu | `src/_data/navigation.json` |
| Audio files | `src/assets/audio/` |
| Images | `src/assets/images/` |
| PDFs | `src/assets/pdf/` |
| Study slides | `src/assets/slides/ChapterFolder/` |
| Main CSS | `src/css/styles.css` |
| Chapter CSS | `src/css/chapter.css` |
| Chapter JS | `src/js/chapter.js` |

### Brand Colors

| Name | Hex | Usage |
|------|-----|-------|
| Gold Primary | `#C4943A` | Headings, links, accents |
| Cream | `#E8DCC4` | Body text, light backgrounds |
| Deep Brown | `#3D2B1F` | Backgrounds |
| Rich Brown | `#2A1D14` | Dark backgrounds |
| Burgundy | `#6B3D3D` | Accent color |
| Teal Muted | `#4A6B6B` | Secondary accent |

---

## 3. Chapter Production Workflow

### Overview

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| 1. Editorial | Style guide, grammar, scripture review | 1-2 hours |
| 2. Documents | Final DOCX and PDF export | 30 minutes |
| 3. Media | Audio, music, podcast, slides, infographic | 3-5 hours |
| 4. Website | Markdown file, timestamps, assets | 1-2 hours |
| 5. Testing | Feature verification, cross-browser | 30-60 min |
| 6. Deployment | Commit, push, verify | 15 minutes |
| **TOTAL** | | **6-10 hours** |

---

### Phase 1: Editorial Process

#### Step 1.1: Prepare Source Document

**Input:** Raw chapter manuscript (DOCX or Google Doc)  
**Output:** Edited document ready for production

1. Open source document
2. Enable Track Changes (if using Word)
3. Create backup copy
4. Note existing footnotes for conversion to inline citations

#### Step 1.2: AI-Assisted Editorial Review

**Tool:** Claude.ai | **Time:** 30-60 minutes

**Editorial Focus Areas:**
- **Footnote Conversion:** Convert to inline citations
- **Church Style Guide:** Align terminology per current guidelines
- **Grammar & Style:** Active voice, sentence variety, transitions
- **Tone Consistency:** Pastoral warmth, scholarly accuracy
- **Scripture Review:** Verify citations, standardize format
- **Accessibility:** Define terms, ensure interfaith accessibility

**Church Style Guide Quick Reference:**

| ❌ Avoid | ✅ Use |
|----------|--------|
| Mormon | Member of The Church of Jesus Christ of Latter-day Saints |
| LDS | The Church, or the full name |
| Mormon Church | The Church of Jesus Christ of Latter-day Saints |
| Mormonism | The restored gospel of Jesus Christ |

#### Step 1.3: Review & Accept Edits

**Time:** 20-40 minutes

1. Review all suggested changes
2. Accept/reject each edit with Track Changes
3. Resolve editorial notes or queries
4. Read through for flow and coherence
5. Save as `chapter-##-[slug]-edited.docx`

---

### Phase 2: Final Document Production

#### Step 2.1: DOCX Export

1. Remove all Track Changes (Accept All)
2. Remove all comments
3. Apply consistent heading styles
4. Save as `chapter-##-[slug]-final.docx`

#### Step 2.2: PDF Export

1. Open final DOCX
2. File → Export → Create PDF/XPS
3. Optimize for: Standard (publishing online)
4. Save as `WoP_Ch##_[Title].pdf`
5. Copy to `src/assets/pdf/`

---

### Phase 3: Media Production

#### Step 3.1: Audio Narration

**Tool:** ElevenLabs API  
**Voice ID:** `As8zJaZyH4MAgaQ93FMc`

1. Export plain text from final document
2. Split into chunks (~1000 characters)
3. Generate audio via ElevenLabs
4. Process with ffmpeg for proper encoding
5. Generate sentence-level timestamps
6. Save audio as `chapter-##-narration.mp3`
7. Save timestamps as JSON (see Step 4.3)

**Timestamp Generation:**
```bash
python generate-chapter-audio-chunked.py
python fix-audio-ffmpeg.py
python convert-to-sentence-timestamps.py
```

#### Step 3.2: Musical Testimony

**Tool:** Suno AI | **Time:** 1-2 hours

1. Review chapter themes and key messages
2. Draft lyrics (2-3 verses + chorus) using Claude
3. Review for theological accuracy
4. Generate music in Suno with style prompt (Sacred Americana)
5. Select best version, download MP3
6. Save as: `##_1_[Song_Title]_-_Sacred_Americana_Testimony.mp3`

#### Step 3.3: Chapter Overview Podcast

**Tool:** ElevenLabs | **Time:** 1-2 hours

**Podcast Structure (5-8 minutes):**
- Intro (30 sec): Welcome, chapter introduction
- Context (1-2 min): Questions addressed, why it matters
- Key Themes (2-3 min): Main points explained
- Scripture Highlight (1 min): Key verse and reflection
- Invitation (30 sec): Encourage full reading, mention Discord
- Outro (15 sec): Thank you, closing

Save as: `chapter-##-overview.mp3`

#### Step 3.4: Group Study Slides

**Tool:** Google Slides | **Time:** 1-2 hours

**Recommended Structure (8-12 slides):**
- Title slide with scripture epigraph
- Overview of chapter themes
- Key concepts with supporting scripture (2-3 sections)
- Reflection questions for group discussion
- Summary and call to action

**Export:**
1. File → Download → PNG images
2. Rename: `slide-01.png`, `slide-02.png`, etc.
3. Create folder: `src/assets/slides/WoP_Ch##/`
4. Copy slides to folder

#### Step 3.5: Infographic Summary

**Tool:** Canva or similar | **Time:** 30-60 minutes

- Chapter title and 3-5 key points
- 1-2 scripture references
- Portrait orientation, brand colors
- Export as PNG to `src/assets/images/chapter-##-infographic.png`

---

### Phase 4: Website Assembly

#### Step 4.1: Create Chapter Markdown File

Create new file: `src/chapters/##-[slug].md`

**Complete Frontmatter Template:**

```yaml
---
title: "Chapter Title"
chapter: ##
layout: layouts/chapter.njk
scripture:
  text: "Scripture quote text here"
  reference: "Book Chapter:Verse"
readingTime: "~## min read"
audio:
  narration: /assets/audio/chapter-##-narration.mp3
  overview: /assets/audio/chapter-##-overview.mp3
  testimony:
    file: /assets/audio/##_1_Song_Title_-_Sacred_Americana_Testimony.mp3
    title: "Song Title"
    description: "One-line description of song themes"
pdf: /assets/pdf/WoP_Ch##_Title.pdf
infographic: /assets/images/chapter-##-infographic.png
slidesPath: "WoP_Ch##"
slidesCount: 9
toc:
  - id: section-1-id
    title: First Section Title
  - id: section-2-id
    title: Second Section Title
  - id: section-3-id
    title: Third Section Title
navigation:
  prevChapter: "/chapters/##-previous-slug/"
  prevTitle: "Previous Chapter Title"
  nextChapter: "/chapters/##-next-slug/"
  nextTitle: "Next Chapter Title"
discordChannelId: "DISCORD_CHANNEL_ID"
---
```

#### Step 4.2: Add Chapter Content with Sentence Markup

Wrap each sentence in shortcodes for audio synchronization:

```markdown
## Section Title {#section-1-id}

{% sentence 0 %}First sentence of the chapter.{% endsentence %}
{% sentence 1 %}Second sentence continues the thought.{% endsentence %}
{% sentence 2 %}Third sentence here.{% endsentence %}

## Next Section {#section-2-id}

{% sentence 3 %}Content continues with sequential numbering.{% endsentence %}
{% sentence 4 %}Each sentence gets a unique index.{% endsentence %}
```

**Important Rules:**
- Sentence indices must be sequential (0, 1, 2, 3...)
- Indices continue across sections (don't restart at each heading)
- Section IDs must match the `toc` entries in frontmatter
- Scripture references are auto-linked (just write them naturally)

#### Step 4.3: Create Timestamp File

Create: `src/_data/timestamps/chapter-##-[slug].json`

```json
{
  "0": 0.0,
  "1": 2.847,
  "2": 5.234,
  "3": 8.901,
  "4": 12.456
}
```

**Format:**
- Keys: Sentence indices as strings
- Values: Start time in seconds (float)
- Generated from ElevenLabs audio processing

#### Step 4.4: Update Navigation

**Previous Chapter:**
Edit the previous chapter's frontmatter to add `nextChapter` and `nextTitle`:

```yaml
navigation:
  prevChapter: "/chapters/##-earlier/"
  prevTitle: "Earlier Chapter"
  nextChapter: "/chapters/##-new-chapter/"
  nextTitle: "New Chapter Title"
```

#### Step 4.5: Copy Assets

Copy all media files to appropriate locations:

```bash
# Audio files
cp chapter-##-narration.mp3 src/assets/audio/
cp chapter-##-overview.mp3 src/assets/audio/
cp ##_1_Song_Title_-_Sacred_Americana_Testimony.mp3 src/assets/audio/

# PDF
cp WoP_Ch##_Title.pdf src/assets/pdf/

# Infographic
cp chapter-##-infographic.png src/assets/images/

# Slides (create folder first)
mkdir -p src/assets/slides/WoP_Ch##/
cp slide-*.png src/assets/slides/WoP_Ch##/
```

#### Step 4.6: Create Discord Channel

1. Create new channel in Discord server for chapter discussion
2. Copy the channel ID
3. Add to chapter frontmatter: `discordChannelId: "CHANNEL_ID"`

---

### Phase 5: Testing

#### Pre-Deployment Checklist

**Navigation & Layout:**
- [ ] Header links work
- [ ] Mobile menu functions
- [ ] TOC sidebar links jump correctly (desktop)
- [ ] TOC mobile panel works
- [ ] Previous/Next chapter links correct
- [ ] Back-to-top button appears
- [ ] Reading progress bar updates

**Audio Features:**
- [ ] Read Aloud button shows player
- [ ] Play/pause works
- [ ] Seek bar functions
- [ ] Speed control works (0.75x, 1x, 1.25x, 1.5x)
- [ ] Text highlighting syncs with audio
- [ ] Click-to-seek works (click sentence → audio jumps)
- [ ] Scripture links don't trigger audio playback

**Interactive Features:**
- [ ] Font size controls work (A- A A+)
- [ ] Bookmark saves and restores
- [ ] Share button works
- [ ] Reflections save to localStorage

**Study Resources:**
- [ ] PDF download works
- [ ] Audio overview plays in modal
- [ ] Testimony music plays in modal
- [ ] Infographic displays in modal
- [ ] Slides carousel functions
- [ ] Fullscreen mode works for slides

**Discord & Responsive:**
- [ ] Discord section displays correctly
- [ ] Join button links to server
- [ ] Desktop layout (1200px+)
- [ ] Tablet layout (768-1199px)
- [ ] Mobile layout (<768px)

---

### Phase 6: Deployment

#### Step 6.1: Commit Changes

```bash
git add .
git commit -m "Add Chapter ##: [Title]

- Full chapter content with sentence markup
- Audio narration with timestamps
- Musical testimony: [Song Title]
- Study slides (## slides)
- PDF download
- Discord channel integration"
```

#### Step 6.2: Push to Deploy

```bash
git push origin main
```

Vercel automatically deploys when changes are pushed to `main`.

#### Step 6.3: Post-Deployment Verification

1. Visit production URL: `https://words-of-plainness.vercel.app`
2. Navigate to new chapter
3. Test audio playback and sync
4. Verify all study resources load
5. Test on mobile device

#### Step 6.4: Announcements

- [ ] Post in Discord #announcements
- [ ] Update Writings page if needed (auto-updates from collection)
- [ ] Share on social media (if applicable)

---

## 4. Static Page Management

### Page Locations

| Page | File | URL |
|------|------|-----|
| Homepage | `src/pages/index.njk` | `/` |
| Writings | `src/pages/writings.njk` | `/writings/` |
| Music | `src/pages/music.njk` | `/music/` |
| Discipleship | `src/pages/discipleship.njk` | `/discipleship/` |
| Connect | `src/pages/connect.njk` | `/connect/` |
| About | `src/pages/about.njk` | `/about/` |
| New Here | `src/pages/new-here.njk` | `/new-here/` |

### Basic Page Structure

```nunjucks
---
title: Page Title
layout: layouts/page.njk
permalink: /page-url/
---

<section class="page-section">
    <h1>Page Heading</h1>
    <p>Content here...</p>
</section>
```

### Editing Static Pages

1. Open the appropriate `.njk` file
2. Edit content within the template
3. Use Nunjucks syntax for dynamic content:
   ```nunjucks
   {% for item in collection %}
       <div>{{ item.title }}</div>
   {% endfor %}
   ```
4. Test locally with `npm run serve`
5. Commit and push to deploy

### Adding a New Static Page

1. Create file: `src/pages/new-page.njk`
2. Add frontmatter:
   ```yaml
   ---
   title: New Page Title
   layout: layouts/page.njk
   permalink: /new-page/
   ---
   ```
3. Add content below frontmatter
4. Add to navigation (see Section 4.4)
5. Test and deploy

### Updating Navigation Menu

Edit `src/_data/navigation.json`:

```json
{
  "main": [
    { "label": "Home", "url": "/" },
    { "label": "Writings", "url": "/writings/" },
    { "label": "Music", "url": "/music/" },
    { "label": "Discipleship", "url": "/discipleship/" },
    { "label": "Connect", "url": "/connect/" },
    { "label": "About", "url": "/about/" }
  ]
}
```

---

## 5. Music Page Management

### Adding a New Song

When a new chapter is published with a musical testimony:

1. **Update chapter frontmatter** with testimony details:
   ```yaml
   audio:
     testimony:
       file: /assets/audio/##_1_Song_Title_-_Sacred_Americana_Testimony.mp3
       title: "Song Title"
       description: "One-line theme description"
   ```

2. **Copy audio file** to `src/assets/audio/`

3. **The Music page automatically updates** — it pulls from `collections.chapters`

### Music Page Features

The playlist automatically includes all chapters with testimony data:
- Song title (clickable to play)
- Theme description
- Chapter link
- Duration
- Download button

### Player Controls Reference

| Control | Function |
|---------|----------|
| ▶ / ⏸ | Play / Pause |
| ⏮ | Previous track |
| ⏭ | Next track |
| 🔀 | Shuffle mode toggle |
| 🔁 | Repeat mode (off → all → one) |
| Volume slider | Adjust playback volume |
| Progress bar | Seek within track |

---

## 6. Asset Management

### Audio Files

**Location:** `src/assets/audio/`

**Naming Conventions:**
| Type | Format |
|------|--------|
| Narration | `chapter-##-narration.mp3` |
| Podcast | `chapter-##-overview.mp3` |
| Testimony | `##_#_Song_Title_-_Sacred_Americana_Testimony.mp3` |

**Requirements:**
- Format: MP3
- Properly encoded for web streaming (seekable)
- Reasonable file size (optimize for web)

### Images

**Location:** `src/assets/images/`

**Types:**
| Type | Naming | Dimensions |
|------|--------|------------|
| Infographic | `chapter-##-infographic.png` | Portrait, ~800px wide |
| General images | `descriptive-name.png/jpg` | As needed |
| Backgrounds | `background-name.jpg` | 1920px wide recommended |

**Optimization:**
- Compress images before adding
- Use appropriate format (PNG for transparency, JPG for photos)
- Consider WebP for better compression

### PDFs

**Location:** `src/assets/pdf/`

**Naming:** `WoP_Ch##_Title.pdf`

### Study Slides

**Location:** `src/assets/slides/[ChapterFolder]/`

**Structure:**
```
src/assets/slides/
├── WoP_Ch01/
│   ├── slide-01.png
│   ├── slide-02.png
│   └── ...
├── WoP_Ch02/
│   ├── slide-01.png
│   └── ...
```

**Requirements:**
- PNG format
- Sequential naming: `slide-01.png`, `slide-02.png`, etc.
- Consistent dimensions across slides
- Update `slidesCount` in chapter frontmatter

### Favicons

**Location:** `src/assets/favicons/`

**Files needed:**
- `favicon.ico` (multi-size)
- `favicon-16x16.png`
- `favicon-32x32.png`
- `apple-touch-icon.png` (180x180)
- `android-chrome-192x192.png`
- `android-chrome-512x512.png`

---

## 7. Styling & Design Updates

### CSS File Organization

| File | Purpose |
|------|---------|
| `src/css/styles.css` | Global styles, layout, header, footer |
| `src/css/chapter.css` | Chapter page specific styles |
| `src/css/music.css` | Music page player styles |
| `src/css/auth-modal.css` | Authentication modal styles |

### Making Style Changes

1. Identify the appropriate CSS file
2. Make changes using CSS custom properties where possible:
   ```css
   .element {
       color: var(--gold-primary);
       background: var(--rich-brown);
   }
   ```
3. Test at multiple viewport sizes
4. Verify changes don't break other pages

### CSS Custom Properties (Variables)

Defined in `styles.css`:
```css
:root {
    --gold-primary: #C4943A;
    --cream: #E8DCC4;
    --deep-brown: #3D2B1F;
    --rich-brown: #2A1D14;
    --burgundy: #6B3D3D;
    --teal-muted: #4A6B6B;
}
```

### Z-Index Hierarchy

Maintain this stacking order:
| Element | Z-Index |
|---------|---------|
| Base content | auto |
| TOC sidebar | 100 |
| Music player bar | 100 |
| Floating action bar | 1001 |
| FAB dropdown | 1002 |
| Bookmark prompt | 1500 |
| Modals backdrop | 2000 |
| Modals content | 2001 |
| Auth modal | 3000 |

### Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 767px) { }

/* Tablet */
@media (min-width: 768px) and (max-width: 1199px) { }

/* Desktop */
@media (min-width: 1200px) { }
```

---

## 8. JavaScript & Interactivity

### JavaScript Files

| File | Purpose |
|------|---------|
| `src/js/chapter.js` | Chapter page functionality |
| `src/js/audio-sync.js` | Audio-text synchronization |
| `src/js/music-player.js` | Music page playlist player |
| `src/js/api.js` | API communication, auth state |
| `src/js/auth-modal.js` | Login/signup modal handling |

### Key Functions Reference

**Audio Sync (`audio-sync.js`):**
- `highlightSentence(index)` — Highlight specific sentence
- `seekToSentence(index)` — Jump audio to sentence
- `updateProgress()` — Update UI during playback

**Chapter (`chapter.js`):**
- `initChapter()` — Initialize all chapter features
- `toggleAudioPlayer()` — Show/hide audio controls
- `saveReflection()` — Save user reflection
- `setBookmark()` / `restoreBookmark()` — Bookmark functionality

**Music Player (`music-player.js`):**
- `playTrack(index)` — Play specific track
- `toggleShuffle()` — Toggle shuffle mode
- `cycleRepeat()` — Cycle repeat modes

### Adding New Functionality

1. Determine appropriate JS file (or create new one)
2. Follow existing code patterns
3. Test thoroughly across browsers
4. Ensure mobile compatibility
5. Add to base layout if needed:
   ```html
   <script src="/js/new-script.js"></script>
   ```

---

## 9. Authentication & User Features

### Current Auth System

| Component | Status |
|-----------|--------|
| Sign In / Sign Up modals | ✅ Functional |
| Django API backend | ✅ On PythonAnywhere |
| User menu UI | ✅ Shows after login |
| Reflections sync | ✅ For logged-in users |
| LocalStorage fallback | ✅ For guests |

### Auth UI Behavior

**Logged Out:**
- Header shows "Sign In" and "Join Free" buttons
- Reflections save to localStorage only

**Logged In:**
- Header shows user avatar, name, dropdown menu
- Reflections sync to Django API
- Sign Out option available

### API Endpoints

Base URL: `https://[your-pythonanywhere-username].pythonanywhere.com/api/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login/` | POST | User login |
| `/auth/register/` | POST | User registration |
| `/auth/logout/` | POST | User logout |
| `/reflections/` | GET/POST | User reflections |

### Modifying Auth Features

1. Backend changes: Edit Django app on PythonAnywhere
2. Frontend modals: Edit `src/js/auth-modal.js`
3. API calls: Edit `src/js/api.js`
4. Styling: Edit `src/css/auth-modal.css`

---

## 10. Testing Procedures

### Local Development Testing

```bash
# Start dev server
npm run serve

# Opens at http://localhost:8080 (or next available)
```

### Browser Testing Matrix

| Browser | Priority |
|---------|----------|
| Chrome (desktop) | High |
| Safari (desktop) | High |
| Firefox (desktop) | Medium |
| Chrome (mobile) | High |
| Safari (iOS) | High |
| Edge | Medium |

### Responsive Testing

Test at these widths:
- 375px (mobile)
- 768px (tablet)
- 1024px (small desktop)
- 1440px (large desktop)

### Audio Testing Checklist

- [ ] Audio loads without errors
- [ ] Play/pause functions correctly
- [ ] Seek bar allows jumping to any position
- [ ] Speed control changes playback rate
- [ ] Sentence highlighting syncs accurately
- [ ] Click-to-seek works on all sentences
- [ ] Audio continues when scrolling
- [ ] Mobile audio controls work

### Build Verification

```bash
# Run production build
npm run build

# Check for errors in output
# Verify _site/ contains expected files
ls -la _site/
ls -la _site/chapters/
```

---

## 11. Deployment

### Automatic Deployment (Preferred)

Push to `main` branch triggers Vercel auto-deploy:

```bash
git add .
git commit -m "Descriptive commit message"
git push origin main
```

### Manual Deployment (If Needed)

```bash
vercel --prod
```

### Deployment Checklist

- [ ] Local build succeeds (`npm run build`)
- [ ] All tests pass
- [ ] Commit message is descriptive
- [ ] Push to main branch
- [ ] Verify Vercel deployment starts
- [ ] Check production site after deployment

### Rollback Procedure

If deployment causes issues:

1. **Via Vercel Dashboard:**
   - Go to Deployments
   - Find last working deployment
   - Click "..." → "Promote to Production"

2. **Via Git:**
   ```bash
   git revert HEAD
   git push origin main
   ```

---

## 12. Troubleshooting

### Common Issues

#### Build Fails

**Symptom:** `npm run build` shows errors

**Solutions:**
1. Check for syntax errors in Nunjucks templates
2. Verify all referenced files exist
3. Check frontmatter YAML syntax
4. Run `npm install` to ensure dependencies

#### Audio Not Playing

**Symptom:** Audio player shows but doesn't play

**Solutions:**
1. Verify audio file exists in `src/assets/audio/`
2. Check file path in chapter frontmatter
3. Ensure MP3 is properly encoded (use ffmpeg to re-encode)
4. Check browser console for errors

#### Timestamps Not Syncing

**Symptom:** Sentences don't highlight during playback

**Solutions:**
1. Verify timestamp file exists: `src/_data/timestamps/chapter-##-slug.json`
2. Check sentence indices match between content and timestamps
3. Verify timestamp values are in seconds (floats)
4. Clear browser cache and reload

#### Styles Not Applying

**Symptom:** CSS changes don't appear

**Solutions:**
1. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. Check CSS file is linked in layout
3. Verify selector specificity
4. Check for typos in class names

#### Scripture Links Not Working

**Symptom:** Scripture references appear as plain text

**Solutions:**
1. Verify scripture format matches expected patterns
2. Check scripture linking JavaScript is loaded
3. Test with known-good reference format (e.g., "2 Nephi 31:3")

### Debug Mode

Add to browser console for debugging:
```javascript
// Check if audio sync is working
console.log(window.TIMESTAMPS);

// Check chapter data
console.log(document.querySelectorAll('[data-sentence]'));
```

---

## 13. Appendices

### A. ElevenLabs Voice Reference

| Setting | Value |
|---------|-------|
| Voice ID | `As8zJaZyH4MAgaQ93FMc` |
| Model | Eleven Multilingual v2 |
| Stability | 0.5 |
| Similarity Boost | 0.75 |

### B. Scripture URL Patterns

Auto-linking converts references to Church scripture URLs:

| Scripture | URL Pattern |
|-----------|-------------|
| Book of Mormon | `/scriptures/bofm/[book]/[chapter]?id=p[verse]` |
| Doctrine & Covenants | `/scriptures/dc-testament/dc/[section]?id=p[verse]` |
| Old Testament | `/scriptures/ot/[book]/[chapter]?id=p[verse]` |
| New Testament | `/scriptures/nt/[book]/[chapter]?id=p[verse]` |
| Pearl of Great Price | `/scriptures/pgp/[book]/[chapter]?id=p[verse]` |

Base URL: `https://www.churchofjesuschrist.org/study`

### C. Discord Integration

| Resource | Value |
|----------|-------|
| Server Invite | `https://discord.gg/tNwADDjTRV` |
| Ch01 Channel ID | `1463835662238224578` |

### D. Git Commit Message Format

```
[Type]: Brief description

- Detail 1
- Detail 2
- Detail 3
```

**Types:**
- `Add` — New feature or content
- `Fix` — Bug fix
- `Update` — Modification to existing
- `Remove` — Deletion
- `Refactor` — Code restructuring
- `Style` — Formatting, CSS
- `Docs` — Documentation

### E. File Naming Conventions

| Content | Convention |
|---------|------------|
| Chapter content | `##-slug.md` |
| Chapter timestamps | `chapter-##-slug.json` |
| Audio narration | `chapter-##-narration.mp3` |
| Audio overview | `chapter-##-overview.mp3` |
| Musical testimony | `##_#_Title_-_Sacred_Americana_Testimony.mp3` |
| PDF | `WoP_Ch##_Title.pdf` |
| Infographic | `chapter-##-infographic.png` |
| Slides folder | `WoP_Ch##/` |
| Slide images | `slide-##.png` |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 22, 2026 | Original pre-migration workflow |
| 2.0 | Jan 29, 2026 | Complete rewrite for Eleventy architecture |

---

*"For my soul delighteth in plainness; for after this manner doth the Lord God work among the children of men."*  
— 2 Nephi 31:3
