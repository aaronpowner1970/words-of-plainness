/**
 * WORDS OF PLAINNESS — Singleton Mini-Player
 * ==========================================
 * One sticky footer bar + lyrics drawer, one <audio> element. Any page
 * that triggers playback (Articles "Musical testimonies", chapter-page
 * Musical Testimony pill) calls WopPlayer.play(fileOrDescriptor). The
 * bar auto-hides until first play; volume persists via localStorage.
 *
 * Catalog: reads window.WOP_MUSIC_CATALOG (built by the musicCatalog
 * Eleventy filter). Descriptor keys used: file, audioUrl, title, style,
 * duration, lyricsUrl (optional WebVTT), lyricsHtml (formatted static
 * fallback). Passing just a file string looks it up in the catalog.
 *
 * Lyrics drawer is a progressive enhancement:
 *   • lyricsUrl set  → <track kind="metadata"> + cuechange highlights
 *                      and auto-scrolls the active line to center
 *                      (skipped when prefers-reduced-motion).
 *   • lyricsUrl null → renders lyricsHtml statically.
 */
(function () {
    'use strict';

    var VOLUME_KEY = 'wop-music-volume';

    var P = {
        audio: null,
        root: null,
        els: {},
        currentFile: null,
        currentDesc: null,
        vttTrackEl: null,
        vttLines: [],       // array of {el, cue}
        activeLineEl: null,
        loadToken: 0,
        prefersReducedMotion: false,
        initialized: false,

        // Public API — resolve a file id or descriptor and start playback.
        play: function (arg) {
            if (!this.initialized) this.init();
            var desc = this.resolve(arg);
            if (!desc || !desc.audioUrl) return;

            if (this.currentFile === desc.file && this.audio.src) {
                this.togglePlay();
                return;
            }

            this.loadToken++;
            var thisToken = this.loadToken;

            this.currentFile = desc.file;
            this.currentDesc = desc;

            this.audio.pause();
            this.detachVttTrack();
            this.audio.src = desc.audioUrl;
            this.updateMeta(desc);
            this.attachLyrics(desc);
            this.showBar();
            this.setPlayIcon(false);
            this.els.btnPlay.classList.add('wp-loading');

            var self = this;
            this.audio.play().catch(function (err) {
                if (thisToken !== self.loadToken) return;         // superseded
                if (err && (err.name === 'AbortError' ||
                            err.name === 'NotAllowedError')) return;
                self.els.btnPlay.classList.remove('wp-loading');
                console.warn('WopPlayer: play failed —', err && err.message);
            });
        },

        resolve: function (arg) {
            if (!arg) return null;
            if (typeof arg === 'string') {
                var cat = window.WOP_MUSIC_CATALOG || {};
                return cat[arg] || null;
            }
            // Descriptor object; ensure audioUrl fallback from file
            if (!arg.audioUrl && arg.file) {
                arg.audioUrl = 'https://media.wordsofplainness.org/web/' + arg.file;
            }
            return arg;
        },

        init: function () {
            if (this.initialized) return;
            this.initialized = true;
            this.prefersReducedMotion = window.matchMedia &&
                window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            this.buildDom();
            this.bindEvents();
            this.loadVolume();
        },

        buildDom: function () {
            var root = document.createElement('div');
            root.id = 'wopPlayer';
            root.className = 'wp';
            root.setAttribute('hidden', '');
            root.innerHTML = [
                '<div class="wp-bar" role="region" aria-label="Music player">',
                    '<button class="wp-btn wp-play" type="button" aria-label="Play/Pause">',
                        '<svg class="wp-icon-play" viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><polygon points="5 3 20 12 5 21"/></svg>',
                        '<svg class="wp-icon-pause" viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true" style="display:none"><rect x="5" y="3" width="4" height="18"/><rect x="15" y="3" width="4" height="18"/></svg>',
                    '</button>',
                    '<div class="wp-meta">',
                        '<div class="wp-title" aria-live="polite">—</div>',
                        '<div class="wp-style"></div>',
                    '</div>',
                    '<div class="wp-scrub">',
                        '<span class="wp-time wp-time-cur">0:00</span>',
                        '<input type="range" class="wp-progress" min="0" max="1000" value="0" step="1" aria-label="Seek">',
                        '<span class="wp-time wp-time-tot">0:00</span>',
                    '</div>',
                    '<div class="wp-vol">',
                        '<button class="wp-btn wp-mute" type="button" aria-label="Toggle mute">',
                            '<svg class="wp-icon-vol" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
                            '<svg class="wp-icon-mute" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" style="display:none"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>',
                        '</button>',
                        '<input type="range" class="wp-volume" min="0" max="100" value="80" aria-label="Volume">',
                    '</div>',
                    '<button class="wp-btn wp-lyrics-toggle" type="button" aria-expanded="false" aria-controls="wopDrawer">',
                        '<span>Lyrics</span>',
                        '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 15 12 9 18 15"/></svg>',
                    '</button>',
                    '<button class="wp-btn wp-close" type="button" aria-label="Close player">',
                        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
                    '</button>',
                    '<audio class="wp-audio" preload="none"></audio>',
                '</div>',
                '<div class="wp-drawer" id="wopDrawer" hidden>',
                    '<div class="wp-drawer-inner">',
                        '<div class="wp-drawer-body" aria-live="off"></div>',
                    '</div>',
                '</div>'
            ].join('');
            document.body.appendChild(root);

            this.root = root;
            this.audio = root.querySelector('.wp-audio');
            this.els = {
                bar:          root.querySelector('.wp-bar'),
                btnPlay:      root.querySelector('.wp-play'),
                iconPlay:     root.querySelector('.wp-icon-play'),
                iconPause:    root.querySelector('.wp-icon-pause'),
                title:        root.querySelector('.wp-title'),
                style:        root.querySelector('.wp-style'),
                timeCur:      root.querySelector('.wp-time-cur'),
                timeTot:      root.querySelector('.wp-time-tot'),
                progress:     root.querySelector('.wp-progress'),
                btnMute:      root.querySelector('.wp-mute'),
                iconVol:      root.querySelector('.wp-icon-vol'),
                iconMute:     root.querySelector('.wp-icon-mute'),
                volume:       root.querySelector('.wp-volume'),
                btnLyrics:    root.querySelector('.wp-lyrics-toggle'),
                btnClose:     root.querySelector('.wp-close'),
                drawer:       root.querySelector('.wp-drawer'),
                drawerBody:   root.querySelector('.wp-drawer-body')
            };
        },

        bindEvents: function () {
            var self = this, a = this.audio;

            a.addEventListener('play',           function () { self.setPlayIcon(true); self.els.btnPlay.classList.remove('wp-loading'); });
            a.addEventListener('pause',          function () { self.setPlayIcon(false); });
            a.addEventListener('loadedmetadata', function () { self.els.timeTot.textContent = fmt(a.duration); });
            a.addEventListener('timeupdate',     function () { self.onTimeUpdate(); });
            a.addEventListener('ended',          function () { self.onEnded(); });
            a.addEventListener('error', function () {
                self.els.btnPlay.classList.remove('wp-loading');
                console.warn('WopPlayer: audio error', a.error);
            });

            this.els.btnPlay.addEventListener('click',   function () { self.togglePlay(); });
            this.els.btnClose.addEventListener('click',  function () { self.stopAndHide(); });
            this.els.btnLyrics.addEventListener('click', function () { self.toggleDrawer(); });

            this.els.progress.addEventListener('input', function (e) {
                if (!a.duration) return;
                a.currentTime = (parseFloat(e.target.value) / 1000) * a.duration;
            });

            this.els.volume.addEventListener('input', function (e) {
                var v = parseInt(e.target.value, 10);
                a.volume = v / 100;
                a.muted = false;
                try { localStorage.setItem(VOLUME_KEY, String(v)); } catch (_) {}
                self.updateMuteIcon();
            });

            this.els.btnMute.addEventListener('click', function () {
                a.muted = !a.muted;
                self.updateMuteIcon();
            });

            // Keyboard: space toggles playback while the bar is visible and
            // focus isn't in a text field.
            document.addEventListener('keydown', function (e) {
                if (self.root.hasAttribute('hidden')) return;
                var t = e.target;
                if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
                if (e.code === 'Space') {
                    e.preventDefault();
                    self.togglePlay();
                }
            });
        },

        togglePlay: function () {
            if (!this.audio.src) return;
            if (this.audio.paused) {
                this.audio.play().catch(function () {});
            } else {
                this.audio.pause();
            }
        },

        onTimeUpdate: function () {
            var a = this.audio;
            this.els.timeCur.textContent = fmt(a.currentTime);
            if (a.duration) {
                this.els.progress.value = String((a.currentTime / a.duration) * 1000);
            }
        },

        onEnded: function () {
            this.setPlayIcon(false);
            this.els.progress.value = '0';
            this.els.timeCur.textContent = '0:00';
            this.clearActiveLine();
        },

        setPlayIcon: function (isPlaying) {
            this.els.iconPlay.style.display  = isPlaying ? 'none' : '';
            this.els.iconPause.style.display = isPlaying ? '' : 'none';
            this.els.btnPlay.setAttribute('aria-label', isPlaying ? 'Pause' : 'Play');
        },

        updateMeta: function (desc) {
            this.els.title.textContent = desc.title || '';
            var style = desc.style || '';
            if (!desc.isMinistry && desc.chapter) {
                style = (style ? style + ' · ' : '') + 'Chapter ' + desc.chapter;
            }
            this.els.style.textContent = style;
        },

        updateMuteIcon: function () {
            var muted = this.audio.muted || this.audio.volume === 0;
            this.els.iconVol.style.display  = muted ? 'none' : '';
            this.els.iconMute.style.display = muted ? '' : 'none';
        },

        loadVolume: function () {
            var raw;
            try { raw = localStorage.getItem(VOLUME_KEY); } catch (_) { raw = null; }
            var v = raw == null ? 80 : parseInt(raw, 10);
            if (isNaN(v)) v = 80;
            this.audio.volume = v / 100;
            this.els.volume.value = String(v);
            this.updateMuteIcon();
        },

        showBar: function () {
            if (this.root.hasAttribute('hidden')) {
                this.root.removeAttribute('hidden');
                document.body.classList.add('wp-visible');
            }
        },

        stopAndHide: function () {
            this.audio.pause();
            this.audio.removeAttribute('src');
            try { this.audio.load(); } catch (_) {}
            this.detachVttTrack();
            this.clearActiveLine();
            this.els.drawerBody.innerHTML = '';
            this.closeDrawer();
            this.currentFile = null;
            this.currentDesc = null;
            this.root.setAttribute('hidden', '');
            document.body.classList.remove('wp-visible');
            this.setPlayIcon(false);
        },

        // ── Lyrics ──────────────────────────────────────────────

        toggleDrawer: function () {
            if (this.els.drawer.hasAttribute('hidden')) this.openDrawer();
            else this.closeDrawer();
        },

        openDrawer: function () {
            this.els.drawer.removeAttribute('hidden');
            this.els.btnLyrics.setAttribute('aria-expanded', 'true');
            this.root.classList.add('wp-drawer-open');
            // Scroll the currently-active line into center on open.
            if (this.activeLineEl) this.scrollLineIntoView(this.activeLineEl);
        },

        closeDrawer: function () {
            this.els.drawer.setAttribute('hidden', '');
            this.els.btnLyrics.setAttribute('aria-expanded', 'false');
            this.root.classList.remove('wp-drawer-open');
        },

        attachLyrics: function (desc) {
            this.els.drawerBody.innerHTML = '';
            this.vttLines = [];
            this.activeLineEl = null;

            if (desc.lyricsUrl) {
                this.attachVttTrack(desc.lyricsUrl);
            } else if (desc.lyricsHtml) {
                var wrap = document.createElement('div');
                wrap.className = 'wp-static-lyrics';
                wrap.innerHTML = desc.lyricsHtml;
                this.els.drawerBody.appendChild(wrap);
            } else {
                var empty = document.createElement('p');
                empty.className = 'wp-lyrics-empty';
                empty.textContent = 'Lyrics not available for this testimony.';
                this.els.drawerBody.appendChild(empty);
            }
        },

        attachVttTrack: function (vttUrl) {
            // <track> from a cross-origin URL requires the audio element to be
            // CORS-enabled AND the server to send the CORS headers. Set it
            // only when a VTT is present so the plain-mp3 path (Phase 1) is
            // never blocked by missing CORS on the CDN.
            this.audio.crossOrigin = 'anonymous';
            var t = document.createElement('track');
            t.kind = 'metadata';
            t.src = vttUrl;
            t.default = true;
            this.audio.appendChild(t);
            this.vttTrackEl = t;

            var self = this;
            t.addEventListener('load', function () {
                self.renderVttLines(t.track);
                if (t.track) t.track.mode = 'hidden'; // fires cuechange without rendering native captions
                if (t.track) {
                    t.track.addEventListener('cuechange', function () {
                        self.onCueChange(t.track);
                    });
                }
            });
            // Some browsers won't fire 'load' if src is empty/errors — no-op is fine.
        },

        renderVttLines: function (track) {
            if (!track || !track.cues) return;
            var body = this.els.drawerBody;
            body.innerHTML = '';
            var list = document.createElement('ol');
            list.className = 'wp-vtt-lines';
            for (var i = 0; i < track.cues.length; i++) {
                var cue = track.cues[i];
                var li = document.createElement('li');
                li.className = 'wp-vtt-line';
                li.textContent = cue.text;
                li.dataset.cueIndex = String(i);
                list.appendChild(li);
                this.vttLines.push({ el: li, cue: cue });
            }
            body.appendChild(list);
        },

        onCueChange: function (track) {
            var active = track.activeCues && track.activeCues[0];
            if (!active) return;
            for (var i = 0; i < this.vttLines.length; i++) {
                if (this.vttLines[i].cue === active) {
                    this.setActiveLine(this.vttLines[i].el);
                    return;
                }
            }
        },

        setActiveLine: function (el) {
            if (this.activeLineEl === el) return;
            if (this.activeLineEl) this.activeLineEl.classList.remove('wp-vtt-active');
            this.activeLineEl = el;
            el.classList.add('wp-vtt-active');
            if (!this.els.drawer.hasAttribute('hidden')) this.scrollLineIntoView(el);
        },

        scrollLineIntoView: function (el) {
            try {
                el.scrollIntoView({
                    behavior: this.prefersReducedMotion ? 'auto' : 'smooth',
                    block: 'center'
                });
            } catch (_) {
                el.scrollIntoView();
            }
        },

        clearActiveLine: function () {
            if (this.activeLineEl) this.activeLineEl.classList.remove('wp-vtt-active');
            this.activeLineEl = null;
        },

        detachVttTrack: function () {
            if (this.vttTrackEl && this.vttTrackEl.parentNode) {
                this.vttTrackEl.parentNode.removeChild(this.vttTrackEl);
            }
            this.vttTrackEl = null;
            this.vttLines = [];
            this.activeLineEl = null;
            // Drop CORS mode so the next plain-mp3 track loads without needing
            // the CDN to send Access-Control-Allow-Origin headers.
            this.audio.removeAttribute('crossorigin');
        }
    };

    function fmt(seconds) {
        if (!seconds || !isFinite(seconds)) return '0:00';
        var m = Math.floor(seconds / 60);
        var s = Math.floor(seconds % 60);
        return m + ':' + (s < 10 ? '0' + s : s);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { P.init(); });
    } else {
        P.init();
    }

    window.WopPlayer = P;
})();
