# Lantern Post source gate

A Lantern Post draft may link to, and draw from, only published pages, meaning exactly the pages in the sitemap of the production-equivalent build, minus Coming Soon stubs and URLs that `vercel.json` redirects.

Needs Node 20+ and `npm ci`. No new dependencies. Run from the repo root.

```
node tools/lantern/sources.mjs build       # production-equivalent build into .lantern/site (leaves _site alone)
node tools/lantern/sources.mjs manifest    # writes .lantern/manifest.json (gitignored)
node tools/lantern/sources.mjs check draft.txt   # or: cat draft.txt | node tools/lantern/sources.mjs check
node --test tools/lantern/test/sources.test.mjs
```

- **build** sets `VERCEL_ENV=production`, leaves the AOID2 Second Edition switch unset (as Vercel does), runs the read-only `sjn-verify-data.js` check, then `eleventy --output=.lantern/site`. It skips the Python lyrics prebuild (which rewrites a tracked file) and Pagefind (search index only).
- **manifest** reads the built `sitemap.xml`. For each URL it records title, Focused-mode category, main-content text, word count and source input path. Stubs and redirects go to `excluded` with a reason. Media (music, narrations, podcasts, videos) are listed only where they appear in a published page's main content.
- **check** exits 1 and lists any link to wordsofplainness.org (www or apex) or any site-relative link that is not a manifest page. Other hosts are ignored.

Categories live in one table, `CATEGORY_RULES` in `sources.mjs`; anything unmatched is "Other pages".

Windows note: clone with `core.autocrlf=false` (Linux and cloud sessions do this by default). With CRLF checkouts the production `sjn-verify-data.js` hash check fails, and `build` stops, exactly as production would.
