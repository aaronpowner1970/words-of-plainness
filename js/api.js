/**
 * Words of Plainness - API Integration Module
 * Handles all communication with the Django backend
 * API Base: https://apowner.pythonanywhere.com/api/v1/
 */

const WoPAPI = (function() {
    'use strict';

    // Configuration
    const API_BASE = 'https://apowner.pythonanywhere.com/api/v1';
    const TOKEN_KEY = 'wop_auth_token';
    const USER_KEY = 'wop_user_data';

    // =====================================================
    // TOKEN MANAGEMENT
    // =====================================================

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        if (token) {
            localStorage.setItem(TOKEN_KEY, token);
        } else {
            localStorage.removeItem(TOKEN_KEY);
        }
    }

    function getStoredUser() {
        const data = localStorage.getItem(USER_KEY);
        return data ? JSON.parse(data) : null;
    }

    function setStoredUser(user) {
        if (user) {
            localStorage.setItem(USER_KEY, JSON.stringify(user));
        } else {
            localStorage.removeItem(USER_KEY);
        }
    }

    function isAuthenticated() {
        return !!getToken();
    }

    // =====================================================
    // HTTP HELPERS
    // =====================================================

    async function request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const token = getToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Token ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, config);

            // Handle 204 No Content
            if (response.status === 204) {
                return { success: true };
            }

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                // Handle token expiration
                if (response.status === 401) {
                    clearAuth();
                    window.dispatchEvent(new CustomEvent('wop:auth:expired'));
                }

                throw {
                    status: response.status,
                    message: data.detail || data.error || extractErrors(data) || 'Request failed',
                    errors: data
                };
            }

            return data;
        } catch (error) {
            if (error.status) {
                throw error;
            }
            throw {
                status: 0,
                message: 'Network error. Please check your connection.',
                errors: {}
            };
        }
    }

    function extractErrors(data) {
        if (typeof data === 'string') return data;
        if (data.non_field_errors) return data.non_field_errors.join(', ');

        const errors = [];
        for (const [key, value] of Object.entries(data)) {
            if (Array.isArray(value)) {
                errors.push(`${key}: ${value.join(', ')}`);
            } else if (typeof value === 'string') {
                errors.push(`${key}: ${value}`);
            }
        }
        return errors.length > 0 ? errors.join('; ') : null;
    }

    function clearAuth() {
        setToken(null);
        setStoredUser(null);
    }

    // =====================================================
    // AUTHENTICATION ENDPOINTS
    // =====================================================

    /**
     * Register a new user
     * POST /accounts/register/
     */
    async function register(data) {
        const result = await request('/accounts/register/', {
            method: 'POST',
            body: data
        });

        if (result.token) {
            setToken(result.token);
        }
        if (result.user) {
            setStoredUser(result.user);
        }

        window.dispatchEvent(new CustomEvent('wop:auth:login', { detail: result.user }));
        return result;
    }

    /**
     * Login with email and password
     * POST /accounts/login/
     */
    async function login(data) {
        const result = await request('/accounts/login/', {
            method: 'POST',
            body: data
        });

        if (result.token) {
            setToken(result.token);
        }
        if (result.user) {
            setStoredUser(result.user);
        }

        window.dispatchEvent(new CustomEvent('wop:auth:login', { detail: result.user }));
        return result;
    }

    /**
     * Logout current user
     * POST /accounts/logout/
     */
    async function logout() {
        try {
            await request('/accounts/logout/', {
                method: 'POST'
            });
        } catch (e) {
            // Ignore errors on logout
        } finally {
            clearAuth();
            window.dispatchEvent(new CustomEvent('wop:auth:logout'));
        }
    }

    /**
     * Get current user profile
     * GET /accounts/me/
     */
    async function getCurrentUser() {
        if (!isAuthenticated()) {
            return null;
        }

        try {
            const user = await request('/accounts/me/', {
                method: 'GET'
            });
            setStoredUser(user);
            return user;
        } catch (error) {
            if (error.status === 401) {
                clearAuth();
            }
            throw error;
        }
    }

    // =====================================================
    // REFLECTIONS ENDPOINTS
    // =====================================================

    /**
     * Get current user's reflections
     * GET /reflections/mine/
     */
    async function getMyReflections() {
        return await request('/reflections/mine/', {
            method: 'GET'
        });
    }

    /**
     * Save/create a reflection
     * POST /reflections/mine/
     */
    async function saveReflection(data) {
        return await request('/reflections/mine/', {
            method: 'POST',
            body: data
        });
    }

    /**
     * Get public reflections for a chapter
     * GET /reflections/chapters/{slug}/
     */
    async function getChapterReflections(chapterSlug) {
        return await request(`/reflections/chapters/${chapterSlug}/`, {
            method: 'GET'
        });
    }

    /**
     * Appreciate a public reflection
     * POST /reflections/{id}/appreciate/
     */
    async function appreciateReflection(reflectionId) {
        return await request(`/reflections/${reflectionId}/appreciate/`, {
            method: 'POST'
        });
    }

    // =====================================================
    // PUBLIC API
    // =====================================================

    return {
        // Config
        API_BASE,

        // Auth state
        isAuthenticated,
        getToken,
        getStoredUser,
        clearAuth,

        // Auth endpoints
        register,
        login,
        logout,
        getCurrentUser,

        // Reflections endpoints
        getMyReflections,
        saveReflection,
        getChapterReflections,
        appreciateReflection,

        // Raw request helper (for extensions)
        request
    };
})();

// Make available globally
window.WoPAPI = WoPAPI;
