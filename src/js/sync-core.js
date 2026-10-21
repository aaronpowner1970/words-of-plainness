/**
 * sync-core.js — one shared media↔text sync component (window.WopSync).
 *
 * Drives "highlight the element that is being spoken or sung" from a media
 * element's WebVTT metadata <track> (cuechange, with timeupdate/seeked as a
 * fallback), keeps the active element inside a comfort band with auto-scroll,
 * suspends auto-scroll when the visitor scrolls by hand, and turns clicks and
 * keys on targets into seeks.
 *
 * Modes (defaults only; every option can be overridden):
 *   'video'        — narration of a page; targets are [data-narr] elements in
 *                    the document, the window scrolls.
 *   'audio-lyrics' — a lyric sheet; targets are line elements, `scroller` is
 *                    the lyrics container, nothing is click-seekable unless
 *                    `clickSeek` is set.
 *
 * Cue identifier (cue.id) must equal the target's id attribute value. The cue
 * list comes from the VTT, which is generated from the timing JSON — this file
 * holds no times of its own.
 *
 * wop-player.js / anthem-player.js / creation.js predate this and keep their
 * own sync; they can adopt this module later (same cue→element contract).
 */
(function (root) {
    'use strict';

    function create(opts) {
        var mode = opts.mode || 'video';
        var media = opts.media;
        var idAttr = opts.idAttr || 'data-narr';
        var scroller = opts.scroller || null;
        var clickSeek = opts.clickSeek !== undefined ? opts.clickSeek : mode === 'video';
        var doc = opts.root || document;
        var track = null;
        var cues = [];                    // [{id, start, end, el}] sorted by start
        var els = {};                     // id -> element
        var activeIdx = -1;
        var follow = true;
        var finished = false;
        var fadeTimer = null;
        var progUntil = 0, progTimer = null;
        var destroyed = false;

        function reduced() {
            return !!(root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches);
        }

        /* ---------- cues ---------- */
        function loadCues() {
            var list = track && track.cues ? Array.prototype.slice.call(track.cues) : [];
            if (!list.length) return false;
            cues = list.map(function (c) { return { id: c.id, start: c.startTime, end: c.endTime, el: els[c.id] || null }; })
                       .sort(function (a, b) { return a.start - b.start; });
            if (opts.onReady) opts.onReady(cues);
            return true;
        }

        function collect() {
            els = {};
            var nodes = doc.querySelectorAll(opts.selector || '[' + idAttr + ']');
            for (var i = 0; i < nodes.length; i++) els[nodes[i].getAttribute(idAttr)] = nodes[i];
        }

        function indexAt(t) {
            // Last cue with start <= t; -1 before the first. Binary search.
            var lo = 0, hi = cues.length - 1, r = -1;
            while (lo <= hi) {
                var mid = (lo + hi) >> 1;
                if (cues[mid].start <= t) { r = mid; lo = mid + 1; } else hi = mid - 1;
            }
            return r;
        }

        /* ---------- highlight ---------- */
        function setActive(idx) {
            if (idx === activeIdx) return;
            var prev = activeIdx >= 0 ? cues[activeIdx].el : null;
            if (prev) prev.classList.remove('is-active', 'is-fading');
            clearTimeout(fadeTimer);
            activeIdx = idx;
            var el = idx >= 0 ? cues[idx].el : null;
            if (el) {
                el.classList.add('is-active');
                if (follow) ensureVisible(el);
            }
            if (opts.onActive) opts.onActive(idx >= 0 ? cues[idx].id : null, el, idx);
        }

        function update() {
            if (destroyed || !cues.length) return;
            var t = media.currentTime;
            var last = cues[cues.length - 1];
            if (t >= last.end - 0.02 && !finished) {
                finish();
                return;
            }
            if (t < last.end - 0.5) finished = false;
            var idx = indexAt(t);
            // Gaps between cues (the speaker's pauses) hold the previous highlight.
            if (idx >= 0 && finished) return;
            setActive(idx);
        }

        function finish() {
            finished = true;
            var el = activeIdx >= 0 ? cues[activeIdx].el : null;
            if (el) el.classList.add('is-fading');
            clearTimeout(fadeTimer);
            fadeTimer = setTimeout(function () {
                if (el) el.classList.remove('is-active', 'is-fading');
                activeIdx = -1;
                if (opts.onEnd) opts.onEnd();
            }, reduced() ? 0 : 1100);
        }

        /* ---------- comfort-band auto-scroll ---------- */
        function band() {
            var vp = scroller ? scroller.getBoundingClientRect() : { top: 0, bottom: root.innerHeight };
            var ins = opts.insets ? opts.insets() : { top: 0, bottom: 0 };
            var top = vp.top + (ins.top || 0), bottom = vp.bottom - (ins.bottom || 0);
            var h = Math.max(bottom - top, 80);
            return { top: top, h: h, lo: top + h * 0.12, hi: top + h * 0.72, aim: top + h * 0.28 };
        }

        function ensureVisible(el, force) {
            if (!follow && !force) return;
            var rects = el.getClientRects();
            if (!rects.length) return;
            var first = rects[0], lastR = rects[rects.length - 1];
            var b = band();
            var tall = (lastR.bottom - first.top) > (b.hi - b.lo);
            var inBand = first.top >= b.lo && (tall ? first.top <= b.hi : lastR.bottom <= b.hi);
            if (inBand && !force) return;
            var delta = first.top - b.aim;
            if (Math.abs(delta) < 2) return;
            markProgrammatic();
            // 'instant' not 'auto': the site sets html { scroll-behavior: smooth }, which 'auto' would follow.
            var o = { top: delta, behavior: reduced() ? 'instant' : 'smooth' };
            if (scroller) scroller.scrollBy(o); else root.scrollBy(o);
        }

        function markProgrammatic() {
            progUntil = Date.now() + 1500;
            clearTimeout(progTimer);
            // Smooth scrolls can start late; wheel/touch/key input is caught separately,
            // so this window only has to cover the first scroll event of our own scroll.
            progTimer = setTimeout(function () { progUntil = 0; }, 1200);
        }

        function onScroll() {
            if (progUntil) {
                // our own smooth scroll is still moving: extend the window while events keep coming
                clearTimeout(progTimer);
                progTimer = setTimeout(function () { progUntil = 0; }, 150);
                return;
            }
            suspend();
        }
        function onManual() { suspend(); }

        function suspend() {
            // Only an engaged session (player open) can be "suspended" by the visitor's scrolling.
            if (!follow || (opts.keysActive && !opts.keysActive())) return;
            follow = false;
            if (opts.onSuspend) opts.onSuspend();
        }

        function resumeFollow(o) {
            var wasOff = !follow;
            follow = true;
            if (activeIdx >= 0 && cues[activeIdx].el) ensureVisible(cues[activeIdx].el, !o || o.scroll !== false);
            if (wasOff && opts.onResume) opts.onResume();
        }

        /* ---------- seek / navigate ---------- */
        function seekTo(id, o) {
            for (var i = 0; i < cues.length; i++) {
                if (cues[i].id === id) {
                    finished = false;
                    media.currentTime = cues[i].start + 0.02;
                    setActive(i);
                    resumeFollow({ scroll: !(o && o.scroll === false) });
                    return true;
                }
            }
            return false;
        }
        function step(dir) {
            if (!cues.length) return;
            var cur = activeIdx >= 0 ? activeIdx : Math.max(indexAt(media.currentTime), 0);
            var next = Math.min(Math.max(cur + dir, 0), cues.length - 1);
            seekTo(cues[next].id);
        }

        /* ---------- input ---------- */
        function onClick(e) {
            if (!clickSeek || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            var t = e.target.closest && e.target.closest('[' + idAttr + ']');
            if (!t || !doc.contains(t)) return;
            if (e.target.closest('a')) return;                     // links navigate, no seek
            var sel = root.getSelection && root.getSelection();
            if (sel && !sel.isCollapsed && sel.toString().trim()) return;   // selecting text, no seek
            if (opts.onTargetClick) opts.onTargetClick(t.getAttribute(idAttr), e);
        }

        function onKey(e) {
            if (e.altKey || e.ctrlKey || e.metaKey) return;
            var t = e.target;
            var isTarget = t && t.hasAttribute && t.hasAttribute(idAttr);
            if (isTarget && e.key === 'Enter' && clickSeek) {
                e.preventDefault();
                if (opts.onTargetClick) opts.onTargetClick(t.getAttribute(idAttr), e);
                return;
            }
            if (!opts.keysActive || !opts.keysActive()) return;
            var tag = t && t.tagName;
            var typing = t && (t.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT');
            var onControl = t && (tag === 'BUTTON' || tag === 'A' || (t.getAttribute && t.getAttribute('role') === 'button'));
            if (e.key === 'Escape') { if (opts.onEscape) opts.onEscape(); return; }
            if (typing) return;
            if (e.key === ' ' || e.code === 'Space') {
                if (onControl && !isTarget) return;                // the focused button handles its own Space
                e.preventDefault();
                if (opts.onToggle) opts.onToggle();
            } else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
        }

        /* ---------- lifecycle ---------- */
        function start() {
            collect();
            track = opts.track || (media.textTracks && media.textTracks[0]);
            if (!track) return;
            track.mode = 'hidden';
            if (!loadCues()) {
                var trackEl = opts.trackEl;
                if (trackEl) trackEl.addEventListener('load', function () { loadCues(); update(); });
            }
            track.addEventListener('cuechange', update);
            media.addEventListener('timeupdate', update);
            media.addEventListener('seeked', update);
            media.addEventListener('ended', update);
            var s = scroller || root;
            s.addEventListener('scroll', onScroll, { passive: true });
            s.addEventListener('wheel', onManual, { passive: true });
            s.addEventListener('touchmove', onManual, { passive: true });
            root.addEventListener('keydown', function (e) {
                if (['PageUp', 'PageDown', 'Home', 'End', 'ArrowUp', 'ArrowDown'].indexOf(e.key) >= 0 && !(e.target.tagName === 'INPUT')) onManual();
            }, true);
            doc.addEventListener('click', onClick);
            root.addEventListener('keydown', onKey);
        }

        return {
            start: start,
            seekTo: seekTo,
            next: function () { step(1); },
            prev: function () { step(-1); },
            resumeFollow: resumeFollow,
            isFollowing: function () { return follow; },
            isFinished: function () { return finished; },
            activeId: function () { return activeIdx >= 0 ? cues[activeIdx].id : null; },
            activeEl: function () { return activeIdx >= 0 ? cues[activeIdx].el : null; },
            cues: function () { return cues; },
            refresh: function () { collect(); loadCues(); update(); },
            reset: function () { finished = false; setActive(-1); },
            destroy: function () { destroyed = true; }
        };
    }

    root.WopSync = { create: create };
})(window);
