/**
 * WORDS OF PLAINNESS - Reading Progress Sync
 * ============================================
 *
 * Syncs reading progress (scroll position, bookmarks, completion status)
 * to the Django API for authenticated users. Falls back to localStorage
 * when offline or unauthenticated.
 */

const ReadingProgress = {
    chapterSlug: null,
    config: null,
    lastScrollPosition: 0,
    lastSentence: null,
    saveInterval: null,
    hasSentInProgress: false,
    hasSentCompleted: false,
    scrollDirty: false,
    autoDismissTimer: null,

    init(config) {
        this.config = config;
        this.chapterSlug = config.id;

        if (!this.chapterSlug) return;

        if (window.API?.isAuthenticated()) {
            this.loadProgress();
        }

        this.setupScrollTracking();
        this.setupUnload();
        this.enhanceBookmark();
    },

    // =========================================
    // Load Progress
    // =========================================

    async loadProgress() {
        try {
            const data = await window.API.getProgress(this.chapterSlug);
            this.handleLoadedProgress(data);
            this.mergeLocalStorage(data);
        } catch (e) {
            if (e.status === 404) return;
            console.warn('Could not load progress:', e);
            this.loadFromLocalStorage();
        }
    },

    handleLoadedProgress(data) {
        if (!data) return;

        if (data.scroll_position > 5) {
            const label = data.bookmark_label || 'where you left off';
            this.showResumeBanner(label, data.scroll_position);
        }
    },

    // =========================================
    // Scroll Tracking
    // =========================================

    setupScrollTracking() {
        window.addEventListener('scroll', () => {
            this.updateScrollData();
        });

        this.saveInterval = setInterval(() => {
            if (this.scrollDirty && window.API?.isAuthenticated()) {
                this.saveScrollPosition();
                this.scrollDirty = false;
            }
        }, 30000);
    },

    updateScrollData() {
        const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (scrollHeight <= 0) return;

        const percent = Math.round((window.scrollY / scrollHeight) * 100);
        this.lastScrollPosition = percent;
        this.lastSentence = this.findNearestSentence();
        this.scrollDirty = true;

        if (!this.hasSentInProgress && percent > 5 && window.API?.isAuthenticated()) {
            this.hasSentInProgress = true;
            this.patchProgress({ status: 'in_progress' });
        }

        if (!this.hasSentCompleted && percent > 90 && window.API?.isAuthenticated()) {
            this.hasSentCompleted = true;
            this.patchProgress({ status: 'completed' });
        }
    },

    findNearestSentence() {
        const sentences = document.querySelectorAll('.sentence[data-index]');
        let nearest = null;
        let minDistance = Infinity;

        for (const el of sentences) {
            const rect = el.getBoundingClientRect();
            const distance = Math.abs(rect.top);
            if (distance < minDistance) {
                minDistance = distance;
                nearest = el.dataset.index;
            }
        }
        return nearest;
    },

    findNearestHeading() {
        const headings = document.querySelectorAll('.chapter-content h2, .chapter-reading h2');
        let label = null;
        const scrollY = window.scrollY;

        for (const h of headings) {
            if (h.offsetTop <= scrollY + 200) {
                label = h.textContent.trim();
            }
        }
        return label;
    },

    async saveScrollPosition() {
        const payload = {
            scroll_position: this.lastScrollPosition,
            last_sentence: this.lastSentence
        };

        try {
            await window.API.updateProgress(this.chapterSlug, payload);
        } catch (e) {
            this.saveToLocalStorage(payload);
        }
    },

    async patchProgress(data) {
        try {
            await window.API.updateProgress(this.chapterSlug, data);
        } catch (e) {
            console.warn('Progress patch failed:', e);
        }
    },

    // =========================================
    // Page Unload
    // =========================================

    setupUnload() {
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                this.sendBeaconProgress();
            }
        });

        window.addEventListener('beforeunload', () => {
            this.sendBeaconProgress();
        });
    },

    sendBeaconProgress() {
        if (!window.API?.isAuthenticated() || !this.chapterSlug) return;

        const payload = JSON.stringify({
            scroll_position: this.lastScrollPosition,
            last_sentence: this.lastSentence
        });

        const url = `${window.API.baseUrl}/progress/${encodeURIComponent(this.chapterSlug)}/`;

        // Use fetch with keepalive (supports auth headers, unlike sendBeacon)
        try {
            fetch(url, {
                method: 'PATCH',
                headers: window.API.getHeaders(),
                body: payload,
                keepalive: true
            });
        } catch (e) { /* ignore unload errors */ }
    },

    // =========================================
    // Bookmark Enhancement
    // =========================================

    enhanceBookmark() {
        document.addEventListener('wop:bookmark-saved', () => {
            this.onBookmarkSaved();
        });
    },

    onBookmarkSaved() {
        if (!window.API?.isAuthenticated()) {
            this.showToast();
            return;
        }

        const sentence = this.findNearestSentence();
        const label = this.findNearestHeading();

        this.patchProgress({
            bookmark_sentence: sentence,
            bookmark_label: label,
            scroll_position: this.lastScrollPosition
        });

        this.showToast();
    },

    showToast() {
        const toast = document.getElementById('bookmarkToast');
        if (!toast) return;

        toast.classList.remove('hidden');
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hidden');
        }, 2000);
    },

    // =========================================
    // Resume Banner
    // =========================================

    showResumeBanner(label, scrollPercent) {
        const banner = document.getElementById('progressResumeBanner');
        const text = document.getElementById('progressResumeText');
        if (!banner || !text) return;

        text.textContent = `Welcome back! Resume reading from "${label}"?`;
        banner.classList.remove('hidden');

        const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
        const targetScroll = (scrollPercent / 100) * scrollHeight;

        document.getElementById('progressResumeYes')?.addEventListener('click', () => {
            window.scrollTo({ top: targetScroll, behavior: 'smooth' });
            this.dismissResumeBanner();
        }, { once: true });

        document.getElementById('progressResumeNo')?.addEventListener('click', () => {
            this.dismissResumeBanner();
        }, { once: true });

        document.getElementById('progressResumeReflect')?.addEventListener('click', () => {
            this.dismissResumeBanner();
            document.getElementById('reflectionSection')?.scrollIntoView({ behavior: 'smooth' });
            setTimeout(() => document.getElementById('reflection1')?.focus(), 800);
        }, { once: true });

        this.autoDismissTimer = setTimeout(() => this.dismissResumeBanner(), 10000);
    },

    dismissResumeBanner() {
        const banner = document.getElementById('progressResumeBanner');
        if (banner) banner.classList.add('hidden');
        if (this.autoDismissTimer) {
            clearTimeout(this.autoDismissTimer);
            this.autoDismissTimer = null;
        }
    },

    // =========================================
    // localStorage Fallback
    // =========================================

    saveToLocalStorage(data) {
        try {
            const key = `wop-progress-${this.chapterSlug}`;
            const existing = JSON.parse(localStorage.getItem(key) || '{}');
            const merged = { ...existing, ...data, _ts: Date.now() };
            localStorage.setItem(key, JSON.stringify(merged));
        } catch (e) { /* storage full or unavailable */ }
    },

    loadFromLocalStorage() {
        try {
            const key = `wop-progress-${this.chapterSlug}`;
            const data = JSON.parse(localStorage.getItem(key) || 'null');
            if (data && data.scroll_position > 5) {
                this.showResumeBanner(data.bookmark_label || 'where you left off', data.scroll_position);
            }
        } catch (e) { /* ignore */ }
    },

    async mergeLocalStorage(apiData) {
        try {
            const key = `wop-progress-${this.chapterSlug}`;
            const local = JSON.parse(localStorage.getItem(key) || 'null');
            if (!local || !local._ts) return;

            // If local data is newer, push it to API
            const patch = {};
            if (local.scroll_position != null && local.scroll_position > (apiData.scroll_position || 0)) {
                patch.scroll_position = local.scroll_position;
                patch.last_sentence = local.last_sentence;
            }
            if (local.bookmark_sentence) {
                patch.bookmark_sentence = local.bookmark_sentence;
                patch.bookmark_label = local.bookmark_label;
            }

            if (Object.keys(patch).length > 0) {
                await window.API.updateProgress(this.chapterSlug, patch);
            }

            localStorage.removeItem(key);
        } catch (e) {
            console.warn('Failed to merge localStorage progress:', e);
        }
    }
};

window.ReadingProgress = ReadingProgress;
