/**
 * WORDS OF PLAINNESS - My Reflections & Goals Dashboard
 * =====================================================
 *
 * Fetches user reflections from the API and renders a dashboard.
 * Goals are stored locally in localStorage.
 */

const Dashboard = {
    reflections: [],
    progress: [],
    goals: [],

    CHAPTER_MAP: {
        '01-introduction':       { number: 1, title: 'Introduction' },
        '02-our-search':         { number: 2, title: 'Our Search' },
        '03-academic-knowledge': { number: 3, title: 'Academic Knowledge' },
        '04-spiritual-knowledge':{ number: 4, title: 'Spiritual Knowledge' },
        '05-sincere-prayer':     { number: 5, title: 'Sincere Prayer' },
        '06-embrace-the-savior': { number: 6, title: 'Embrace the Savior' }
    },

    init() {
        if (!window.API) return;

        if (API.isAuthenticated()) {
            document.getElementById('dashboardAuthGate').style.display = 'none';
            document.getElementById('dashboardContent').style.display = 'block';
            this.loadData();
        }

        // Sign-in button opens auth modal
        document.getElementById('dashboardSignIn')?.addEventListener('click', () => {
            const modal = document.getElementById('authModal');
            if (modal) modal.style.display = 'flex';
        });

        this.loadGoals();
        this.setupGoalHandlers();
        this.setupExport();

        // Watch for login while on this page
        this._authCheck = setInterval(() => {
            if (API.isAuthenticated() && document.getElementById('dashboardContent').style.display === 'none') {
                clearInterval(this._authCheck);
                document.getElementById('dashboardAuthGate').style.display = 'none';
                document.getElementById('dashboardContent').style.display = 'block';
                this.loadData();
            }
        }, 500);
    },

    // =========================================
    // Data Loading
    // =========================================

    async loadData() {
        try {
            const [reflections, progress] = await Promise.all([
                API.getAllReflections().catch(() => []),
                API.getAllProgress().catch(() => [])
            ]);

            this.reflections = this.unwrapResults(reflections);
            this.progress = this.unwrapResults(progress);

            document.getElementById('reflectionsLoading').style.display = 'none';
            this.renderSummary();
            this.renderChapters();
        } catch (error) {
            console.error('[Dashboard] Failed to load data:', error);
            document.getElementById('reflectionsLoading').textContent = 'Failed to load reflections. Please try refreshing.';
        }
    },

    unwrapResults(data) {
        if (Array.isArray(data)) return data;
        if (data && Array.isArray(data.results)) return data.results;
        return [];
    },

    // =========================================
    // Chapter Info
    // =========================================

    getChapterInfo(slug) {
        if (this.CHAPTER_MAP[slug]) return this.CHAPTER_MAP[slug];
        // Fallback: parse slug
        const parts = slug.split('-');
        const num = parseInt(parts[0]);
        const title = parts.slice(1).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        return { number: num || '?', title: title || slug };
    },

    // =========================================
    // Summary
    // =========================================

    renderSummary() {
        const total = this.reflections.length;
        const chapterSlugs = [...new Set(this.reflections.map(r => r.chapter_slug))];
        const totalChapters = Math.max(Object.keys(this.CHAPTER_MAP).length, chapterSlugs.length);

        let mostRecent = '—';
        if (total > 0) {
            const dates = this.reflections
                .map(r => r.updated_at || r.created_at)
                .filter(Boolean)
                .sort()
                .reverse();
            if (dates.length > 0) {
                mostRecent = new Date(dates[0]).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', year: 'numeric'
                });
            }
        }

        document.getElementById('statTotalReflections').textContent = total;
        document.getElementById('statChaptersCount').textContent = `${chapterSlugs.length} of ${totalChapters}`;
        document.getElementById('statMostRecent').textContent = mostRecent;
    },

    // =========================================
    // Chapter Accordion
    // =========================================

    renderChapters() {
        const accordion = document.getElementById('chapterAccordion');
        const noMsg = document.getElementById('noReflectionsMsg');

        if (this.reflections.length === 0) {
            noMsg.style.display = 'block';
            accordion.innerHTML = '';
            accordion.appendChild(noMsg);
            return;
        }

        noMsg.style.display = 'none';

        // Group by chapter
        const byChapter = {};
        this.reflections.forEach(r => {
            const slug = r.chapter_slug || 'unknown';
            if (!byChapter[slug]) byChapter[slug] = [];
            byChapter[slug].push(r);
        });

        // Sort by chapter number
        const sortedSlugs = Object.keys(byChapter).sort((a, b) => {
            return (this.getChapterInfo(a).number || 0) - (this.getChapterInfo(b).number || 0);
        });

        const html = sortedSlugs.map(slug => {
            const info = this.getChapterInfo(slug);
            const refs = byChapter[slug];
            const count = refs.length;
            const dates = refs.map(r => r.updated_at || r.created_at).filter(Boolean).sort().reverse();
            const lastDate = dates.length > 0
                ? new Date(dates[0]).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                : '';

            const entriesHtml = refs.map(r => this.renderEntry(r)).join('');

            return `
                <div class="mr-chapter-card" data-chapter="${this.esc(slug)}">
                    <div class="mr-chapter-header" onclick="Dashboard.toggleChapter(this)">
                        <div class="mr-chapter-info">
                            <div class="mr-chapter-title">Chapter ${info.number}: ${this.esc(info.title)}</div>
                            <div class="mr-chapter-meta">${count} reflection${count !== 1 ? 's' : ''}${lastDate ? ' &middot; Last updated ' + lastDate : ''}</div>
                        </div>
                        <svg class="mr-chapter-toggle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                    <div class="mr-chapter-body">
                        <div class="mr-chapter-content">${entriesHtml}</div>
                    </div>
                </div>`;
        }).join('');

        accordion.innerHTML = html;
    },

    renderEntry(r) {
        const date = r.updated_at || r.created_at;
        const dateStr = date
            ? new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
            : '';

        return `
            <div class="mr-entry" id="ref-${r.id}">
                <div class="mr-entry-header">
                    <span class="mr-entry-title">${this.esc(r.title || 'Reflection')}</span>
                    <span class="mr-entry-date">${dateStr}</span>
                </div>
                <div class="mr-entry-text">${this.esc(r.content || '')}</div>
                <div class="mr-entry-actions">
                    <button class="mr-btn-action" onclick="Dashboard.editReflection(${r.id})">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        Edit
                    </button>
                    <button class="mr-btn-action delete" onclick="Dashboard.deleteReflection(${r.id})">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14H7L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                        Delete
                    </button>
                </div>
            </div>`;
    },

    toggleChapter(headerEl) {
        headerEl.closest('.mr-chapter-card').classList.toggle('open');
    },

    // =========================================
    // Edit / Delete Reflections
    // =========================================

    editReflection(id) {
        const entry = document.getElementById(`ref-${id}`);
        if (!entry) return;

        const textEl = entry.querySelector('.mr-entry-text');
        const actionsEl = entry.querySelector('.mr-entry-actions');
        const currentText = textEl.textContent.trim();

        textEl.innerHTML = `<textarea class="mr-edit-textarea">${this.esc(currentText)}</textarea>`;
        actionsEl.innerHTML = `
            <div class="mr-edit-actions">
                <button class="mr-btn-save" onclick="Dashboard.saveEdit(${id})">Save</button>
                <button class="mr-btn-cancel" onclick="Dashboard.cancelEdit()">Cancel</button>
            </div>`;

        textEl.querySelector('textarea').focus();
    },

    async saveEdit(id) {
        const entry = document.getElementById(`ref-${id}`);
        if (!entry) return;

        const textarea = entry.querySelector('.mr-edit-textarea');
        const newContent = textarea.value.trim();
        if (!newContent) return;

        try {
            await API.updateReflection(id, { content: newContent });
            const ref = this.reflections.find(r => r.id === id);
            if (ref) ref.content = newContent;
            this.renderChapters();
        } catch (error) {
            alert('Failed to save: ' + error.message);
        }
    },

    cancelEdit() {
        this.renderChapters();
    },

    async deleteReflection(id) {
        if (!confirm('Are you sure you want to delete this reflection?')) return;

        try {
            await API.request(`/reflections/mine/${id}/`, { method: 'DELETE' });
            this.reflections = this.reflections.filter(r => r.id !== id);
            this.renderSummary();
            this.renderChapters();
        } catch (error) {
            alert('Failed to delete: ' + error.message);
        }
    },

    // =========================================
    // Goals (localStorage)
    // =========================================

    loadGoals() {
        try {
            this.goals = JSON.parse(localStorage.getItem('wop-personal-goals') || '[]');
        } catch {
            this.goals = [];
        }
        this.renderGoals();
    },

    saveGoals() {
        localStorage.setItem('wop-personal-goals', JSON.stringify(this.goals));
    },

    setupGoalHandlers() {
        document.getElementById('addGoalBtn')?.addEventListener('click', () => this.addGoal());
        document.getElementById('goalInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.addGoal();
            }
        });
    },

    addGoal() {
        const input = document.getElementById('goalInput');
        const text = input.value.trim();
        if (!text) return;

        this.goals.unshift({
            id: Date.now(),
            text: text,
            createdAt: new Date().toISOString(),
            completedAt: null,
            status: 'active'
        });

        this.saveGoals();
        this.renderGoals();
        input.value = '';
    },

    toggleGoal(id) {
        const goal = this.goals.find(g => g.id === id);
        if (!goal) return;

        if (goal.status === 'active') {
            goal.status = 'completed';
            goal.completedAt = new Date().toISOString();
        } else {
            goal.status = 'active';
            goal.completedAt = null;
        }

        this.saveGoals();
        this.renderGoals();
    },

    deleteGoal(id) {
        this.goals = this.goals.filter(g => g.id !== id);
        this.saveGoals();
        this.renderGoals();
    },

    renderGoals() {
        const list = document.getElementById('goalsList');
        if (!list) return;

        if (this.goals.length === 0) {
            list.innerHTML = '<p class="mr-empty">No goals yet. Add your first commitment above.</p>';
            return;
        }

        // Active first, then completed
        const sorted = [...this.goals].sort((a, b) => {
            if (a.status === 'active' && b.status !== 'active') return -1;
            if (a.status !== 'active' && b.status === 'active') return 1;
            return 0;
        });

        list.innerHTML = sorted.map(g => {
            const done = g.status === 'completed';
            const dateStr = new Date(g.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            const completedStr = g.completedAt
                ? ' &middot; Completed ' + new Date(g.completedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                : '';

            return `
                <div class="mr-goal-card${done ? ' completed' : ''}">
                    <button class="mr-goal-checkbox" onclick="Dashboard.toggleGoal(${g.id})" title="${done ? 'Mark as active' : 'Mark as completed'}">
                        ${done ? '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
                    </button>
                    <div class="mr-goal-body">
                        <div class="mr-goal-text">${this.esc(g.text)}</div>
                        <div class="mr-goal-meta">Set ${dateStr}${completedStr}</div>
                    </div>
                    <button class="mr-goal-delete" onclick="Dashboard.deleteGoal(${g.id})" title="Delete goal">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>`;
        }).join('');
    },

    // =========================================
    // Export
    // =========================================

    setupExport() {
        document.getElementById('exportBtn')?.addEventListener('click', () => this.exportReflections());
    },

    exportReflections() {
        const lines = [];
        lines.push('MY REFLECTIONS & GOALS');
        lines.push('Words of Plainness');
        lines.push('Exported: ' + new Date().toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        }));
        lines.push('');
        lines.push('='.repeat(50));

        // Group reflections by chapter
        const byChapter = {};
        this.reflections.forEach(r => {
            const slug = r.chapter_slug || 'unknown';
            if (!byChapter[slug]) byChapter[slug] = [];
            byChapter[slug].push(r);
        });

        const sortedSlugs = Object.keys(byChapter).sort((a, b) => {
            return (this.getChapterInfo(a).number || 0) - (this.getChapterInfo(b).number || 0);
        });

        if (sortedSlugs.length > 0) {
            lines.push('');
            lines.push('REFLECTIONS');
            lines.push('-'.repeat(50));

            sortedSlugs.forEach(slug => {
                const info = this.getChapterInfo(slug);
                lines.push('');
                lines.push(`Chapter ${info.number}: ${info.title}`);
                lines.push('-'.repeat(30));

                byChapter[slug].forEach(r => {
                    lines.push('');
                    lines.push(`  ${r.title || 'Reflection'}`);
                    const date = r.updated_at || r.created_at;
                    if (date) {
                        lines.push(`  Date: ${new Date(date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`);
                    }
                    lines.push('');
                    (r.content || '').split('\n').forEach(line => lines.push('  ' + line));
                });
                lines.push('');
            });
        } else {
            lines.push('');
            lines.push('No reflections recorded yet.');
        }

        // Goals
        if (this.goals.length > 0) {
            lines.push('');
            lines.push('='.repeat(50));
            lines.push('');
            lines.push('PERSONAL GOALS');
            lines.push('-'.repeat(50));
            lines.push('');

            this.goals.forEach(g => {
                const status = g.status === 'completed' ? '[COMPLETED]' : '[ACTIVE]';
                const dateStr = new Date(g.createdAt).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
                lines.push(`${status} ${g.text}`);
                lines.push(`  Set: ${dateStr}`);
                if (g.completedAt) {
                    lines.push(`  Completed: ${new Date(g.completedAt).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`);
                }
                lines.push('');
            });
        }

        const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'my-reflections-words-of-plainness.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    // =========================================
    // Utilities
    // =========================================

    esc(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => Dashboard.init(), 100);
});

window.Dashboard = Dashboard;
