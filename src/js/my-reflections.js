/**
 * WORDS OF PLAINNESS — My Discipleship Journal
 * ==============================================
 *
 * Unified dashboard for all reader engagement data:
 * - R·J·W pause-point responses (from Django API)
 * - Card-chapter commitments (from Django API)
 * - localStorage fallback for unauthenticated users
 */

var CHAPTER_INFO = {
    'chapter-01-introduction':       { number: 1,  title: 'Introduction' },
    'chapter-02-our-search':         { number: 2,  title: 'Our Search' },
    'chapter-03-academic-knowledge': { number: 3,  title: 'Academic Knowledge' },
    'chapter-04-spiritual-knowledge':{ number: 4,  title: 'Spiritual Knowledge' },
    'chapter-05-sincere-prayer':     { number: 5,  title: 'Sincere Prayer' },
    'chapter-06-embrace-the-savior': { number: 6,  title: 'Embrace the Savior' },
    'chapter-07-prophecies-birth-youth': { number: 7,  title: 'Prophecies, Birth, and Youth' },
    'chapter-08-baptism-temptations-ministry': { number: 8,  title: 'Baptism, Temptations, and Mortal Ministry' },
    'chapter-09-christs-personal-character': { number: 9,  title: 'Yehoshua the Man' },
    'chapter-10-suffering-trial-crucifixion-resurrection': { number: 10, title: 'Suffering, Trial, Crucifixion, and Resurrection' },
    'chapter-11-the-living-christ':  { number: 11, title: 'The Living Christ' },
    'chapter-12-beatitudes':         { number: 12, title: 'The Beatitudes' },
    'chapter-13-sermon-on-the-mount':{ number: 13, title: 'The Sermon on the Mount' },
    'chapter-14-prayer-as-a-lifestyle':{ number: 14, title: 'Prayer as a Lifestyle' },
    'chapter-16-keeping-the-sabbath': { number: 16, title: 'Keeping the Sabbath' }
};

function djGetChapterInfo(slug) {
    if (CHAPTER_INFO[slug]) return CHAPTER_INFO[slug];
    var parts = slug.replace(/^chapter-/, '').split('-');
    var num = parseInt(parts[0]);
    var title = parts.slice(1).map(function(w) {
        return w.charAt(0).toUpperCase() + w.slice(1);
    }).join(' ');
    return { number: num || 0, title: title || slug };
}

function djEsc(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

function djFormatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric'
    });
}

function djStarsHtml(n) {
    var s = '';
    for (var i = 1; i <= 5; i++) {
        s += (i <= n) ? '\u2605' : '\u2606';
    }
    return '<span class="dj-stars">' + s + '</span>';
}

var Journal = {
    rjwEntries: [],
    commitments: [],

    init: function() {
        var hasAPI = window.API && typeof API.isAuthenticated === 'function';
        var isAuthed = hasAPI && API.isAuthenticated();

        var signInBtn = document.getElementById('djSignIn');
        if (signInBtn) {
            signInBtn.addEventListener('click', function() {
                var modal = document.getElementById('authModal');
                if (modal) modal.style.display = 'flex';
            });
        }

        if (isAuthed) {
            document.getElementById('djAuthGate').style.display = 'none';
            document.getElementById('djContent').style.display = 'block';
            this.loadFromAPI();
        } else {
            this.loadFromLocalStorage();
        }

        if (hasAPI) {
            var self = this;
            this._authCheck = setInterval(function() {
                if (API.isAuthenticated() && document.getElementById('djContent').style.display === 'none') {
                    clearInterval(self._authCheck);
                    document.getElementById('djAuthGate').style.display = 'none';
                    document.getElementById('djContent').style.display = 'block';
                    self.loadFromAPI();
                }
            }, 500);
        }
    },

    loadFromAPI: function() {
        var self = this;
        Promise.all([
            API.getAllPauseResponses().catch(function() { return []; }),
            API.getAllCardCommitments().catch(function() { return []; })
        ]).then(function(results) {
            var rjwRaw = results[0];
            var ccRaw = results[1];
            self.rjwEntries = Array.isArray(rjwRaw) ? rjwRaw : (rjwRaw && rjwRaw.results ? rjwRaw.results : []);
            self.commitments = Array.isArray(ccRaw) ? ccRaw : (ccRaw && ccRaw.results ? ccRaw.results : []);
            document.getElementById('djLoading').style.display = 'none';
            self.render();
        }).catch(function(err) {
            console.error('[Journal] Load failed:', err);
            document.getElementById('djLoading').textContent = 'Failed to load. Please refresh.';
        });
    },

    loadFromLocalStorage: function() {
        var rjw = [];
        for (var i = 0; i < localStorage.length; i++) {
            var k = localStorage.key(i);
            if (k && k.indexOf('wop-rjw-') === 0) {
                var val = localStorage.getItem(k);
                if (!val || !val.trim() || val === 'true' || val === 'false') continue;
                var remainder = k.substring(8);
                var parts = remainder.split('::');
                if (parts.length !== 2) continue;
                var tabKey = parts[1];
                if (['reflect','journal','witness'].indexOf(tabKey) === -1) continue;
                rjw.push({
                    pause_id: parts[0],
                    chapter_slug: 'unknown',
                    tab_type: tabKey,
                    response_text: val,
                    include_in_document: localStorage.getItem('wop-rjw-' + parts[0] + '::witness-include-document') === 'true',
                    updated_at: null
                });
            }
        }
        this.rjwEntries = rjw;

        this.commitments = [];
        if (window.wopReflections) {
            var all = wopReflections.loadAll();
            var self = this;
            all.forEach(function(e) {
                if (e.type === 'commitment') {
                    self.commitments.push({
                        chapter_slug: e.chapterId || '',
                        card_id: (e.meta && e.meta.cardId) || '',
                        card_title: e.promptLabel || '',
                        tier: (e.meta && e.meta.tier) || '',
                        commitment_text: e.content || '',
                        reflection_text: '',
                        confidence: (e.meta && e.meta.confidence) || 0,
                        updated_at: e.timestamp || null
                    });
                }
            });
        }

        if (this.rjwEntries.length === 0 && this.commitments.length === 0) {
            return;
        }

        document.getElementById('djAuthGate').style.display = 'none';
        document.getElementById('djContent').style.display = 'block';
        document.getElementById('djLoading').style.display = 'none';
        this.render();
    },

    render: function() {
        this.renderStats();
        this.renderChapters();
        this.renderDocument();
    },

    renderStats: function() {
        var totalRjw = this.rjwEntries.filter(function(r) {
            return r.response_text && r.response_text.trim();
        }).length;
        var totalCC = this.commitments.length;
        var total = totalRjw + totalCC;

        var slugs = {};
        this.rjwEntries.forEach(function(r) { if (r.chapter_slug) slugs[r.chapter_slug] = true; });
        this.commitments.forEach(function(c) { if (c.chapter_slug) slugs[c.chapter_slug] = true; });
        var chapterCount = Object.keys(slugs).length;

        var allDates = [];
        this.rjwEntries.forEach(function(r) { if (r.updated_at) allDates.push(r.updated_at); });
        this.commitments.forEach(function(c) { if (c.updated_at) allDates.push(c.updated_at); });
        allDates.sort().reverse();
        var recent = allDates.length > 0 ? djFormatDate(allDates[0]) : '\u2014';

        document.getElementById('statTotal').textContent = total;
        document.getElementById('statChapters').textContent = chapterCount + ' of ' + Object.keys(CHAPTER_INFO).length;
        document.getElementById('statRecent').textContent = recent;
    },

    renderChapters: function() {
        var accordion = document.getElementById('chapterAccordion');
        var emptyMsg = document.getElementById('djEmpty');

        var byChapter = {};
        this.rjwEntries.forEach(function(r) {
            var s = r.chapter_slug || 'unknown';
            if (!byChapter[s]) byChapter[s] = { rjw: [], commitments: [] };
            if (r.response_text && r.response_text.trim()) {
                byChapter[s].rjw.push(r);
            }
        });
        this.commitments.forEach(function(c) {
            var s = c.chapter_slug || 'unknown';
            if (!byChapter[s]) byChapter[s] = { rjw: [], commitments: [] };
            byChapter[s].commitments.push(c);
        });

        var slugs = Object.keys(byChapter).sort(function(a, b) {
            return (djGetChapterInfo(a).number || 0) - (djGetChapterInfo(b).number || 0);
        });

        if (slugs.length === 0) {
            emptyMsg.style.display = 'block';
            accordion.innerHTML = '';
            accordion.appendChild(emptyMsg);
            return;
        }

        emptyMsg.style.display = 'none';

        var html = slugs.map(function(slug) {
            var info = djGetChapterInfo(slug);
            var data = byChapter[slug];
            var entryCount = data.rjw.length + data.commitments.length;

            var entriesHtml = '';

            if (data.rjw.length > 0) {
                var byPause = {};
                data.rjw.forEach(function(r) {
                    var pid = r.pause_id || 'default';
                    if (!byPause[pid]) byPause[pid] = [];
                    byPause[pid].push(r);
                });
                Object.keys(byPause).forEach(function(pid) {
                    entriesHtml += '<div class="dj-entry-group">';
                    entriesHtml += '<div class="dj-entry-group-label">Reflect \u00b7 Journal \u00b7 Witness</div>';
                    byPause[pid].forEach(function(r) {
                        var cls = 'dj-entry dj-entry-' + r.tab_type;
                        entriesHtml += '<div class="' + cls + '">';
                        entriesHtml += '<div class="dj-entry-label ' + r.tab_type + '">' + r.tab_type + '</div>';
                        entriesHtml += '<div class="dj-entry-text">' + djEsc(r.response_text) + '</div>';
                        entriesHtml += '</div>';
                    });
                    entriesHtml += '</div>';
                });
            }

            if (data.commitments.length > 0) {
                entriesHtml += '<div class="dj-entry-group">';
                entriesHtml += '<div class="dj-entry-group-label">Discipleship Commitments</div>';
                data.commitments.forEach(function(c) {
                    entriesHtml += '<div class="dj-entry dj-entry-commitment">';
                    entriesHtml += '<div class="dj-entry-label commitment">' + djEsc(c.card_title || c.card_id) + '</div>';
                    entriesHtml += '<div class="dj-entry-text">' + djEsc(c.commitment_text) + '</div>';
                    if (c.reflection_text && c.reflection_text.trim()) {
                        entriesHtml += '<div class="dj-entry-text" style="margin-top:6px;opacity:0.8;font-style:italic;">' + djEsc(c.reflection_text) + '</div>';
                    }
                    if (c.confidence > 0) {
                        entriesHtml += '<div class="dj-commitment-meta">Confidence: ' + djStarsHtml(c.confidence) + '</div>';
                    }
                    entriesHtml += '</div>';
                });
                entriesHtml += '</div>';
            }

            return '<div class="dj-chapter-card" data-chapter="' + djEsc(slug) + '">' +
                '<div class="dj-chapter-header" onclick="Journal.toggleChapter(this)">' +
                    '<div>' +
                        '<div class="dj-chapter-title">Chapter ' + info.number + ': ' + djEsc(info.title) + '</div>' +
                        '<div class="dj-chapter-meta">' + entryCount + ' entr' + (entryCount === 1 ? 'y' : 'ies') + '</div>' +
                    '</div>' +
                    '<svg class="dj-chapter-toggle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
                '</div>' +
                '<div class="dj-chapter-body"><div class="dj-chapter-content">' + entriesHtml + '</div></div>' +
            '</div>';
        }).join('');

        accordion.innerHTML = html;
    },

    renderDocument: function() {
        var container = document.getElementById('pauseDocSection');
        if (!container) return;

        var chapters = {};

        this.rjwEntries.forEach(function(r) {
            if (!r.response_text || !r.response_text.trim()) return;
            var s = r.chapter_slug || 'unknown';
            if (!chapters[s]) chapters[s] = { rjw: {}, commitments: [] };
            if (!chapters[s].rjw[r.pause_id]) chapters[s].rjw[r.pause_id] = {};
            chapters[s].rjw[r.pause_id][r.tab_type] = r;
        });

        this.commitments.forEach(function(c) {
            var s = c.chapter_slug || 'unknown';
            if (!chapters[s]) chapters[s] = { rjw: {}, commitments: [] };
            chapters[s].commitments.push(c);
        });

        var slugs = Object.keys(chapters).sort(function(a, b) {
            return (djGetChapterInfo(a).number || 0) - (djGetChapterInfo(b).number || 0);
        });

        if (slugs.length === 0) {
            container.innerHTML = '<p class="dj-empty">No entries recorded yet.</p>';
            return;
        }

        var html = '<div class="pd-document">';
        html += '<div class="pd-doc-header">';
        html += '<h3 class="pd-doc-title">My Discipleship Document</h3>';
        html += '<p class="pd-doc-subtitle">Words of Plainness \u00b7 Personal Study Record</p>';
        html += '</div>';

        slugs.forEach(function(slug) {
            var info = djGetChapterInfo(slug);
            var data = chapters[slug];
            html += '<div class="pd-chapter">';
            html += '<h4 class="pd-chapter-title">Chapter ' + info.number + ' \u00b7 ' + djEsc(info.title) + '</h4>';

            var pauseIds = Object.keys(data.rjw).sort();
            pauseIds.forEach(function(pid) {
                var tabs = data.rjw[pid];
                if (pauseIds.length > 1) {
                    var label = pid.replace(/-/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
                    html += '<div class="pd-pause-label">' + djEsc(label) + '</div>';
                }
                if (tabs.journal && tabs.journal.response_text && tabs.journal.response_text.trim()) {
                    html += '<div class="pd-entry pd-journal"><div class="pd-entry-label">Journal</div>';
                    html += '<div class="pd-entry-text">' + djEsc(tabs.journal.response_text) + '</div></div>';
                } else {
                    html += '<div class="pd-entry pd-journal pd-empty"><div class="pd-entry-label">Journal</div>';
                    html += '<div class="pd-entry-text">No journal entry for this section.</div></div>';
                }
                if (tabs.witness && tabs.witness.include_in_document && tabs.witness.response_text && tabs.witness.response_text.trim()) {
                    html += '<div class="pd-entry pd-witness"><div class="pd-entry-label">Witness</div>';
                    html += '<div class="pd-entry-text">' + djEsc(tabs.witness.response_text) + '</div></div>';
                } else {
                    html += '<div class="pd-entry pd-witness pd-empty"><div class="pd-entry-label">Witness</div>';
                    html += '<div class="pd-entry-text">No witness entry for this section.</div></div>';
                }
            });

            if (data.commitments.length > 0) {
                html += '<div class="pd-pause-label">Discipleship Commitments</div>';
                data.commitments.forEach(function(c) {
                    html += '<div class="pd-entry pd-commitment"><div class="pd-entry-label">' + djEsc(c.card_title || c.card_id) + '</div>';
                    html += '<div class="pd-entry-text">' + djEsc(c.commitment_text) + '</div></div>';
                });
            }

            html += '</div>';
        });

        html += '<div class="pd-actions">';
        html += '<button class="dj-btn-primary" onclick="window.print()">Print / Save as PDF</button>';
        html += '</div>';
        html += '</div>';

        container.innerHTML = html;
    },

    toggleChapter: function(headerEl) {
        headerEl.closest('.dj-chapter-card').classList.toggle('open');
    }
};

window.Journal = Journal;

document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() { Journal.init(); }, 150);
});
