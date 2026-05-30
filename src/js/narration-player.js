/**
 * WORDS OF PLAINNESS — Narration Player (Two-Track)
 * ==================================================
 * Two-track-per-chapter player for the Narrations page.
 * Each chapter has a podcast track and a full narration track.
 * Auto-advance stays in the same lane (podcast->podcast, narration->narration).
 * Progress sync: authenticated users save to Django API; guests use localStorage.
 */

var CDN_BASE = 'https://media.wordsofplainness.org/web/';

var NarrationPlayer = {
    // State
    audio: null,
    chapters: [],
    currentIndex: -1,
    currentSectionIndex: 0,
    currentTrackType: null, // "podcast" or "narration"
    isPlaying: false,
    playIntent: 0,

    // Progress sync state
    _saveInterval: null,
    _saveInFlight: false,
    SAVE_INTERVAL_MS: 30000,

    // localStorage keys
    STORAGE_KEY_CHAPTER: 'wop-narration-chapter',
    STORAGE_KEY_POSITION: 'wop-narration-position',
    STORAGE_KEY_VOLUME: 'wop-narration-volume',
    STORAGE_KEY_TRACK_TYPE: 'wop-narration-track-type',

    // DOM refs
    els: {},

    init: function() {
        this.audio = document.getElementById('narrationAudio');
        if (!this.audio) return;

        this.cacheElements();
        this.loadChapters();
        this.loadVolume();
        this.bindEvents();
        this.restoreViewTextState();
        this.loadCheckmarks();
        this.loadResumePrompt();
        this.restorePosition();

        console.log('NarrationPlayer initialized with', this.chapters.length, 'chapters');
    },

    cacheElements: function() {
        var id = function(s) { return document.getElementById(s); };
        this.els = {
            npTitle: id('npTitle'),
            npChapter: id('npChapter'),
            btnPlay: id('btnPlay'),
            btnPrev: id('btnPrev'),
            btnNext: id('btnNext'),
            timeCurrent: id('timeCurrent'),
            timeTotal: id('timeTotal'),
            progressFill: id('progressFill'),
            progressInput: id('progressInput'),
            btnVolume: id('btnVolume'),
            volumeInput: id('volumeInput'),
            viewTextWrapper: id('viewTextWrapper'),
            viewTextToggle: id('viewTextToggle'),
            viewTextArrow: id('viewTextArrow'),
            viewTextHeading: id('viewTextHeading'),
            viewTextContent: id('viewTextContent')
        };
    },

    loadChapters: function() {
        var self = this;

        // Articles Podcast series — single-track episode rows (no chapter twin)
        var episodes = Array.from(document.querySelectorAll('.narration-episode-row')).map(function(row) {
            return {
                isEpisode: true,
                chapter: null,
                title: row.dataset.title,
                slug: 'articles-pod-' + row.dataset.episode,
                url: row.dataset.chapterUrl || '/articles/',
                group: row,
                podcastRow: row,
                narrationRow: null,
                podcast: { src: row.dataset.src, type: 'single' },
                narration: { type: 'single', src: row.dataset.src }
            };
        });

        var groups = document.querySelectorAll('.narration-chapter-group');
        var chapters = Array.from(groups).map(function(group) {
            var podcastRow = group.querySelector('[data-track-type="podcast"]');
            var narrationRow = group.querySelector('[data-track-type="narration"]');

            return {
                isEpisode: false,
                chapter: parseInt(podcastRow.dataset.chapter, 10),
                title: podcastRow.dataset.title,
                slug: podcastRow.dataset.slug,
                url: podcastRow.dataset.chapterUrl,
                group: group,
                podcastRow: podcastRow,
                narrationRow: narrationRow,
                podcast: {
                    src: podcastRow.dataset.src,
                    type: 'single'
                },
                narration: self.parseNarrationTrack(narrationRow)
            };
        });

        // Episodes first (DOM order), then chapters. Re-index sequentially.
        this.chapters = episodes.concat(chapters);
        this.chapters.forEach(function(ch, i) { ch.index = i; });
    },

    parseNarrationTrack: function(row) {
        var narrationType = row.dataset.narrationType;
        if (narrationType === 'sections') {
            var sections = [];
            try {
                sections = JSON.parse(row.dataset.sections);
            } catch (e) {
                sections = [];
            }
            return {
                type: 'sections',
                sections: sections,
                src: sections.length > 0 ? CDN_BASE + sections[0].prose : ''
            };
        } else {
            return {
                type: 'single',
                src: row.dataset.src
            };
        }
    },

    loadVolume: function() {
        var saved = localStorage.getItem(this.STORAGE_KEY_VOLUME);
        var vol = saved !== null ? parseInt(saved, 10) : 80;
        this.audio.volume = vol / 100;
        this.els.volumeInput.value = vol;
    },

    bindEvents: function() {
        var self = this;

        // Audio events
        this.audio.addEventListener('timeupdate', function() { self.onTimeUpdate(); });
        this.audio.addEventListener('loadedmetadata', function() { self.onMetadataLoaded(); });
        this.audio.addEventListener('ended', function() { self.onEnded(); });
        this.audio.addEventListener('play', function() {
            self.clearLoading();
            self.updatePlayState(true);
            self.startProgressInterval();
        });
        this.audio.addEventListener('pause', function() {
            self.updatePlayState(false);
            self.stopProgressInterval();
            self.saveProgress(false);
        });
        this.audio.addEventListener('error', function() { self.onAudioError(); });

        // Control buttons
        this.els.btnPlay.addEventListener('click', function() { self.togglePlay(); });
        this.els.btnPrev.addEventListener('click', function() { self.prevChapter(); });
        this.els.btnNext.addEventListener('click', function() { self.nextChapter(); });
        this.els.viewTextToggle.addEventListener('click', function() { self.toggleViewText(); });

        // Progress seeking
        this.els.progressInput.addEventListener('input', function(e) {
            if (self.audio.duration) {
                self.audio.currentTime = (e.target.value / 100) * self.audio.duration;
            }
        });

        // Volume
        this.els.volumeInput.addEventListener('input', function(e) {
            var vol = parseInt(e.target.value, 10);
            self.audio.volume = vol / 100;
            self.audio.muted = false;
            localStorage.setItem(self.STORAGE_KEY_VOLUME, vol);
            self.updateVolumeIcon();
        });

        this.els.btnVolume.addEventListener('click', function() {
            self.audio.muted = !self.audio.muted;
            self.updateVolumeIcon();
        });

        // Track row clicks
        this.chapters.forEach(function(ch, i) {
            ch.podcastRow.addEventListener('click', function(e) {
                if (e.target.closest('a')) return;
                self.dismissResume();
                self.loadTrack(i, 'podcast');
                self.play();
            });
            if (ch.narrationRow) {
                ch.narrationRow.addEventListener('click', function(e) {
                    if (e.target.closest('a')) return;
                    self.dismissResume();
                    self.loadTrack(i, 'narration');
                    self.play();
                });
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch (e.code) {
                case 'Space':
                    e.preventDefault();
                    self.togglePlay();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    if (self.audio.duration) {
                        self.audio.currentTime = Math.max(0, self.audio.currentTime - 5);
                    }
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    if (self.audio.duration) {
                        self.audio.currentTime = Math.min(self.audio.duration, self.audio.currentTime + 5);
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    self.adjustVolume(5);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    self.adjustVolume(-5);
                    break;
            }
        });

        // Save on page unload and visibility change
        window.addEventListener('beforeunload', function() {
            self.saveProgress(false);
        });
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                self.saveProgress(false);
            }
        });
    },

    // =========================================
    // Playback
    // =========================================

    loadTrack: function(index, trackType, sectionIndex) {
        if (index < 0 || index >= this.chapters.length) return;

        // Stop progress interval for the old track
        this.stopProgressInterval();

        var ch = this.chapters[index];
        if (ch.isEpisode) { trackType = 'podcast'; }
        this.currentIndex = index;
        this.currentTrackType = trackType;
        this.currentSectionIndex = sectionIndex || 0;

        // Determine the audio source
        var src;
        if (trackType === 'podcast') {
            src = ch.podcast.src;
        } else {
            var narr = ch.narration;
            if (narr.type === 'sections' && narr.sections.length > 0) {
                src = CDN_BASE + narr.sections[this.currentSectionIndex].prose;
            } else {
                src = narr.src;
            }
        }

        // Cancel stale play attempts
        this.playIntent++;

        // Stop current playback
        this.audio.pause();
        this.audio.src = src;

        // Show loading state
        this.els.btnPlay.classList.add('loading');

        // Update UI
        this.updateNowPlaying(ch, trackType);
        this.updateViewText(ch.chapter, ch.title, trackType);
        this.clearAllHighlights();
        var activeRow = trackType === 'podcast' ? ch.podcastRow : ch.narrationRow;
        if (activeRow) {
            activeRow.classList.add('playing');
            activeRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Save to localStorage (chapter restore keys don't apply to episodes)
        if (!ch.isEpisode) {
            localStorage.setItem(this.STORAGE_KEY_CHAPTER, ch.chapter);
            localStorage.setItem(this.STORAGE_KEY_TRACK_TYPE, trackType);
        }

        // Reset progress display
        this.els.progressFill.style.width = '0%';
        this.els.progressInput.value = 0;
        this.els.timeCurrent.textContent = '0:00';
        this.els.timeTotal.textContent = '0:00';
    },

    clearAllHighlights: function() {
        var allRows = document.querySelectorAll('.narration-track-row, .narration-episode-row');
        for (var i = 0; i < allRows.length; i++) {
            allRows[i].classList.remove('playing');
        }
    },

    clearLoading: function() {
        this.els.btnPlay.classList.remove('loading');
    },

    play: function() {
        var self = this;
        var thisIntent = this.playIntent;

        this.audio.play().catch(function(err) {
            if (thisIntent !== self.playIntent) return;
            if (err.name === 'AbortError') return;
            if (err.name === 'NotAllowedError') return;
            self.clearLoading();
            console.warn('Playback failed:', err.message);
        });
    },

    pause: function() {
        this.audio.pause();
    },

    togglePlay: function() {
        if (this.currentIndex === -1) {
            this.loadTrack(0, 'podcast');
            this.play();
            return;
        }

        if (this.audio.paused) {
            this.play();
        } else {
            this.pause();
        }
    },

    prevChapter: function() {
        if (this.chapters.length === 0) return;
        var trackType = this.currentTrackType || 'podcast';

        if (this.currentIndex >= 0 && trackType === 'narration') {
            var ch = this.chapters[this.currentIndex];
            if (ch.narration.type === 'sections' && this.currentSectionIndex > 0 && this.audio.currentTime <= 5) {
                this.loadTrack(this.currentIndex, 'narration', this.currentSectionIndex - 1);
                this.play();
                return;
            }
        }

        if (this.audio.currentTime > 5) {
            this.audio.currentTime = 0;
            return;
        }

        var prevIndex = this.currentIndex - 1;
        if (prevIndex >= 0) {
            this.loadTrack(prevIndex, trackType);
            this.play();
        }
    },

    nextChapter: function() {
        if (this.chapters.length === 0) return;
        var trackType = this.currentTrackType || 'podcast';

        if (this.currentIndex >= 0 && trackType === 'narration') {
            var ch = this.chapters[this.currentIndex];
            if (ch.narration.type === 'sections' && this.currentSectionIndex < ch.narration.sections.length - 1) {
                this.loadTrack(this.currentIndex, 'narration', this.currentSectionIndex + 1);
                this.play();
                return;
            }
        }

        var nextIndex = this.currentIndex + 1;
        if (nextIndex < this.chapters.length) {
            this.loadTrack(nextIndex, trackType);
            this.play();
        }
    },

    // =========================================
    // Audio Events
    // =========================================

    onTimeUpdate: function() {
        if (!this.audio.duration) return;
        var pct = (this.audio.currentTime / this.audio.duration) * 100;
        this.els.progressFill.style.width = pct + '%';
        this.els.progressInput.value = pct;
        this.els.timeCurrent.textContent = this.formatTime(this.audio.currentTime);
    },

    onMetadataLoaded: function() {
        this.els.timeTotal.textContent = this.formatTime(this.audio.duration);
    },

    onAudioError: function() {
        this.clearLoading();
        var err = this.audio.error;
        if (err) {
            console.warn('Audio error:', err.code, err.message);
        }
        if (this.currentIndex >= 0) {
            var self = this;
            setTimeout(function() { self.nextChapter(); }, 500);
        }
    },

    onEnded: function() {
        if (this.currentIndex < 0) return;

        var ch = this.chapters[this.currentIndex];

        // Articles Podcast: advance to the next episode, then stop at the end of the series
        if (ch.isEpisode) {
            this.saveProgress(true);
            this.markTrackCompleted(ch.slug, 'podcast');
            var nextEp = this.currentIndex + 1;
            if (nextEp < this.chapters.length && this.chapters[nextEp].isEpisode) {
                this.loadTrack(nextEp, 'podcast');
                this.play();
            } else {
                this.resetPlayer();
            }
            return;
        }

        // For section-based narrations, advance to next section within the chapter
        if (this.currentTrackType === 'narration' && ch.narration.type === 'sections') {
            if (this.currentSectionIndex < ch.narration.sections.length - 1) {
                this.loadTrack(this.currentIndex, 'narration', this.currentSectionIndex + 1);
                this.play();
                return;
            }
        }

        // Mark this track completed
        this.saveProgress(true);
        this.markTrackCompleted(ch.slug, this.currentTrackType);

        // Advance to next chapter in the same lane
        var nextIndex = this.currentIndex + 1;
        if (nextIndex < this.chapters.length) {
            this.loadTrack(nextIndex, this.currentTrackType);
            this.play();
        } else {
            this.resetPlayer();
        }
    },

    resetPlayer: function() {
        this.stopProgressInterval();
        this.currentIndex = -1;
        this.currentSectionIndex = 0;
        this.currentTrackType = null;
        this.els.npTitle.textContent = 'Select a chapter';
        this.els.npChapter.textContent = '';
        this.els.progressFill.style.width = '0%';
        this.els.progressInput.value = 0;
        this.els.timeCurrent.textContent = '0:00';
        this.els.timeTotal.textContent = '0:00';
        this.clearAllHighlights();
        this.updatePlayState(false);
    },

    updateNowPlaying: function(ch, trackType) {
        this.els.npTitle.textContent = ch.title;
        if (ch.isEpisode) {
            this.els.npChapter.textContent = 'Articles Podcast';
            return;
        }
        var label = 'Ch. ' + ch.chapter;
        if (trackType === 'podcast') {
            var podcastLabel = ch.podcastRow.querySelector('.narration-track-label');
            label += ' \u2014 ' + (podcastLabel ? podcastLabel.textContent : 'Podcast');
        } else {
            label += ' \u2014 Full Narration';
            if (ch.narration.type === 'sections' && ch.narration.sections.length > 1) {
                label += ' (Part ' + (this.currentSectionIndex + 1) + ' of ' + ch.narration.sections.length + ')';
            }
        }
        this.els.npChapter.textContent = label;
    },

    updatePlayState: function(isPlaying) {
        this.isPlaying = isPlaying;
        var playIcon = this.els.btnPlay.querySelector('.icon-play');
        var pauseIcon = this.els.btnPlay.querySelector('.icon-pause');

        if (isPlaying) {
            playIcon.style.display = 'none';
            pauseIcon.style.display = 'block';
            this.els.btnPlay.title = 'Pause';
        } else {
            playIcon.style.display = 'block';
            pauseIcon.style.display = 'none';
            this.els.btnPlay.title = 'Play';
        }
    },

    // =========================================
    // Progress Sync
    // =========================================

    _isAuthenticated: function() {
        return window.API && API.isAuthenticated();
    },

    startProgressInterval: function() {
        this.stopProgressInterval();
        var self = this;
        this._saveInterval = setInterval(function() {
            self.saveProgress(false);
        }, this.SAVE_INTERVAL_MS);
    },

    stopProgressInterval: function() {
        if (this._saveInterval) {
            clearInterval(this._saveInterval);
            this._saveInterval = null;
        }
    },

    saveProgress: function(completed) {
        if (this.currentIndex < 0) return;
        var ch = this.chapters[this.currentIndex];
        var trackType = this.currentTrackType;
        var position = completed ? 0 : Math.floor(this.audio.currentTime || 0);

        // Always save to localStorage
        var lsKey = 'wop-narration-progress::' + ch.slug + '::' + trackType;
        localStorage.setItem(lsKey, JSON.stringify({
            position_seconds: position,
            completed: !!completed,
            updated_at: new Date().toISOString()
        }));

        // Also save the simple restore keys (chapters only — episodes don't restore by number)
        if (!ch.isEpisode) {
            localStorage.setItem(this.STORAGE_KEY_CHAPTER, ch.chapter);
            localStorage.setItem(this.STORAGE_KEY_POSITION, position);
            localStorage.setItem(this.STORAGE_KEY_TRACK_TYPE, trackType);
        }

        // If authenticated, save to API (skip episodes — not chapter-backed)
        if (!ch.isEpisode && this._isAuthenticated() && !this._saveInFlight) {
            this._saveInFlight = true;
            var self = this;
            API.request('/progress/narration-progress/', {
                method: 'POST',
                body: JSON.stringify({
                    chapter_slug: ch.slug,
                    track_type: trackType,
                    position_seconds: position,
                    completed: !!completed
                })
            }).catch(function(err) {
                console.warn('Progress save failed:', err.message);
            }).finally(function() {
                self._saveInFlight = false;
            });
        }
    },

    // =========================================
    // Checkmarks
    // =========================================

    markTrackCompleted: function(slug, trackType) {
        var self = this;
        // Find the chapter and add checkmark to the correct row
        this.chapters.forEach(function(ch) {
            if (ch.slug === slug) {
                var row = trackType === 'podcast' ? ch.podcastRow : ch.narrationRow;
                self._addCheckmark(row);
            }
        });
    },

    _addCheckmark: function(row) {
        if (row.querySelector('.track-completed')) return;
        var check = document.createElement('span');
        check.className = 'track-completed';
        check.textContent = '\u2713';
        check.setAttribute('aria-label', 'Completed');
        var label = row.querySelector('.narration-track-label');
        if (label) {
            label.parentNode.insertBefore(check, label.nextSibling);
        }
    },

    loadCheckmarks: function() {
        var self = this;

        if (this._isAuthenticated()) {
            API.request('/progress/narration-completions/').then(function(data) {
                if (data && data.completed_tracks) {
                    data.completed_tracks.forEach(function(entry) {
                        self.markTrackCompleted(entry.chapter_slug, entry.track_type);
                    });
                }
            }).catch(function(err) {
                console.warn('Failed to load completions:', err.message);
                // Fall back to localStorage
                self._loadLocalCheckmarks();
            });
        } else {
            this._loadLocalCheckmarks();
        }
    },

    _loadLocalCheckmarks: function() {
        var self = this;
        this.chapters.forEach(function(ch) {
            ['podcast', 'narration'].forEach(function(trackType) {
                var key = 'wop-narration-progress::' + ch.slug + '::' + trackType;
                var raw = localStorage.getItem(key);
                if (raw) {
                    try {
                        var data = JSON.parse(raw);
                        if (data.completed) {
                            self.markTrackCompleted(ch.slug, trackType);
                        }
                    } catch (e) { /* skip */ }
                }
            });
        });
    },

    // =========================================
    // Resume Prompt
    // =========================================

    loadResumePrompt: function() {
        if (!this._isAuthenticated()) return;

        var self = this;
        API.request('/progress/narration-progress/').then(function(data) {
            if (!data || !data.progress) return;
            var p = data.progress;
            if (p.completed || p.position_seconds <= 0) return;

            // Find the chapter
            var ch = null;
            var chIndex = -1;
            for (var i = 0; i < self.chapters.length; i++) {
                if (self.chapters[i].slug === p.chapter_slug) {
                    ch = self.chapters[i];
                    chIndex = i;
                    break;
                }
            }
            if (!ch) return;

            // Build the track label
            var trackLabel;
            if (p.track_type === 'narration') {
                trackLabel = 'Full Narration';
            } else {
                var podcastLabelEl = ch.podcastRow.querySelector('.narration-track-label');
                trackLabel = podcastLabelEl ? podcastLabelEl.textContent : 'Podcast Overview';
            }

            var timeStr = self.formatTime(p.position_seconds);

            // Create resume element
            var resume = document.createElement('div');
            resume.className = 'narration-resume-prompt';
            resume.id = 'narrationResumePrompt';
            resume.innerHTML = '<span class="resume-text">Resume <strong>' + trackLabel +
                '</strong> at ' + timeStr + '</span>' +
                '<button class="resume-btn" type="button">Resume</button>' +
                '<button class="resume-dismiss" type="button" aria-label="Dismiss">&times;</button>';

            // Insert after the chapter header
            var header = ch.group.querySelector('.narration-chapter-header');
            if (header) {
                header.parentNode.insertBefore(resume, header.nextSibling);
            }

            // Bind events
            resume.querySelector('.resume-btn').addEventListener('click', function() {
                self.dismissResume();
                self.loadTrack(chIndex, p.track_type);
                // Seek to saved position after metadata loads
                var seekTo = p.position_seconds;
                self.audio.addEventListener('loadedmetadata', function onMeta() {
                    self.audio.removeEventListener('loadedmetadata', onMeta);
                    if (seekTo < self.audio.duration) {
                        self.audio.currentTime = seekTo;
                    }
                });
                self.play();
            });
            resume.querySelector('.resume-dismiss').addEventListener('click', function() {
                self.dismissResume();
            });
        }).catch(function(err) {
            console.warn('Failed to load resume state:', err.message);
        });
    },

    dismissResume: function() {
        var el = document.getElementById('narrationResumePrompt');
        if (el) el.remove();
    },

    // =========================================
    // View Text Panel
    // =========================================

    toggleViewText: function() {
        var wrapper = this.els.viewTextWrapper;
        var isOpen = wrapper.classList.toggle('open');
        this.els.viewTextToggle.setAttribute('aria-expanded', isOpen);
        this.els.viewTextArrow.innerHTML = isOpen ? '&#9650;' : '&#9660;';
        localStorage.setItem('wop-narration-viewtext', isOpen ? '1' : '0');
    },

    restoreViewTextState: function() {
        var saved = localStorage.getItem('wop-narration-viewtext');
        if (saved === '1') {
            this.els.viewTextWrapper.classList.add('open');
            this.els.viewTextToggle.setAttribute('aria-expanded', 'true');
            this.els.viewTextArrow.innerHTML = '&#9650;';
        }
    },

    updateViewText: function(chapterNum, chapterTitle, trackType) {
        var panel = document.querySelector('#viewTextPanel .view-text-panel');
        if (!panel) return;

        if (chapterNum == null) {
            panel.innerHTML = '<h2 class="view-text-heading">' + chapterTitle + '</h2>' +
                '<div class="view-text-content"><p class="view-text-gated">This is a dramatized episode from the Articles Podcast. You can read the Articles of Interfaith Discipleship in full on the <a href="/articles/">Articles page</a>.</p></div>';
            return;
        }

        if (trackType === 'podcast') {
            panel.innerHTML = '<h2 class="view-text-heading">Chapter ' + chapterNum + ': ' + chapterTitle + '</h2>' +
                '<div class="view-text-content"><p class="view-text-gated">Full chapter text is available when listening to the Full Narration.</p></div>';
            return;
        }

        var store = document.getElementById('chapterContentStore');
        if (!store) return;

        var allChapters = store.querySelectorAll('.view-text-chapter');
        var found = false;

        allChapters.forEach(function(div) {
            if (parseInt(div.dataset.chapter, 10) === chapterNum) {
                panel.innerHTML = div.innerHTML;
                found = true;
            }
        });

        if (!found) {
            panel.innerHTML = '<h2 class="view-text-heading">Chapter ' + chapterNum + ': ' + chapterTitle + '</h2>' +
                '<div class="view-text-content"><p class="no-text">Text not available for this chapter.</p></div>';
        }
    },

    // =========================================
    // Position Persistence (localStorage)
    // =========================================

    restorePosition: function() {
        var savedChapter = localStorage.getItem(this.STORAGE_KEY_CHAPTER);
        var savedPosition = localStorage.getItem(this.STORAGE_KEY_POSITION);
        var savedTrackType = localStorage.getItem(this.STORAGE_KEY_TRACK_TYPE);

        if (savedChapter === null) return;

        var chapterNum = parseInt(savedChapter, 10);
        var position = savedPosition ? parseInt(savedPosition, 10) : 0;
        var trackType = savedTrackType || 'podcast';

        var index = -1;
        for (var i = 0; i < this.chapters.length; i++) {
            if (this.chapters[i].chapter === chapterNum) {
                index = i;
                break;
            }
        }

        if (index >= 0) {
            this.loadTrack(index, trackType);
            if (position > 0) {
                var self = this;
                this.audio.addEventListener('loadedmetadata', function onMeta() {
                    self.audio.removeEventListener('loadedmetadata', onMeta);
                    if (position < self.audio.duration) {
                        self.audio.currentTime = position;
                    }
                });
                this.audio.preload = 'metadata';
                this.audio.load();
            }
        }
    },

    // =========================================
    // Volume
    // =========================================

    adjustVolume: function(delta) {
        var current = Math.round(this.audio.volume * 100);
        var next = Math.max(0, Math.min(100, current + delta));
        this.audio.volume = next / 100;
        this.audio.muted = false;
        this.els.volumeInput.value = next;
        localStorage.setItem(this.STORAGE_KEY_VOLUME, next);
        this.updateVolumeIcon();
    },

    updateVolumeIcon: function() {
        var volOn = this.els.btnVolume.querySelector('.icon-vol-on');
        var volMute = this.els.btnVolume.querySelector('.icon-vol-mute');

        if (this.audio.muted || this.audio.volume === 0) {
            volOn.style.display = 'none';
            volMute.style.display = 'block';
        } else {
            volOn.style.display = 'block';
            volMute.style.display = 'none';
        }
    },

    // =========================================
    // Helpers
    // =========================================

    formatTime: function(seconds) {
        if (!seconds || !isFinite(seconds)) return '0:00';
        var m = Math.floor(seconds / 60);
        var s = Math.floor(seconds % 60);
        return m + ':' + String(s).padStart(2, '0');
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    NarrationPlayer.init();
});

window.NarrationPlayer = NarrationPlayer;
