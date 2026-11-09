The author-and-SCRIBE record of every correction to reader-facing text on the site, newest first.
Not shown to readers and not published: Eleventy's input is src/, so docs/ reaches no build output (AOID2-READER-NO-CHANGELOG, AOID2-CHANGELOG-REPO).

## 9 November 2026 - Broken Vessels, "The Doctrine and the Ministry": article titles and numbers corrected to the approved wording (CODE-AOID2-116, AOID2 step 209)
- What changed (both editions; not gated by the Second Edition switch, because Articles 2-13 carry the same numbers in the First and Second Editions):
  - src/pages/studies/broken-vessels.njk, section "The Doctrine and the Ministry" (id doctrine-and-ministry), paragraph 1: "Article 10, Living by Grace" -> "Article 10, Of Living by Grace". Nothing else in the paragraph changed.
  - Same section, paragraph 2, replaced whole with the approved text: Article 8 is named "Of Fellow Believers" (was "Of Our Fellow Believers"); the sentence on "Article 12, Of the Restoration", an article that does not exist (Article 12 is "Of Immortality and Eternal Life" in both editions), is replaced by a sentence on Article 9, "Of Finding Our Way"; "Of Covenants and Commitments" is numbered Article 11 (was 13).
  - The file was edited in place and keeps its creation time, so the page's datePublished and sitemap lastmod (2026-08-01) are unchanged.
- Why: AOID2 pathway step 209, applying the wording Aaron approved 9 Nov 2026 (CHAT-AOID2-114a, option 1; AOID2 step 208): wop-scratch/WoP_AOID2_Step208_BrokenVessels_ApprovedWording_20261109.md.
- Also in this commit, not reader-facing (AOID2 step 297): Aaron's ruling of 9 Nov 2026 (CHAT-AOID2-114a) that banner WebPs, served "public, max-age=31536000, immutable", never reuse a file name or URL (a replacement takes a new slug suffix such as -v2, banners.json is updated to match, the old R2 objects stay) is written into the header comment of src/_includes/macros/banner.njk and the docstring of tools/wop_r2_upload_banners.py. No build output changes.

## 9 November 2026 - /living-tree/ follow-up: approved wording version 2, the 2.9 ACNA note, inquirer resources under Aaron's signed labels, and the phone-width "Back to the picture" bar (9942d76, CODE-AOID2-113, AOID2 step 287)
- What changed (live at /living-tree/, which production builds with the Second Edition switch OFF; the page stays noindex, out of site search and linked from nowhere in that state, as it was):
  - The page reads version 2 of the approved wording: data-sources/living-tree/WoP_AOID2_LivingTree_ApprovedWording_v2_20261109.md, a byte-identical copy of the wop-scratch file approved by Aaron 9 Nov 2026 (CHAT-AOID2-111b), under the same SHA-256 guard in src/_data/livingTreeText.js. The version 1 copy is retired, so one approved file governs the page.
  - Changed, both editions, from version 2: the first sentence of the key (2.3) now reads "The five rows group the branches by historical setting, theological affinity, cultural relationship, revival influence or restorationist self-understanding, as the panels on the picture show." (AOID2-LT-ROWS-ACCOUNT, option 1); five source lines: Anglican (Church of England, Canon C 15, new address; Anglican Communion Office, What Anglicans Believe), Lutheran (Evangelical Lutheran Church in America, Who We Are), Stone-Campbell (Disciples of Christ Historical Society, A Brief History of the Stone-Campbell Tradition) and Chinese House Churches (the Pew glossary at www.pewresearch.org).
  - Added, both editions: the approved note 2.9, in small italic type directly under the Anglican Church in North America resource on the Anglican branch, with its two sources (AOID2-LT-ACNA, option 2).
  - Changed, both editions: every inquirer resource is shown under the label and address Aaron signed (data-sources/living-tree/WoP_AOID2_LivingTree_ResourceLabels_Signed_20261109.md, a byte-identical copy; gate G4), read by tools/build_living_tree.py --resources-only in place of the CODE-AOID2-88 label fields. Shown: 44 on 20 branches (was 36 on 16), adding the Assyrian Church of the East home page, Mennonite Church USA, both UMJC pages, OAIC and ACNA (cleared under AOID2-LT-RES-UNVERIFIED, option 2, and AOID2-LT-ACNA, option 2) and the two approved replacements (Holy See, Catechism of the Catholic Church; North American Division of Seventh-day Adventists, Beliefs). Every one passed rule (b) on the new two-instrument record data-sources/living-tree/link_checks_20261109_CODE-AOID2-113.json. Withheld (review.json, resources.withheld): the six unsigned CODE-AOID2-88 entries (USCCB x2, Anglican Communion Office About us, World Methodist Council member directory, adventist.org x2). Chinese House Churches: none, by design.
  - Changed, both editions: at 800 px and below, while the deep zoom is open, "Back to the picture" sits in a bar above the viewer instead of over the picture, so it covers no branch spot. Above 800 px nothing changes; the overlay boxes are untouched.
- Why: AOID2 pathway step 287, Aaron's review of the CODE-AOID2-112 report (9 Nov 2026; rulings AOID2-LT-RES-UNVERIFIED option 2, AOID2-LT-ROWS-ACCOUNT option 1, AOID2-LT-TPS-OFFSCORE option 1, AOID2-LT-ACNA option 2).

## 9 November 2026 - /living-tree/ first pass: one page in both editions, with the approved introduction, teaching lines, 25 branch descriptions and inquirer resources (4baa3c2, CODE-AOID2-112, AOID2 step 163)
- What changed (live at /living-tree/, which production builds with the Second Edition switch OFF; the page stays noindex, out of site search and linked from nowhere in that state, as it was):
  - /living-tree/ is one page, src/pages/living-tree.njk, with the switch ON or OFF. src/pages/living-tree-links.njk (CODE-AOID2-110) is retired; its 25 picture spots, deep zoom, branch list, member churches, adopted-text links and help lines are carried over unchanged.
  - Added, in both editions, read at build time by src/_data/livingTreeText.js from data-sources/living-tree/WoP_AOID2_LivingTree_ApprovedWording_20261109.md (byte-identical copy of the wop-scratch file approved by Aaron 9 Nov 2026, CHAT-AOID2-111b; the build stops if its SHA-256 changes): the introduction (Part 1); the practice line, the how-to-read line and the key to the rows (2.1-2.3); on each branch the "Placement:" label (2.4), the description (Part 3, 25 of them), the Source/Sources line (2.7; none on Independent New Religious Movements and Local & Regional Expressions, as approved) and the question line (2.6). Ephesians 2:20 in the Latter-day Saint description is linked by the site's scripture link generator.
  - Added, Second Edition only: on each branch the correction line "Has your church's text been misread or missed? Tell us." (2.5), linked to /aoid/corrections/.
  - Added, both editions: "Learn more from the tradition itself:" (2.8) with 36 inquirer resources on 16 branches, written into src/_data/livingTree.json by tools/build_living_tree.py --resources-only from the CODE-AOID2-88 JSON and the two-instrument check record data-sources/living-tree/link_checks_20261109.json. Twelve were withheld (data-sources/living-tree/review.json, resources.withheld). Chinese House Churches: none, by design.
  - Removed, switch OFF: the CODE-AOID2-110 subtitle "Each branch, with links to the churches’ own published copies of the texts that govern them" (the approved introduction now says what the page holds).
  - Unchanged, switch ON: the A6a title, subtitle, L1-L3, alt text, "What the sixteen cover." note and table, method-account sentence and "View the map at full size" link. L1 stands above the introduction; the note, table, sentence and link follow the picture; L3 stays at the foot of the page. The method account's Living Tree link (METHOD_LINKS.livingTree) was already /living-tree/ and is unchanged.
- Why: AOID2 pathway step 163, "Build /living-tree/ (first pass) and link it from the method account"; wording approved by Aaron 9 Nov 2026 (rulings AOID2-LT-NOVOICE, AOID2-LT-INRM-SCOPE, AOID2-LT-LRE-SCOPE).

## 2 November 2026 - 58 sub-floors replace 18 list floors in the Second Edition panel comments (CODE-AOID2-98, CODE-AOID2-99, AOID2 step 246)
- What changed (Second Edition only; not yet live, because production builds with the Second Edition switch OFF; the First Edition output is byte-identical):
  - src/_data/apparatusData.json: on 35 spans of Articles 4, 6 and 11, the parent floor paragraph is replaced by its sub-floors, one paragraph each; `panel_comment_first_edition` is added where it was absent and holds the old comment.
  - data-sources/aoid/floor_ledger.yaml: 58 sub-floor entries; the 18 parents carry `superseded_by` and keep their text and hash; the scored parents carry a `withheld` note and keep their result line.
  - data-sources/aoid/floors/: a dated addendum in each of the six floor documents, carrying the sub-floor text as approved by Aaron on 2 Nov 2026.
  - data-sources/aoid/floor_counts.json: the 11 scored parents that were split no longer show a count (status WITHHELD); the sub-floors are UNSCORED. Floors showing a count: 30 -> 19.
  - scripts/aoid-verify-floors.js and data-sources/aoid/FLOOR_CHECK.md: `floor_paragraph` may be a map from span to paragraph; `superseded_by` marks a parent as SUPERSEDED, and a named sub-floor missing from the ledger fails the parent.
  - scripts/aoid_tests: six tests updated as ruled in AOID2-STEP246-TESTS (option 1), and eleven tests added for the new floor-check routes. The Step 89 minimum of floors with counts is 19, temporary until the clause audit, step 238.
- Why: AOID2-LIST-FLOORS and AOID2-SUBFLOOR-FIVE (codex v0.31, C4(a)(v) amended and A4(f) widened), approved by Aaron 2 Nov 2026. No floor was scored in this change.

## 2 November 2026 - Article 9 s7 and s8 Second Edition panel comments, one sentence each (ad51eca, CODE-AOID2-93)
- What changed (Second Edition only; not yet live, because production builds with the Second Edition switch OFF):
  - src/_data/apparatusData.json, A09, `panel_comment` (paragraph 2 only; the floor paragraph and every `panel_comment_first_edition` are untouched):
    - s7: "What the span refuses is to make the accuracy of a disciple's doctrine the measure of the disciple." -> "What the span refuses is to let the accuracy of what we say about God take precedence over loving Him and being known of Him."
    - s8: "Christ's own call is the measure:" -> "Christ's own call shows what that following is:" (the Luke 9:23 quotation after the colon is unchanged).
- Why: both sentences echoed the superseded 17 Oct floor theses ("the measure of the disciple"; "by which the disciple's life is measured"), and the s7 sentence came close to answering a question the A9-F2 floor leaves open ("how much right belief God requires of each soul"), which codex A4(g) forbids in commentary. Approved by Aaron, 31 Oct 2026 (source: wop-scratch/WoP_AOID2_Step171_A09_s7_s8_Para2_20261031.md; CODE-AOID2-67 report, open item 1).

## 1 November 2026 - Last verification date and the Corrections form's dated-record promise removed (fef4580, CODE-AOID2-83)
- What changed:
  - Father of Spirits disclosure translation note, /aoid/disclosures/father-of-spirits/ (both editions) and the Second Edition Article 2 tab. Source: data-sources/aoid/disclosures/WoP_AOID2_FatherOfSpirits_Disclosure_Final_20261004.md. Date removed: "4 Oct 2026". "Every quotation above was verified on 4 Oct 2026 by two instruments (WebFetch, and a browser read of the page text)" -> "Every quotation above was verified by two instruments (WebFetch, and a browser read of the page text)".
  - Corrections form text, /aoid/corrections/ (Second Edition only). Source: data-sources/aoid/second-edition/WoP_AOID2_Step88_CorrectionsForm_Spec_Draft_v1_20261019.md, line 13, read by src/_data/aoidCorrections.js. Promise removed: "and recorded with its date and reason". "...any change to a count is decided openly and recorded with its date and reason." -> "...any change to a count is decided openly."
- Why: AOID2-READER-NO-CHANGELOG, AOID2-LIVE-DISCLOSURE-DATES, AOID2-SE-CHANGELOG-PAGE (review of CODE-AOID2-82, items 1a and 1b, approved by Aaron 1 Nov 2026).

## 1 November 2026 - Article 9 quotations, change dates and change-record promises removed (dc84a27, CODE-AOID2-82)
- What changed:
  - src/_data/apparatusData.json, A09 (First Edition only; the Second Edition comments are untouched):
    - s20, `panel_comment_first_edition`, inside the 2 Corinthians 3:17-18 quotation: "are changed into the same image, from glory to glory" -> "are changed into the same image from glory to glory".
    - s22, `panel_comment_first_edition`, inside the 3 Nephi 27:33 quotation: "narrow is the way that leadeth unto life" -> "narrow is the way that leads to life".
  - Change dates removed from /aoid/disclosures/father-of-spirits/ and /aoid/disclosures/sexual-holiness/, in both editions, and from the same text in the Second Edition Disclosure and Record tabs of Article 2 (Father of Spirits) and Article 11 (Sexual Holiness). Source: data-sources/aoid/disclosures/*_Disclosure_Final_*.md, read by src/_data/aoidDisclosures.js. Each line below gives the file line, the date text removed, and the sentence it stood in. Dates that belong to the content (church documents and statements) and the verification date in the Father of Spirits translation note were kept.
    - Father of Spirits, source line 134: removed "AOID2-FOS-EO-MOGILA-CURRENCY, 11 Oct 2026)" in: "...by its synod or an official teaching statement, on God as the source of the human spirit; AOID2-FOS-EO-MOGILA-CURRENCY, 11 Oct 2026); Anabaptist (Q-A2-F1-AN: the ..."
    - Father of Spirits, source line 136: removed "rulings of 2 and 3 Oct 2026 (" in: "...d (CODE-AOID2-08, section 5.1, the final table), all in wop-scratch. The rows reflect the rulings of 2 and 3 Oct 2026 (AOID2-FLOOR-SUBSTANCE as amend..."
    - Father of Spirits, source line 143: removed "AOID2-SOUL-SPIRIT-REFERENT, 11 Oct 2026)" in: "..., the text is read in that meaning and is not counted on the strength of the shared word (AOID2-SOUL-SPIRIT-REFERENT, 11 Oct 2026)...."
    - Father of Spirits, source line 147: removed "AOID2-SOUL-SPIRIT-REFERENT, 11 Oct 2026)" in: "... the spirit their publications say returns to God is the life-force, not a personal self (AOID2-SOUL-SPIRIT-REFERENT, 11 Oct 2026)...."
    - Father of Spirits, source line 163: removed "AOID2-HOLINESS-FAMILY, 1 Oct 2026)" in: "...  - **Holiness is measured as a family of its own (AOID2-HOLINESS-FAMILY, 1 Oct 2026).** The Holiness churches desc..."
    - Father of Spirits, source line 165: removed "AOID2-DENOMINATOR-EAST, 1 Oct 2026)" in: "...e fifth century, are not represented by them; they are measured as families of their own (AOID2-DENOMINATOR-EAST, 1 Oct 2026)...."
    - Father of Spirits, source line 167: removed "Ruled 1 Oct 2026:" in: "...  Ruled 1 Oct 2026: the Oriental Orthodox churche..."
    - Sexual Holiness, source line 151: removed "AOID2-29A-BAPTIST-ALLIANCE, 1 Oct 2026)" in: "...ments in its own name, as the UCC's General Synod and the Southern Baptist Convention do (AOID2-29A-BAPTIST-ALLIANCE, 1 Oct 2026). The family is divided; the S..."
    - Sexual Holiness, source line 152: removed "AOID2-29B-BAPTIST-ALLIANCE, 1 Oct 2026)" in: "...regational life, read as a church-side act on the precedent of the UCC's 2005 resolution (AOID2-29B-BAPTIST-ALLIANCE, 1 Oct 2026)...."
    - Sexual Holiness, source line 153: removed "Accepted by Aaron, 1 Oct 2026." in: "...text rests on a single publisher (B4). Several smaller Holiness bodies could not be read. Accepted by Aaron, 1 Oct 2026...."
    - Sexual Holiness, source line 154: removed "Accepted by Aaron, 1 Oct 2026." in: "...amed, because their texts were read only as others reported them or could not be reached. Accepted by Aaron, 1 Oct 2026...."
    - Sexual Holiness, source line 155: removed "AOID2-MCEC-29B, 8 Oct 2026)" in: "...- **Anabaptist, 29b (AOID2-MCEC-29B, 8 Oct 2026):** a 2019 statement by the Le..."
    - Sexual Holiness, source line 156: removed "AOID2-SH-ANABAPTIST-29B-FORBEARANCE, 11 Oct 2026)" in: "...- **Anabaptist, 29b (AOID2-SH-ANABAPTIST-29B-FORBEARANCE, 11 Oct 2026):** Mennonite Church Canada (2..."
    - Sexual Holiness, source line 159: removed ", corrected 1 Oct 2026)" in: "...ote 10), WoP_AOID2_29ab_EastFamilies_Report_20261001.md (CODE-AOID2-03, families 14 and 15, corrected 1 Oct 2026), WoP_AOID2_29ab_Verification_..."
    - Sexual Holiness, source line 182: removed "AOID2-MCC-PLACEMENT, 8 Oct 2026)" in: "...  - **The Metropolitan Community Churches are not counted with any family (AOID2-MCC-PLACEMENT, 8 Oct 2026).** They govern themselves thr..."
    - Sexual Holiness, source line 183: removed "AOID2-HOLINESS-FAMILY, 1 Oct 2026)" in: "...  - **Holiness is measured as a family of its own (AOID2-HOLINESS-FAMILY, 1 Oct 2026).** The Holiness churches desc..."
    - Sexual Holiness, source line 185: removed "AOID2-DENOMINATOR-EAST, 1 Oct 2026)" in: "...the fifth century, are not represented by it; they are measured as families of their own (AOID2-DENOMINATOR-EAST, 1 Oct 2026)...."
    - Sexual Holiness, source line 187: removed "Ruled 1 Oct 2026:" in: "...  Ruled 1 Oct 2026: the Oriental Orthodox churche..."
    - Sexual Holiness, source line 159 (the "Sources for the table" paragraph): removed "of 22 Sep to 1 Oct" from "The 29a rows reflect the final rulings of 22 Sep to 1 Oct (AOID2-29A-METHODIST, ...)", and "of 1 Oct" twice, from "the 29b ruling of 1 Oct (AOID2-29B-BAPTIST-ALLIANCE) and the family ruling of 1 Oct (AOID2-HOLINESS-FAMILY)" (found by check d, no year given).
  - Second Edition "What Changed in the Second Edition" page (/aoid/second-edition/, switch ON only). Source: data-sources/aoid/second-edition/WoP_AOID2_Step89_ChangeLog_Draft_v1_20261019.md, with the films line in src/_data/aoidStep89.js:
    - Section "Later corrections" removed, heading and its paragraph: "None yet. Any change to a count, or any correction made after publication, will be recorded here with its date and its reason."
    - ", each with a dated note" removed from the Article 9 line (source line only; the built line comes from amendment B1 and never carried it), and from the step 124 line (held, not rendered) in both places it is written: the [PENDING, step 124] line and the held line inside amendment B1.
    - Films line: "The films for Articles 2 and 6, made on 7 October 2026, read ..." -> "The films for Articles 2 and 6 read ..." (date removed: 7 October 2026). "(2026)" in the opening kept.
  - Method account, "If we have it wrong" (the Disclosure tab of every Article, switch ON; source WoP_AOID2_Step89_MethodAccount_Draft_v1_20261019.md): "Every correction is read, and any change to a count is decided openly and recorded with its date and reason." -> "Every correction is read, and any change to a count is decided openly." (promise of a dated record removed; no date).
  - Record tab, "Date measured" column removed, header and cells (src/_data/aoidCounts.js; switch ON, Articles 2, 4, 6 and 11). Date in each row before removal (row id: teaching: date):
    - A2-F1: The Father of our spirits: 3 October 2026, revised 11 October 2026
    - A2-F2: God is good, His purposes are good, and His love for His children has no limit: 3 October 2026
    - A2-F3: Providence: He sustains, He knows, He cares: 3 October 2026
    - A2-F4: God in the Highest: 3 October 2026
    - A2-F5: What no mortal knows, and what He reveals: 3 October 2026
    - A4-F1: Prophets, men and women, whose word was of God: 3 October 2026
    - A4-F2: Worship belongs to God alone: 3 October 2026
    - A4-F3: God spoke, speaks, and will yet speak: 3 October 2026
    - A4-F4: Broken vessels: 4 October 2026
    - A4-F5: Study, the Spirit, and the Scriptures as the measure: 3 October 2026
    - A4-F7: Received, and leading to Christ: 3 October 2026
    - A4-F6: Preserved, plainly: 4 October 2026
    - A6-F1: Entrance to the Kingdom through Christ alone: 5 October 2026
    - A6-F2: What we are saved from and for, known in part: 5 October 2026
    - A6-F3: Grace and the Atonement of the Son of God as the ground: 5 October 2026
    - A6-F4: The arc: created in His image, conformed to His, glorified with Him: 5 October 2026
    - A6-F5: Known in part, and never reduced: 5 October 2026
    - A6-F6: The gospel's parts: faith, repentance, new birth, the Spirit's fruit and sealing: 5 October 2026
    - A6-F7: Works as fruit, not price: 5 October 2026
    - A6-F8: Judgment belongs to Christ: 5 October 2026
    - A6-F9: The charge, the Spirit and the Word, and the disciple's labor: 5 October 2026
    - A11-F1: Children of God by birth: 5 October 2026
    - A11-F2: Disciples by covenant: 5 October 2026, revised 25 October 2026
    - A11-F3: Love proven by obedience, and not salvation's price: 5 October 2026
    - A11-F4: The cost, the cross, the return: 5 October 2026
    - A11-F5: Christ's baptism and the ordinances, and the welcome of God: (no date; the cell showed an em dash)
    - G8: Completing Acts 2:38: 5 October 2026
    - A11-F7: Born of water and of the Spirit: 5 October 2026
    - A11-F8: The way, prayer, endurance, the Kingdom at hand: 5 October 2026
    - 29a: Sexual relations belong within marriage: 1 October 2026
    - 29b: Marriage is between a man and a woman: 1 October 2026
- Why: AOID2-READER-NO-CHANGELOG and AOID2-CHANGELOG-REPO (readers are shown no date of a change and no change log; this log is the record); AOID2-LIVE-DISCLOSURE-DATES (1 Nov 2026, a freeze on a live edition never bars removing change dates); AOID2-SE-CHANGELOG-PAGE (the Second Edition "What Changed" page stays as a topic-only edition explainer); AOID2-A09-FE-MISQUOTES and codex A5(b) for the two quotations. Codex v0.27.
- Approved wording: C:\Users\aaron\Documents\wop-scratch\WoP_AOID2_Step206_Review_CODE-AOID2-81_v1_20261101.md (points 1, 2, 3 and 5)

## 1 November 2026 - Article 9, First Edition and Second Edition (da1bb8b, CODE-AOID2-81)
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
