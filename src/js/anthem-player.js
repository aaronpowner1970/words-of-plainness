/**
 * WORDS OF PLAINNESS - Anthem Player
 * ====================================
 * 
 * Homepage anthem player for "The Marks of Your Worth"
 * Handles play/pause with HTML5 Audio, waveform animation,
 * progress tracking, and lyrics dropdown toggle.
 * 
 * Follows the DOMContentLoaded pattern established in main.js.
 */

document.addEventListener('DOMContentLoaded', () => {
    const playArea = document.getElementById('anthemPlayArea');
    const playBtn = document.getElementById('anthemPlayBtn');
    const audio = document.getElementById('anthemAudio');
    const lyricsToggle = document.getElementById('anthemLyricsToggle');
    const lyricsBody = document.getElementById('anthemLyricsBody');
    const lyricsToggleText = document.getElementById('anthemLyricsToggleText');
    const currentTimeEl = document.getElementById('anthemTimeCurrent');
    const progressFill = document.getElementById('anthemProgressFill');

    if (!playArea || !playBtn || !audio) return;

    let animationFrames = [];

    // ── Format time as m:ss ──────────────────
    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    // ── Waveform animation ───────────────────
    function startWaveformAnimation() {
        const bars = playArea.querySelectorAll('.anthem-waveform-bars span');
        bars.forEach(bar => {
            const pulse = () => {
                if (audio.paused) return;
                bar.style.height = (18 + Math.random() * 82) + '%';
                bar.style.opacity = (0.35 + Math.random() * 0.65).toString();
                const timeout = setTimeout(pulse, 180 + Math.random() * 350);
                animationFrames.push(timeout);
            };
            pulse();
        });
    }

    function stopWaveformAnimation() {
        // Clear all pending timeouts
        animationFrames.forEach(id => clearTimeout(id));
        animationFrames = [];

        // Reset bars to CSS defaults
        const bars = playArea.querySelectorAll('.anthem-waveform-bars span');
        bars.forEach(bar => {
            bar.style.height = '';
            bar.style.opacity = '';
        });
    }

    // ── Play / Pause toggle ──────────────────
    function togglePlay() {
        if (audio.paused) {
            audio.play().then(() => {
                playBtn.classList.add('is-playing');
                startWaveformAnimation();
            }).catch(err => {
                console.log('Anthem playback prevented:', err);
            });
        } else {
            audio.pause();
            playBtn.classList.remove('is-playing');
            stopWaveformAnimation();
        }
    }

    playArea.addEventListener('click', (e) => {
        // Don't trigger if clicking inside lyrics area
        if (e.target.closest('.anthem-lyrics-toggle') || e.target.closest('.anthem-lyrics-body')) return;
        togglePlay();
    });

    // ── Audio progress tracking ──────────────
    audio.addEventListener('timeupdate', () => {
        if (!audio.duration) return;
        const pct = (audio.currentTime / audio.duration) * 100;
        if (progressFill) progressFill.style.width = pct + '%';
        if (currentTimeEl) currentTimeEl.textContent = formatTime(audio.currentTime);
    });

    // ── Audio ended ──────────────────────────
    audio.addEventListener('ended', () => {
        playBtn.classList.remove('is-playing');
        stopWaveformAnimation();
        if (progressFill) progressFill.style.width = '0%';
        if (currentTimeEl) currentTimeEl.textContent = '0:00';
    });

    // ── Lyrics dropdown toggle ───────────────
    if (lyricsToggle && lyricsBody) {
        lyricsToggle.addEventListener('click', (e) => {
            e.stopPropagation(); // prevent play area click
            const isOpen = lyricsToggle.classList.toggle('is-open');
            lyricsBody.classList.toggle('is-open');
            if (lyricsToggleText) {
                lyricsToggleText.textContent = isOpen ? 'Hide Lyrics' : 'View Lyrics';
            }
        });
    }
});

console.log('Words of Plainness - Anthem player loaded');
