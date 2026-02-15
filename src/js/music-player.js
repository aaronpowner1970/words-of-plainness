/**
 * WORDS OF PLAINNESS — Music Player
 * ==================================
 * Unified playlist player for the Music page.
 * All primaries and alternates play through a single audio element.
 */

const MusicPlayer = {
    // State
    audio: null,
    tracks: [],
    currentIndex: -1,
    shuffle: false,
    repeat: 'none', // 'none', 'all', 'one'
    shuffleOrder: [],
    playIntent: 0, // incremented on each playTrack call to cancel stale play attempts

    // DOM refs
    els: {},

    init() {
        this.audio = document.getElementById('musicAudio');
        if (!this.audio) return;

        this.cacheElements();
        this.loadTracks();
        this.loadVolume();
        this.bindEvents();

        console.log('MusicPlayer initialized with', this.tracks.length, 'tracks');
    },

    cacheElements() {
        const id = (s) => document.getElementById(s);
        this.els = {
            npTitle: id('npTitle'),
            npChapter: id('npChapter'),
            btnPlay: id('btnPlay'),
            btnPrev: id('btnPrev'),
            btnNext: id('btnNext'),
            btnShuffle: id('btnShuffle'),
            btnRepeat: id('btnRepeat'),
            repeatBadge: id('repeatBadge'),
            timeCurrent: id('timeCurrent'),
            timeTotal: id('timeTotal'),
            progressFill: id('progressFill'),
            progressInput: id('progressInput'),
            btnVolume: id('btnVolume'),
            volumeInput: id('volumeInput'),
            lyricsHeading: id('lyricsHeading'),
            lyricsContent: id('lyricsContent'),
            lyricsAltNote: id('lyricsAltNote'),
            lyricsWrapper: id('lyricsWrapper'),
            lyricsToggle: id('lyricsToggle'),
            lyricsArrow: id('lyricsArrow')
        };
    },

    loadTracks() {
        const rows = document.querySelectorAll('.playlist-row');
        this.tracks = Array.from(rows).map((row, i) => ({
            index: i,
            src: row.dataset.src,
            title: row.dataset.title,
            label: row.dataset.label || '',
            chapter: parseInt(row.dataset.chapter, 10),
            chapterTitle: row.dataset.chapterTitle,
            chapterUrl: row.dataset.chapterUrl,
            lyrics: row.dataset.lyrics || '',
            row: row
        }));
    },

    loadVolume() {
        const saved = localStorage.getItem('wop-music-volume');
        const vol = saved !== null ? parseInt(saved, 10) : 80;
        this.audio.volume = vol / 100;
        this.els.volumeInput.value = vol;
    },

    bindEvents() {
        // Audio events
        this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audio.addEventListener('loadedmetadata', () => this.onMetadataLoaded());
        this.audio.addEventListener('ended', () => this.onTrackEnded());
        this.audio.addEventListener('play', () => this.updatePlayState(true));
        this.audio.addEventListener('pause', () => this.updatePlayState(false));
        this.audio.addEventListener('error', (e) => this.onAudioError(e));

        // Control buttons
        this.els.btnPlay.addEventListener('click', () => this.togglePlay());
        this.els.btnPrev.addEventListener('click', () => this.prev());
        this.els.btnNext.addEventListener('click', () => this.next());
        this.els.btnShuffle.addEventListener('click', () => this.toggleShuffle());
        this.els.btnRepeat.addEventListener('click', () => this.toggleRepeat());
        this.els.lyricsToggle.addEventListener('click', () => this.toggleLyrics());

        // Progress seeking
        this.els.progressInput.addEventListener('input', (e) => {
            if (this.audio.duration) {
                this.audio.currentTime = (e.target.value / 100) * this.audio.duration;
            }
        });

        // Volume
        this.els.volumeInput.addEventListener('input', (e) => {
            const vol = parseInt(e.target.value, 10);
            this.audio.volume = vol / 100;
            this.audio.muted = false;
            localStorage.setItem('wop-music-volume', vol);
            this.updateVolumeIcon();
        });

        this.els.btnVolume.addEventListener('click', () => {
            this.audio.muted = !this.audio.muted;
            this.updateVolumeIcon();
        });

        // Playlist row clicks
        this.tracks.forEach((track, i) => {
            track.row.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                this.playTrack(i);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch (e.code) {
                case 'Space':
                    e.preventDefault();
                    this.togglePlay();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    if (this.audio.duration) {
                        this.audio.currentTime = Math.max(0, this.audio.currentTime - 5);
                    }
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    if (this.audio.duration) {
                        this.audio.currentTime = Math.min(this.audio.duration, this.audio.currentTime + 5);
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.adjustVolume(5);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.adjustVolume(-5);
                    break;
            }
        });
    },

    // =========================================
    // Playback
    // =========================================

    playTrack(index, forceRestart) {
        if (index < 0 || index >= this.tracks.length) return;

        const track = this.tracks[index];
        const wasSameTrack = this.currentIndex === index;

        this.currentIndex = index;

        if (wasSameTrack && this.audio.src && !forceRestart) {
            this.togglePlay();
            return;
        }

        // Cancel any stale play attempt
        this.playIntent++;
        const thisIntent = this.playIntent;

        // Stop current playback cleanly before switching
        this.audio.pause();
        this.audio.src = track.src;

        // Update UI immediately (don't wait for audio)
        this.updateNowPlaying(track);
        this.updateLyrics(track);
        this.tracks.forEach(t => t.row.classList.remove('playing', 'is-playing'));
        track.row.classList.add('playing', 'is-playing');
        track.row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Play immediately — browser handles buffering natively
        this.audio.play().catch((err) => {
            if (thisIntent !== this.playIntent) return; // stale — user clicked another track
            if (err.name === 'AbortError') return; // expected when switching tracks
            if (err.name === 'NotAllowedError') return; // autoplay policy
            console.warn('Playback failed:', err.message);
        });
    },

    updateNowPlaying(track) {
        // Always show style label — primaries default to "Sacred Americana"
        var displayLabel = track.label || 'Sacred Americana';
        this.els.npTitle.textContent = track.title + ' \u2014 ' + displayLabel;
        this.els.npChapter.textContent = '(Ch ' + track.chapter + ')';
    },

    togglePlay() {
        if (this.currentIndex === -1) {
            this.playTrack(this.shuffle ? this.getShuffledIndex(0) : 0);
            return;
        }

        if (this.audio.paused) {
            this.audio.play().catch((err) => {
                if (err.name !== 'AbortError') {
                    console.warn('Play failed:', err.message);
                }
            });
        } else {
            this.audio.pause();
        }
    },

    prev() {
        if (this.tracks.length === 0) return;

        // If more than 3s in, restart current track
        if (this.audio.currentTime > 3) {
            this.audio.currentTime = 0;
            return;
        }

        const prevIndex = this.getAdjacentIndex(-1);
        if (prevIndex !== -1) {
            this.playTrack(prevIndex);
        }
    },

    next() {
        if (this.tracks.length === 0) return;
        const nextIndex = this.getAdjacentIndex(1);
        if (nextIndex !== -1) {
            this.playTrack(nextIndex);
        }
    },

    /**
     * Get the next or previous track index for button presses.
     * Wraps around when repeat is 'all'.
     */
    getAdjacentIndex(direction) {
        if (this.shuffle) {
            const shufflePos = this.shuffleOrder.indexOf(this.currentIndex);
            const newPos = shufflePos + direction;
            if (newPos >= 0 && newPos < this.shuffleOrder.length) {
                return this.shuffleOrder[newPos];
            }
            if (this.repeat === 'all') {
                return direction > 0 ? this.shuffleOrder[0] : this.shuffleOrder[this.shuffleOrder.length - 1];
            }
            return -1;
        }

        const newIndex = this.currentIndex + direction;
        if (newIndex >= 0 && newIndex < this.tracks.length) {
            return newIndex;
        }
        if (this.repeat === 'all') {
            return direction > 0 ? 0 : this.tracks.length - 1;
        }
        return -1;
    },

    getShuffledIndex(pos) {
        if (this.shuffleOrder.length === 0) this.generateShuffleOrder();
        return this.shuffleOrder[pos] || 0;
    },

    generateShuffleOrder() {
        this.shuffleOrder = this.tracks.map((_, i) => i);
        // Fisher-Yates shuffle
        for (let i = this.shuffleOrder.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.shuffleOrder[i], this.shuffleOrder[j]] = [this.shuffleOrder[j], this.shuffleOrder[i]];
        }
    },

    // =========================================
    // Audio Events
    // =========================================

    onTimeUpdate() {
        if (!this.audio.duration) return;
        const pct = (this.audio.currentTime / this.audio.duration) * 100;
        this.els.progressFill.style.width = pct + '%';
        this.els.progressInput.value = pct;
        this.els.timeCurrent.textContent = this.formatTime(this.audio.currentTime);
    },

    onMetadataLoaded() {
        this.els.timeTotal.textContent = this.formatTime(this.audio.duration);

        // Populate the duration cell in the track list for the current track
        if (this.currentIndex >= 0) {
            const cell = this.tracks[this.currentIndex].row.querySelector('[data-duration]');
            if (cell) {
                cell.textContent = this.formatTime(this.audio.duration);
            }
        }
    },

    onAudioError(e) {
        const err = this.audio.error;
        if (err) {
            console.warn('Audio error:', err.code, err.message);
        }
        // If a track fails to load, auto-advance to next
        if (this.currentIndex >= 0) {
            const nextIndex = this.getNextAutoAdvance();
            if (nextIndex !== -1) {
                setTimeout(() => this.playTrack(nextIndex), 500);
            }
        }
    },

    onTrackEnded() {
        // Repeat one: loop current track regardless of shuffle
        if (this.repeat === 'one') {
            this.audio.currentTime = 0;
            this.audio.play().catch(() => {});
            return;
        }

        // Find next track in current order (no wrapping)
        const nextIndex = this.getNextAutoAdvance();

        if (nextIndex !== -1) {
            // More tracks in the current pass
            this.playTrack(nextIndex);
        } else if (this.repeat === 'all') {
            // End of list with repeat-all
            if (this.shuffle) {
                this.generateShuffleOrder(); // reshuffle for new pass
            }
            const firstIdx = this.shuffle ? this.shuffleOrder[0] : 0;
            setTimeout(() => this.playTrack(firstIdx, true), 50);
        } else {
            // End of list, no repeat — stop
            this.resetPlayer();
        }
    },

    /**
     * Get the next track for auto-advance (no wrapping).
     * Returns -1 when at end of the current order.
     */
    getNextAutoAdvance() {
        if (this.shuffle) {
            const shufflePos = this.shuffleOrder.indexOf(this.currentIndex);
            const nextPos = shufflePos + 1;
            if (nextPos < this.shuffleOrder.length) {
                return this.shuffleOrder[nextPos];
            }
            return -1;
        }
        const nextIndex = this.currentIndex + 1;
        return nextIndex < this.tracks.length ? nextIndex : -1;
    },

    resetPlayer() {
        this.currentIndex = -1;
        this.els.npTitle.textContent = 'Select a song';
        this.els.npChapter.textContent = '';
        this.els.progressFill.style.width = '0%';
        this.els.progressInput.value = 0;
        this.els.timeCurrent.textContent = '0:00';
        this.els.timeTotal.textContent = '0:00';
        this.tracks.forEach(t => t.row.classList.remove('playing', 'is-playing'));
        this.updatePlayState(false);
        this.updateLyrics(null);
    },

    updatePlayState(isPlaying) {
        const playIcon = this.els.btnPlay.querySelector('.icon-play');
        const pauseIcon = this.els.btnPlay.querySelector('.icon-pause');

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
            const row = this.tracks[this.currentIndex].row;
            if (isPlaying) {
                row.classList.add('is-playing');
            } else {
                row.classList.remove('is-playing');
            }
        }
    },

    // =========================================
    // Shuffle & Repeat
    // =========================================

    toggleShuffle() {
        this.shuffle = !this.shuffle;
        this.els.btnShuffle.classList.toggle('active', this.shuffle);

        if (this.shuffle) {
            this.generateShuffleOrder();
            this.els.btnShuffle.title = 'Shuffle: On';
        } else {
            this.shuffleOrder = [];
            this.els.btnShuffle.title = 'Shuffle: Off';
        }
    },

    toggleRepeat() {
        const modes = ['none', 'all', 'one'];
        const current = modes.indexOf(this.repeat);
        this.repeat = modes[(current + 1) % modes.length];

        const btn = this.els.btnRepeat;
        const badge = this.els.repeatBadge;

        switch (this.repeat) {
            case 'none':
                btn.classList.remove('active');
                badge.style.display = 'none';
                btn.title = 'Repeat: Off';
                break;
            case 'all':
                btn.classList.add('active');
                badge.style.display = 'none';
                btn.title = 'Repeat: All';
                break;
            case 'one':
                btn.classList.add('active');
                badge.style.display = 'flex';
                btn.title = 'Repeat: One';
                break;
        }
    },

    // =========================================
    // Volume
    // =========================================

    adjustVolume(delta) {
        const current = Math.round(this.audio.volume * 100);
        const next = Math.max(0, Math.min(100, current + delta));
        this.audio.volume = next / 100;
        this.audio.muted = false;
        this.els.volumeInput.value = next;
        localStorage.setItem('wop-music-volume', next);
        this.updateVolumeIcon();
    },

    updateVolumeIcon() {
        const volOn = this.els.btnVolume.querySelector('.icon-vol-on');
        const volMute = this.els.btnVolume.querySelector('.icon-vol-mute');

        if (this.audio.muted || this.audio.volume === 0) {
            volOn.style.display = 'none';
            volMute.style.display = 'block';
        } else {
            volOn.style.display = 'block';
            volMute.style.display = 'none';
        }
    },

    // =========================================
    // Lyrics
    // =========================================

    toggleLyrics() {
        const wrapper = this.els.lyricsWrapper;
        const isOpen = wrapper.classList.toggle('open');
        this.els.lyricsToggle.setAttribute('aria-expanded', isOpen);
        this.els.lyricsArrow.innerHTML = isOpen ? '&#9650;' : '&#9660;';
    },

    updateLyrics(track) {
        if (!this.els.lyricsContent) return;

        if (track) {
            // Update heading with song title
            this.els.lyricsHeading.textContent = track.title;

            if (track.lyrics) {
                this.els.lyricsContent.innerHTML = track.lyrics;
            } else {
                this.els.lyricsContent.innerHTML = '<p class="no-lyrics">Lyrics not yet available for this testimony.</p>';
            }

            // Show alt note when playing an alternate version
            if (this.els.lyricsAltNote) {
                this.els.lyricsAltNote.style.display = track.label ? 'block' : 'none';
            }
        } else {
            // No track selected
            this.els.lyricsHeading.textContent = 'Select a song to view lyrics';
            this.els.lyricsContent.innerHTML = '<p class="no-lyrics">Choose a track from the playlist below to begin listening.</p>';
            if (this.els.lyricsAltNote) {
                this.els.lyricsAltNote.style.display = 'none';
            }
        }
    },

    // =========================================
    // Helpers
    // =========================================

    formatTime(seconds) {
        if (!seconds || !isFinite(seconds)) return '0:00';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return m + ':' + String(s).padStart(2, '0');
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    MusicPlayer.init();
});

window.MusicPlayer = MusicPlayer;
