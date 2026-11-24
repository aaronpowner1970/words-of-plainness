/**
 * WORDS OF PLAINNESS — My Discipleship Journal (/my-reflections/)
 * ================================================================
 *
 * The device-only journal page (CODE-SITE-18, SITE step 27, spec 3.6): every
 * entry kept in this browser by window.wopReflections (js/wop-reflections.js),
 * grouped by chapter or page. No sign-in, no sync, no server call. The
 * Download and Clear actions are the Reflections panel's own
 * (js/wop-reflections-panel.js, inline mode, placed in #djActions).
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
    'chapter-16-keeping-the-sabbath': { number: 16, title: 'Keeping the Sabbath' },
    'articles-of-interfaith-discipleship': { number: 99, title: 'Articles of Interfaith Discipleship', standalone: true },
    'seeking-jesus':                 { number: 98, title: 'Seeking Jesus of Nazareth', standalone: true }
};

var ARTICLE_TITLES = {
    'A01': 'Of Plainness', 'A02': 'Of God', 'A03': 'Of Creation and Life',
    'A04': "Of God's Word", 'A05': 'Of Jesus Christ', 'A06': 'Of Salvation',
    'A07': 'Of the Kingdom at Hand', 'A08': 'Of Fellow Believers',
    'A09': 'Of Finding Our Way', 'A10': 'Of Living by Grace',
    'A11': 'Of Covenants and Commitments', 'A12': 'Of Immortality and Eternal Life',
    'A13': 'Of Our Confidence'
};
// The Second Edition build adds its extra titles through window.WOP_AOID2_SECOND_EDITION
// (an inline script in pages/my-reflections.njk); the site as it stands does not set it.
if (window.WOP_AOID2_SECOND_EDITION) {
    var SECOND_EDITION_TITLES = window.WOP_AOID2_SECOND_EDITION.articleTitles || {};
    Object.keys(SECOND_EDITION_TITLES).forEach(function (k) { ARTICLE_TITLES[k] = SECOND_EDITION_TITLES[k]; });
}

function djArticleLabel(slug, pauseId) {
    if (slug !== 'articles-of-interfaith-discipleship') return '';
    return ARTICLE_TITLES[(pauseId || '').replace(/^aoid-/, '')] || '';
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
        s += (i <= n) ? '★' : '☆';
    }
    return '<span class="dj-stars">' + s + '</span>';
}

var TYPE_LABELS = {
    reflect: 'Reflect', journal: 'Journal', witness: 'Witness', question: 'My question',
    reflection: 'Reflection', commitment: 'Commitment', 'pathway-choice': 'Pathway choice'
};
var NOT_YET_DOWNLOADED = 'Not yet downloaded';   // spec 6.4, word for word

function djSection(e) {
    var m = e.meta || {};
    if (e.type === 'question') return '';
    if (m.section) return m.section;
    if (e.chapterId === 'articles-of-interfaith-discipleship' && m.pauseId) return djArticleLabel(e.chapterId, m.pauseId);
    if (e.type === 'commitment' || (e.type === 'reflection' && m.cardId)) return (e.promptLabel || '').replace(/ \(Reflection\)$/, '');
    return '';
}

function djPrompt(e) {
    var m = e.meta || {};
    if (e.type === 'question' || e.type === 'commitment' || (e.type === 'reflection' && m.cardId)) return '';
    return e.promptLabel || '';
}

var Journal = {
    entries: [],

    init: function() {
        var self = this;
        this.load();
        window.addEventListener('wop:reflections-changed', function () { self.load(); });
        window.addEventListener('storage', function (e) {
            if (!e.key || e.key.indexOf('wop-reflection-') === 0) self.load();
        });
    },

    load: function() {
        this.entries = window.wopReflections ? window.wopReflections.loadAll() : [];
        this.render();
    },

    groups: function() {
        var R = window.wopReflections;
        var byId = {};
        this.entries.forEach(function (e) {
            var gid = R.groupIdFor(e.chapterId);
            if (!byId[gid]) byId[gid] = { id: gid, title: R.titleFor(gid, e.chapterTitle), entries: [] };
            byId[gid].entries.push(e);
        });
        return Object.keys(byId).sort(function (a, b) {
            var d = R.orderFor(a) - R.orderFor(b);
            return d !== 0 ? d : byId[a].title.localeCompare(byId[b].title);
        }).map(function (k) { return byId[k]; });
    },

    render: function() {
        this.renderStats();
        this.renderChapters();
        this.renderDocument();
    },

    renderStats: function() {
        var R = window.wopReflections;
        var slugs = {};
        this.entries.forEach(function (e) {
            var gid = R.groupIdFor(e.chapterId);
            if (CHAPTER_INFO[gid] && !CHAPTER_INFO[gid].standalone) slugs[gid] = true;
        });
        var chapterCount = Object.keys(slugs).length;
        var newest = this.entries.length ? this.entries[0].timestamp : null;

        document.getElementById('statTotal').textContent = this.entries.length;
        // G5 (CODE-SITE-20): the count of chapters the reader has written in, with no 'of n'
        // total that would mark the others as unfinished.
        document.getElementById('statChapters').textContent = chapterCount;
        document.getElementById('statRecent').textContent = newest ? djFormatDate(newest) : '—';
    },

    renderChapters: function() {
        var R = window.wopReflections;
        var accordion = document.getElementById('chapterAccordion');
        var emptyMsg = document.getElementById('djEmpty');
        var groups = this.groups();

        // #djEmpty lives inside the accordion, so the first render with entries
        // removes it; check it exists before touching it (CODE-SITE-39).
        if (groups.length === 0) {
            if (emptyMsg) {
                emptyMsg.style.display = 'block';
            }
            accordion.innerHTML = '';
            if (emptyMsg) {
                accordion.appendChild(emptyMsg);
            }
            return;
        }
        if (emptyMsg) {
            emptyMsg.style.display = 'none';
        }

        var openIds = {};
        Array.prototype.forEach.call(accordion.querySelectorAll('.dj-chapter-card.open'), function (c) {
            openIds[c.getAttribute('data-chapter')] = true;
        });

        var html = groups.map(function (g) {
            var n = g.entries.length;
            var entriesHtml = g.entries.map(function (e) {
                var type = TYPE_LABELS[e.type] ? e.type : 'reflection';
                var cls = { reflect: 'reflect', journal: 'journal', witness: 'witness', commitment: 'commitment', question: 'question' }[type] || 'reflect';
                var label = TYPE_LABELS[type];
                var sec = djSection(e);
                if (sec) label += ' · ' + sec;
                var out = '<div class="dj-entry dj-entry-' + cls + '">';
                out += '<div class="dj-entry-label ' + cls + '">' + djEsc(label) + '</div>';
                var pr = djPrompt(e);
                if (pr) out += '<div class="dj-entry-prompt">' + djEsc(pr) + '</div>';
                out += '<div class="dj-entry-text">' + djEsc(e.content) + '</div>';
                if (e.type === 'commitment' && e.meta && e.meta.confidence > 0) {
                    out += '<div class="dj-commitment-meta">Confidence: ' + djStarsHtml(e.meta.confidence) + '</div>';
                }
                out += '<div class="dj-entry-date">' + djEsc(djFormatDate(e.timestamp));
                if (R.isPending(e)) out += ' <span class="dj-entry-marker">' + NOT_YET_DOWNLOADED + '</span>';
                out += '</div></div>';
                return out;
            }).join('');

            return '<div class="dj-chapter-card' + (openIds[g.id] ? ' open' : '') + '" data-chapter="' + djEsc(g.id) + '">' +
                '<div class="dj-chapter-header" onclick="Journal.toggleChapter(this)">' +
                    '<div>' +
                        '<div class="dj-chapter-title">' + djEsc(g.title) + '</div>' +
                        '<div class="dj-chapter-meta">' + n + ' entr' + (n === 1 ? 'y' : 'ies') + '</div>' +
                    '</div>' +
                    '<svg class="dj-chapter-toggle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
                '</div>' +
                '<div class="dj-chapter-body"><div class="dj-chapter-content">' + entriesHtml + '</div></div>' +
            '</div>';
        }).join('');

        accordion.innerHTML = html;
    },

    // The printable "My Discipleship Document" (Print / Save as PDF), as before:
    // Reflect and Journal for each pause, the Witness only when the reader ticked
    // "Include this witness in my portable discipleship document".
    renderDocument: function() {
        var container = document.getElementById('printDocContent');
        if (!container) return;
        var groups = this.groups();

        if (groups.length === 0) {
            container.innerHTML = '<p class="dj-empty">No entries recorded yet.</p>';
            return;
        }

        var html = '';
        html += '<div class="pd-doc-header">';
        html += '<h3 class="pd-doc-title">My Discipleship Document</h3>';
        html += '<p class="pd-doc-subtitle">Words of Plainness · Personal Study Record</p>';
        html += '</div>';

        groups.forEach(function (g) {
            var info = CHAPTER_INFO[g.id] || {};
            html += '<div class="pd-chapter">';
            html += '<h4 class="pd-chapter-title">' + djEsc(g.title) + '</h4>';

            var pauses = {}, pauseOrder = [], others = [], questions = [];
            g.entries.slice().reverse().forEach(function (e) {
                if (['reflect', 'journal', 'witness'].indexOf(e.type) !== -1) {
                    var pid = (e.meta && (e.meta.pauseId || e.meta.key)) || 'default';
                    if (!pauses[pid]) { pauses[pid] = { section: djSection(e) }; pauseOrder.push(pid); }
                    pauses[pid][e.type] = e;
                } else if (e.type === 'question') {
                    questions.push(e);
                } else {
                    others.push(e);
                }
            });

            pauseOrder.forEach(function (pid) {
                var tabs = pauses[pid];
                if (tabs.section) html += '<div class="pd-pause-label">' + djEsc(tabs.section) + '</div>';
                if (tabs.reflect && tabs.reflect.content.trim()) {
                    html += '<div class="pd-entry pd-journal"><div class="pd-entry-label">Reflect</div>';
                    html += '<div class="pd-entry-text">' + djEsc(tabs.reflect.content) + '</div></div>';
                }
                // G5 (Teaching Practices v1.1; CODE-SITE-20): a tab left blank is simply not
                // listed; nothing marks it as missing.
                if (tabs.journal && tabs.journal.content.trim()) {
                    html += '<div class="pd-entry pd-journal"><div class="pd-entry-label">Journal</div>';
                    html += '<div class="pd-entry-text">' + djEsc(tabs.journal.content) + '</div></div>';
                }
                if (tabs.witness && tabs.witness.meta && tabs.witness.meta.includeInDocument && tabs.witness.content.trim()) {
                    html += '<div class="pd-entry pd-witness"><div class="pd-entry-label">Witness</div>';
                    html += '<div class="pd-entry-text">' + djEsc(tabs.witness.content) + '</div></div>';
                }
            });

            if (others.length > 0) {
                html += '<div class="pd-pause-label">Discipleship Commitments</div>';
                others.forEach(function (c) {
                    var label = djSection(c) || TYPE_LABELS[c.type] || '';
                    if (c.type === 'reflection' && c.meta && c.meta.cardId) label += ' · ' + TYPE_LABELS.reflection;
                    html += '<div class="pd-entry pd-commitment"><div class="pd-entry-label">' + djEsc(label) + '</div>';
                    html += '<div class="pd-entry-text">' + djEsc(c.content) + '</div></div>';
                });
            }

            if (questions.length > 0) {
                html += '<div class="pd-pause-label">My questions</div>';
                questions.forEach(function (q) {
                    html += '<div class="pd-entry pd-journal"><div class="pd-entry-text">' + djEsc(q.content) + '</div></div>';
                });
            }

            html += '</div>';
        });

        container.innerHTML = html;
    },

    toggleChapter: function(headerEl) {
        headerEl.closest('.dj-chapter-card').classList.toggle('open');
    }
};

window.Journal = Journal;

document.addEventListener('DOMContentLoaded', function() {
    Journal.init();
});
