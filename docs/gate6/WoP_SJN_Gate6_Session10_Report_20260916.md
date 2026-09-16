# SJN Gate 6, session 10 — STOPPED at Task 1 (R6-28 Methodist H05 audit) (16 September 2026)

**The session stopped after Task 1 and before Task 2, as R6-28 directs. The author decides the correction.**

- **No model calls. Spend: 0.00 USD** of the 10 USD cap.
- **Not changed:** the workbook, the rulings file, the tp fixture, `prompts.py`, the guard tuple, the measurement rule,
  `operational-state.yaml`, the EO prompt, any packet, the public app.
- **Tasks 2 to 8 were not started.** R6-24 to R6-28 are **not yet recorded** in `author-rulings-pending-workbook.json`;
  they are reproduced verbatim at the end of this report so nothing is lost.
- **Eastern Orthodox did not run.**

Artifact: `data-sources/sjn/recovery-runs/session10/task1-methodist-h05-audit.json`, from `task1_methodist_h05_audit.py`.

---

## The headline

**By the letter of the stop, the audit is clean. By its purpose, it is not, and I stopped.**

| | count |
|---|---:|
| BSR-MW-01 RNR-H05 citations on a Gate 6 recovery packet card (any verdict) | **0** |
| RNR-H05 cards in the seven packets / RNR-H05 cells in live-1 | **0 / 0** |
| **Workbook cells that PUBLIC-CERTIFY a BSR-MW-01 citation for RNR-H05** | **1 — Q-039** |

The packets cannot hold an RNR-H05 citation. Gate 6 runs only OPEN cells (`registry.open_cells`: Rendered State
begins "NOT LOCATED"). All eight RNR-H05 cells, Q-033 to Q-040, were rendered A and PUBLIC-CERTIFIED **before**
Gate 6, so none entered live-1 or a packet. The audit scope named in the prompt was therefore empty by construction.

**Q-039 is exactly the case Chat's reading describes:** a finished Methodist cell citing the Articles of Religion,
Article I, for RNR-H05. And TP-049 is **not a test artifact**: it is Q-039's own ratified phrase, copied from the Case
Study Phrase Targets sheet. The stop says "on a finished-branch card"; Q-039's card is a workbook case-study card, not
a recovery packet card. I read R6-28's purpose ("the author decides the correction") as governing. Proceeding would
also have recorded R6-24's premise in the rulings file while a certified cell contradicts it (§4).

---

## 1. Question 1 — every BSR-MW-01 citation attached to RNR-H05

### The public citation

| field | value |
|---|---|
| branch / cell | Methodist / Wesleyan / **Q-039** (family RNR-H05 "Son") |
| phrase | "the Father, the Son, and the Holy Ghost" |
| locator | Articles of Religion of the Methodist Church, **Article I** (row BSR-MW-01 by URL `umc.org/en/content/articles-of-religion`) |
| verdict | author-ratified Case Study target status **ASSERT**; reviewer status **CERTIFIED**; rendered state **A** |
| on a card | the workbook cell's case-study card (not a Gate 6 packet card) |
| PUBLIC-CERTIFIED | **yes** (workbook v2.25r4 and `src/_data/sjn/cells.json`, v2.23) |
| loses its last citation without it | **yes**: the cell has one case-study target and no other evidence phrase |
| rendered on the live site | **no** (see below) |

### Every stored verifier rubric on a BSR-MW-01 row for RNR-H05 (17 distinct calls; measurement and calibration only, none on a card)

**One model call is one observation.** The files hold 24 records, but seven repeat a call:
- cal-2 and cal-3 re-serve cal-1's cached calls (same `call_id`);
- tp-2 was seeded from tp-1;
- session 8's three v1.3 TP-049 replicates are session 7's, reused.

| row / locator | phrase | distinct calls | read |
|---|---|---:|---|
| MW-01 **Article I** | "the Father, the Son, and the Holy Ghost" (TP-049 = Q-039) | 14 | **5 accept, 9 reject**. v1.2 1/1; v1.3 3/4 (FULL, FULL, PARTIAL; one WORD_ONLY reject); v1.4 0/4; v1.5 0/4; v1.6 1/1 PARTIAL. Every reject is WORD_ONLY. |
| MW-01 Article I | "three persons, of one substance, power, and eternity—the Father, the Son, and the Holy Ghost" | 1 | cal-3 sonnet v1.1: ACCEPT_WITH_CAVEAT |
| MW-01 **Article II** | "The Son, who is the Word of the Father, the very and eternal God" | **2** | ACCEPT FULL from sonnet and from opus, **both verifier gate6-v1.1**. Stored in cal-1, cal-2 and cal-3, but the same two calls. |

The sessions 7, 8 and 9 in-chunk candidates (TP-049-C1..C3) are recorded in `session9/measure-v16.json` and are not
repeated here.

### Instruments and search space (independence by instrument)

| instrument | what was read | RNR-H05 hits |
|---|---|---|
| S1 recovery packets | 7 packets, 247 cards, 1,176 card citations (candidates, rejections, witness-only, caveat slice/sample, exhaustion-sourced) + `dropped_at_build` | 0 |
| S2 live-1 | 247 cell states; 2,861 audit-log calls (meta) | 0 |
| S3 workbook v2.25r4 | Evidence-First Cell Queue, Case Study Phrase Targets, Inherited Public Citations, Citation Phrase Targets | 8 cells; **Q-039 on MW-01** |
| S4 `src/_data/sjn/cells.json` (v2.23) | 456 emitted cells | 8 cells; **Q-039 on MW-01** |
| S5 rubrics | cal-1..3 cells; tp-1, tp-2, tp-3, tp-4, tp-4-v1.5, tp-4-v1.6; sessions 7/8/9 replicate files | 157 distinct RNR-H05 verifier calls |
| S6 live site (browser `fetch`) | the five `/seeking-jesus/` pages on www.wordsofplainness.org | Q-039 **not rendered** |

S3 and S4 are the same publisher (the workbook and its pipeline output), so they count as one observation of the
certification, not two.

**Live site, read in the browser:**
- RNR-H05 renders only its Inherited Public Citation: Baptist Faith and Message 2000, II.B, "Christ is the eternal Son
  of God".
- "Q-039" appears on no page, and `cells.json` is not served (404).
- The two occurrences of "the Father, the Son, and the Holy Ghost" on the index page are the Latter-day Saint Godhead
  diagram text, not a citation.
- The only Articles of Religion citation rendered is RNR-H42 "without body or parts".
- `commandments.brotheraaron.org/seeking-jesus/` returns 404; the app is served from wordsofplainness.org.

**So the error is certified, not yet displayed.** `operational-state.yaml` lists the pending M3a as "certified case
studies (H05/H22/H43 from cells.json case_study_target)". Building M3a as planned would publish Q-039's phrase as an
agreement card.

---

## 2. Question 2 — RNR-H05 citations whose stored rubric says the phrase lacks the assertion

Public H05 citations only (the calibration and measurement candidates that are not citations are in the artifact,
`q2_by_citation`, 19 in all):

| cell | row | phrase | stored rubrics | what they say |
|---|---|---|---|---|
| **Q-039** Methodist | MW-01 Art I | "the Father, the Son, and the Holy Ghost" | 5/14 calls accept; **11 non-FULL or reject** | e.g. v1.5: "merely enumerates 'the Son' as a Trinitarian person … does not assert the eternal filial relation of the Logos"; v1.6: "does not explicitly state the relational/generative aspect (e.g., 'begotten of the Father')" |
| Q-040 Mennonite | MA-01 Art 1 | "the only Son, the Word who became flesh" | 9/11 calls accept; 2 reject | both rejects are **v1.4** (never in force), and the ground is subject, not content: "the title 'Son' is used as an object of the sentence rather than as the subject of an assertion about the eternal filial relation" |

- **No stored rubric at all on their ratified phrase:** Q-033 (Roman Catholic, Lateran IV: "the only begotten Son of
  God made flesh"; the phrase is not verbatim in the stored chunk) and Q-036 (Belgic Confession: "the only Son of God";
  trimmed from the fixture at the cap).
- **Accepted on every stored rubric:** Q-034, Q-035, Q-037 and Q-038 (TP-046, TP-047, TP-048 and TP-005).
- **Not changed.** Reported only, as instructed.

---

## 3. The author's decision: Q-039's correction (ranked, each with its weakness)

1. **Re-cite Q-039 from Article II of the same Articles:** "The Son, who is the Word of the Father, the very and eternal
   God" (14 words, verbatim in the stored chunk).
   - *For:* same document, same institution, same row. It names the Son, his relation to the Father as Word, and his
     eternity.
   - *Weakness:* it asserts **no generation**. Wesley omitted "begotten from everlasting of the Father". Under Chat's
     reading it is not a true positive either.
   - *Weakness:* its support is **two calls** (sonnet and opus) on **one prompt version, gate6-v1.1**, before
     IDIOM_OR_FORMULA and R6-2. The three calibration files repeat those two calls. It is unmeasured under v1.3 or
     later.
   - *Weakness:* it closely parallels Q-037 (Anglican Article II).
2. **Cite a different Methodist standard:** BSR-MW-02, the EUB Confession Article II, "the eternal Word made flesh, the
   only begotten Son of the Father" (one sonnet and one opus call accept; a third sonnet call accepts the "He is …"
   form; all v1.1).
   - *For:* "only begotten Son of the Father" is filiation language, and "eternal Word" is eternity.
   - *Weakness:* it is a different document from the one the cell names. The cell's Document and Locator change, not
     just its phrase.
   - *Weakness:* the same v1.1-only instrument, and it still says "only begotten", not "eternally begotten".
3. **Withdraw Q-039's certification:** render it NOT LOCATED and let Gate 6 recover it.
   - *For:* nothing public is certified on a phrase the verifier refuses on 9 of 14 calls.
   - *Weakness:* a PUBLIC-CERTIFIED A cell leaves the app, and the branch counts move.
   - *Weakness:* it needs a workbook write and an app release (both outside this session), and a Methodist H05 Gate 6
     run later.

Any of the three is a workbook write, which is outside session 10's constraints.

---

## 4. What I think is wrong in the prompt or in Chat's reading, with the artifact

1. **The audit's named scope could not find the case it exists for.** "Packets, cards and cell states" hold no
   RNR-H05 at all, because closed cells never enter Gate 6.
   - Read literally, R6-28 returns "clean" while a PUBLIC-CERTIFIED Methodist H05 cell cites Article I.
   - Artifact: `task1-methodist-h05-audit.json` → `search_space.why_the_packets_hold_no_h05`, `workbook_h05_cells`.
2. **"TP-049 … not a test artifact" is right, and stronger than stated.** TP-049 *is* Q-039's ratified public phrase
   (Case Study Phrase Targets row 8). Retiring TP-049 from the fixture (R6-24) does not touch the certified cell. The
   fixture and the public app would then disagree about the same citation.
3. **R6-24's premise may be stronger than the family's own scope.** Chat's reading requires *eternal generation*.
   - The workbook defines RNR-H05 as "Names the eternal filial relation of the Logos".
   - Its **Accepted scope note** reads: "Shared filial identity/relationship controls A; thick Nicene metaphysical
     entailments are not imported automatically." (Inherited Public Citations, row 6.)
   - If the scope note governs, "no RNR-H05 true positive exists on BSR-MW-01" is not established. Article II
     (candidate 1 above) is the open question.
   - What holds either way: **Article I's phrase is defective.** 11 of 14 calls floor it below FULL or refuse it, and
     every refusal says it only names the Son.
   - Before R6-24's reason is written into the rulings file, the author should confirm which standard it rests on:
     eternal generation, or eternal filial relation.
   - *Check hardest what you already believe:* I held that Article I fails from session 9. The new evidence here is
     against the broader claim about the whole row, not against Article I.
4. **Calibration evidence is easy to over-count.** cal-2 and cal-3 re-serve cal-1's cached verifier calls, so a
   per-file count triples them. My own first pass here reported Article II as "5/5" before I checked `call_id`; it is
   2 calls. The artifact now counts distinct calls (`search_space.S5_dedup_rule`). Session 9's TP-049 history
   (v1.3 3/4, v1.4 and v1.5 0/8, v1.6 1/1) is consistent with the deduplicated count.
5. **The deployed data file lags the workbook.** `src/_data/sjn/cells.json` is v2.23; the workbook is v2.25r4. Any
   correction to Q-039 reaches the app only through a pipeline rebuild. That is not new, but it bears on the release
   path for §3.

## 5. Pre-read for Task 2 (read-only; nothing built)

These checks change nothing. They are here so a resumed session starts from facts.
- "the Son is eternally begotten of the Father" is **verbatim in the stored BSR-RP-01 chunk**:
  - locator: Chapter 2.3 — Of God, and of the Holy Trinity
  - chunk hash: `fbbd0edc75a1…`
  - words: 8 by `textutil.phrase_word_count`
- **No tp-4 fixture item cites it.** The next free id is **TP-061**.
- It also stands in RP-04 6.013 and BA-02 2.3.
- Its stored rubrics are **two calls on RP-01** (sonnet and opus, both accept), one on RP-04 and two on BA-02, all
  gate6-v1.1. It has no v1.3 baseline, so Task 6's five v1.3 replicates are still needed.

## 6. To resume

The author rules on:
- **(a)** Q-039's correction (§3);
- **(b)** R6-24's reason wording (§4 item 3);
- **(c)** whether Tasks 2 to 8 run unchanged, given (a) and (b).

Session 10's prompt can then be re-issued as it stands. Task 1 need not re-run unless the workbook changes first.

---

## Spend

| run | calls | USD |
|---|---:|---:|
| (none) | 0 | 0.00 |

---

## Author rulings 2026-09-16, fifth set — received, NOT yet recorded (session stopped at R6-28)

R6-24 TP-049 RETIRED: The Methodist Articles (BSR-MW-01) assert no eternal generation, because Wesley omitted the Anglican clause "begotten from everlasting of the Father", so no RNR-H05 true positive exists on that row. TP-049 is retired and replaced by a new RNR-H05 positive on BSR-RP-01, WCF 2.3 ("the Son is eternally begotten of the Father", verbatim and 15 words or fewer), with a new TP id. Fixture tp-5 keeps 60 items and the 0.967 floor. The old phrase becomes documented unstable case U-TP-049, outside the regression set; it never gates a version. N-TP-049 is not created. This supersedes the fixture parts of R6-17.

R6-25 GATE6-V1.7: gate6-v1.6 is not adopted and stays on record as measured and never in force. gate6-v1.7 = v1.6 with the definition of asserted_outside_formula = Y narrowed to cases where the quoted words themselves do not assert the property and the verdict relies on a different sentence. The inference line moves to gate6-v1.8. The outside-formula guard applies to v1.6 and later only.

R6-26 R6-21 AMENDED: A phrase below the floor (3 words / 12 characters) matches no registered creed or definition text and keeps its row's tier. It is a matching rule, not a verifier refusal.

R6-27 R6-22 ENFORCED: A test fails if any row registered as a creed text, by the R6-5 list or any other path, is CATECHETICAL.

R6-28 METHODIST AUDIT: Before any model calls, audit the finished branches for BSR-MW-01 citations on RNR-H05. Stop and report if any is accepted on a card.
