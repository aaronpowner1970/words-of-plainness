/**
 * WORDS OF PLAINNESS — Audio Synchronization (Section Architecture)
 * =================================================================
 *
 * Section-based audio player. Each chapter is divided into prose sections
 * corresponding to RJW pause points. Each section has its own MP3 file and
 * its own timestamp JSON. After each prose section ends, a separate cue file
 * plays, then the RJW panel opens. The reader resumes to the next section.
 *
 * STATE MACHINE:
 *   IDLE → PLAYING_PROSE → PLAYING_CUE → RJW_OPEN → PLAYING_PROSE (next) → ...
 *
 * TIMESTAMP JSON FORMAT (per section, produced by build_section_timestamps.py):
 *   "p{N}"  : float   — start time of paragraph N within this section file
 *   "s{N}"  : integer — paragraph index for sentence N (click-to-seek mapping)
 *
 * HIGHLIGHTING:
 *   Paragraph-level. On timeupdate, find the largest p{N} timestamp ≤ currentTime,
 *   highlight the [data-paragraph="N"] element. Sentences within that paragraph
 *   are highlighted implicitly (they live inside the paragraph element).
 *
 * CLICK-TO-SEEK:
 *   Clicking any sentence span looks up its paragraph via s{N} → paragraphIdx,
 *   then seeks to p{paragraphIdx}. If the sentence belongs to a different section,
 *   that section is loaded first; seek fires on the 'canplay' event (not a
 *   fragile setTimeout) to guarantee the file is ready before seeking.
 *
 * FRONTMATTER SECTIONS ARRAY:
 *   sections:
 *     - id: "pause-humility"
 *       prose: NR_09_S01_Invocation_Humility.mp3
 *       cue: NR_09_CUE_01_Humility.mp3
 *       paragraphs: [1, 23]
 *       timestamps: chapter-09-s01.json
 */

const AudioSync = {

    /* ── Configuration ──────────────────────────────────────────────── */

    CDN_BASE: 'https://media.wordsofplainness.org/web/',

    /* ── State ──────────────────────────────────────────────────────── */

    sections: [],           // Array of section objects from frontmatter
    allTimestamps: {},      // { sectionId: { p1: t, s0: paraIdx, ... } }

    currentSectionIndex: -1,
    state: 'IDLE',          // IDLE | PLAYING_PROSE | PLAYING_CUE | RJW_OPEN

    audioPlayer: null,      // The single <audio id="chapterAudio"> element

    // Per-section paragraph data (rebuilt on section load)
    paragraphTimes: [],     // [[paraIdx, startTime], ...] sorted ascending by startTime
    sentenceToPara: {},     // { sentenceIdx: paragraphIdx } — section scope only
    paragraphRange: [0, 0], // [firstPara, lastPara] inclusive

    currentParagraph: -1,
    autoScrollEnabled: true,

    // Pending seek: used when switching sections via click-to-seek.
    // Cleared once the canplay event fires and the seek is executed.
    _pendingSeekTime: null,

    /* ── Init ───────────────────────────────────────────────────────── */

    /**
     * Initialize section-based audio sync.
     * Called from ChapterManager.initAudioSync() when sections data is present.
     */
    initSections(sections, timestamps, audioPlayer) {
        if (!sections || sections.length === 0) {
            console.log('AudioSync: No sections defined — sync disabled');
            return;
        }
        if (!audioPlayer) {
            console.log('AudioSync: No audio player found — sync disabled');
            return;
        }

        this.sections      = sections;
        this.allTimestamps = timestamps || {};
        this.audioPlayer   = audioPlayer;
        this.state         = 'IDLE';
        this.currentSectionIndex = -1;
        this._pendingSeekTime    = null;

        this._setupPlayerListeners();
        this._makeClickable();
        this.loadSection(0);

        console.log(
            `AudioSync (sections): ${sections.length} sections, ` +
            `${Object.keys(timestamps).length} timestamp sets loaded`
        );
    },

    /**
     * Legacy init path for chapters without sections (Chs 1–8).
     * cueFile: filename only (CDN base prepended automatically)
     * pauseId: the pause-point id to pass to RJW.openModal()
     */
    init(timestamps, audioPlayer, cueFile, pauseId) {
        if (!timestamps || !audioPlayer) return;
        this.audioPlayer = audioPlayer;
        this._legacyInit(timestamps, cueFile, pauseId);
    },

    /* ── Section Loading ────────────────────────────────────────────── */

    loadSection(index) {
        if (index >= this.sections.length) {
            console.log('AudioSync: All sections complete');
            this.state = 'IDLE';
            return;
        }

        const section = this.sections[index];
        this.currentSectionIndex = index;
        this.currentParagraph    = -1;
        this.state               = 'PLAYING_PROSE';

        const sectionTimestamps = this.allTimestamps[section.id] || {};
        this._buildSectionTimestamps(sectionTimestamps);
        this.paragraphRange = section.paragraphs || [0, 9999];

        // Swap src — canplay listener below will fire the pending seek if one exists
        const src = this.CDN_BASE + section.prose;
        this.audioPlayer.src = src;
        this.audioPlayer.load();

        console.log(
            `AudioSync: Section ${index + 1}/${this.sections.length} — ${section.id} ` +
            `| paras ${this.paragraphRange[0]}–${this.paragraphRange[1]} ` +
            `| ${Object.keys(sectionTimestamps).length} ts keys`
        );
    },

    _buildSectionTimestamps(timestamps) {
        this.paragraphTimes = [];
        this.sentenceToPara = {};

        for (const [key, value] of Object.entries(timestamps)) {
            if (key.startsWith('p')) {
                const idx = parseInt(key.slice(1), 10);
                if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
            } else if (key.startsWith('s')) {
                const sentIdx = parseInt(key.slice(1), 10);
                if (!isNaN(sentIdx)) this.sentenceToPara[sentIdx] = parseInt(value, 10);
            }
        }

        // Sort by time ascending so getParagraphAtTime() can linear-scan
        this.paragraphTimes.sort((a, b) => a[1] - b[1]);

        // Force the first paragraph's timestamp to 0.0 — any silence pre-roll
        // in the assembled file shouldn't delay the first highlight.
        if (this.paragraphTimes.length > 0) {
            this.paragraphTimes[0] = [this.paragraphTimes[0][0], 0.0];
        }

        const hasRealData = this.paragraphTimes.some(([, t]) => t > 0);
        if (!hasRealData && this.paragraphTimes.length > 0) {
            console.warn(
                'AudioSync: All paragraph timestamps are 0 — timestamp JSON may be a placeholder. ' +
                'Run build_section_timestamps.py to populate.'
            );
        }
    },

    /* ── Player Event Listeners ─────────────────────────────────────── */

    _setupPlayerListeners() {
        // timeupdate — paragraph highlighting
        this.audioPlayer.addEventListener('timeupdate', () => this._onTimeUpdate());

        // ended — advance state machine
        this.audioPlayer.addEventListener('ended', () => this._onEnded());

        // canplay — fire any pending cross-section seek
        // This is the reliable hook for "file is loaded enough to seek"
        this.audioPlayer.addEventListener('canplay', () => {
            if (this._pendingSeekTime !== null) {
                const t = this._pendingSeekTime;
                this._pendingSeekTime = null;
                this._execSeek(t);
            }
        });

        // play — if resuming after RJW was dismissed without Continue
        this.audioPlayer.addEventListener('play', () => {
            if (this.state === 'RJW_OPEN') {
                this.state = 'PLAYING_PROSE';
            }
        });

        // pause — keep highlight visible (no action needed)
        // seeking — browser fires this; no action needed
    },

    /* ── Sentence Click-to-Seek ─────────────────────────────────────── */

    _makeClickable() {
        document.querySelectorAll('.sentence[data-index]').forEach(el => {
            el.classList.add('clickable');
            el.addEventListener('click', (e) => {
                // Don't intercept clicks on scripture links inside sentence spans
                if (e.target.closest('a')) return;
                this._onSentenceClick(el);
            });
        });
    },

    _onSentenceClick(sentenceEl) {
        const sentIdx = parseInt(sentenceEl.dataset.index, 10);

        // ── Case 1: sentence is in the current section ─────────────────
        if (sentIdx in this.sentenceToPara) {
            const paraIdx = this.sentenceToPara[sentIdx];
            const entry   = this.paragraphTimes.find(([idx]) => idx === paraIdx);
            if (entry) {
                this._seekWithinCurrentSection(entry[1]);
                return;
            }
        }

        // ── Case 1b: legacy bare-numeric format (Chs 1-6) ──────────────
        // sentenceToPara is empty; sentence index == paragraph index directly.
        if (this.sentenceToPara && Object.keys(this.sentenceToPara).length === 0) {
            const entry = this.paragraphTimes.find(([idx]) => idx === sentIdx);
            if (entry) {
                this._seekWithinCurrentSection(entry[1]);
                return;
            }
        }

        // ── Case 2: sentence is in a different section ──────────────────
        this._seekToSentenceAcrossSections(sentIdx);
    },

    _seekWithinCurrentSection(time) {
        this.state = 'PLAYING_PROSE';
        this._showPlayer();
        this.audioPlayer.currentTime = time;
        this._ensurePlaying();
    },

    _seekToSentenceAcrossSections(sentIdx) {
        const sentKey = `s${sentIdx}`;

        for (let i = 0; i < this.sections.length; i++) {
            const sectionTimestamps = this.allTimestamps[this.sections[i].id] || {};

            if (sentKey in sectionTimestamps) {
                const paraIdx  = sectionTimestamps[sentKey];
                const paraKey  = `p${paraIdx}`;
                const paraTime = parseFloat(sectionTimestamps[paraKey] ?? 0);

                if (i === this.currentSectionIndex) {
                    // Same section but sentenceToPara was stale — just seek
                    this._seekWithinCurrentSection(paraTime);
                } else {
                    // Different section — load it, queue the seek for canplay
                    this._pendingSeekTime = paraTime;
                    this.loadSection(i);
                    this._showPlayer();
                    // _execSeek() will fire from the canplay listener
                }
                return;
            }
        }

        console.warn(`AudioSync: sentence ${sentIdx} not found in any section timestamps`);
    },

    _execSeek(time) {
        this.state = 'PLAYING_PROSE';
        this.audioPlayer.currentTime = time;
        this._ensurePlaying();
    },

    _showPlayer() {
        const playerEl = document.getElementById('audioPlayer');
        if (playerEl && !playerEl.classList.contains('visible')) {
            playerEl.classList.add('visible');
        }
    },

    _ensurePlaying() {
        if (this.audioPlayer.paused) {
            this.audioPlayer.play().catch(() => {});
            if (window.ChapterManager) {
                ChapterManager.isPlaying = true;
                document.getElementById('playIcon')  ?.style && (document.getElementById('playIcon').style.display  = 'none');
                document.getElementById('pauseIcon') ?.style && (document.getElementById('pauseIcon').style.display = 'block');
            }
        }
    },

    /* ── Playback Events ────────────────────────────────────────────── */

    _onTimeUpdate() {
        if (this.state !== 'PLAYING_PROSE') return;

        const currentTime    = this.audioPlayer.currentTime;
        const paragraphIndex = this._getParagraphAtTime(currentTime);

        if (paragraphIndex !== this.currentParagraph) {
            this._highlightParagraph(paragraphIndex);
            this.currentParagraph = paragraphIndex;
        }
    },

    _onEnded() {
        this._clearHighlight();

        if (this.state === 'PLAYING_PROSE') {
            this._playCue();
        } else if (this.state === 'PLAYING_CUE') {
            this._openRJW();
        } else {
            this.state = 'IDLE';
        }
    },

    _playCue() {
        const section = this.sections[this.currentSectionIndex];
        if (!section || !section.cue) {
            this._openRJW();
            return;
        }

        this.state = 'PLAYING_CUE';

        // Lock to 1.0x during the contemplative cue — restore after
        this._savedPlaybackRate = this.audioPlayer.playbackRate;
        this.audioPlayer.playbackRate = 1.0;

        const src = this.CDN_BASE + section.cue;
        this.audioPlayer.src = src;
        this.audioPlayer.load();
        this.audioPlayer.play().catch(err => {
            console.warn('AudioSync: Cue playback failed:', err);
            this._openRJW();
        });

        console.log(`AudioSync: Cue — ${section.cue}`);
    },

    _openRJW() {
        this.state = 'RJW_OPEN';
        const section = this.sections[this.currentSectionIndex];

        if (window.ChapterManager) {
            ChapterManager.pause();
        } else {
            this.audioPlayer.pause();
        }

        if (this._savedPlaybackRate) {
            this.audioPlayer.playbackRate = this._savedPlaybackRate;
            this._savedPlaybackRate = null;
        }

        if (window.RJW && section && section.id) {
            console.log(`AudioSync: RJW — ${section.id}`);
            RJW.openModal(section.id, 'reflect');
        }
    },

    /**
     * Called by RJW.closeModal() when the reader clicks Continue.
     */
    advanceSection() {
        const nextIndex = this.currentSectionIndex + 1;
        if (nextIndex >= this.sections.length) {
            console.log('AudioSync: Chapter complete');
            this.state = 'IDLE';
            return;
        }

        this.loadSection(nextIndex);

        setTimeout(() => {
            if (window.ChapterManager) {
                ChapterManager.play();
            } else {
                this.audioPlayer.play().catch(() => {});
            }
        }, 300);
    },

    /**
     * Replay current section's cue. Can be called from "Hear again" button.
     */
    replayCue() {
        const section = this.sections[this.currentSectionIndex];
        if (!section || !section.cue) return;
        this.state = 'PLAYING_CUE';
        this.audioPlayer.src = this.CDN_BASE + section.cue;
        this.audioPlayer.load();
        this.audioPlayer.playbackRate = 1.0;
        this.audioPlayer.play().catch(() => {});
    },

    /* ── Paragraph Highlighting ─────────────────────────────────────── */

    _getParagraphAtTime(time) {
        // paragraphTimes is sorted ascending by time.
        // Find the last entry whose startTime ≤ currentTime.
        let last = -1;
        for (const [paraIdx, startTime] of this.paragraphTimes) {
            if (startTime <= time) {
                last = paraIdx;
            } else {
                break;
            }
        }
        return last;
    },

    _highlightParagraph(paragraphIndex) {
        this._clearHighlight();
        if (paragraphIndex < 0) return;

        // Section/Ch7+ architecture: highlight by data-paragraph
        let el = document.querySelector(`[data-paragraph="${paragraphIndex}"]`);

        // Legacy bare-numeric architecture (Chs 1-6): no data-paragraph,
        // fall back to highlighting the sentence span by data-index
        if (!el) {
            el = document.querySelector(`[data-index="${paragraphIndex}"]`);
        }

        if (!el) return;

        // Don't highlight heading spans inside h2/h3
        if (el.tagName === 'SPAN' && el.closest('h2, h3')) return;

        el.classList.add('highlighted');

        if (this.autoScrollEnabled) {
            this._scrollToElement(el);
        }
    },

    _clearHighlight() {
        document.querySelectorAll('[data-paragraph].highlighted, [data-index].highlighted')
            .forEach(el => el.classList.remove('highlighted'));
    },

    _scrollToElement(el) {
        const rect = el.getBoundingClientRect();
        const vh   = window.innerHeight;
        if (rect.top < vh * 0.3 || rect.bottom > vh * 0.7) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    toggleAutoScroll() {
        this.autoScrollEnabled = !this.autoScrollEnabled;
        return this.autoScrollEnabled;
    },

    /* ── Legacy Single-File Support (Chs 1–8) ──────────────────────── */

    _legacyInit(timestamps, cueFile, pauseId) {
        this.paragraphTimes   = [];
        this.sentenceToPara   = {};
        this._legacyCueFile   = cueFile  || null;
        this._legacyPauseId   = pauseId  || null;

        // Handle three legacy timestamp formats:
        // Format A (Chs 1-2): Array of {index, start, end} objects
        // Format B (Chs 3-6): Object with bare numeric string keys {"0": time, "1": time}
        // Format C (Chs 7-8): Object with p{N}/s{N} keys

        if (Array.isArray(timestamps)) {
            // Format A — array of {index, start, end}
            for (const entry of timestamps) {
                if (entry && typeof entry.index === 'number' && typeof entry.start === 'number') {
                    this.paragraphTimes.push([entry.index, entry.start]);
                }
            }
        } else {
            for (const [key, value] of Object.entries(timestamps)) {
                if (key.startsWith('p')) {
                    // Format C — paragraph time
                    const idx = parseInt(key.slice(1), 10);
                    if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
                } else if (key.startsWith('s')) {
                    // Format C — sentence-to-paragraph map
                    const sentIdx = parseInt(key.slice(1), 10);
                    if (!isNaN(sentIdx)) this.sentenceToPara[sentIdx] = parseInt(value, 10);
                } else {
                    // Format B — bare numeric key, value is the timestamp directly
                    const idx = parseInt(key, 10);
                    if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
                }
            }
        }

        this.paragraphTimes.sort((a, b) => a[1] - b[1]);

        if (this.paragraphTimes.length === 0) {
            console.log('AudioSync (legacy): No timestamps — sync disabled');
            return;
        }

        const allZero = this.paragraphTimes.every(([, t]) => t === 0);
        if (allZero) {
            console.log('AudioSync (legacy): All timestamps are placeholder zeros — sync disabled');
            return;
        }

        this.state = 'PLAYING_PROSE';
        this._makeClickable();
        this._setupLegacyListeners();

        console.log(`AudioSync (legacy): ${this.paragraphTimes.length} paragraph timestamps`);
    },

    _setupLegacyListeners() {
        this.audioPlayer.addEventListener('timeupdate', () => {
            if (this.state !== 'PLAYING_PROSE') return;
            const paragraphIndex = this._getParagraphAtTime(this.audioPlayer.currentTime);
            if (paragraphIndex !== this.currentParagraph) {
                this._highlightParagraph(paragraphIndex);
                this.currentParagraph = paragraphIndex;
            }
        });

        this.audioPlayer.addEventListener('ended', () => {
            this._clearHighlight();

            if (this.state === 'PLAYING_PROSE' && this._legacyCueFile) {
                // Play cue file then open RJW — same flow as section architecture
                this.state = 'PLAYING_CUE';
                this._savedPlaybackRate = this.audioPlayer.playbackRate;
                this.audioPlayer.playbackRate = 1.0;
                this.audioPlayer.src = this.CDN_BASE + this._legacyCueFile;
                this.audioPlayer.load();
                this.audioPlayer.play().catch(() => this._legacyOpenRJW());
            } else if (this.state === 'PLAYING_CUE') {
                this._legacyOpenRJW();
            }
            // If no cue file, just clear highlight and stop (original behaviour)
        });
    },

    _legacyOpenRJW() {
        this.state = 'RJW_OPEN';
        if (this._savedPlaybackRate) {
            this.audioPlayer.playbackRate = this._savedPlaybackRate;
            this._savedPlaybackRate = null;
        }
        if (window.ChapterManager) ChapterManager.pause();
        if (window.RJW && this._legacyPauseId) {
            RJW.openModal(this._legacyPauseId, 'reflect');
        }
    },
};

window.AudioSync = AudioSync;
