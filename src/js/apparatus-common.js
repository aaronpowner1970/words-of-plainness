/* ============================================================
   apparatus-common.js — the parts of the citation apparatus that
   BOTH panels render, defined exactly once.

   /articles/ (articles-panel.js) and /articles/video-NN/
   (aoid-video.js) show the same apparatus entries in two different
   containers. Everything about how an entry READS therefore belongs
   here, so the two panels cannot drift apart:

     scriptureUrl(ref, books)  a churchofjesuschrist.org/study link
                               built from the site's own book map
                               (src/_data/scriptures.json)
     definitionHtml(text)      a definition field with <em> and
                               <strong> honoured as markup

   No DOM, no state, no page assumptions: each caller supplies its own
   book map, which both take from scriptures.json at build time.
   ============================================================ */
(function (w) {
    'use strict';

    var BASE = 'https://www.churchofjesuschrist.org/study/scriptures/';

    function esc(s) {
        return (s || '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* Scripture links follow the existing churchofjesuschrist.org/study
       convention, built from the same book map .eleventy.js uses. A reference
       the map cannot parse returns null, and the caller renders plain text
       rather than a broken link.

       "Book C:V", "Book C:V–V", and a bare "Book C". Anything trailing (a verse
       list like "Mormon 8:12, 17", or a gloss) is ignored and the link lands on
       the first verse named, which is where a reader wants to arrive. */
    function scriptureUrl(ref, books) {
        var map = books || {};
        var s = (ref || '').trim();
        var m = /^(.+?)\s+(\d+):(\d+)(?:\s*[–—-]\s*(\d+))?/.exec(s);
        var chapterOnly = false;
        if (!m) {
            m = /^(.+?)\s+(\d+)\s*$/.exec(s);
            chapterOnly = true;
        }
        if (!m) { return null; }
        var path = map[m[1].toLowerCase().trim()];
        if (!path) { return null; }
        var url = BASE + path + '/' + m[2];
        if (chapterOnly) { return url + '?lang=eng'; }
        if (m[4]) { return url + '?lang=eng&id=p' + m[3] + '-p' + m[4] + '#p' + m[3] + '-p' + m[4]; }
        return url + '?lang=eng&id=p' + m[3] + '#p' + m[3];
    }

    /* Definition fields carry <em> for transliterated Greek and Hebrew (the
       Merognosticism entry's "ek merous"), and both panels used to print the
       tags as literal text. Exactly two tags are honoured, with no attributes:
       the text is escaped FIRST, so nothing but those four tokens can come
       back, and the YAML is never edited.

       Unbalanced markup falls back to the fully escaped text. The browser would
       repair it inside the target element anyway, but a definition that renders
       half-italic is a data error worth seeing as data. */
    var ALLOWED = /&lt;(\/?)(em|strong)&gt;/g;

    function balanced(s) {
        var names = ['em', 'strong'], i, open, close, re;
        for (i = 0; i < names.length; i++) {
            re = new RegExp('&lt;' + names[i] + '&gt;', 'g');
            open = (s.match(re) || []).length;
            re = new RegExp('&lt;/' + names[i] + '&gt;', 'g');
            close = (s.match(re) || []).length;
            if (open !== close) { return false; }
        }
        return true;
    }

    function definitionHtml(text) {
        var out = esc(text);
        if (!balanced(out)) { return out; }
        return out.replace(ALLOWED, '<$1$2>');
    }

    w.WOP_APPARATUS = {
        BASE: BASE,
        esc: esc,
        scriptureUrl: scriptureUrl,
        definitionHtml: definitionHtml
    };
}(window));
