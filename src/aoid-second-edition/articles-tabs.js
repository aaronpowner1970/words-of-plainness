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

    window.addEventListener('hashchange', fromHash);
    document.addEventListener('DOMContentLoaded', function () { sections.forEach(tidy); });
    window.addEventListener('load', function () { sections.forEach(tidy); fromHash(); });
    fromHash();
})();
