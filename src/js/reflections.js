/**
 * WORDS OF PLAINNESS - Reflections Manager
 * =========================================
 *
 * Handles saving and loading reflection prompts.
 * - Saves to Django API for authenticated users (POST new, PATCH existing)
 * - Falls back to localStorage for guests
 * - Auto-saves as user types (2s debounce)
 */

const PROMPT_TITLES = {
    '1': 'What stood out to you?',
    '2': 'Why does it matter to you?',
    '3': 'What will you do?'
};

const Reflections = {
    chapterId: null,
    debounceTimers: {},
    saveDelay: 2000,    // 2 second debounce for auto-save
    savedIds: {},       // prompt number → API reflection id (for PATCH updates)
    saving: {},         // prompt number → true while a save is in-flight

    init(chapterId) {
        this.chapterId = chapterId;
        this.setupInputListeners();
        this.setupSaveButton();
        this.setupClearButton();

        console.log('[Reflections] Initialized for:', chapterId);
        console.log('[Reflections] Authenticated:', this.isUserAuthenticated());

        this.loadReflections();
    },

    isUserAuthenticated() {
        if (window.API && window.API.isAuthenticated()) {
            return true;
        }
        const token = localStorage.getItem('wop_access_token')
            || localStorage.getItem('wop-auth-token');
        return !!token;
    },

    canUseAPI() {
        return this.isUserAuthenticated() && window.API && window.API.baseUrl;
    },

    setupInputListeners() {
        document.querySelectorAll('.reflection-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const prompt = e.target.dataset.prompt;
                this.clearReflectionError(prompt);
                this.debounceSave(prompt, e.target.value);
            });
        });
    },

    debounceSave(prompt, value) {
        // Cancel any pending timer for this prompt
        if (this.debounceTimers[prompt]) {
            clearTimeout(this.debounceTimers[prompt]);
        }

        if (!value.trim()) {
            this.updateStatus('default');
            return;
        }

        this.updateStatus('saving');

        this.debounceTimers[prompt] = setTimeout(() => {
            this.debounceTimers[prompt] = null;
            this.saveReflection(prompt, value);
        }, this.saveDelay);
    },

    /**
     * Cancel all pending debounce timers. Called before immediate save.
     */
    cancelAllTimers() {
        for (const prompt of Object.keys(this.debounceTimers)) {
            if (this.debounceTimers[prompt]) {
                clearTimeout(this.debounceTimers[prompt]);
                this.debounceTimers[prompt] = null;
            }
        }
    },

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

        // Prevent concurrent saves for the same prompt
        if (this.saving[prompt]) {
            console.log('[Reflections] Save already in-flight for prompt', prompt, '— skipping');
            return;
        }

        if (this.canUseAPI()) {
            this.saving[prompt] = true;
            try {
                const existingId = this.savedIds[prompt];

                if (existingId) {
                    // PATCH existing reflection
                    console.log('[Reflections] Updating existing reflection', existingId, 'for prompt', prompt);
                    const result = await window.API.updateReflection(existingId, {
                        content: value
                    });
                    console.log('[Reflections] Reflection updated:', result);
                } else {
                    // POST new reflection
                    const payload = this.buildPayload(prompt, value);
                    console.log('[Reflections] Creating new reflection:', payload.title);
                    const result = await window.API.saveReflection(payload);
                    console.log('[Reflections] Reflection created:', result);
                    if (result && result.id) {
                        this.savedIds[prompt] = result.id;
                    }
                }

                this.updateStatus('saved');
                this.clearReflectionError(prompt);
                return;
            } catch (error) {
                // Content moderation or validation error (400) — do NOT fall back to localStorage
                if (error.status === 400) {
                    console.warn('[Reflections] Content rejected by server:', error.message);
                    const fieldMsg = this.extractFieldError(error);
                    this.showReflectionError(prompt, fieldMsg || error.message);
                    this.updateStatus('error');
                    return;
                }
                // Network or server error — fall back to localStorage
                console.warn('[Reflections] API save failed, falling back to localStorage:', error.message);
            } finally {
                this.saving[prompt] = false;
            }
        } else {
            console.log('[Reflections] Not authenticated, saving to localStorage');
        }

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
        if (this.canUseAPI()) {
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

        // Clear savedIds before repopulating
        this.savedIds = {};

        reflections.forEach(r => {
            const promptNum = titleToPrompt[r.title] || r.prompt;
            if (!promptNum) {
                console.log('[Reflections] Could not match reflection to prompt:', r.title);
                return;
            }

            const input = document.getElementById(`reflection${promptNum}`);
            if (input) {
                input.value = r.content || '';
                console.log('[Reflections] Loaded prompt', promptNum, '(id:', r.id + '):', (r.content || '').substring(0, 50));
            }
            if (r.id) {
                this.savedIds[promptNum] = r.id;
            }
        });

        console.log('[Reflections] Saved IDs map:', JSON.stringify(this.savedIds));
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
            console.log('[Reflections] Save button clicked — cancelling pending auto-saves');

            // Cancel all pending debounce timers to prevent double-saves
            this.cancelAllTimers();

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
        this.cancelAllTimers();

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

    extractFieldError(error) {
        if (!error.fieldErrors || typeof error.fieldErrors !== 'object') return null;
        const msgs = Object.entries(error.fieldErrors)
            .filter(([, v]) => Array.isArray(v))
            .map(([, msgs]) => msgs.join(' '));
        return msgs.length > 0 ? msgs.join(' ') : null;
    },

    showReflectionError(prompt, message) {
        const input = document.getElementById(`reflection${prompt}`);
        if (!input) return;

        // Remove existing error for this prompt
        this.clearReflectionError(prompt);

        const errorEl = document.createElement('div');
        errorEl.className = 'reflection-error';
        errorEl.setAttribute('data-prompt-error', prompt);
        errorEl.textContent = message;
        input.insertAdjacentElement('afterend', errorEl);
    },

    clearReflectionError(prompt) {
        const existing = document.querySelector(`[data-prompt-error="${prompt}"]`);
        existing?.remove();
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
