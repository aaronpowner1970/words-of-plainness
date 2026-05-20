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
 *   <script type="application/json" id="apparatusData">{{ apparatusData | dump | safe }}</script>
 *   Structure: apparatus[articleId][spanId] = { text, type, named_concept,
 *     definition, panel_comment, biblical[], restoration[], crossref[] }
 *
 * SPAN MARKUP
 *   <span data-span="s1" data-article="A01" data-type="concept" data-named="true">text</span>
 * ─────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Static article title map ─────────────────────────────────
    // Article metadata is not included in apparatusData; kept here instead.
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

    // ── Element references ───────────────────────────────────────
    var panel           = document.getElementById('apPanel');
    var backdrop        = document.getElementById('apBackdrop');
    var closeBtn        = document.getElementById('apClose');
    var panelBody       = document.getElementById('apBody');

    // Header elements
    var elTypeBadge     = document.getElementById('apTypeBadge');
    var elArticleLabel  = document.getElementById('apArticleLabel');

    // Body elements
    var elSpanText          = document.getElementById('apSpanText');
    var elDefinitionBlock   = document.getElementById('apDefinitionBlock');
    var elDefinition        = document.getElementById('apDefinition');
    var elCommentBlock      = document.getElementById('apCommentBlock');
    var elComment           = document.getElementById('apComment');
    var elBiblicalBlock     = document.getElementById('apBiblicalBlock');
    var elBiblicalList      = document.getElementById('apBiblicalList');
    var elRestorationBlock  = document.getElementById('apRestorationBlock');
    var elRestorationList   = document.getElementById('apRestorationList');
    var elCrossrefBlock     = document.getElementById('apCrossrefBlock');
    var elCrossrefList      = document.getElementById('apCrossrefList');

    // Guard: bail if the panel isn't in the DOM
    if (!panel) { return; }

    // ── Load apparatus data ──────────────────────────────────────
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

    // ── Utility: breakpoint check ────────────────────────────────
    function isDesktopHover() {
        return window.matchMedia('(min-width: 1200px) and (hover: hover)').matches;
    }

    // ── Panel open / close ───────────────────────────────────────
    function openPanel() {
        if (isOpen) { return; }
        isOpen = true;
        panel.classList.add('ap-open');
        panel.setAttribute('aria-hidden', 'false');
        if (!isDesktopHover()) {
            backdrop.classList.add('ap-open');
        }
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

    // ── Build helpers ─────────────────────────────────────────────

    function typeBadgeLabel(type) {
        var labels = {
            direct:    'Direct',
            concept:   'Concept',
            paraphrase:'Paraphrase',
            xref:      'Cross-ref',
        };
        return labels[type] || type || '';
    }

    function buildAnchorItem(anchor, isRestoration) {
        var li = document.createElement('li');
        li.className = 'ap-anchor-item' + (isRestoration ? ' ap-restoration-ref' : '');

        var ref = document.createElement('div');
        ref.className = 'ap-anchor-ref';
        ref.textContent = anchor.ref || '';
        li.appendChild(ref);

        if (anchor.text) {
            var verseText = document.createElement('p');
            verseText.className = 'ap-anchor-text';
            verseText.textContent = anchor.text;
            li.appendChild(verseText);
        }

        if (anchor.comment) {
            var comment = document.createElement('p');
            comment.className = 'ap-anchor-comment';
            comment.textContent = anchor.comment;
            li.appendChild(comment);
        }

        return li;
    }

    function buildCrossrefItem(xref) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.className = 'ap-crossref-link';
        a.href = xref.href || '#';
        if (xref.href && xref.href.charAt(0) !== '#') {
            a.setAttribute('target', '_blank');
            a.setAttribute('rel', 'noopener');
        }

        if (xref.label) {
            var labelEl = document.createElement('span');
            labelEl.className = 'ap-crossref-label';
            labelEl.textContent = xref.label;
            a.appendChild(labelEl);
        }

        var titleEl = document.createElement('span');
        titleEl.className = 'ap-crossref-title';
        titleEl.textContent = xref.title || '';
        a.appendChild(titleEl);

        li.appendChild(a);
        return li;
    }

    // ── Populate panel ────────────────────────────────────────────
    function populatePanel(spanEl) {
        var spanId    = spanEl.dataset.span;
        var articleId = spanEl.dataset.article;
        var spanType  = spanEl.dataset.type  || '';
        var isNamed   = spanEl.dataset.named === 'true';

        // Span text (the declaration clause)
        elSpanText.textContent = spanEl.textContent.trim();

        // ── Header: type badge ─────────────────────────────────────
        var typeLabel = typeBadgeLabel(spanType);
        elTypeBadge.textContent = typeLabel || '';
        elTypeBadge.setAttribute('data-type', spanType);
        elTypeBadge.style.display = typeLabel ? '' : 'none';

        // Remove old named badge if any
        var oldNamedBadge = elTypeBadge.parentElement.querySelector('.ap-named-badge');
        if (oldNamedBadge) { oldNamedBadge.remove(); }
        if (isNamed) {
            var namedBadge = document.createElement('span');
            namedBadge.className = 'ap-named-badge';
            namedBadge.textContent = '\u25c8 Named';
            elTypeBadge.insertAdjacentElement('afterend', namedBadge);
        }

        // ── Header: article label ───────────────────────────────────
        var artTitle = ARTICLE_TITLES[articleId] || articleId || '';
        var artNum   = articleId ? parseInt(articleId.replace('A', ''), 10) : null;
        elArticleLabel.textContent = artNum ? ('Article ' + artNum + ': ' + artTitle) : artTitle;

        // ── Retrieve span data ──────────────────────────────────────
        var artData  = apparatus[articleId] || {};
        var spanData = artData[spanId]       || {};

        // ── Definition (named-concept spans) ───────────────────────
        var hasDefinition = isNamed && !!(spanData.definition && spanData.definition.trim());
        toggleBlock(elDefinitionBlock, hasDefinition);
        if (hasDefinition) {
            elDefinition.textContent = spanData.definition;
        }

        // ── Panel comment ───────────────────────────────────────────
        var comment    = spanData.panel_comment || '';
        var hasComment = comment.trim().length > 0;
        toggleBlock(elCommentBlock, hasComment);
        if (hasComment) {
            elComment.textContent = comment;
        }

        // ── Biblical anchors ────────────────────────────────────────
        var biblical = Array.isArray(spanData.biblical) ? spanData.biblical : [];
        toggleBlock(elBiblicalBlock, biblical.length > 0);
        elBiblicalList.innerHTML = '';
        biblical.forEach(function (anchor) {
            elBiblicalList.appendChild(buildAnchorItem(anchor, false));
        });

        // ── Restoration anchors ─────────────────────────────────────
        var restoration = Array.isArray(spanData.restoration) ? spanData.restoration : [];
        toggleBlock(elRestorationBlock, restoration.length > 0);
        elRestorationList.innerHTML = '';
        restoration.forEach(function (anchor) {
            elRestorationList.appendChild(buildAnchorItem(anchor, true));
        });

        // ── Cross-references ────────────────────────────────────────
        var crossrefs = Array.isArray(spanData.crossref) ? spanData.crossref : [];
        toggleBlock(elCrossrefBlock, crossrefs.length > 0);
        elCrossrefList.innerHTML = '';
        crossrefs.forEach(function (xref) {
            elCrossrefList.appendChild(buildCrossrefItem(xref));
        });

        // ── No-data fallback ────────────────────────────────────────
        var hasAnyData = hasDefinition || hasComment || biblical.length > 0
                          || restoration.length > 0 || crossrefs.length > 0;
        var emptyNote = panelBody.querySelector('.ap-empty-note');
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

        // Scroll body to top on each new span
        panelBody.scrollTop = 0;
    }

    function toggleBlock(el, show) {
        if (show) {
            el.classList.remove('ap-hidden');
        } else {
            el.classList.add('ap-hidden');
        }
    }

    // ── Activation (shared by click and hover paths) ──────────────
    function activateSpan(spanEl) {
        setActiveSpan(spanEl);
        populatePanel(spanEl);
        openPanel();
    }

    // ── Click / tap handler (document delegation, capture phase) ──
    document.addEventListener('click', function (e) {
        var spanEl = e.target.closest('[data-span]');

        if (spanEl) {
            e.stopPropagation();
            clearTimeout(hoverTimer);
            clearTimeout(leaveTimer);
            activateSpan(spanEl);
            return;
        }

        // Click outside closes on desktop (backdrop handles mobile)
        if (isOpen && !panel.contains(e.target)) {
            closePanel();
        }
    }, true);

    // ── Hover handlers (desktop / pointer:hover only) ─────────────
    document.addEventListener('mouseover', function (e) {
        if (!isDesktopHover()) { return; }
        var spanEl = e.target.closest('[data-span]');
        if (!spanEl) { return; }

        clearTimeout(leaveTimer);
        clearTimeout(hoverTimer);

        hoverTimer = setTimeout(function () {
            activateSpan(spanEl);
        }, 120);
    });

    document.addEventListener('mouseout', function (e) {
        if (!isDesktopHover()) { return; }
        var spanEl = e.target.closest('[data-span]');
        if (!spanEl) { return; }

        // If moving into the panel, don't close
        var dest = e.relatedTarget;
        if (dest && panel.contains(dest)) { return; }

        clearTimeout(hoverTimer);
        leaveTimer = setTimeout(function () {
            if (!panel.matches(':hover')) {
                closePanel();
            }
        }, 260);
    });

    // When cursor leaves the panel itself
    panel.addEventListener('mouseleave', function (e) {
        if (!isDesktopHover()) { return; }
        var dest = e.relatedTarget;
        if (dest && dest.closest('[data-span]')) { return; }

        clearTimeout(hoverTimer);
        leaveTimer = setTimeout(function () {
            closePanel();
        }, 300);
    });

    panel.addEventListener('mouseenter', function () {
        if (!isDesktopHover()) { return; }
        clearTimeout(leaveTimer);
        clearTimeout(hoverTimer);
    });

    // ── Close handlers ────────────────────────────────────────────
    closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        closePanel();
    });

    backdrop.addEventListener('click', function (e) {
        e.stopPropagation();
        closePanel();
    });

    document.addEventListener('keydown', function (e) {
        if ((e.key === 'Escape' || e.key === 'Esc') && isOpen) {
            closePanel();
        }
    });

    // ── Span keyboard activation ──────────────────────────────────
    // Spans are inline text — add tabindex at runtime so they're keyboard-reachable
    document.querySelectorAll('[data-span]').forEach(function (el) {
        if (!el.hasAttribute('tabindex')) {
            el.setAttribute('tabindex', '0');
            el.setAttribute('role', 'button');
            el.setAttribute('aria-label',
                'View annotation: ' + el.textContent.trim().slice(0, 60));
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
