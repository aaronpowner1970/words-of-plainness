# SJN Gate 6 — Calibration report (cal-2)

Workbook Seeking_Jesus_Teaching_Predicate_Source_v2.23_REGISTRY_CORRECTIONS_20260910.xlsx (v2.23 REGISTRY CORRECTIONS) · prompt version gate6-v1.1 · locator model `sonnet` · verifier models `sonnet`, `opus` · backend batch · generated 2026-09-11 22:21 UTC

Locators hidden: the agents received predicate, definition, floor note, subject scope and registry chunks only — never the workbook's document, locator or phrase. False-accept = verifier ACCEPT or ACCEPT_WITH_CAVEAT on a planted near-miss. Thresholds: recall ≥ 0.8, false-accept ≤ 0.05 (Dositheus slice held to 0.05 on its own). Thresholds were not moved.

### The three recall metrics

| metric | a verified candidate counts as a hit when it sits… | role |
|---|---|---|
| same-division | in the same registry standard AND the same division the released cell cites | diagnostic |
| same-standard | in the same registry standard the released cell cites | diagnostic, kept in the table |
| **tier-respecting** | in the same registry standard, **or** in a different ratified standard of the correct branch whose `authority_tier` is equal to or higher than the tier of the cited standard | **the threshold metric** |

A substitution into a LOWER tier is a **partial**. It is not credited and is reported in its own column.

**AUTHOR RATIFIED 2026-09-11 (AJP)** — `authority_tier` is a genuine authority rank, descending:

`CONCILIAR > CONFESSIONAL > CATECHETICAL > OFFICIAL_EXPOSITION > CURRENT_OFFICIAL_WITNESS`

Used as given, not re-derived from the workbook. Ranking is on the **bare tier**: the parenthetical qualifiers on BSR-RC-03 (`CONCILIAR (translation)`), BSR-EO-04 (`CATECHETICAL (historic)`) and BSR-BA-02 (`CONFESSIONAL (voluntary church-level subscription)`) are disclosure, not rank. The rank is proposed to Gate 7 as the APP CONFIG key `authority_tier_rank` in `recovery-runs/proposed-app-config-gate7.md`. **Nothing in Gate 6 writes to the workbook.**

## What changed since cal-1

cal-1 is kept intact beside this report at `recovery-runs/cal-1/`. cal-2 re-ran the 105 cells whose supplied chunk set changed under the retrieval fixes below; the other 43 were carried over unchanged from cal-1's answered calls and cost nothing.

### Retrieval — the dominant cal-1 defect

cal-1's largest residue was `LOCATOR_EMPTY`: 10 cells per model where the locator was handed the correct standard and still found nothing. Three separate faults, all in the harness:

1. **The query was swamped by the floor note.** `query_text()` weighted the predicate term, its definition and the floor note equally. The floor note is analytic prose about the coding decision, so ranking favoured long scholastic discussion over the terse creedal assertion that is the actual evidence. The predicate term is now weighted three times.
2. **No lexical guarantee.** Nothing ensured that chunks literally using the predicate's own vocabulary reached the locator. 70% of each standard's character allowance is now reserved for them, ranked among themselves on the predicate term alone. Blending that with the general ranking (RRF) was measurably worse and was rejected.
3. **Composite volumes swallowed their own allowance.** BSR-LU-01 is the whole Book of Concord (738 chunks) and BSR-RP-04 the whole Book of Confessions (1,018). A flat ranking let the longest constituent book take every slot: the three Ecumenical Creeds are 3 chunks of BSR-LU-01's 738 and never surfaced. The allowance is now allocated round-robin across the constituent works read off each chunk's own locator, so every constituent is represented. For a flat text such as the Catechism, where each chunk is its own division, this degenerates to plain rank order and changes nothing.

4. **Function words drove the lexical slice.** The slice admitted a chunk on any predicate word of four letters or more, and “without” appears in 48% of the Book of Concord and 55% of the Confession of Dositheus. Terms above a 35% document frequency within a standard are now dropped for that standard, keeping the rarest if all are above it. This swapped out 10 to 11 noise chunks each for Q-331 and Q-339, the two “without” cases in the Book of Concord.

`LOCATOR_EMPTY` fell from 10 per model to 6.

These changes are not uniformly positive, and the report does not claim they are. Measured cell by cell against cal-1, 9 cells gained a tier-respecting hit and 8 lost one, for a net of +1 before the frequency ceiling was added. Every one of the 8 losses was checked individually: in all 8 the division the released cell cites was supplied to the locator in both runs, so none was a retrieval regression. Six found evidence in a lower-tier standard instead and scored as partials; four returned nothing while the correct article sat in the supplied context. Those are locator judgment, not harness defects, and they are the honest cost of the sampling.

### Q-363 — the Athanasian Creed (step 4)

The creeds **are** in BSR-LU-01's indexed corpus, so this was never a splitter coverage gap. It was fault 3 above. The Athanasian Creed ranked 260th of 738 on the cal-1 query and was never supplied; under the division round robin it arrives at slot 6. The locator now returns the workbook's own passage — *“The Father eternal, the Son eternal, and the Holy Ghost eternal”* — and both verifiers accept it.

### Eastern Orthodox zero-chunk exposure (step 4)

**0 of the 10 Eastern Orthodox released cells cite a row that yielded zero chunks.** Only BSR-EO-03 has zero chunks (`FETCH_BLOCKED`, Cloudflare) and no released cell cites it. An earlier reading of cal-1 attributed the Eastern Orthodox recall gap to that block; that was wrong and is corrected here. The Eastern Orthodox gap is a tier effect: the branch's conciliar row BSR-EO-06 holds 2 chunks of OCA *Church History* summary prose rather than the conciliar definitions, so evidence is recovered from lower-tier rows and scores as a partial.

### BSR-EO-04 accepted drift (step 3)

| | chunks | characters | `text_hash` |
|---|---|---|---|
| before | 305 | 197,641 | `2248097d27346f7b…9de2b21c` |
| after | 610 | 197,336 | `9277b1dc0eb3ad01…e9baf6a6` |

The character count moved by 305 of 197,641 (0.15%) while the chunk count doubled, which is the signature of a boundary change rather than a content change: the same text, cut in twice as many places. The page changes shape partway through — questions 1–306 lead with a `<p>` carrying “N. text”, from 307 they move into `<b>` with the text inline — and the earlier splitter recognised only one shape, so it merged question pairs across most of the document. The **gap-tolerance fix** (accepting a question number up to three ahead of the expected one) had raised the count from 287 to 305 by letting the walk survive the numbers the page omits; it did not address the tag change. Splitting is now driven by the question sequence rather than tag shape, which recovers 610 of the catechism's 611 questions. Philaret is the branch's largest corpus, so this materially widened what the Eastern Orthodox locator could see.

### Skipped cells (step 3)

cal-1 skipped 9 cells for `sonnet` and 6 for `opus` while `corpus unavailable` read 0. Every one was the same artifact, per cell: a verifier reply truncated at the token ceiling or returned with no text block at all, recorded `UNPARSEABLE` and then treated as terminal so it was never retried. The corpus was never the problem, which is why `corpus unavailable` read 0. Three cells — Q-048, Q-215 and Q-363 — had the same failure in the **locator** pass: an empty reply banked as a genuine empty result. All were re-run for cal-2 and the per-cell table below now shows 0 skipped for both models.

### Fixed and re-run (step 5)

| fix | where | effect |
|---|---|---|
| Predicate term weighted 3x in the retrieval query | `retrieval.py` `query_text` | ranking follows the predicate, not the floor note |
| Lexical slice: 70% of the allowance reserved for chunks using the predicate's vocabulary | `retrieval.py` `select_chunks` | Book of Concord supply went from 13 chunks, almost none using the term, to 28 of which 27 do |
| Document-frequency ceiling of 35% on slice terms | `retrieval.py` `discriminating_terms` | “without” no longer admits half the Book of Concord |
| Division round robin across a composite volume's constituent works | `retrieval.py` `division_of`, `round_robin` | the Ecumenical Creeds reach the locator; Q-363 recovered |
| Philaret split by question sequence rather than tag shape | `sources.py` `philaret` | BSR-EO-04 305 -> 610 chunks |
| `UNPARSEABLE` made retryable at both locator and verifier | `agents.py` | 15 skipped cells recovered; 0 skipped in cal-2 |
| Empty-reply guard: a reply with no text block is retried with a larger ceiling | `api_executor.py` | no more empty answers banked as forced REJECT |

### Not fixable without an author call

| row | state | why it is not a Gate 6 defect |
|---|---|---|
| BSR-EO-03 | `FETCH_BLOCKED` (Cloudflare), 0 chunks | No released cell cites it; no recall effect measured. |
| BSR-MW-03 | `UNAVAILABLE_ON_RATIFIED_DOMAIN`, 404 | AC-06 ratified both the GMC and the Wesleyan row; the surviving row carries the branch. |
| BSR-LU-02 | `AUTHORITY_URL_ONLY`, no corpus | AC-08 as drafted needs nothing further. |
| BSR-RC-03 | `canonical_url` still `ewtn.com` | AC-02 MIGRATE_WHERE_OFFICIAL is a Gate 7 action. Expected, not a defect. |
| Q-449 | OUT_OF_RATIFIED_SCOPE | The cited text is Lateran IV canon 2; BSR-RC-04 ratifies canon 1. Widening the row or re-pointing the cell is an author call. |

## Verdict by verifier model

| verifier model | model id | n | recall same-division | recall same-standard | **recall tier-respecting** | partial (lower tier) | false-accept | Dositheus false-accept | calls | cost (USD) | thresholds |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sonnet` | claude-sonnet-5 | 140 | 91/140 = 0.650 | 112/140 = 0.800 | **126/140 = 0.900** | 6 | 0.000 | 0.000 | 875 | 28.70 (est.) | MET |
| `opus` | claude-opus-5 | 140 | 91/140 = 0.650 | 113/140 = 0.807 | **127/140 = 0.907** | 6 | 0.000 | 0.000 | 588 | 39.88 (est.) | MET |

The denominator excludes **1** released cell(s) classed OUT_OF_RATIFIED_SCOPE (listed below). The threshold is scored on the tier-respecting column only.

Locator `sonnet`: 875 calls, 28.70 USD (est.). Total calls 1463.

**Live-run verifier: NOT NAMED HERE.** Gate 6 reports the thresholds and stops; the author selects the live-run verifier after reading this report. Models meeting every threshold: `sonnet`, `opus`.

**The live run against the 315 open cells has not been started.**

## Why each released cell scored as it did

Gate 5 widened every branch to two tiers, so a branch now carries several ratified standards that each confess the same predicate. A team that cites a different one of them has not failed. Row B1 is that case at an equal or higher authority tier and is credited; row B2 is the same case at a LOWER tier and is a partial, never credited. Rows C and D are the genuine no-evidence outcomes. Row E is excluded from every denominator.

| outcome | `sonnet` | `opus` |
|---|---|---|
| A. hit in the same standard the cell cites | 112 | 113 |
| B1. different ratified standard of the branch, **equal or higher** tier — credited | 14 | 14 |
| B2. different ratified standard of the branch, **lower** tier — partial, not credited | 6 | 6 |
| B3. survivor outside the cell's branch | 0 | 0 |
| C. candidates found, all rejected by the verifier | 2 | 1 |
| D. locator returned empty | 6 | 6 |
| E. excluded — cited text outside every ratified row of the branch | 1 | 1 |
| **total scored** | 141 | 141 |

- `sonnet`: tier-respecting recall **126/140 = 0.900** (the threshold metric); same-standard **112/140 = 0.800**; lower-tier partials **6** (not credited); genuine no-evidence **8/140**.
- `opus`: tier-respecting recall **127/140 = 0.907** (the threshold metric); same-standard **113/140 = 0.807**; lower-tier partials **6** (not credited); genuine no-evidence **7/140**.

## Recall per branch — all three metrics, by verifier model

Secondary-verifier scope: ALL. A model's recall denominator is the cells it verified in full (`done`); cells outside a secondary model's scope are counted under `skipped`.

| branch | model | released cells | done | skipped | excl. scope | located (any) | same-division | same-standard | **tier-respecting** | partial (lower) | empty | corpus unavailable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Roman Catholic | `sonnet` | 20 | 19 | 0 | 1 | 19 | 11/19 = 0.58 | 14/19 = 0.74 | **16/19 = 0.84** | 3 | 0 | 0 |
| Roman Catholic | `opus` | 20 | 19 | 0 | 1 | 19 | 11/19 = 0.58 | 14/19 = 0.74 | **16/19 = 0.84** | 3 | 0 | 0 |
| Lutheran | `sonnet` | 15 | 15 | 0 | 0 | 11 | 6/15 = 0.40 | 11/15 = 0.73 | **11/15 = 0.73** | 0 | 4 | 0 |
| Lutheran | `opus` | 15 | 15 | 0 | 0 | 12 | 6/15 = 0.40 | 12/15 = 0.80 | **12/15 = 0.80** | 0 | 3 | 0 |
| Reformed / Presbyterian | `sonnet` | 37 | 37 | 0 | 0 | 36 | 21/37 = 0.57 | 27/37 = 0.73 | **36/37 = 0.97** | 0 | 1 | 0 |
| Reformed / Presbyterian | `opus` | 37 | 37 | 0 | 0 | 36 | 21/37 = 0.57 | 27/37 = 0.73 | **36/37 = 0.97** | 0 | 1 | 0 |
| Baptist | `sonnet` | 16 | 16 | 0 | 0 | 16 | 16/16 = 1.00 | 16/16 = 1.00 | **16/16 = 1.00** | 0 | 0 | 0 |
| Baptist | `opus` | 16 | 16 | 0 | 0 | 16 | 16/16 = 1.00 | 16/16 = 1.00 | **16/16 = 1.00** | 0 | 0 | 0 |
| Methodist / Wesleyan | `sonnet` | 18 | 18 | 0 | 0 | 18 | 17/18 = 0.94 | 18/18 = 1.00 | **18/18 = 1.00** | 0 | 0 | 0 |
| Methodist / Wesleyan | `opus` | 18 | 18 | 0 | 0 | 18 | 17/18 = 0.94 | 18/18 = 1.00 | **18/18 = 1.00** | 0 | 0 | 0 |
| Anglican | `sonnet` | 12 | 12 | 0 | 0 | 9 | 8/12 = 0.67 | 9/12 = 0.75 | **9/12 = 0.75** | 0 | 3 | 0 |
| Anglican | `opus` | 12 | 12 | 0 | 0 | 9 | 8/12 = 0.67 | 9/12 = 0.75 | **9/12 = 0.75** | 0 | 3 | 0 |
| Mennonite / Anabaptist | `sonnet` | 13 | 13 | 0 | 0 | 13 | 10/13 = 0.77 | 12/13 = 0.92 | **13/13 = 1.00** | 0 | 0 | 0 |
| Mennonite / Anabaptist | `opus` | 13 | 13 | 0 | 0 | 13 | 10/13 = 0.77 | 12/13 = 0.92 | **13/13 = 1.00** | 0 | 0 | 0 |
| Eastern Orthodox | `sonnet` | 10 | 10 | 0 | 0 | 10 | 2/10 = 0.20 | 5/10 = 0.50 | **7/10 = 0.70** | 3 | 0 | 0 |
| Eastern Orthodox | `opus` | 10 | 10 | 0 | 0 | 10 | 2/10 = 0.20 | 5/10 = 0.50 | **7/10 = 0.70** | 3 | 0 | 0 |

## OUT_OF_RATIFIED_SCOPE — cells excluded from the recall denominator

**1 released cell(s) excluded.** The cited text lies outside the ratified scope of every row in the cell's branch, so no agent could have found it: the passage is not in the corpus the registry ratified. These are not misses and are not counted as misses.

| cell | cited | ratified scope | where the phrase actually sits | reason |
|---|---|---|---|---|
| Q-449 | Fourth Lateran Council, Constitution 1 (Firmiter credimus) | BSR-RC-04 ratifies Lateran IV canon 1 only (4 chunks, 3,574 chars). | Lateran IV canon 2 (Damnamus… the condemnation of Joachim of Fiore), where the maior dissimilitudo clause stands. | No ratified Roman Catholic row contains 'dissimilitude', 'dissimilar', 'unlikeness' or 'Joachim' in any chunk. The predicate's own text is unreachable from the registry as ratified. |

## Caveated rows in winning candidates (AC-03, AC-05)

27 candidate(s) landed on a caveated row. The caveat travels with the packet entry.

| cell | model | row | locator | credited | caveat |
|---|---|---|---|---|---|
| Q-010 | `sonnet` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-010 | `opus` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-026 | `sonnet` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-026 | `sonnet` | BSR-EO-04 | Q.67 (On the Creed generally, and on its Origi | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-026 | `opus` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-026 | `opus` | BSR-EO-04 | Q.67 (On the Creed generally, and on its Origi | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-034 | `sonnet` | BSR-EO-05 | Decree 1 | no (lower tier — partial) | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-034 | `sonnet` | BSR-EO-04 | Q.129 (On the Second Article) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-034 | `opus` | BSR-EO-05 | Decree 1 | no (lower tier — partial) | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-034 | `opus` | BSR-EO-04 | Q.129 (On the Second Article) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-042 | `opus` | BSR-EO-04 | Q.503 (On the First Commandment) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-170 | `sonnet` | BSR-EO-04 | Q.97 (On the First Article) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-170 | `opus` | BSR-EO-04 | Q.97 (On the First Article) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-266 | `sonnet` | BSR-EO-04 | Q.240 (On the Eighth Article) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-266 | `opus` | BSR-EO-04 | Q.240 (On the Eighth Article) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-290 | `sonnet` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-290 | `sonnet` | BSR-EO-04 | Q.94 (On the First Article) | yes | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-290 | `opus` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-290 | `opus` | BSR-EO-04 | Q.94 (On the First Article) | yes | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-306 | `sonnet` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-306 | `sonnet` | BSR-EO-04 | Q.122 (On the First Article) | yes | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-306 | `opus` | BSR-EO-05 | Decree 1 | yes | AC-05 — the Confession of Dositheus (Synod of Jerusalem 1672) is CONFESSIONAL (local synod); its authority is regional, not pan-Orthodox. |
| Q-306 | `opus` | BSR-EO-04 | Q.122 (On the First Article) | yes | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-354 | `sonnet` | BSR-EO-04 | Q.86 (On the First Article) | yes | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-354 | `opus` | BSR-EO-04 | Q.86 (On the First Article) | yes | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-434 | `sonnet` | BSR-EO-04 | Q.182 (Of the Son of God) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |
| Q-434 | `opus` | BSR-EO-04 | Q.182 (Of the Son of God) | no (lower tier — partial) | AC-03 — Philaret's Longer Catechism is CATECHETICAL (historic); it is a 19th-century Russian catechism, not a pan-Orthodox conciliar standard. |

## Residue under the tier-respecting metric


### `sonnet` — 14 cell(s) not credited

| cell | branch | predicate | cited tier | class | lower-tier evidence offered |
|---|---|---|---|---|---|
| Q-033 | Roman Catholic | Son | CONCILIAR | PARTIAL_LOWER_TIER | BSR-RC-06 (CONFESSIONAL) Nicene Creed; BSR-RC-01 (CATECHETICAL) CCC 242 |
| Q-034 | Eastern Orthodox | Son | CONCILIAR | PARTIAL_LOWER_TIER | BSR-EO-05 (CONFESSIONAL) Decree 1; BSR-EO-01 (CONFESSIONAL) The Symbol of Faith — "Son of ; BSR-EO-04 (CATECHETICAL) Q.129 (On the Second Article) |
| Q-042 | Eastern Orthodox | Lord | CONCILIAR | PARTIAL_LOWER_TIER | BSR-EO-01 (CONFESSIONAL) The Symbol of Faith — "God" |
| Q-155 | Lutheran | Glorious | CONFESSIONAL | ALL_CANDIDATES_REJECTED | — |
| Q-170 | Eastern Orthodox | Creator / Maker | CONFESSIONAL | PARTIAL_LOWER_TIER | BSR-EO-04 (CATECHETICAL) Q.97 (On the First Article) |
| Q-201 | Roman Catholic | Judge | CONFESSIONAL | PARTIAL_LOWER_TIER | BSR-RC-01 (CATECHETICAL) CCC 841; BSR-RC-01 (CATECHETICAL) CCC 1040 |
| Q-209 | Roman Catholic | Savior | CONFESSIONAL | PARTIAL_LOWER_TIER | BSR-RC-01 (CATECHETICAL) CCC 207 |
| Q-228 | Reformed / Presbyterian | Fountain of being | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-291 | Lutheran | Unbegotten | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-331 | Lutheran | Incorporeal / without body | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-333 | Anglican | Incorporeal / without body | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-339 | Lutheran | Without parts / simple | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-341 | Anglican | Without parts / simple | CONFESSIONAL | ALL_CANDIDATES_REJECTED | — |
| Q-349 | Anglican | Without passions / impassible | CONFESSIONAL | LOCATOR_EMPTY | — |

### `opus` — 13 cell(s) not credited

| cell | branch | predicate | cited tier | class | lower-tier evidence offered |
|---|---|---|---|---|---|
| Q-033 | Roman Catholic | Son | CONCILIAR | PARTIAL_LOWER_TIER | BSR-RC-06 (CONFESSIONAL) Nicene Creed; BSR-RC-01 (CATECHETICAL) CCC 242 |
| Q-034 | Eastern Orthodox | Son | CONCILIAR | PARTIAL_LOWER_TIER | BSR-EO-05 (CONFESSIONAL) Decree 1; BSR-EO-01 (CONFESSIONAL) The Symbol of Faith — "Son of ; BSR-EO-04 (CATECHETICAL) Q.129 (On the Second Article) |
| Q-042 | Eastern Orthodox | Lord | CONCILIAR | PARTIAL_LOWER_TIER | BSR-EO-01 (CONFESSIONAL) The Symbol of Faith — "God"; BSR-EO-04 (CATECHETICAL) Q.503 (On the First Commandmen |
| Q-170 | Eastern Orthodox | Creator / Maker | CONFESSIONAL | PARTIAL_LOWER_TIER | BSR-EO-04 (CATECHETICAL) Q.97 (On the First Article) |
| Q-201 | Roman Catholic | Judge | CONFESSIONAL | PARTIAL_LOWER_TIER | BSR-RC-01 (CATECHETICAL) CCC 841; BSR-RC-01 (CATECHETICAL) CCC 1040 |
| Q-209 | Roman Catholic | Savior | CONFESSIONAL | PARTIAL_LOWER_TIER | BSR-RC-01 (CATECHETICAL) CCC 431; BSR-RC-01 (CATECHETICAL) CCC 207 |
| Q-228 | Reformed / Presbyterian | Fountain of being | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-291 | Lutheran | Unbegotten | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-331 | Lutheran | Incorporeal / without body | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-333 | Anglican | Incorporeal / without body | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-339 | Lutheran | Without parts / simple | CONFESSIONAL | LOCATOR_EMPTY | — |
| Q-341 | Anglican | Without parts / simple | CONFESSIONAL | ALL_CANDIDATES_REJECTED | — |
| Q-349 | Anglican | Without passions / impassible | CONFESSIONAL | LOCATOR_EMPTY | — |

## Skipped cells — reason per cell

`SECONDARY_SCOPE` means the cell is outside that model's defined sample (every Eastern Orthodox cell, every reviewed-empty cell, and a deterministic quarter of the rest). It is not a failure and the cell is not in that model's denominator. `VERIFICATION_INCOMPLETE` and `CELL_NOT_DONE` are.


### `sonnet` — 0 skipped (none)

None.


### `opus` — 0 skipped (none)

None.


## Expected-empty cells (NOT LOCATED — CURRENT STANDARD REVIEWED)

| cell | branch | predicate | model | outcome | survivors |
|---|---|---|---|---|---|
| Q-294 | Baptist | Unbegotten | sonnet | LOCATED_IN_OTHER_REGISTRY_STANDARD | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity), paragraph 3: “the Father is of none, neither begotten nor proceeding” |
| Q-294 | Baptist | Unbegotten | opus | LOCATED_IN_OTHER_REGISTRY_STANDARD | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity), paragraph 3: “the Father is of none, neither begotten nor proceeding” |
| Q-295 | Methodist / Wesleyan | Unbegotten | sonnet | LOCATED_IN_SAME_STANDARD | BSR-MW-04 Article 2. The Father, ¶212: “the Father is the Source of all that exists”; BSR-MW-01 Article I — Of Faith in the Holy Trinity: “the maker and preserver of all things, both visible and invisible”; BSR-MW-02 Article I — God: “Creator, Sovereign and Preserver of all things visible and invisible” |
| Q-295 | Methodist / Wesleyan | Unbegotten | opus | EMPTY |  |
| Q-296 | Mennonite / Anabaptist | Unbegotten | sonnet | LOCATED_IN_SAME_STANDARD | BSR-MA-02 Article I. Of God and the Creation of all Things: “before whom no God was made or existed, nor shall there be any after Him”; BSR-MA-01 Article 5. Creation and Divine Providence: “Scripture is clear that God was before anything else existed”; BSR-MA-02 Article I. Of God and the Creation of all Things: “in one eternal, almighty, and incomprehensible God, the Father, Son, and Holy Ghost” |
| Q-296 | Mennonite / Anabaptist | Unbegotten | opus | LOCATED_IN_OTHER_REGISTRY_STANDARD | BSR-MA-02 Article I. Of God and the Creation of all Things: “before whom no God was made or existed, nor shall there be any after Him”; BSR-MA-02 Article I. Of God and the Creation of all Things: “in one eternal, almighty, and incomprehensible God, the Father, Son, and Holy Ghost” |
| Q-357 | Anglican | Immutable / unchangeable | sonnet | LOCATED_IN_SAME_STANDARD | BSR-AN-01 Article XVII (17) — Of Predestination And Election: “he hath constantly decreed by his counsel secret to us” |
| Q-357 | Anglican | Immutable / unchangeable | opus | LOCATED_IN_SAME_STANDARD | BSR-AN-01 Article XVII (17) — Of Predestination And Election: “he hath constantly decreed by his counsel secret to us” |
| Q-358 | Baptist | Immutable / unchangeable | sonnet | LOCATED_IN_OTHER_REGISTRY_STANDARD | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity), paragraph 1: “who is immutable, immense, eternal, incomprehensible, almighty, every way infinite” |
| Q-358 | Baptist | Immutable / unchangeable | opus | LOCATED_IN_OTHER_REGISTRY_STANDARD | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity), paragraph 1: “who is immutable, immense, eternal, incomprehensible, almighty, every way infinite” |
| Q-359 | Methodist / Wesleyan | Immutable / unchangeable | sonnet | EMPTY |  |
| Q-359 | Methodist / Wesleyan | Immutable / unchangeable | opus | EMPTY |  |
| Q-360 | Mennonite / Anabaptist | Immutable / unchangeable | sonnet | LOCATED_IN_SAME_STANDARD | BSR-MA-01 Article 1. God: “God's infinite freedom and constant self-giving are perfect in faithful love” |
| Q-360 | Mennonite / Anabaptist | Immutable / unchangeable | opus | LOCATED_IN_SAME_STANDARD | BSR-MA-01 Article 1. God: “God's infinite freedom and constant self-giving are perfect in faithful love” |

The registry ratified in Gate 5 is broader than the standards those cells were closed against; a candidate located in another registry standard of the same branch is new evidence for Gate 7, not a false accept.

## Planted near-misses — false-accept by slice and model

| slice | model | planted | false accepts | rate | pending |
|---|---|---|---|---|---|
| Anglican | `sonnet` | 5 | 0 | 0.000 | 0 |
| Anglican | `opus` | 5 | 0 | 0.000 | 0 |
| Baptist | `sonnet` | 5 | 0 | 0.000 | 0 |
| Baptist | `opus` | 5 | 0 | 0.000 | 0 |
| Dositheus | `sonnet` | 23 | 0 | 0.000 | 0 |
| Dositheus | `opus` | 23 | 0 | 0.000 | 0 |
| Eastern Orthodox | `sonnet` | 6 | 0 | 0.000 | 0 |
| Eastern Orthodox | `opus` | 6 | 0 | 0.000 | 0 |
| Lutheran | `sonnet` | 13 | 0 | 0.000 | 0 |
| Lutheran | `opus` | 13 | 0 | 0.000 | 0 |
| Mennonite / Anabaptist | `sonnet` | 3 | 0 | 0.000 | 0 |
| Mennonite / Anabaptist | `opus` | 3 | 0 | 0.000 | 0 |
| Methodist / Wesleyan | `sonnet` | 4 | 0 | 0.000 | 0 |
| Methodist / Wesleyan | `opus` | 4 | 0 | 0.000 | 0 |
| Reformed / Presbyterian | `sonnet` | 9 | 0 | 0.000 | 0 |
| Reformed / Presbyterian | `opus` | 9 | 0 | 0.000 | 0 |
| Roman Catholic | `sonnet` | 6 | 0 | 0.000 | 0 |
| Roman Catholic | `opus` | 6 | 0 | 0.000 | 0 |

## Dositheus slice (BSR-EO-05) — natural candidates from the Eastern Orthodox cells

| model | Dositheus candidates | accepted | rejected |
|---|---|---|---|
| `sonnet` | 6 | 5 | 1 |
| `opus` | 6 | 5 | 1 |

## Corpus state at calibration

| registry | branch | status | chunks |
|---|---|---|---|
| BSR-RC-01 | Roman Catholic | UNCHANGED | 570 |
| BSR-RC-02 | Roman Catholic | UNCHANGED | 22 |
| BSR-RC-03 | Roman Catholic | UNCHANGED | 3 |
| BSR-RC-04 | Roman Catholic | UNCHANGED | 4 |
| BSR-RC-05 | Roman Catholic | LINEAGE | 0 |
| BSR-RC-06 | Roman Catholic | UNCHANGED | 2 |
| BSR-RC-07 | Roman Catholic | UNCHANGED | 533 |
| BSR-EO-01 | Eastern Orthodox | UNCHANGED | 19 |
| BSR-EO-02 | Eastern Orthodox | UNCHANGED | 14 |
| BSR-EO-03 | Eastern Orthodox | FETCH_BLOCKED | 0 |
| BSR-EO-04 | Eastern Orthodox | UNCHANGED | 610 |
| BSR-EO-05 | Eastern Orthodox | UNCHANGED | 22 |
| BSR-EO-06 | Eastern Orthodox | UNCHANGED | 2 |
| BSR-LU-01 | Lutheran | UNCHANGED | 738 |
| BSR-LU-02 | Lutheran | AUTHORITY_URL_ONLY | 0 |
| BSR-LU-03 | Lutheran | UNCHANGED | 1 |
| BSR-RP-01 | Reformed / Presbyterian | UNCHANGED | 171 |
| BSR-RP-02 | Reformed / Presbyterian | UNCHANGED | 107 |
| BSR-RP-03 | Reformed / Presbyterian | UNCHANGED | 196 |
| BSR-RP-04 | Reformed / Presbyterian | UNCHANGED | 1018 |
| BSR-RP-05 | Reformed / Presbyterian | UNCHANGED | 128 |
| BSR-RP-06 | Reformed / Presbyterian | UNCHANGED | 37 |
| BSR-AN-01 | Anglican | UNCHANGED | 39 |
| BSR-AN-02 | Anglican | UNCHANGED | 25 |
| BSR-AN-03 | Anglican | UNCHANGED | 1 |
| BSR-AN-04 | Anglican | UNCHANGED | 124 |
| BSR-AN-05 | Anglican | UNCHANGED | 368 |
| BSR-BA-01 | Baptist | UNCHANGED | 21 |
| BSR-BA-02 | Baptist | UNCHANGED | 3 |
| BSR-BA-03 | Baptist | UNCHANGED | 10 |
| BSR-MW-01 | Methodist / Wesleyan | UNCHANGED | 25 |
| BSR-MW-02 | Methodist / Wesleyan | UNCHANGED | 16 |
| BSR-MW-03 | Methodist / Wesleyan | UNAVAILABLE_ON_RATIFIED_DOMAIN | 0 |
| BSR-MW-04 | Methodist / Wesleyan | UNCHANGED | 22 |
| BSR-MA-01 | Mennonite / Anabaptist | UNCHANGED | 23 |
| BSR-MA-02 | Mennonite / Anabaptist | UNCHANGED | 18 |

## Per-cell detail (primary verifier)

`STD+DIV` same standard and division · `STD` same standard · `TIER` different ratified standard of the branch at an equal or higher tier (credited) · `PARTIAL (lower tier)` different standard at a lower tier (not credited) · `MISS` no verified evidence.

| cell | branch | predicate | cited tier | existing citation | hit | survivors | rejected (reason) |
|---|---|---|---|---|---|---|---|
| Q-001 | Roman Catholic | Living | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-02 Caput I — De Deo Rerum Omnium Creatore: “unum esse Deum verum et vivum”; BSR-RC-03 Chapter I (English witness), paragraph 1: “there is one true and living God”; BSR-RC-07 Compendium Q.38: “God revealed himself to Moses as the living God” |  |
| Q-005 | Anglican | Living | CONFESSIONAL | Thirty-Nine Articles — Articles I-II | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “THERE is but one living and true God” |  |
| Q-006 | Baptist | Living | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — one living and tr | STD+DIV | BSR-BA-01 II. God: “one and only one living and true God”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “one only living and true God”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “having all life, glory, goodness, blessedness, in and of Himself” |  |
| Q-007 | Methodist / Wesleyan | Living | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “one living and true God”; BSR-MW-02 Article I — God: “one true, holy and living God”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “one living and true God” |  |
| Q-009 | Roman Catholic | True | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Creed, Godhead an | TIER | BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “there is only one true God, eternal and immeasurable, almighty, unchangeable”; BSR-RC-03 Chapter I (English witness), paragraph 1: “there is one true and living God, creator and Lord of heaven and earth”; BSR-RC-01 CCC 215: “God is Truth itself, whose words cannot deceive” |  |
| Q-010 | Eastern Orthodox | True | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Nicene Creed, God | STD | BSR-EO-05 Decree 1: “We believe in one God, true, almighty and infinite”; BSR-EO-01 The Symbol of Faith — "God": “He is the true and living God, the only God” | BSR-EO-04 Q.505 (On the First Commandmen REJECT/WRONG_SUBJECT |
| Q-011 | Lutheran | True | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Nicene Creed | STD | BSR-LU-01 Large Catechism: Holy Baptism, ¶55–59: “we know that God does not lie” | BSR-LU-01 Large Catechism: The Ten Comma REJECT/WRONG_SUBJECT |
| Q-013 | Anglican | True | CONFESSIONAL | Thirty-Nine Articles — Articles I–II | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “THERE is but one living and true God” |  |
| Q-014 | Baptist | True | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — one living and tr | STD+DIV | BSR-BA-01 II. God: “There is one and only one living and true God”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “The Lord our God is but one only living and true God” |  |
| Q-015 | Methodist / Wesleyan | True | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “There is but one living and true God”; BSR-MW-02 Article I — God: “We believe in the one true, holy and living God”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “We believe in the one living and true God” |  |
| Q-025 | Roman Catholic | Father | CONFESSIONAL | Apostles' Creed — Apostles' Creed, articles 1–12 | STD+DIV | BSR-RC-06 Nicene Creed: “We believe in one God, the Father, the Almighty”; BSR-RC-06 Apostles' Creed: “I believe in God the Father almighty, creator of heaven and earth” |  |
| Q-026 | Eastern Orthodox | Father | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Nicene Creed, God | STD | BSR-EO-01 The Symbol of Faith — "God": “One God, the Father Almighty”; BSR-EO-04 Q.67 (On the Creed generally, and on its: “I believe in one God the Father, Almighty, Maker of heaven and earth”; BSR-EO-05 Decree 1: “We believe in one God, true, almighty and infinite, the Father” |  |
| Q-027 | Lutheran | Father | CONFESSIONAL | Nicene Creed — Nicene Creed | STD+DIV | BSR-LU-03 Small Catechism, The Creed — First Artic: “I believe in God, the Father Almighty, Maker of heaven and earth”; BSR-LU-01 Ecumenical Creeds: The Apostles' Creed: “I believe in God the Father Almighty, Maker of heaven and earth”; BSR-LU-01 Ecumenical Creeds: The Nicene Creed: “I believe in one God, the Father Almighty, Maker of heaven and earth” |  |
| Q-028 | Reformed / Presbyterian | Father | CONFESSIONAL | Nicene Creed — 1.1–3, Nicene Creed | STD+DIV | BSR-RP-04 Book of Confessions 2.1 (Apostles' Creed: “I BELIEVE in God the Father Almighty, Maker of heaven and earth”; BSR-RP-01 Chapter 2.3 — Of God, and of the Holy Tr: “God the Father, God the Son, and God the Holy Ghost” | BSR-RP-02 Shorter Catechism Q.6 REJECT/BELOW_FLOOR |
| Q-030 | Baptist | Father | CONFESSIONAL | Baptist Faith and Message 2000 — II.A. God the Father | STD+DIV | BSR-BA-01 II.A. God the Father: “God as Father reigns with providential care over His universe, His creatures”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “there are three subsistences, the Father, the Word or Son, and Holy Spirit”; BSR-BA-01 II. God: “The eternal triune God reveals Himself to us as Father, Son, and Holy Spirit” |  |
| Q-032 | Mennonite / Anabaptist | Father | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | TIER | BSR-MA-02 Article I. Of God and the Creation of al: “in one eternal, almighty, and incomprehensible God, the Father, Son, and Holy Ghost” |  |
| Q-033 | Roman Catholic | Son | CONCILIAR | Fourth Lateran Council — Constitution 1, Firmiter credimus | PARTIAL (lower tier) | BSR-RC-06 Nicene Creed: “the only Son of God, eternally begotten of the Father, God from God”; BSR-RC-01 CCC 242: “the only-begotten Son of God, eternally begotten of the Father, light from light” |  |
| Q-034 | Eastern Orthodox | Son | CONCILIAR | Third Council of Constantinople — Sixth Ecumenical Council | PARTIAL (lower tier) | BSR-EO-05 Decree 1: “the Son begotten of the Father before the ages, and consubstantial with him”; BSR-EO-01 The Symbol of Faith — "Son of God": “There is but one eternal Son of God.”; BSR-EO-04 Q.129 (On the Second Article): “Son of God is the name of the second Person of the Holy Trinity” |  |
| Q-035 | Lutheran | Son | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Nicene Creed | STD+DIV | BSR-LU-01 Ecumenical Creeds: The Athanasian Creed: “The Son is of the Father alone; not made, nor created, but begotten” |  |
| Q-036 | Reformed / Presbyterian | Son | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD | BSR-RP-01 Chapter 2.3 — Of God, and of the Holy Tr: “the Son is eternally begotten of the Father”; BSR-RP-06 Article 10: The Deity of Christ: “the only Son of God— eternally begotten, not made or created”; BSR-RP-03 Larger Catechism Q.10: “the Son to be begotten of the Father, and to the Holy Ghost to proceed” |  |
| Q-037 | Anglican | Son | CONFESSIONAL | Thirty-Nine Articles — Articles I–II | STD+DIV | BSR-AN-01 Article II (2) — Of The Word Or Son Of G: “begotten from everlasting of the Father, the very and eternal God”; BSR-AN-03 Quicunque Vult (Creed of S. Athanasius),: “The Father eternal, the Son eternal: and the Holy Ghost eternal” | BSR-AN-01 Article I (1) — Of Faith In Th REJECT/WRONG_SUBJECT |
| Q-038 | Baptist | Son | CONFESSIONAL | Baptist Faith and Message 2000 — II.B. God the Son | STD+DIV | BSR-BA-01 II.B. God the Son: “Christ is the eternal Son of God.”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “the Son is eternally begotten of the Father” | BSR-BA-01 II. God REJECT/WRONG_SUBJECT |
| Q-039 | Methodist / Wesleyan | Son | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD | BSR-MW-01 Article II — Of the Word, or Son of God,: “The Son, who is the Word of the Father, the very and eternal God”; BSR-MW-02 Article II — Jesus Christ: “the eternal Word made flesh, the only begotten Son of the Father”; BSR-MW-04 Article 3. The Son of God, ¶214: “Jesus Christ, the only begotten Son of God” |  |
| Q-040 | Mennonite / Anabaptist | Son | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD | BSR-MA-02 Article IV. The Advent of Christ into Th: “who is God’s only, first and own Son”; BSR-MA-01 Article 2. Jesus Christ: “the only Son of God, the Word of God incarnate” | BSR-MA-02 Article I. Of God and the Crea REJECT/WRONG_SUBJECT |
| Q-041 | Roman Catholic | Lord | CATECHETICAL | Third Council of Constantinople / CCC restatement — CCC 475; | STD | BSR-RC-03 Chapter I (English witness), paragraph 1: “one true and living God, creator and Lord of heaven and earth”; BSR-RC-01 CCC 269: “He is the Lord of the universe, whose order he established” | BSR-RC-02 Canon I.1 — De Deo Rerum Omniu REJECT/WRONG_SUBJECT |
| Q-042 | Eastern Orthodox | Lord | CONCILIAR | Definition of Chalcedon — Fourth Ecumenical Council / Chalce | PARTIAL (lower tier) | BSR-EO-01 The Symbol of Faith — "God": “the Lord our God is one God” | BSR-EO-04 Q.503 (On the First Commandmen REJECT/BELOW_FLOOR; BSR-EO-04 Q.493 (On the Law of God and t REJECT/WRONG_SUBJECT |
| Q-043 | Lutheran | Lord | CONFESSIONAL | Nicene Creed — Nicene Creed | STD+DIV | BSR-LU-01 Ecumenical Creeds: The Athanasian Creed: “So likewise the Father is Lord, the Son Lord, and the Holy Ghost Lord”; BSR-LU-01 Ecumenical Creeds: The Athanasian Creed: “acknowledge every Person by Himself to be God and Lord”; BSR-LU-01 Large Catechism: The Ten Commandments, ¶: “you have a rich Lord, who is certainly sufficient for you” |  |
| Q-044 | Reformed / Presbyterian | Lord | CONFESSIONAL | Nicene Creed — 1.1–3, Nicene Creed | STD | BSR-RP-01 Chapter 21.1 — Of Religious Worship, and: “there is a God, who hath lordship and sovereignty over all”; BSR-RP-01 Chapter 23.1 — Of the Civil Magistrate: “God, the supreme Lord and King of all the world”; BSR-RP-04 Book of Confessions 6.112 (Westminster C: “there is a God, who hath lordship and sovereignty over all” |  |
| Q-046 | Baptist | Lord | CONFESSIONAL | Baptist Faith and Message 2000 — II.B. God the Son — living  | STD+DIV | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “The Lord our God is but one only living and true God”; BSR-BA-01 XVII. Religious Liberty: “God alone is Lord of the conscience”; BSR-BA-01 II.A. God the Father: “God as Father reigns with providential care over His universe, His creatures” |  |
| Q-048 | Mennonite / Anabaptist | Lord | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-01 Article 1. God: “God's sovereign power and unending mercy are perfect in almighty love”; BSR-MA-01 Article 24. The Reign of God: “God, who created the universe, continues to rule over it in wisdom, patience, and justice”; BSR-MA-02 Article I. Of God and the Creation of al: “He still governs and upholds the same and all His works through His wisdom, might” |  |
| Q-059 | Lutheran | Wise / all-wise | CONFESSIONAL | Augsburg Confession — Article I, God | STD+DIV | BSR-LU-01 Augsburg Confession: Article I. Of God, : “of infinite power, wisdom, and goodness, the Maker and Preserver of all things” | BSR-LU-01 Formula of Concord, Solid Decl REJECT/WRONG_SUBJECT; BSR-LU-01 Formula of Concord, Solid Decl REJECT/WRONG_SUBJECT |
| Q-060 | Reformed / Presbyterian | Wise / all-wise | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “immutable, immense, eternal, incomprehensible, almighty, most wise, most holy, most free”; BSR-RP-03 Larger Catechism Q.7: “almighty, knowing all things, most wise, most holy, most just, most merciful and gracious”; BSR-RP-06 Article 1: The Only God: “completely wise, just, and good, and the overflowing source of all good” |  |
| Q-061 | Anglican | Wise / all-wise | CONFESSIONAL | Thirty-Nine Articles — Articles I–II | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “of infinite power, wisdom, and goodness” |  |
| Q-062 | Baptist | Wise / all-wise | CONFESSIONAL | Baptist Faith and Message 2000 — II.A. God the Father — all  | STD+DIV | BSR-BA-01 II.A. God the Father: “He is all powerful, all knowing, all loving, and all wise”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “most holy, most wise, most free, most absolute” | BSR-BA-01 V. God’s Purpose of Grace REJECT/WRONG_SUBJECT |
| Q-063 | Methodist / Wesleyan | Wise / all-wise | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “of infinite power, wisdom, and goodness”; BSR-MW-02 Article I — God: “He is infinite in power, wisdom, justice, goodness and love”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “unlimited in power, wisdom and goodness” |  |
| Q-065 | Roman Catholic | Good | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-01 CCC 385: “God is infinitely good and all his works are good”; BSR-RC-03 Chapter I (English witness), paragraph 2: “This one true God, in his goodness and almighty power”; BSR-RC-01 CCC 214: “God displays, not only his kindness, goodness, grace and steadfast love” |  |
| Q-067 | Lutheran | Good | CONFESSIONAL | Augsburg Confession — Article I, Of God | STD | BSR-LU-01 Large Catechism: The Ten Commandments, ¶: “because He is the only eternal good”; BSR-LU-03 Small Catechism, The Creed — First Artic: “out of fatherly, divine goodness and mercy” |  |
| Q-068 | Reformed / Presbyterian | Good | CONFESSIONAL | Scots Confession — Chapter 1 | TIER | BSR-RP-06 Article 1: The Only God: “completely wise, just, and good, and the overflowing source of all good”; BSR-RP-01 Chapter 2.2 — Of God, and of the Holy Tr: “God hath all life, glory, goodness, blessedness, in and of himself” |  |
| Q-069 | Anglican | Good | CONFESSIONAL | Thirty-Nine Articles — Articles I–II | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “of infinite power, wisdom, and goodness”; BSR-AN-02 Catechism, Q.13 — "What desirest thou of: “our heavenly Father, who is the giver of all goodness” |  |
| Q-071 | Methodist / Wesleyan | Good | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-02 Article I — God: “He is infinite in power, wisdom, justice, goodness and love”; BSR-MW-01 Article I — Of Faith in the Holy Trinity: “living and true God, everlasting, without body or parts, of infinite power, wisdom, and goodness”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “living and true God, both holy and loving, eternal, unlimited in power, wisdom and goodness” |  |
| Q-072 | Mennonite / Anabaptist | Good | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-01 Article 5. Creation and Divine Providenc: “because God is good and provides all that is needed for life” |  |
| Q-076 | Reformed / Presbyterian | Source of all good | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-06 Article 1: The Only God: “completely wise, just, and good, and the overflowing source of all good”; BSR-RP-04 Book of Confessions 4.125 (Heidelberg Ca: “you are the only source of everything good” | BSR-RP-05 Q&A 125 (Lord’s Day 50) REJECT/NOT_ASSERTION |
| Q-084 | Reformed / Presbyterian | Just / righteous | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | TIER | BSR-RP-02 Shorter Catechism Q.4: “God is a spirit, infinite, eternal, and unchangeable, in his being, wisdom, power, holiness, justice”; BSR-RP-03 Larger Catechism Q.7: “almighty, knowing all things, most wise, most holy, most just, most merciful and gracious” | BSR-RP-01 Chapter 2.1 — Of God, and of t REJECT/BELOW_FLOOR |
| Q-087 | Methodist / Wesleyan | Just / righteous | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-02 Article I — God: “He is infinite in power, wisdom, justice, goodness and love”; BSR-MW-04 Article 21. The Judgment of All Persons,: “based on His omniscience and eternal justice” |  |
| Q-092 | Reformed / Presbyterian | Holy | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD | BSR-RP-02 Shorter Catechism Q.4: “God is a spirit, infinite, eternal, and unchangeable, in his being, wisdom, power, holiness”; BSR-RP-03 Larger Catechism Q.7: “almighty, knowing all things, most wise, most holy, most just, most merciful”; BSR-RP-01 Chapter 5.4 — Of Providence: “God, who, being most holy and righteous, neither is nor can be the author” |  |
| Q-094 | Baptist | Holy | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — infinite in holin | STD+DIV | BSR-BA-01 II. God: “God is infinite in holiness and all other perfections.”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “He is most holy in all His counsels”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “every way infinite, most holy, most wise, most free, most absolute” |  |
| Q-095 | Methodist / Wesleyan | Holy | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-02 Article I — God: “the one true, holy and living God, Eternal Spirit”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “the one living and true God, both holy and loving” |  |
| Q-096 | Mennonite / Anabaptist | Holy | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-01 Article 1. God: “We worship the one holy and loving God who is Father”; BSR-MA-01 Article 1. God: “To the one holy and ever-loving triune God be glory” |  |
| Q-100 | Reformed / Presbyterian | Truthful / faithful | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | TIER | BSR-RP-04 Book of Confessions 11.3 (A Brief Statem: “God is faithful still”; BSR-RP-05 Q&A 26 (Lord’s Day 9): “he is almighty God and desires to do this because he is a faithful Father” |  |
| Q-108 | Reformed / Presbyterian | Love / loving | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “most loving, gracious, merciful, long-suffering, abundant in goodness and truth”; BSR-RP-04 Book of Confessions 9.14 (Confession of : “God's love never changes”; BSR-RP-06 Article 20: The Justice and Mercy of God: “giving to us his Son to die, by a most perfect love” |  |
| Q-110 | Baptist | Love / loving | CONFESSIONAL | Baptist Faith and Message 2000 — II.A. God the Father — all  | STD+DIV | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “most loving, gracious, merciful, long-suffering, abundant in goodness and truth”; BSR-BA-01 II.A. God the Father: “He is all powerful, all knowing, all loving, and all wise”; BSR-BA-03 Fact 1: “eternal fellowship with a loving God” |  |
| Q-111 | Methodist / Wesleyan | Love / loving | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “the one living and true God, both holy and loving”; BSR-MW-04 Article 2. The Father, ¶212: “In love, He both seeks and receives penitent sinners.”; BSR-MW-02 Article I — God: “He is infinite in power, wisdom, justice, goodness and love” |  |
| Q-112 | Mennonite / Anabaptist | Love / loving | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-02 Article II. Of the Fall of Man: “made provision for it, and interposed with His love and mercy”; BSR-MA-01 Article 1. God: “We worship the one holy and loving God who is Father, Son, and Holy Spirit”; BSR-MA-01 Article 1. God: “To the one holy and ever-loving triune God be glory for ever and ever” |  |
| Q-116 | Reformed / Presbyterian | Merciful | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “most loving, gracious, merciful, long-suffering, abundant in goodness and truth”; BSR-RP-05 Q&A 11 (Lord’s Day 4): “God is certainly merciful, but also just”; BSR-RP-06 Article 16: The Doctrine of Election: “God showed himself to be as he is: merciful and just” |  |
| Q-124 | Reformed / Presbyterian | Gracious | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “most loving, gracious, merciful, long-suffering, abundant in goodness and truth”; BSR-RP-03 Larger Catechism Q.7: “most wise, most holy, most just, most merciful and gracious, longsuffering”; BSR-RP-04 Book of Confessions 5.015 (Second Helvet: “a God merciful and gracious, slow to anger” |  |
| Q-127 | Methodist / Wesleyan | Gracious | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-02 Article I — God: “rules with gracious regard for the well-being and salvation of men” | BSR-MW-04 Article 18. The Sacraments: Ba REJECT/WRONG_SUBJECT; BSR-MW-02 Article VI — The Sacraments REJECT/WRONG_SUBJECT |
| Q-132 | Reformed / Presbyterian | Long-suffering / patient | CONFESSIONAL | Westminster Confession of Faith — 6.001 onward; Westminster  | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “most loving, gracious, merciful, long-suffering, abundant in goodness and truth”; BSR-RP-03 Larger Catechism Q.7: “most merciful and gracious, longsuffering, and abundant in goodness and truth”; BSR-RP-04 Book of Confessions 6.011 (Westminster C: “most loving, gracious, merciful, long-suffering, abundant in goodness and truth” |  |
| Q-140 | Reformed / Presbyterian | Forgiving | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “forgiving iniquity, transgression, and sin”; BSR-RP-01 Chapter 11.5 — Of Justification: “God doth continue to forgive the sins of those that are justified”; BSR-RP-04 Book of Confessions 5.102 (Second Helvet: “he forgives all sinners of all sins except the one sin against the Holy Spirit” |  |
| Q-145 | Roman Catholic | Blessed | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-02 Caput I — De Deo Rerum Omnium Creatore: “in se et ex se beatissimus”; BSR-RC-03 Chapter I (English witness), paragraph 1: “supremely happy in and from Himself”; BSR-RC-01 CCC 257: “God is eternal blessedness, undying life, unfading light” |  |
| Q-148 | Reformed / Presbyterian | Blessed | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD | BSR-RP-01 Chapter 2.2 — Of God, and of the Holy Tr: “God hath all life, glory, goodness, blessedness, in and of himself”; BSR-RP-03 Larger Catechism Q.7: “God is a Spirit, in and of himself infinite in being, glory, blessedness, and perfection” |  |
| Q-155 | Lutheran | Glorious | CONFESSIONAL | Athanasian Creed — Trinity and person/substance clauses | MISS |  | BSR-LU-01 Formula of Concord, Epitome: X REJECT/WRONG_SUBJECT |
| Q-156 | Reformed / Presbyterian | Glorious | CONFESSIONAL | Scots Confession — 3.01–3.25; especially chapter 1 | STD | BSR-RP-01 Chapter 2.2 — Of God, and of the Holy Tr: “God hath all life, glory, goodness, blessedness, in and of himself”; BSR-RP-04 Book of Confessions 6.012 (Westminster C: “God hath all life, glory, goodness, blessedness, in and of himself”; BSR-RP-02 Shorter Catechism Q.6: “these three are one God, the same in substance, equal in power and glory” |  |
| Q-164 | Reformed / Presbyterian | Life-giving | CONFESSIONAL | Second Helvetic Confession — 5.001 onward; chapter III | STD+DIV | BSR-RP-04 Book of Confessions 10.5 (Confession of : “that God's life-giving Word and Spirit has conquered the powers of sin and death”; BSR-RP-06 Article 20: The Justice and Mercy of God: “raising him to life for our justification” |  |
| Q-169 | Roman Catholic | Creator / Maker | CONFESSIONAL | Niceno-Constantinopolitan Creed (Vatican-hosted Credo) — Mak | STD | BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “one principle of all things, creator of all things invisible and visible, spiritual and corporeal”; BSR-RC-03 Chapter I (English witness), paragraph 1: “there is one true and living God, creator and Lord of heaven and earth”; BSR-RC-06 Nicene Creed: “We believe in one God, the Father, the Almighty, maker of heaven and earth” |  |
| Q-170 | Eastern Orthodox | Creator / Maker | CONFESSIONAL | Nicene Creed / Symbol of Faith — Maker of heaven and earth | PARTIAL (lower tier) | BSR-EO-04 Q.97 (On the First Article): “all was made by God, and that nothing can be without God” |  |
| Q-171 | Lutheran | Creator / Maker | CONFESSIONAL | Augsburg Confession — Article I, Of God | STD+DIV | BSR-LU-03 Small Catechism, The Creed — First Artic: “I believe that God has made me and all creatures”; BSR-LU-01 Augsburg Confession: Article I. Of God, : “the Maker and Preserver of all things, visible and invisible”; BSR-LU-01 Large Catechism: The Apostles' Creed, ¶1: “the Father, who has created heaven and earth” |  |
| Q-172 | Reformed / Presbyterian | Creator / Maker | CONFESSIONAL | Westminster Confession of Faith — Chapter IV, Of Creation | TIER | BSR-RP-06 Article 12: The Creation of All Things: “created heaven and earth and all other creatures from nothing, by the Word” |  |
| Q-173 | Anglican | Creator / Maker | CONFESSIONAL | Thirty-Nine Articles — Article I | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “the Maker, and Preserver of all things both visible and invisible”; BSR-AN-02 Catechism, Q.5 — "Rehearse the Articles : “I BELIEVE in God the Father Almighty, Maker of heaven and earth”; BSR-AN-04 Outline of the Faith (BCP p. 846) — God : “there is one God, the Father Almighty, creator of heaven and earth” |  |
| Q-174 | Baptist | Creator / Maker | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — Creator of the un | STD+DIV | BSR-BA-01 II. God: “the Creator, Redeemer, Preserver, and Ruler of the universe”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “He is the alone fountain of all being”; BSR-BA-03 Fact 1: “the God who is revealed as Creator, Savior and Advocate” |  |
| Q-175 | Methodist / Wesleyan | Creator / Maker | CONFESSIONAL | Articles of Religion — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “the maker and preserver of all things, both visible and invisible”; BSR-MW-02 Article I — God: “who is Creator, Sovereign and Preserver of all things visible and invisible”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “the Creator and Preserver of all things” |  |
| Q-176 | Mennonite / Anabaptist | Creator / Maker | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD | BSR-MA-02 Article I. Of God and the Creation of al: “He is the Creator of all things visible and invisible”; BSR-MA-01 Article 1. God: “We believe that God has created all things visible and invisible” |  |
| Q-180 | Reformed / Presbyterian | Preserver / Sustainer | CONFESSIONAL | Scots Confession — Chapter 1 | TIER | BSR-RP-01 Chapter 5.1 — Of Providence: “God the great Creator of all things doth uphold, direct, dispose, and govern all creatures”; BSR-RP-06 Article 12: The Creation of All Things: “Even now God also sustains and governs them all, according to his eternal providence”; BSR-RP-05 Q&A 27 (Lord’s Day 10): “God upholds, as with his hand, heaven and earth and all creatures” |  |
| Q-181 | Anglican | Preserver / Sustainer | CONFESSIONAL | Thirty-Nine Articles — Article I | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “the Maker, and Preserver of all things both visible and invisible”; BSR-AN-04 Outline of the Faith (BCP p. 846) — God : “the work of a single loving God who creates, sustains, and directs it” |  |
| Q-182 | Baptist | Preserver / Sustainer | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — Preserver of the  | STD+DIV | BSR-BA-01 II. God: “the Creator, Redeemer, Preserver, and Ruler of the universe”; BSR-BA-01 II.A. God the Father: “reigns with providential care over His universe, His creatures” |  |
| Q-183 | Methodist / Wesleyan | Preserver / Sustainer | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “the maker and preserver of all things, both visible and invisible”; BSR-MW-02 Article I — God: “Creator, Sovereign and Preserver of all things visible and invisible”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “the Creator and Preserver of all things” |  |
| Q-184 | Mennonite / Anabaptist | Preserver / Sustainer | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-02 Article I. Of God and the Creation of al: “He still governs and upholds the same and all His works”; BSR-MA-01 Article 5. Creation and Divine Providenc: “God preserves and renews what has been made”; BSR-MA-01 Article 5. Creation and Divine Providenc: “We acknowledge that God sustains creation in both continuity and change” |  |
| Q-185 | Roman Catholic | Governor / Ruler | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-03 Chapter I (English witness), paragraph 3: “God protects and governs by his providence all that He has created”; BSR-RC-02 Caput I — De Deo Rerum Omnium Creatore: “Universa vero, quae condidit, Deus providentia sua tuetur atque gubernat”; BSR-RC-01 CCC 302: “By his providence God protects and governs all things which he has made” |  |
| Q-188 | Reformed / Presbyterian | Governor / Ruler | CONFESSIONAL | Heidelberg Catechism — Lord's Days 9–10, Q&A 26–28 | TIER | BSR-RP-01 Chapter 5.1 — Of Providence: “doth uphold, direct, dispose, and govern all creatures, actions, and things”; BSR-RP-06 Article 13: The Doctrine of God's Provid: “leads and governs them according to his holy will”; BSR-RP-02 Shorter Catechism Q.11: “his most holy, wise and powerful preserving and governing all his creatures” |  |
| Q-190 | Baptist | Governor / Ruler | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — Ruler of the univ | STD+DIV | BSR-BA-01 II.A. God the Father: “God as Father reigns with providential care over His universe”; BSR-BA-01 II. God: “the Creator, Redeemer, Preserver, and Ruler of the universe”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “He hath most sovereign dominion over all creatures, to do by them” |  |
| Q-191 | Methodist / Wesleyan | Governor / Ruler | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-02 Article I — God: “rules with gracious regard for the well-being and salvation of men” | BSR-MW-04 Article 6. God’s Purpose for H REJECT/WRONG_SUBJECT; BSR-MW-02 Article XVI — Civil Government REJECT/WRONG_SUBJECT |
| Q-196 | Reformed / Presbyterian | Sovereign | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.2 — Of God, and of the Holy Tr: “hath most sovereign dominion over them, to do by them”; BSR-RP-01 Chapter 21.1 — Of Religious Worship, and: “there is a God, who hath lordship and sovereignty over all”; BSR-RP-03 Larger Catechism Q.101: “God manifesteth his sovereignty, as being JEHOVAH, the eternal, immutable, and almighty God” |  |
| Q-199 | Methodist / Wesleyan | Sovereign | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-02 Article I — God: “who is Creator, Sovereign and Preserver of all things visible and invisible”; BSR-MW-02 Article XVI — Civil Government: “civil government derives its just powers from the sovereign God”; BSR-MW-02 Article XV — The Christian and Property: “under the sovereignty of God” |  |
| Q-201 | Roman Catholic | Judge | CONFESSIONAL | Apostles' Creed (Vatican Credo) — He will come to judge the  | PARTIAL (lower tier) | BSR-RC-01 CCC 841: “the one, merciful God, mankind's judge on the last day”; BSR-RC-01 CCC 1040: “he will pronounce the final word on all history” |  |
| Q-206 | Baptist | Judge | CONFESSIONAL | Baptist Faith and Message 2000 — II.B. God the Son — will re | STD+DIV | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “most just and terrible in His judgments”; BSR-BA-01 X. Last Things: “Christ will judge all men in righteousness”; BSR-BA-01 II.B. God the Son: “He will return in power and glory to judge the world” |  |
| Q-209 | Roman Catholic | Savior | CONFESSIONAL | Apostles' Creed / Credo — Jesus Christ, salvific confession | PARTIAL (lower tier) | BSR-RC-01 CCC 207: “present to his people in order to save them” | BSR-RC-01 CCC 431 REJECT/WRONG_SUBJECT |
| Q-214 | Baptist | Savior | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — Redeemer; II.B re | STD+DIV | BSR-BA-01 II. God: “the Creator, Redeemer, Preserver, and Ruler of the universe”; BSR-BA-01 V. God’s Purpose of Grace: “He regenerates, justifies, sanctifies, and glorifies sinners”; BSR-BA-03 Fact 1: “the God who is revealed as Creator, Savior and Advocate” |  |
| Q-215 | Methodist / Wesleyan | Savior | CONFESSIONAL | EUB Confession of Faith — Article I | STD+DIV | BSR-MW-02 Article VIII — Reconciliation Through Ch: “God was in Christ reconciling the world to himself”; BSR-MW-04 Article 2. The Father, ¶212: “In love, He both seeks and receives penitent sinners”; BSR-MW-02 Article I — God: “rules with gracious regard for the well-being and salvation of men” |  |
| Q-216 | Mennonite / Anabaptist | Savior | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-01 Article 8. Salvation: “God offers salvation from sin and a new way of life to all people”; BSR-MA-01 Article 1. God: “has brought salvation and new life to humanity through Jesus Christ”; BSR-MA-02 Article II. Of the Fall of Man: “God, in compassion for His creatures, made provision for it” |  |
| Q-220 | Reformed / Presbyterian | Revealer | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-01 Chapter 1.1 — Of the Holy Scripture: “to reveal himself, and to declare that his will unto his church”; BSR-RP-05 Q&A 25 (Lord’s Day 8): “that is how God has revealed himself in his Word”; BSR-RP-06 Article 2: The Means by Which We Know Go: “God makes himself known to us more clearly by his holy and divine Word” |  |
| Q-222 | Baptist | Revealer | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — eternal triune Go | STD+DIV | BSR-BA-01 II. God: “The eternal triune God reveals Himself to us as Father, Son, and Holy Spirit”; BSR-BA-03 Fact 1: “the God who is revealed as Creator, Savior and Advocate” | BSR-BA-01 I. The Scriptures REJECT/WRONG_SUBJECT |
| Q-224 | Mennonite / Anabaptist | Revealer | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-01 Article 1. God: “God has spoken to humanity and related to us in many and various ways”; BSR-MA-01 Article 1. God: “God has spoken above all in the only Son, the Word who became flesh” |  |
| Q-228 | Reformed / Presbyterian | Fountain of being | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | MISS |  |  |
| Q-236 | Reformed / Presbyterian | Word / Logos | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-06 Article 8: The Trinity: “The Son is the Word, the Wisdom, and the image of the Father”; BSR-RP-06 Article 10: The Deity of Christ: “the one who is called God, the Word, the Son, and Jesus Christ already existed” |  |
| Q-240 | Mennonite / Anabaptist | Word / Logos | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-01 Article 2. Jesus Christ: “Jesus Christ, the Word of God become flesh”; BSR-MA-02 Article IV. The Advent of Christ into Th: “and the Word, Himself became flesh and man”; BSR-MA-01 Article 1. God: “the only Son, the Word who became flesh” |  |
| Q-244 | Reformed / Presbyterian | Wisdom | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-06 Article 8: The Trinity: “The Son is the Word, the Wisdom, and the image of the Father”; BSR-RP-04 Book of Confessions 8.13 (Theological De: “Christ Jesus, whom God made our wisdom, our righteousness and sanctification and redemption” |  |
| Q-260 | Reformed / Presbyterian | Image of the Father | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-06 Article 10: The Deity of Christ: “the exact image of the person of the Father”; BSR-RP-06 Article 8: The Trinity: “The Son is the Word, the Wisdom, and the image of the Father” |  |
| Q-265 | Roman Catholic | Giver of life | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Creed, Godhead an | STD+DIV | BSR-RC-06 Nicene Creed: “the Holy Spirit, the Lord, the giver of life”; BSR-RC-01 CCC 245: “We believe in the Holy Spirit, the Lord and giver of life”; BSR-RC-01 CCC 291: “the creative action of the Holy Spirit, the "giver of life"” |  |
| Q-266 | Eastern Orthodox | Giver of life | CONFESSIONAL | Nicene / Niceno-Constantinopolitan Creed — Nicene Creed, God | STD+DIV | BSR-EO-01 The Symbol of Faith — "Nicene Creed": “in the Holy Spirit, the Lord, the Giver of Life, who proceeds from the Father”; BSR-EO-04 Q.240 (On the Eighth Article): “he, together with God the Father and the Son, giveth life to all creatures” |  |
| Q-267 | Lutheran | Giver of life | CONFESSIONAL | Nicene Creed — Nicene Creed | STD+DIV | BSR-LU-01 Ecumenical Creeds: The Nicene Creed: “the Holy Ghost, the Lord and Giver of life” |  |
| Q-276 | Reformed / Presbyterian | Eternal power and might | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | TIER | BSR-RP-04 Book of Confessions 6.183 (Westminster C: “of the same substance and equal in power and glory” | BSR-RP-01 Chapter 2.3 — Of God, and of t REJECT/WRONG_SUBJECT |
| Q-289 | Roman Catholic | Unbegotten | CATECHETICAL | Compendium of the Catechism of the Catholic Church — Q47 — F | TIER | BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “The Father is from none, the Son from the Father alone”; BSR-RC-01 CCC 254: “It is the Father who generates, the Son who is begotten” |  |
| Q-290 | Eastern Orthodox | Unbegotten | CATECHETICAL | The Orthodox Faith, Vol. I — The Holy Trinity: One God, One  | TIER | BSR-EO-05 Decree 1: “the Father unbegotten”; BSR-EO-04 Q.94 (On the First Article): “God the Father is neither begotten, nor proceeds from any other Person” |  |
| Q-291 | Lutheran | Unbegotten | CONFESSIONAL | Athanasian Creed — Trinity and person/substance clauses | MISS |  |  |
| Q-292 | Reformed / Presbyterian | Unbegotten | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3 etc. | STD+DIV | BSR-RP-01 Chapter 2.3 — Of God, and of the Holy Tr: “the Father is of none, neither begotten, nor proceeding”; BSR-RP-04 Book of Confessions 6.013 (Westminster C: “The Father is of none, neither begotten nor proceeding”; BSR-RP-06 Article 8: The Trinity: “The Father is the cause, origin, and source of all things” |  |
| Q-293 | Anglican | Unbegotten | CONFESSIONAL | Creed of S. Athanasius, Book of Common Prayer — The Father i | STD | BSR-AN-03 Quicunque Vult (Creed of S. Athanasius),: “The Father is made of none: neither created, nor begotten” |  |
| Q-305 | Roman Catholic | Infinite | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-03 Chapter I (English witness), paragraph 1: “infinite in understanding, will and every perfection”; BSR-RC-02 Caput I — De Deo Rerum Omnium Creatore: “intellectu ac voluntate omnique perfectione infinitum”; BSR-RC-01 CCC 202: “one true God, eternal infinite (immensus) and unchangeable, incomprehensible, almighty and ineffable” |  |
| Q-306 | Eastern Orthodox | Infinite | CATECHETICAL | The Orthodox Faith, Vol. I — The Holy Trinity — Timeless, sp | TIER | BSR-EO-05 Decree 1: “one God, true, almighty and infinite, the Father, the Son and the Holy Spirit”; BSR-EO-04 Q.122 (On the First Article): “God, of his foreknowledge and infinite mercy, hath predestined” | BSR-EO-05 Decree 8 REJECT/WRONG_SUBJECT |
| Q-307 | Lutheran | Infinite | CONFESSIONAL | Augsburg Confession — Article I, God | STD | BSR-LU-01 Formula of Concord, Solid Declaration: I: “God, out of His infinite goodness and mercy, comes first to us” |  |
| Q-308 | Reformed / Presbyterian | Infinite | CONFESSIONAL | Westminster Shorter Catechism — Q&A 1 and 4–6 as applicable | TIER | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “who is infinite in being and perfection, a most pure spirit”; BSR-RP-03 Larger Catechism Q.7: “God is a Spirit, in and of himself infinite in being, glory, blessedness, and perfection”; BSR-RP-04 Book of Confessions 3.01 (Scots Confessi: “Who is eternal, infinite, immeasurable, incomprehensible, omnipotent, invisible” |  |
| Q-309 | Anglican | Infinite | CONFESSIONAL | Thirty-Nine Articles — Article I — infinite power, wisdom, a | STD+DIV | BSR-AN-01 Article I (1) — Of Faith In The Holy Tri: “of infinite power, wisdom, and goodness” |  |
| Q-310 | Baptist | Infinite | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — infinite in holin | STD+DIV | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “infinite in being and perfection”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “all infinite, without beginning, therefore but one God”; BSR-BA-01 II. God: “God is infinite in holiness and all other perfections” |  |
| Q-311 | Methodist / Wesleyan | Infinite | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-02 Article I — God: “He is infinite in power, wisdom, justice, goodness and love”; BSR-MW-01 Article I — Of Faith in the Holy Trinity: “of infinite power, wisdom, and goodness”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “unlimited in power, wisdom and goodness” |  |
| Q-312 | Mennonite / Anabaptist | Infinite | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995) — Arti | STD+DIV | BSR-MA-01 Article 1. God: “God's infinite freedom and constant self-giving are perfect in faithful love” | BSR-MA-02 Article I. Of God and the Crea REJECT/BELOW_FLOOR |
| Q-324 | Reformed / Presbyterian | Invisible | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “who is infinite in being and perfection, a most pure spirit, invisible”; BSR-RP-06 Article 1: The Only God: “there is a single and simple spiritual being, whom we call God— eternal, incomprehensible, invisible”; BSR-RP-04 Book of Confessions 5.015 (Second Helvet: “God is one in essence or nature, subsisting in himself, all sufficient in himself, invisible” |  |
| Q-331 | Lutheran | Incorporeal / without body | CONFESSIONAL | Augsburg Confession — Article I, God | MISS |  |  |
| Q-332 | Reformed / Presbyterian | Incorporeal / without body | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “a most pure spirit, invisible, without body, parts, or passions”; BSR-RP-04 Book of Confessions 5.015 (Second Helvet: “subsisting in himself, all sufficient in himself, invisible, incorporeal, immense, eternal” |  |
| Q-333 | Anglican | Incorporeal / without body | CONFESSIONAL | Thirty-Nine Articles — Article I | MISS |  |  |
| Q-335 | Methodist / Wesleyan | Incorporeal / without body | CONFESSIONAL | Articles of Religion of the Methodist Church — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “There is but one living and true God, everlasting, without body or parts”; BSR-MW-02 Article I — God: “the one true, holy and living God, Eternal Spirit” |  |
| Q-337 | Roman Catholic | Without parts / simple | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-02 Caput I — De Deo Rerum Omnium Creatore: “cum sit una singularis, simplex omnino et incommutabilis substantia spiritualis”; BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “three persons but one absolutely simple essence, substance or nature”; BSR-RC-03 Chapter I (English witness), paragraph 1: “He is a one unique, completely simple and unchangeable spiritual substance” |  |
| Q-339 | Lutheran | Without parts / simple | CONFESSIONAL | Augsburg Confession — Article I, Of God | MISS |  |  |
| Q-340 | Reformed / Presbyterian | Without parts / simple | CONFESSIONAL | Westminster Confession of Faith — Chapter II | STD | BSR-RP-06 Article 1: The Only God: “there is a single and simple spiritual being, whom we call God”; BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “a most pure spirit, invisible, without body, parts, or passions”; BSR-RP-04 Book of Confessions 6.011 (Westminster C: “a most pure spirit, invisible, without body, parts, or passions” |  |
| Q-341 | Anglican | Without parts / simple | CONFESSIONAL | Thirty-Nine Articles — Article I | MISS |  | BSR-AN-04 Outline of the Faith (BCP p. 8 REJECT/WRONG_SUBJECT |
| Q-343 | Methodist / Wesleyan | Without parts / simple | CONFESSIONAL | Articles of Religion — Article I | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “without body or parts” |  |
| Q-348 | Reformed / Presbyterian | Without passions / impassible | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “a most pure spirit, invisible, without body, parts, or passions; immutable, immense, eternal, incomprehensible, almighty”; BSR-RP-04 Book of Confessions 6.011 (Westminster C: “a most pure spirit, invisible, without body, parts, or passions, immutable, immense, eternal, incomprehensible” |  |
| Q-349 | Anglican | Without passions / impassible | CONFESSIONAL | Thirty-Nine Articles — Articles I–II | MISS |  |  |
| Q-353 | Roman Catholic | Immutable / unchangeable | CONCILIAR | Fourth Lateran Council — Constitution 1, Firmiter credimus | STD+DIV | BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “eternal and immeasurable, almighty, unchangeable, incomprehensible and ineffable”; BSR-RC-03 Chapter I (English witness), paragraph 1: “Since He is a one unique, completely simple and unchangeable spiritual substance”; BSR-RC-01 CCC 202: “there is only one true God, eternal infinite (immensus) and unchangeable” |  |
| Q-354 | Eastern Orthodox | Immutable / unchangeable | CATECHETICAL | The Orthodox Faith / Divine Liturgy — Ever-existing and eter | STD | BSR-EO-04 Q.86 (On the First Article): “unchangeable, all-sufficing to himself, all-blessed”; BSR-EO-02 The Holy Trinity — "The Three Divine Per: “ineffable, inconceivable, invisible, incomprehensible, ever-existing, and eternally the same” |  |
| Q-355 | Lutheran | Immutable / unchangeable | CONFESSIONAL | Formula of Concord, Solid Declaration — Divine nature: 'sinc | STD | BSR-LU-01 Formula of Concord, Solid Declaration: X: “who cannot deny Himself, because He is unchangeable in will and essence” | BSR-LU-01 Formula of Concord, Solid Decl REJECT/WRONG_SUBJECT; BSR-LU-01 Formula of Concord, Solid Decl REJECT/WRONG_SUBJECT |
| Q-356 | Reformed / Presbyterian | Immutable / unchangeable | CONFESSIONAL | Belgic Confession — Articles 1–2 and 8 | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “without body, parts, or passions; immutable, immense, eternal, incomprehensible”; BSR-RP-02 Shorter Catechism Q.4: “God is a spirit, infinite, eternal, and unchangeable, in his being”; BSR-RP-06 Article 1: The Only God: “eternal, incomprehensible, invisible, unchangeable, infinite, almighty” |  |
| Q-363 | Lutheran | Eternal | CONFESSIONAL | Athanasian Creed — Trinity and person/substance clauses | STD | BSR-LU-01 Augsburg Confession: Article I. Of God, : “there is one Divine Essence which is called and which is God: eternal”; BSR-LU-01 Ecumenical Creeds: The Athanasian Creed: “The Father eternal, the Son eternal, and the Holy Ghost eternal”; BSR-LU-01 Formula of Concord, Solid Declaration: I: “the eternal Father calls down from heaven concerning His dear Son” |  |
| Q-364 | Reformed / Presbyterian | Eternal | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | STD+DIV | BSR-RP-01 Chapter 2.1 — Of God, and of the Holy Tr: “immutable, immense, eternal, incomprehensible, almighty, most wise”; BSR-RP-06 Article 1: The Only God: “there is a single and simple spiritual being, whom we call God— eternal” |  |
| Q-366 | Baptist | Eternal | CONFESSIONAL | Baptist Faith and Message 2000 — II. God — eternal triune Go | STD+DIV | BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “who is immutable, immense, eternal, incomprehensible, almighty, every way infinite”; BSR-BA-01 II. God: “The eternal triune God reveals Himself to us as Father, Son, and Holy Spirit”; BSR-BA-02 Chapter 2 (Of God and the Holy Trinity),: “of one substance, power, and eternity, each having the whole divine essence” |  |
| Q-367 | Methodist / Wesleyan | Eternal | CONFESSIONAL | Confession of Faith of the Evangelical United Brethren Churc | STD+DIV | BSR-MW-01 Article I — Of Faith in the Holy Trinity: “There is but one living and true God, everlasting, without body or parts”; BSR-MW-02 Article I — God: “the one true, holy and living God, Eternal Spirit, who is Creator”; BSR-MW-04 Article 1. Faith in the Holy Trinity, ¶2: “the one living and true God, both holy and loving, eternal, unlimited in power” |  |
| Q-369 | Roman Catholic | Incomprehensible | CONCILIAR | First Vatican Council, Dei Filius — Chapter I, God the Creat | STD+DIV | BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “eternal and immeasurable, almighty, unchangeable, incomprehensible and ineffable”; BSR-RC-03 Chapter I (English witness), paragraph 1: “almighty, eternal, immeasurable, incomprehensible, infinite in understanding, will and every perfection” |  |
| Q-372 | Reformed / Presbyterian | Incomprehensible | CONFESSIONAL | Westminster Confession of Faith — Chapters II.1–3; III; V; V | TIER | BSR-RP-03 Larger Catechism Q.7: “God is a Spirit, in and of himself infinite in being”; BSR-RP-04 Book of Confessions 3.01 (Scots Confessi: “eternal, infinite, immeasurable, incomprehensible, omnipotent, invisible”; BSR-RP-06 Article 1: The Only God: “eternal, incomprehensible, invisible, unchangeable, infinite, almighty” |  |
| Q-376 | Mennonite / Anabaptist | Incomprehensible | CONFESSIONAL | Confession of Faith in a Mennonite Perspective (1995), Artic | STD+DIV | BSR-MA-02 Article I. Of God and the Creation of al: “one eternal, almighty, and incomprehensible God, the Father, Son, and Holy Ghost”; BSR-MA-01 Article 1. God: “God far surpasses human comprehension and understanding” | BSR-MA-02 Article XVIII. Of the Resurrec REJECT/WRONG_SUBJECT |
| Q-377 | Roman Catholic | Ineffable | CONCILIAR | Fourth Lateran Council — Constitution 1, Firmiter credimus | STD+DIV | BSR-RC-04 Canon 1 (Confession of Faith), paragraph: “eternal and immeasurable, almighty, unchangeable, incomprehensible and ineffable”; BSR-RC-01 CCC 202: “incomprehensible, almighty and ineffable, the Father and the Son and the Holy Spirit”; BSR-RC-01 CCC 206: “his name is ineffable, and he is the God who makes himself close” |  |
| Q-388 | Reformed / Presbyterian | Inscrutable | CONFESSIONAL | Scots Confession — 3.01–3.25; especially chapter 1 | STD+DIV | BSR-RP-04 Book of Confessions 3.01 (Scots Confessi: “to be ruled and guided by his inscrutable providence”; BSR-RP-01 Chapter 3.7 — Of God’s Eternal Decree: “according to the unsearchable counsel of his own will”; BSR-RP-01 Chapter 5.4 — Of Providence: “the almighty power, unsearchable wisdom, and infinite goodness of God” |  |
| Q-433 | Roman Catholic | Without separation | CATECHETICAL | Third Council of Constantinople / CCC restatement — CCC 475 | STD | BSR-RC-01 CCC 467: “in two natures without confusion, change, division or separation”; BSR-RC-01 CCC 469: “Jesus is inseparably true God and true man”; BSR-RC-07 Compendium Q.87: “Jesus is inseparably true God and true man in the unity” |  |
| Q-434 | Eastern Orthodox | Without separation | CONCILIAR | Third Council of Constantinople — Sixth Ecumenical Council | STD+DIV | BSR-EO-06 Church History — Fifth Century — "The Fo: “without change, without confusion, without division, without separation”; BSR-EO-04 Q.182 (Of the Son of God): “There are in him, without separation and without confusion, two natures”; BSR-EO-06 Church History — Fifth Century — "The Fo: “neither changed, nor confused, nor separated, nor divided” |  |
