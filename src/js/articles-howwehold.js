/* ============================================================
   HOW-WE-HOLD-THIS — Articles of Interfaith Discipleship
   Per-article reader-facing confessional disclosure. An inline
   "How we hold this" cue sits on a chosen span; a collapsed
   disclosure (gd-block sibling) carries the pastoral clarification.
   Data: window.WOP_HOLD[sectionId] (see src/_data/howWeHold.js).
   Mirrors the articles-godeeper.js injector. Closed by default.
   Touches neither the locked declaration markup nor the apparatus.
   ============================================================ */

(function () {
    'use strict';

    var DATA = (typeof window !== 'undefined' && window.WOP_HOLD) || {};
    if (!DATA || !Object.keys(DATA).length) { return; }

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    var CHEVRON = '<svg class="hw-cv" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>';
    var HEART   = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-4.4-9.3-8.5C1.2 9.7 2.6 6.5 6 6.5c2 0 3.2 1.4 4 2.6.8-1.2 2-2.6 4-2.6 3.4 0 4.8 3.2 3.3 6C19 16.6 12 21 12 21z"/></svg>';

    function buildCue(cfg, bodyId) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'hw-cue';
        b.setAttribute('aria-expanded', 'false');
        b.setAttribute('aria-controls', bodyId);
        b.innerHTML = esc(cfg.label) + CHEVRON;
        return b;
    }

    function buildBlock(cfg, bodyId) {
        var d = document.createElement('div');
        d.className = 'hw-block';
        d.setAttribute('data-hw', cfg.targetArticle || '');
        d.innerHTML =
            '<button class="hw-toggle" type="button" aria-expanded="false" aria-controls="' + bodyId + '">'
                + '<span class="hw-toggle-icon" aria-hidden="true">' + HEART + '</span>'
                + '<span class="hw-toggle-text">'
                    + '<span class="hw-toggle-label">' + esc(cfg.label) + '</span>'
                    + '<span class="hw-toggle-scent">' + esc(cfg.scent) + '</span>'
                + '</span>'
                + '<span class="hw-toggle-chevron">' + CHEVRON + '</span>'
            + '</button>'
            + '<div class="hw-body" id="' + bodyId + '" role="region" aria-label="' + esc(cfg.label) + '" hidden>'
                + '<div class="hw-inner">' + (cfg.html || '') + '</div>'
            + '</div>';
        return d;
    }

    // Insert the cue immediately AFTER the target span's sentence
    // punctuation (so it reads "…division. [cue] We are not…").
    function placeCue(section, cfg, cue) {
        var sel = '[data-span="' + cfg.targetSpan + '"][data-article="' + cfg.targetArticle + '"]';
        var target = section.querySelector(sel);
        if (!target) { return false; }
        var sib = target.nextSibling;
        if (sib && sib.nodeType === 3 && /^\s*[.;:,!?]/.test(sib.nodeValue)) {
            var ref = sib.nextSibling;                 // node after the ". " text (the next span)
            target.parentNode.insertBefore(cue, ref);
            target.parentNode.insertBefore(document.createTextNode(' '), ref);
        } else {
            target.insertAdjacentElement('afterend', cue);
        }
        return true;
    }

    function wire(block, cue) {
        var toggle = block.querySelector('.hw-toggle');
        var body   = block.querySelector('.hw-body');
        function set(open, scroll) {
            block.classList.toggle('hw-open', open);
            body.hidden = !open;
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (cue) { cue.setAttribute('aria-expanded', open ? 'true' : 'false'); }
            if (open && scroll) { block.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
        }
        toggle.addEventListener('click', function () { set(body.hidden, false); });
        if (cue) {
            cue.addEventListener('click', function (e) { e.preventDefault(); set(true, true); });
        }
    }

    function init() {
        var sections = document.querySelectorAll('.article-section');
        sections.forEach(function (section) {
            var id = section.id;
            var cfg = id && DATA[id];
            if (!cfg) { return; }
            if (section.querySelector('.hw-block')) { return; }   // idempotent

            var body   = section.querySelector('.article-body') || section;
            var bodyId = 'hw-body-' + id;

            var cue = buildCue(cfg, bodyId);
            if (!placeCue(section, cfg, cue)) { cue = null; }      // span gone → foot toggle still works

            var block = buildBlock(cfg, bodyId);
            var rjw = section.querySelector('.article-rjw');
            if (rjw) { body.insertBefore(block, rjw); } else { body.appendChild(block); }

            wire(block, cue);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
