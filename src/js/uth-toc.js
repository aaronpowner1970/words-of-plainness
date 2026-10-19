/* uth-toc.js — contents tray for /about/under-the-hood/.
 *
 * Same behavior as the Articles navigation drawer (layouts/articles.njk):
 * the tab toggles it, the close button, Escape and a click outside close it,
 * choosing a link scrolls to the section and closes it. Added here because
 * that script is inline in the Articles layout, and /articles/ is left alone:
 *   - focus moves into the tray on open and back to the tab on close
 *   - the closed tray is `inert`, so its links are not reachable by keyboard
 *   - the target heading takes focus after a link is chosen
 *   - scroll-spy marks the current section (.an-active + aria-current), the
 *     way articles-progress.js does for the Articles list
 * Smooth scrolling is skipped when the reader prefers reduced motion.
 */
(function () {
    'use strict';

    var tab    = document.getElementById('anTab');
    var drawer = document.getElementById('anDrawer');
    var close  = document.getElementById('anClose');
    if (!tab || !drawer) return;

    var open = false;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

    function setOpen(next, returnFocus) {
        open = next;
        drawer.classList.toggle('an-open', open);
        tab.classList.toggle('an-is-open', open);
        tab.setAttribute('aria-expanded', open ? 'true' : 'false');
        tab.setAttribute('aria-label', open ? 'Close page contents' : 'Open page contents');
        drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
        if (open) {
            drawer.removeAttribute('inert');
            if (close) close.focus();
        } else {
            drawer.setAttribute('inert', '');
            if (returnFocus) tab.focus();
        }
    }

    tab.addEventListener('click', function (e) {
        e.stopPropagation();
        setOpen(!open, true);
    });

    if (close) {
        close.addEventListener('click', function (e) {
            e.stopPropagation();
            setOpen(false, true);
        });
    }

    document.addEventListener('click', function (e) {
        if (!open) return;
        if (drawer.contains(e.target) || tab.contains(e.target)) return;
        setOpen(false, false);
    });

    document.addEventListener('keydown', function (e) {
        if ((e.key === 'Escape' || e.key === 'Esc') && open) {
            setOpen(false, true);
        }
    });

    var links = Array.prototype.slice.call(drawer.querySelectorAll('.uth-toc-link'));

    links.forEach(function (link) {
        link.addEventListener('click', function (e) {
            var href = link.getAttribute('href') || '';
            if (href.charAt(0) !== '#') return;
            var target = document.getElementById(href.slice(1));
            if (!target) return;
            e.preventDefault();
            setOpen(false, false);
            target.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'start' });
            if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
            target.focus({ preventScroll: true });
            if (history.replaceState) history.replaceState(null, '', href);
        });
    });

    // Scroll-spy: the last heading whose top has passed the upper quarter of
    // the viewport is current. Document order puts an H3 after its H2, so a
    // subsection wins over its parent once the reader reaches it.
    var targets = links.map(function (l) {
        return document.getElementById(l.getAttribute('href').slice(1));
    });
    var current = null;
    var queued = false;

    function render() {
        links.forEach(function (l) {
            var on = l.getAttribute('href') === '#' + current;
            l.classList.toggle('an-active', on);
            if (on) l.setAttribute('aria-current', 'location');
            else l.removeAttribute('aria-current');
        });
    }

    function update() {
        queued = false;
        var line = window.innerHeight * 0.25;
        var found = null;
        for (var i = 0; i < targets.length; i++) {
            if (targets[i] && targets[i].getBoundingClientRect().top <= line) found = targets[i].id;
        }
        if (found !== current) { current = found; render(); }
    }

    function onScroll() {
        if (queued) return;
        queued = true;
        window.requestAnimationFrame(update);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();
})();
