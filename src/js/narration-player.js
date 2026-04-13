/**
 * WORDS OF PLAINNESS — Narration Player
 * ======================================
 * Sequential chapter narration player for the Narrations page.
 * Supports single-file and section-based chapters with continuous auto-advance.
 */

const CDN_BASE = 'https://media.wordsofplainness.org/web/';

const NarrationPlayer = {
    // State
    audio: null,
    chapters: [],
    currentIndex: -1,
    currentSectionIndex: 0,
    isPlaying: false,
    playIntent: 0,

    // localStorage keys
    STORAGE_KEY_CHAPTER: 'wop-narration-chapter',
    STORAGE_KEY_POSITION: 'wop-narration-position',
    STORAGE_KEY_VOLUME: 'wop-narration-volume',

    // DOM refs
    els: {},

    init() {
        this.audio = document.getElementById('narrationAudio');
        if (!this.audio) return;

        this.cacheElements();
        this.loadChapters();
        this.loadVolume();
        this.bindEvents();
        this.restorePosition();

        console.log('NarrationPlayer initialized with', this.chapters.length, 'chapters');
    },

    cacheElements() {
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

    loadChapters() {
        var rows = document.querySelectorAll('.narration-row');
        this.chapters = Array.from(rows).map(function(row, i) {
            var ch = {
                index: i,
                chapter: parseInt(row.dataset.chapter, 10),
                title: row.dataset.title,
                url: row.dataset.chapterUrl,
                type: row.dataset.narrationType,
                row: row
            };

            if (ch.type === 'sections') {
                try {
                    ch.sections = JSON.parse(row.dataset.sections);
                } catch (e) {
                    ch.sections = [];
                }
                ch.src = ch.sections.length > 0 ? CDN_BASE + ch.sections[0].prose : '';
            } else {
                ch.src = row.dataset.src;
                ch.sections = [];
            }

            return ch;
        });
    },

    loadVolume() {
        var saved = localStorage.getItem(this.STORAGE_KEY_VOLUME);
        var vol = saved !== null ? parseInt(saved, 10) : 80;
        this.audio.volume = vol / 100;
        this.els.volumeInput.value = vol;
    },

    bindEvents() {
        var self = this;

        // Audio events
        this.audio.addEventListener('timeupdate', function() { self.onTimeUpdate(); });
        this.audio.addEventListener('loadedmetadata', function() { self.onMetadataLoaded(); });
        this.audio.addEventListener('ended', function() { self.onEnded(); });
        this.audio.addEventListener('play', function() { self.updatePlayState(true); });
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

        // Row clicks
        this.chapters.forEach(function(ch, i) {
            ch.row.addEventListener('click', function(e) {
                if (e.target.closest('a')) return;
                self.loadChapter(i);
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

    loadChapter(index, sectionIndex) {
        if (index < 0 || index >= this.chapters.length) return;

        var ch = this.chapters[index];
        this.currentIndex = index;
        this.currentSectionIndex = sectionIndex || 0;

        // Determine the audio source
        var src;
        if (ch.type === 'sections' && ch.sections.length > 0) {
            src = CDN_BASE + ch.sections[this.currentSectionIndex].prose;
        } else {
            src = ch.src;
        }

        // Cancel stale play attempts
        this.playIntent++;

        // Stop current playback
        this.audio.pause();
        this.audio.src = src;

        // Update UI
        this.updateNowPlaying(ch);
        this.chapters.forEach(function(c) { c.row.classList.remove('playing', 'is-playing'); });
        ch.row.classList.add('playing', 'is-playing');
        ch.row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Save to localStorage
        localStorage.setItem(this.STORAGE_KEY_CHAPTER, ch.chapter);

        // Reset progress display
        this.els.progressFill.style.width = '0%';
        this.els.progressInput.value = 0;
        this.els.timeCurrent.textContent = '0:00';
        this.els.timeTotal.textContent = '0:00';
    },

    play() {
        var self = this;
        var thisIntent = this.playIntent;

        this.audio.play().catch(function(err) {
            if (thisIntent !== self.playIntent) return;
            if (err.name === 'AbortError') return;
            if (err.name === 'NotAllowedError') return;
            console.warn('Playback failed:', err.message);
        });
    },

    pause() {
        this.audio.pause();
    },

    togglePlay() {
        if (this.currentIndex === -1) {
            this.loadChapter(0);
            this.play();
            return;
        }

        if (this.audio.paused) {
            this.play();
        } else {
            this.pause();
        }
    },

    prevChapter() {
        if (this.chapters.length === 0) return;

        // For section-based chapters, go to previous section first
        if (this.currentIndex >= 0) {
            var ch = this.chapters[this.currentIndex];
            if (ch.type === 'sections' && this.currentSectionIndex > 0 && this.audio.currentTime <= 5) {
                this.loadChapter(this.currentIndex, this.currentSectionIndex - 1);
                this.play();
                return;
            }
        }

        // If more than 5 seconds in, restart current chapter/section
        if (this.audio.currentTime > 5) {
            this.audio.currentTime = 0;
            return;
        }

        // Go to previous chapter
        var prevIndex = this.currentIndex - 1;
        if (prevIndex >= 0) {
            this.loadChapter(prevIndex);
            this.play();
        }
    },

    nextChapter() {
        if (this.chapters.length === 0) return;

        // For section-based chapters, advance to next section first
        if (this.currentIndex >= 0) {
            var ch = this.chapters[this.currentIndex];
            if (ch.type === 'sections' && this.currentSectionIndex < ch.sections.length - 1) {
                this.loadChapter(this.currentIndex, this.currentSectionIndex + 1);
                this.play();
                return;
            }
        }

        // Advance to next chapter
        var nextIndex = this.currentIndex + 1;
        if (nextIndex < this.chapters.length) {
            this.loadChapter(nextIndex);
            this.play();
        }
    },

    // =========================================
    // Audio Events
    // =========================================

    onTimeUpdate() {
        if (!this.audio.duration) return;
        var pct = (this.audio.currentTime / this.audio.duration) * 100;
        this.els.progressFill.style.width = pct + '%';
        this.els.progressInput.value = pct;
        this.els.timeCurrent.textContent = this.formatTime(this.audio.currentTime);
    },

    onMetadataLoaded() {
        this.els.timeTotal.textContent = this.formatTime(this.audio.duration);

        // Populate duration cell for single-file chapters
        if (this.currentIndex >= 0) {
            var ch = this.chapters[this.currentIndex];
            if (ch.type === 'single') {
                var cell = ch.row.querySelector('[data-duration]');
                if (cell) {
                    cell.textContent = this.formatTime(this.audio.duration);
                }
            }
        }
    },

    onAudioError() {
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

    onEnded() {
        if (this.currentIndex < 0) return;

        var ch = this.chapters[this.currentIndex];

        // For section-based chapters, advance to next section
        if (ch.type === 'sections' && this.currentSectionIndex < ch.sections.length - 1) {
            this.loadChapter(this.currentIndex, this.currentSectionIndex + 1);
            this.play();
            return;
        }

        // Advance to next chapter
        var nextIndex = this.currentIndex + 1;
        if (nextIndex < this.chapters.length) {
            this.loadChapter(nextIndex);
            this.play();
        } else {
            // End of list — stop
            this.resetPlayer();
        }
    },

    resetPlayer() {
        this.currentIndex = -1;
        this.currentSectionIndex = 0;
        this.els.npTitle.textContent = 'Select a chapter';
        this.els.npChapter.textContent = '';
        this.els.progressFill.style.width = '0%';
        this.els.progressInput.value = 0;
        this.els.timeCurrent.textContent = '0:00';
        this.els.timeTotal.textContent = '0:00';
        this.chapters.forEach(function(c) { c.row.classList.remove('playing', 'is-playing'); });
        this.updatePlayState(false);
    },

    updateNowPlaying(ch) {
        this.els.npTitle.textContent = ch.title;
        var label = 'Ch. ' + ch.chapter;
        if (ch.type === 'sections' && ch.sections.length > 1) {
            label += ' \u2014 Part ' + (this.currentSectionIndex + 1) + ' of ' + ch.sections.length;
        }
        this.els.npChapter.textContent = label;
    },

    updatePlayState(isPlaying) {
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

        // Update row highlight
        if (this.currentIndex >= 0) {
            var row = this.chapters[this.currentIndex].row;
            if (isPlaying) {
                row.classList.add('is-playing');
            } else {
                row.classList.remove('is-playing');
            }
        }
    },

    // =========================================
    // View Text Panel
    // =========================================

    toggleViewText() {
        var wrapper = this.els.viewTextWrapper;
        var isOpen = wrapper.classList.toggle('open');
        this.els.viewTextToggle.setAttribute('aria-expanded', isOpen);
        this.els.viewTextArrow.innerHTML = isOpen ? '&#9650;' : '&#9660;';
    },

    // =========================================
    // Position Persistence
    // =========================================

    savePosition() {
        if (this.currentIndex >= 0 && this.audio.currentTime > 0) {
            localStorage.setItem(this.STORAGE_KEY_CHAPTER, this.chapters[this.currentIndex].chapter);
            localStorage.setItem(this.STORAGE_KEY_POSITION, Math.floor(this.audio.currentTime));
        }
    },

    restorePosition() {
        var savedChapter = localStorage.getItem(this.STORAGE_KEY_CHAPTER);
        var savedPosition = localStorage.getItem(this.STORAGE_KEY_POSITION);

        if (savedChapter === null) return;

        var chapterNum = parseInt(savedChapter, 10);
        var position = savedPosition ? parseInt(savedPosition, 10) : 0;

        // Find the chapter index
        var index = -1;
        for (var i = 0; i < this.chapters.length; i++) {
            if (this.chapters[i].chapter === chapterNum) {
                index = i;
                break;
            }
        }

        if (index >= 0) {
            this.loadChapter(index);
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

    adjustVolume(delta) {
        var current = Math.round(this.audio.volume * 100);
        var next = Math.max(0, Math.min(100, current + delta));
        this.audio.volume = next / 100;
        this.audio.muted = false;
        this.els.volumeInput.value = next;
        localStorage.setItem(this.STORAGE_KEY_VOLUME, next);
        this.updateVolumeIcon();
    },

    updateVolumeIcon() {
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

    formatTime(seconds) {
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
