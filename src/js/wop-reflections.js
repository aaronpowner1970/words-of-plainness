/**
 * WORDS OF PLAINNESS — Unified Reflection Storage
 * =================================================
 *
 * Single source of truth for all user reflection data.
 * Replaces three separate localStorage patterns with one consistent schema.
 *
 * Attaches to window.wopReflections — no imports, plain browser JS.
 *
 * LOCALSTORAGE KEY STRUCTURE:
 *   wop-reflection-{chapterId}   — JSON array of entry objects
 *   wop-migration-done           — "1" once legacy data has been migrated
 *
 * ENTRY SCHEMA:
 * @typedef {Object} ReflectionEntry
 * @property {string} id            - Date.now().toString() at save time
 * @property {string} type          - "reflection" | "commitment" | "pathway-choice"
 * @property {string} chapterId     - e.g. "01-introduction"
 * @property {string} chapterTitle  - e.g. "Introduction"
 * @property {string} promptLabel   - human-readable label for the prompt or card
 * @property {string} content       - the user's text or selected option
 * @property {string} timestamp     - ISO 8601 string
 * @property {Object} meta          - {} for standard reflections; see below
 *
 * META — card-chapter commitments:
 *   { cardId: "card-1", tier: "option-2", confidence: 4 }
 *
 * META — Ch6 pathway reflections:
 *   { pathway: "seeker", step: "assess" }
 */

(function () {
    'use strict';

    var PREFIX = 'wop-reflection-';

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /**
     * Best-effort chapter title from a chapterId slug.
     * Handles formats like "chapter-01-introduction" and "01-introduction".
     * Strips "chapter-" prefix if present, then the leading number, capitalises each word.
     * @param {string} chapterId
     * @returns {string}
     */
    function titleFromSlug(chapterId) {
        if (!chapterId) return 'Unknown';
        var slug = chapterId.replace(/^chapter-/, '').replace(/^\d+-/, '');
        var parts = slug.split('-');
        return parts.map(function (w) {
            return w.charAt(0).toUpperCase() + w.slice(1);
        }).join(' ');
    }

    /**
     * Find an existing entry index that matches the "identity" of a new entry.
     * Identity = same type + promptLabel + matching meta identity fields
     * (pathway, step, cardId). If found, the caller can replace rather than append.
     * @param {ReflectionEntry[]} entries
     * @param {ReflectionEntry} entry
     * @returns {number} index or -1
     */
    function findExistingIndex(entries, entry) {
        var nMeta = entry.meta || {};
        for (var i = 0; i < entries.length; i++) {
            var e = entries[i];
            if (e.type !== entry.type) continue;
            if (e.promptLabel !== entry.promptLabel) continue;
            var eMeta = e.meta || {};
            if ((eMeta.pathway || '') !== (nMeta.pathway || '')) continue;
            if ((eMeta.step || '') !== (nMeta.step || '')) continue;
            if ((eMeta.cardId || '') !== (nMeta.cardId || '')) continue;
            return i;
        }
        return -1;
    }

    /**
     * Read the entry array for a chapter from localStorage.
     * @param {string} chapterId
     * @returns {ReflectionEntry[]}
     */
    function readBucket(chapterId) {
        try {
            var raw = localStorage.getItem(PREFIX + chapterId);
            if (raw) return JSON.parse(raw);
        } catch (e) { /* corrupt data — treat as empty */ }
        return [];
    }

    /**
     * Write an entry array back to localStorage for a chapter.
     * @param {string} chapterId
     * @param {ReflectionEntry[]} entries
     */
    function writeBucket(chapterId, entries) {
        localStorage.setItem(PREFIX + chapterId, JSON.stringify(entries));
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    var api = {
        /**
         * Save a new reflection entry.
         *
         * @param {Object} opts
         * @param {string} opts.chapterId
         * @param {string} opts.chapterTitle
         * @param {string} opts.type          - "reflection" | "commitment" | "pathway-choice"
         * @param {string} opts.promptLabel
         * @param {string} opts.content
         * @param {Object} [opts.meta]
         * @param {string} [opts.timestamp]   - override (used by migration)
         * @returns {ReflectionEntry} the saved entry
         */
        save: function (opts) {
            var entry = {
                id: Date.now().toString(),
                type: opts.type || 'reflection',
                chapterId: opts.chapterId,
                chapterTitle: opts.chapterTitle || titleFromSlug(opts.chapterId),
                promptLabel: opts.promptLabel || '',
                content: opts.content || '',
                timestamp: opts.timestamp || new Date().toISOString(),
                meta: opts.meta || {}
            };

            var entries = readBucket(entry.chapterId);
            var idx = findExistingIndex(entries, entry);
            if (idx !== -1) {
                // Preserve original id, update everything else
                entry.id = entries[idx].id;
                entries[idx] = entry;
            } else {
                entries.push(entry);
            }
            writeBucket(entry.chapterId, entries);
            return entry;
        },

        /**
         * Load all entries for a single chapter, newest first.
         * @param {string} chapterId
         * @returns {ReflectionEntry[]}
         */
        load: function (chapterId) {
            return readBucket(chapterId).sort(function (a, b) {
                return (b.timestamp || '').localeCompare(a.timestamp || '');
            });
        },

        /**
         * Load entries across ALL chapters, newest first.
         * Scans every localStorage key with the wop-reflection- prefix.
         * @returns {ReflectionEntry[]}
         */
        loadAll: function () {
            var all = [];
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                if (key && key.indexOf(PREFIX) === 0) {
                    try {
                        var arr = JSON.parse(localStorage.getItem(key));
                        if (Array.isArray(arr)) {
                            all = all.concat(arr);
                        }
                    } catch (e) { /* skip corrupt keys */ }
                }
            }
            return all.sort(function (a, b) {
                return (b.timestamp || '').localeCompare(a.timestamp || '');
            });
        },

        /**
         * Remove all entries for a chapter.
         * @param {string} chapterId
         */
        clear: function (chapterId) {
            localStorage.removeItem(PREFIX + chapterId);
        },

        /**
         * Delete a single entry by id within a chapter.
         * @param {string} chapterId
         * @param {string} id
         */
        delete: function (chapterId, id) {
            var entries = readBucket(chapterId).filter(function (e) {
                return e.id !== id;
            });
            if (entries.length > 0) {
                writeBucket(chapterId, entries);
            } else {
                localStorage.removeItem(PREFIX + chapterId);
            }
        }
    };

    // ------------------------------------------------------------------
    // Migration — runs once on first script load
    // ------------------------------------------------------------------

    /**
     * Step-label map for Ch6 interactive reflections.
     * @type {Object<string, string>}
     */
    var STEP_LABELS = {
        assess: 'Honest Assessment',
        align: 'What Stirred in Me',
        act: 'My Commitment'
    };

    function runMigration() {
        if (localStorage.getItem('wop-migration-done')) return;

        console.log('[wop-reflections] Running one-time migration…');

        // ----------------------------------------------------------
        // Step 1 — System 1: standard chapter reflections
        //   Keys: wop-reflection-{slug}-{1|2|3}
        // ----------------------------------------------------------
        var keysToDelete = [];

        for (var i = 0; i < localStorage.length; i++) {
            var key = localStorage.key(i);
            if (!key || key.indexOf('wop-reflection-') !== 0) continue;

            // Match keys ending in -1, -2, or -3 (old per-prompt format)
            var match = key.match(/^wop-reflection-(.+)-([123])$/);
            if (!match) continue;

            var slug = match[1];
            var promptNum = match[2];

            // Skip keys that belong to the NEW unified format (they hold arrays)
            var rawVal;
            try { rawVal = localStorage.getItem(key); } catch (e) { continue; }
            if (!rawVal) continue;

            var parsed;
            try { parsed = JSON.parse(rawVal); } catch (e) { continue; }

            // New-format keys hold arrays; old-format keys hold objects with a content field
            if (Array.isArray(parsed)) continue;
            if (!parsed || typeof parsed !== 'object' || !parsed.content) continue;

            var ts = parsed.timestamp;
            if (typeof ts === 'number') {
                ts = new Date(ts).toISOString();
            } else if (!ts) {
                ts = new Date().toISOString();
            }

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

        keysToDelete.forEach(function (k) { localStorage.removeItem(k); });

        // ----------------------------------------------------------
        // Step 2 — System 3: Ch6 pathway reflections
        //   Keys: wop_ch06_ref_{path}_{step}
        // ----------------------------------------------------------
        var paths = ['skeptic', 'seeker', 'disciple'];
        var steps = ['assess', 'align', 'act'];

        paths.forEach(function (path) {
            steps.forEach(function (step) {
                var k = 'wop_ch06_ref_' + path + '_' + step;
                var val;
                try { val = localStorage.getItem(k); } catch (e) { return; }
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

                localStorage.removeItem(k);
            });
        });

        // ----------------------------------------------------------
        // Step 3 — System 4: card-chapter commitments
        //   Keys: wop-card-{chapterId}
        // ----------------------------------------------------------
        var cardKeys = [];
        for (var j = 0; j < localStorage.length; j++) {
            var ck = localStorage.key(j);
            if (ck && ck.indexOf('wop-card-') === 0) cardKeys.push(ck);
        }

        cardKeys.forEach(function (ck) {
            var chId = ck.replace('wop-card-', '');
            var data;
            try { data = JSON.parse(localStorage.getItem(ck)); } catch (e) { return; }
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

                // If there is a reflection attached to the card, save it too
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

            localStorage.removeItem(ck);
        });

        // Mark migration complete
        localStorage.setItem('wop-migration-done', '1');
        console.log('[wop-reflections] Migration complete.');
    }

    // ------------------------------------------------------------------
    // Initialise
    // ------------------------------------------------------------------

    window.wopReflections = api;
    runMigration();

})();
