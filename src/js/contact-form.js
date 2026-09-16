/**
 * WORDS OF PLAINNESS - Contact Form Handler
 * ==========================================
 *
 * Handles the "Contact Brother Aaron" form on the Connect page.
 * - Posts to Django API /contact/ endpoint
 * - Pre-fills name/email for logged-in users
 * - Client-side validation with inline errors
 * - Success/error states
 */

const ContactForm = {
    form: null,
    submitBtn: null,

    init() {
        this.form = document.getElementById('contactForm');
        this.submitBtn = document.getElementById('contactSubmit');

        if (!this.form) return;

        this.prefillFromAuth();
        this.prefillFromQuery();
        this.setupSubmit();
        this.setupSendAnother();
        this.setupInputClear();

        console.log('[ContactForm] Initialized');
    },

    prefillFromAuth() {
        if (!window.API?.isAuthenticated() || !window.API.user) return;

        const nameInput = document.getElementById('contact-name');
        const emailInput = document.getElementById('contact-email');

        if (nameInput && !nameInput.value && window.API.user.name) {
            nameInput.value = window.API.user.name;
        }
        if (emailInput && !emailInput.value && window.API.user.email) {
            emailInput.value = window.API.user.email;
        }
    },

    /**
     * Context prefill from the URL.
     *
     * The correction links on the AoID reading pages (/articles/video-NN/) carry
     * the article code, span id and page URL, so a reader reporting a
     * misrepresentation does not have to describe where they saw it. Any page
     * can hand this form the same three params.
     *
     * Deliberately narrow: ONLY submission_type, subject and message. Name and
     * email are never taken from the URL — a crafted link must not be able to
     * put someone else's identity on a message, and those two fields stay the
     * sender's own to type. Nothing is submitted automatically either; the
     * reader still reads what is there and presses Send.
     * Anything already filled (by auth, or by the reader) wins over the URL.
     */
    prefillFromQuery() {
        let params;
        try { params = new URLSearchParams(window.location.search); } catch (e) { return; }
        if (![...params.keys()].length) return;

        const MAX = { subject: 300, message: 4000, submission_type: 40 };
        const setIfEmpty = (id, value) => {
            const el = document.getElementById(id);
            if (el && !el.value && value) { el.value = value; }
        };

        const type = (params.get('submission_type') || '').slice(0, MAX.submission_type);
        if (type) {
            const sel = document.getElementById('contact-type');
            // Only a value the select actually offers; an unknown topic is ignored.
            if (sel && [...sel.options].some(o => o.value === type)) { sel.value = type; }
        }

        setIfEmpty('contact-subject', (params.get('subject') || '').slice(0, MAX.subject));
        setIfEmpty('contact-message', (params.get('message') || '').slice(0, MAX.message));
    },

    setupSubmit() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit();
        });
    },

    setupSendAnother() {
        document.getElementById('contactSendAnother')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.form.reset();
            this.clearAllErrors();
            document.getElementById('contactSuccess')?.classList.add('hidden');
            this.form.classList.remove('hidden');
            this.prefillFromAuth();
        });
    },

    setupInputClear() {
        this.form.querySelectorAll('input, textarea, select').forEach(el => {
            el.addEventListener('input', () => {
                const field = el.name;
                const errorEl = document.querySelector(`[data-contact-error="${field}"]`);
                if (errorEl) {
                    errorEl.textContent = '';
                    errorEl.classList.add('hidden');
                }
            });
        });
    },

    validate() {
        this.clearAllErrors();
        let valid = true;

        const name = document.getElementById('contact-name').value.trim();
        const email = document.getElementById('contact-email').value.trim();
        const type = document.getElementById('contact-type').value;
        const subject = document.getElementById('contact-subject').value.trim();
        const message = document.getElementById('contact-message').value.trim();

        if (!name) {
            this.showFieldError('name', 'Name is required.');
            valid = false;
        }
        if (!email || !email.includes('@')) {
            this.showFieldError('email', 'Please enter a valid email address.');
            valid = false;
        }
        if (!type) {
            this.showFieldError('submission_type', 'Please select a topic.');
            valid = false;
        }
        if (!subject) {
            this.showFieldError('subject', 'Subject is required.');
            valid = false;
        }
        if (!message) {
            this.showFieldError('message', 'Message is required.');
            valid = false;
        } else if (message.length < 10) {
            this.showFieldError('message', 'Message must be at least 10 characters.');
            valid = false;
        }

        return valid;
    },

    async handleSubmit() {
        if (!this.validate()) return;

        const data = {
            name: document.getElementById('contact-name').value.trim(),
            email: document.getElementById('contact-email').value.trim(),
            submission_type: document.getElementById('contact-type').value,
            subject: document.getElementById('contact-subject').value.trim(),
            message: document.getElementById('contact-message').value.trim()
        };

        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Sending...';
        this.hideFormError();

        try {
            await window.API.submitContact(data);

            // Show success state
            this.form.classList.add('hidden');
            document.getElementById('contactSuccess')?.classList.remove('hidden');

        } catch (error) {
            if (error.message === 'Failed to fetch') {
                this.showFormError(
                    'Unable to send your message right now. Please try again or email directly at brother@wordsofplainness.com.'
                );
            } else if (error.fieldErrors && typeof error.fieldErrors === 'object') {
                this.clearAllErrors();
                const unmapped = [];

                if (Array.isArray(error.fieldErrors.non_field_errors)) {
                    unmapped.push(error.fieldErrors.non_field_errors.join(' '));
                }

                for (const [field, msgs] of Object.entries(error.fieldErrors)) {
                    if (field === 'non_field_errors' || !Array.isArray(msgs)) continue;
                    const el = document.querySelector(`[data-contact-error="${field}"]`);
                    if (el) {
                        this.showFieldError(field, msgs.join(' '));
                    } else {
                        unmapped.push(`${field}: ${msgs.join(' ')}`);
                    }
                }

                if (unmapped.length > 0) {
                    this.showFormError(unmapped.join('\n'));
                }
            } else {
                this.showFormError(error.message);
            }
        } finally {
            this.submitBtn.disabled = false;
            this.submitBtn.textContent = 'Send Message';
        }
    },

    showFieldError(field, message) {
        const el = document.querySelector(`[data-contact-error="${field}"]`);
        if (el) {
            el.textContent = message;
            el.classList.remove('hidden');
        }
    },

    clearAllErrors() {
        document.querySelectorAll('[data-contact-error]').forEach(el => {
            el.textContent = '';
            el.classList.add('hidden');
        });
        this.hideFormError();
    },

    showFormError(message) {
        const el = document.getElementById('contactFormError');
        if (el) {
            el.textContent = message;
            el.classList.remove('hidden');
        }
    },

    hideFormError() {
        const el = document.getElementById('contactFormError');
        if (el) {
            el.textContent = '';
            el.classList.add('hidden');
        }
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    ContactForm.init();
});

window.ContactForm = ContactForm;
