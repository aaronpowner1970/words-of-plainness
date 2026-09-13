# Gate 6 — session 6 report (2026-09-13): the author's four rulings

**Code · workbook v2.25r4 GATE6 SCOPE RATIFIED (unchanged, never written) · run live-1 · packets `recovery-packets/*.json` · extracts `recovery-packets/extracts/` · artifacts `recovery-runs/session6/`, `pr-1/`, `tp-2/`, `tp-3/`**

This session answers `wop-scratch/WoP_SJN_Gate6_Session6_Prompt_20260913.txt` and `WoP_SJN_B4_ReviewAddendum_20260913.md`. Eastern Orthodox did
not run. **Spend: 4.42 USD of the 25 USD cap** (table at the end).

**How the rulings reach the harness.** The workbook is never written, so the rulings are applied in memory from one committed
file, `recovery-runs/author-rulings-pending-workbook.json`, read by `scripts/sjn_recovery/rulings.py` at every start:
`Registry()` retires the rows it names, `load_predicates()` retypes the families it names, `allocation.allocate()` reads the
declared same-text rows, and `agents.finalize()` applies its floor rulings. Once the workbook carries a change, the workbook
value is read instead, and it must agree with the ruling or the start fails. A missing rulings file stops every start
(tested), and `run.py` prints the rulings and prompt versions it applied as its second line. Every packet header now carries
`author_rulings_applied`, so EO cannot launch without the rulings, and a card shows which rulings shaped it.

---

## Ruling 1 — required_subject

### 1a. The delta (`wop-scratch/WoP_SJN_RequiredSubject_Delta_20260913.csv`, 57 rows; `session6/task1a-required-subject-delta.json`)

**There is no required-subject field in the workbook to retype.** Inherited 57 has twelve columns: Predicate ID, Original mode,
Teaching family, Normalized predicate family, Historical source-report definition, Current A/Q/D/U, Teaching lens, floor note,
Coding provenance, Confidence, Historical source record, Source locator. The subject on every card comes from
`registry.subject_scope()`, which infers it from the definition's wording. The delta is therefore a **new column**,
"Required subject", on all 57 rows: 52 keep the harness value and 5 are retyped.

> **Proposed workbook change (author to ratify):** Inherited 57 — add column `Required subject` (57 rows, values in the delta CSV).

| family | old value (harness-derived) | new value | queue cells (open) |
|---|---|---|---|
| RNR-H06 Lord | GOD (the one God, or the Father; not the Church, not humanity, not Christ's human nature) | GOD (the one God: the Father, or the Son or the Holy Spirit where the passage asserts the predicate of that person as divine — e.g. "the Lord, the giver of life" of the Spirit; not the Church, not humanity, not Christ's human nature as such) | Q-041…Q-048 (open: Q-045 AN, Q-047 MW) |
| RNR-H21 Life-giving | same | same, example "the Lord, the giver of life" of the Spirit | Q-161…Q-168 (7 open incl. Q-162 EO) |
| RNR-H26 Judge | same | same, example "to judge the living and the dead" of the Son | Q-201…Q-208 (6 open incl. Q-202 EO) |
| RNR-H27 Savior | same | same, example "for us men and for our salvation" of the Son | Q-209…Q-216 (4 open incl. Q-210 EO) |
| RNR-H38 Not made | same | same, example "begotten, not made" of the Son | Q-297…Q-304 (8 open incl. Q-298 EO) |

The wording of the new value is mine, and it is what the verifier reads: each family carries its own ruling example, and "as
such" keeps a predication about Christ's human nature excluded. Lord has no open EO cell (Q-042 is closed), so the Creed
touches four of the five on EO: Q-162, Q-202, Q-210, Q-298.

### 1b. The 49 re-verified (`session6/task1b-reverify-items.json`, `…-results.json`)

The cell states hold exactly 49, and they match the packets at HEAD (49/49, no strays). Each was re-verified under verifier
gate6-v1.2 with the new subject, by the models that had verified it before (43 sonnet only; 6 sonnet + opus on the reject-all
route). Stored rubrics were moved to `superseded_rubrics`, not deleted.

- **30 now accepted** (19 ACCEPT FULL, 8 ACCEPT_WITH_CAVEAT FULL, 3 ACCEPT_WITH_CAVEAT PARTIAL). **19 still refused:** 17 WRONG_SUBJECT —
  genuinely other subjects ("you", "civil government", "all forms of property", "good works", "regeneration", "all people", "created reason") —
  and 2 BELOW_FLOOR. One of those two is Q-161 RC-01-3, "believing in the Holy Spirit as 'Lord and giver of life'": it now passes
  the subject line, but **IDIOM_OR_FORMULA capped it** ("reproduces the Nicene Creed's fixed title"). See §EO risks.
- **Cells that changed state: none.** All 49 sat on cards that were already filled.
- **Cards that gained a candidate: 11 (17 candidates).**

| branch | card | joined | left the card (cap) |
|---|---|---|---|
| Roman Catholic | Q-297 Not made | RC-06-1 "begotten, not made, of one Being with the Father"; RC-01-1 "begotten not made, consubstantial with the Father" (RC-07-1, identical, recorded as parallel witness) | RC-02-2 (Dei Filius), RC-04-2 (Lateran) |
| Anglican | Q-165 Life-giving | AN-04-1 "The Holy Spirit is revealed in the Old Covenant as the giver of life" | — |
| Anglican | Q-205 Judge | AN-01-1 "until he return to judge all Men at the last day" | AN-04-1 |
| Anglican | Q-213 Savior | AN-01-2 "The Offering of Christ once made is that perfect redemption…" (FULL); AN-01-3 "to reconcile his Father to us" (PARTIAL) | AN-02-2 |
| Lutheran | Q-163 Life-giving | LU-01-1 "the Holy Ghost, the Lord and Giver of life"; LU-02-1 "He will give to the godly and elect eternal life" | — |
| Lutheran | Q-203 Judge | LU-02-1 "Christ will appear for judgment…"; LU-01-2 "He shall come again with glory to judge the quick and the dead" | — |
| Lutheran | Q-211 Savior | LU-01-1 "our only Savior and Redeemer, Jesus Christ" | — |
| Reformed / Presbyterian | Q-212 Savior | RP-01-1 "the Head and Savior of his church"; RP-05-1 "he saves us from our sins" | RP-02-1, RP-03-1 |
| Reformed / Presbyterian | Q-300 Not made | RP-04-1 "begotten, not made, of one Being with the Father" | RP-03-1 |
| Methodist / Wesleyan | Q-207 Judge | MW-02-2 "by him all men will be judged"; MW-03-2 "he return to judge all men at the last day" (PARTIAL; 2c-sampled: opus FULL, disclosure) | MW-04-2 |
| Mennonite / Anabaptist | Q-208 Judge | MA-02-1 "whence He will come again to judge the quick and the dead" | — |

The other 13 accepts did not reach a card (cap or group rule): Q-163 LU-02-2, Q-168 MA-01-3, Q-203 LU-01-3 / LU-02-2, Q-204 RP-06-1,
Q-211 LU-01-3, Q-212 RP-06-1 / RP-05-2 / RP-06-2, Q-300 RP-05-2 / RP-06-2 / RP-05-3, and RC-07-1 as a parallel witness.
**For the author's read.** These accepts test where "as divine" stops and "human nature" starts:
Q-213 AN-01-2 (subject "The Offering of Christ", an act), Q-213 AN-01-3 ("to reconcile his Father to us", Article II's "very
God and very Man"), and Q-163 LU-02-1 (Christ giving eternal life at the judgment). Also Q-300 RP-05-2 "who is and remains
true and eternal God", accepted FULL for *Not made*: that is an inference from eternity, and R6-2 would call it neighbouring.

### 1c. tp-1 re-run — corrected recall **0.983 (59 of 60)**, above 0.93

`tp-2` = the tp-1 fixture under v1.2 with the new subject. 55 calls were identical and served from tp-1's log; only the 5 retyped
items were new. All five recovered: TP-006 "one Lord, Jesus Christ", TP-018 "the Lord, the giver of life", TP-023 "judge the
living and the dead", TP-024 "eternal Savior and Mediator", TP-033 "begotten, not made" (all subject Y, FULL). **The one
remaining miss is TP-060** (Eastern Orthodox, BSR-EO-01, Unbegotten, "God is an eternal Father by nature"): WORD_ONLY / BELOW_FLOOR,
"concerns God's eternal fatherhood relative to the Son, not a denial that God derives from another source".

The **forward verifier** (gate6-v1.3, i.e. R6-1 and R6-2 together; `tp-3`, 60 fresh calls) recalls **0.967 (58/60)**. It also refuses
**TP-059** (EO-02, Unbegotten, "There is only one God because there is only one Father") as "only adjacent claims about oneness and
origin". So both residual misses are **author-ratified EO Unbegotten citations that R6-2's own logic calls neighbouring** — a direct
conflict between two things the author has ratified. No open EO cell is Unbegotten (those citations belong to a released cell), but
EO's open Uncreated (Q-282) and Not made (Q-298) cells are likely to meet the same "one Father / eternal Father" monarchy wording
(a forecast, not measured), and on these two items v1.3 floored that wording at WORD_ONLY. It needs a ruling before EO. IDIOM_OR_FORMULA raised 3 times on tp-3; all 3 still accepted.

### 1d. Eternal power and might (12) and Giver of life (9) — not affected; the cause is grammatical, not typing

Both families are correctly typed THE HOLY SPIRIT, and none of the 21 rejections is a creedal clause refused for its person. Two causes:

| cause | Eternal power and might | Giver of life |
|---|---|---|
| **Compound / triadic subject** — the Spirit predicated jointly with the Father and the Son, or as the one God confessed in three: "the Father is Almighty, the Son Almighty: and the Holy Ghost Almighty" (AN-03, LU-01), "of one substance, power, and eternity" (BA-02), "three Persons, of the same essence and power" (LU-02), "one eternal, almighty… God, the Father, Son, and Holy Ghost" (MA-02), Lateran IV (RC-04) | 6 | 0 |
| **Instrumental / passive agent** — the Spirit in a by-phrase or genitive with another grammatical subject: "renewed by the Holy Spirit", "born anew… by the Spirit", "conceived by the power of the Holy Spirit", "the power of the Holy Spirit dwelling in him" | 6 | 9 |

The verifier is not consistent on the first class. The same Athanasian wording was **accepted FULL** from AN-04 on Q-277 and
**refused** from AN-03. The creedal form itself works when typed correctly: Reformed Q-268 accepted "We believe in the Holy
Spirit, the Lord, the giver of life" at FULL. **Question for the author before EO** (Q-274 Eternal power and might is an open
EO cell): does a predication of the three persons jointly, or of the one God confessed as Father, Son and Holy Spirit, satisfy a
Spirit-typed family? The Byzantine liturgies are full of "the consubstantial and undivided Trinity". Passive agency is a second,
separate question.

---

## Ruling 2 — the hedged PARTIAL

### 2a. Sample (`scripts/sjn_recovery/partial_rule.py`; `recovery-runs/pr-1/sample.json`, `report.json`, `report.txt`)

- **Seed 20260913.** Frame: the carded PARTIAL candidates in the packets at HEAD. I reproduce the addendum's **145 exactly**
  (RC 20, AN 25, LU 21, RP 11, BA 21, MW 22, MA 25), then exclude the 5 candidates of Q-382/Q-390/Q-454, leaving **140**.
- Stratified: 5 each from the two largest frames (Anglican, Mennonite), 4 from each other branch, making 30. Within a branch
  the order is sha256(seed|candidate_id); the draw is round-robin over branches, preferring families not yet drawn (28
  families across the 30).
- **Instrument:** sonnet only, verifier **gate6-v1.3**. Line 4 states the rule without naming any predicate, and a new
  companion line `partial_asserts_predicate` Y/N means PARTIAL with N is capped at WORD_ONLY in code. Each item is judged on
  its stored chunk under the subject its card carried, so R6-1 cannot confound it.
- **Classification from the rubric lines, not a regex:** LEAK means lines 1–3 are Y and the re-ruled floor is WORD_ONLY (not
  the formula cap).
- **Control:** a fresh gate6-v1.2 replicate of every item (identical prompt, distinct call identity), so the rule's effect can be
  separated from redraw noise. This was not asked for. I added it because the result sat on the threshold.

### 2b. Measured leak rate — three figures, ranked, each with its weakness

| figure | count | rate | definition | weakness |
|---|---:|---:|---|---|
| **A — floor leak (the decision figure)** | **14** | **0.467** | lines 1–3 Y, re-ruled WORD_ONLY under v1.3 | one draw of one model; includes redraw noise |
| B — inclusive | 17 | 0.567 | A plus line-2/3 refusals that also floor WORD_ONLY (outside the R6-1 families) | mixes a subject refusal into a floor rate |
| C — rule effect net of noise | 11 | 0.367 | A, and the v1.2 replicate still accepts | one replicate per item |

**A is below 0.5, so per the ruling the rule was applied to nothing but the three Baptist cells.** I don't think the threshold
can bear that weight. On n = 30 the 95% interval around 0.467 runs from about 0.29 to 0.65, and one item decides the side
(15 of 30 = 0.5). Read plainly: roughly a third to a half of carded PARTIALs are neighbouring propositions under the rule.
That is far more than three bad calls and fewer than the 113. Stratified to the frame, A estimates about **65 of 140** and C
about **51**. Re-ruling the remaining 110 would cost about 3.3 USD with `partial_rule.py frame / verify / apply`, ready to run
on your word.

**The 14 leaks** (none capped — the rule was not applied beyond the three cells):
PR-05 MW Q-287 Uncreated "Eternal Spirit, who is Creator, Sovereign and Preserver…" · PR-07 RC Q-273 Eternal power "He is God, one and equal
with the Father and the Son" · PR-08 AN Q-317 Immense "without body, parts, or passions" · PR-09 BA Q-102 Truthful "one only living and true God"
(v1.2 replicate also WORD_ONLY: different sense) · PR-10 LU Q-419 Without change "two natures… inseparably enjoined" · PR-11 MA Q-416 Without
confusion "Jesus Christ has both a human and a divine nature" · PR-13 RP Q-300 Not made "in and of himself infinite in being…" · PR-14 RC
Q-193 Sovereign "one principle of all things, creator…" · PR-15 AN Q-453 Greater dissimilarity "The Father incomprehensible, the Son
incomprehensible…" (replicate also WORD_ONLY) · PR-16 BA Q-158 Glorious "for His own glory" · PR-17 LU Q-379 Ineffable "of His pure unutterable
love" · PR-21 RC Q-257 Image of the Father "God from God, Light from Light…" · PR-26 MW Q-167 Life-giving "He works within us to quicken…" ·
PR-27 RP Q-404 No adequate likeness "God's power and goodness are so great and incomprehensible".

**The addendum's regex, measured against A:** 22 of the 30 are hedge-shaped (by my reconstruction of the pattern; it finds 110
of 145 at HEAD against the addendum's 113). Precision is **0.50**: 11 of the 22 hedge-shaped items hold, which are the false
positives PR-02, 03, 06, 12, 20, 22, 23, 24, 25, 29, 30. Recall is **0.79**: it misses 3 leaks, the false negatives PR-09, PR-10,
PR-21. So 113 is not an upper bound either. It over-captures and under-captures at once.

**The discriminating feature.** A PARTIAL holds when the passage predicates **the predicate's own attribute of God in narrower
scope**: "the name of God is in itself holy", "righteously opposing all sin and evil", "faithfully remains with us". It leaks
when the predicate is reached **only by inference from a different attribute**: creatorship for sovereignty, aseity for *not made*,
equality for power, union for *without change*, "unutterable love" for an ineffable God. v1.3 applies that line
**inconsistently on inference cases**. It held 3 of them (PR-18, PR-20, PR-30). **PR-18 (Mennonite Q-392 Inscrutable on "one
eternal, almighty, and incomprehensible God") held on both draws. That is exactly the shape of Q-390, which you refused.** The
forward verifier does not yet reproduce your own example. If you want it to, the line to add is: "a proposition from which
the predicate can be inferred is neighbouring, not PARTIAL". That would be gate6-v1.4, and it should be re-measured on these
30 plus tp-1 before EO (about 1.7 USD). I have not done this; it is your call.

### 2c. Q-382, Q-390, Q-454 refused — Baptist **30 of 37** filled

All five of their candidates carry a floor ruling (`floor_rulings: AUTHOR_RULING_R6-2`, WORD_ONLY), which `agents.finalize`
applies as a lower floor on every rebuild. The stored rubrics are untouched, and a ruling cap is not counted as an opus overturn.
All three cells now render **NOT LOCATED — CURRENT STANDARD REVIEWED**, offered: BA-01, BA-02 and BA-03 were each read whole.
Baptist: 30 filled, 7 empty, REVIEWED offered on 7.

**Forward.** Verifier **gate6-v1.3** is now the verifier in force, and the finished branches keep their stored rubrics. Locator
**gate6-v1.5**: rule 4 of the v1.4 locator prompt defined PARTIAL as "a narrower **or adjacent** proposition". That line told the
locator to propose exactly what R6-2 refuses, and it is now removed. It is plausibly where the leak started.

---

## Ruling 3 — BSR-EO-03 retired

### 3a. Delta (`wop-scratch/WoP_SJN_BranchSourceRegistries_Draft3r5_20260913.csv` = Draft3r4 + `r5_change` / `r5_change_note`; `session6/task3-eo03-retirement.json`)

> **Proposed workbook change (author to ratify):** Branch Source Registry, BSR-EO-03: `status` AUTHOR_RATIFIED → **RETIRED**; `author_decision` APPROVE → EXCLUDE; `reason_code` '' → **HOST_RETIRED**; `author_note` → "Retired 2026-09-13 (session 6, R6-3): goarch.org is a retired registry host (its bot check fails for human users, so a citation there cannot be audited); the row has no text, and under the session-5 NO TEXT rule a citable ratified row with no text blocks the REVIEWED offer on every Eastern Orthodox cell. Recorded as a host fact and its consequence, not as a judgment about the source. GOARCH's rite remains in the branch through BSR-EO-07 (and BSR-EO-14)."; `decision_date` → 2026-09-13.

HOST_RETIRED is a new value in that column; the existing RETIRED rows carry OTHER and WRONG_SUBJECT. EXCLUDE follows their pattern.

### 3b. The corpus store, not the audit

Instrument: the chunk files and `corpus-manifest.json`, read directly for every EO row, plus a wrapper/challenge scan (javascript,
captcha, "checking your browser", cloudflare, access denied, raw markup).

| row | status now | manifest | chunks | chars | markers | first words of the store |
|---|---|---|---:|---:|---|---|
| EO-01 | ratified | UNCHANGED | 19 | 158,964 | none | "The Nicene Creed should be called the Nicene-Constantinopolitan Creed…" |
| EO-02 | ratified | UNCHANGED | 14 | 21,890 | none | "The doctrine of the Holy Trinity is not merely an 'article of faith'…" |
| **EO-03** | **RETIRED (ruling)** | HOST_RETIRED | 0 | 0 | — | — |
| EO-04 | ratified | UNCHANGED | 610 | 197,945 | none | "1. What is an Orthodox Catechism?…" |
| EO-05 | ratified | UNCHANGED | 22 | 61,866 | none | "We believe in one God, true, almighty and infinite…" |
| EO-06 | ratified | UNCHANGED | 20 | 17,974 | none | "The holy, great, and ecumenical synod…" |
| EO-07 | ratified | UNCHANGED | 25 | 38,174 | none | "Priest: In peace let us pray to the Lord…" |
| EO-08 | ratified | REBUILT (drift accepted) | 16 | 22,314 | none | "PRAYERS OF THE LITURGY OF ST. BASIL…" |
| EO-09 | ratified | UNCHANGED | 6 | 5,698 | none | "Who is so great a God as our God?…" |
| EO-10 | ratified | UNCHANGED | 45 | 50,969 | none | "The Orthodox Church, as the One, Holy, Catholic…" |
| EO-11 | ratified | UNCHANGED | 2 | 1,637 | none | "Although the Newborn is a human being…" |
| EO-12 | ratified | UNCHANGED | 12 | 1,100 | none | "Πιστεύω εἰς ἕνα Θεόν, Πατέρα, Παντοκράτορα…" |
| EO-13 | ratified | UNCHANGED | 10 | 10,063 | none | "The holy, great, and Ecumenical Synod…" |
| EO-14 | ratified | UNCHANGED | 19 | 33,504 | none | "Priest: In peace let us pray to the Lord…" |

**No other EO row is in EO-03's state.** All 13 have text and none is a wrapper. As a check, `packets.no_text_rows` on a
hypothetical EO cell covering every citable row returns nothing and offers REVIEWED.

### 3c. EO now has 13 ratified rows, all citable. Tier A in the EO prompt is unchanged; Tier B is five rows.

Cost effect of the retirement: **0 USD**. EO-03 never had a corpus, so it never cost a locator call. What the retirement changes
is the REVIEWED offer, not the spend.

---

## Ruling 4 — one text, one slot

**Guard** (`allocation.same_text_key`, `allocation.allocate` step 5). Walking the slot order, a phrase whose NFKC-casefolded
text, with every punctuation and symbol character removed and whitespace collapsed, equals a **seated** phrase takes no slot,
whatever its row or group. It is recorded on the seated entry as `same_text_parallel_witnesses`, carrying its own registry_id,
speaks_for, locator and verdict. Parallel witnesses are recorded even after the cap fills.

### 4a/4b. At build time across the seven branches (the guard alone against HEAD: `session6/step1-r4-card-diff.json`)

**28 cards, 34 parallel witnesses, 20 slots freed.** It reaches much further than Lutheran, and most of it is **not two hosts
of one translation**. It is different bodies subscribing the same wording: Westminster in OPC (RP-01/02/03) and in the PC(USA)
Book of Confessions (RP-04); the Athanasian Creed in AN-03 and AN-04; the UMC and EUB articles (MW-02/MW-03). Your rationale
("two hosts of one translation are one witness") covers LU-01/LU-02. The rule as you worded it ("regardless of speaks_for
group") covers these too, and I applied it as worded. **Please confirm** that, for example, PC(USA)'s adoption of Westminster's
sentence is a parallel witness and not a slot.

| branch | card | slots freed | what took the freed slot | parallel witness (of seated) |
|---|---|---:|---|---|
| Anglican | Q-157 Glorious | 1 | — (no other survivor) | AN-04-1 of AN-03-1 |
| Anglican | Q-285 Uncreated | 1 | AN-03-2 "but one uncreated, and one incomprehensible" | AN-03-1 of AN-04-1 ¹ |
| Anglican | Q-365 Eternal | 1 | AN-03-2 "And yet they are not three eternals: but one eternal" | AN-03-1 of AN-04-1 |
| Anglican | Q-373 Incomprehensible | 1 | AN-04-2 "but one uncreated, and one incomprehensible" | AN-04-1 of AN-03-1 |
| Anglican | Q-445 Neither confounding nor dividing | 1 | — | AN-03-1 of AN-04-1 |
| Lutheran | Q-123 Gracious | 0 | — | LU-01-2 of LU-02-1 |
| Lutheran | **Q-179** Preserver / Sustainer | 1 | LU-03-2 "He defends me against all danger…" | LU-02-1 of LU-01-1 |
| Lutheran | **Q-227** Fountain of being | 1 | LU-01-2 "Maker of heaven and earth, and of all things visible and invisible" | LU-02-1 of LU-01-1 |
| Lutheran | **Q-235** Word / Logos | 1 | — | LU-02-1 of LU-01-1 |
| Lutheran | **Q-243** Wisdom | 1 | — | **LU-01-2 of LU-01-1 (one row twice)** |
| Reformed / Presbyterian | Q-004 Living | 1 | RP-04-2 "living, quickening and preserving all things…" | RP-04-1 of RP-01-1; RP-03-1 and RP-04-3 of RP-02-1 |
| Reformed / Presbyterian | Q-012 True | 0 | — | RP-02-1, RP-03-1 of RP-04-1 |
| Reformed / Presbyterian | Q-204 Judge | 0 | — | RP-01-2 of RP-04-1 |
| Reformed / Presbyterian | Q-284 Uncreated | 0 | — | RP-04-2 of RP-01-1 |
| Reformed / Presbyterian | Q-412 / Q-420 / Q-428 / Q-436 (the four Chalcedonian adverbs) | 1 each | RP-02-1 "God and man in two distinct natures, and one person, forever" | RP-04-1 of RP-01-1 (each) |
| Methodist / Wesleyan | Q-023 Spirit | 1 | — | MW-03-1 of MW-02-1 |
| Methodist / Wesleyan | Q-031 Father | 0 | — | MW-03-2 of MW-01-1; MW-02-1 of MW-03-1 |
| Methodist / Wesleyan | Q-047 Lord | 1 | — | MW-03-1 of MW-02-1 |
| Methodist / Wesleyan | Q-167 Life-giving | 1 | MW-03-2 "he doth work invisibly in us, and doth not only quicken" | MW-03-1 of MW-02-1 |
| Methodist / Wesleyan | Q-231 Fountain of being | 1 | MW-02-1 "who is Creator, Sovereign and Preserver…" | MW-03-1 of MW-01-1; MW-03-2 of MW-02-1 |
| Methodist / Wesleyan | Q-239 Word / Logos | 1 | MW-03-2 "He is the eternal Word made flesh…" | MW-03-1 of MW-01-1 |
| Methodist / Wesleyan | Q-287 Uncreated | 1 | MW-01-2 "There is but one living and true God, everlasting" | MW-03-1 of MW-02-1 ¹ |
| Methodist / Wesleyan | Q-431 / Q-439 / Q-447 | 0 | — | MW-03-2 (and MW-02-1 on Q-447) |

¹ After the floor-claim defect fix (below), Q-285 seats AN-03-1 with AN-04-1 as its parallel, and Q-287 seats MW-03-1 with MW-02-1
as its parallel. The pair is the same; which one holds the slot follows the ratified FULL-before-PARTIAL order.
Final packets: parallel witnesses on AN 5 cards, LU 5, RP 9 (11 witnesses), MW 13, RC 1 (Q-297, from R6-1). Baptist and
Mennonite have none. The run log's candidate IDs above are `Q-nnn-p1-<row>-n`.

### 4c. EO-07 and EO-14 — the textual guard does not see one rite in two translations

Instrument: every clause of both stored corpora keyed by the guard's own `same_text_key`, and every 5-to-15-word window of EO-07
tested against EO-14 (`session6/task4c-eo07-eo14.json`).

- **28 of 341 EO-07 clauses (8.2%) are textually identical in EO-14**, and 8.5% of phrase windows. They are the acclamations and
  responses ("And with your spirit", "Hosanna in the highest") and the Creed's first article.
- **The clauses that matter differ:** "begotten not made" appears only in EO-07; "to judge the living and the dead" only in EO-07
  (EO-14: "to judge the living and dead"); "the Lord and Giver of Life" (EO-07) vs "the Lord, the Creator of life" (EO-14);
  "inconceivable" / "incomprehensible" / "unchangeable" only in EO-07; "beyond comprehension" / "beyond understanding" / "of one
  essence with the Father" only in EO-14.
- On a card where both survive with different wording, **the textual guard seats both**.

So I added the case your EO prompt (Task 2d) describes, as a **declared** relation rather than string equality:
`rulings.same_text_rows = {BSR-EO-14: BSR-EO-07}`. The evidence is EO-14's reception_note ("Registered alongside BSR-EO-07…
WORDING DIFFERS") and its draft_recommendation ("the durable alternate to BSR-EO-07"). While EO-07 has a live candidate, EO-14's
candidates are held out of the slot order. If an EO-07 candidate is seated, EO-14's become its parallel witnesses
(`rule SAME_TEXT_ROW`) whatever the wording or order. If EO-07 seats nothing, EO-14 competes normally. Tested both ways. **The
pair is pending your confirmation** in the rulings file.

---

## Defects found and fixed on the way (each diffed separately from the rulings)

1. **The packet builder never passed `floor_claim` to the allocator.** Entries carried it as `locator_floor_claim`, so every
   packet ranked groups for their first slot by registry row alone and dropped the ratified FULL-before-PARTIAL key. The cell
   runner (which the coder follows) did apply it, so **8 of 247 cards differed** from what the coder was allocated. That explains
   the "not coded" notes on older cards. Fixed and tested; `session6/step3-floorclaim-card-diff.json`. Membership changed on RC
   Q-193; AN Q-197, Q-285, Q-301, Q-437; RP Q-420; MW Q-287; MA Q-288. Leads were reordered on a handful more.
2. **A verifier reply cut off before its `floor` line was scored ACCEPT.** `parse_json` salvaged the partial object and a
   missing floor fell through to ACCEPT. Two carded live-1 candidates had this (Q-081 RC-01-1, Q-099 LU-01-3), plus one rejection
   (Q-115) and PR-17 in this session's sample. Now a reply missing any rubric line takes the ceiling retry, a floorless rubric is
   REJECT/UNPARSEABLE, and all four were re-verified. **Q-081 still accepted (FULL). Q-099 LU-01-3 "spoken by that Lord who is
   infinite Wisdom and Truth itself" is now REJECT WRONG_SUBJECT** (said of Christ; Truthful stays typed GOD) and left its card.
3. **Re-entering `run.py` on a finished branch does more than finish cards.** I ran it once per branch to get the coder onto new
   card entries, dry-running before spend as the standing practice requires. It re-opened **Q-380's stopped exhaustion** (13 batches
   over BSR-RP-04), sent **4 old Roman Catholic caveated accepts** to the 2c sample, and on Anglican **entered exhaustion for the
   first time and crashed on the URL guard** at a BSR-AN-05 chunk (Q.368, a citation with `<http://`). That wrote a PARTIAL
   anglican.json and set cost-state to RUN_FAILED. **No job was answered.** I restored every cell state from git, removed the 40
   unanswered jobs (`live-1` now has 0 pending, so the EO launch cannot pick them up), reset Anglican to DONE with a note, and
   replayed the session's re-verifications from the audit log at zero cost (identical, byte for byte). The 42 card entries without
   a coder proposal (30 that joined cards this session, 12 older backlog) were then coded by `session6/finish_coder.py`, which
   calls nothing but the coder and the 2c sample on this session's new verdicts (1 opus call). The reverted logs are kept as
   `session6/step2-REVERTED-loop-*.out`. The URL-scrub miss is the only such chunk in the whole corpus; every EO chunk is clean.

---

## Refreshed review extracts

All seven branches were rebuilt, and every extract was rewritten with the packet (`recovery-packets/extracts/*-extract.json`). The
extract header now carries `same_text_guard`
and `author_rulings_applied`; each candidate carries `parallel_witnesses`.

| branch | cells | filled | empty | REVIEWED offered | review incomplete | all-rejected |
|---|---:|---:|---:|---:|---:|---:|
| Roman Catholic | 34 | 34 | 0 | 0 | 0 | 0 |
| Anglican | 43 | 38 | 5 | 0 | 5 | 1 |
| Lutheran | 39 | 34 | 5 | 5 | 0 | 3 |
| Reformed / Presbyterian | 16 | 15 | 1 | 0 | 1 | 1 |
| **Baptist** | 37 | **30** (was 33) | **7** | **7** | 0 | 3 |
| Methodist / Wesleyan | 37 | 22 | 15 | 15 | 0 | 0 |
| Mennonite / Anabaptist | 41 | 31 | 10 | 10 | 0 | 4 |

---

## Spend against the 25 USD cap (metered, audit logs; `session6/spend.json`)

| ruling | what | calls | USD |
|---|---|---:|---:|
| 1 | 49 re-verifications (43 sonnet, 6 sonnet+opus) + 3 truncated-reply re-verifications | 52 sonnet + 6 opus | 1.54 |
| 1 | tp-2 (5 new calls; 55 served from tp-1) | 5 | 0.05 |
| 2 | 30-item sample under v1.3 (+1 ceiling retry) | 31 | 0.93 |
| 2 | v1.2 replicate control (not asked; added at the threshold) | 30 | 0.68 |
| 2 | tp-3, the forward verifier's recall | 60 | 0.76 |
| 3 | — | 0 | 0.00 |
| 4 + card completion | coder on 42 card entries; 1 2c disclosure sample (opus) | 42 + 1 | 0.46 |
| | **session** | **227** | **4.42** |

The 2a estimate of about 0.50 USD became 0.93: v1.3 replies are longer (mean 0.030 USD per call against 0.023 for v1.2 on the same items).

---

## Eastern Orthodox estimate, restated after the retirement

Inputs (`session6/eo-estimate-inputs.json`) are the **actual** per-row locator input for all 44 EO cells, from
`retrieval.select_for_standard` with no model calls, and **measured** rates from the live-1 audit log: locator 0.00143 USD per 1,000
input characters; Reformed (the six-standard analogue) sonnet verifier 0.020 and opus 0.022 USD per standard-cell; v1.3 ×1.32; coder
about 0.045 per cell.

| component | basis | USD |
|---|---|---:|
| Tier A locator, every cell | EO-01 54.4k (sampled of 159k), EO-06 18.0k, EO-12 1.1k, EO-07 38.2k, EO-08 22.3k, EO-09 5.7k = 139.6k chars → 0.200/cell × 44 | 8.8 |
| Tier A verify + opus | 6 standards × (0.026 + 0.022–0.035) × 44 | 12.8–16.1 |
| Tier B, entered cells | EO-14 33.5k, EO-02 21.9k, EO-04 59.7k (sampled of 197k), EO-10 50.9k, EO-05 58.6k (sampled of 62k) = 224.6k → 0.321 + 5 × (0.048–0.061); × 18–30 cells | 10.1–18.9 |
| exhaustion | remaining EO-01 104k + EO-04 138k + EO-05 3k chars ≈ 0.35 locator + ~0.1 verify per empty; × 8–14 empties | 3.6–6.3 |
| coder, recuts | | 2.3 |
| **total** | | **≈ 38–52 (central ≈ 45)** |

This sits inside the EO prompt's 45–65 ladder estimate at its low end, below my earlier flat 55–65, and well below 90–110. The
dominant uncertainties are how many cells enter Tier B, and the opus volume from the slice rows (EO-09 in Tier A; EO-04 and
EO-05 in Tier B). R6-2 pushes the empty count and Tier B entry up. R6-1 pulls four Creed-family cells (Q-162, Q-202, Q-210,
Q-298) toward a Tier A fill.

**The 10-cell checkpoint will under-project if read straight.** In queue order the first 10 EO cells are all kataphatic (Q-002
Living … Q-114 Merciful). The 16 apophatic, delimiter and meta-apophatic cells, which is where Tier B, exhaustion and R6-2 fall,
are the last 16. Expect about 0.5–0.6 USD per cell at the checkpoint (≈ 24 USD if multiplied by 44). The honest projection is
28 × (first-10 rate) + 16 × (first-10 rate + about 1.0). Either read the checkpoint that way, or draw the first 10 stratified
(6 kataphatic, 4 not).

---

## EO launch readiness — what the rulings did not settle

1. **The NO TEXT rule does not know about the ladder.** `packets.no_text_rows` reads every citable ratified row a cell's coverage
   lacks as "NO TEXT — the cell ran before this standard had a corpus". On a Tier-A-only EO card it lists **EO-02, EO-04, EO-05,
   EO-10, EO-11, EO-13 and EO-14 as NO TEXT** (verified on a hypothetical card). That is false for filled cards. For an empty
   cell after Tiers A and B, the Tier C rows **EO-11 and EO-13 would block REVIEWED on every EO empty**, which is exactly what
   retiring EO-03 was meant to prevent. EO prompt 1b says the refusals apply "unchanged"; unchanged, they misfire. The EO
   session's ladder must record "NOT CONSULTED (ladder tier)" and exclude Tier C from the REVIEWED test.
2. **IDIOM_OR_FORMULA can cap the Creed.** Q-161 RC-01-3 passed the new subject line and was capped because the verifier called
   "Lord and giver of life" a fixed title. EO-07 and EO-14 recite the Creed inside the liturgy. The flag's definition turns on
   "the passage's actual assertion lies elsewhere", which is not true of a creed, but the verifier applied it anyway once. Worth a
   one-line ruling: a creed confessed within a liturgy is not a liturgical formula for this flag.
3. **The ratified EO Unbegotten citations conflict with R6-2** (TP-059, TP-060; see 1c).
4. **Compound-subject predication for Spirit-typed families** (see 1d).
5. **EO-01 is typed CONCILIAR, but its 19 stored chunks are Hopko's OCA exposition** ("The Nicene Creed should be called…"), which
   quotes the Creed. Creed resolution will treat exposition sentences on those pages as conciliar. EO-02 is the same volume,
   typed CATECHETICAL.
6. v1.3 does not reproduce the Q-390 refusal on PR-18's shape (2b).

## Where the addendum is wrong (with the artifact)

1. **§3.2 "The workbook already types subjects per predicate (183 cards GOD/Father, 27 CHRIST, 22 THE SON, 11 THE HOLY SPIRIT, 4 GOD AS
   TRINITY)."** The card counts are right: 247 cards, as the harness types them. **The workbook types nothing.** Inherited 57 has
   no subject column (its twelve columns are listed in `session6/task1a-required-subject-delta.json`); the typing is
   `registry.subject_scope()` in code. So "a typing question on specific families, not a missing field" has it backwards: it is
   a missing field whose derived values are wrong on five families. The proposed change adds the column.
2. **§2 "Treat 113 as an upper bound."** It is not a bound of any kind. Measured on the sample, the hedge regex has precision 0.50 and
   **misses 3 of 14 leaks** (PR-09, PR-10, PR-21, none of which is hedge-shaped). 34 "cells that would empty" inherits the same
   instrument; I did not reproduce it (my reconstruction of the pattern gives 110 and 32).
3. **§3.1 / Ruling 4 "Two hosts of one translation are one witness."** True of LU-01/LU-02, but it is not what most of the guard's 28
   cards are. They are separate bodies' adoptions of shared confessional wording (Westminster in OPC and PC(USA); the Athanasian
   Creed in two Anglican rows; UMC/EUB articles). The rule's words cover them; its stated reason does not. Confirm the scope.
4. **Ruling 2's decision rule** asks n = 30 to separate 0.467 from 0.5; it cannot (2b).
5. **EO prompt Task 3c** (the ten-cell checkpoint) is biased by queue order, and **Task 1b**'s "unchanged" NO TEXT refusal misfires under
   the ladder (above). Both are in the EO prompt, not the addendum, but both are load-bearing for the launch.

## Open for the author

1. Ratify: the `Required subject` column (1a); the Draft3r5 EO-03 retirement (3a); the declared pair BSR-EO-14 → BSR-EO-07 (4c);
   the scope of the same-text guard beyond two-host cases (4b).
2. Rule: v1.3 as it stands, or v1.4 "an inferable proposition is neighbouring" (re-measure first); and whether to apply R6-2 to the
   remaining 110 carded PARTIALs (about 3.3 USD) given 0.37–0.57.
3. Rule before EO: the Unbegotten conflict (TP-059/TP-060), compound Spirit predication (1d), and the Creed under IDIOM_OR_FORMULA.
4. Read: the "as divine" boundary accepts (Q-213 AN-01-2/-3, Q-163 LU-02-1, Q-300 RP-05-2) and Q-099's lost candidate.
5. EO session: the ladder must teach `no_text_rows` about unconsulted rows; read the checkpoint by mode.
6. Still open from sessions 4–5: the reject-all exemption question, the four derived translation pairs, the Draft3r4 URL
   ratifications (BSR-BA-02, BSR-LU-02).
