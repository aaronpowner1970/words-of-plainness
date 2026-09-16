/* ============================================================
   chat-menu.js — /chat/ only.

   Two jobs, one screen. For the host it is a launcher; for the room it is
   what is on the projector between videos. The only state it keeps is
   "what's next", and it keeps it in localStorage because only the host's
   browser is ever asked the question.
   ============================================================ */
(function () {
    'use strict';

    var VIDEOS = window.WOP_CHAT_VIDEOS || [];
    if (!VIDEOS.length) { return; }

    var KEY = 'wop-chat-next';

    function byNn(nn) {
        for (var i = 0; i < VIDEOS.length; i++) { if (VIDEOS[i].nn === nn) { return VIDEOS[i]; } }
        return null;
    }

    function mmss(s) {
        s = Math.max(0, Math.round(Number(s) || 0));
        return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }

    function readNext() {
        try {
            var v = byNn(window.localStorage.getItem(KEY));
            if (v) { return v; }
        } catch (_) {}
        // Nothing set, or storage unavailable: the slot shows the first video,
        // so the screen is never blank and the host can always just press Open.
        return VIDEOS[0];
    }

    function one(hook) { return document.querySelector('[data-chat-next="' + hook + '"]'); }

    function paintNext(v) {
        var title = one('title'), label = one('label'), time = one('time'),
            open = one('open'), bannerBox = one('banner');

        if (title) { title.textContent = v.title; }
        if (label) {
            label.textContent = v.label || ('Article ' + v.n);
            label.hidden = false;
        }
        if (time) {
            // Match the card: a film shown in part names the part it will play.
            time.textContent = (v.parts && v.parts[0] && v.parts[0].end)
                ? (mmss(v.parts[0].end) + ' · ' + v.parts[0].label + ' (' + mmss(v.duration_s) + ' full)')
                : mmss(v.duration_s);
        }
        if (open) {
            open.setAttribute('href', v.href);
            open.textContent = 'Open';
        }

        // The banner is cloned from the matching card rather than re-built, so
        // the slot uses the same srcset the card already loaded — no second
        // fetch, and one definition of the image markup (macros/banner.njk).
        if (bannerBox) {
            var card = document.querySelector('[data-chat-card="' + v.nn + '"] .chat-card-banner');
            bannerBox.textContent = '';
            if (card) {
                var clone = card.cloneNode(true);
                clone.classList.remove('chat-card-banner');
                clone.classList.add('chat-next-figure');
                bannerBox.appendChild(clone);
            }
        }

        [].forEach.call(document.querySelectorAll('[data-chat-card]'), function (li) {
            li.classList.toggle('chat-card--next', li.getAttribute('data-chat-card') === v.nn);
        });
    }

    [].forEach.call(document.querySelectorAll('[data-chat-setnext]'), function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var nn = btn.getAttribute('data-chat-setnext');
            var v = byNn(nn);
            if (!v) { return; }
            try { window.localStorage.setItem(KEY, nn); } catch (_) {}
            paintNext(v);
        });
    });

    paintNext(readNext());
}());
