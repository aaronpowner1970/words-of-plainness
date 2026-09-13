# Gate 6 — session 4 report (2026-09-13): slot diversity, the lower floor, the formula hazard, exhaustion marks, Baptist / Methodist / Mennonite

**Code · workbook v2.25r4 GATE6 SCOPE RATIFIED (unchanged; 47 rows, 45 ratified) · run live-1 · packets `recovery-packets/*.json`**

Answers `docs/gate6/WoP_SJN_LU_RP_Packet_Review_20260913.md` (copied in at Step 0). Nothing written to the workbook. No bot
challenge defeated, no blocked host routed around. Eastern Orthodox did not run. Every `run.py` start asserted the ratified
scope from APP CONFIG: `456 = 291 open + 24 closed + 141 released`.

Tasks 1, 2 and 4 are deterministic rebuilds of the four stored packets (`run.py --rebuild-packet-only`, no model calls),
diffed against the committed packets by `rebuild_diff.py` → `recovery-runs/live-1/rebuild-diff-20260913.md`. The first model
call of the session was Task 5.

## Task 1 — candidate-slot diversity (RATIFIED rule, implemented in `allocation.py`)

Within an authority-tier tie the survivors are grouped by the body the row speaks for; no group takes a second slot until
every group with a surviving verified candidate has taken a first; groups are ranked for their first slot by the existing
keys (non-witness before witness, then the locator's floor claim); registry row order is the last resort and orders
presentation only. Group by `speaks_for`, resolved per row; every packet header carries the resolution table.

**How each `speaks_for` was resolved** (rule in brackets; the table is `speaks_for_groups` in the packet):

| branch | row | speaks_for as written | group | rule |
|---|---|---|---|---|
| Reformed | BSR-RP-01 | OPC and Westminster churches | opc and westminster churches | VERBATIM |
| Reformed | BSR-RP-02, BSR-RP-03 | **as above** | opc and westminster churches | AS_ABOVE_PREVIOUS_ROW — resolved to the nearest preceding row of the branch that names a body (RP-01) |
| Reformed | BSR-RP-04 | PC(USA); "subordinate standards" affirmed at ordination | pc(usa) | BODY_BEFORE_SEMICOLON ("PC(USA)" keeps its parenthesis: a parenthetical glued to a word is a name) |
| Reformed | BSR-RP-05 / BSR-RP-06 | CRCNA and RCA / CRCNA and RCA; Dort required subscription | crcna and rca | VERBATIM / BODY_BEFORE_SEMICOLON — one body, the Three Forms |
| Anglican | BSR-AN-01 / 02 / 03 | Church of England; received across the Communion / Church of England / Church of England (appointed in the BCP) | church of england | BODY_BEFORE_SEMICOLON / VERBATIM / PARENTHETICAL_STRIPPED |
| Anglican | BSR-AN-04 | The Episcopal Church (certified Standard Book) | the episcopal church | PARENTHETICAL_STRIPPED |
| Anglican | BSR-AN-05 | Anglican Church in North America (College of Bishops) | anglican church in north america | PARENTHETICAL_STRIPPED (fallback row; the fallback guard runs first) |
| Roman Catholic | BSR-RC-01/02/04/06/07 | Universal Church | universal church | VERBATIM |
| Roman Catholic | BSR-RC-08 | Universal Church; published by the Holy See's Dicastery for Communication | universal church | BODY_BEFORE_SEMICOLON |
| Roman Catholic | BSR-RC-03, BSR-RC-05 | — (witness rows) | universal church | **WITNESS_OF_CONTROLLING_ROW** — a translation witness speaks for the body of its controlling row (RC-02, RC-04; the derived pairs in the header) |
| Lutheran | BSR-LU-01 | Lutheran churches subscribing the Book of Concord | (as written) | VERBATIM |
| Lutheran | BSR-LU-02, BSR-LU-03 | LCMS | lcms | VERBATIM |

One resolution is mine, not the author's, and is flagged: a witness row has no body of its own ("—"). On the first rebuild I
let it stand as its own group, and on Roman Catholic an unpaired second RC-03 witness then took a first slot on five cards
ahead of the Universal Church's second candidate — the witness-led shape the RC review rejected. A translation witness reads
its controlling row's text in English, so it speaks for that body; under that resolution Roman Catholic is unchanged. Groups
with no derivable controlling row (none today) stay their own group and sort last.

**Rebuild result, per branch** (`rebuild-diff-20260913.md`; "lead changed" counts only Task 1 effects — a lead that changed
because the lower-floor rule removed the old lead is listed under Task 2):

| branch | cards that changed lead | cards that gained a body the cap had cut | candidates added to a card | of which not yet coded |
|---|---|---|---|---|
| Anglican | 0 | 0 | 0 | 0 |
| Roman Catholic | 0 | 0 | 0 | 0 |
| Lutheran | 0 | 0 | 0 | 0 |
| Reformed / Presbyterian | 0 | **10** (Q-004, Q-012, Q-020, Q-204, Q-284, Q-316, Q-412, Q-420, Q-428, Q-436) | 18 | 18 |

Reformed / Presbyterian before → after: bodies present on cards — Westminster 15 → 14 cards (Q-380 emptied, below), PC(USA)
8 → 14, the Three Forms 3 → 11. Kept candidates by row: RP-01 14 → 13, RP-02 10 → 2, RP-03 12 → 2, RP-04 8 → 16, RP-05 0 →
7, RP-06 3 → 4. BSR-RP-01 still leads 13 of 15 filled cards: the group rule decides which bodies are heard, not which body
speaks first, and among first slots the Westminster Confession's FULL floor claims sort before the others' (floor claim
precedes row order). The 18 candidates that entered cards were never coded (the coder ran only on the old allocation, fix
1c); each carries `coder_note` and would be coded by re-running the branch (18 coder calls, about 0.20 USD). Anglican: the
three Church of England rows against TEC and ACNA were already spread by tier (CONFESSIONAL AN-01/AN-03 over CATECHETICAL
AN-02/AN-04), so the rule changed nothing. Lutheran has one body per tier. Roman Catholic has one body.

## Task 2 — the lower floor is final (`agents.finalize`; rule `LOWER_FLOOR_2026-09-13`)

2a: where the two models return different floors for one candidate, the LOWER floor is final and the verdict is recomputed
at that floor by the same rule `verify()` applies; never averaged, never the adjudicator's. 2b: opus stays on the reject-all
and slice routes and still adjudicates lines 1–3 — a rescue for subject or speech act stands; a rescue by a higher floor does
not. 2c: caveated accepts are no longer routed for adjudication; a deterministic sample of at most 20% of those that reach a
card (hash bucket plus a running per-branch quota) goes to opus for disclosure, shown on the card as `caveat_sample`, and can
lower a floor but never raise a verdict. Every stored verdict of the four branches was re-finalised from its rubrics; the
live run's verdict is kept beside it as `final_at_run`.

**One thing to rule on.** The instruction says Q-403 came through the caveated-accept adjudication. It did not: the packet
records it as `PRIMARY_REJECTED_ALL` — sonnet rejected all four exhaustion candidates in that cell, opus rescued the fourth at
PARTIAL over sonnet's WORD_ONLY. The session-3 report listed it among the three Lutheran rescues. So the case that motivated
2a IS a reject-all rescue, and 2a as written ("where two models return different floors … take the LOWER floor") is applied
on every route. That is the reading that gets Q-403 off the card, and it is the conservative one; its price is that most of
the earlier opus rescues were floor rescues:

| route | floor disagreements in the four branches | final floor lowered | candidates refused by the rule | of which opus rescues |
|---|---|---|---|---|
| PRIMARY_REJECTED_ALL | 13 | 13 | 8 (Q-147, Q-403, Q-380 ×5, Q-213 AN-02) | 8 |
| SLICE_ROW (BSR-AN-05) | 3 | 2 | 1 (Q-085 AN-05 Q.106) | 1 |
| CAVEATED_ACCEPT (retired) | 6 | 3 | 0 | — |

Of the eight rescues the session-3 report credited to the reject-all route on Lutheran and Reformed, seven were sonnet
WORD_ONLY / opus PARTIAL and are refused now; the one that stands is Q-347 (sonnet PARTIAL but WRONG_SUBJECT, opus FULL — a
subject rescue, kept at PARTIAL). Anglican loses two more of the same shape (Q-213 AN-02, Q-085 AN-05). If the author wants
the reject-all route exempt from 2a, it is one condition in `finalize` and a free rebuild; I did not do it because 2a is
unconditional and Q-403 sits on that route.

**Cells whose state changed:**

| cell | branch | predicate | before → after | candidate(s) dropped (floors sonnet / opus) |
|---|---|---|---|---|
| Q-147 | Lutheran | Blessed | FILLED → EMPTY (all-rejected) | Formula SD VIII ¶6–10 "who is over all, God blessed forever" (WORD_ONLY / PARTIAL) |
| Q-403 | Lutheran | No adequate likeness or comparison | FILLED → EMPTY (all-rejected; Book of Concord exhausted, REVIEWED offered) | Formula SD XI ¶61–66 "How unsearchable are His judgments …" (WORD_ONLY / PARTIAL) |
| Q-380 | Reformed | Ineffable | FILLED → EMPTY (all-rejected) | WCF 2.1 "immutable, immense, eternal, incomprehensible …"; Second Helvetic 5.016 "begotten by an ineffable generation" and 5.062 "in an inexpressible manner"; Belgic 1 "eternal, incomprehensible" and 13 "so great and incomprehensible" (all WORD_ONLY / PARTIAL) |

**Candidates dropped off a card in cells that stay filled:** Q-085 Anglican (AN-05 Q.106 "All sin is opposed to the
righteousness of God", WORD_ONLY / PARTIAL; two AN-05 candidates remain) and Q-213 Anglican (AN-02 Q.4 "through Jesus Christ
our Saviour", WORD_ONLY / FULL — the card's lead moves from BSR-AN-02 to BSR-AN-04, the only lead change in the session).
Verdict labels also moved without changing a card: seven candidates that opus had upgraded to ACCEPT return to
ACCEPT_WITH_CAVEAT at the primary's PARTIAL (Q-085 AN-05-3, Q-213 AN-04-1, Q-019, Q-227, Q-020, Q-428, Q-436). Nothing on the
retired caveated-accept route dropped: opus never set a floor below sonnet's there, which is the 0-of-34 finding restated.

Two of the three emptied cells are honest empties of the weaker kind. Q-403's Book of Concord was exhausted, so REVIEWED is
offered. Q-147 and Q-380 never entered exhaustion (they had a surviving candidate when they ran), so their cards say NOT LOCATED
— NOT YET RECOVERED with the sampled shares (Q-147: LU-01 3%; Q-380: RP-01 88%, RP-03 68%, RP-04 11%). Re-running the two
branches would enter exhaustion for exactly these two cells; not done (model calls).

## Task 3 — an oath formula is not a predication (verifier prompt gate6-v1.2)

Hazard `IDIOM_OR_FORMULA`: the phrase is, or lies inside, a fixed idiom, oath, doxology, greeting or liturgical formula whose
surface wording names the predicate while the passage's actual assertion lies elsewhere. The verifier also answers
`asserted_outside_formula` (Y/N/NA); raising the flag caps the floor at WORD_ONLY in code unless that line is Y, with the
model's own floor kept as `floor_model` / `floor_capped_by`. Applied to every verifier call from Task 5 onward (a new prompt
version means a new call identity; nothing stored was re-run).

**Q-003 (Lutheran, Living) is the case that motivated it and is flagged for the author's ruling on that cell directly.** The
Apology X quoting Ezekiel 33:11 "As I live, saith the Lord God" stands on the card as an exhaustion-sourced ACCEPT_WITH_CAVEAT
at PARTIAL (sonnet: SLOGAN_COMPRESSION; opus: SEMANTIC_FLOOR — "presupposed rather than asserted"); under the new hazard it
would be capped WORD_ONLY and refused. I did not re-run it.

## Task 4 — exhaustion marked; BSR-LU-02 on the branch record

4a. Every exhaustion-sourced candidate carries `found_in_exhaustion: true` and an `exhaustion_note` naming the batch
("FOUND IN EXHAUSTION: located in batch 22 of 27 over the chunks of BSR-LU-01 that the sampled retrieval did not supply …");
each card lists `exhaustion_sourced_candidates` and the header counts them. Lutheran after the rebuild: 8 such candidates on 6
cards (Q-003, Q-019, Q-091, Q-259, Q-347, Q-379 ×3); exhaustion now changes 6 cells, not 7 (Q-403 fell to Task 2).

4b. The packet header now says `branch_ran_on: "2 of 3 ratified rows: BSR-LU-02 had no text (AUTHORITY_URL_ONLY)"` with the
manifest note, and the same field names BSR-RC-05 (LINEAGE, no corpus) on Roman Catholic and will name BSR-BA-02 on Baptist.

**What blocks the text.** The ratified URL `files.lcms.org/file/preview/96D5ADA9-…` returns HTTP 200 and 6,013 bytes of
HTML that is a React application shell: title "LCMS Document Library", "You need to enable JavaScript to run this app", two
script bundles (`/static/js/5.…chunk.js`, `main.…chunk.js`), a Google Tag Manager iframe, and no document text, PDF link,
`<embed>` or `<object>`. The response's Content-Security-Policy allows frames from `view.officeapps.live.com` and connections
to the site's own API, so the document is rendered client-side through a viewer after the app loads; the text is reachable
only by executing the application, which the policy forbids (AC-08; "PDF behind client viewer" is accurate). The short link
the LCMS beliefs page uses for the same file, `files.lcms.org/f/the-augsburg-confession`, returns the same shell.

**Whether lcms.org exposes it any other way.** `lcms.org/about/beliefs` links "Augsburg Confession" to that preview URL, and
`lcms.org/about/beliefs/lutheran-confessions` links each Book of Concord document to a `files.lcms.org/f/…` short link (the
Augsburg Confession, its Apology, the Large Catechism, the Smalcald Articles, the Treatise, the Epitome and Solid Declaration)
and the Small Catechism to `catechism.cph.org`; neither page prints any confessional text. Nothing on lcms.org serves the
Augsburg Confession as plain HTML or as a direct PDF that a plain fetch receives.

**Recoverable or retire.** Not recoverable as a text row under the standing policy: no plain-fetch text exists on the admitted
host and every route to it runs through the viewer. The row's own draft recommendation was "INCLUDE as authority/adoption URL
only" and that is what it has been: it registers the LCMS's adoption of the Augsburg Confession; the text the branch cites is
BSR-LU-01 (bookofconcord.org). Recommendation: keep BSR-LU-02 as an adoption/provenance row and make that explicit in the
registry (a reception_note "adoption URL only; text cited from BSR-LU-01"), or retire it from the citable set — either way the
packet now says on its face that Lutheran ran on two rows. Not acted on.

## Task 5 — planted re-validation fa-3 (both models, verifier gate6-v1.2, the lower-floor rule)

| model | planted | false accepts | rate | Dositheus | Dositheus false accepts |
|---|---|---|---|---|---|
| sonnet | 74 | 0 | 0.000 | 23 | 0 |
| opus | 74 | 0 | 0.000 | 23 | 0 |
| routed (final) | 74 | 0 | 0.000 | 23 | 0 |

148 calls, **7.57 USD** (sonnet 1.15, opus 6.41 — the "both models on every item" instruction is what costs; fa-2 was 6.80).
Floor disagreements on the planted set: 0, so the lower-floor rule changed no planted outcome. IDIOM_OR_FORMULA was raised on
8 rubrics (5 items: PNM-004, -019, -021, -038, -072 — doxologies and titles) and capped nothing, because every one was already
WORD_ONLY; on PNM-072 opus answered `asserted_outside_formula: Y` and the rubric still rejected on the subject line.

**Planted recall.** Not measurable on this fixture: all 74 items are near-misses with no true positives, so there is no
recall to move. The recall cost of the rule was measured instead where it can be, for free: cal-3's 141 released cells,
re-finalised from their stored rubrics (`recall_recompute.py` → `recovery-runs/cal-3/lower-floor-recall-20260913.json`).
Same-standard recall **0.929 → 0.915** (131 → 129 of 141); 7 candidates refused, 2 cells lost — Q-155 Lutheran *Glorious*
and Q-215 Methodist / Wesleyan *Savior* — both opus floor rescues; still above the 0.8 gate. That is the figure to weigh
against the nine refused rescues above before deciding whether the reject-all route should be exempt.

## Task 6 — Baptist, Methodist / Wesleyan, Mennonite / Anabaptist

Run in that order by `branch_loop.py`, cap 25 USD per branch through `cost-state.json`, exhaustion on, verifier gate6-v1.2,
the lower-floor rule, the 2c sample. Packets `recovery-packets/{baptist,methodist-wesleyan,mennonite-anabaptist}.json`.

**Registry notes for the next session (not edited in the workbook).** BSR-BA-02 (1689 Confession, the1689confession.com)
has no corpus: the apex host 301s onto `www.` and the corpus builder refuses a cross-host hop, so Baptist ran on BSR-BA-01
(Baptist Faith and Message 2000) and BSR-BA-03 (ABC-USA "10 facts", OFFICIAL_EXPOSITION, descriptive) — the packet header says
so (`branch_ran_on: "2 of 3 ratified rows: BSR-BA-02 had no text (HOST_REDIRECTS_CROSS_HOST)"`). R001 would admit the `www.`
host (same registrable domain); the fix is a ratified `www.` canonical URL or a builder rule for same-domain redirects, the
author's call, not a mirror. BSR-MA-01 (Mennonite 1995) and BSR-MA-02 (Dordrecht) are HTML-sourced: MA-01's adapter reads the
24 article pages on mennoniteusa.org, MA-02's the anabaptistresources.org page; the registry's fetch_mode says "HTML + PDF" and
"PDF" — the corrected note is `fetch_mode: HTML` for both. BSR-MW-03 was not re-chunked (audited CLEAN, "of infinite power,
wisdom, and good" intact).

| branch | cells | filled | honest empties | REVIEWED offered | all-rejected | rejections kept | dropped at build | ran on |
|---|---|---|---|---|---|---|---|---|
| Baptist | 37 | 15 | 22 | 22 of 22 | 3 | 12 | 0 | 2 of 3 rows |
| Methodist / Wesleyan | 37 | 22 | 15 | 15 of 15 | 0 | 74 | 0 | 4 of 4 rows |
| Mennonite / Anabaptist | 41 | 31 | 10 | 10 of 10 | 4 | 51 | 0 | 2 of 2 rows |

Baptist: BSR-BA-01 leads all 15 filled cards (BA-03's ten descriptive facts yield little); 22 empties are the strong kind —
both rows are supplied whole (25k and 5k characters), so nothing was sampled and nothing needed exhausting. Mennonite /
Anabaptist: MA-01 leads 22 cards, MA-02 9; MA-02's `speaks_for` "Historic; no current binding statement" resolves to the group
"historic" (BODY_BEFORE_SEMICOLON) — a body name in form only, disclosed in the header for the author.

**Exhaustion.** Baptist: no cell entered (nothing sampled). Mennonite / Anabaptist: MA-01 (114k characters) is sampled at
60k, so every empty-track cell entered — **10 cells entered, 10 locator batch calls + 2 verifier calls, 0.99 USD, 0 changed
from empty to filled; MA-01 read to the end in every one** (standards exhausted 10, stopped early 0). The ten empties therefore
carry REVIEWED honestly, and the Lutheran 7-of-9 did not repeat here: on a 23-chunk standard the sample already held what
there was.

**Task 2 and 2c in the live run.** Baptist: 4 floor disagreements, 1 candidate refused by the lower floor (Q-302, sonnet
WORD_ONLY / opus PARTIAL — an opus rescue that no longer carries); 2c sample 1 of 10 eligible (share 0.10), nothing lowered.
Mennonite / Anabaptist: 1 disagreement, 1 refused (Q-440, WORD_ONLY / PARTIAL); sample 2 of 25 eligible (0.08), nothing
lowered. **Task 3 in the live run.** IDIOM_OR_FORMULA was raised on 7 Mennonite rubrics (Q-008 "the Son of the living God",
"church of the living God"; Q-128 and Q-160 doxologies "to … God be glory"; Q-152 "to the One seated on the throne and to the
Lamb be …"; Q-016 "pledge allegiance to the one true God") and on none of Baptist's; every one was already WORD_ONLY, so the
cap changed no verdict — the flag is doing its work as a named reason rather than as a new refusal.

**Cost against 0.336 USD per cell** (metered, from the audit log; `run.json` `branch_spend`):

| branch | cells | calls | USD | per cell | vs 0.336 | of which exhaustion | of which 2c sample | opus |
|---|---|---|---|---|---|---|---|---|
| Baptist | 37 | 136 | 4.41 | 0.119 | 0.35× | 0.00 | 0.11 | 10 calls, 1.06 |
| Methodist / Wesleyan | 37 | 326 | 9.22 | 0.249 | 0.74× | 0.00 | 0.26 | 7 calls, 0.69 |
| Mennonite / Anabaptist | 41 | 270 | 10.70 | 0.261 | 0.78× | 0.99 | 0.27 | 8 calls, 1.11 |
| **three branches** | **115** | **732** | **24.33** | **0.212** | **0.63×** | 0.99 | 0.64 | 25 calls, 2.86 |

All three ran under the Anglican rate, as the review predicted for three- and four-row branches; the review's "perhaps $35
for all 115 cells" came in at 24.33 USD. No cap was approached (highest branch 10.70 of 25).

**Methodist / Wesleyan** stopped after its first executor round on a latent harness defect, not on spend: one locator reply
carried an explicit `"result": null` beside its candidates and `locate_standard` called `.startswith` on it. All 148 locator
answers of that round were already in the audit log (5.94 USD); the null default was fixed
(`str(parsed.get("result") or "")`), the branch resumed from its stored answers at no repeated cost, and it finished four
minutes later: 37 cells, 22 filled, 15 honest empties with REVIEWED offered on every one (all four rows are supplied whole,
nothing sampled, no exhaustion), 0 all-rejected, 74 rejections kept, 0 dropped at build. Leads: MW-01 (UMC Articles) 10,
MW-02 (UMC Confession) 6, MW-03 (GMC) 3, MW-04 (Wesleyan) 3; bodies on cards: Global Methodist 18, United Methodist 17, The
Wesleyan Church 13 — the group rule cut a same-body second candidate (UMC's Articles and Confession are one body) on 10 of
the 22 filled cards so that a third body could be heard, and 21 of 75 survivors were not coded for that reason (fix 1c,
0.18 USD saved). 2c sample 3 of 21 eligible (0.143), nothing lowered; 2 floor disagreements, both refused (Q-079, twice,
sonnet WORD_ONLY / opus PARTIAL); IDIOM_OR_FORMULA raised on 2 rubrics (Q-047 "love the Lord our God with all the heart",
Q-159 "to the glory of his name"), both already WORD_ONLY.

## Summary for the author, in the order asked

- **Task 1.** Per branch, cards that changed lead: Anglican 0, Roman Catholic 0, Lutheran 0, Reformed 0 (the one Anglican lead
  change, Q-213, is a Task 2 drop). Cards that gained a body the cap had cut: Reformed 10, the others 0. "As above" (BSR-RP-02,
  BSR-RP-03) resolved to the nearest preceding row naming a body, BSR-RP-01 "OPC and Westminster churches"; every other
  resolution is in the table above and in each packet's `speaks_for_groups`. My one addition — a translation witness speaks for
  its controlling row's body — is flagged for the author.
- **Task 2.** Cells whose state changed: Q-147 Lutheran, Q-403 Lutheran, Q-380 Reformed (filled → empty, all-rejected).
  Candidates dropped off a card: those three cells' nine, plus Q-085 AN-05 Q.106 and Q-213 AN-02 Q.4 on Anglican; every one a
  sonnet WORD_ONLY / opus PARTIAL-or-FULL disagreement on the reject-all or slice route. Nothing dropped on the retired
  caveated-accept route. The rule as stated applies to the reject-all route, which is where Q-403 actually sat; that refuses
  seven of the eight session-3 rescues — the author's ruling is needed on whether that route is exempt.
- **Task 4b.** BSR-LU-02 is a JavaScript application shell with no text on any plain route; lcms.org links every Book of
  Concord document to the same viewer and prints none. Not recoverable as text under the policy; keep it as the adoption /
  provenance row it was ratified to be (and say so in its reception_note), or retire it from the citable set.
- **Task 5.** False-accept 0.000 on sonnet, opus and the routed outcome; Dositheus 0.000; 7.57 USD. Planted recall is
  undefined on a near-miss fixture; on cal-3's 141 released cells the rule costs 2 cells of same-standard recall (0.929 →
  0.915, both opus floor rescues), still above the 0.8 gate.
- **Packets.** Baptist 37: 15 filled, 22 honest empties (REVIEWED on all), 3 all-rejected. Methodist / Wesleyan 37: 22 filled,
  15 honest empties (REVIEWED on all), 0 all-rejected. Mennonite / Anabaptist 41: 31 filled, 10 honest empties (REVIEWED on
  all), 4 all-rejected.
- **Exhaustion.** Cells entered: Baptist 0, Methodist 0, Mennonite 10; cost 0.99 USD; cells changed from empty to filled: 0.
- **Cost against 0.336 per cell.** Baptist 0.119, Methodist / Wesleyan 0.249, Mennonite / Anabaptist 0.261; 24.33 USD for
  115 cells (0.212). Session spend including fa-3: 31.90 USD.
- **Eastern Orthodox.** ≈ 55–65 USD as-is at fourteen rows (locator ≈ 35 USD, of which the three sampled rows ≈ 15); details
  and the two per-cell-cap alternatives in the section below. Not run.

## Eastern Orthodox estimate — not run

Fourteen rows; thirteen have text (BSR-EO-03 is HOST_RETIRED). Three are sampled at the 60k budget: EO-01 (159k chars),
EO-04 (197k, 610 chunks), EO-05 (62k); the other ten are supplied whole (EO-02 22k, EO-06 18k, EO-07 38k, EO-08 22k, EO-09 6k,
EO-10 51k, EO-11 2k, EO-12 1k, EO-13 10k, EO-14 33k) — 383k characters of context per cell, thirteen locator calls per cell.

Locator cost, calibrated on the measured live-1 rates (Lutheran 0.070 USD per locator call at ~40k average context; Reformed
0.112 at ~55k; Anglican 0.052 at ~25k — about 0.0017 USD per 1k characters plus ~0.012 fixed per call):

| component | per cell | × 44 cells | basis |
|---|---|---|---|
| locator, the three sampled rows (180k chars, 3 calls) | 0.34 | 15.0 | 47% of the context |
| locator, the ten whole rows (203k chars, 10 calls) | 0.46 | 20.4 | |
| verifier (about eight slotted candidates; opus always on EO-04, EO-05, EO-09 and on reject-all) | 0.40 | 17.6 | Anglican / Lutheran opus rates 0.10–0.11 per call |
| coder (three per filled cell) | 0.03 | 1.3 | |
| exhaustion (EO-01 99k + EO-04 137k + EO-05 2k unsupplied ≈ 4 batches of 60k per empty-track cell, plus verifier) | — | 6–10 | if 10–15 cells go empty on passes 1–2 |
| **total as-is** | **≈ 1.2** | **≈ 55–65 USD** | cap 70 |

The Reformed-based extrapolation in the review (75–90 USD) assumed six 60k contexts per cell; Eastern Orthodox has three,
so the locator is 35 USD, not 50–60. A per-cell cap on standards consulted saves most where it removes the sampled rows:
consulting the ten whole rows only would cost ≈ 20 USD of locator and lose the guaranteed slots of the Longer Catechism
(EO-04), Dositheus (EO-05) and the OCA Symbol of Faith page (EO-01) — EO-04 and EO-05 are the caveated rows the opus slice
exists for, so that cap changes what the branch is, not just its price. Consulting whole rows plus EO-01 only (drop EO-04 and
EO-05 from routine consultation) is ≈ 27 USD of locator and keeps the conciliar and liturgical rows intact. The author's call.
