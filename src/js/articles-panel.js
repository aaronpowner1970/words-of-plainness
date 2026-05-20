/**
 * articles-panel.js
 * ─────────────────────────────────────────────────────────────────────────
 * Annotation panel for the Articles of Interfaith Discipleship page.
 *
 * INTERACTION MODEL
 *   Desktop (≥1200px, hover device):
 *     - Hover over [data-span]  → open panel after 120ms delay
 *     - Mouse enters panel      → panel stays open
 *     - Mouse leaves both span and panel → close after 280ms
 *     - Click outside panel     → close
 *
 *   Mobile / tablet (<1200px, or touch device):
 *     - Tap [data-span]         → open panel
 *     - Tap backdrop            → close
 *     - Tap × button            → close
 *     - Escape key              → close
 *
 * DATA SOURCE
 *   <script type="application/json" id="apparatusData">…</script>
 *   Structure: apparatus[articleId][spanId] = { text, type, named_concept,
 *     definition, panel_comment, biblical[], restoration[], crossref[] }
 *
 * SPAN MARKUP
 *   <span data-span="s1" data-article="A01" data-type="concept" data-named="true">text</span>
 * ─────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Static article title map ──────────────────────────────────
    var ARTICLE_TITLES = {
        A01: 'Of Plainness',
        A02: 'Of God',
        A03: 'Of Creation and Life',
        A04: 'Of God\'s Word',
        A05: 'Of Jesus Christ',
        A06: 'Of Salvation',
        A07: 'Of the Kingdom at Hand',
        A08: 'Of Fellow Believers',
        A09: 'Of Finding Our Way',
        A10: 'Of Living by Grace',
        A11: 'Of Covenants and Commitments',
        A12: 'Of Immortality and Eternal Life',
        A13: 'Of Our Confidence',
    };

    // ── Element references ────────────────────────────────────────
    var panel    = document.getElementById('apPanel');
    var backdrop = document.getElementById('apBackdrop');
    var closeBtn = document.getElementById('apClose');
    var panelBody = document.getElementById('apBody');

    // Header
    var elTypeBadge    = document.getElementById('apTypeBadge');
    var elArticleLabel = document.getElementById('apArticleLabel');

    // Body — span text + definition + commentary
    var elSpanText        = document.getElementById('apSpanText');
    var elDefinitionBlock = document.getElementById('apDefinitionBlock');
    var elDefinition      = document.getElementById('apDefinition');
    var elCommentBlock    = document.getElementById('apCommentBlock');
    var elComment         = document.getElementById('apComment');

    // Anchor tabs
    var elAnchorTabsBlock  = document.getElementById('apAnchorTabsBlock');
    var elTabBiblical      = document.getElementById('apTabBiblical');
    var elTabRestoration   = document.getElementById('apTabRestoration');
    var elBiblicalPane     = document.getElementById('apBiblicalPane');
    var elRestorationPane  = document.getElementById('apRestorationPane');
    var elBiblicalList     = document.getElementById('apBiblicalList');
    var elRestorationList  = document.getElementById('apRestorationList');
    var elBiblicalEmpty    = document.getElementById('apBiblicalEmpty');
    var elRestorationEmpty = document.getElementById('apRestorationEmpty');

    // Crossrefs
    var elCrossrefBlock = document.getElementById('apCrossrefBlock');
    var elCrossrefList  = document.getElementById('apCrossrefList');

    if (!panel) { return; }

    // ── Load apparatus data ───────────────────────────────────────
    var apparatus = {};
    try {
        var dataScript = document.getElementById('apparatusData');
        if (dataScript && dataScript.textContent.trim()) {
            apparatus = JSON.parse(dataScript.textContent) || {};
        }
    } catch (e) {
        console.warn('[articles-panel] Could not parse apparatus JSON:', e);
    }

    // ── State ─────────────────────────────────────────────────────
    var activeSpanEl = null;
    var isOpen       = false;
    var hoverTimer   = null;
    var leaveTimer   = null;

    // ── Helpers ───────────────────────────────────────────────────

    function isDesktopHover() {
        return window.matchMedia('(min-width: 1200px) and (hover: hover)').matches;
    }

    function toggleBlock(el, show) {
        el.classList.toggle('ap-hidden', !show);
    }

    // ── Tab switching ─────────────────────────────────────────────

    function switchTab(tabBtn) {
        var tabs  = [elTabBiblical, elTabRestoration];
        var panes = [elBiblicalPane, elRestorationPane];

        tabs.forEach(function (t, i) {
            var isActive = (t === tabBtn);
            t.classList.toggle('ap-anchor-tab--active', isActive);
            t.setAttribute('aria-selected', isActive ? 'true' : 'false');
            toggleBlock(panes[i], isActive);
        });
    }

    // Tab click listeners
    elTabBiblical.addEventListener('click', function () { switchTab(elTabBiblical); });
    elTabRestoration.addEventListener('click', function () { switchTab(elTabRestoration); });

    // ── Panel open / close ────────────────────────────────────────

    function openPanel() {
        if (isOpen) { return; }
        isOpen = true;
        panel.classList.add('ap-open');
        panel.setAttribute('aria-hidden', 'false');
        if (!isDesktopHover()) { backdrop.classList.add('ap-open'); }
    }

    function closePanel() {
        if (!isOpen) { return; }
        isOpen = false;
        panel.classList.remove('ap-open');
        panel.setAttribute('aria-hidden', 'true');
        backdrop.classList.remove('ap-open');
        if (activeSpanEl) {
            activeSpanEl.classList.remove('ap-active');
            activeSpanEl = null;
        }
    }

    function setActiveSpan(el) {
        if (activeSpanEl && activeSpanEl !== el) {
            activeSpanEl.classList.remove('ap-active');
        }
        activeSpanEl = el;
        if (el) { el.classList.add('ap-active'); }
    }

    // ── DOM builders ─────────────────────────────────────────────

    function typeBadgeLabel(type) {
        return { direct: 'Direct', concept: 'Concept', paraphrase: 'Paraphrase', xref: 'Cross-ref' }[type] || type || '';
    }

    function buildAnchorItem(anchor, isRestoration) {
        var li = document.createElement('li');
        li.className = 'ap-anchor-item' + (isRestoration ? ' ap-restoration-ref' : '');

        var ref = document.createElement('div');
        ref.className = 'ap-anchor-ref';
        ref.textContent = anchor.ref || '';
        li.appendChild(ref);

        if (anchor.text) {
            var vt = document.createElement('p');
            vt.className = 'ap-anchor-text';
            vt.textContent = anchor.text;
            li.appendChild(vt);
        }
        if (anchor.comment) {
            var cm = document.createElement('p');
            cm.className = 'ap-anchor-comment';
            cm.textContent = anchor.comment;
            li.appendChild(cm);
        }
        return li;
    }

    function buildCrossrefItem(xref) {
        var li = document.createElement('li');
        var a  = document.createElement('a');
        a.className = 'ap-crossref-link';
        a.href = xref.href || '#';
        if (xref.href && xref.href.charAt(0) !== '#') {
            a.setAttribute('target', '_blank');
            a.setAttribute('rel', 'noopener');
        }
        if (xref.label) {
            var lbl = document.createElement('span');
            lbl.className = 'ap-crossref-label';
            lbl.textContent = xref.label;
            a.appendChild(lbl);
        }
        var ttl = document.createElement('span');
        ttl.className = 'ap-crossref-title';
        ttl.textContent = xref.title || '';
        a.appendChild(ttl);
        li.appendChild(a);
        return li;
    }

    // ── Populate panel ────────────────────────────────────────────

    function populatePanel(spanEl) {
        var spanId    = spanEl.dataset.span;
        var articleId = spanEl.dataset.article;
        var spanType  = spanEl.dataset.type || '';
        var isNamed   = spanEl.dataset.named === 'true';

        // Span text
        elSpanText.textContent = spanEl.textContent.trim();

        // Type badge
        var typeLabel = typeBadgeLabel(spanType);
        elTypeBadge.textContent = typeLabel;
        elTypeBadge.setAttribute('data-type', spanType);
        elTypeBadge.style.display = typeLabel ? '' : 'none';

        // Named badge
        var oldNamedBadge = elTypeBadge.parentElement.querySelector('.ap-named-badge');
        if (oldNamedBadge) { oldNamedBadge.remove(); }
        if (isNamed) {
            var nb = document.createElement('span');
            nb.className = 'ap-named-badge';
            nb.textContent = '\u25c8 Named';
            elTypeBadge.insertAdjacentElement('afterend', nb);
        }

        // Article label
        var artTitle = ARTICLE_TITLES[articleId] || articleId || '';
        var artNum   = articleId ? parseInt(articleId.replace('A', ''), 10) : null;
        elArticleLabel.textContent = artNum ? ('Article ' + artNum + ': ' + artTitle) : artTitle;

        // Span data
        var spanData = (apparatus[articleId] || {})[spanId] || {};

        // Definition
        var hasDef = isNamed && !!(spanData.definition && spanData.definition.trim());
        toggleBlock(elDefinitionBlock, hasDef);
        if (hasDef) { elDefinition.textContent = spanData.definition; }

        // Commentary
        var comment    = spanData.panel_comment || '';
        var hasComment = comment.trim().length > 0;
        toggleBlock(elCommentBlock, hasComment);
        if (hasComment) { elComment.textContent = comment; }

        // Anchor tabs
        var biblical    = Array.isArray(spanData.biblical)    ? spanData.biblical    : [];
        var restoration = Array.isArray(spanData.restoration) ? spanData.restoration : [];
        var hasAnchors  = biblical.length > 0 || restoration.length > 0;
        toggleBlock(elAnchorTabsBlock, hasAnchors);

        if (hasAnchors) {
            elBiblicalList.innerHTML = '';
            biblical.forEach(function (a) { elBiblicalList.appendChild(buildAnchorItem(a, false)); });
            toggleBlock(elBiblicalEmpty, biblical.length === 0);

            elRestorationList.innerHTML = '';
            restoration.forEach(function (a) { elRestorationList.appendChild(buildAnchorItem(a, true)); });
            toggleBlock(elRestorationEmpty, restoration.length === 0);

            // Default to the tab that has content; biblical wins ties
            switchTab(biblical.length > 0 ? elTabBiblical : elTabRestoration);
        }

        // Crossrefs
        var crossrefs = Array.isArray(spanData.crossref) ? spanData.crossref : [];
        toggleBlock(elCrossrefBlock, crossrefs.length > 0);
        elCrossrefList.innerHTML = '';
        crossrefs.forEach(function (x) { elCrossrefList.appendChild(buildCrossrefItem(x)); });

        // No-data fallback
        var hasAnyData = hasDef || hasComment || hasAnchors || crossrefs.length > 0;
        var emptyNote  = panelBody.querySelector('.ap-empty-note');
        if (!hasAnyData) {
            if (!emptyNote) {
                emptyNote = document.createElement('p');
                emptyNote.className = 'ap-empty-note';
                emptyNote.textContent = 'Commentary for this span is not yet available.';
                panelBody.appendChild(emptyNote);
            }
            emptyNote.style.display = '';
        } else if (emptyNote) {
            emptyNote.style.display = 'none';
        }

        panelBody.scrollTop = 0;
    }

    // ── Activation ────────────────────────────────────────────────

    function activateSpan(spanEl) {
        setActiveSpan(spanEl);
        populatePanel(spanEl);
        openPanel();
    }

    // ── Event: click / tap ────────────────────────────────────────

    document.addEventListener('click', function (e) {
        var spanEl = e.target.closest('[data-span]');
        if (spanEl) {
            e.stopPropagation();
            clearTimeout(hoverTimer);
            clearTimeout(leaveTimer);
            activateSpan(spanEl);
            return;
        }
        if (isOpen && !panel.contains(e.target)) { closePanel(); }
    }, true);

    // ── Event: hover (desktop only) ───────────────────────────────

    document.addEventListener('mouseover', function (e) {
        if (!isDesktopHover()) { return; }
        var spanEl = e.target.closest('[data-span]');
        if (!spanEl) { return; }
        clearTimeout(leaveTimer);
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(function () { activateSpan(spanEl); }, 120);
    });

    document.addEventListener('mouseout', function (e) {
        if (!isDesktopHover()) { return; }
        var spanEl = e.target.closest('[data-span]');
        if (!spanEl) { return; }
        if (e.relatedTarget && panel.contains(e.relatedTarget)) { return; }
        clearTimeout(hoverTimer);
        leaveTimer = setTimeout(function () {
            if (!panel.matches(':hover')) { closePanel(); }
        }, 260);
    });

    panel.addEventListener('mouseleave', function (e) {
        if (!isDesktopHover()) { return; }
        if (e.relatedTarget && e.relatedTarget.closest('[data-span]')) { return; }
        clearTimeout(hoverTimer);
        leaveTimer = setTimeout(closePanel, 300);
    });

    panel.addEventListener('mouseenter', function () {
        if (!isDesktopHover()) { return; }
        clearTimeout(leaveTimer);
        clearTimeout(hoverTimer);
    });

    // ── Event: close ──────────────────────────────────────────────

    closeBtn.addEventListener('click', function (e) { e.stopPropagation(); closePanel(); });
    backdrop.addEventListener('click', function (e) { e.stopPropagation(); closePanel(); });
    document.addEventListener('keydown', function (e) {
        if ((e.key === 'Escape' || e.key === 'Esc') && isOpen) { closePanel(); }
    });

    // ── Keyboard accessibility on spans ──────────────────────────

    document.querySelectorAll('[data-span]').forEach(function (el) {
        if (!el.hasAttribute('tabindex')) {
            el.setAttribute('tabindex', '0');
            el.setAttribute('role', 'button');
            el.setAttribute('aria-label', 'View annotation: ' + el.textContent.trim().slice(0, 60));
        }
        el.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                clearTimeout(hoverTimer);
                clearTimeout(leaveTimer);
                activateSpan(el);
            }
        });
    });

})();
