# Words of Plainness — Citation Panel
## Implementation Specification · March 2026

**Status:** Ready for Claude Code  
**Depends on:** R·J·W system (deployed), chapter frontmatter pattern (deployed)  
**Affects:** All chapter pages (Volumes 1 and 2)  
**Repo:** `C:\Users\aaron\Documents\words-of-plainness\`

---

## 1. Overview

The citation panel replaces inline parenthetical scripture citations across all chapter pages. A dagger (†) marker embedded in prose triggers a left-side slide-out panel containing all citations for the chapter, grouped by section heading, with auto-scroll to the triggered citation. The panel header carries a brief authorial explanation of source types, a color-coded source key, and a link to the About/Sources page.

The panel slides in from the **left**. The R·J·W modal slides in from the **right**. The two systems never overlap. If the R·J·W modal is open when a † is clicked, R·J·W closes first, then the citation panel opens.

---

## 2. Design Tokens (no new tokens required)

All citation panel colors draw exclusively from the existing WoP token set. No additions to `:root`.

| Element | Token |
|---|---|
| Panel background | `--deep-brown` |
| Panel header background | `--mid-brown` |
| Panel border | `rgba(196,148,58,0.22)` |
| Dagger color (rest) | `--gold-dim` |
| Dagger color (hover) | `--gold` |
| Citation reference link | `--gold` |
| Citation reference link (hover) | `--gold-pale` |
| Citation body text | `--cream-dim` |
| Section label | `--gold-dim` |
| Highlight pulse background | `rgba(196,148,58,0.13)` |
| Explanation block background | `rgba(196,148,58,0.06)` |
| Explanation block border | `rgba(196,148,58,0.15)` |

---

## 3. New CSS Custom Properties

Add to the existing `:root` block in the site's global stylesheet (or chapter base layout):

```css
:root {
  --cite-panel-w: 360px;
  --cite-highlight-duration: 1800ms;
}

@media (max-width: 600px) {
  :root {
    --cite-panel-w: 100vw;
    --cite-highlight-duration: 2400ms;
  }
}
```

`--cite-panel-w` is `360px` on desktop. On mobile it expands to full viewport width so the panel is readable without zooming. `--cite-highlight-duration` is longer on mobile to compensate for slower scroll animation settling time.

---

## 4. Dagger Marker — The `{% cite %}` Shortcode

### 4a. Shortcode definition

Add to `.eleventy.js`:

```js
eleventyConfig.addShortcode("cite", function(entryId, tip) {
  const tooltip = tip || "Open citations panel.";
  return `<span class="cite-mark" data-tip="${tooltip}" data-entry="${entryId}" tabindex="0" role="button" aria-label="Open citations panel"></span>`;
});
```

### 4b. Usage in chapter markdown

```markdown
He was moved with compassion for the leper who knelt before him {% cite "ce-matt82" %}.
For the widow of Nain {% cite "ce-luke713" %}.
```

The shortcode always emits the same tooltip text ("Open citations panel.") unless overridden by a second argument. Override is available but not expected to be needed in practice.

### 4c. CSS for the dagger mark

```css
.cite-mark {
  display: inline-block;
  font-size: 0.78em;
  vertical-align: super;
  line-height: 1;
  color: var(--gold-dim);
  cursor: pointer;
  margin-left: 2px;
  font-family: 'Cinzel', serif;
  font-weight: 400;
  border-bottom: 1px solid transparent;
  transition: color 0.18s, border-color 0.18s;
  user-select: none;
  position: relative;
}

.cite-mark::after {
  content: '†';
}

.cite-mark:hover {
  color: var(--gold);
  border-bottom-color: rgba(196,148,58,0.5);
}

/* Tooltip — desktop hover only */
.cite-mark[data-tip]:hover::before {
  content: attr(data-tip);
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  background: var(--mid-brown);
  border: 1px solid rgba(196,148,58,0.3);
  color: var(--gold-pale);
  padding: 4px 10px;
  border-radius: 2px;
  pointer-events: none;
  z-index: 10;
}
```

### 4d. Silent zone constraint (inherited from R·J·W spec)

`{% cite %}` shortcodes must **never** be placed inside pause-point elements or the `.tab-cluster`. Pause-points are a silent zone — no shortcodes of any kind fire inside them.

---

## 5. YAML Frontmatter — Citation Data Structure

Each chapter's frontmatter carries a `citations` array. Each item in the array belongs to a named section group. Citation entries that appear in more than one prose location (e.g., Alma 7:11–12 cited twice in Ch. 9) receive distinct `id` values with a suffix (`-a`, `-b`) so each † in the prose can scroll to a distinct panel entry.

```yaml
---
citations:
  - section: "Invocation"
    entries:
      - id: "ce-matt1129"
        ref: "Matthew 11:29"
        type: "nt"
        note: "\"Take my yoke upon you, and learn of me; for I am meek and lowly in heart.\""

  - section: "Master of Compassion"
    entries:
      - id: "ce-matt82"
        ref: "Matthew 8:2–3"
        type: "nt"
        note: "Healing of the leper — moved with compassion."
      - id: "ce-luke713"
        ref: "Luke 7:13"
        type: "nt"
        note: "The widow of Nain — her only son being carried out for burial."
      - id: "ce-matt936"
        ref: "Matthew 9:36"
        type: "nt"
        note: "Crowds \"scattered abroad, as sheep having no shepherd.\""
      - id: "ce-alma711-a"
        ref: "Alma 7:11–12"
        type: "bom"
        note: "He takes upon him the pains and sicknesses of his people — that his bowels may be filled with mercy according to the flesh."

  - section: "Master of Meekness and Courage"
    entries:
      - id: "ce-matt2333"
        ref: "Matthew 23:33"
        type: "nt"
        note: "\"Ye serpents, ye generation of vipers.\""
      - id: "ce-john530"
        ref: "John 5:30"
        type: "nt"
        note: "\"I can of mine own self do nothing… I seek not mine own will, but the will of the Father.\""
      - id: "ce-matt2713"
        ref: "Matthew 27:13–14"
        type: "nt"
        note: "Before Pilate — he held his peace."
      - id: "ce-john660"
        ref: "John 6:60–68"
        type: "nt"
        note: "\"This is an hard saying; who can hear it?\" — \"Will ye also go away?\""
      - id: "ce-matt55"
        ref: "Matthew 5:5"
        type: "nt"
        note: "\"Blessed are the meek, for they shall inherit the earth.\""

  - section: "No Stranger to Your Sorrows"
    entries:
      - id: "ce-isa533"
        ref: "Isaiah 53:3"
        type: "ot"
        note: "\"A man of sorrows, and acquainted with grief\" — yada, to know by experience from the inside."
      - id: "ce-john1135"
        ref: "John 11:35"
        type: "nt"
        note: "\"Jesus wept.\" — standing in the grief of people he loved."
      - id: "ce-alma711-b"
        ref: "Alma 7:11–12"
        type: "bom"
        note: "He gets beneath the weight — succurrere, to run beneath and support from below."
---
```

### Type values and their panel badge labels

| `type` value | Badge label | Badge class |
|---|---|---|
| `ot` | Old Testament | `.source-badge.ot` |
| `nt` | New Testament | `.source-badge.nt` |
| `bom` | Book of Mormon | `.source-badge.bom` |
| `dc` | D&C / Pearl | `.source-badge.dc` |

---

## 6. Scripture URL Construction

The existing inline scripture link pattern builds Church of Jesus Christ URLs. That same logic must apply to citation reference links in the panel. Since panel content is rendered at build time from the Nunjucks template (not via API), the URL constructor runs as a Nunjucks filter or macro at build time.

If the existing scripture URL logic is a JavaScript filter registered in `.eleventy.js`:

```js
eleventyConfig.addFilter("scriptureUrl", function(ref) {
  // existing URL construction logic
  // returns: "https://www.churchofjesuschrist.org/study/scriptures/..."
});
```

Apply it in the citation panel template:

```nunjucks
<a class="cite-ref-link"
   href="{{ entry.ref | scriptureUrl }}"
   target="_blank"
   rel="noopener noreferrer">
  {{ entry.ref }}
</a>
```

If the existing implementation uses a different mechanism (e.g., a shortcode that fires inline), that mechanism will **not** fire inside Nunjucks-rendered panel HTML. In that case, replicate the URL construction as a dedicated `scriptureUrl` filter rather than trying to invoke the shortcode inside a loop. This is the recommended path regardless — filters compose cleanly with Nunjucks `for` loops; shortcodes do not.

All citation links open in a new tab (`target="_blank"`, `rel="noopener noreferrer"`). This matches the existing inline behavior.

---

## 7. Panel HTML Template

Add to the chapter base layout (`_includes/layouts/chapter.njk` or equivalent), **before** the closing `</body>` tag, **after** the R·J·W modal panel markup:

```nunjucks
{% if citations %}
<div class="cite-overlay" id="citePanel" aria-label="Citations panel" role="complementary">
  <div class="cite-header">
    <div class="cite-header-top">
      <div>
        <div class="cite-eyebrow">Sources &amp; Citations</div>
        <div class="cite-chapter-name">{{ title }}</div>
      </div>
      <button class="cite-close" onclick="citePanelClose()" aria-label="Close citations panel">✕</button>
    </div>
    <div class="cite-explanation">
      <p>This chapter draws on the Old and New Testaments as its primary witnesses,
         with Restoration scriptures cited where they offer the clearest amplification
         of a biblical truth. All citations open in the Church of Jesus Christ
         scripture tool for reading and study.</p>
      <div class="source-key">
        <span class="source-badge ot">Old Testament</span>
        <span class="source-badge nt">New Testament</span>
        <span class="source-badge bom">Book of Mormon</span>
        <span class="source-badge dc">D&amp;C / Pearl</span>
      </div>
      <a class="cite-learn-link" href="/about/sources/">About our sources →</a>
    </div>
  </div>

  <div class="cite-body" id="citeBody">
    {% for group in citations %}
    <div class="cite-section-group">
      <div class="cite-section-label">{{ group.section }}</div>
      {% for entry in group.entries %}
      <div class="cite-entry" id="{{ entry.id }}">
        <span class="cite-entry-badge">
          <span class="source-badge {{ entry.type }}">
            {% if entry.type == "ot" %}OT
            {% elif entry.type == "nt" %}NT
            {% elif entry.type == "bom" %}BoM
            {% elif entry.type == "dc" %}D&amp;C
            {% endif %}
          </span>
        </span>
        <div>
          <a class="cite-ref-link"
             href="{{ entry.ref | scriptureUrl }}"
             target="_blank"
             rel="noopener noreferrer">{{ entry.ref }}</a>
          <div class="cite-ref-text">{{ entry.note }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% endfor %}
  </div>
</div>
{% endif %}
```

The `{% if citations %}` guard means the panel is emitted only for chapters that have a `citations` array in frontmatter. Pages without citations (landing pages, safety page, Connect page, etc.) receive no panel markup and no panel JS.

---

## 8. Panel CSS

Add to the chapter stylesheet (or global stylesheet if chapter styles are global):

```css
/* ── CITATION PANEL — LEFT SLIDE-OUT ──────────────── */

.cite-overlay {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  width: var(--cite-panel-w);
  background: var(--deep-brown);
  border-right: 1px solid rgba(196,148,58,0.22);
  box-shadow: 6px 0 40px rgba(0,0,0,0.65);
  transform: translateX(-100%);
  transition: transform 0.38s cubic-bezier(0.4,0,0.2,1);
  display: flex;
  flex-direction: column;
  z-index: 300;
  /* Above page content; below R·J·W overlay (z-index: 400) */
}

.cite-overlay.open {
  transform: translateX(0);
}

/* HEADER */
.cite-header {
  padding: 22px 20px 14px;
  background: var(--mid-brown);
  border-bottom: 1px solid rgba(196,148,58,0.15);
  flex-shrink: 0;
}

.cite-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.cite-eyebrow {
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.32em;
  color: var(--gold-dim);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.cite-chapter-name {
  font-family: 'Crimson Pro', serif;
  font-size: 15px;
  font-weight: 600;
  color: var(--cream-dim);
  line-height: 1.3;
}

.cite-close {
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid rgba(196,148,58,0.2);
  border-radius: 50%;
  color: var(--cream-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 2px;
  transition: background 0.2s, border-color 0.2s, color 0.2s;
}

.cite-close:hover {
  background: var(--cream-faint);
  border-color: var(--gold-dim);
  color: var(--cream);
}

/* EXPLANATION BLOCK */
.cite-explanation {
  padding: 11px 14px;
  background: rgba(196,148,58,0.06);
  border: 1px solid rgba(196,148,58,0.15);
  border-radius: 3px;
  margin-bottom: 0;
}

.cite-explanation p {
  font-size: 13px;
  color: var(--cream-dim);
  line-height: 1.6;
  margin-bottom: 8px;
  font-style: italic;
}

/* SOURCE KEY */
.source-key {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.source-badge {
  font-family: 'Cinzel', serif;
  font-size: 8px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  padding: 3px 9px;
  border-radius: 2px;
  border: 1px solid;
  white-space: nowrap;
}

.source-badge.ot {
  background: rgba(196,148,58,0.12);
  border-color: rgba(196,148,58,0.35);
  color: var(--gold-pale);
}

.source-badge.nt {
  background: rgba(196,148,58,0.18);
  border-color: var(--gold-dim);
  color: var(--gold);
}

.source-badge.bom {
  background: rgba(58,99,99,0.18);
  border-color: rgba(58,99,99,0.5);
  color: #7BB8B8;
}

.source-badge.dc {
  background: rgba(107,61,61,0.18);
  border-color: rgba(107,61,61,0.5);
  color: #C47A7A;
}

.cite-learn-link {
  display: inline-block;
  margin-top: 10px;
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold-dim);
  text-decoration: none;
  border-bottom: 1px solid rgba(196,148,58,0.3);
  transition: color 0.2s, border-color 0.2s;
}

.cite-learn-link:hover {
  color: var(--gold);
  border-bottom-color: var(--gold);
}

/* PANEL BODY */
.cite-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0 32px;
  scrollbar-width: thin;
  scrollbar-color: var(--warm-brown) transparent;
}

/* SECTION GROUPS */
.cite-section-group {
  padding: 16px 20px 0;
}

.cite-section-group + .cite-section-group {
  margin-top: 6px;
}

.cite-section-label {
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--gold-dim);
  padding-bottom: 8px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(196,148,58,0.15);
}

/* INDIVIDUAL CITATION ENTRIES */
.cite-entry {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 9px 10px;
  margin-bottom: 4px;
  border-radius: 3px;
  transition: background 0.38s cubic-bezier(0.4,0,0.2,1);
}

.cite-entry.highlight {
  background: rgba(196,148,58,0.13);
}

.cite-entry:hover {
  background: var(--cream-glass);
}

.cite-entry-badge {
  flex-shrink: 0;
  margin-top: 3px;
}

.cite-ref-link {
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--gold);
  text-decoration: none;
  border-bottom: 1px solid rgba(196,148,58,0.3);
  transition: color 0.2s, border-color 0.2s;
  display: block;
  margin-bottom: 3px;
  line-height: 1.4;
}

.cite-ref-link:hover {
  color: var(--gold-pale);
  border-bottom-color: var(--gold-pale);
}

.cite-ref-text {
  font-size: 13.5px;
  color: var(--cream-dim);
  line-height: 1.55;
  font-style: italic;
}
```

---

## 9. Z-Index Layer Map (full system)

The citation panel must sit in the correct layer relative to the R·J·W system. The R·J·W overlay and modal must always render above the citation panel when both are technically present in the DOM simultaneously during the close-first transition.

| Element | z-index |
|---|---|
| Page content | 0 (normal flow) |
| Bottom toolbar (bookmark / complete) | 50 |
| Citation panel `.cite-overlay` | 300 |
| R·J·W overlay backdrop | 400 |
| R·J·W modal panel | 401 |
| Demo badge (mockup only, remove in production) | 500 |

---

## 10. JavaScript

Add to the chapter base layout, inside a `<script>` block **after** all panel HTML, **after** the existing R·J·W script block. The citation panel JS must never be inlined in the Nunjucks template loop — one script block, loaded once.

```js
/* ── CITATION PANEL ──────────────────────────────────
   Coexists with R·J·W system. Left-side panel only.
   R·J·W modal (right side) closes before this opens.
   ─────────────────────────────────────────────────── */

(function () {
  'use strict';

  let citePanelOpen = false;
  let citeActiveEntry = null;
  let citeHighlightTimer = null;

  /* ── OPEN ─────────────────────────────────────── */
  function citePanelOpen_() {
    document.getElementById('citePanel').classList.add('open');
    citePanelOpen = true;
  }

  /* ── CLOSE ────────────────────────────────────── */
  window.citePanelClose = function () {
    document.getElementById('citePanel').classList.remove('open');
    citePanelOpen = false;
    clearCiteHighlight();
  };

  /* ── CLEAR HIGHLIGHT ──────────────────────────── */
  function clearCiteHighlight() {
    if (citeHighlightTimer) {
      clearTimeout(citeHighlightTimer);
      citeHighlightTimer = null;
    }
    if (citeActiveEntry) {
      const el = document.getElementById(citeActiveEntry);
      if (el) el.classList.remove('highlight');
      citeActiveEntry = null;
    }
  }

  /* ── OPEN AT ENTRY ────────────────────────────── */
  /*
    Called by each .cite-mark element via data-entry attribute.
    If R·J·W modal is open, close it first, then open citation
    panel after the R·J·W close animation completes (390ms ≈
    --ease duration + margin).

    If citation panel is already open, scroll to new entry
    without closing and reopening.
  */
  window.citeOpenAt = function (entryId) {
    const rjwPanel = document.getElementById('modalPanel');
    const rjwIsOpen = rjwPanel && rjwPanel.classList.contains('open');

    function doOpen() {
      const wasOpen = citePanelOpen;
      if (!citePanelOpen) citePanelOpen_();
      clearCiteHighlight();
      citeActiveEntry = entryId;

      const delay = wasOpen ? 0 : 420;
      setTimeout(function () {
        const el = document.getElementById(entryId);
        if (!el) return;
        el.classList.add('highlight');
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        const dur = parseInt(
          getComputedStyle(document.documentElement)
            .getPropertyValue('--cite-highlight-duration')
        ) || 1800;

        citeHighlightTimer = setTimeout(function () {
          el.classList.remove('highlight');
          citeHighlightTimer = null;
        }, dur);
      }, delay);
    }

    if (rjwIsOpen) {
      /* Close R·J·W first. closeModal() is the existing R·J·W
         close function defined in the R·J·W script block. */
      closeModal();
      setTimeout(doOpen, 400);
    } else {
      doOpen();
    }
  };

  /* ── WIRE UP DAGGER MARKS ─────────────────────── */
  /*
    Attach click and keyboard handlers to all .cite-mark elements.
    Runs on DOMContentLoaded — shortcode renders entryId into
    data-entry attribute at build time.
  */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.cite-mark').forEach(function (mark) {
      const entryId = mark.getAttribute('data-entry');
      if (!entryId) return;

      mark.addEventListener('click', function () {
        citeOpenAt(entryId);
      });

      mark.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          citeOpenAt(entryId);
        }
      });
    });
  });

  /* ── KEYBOARD CLOSE ───────────────────────────── */
  /*
    Escape closes citation panel. R·J·W already listens for
    Escape to close its own modal. If both were somehow open
    (impossible by design but defensive), R·J·W takes priority
    because its z-index is higher and its Escape listener fires
    first in document order.
  */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && citePanelOpen) {
      window.citePanelClose();
    }
  });

})();
```

### Dependency note

`citeOpenAt` calls `closeModal()` when R·J·W is open. `closeModal()` is the existing R·J·W close function. The citation panel script block must appear **after** the R·J·W script block in the DOM so `closeModal` is defined before `citeOpenAt` can reference it. This is already satisfied if both script blocks are in the chapter base layout footer.

---

## 11. Coexistence Rules Summary

| Scenario | Behavior |
|---|---|
| Citation panel closed, R·J·W closed → † clicked | Citation panel opens, scrolls to entry |
| Citation panel open → different † clicked | Panel stays open, scrolls to new entry, old highlight clears |
| Citation panel open → R·J·W pill clicked | Citation panel stays open; R·J·W opens on the right; both visible simultaneously |
| R·J·W open → † clicked | R·J·W closes (400ms), then citation panel opens and scrolls |
| Either panel open → Escape pressed | That panel closes; other panel unaffected |
| Citation panel open → overlay area clicked | No overlay for citation panel — only the ✕ button and Escape close it |

Note on row 3: the citation panel and R·J·W panel **can** be open simultaneously, since they occupy opposite sides of the viewport. The only enforced close-first is R·J·W → citation panel, because the R·J·W modal is wider (480px right) and a reader is unlikely to be using both systems at the same moment. The reverse (citation panel open → R·J·W pill clicked) requires no special handling — R·J·W opens normally on the right.

---

## 12. Accessibility

- `.cite-mark` receives `role="button"` and `tabindex="0"` from the shortcode. Keyboard activation via `Enter` or `Space` is wired in the JS handler.
- `.cite-overlay` receives `aria-label="Citations panel"` and `role="complementary"`.
- `.cite-close` receives `aria-label="Close citations panel"`.
- Citation reference links open in a new tab and carry `rel="noopener noreferrer"`. No `aria-label` is needed — the visible text (`Matthew 11:29`, etc.) is the label.
- The panel is not a modal in the ARIA sense (it does not trap focus). It is a complementary landmark that the reader can ignore or engage freely. This matches the R·J·W panel's accessibility model.

---

## 13. Mobile Considerations

- Panel width expands to `100vw` on screens ≤600px.
- Highlight duration extends to `2400ms` on screens ≤600px.
- The tooltip (CSS `::before` pseudo-element) does not fire on touch — this is expected and acceptable. The † glyph in `--gold-dim` at superscript scale carries sufficient affordance without the tooltip on mobile.
- On very narrow screens where prose is a single column, the prose does **not** shift when the panel opens (unlike the desktop behavior where content shifts rightward when the R·J·W panel opens). The citation panel overlays the prose on mobile. This is standard behavior for full-width mobile panels and requires no special CSS — `margin-left` shift is only appropriate when the panel does not consume the full viewport width.

---

## 14. Pages Where Citations Panel Is Active

The `{% if citations %}` guard in the chapter template means the panel only activates on pages with a `citations` frontmatter array. Apply `citations` frontmatter to:

- All Movement 1 chapters (Ch. 1–6) — retrofit existing inline citations
- All Movement 2 chapters (Ch. 7–11) — new chapters receive citations in frontmatter from authoring
- All Movement 3 card-chapters — scripture citations within card content
- All Movement 4 chapters and Volume 2 chapters

Do **not** add `citations` to: landing pages, the Safety page, the Connect page, the About pages, or any non-chapter page.

---

## 15. Retrofit Plan for Existing Deployed Chapters (Ch. 1–6)

Chapters 1–6 currently use inline parenthetical citations. The retrofit sequence for each chapter:

1. Audit the chapter markdown for all inline scripture references.
2. Build the `citations` YAML frontmatter array (section groups, entry IDs, type, note).
3. Replace each inline parenthetical `(Matthew 11:29)` or `<a class="scripture">Matthew 11:29</a>` with `{% cite "ce-[id]" %}`.
4. Verify build output: panel renders, all † markers scroll to correct entries, scripture links resolve.
5. Commit as a single clean commit per chapter.

Do not batch all six chapters into one commit — individual chapter commits make rollback surgical if a citation ID conflict arises.

---

## 16. Claude Code Prompt Template

Use this prompt to initiate each chapter's citation panel deployment. Paste into Claude Code, filling in the chapter number and slug.

```
Implement the citation panel for Chapter [N] ([Title]) of the Words of Plainness
site per WoP_CitationPanel_Spec_Mar2026.md.

Tasks:
1. Add `citations` frontmatter array to `src/chapters/ch[N]-[slug].md` using the
   entry IDs and data provided below.
2. Replace all inline scripture citations in the chapter markdown with
   `{% cite "ce-[id]" %}` shortcodes.
3. Confirm the `{% cite %}` shortcode is registered in `.eleventy.js`. If not,
   add it per Section 4a of the spec.
4. Confirm `.cite-mark` CSS is present in the chapter stylesheet. If not, add
   per Section 4d of the spec.
5. Confirm citation panel HTML template is present in the chapter base layout.
   If not, add per Section 7 of the spec.
6. Confirm citation panel JS is present after the R·J·W script block in the
   chapter base layout. If not, add per Section 10 of the spec.
7. Verify the `scriptureUrl` filter exists in `.eleventy.js`. If not, implement
   it to replicate the existing inline scripture link URL construction.

Citation data:
[PASTE YAML FRONTMATTER BLOCK HERE]

Push this commit directly to main. Do not create a PR.
```

---

*Words of Plainness · Aaron Powner Publishing · March 2026*  
*Spec version 1.0 — treat all decisions herein as constraints unless Aaron authorizes revision.*
