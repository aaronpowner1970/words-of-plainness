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
 *
 * Playlist mode (OPT-IN, /music/ only):
 *   Call WopPlayer.setQueue([...files]) to activate — reveals shuffle,
 *   prev/next, and repeat (off / all / one) transport buttons, enables
 *   auto-advance on 'ended', and skip-on-error. Single-track callers
 *   (/articles/, chapter pages) don't call setQueue and get the plain
 *   bar unchanged. Behavior ported from the legacy src/js/music-player.js.
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

        // Playlist mode (opt-in via setQueue). Ignored when queue is empty.
        queue: [],           // ordered file names
        queueIndex: -1,      // index of currentFile in queue, or -1 if off-queue
        shuffle: false,
        shuffleOrder: [],
        repeat: 'off',       // 'off' | 'all' | 'one'

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
            // In playlist mode, track the queue index so prev/next and
            // auto-advance work regardless of whether this play was triggered
            // by the transport or by a direct row click (including off-queue
            // rows like an alternate clicked while scope is Core Journey).
            this.queueIndex = this.queue.length ? this.queue.indexOf(desc.file) : -1;

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
                // Always clear the loading spinner — AbortError (superseded
                // load) and NotAllowedError (autoplay blocked) used to return
                // early leaving wp-loading stuck on the play button forever.
                self.els.btnPlay.classList.remove('wp-loading');
                if (err && err.name === 'AbortError') return;
                if (err && err.name === 'NotAllowedError') {
                    // Autoplay blocked (Safari/iOS/Firefox on deep-link entry
                    // and gesture-less plays). Leave the bar visible with the
                    // track loaded, arm the play button, and clear the arm on
                    // the first successful play (bound once in bindEvents).
                    self.root.classList.add('wp-armed');
                    return;
                }
                console.warn('WopPlayer: play failed —', err && err.message);
            });
        },

        // ── Playlist mode API (opt-in — /music/ activates; other pages don't) ──

        setQueue: function (files) {
            if (!this.initialized) this.init();
            this.queue = Array.isArray(files) ? files.slice() : [];
            // Recompute queueIndex against the new queue so the transport
            // handles the currently-playing track correctly if it's still in.
            this.queueIndex = this.currentFile ? this.queue.indexOf(this.currentFile) : -1;
            if (this.shuffle) this.generateShuffleOrder();
            this.root.classList.toggle('wp-playlist-mode', this.queue.length > 0);
        },

        clearQueue: function () {
            this.setQueue([]);
        },

        playlistMode: function () {
            return this.queue.length > 0;
        },

        playIndex: function (i) {
            if (i < 0 || i >= this.queue.length) return;
            this.play(this.queue[i]);
        },

        prev: function () {
            if (!this.playlistMode() || !this.queue.length) return;
            // Restart current if we're more than 3s in — familiar player behavior.
            if (this.audio.currentTime > 3) { this.audio.currentTime = 0; return; }
            var i = this.getAdjacentIndex(-1);
            if (i !== -1) this.playIndex(i);
        },

        next: function () {
            if (!this.playlistMode() || !this.queue.length) return;
            var i = this.getAdjacentIndex(1);
            if (i !== -1) this.playIndex(i);
        },

        getAdjacentIndex: function (direction) {
            var n = this.queue.length;
            if (!n) return -1;
            // If off-queue (queueIndex=-1), prev/next drops us into the queue
            // at the start (or end) instead of no-op.
            if (this.queueIndex === -1) {
                if (this.shuffle) return this.shuffleOrder[direction > 0 ? 0 : this.shuffleOrder.length - 1];
                return direction > 0 ? 0 : n - 1;
            }
            if (this.shuffle) {
                var pos = this.shuffleOrder.indexOf(this.queueIndex);
                var np = pos + direction;
                if (np >= 0 && np < this.shuffleOrder.length) return this.shuffleOrder[np];
                if (this.repeat === 'all') {
                    return direction > 0 ? this.shuffleOrder[0]
                                         : this.shuffleOrder[this.shuffleOrder.length - 1];
                }
                return -1;
            }
            var ni = this.queueIndex + direction;
            if (ni >= 0 && ni < n) return ni;
            if (this.repeat === 'all') return direction > 0 ? 0 : n - 1;
            return -1;
        },

        getNextAutoAdvance: function () {
            // Auto-advance never wraps on its own — end-of-list needs repeat=all
            // to reshuffle and restart. Off-queue direct plays fall through to
            // the start of the queue so the reader isn't stranded.
            if (!this.queue.length) return -1;
            if (this.queueIndex === -1) {
                return this.shuffle ? (this.shuffleOrder[0] || 0) : 0;
            }
            if (this.shuffle) {
                var pos = this.shuffleOrder.indexOf(this.queueIndex);
                var np = pos + 1;
                return np < this.shuffleOrder.length ? this.shuffleOrder[np] : -1;
            }
            var ni = this.queueIndex + 1;
            return ni < this.queue.length ? ni : -1;
        },

        toggleShuffle: function () {
            this.shuffle = !this.shuffle;
            this.els.btnShuffle.classList.toggle('wp-active', this.shuffle);
            this.els.btnShuffle.setAttribute('aria-pressed', this.shuffle ? 'true' : 'false');
            this.els.btnShuffle.title = 'Shuffle: ' + (this.shuffle ? 'On' : 'Off');
            if (this.shuffle) this.generateShuffleOrder();
            else this.shuffleOrder = [];
        },

        generateShuffleOrder: function () {
            // Fisher-Yates, ported from legacy music-player.js.
            var n = this.queue.length;
            this.shuffleOrder = [];
            for (var i = 0; i < n; i++) this.shuffleOrder.push(i);
            for (var j = n - 1; j > 0; j--) {
                var k = Math.floor(Math.random() * (j + 1));
                var tmp = this.shuffleOrder[j];
                this.shuffleOrder[j] = this.shuffleOrder[k];
                this.shuffleOrder[k] = tmp;
            }
        },

        toggleRepeat: function () {
            var modes = ['off', 'all', 'one'];
            var i = modes.indexOf(this.repeat);
            this.repeat = modes[(i + 1) % modes.length];
            var b = this.els.btnRepeat;
            b.classList.toggle('wp-active', this.repeat !== 'off');
            b.title = 'Repeat: ' + (this.repeat === 'off' ? 'Off'
                                   : this.repeat === 'all' ? 'All' : 'One');
            this.els.repeatBadge.style.display = this.repeat === 'one' ? 'block' : 'none';
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
                    // Transport (playlist mode only — hidden by CSS unless .wp has .wp-playlist-mode).
                    '<button class="wp-btn wp-tx wp-shuffle" type="button" title="Shuffle: Off" aria-label="Toggle shuffle" aria-pressed="false">',
                        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>',
                    '</button>',
                    '<button class="wp-btn wp-tx wp-prev" type="button" aria-label="Previous track">',
                        '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none" aria-hidden="true"><polygon points="19 20 9 12 19 4 19 20"/><rect x="4" y="4" width="2" height="16"/></svg>',
                    '</button>',
                    '<button class="wp-btn wp-play" type="button" aria-label="Play/Pause">',
                        '<svg class="wp-icon-play" viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><polygon points="5 3 20 12 5 21"/></svg>',
                        '<svg class="wp-icon-pause" viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true" style="display:none"><rect x="5" y="3" width="4" height="18"/><rect x="15" y="3" width="4" height="18"/></svg>',
                    '</button>',
                    '<button class="wp-btn wp-tx wp-next" type="button" aria-label="Next track">',
                        '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none" aria-hidden="true"><polygon points="5 4 15 12 5 20 5 4"/><rect x="18" y="4" width="2" height="16"/></svg>',
                    '</button>',
                    '<button class="wp-btn wp-tx wp-repeat" type="button" title="Repeat: Off" aria-label="Cycle repeat mode">',
                        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>',
                        '<span class="wp-repeat-badge" aria-hidden="true">1</span>',
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
                btnShuffle:   root.querySelector('.wp-shuffle'),
                btnPrev:      root.querySelector('.wp-prev'),
                btnPlay:      root.querySelector('.wp-play'),
                btnNext:      root.querySelector('.wp-next'),
                btnRepeat:    root.querySelector('.wp-repeat'),
                repeatBadge:  root.querySelector('.wp-repeat-badge'),
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

            a.addEventListener('play',           function () { self.setPlayIcon(true); self.els.btnPlay.classList.remove('wp-loading'); self.root.classList.remove('wp-armed'); });
            a.addEventListener('pause',          function () { self.setPlayIcon(false); });
            a.addEventListener('loadedmetadata', function () { self.els.timeTot.textContent = fmt(a.duration); });
            a.addEventListener('timeupdate',     function () { self.onTimeUpdate(); });
            a.addEventListener('ended',          function () { self.onEnded(); });
            a.addEventListener('error', function () {
                self.els.btnPlay.classList.remove('wp-loading');
                console.warn('WopPlayer: audio error', a.error);
                // Skip-on-error: in playlist mode, jump to the next track so a
                // single missing file doesn't stall the whole queue.
                if (self.playlistMode()) {
                    var nxt = self.getNextAutoAdvance();
                    if (nxt !== -1) setTimeout(function () { self.playIndex(nxt); }, 400);
                }
            });

            this.els.btnPlay.addEventListener('click',    function () { self.togglePlay(); });
            this.els.btnClose.addEventListener('click',   function () { self.stopAndHide(); });
            this.els.btnLyrics.addEventListener('click',  function () { self.toggleDrawer(); });
            this.els.btnPrev.addEventListener('click',    function () { self.prev(); });
            this.els.btnNext.addEventListener('click',    function () { self.next(); });
            this.els.btnShuffle.addEventListener('click', function () { self.toggleShuffle(); });
            this.els.btnRepeat.addEventListener('click',  function () { self.toggleRepeat(); });

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

            if (!this.playlistMode()) return;

            // Repeat-one loops the same track regardless of shuffle.
            if (this.repeat === 'one') {
                this.audio.currentTime = 0;
                var self = this;
                this.audio.play().catch(function () {});
                return;
            }

            var nxt = this.getNextAutoAdvance();
            if (nxt !== -1) {
                this.playIndex(nxt);
                return;
            }
            if (this.repeat === 'all') {
                // End of pass with repeat-all: reshuffle (if shuffling) and restart from top.
                if (this.shuffle) this.generateShuffleOrder();
                this.playIndex(this.shuffle ? this.shuffleOrder[0] : 0);
            }
            // Else: end of list, no repeat — leave the bar showing but idle.
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
            // <track> requires the audio element to be CORS-enabled ONLY when
            // the track src is cross-origin from the page. Same-origin VTTs
            // (shipped under /assets/lyrics/) work without CORS on either
            // side, which lets the pilot avoid a Cloudflare-dashboard round
            // trip to expand R2 bucket CORS beyond the two production hosts.
            if (isCrossOrigin(vttUrl)) this.audio.crossOrigin = 'anonymous';
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

    function isCrossOrigin(url) {
        // Relative URLs are always same-origin.
        if (!/^https?:\/\//i.test(url)) return false;
        try {
            return new URL(url, window.location.href).origin !== window.location.origin;
        } catch (_) {
            return true;
        }
    }

    // Deep-link handler — /music/?play=FILENAME arms and plays the track.
    // Runs after init so P.play() has a built DOM and event bindings. Reads
    // ?play=, decodes it, requires the file to exist in WOP_MUSIC_CATALOG,
    // then calls P.play(). If autoplay policy blocks the play() promise, the
    // NotAllowedError handler in P.play() adds .wp-armed to the root so the
    // play button pulses; the .wp-armed class is cleared on the first
    // successful 'play' event (see bindEvents). The ?play= parameter is
    // stripped with history.replaceState so a refresh doesn't re-fire.
    //
    // On /music/, also scroll the matching playlist row into view and mark
    // it as the current row so the reader sees where the track lives.
    //
    // Optional &lyrics=1 opens the lyrics drawer once the track has LOADED
    // (P.play() attaches lyrics synchronously before calling audio.play()),
    // so the drawer shows even when autoplay is blocked and the player lands
    // in the armed-but-paused state. Absent the parameter, behaviour is
    // unchanged. It is stripped alongside ?play= below.
    function processDeepLink() {
        var params = new URLSearchParams(window.location.search);
        var raw = params.get('play');
        var wantLyrics = !!params.get('lyrics') && params.get('lyrics') !== '0';
        if (!raw) return;
        var file;
        try { file = decodeURIComponent(raw); } catch (_) { file = raw; }

        var catalog = window.WOP_MUSIC_CATALOG || {};
        if (!catalog[file]) return;

        // /music/-specific decoration: scroll the row into view and mark it.
        if (window.location.pathname.replace(/\/+$/, '') === '/music') {
            var row = document.querySelector(
                '.playlist-row[data-play-file="' + cssEscape(file) + '"]'
            );
            if (row) {
                row.classList.add('playlist-row--current');
                try { row.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                catch (_) { row.scrollIntoView(); }
            }
        }

        P.play(file);
        if (wantLyrics) P.openDrawer();

        // Strip ?play= (and &lyrics=) so refresh doesn't re-fire. Preserve
        // any other params.
        params.delete('play');
        params.delete('lyrics');
        var qs = params.toString();
        var newUrl = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
        try { history.replaceState(null, '', newUrl); } catch (_) {}
    }

    // Minimal CSS.escape polyfill for the row selector — modern browsers
    // have it natively; fall back to a safe passthrough for older ones.
    function cssEscape(s) {
        if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(s);
        return String(s).replace(/["\\]/g, '\\$&');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            P.init();
            processDeepLink();
        });
    } else {
        P.init();
        processDeepLink();
    }

    window.WopPlayer = P;
})();
