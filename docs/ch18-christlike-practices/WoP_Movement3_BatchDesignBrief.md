# Words of Plainness — Movement 3 Batch Design Brief

**Phase 0 deliverable · Cowork session, Aug 7 2026**
Governs the remaining Volume 1 card-chapters: Ch 17–29 (13 chapters) plus the Ch 14 amendment.
All subsequent drafts inherit this brief. Source of authority: `handoff-mvt3-batch-design.txt` (Aug 7, thrice revised) and Aaron's same-day rulings. Standards in force: 5-Phase Card-Chapter Development Standard, Authoring Guide (Feb 2026) + Addendum 1 (Apr 2026). All drafted prose is push-off material under the SCRIBE role; Aaron writes the canonical text.

---

## 1. Naming ruling applied — slugs, filenames, chapterIds

Per the standing naming ruling (Aug 7): every chapter in this batch is unwritten, therefore **every slug is unnumbered from birth**. Filenames keep numbers so the directory sorts in reading order. `chapterId` = `chapter-` + slug (localStorage key; lives in the `.njk` frontmatter, never in `chapter-status.yaml`).

| Ch | Title | Slug (permalink `/chapters/<slug>/`) | Filename | chapterId |
|----|-------|--------------------------------------|----------|-----------|
| 17 | Searching the Scriptures | `searching-the-scriptures` | `17-searching-the-scriptures.njk` | `chapter-searching-the-scriptures` |
| 18 | Christlike Virtues | `christlike-virtues` | `18-christlike-virtues.njk` | `chapter-christlike-virtues` |
| 19 | Loving Our Neighbors | `loving-our-neighbors` | `19-loving-our-neighbors.njk` | `chapter-loving-our-neighbors` |
| 20 | Building Godly Marriages | `building-godly-marriages` | `20-building-godly-marriages.njk` | `chapter-building-godly-marriages` |
| 21 | Raising Children in Righteousness | `raising-children-in-righteousness` | `21-raising-children-in-righteousness.njk` | `chapter-raising-children-in-righteousness` |
| 22 | Developing Our Talents | `developing-our-talents` | `22-developing-our-talents.njk` | `chapter-developing-our-talents` |
| 23 | Financial Stewardship | `financial-stewardship` | `23-financial-stewardship.njk` | `chapter-financial-stewardship` |
| 24 | Tending the Garden | `tending-the-garden` | `24-tending-the-garden.njk` | `chapter-tending-the-garden` |
| 25 | Witnessing of Christ | `witnessing-of-christ` | `25-witnessing-of-christ.njk` | `chapter-witnessing-of-christ` |
| 26 | Faithful Service | `faithful-service` | `26-faithful-service.njk` | `chapter-faithful-service` |
| 27 | Bearing Trials in Faith | `bearing-trials-in-faith` | `27-bearing-trials-in-faith.njk` | `chapter-bearing-trials-in-faith` |
| 28 | Laying Up Treasures in Heaven | `laying-up-treasures-in-heaven` | `28-laying-up-treasures-in-heaven.njk` | `chapter-laying-up-treasures-in-heaven` |
| 29 | Enduring to the End | `enduring-to-the-end` | `29-enduring-to-the-end.njk` | `chapter-enduring-to-the-end` |

Ch 14 is published: it keeps its numbered slug, chapterId, and asset scheme. The fasting card is **appended as card 5** — never inserted — so the localStorage keys for cards 1–4 are untouched.

**Asset timing corollary (in force):** no asset filename receives a chapter number until Volume 1 numbering is final. All Learning Tools assets are deferred to the back end of the batch (~13 tab-audio runs at ≈$1.50 each). `27_1_The_Chapel_of_My_Heart` and `27_2_We_Who_Love_God` do not reach R2 until numbering is settled.

---

## 2. Drafting order and the calibration delta

1. **Ch 18 — Christlike Virtues** (this session's draft; the voice-calibration chapter). Aaron edits it to completion; a calibration delta is extracted from the diff and governs every remaining draft.
2. **Ch 25, Ch 26** (largely grade A witnesses).
3. **Ch 17** (novel content — benefits most from the delta).
4. **Witness Harvest** (Section 6; Ch 20/21 prompts first).
5. Relational: **19 → 20 → 21**.
6. Stewardship: **22 → 23 → 24**.
7. Endurance: **27 → 28 → 29**.

Drafts deploy under `status: draft` in `chapter-status.yaml` (builds at real URL, renders nowhere on volume pages, noindex, excluded from counts). No public Rough Draft badge.

---

## 3. Overlap map (ratified) + collision routings found in source reads

One teaching home per recurring theme; all other chapters reference without re-teaching.

| Theme | Home | Boundary |
|-------|------|----------|
| Service to the person in front of you | Ch 19 | Ch 26 owns the organized channel |
| Organized/congregational/community service | Ch 26 | experience only; institutional structure lives in Vol 2 / prose |
| Generosity — what you do with means | Ch 23 | — |
| Generosity — what you love | Ch 28 | — |
| Generosity — who you love | Ch 19 | — |
| Consecration | Named once in Ch 22 (opens Stewardship group) | Ch 23–24 inherit silently |
| Endurance — what happens to you | Ch 27 | — |
| Endurance — what you keep doing | Ch 29 | 2 Nephi 31:20 belongs to Ch 29 if used anywhere |
| Gratitude, humility, honor | Ch 18 only | — |
| Forgiveness of others | Ch 19 | Ch 15 owns confession/repentance; Ch 18 teaches mercy as character and points to Ch 19 for practice |
| Grace thesis echoes | Ch 9 → 12 → 13 → 15 → **18** → **29** → 30 | Ch 18: virtues received through beholding, not performed. Ch 29: grace sustaining the long walk, not rewarding it. Designed as a pair. |

**Collision routings discovered in the manuscript reads (binding for drafting):**

- Ms 23's charity/compassion block (1 Corinthians 13, Moroni 7:45–48, "mourn with those that mourn") routes to **Ch 19**, not Ch 26.
- Ms 21's greed/covetousness run (1 Timothy 6:9–10, Colossians 3:5, Jacob 2:18–19, etc.) routes to **Ch 28**; Ch 23 keeps only practice-level contentment.
- Ms 34's forgiveness-of-others block (D&C 64:9–10, Matthew 6:14–15, Kimball) routes to **Ch 19 Card 4**; Ch 18 Card 5 cross-references only.
- Ms 25's seven-bullet "Building" list and Ms 26's parenting list are near-verbatim twins. The **Ch 20 companion appendix** owns the full shared architecture; Ch 21 Card 3 absorbs only teaching/worship/routine elements, with a one-line cross-reference.
- Isaiah 58 is split: the **Ch 14 fasting card** owns the practice of the fast (vv. 6–9); **Ch 23 Card 4** owns the fast-to-feed offering link (vv. 10–11).
- Ms 35's tithes/offerings bullet routes to **Ch 23**; its trials and treasures bullets become closing back-references to Ch 27/28, not content.

---

## 4. Per-chapter card slates

Format per card: **Title** — scope · anchors (Bible-first; Restoration texts marked ✦ are confirming-witness tier only) · witness grade (A seedable / B harvestable / C new memory). Manuscript harvest lines are retained in the drafting files; the strongest are quoted here.

### Ch 17 — Searching the Scriptures (4 cards; largely novel content)

Hero scripture: John 5:39 — "they are they which testify of me." Built out from the scripture-study material gestured at in Ch 16. Ratified provisional shape (verify against no manuscript — there is none):

1. **Coming to the Word** — why we open the book at all; scripture as Christ's own imperative. John 5:39; 2 Timothy 3:16–17. — B
2. **Searching, Not Just Reading** — the Berean practice: method, questions, context. Acts 17:11; Proverbs 2:1–5. — B
3. **Feasting and Pondering** — meditation as distinct from reading. Psalm 1:2; Joshua 1:8; ✦2 Nephi 32:3. — B
4. **Studying to Know Him** — Christ as the interpretive key of all scripture. Luke 24:27, 32 (Emmaus); John 5:39 reprise. — B

Readiness check: light (points to Ch 16's Sabbath-study gesture and Ch 4 Spiritual Knowledge). No appendix. Drafted fourth, after the calibration delta.

### Ch 18 — Christlike Virtues (5 cards; sources Ms 33 + Ms 34) — DRAFTED THIS SESSION

Hero scripture: Micah 6:8. Governing question (INFERENCE, swappable): *"What if Christlike character isn't built by trying harder—but received by looking longer?"* Grace echo lands in Card 1 and resonates in Card 5. Six virtues in five cards: the two manuscript triads (humility/honor/gratitude — the foundational; justice/mercy/grace — the crowning) under a beholding frame, with the crowning triad kept together because Ms 34 teaches them as one practice: the wisdom to choose rightly among them.

1. **Becoming by Beholding** — the frame: character received by looking at Christ, not manufactured by willpower; grace echo. 2 Corinthians 3:18; Matthew 5:48; Proverbs 12:22; ✦Alma 5:14. — A (authorial voice)
2. **The Empty Vessel** (humility) — truth about one's self; worth without pride, faults without despair. Micah 6:8c; Luke 18:9–14; Matthew 23:12; ✦Ether 12:27; ✦2 Timothy 2:21. — A
3. **A Being of Truth** (honor) — integrity in word, promise, and dealing. Psalm 15:1–4; Proverbs 20:7; Matthew 5:37; Exodus 20:15–16; ✦D&C 124:15. — A (optional personal seam noted in draft)
4. **Live in Thanksgiving Daily** (gratitude) — the returning leper; gratitude as presence, not inventory. Luke 17:12–19; Psalm 100:3–4; 1 Thessalonians 5:18; Romans 8:28; ✦Alma 34:38; ✦D&C 78:19. — A
5. **The Crowning Virtues** (justice, mercy & grace) — choosing rightly among the three, as God does. Micah 6:8a–b; Matthew 7:1–2 with John 7:24; Luke 6:36–37; James 2:13; ✦D&C 84:102; ✦2 Nephi 11:5. Forgiveness practice → Ch 19. — A

Readiness check: moderate — Ch 9 (grace as power) and Ch 12 (the Beatitude portrait). Drafting note: once Ch 17 is live, add one adjacency line (beholding Him in His word → beholding Him in character). No appendix. Key harvest: "justice is when we get what we deserve, mercy is when we do not get what we deserve, and grace is when we are given something we do not deserve" (Ms 34 summary — Card 5 spine); "It is impossible for our 'vessels' to be at the same time filled with pride and filled with the Spirit of God" (Ms 33); "one of the worst things we can do is to pretend that we are better than we are, while one of the best things we can ever do is to try to be better than we are" (Ms 33); "Every heartbeat is a special dispensation from heaven" (Ms 33).

### Ch 19 — Loving Our Neighbors (4 cards; source Ms 27)

Governing frame (with Ch 20): John 14:15 + John 13:35.

1. **Who Is My Neighbor?** — the person in front of you; mercy as the mark of discipleship. Luke 10:25–37; Matthew 22:36–40; John 13:34–35. — B
2. **Learn Their Names** — generosity of self: names, circumstances, time. Romans 12:10–13; Hebrews 13:1–2; Proverbs 27:10. — B
3. **Pray, Then Knock** — praying for neighbors by name until the prayer volunteers you. James 2:15–16; 1 John 3:17–18; Matthew 7:12. — C
4. **Seventy Times Seven** — forgiveness of others (teaching home): pray, forgive, serve. Matthew 5:43–44; 18:21–22; 6:14–15; Colossians 3:13; ✦D&C 64:9–10. — C

Receives from Ms 23: the charity block (1 Corinthians 13; ✦Moroni 7:45–48). Defer: ordinance-path framing in Ms 27's opening (Vol 2). No appendix. Readiness check: light (Ch 12, Ch 15 for the forgiveness card's repentance boundary).

### Ch 20 — Building Godly Marriages (5 cards; source Ms 25) — companion appendix RECOMMENDED

Chastity generalized to Christ's Higher Law; Genesis 2:24 carries special emphasis (Christ's own citation, Matthew 19:4–6 / Mark 10:7–8; Paul's twice, 1 Corinthians 6:16 / Ephesians 5:31). Same-sex attraction not treated in Volume 1.

1. **One Flesh** — marriage as God's architecture: leave, cleave, one flesh. Genesis 2:24; Matthew 19:4–6; Ephesians 5:31; 1 Corinthians 6:16. — C
2. **Being the Right Person** — built less by finding than by becoming; Christ first. Matthew 6:33; Proverbs 16:3; 1 Corinthians 13:4–7. — C
3. **Fidelity of the Heart** — the Higher Law: fidelity of eye, thought, and habit. Matthew 5:27–28; Genesis 2:24; Proverbs 5:15–19; Hebrews 13:4. — B
4. **Words That Build** — daily speech and daily forbearance inside the covenant. Ephesians 4:29; Colossians 3:12–13; 1 Corinthians 13:4–5; James 1:19. — C
5. **A Threefold Cord** — Christ as the third strand: shared prayer, worship, courtship kept alive; hope for strained marriages. Ecclesiastes 4:9–12; Isaiah 43:18–19; Ephesians 5:33. — C

Appendix absorbs: the full seven-bullet Building list, roles deep-dive, extended marriage counsel. Defer to Vol 2: polygamy block, temple sealing/celestial framing, presiding-priesthood doctrine, Proclamation-as-document, gendered-roles material. Harvest survivors: Hunter "being the right person" quote; the fidelity clause; "It is utterly false that two people can have irreconcilable differences"; heart-turning as the real breach. Card 4 forbearance stays marital — full forgiveness teaching lives in Ch 19. Readiness check: moderate (Ch 12; Ch 19).

### Ch 21 — Raising Children in Righteousness (4 cards; source Ms 26)

1. **An Heritage of the Lord** — children belong to God; parenting as stewardship of entrusted souls. Psalm 127:3; Mark 10:13–16; 1 Samuel 1:27–28. — C
2. **Provoke Not to Wrath** — nurture over harshness; correction that builds. Ephesians 6:4; Colossians 3:21; 1 John 3:18. — C
3. **As You Walk by the Way** — a weekly family worship rhythm plus daily teaching moments. Deuteronomy 6:6–7; Proverbs 22:6; Joshua 24:15. — B
4. **Lois and Eunice** — parenting never retires: blessing the generation behind you. 2 Timothy 1:5; Psalm 78:4–7; Proverbs 17:6. — C

Generalize: Family Home Evening → "one night each week set apart for family worship." Defer to Vol 2: premortal framing, multiply-and-replenish exaltation track, the family-size counsel block (the "extreme selfishness" sentence must not carry into Vol 1 in any form), Proclamation citation. Card 3 absorbs only teaching/worship/routines from the twin list (see §3). No appendix. Readiness check: light (Ch 14 family prayer; Ch 16).

### Ch 22 — Developing Our Talents (4 cards; source Ms 24 — short source; expect stretch)

**Names consecration once (Card 1) — the whole Stewardship group inherits.**

1. **The Master's Goods** — all we have is entrusted, not owned; consecration named as the whole-life offering. Matthew 25:14–15; 1 Chronicles 29:14; Luke 12:48; 1 Peter 4:10. — B
2. **The Buried Coin** — naming the gift you have hidden through timidity or neglect. Matthew 25:18, 25; 1 Timothy 4:14; 2 Timothy 1:6. — B
3. **Trading Upward** — deliberate improvement as devotion; lifelong learning in God's service. Matthew 25:16–17; Proverbs 22:29; ✦D&C 82:18. — B
4. **No Small Gifts** — the seemingly insignificant skill put to work this week. 1 Peter 4:10; 1 Corinthians 12:4–7, 22; Matthew 25:21. — B

Key harvest: "No talent is a waste of time… if we are willing to exercise a little imagination and creativity" (strongest line in Ms 24). Readiness check: light. No appendix.

### Ch 23 — Financial Stewardship (4 cards; sources Ms 22 + Ms 21)

Inherits consecration silently. Lane: what you do with means.

1. **The Work of Your Hands** (Ms 21) — honest, diligent labor as the ground floor. 1 Thessalonians 4:11–12; Colossians 3:23; Genesis 3:19; 2 Thessalonians 3:10. — B
2. **Enough Is a Skill** (Ms 21) — contentment, living below your means, foresight. 1 Timothy 6:6–8; Proverbs 6:6–8; Philippians 4:11–12. — B
3. **The Lord's Tenth** (Ms 22) — proportionate first-fruits giving; universal tithe framing first, Latter-day Saint specifics in the tab. Malachi 3:8–10; Genesis 14:18–20; 28:20–22; Proverbs 3:9. — B
4. **The Willing Offering** (Ms 22) — voluntary giving beyond the tithe; the fast-to-feed link. 2 Corinthians 9:7; Isaiah 58:10–11; Acts 20:35. — B

Defer to Vol 2: United Order/endowment consecration covenant, worthiness/recommend adjacency (D&C 119:5, Joseph F. Smith), D&C 64:23–25 fear framing. Greed/covetousness run → Ch 28. Fix at drafting: Ms 21 misattributes 1 Thessalonians 4:11–12 as Colossians 3:23. Readiness check: light. No appendix.

### Ch 24 — Tending the Garden (4 cards recommended — 3 + optional; source Ms 20 partial + NOVEL)

Health-code specifics move wholesale to Volume 2. Two-gardens framing in general Christian terms. **The manuscript runs out after the body-as-temple/moderation material; Cards 3–4 are substantially novel writing.**

1. **A Temple of Flesh and Bone** — the body as God's entrusted gift; gratitude-driven care. 1 Corinthians 6:19–20; Romans 12:1; Psalm 139:14. — A/B (science-teacher wonder; verify seed, fallback prompt in §6)
2. **With Judgment, Not to Excess** — moderation under the spirit's governance; no substance list. Philippians 4:5; 1 Corinthians 9:25–27; Galatians 5:22–23. — B
3. **Dress It and Keep It** — the second garden: tending the earth as the Lord's. Genesis 2:15; Psalm 24:1; Genesis 1:28; ✦D&C 59:18–20. — B
4. **Rhythms of Rest** *(optional 4th — RECOMMENDED to include; the chapter is thin at 3 and rest bridges both gardens)* — sleep and renewal as garden-keeping. Psalm 127:2; Mark 6:31; Exodus 23:12. — C

No appendix (withdrawn — ruling). Readiness check: light (Ch 16 rest adjacency).

### Ch 25 — Witnessing of Christ (5 cards; source Ms 18) — grade A chapter

Witness seeds: VR ministry + Articles of Interfaith Discipleship.

1. **Joy Worth Sharing** — witness as overflow of conversion joy. Matthew 28:19; Psalm 66:16; John 4:35–36; ✦1 Nephi 8:11–12. — A
2. **Ready with a Reason** — deliberate preparation to witness. 1 Peter 3:15; Colossians 4:6; 2 Timothy 2:15. — A
3. **The Gentle Witness** — witnessing without contention; never an opponent to defeat. 2 Timothy 2:24–25; Romans 12:16; John 13:35; ✦D&C 121:37. — A
4. **A Life That Testifies** — when words are unwelcome, the witness is the life. Matthew 5:16; 1 Peter 2:12; Titus 2:7. — B
5. **Open Your Mouth** — courage in the unplanned moment. Matthew 10:19–20; 2 Timothy 1:7–8; ✦D&C 33:8. — A

Defer: D&C missionary-call material to confirming tier. Do not re-teach member-vs-disciple (one echo line max). Readiness check: light. No appendix.

### Ch 26 — Faithful Service (5 cards; sources Ms 23 + Ms 28 + Ms 30) — grade A chapter

The organized channel. Experience, never institutional structure.

1. **Anxiously Engaged** (Ms 23) — volunteering into good works before being asked. Galatians 6:9–10; Acts 10:38; Titus 2:14; ✦D&C 58:26–28. — A
2. **A Community of Saints** (Ms 28) — from stranger to fellowcitizen: known, missed, needed. Ephesians 2:19; Romans 12:4–5; Hebrews 10:24–25. — A
3. **The Weight of a Calling** (Ms 28) — saying yes to unpaid work you didn't choose. 1 Peter 4:10–11; Romans 12:6–8; Colossians 3:23. — A
4. **The Ones You're Given** (Ms 28) — ministering as assigned stewardship; loving people you didn't pick. John 21:16–17; Galatians 6:2; 1 Thessalonians 5:11. — A (draft as "ministering" — ms terminology is obsolete)
5. **Seek the Peace of the City** (Ms 30 + 23) — serving your town through organized channels. Jeremiah 29:7; Galatians 6:10; Titus 3:1; ✦Mosiah 2:17. — B

Defer: all hierarchy content (Ms 28) and the political-philosophy apparatus (Ms 30). Charity block → Ch 19. Readiness check: light. No appendix.

### Ch 27 — Bearing Trials in Faith (4 cards; source Ms 31 + the diptych) — companion appendix RECOMMENDED

Built FROM the two song lyrics (standing instruction). Slate verified against Ms 31 this session: **supportable; 3 of 4 cards land squarely on manuscript material; Card 4's communal half is lyric-borne by design** (the manuscript's community is Job's failed comforters — the negative example; "We Who Love God" supplies the positive). Diptych scripture-balance ruling is CLOSED; D&C 122:8 carries the load-bearing line.

1. **When the Faithful Walk in Darkness** — the dark night named, not hurried past; obedience does not exempt; knowing vs feeling. Job 6 with Job 27:3–4; Matthew 7:24–27 (rain fell on the wise man's house too); ✦D&C 121:1–3 (the Liberty Jail cry). — A (lyric 1 carries it)
2. **He Descended Below Them All** — Christ's own unanswered petition; descent as solidarity. Luke 22:42; Hebrews 5:8; Isaiah 53:4 *(add fresh — NOT in Ms 31)*; Romans 8:28; ✦D&C 122:6–8 (load-bearing, ratified); John 16:33. — B (needs one unanswered-prayer memory)
3. **Let the Furnace Do Its Holy Work** — Malachi 3:3; trusting the Hand rather than understanding the fire; the turn to second person. Malachi 3:3; 1 Peter 1:6–7; ✦D&C 121:7–8. — B
4. **Borne Together** — lament spoken aloud among believers; reaching for another person as practice, not failure. Job 10:1–2, 15; James 5:11; Galatians 6:2; Romans 12:15. — B (lyric 2 carries the frame; the reaching move wants a memory)

Must land somewhere (Card 1 or 4): *"There are many, however, that receive no relief in this life, suffering even unto death"* — the manuscript's most pastorally honest line, and the guard on the binding constraint. EXCLUDE from Vol 1: JoD 1:148 heartstrings threat; "God determined to test him" framing; performance-conditional chastening texts. Pastoral constraint governs every tier: explore-tier commitments must be doable IN darkness; Card 3's commitment worded as leaning, not resolving; the chapter points plainly toward real human help where a reader may be in crisis. 2 Nephi 31:20 deliberately left to Ch 29. Readiness check: moderate (Ch 9; Ch 14 prayer). Two-testimony template extension stays DEFERRED to the Ch 27 draft session.

### Ch 28 — Laying Up Treasures in Heaven (4 cards; source Ms 32)

Lane: what you love. RV downsizing = the strongest untapped witness in the batch.

1. **Where Your Treasure Is** — the honest inventory of what your heart actually treasures. Matthew 6:19–21; Luke 12:15, 34. — A (SEED: RV downsizing)
2. **Labor for What Satisfies** — redirecting yearning to authentic treasures. Isaiah 55:2; John 6:27; Matthew 6:33; ✦2 Nephi 9:51. — B
3. **No Heart Can Serve Two Masters** — naming your Babylon; turning toward Zion as purity of heart. Matthew 6:24; 1 John 2:15–17; 1 Timothy 6:6–10; ✦Moses 7:18. — B
4. **Open Hands** — practicing release: the treasure travels ahead of you. Luke 12:33; Matthew 19:21; Acts 20:35; 1 Timothy 6:7; ✦Mormon 8:37 (heart-diagnosis only). — A (SEED: RV downsizing)

Defer to Vol 2: consecration economics, D&C 105, Nibley polemic, flee-Babylon eschatology. Drop/soften Revelation 3:16. Readiness check: light. No appendix.

### Ch 29 — Enduring to the End (4 cards; source Ms 35) — FINAL GRACE ECHO

Lane: what you keep doing. Scripture study removed (→ Ch 17). Echo designed as Ch 18's pair.

1. **Begun Is Not Finished** — conversion is a road, not an arrival. Matthew 24:13; Philippians 3:12–14; Luke 9:62; Hebrews 12:1–2; ✦2 Nephi 31:16. — B
2. **Return Quickly** — the practice is speed of return, not perfection of record. Ezekiel 33:14–16; Proverbs 24:16; 1 John 1:9; Luke 15:20. — B
3. **Watch Your Joy** — joy as the gauge; when it fades, back to basics (drift-detection, NOT Ch 27's dark night — boundary named in draft). John 15:10–11; Psalm 51:12; Galatians 6:9. — B
4. **Grace for the Long Walk** — the final echo: strength to keep walking is itself received. Isaiah 40:29–31; 2 Corinthians 12:9; Philippians 1:6; Luke 21:19; ✦D&C 14:7 (the ms itself calls eternal life a *gift* — the echo's warrant). Commitments receptive in grammar (ask/wait/lean), not performative. — B

Defer to Vol 2: covenant/practice checklists (temple, priesthood, Word of Wisdom, sacrament renewal, "unite with the true Church"). Omit Alma 24:30 fall-from-grace framing from Vol 1. Tithes bullet → Ch 23. Readiness check: light (Ch 15). No appendix.

---

## 5. Witness grading summary (55 slate cards + Ch 14 card 5)

| Grade | Count | Cards |
|-------|-------|-------|
| A | 15 | Ch 18 (5), Ch 25 (4: cards 1,2,3,5), Ch 26 (4: cards 1–4), Ch 27 card 1, Ch 28 cards 1,4 — minus overlaps counted once |
| B | 28 | Ch 17 (4), Ch 19 cards 1–2, Ch 20 card 3, Ch 21 card 3, Ch 22 (4), Ch 23 (4), Ch 24 cards 1–3, Ch 25 card 4, Ch 26 card 5, Ch 27 cards 2–4, Ch 28 cards 2–3, Ch 29 (4) |
| C | 13 | Ch 19 cards 3–4, Ch 20 cards 1,2,4,5, Ch 21 cards 1,2,4, Ch 24 card 4, Ch 14 card 5 (fasting), plus 2 marked optional seams |

The C cluster concentrates exactly where the first pass predicted: Ch 20 marriage, Ch 21 children — plus Ch 19's two hardest cards. Ch 27 resolved better than its C prediction because the diptych carries cards 1 and 4.

---

## 6. Witness Harvest prompt list (Ch 20 and Ch 21 first, per ruling)

Each prompt is designed to surface ONE concrete memory usable as a 100–150 word first-person witness. Answer in any form — voice memo, bullet, paragraph.

### Ch 20 — Building Godly Marriages (first priority)

1. *(Card 1, One Flesh)* Take me back to a single early-marriage moment with Michelle when it stopped being "my life plus her" and became one thing — a decision, a move, a hard season — when "we" quietly replaced "I." Where were you, and what changed after?
2. *(Card 2, Being the Right Person)* What is one specific habit or reflex of yours that you deliberately went to work on for Michelle's sake — not because she demanded it, but because you saw it was costing her something? What did the first month of that private project look like?
3. *(Card 3, Fidelity of the Heart)* You and Michelle live and travel in a few hundred square feet with total transparency. What is one concrete guardrail or habit you two keep — about screens, travel, friendships, or how you speak about each other to others — that protects the marriage, and where did it come from?
4. *(Card 4, Words That Build)* RV life means breakdowns, wrong turns, and no room to sulk. Tell me about one specific tense day on the road when a kind word — yours or Michelle's — turned the whole day. What was actually said?
5. *(Card 5, A Threefold Cord)* What does couple worship actually look like in your rig — when do you and Michelle pray or read together, who starts it, and was there ever a stretch when the habit lapsed and you had to rebuild it? Tell me about the rebuild.

### Ch 21 — Raising Children in Righteousness (first priority)

6. *(Card 1, An Heritage of the Lord)* In 26 years, was there one student who walked into your science room clearly carrying a load from home — and you realized that for 55 minutes a day, this was a child God had entrusted to you? What did you change about how you treated that one kid?
7. *(Card 2, Provoke Not to Wrath)* Every teacher has a moment they almost handled in anger and didn't — a lab wrecked, a lie told, defiance in front of the class. Tell me about one time you corrected a young person firmly but left their dignity intact. What did you say, and what happened between you afterward?
8. *(Card 3, As You Walk by the Way)* Give me one specific teachable moment you engineered — in your classroom, with family, or around a campfire in your ministry travels — where an ordinary thing became a lesson about God. What was the object, and what was the sentence that landed?
9. *(Card 4, Lois and Eunice)* From the road, how do you actively stay a blessing to the generation behind you — a grown child, a grandchild, or a former student who still writes to you? Tell me about one recent call, letter, or visit where you got to hand something of your faith forward. *(Confirm: should this witness be biological or spiritual generation?)*

### Ch 27 — Bearing Trials in Faith

10. *(Card 2)* Tell me about one prayer you prayed hard — in the teaching years, the ordination years, or on the road with Michelle — that God did not answer the way you begged Him to. Where were you standing, and what did you do the next morning?
11. *(Card 3)* As a science teacher you actually understand refining chemistry. Was there a season of your life you only recognized as a furnace afterward — something the downsizing, or leaving the classroom, burned away? What did it cost while it was hot?
12. *(Card 4)* Was there a time someone sat with you or Michelle in a hard stretch without fixing anything — or a time in your ministry when someone in darkness reached for you? What did their reaching look like, concretely?

### Ch 19 — Loving Our Neighbors

13. *(Card 1)* In your RV travels, tell me about one time a stranger at a campground — someone you'd never see again — needed something concrete (a jack, a jump, a meal, an ear). What did you actually do in the next ten minutes?
14. *(Card 2)* You get brand-new neighbors every time you park. Was there one neighboring camper whose name and story you deliberately learned — how did the first conversation start, and what did you know about them by the time you pulled out?
15. *(Card 3)* Has there been one person you were praying for by name when it dawned on you that YOU were supposed to be part of the answer? What was the prayer, and what did you do that same week?
16. *(Card 4)* In 26 years of teaching there was surely a colleague, parent, or administrator whose offense you had to carry into the building every morning. Pick one (no names needed). What did the first day of deliberately choosing kindness toward that person look like — and when did the weight lift?

### Ch 22 — Developing Our Talents

17. *(Card 1)* When you and Michelle sold or gave away nearly everything to fit into the RV, was there one specific possession or moment at the donation pile where "it was never really mine anyway" became real? Tell me that moment.
18. *(Card 2)* Was there a stretch of years when your music sat buried — and what specifically pulled the first new composition out of you? What did it feel like the first time one of your sacred pieces was actually heard?
19. *(Card 3)* Who is one student whose face you still remember — someone you watched discover an ability they didn't know they had? What did they do with it?
20. *(Card 4)* On the road, what's the smallest, least "spiritual" skill — fixing something, a science explanation, a camp-neighbor kindness — that unexpectedly opened a door for ministry?

### Ch 23 — Financial Stewardship

21. *(Card 1)* Was there a season when providing was genuinely hard — early teaching salary, an unexpected bill — where you saw God honor plain hard work? One specific month or provision.
22. *(Card 2)* What's one thing you thought you couldn't live without that didn't fit in the RV — and when did you last miss it? What did 45 feet teach you about "enough" that a whole house never did?
23. *(Card 3)* Can you remember one tithing payment that genuinely cost you — a month it didn't add up on paper — and what happened after?
24. *(Card 4)* Tell me about one time on the road you or Michelle gave something unplanned — or one fast Sunday where skipping two meals connected you to a specific person's hunger. Who was it?

### Ch 24 — Tending the Garden

25. *(Card 1, fallback if seed thin)* What single fact about the human body never stopped astonishing you in 26 years of teaching it — and when did a student's jaw last drop with yours?
26. *(Card 2)* Is there one appetite or habit — food, screens, late nights — that you deliberately put under governance on the road, and what changed in your prayer or your temper?
27. *(Card 3)* Name one specific place — a canyon rim, a night sky at a boondock site — where "the earth is the Lord's" stopped being a verse and became the view. What did you and Michelle do differently afterward?
28. *(Card 4, if included)* Retirement and the RV rebuilt your daily rhythm from scratch. What does the first hour of a good morning look like now — and what has that rhythm given back that the teaching years couldn't?

### Ch 25 / Ch 26 (single gaps in grade-A chapters)

29. *(Ch 25 card 4)* Was there ever a moment, in a VR world or anywhere else, where you *couldn't* talk about Christ — and later someone told you they'd noticed something different about how you treated people? Who was it, what did they say?
30. *(Ch 26 card 5)* Pick one time you served your community through something organized that wasn't the Church — a food drive, a school event, a cleanup, a shelter shift. What's one scene you can still picture?

### Ch 28 / Ch 29

31. *(Ch 28 card 2)* Name one thing you stopped spending yourself on and one thing you started — a specific evening where the trade turned out to be bread instead of husks.
32. *(Ch 28 card 3)* Was there a stretch — mid-career, salary and house and reputation growing — when you'd have said you served God but your calendar said otherwise? When did you first see the two masters clearly?
33. *(Ch 28 card 4, sharpen the A-seed)* Which single possession was hardest to let go of when you emptied the house — and who has it now?
34. *(Ch 29 card 1)* Twenty-six years of first-period bells: what small, unglamorous thing did you do every school morning that kept you a teacher — and is there a spiritual practice you've kept the same way since?
35. *(Ch 29 card 2)* Tell me about a time you drifted — a season your prayers went quiet — and what the first step back actually was. Who or what met you on the way back?
36. *(Ch 29 card 3)* How do you and Michelle notice when one of you is running dry — is there a tell, a phrase, a mile-marker moment? What did "back to basics" look like in a 45-foot RV?
37. *(Ch 29 card 4)* Name one long stretch you now know you did NOT power through on your own — where did the strength actually come from, and when did you first realize it hadn't been yours?

### Ch 14 amendment

38. *(Fasting card)* Tell me about one fast that mattered — a Sunday you fasted *for* something or someone specific. What was the need, what did the hunger keep reminding you of, and how did the fast end?

---

## 7. Ch 14 amendment — the fasting card (card 5, drafted)

**Ships as one unit with CC_14_5 practice + blesses audio and a regenerated `card-audio-14-prayer-as-a-lifestyle.json` manifest — the manifest keys otherwise mismatch the rendered cards. This is not optional and does not ship after the card.** Ch 14 keeps its numbered slug and asset scheme. Appended as card 5; localStorage keys for cards 1–4 untouched.

### Card 5 — Fasting with Purpose

**Scriptures (header chips)**

| display | url (after /study/scriptures/) |
|---|---|
| Isaiah 58:6–9 | ot/isa/58?id=p6#p6 |
| Matthew 6:16–18 | nt/matt/6?id=p16#p16 |
| Mark 9:29 | nt/mark/9?id=p29#p29 |
| Acts 13:2–3 | nt/acts/13?id=p2#p2 |

*In-text inline links: Alma 5:46 → bofm/alma/5?id=p46#p46 · D&C 59:13–14 → dc-testament/dc/59?id=p13#p13*

#### Tab 1 — How We Practice
**`<h4>The Fast God Chooses</h4>`**

Fasting is prayer's purposeful companion. When we fast, we set aside food for a time—ordinarily two meals—and give the Lord what those hours and that hunger would have claimed. But going without eating is only the shell of the practice. The Lord asked Israel, "Is not this the fast that I have chosen?"—a fast that looses burdens, breaks yokes, and draws His answer near: "Then shalt thou call, and the Lord shall answer" (Isaiah 58:6–9). A true fast always faces toward God and carries a purpose before Him.

Jesus taught His disciples to fast quietly, without display, "unto thy Father which is in secret" (Matthew 6:16–18)—and He named fasting alongside prayer as the way certain strongholds finally yield: "This kind can come forth by nothing, but by prayer and fasting" (Mark 9:29). The early Church fasted when it sought direction at hinge moments, and the Spirit spoke (Acts 13:2–3). Prophets in every age have done the same, fasting "many days" to know the things of God (Alma 5:46).

So we fast with a purpose we can name: a question that needs an answer, a person who needs heaven's help, a weakness that needs breaking, a thanksgiving that needs room. We open the fast with prayer, let each pang of hunger renew the petition, and close the fast with prayer. Begun and ended at the Lord's feet, the fast becomes something greater than hunger—it becomes prayer that the whole body prays.

*Drafting notes: ~250 words. Expands and clarifies the discipleship practice already taught in prose Ch 5—does not introduce it. Isaiah 58:6–9 is the spine; vv. 10–11 (feed the hungry) deliberately left to Ch 23's offering card per the overlap split. Mark 9:29 used rather than Matthew 17:21 (manuscript-attestation caution); drafter may swap. LDS specificity (fast Sunday rhythm, two meals) kept inside the tab per Group 5 convention.*

#### Tab 2 — How It Blesses
**`<h4>Hunger That Turns to Light</h4>`**

The promise of Isaiah's fast is extravagant: "Then shall thy light break forth as the morning, and thine health shall spring forth speedily… thou shalt call, and the Lord shall answer; thou shalt cry, and he shall say, Here I am" (Isaiah 58:8–9). Modern revelation adds that fasting done with "full purpose of heart" brings "fulness of joy" (D&C 59:13–14). Fasting does not earn these blessings; it clears the table for them.

[WITNESS SEAM — Aaron: one specific fast (see harvest prompt 38). Frame: the purpose you carried, what the hunger kept reminding you of, how the answer or the peace arrived. 100–150 words, first person.]

`<p class="bridge-text">`Whether fasting is a practiced rhythm for you or something you have never once tried on purpose, the commitment below invites you to give the Lord one fast with a purpose you can name.`</p>`

#### Tab 3 — How Will You Practice?

| tier | text |
|---|---|
| covenant | This fast Sunday, I will fast with a written purpose—opening and closing the fast with prayer, and pairing it with a generous fast offering. |
| seeker | This week, I will skip one meal for a purpose I can name, and spend the mealtime in prayer or quiet reflection on that need. |
| explore | This week, I will set aside one thing for one day—a meal, a screen, a comfort—and notice what fills the space when I ask God to. |

**Reflection prompt:** *If your next fast could carry one question or one person's name to God, whose would it be?*

*Readiness check note for assembly: the card's intro line should point back to prose Ch 5 (Sincere Prayer) where the principle is first taught.*

---

## 8. Appendix decisions (consolidated)

| Chapter | Appendix | Note |
|---------|----------|------|
| Ch 20 | **YES — recommended** | Owns the shared marriage/parenting "Building" architecture, roles deep-dive, extended counsel. Dual-audience per Addendum 1 §11. |
| Ch 27 | **YES — recommended** | Deep pathway for suffering theology (Job arc with the "no relief in this life" counterweight, Gethsemane, refiner texts); carries the exegetical weight the cards must not. |
| Ch 24 | **NO — withdrawn** | Health specifics gone to Vol 2; no overflow remains. |
| All others | NO | Readiness checks name prerequisite chapters directly. |

---

## 9. Flags, risks, and corrections from the source reads

1. **Ch 27 production guides NOT FOUND on disk.** The handoff says `Ch31-The-Chapel-of-My-Heart-Production-Guide` and `Ch31-We-Who-Love-God-Production-Guide` live in `C:\Users\aaron\Documents\WoP\` — that folder contains only ops files, and a Documents-wide search found nothing under those names; ministry-rag search also did not surface them. This session's Ch 27 slate was verified against Ms 31 plus the handoff's harvested diptych principles (which are detailed and sufficient for Phase 0). **Before the Ch 27 draft session, locate or re-save both guides** — the standing instruction requires reading them in full before drafting.
2. **Scripture corrections found:** Ms 21 misattributes 1 Thessalonians 4:11–12 as Colossians 3:23. Isaiah 53:4 is listed in the handoff as "present" in the We Who Love God context but is NOT in Ms 31—add it fresh in Ch 27 Card 2. Verify the Holland/Matthew Henry "close to his heart" attribution if used in Ch 20.
3. **Style-guide violations in sources** ("Mormon Christians," "Mormon polygamy," obsolete "home/visiting teaching"): never carry into drafts; "Mormon Christianity" survives only as the book subtitle.
4. **Encoding artifacts** (mojibake "Aÿ", "Crist" typo) in Ms 21/25/26 — repair before quoting.
5. **The "extreme selfishness" sentence in Ms 26** (family-size counsel) must not carry into Volume 1 in any form.
6. **Ch 22's source is thin (52 lines)** — expect drafting stretch; the four-card slate compensates with the parable's own structure.
7. **Repo hygiene items** (stale prevChapter links, nine sitemap-leaking stubs, Ch 17 stub permalink still numbered) remain open in Claude Code and do not block drafting.

---

## 10. What every subsequent draft inherits

1. This brief's slates, lanes, grades, and deferrals.
2. The **calibration delta** extracted from Aaron's completed edit of Ch 18 (voice, register, compression, witness texture).
3. The 5-Phase Standard + Addendum 1 protocols (pedagogy test, readiness template, overflow rule).
4. Unnumbered slugs; numbered filenames; asset timing corollary; `status: draft` deployment; Chicago em-dashes, no spaces; Latter-day Saint style guide.
5. Witness material only from graded seeds or harvested answers — no invented first-person memory, ever. Unfilled seams ship as marked seams.

*— End of Batch Design Brief —*


---

# AMENDMENT 1 — August 9, 2026 (ratified by Aaron)

**Trigger:** The Ch 18 direction changed. The Christlike Practices web app (interactive companion built on the ~70-practice behavior-first corpus, eight virtue domains, practice cycles) supplants the five-card Ch 18 slate. Reconciled architecture: `WoP_Ch18_ChristlikePractices_ReconciledArchitecture_20260809.md` (project knowledge). This amendment supersedes the brief wherever they conflict; everything not named here stands as written.

## A1.1 Ch 18 slate withdrawn

The five-card Ch 18 slate (Becoming by Beholding · The Empty Vessel · A Being of Truth · Live in Thanksgiving Daily · The Crowning Virtues) is **withdrawn from the card-chapter slate**. Ch 18 breaks the card-chapter pattern of necessity; the remaining Movement 3 chapters (17, 19–29) **return to the standard card-chapter pattern** per Aaron's ruling. Batch card accounting drops by five.

The withdrawn draft is **not discarded**: its content, the beholding frame, and the Ms 33/34 harvest lines (vessel/pride, "better than we are," "every heartbeat," justice/mercy/grace summary) remain source material for (a) the Ch 18 introductory prose and (b) the updated Character-of-Jesus portrait, which becomes Ch 18's narrative alternative to the app (read/listen).

## A1.2 Ch 18 identity

- **Title:** *Do As I Have Done* (from John 13:15 KJV, "I have given you an example, that ye should do as I have done to you"). Supersedes "Christlike Virtues."
- **Slug:** `do-as-i-have-done` (unnumbered per the Aug 7 naming ruling). Supersedes `christlike-virtues`. Stub rename (`src/chapters/18-christlike-virtues.njk` → `18-do-as-i-have-done.njk`, pageTitle, permalink, chapter-status.yaml) is a Claude Code task; nothing published, no redirect burden.
- **Hero scripture:** John 13:15 (supersedes Micah 6:8).
- **Intro scripture set:** 1 John 2:6 · 1 Peter 2:21 · Ephesians 5:1-2 · 1 Corinthians 11:1 (with John 13:15 as hero).
- **Role:** motivational introduction, behavior-first methodology explanation, app tutorial, and launch point (`/practices/`, in-site route, ratified) — plus the portrait as narrative alternative.

## A1.3 Voice calibration reassigned

Ch 18 no longer anchors calibration. **Aaron's editorial pass over the ~70 practice cards (Christlike Practices corpus, Phase 1) is the voice-calibration corpus.** The calibration delta is extracted from the diffs of those edits (batched by domain) and governs every remaining Movement 3 draft. This yields a far larger delta sample than five cards would have.

**Drafting order becomes:** practice-corpus batches (calibration) → **Ch 25, 26** → **Ch 17** → Witness Harvest (Ch 20/21 prompts first) → 19 → 20 → 21 → 22 → 23 → 24 → 27 → 28 → 29. If Aaron prefers not to gate Ch 25/26 on the full corpus pass, the delta from the first two or three domain batches is sufficient to begin.

## A1.4 Grace-echo chain preserved (ratified)

The chain Ch 9 → 12 → 13 → 15 → **18** → **29** → 31 stands. Ch 18's echo is carried **explicitly in the intro prose**: virtues received through beholding, not performed — the app is a place of practice, never a ladder of merit; the OBSERVE JESUS → IMITATE sequence is the beholding frame in interactive form. The Ch 18 ↔ Ch 29 designed pairing is intact (Ch 29: grace sustaining the long walk, not rewarding it).

## A1.5 Overlap-map touchpoints

- "Gratitude, humility, honor — Ch 18 only" now resolves to the app corpus (Humility & Inner Government domain: CDP-006, 017, 041 et al.) with Ch 18 prose introducing, not teaching, the virtues.
- Forgiveness-of-others teaching home remains **Ch 19 Card 4**. The app's Grace & Restoration domain (esp. CDP-028 Forgiveness Without Limit) must cross-reference Ch 19 for the practice, mirroring the withdrawn Card 5 routing rule.
- Witness-grade accounting: Ch 18's five grade-A cards leave the batch tally; the Witness Harvest list is unaffected (no Ch 18 prompts were in it).

## A1.6 Unchanged

Ch 14 fasting-card amendment; all other slates, witness grades, collision routings, appendix decisions (Ch 20 yes / Ch 27 yes / Ch 24 withdrawn); `status: draft` deployment convention; asset-timing corollary.

*— End Amendment 1 —*
