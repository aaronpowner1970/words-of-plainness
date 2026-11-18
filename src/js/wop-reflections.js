/**
 * WORDS OF PLAINNESS — Unified Reflection Storage (device-only)
 * ==============================================================
 *
 * The one store for everything a reader writes on this site: R·J·W pause
 * answers, Articles reflections, card commitments and card reflections,
 * Chapter 6 pathway reflections, the Seeking Jesus journal, and the reader's
 * own questions ("My questions" in the Reflections panel).
 *
 * Everything stays in this browser's localStorage until the reader clears it.
 * Nothing here, or anywhere else on the site, sends it off the device
 * (CODE-SITE-18, SITE step 27; rulings SITE-JOURNAL-DEVICE-ONLY and
 * SITE-ACCOUNTS-RETIRE, 24 Oct 2026).
 *
 * Loaded on every page (layouts/base.njk, in <head>), after
 * /js/wop-reflection-sources.js. Attaches window.wopReflections.
 *
 * LOCALSTORAGE KEYS
 *   wop-reflection-{chapterId}   JSON array of entries (the only store)
 *   wop-migration-done           "1" once the first (pre-2026) migration ran
 *
 * ENTRY
 *   id            string, unique within its bucket
 *   type          "reflection" | "commitment" | "pathway-choice"
 *                 | "reflect" | "journal" | "witness"   (R·J·W tabs; Articles use "reflect")
 *                 | "question"                           (My questions)
 *   chapterId     bucket id, e.g. "chapter-11-the-living-christ", "seeking-jesus"
 *   chapterTitle  readable title kept with the entry
 *   promptLabel   the prompt (or card) the entry answers, as plain text
 *   content       the reader's words, exactly as typed
 *   timestamp     ISO 8601, when the words were last written
 *   downloadedAt  ISO 8601, when the entry was last included in a download (optional)
 *   meta          { key, pauseId, section, includeInDocument, cardId, tier, confidence,
 *                   pathway, step, module, article, pageUrl, carriedOver }
 *
 * CARRY-OVER (every load; each step only acts on keys that still exist)
 *   1. the first migration (wop-reflection-{slug}-{1|2|3}, wop_ch06_ref_*, wop-card-*), unchanged
 *   2. wop-rjw-{pauseId}::{reflect|journal|witness} (+ ::witness-include-document) and the
 *      older Articles key wop-rjw-A01 → entries of type reflect / journal / witness.
 *      The reader's words are copied byte for byte; the old key is removed only after the
 *      copy has been read back.
 *   3. sjn:journal-queue (the old Seeking Jesus upload queue): any entry not already in
 *      the store is copied in; the queue is removed only when every entry is in the store.
 *   4. account leftovers are removed: wop_access_token, wop_refresh_token, wop-auth-token,
 *      wop-user and wop-engagement-queue (rulings SITE-ACCOUNTS-RETIRE and
 *      SITE-JOURNAL-ENGAGEMENT-QUEUE).
 */

(function () {
    'use strict';

    if (window.wopReflections && window.wopReflections.version >= 2) return;

    var PREFIX = 'wop-reflection-';
    var RJW_PREFIX = 'wop-rjw-';
    var RJW_TABS = ['reflect', 'journal', 'witness'];
    var ARTICLES_ID = 'articles-of-interfaith-discipleship';
    var ARTICLES_TITLE = 'Articles of Interfaith Discipleship';
    var SJN_ID = 'seeking-jesus';
    var SJN_TITLE = 'Seeking Jesus of Nazareth';
    // An R·J·W pause id that several chapters share (the closing pause) was stored
    // without its chapter, so its chapter cannot be known. Such answers are kept
    // here rather than guessed into a chapter.
    var UNRECORDED_ID = 'rjw-chapter-not-recorded';
    var UNRECORDED_TITLE = 'Reflect · Journal · Witness (chapter not recorded)';
    var ACCOUNT_KEYS = ['wop_access_token', 'wop_refresh_token', 'wop-auth-token', 'wop-user', 'wop-engagement-queue'];

    function store() {
        try { return window.localStorage; } catch (e) { return null; }
    }

    function sources() {
        var s = window.WOP_REFLECTION_SOURCES || {};
        return { chapters: s.chapters || {}, pauses: s.pauses || [], articles: s.articles || {} };
    }

    function keysWithPrefix(prefix) {
        var ls = store(), out = [];
        if (!ls) return out;
        for (var i = 0; i < ls.length; i++) {
            var k = ls.key(i);
            if (k && k.indexOf(prefix) === 0) out.push(k);
        }
        return out;
    }

    function stripTags(html) {
        if (!html) return '';
        var div = document.createElement('div');
        div.innerHTML = String(html).replace(/<\/p>\s*<p[^>]*>/gi, '</p>\n\n<p>').replace(/<br\s*\/?>/gi, '\n');
        return (div.textContent || '').replace(/[ \t]+\n/g, '\n').trim();
    }

    /**
     * Best-effort chapter title from a chapterId slug.
     * Handles formats like "chapter-01-introduction" and "01-introduction".
     */
    function titleFromSlug(chapterId) {
        if (!chapterId) return 'Unknown';
        var slug = chapterId.replace(/^chapter-/, '').replace(/^\d+-/, '');
        return slug.split('-').map(function (w) {
            return w.charAt(0).toUpperCase() + w.slice(1);
        }).join(' ');
    }

    var idCounter = 0;
    function newId() {
        idCounter = (idCounter + 1) % 1000;
        return Date.now().toString() + '-' + idCounter + Math.random().toString(36).slice(2, 7);
    }

    /**
     * Identity of an entry: a new entry with the same identity replaces the old one.
     * Entries that carry meta.key are matched on that key alone; older entries on
     * type + promptLabel + pathway/step/cardId, as before.
     */
    function sameIdentity(e, n) {
        var em = e.meta || {}, nm = n.meta || {};
        if (em.key || nm.key) return !!em.key && em.key === nm.key;
        if (e.type !== n.type) return false;
        if (e.promptLabel !== n.promptLabel) return false;
        if ((em.pathway || '') !== (nm.pathway || '')) return false;
        if ((em.step || '') !== (nm.step || '')) return false;
        if ((em.cardId || '') !== (nm.cardId || '')) return false;
        return true;
    }

    function findExistingIndex(entries, entry) {
        for (var i = 0; i < entries.length; i++) {
            if (sameIdentity(entries[i], entry)) return i;
        }
        return -1;
    }

    function readBucket(chapterId) {
        var ls = store();
        if (!ls) return [];
        try {
            var raw = ls.getItem(PREFIX + chapterId);
            if (raw) {
                var arr = JSON.parse(raw);
                if (Array.isArray(arr)) return arr;
            }
        } catch (e) { /* corrupt data — treat as empty */ }
        return [];
    }

    function writeBucket(chapterId, entries) {
        var ls = store();
        if (!ls) throw new Error('localStorage unavailable');
        if (entries.length) ls.setItem(PREFIX + chapterId, JSON.stringify(entries));
        else ls.removeItem(PREFIX + chapterId);
    }

    function byNewest(a, b) {
        return (b.timestamp || '').localeCompare(a.timestamp || '');
    }

    var notifyTimer = null;
    function notify() {
        clearTimeout(notifyTimer);
        notifyTimer = setTimeout(function () {
            try { window.dispatchEvent(new CustomEvent('wop:reflections-changed')); } catch (e) { /* old browser */ }
        }, 0);
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    var api = {
        version: 2,
        UNRECORDED_ID: UNRECORDED_ID,

        /**
         * Save an entry. An existing entry with the same identity is replaced.
         * If the reader's words are unchanged, the entry keeps when it was
         * written and whether it has been downloaded.
         */
        save: function (opts) {
            var entry = {
                id: newId(),
                type: opts.type || 'reflection',
                chapterId: opts.chapterId,
                chapterTitle: opts.chapterTitle || titleFromSlug(opts.chapterId),
                promptLabel: opts.promptLabel || '',
                content: opts.content == null ? '' : String(opts.content),
                timestamp: opts.timestamp || new Date().toISOString(),
                meta: opts.meta || {}
            };

            var entries = readBucket(entry.chapterId);
            var idx = findExistingIndex(entries, entry);
            if (idx !== -1) {
                var old = entries[idx];
                entry.id = old.id;
                if (old.content === entry.content && !opts.timestamp) {
                    entry.timestamp = old.timestamp || entry.timestamp;
                    if (old.downloadedAt) entry.downloadedAt = old.downloadedAt;
                    if (!entry.promptLabel && old.promptLabel) entry.promptLabel = old.promptLabel;
                }
                entries[idx] = entry;
            } else {
                entries.push(entry);
            }
            writeBucket(entry.chapterId, entries);
            notify();
            return entry;
        },

        /**
         * Save as the reader types: an empty answer removes the entry instead.
         * Returns the saved entry, or null when it was removed.
         */
        put: function (opts) {
            var text = opts.content == null ? '' : String(opts.content);
            if (!text.trim()) {
                api.removeMatching(opts.chapterId, { type: opts.type || 'reflection', promptLabel: opts.promptLabel || '', meta: opts.meta || {} });
                return null;
            }
            return api.save(opts);
        },

        /** Find the stored entry with the same identity as `probe`, or null. */
        find: function (chapterId, probe) {
            var entries = readBucket(chapterId);
            var idx = findExistingIndex(entries, { type: probe.type, promptLabel: probe.promptLabel || '', meta: probe.meta || {} });
            return idx === -1 ? null : entries[idx];
        },

        /** Remove the entry with the same identity as `probe`. */
        removeMatching: function (chapterId, probe) {
            var entries = readBucket(chapterId);
            var idx = findExistingIndex(entries, { type: probe.type, promptLabel: probe.promptLabel || '', meta: probe.meta || {} });
            if (idx === -1) return false;
            entries.splice(idx, 1);
            writeBucket(chapterId, entries);
            notify();
            return true;
        },

        /** All entries for one chapter or page, newest first. */
        load: function (chapterId) {
            return readBucket(chapterId).sort(byNewest);
        },

        /** All entries for several chapter or page ids, newest first. */
        loadMany: function (ids) {
            var all = [];
            (ids || []).forEach(function (id) { all = all.concat(readBucket(id)); });
            return all.sort(byNewest);
        },

        /** Every entry on this device, newest first. */
        loadAll: function () {
            var all = [];
            keysWithPrefix(PREFIX).forEach(function (key) {
                try {
                    var arr = JSON.parse(store().getItem(key));
                    if (Array.isArray(arr)) all = all.concat(arr);
                } catch (e) { /* skip corrupt keys */ }
            });
            return all.sort(byNewest);
        },

        /** Remove all entries for a chapter. */
        clear: function (chapterId) {
            var ls = store();
            if (ls) ls.removeItem(PREFIX + chapterId);
            notify();
        },

        /** Delete a single entry by id within a chapter. */
        delete: function (chapterId, id) {
            var entries = readBucket(chapterId).filter(function (e) { return e.id !== id; });
            writeBucket(chapterId, entries);
            notify();
        },

        /** True when the entry was written (or changed) after it was last downloaded. */
        isPending: function (entry) {
            return !(entry && entry.downloadedAt && entry.downloadedAt >= (entry.timestamp || ''));
        },

        /** Record that these entries were included in a download. */
        markDownloaded: function (entries) {
            var when = new Date().toISOString();
            var byBucket = {};
            (entries || []).forEach(function (e) {
                if (!e || !e.chapterId) return;
                (byBucket[e.chapterId] = byBucket[e.chapterId] || {})[e.id] = true;
            });
            Object.keys(byBucket).forEach(function (chapterId) {
                var bucket = readBucket(chapterId);
                var changed = false;
                bucket.forEach(function (e) {
                    if (byBucket[chapterId][e.id]) { e.downloadedAt = when; changed = true; }
                });
                if (changed) writeBucket(chapterId, bucket);
            });
            notify();
        },

        /**
         * How many answers "Clear my answers from this browser" would remove:
         * every stored entry, any R·J·W answer not yet carried over, and the
         * Seeking Jesus goals and self-check answers.
         */
        countForClear: function () {
            var n = api.loadAll().length + uncarriedRjwAnswerKeys().length;
            var ls = store();
            if (!ls) return n;
            try {
                var goals = JSON.parse(ls.getItem('sjn:goals') || '[]');
                if (Array.isArray(goals)) n += goals.length;
            } catch (e) { /* ignore */ }
            keysWithPrefix('sjn:selfcheck-').forEach(function (k) {
                try {
                    var v = JSON.parse(ls.getItem(k) || '{}');
                    if (v && Object.keys(v).some(function (q) { return q !== '_at'; })) n += 1;
                } catch (e) { /* ignore */ }
            });
            return n;
        },

        /**
         * "Clear my answers from this browser" (spec 3.5; ruling
         * SITE-JOURNAL-CHECK6-CLEAR): removes every wop-reflection-* key, every
         * wop-rjw-* key (answers not yet carried over, with their witness flags),
         * and from Seeking Jesus sjn:journal-queue, sjn:goals and sjn:selfcheck-*.
         * It leaves sjn:lens, codings, reading progress and narration position.
         * Returns how many answers were removed.
         */
        clearAll: function () {
            var n = api.countForClear();
            var ls = store();
            if (!ls) return 0;
            var keys = keysWithPrefix(PREFIX)
                .concat(keysWithPrefix(RJW_PREFIX))
                .concat(keysWithPrefix('sjn:selfcheck-'));
            ['sjn:journal-queue', 'sjn:goals'].forEach(function (k) {
                if (ls.getItem(k) !== null) keys.push(k);
            });
            keys.forEach(function (k) { ls.removeItem(k); });
            notify();
            return n;
        },

        /** The id entries are grouped under for display ("06-embrace-the-savior" → its chapterId). */
        groupIdFor: function (chapterId) {
            var ch = sources().chapters;
            if (chapterId && !ch[chapterId] && ch['chapter-' + chapterId]) return 'chapter-' + chapterId;
            return chapterId;
        },

        /** Readable title for a chapter or page id. */
        titleFor: function (chapterId, fallback) {
            if (chapterId === UNRECORDED_ID) return UNRECORDED_TITLE;
            var ch = sources().chapters[chapterId];
            if (ch && ch.title) {
                return (ch.number && !ch.standalone) ? ('Chapter ' + ch.number + ': ' + ch.title) : ch.title;
            }
            return fallback || titleFromSlug(chapterId);
        },

        /** Sort key so that chapters come in reading order. */
        orderFor: function (chapterId) {
            if (chapterId === UNRECORDED_ID) return 9999;
            var ch = sources().chapters[chapterId];
            if (ch && ch.standalone) return chapterId === ARTICLES_ID ? 1000 : 1001;
            if (ch && ch.number) return ch.number;
            var m = /^(?:chapter-)?(\d+)-/.exec(chapterId || '');
            return m ? parseInt(m[1], 10) : 2000;
        },

        /** The plain-text prompt for an R·J·W pause tab, from the build-time sources. */
        pausePrompt: function (chapterId, pauseId, tab) {
            var p = sources().pauses.filter(function (x) { return x.chapterId === chapterId && x.id === pauseId; })[0];
            return p ? { section: p.title || '', prompt: stripTags(p[tab] || '') } : null;
        },

        /** The Articles reflection prompt and title, from the build-time sources. */
        articlePrompt: function (code) {
            var a = sources().articles[code];
            return a ? { title: a.title || '', prompt: stripTags(a.prompt || '') } : null;
        },

        stripTags: stripTags,
        titleFromSlug: titleFromSlug
    };

    // ------------------------------------------------------------------
    // 1. The first migration — runs once (unchanged)
    // ------------------------------------------------------------------

    var STEP_LABELS = {
        assess: 'Honest Assessment',
        align: 'What Stirred in Me',
        act: 'My Commitment'
    };

    function runMigration() {
        var ls = store();
        if (!ls || ls.getItem('wop-migration-done')) return;

        // Step 1 — standard chapter reflections: wop-reflection-{slug}-{1|2|3}
        var keysToDelete = [];
        for (var i = 0; i < ls.length; i++) {
            var key = ls.key(i);
            if (!key || key.indexOf('wop-reflection-') !== 0) continue;
            var match = key.match(/^wop-reflection-(.+)-([123])$/);
            if (!match) continue;
            var slug = match[1];
            var promptNum = match[2];
            var rawVal;
            try { rawVal = ls.getItem(key); } catch (e) { continue; }
            if (!rawVal) continue;
            var parsed;
            try { parsed = JSON.parse(rawVal); } catch (e) { continue; }
            if (Array.isArray(parsed)) continue;
            if (!parsed || typeof parsed !== 'object' || !parsed.content) continue;
            var ts = parsed.timestamp;
            if (typeof ts === 'number') ts = new Date(ts).toISOString();
            else if (!ts) ts = new Date().toISOString();
            api.save({
                chapterId: parsed.chapter_slug || slug,
                chapterTitle: titleFromSlug(parsed.chapter_slug || slug),
                type: 'reflection',
                promptLabel: parsed.title || ('Reflection ' + promptNum),
                content: parsed.content,
                meta: {},
                timestamp: ts
            });
            keysToDelete.push(key);
        }
        keysToDelete.forEach(function (k) { ls.removeItem(k); });

        // Step 2 — Ch6 pathway reflections: wop_ch06_ref_{path}_{step}
        ['skeptic', 'seeker', 'disciple'].forEach(function (path) {
            ['assess', 'align', 'act'].forEach(function (step) {
                var k = 'wop_ch06_ref_' + path + '_' + step;
                var val;
                try { val = ls.getItem(k); } catch (e) { return; }
                if (!val) return;
                api.save({
                    chapterId: '06-embrace-the-savior',
                    chapterTitle: 'Embrace the Savior',
                    type: 'reflection',
                    promptLabel: STEP_LABELS[step] || step,
                    content: val,
                    meta: { pathway: path, step: step },
                    timestamp: new Date().toISOString()
                });
                ls.removeItem(k);
            });
        });

        // Step 3 — card-chapter commitments: wop-card-{chapterId}
        keysWithPrefix('wop-card-').forEach(function (ck) {
            var chId = ck.replace('wop-card-', '');
            var data;
            try { data = JSON.parse(ls.getItem(ck)); } catch (e) { return; }
            if (!data || typeof data !== 'object') return;
            var confidence = data.confidence || 0;
            Object.keys(data).forEach(function (cardKey) {
                if (cardKey === 'confidence') return;
                var card = data[cardKey];
                if (!card || typeof card !== 'object') return;
                var ts = card.timestamp || new Date().toISOString();
                api.save({
                    chapterId: chId,
                    chapterTitle: titleFromSlug(chId),
                    type: 'commitment',
                    promptLabel: card.title || cardKey,
                    content: card.label || card.value || '',
                    meta: { cardId: cardKey, tier: card.value, confidence: confidence },
                    timestamp: ts
                });
                if (card.reflection) {
                    api.save({
                        chapterId: chId,
                        chapterTitle: titleFromSlug(chId),
                        type: 'reflection',
                        promptLabel: (card.title || cardKey) + ' (Reflection)',
                        content: card.reflection,
                        meta: { cardId: cardKey },
                        timestamp: ts
                    });
                }
            });
            ls.removeItem(ck);
        });

        ls.setItem('wop-migration-done', '1');
    }

    // ------------------------------------------------------------------
    // 2. R·J·W carry-over: wop-rjw-* → the store
    // ------------------------------------------------------------------

    /** Every wop-rjw-* key that holds an answer (not a true/false flag). */
    function uncarriedRjwAnswerKeys() {
        var ls = store();
        if (!ls) return [];
        return keysWithPrefix(RJW_PREFIX).filter(function (k) {
            var parsed = parseRjwKey(k);
            if (!parsed) return false;
            var v = ls.getItem(k);
            return v != null && v !== 'true' && v !== 'false' && v.trim() !== '';
        });
    }

    /** "wop-rjw-pause-closing::journal" → { pauseId, tab }; "wop-rjw-A01" → Articles, reflect. */
    function parseRjwKey(key) {
        var rest = key.substring(RJW_PREFIX.length);
        var parts = rest.split('::');
        if (parts.length === 2 && RJW_TABS.indexOf(parts[1]) !== -1 && parts[0]) {
            return { pauseId: parts[0], tab: parts[1], legacyArticle: false };
        }
        if (parts.length === 1 && /^A\d{2}$/.test(rest)) {
            return { pauseId: 'aoid-' + rest, tab: 'reflect', legacyArticle: true };
        }
        return null;
    }

    function chaptersForPause(pauseId) {
        var ids = [];
        sources().pauses.forEach(function (p) {
            if (p.id === pauseId && ids.indexOf(p.chapterId) === -1) ids.push(p.chapterId);
        });
        return ids;
    }

    /** Where an old R·J·W answer belongs, and how to label it. */
    function placeRjw(pauseId, tab) {
        if (pauseId.indexOf('aoid-') === 0) {
            var code = pauseId.substring(5);
            var art = api.articlePrompt(code);
            return {
                chapterId: ARTICLES_ID, chapterTitle: ARTICLES_TITLE,
                promptLabel: art ? art.prompt : '',
                section: art ? art.title : '',
                key: 'aoid:' + code, extra: { article: code }
            };
        }
        var chapters = chaptersForPause(pauseId);
        if (chapters.length === 1) {
            var info = api.pausePrompt(chapters[0], pauseId, tab) || { section: '', prompt: '' };
            return {
                chapterId: chapters[0], chapterTitle: api.titleFor(chapters[0]),
                promptLabel: info.prompt, section: info.section,
                key: 'rjw:' + pauseId + ':' + tab, extra: {}
            };
        }
        return {
            chapterId: UNRECORDED_ID, chapterTitle: UNRECORDED_TITLE,
            promptLabel: '', section: '',
            key: 'rjw:' + pauseId + ':' + tab, extra: {}
        };
    }

    function carryOverRjw() {
        var ls = store();
        if (!ls) return;
        // Without the sources a pause's chapter cannot be known; wait for a load that has them.
        if (!window.WOP_REFLECTION_SOURCES) return;
        var stamp = new Date().toISOString();
        keysWithPrefix(RJW_PREFIX).forEach(function (key) {
            var parsed = parseRjwKey(key);
            if (!parsed) return;
            var value = ls.getItem(key);
            if (value == null) return;
            if (value.trim() === '') { ls.removeItem(key); return; }   // nothing written

            var place = placeRjw(parsed.pauseId, parsed.tab);
            var entryKey = place.key;
            if (parsed.legacyArticle) {
                // The pre-fix Articles key. If the current key holds different words,
                // keep both rather than choose.
                var current = ls.getItem(RJW_PREFIX + parsed.pauseId + '::reflect');
                var existing = api.find(place.chapterId, { type: 'reflect', meta: { key: entryKey } });
                var other = (current != null && current.trim() !== '') ? current : (existing ? existing.content : null);
                if (other != null && other !== value) entryKey = entryKey + ':earlier';
                else if (other === value) { ls.removeItem(key); return; }
            }

            var meta = { key: entryKey, pauseId: parsed.pauseId, section: place.section, carriedOver: true };
            Object.keys(place.extra).forEach(function (k) { meta[k] = place.extra[k]; });
            if (parsed.tab === 'witness') {
                meta.includeInDocument = ls.getItem(RJW_PREFIX + parsed.pauseId + '::witness-include-document') === 'true';
            }

            try {
                var saved = api.save({
                    chapterId: place.chapterId,
                    chapterTitle: place.chapterTitle,
                    type: parsed.tab,
                    promptLabel: place.promptLabel,
                    content: value,
                    meta: meta,
                    timestamp: stamp
                });
                var check = api.find(place.chapterId, { type: parsed.tab, meta: { key: entryKey } });
                if (!check || check.content !== value || check.id !== saved.id) return;   // keep the old key
            } catch (e) {
                return;   // storage full: keep the old key, nothing is lost
            }

            ls.removeItem(key);
            if (parsed.tab === 'witness') {
                ls.removeItem(RJW_PREFIX + parsed.pauseId + '::witness-include-document');
                ls.removeItem(RJW_PREFIX + parsed.pauseId + '::witness-submit-community');
            }
        });

        // Witness flags whose answer was empty or is already carried over.
        keysWithPrefix(RJW_PREFIX).forEach(function (key) {
            var m = key.match(/^wop-rjw-(.+)::witness-(include-document|submit-community)$/);
            if (!m) return;
            var answer = ls.getItem(RJW_PREFIX + m[1] + '::witness');
            if (answer == null || answer.trim() === '') ls.removeItem(key);
        });
    }

    // ------------------------------------------------------------------
    // 3. Seeking Jesus: the old upload queue → the store
    // ------------------------------------------------------------------

    function carryOverSjnQueue() {
        var ls = store();
        if (!ls) return;
        var raw = ls.getItem('sjn:journal-queue');
        if (raw == null) return;
        var queue;
        try { queue = JSON.parse(raw); } catch (e) { return; }
        if (!Array.isArray(queue)) return;

        var allIn = true;
        queue.forEach(function (p) {
            if (!p || !p.card_id) return;
            var bucket = readBucket(SJN_ID);
            var has = bucket.some(function (e) { return e.meta && e.meta.cardId === p.card_id && e.content === (p.commitment_text || ''); });
            if (!has && (p.commitment_text || '').trim() !== '') {
                try {
                    api.save({
                        chapterId: SJN_ID, chapterTitle: SJN_TITLE, type: 'commitment',
                        promptLabel: p.card_title || '', content: p.commitment_text,
                        meta: { key: 'sjn-queue:' + p.card_id + ':' + (p.commitment_text || '').length, cardId: p.card_id, tier: 'seeking-jesus', confidence: p.confidence || 0, carriedOver: true }
                    });
                } catch (e) { allIn = false; return; }
                has = readBucket(SJN_ID).some(function (e) { return e.meta && e.meta.cardId === p.card_id && e.content === p.commitment_text; });
                if (!has) allIn = false;
            }
            if ((p.reflection_text || '').trim() !== '') {
                var probe = { type: 'reflection', meta: { key: 'sjn-queue-reflection:' + p.card_id } };
                if (!api.find(SJN_ID, probe)) {
                    try {
                        api.save({
                            chapterId: SJN_ID, chapterTitle: SJN_TITLE, type: 'reflection',
                            promptLabel: (p.card_title || '') + ' (Reflection)', content: p.reflection_text,
                            meta: { key: 'sjn-queue-reflection:' + p.card_id, cardId: p.card_id, carriedOver: true }
                        });
                    } catch (e) { allIn = false; }
                }
            }
        });
        if (allIn) ls.removeItem('sjn:journal-queue');
    }

    // ------------------------------------------------------------------
    // 4. Account leftovers
    // ------------------------------------------------------------------

    function removeAccountLeftovers() {
        var ls = store();
        if (!ls) return;
        ACCOUNT_KEYS.forEach(function (k) {
            try { ls.removeItem(k); } catch (e) { /* ignore */ }
        });
    }

    // ------------------------------------------------------------------
    // Initialise
    // ------------------------------------------------------------------

    window.wopReflections = api;
    try { runMigration(); } catch (e) { /* never block the page */ }
    try { carryOverRjw(); } catch (e) { /* never block the page */ }
    try { carryOverSjnQueue(); } catch (e) { /* never block the page */ }
    try { removeAccountLeftovers(); } catch (e) { /* never block the page */ }

})();
