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
        
        if (this.token) {
            this.updateUIForAuth();
        }
        
        console.log('API client initialized');
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
        const userMenu = document.getElementById('userMenu');
        const signInBtn = document.getElementById('signInBtn');
        
        if (this.isAuthenticated()) {
            signInBtn?.classList.add('hidden');
            userMenu?.classList.remove('hidden');
            
            const userName = document.getElementById('userName');
            if (userName && this.user) {
                userName.textContent = this.user.name || this.user.email;
            }
        } else {
            signInBtn?.classList.remove('hidden');
            userMenu?.classList.add('hidden');
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
