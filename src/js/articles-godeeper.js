/* ============================================================
   GO-DEEPER PANEL — Articles of Interfaith Discipleship
   Per-article inline "Go deeper" disclosure with three tabs:
     • Related chapters    (theme-overlap, from window.WOP_GODEEPER)
     • Musical testimonies (testimonies among the related chapters)
     • Search this theme   (→ /search/?q=<searchSeed>)

   DATA (injected in articles.njk by the goDeeperData filter in
   .eleventy.js — recomputed every build, nothing hand-maintained):

     window.WOP_GODEEPER[sectionId] = {
       themes:     [slug, ...],
       searchSeed: "…",
       chapters:   [{ title, description, url, scripture }, ...],
       music:      [{ title, file, label, duration, chapter, url }, ...]
     }

   Mirrors the articles-slides.js injector pattern: read a global,
   iterate .article-section, inject per section. Keyed by section.id
   (e.g. "of-plainness"), which matches the WOP_GODEEPER keys.
   ============================================================ */

(function () {
    'use strict';

    var DATA = (typeof window !== 'undefined' && window.WOP_GODEEPER) || {};
    if (!DATA || !Object.keys(DATA).length) { return; }

    function esc(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /* ── Pane renderers ──────────────────────────────────────── */

    function chaptersPaneHTML(chapters) {
        if (!chapters || !chapters.length) {
            return '<p class="gd-empty">No related chapters yet.</p>';
        }
        return '<ul class="gd-list">' + chapters.map(function (c) {
            return '<li class="gd-item">'
                + '<a class="gd-item-link" href="' + esc(c.url) + '">'
                    + '<span class="gd-item-title">'
                        + (c.chapter ? '<span class="gd-item-num">' + esc(c.chapter) + '</span>' : '')
                        + esc(c.title)
                    + '</span>'
                    + (c.scripture ? '<span class="gd-item-meta">' + esc(c.scripture) + '</span>' : '')
                + '</a>'
                + (c.description ? '<p class="gd-item-desc">' + esc(c.description) + '</p>' : '')
            + '</li>';
        }).join('') + '</ul>';
    }

    function musicPaneHTML(music) {
        if (!music || !music.length) {
            return '<p class="gd-empty">No musical testimony yet for these themes.</p>';
        }
        var items = music.map(function (m) {
            var meta = [m.label, m.duration].filter(Boolean).map(esc).join(' \u00b7 ');
            return '<li class="gd-item gd-item--music">'
                + '<button type="button" class="gd-item-link gd-item-play" data-play-file="' + esc(m.file) + '" aria-label="Play ' + esc(m.title) + '">'
                    + '<span class="gd-music-icon" aria-hidden="true">'
                        + '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" stroke="none"><polygon points="6 4 20 12 6 20"/></svg>'
                    + '</span>'
                    + '<span class="gd-music-body">'
                        + '<span class="gd-item-title">' + esc(m.title) + '</span>'
                        + (meta ? '<span class="gd-item-meta">' + meta + '</span>' : '')
                    + '</span>'
                + '</button>'
            + '</li>';
        }).join('');
        return '<ul class="gd-list gd-list--music">' + items + '</ul>'
            + '<p class="gd-music-foot"><a href="/music/">Hear the full collection \u2192</a></p>';
    }

    function searchPaneHTML(seed) {
        var q = seed || '';
        return '<p class="gd-search-lead">Explore everywhere this theme appears across the writings \u2014 opens in a new tab, so you keep your place here.</p>'
            + '<a class="gd-search-btn" href="/search/?q=' + encodeURIComponent(q) + '" target="_blank" rel="noopener">'
                + '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
                + '<span>Search the library' + (q ? ' for &ldquo;' + esc(q) + '&rdquo;' : '') + '</span>'
                + '<svg class="gd-search-ext" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7"/><path d="M9 7h8v8"/></svg>'
            + '</a>';
    }

    /* ── Block builder ───────────────────────────────────────── */

    function scentLine(d) {
        var parts = [];
        var nc = (d.chapters && d.chapters.length) || 0;
        if (nc) { parts.push(nc + ' related chapter' + (nc === 1 ? '' : 's')); }
        var nm = (d.music && d.music.length) || 0;
        if (nm) { parts.push(nm + ' testimon' + (nm === 1 ? 'y' : 'ies')); }
        parts.push('search');
        return parts.join(' \u00b7 ');
    }

    function buildBlock(sectionId, d) {
        var block = document.createElement('div');
        block.className = 'gd-block';
        block.setAttribute('data-gd', sectionId);
        var scent = scentLine(d);
        block.innerHTML =
            '<button class="gd-toggle" type="button" aria-expanded="false">'
                + '<span class="gd-toggle-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/></svg></span>'
                + '<span class="gd-toggle-text">'
                    + '<span class="gd-toggle-label">Go deeper into these themes</span>'
                    + '<span class="gd-toggle-scent">' + esc(scent) + '</span>'
                + '</span>'
                + '<svg class="gd-toggle-chevron" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>'
            + '</button>'
            + '<div class="gd-body" hidden>'
                + '<div class="gd-tabs" role="tablist" aria-label="Go deeper">'
                    + '<button class="gd-tab gd-tab--active" type="button" role="tab" aria-selected="true" data-gd-pane="chapters">Related chapters</button>'
                    + '<button class="gd-tab" type="button" role="tab" aria-selected="false" data-gd-pane="music">Musical testimonies</button>'
                    + '<button class="gd-tab" type="button" role="tab" aria-selected="false" data-gd-pane="search">Search this theme</button>'
                + '</div>'
                + '<div class="gd-pane" role="tabpanel" data-gd-pane="chapters">' + chaptersPaneHTML(d.chapters) + '</div>'
                + '<div class="gd-pane gd-hidden" role="tabpanel" data-gd-pane="music">' + musicPaneHTML(d.music) + '</div>'
                + '<div class="gd-pane gd-hidden" role="tabpanel" data-gd-pane="search">' + searchPaneHTML(d.searchSeed) + '</div>'
            + '</div>';
        return block;
    }

    function wireBlock(block) {
        var toggle = block.querySelector('.gd-toggle');
        var body   = block.querySelector('.gd-body');
        var tabs   = block.querySelectorAll('.gd-tab');
        var panes  = block.querySelectorAll('.gd-pane');

        toggle.addEventListener('click', function () {
            var open = block.classList.toggle('gd-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            body.hidden = !open;
        });

        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                var key = tab.getAttribute('data-gd-pane');
                tabs.forEach(function (t) {
                    var active = (t === tab);
                    t.classList.toggle('gd-tab--active', active);
                    t.setAttribute('aria-selected', active ? 'true' : 'false');
                });
                panes.forEach(function (p) {
                    p.classList.toggle('gd-hidden', p.getAttribute('data-gd-pane') !== key);
                });
            });
        });

        // Testimony rows trigger the singleton mini-player instead of
        // navigating to the chapter (defect fix — readers used to land
        // lost on the chapter page with the audio hidden behind a pill).
        block.querySelectorAll('[data-play-file]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var file = btn.getAttribute('data-play-file');
                if (file && window.WopPlayer) window.WopPlayer.play(file);
            });
        });
    }

    /* ── Inject one block at the end of each themed article ──── */

    function init() {
        var sections = document.querySelectorAll('.article-section');
        sections.forEach(function (section) {
            var id = section.id;
            if (!id || !DATA[id]) { return; }
            if (section.querySelector('.gd-block')) { return; }  // idempotent
            var block = buildBlock(id, DATA[id]);
            var body = section.querySelector('.article-body');
            if (body) { body.appendChild(block); }
            else { section.appendChild(block); }
            wireBlock(block);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
