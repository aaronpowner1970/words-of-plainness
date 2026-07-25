/* ============================================================
   ARTICLES PROGRESS INDICATOR  (scroll-spy)
   /articles/ — tracks which of the thirteen articles is in view.

   Two synchronized outputs, one source of truth:
     1. #anProgress  — "Article N of 13 — Title" readout in the drawer
                       header (aria-live="polite").
     2. .an-link     — aria-current="true" + .an-active on the matching
                       Contents-drawer entry (and #anTabCount "N/13" on the
                       closed tab).

   Front matter (A00 banner, prologue, Learning Pathways) sits before
   Article 1, so the indicator holds a pre-count state — "Invitation" —
   until A01 reaches the band.

   Supersedes the inline observer that previously lived in
   layouts/articles.njk. Two observers both toggling .an-active fought each
   other; this is the only writer now.

   Progressive enhancement: with JS off, the drawer still navigates and the
   readout stays empty (.an-progress:empty is display:none). Paragraph
   indices (data-paragraph / sync-para) are not touched — nothing here reads
   or writes them.
   ============================================================ */

(function () {
    'use strict';

    var TOTAL = 13;
    var PRECOUNT_LABEL = 'Invitation';

    // Band: current flips when a heading crosses roughly the upper third of
    // the viewport. -30% top / -60% bottom leaves a 10%-tall detection strip,
    // so normally exactly one section qualifies — the main defence against
    // boundary jitter. Ties are broken by document order (topmost wins).
    var ROOT_MARGIN = '-30% 0px -60% 0px';

    function init() {
        var sections = Array.prototype.slice.call(
            document.querySelectorAll('.article-section')
        );
        if (!sections.length || !('IntersectionObserver' in window)) return;

        var drawer  = document.getElementById('anDrawer');
        var readout = document.getElementById('anProgress');
        var badge   = document.getElementById('anTabCount');

        // Only the thirteen in-page article links — the download, companion,
        // and music links in the drawer share .an-link but are not articles.
        var links = drawer
            ? Array.prototype.slice.call(drawer.querySelectorAll('.an-link'))
                .filter(function (l) {
                    return (l.getAttribute('href') || '').charAt(0) === '#';
                })
            : [];

        var order   = sections.map(function (s) { return s.id; });
        var visible = Object.create(null);
        var current = null;      // section id, or null for the pre-count state
        var firstSection = sections[0];

        function titleOf(section) {
            var h = section.querySelector('.article-title');
            return h ? h.textContent.trim() : '';
        }

        function render() {
            var idx = current ? order.indexOf(current) : -1;

            if (readout) {
                readout.textContent = idx < 0
                    ? PRECOUNT_LABEL
                    : 'Article ' + (idx + 1) + ' of ' + TOTAL + ' — ' +
                      titleOf(sections[idx]);
            }

            if (badge) {
                badge.textContent = idx < 0 ? '' : (idx + 1) + '/' + TOTAL;
            }

            links.forEach(function (l) {
                var match = current && l.getAttribute('href') === '#' + current;
                l.classList.toggle('an-active', !!match);
                if (match) {
                    l.setAttribute('aria-current', 'true');
                } else {
                    l.removeAttribute('aria-current');
                }
            });
        }

        function resolve() {
            var top = null;
            for (var i = 0; i < order.length; i++) {
                if (visible[order[i]]) { top = order[i]; break; }
            }

            if (top) {
                current = top;
            } else if (firstSection.getBoundingClientRect().top >
                       window.innerHeight * 0.3) {
                // Above Article 1 — front matter.
                current = null;
            }
            // Otherwise hold the last known article: the reader is between
            // detection bands (a divider, a tall banner), not back at the top.
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                visible[entry.target.id] = entry.isIntersecting;
            });

            var previous = current;
            resolve();

            // Render only on change. The readout is an aria-live region, so a
            // render per callback would announce continuously while scrolling.
            if (current !== previous) render();
        }, { rootMargin: ROOT_MARGIN, threshold: 0 });

        sections.forEach(function (s) { observer.observe(s); });

        render();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
