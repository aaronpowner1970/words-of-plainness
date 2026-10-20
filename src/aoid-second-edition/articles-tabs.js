/* ============================================================
   Article tabs: Declaration / Disclosure / Record  (CODE-AOID2-26)
   Loaded only when the Second Edition switch is ON.
   Markup: src/_includes/components/article-tabs.njk. Styles: articles-tabs.css.

   What it does
     - tab semantics: click, ArrowLeft / ArrowRight (wrapping), Home, End; roving tabindex
     - deep links: #a02-declaration, #a02-disclosure, #a02-record open that tab on load and on
       hashchange; so does any link or hash that points at something inside a hidden tab
       (e.g. #a02-record-what-the-sixteen-cover)
     - the footnote's link to the standalone disclosure opens the Disclosure tab in place
       (the link keeps its href, so it still works without this script)
     - folds the Listen / Slides / Video buttons, which other scripts add after the title,
       into the Declaration tab
     - moves the "How we hold this" note (built by articles-howwehold.js) into the Disclosure tab,
       and makes its inline cue open that tab first
   Step 89 (CODE-AOID2-48), also here:
     - the count sentence in a measured span's panel, read from the embedded #aoidCountData (written from
       data-sources/aoid/floor_counts.json), with "See the record" and "How this was measured"
     - "How this was measured" (AOID2-FLOOR-METHOD-LINK): closes the panel, opens the Article's Disclosure tab, scrolls
       to the top of the method account with a brief highlight, and shows one line above it, "Back to span N", that
       returns to the Declaration tab with that span selected and its panel open. Opening the Disclosure tab any other
       way shows no back line. "See the record" opens the Record tab at that teaching's row.
   It changes nothing inside .article-body.
   ============================================================ */
(function () {
    'use strict';

    var NAMES = ['declaration', 'disclosure', 'record'];
    var MEDIA = '.article-read-aloud-btn, .article-slides-btn, .article-video-btn';

    function all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

    var sections = all('.article-section').filter(function (s) { return s.querySelector(':scope > .an-tabs'); });
    if (!sections.length) { return; }

    function idOf(section) { return section.querySelector(':scope > .an-tabs [role="tab"]').id.replace(/-tab-declaration$/, ''); }
    function tabsOf(section) { return all(':scope > .an-tabs [role="tab"]', section); }
    function panelOf(section, name) { return document.getElementById(idOf(section) + '-' + name); }
    function titleOf(section) { return section.querySelector(':scope > .article-title'); }

    function select(section, name, focus) {
        var tabs = tabsOf(section);
        all('.an-method-back', section).forEach(function (b) { b.hidden = true; });
        NAMES.forEach(function (n, i) {
            var on = n === name;
            tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
            tabs[i].tabIndex = on ? 0 : -1;
            panelOf(section, n).hidden = !on;
            if (on && focus) { tabs[i].focus(); }
        });
    }

    // `instant` skips the page's smooth scrolling (deep links should land, not glide from the top).
    function toTitle(section, instant) {
        var t = titleOf(section);
        if (t) { t.scrollIntoView(instant ? { block: 'start', behavior: 'instant' } : { block: 'start' }); }
    }

    function setHash(section, name) {
        try { history.replaceState(null, '', '#' + idOf(section) + '-' + name); } catch (e) { /* sandboxed */ }
    }

    // Open whatever tab holds `target`, then bring `target` (or the Article's title) into view.
    function reveal(target, instant) {
        var panel = target.closest ? target.closest('.an-panel') : null;
        if (!panel) { return false; }
        var section = panel.closest('.article-section');
        var name = panel.id.slice(idOf(section).length + 1);
        if (panel.hidden) { select(section, name, false); }
        if (target === panel) { toTitle(section, instant); }
        else { target.scrollIntoView(instant ? { block: 'start', behavior: 'instant' } : { block: 'start' }); }
        return true;
    }

    function fromHash() {
        var id;
        try { id = decodeURIComponent(location.hash.slice(1)); } catch (e) { return; }
        var el = id && document.getElementById(id);
        if (el) { reveal(el, true); }
    }

    // ── Wire each Article ───────────────────────────────────────
    function tidy(section) {
        var media = section.querySelector('.an-media');
        if (media) {
            all(MEDIA, section).forEach(function (b) { if (!media.contains(b)) { media.appendChild(b); } });
        }
        var slot = section.querySelector('.an-note-slot');
        var block = section.querySelector('.hw-block');
        if (slot && block && block.parentNode !== slot) { slot.appendChild(block); }
    }

    sections.forEach(function (section) {
        section.classList.add('an-tabbed');
        var tabs = tabsOf(section);
        tabs.forEach(function (tab, i) {
            tab.addEventListener('click', function () {
                select(section, NAMES[i], false);
                setHash(section, NAMES[i]);
            });
            tab.addEventListener('keydown', function (e) {
                var j = i;
                if (e.key === 'ArrowRight') { j = (i + 1) % tabs.length; }
                else if (e.key === 'ArrowLeft') { j = (i - 1 + tabs.length) % tabs.length; }
                else if (e.key === 'Home') { j = 0; }
                else if (e.key === 'End') { j = tabs.length - 1; }
                else { return; }
                e.preventDefault();
                select(section, NAMES[j], true);
                setHash(section, NAMES[j]);
            });
        });
        tidy(section);
        // Listen, Slides and Video are added by other scripts, in any order, after this one runs.
        new MutationObserver(function () { tidy(section); }).observe(section, { childList: true });
    });

    // ── Links ────────────────────────────────────────────────────
    function samePath(href, address) {
        try { return new URL(href, location.href).pathname.replace(/\/?$/, '/') === address; } catch (e) { return false; }
    }

    document.addEventListener('click', function (e) {
        var cue = e.target.closest && e.target.closest('.hw-cue');
        if (cue) {                                   // inline "How we hold this" cue: show the Disclosure tab first
            var home = cue.closest('.article-section');
            if (home && home.querySelector(':scope > .an-tabs')) { select(home, 'disclosure', false); setHash(home, 'disclosure'); }
            return;
        }
        var a = e.target.closest && e.target.closest('a[href]');
        if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) { return; }
        if (a.hasAttribute('data-an-method') || a.hasAttribute('data-an-back') || a.hasAttribute('data-an-record')) { return; }   // step 89 links, handled below

        // The footnote's link to the standalone disclosure opens the Disclosure tab in place.
        var decl = a.closest('.an-declaration');
        if (decl) {
            var section = decl.closest('.article-section');
            var disc = panelOf(section, 'disclosure');
            var address = disc && disc.getAttribute('data-address');
            if (address && samePath(a.getAttribute('href'), address)) {
                e.preventDefault();
                select(section, 'disclosure', true);
                setHash(section, 'disclosure');
                toTitle(section);
                return;
            }
        }

        // A link to something inside a hidden tab opens that tab.
        var href = a.getAttribute('href');
        if (href.charAt(0) !== '#' || href.length < 2) { return; }
        var id;
        try { id = decodeURIComponent(href.slice(1)); } catch (err) { return; }
        var target = document.getElementById(id);
        var panel = target && target.closest && target.closest('.an-panel');
        if (panel && panel.hidden) {
            e.preventDefault();
            try { history.pushState(null, '', href); } catch (err2) { /* ignore */ }
            reveal(target);
        }
    }, true);

    // ── Step 89: counts in a span's panel ──────────────────────
    var COUNTS = {};
    try { COUNTS = JSON.parse((document.getElementById('aoidCountData') || {}).textContent || '{}') || {}; } catch (err3) { COUNTS = {}; }
    var apBody = document.getElementById('apBody');
    var apSpanText = document.getElementById('apSpanText');
    var apComment = document.getElementById('apCommentBlock');
    var countBlock = null;
    var fromSpan = null;                       // the span whose panel opened the method link

    function el(tag, cls, text) { var e = document.createElement(tag); if (cls) { e.className = cls; } if (text !== undefined) { e.textContent = text; } return e; }
    function spanNo(id) { return id.replace(/^s/, ''); }

    function showCounts() {
        if (!apBody || !apComment) { return; }
        if (countBlock) { countBlock.remove(); countBlock = null; }
        var active = document.querySelector('[data-span].ap-active');
        if (!active) { return; }
        var art = active.getAttribute('data-article');
        var span = active.getAttribute('data-span');
        var floors = (COUNTS[art] || {})[span];
        if (!floors || !floors.length) { return; }
        var key = art.toLowerCase();
        countBlock = el('div', 'ap-count-block');
        floors.forEach(function (f) {
            countBlock.appendChild(el('p', 'ap-count-sentence', 'Taught in ' + f.t + ', contradicted in ' + f.c + ', no position in ' + f.n + ', of sixteen.'));
            var links = el('p', 'ap-count-links');
            var rec = el('a', '', 'See the record');
            rec.href = '#' + key + '-record-' + f.id;
            rec.setAttribute('data-an-record', f.id);
            var how = el('a', '', 'How this was measured');
            how.href = '#' + key + '-method';
            how.setAttribute('data-an-method', '1');
            links.appendChild(rec);
            links.appendChild(how);
            countBlock.appendChild(links);
        });
        apComment.insertAdjacentElement('afterend', countBlock);
    }
    if (apSpanText && window.MutationObserver) {
        // the panel script rewrites the span text each time it fills the panel (click or keyboard)
        new MutationObserver(showCounts).observe(apSpanText, { childList: true, characterData: true, subtree: true });
    }

    // Scroll `node` into view at once (as the page's deep links do) and again as the layout settles (hiding a tab
    // and closing the panel shift the page), unless the reader has touched the page in between.
    function land(node, block) {
        var touched = false;
        var mark = function () { touched = true; };
        ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (n) { window.addEventListener(n, mark, { once: true, passive: true }); });
        node.scrollIntoView({ block: block, behavior: 'instant' });
        [120, 400, 800].forEach(function (ms) {
            setTimeout(function () { if (!touched) { node.scrollIntoView({ block: block, behavior: 'instant' }); } }, ms);
        });
    }
    function closePanel() { var c = document.getElementById('apClose'); if (c) { c.click(); } }
    function flash(node, cls) {
        node.classList.remove(cls);
        void node.offsetWidth;
        node.classList.add(cls);
        setTimeout(function () { node.classList.remove(cls); }, 2000);
    }

    document.addEventListener('click', function (e) {
        var a = e.target.closest && e.target.closest('a');
        if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) { return; }

        if (a.hasAttribute('data-an-method')) {         // "How this was measured" (AOID2-FLOOR-METHOD-LINK)
            var span = document.querySelector('[data-span].ap-active');
            var section = span && span.closest('.article-section');
            var target = document.getElementById(a.getAttribute('href').slice(1));
            if (!section || !target) { return; }
            e.preventDefault();
            e.stopPropagation();
            fromSpan = span;
            closePanel();
            select(section, 'disclosure', false);
            var back = target.querySelector('.an-method-back');
            if (back) {
                back.querySelector('a').textContent = 'Back to span ' + spanNo(span.getAttribute('data-span'));
                back.hidden = false;
            }
            try { history.pushState(null, '', '#' + target.id); } catch (err4) { /* sandboxed */ }
            land(target, 'start');
            flash(target, 'an-method-flash');
            return;
        }
        if (a.hasAttribute('data-an-back')) {            // "Back to span N"
            var home = a.closest('.article-section');
            e.preventDefault();
            e.stopPropagation();
            a.closest('.an-method-back').hidden = true;
            if (home) { select(home, 'declaration', false); setHash(home, 'declaration'); }
            if (fromSpan) {
                land(fromSpan, 'center');
                fromSpan.click();
            }
            return;
        }
        if (a.hasAttribute('data-an-record')) {          // "See the record"
            var active2 = document.querySelector('[data-span].ap-active');
            var recSection = active2 && active2.closest('.article-section');
            var row = document.getElementById(a.getAttribute('href').slice(1));
            if (!recSection || !row) { return; }
            e.preventDefault();
            e.stopPropagation();
            closePanel();
            select(recSection, 'record', false);
            land(row, 'center');
            flash(row, 'an-row-flash');
        }
    }, true);

    window.addEventListener('hashchange', fromHash);
    document.addEventListener('DOMContentLoaded', function () { sections.forEach(tidy); });
    window.addEventListener('load', function () { sections.forEach(tidy); fromHash(); });
    fromHash();
})();
