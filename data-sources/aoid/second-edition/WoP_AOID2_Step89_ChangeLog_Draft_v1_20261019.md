# AOID2 step 89, part 1: the Second Edition change log, DRAFT v1
Session CHAT-AOID2-48a, 19 Oct 2026. Ledger row 1A.9 (Gate 1 criterion 5, AOID2-EDITION). Status: APPROVED by Aaron 19 Oct 2026, 18:56 ET ("Approve the change log."), with the five design choices as written. BUILD TEXT. [VERIFY] lines are checked by the build run against the switch-OFF and switch-ON builds; [PENDING] lines are settled at the text freeze. Placement: RULED AOID2-CHANGELOG-PLACEMENT option 1 (19 Oct 2026, 18:58 ET, topic-only): its own page, /aoid/second-edition/, linked from the words "Second Edition" in the Prologue's edition note (markup only, wording unchanged); the preserved First Edition page may link back. Teaching Practices scoring owed before deploy.

## How this inventory was built (not build text)

- **Baseline.** The First Edition is the Articles as they stood at commit c8999d1 (20 Sep 2026), the text preserved at /articles/first-edition/ (src/_data/aoidSecondEdition.js; CODE-AOID2-25 report). Everything since c8999d1 is a Second Edition change, whether or not it sits behind the switch.
- **Read:** git history of src/_includes/aoid and src/_data/apparatusData.json since c8999d1 (wop-shell git_log); the approved-wording files (Step75 Prologue, Step78 Article 1, Step79 Articles 4, 5, 9, 11 and 13, A08 v3, A12 v3); the live a02.njk, a06.njk and all fourteen article titles (wop-shell, read directly).
- **Not read:** a built-page diff. Commit messages are descriptions, so the build run must check every line below against the switch-OFF First Edition page and the switch-ON build before anything goes live (codex D1). Items marked [VERIFY] rest on a description only.
- **Seven changes are already live without the switch,** so the site today already differs from the preserved First Edition: the Article 2 dagger and footnote; Article 6 s18 (Philippians 2:13); the Article 11 patience sentence; the Article 13 s4 sentence; the Article 4 "open canon" notes; the Article 8 conviction paragraph; Hebrews 13:8 moved to the biblical column. The log includes them.

## Design choices for Aaron to approve with the text

1. **No counts in the change log.** Counts live in the footnotes, the disclosures and (once built) beside each teaching. A recount then never makes the log wrong.
2. **Apparatus changes summed up, not listed span by span.** The span-level record stays in the repository and the conductor; readers get the shape.
3. **A "Later corrections" section that starts empty.** The approved method account promises that "any change to a count is decided openly and recorded with its date and reason." This gives that promise a home on the page.
4. **[PENDING] lines** describe work not yet built. Each stays or comes out at the text freeze.
5. **Placement** is ruled: AOID2-CHANGELOG-PLACEMENT option 1 (see status line).

---

## What Changed in the Second Edition

**In short.** The Second Edition (2026) keeps the witness of the First Edition and adds to it. A new Article on love for God and neighbor now leads the Articles. Teachings held in common across Christian traditions were added to nine others, and each added teaching was measured against sixteen traditions. Every Article now shows how it was measured. The [First Edition](/articles/first-edition/) remains as first given.

### The shape of the Articles

- **A Prologue.** *Of Plainness*, the First Edition's first Article, now stands before the Articles as the Prologue. It gains a note on this edition, and one sentence on the only line these Articles draw for fellowship: the confession of Christ's name, a line that closes no door.
- **A new Article 1.** *Of Love for God and Neighbor* sets the two great commandments at the head of the Articles. Articles 2 to 13 keep their numbers and their titles.

### What each Article gained

- **Article 1, Of Love for God and Neighbor** (new). The two great commandments and the good Samaritan; the golden rule; love for enemies; forgiveness; truthful speech; care for the hungry, the stranger, the naked, the sick and the prisoner; doing good to all; hospitality; prayer for the sick; and Christ's new commandment, that His disciples love one another as He has loved them.
- **Article 2, Of God.** No new sentences. The teaching that God is the Father of our spirits is now marked as biblical witness rather than common ground (†), with a footnote and a full disclosure.
- **Article 3, Of Creation and Life.** Unchanged.
- **Article 4, Of God's Word.** The witness of the apostles Christ chose, who bore witness of what they had seen and heard.
- **Article 5, Of Jesus Christ.** That He came to seek and to save that which was lost; and that He ascended into heaven, sat down at the right hand of God, and ever lives to make intercession for us as our advocate with the Father.
- **Article 6, Of Salvation.** Paul's counsel to work out our own salvation with fear and trembling now carries its second half: God works in us both to will and to do.
- **Article 7, Of the Kingdom at Hand.** Unchanged.
- **Article 8, Of Fellow Believers.** It now begins with the Father: Christ taught His disciples to pray "Our Father," called God "my Father, and your Father," and set the standard by which all would know His disciples, their love one to another. New: the disciples' gathering together to pray, to read the scriptures, to sing and to strengthen one another, with Christ's promise to be in the midst of them. Several sentences are reworded [VERIFY which, against the First Edition text]. A link now leads to the Fellowship Agreement that governs our gatherings, and the Article's refusal to defend the walls of division is disclosed as this ministry's own conviction, not a teaching measured across the traditions.
- **Article 9, Of Finding Our Way.** Its second paragraph is rewritten. New: a paragraph on the Holy Spirit, the promised Comforter, by whom God is present with His people, who teaches, testifies of Christ, sanctifies, and gives gifts for the good of all; and a sentence on submitting to God and resisting the devil. The commentary is revised throughout, and five quotations of Latter-day Saint scripture in the First Edition commentary that did not match their source are corrected, each with a dated note.
- **Article 10, Of Living by Grace.** Unchanged.
- **Article 11, Of Covenants and Commitments.** A sentence on Christ's patience with our becoming. New: sexual holiness (sexual union as a holy gift whose rightful place is marriage, and chastity outside it), introduced with the plain acknowledgment that Christ's disciples are not all of one mind on it, and marked as witness (†); marriage held in honor; rendering to Caesar and to God; honest work; and the Lord's Supper.
- **Article 12, Of Immortality and Eternal Life.** Christ's return in glory, and the promised new heavens and new earth. The sentences on the final accounting are reworded, and the reflection question is new.
- **Article 13, Of Our Confidence.** That Christ receives all who sincerely confess His name and seek to do the will of His Father; and Christ's commission to make disciples of all nations, with His promise to be with them always.

### How the Articles are now shown

- **Three tabs on every Article:** Declaration (the Article itself, with its sources a click away), Disclosure (how we hold it and how it was measured), and Record (the research behind the counts, where an Article has one).
- **Plain commentary.** The commentary on each measured teaching now opens by saying exactly what the Article claims, and what it leaves to each tradition to fill in its own house. Biblical sources were added throughout.
- **How this was measured.** A short link under each measured teaching leads to the account of the method.
- [PENDING, step 89] **The count beside each teaching:** taught in so many, contradicted in so many, no position in so many, of sixteen.
- **Two disclosures in full,** for the two teachings kept as witness: *Of the Father of Spirits* and *Sexual Holiness*.
- **A way to correct us.** Readers can tell us of a church text we have misread or missed.
- [PENDING, step 124] Quotations in the First Edition commentary of the other Articles that did not match their source are corrected, each with a dated note.
- [VERIFY] The First Edition's films, PDFs and slides are labelled First Edition; the films for Articles 2 and 6 are new.

### Later corrections

None yet. Any change to a count, or any correction made after publication, will be recorded here with its date and its reason.

---

## Teaching Practices score (WoP-Teaching-Practices-Standard.md v1.0, read from WoP\ops 19 Oct 2026)

Scorer: Claude (Chat), CHAT-AOID2-48a. Date: 19 Oct 2026, 19:10 ET. Scored: the approved v1 text above, as prose.

**Hard gates.**
- G1 Sourced at the unit of display: **NOT MET.** Each line claims a change but no line links to the Article it names, and "measured against sixteen traditions" does not link to the method account. Fix: A2, A3 below.
- G2 Absence renders as absence: MET ("Unchanged" for Articles 3, 7, 10; "No new sentences" for Article 2).
- G3 No score on a people: MET. No figures attached to any communion.
- G4 Author sign-off: MET (approved 19 Oct 2026, 18:56 ET).

**Criteria (0/1/2).** N/A: 1 (a record of edits has no phenomenon to stage without distorting it), 2, 7 and 8 (it argues nothing and weighs no evidence).
3. Non-examples: 1. It marks what did not change, which is the record's own boundary.
4. Model visible and portable: 0. It names measurement but neither shows nor links the method.
5. Two or more lenses: 2. Stability and change; structure and function (the tabs).
6. Quantities carry their uncertainty: 1. "Nine others" is wrong (see A1); "five quotations" carries its locator.
9. Practice named: 0.
10. Correction channel prominent: 1. Named ("A way to correct us") but not linked.

**Total:** 5 of 12 applicable, prorated 8 of 20, and G1 not met. **Not ready.**

**Error in the approved text (Chat's, owned).** "Teachings held in common ... were added to nine others" is wrong. By the approved-wording files, measured shared teachings were added to seven Articles besides Article 1: 4, 5, 8, 9, 11, 12 and 13. Article 6 gained a clause of a verse already cited (Philippians 2:13), not a new floor; Article 2 gained only its dagger.

**Finding.** "Each added teaching was measured against sixteen traditions" is true only after Stage 2 (step 49); see the same finding in the method account file.

## AMENDMENTS v2: APPROVED by Aaron 19 Oct 2026, 19:13 ET ("Approve the amendments"). A1-A5 are BUILD TEXT; A1 corrects the approved "nine others" to "seven others". Re-score on the built page before deploy.

**A1 (correction).** In short: "added to nine others" becomes "added to seven others."
**A2 (G1, criterion 4).** In short: link "measured against sixteen traditions" to the method account ("How These Articles Were Measured").
**A3 (G1).** Each Article name in "What each Article gained" links to that Article; "First Edition" in the opening already links.
**A4 (criterion 10).** "A way to correct us" links to /aoid/corrections/.
**A5 (criterion 9), after the In short paragraph:**
> Read it beside the [First Edition](/articles/first-edition/) to see how the Articles grew, and what was kept as first given.

**Projected score with A1-A5:** G1 met; 3:1, 4:1, 5:2, 6:2, 9:2, 10:2 = 10 of 12, prorated 17 of 20. **Deploy with gaps named:** criteria 3 and 4 stay partial because a change log records the method rather than running it; the method account carries that work.


---

## AMENDMENTS v3, B1-B5 (APPROVED by Aaron 20 Oct 2026, 09:29 ET: "I approve B1 through B5.") Session CHAT-AOID2-48b, after the CODE-AOID2-48 review.

**B1. Article 9.** The line becomes: "**Article 9, Of Finding Our Way.** Its second paragraph is rewritten. New: a paragraph on the Holy Spirit, the promised Comforter, by whom God is present with His people, who teaches, testifies of Christ, sanctifies, and gives gifts for the good of all; and a sentence on submitting to God and resisting the devil. The commentary is revised throughout." The held step-124 line becomes (still not rendered until step 124 is built): "Quotations in the First Edition commentary that did not match their source are corrected, each with a dated note."

**B2. Article 11.** The line becomes: "**Article 11, Of Covenants and Commitments.** A sentence on Christ's patience with our becoming. New: sexual holiness (sexual union as a holy gift whose rightful place is marriage, and chastity outside it), introduced with the plain acknowledgment that Christ's disciples are not all of one mind on it, and marked as witness (†); marriage held in honor; rendering to Caesar and to God; honest work; and the Lord's Supper. Christ's command to His apostles to teach all nations, baptizing them, now stands beside His own baptism, and the first disciples' answer follows: they that gladly received the word were baptized. Peter's answer is quoted in full, with the promise of the gift of the Holy Ghost. New: a pledge that we will not explain away or set aside anything Christ did as our example, plainly taught, or implied in His parables. John 3:5 is now quoted in the King James words, \"born of water and of the Spirit.\"" (The witness mark is the dagger †.)

**B3. Article 12.** "the reflection question is new" becomes "the reflection question is reworded".

**B4. The two new films (Articles 2 and 6, made 7 Oct 2026).** The build run checks whether each new film reads the Second Edition text of its Article. If it does, its button reads "Second Edition"; if not, it keeps "First Edition". The change log's films line states what was found, replacing the [VERIFY] line.

**B5. New line under "How the Articles are now shown":** "Where the earlier disclosures said a family held \"no common position,\" the Articles now say \"no position.\" The meaning is unchanged: no church in the family has adopted a text either way." (Ruling AOID2-NO-POSITION-VOCAB.)
