# Gate 6 — session 3 report (2026-09-13): PDF extraction, auditable empties, caveat slice, Lutheran and Reformed / Presbyterian

**Code · workbook v2.25r4 GATE6 SCOPE RATIFIED · run live-1 · packets `recovery-packets/{roman-catholic,lutheran,reformed-presbyterian}.json`**

Stopped after the two branches, as instructed. Baptist, Methodist / Wesleyan, Mennonite / Anabaptist and Eastern Orthodox
have not run.

## Start-up: the open-cell rule is a workbook fact

`registry.gate6_scope` reads `gate6_open_cell_rule`, `gate6_closed_states` and `gate6_open_cell_count` from APP CONFIG and
`run.py` refuses to start unless the harness's computed open set equals the ratified count. Every run this session logged:

    456 = 291 open + 24 closed + 141 released; closed by state {VECTOR PENDING 9, retired 3, VECTOR COMPLETE 3, PENDING REVIEW 1, OUT OF SCOPE 8}

The v2.25r3 workbook (no keys) fails the assertion, which is the point of it.

## Task 1 — PDF audit, per row (`recovery-runs/pdf-audit.md`)

Three chunkings of every row through its own adapter and the same fetch cache: LEGACY (the path the earlier branches ran on),
REPAIRED (this session's path), STORED (the chunk store now). No model calls.

| row | measured source | verdict | LEGACY defects | LEGACY → REPAIRED | re-chunked |
|---|---|---|---|---|---|
| BSR-AN-04 (Episcopal BCP catechism) | PDF text layer | **AFFECTED** | even-page footer "846 Catechism" spliced into 7 chunks and 2 locators, once mid-sentence ("bishops, 860 Catechism priests, and deacons") | 7 chunks changed, 2 locators renamed | yes |
| BSR-AN-05 (ACNA To Be a Christian) | PDF text layer | **AFFECTED** | 55 soft-hyphen line breaks ("cove nantal", "Philip pians"); 269 running-header lines spliced ("the ten commandments", "believing in christ"); 24 intra-word split candidates | 120 chunks changed; 12 evidence joins made (6 "cove nant", 5 "Chris tian", 1 "cove nantal" by stem); 0 residual | yes |
| BSR-LU-02 (LCMS file viewer) | no text by policy | NO_TEXT | — | — | no |
| BSR-RP-04 (PC(USA) Book of Confessions) | PDF text layer | **AFFECTED** | `[TEXT]` title markers and the stacked Westminster column header ("Presbyterian Church / in the United States / The United Presbyterian Church / in the United States of America") spliced into 74 chunks, mid-sentence at 6.006 | 60 chunks changed | yes |
| BSR-MW-03 (GMC 2024 BDD) | PDF text layer | CLEAN | none | 0 | no |
| BSR-MA-01 (Mennonite 1995) | HTML pages | HTML_SOURCED | none | 0 | no |
| BSR-MA-02 (Dordrecht) | HTML page | HTML_SOURCED | none | 0 | no |
| BSR-EO-08, BSR-EO-09 (ROEA PDFs) | PDF text layer | CLEAN | none | 0 | no |

BSR-AN-04 was **not** clean: the adapter stripped the odd-page header "Catechism 847" but not the even-page footer
"846   Catechism". BSR-MW-03's Article I reads "of infinite power, wisdom, and good" in all three chunkings and the
"goodness" variant appears nowhere. The registry says "PDF" for BSR-MA-01 and BSR-MA-02, but their adapters read HTML pages;
they were scanned and are unaffected. The Anglican branch was not re-run; its packet's phrases were asserted against the old
AN-04/AN-05 chunks and would now fail the hash check if rebuilt, so it stands as accepted.

The furniture rule: a line (digits folded) recurring in the top or bottom three lines of at least 3 pages, with at least 75%
of its full-line occurrences in that zone, at most 10 words, no terminal punctuation, not opening with a conjunction —
detection repeated on the peeled pages. "Q." (13 of 124 occurrences at a page top) and "Amen." (18 of 85) are never touched.
Intra-word joins need evidence: the closed form is a word of the document or of the ratified corpus and neither fragment
occurs outside such splits; or the left fragment already has two attested joins and the right fragment extends the stem by at
most four letters. Every removed line and every join is written to the manifest notes.

## Task 2 — auditable empties

- `empty_result_option.standards_reviewed` is now a list of `{registry_id, coverage, supplied, of, share, status, silence_rationale}`;
  status is REVIEWED WHOLE, EXHAUSTED or SAMPLED.
- NOT LOCATED — CURRENT STANDARD REVIEWED is offered only when every consulted standard is FULL or EXHAUSTED; otherwise the
  card names the sampled standard, its share, and the honest state NOT LOCATED — NOT YET RECOVERED.
- Locator prompt gate6-v1.4: an empty reply carries a one-sentence `silence_rationale`. Where candidates were found and refused,
  the rationale is the verifier's reason codes.
- Exhaustion (2c): where a cell would go empty and a standard was sampled, the locator continues over that standard's
  unretrieved chunks in ranked batches within the ordinary budget, four batches per standard per round, until every chunk has
  been supplied or a candidate survives verification.

**What 2c cost and changed.** Lutheran: 9 of 39 cells entered exhaustion (the Book of Concord, 738 chunks, is retrieved at
60k characters per call, so every Lutheran cell samples it); 195 locator calls + 27 verifier calls = **16.49 USD, 1.83 USD per
entered cell**; it changed **7 of the 9** from empty to filled (Q-003, Q-019, Q-091, Q-259, Q-347, Q-379, Q-403); the two that
stayed empty (Q-323 Invisible, Q-451 Greater dissimilarity) had the Book of Concord fully exhausted (27 of 27 batches) and
carry REVIEWED with a rationale per standard. Reformed / Presbyterian: no cell entered exhaustion (every cell had a surviving
pass-1 candidate), so 2c cost nothing there. The 7-of-9 figure is the finding: on a 1.6-million-character standard the sampled
retrieval was missing evidence that a full read finds. The seven are candidates for the author's first read; two of them are
scripture quotations inside the standard (Q-003 "As I live, saith the Lord God", Apology X; Q-403 "How unsearchable are His
judgments", Formula SD XI) and one rests on the Large Catechism's "mirror of the paternal heart" (Q-259).

## Task 3 — caveat slice

Route CAVEATED_ACCEPT: after the primary verdicts the cell is allocated, and every candidate that would reach the card whose
primary verdict is ACCEPT_WITH_CAVEAT at a PARTIAL floor or raising SEMANTIC_FLOOR / SAME_WORD_DIFFERENT_MEANING goes to opus;
repeated until the card is stable.

| branch | caveated accepts sent to opus | calls | cost | overturned |
|---|---|---|---|---|
| Lutheran | 17 | 17 | 1.83 USD | 0 |
| Reformed / Presbyterian | 17 | 17 | 1.50 USD | 0 |

Opus confirmed all 34 (15 + 15 ACCEPT_WITH_CAVEAT, 2 + 2 upgraded to ACCEPT). The overturn rate on this path is 0.00 over 34
candidates, so there is no finding against the primary verifier from these two branches. Where opus did change outcomes it was
the other direction: on the PRIMARY_REJECTED_ALL route it rescued 3 Lutheran candidates (Q-147 "who is over all, God blessed
forever"; Q-347 "the divine nature can neither suffer nor die"; Q-403 above) and 5 Reformed / Presbyterian candidates that
sonnet had refused (WRONG_SUBJECT / BELOW_FLOOR). Those rescues, not the caveated accepts, are where a second read matters.

A defect surfaced and was fixed mid-run: the first Lutheran pass skipped re-ingesting an opus verdict that was still pending
from an earlier round, so 29 cells finalised on the primary verdict. The loop was stopped, the condition fixed, and every cell
re-entered; the 12 answered opus calls were served from the audit log at no cost and none of the 29 changed.

## Task 4 — Roman Catholic rebuilt (no model calls)

Rebuilt from the stored candidates, verdicts and coder proposals under the 1a/1b allocator. **14 cells reordered**:
Q-017, Q-073, Q-121, Q-177, Q-193, Q-225, Q-281, Q-297, Q-313, Q-329, Q-345, Q-361, Q-385, Q-401. **12 cells now pair
BSR-RC-02's Latin with BSR-RC-03's English on one card** (Q-017, Q-073, Q-177, Q-193, Q-225, Q-297, Q-313, Q-329, Q-345,
Q-361, Q-385, Q-401). The four cells the review named as witness-led (Q-281, Q-297, Q-385, Q-401) now lead with BSR-RC-04 or
BSR-RC-02. In Q-121 the English witness paired with the RC-02 Caput I candidate that the cap then cut, so it is recorded as a
cut witness, not shown; in Q-281 there is no RC-02 candidate, so RC-03 stays a plain witness, sorts last within CONCILIAR and
is cut by the cap. The packet header records `rebuilt_from`; the Task 3 slice did not run on these stored verdicts.

## The four derived translation pairs — for ratification one by one

| pair | rule the code applied | evidence, verbatim from the registry | weakness |
|---|---|---|---|
| BSR-RC-03 → BSR-RC-02 | SHARED_TITLE_TOKEN | titles share `filius`: "*Dei Filius* English (EWTN)" / "Vatican I, *Dei Filius* (Latin, official)" | nothing in the row text names RC-02; the link is one title word |
| BSR-RC-05 → BSR-RC-04 | SHARED_TITLE_TOKEN | titles share `fourth`, `lateran`: "Fourth Lateran (Fordham sourcebook)" / "Fourth Lateran Council, canons 1-2 (Firmiter credimus; Damnamus ergo)" | as above; RC-05 has no corpus (LINEAGE), so the pair never fired |
| BSR-EO-11 → BSR-EO-06 | NAMED_IN_NOTE | reception_note: "…BSR-EO-06 remains the controlling conciliar text." | none: the note states control explicitly |
| BSR-EO-13 → BSR-EO-06 | NAMED_IN_NOTE | reception_note: "…Registered as its own row rather than as a second domain on BSR-EO-06, following the BSR-RC-05 pattern…" | the note MENTIONS EO-06 but does not say it controls; the code's rule counts any mention, so this pair rests on a registration remark, not a statement of control — weaker than it looks |

Recommendation: ratify EO-11 → EO-06 and RC-03 → RC-02 as they stand (the RC pairing is confirmed by 12 cells of matching
chapter locators); RC-05 → RC-04 is moot until RC-05 has text; EO-13 → EO-06 should not be acted on unless the author writes
the control relation into the EO-13 note. Nothing was acted on for Eastern Orthodox.

## Packets

| branch | cells | filled | honest empties | all-rejected | REVIEWED offered | rejections kept | dropped at build |
|---|---|---|---|---|---|---|---|
| Lutheran | 39 | 37 | 2 | 0 | 2 of 2 | 25 | 0 |
| Reformed / Presbyterian | 16 | 16 | 0 | 0 | — | 162 | 0 |

Lutheran final verdicts: 24 ACCEPT, 45 ACCEPT_WITH_CAVEAT, 18 REJECT (opus adjudicated 23). Reformed / Presbyterian: 18
ACCEPT, 29 ACCEPT_WITH_CAVEAT, 28 REJECT (opus 21). Every phrase was re-asserted at build; 0 dropped. Rejections carry rubric,
chunk context and reason code.

## How the Reformed / Presbyterian tie was ordered

All six rows are CONFESSIONAL and none is a witness, so 1a's witness-last rule had nothing to sort and the order fell entirely
to the residual tie-break: the slotting order — each standard's guaranteed (best) candidate in **registry row order**, then the
extra slots by floor claim and locator rank. The packet's `ordering` string now says so. The result: BSR-RP-01 (Westminster
Confession, OPC) leads 14 of 16 cards; 9 cards read RP-01, RP-02, RP-03 exactly; BSR-RP-04 (the PC(USA) Book of Confessions)
leads only Q-268 and BSR-RP-02 leads Q-212; 40 of the 47 kept candidates are guaranteed slots. That is a consequence of row
position in the registry, not of any judgement about the standards, and the author should say whether registry row order is
the tie-break he wants inside one tier (the alternative is the verifier's floor, FULL before PARTIAL, which would still leave
most cards unchanged).

## Cost

| branch | cells | calls | USD | per cell | Anglican rate | of which 2c | of which Task 3 |
|---|---|---|---|---|---|---|---|
| Lutheran | 39 | 457 | 23.91 | 0.613 | 0.336 | 16.49 | 1.83 |
| Reformed / Presbyterian | 16 | 301 | 15.18 | 0.949 | 0.336 | 0.00 | 1.50 |
| both | 55 | 758 | 39.09 | 0.711 | 0.336 | 16.49 | 3.33 |

Against the roughly 19 USD the author expected at the Anglican rate: Lutheran without exhaustion would have been 7.42 USD
(0.19 per cell, two standards per cell); the 16.49 USD is the price of reading the Book of Concord to the end for nine cells,
and it changed seven of them. Reformed / Presbyterian's rate is the shape of its registry — six standards per cell, three of
them 60k-character retrieved contexts (RP-01, RP-03, RP-04) — so its locator alone cost 10.71 USD; no exhaustion, no empties.
One stray Lutheran coder answer (0.01 USD) from the interrupted round was paid for and never consumed. Caps: Lutheran 40 USD,
Reformed / Presbyterian 25 USD, neither reached; cost-state.json carries both branches as DONE.

## Not done, deliberately

- Anglican not re-run (7 of 148 verdicts touched AN-05; the author's call).
- No branch beyond the two named.
- Nothing written to the workbook; the EO pairs not acted on.
