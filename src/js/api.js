/**
 * WORDS OF PLAINNESS - API Client
 * ================================
 *
 * Sends the site's forms to the Django API on PythonAnywhere, and nothing else:
 * - submitContact: the contact form (/connect/) and the AoID corrections form
 * - subscribeNewsletter: the newsletter forms
 *
 * This site has no accounts. No sign-in token is sent with any form, and no
 * reflection, journal entry, progress or engagement data is sent anywhere
 * (CODE-SITE-18, SITE step 27; rulings SITE-JOURNAL-DEVICE-ONLY,
 * SITE-ACCOUNTS-RETIRE, SITE-JOURNAL-FORM-TOKEN).
 */

const API = {
    baseUrl: '',

    init(baseUrl) {
        this.baseUrl = baseUrl || '';
    },

    /**
     * POST a form's data to the API and return the parsed reply.
     */
    async request(endpoint, options = {}) {
        if (!this.baseUrl) {
            throw new Error('API not configured');
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: { 'Content-Type': 'application/json' }
        });

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

    // =========================================
    // Contact API
    // =========================================

    async submitContact(data) {
        return this.request('/contact/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // =========================================
    // Newsletter API
    // =========================================

    async subscribeNewsletter(data) {
        return this.request('/newsletter/subscribe/', {
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
