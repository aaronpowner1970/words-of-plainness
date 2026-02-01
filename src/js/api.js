/**
 * WORDS OF PLAINNESS - API Client
 * ================================
 *
 * Handles communication with the Django API on PythonAnywhere.
 * - Authentication (login, logout, register) with JWT access/refresh tokens
 * - Automatic token refresh on 401
 * - Reflection storage and retrieval
 * - User profile management
 */

const API = {
    baseUrl: '',
    accessToken: null,
    refreshToken: null,
    user: null,
    _refreshing: null, // mutex for token refresh

    init(baseUrl) {
        this.baseUrl = baseUrl || '';

        // Load tokens — support both new JWT keys and legacy single-token key
        this.accessToken = localStorage.getItem('wop_access_token')
            || localStorage.getItem('wop-auth-token')
            || null;
        this.refreshToken = localStorage.getItem('wop_refresh_token') || null;
        this.user = JSON.parse(localStorage.getItem('wop-user') || 'null');

        // Migrate legacy key if present
        if (localStorage.getItem('wop-auth-token') && !localStorage.getItem('wop_access_token')) {
            localStorage.setItem('wop_access_token', this.accessToken);
            localStorage.removeItem('wop-auth-token');
        }

        this.updateUIForAuth();
        this.setupUserMenu();

        console.log('API client initialized', this.baseUrl ? `→ ${this.baseUrl}` : '(no API URL)');
    },

    setupUserMenu() {
        const toggle = document.getElementById('userMenuToggle');
        const dropdown = document.getElementById('userDropdown');

        if (toggle && dropdown) {
            toggle.addEventListener('click', () => {
                dropdown.classList.toggle('open');
            });

            document.addEventListener('click', (e) => {
                if (!toggle.contains(e.target) && !dropdown.contains(e.target)) {
                    dropdown.classList.remove('open');
                }
            });
        }

        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            this.logout();
        });
    },

    isAuthenticated() {
        return !!this.accessToken;
    },

    getHeaders() {
        const headers = { 'Content-Type': 'application/json' };

        if (this.accessToken) {
            // Support both JWT ("Bearer") and DRF TokenAuth ("Token") formats.
            // JWT tokens contain dots; legacy DRF tokens do not.
            const prefix = this.accessToken.includes('.') ? 'Bearer' : 'Token';
            headers['Authorization'] = `${prefix} ${this.accessToken}`;
        }

        return headers;
    },

    /**
     * Core request method with automatic 401 retry via token refresh.
     */
    async request(endpoint, options = {}, _retried = false) {
        if (!this.baseUrl) {
            throw new Error('API not configured');
        }

        const url = `${this.baseUrl}${endpoint}`;

        const response = await fetch(url, {
            ...options,
            headers: this.getHeaders()
        });

        // On 401, try refreshing the token once
        if (response.status === 401 && !_retried && this.refreshToken) {
            const refreshed = await this.tryRefreshToken();
            if (refreshed) {
                return this.request(endpoint, options, true);
            }
            // Refresh failed — force logout
            this.logout();
            throw new Error('Session expired. Please sign in again.');
        }

        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            const err = new Error(this.parseErrorMessage(body, response.status));
            err.status = response.status;
            err.fieldErrors = body;
            throw err;
        }

        // Handle 204 No Content
        if (response.status === 204) return null;

        return response.json();
    },

    /**
     * Extract a user-friendly error message from API error responses.
     */
    parseErrorMessage(body, status) {
        // Django REST Framework returns errors in several formats
        if (body.detail) return body.detail;
        if (body.non_field_errors) return body.non_field_errors.join(' ');

        // Field-level errors: { "email": ["This field is required."] }
        const fieldErrors = Object.entries(body)
            .filter(([, v]) => Array.isArray(v))
            .map(([field, msgs]) => `${field}: ${msgs.join(' ')}`)
            .join('\n');
        if (fieldErrors) return fieldErrors;

        // Fallback
        switch (status) {
            case 400: return 'Please check your input and try again.';
            case 401: return 'Invalid email or password.';
            case 403: return 'You do not have permission to do that.';
            case 404: return 'The requested resource was not found.';
            case 409: return 'An account with that email already exists.';
            case 429: return 'Too many requests. Please wait a moment.';
            case 500: return 'Server error. Please try again later.';
            default: return `Something went wrong (error ${status}).`;
        }
    },

    /**
     * Attempt to refresh the access token using the refresh token.
     */
    async tryRefreshToken() {
        // Prevent concurrent refresh attempts
        if (this._refreshing) return this._refreshing;

        this._refreshing = (async () => {
            try {
                const response = await fetch(`${this.baseUrl}/token/refresh/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh: this.refreshToken })
                });

                if (!response.ok) return false;

                const data = await response.json();
                this.accessToken = data.access;
                localStorage.setItem('wop_access_token', data.access);

                // Some backends rotate the refresh token too
                if (data.refresh) {
                    this.refreshToken = data.refresh;
                    localStorage.setItem('wop_refresh_token', data.refresh);
                }

                return true;
            } catch {
                return false;
            } finally {
                this._refreshing = null;
            }
        })();

        return this._refreshing;
    },

    // =========================================
    // Authentication
    // =========================================

    async login(email, password) {
        const data = await this.request('/accounts/login/', {
            method: 'POST',
            body: JSON.stringify({ username: email, password })
        });

        this.setAuth(data);
        return data;
    },

    async register({ username, email, password, password_confirm, display_name }) {
        const data = await this.request('/accounts/register/', {
            method: 'POST',
            body: JSON.stringify({ username, email, password, password_confirm, display_name })
        });

        this.setAuth(data);
        return data;
    },

    logout() {
        this.accessToken = null;
        this.refreshToken = null;
        this.user = null;
        localStorage.removeItem('wop_access_token');
        localStorage.removeItem('wop_refresh_token');
        localStorage.removeItem('wop-auth-token'); // legacy cleanup
        localStorage.removeItem('wop-user');
        this.updateUIForAuth();
    },

    /**
     * Save auth data from login/register response.
     * Supports both JWT format ({ access, refresh, user })
     * and DRF TokenAuth format ({ token, user }).
     */
    setAuth(data) {
        if (data.access) {
            // JWT format
            this.accessToken = data.access;
            this.refreshToken = data.refresh || null;
            localStorage.setItem('wop_access_token', data.access);
            if (data.refresh) localStorage.setItem('wop_refresh_token', data.refresh);
        } else if (data.token) {
            // Legacy DRF TokenAuth format
            this.accessToken = data.token;
            localStorage.setItem('wop_access_token', data.token);
        }

        if (data.user) {
            this.user = data.user;
            localStorage.setItem('wop-user', JSON.stringify(data.user));
        }

        this.updateUIForAuth();

        // After login, check for localStorage reflections to migrate
        this.checkReflectionMigration();
    },

    // =========================================
    // UI Updates
    // =========================================

    updateUIForAuth() {
        const authButtons = document.getElementById('navAuthButtons');
        const userMenu = document.getElementById('userMenu');

        // Mobile menu auth elements
        const mobileLoggedOut = document.getElementById('mobileAuthLoggedOut');
        const mobileLoggedIn = document.getElementById('mobileAuthLoggedIn');
        const mobileUsername = document.getElementById('mobileUsername');
        const mobileAvatar = document.getElementById('mobileUserAvatar');

        if (this.isAuthenticated() && this.user) {
            authButtons?.classList.add('hidden');
            userMenu?.classList.remove('hidden');

            const displayName = this.user.name || this.user.email || 'User';
            const email = this.user.email || '';
            const initial = displayName.charAt(0).toUpperCase();

            const userName = document.getElementById('userName');
            const userAvatar = document.getElementById('userAvatar');
            const userDropdownName = document.getElementById('userDropdownName');
            const userDropdownEmail = document.getElementById('userDropdownEmail');

            if (userName) userName.textContent = displayName;
            if (userAvatar) userAvatar.textContent = initial;
            if (userDropdownName) userDropdownName.textContent = displayName;
            if (userDropdownEmail) userDropdownEmail.textContent = email;

            mobileLoggedOut?.classList.add('hidden');
            mobileLoggedIn?.classList.remove('hidden');
            if (mobileUsername) mobileUsername.textContent = displayName;
            if (mobileAvatar) mobileAvatar.textContent = initial;
        } else {
            authButtons?.classList.remove('hidden');
            userMenu?.classList.add('hidden');

            mobileLoggedOut?.classList.remove('hidden');
            mobileLoggedIn?.classList.add('hidden');
        }
    },

    // =========================================
    // Reflection Migration (localStorage → API)
    // =========================================

    checkReflectionMigration() {
        if (!this.isAuthenticated()) return;

        // Look for any localStorage reflections
        const localReflections = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('wop-reflection-')) {
                try {
                    localReflections.push({
                        key: key,
                        data: JSON.parse(localStorage.getItem(key))
                    });
                } catch { /* skip malformed */ }
            }
        }

        if (localReflections.length === 0) return;

        // Show migration prompt
        const count = localReflections.length;
        const noun = count === 1 ? 'reflection' : 'reflections';

        // Small delay so the auth modal has time to close
        setTimeout(() => {
            if (confirm(`You have ${count} ${noun} saved on this device. Would you like to sync them to your account so they're available on all your devices?`)) {
                this.migrateReflections(localReflections);
            }
        }, 500);
    },

    async migrateReflections(items) {
        const promptTitles = {
            '1': 'What stood out to you?',
            '2': 'Why does it matter to you?',
            '3': 'What will you do?'
        };
        let migrated = 0;

        for (const item of items) {
            try {
                // Normalize old format { chapter, prompt, content } to Django schema
                const d = item.data;
                const payload = {
                    content: d.content || '',
                    chapter_slug: d.chapter_slug || d.chapter || '',
                    title: d.title || promptTitles[d.prompt] || `Reflection ${d.prompt}`,
                    visibility: d.visibility || 'private'
                };
                if (!payload.content || !payload.chapter_slug) {
                    localStorage.removeItem(item.key);
                    continue;
                }
                await this.saveReflection(payload);
                localStorage.removeItem(item.key);
                migrated++;
            } catch (error) {
                console.warn('Failed to migrate reflection:', item.key, error);
            }
        }

        if (migrated > 0) {
            console.log(`Migrated ${migrated} reflections to account`);
            // Reload reflections UI if on a chapter page
            if (typeof Reflections !== 'undefined' && Reflections.chapterId) {
                Reflections.loadReflections();
            }
        }
    },

    // =========================================
    // Reflections API
    // =========================================

    async saveReflection(data) {
        return this.request('/reflections/mine/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateReflection(id, data) {
        return this.request(`/reflections/mine/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    async getReflections(chapterSlug) {
        return this.request(`/reflections/mine/?chapter_slug=${encodeURIComponent(chapterSlug)}`);
    },

    async getAllReflections() {
        return this.request('/reflections/mine/');
    },

    async getCommunityReflections(chapterId) {
        const query = chapterId ? `?chapter=${chapterId}` : '';
        return this.request(`/reflections/community/${query}`);
    },

    async appreciateReflection(id) {
        return this.request(`/reflections/${id}/appreciate/`, {
            method: 'POST'
        });
    },

    // =========================================
    // Contact API
    // =========================================

    async submitContact(data) {
        return this.request('/contact/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const apiUrl = document.body.dataset.apiUrl || '';
    API.init(apiUrl);
});

// Export
window.API = API;
