The author-and-SCRIBE record of every correction to reader-facing text on the site, newest first.
Not shown to readers and not published: Eleventy's input is src/, so docs/ reaches no build output (AOID2-READER-NO-CHANGELOG, AOID2-CHANGELOG-REPO).

## 1 November 2026 - Article 9, First Edition and Second Edition (COMMIT-PENDING, CODE-AOID2-81)
- What changed (src/_data/apparatusData.json, A09, unless noted):
  - s4, `panel_comment_first_edition` (First Edition): clause "; and D&C 35:17-18 names the continuity of His mission and message in the latter-day commission - 'these signs shall follow them that believe' - the same signs, the same gospel, the same Christ" removed; "and" added after the semicolon before "D&C 6:21". The sentence now ends "... what He still is in the present age."
  - s7, anchor "Alma 32:27-28", `comment` (Second Edition only): "let that desire work in you" -> "let this desire work in you". `comment_first_edition` untouched.
  - Anchor verse text, both editions (words only, same start and end points):
    - s2, 3 Nephi 11:11: "and I have glorified the Father" -> "and have glorified the Father"
    - s4, Galatians 1:8-9: "than that which ye have received" -> "than that ye have received"
    - s4, John 8:25: "And Jesus said unto them" -> "And Jesus saith unto them"
    - s11 and s12, Mosiah 3:19: "putteth off the natural man, and becometh" -> "putteth off the natural man and becometh"
    - s20, 2 Corinthians 3:17-18: "changed into the same image, from glory to glory" -> "changed into the same image from glory to glory"
    - s22, D&C 50:44: opening "For I am the good shepherd" -> "Wherefore, I am in your midst, and I am the good shepherd"
    - s22, 3 Nephi 27:33: "the way that leadeth unto life" -> "the way that leads to life"; "the way which leadeth to death" -> "the way which leads to death"; ending "until the time is past, that they may no more enter in, because of the iniquity of which they aboundeth." -> "until the night cometh, wherein no man can work."
  - src/_includes/aoid/a09.njk: the dated correction note added at the foot of Article 9 by CODE-AOID2-80 (commit cdf1219) removed, so it shows on no page (/articles/, /articles/video-09/, /chat/video-09/). The template is as before cdf1219 in that spot.
- Why: AOID2-STEP203-A09-VERSETEXT (verse text under an anchor is covered by codex A5(b)); AOID2-A09-FE-MISQUOTES (s4 comment still quoted the anchor removed in cdf1219); Aaron's acceptance of the Alma 32:27 wording at step 203 (review point 2, item 3); AOID2-READER-NO-CHANGELOG and AOID2-CHANGELOG-REPO (no change dates or change logs shown to readers; this log is the record). Codex A5(b), v0.26. Verse wording read from churchofjesuschrist.org by two instruments (fetch-and-extract; rendered browser).
- Approved wording: C:\Users\aaron\Documents\wop-scratch\WoP_AOID2_Step203_Review_CODE-AOID2-80_v1_20261101.md (points 1, 2.3, 4 and 6R-a)

## 1 November 2026 - Article 9, First Edition (cdf1219, CODE-AOID2-80)
- What changed (src/_data/apparatusData.json, A09, unless noted):
  - s13, `panel_comment_first_edition` (First Edition): scripture quoted for D&C 50:31-32 now reads as published.
  - s14, `panel_comment_first_edition` (First Edition): scripture quoted for D&C 33:16 now reads as published.
  - s14, anchor "D&C 33:16", `text` (both editions): "And the scriptures shall be given, even as they are in mine own bosom, ..." -> "And the Book of Mormon and the holy scriptures are given of me for your instruction; and the power of my Spirit quickeneth all things." `comment_first_edition` rewritten to match; the Second Edition comment untouched.
  - s18, `panel_comment_first_edition` (First Edition): the words at Mosiah 27:25-26 credited to Alma's report of the Lord's words; the quoted scripture corrected (two clauses).
  - s18, anchor "2 Nephi 32:5", `comment_first_edition` (First Edition): rewritten with the verse's condition restored (the Holy Ghost's guidance is promised to those who enter in by the way).
  - s4, restoration anchor "D&C 35:17-18" (First Edition only): removed, because its text was not found in that verse (the words are D&C 84:65).
  - src/_includes/aoid/a09.njk: a dated correction note was placed at the foot of Article 9 (switch OFF only; it also showed on /articles/video-09/ and /chat/video-09/). It was removed by CODE-AOID2-81.
  - Second Edition (same commit): the s7 John 17:3 and Alma 32:27-28 notes and three crossref titles (s7 to s8, s9 to s6) built from the 19 Oct approved wording, old titles kept as `title_first_edition`; 15 verse-range hyphens changed to en dashes in non-floor Second Edition prose.
- Why: AOID2-A09-FE-MISQUOTES (codex A5(b), live First Edition misquotations corrected, quotation only); AOID2-STEP144-SCOPE, AOID2-STEP144-FREEZE (the 28 Oct freeze, AOID2-FILM-TIMING, does not bar scripture errata), AOID2-STEP144-DISCLOSURE-PLACE (the dated note, since superseded by AOID2-READER-NO-CHANGELOG); AOID2-A09-S14-DC, AOID2-A09-S4-DC35.
- Approved wording: C:\Users\aaron\Documents\wop-scratch\WoP_AOID2_Step144_A09_Corrections_Draft_v1_20261101.md (report: C:\Users\aaron\Documents\wop-scratch\WoP_AOID2_CODE-AOID2-80_A09Step144_Report_20261101.md)
