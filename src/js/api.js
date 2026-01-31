/**
 * WORDS OF PLAINNESS - API Client
 * ================================
 * 
 * Handles communication with the Django API on PythonAnywhere.
 * - Authentication (login, logout, register)
 * - Reflection storage and retrieval
 * - User profile management
 */

const API = {
    baseUrl: '', // Set from site.json or config
    token: null,
    user: null,
    
    init(baseUrl) {
        this.baseUrl = baseUrl || '';
        this.token = localStorage.getItem('wop-auth-token');
        this.user = JSON.parse(localStorage.getItem('wop-user') || 'null');

        this.updateUIForAuth();
        this.setupUserMenu();

        console.log('API client initialized');
    },

    setupUserMenu() {
        // User menu dropdown toggle
        const toggle = document.getElementById('userMenuToggle');
        const dropdown = document.getElementById('userDropdown');

        if (toggle && dropdown) {
            toggle.addEventListener('click', () => {
                dropdown.classList.toggle('open');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!toggle.contains(e.target) && !dropdown.contains(e.target)) {
                    dropdown.classList.remove('open');
                }
            });
        }

        // Logout button
        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            this.logout();
        });
    },
    
    isAuthenticated() {
        return !!this.token;
    },
    
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.token) {
            headers['Authorization'] = `Token ${this.token}`;
        }
        
        return headers;
    },
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const response = await fetch(url, {
            ...options,
            headers: this.getHeaders()
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `API Error: ${response.status}`);
        }
        
        return response.json();
    },
    
    // Authentication
    async login(email, password) {
        const data = await this.request('/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        this.setAuth(data.token, data.user);
        return data;
    },
    
    async register(email, password, name) {
        const data = await this.request('/auth/register/', {
            method: 'POST',
            body: JSON.stringify({ email, password, name })
        });
        
        this.setAuth(data.token, data.user);
        return data;
    },
    
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('wop-auth-token');
        localStorage.removeItem('wop-user');
        this.updateUIForAuth();
    },
    
    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('wop-auth-token', token);
        localStorage.setItem('wop-user', JSON.stringify(user));
        this.updateUIForAuth();
    },
    
    updateUIForAuth() {
        // Update header UI based on auth state
        const authButtons = document.getElementById('navAuthButtons');
        const userMenu = document.getElementById('userMenu');

        // Mobile menu auth elements
        const mobileLoggedOut = document.getElementById('mobileAuthLoggedOut');
        const mobileLoggedIn = document.getElementById('mobileAuthLoggedIn');
        const mobileUsername = document.getElementById('mobileUsername');
        const mobileAvatar = document.getElementById('mobileUserAvatar');

        if (this.isAuthenticated() && this.user) {
            // Hide login buttons, show user menu
            authButtons?.classList.add('hidden');
            userMenu?.classList.remove('hidden');

            // Populate user info
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

            // Mobile menu: show logged-in state
            mobileLoggedOut?.classList.add('hidden');
            mobileLoggedIn?.classList.remove('hidden');
            if (mobileUsername) mobileUsername.textContent = displayName;
            if (mobileAvatar) mobileAvatar.textContent = initial;
        } else {
            // Show login buttons, hide user menu
            authButtons?.classList.remove('hidden');
            userMenu?.classList.add('hidden');

            // Mobile menu: show logged-out state
            mobileLoggedOut?.classList.remove('hidden');
            mobileLoggedIn?.classList.add('hidden');
        }
    },
    
    // Reflections
    async saveReflection(data) {
        return this.request('/reflections/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    async getReflections(chapterId) {
        return this.request(`/reflections/?chapter=${chapterId}`);
    },
    
    async getAllReflections() {
        return this.request('/reflections/');
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Get API URL from site config or data attribute
    const apiUrl = document.body.dataset.apiUrl || '';
    API.init(apiUrl);
});

// Export
window.API = API;
