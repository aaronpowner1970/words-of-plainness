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
        this.loadReflections();
        this.setupClearButton();

        console.log('Reflections initialized for:', chapterId);
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

        // Try API first if authenticated
        if (window.API && window.API.isAuthenticated()) {
            try {
                const payload = this.buildPayload(prompt, value);
                const result = await window.API.saveReflection(payload);
                if (result && result.id) {
                    this.savedIds[prompt] = result.id;
                }
                this.updateStatus('saved');
                return;
            } catch (error) {
                console.warn('API save failed, falling back to localStorage:', error);
            }
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
        if (window.API && window.API.isAuthenticated()) {
            try {
                const reflections = await window.API.getReflections(this.chapterId);
                this.populateFromAPI(reflections);
                return;
            } catch (error) {
                console.warn('API load failed, falling back to localStorage:', error);
            }
        }

        this.loadFromLocalStorage();
    },

    /**
     * Populate inputs from API response.
     * API returns an array of reflection objects with { id, title, content, ... }.
     * Match them back to prompt numbers by title.
     */
    populateFromAPI(reflections) {
        if (!Array.isArray(reflections)) {
            // Some APIs wrap in { results: [...] }
            if (reflections && Array.isArray(reflections.results)) {
                reflections = reflections.results;
            } else {
                return;
            }
        }

        // Build reverse lookup: title → prompt number
        const titleToPrompt = {};
        for (const [num, title] of Object.entries(PROMPT_TITLES)) {
            titleToPrompt[title] = num;
        }

        reflections.forEach(r => {
            // Try matching by title first, then fall back to prompt field
            const promptNum = titleToPrompt[r.title] || r.prompt;
            if (!promptNum) return;

            const input = document.getElementById(`reflection${promptNum}`);
            if (input) {
                input.value = r.content || '';
            }
            if (r.id) {
                this.savedIds[promptNum] = r.id;
            }
        });
    },

    loadFromLocalStorage() {
        for (let i = 1; i <= 3; i++) {
            const key = `wop-reflection-${this.chapterId}-${i}`;
            const data = localStorage.getItem(key);

            if (data) {
                try {
                    const parsed = JSON.parse(data);
                    const input = document.getElementById(`reflection${i}`);
                    if (input) {
                        input.value = parsed.content || '';
                    }
                } catch (e) {
                    console.error('Error parsing reflection:', e);
                }
            }
        }
    },

    setupSaveButton() {
        const saveBtn = document.getElementById('saveReflections');

        saveBtn?.addEventListener('click', () => {
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

        // Clear localStorage
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
