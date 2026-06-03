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
