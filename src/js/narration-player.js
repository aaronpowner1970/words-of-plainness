/**
 * WORDS OF PLAINNESS — Narration Player (Two-Track)
 * ==================================================
 * Two-track-per-chapter player for the Narrations page.
 * Each chapter has a podcast track and a full narration track.
 * Auto-advance stays in the same lane (podcast→podcast, narration→narration).
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
        var groups = document.querySelectorAll('.narration-chapter-group');
        var self = this;
        this.chapters = Array.from(groups).map(function(group, i) {
            var podcastRow = group.querySelector('[data-track-type="podcast"]');
            var narrationRow = group.querySelector('[data-track-type="narration"]');

            var ch = {
                index: i,
                chapter: parseInt(podcastRow.dataset.chapter, 10),
                title: podcastRow.dataset.title,
                url: podcastRow.dataset.chapterUrl,
                podcastRow: podcastRow,
                narrationRow: narrationRow,
                podcast: {
                    src: podcastRow.dataset.src,
                    type: 'single'
                },
                narration: self.parseNarrationTrack(narrationRow)
            };

            return ch;
        });
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
        this.audio.addEventListener('play', function() { self.clearLoading(); self.updatePlayState(true); });
        this.audio.addEventListener('pause', function() {
            self.updatePlayState(false);
            self.savePosition();
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
                self.loadTrack(i, 'podcast');
                self.play();
            });
            ch.narrationRow.addEventListener('click', function(e) {
                if (e.target.closest('a')) return;
                self.loadTrack(i, 'narration');
                self.play();
            });
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

        // Save position on page unload
        window.addEventListener('beforeunload', function() {
            self.savePosition();
        });
    },

    // =========================================
    // Playback
    // =========================================

    loadTrack: function(index, trackType, sectionIndex) {
        if (index < 0 || index >= this.chapters.length) return;

        var ch = this.chapters[index];
        this.currentIndex = index;
        this.currentTrackType = trackType;
        this.currentSectionIndex = sectionIndex || 0;

        // Determine the audio source
        var src;
        if (trackType === 'podcast') {
            src = ch.podcast.src;
        } else {
            // narration
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
        this.updateViewText(ch.chapter, ch.title);
        this.clearAllHighlights();
        var activeRow = trackType === 'podcast' ? ch.podcastRow : ch.narrationRow;
        activeRow.classList.add('playing');
        activeRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Save to localStorage
        localStorage.setItem(this.STORAGE_KEY_CHAPTER, ch.chapter);
        localStorage.setItem(this.STORAGE_KEY_TRACK_TYPE, trackType);

        // Reset progress display
        this.els.progressFill.style.width = '0%';
        this.els.progressInput.value = 0;
        this.els.timeCurrent.textContent = '0:00';
        this.els.timeTotal.textContent = '0:00';
    },

    clearAllHighlights: function() {
        var allRows = document.querySelectorAll('.narration-track-row');
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

        // For section-based narrations, go to previous section first
        if (this.currentIndex >= 0 && trackType === 'narration') {
            var ch = this.chapters[this.currentIndex];
            if (ch.narration.type === 'sections' && this.currentSectionIndex > 0 && this.audio.currentTime <= 5) {
                this.loadTrack(this.currentIndex, 'narration', this.currentSectionIndex - 1);
                this.play();
                return;
            }
        }

        // If more than 5 seconds in, restart current track
        if (this.audio.currentTime > 5) {
            this.audio.currentTime = 0;
            return;
        }

        // Go to previous chapter (same lane)
        var prevIndex = this.currentIndex - 1;
        if (prevIndex >= 0) {
            this.loadTrack(prevIndex, trackType);
            this.play();
        }
    },

    nextChapter: function() {
        if (this.chapters.length === 0) return;
        var trackType = this.currentTrackType || 'podcast';

        // For section-based narrations, advance to next section first
        if (this.currentIndex >= 0 && trackType === 'narration') {
            var ch = this.chapters[this.currentIndex];
            if (ch.narration.type === 'sections' && this.currentSectionIndex < ch.narration.sections.length - 1) {
                this.loadTrack(this.currentIndex, 'narration', this.currentSectionIndex + 1);
                this.play();
                return;
            }
        }

        // Advance to next chapter (same lane)
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
        // Auto-advance on error
        if (this.currentIndex >= 0) {
            var self = this;
            setTimeout(function() { self.nextChapter(); }, 500);
        }
    },

    onEnded: function() {
        if (this.currentIndex < 0) return;

        var ch = this.chapters[this.currentIndex];

        // For section-based narrations, advance to next section within the chapter
        if (this.currentTrackType === 'narration' && ch.narration.type === 'sections') {
            if (this.currentSectionIndex < ch.narration.sections.length - 1) {
                this.loadTrack(this.currentIndex, 'narration', this.currentSectionIndex + 1);
                this.play();
                return;
            }
        }

        // Advance to next chapter in the same lane
        var nextIndex = this.currentIndex + 1;
        if (nextIndex < this.chapters.length) {
            this.loadTrack(nextIndex, this.currentTrackType);
            this.play();
        } else {
            // End of list — stop
            this.resetPlayer();
        }
    },

    resetPlayer: function() {
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

    updateViewText: function(chapterNum, chapterTitle) {
        var store = document.getElementById('chapterContentStore');
        if (!store) return;

        var allChapters = store.querySelectorAll('.view-text-chapter');
        var found = false;

        allChapters.forEach(function(div) {
            if (parseInt(div.dataset.chapter, 10) === chapterNum) {
                var panel = document.querySelector('#viewTextPanel .view-text-panel');
                if (panel) {
                    panel.innerHTML = div.innerHTML;
                }
                found = true;
            }
        });

        if (!found) {
            var panel = document.querySelector('#viewTextPanel .view-text-panel');
            if (panel) {
                panel.innerHTML = '<h2 class="view-text-heading">Chapter ' + chapterNum + ': ' + chapterTitle + '</h2>' +
                    '<div class="view-text-content"><p class="no-text">Text not available for this chapter.</p></div>';
            }
        }
    },

    // =========================================
    // Position Persistence
    // =========================================

    savePosition: function() {
        if (this.currentIndex >= 0 && this.audio.currentTime > 0) {
            localStorage.setItem(this.STORAGE_KEY_CHAPTER, this.chapters[this.currentIndex].chapter);
            localStorage.setItem(this.STORAGE_KEY_POSITION, Math.floor(this.audio.currentTime));
            localStorage.setItem(this.STORAGE_KEY_TRACK_TYPE, this.currentTrackType);
        }
    },

    restorePosition: function() {
        var savedChapter = localStorage.getItem(this.STORAGE_KEY_CHAPTER);
        var savedPosition = localStorage.getItem(this.STORAGE_KEY_POSITION);
        var savedTrackType = localStorage.getItem(this.STORAGE_KEY_TRACK_TYPE);

        if (savedChapter === null) return;

        var chapterNum = parseInt(savedChapter, 10);
        var position = savedPosition ? parseInt(savedPosition, 10) : 0;
        var trackType = savedTrackType || 'podcast';

        // Find the chapter index
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
                // Trigger metadata load without playing
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
