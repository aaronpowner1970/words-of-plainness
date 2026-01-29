/**
 * WORDS OF PLAINNESS — Music Player
 * ==================================
 * Full playlist player for the Music page.
 */

const MusicPlayer = {
    // State
    audio: null,
    tracks: [],
    currentIndex: -1,
    shuffle: false,
    repeat: 'none', // 'none', 'all', 'one'
    shuffleOrder: [],

    // DOM refs
    els: {},

    init() {
        this.audio = document.getElementById('musicAudio');
        if (!this.audio) return;

        this.cacheElements();
        this.loadTracks();
        this.loadVolume();
        this.bindEvents();
        this.loadDurations();

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
            table: id('playlistTable')
        };
    },

    loadTracks() {
        const rows = document.querySelectorAll('.playlist-row');
        this.tracks = Array.from(rows).map((row, i) => ({
            index: i,
            src: row.dataset.src,
            title: row.dataset.title,
            chapter: row.dataset.chapter,
            chapterUrl: row.dataset.chapterUrl,
            row: row
        }));
    },

    loadVolume() {
        const saved = localStorage.getItem('wop-music-volume');
        const vol = saved !== null ? parseInt(saved, 10) : 80;
        this.audio.volume = vol / 100;
        this.els.volumeInput.value = vol;
    },

    loadDurations() {
        // Preload metadata for each track to get duration
        this.tracks.forEach((track) => {
            const tempAudio = new Audio();
            tempAudio.preload = 'metadata';
            tempAudio.addEventListener('loadedmetadata', () => {
                const cell = track.row.querySelector('[data-duration]');
                if (cell) {
                    cell.textContent = this.formatTime(tempAudio.duration);
                }
            });
            tempAudio.src = track.src;
        });
    },

    bindEvents() {
        // Audio events
        this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audio.addEventListener('loadedmetadata', () => this.onMetadataLoaded());
        this.audio.addEventListener('ended', () => this.onTrackEnded());
        this.audio.addEventListener('play', () => this.updatePlayState(true));
        this.audio.addEventListener('pause', () => this.updatePlayState(false));

        // Control buttons
        this.els.btnPlay.addEventListener('click', () => this.togglePlay());
        this.els.btnPrev.addEventListener('click', () => this.prev());
        this.els.btnNext.addEventListener('click', () => this.next());
        this.els.btnShuffle.addEventListener('click', () => this.toggleShuffle());
        this.els.btnRepeat.addEventListener('click', () => this.toggleRepeat());

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
            // Row click (except links and buttons)
            track.row.addEventListener('click', (e) => {
                if (e.target.closest('a') || e.target.closest('.btn-download')) return;
                this.playTrack(i);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Don't capture when typing in inputs
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

    playTrack(index) {
        if (index < 0 || index >= this.tracks.length) return;

        const track = this.tracks[index];
        const wasSameTrack = this.currentIndex === index;

        this.currentIndex = index;

        if (wasSameTrack && this.audio.src) {
            // Toggle play/pause on same track
            this.togglePlay();
            return;
        }

        this.audio.src = track.src;
        this.audio.play().catch(() => {});

        // Update Now Playing
        this.els.npTitle.textContent = track.title;
        this.els.npChapter.textContent = track.chapter;

        // Highlight row
        this.tracks.forEach(t => {
            t.row.classList.remove('playing', 'is-playing');
        });
        track.row.classList.add('playing', 'is-playing');

        // Scroll row into view if needed
        track.row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    togglePlay() {
        if (this.currentIndex === -1) {
            // Nothing loaded — play first track
            this.playTrack(this.shuffle ? this.getShuffledIndex(0) : 0);
            return;
        }

        if (this.audio.paused) {
            this.audio.play().catch(() => {});
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
    },

    onTrackEnded() {
        if (this.repeat === 'one') {
            this.audio.currentTime = 0;
            this.audio.play().catch(() => {});
            return;
        }

        const nextIndex = this.getAdjacentIndex(1);
        if (nextIndex !== -1) {
            this.playTrack(nextIndex);
        } else {
            // Playlist ended
            this.updatePlayState(false);
        }
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

        // Update row icon state
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
