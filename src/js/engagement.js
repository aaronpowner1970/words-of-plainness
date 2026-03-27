/**
 * WORDS OF PLAINNESS — Engagement Event Tracking
 */
const Engagement = {
    STORAGE_KEY: 'wop-engagement-queue',
    API_ENDPOINT: '/events/',

    track(eventType, data = {}) {
        const event = {
            event_type: eventType,
            chapter_slug: data.chapter_slug || this._currentChapter(),
            metadata: { ...data },
            client_ts: new Date().toISOString()
        };
        delete event.metadata.chapter_slug;
        if (window.API?.isAuthenticated()) {
            this._post([event]);
        } else {
            this._enqueue(event);
        }
    },

    _enqueue(event) {
        try {
            const queue = this._loadQueue();
            queue.push(event);
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(queue.slice(-100)));
        } catch (e) {}
    },

    _loadQueue() {
        try { return JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '[]'); }
        catch (e) { return []; }
    },

    _clearQueue() {
        try { localStorage.removeItem(this.STORAGE_KEY); } catch (e) {}
    },

    async flushQueue() {
        const queue = this._loadQueue();
        if (queue.length === 0) return;
        try {
            await this._post(queue);
            this._clearQueue();
        } catch (e) {
            console.warn('Engagement queue flush failed:', e);
        }
    },

    async _post(events) {
        if (!window.API?.baseUrl) return;
        try {
            await window.API.request(this.API_ENDPOINT, {
                method: 'POST',
                body: JSON.stringify({ events })
            });
        } catch (e) {
            events.forEach(ev => this._enqueue(ev));
        }
    },

    _currentChapter() {
        return window.ChapterManager?.config?.id || '';
    },

    initChapterPage() {
        this.track('page_view', {
            is_authenticated: window.API?.isAuthenticated() || false
        });
        document.addEventListener('wop:auth-login', () => this.flushQueue());
    }
};
window.Engagement = Engagement;
