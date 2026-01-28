/**
 * WORDS OF PLAINNESS - Reflections Manager
 * =========================================
 * 
 * Handles saving and loading reflection prompts.
 * - Saves to Django API for authenticated users
 * - Falls back to localStorage for guests
 * - Auto-saves as user types (debounced)
 */

const Reflections = {
    chapterId: null,
    debounceTimers: {},
    saveDelay: 1000, // 1 second debounce
    
    init(chapterId) {
        this.chapterId = chapterId;
        this.setupInputListeners();
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
        // Clear existing timer
        if (this.debounceTimers[prompt]) {
            clearTimeout(this.debounceTimers[prompt]);
        }
        
        // Show saving status
        this.updateStatus('saving');
        
        // Set new timer
        this.debounceTimers[prompt] = setTimeout(() => {
            this.saveReflection(prompt, value);
        }, this.saveDelay);
    },
    
    async saveReflection(prompt, value) {
        const data = {
            chapter: this.chapterId,
            prompt: prompt,
            content: value,
            timestamp: Date.now()
        };
        
        // Try API first if user is authenticated
        if (window.API && window.API.isAuthenticated()) {
            try {
                await window.API.saveReflection(data);
                this.updateStatus('saved');
                return;
            } catch (error) {
                console.warn('API save failed, falling back to localStorage:', error);
            }
        }
        
        // Fallback to localStorage
        this.saveToLocalStorage(data);
        this.updateStatus('saved-local');
    },
    
    saveToLocalStorage(data) {
        const key = `wop-reflection-${data.chapter}-${data.prompt}`;
        localStorage.setItem(key, JSON.stringify(data));
    },
    
    async loadReflections() {
        // Try API first
        if (window.API && window.API.isAuthenticated()) {
            try {
                const reflections = await window.API.getReflections(this.chapterId);
                this.populateInputs(reflections);
                return;
            } catch (error) {
                console.warn('API load failed, falling back to localStorage:', error);
            }
        }
        
        // Load from localStorage
        this.loadFromLocalStorage();
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
    
    populateInputs(reflections) {
        if (!Array.isArray(reflections)) return;
        
        reflections.forEach(r => {
            const input = document.getElementById(`reflection${r.prompt}`);
            if (input) {
                input.value = r.content || '';
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
        // Clear inputs
        document.querySelectorAll('.reflection-input').forEach(input => {
            input.value = '';
        });
        
        // Clear localStorage
        for (let i = 1; i <= 3; i++) {
            const key = `wop-reflection-${this.chapterId}-${i}`;
            localStorage.removeItem(key);
        }
        
        // TODO: Clear from API if authenticated
        
        this.updateStatus('cleared');
    },
    
    updateStatus(status) {
        const statusEl = document.querySelector('.save-status .status-text');
        const iconEl = document.querySelector('.save-status .status-icon');
        
        if (!statusEl) return;
        
        switch (status) {
            case 'saving':
                statusEl.textContent = 'Saving...';
                iconEl.innerHTML = '⏳';
                break;
            case 'saved':
                statusEl.textContent = 'Saved to your account';
                iconEl.innerHTML = '✓';
                break;
            case 'saved-local':
                statusEl.textContent = 'Saved locally (sign in to sync across devices)';
                iconEl.innerHTML = '✓';
                break;
            case 'cleared':
                statusEl.textContent = 'Reflections cleared';
                iconEl.innerHTML = '';
                break;
            case 'error':
                statusEl.textContent = 'Error saving';
                iconEl.innerHTML = '⚠';
                break;
            default:
                statusEl.textContent = 'Reflections auto-save as you type';
                iconEl.innerHTML = '';
        }
    }
};

// Export
window.Reflections = Reflections;
