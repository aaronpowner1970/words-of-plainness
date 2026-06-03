/* ============================================================
   ARTICLE STUDY SLIDES — Articles of Interfaith Discipleship
   Per-article "Slides" button → in-page carousel modal.

   - Injects a "Slides" trigger beside each article's "Listen" button
     (only for articles that have a slide set defined below)
   - One shared modal; Fullscreen-capable for group/VR projection
   - Slide types: title | points | concept | scripture | discuss | doorway

   ADDING ARTICLES: append a key (e.g. "A02") to WOP_ARTICLE_SLIDES.
   Article id is derived from each section's data-audio (AP_A##_...).
   (Prototype ships Article 1 only.)
   ============================================================ */

(function () {
    'use strict';

    var SCRIPTURE_BASE = 'https://www.churchofjesuschrist.org/study/scriptures/';

    /* ── Slide data ──────────────────────────────────────────── */

    /* Data lives in articles-slides-data.js (window.WOP_ARTICLE_SLIDES).
       That file must be loaded BEFORE this viewer in articles.njk. */
    var WOP_ARTICLE_SLIDES = (typeof window !== 'undefined' && window.WOP_ARTICLE_SLIDES) || {};

    var DATA = WOP_ARTICLE_SLIDES;

    /* ── Small HTML escaper for authored text fields ─────────── */

    function esc(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    /* ── Slide renderers by type ─────────────────────────────── */

    function slideHTML(s) {
        switch (s.type) {
            case 'title':
                return '<div class="as-slide as-slide--title">'
                    + '<p class="as-number">' + esc(s.number) + '</p>'
                    + '<h2 class="as-title">' + esc(s.title) + '</h2>'
                    + (s.lead ? '<p class="as-lead">' + esc(s.lead) + '</p>' : '')
                    + '</div>';

            case 'points':
                return '<div class="as-slide as-slide--points">'
                    + (s.heading ? '<p class="as-heading">' + esc(s.heading) + '</p>' : '')
                    + '<ul class="as-points">'
                    + s.items.map(function (i) { return '<li>' + esc(i) + '</li>'; }).join('')
                    + '</ul>'
                    + '</div>';

            case 'concept':
                return '<div class="as-slide as-slide--concept">'
                    + (s.label ? '<p class="as-heading">' + esc(s.label) + '</p>' : '')
                    + '<p class="as-term">' + esc(s.term) + '</p>'
                    + '<p class="as-def">' + esc(s.def) + '</p>'
                    + (s.sub ? '<p class="as-sub">' + esc(s.sub) + '</p>' : '')
                    + '</div>';

            case 'scripture':
                return '<div class="as-slide as-slide--scripture">'
                    + (s.label ? '<p class="as-heading">' + esc(s.label) + '</p>' : '')
                    + s.verses.map(function (v) {
                        return '<div class="as-verse">'
                            + '<p class="as-verse-text">“' + esc(v.text) + '”</p>'
                            + '<p class="as-verse-ref"><a href="' + SCRIPTURE_BASE + v.url + '" target="_blank" rel="noopener">' + esc(v.ref) + '</a></p>'
                            + '</div>';
                    }).join('')
                    + '</div>';

            case 'discuss':
                return '<div class="as-slide as-slide--discuss">'
                    + (s.label ? '<p class="as-heading">' + esc(s.label) + '</p>' : '')
                    + s.questions.map(function (q) {
                        return '<div class="as-q">'
                            + '<span class="as-q-tag">' + esc(q.tag) + '</span>'
                            + '<p class="as-q-text">' + esc(q.text) + '</p>'
                            + '</div>';
                    }).join('')
                    + '</div>';

            case 'doorway':
                return '<div class="as-slide as-slide--doorway">'
                    + (s.label ? '<p class="as-heading">' + esc(s.label) + '</p>' : '')
                    + '<h2 class="as-doorway-title">' + esc(s.title) + '</h2>'
                    + (s.blurb ? '<p class="as-doorway-blurb">' + esc(s.blurb) + '</p>' : '')
                    + '<a class="as-doorway-link" href="' + s.href + '" target="_blank" rel="noopener">Read the essay ↗</a>'
                    + '</div>';

            default:
                return '';
        }
    }

    /* ── Build shared modal ──────────────────────────────────── */

    var backdrop = document.createElement('div');
    backdrop.className = 'as-backdrop';
    backdrop.setAttribute('aria-hidden', 'true');

    var modal = document.createElement('div');
    modal.className = 'as-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Study slides');
    modal.setAttribute('aria-hidden', 'true');
    modal.setAttribute('tabindex', '-1');
    modal.innerHTML =
        '<div class="as-bar">'
            + '<span class="as-eyebrow"></span>'
            + '<div class="as-bar-actions">'
                + '<button class="as-notes" type="button" aria-label="Facilitator notes" aria-pressed="false">'
                    + '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        + '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                        + '<polyline points="14 2 14 8 20 8"/>'
                        + '<line x1="8" y1="13" x2="16" y2="13"/>'
                        + '<line x1="8" y1="17" x2="16" y2="17"/>'
                    + '</svg>'
                + '</button>'
                + '<button class="as-fullscreen" type="button" aria-label="Toggle fullscreen">'
                    + '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        + '<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/>'
                    + '</svg>'
                + '</button>'
                + '<button class="as-close" type="button" aria-label="Close slides">'
                    + '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
                        + '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
                    + '</svg>'
                + '</button>'
            + '</div>'
        + '</div>'
        + '<div class="as-stage-host">'
            + '<div class="as-stage"></div>'
            + '<aside class="as-facilitator" aria-hidden="true"></aside>'
        + '</div>'
        + '<div class="as-controls">'
            + '<button class="as-prev" type="button" aria-label="Previous slide">‹</button>'
            + '<div class="as-dots"></div>'
            + '<span class="as-counter"></span>'
            + '<button class="as-next" type="button" aria-label="Next slide">›</button>'
        + '</div>';

    document.body.appendChild(backdrop);
    document.body.appendChild(modal);

    var eyebrowEl = modal.querySelector('.as-eyebrow');
    var stageEl   = modal.querySelector('.as-stage');
    var dotsEl    = modal.querySelector('.as-dots');
    var counterEl = modal.querySelector('.as-counter');
    var prevBtn   = modal.querySelector('.as-prev');
    var nextBtn   = modal.querySelector('.as-next');
    var fsBtn     = modal.querySelector('.as-fullscreen');
    var closeBtn  = modal.querySelector('.as-close');
    var notesBtn  = modal.querySelector('.as-notes');
    var facEl     = modal.querySelector('.as-facilitator');

    var current = null;   // { slides: [...], idx: 0 }

    /* ── Render ──────────────────────────────────────────────── */

    function render() {
        if (!current) return;
        var slides = current.slides;
        var idx = current.idx;

        stageEl.innerHTML = slideHTML(slides[idx]);

        var dots = dotsEl.querySelectorAll('.as-dot');
        dots.forEach(function (d, i) { d.classList.toggle('active', i === idx); });

        counterEl.textContent = (idx + 1) + ' / ' + slides.length;
        prevBtn.disabled = (idx === 0);
        nextBtn.disabled = (idx === slides.length - 1);
    }

    function buildDots(n) {
        dotsEl.innerHTML = '';
        for (var i = 0; i < n; i++) {
            var dot = document.createElement('button');
            dot.className = 'as-dot';
            dot.type = 'button';
            dot.setAttribute('aria-label', 'Slide ' + (i + 1));
            (function (target) {
                dot.addEventListener('click', function () {
                    current.idx = target;
                    render();
                });
            })(i);
            dotsEl.appendChild(dot);
        }
    }

    function nav(delta) {
        if (!current) return;
        var next = current.idx + delta;
        if (next < 0 || next > current.slides.length - 1) return;
        current.idx = next;
        render();
    }


    /* ── Facilitator notes panel ─────────────────────── */

    function renderFacilitator(fac) {
        if (!fac) { facEl.innerHTML = ''; notesBtn.style.display = 'none'; return; }
        notesBtn.style.display = '';
        var html = '<div class="as-fac-inner">'
            + '<header class="as-fac-header">'
                + '<span class="as-fac-eyebrow">Facilitator Notes</span>'
                + '<button class="as-fac-close-x" type="button" aria-label="Close facilitator notes">'
                    + '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
                        + '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
                    + '</svg>'
                + '</button>'
            + '</header>'
            + '<div class="as-fac-body">';
        if (fac.intro) {
            html += '<p class="as-fac-intro">' + esc(fac.intro) + '</p>';
        }
        if (fac.scriptureExamples && fac.scriptureExamples.length) {
            html += '<section class="as-fac-block">'
                + '<h4 class="as-fac-h4">Scripture echoes</h4>'
                + '<ul class="as-fac-list">'
                + fac.scriptureExamples.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('')
                + '</ul>'
                + '</section>';
        }
        if (fac.liveExamples && fac.liveExamples.length) {
            html += '<section class="as-fac-block">'
                + '<h4 class="as-fac-h4">Live disagreements</h4>'
                + '<ul class="as-fac-list">'
                + fac.liveExamples.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('')
                + '</ul>'
                + '</section>';
        }
        if (fac.frame) {
            html += '<section class="as-fac-block">'
                + '<h4 class="as-fac-h4">The frame</h4>'
                + '<p class="as-fac-frame">' + esc(fac.frame) + '</p>'
                + '</section>';
        }
        if (fac.probe) {
            html += '<section class="as-fac-block as-fac-probe-block">'
                + '<span class="as-fac-leader-tag">Leader-only</span>'
                + '<p class="as-fac-probe">' + esc(fac.probe) + '</p>'
                + '</section>';
        }
        html += '</div></div>';
        facEl.innerHTML = html;
        facEl.querySelector('.as-fac-close-x').addEventListener('click', closeFacilitator);
    }

    function openFacilitator() {
        facEl.classList.add('open');
        facEl.setAttribute('aria-hidden', 'false');
        notesBtn.classList.add('active');
        notesBtn.setAttribute('aria-pressed', 'true');
    }

    function closeFacilitator() {
        facEl.classList.remove('open');
        facEl.setAttribute('aria-hidden', 'true');
        notesBtn.classList.remove('active');
        notesBtn.setAttribute('aria-pressed', 'false');
    }

    function toggleFacilitator() {
        if (facEl.classList.contains('open')) closeFacilitator();
        else openFacilitator();
    }

    /* ── Open / close ────────────────────────────────────────── */

    function openSlides(articleId) {
        var data = DATA[articleId];
        if (!data) return;
        current = { slides: data.slides, idx: 0 };
        eyebrowEl.textContent = data.eyebrow || '';
        buildDots(data.slides.length);
        render();
        renderFacilitator(data.facilitator || null);
        closeFacilitator();
        backdrop.classList.add('open');
        modal.classList.add('open');
        backdrop.setAttribute('aria-hidden', 'false');
        modal.setAttribute('aria-hidden', 'false');
        // Close any open Learning Tools dropdowns
        var dd1 = document.getElementById('featuresDropdown');
        var dd2 = document.getElementById('bottomFeaturesDropdown');
        if (dd1) dd1.classList.remove('open');
        if (dd2) dd2.classList.remove('open');
        modal.focus();
    }

    function closeSlides() {
        closeFacilitator();
        if (document.fullscreenElement || document.webkitFullscreenElement) {
            (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        }
        backdrop.classList.remove('open');
        modal.classList.remove('open');
        backdrop.setAttribute('aria-hidden', 'true');
        modal.setAttribute('aria-hidden', 'true');
    }

    function toggleFullscreen() {
        var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
        if (!fsEl) {
            var req = modal.requestFullscreen || modal.webkitRequestFullscreen;
            if (req) req.call(modal);
        } else {
            (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        }
    }

    /* ── Wire modal controls ─────────────────────────────────── */

    prevBtn.addEventListener('click', function () { nav(-1); });
    nextBtn.addEventListener('click', function () { nav(1); });
    fsBtn.addEventListener('click', toggleFullscreen);
    closeBtn.addEventListener('click', closeSlides);
    backdrop.addEventListener('click', closeSlides);
    notesBtn.addEventListener('click', toggleFacilitator);

    // Auto-close facilitator panel when entering fullscreen
    function onFsChange() {
        var fs = document.fullscreenElement || document.webkitFullscreenElement;
        if (fs && facEl.classList.contains('open')) {
            closeFacilitator();
        }
    }
    document.addEventListener('fullscreenchange', onFsChange);
    document.addEventListener('webkitfullscreenchange', onFsChange);

    document.addEventListener('keydown', function (e) {
        if (!modal.classList.contains('open')) return;
        if (e.key === 'ArrowRight') { nav(1); }
        else if (e.key === 'ArrowLeft') { nav(-1); }
        else if (e.key === 'Escape' || e.key === 'Esc') {
            if (document.fullscreenElement || document.webkitFullscreenElement) {
                (document.exitFullscreen || document.webkitExitFullscreen).call(document);
            } else if (facEl.classList.contains('open')) {
                closeFacilitator();
            } else {
                closeSlides();
            }
        }
    });

    /* ── Inject "Slides" buttons beside each "Listen" button ──── */

    var sections = document.querySelectorAll('.article-section[data-audio]');

    sections.forEach(function (section) {
        var match = /AP_(A\d{2})_/.exec(section.dataset.audio || '');
        if (!match) return;
        var articleId = match[1];
        if (!DATA[articleId]) return;   // only render where a slide set exists

        var titleEl = section.querySelector('.article-title');
        var titleText = titleEl ? titleEl.textContent.trim() : 'this article';

        var btn = document.createElement('button');
        btn.className = 'article-slides-btn';
        btn.type = 'button';
        btn.setAttribute('aria-label', 'Open study slides for ' + titleText);
        btn.dataset.article = articleId;
        btn.innerHTML =
            '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                + '<rect x="2" y="3" width="20" height="14" rx="2"></rect>'
                + '<line x1="8" y1="21" x2="16" y2="21"></line>'
                + '<line x1="12" y1="17" x2="12" y2="21"></line>'
            + '</svg>'
            + '<span class="asb-label">Slides</span>';

        var listenBtn = section.querySelector('.article-read-aloud-btn');
        if (listenBtn) {
            listenBtn.insertAdjacentElement('afterend', btn);
        } else if (titleEl) {
            var next = titleEl.nextElementSibling;
            if (next) { section.insertBefore(btn, next); } else { section.appendChild(btn); }
        }

        btn.addEventListener('click', function () { openSlides(articleId); });
    });

})();
