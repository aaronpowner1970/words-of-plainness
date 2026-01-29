# Words of Plainness - Eleventy Migration (Phase 1)

## 📋 Overview

This package contains the complete **Phase 1: Setup & Infrastructure** files for migrating the Words of Plainness website from standalone HTML files to an Eleventy-based static site generator architecture.

**Current state:** 3,000+ line HTML files for each chapter  
**Target state:** Single template + Markdown content files

## 🚀 Quick Start (Claude Code)

Run these commands in Claude Code to apply the migration to your repository:

```bash
# 1. Create feature branch
cd ~/words-of-plainness
git checkout -b feature/eleventy-migration

# 2. Backup existing files
mkdir -p rollback-originals
cp -r pages rollback-originals/
cp -r styles.css rollback-originals/
cp -r scripts.js rollback-originals/

# 3. Copy the Phase 1 files from this package
# (Claude Code will handle the file copying)

# 4. Install dependencies
npm install

# 5. Test the build
npm run build

# 6. Start development server
npm start
# Site will be available at http://localhost:8080
```

## 📁 Directory Structure

```
words-of-plainness/
├── .eleventy.js              # Eleventy configuration
├── .gitignore                # Build output & dependencies
├── package.json              # Dependencies & scripts
├── vercel.json               # Deployment configuration
│
├── src/                      # Source files
│   ├── _data/                # Global data
│   │   ├── site.json         # Site metadata
│   │   ├── navigation.json   # Nav menu items
│   │   └── timestamps/       # Audio sync data
│   │       └── chapter-01.json
│   │
│   ├── _includes/            # Templates & components
│   │   ├── layouts/
│   │   │   ├── base.njk      # HTML skeleton
│   │   │   ├── page.njk      # Standard pages
│   │   │   └── chapter.njk   # Chapter pages
│   │   │
│   │   ├── partials/
│   │   │   ├── header.njk
│   │   │   ├── footer.njk
│   │   │   └── mobile-menu.njk
│   │   │
│   │   └── components/       # Chapter UI components
│   │       ├── floating-action-bar.njk
│   │       ├── audio-player.njk
│   │       ├── toc-sidebar.njk
│   │       ├── toc-mobile.njk
│   │       ├── study-resources.njk
│   │       ├── reflection-section.njk
│   │       ├── discord-section.njk
│   │       ├── chapter-nav.njk
│   │       ├── bottom-toolbar.njk
│   │       ├── back-to-top.njk
│   │       ├── fab-lantern.njk
│   │       ├── resume-prompt.njk
│   │       └── modals.njk
│   │
│   ├── chapters/             # Chapter content (Markdown)
│   │   ├── chapters.json     # Directory data
│   │   └── _template.md      # Template for new chapters
│   │
│   ├── pages/                # Static pages (to be added)
│   │
│   ├── css/
│   │   ├── chapter.css       # Chapter-specific styles
│   │   └── auth-modal.css    # Authentication modal
│   │
│   ├── js/
│   │   ├── main.js           # Global scripts
│   │   ├── chapter.js        # Chapter functionality
│   │   ├── audio-sync.js     # Sentence highlighting
│   │   ├── api.js            # Django API client
│   │   ├── auth-modal.js     # Auth UI
│   │   └── reflections.js    # Reflection saving
│   │
│   └── assets/               # Static assets (copied from existing)
│       ├── images/
│       ├── audio/
│       ├── pdf/
│       ├── slides/
│       └── favicons/
│
├── _site/                    # Build output (gitignored)
│
└── rollback-originals/       # Pre-migration backup
```

## 📝 NPM Scripts

```bash
npm start     # Start dev server with hot reload
npm run build # Build site to _site/
npm run debug # Build with verbose logging
npm run clean # Delete _site/
```

## ✅ Phase 1 Checklist

- [x] Initialize Eleventy configuration
- [x] Create package.json with dependencies
- [x] Configure Vercel deployment
- [x] Create base folder structure
- [x] Create base layout template (base.njk)
- [x] Create chapter layout template (chapter.njk)
- [x] Create page layout template (page.njk)
- [x] Create all component stubs
- [x] Create JavaScript modules
- [x] Create placeholder CSS files
- [x] Create .gitignore
- [x] Create site.json data file
- [x] Create navigation.json data file
- [x] Create chapters directory data

## 📋 Next Steps: Phase 2

After applying Phase 1 files:

1. **Copy existing styles.css** to `src/css/styles.css`
2. **Copy existing assets** (images, audio, pdf, slides, favicons)
3. **Extract Chapter 1 embedded CSS** into `src/css/chapter.css`
4. **Extract Chapter 1 JavaScript** into modular JS files
5. **Test the build** with `npm run build`
6. **Start dev server** with `npm start`

## 🔧 Configuration Files

### .eleventy.js

- Passthrough copy for assets, CSS, JS
- Chapters collection sorted by number
- `sentence` shortcode for audio sync markup
- `scripture` shortcode for build-time linking
- Comprehensive scripture URL mappings

### vercel.json

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "_site",
  "framework": null,
  "installCommand": "npm install"
}
```

### site.json

Contains:
- Site name and tagline
- Author information
- Discord server link
- API base URL
- Brand colors

## 🎨 Brand Colors

| Color | Hex |
|-------|-----|
| Gold Primary | #C4943A |
| Cream | #E8DCC4 |
| Deep Brown | #3D2B1F |
| Rich Brown | #2A1D14 |
| Burgundy | #6B3D3D |
| Teal Muted | #4A6B6B |

## 📖 Creating New Chapters

After migration is complete, new chapters are simple:

```bash
# 1. Copy template
cp src/chapters/_template.md src/chapters/02-the-plan.md

# 2. Edit frontmatter and content
# 3. Add timestamps to src/_data/timestamps/chapter-02.json
# 4. Build and test: npm start
# 5. Commit and push - Vercel auto-deploys
```

## 🔗 Resources

- **Eleventy Docs:** https://www.11ty.dev/docs/
- **Nunjucks Templating:** https://mozilla.github.io/nunjucks/
- **Production Site:** https://words-of-plainness.vercel.app
- **GitHub Repository:** github.com/aaronpowner1970/words-of-plainness

---

*"For my soul delighteth in plainness; for after this manner doth the Lord God work among the children of men."*  
— 2 Nephi 31:3
