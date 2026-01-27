# Words of Plainness — Chapter Template Rollback Guide

## Version Information

| Version | Date | Description |
|---------|------|-------------|
| v2.0 | January 25, 2026 | Original template with quick-nav bar |
| v3.0 | January 27, 2026 | Redesigned with floating action bar, dropdown menu, mobile FAB |

---

## Backup Location

**Original template preserved at:**
```
rollback-originals/CHAPTER-TEMPLATE-ORIGINAL.html
```

---

## How to Rollback

### Option 1: Full Rollback (Revert to v2.0)

Replace the new template with the original:

```bash
# In your words-of-plainness repository
cp rollback-originals/CHAPTER-TEMPLATE-ORIGINAL.html pages/chapters/CHAPTER-TEMPLATE.html

# For any chapter already using v3.0, replace with the original
# (You may need to re-apply chapter-specific content)
```

### Option 2: Per-Chapter Rollback

If you've already published chapters with v3.0 and want to revert specific ones:

1. Copy content sections from the v3.0 chapter
2. Open the v2.0 template
3. Paste content into the appropriate sections
4. Re-apply timestamps and asset paths

---

## What Changed (v2.0 → v3.0)

### Removed Elements
- ❌ Quick navigation bar with Read Aloud, A-, A+, Bookmark, Share buttons
- ❌ Static "Jump to" section links
- ❌ Persistent "You left off at" banner

### Added Elements
- ✅ Floating action bar (appears on scroll)
  - "Listen to Chapter" pill button
  - "Other Features" dropdown menu
- ✅ Auto-dismissing resume prompt (8 seconds)
- ✅ Mobile FAB (lantern icon) with expandable menu
- ✅ Mobile slide-out Table of Contents panel
- ✅ Bottom toolbar for font/bookmark/share (appears on scroll)

### Relocated Elements
- Font controls → Bottom toolbar
- Bookmark → Bottom toolbar
- Share → Bottom toolbar
- Contents access → Dropdown menu + Mobile FAB

---

## Testing Checklist After Rollback

If you rollback, verify these features work:

- [ ] Quick nav bar displays correctly
- [ ] Read Aloud button activates audio player
- [ ] Font size buttons work
- [ ] Bookmark saves position
- [ ] Share functionality works
- [ ] TOC sidebar displays on desktop
- [ ] Mobile layout functions properly

---

## Files in This Package

```
/outputs/
├── CHAPTER-TEMPLATE.html              ← NEW v3.0 template
├── WoP-Chapter-Layout-Wireframe.html  ← Interactive preview
├── WoP-Chapter-Page-Redesign-Spec.md  ← Design specification
└── rollback-originals/
    └── CHAPTER-TEMPLATE-ORIGINAL.html ← BACKUP v2.0 template
```

---

## Deployment Instructions

### To Use v3.0 (New Design)

1. Copy `CHAPTER-TEMPLATE.html` to your repository:
   ```bash
   cp CHAPTER-TEMPLATE.html /path/to/words-of-plainness/pages/chapters/
   ```

2. For new chapters, use the v3.0 template

3. For existing chapters (like Chapter 1), you'll need to:
   - Extract the chapter content from the existing file
   - Apply it to the new template structure
   - Update timestamps and asset paths

### Repository Update Workflow

```bash
cd words-of-plainness
git checkout -b feature/chapter-redesign-v3

# Copy new template
cp /path/to/CHAPTER-TEMPLATE.html pages/chapters/

# Commit changes
git add .
git commit -m "Update chapter template to v3.0 with floating action bar and mobile FAB"

# Test locally, then merge when satisfied
git checkout main
git merge feature/chapter-redesign-v3
git push origin main

# Deploy
vercel --prod
```

---

## Contact

If issues arise, the original template is always available in `rollback-originals/`.

*"For my soul delighteth in plainness..."* — 2 Nephi 31:3
