/**
 * WORDS OF PLAINNESS - Reflections Manager
 * =========================================
 *
 * Handles saving and loading reflection prompts.
 * - Saves to Django API for authenticated users
 * - Falls back to localStorage for guests
 * - Auto-saves as user types (debounced)
 */

const PROMPT_TITLES = {
    '1': 'What stood out to you?',
    '2': 'Why does it matter to you?',
    '3': 'What will you do?'
};

const Reflections = {
    chapterId: null,    // e.g. "chapter-01-introduction" (matches chapter_slug)
    debounceTimers: {},
    saveDelay: 1000,
    savedIds: {},       // prompt number → API reflection id (for updates)

    init(chapterId) {
        this.chapterId = chapterId;
        this.setupInputListeners();
        this.setupSaveButton();
        this.setupClearButton();

        console.log('[Reflections] Initialized for:', chapterId);
        console.log('[Reflections] API available:', !!window.API);
        console.log('[Reflections] API baseUrl:', window.API?.baseUrl || '(none)');
        console.log('[Reflections] Authenticated:', this.isUserAuthenticated());

        this.loadReflections();
    },

    /**
     * Check if user is authenticated.
     * Uses API.isAuthenticated() if available, with localStorage fallback
     * in case API.init() hasn't run yet.
     */
    isUserAuthenticated() {
        // Primary: check the API client
        if (window.API && window.API.isAuthenticated()) {
            return true;
        }
        // Fallback: check localStorage directly (handles init timing issues)
        const token = localStorage.getItem('wop_access_token')
            || localStorage.getItem('wop-auth-token');
        return !!token;
    },

    setupInputListeners() {
        document.querySelectorAll('.reflection-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const prompt = e.target.dataset.prompt;
                this.debounceSave(prompt, e.target.value);
            });
        });
    },

    debounceSave(prompt, value) {
        if (this.debounceTimers[prompt]) {
            clearTimeout(this.debounceTimers[prompt]);
        }

        this.updateStatus('saving');

        this.debounceTimers[prompt] = setTimeout(() => {
            if (value.trim()) {
                this.saveReflection(prompt, value);
            } else {
                this.updateStatus('default');
            }
        }, this.saveDelay);
    },

    /**
     * Build the API payload matching Django's expected schema.
     */
    buildPayload(prompt, value) {
        return {
            content: value,
            chapter_slug: this.chapterId,
            title: PROMPT_TITLES[prompt] || `Reflection ${prompt}`,
            visibility: 'private'
        };
    },

    async saveReflection(prompt, value) {
        if (!value.trim()) return;

        // Try API if authenticated
        if (this.isUserAuthenticated() && window.API && window.API.baseUrl) {
            try {
                const payload = this.buildPayload(prompt, value);
                console.log('[Reflections] Saving to API...', payload.title);
                const result = await window.API.saveReflection(payload);
                console.log('[Reflections] Reflection saved:', payload.title, result);
                if (result && result.id) {
                    this.savedIds[prompt] = result.id;
                }
                this.updateStatus('saved');
                return;
            } catch (error) {
                console.warn('[Reflections] API save failed, falling back to localStorage:', error.message);
            }
        } else {
            console.log('[Reflections] Not authenticated or API not configured, saving to localStorage');
        }

        // Fallback to localStorage
        this.saveToLocalStorage(prompt, value);
        this.updateStatus('saved-local');
    },

    saveToLocalStorage(prompt, value) {
        const key = `wop-reflection-${this.chapterId}-${prompt}`;
        localStorage.setItem(key, JSON.stringify({
            content: value,
            chapter_slug: this.chapterId,
            title: PROMPT_TITLES[prompt] || `Reflection ${prompt}`,
            prompt: prompt,
            timestamp: Date.now()
        }));
    },

    async loadReflections() {
        // Try API first
        if (this.isUserAuthenticated() && window.API && window.API.baseUrl) {
            try {
                console.log('[Reflections] Loading from API for:', this.chapterId);
                const reflections = await window.API.getReflections(this.chapterId);
                console.log('[Reflections] API returned:', reflections);
                this.populateFromAPI(reflections);
                return;
            } catch (error) {
                console.warn('[Reflections] API load failed, falling back to localStorage:', error.message);
            }
        } else {
            console.log('[Reflections] Not authenticated, loading from localStorage');
        }

        this.loadFromLocalStorage();
    },

    /**
     * Populate inputs from API response.
     * API returns an array or { results: [...] } with { id, title, content, ... }.
     * Match them back to prompt numbers by title.
     */
    populateFromAPI(reflections) {
        // Unwrap paginated response
        if (!Array.isArray(reflections)) {
            if (reflections && Array.isArray(reflections.results)) {
                reflections = reflections.results;
            } else {
                console.log('[Reflections] No reflections found in API response');
                return;
            }
        }

        console.log('[Reflections] Populating', reflections.length, 'reflections from API');

        // Build reverse lookup: title → prompt number
        const titleToPrompt = {};
        for (const [num, title] of Object.entries(PROMPT_TITLES)) {
            titleToPrompt[title] = num;
        }

        reflections.forEach(r => {
            const promptNum = titleToPrompt[r.title] || r.prompt;
            if (!promptNum) {
                console.log('[Reflections] Could not match reflection to prompt:', r.title);
                return;
            }

            const input = document.getElementById(`reflection${promptNum}`);
            if (input) {
                input.value = r.content || '';
                console.log('[Reflections] Loaded prompt', promptNum, ':', (r.content || '').substring(0, 50) + '...');
            }
            if (r.id) {
                this.savedIds[promptNum] = r.id;
            }
        });
    },

    loadFromLocalStorage() {
        let loaded = 0;
        for (let i = 1; i <= 3; i++) {
            const key = `wop-reflection-${this.chapterId}-${i}`;
            const data = localStorage.getItem(key);

            if (data) {
                try {
                    const parsed = JSON.parse(data);
                    const input = document.getElementById(`reflection${i}`);
                    if (input) {
                        input.value = parsed.content || '';
                        loaded++;
                    }
                } catch (e) {
                    console.error('[Reflections] Error parsing localStorage:', e);
                }
            }
        }
        if (loaded > 0) {
            console.log('[Reflections] Loaded', loaded, 'reflections from localStorage');
        }
    },

    setupSaveButton() {
        const saveBtn = document.getElementById('saveReflections');

        saveBtn?.addEventListener('click', () => {
            console.log('[Reflections] Save button clicked');
            let saved = 0;
            document.querySelectorAll('.reflection-input').forEach(input => {
                const prompt = input.dataset.prompt;
                if (input.value.trim()) {
                    this.saveReflection(prompt, input.value);
                    saved++;
                }
            });
            if (saved === 0) {
                this.updateStatus('default');
            }
        });
    },

    setupClearButton() {
        const clearBtn = document.getElementById('clearReflections');

        clearBtn?.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all reflections for this chapter?')) {
                this.clearAllReflections();
            }
        });
    },

    clearAllReflections() {
        document.querySelectorAll('.reflection-input').forEach(input => {
            input.value = '';
        });

        for (let i = 1; i <= 3; i++) {
            const key = `wop-reflection-${this.chapterId}-${i}`;
            localStorage.removeItem(key);
        }

        this.savedIds = {};
        this.updateStatus('cleared');
    },

    updateStatus(status) {
        const statusEl = document.querySelector('.save-status .status-text');
        const iconEl = document.querySelector('.save-status .status-icon');

        if (!statusEl) return;

        switch (status) {
            case 'saving':
                statusEl.textContent = 'Saving...';
                if (iconEl) iconEl.textContent = '';
                break;
            case 'saved':
                statusEl.textContent = 'Saved to your account';
                if (iconEl) iconEl.textContent = '\u2713';
                break;
            case 'saved-local':
                statusEl.textContent = 'Saved locally (sign in to sync across devices)';
                if (iconEl) iconEl.textContent = '\u2713';
                break;
            case 'cleared':
                statusEl.textContent = 'Reflections cleared';
                if (iconEl) iconEl.textContent = '';
                break;
            case 'error':
                statusEl.textContent = 'Error saving';
                if (iconEl) iconEl.textContent = '\u26A0';
                break;
            default:
                statusEl.textContent = 'Reflections auto-save as you type';
                if (iconEl) iconEl.textContent = '';
        }
    }
};

// Export
window.Reflections = Reflections;
