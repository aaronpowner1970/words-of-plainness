/**
 * Words of Plainness - Eleventy Configuration
 * 
 * This configuration file controls how Eleventy builds the site.
 * @see https://www.11ty.dev/docs/config/
 */

const fs = require('fs');
const path = require('path');
const scriptureData = require('./src/_data/scriptures.json');
const articleThemes = require('./src/_data/articleThemes.json');
const chapterThemes = require('./src/_data/chapterThemes.json');
const ministryMusic = require('./src/_data/ministryMusic.json');

const MEDIA_BASE = 'https://media.wordsofplainness.org/web/';

module.exports = function(eleventyConfig) {

    // =========================================
    // DEV SERVER - Eleventy v2 built-in server
    // Enable HTTP range requests for audio seeking
    // =========================================

    eleventyConfig.setServerOptions({
        middleware: [
            function(req, res, next) {
                // Only intercept audio/video files
                if (!/\.(mp3|mp4|ogg|wav|m4a|webm)$/i.test(req.url)) {
                    return next();
                }

                const filePath = path.join(__dirname, '_site', decodeURIComponent(req.url.split('?')[0]));

                let stat;
                try {
                    stat = fs.statSync(filePath);
                } catch (e) {
                    return next();
                }

                const total = stat.size;
                const mimeTypes = {
                    '.mp3': 'audio/mpeg',
                    '.mp4': 'video/mp4',
                    '.ogg': 'audio/ogg',
                    '.wav': 'audio/wav',
                    '.m4a': 'audio/mp4',
                    '.webm': 'video/webm'
                };
                const ext = path.extname(filePath).toLowerCase();
                const contentType = mimeTypes[ext] || 'application/octet-stream';
                const range = req.headers.range;

                if (range) {
                    const parts = range.replace(/bytes=/, '').split('-');
                    const start = parseInt(parts[0], 10);
                    const end = parts[1] ? parseInt(parts[1], 10) : total - 1;

                    res.writeHead(206, {
                        'Content-Range': `bytes ${start}-${end}/${total}`,
                        'Accept-Ranges': 'bytes',
                        'Content-Length': end - start + 1,
                        'Content-Type': contentType
                    });
                    fs.createReadStream(filePath, { start, end }).pipe(res);
                } else {
                    res.writeHead(200, {
                        'Accept-Ranges': 'bytes',
                        'Content-Length': total,
                        'Content-Type': contentType
                    });
                    fs.createReadStream(filePath).pipe(res);
                }
            }
        ]
    });

    // =========================================
    // PASSTHROUGH COPY
    // These files/folders are copied as-is to _site
    // =========================================
    
    eleventyConfig.addPassthroughCopy("src/assets");
    eleventyConfig.addPassthroughCopy("src/css");
    eleventyConfig.addPassthroughCopy("src/js");
    eleventyConfig.addPassthroughCopy({"src/robots.txt": "robots.txt"});
    
    // =========================================
    // WATCH TARGETS
    // Rebuild when these files change
    // =========================================
    
    eleventyConfig.addWatchTarget("src/css/");
    eleventyConfig.addWatchTarget("src/js/");
    
    // =========================================
    // COLLECTIONS
    // Group content for listing/navigation
    // =========================================
    
    // Chapters collection - sorted by chapter number
    eleventyConfig.addCollection("chapters", function(collectionApi) {
        return collectionApi.getFilteredByGlob("src/chapters/*.{md,njk}")
            .filter(item => !path.basename(item.inputPath).startsWith("_"))
            .sort((a, b) => a.data.chapter - b.data.chapter);
    });

    // Blog posts collection - sorted by date descending (newest first)
    eleventyConfig.addCollection("posts", function(collectionApi) {
        return collectionApi.getFilteredByGlob("src/posts/*.md")
            .filter(item => !path.basename(item.inputPath).startsWith("_"))
            .sort((a, b) => b.date - a.date);
    });
    
    // =========================================
    // FILTERS
    // Transform data in templates
    // =========================================
    
    // JSON stringify for passing data to JavaScript
    eleventyConfig.addFilter("dump", obj => JSON.stringify(obj, null, 2));
    
    // JSON stringify without pretty printing (for inline use)
    eleventyConfig.addFilter("json", obj => JSON.stringify(obj));

    // Count chapters with status "available" across a volume, movement,
    // or a raw chapters array. Backs the derived counts in the volume
    // landing pages and the /writings/ hub so they can't drift from
    // chapter-status.yaml.
    eleventyConfig.addFilter("availableCount", function(input) {
        if (!input) return 0;
        const countIn = arr => (arr || []).filter(c => c && c.status === "available").length;
        if (Array.isArray(input)) return countIn(input);
        if (input.chapters) return countIn(input.chapters);
        if (input.movements) return input.movements.reduce((s, m) => s + countIn(m.chapters), 0);
        return 0;
    });

    // =========================================
    // GO-DEEPER ENGINE (#4 auto-absorb)
    // Recomputes Articles ↔ chapter correlations on EVERY build from
    // collections.chapters. A chapter joins all article correlations the
    // moment it carries a `themes:` frontmatter line (or a chapterThemes.json
    // seed entry). Nothing here is hand-maintained.
    //   Usage: window.WOP_GODEEPER = {{ collections.chapters | goDeeperData | safe }}
    // =========================================
    eleventyConfig.addFilter("goDeeperData", function(chapters) {
        // Frontmatter `themes:` wins; else fall back to the chapterThemes seed.
        function resolveThemes(ch) {
            if (Array.isArray(ch.data.themes) && ch.data.themes.length) return ch.data.themes;
            var key = ch.data.slug || ch.fileSlug;
            return chapterThemes[key] || [];
        }

        // Index only chapters that actually carry themes.
        var indexed = (chapters || []).map(function(ch) {
            var themes = resolveThemes(ch);
            if (!themes.length) return null;
            var t = (ch.data.audio && ch.data.audio.testimony) ? ch.data.audio.testimony : null;
            return {
                slug: ch.data.slug || ch.fileSlug,
                chapter: ch.data.chapter,
                title: ch.data.title,
                description: ch.data.description || '',
                url: ch.url,
                scripture: (ch.data.scripture && ch.data.scripture.reference) || '',
                themes: themes,
                testimony: t ? {
                    file: t.file || '',
                    title: t.title || '',
                    label: t.label || '',
                    duration: t.duration || null
                } : null
            };
        }).filter(Boolean);

        var out = {};
        Object.keys(articleThemes).forEach(function(slug) {
            var art = articleThemes[slug] || {};
            var artThemes = art.themes || [];

            // Score each themed chapter by count of shared themes.
            var scored = indexed.map(function(ch) {
                var overlap = ch.themes.filter(function(th) { return artThemes.indexOf(th) !== -1; }).length;
                return { ch: ch, overlap: overlap };
            }).filter(function(s) { return s.overlap > 0; });

            // Highest overlap first; ties broken by ascending chapter number.
            scored.sort(function(a, b) {
                if (b.overlap !== a.overlap) return b.overlap - a.overlap;
                return (a.ch.chapter || 0) - (b.ch.chapter || 0);
            });

            var top = scored.slice(0, 6).map(function(s) { return s.ch; });

            out[slug] = {
                themes: artThemes,
                searchSeed: art.searchSeed || '',
                chapters: top.map(function(c) {
                    return { chapter: c.chapter, title: c.title, description: c.description, url: c.url, scripture: c.scripture };
                }),
                music: top.filter(function(c) { return c.testimony; }).map(function(c) {
                    return {
                        title: c.testimony.title,
                        file: c.testimony.file,
                        label: c.testimony.label,
                        duration: c.testimony.duration,
                        chapter: c.chapter,
                        url: c.url
                    };
                })
            };
        });

        return JSON.stringify(out);
    });

    // =========================================
    // TESTIMONY-FOR — look up a chapter's primary testimony
    // Backs the "Musical Testimony" badge on /volume-1/ and /volume-2/.
    // Signature: {{ collections.chapters | testimonyFor(ch) }}
    //   → { file, title, label, duration } or null
    // Match order:
    //   1. URL join — chapter-status.yaml ch.url ≡ collection url
    //      (trailing slashes normalized on both sides). This is the safe
    //      path; url is the sole join key because chapter-status.yaml uses
    //      live-site chapter numbering while chapter frontmatter is the
    //      source of the audio filename.
    //   2. Number fallback WITHIN VOLUME — required when a chapter has a
    //      dual-file split (e.g. Ch 6: `.njk` card page carries the live URL
    //      but `-full.md` carries the audio.testimony frontmatter). Falls
    //      back to matching data.chapter within collection entries whose
    //      URL sits under the SAME top-level directory as the requested
    //      URL, so /chapters/… never crosses into /volume-2/chapters/…
    //      (V2 numbering restarts at 1 and would otherwise collide).
    // Alternates are ignored on purpose — the volume badge represents the
    // primary testimony only.
    // =========================================
    eleventyConfig.addFilter("testimonyFor", function(chapters, ch) {
        if (!chapters || !ch || !ch.url) return null;
        var norm = String(ch.url).replace(/\/+$/, '');
        var chNumber = ch.number;

        // Top-level segment of the requested URL — "/chapters" or "/volume-2".
        // Number-fallback matches stay inside this prefix so V1 and V2 don't cross.
        var prefixMatch = norm.match(/^(\/[^\/]+)/);
        var prefix = prefixMatch ? prefixMatch[1] : '';

        var numberCandidate = null;
        for (var i = 0; i < chapters.length; i++) {
            var c = chapters[i];
            var cUrl = c && c.url ? String(c.url).replace(/\/+$/, '') : '';
            var t = c.data && c.data.audio && c.data.audio.testimony;
            if (!t || !t.file) continue;
            if (cUrl === norm) {
                return {
                    file: t.file,
                    title: t.title || '',
                    label: t.label || '',
                    duration: t.duration || ''
                };
            }
            if (numberCandidate) continue;
            if (typeof chNumber !== 'number' || c.data.chapter !== chNumber) continue;
            if (prefix && cUrl.indexOf(prefix + '/') !== 0) continue;
            numberCandidate = {
                file: t.file,
                title: t.title || '',
                label: t.label || '',
                duration: t.duration || ''
            };
        }
        return numberCandidate;
    });

    // =========================================
    // MUSIC CATALOG — flattens every playable testimony into one map
    // Keyed by R2 filename (stable, unique). Consumed client-side by
    // wop-player.js on /articles/ and chapter pages so a testimony
    // trigger can look up its full playback record without duplicating
    // song metadata anywhere.
    //   Usage: window.WOP_MUSIC_CATALOG = {{ collections.chapters | musicCatalog | safe }}
    // Sources (in this order):
    //   1. ministryMusic.json .collection[] + each .alternates[]
    //   2. chapter.data.audio.testimony + each .alternates[]
    // Each entry:
    //   { file, audioUrl, title, style, duration, lyricsUrl, lyricsHtml,
    //     chapter, chapterUrl, isMinistry, isAlternate, primaryFile }
    // lyricsUrl is OPTIONAL — Phase 2 backfills .vtt paths per song.
    // lyricsHtml is the existing inline formatted lyrics fallback for
    // songs without a VTT (drawer renders static text in that case).
    // =========================================
    eleventyConfig.addFilter("musicCatalog", function(chapters) {
        var catalog = {};

        function put(entry) {
            if (!entry.file) return;
            entry.audioUrl = MEDIA_BASE + entry.file;
            catalog[entry.file] = entry;
        }

        // Ministry collection (anthems + alternates)
        (ministryMusic.collection || []).forEach(function(item) {
            var primaryLyrics = item.lyrics
                || (item.hasLyrics ? (ministryMusic.anthemLyrics || '') : '');
            put({
                file: item.file,
                title: item.title,
                style: item.label || '',
                duration: item.duration || '',
                lyricsUrl: item.lyricsUrl || null,
                lyricsHtml: primaryLyrics,
                chapter: null,
                chapterUrl: null,
                isMinistry: true,
                isAlternate: false,
                primaryFile: item.file
            });
            (item.alternates || []).forEach(function(alt) {
                put({
                    file: alt.file,
                    title: item.title,
                    style: alt.label || '',
                    duration: alt.duration || '',
                    lyricsUrl: alt.lyricsUrl || null,
                    lyricsHtml: primaryLyrics,
                    chapter: null,
                    chapterUrl: null,
                    isMinistry: true,
                    isAlternate: true,
                    primaryFile: item.file
                });
            });
        });

        // Chapter testimonies (primaries + alternates)
        (chapters || []).forEach(function(ch) {
            var t = ch.data && ch.data.audio && ch.data.audio.testimony;
            if (!t || !t.file) return;
            var chLyrics = ch.data.lyrics || '';
            put({
                file: t.file,
                title: t.title || '',
                style: t.label || '',
                duration: t.duration || '',
                lyricsUrl: t.lyricsUrl || null,
                lyricsHtml: chLyrics,
                chapter: ch.data.chapter,
                chapterUrl: ch.url,
                isMinistry: false,
                isAlternate: false,
                primaryFile: t.file
            });
            (t.alternates || []).forEach(function(alt) {
                put({
                    file: alt.file,
                    title: t.title || '',
                    style: alt.label || '',
                    duration: alt.duration || '',
                    lyricsUrl: alt.lyricsUrl || null,
                    lyricsHtml: chLyrics,
                    chapter: ch.data.chapter,
                    chapterUrl: ch.url,
                    isMinistry: false,
                    isAlternate: true,
                    primaryFile: t.file
                });
            });
        });

        return JSON.stringify(catalog);
    });

    // Current year/date for templates
    eleventyConfig.addFilter("now", (value, format) => {
        if (format === "YYYY") return new Date().getFullYear();
        return new Date().toISOString();
    });

    // Blog date formatting — "March 31, 2026"
    eleventyConfig.addFilter("blogDate", function(dateObj) {
        if (!dateObj) return '';
        const d = new Date(dateObj);
        const months = ['January','February','March','April','May','June',
                        'July','August','September','October','November','December'];
        return `${months[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
    });

    // ISO date for datetime attributes — "2026-03-31"
    eleventyConfig.addFilter("isoDate", function(dateObj) {
        if (!dateObj) return '';
        const d = new Date(dateObj);
        return d.toISOString().split('T')[0];
    });

    // RFC-3339 date for Atom feeds — "2026-03-31T00:00:00Z"
    eleventyConfig.addFilter("rfc3339Date", function(dateObj) {
        if (!dateObj) return '';
        return new Date(dateObj).toISOString();
    });

    // Get newest date from a collection (for Atom feed <updated>)
    eleventyConfig.addFilter("newestDate", function(collection) {
        if (!collection || !collection.length) return new Date().toISOString();
        const dates = collection.map(item => new Date(item.date));
        return new Date(Math.max(...dates)).toISOString();
    });

    // Build absolute URL from relative path
    eleventyConfig.addFilter("absoluteUrl", function(relPath) {
        const base = "https://www.wordsofplainness.org";
        if (!relPath) return base;
        return base + relPath;
    });

    // Scripture book mappings as JSON (for client-side injection)
    eleventyConfig.addFilter("scriptureBooksJson", function() {
        const data = require('./src/_data/scriptures.json');
        return JSON.stringify(data.books);
    });

    // Lyrics content loader — reads lyrics partial at build time, returns HTML string
    // Usage in templates: {{ chapter | lyricsContent | safe }}
    // Returns empty string if no lyrics file exists for this chapter number
    eleventyConfig.addFilter("lyricsContent", function(chapterNum) {
        if (!chapterNum) return '';
        const padded = String(chapterNum).padStart(2, '0');
        const lyricsPath = path.join(__dirname, 'src', '_includes', 'lyrics', `chapter-${padded}.njk`);
        try {
            return fs.readFileSync(lyricsPath, 'utf8');
        } catch (e) {
            return '';
        }
    });

    // Strip interactive elements from chapter content for View Text panel
    eleventyConfig.addFilter("stripInteractive", function(content) {
        if (!content) return '';
        return content
            // Remove pause-points and their following section-gap divs
            .replace(/<div class="pause-point"[\s\S]*?<\/div>\s*<\/div>\s*<div class="section-gap"><\/div>/g, '')
            // Remove standalone section-gap divs
            .replace(/<div class="section-gap"><\/div>/g, '')
            // Remove citation dagger marks
            .replace(/<span class="cite-mark"[\s\S]*?<\/span>/g, '')
            // Remove bottom learning tools section
            .replace(/<section class="bottom-learning-tools"[\s\S]*?<\/section>/g, '')
            // Remove chapter navigation
            .replace(/<div class="chapter-nav-bottom"[\s\S]*?<\/div>/g, '')
            // Remove discord section
            .replace(/<section class="discord-section"[\s\S]*?<\/section>/g, '');
    });

    // Format reading time
    eleventyConfig.addFilter("readingTime", minutes => {
        if (minutes < 1) return "< 1 min read";
        return `~${minutes} min read`;
    });

    // Scripture URL construction (build-time filter for citation panel)
    // Wraps existing generateScriptureUrl helper, normalizing en-dashes
    eleventyConfig.addFilter("scriptureUrl", function(ref) {
        return generateScriptureUrl(ref.replace(/\u2013/g, '-'));
    });
    
    // =========================================
    // SHORTCODES
    // Reusable content snippets
    // =========================================
    
    // Sentence span for audio sync
    // Usage: {% sentence 0 %}Content here{% endsentence %}
    eleventyConfig.addPairedShortcode("sentence", function(content, index) {
        return `<span class="sentence" data-index="${index}">${content.trim()}</span>`;
    });

    // Paragraph wrapper for audio sync highlighting
    // Usage: {% para 0 %}...paragraph content...{% endpara %}
    // Wraps content in a <p> with data-paragraph attribute.
    // Heading paragraphs use {% parahead 0 %} which wraps in a <span> instead.
    eleventyConfig.addPairedShortcode("para", function(content, index) {
        return `<p class="sync-para" data-paragraph="${index}">${content.trim()}</p>`;
    });
    eleventyConfig.addPairedShortcode("paraspan", function(content, index) {
        return `<span class="sync-para" data-paragraph="${index}">${content.trim()}</span>`;
    });
    
    // Pause-point for Reflect · Journal · Witness system
    // Usage: {% pausePoint "pause-closing", "reflect" %}
    eleventyConfig.addShortcode("pausePoint", function(id, defaultTab) {
        const tab = defaultTab || "reflect";
        return `<div class="pause-point" id="${id}">
  <span class="pause-cue">Pause here &#10230; Use these tabs to reflect on what you have just read &#10230;</span>
  <div class="tab-cluster">
    <div class="tab-pill reflect" onclick="RJW.openModal('${id}','reflect')">Reflect</div>
    <div class="tab-pill journal" onclick="RJW.openModal('${id}','journal')">Journal</div>
    <div class="tab-pill witness" onclick="RJW.openModal('${id}','witness')">Witness</div>
  </div>
</div>
<div class="section-gap"></div>`;
    });

    // Scripture link (build-time)
    // Usage: {% scripture "Alma 42:8" %}
    eleventyConfig.addShortcode("scripture", function(reference) {
        const url = generateScriptureUrl(reference);
        return `<a href="${url}" class="scripture-link" target="_blank" rel="noopener">${reference}</a>`;
    });

    // Citation dagger mark (build-time)
    // Usage: {% cite "ce-matt1129" %}
    eleventyConfig.addShortcode("cite", function(entryId, tip) {
        const tooltip = tip || "Open citations panel.";
        return `<span class="cite-mark" data-tip="${tooltip}" data-entry="${entryId}" tabindex="0" role="button" aria-label="Open citations panel"></span>`;
    });
    
    // =========================================
    // BLOCK SYNC TRANSFORM (clean-paragraph chapters)
    // -----------------------------------------------------------------
    // Assigns a sequential data-paragraph="N" hook to each NARRATED block
    // in a chapter's prose container so audio-sync.js can highlight and
    // (when real timestamps land) click-to-seek at BLOCK granularity —
    // without re-introducing per-sentence {% sentence %} / {% para %}
    // shortcodes into the clean markdown body.
    //
    // INDEXING CONVENTION (must match the audio/timestamp pipeline — see
    // NARRATION.md; timestamp JSON uses Format-C "p{N}" keys):
    //   • Scope:   only <h2>, <h3>, <p>, and <li> inside
    //              <article class="chapter-content">. Everything outside the
    //              article (RJW modal, citation panel, study/learning tools,
    //              discord, nav) is never touched.
    //   • Indexed: EVERY narrated block — <h2>, <h3>, <p>, and <li> — in
    //              document order, 0-based. This means section headings, the
    //              bold group-label paragraphs (<p><strong>…</strong></p>),
    //              prose paragraphs (including the two inside the
    //              statement-callout <div>), and list items are ALL indexed.
    //   • Skipped: the <style> block and any non-block UI markup
    //              (pause-point, tab pills, section gaps) — none of which use
    //              the four indexed tags.
    //   • Each indexed element also gets class="sync-para" so it reuses the
    //     existing .sync-para.highlighted styling in chapter.css. Putting
    //     data-paragraph DIRECTLY on the <h2>/<h3> (not a span inside it) is
    //     highlighted correctly by audio-sync.js — its SPAN-only heading guard
    //     does not apply to bare heading elements.
    //
    // SAFETY: applies ONLY to "clean" chapters whose prose contains neither
    // {% sentence %} spans (class="sentence") nor pre-existing data-paragraph
    // markup from the {% para %} shortcode. Chapters 2–10 use one or both and
    // are therefore left BYTE-FOR-BYTE unchanged.
    // =========================================
    eleventyConfig.addTransform("paragraphSync", function(content) {
        const outputPath = (this.page && this.page.outputPath) || this.outputPath || '';
        if (!outputPath || !outputPath.endsWith('.html')) return content;

        const ARTICLE_RE = /(<article class="chapter-content"[^>]*>)([\s\S]*?)(<\/article>)/;
        const m = content.match(ARTICLE_RE);
        if (!m) return content;

        const openTag  = m[1];
        const inner    = m[2];
        const closeTag = m[3];

        // Leave self-indexed chapters untouched:
        //   class="sentence"   → Chs 2–6, 7–10 ({% sentence %} highlighting)
        //   data-paragraph     → Chs 7–10 ({% para %} shortcode highlighting)
        if (inner.includes('class="sentence"') || inner.includes('data-paragraph')) {
            return content;
        }

        // Mask <script> and <style> blocks before indexing. Pages can embed
        // dumped JSON inside the article scope (/articles/ ships WOP_HOLD,
        // WOP_GODEEPER, and apparatusData that way), and howWeHold.js builds its
        // disclosures from literal '<p>…</p>' strings. Rewriting those <p> tags
        // injects raw double-quotes into JSON string values, which terminates the
        // string early and throws SyntaxError at parse time — so the payload never
        // defines. Masking also keeps script/style content out of the counter, so
        // real narrated blocks index exactly as before.
        const masked = [];
        const maskedInner = inner.replace(
            /<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi,
            function(block) {
                masked.push(block);
                return ` WOP_MASK_${masked.length - 1} `;
            }
        );

        let counter = 0;
        const indexed = maskedInner.replace(/<(h2|h3|p|li)\b([^>]*)>/g, function(full, tag, attrs) {
            const idx = counter++;
            let a = attrs || '';
            if (/\bclass\s*=\s*["']/.test(a)) {
                a = a.replace(/\bclass\s*=\s*["']/, function(cm) { return cm + 'sync-para '; });
            } else {
                a = ' class="sync-para"' + a;
            }
            return `<${tag}${a} data-paragraph="${idx}">`;
        });

        if (counter === 0) return content;

        // Restore the masked blocks byte-for-byte. split/join rather than
        // replace() so `$`-sequences inside the payloads are never interpreted.
        let restored = indexed;
        for (let i = 0; i < masked.length; i++) {
            restored = restored.split(` WOP_MASK_${i} `).join(masked[i]);
        }

        return content.replace(ARTICLE_RE, function() {
            return openTag + restored + closeTag;
        });
    });

    // =========================================
    // HELPER FUNCTIONS
    // =========================================
    
    /**
     * Generate churchofjesuschrist.org scripture URL from reference
     * @param {string} reference - e.g., "Alma 42:8", "2 Nephi 31:3", "John 3:16"
     * @returns {string} Full URL to scripture
     */
    function generateScriptureUrl(reference) {
        const baseUrl = "https://www.churchofjesuschrist.org/study/scriptures";
        
        const bookMappings = scriptureData.books;
        
        // Parse reference: "Alma 42:8" or "2 Nephi 31:3-5"
        const match = reference.match(/^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/i);
        
        if (!match) {
            console.warn(`Could not parse scripture reference: ${reference}`);
            return `${baseUrl}`;
        }
        
        const [, book, chapter, verseStart, verseEnd] = match;
        const bookKey = book.toLowerCase().trim();
        const bookPath = bookMappings[bookKey];
        
        if (!bookPath) {
            console.warn(`Unknown book: ${book}`);
            return `${baseUrl}`;
        }
        
        // Build URL with verse anchor
        let url = `${baseUrl}/${bookPath}/${chapter}`;
        if (verseEnd) {
            url += `?lang=eng&id=p${verseStart}-p${verseEnd}#p${verseStart}-p${verseEnd}`;
        } else {
            url += `?lang=eng&id=p${verseStart}#p${verseStart}`;
        }
        
        return url;
    }
    
    // =========================================
    // CONFIGURATION
    // =========================================
    
    // Ignore template/internal files and retired chapters (underscore-prefixed)
    eleventyConfig.ignores.add("src/chapters/_*");

    return {
        dir: {
            input: "src",
            output: "_site",
            includes: "_includes",
            data: "_data"
        },
        templateFormats: ["njk", "md", "html"],
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk"
    };
};
