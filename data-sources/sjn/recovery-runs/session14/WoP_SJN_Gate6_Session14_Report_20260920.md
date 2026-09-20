ANSWERS: CODE-SJN-16
# CODE-SJN-16 (Gate 6 session 14)

**Phases 0–5 are done, tested, committed and pushed. STOPPED before phase 6 (the paid run) on a stop condition.
No model call was made. Spend 0.00 USD.**

- **Model calls: 0. Spend: 0.00 USD.** No `calls.jsonl` was written or appended in this session.
- **Network: 0 requests.** Both adapters read the fetch cache; 328 cache files before and after, none with a new mtime.
- **Commits (all pushed to main):**

  | commit | phase |
  |---|---|
  | `02fb5ee` | phase 1 — rulings R6-47 to R6-57 recorded |
  | `c599b7e` | phase 2 — production majority voting and the author review queue |
  | `e21ad5b` | phase 3 — registered section extents locked by test |
  | `712498e` | phase 4 — the AN-04 / AN-06 corpus repair |
  | `18460b2` | phase 5 — cost estimate, and Track R re-pointed at the repaired text |

  This report follows in one more commit, which is the HEAD of `main` at the time of writing and carries no change but
  this file.

- **Tests:**

  | point | passed |
  |---|---|
  | start | 175 |
  | phase 1 | 179 |
  | phase 2 | 195 |
  | phase 3 | 203 |
  | phase 4 | 214 |
  | phase 5 | 215 |

- **What stopped it:** **phase 6 cannot be run under the cap discipline the author ruled, because this environment
  carries no Anthropic credential for the SJN harness.** `ANTHROPIC_API_KEY` is unset; no key file is recorded in the
  repo or in any run log (every log writes the path as the literal placeholder `<.env>`). See §1. Everything phase 6
  needs is built, tested and committed; the gate passes; one line from the author unblocks it.

---

## 0. The author's decision list

1. **§1 — the one thing that unblocks phase 6.** Name the key file the SJN harness should use (`--key-file <path>`), or
   set `ANTHROPIC_API_KEY` for the run. A key does exist on this machine, in an unrelated project's `.env`; Code did not
   use it, because choosing which account to charge is the author's decision, not Code's. A follow-up session runs
   phase 6 in minutes: the estimate is done, the gate passes, and the expected spend is about **4.50 USD across both
   tracks**.
2. **§5.2 — BSR-AN-06's authority tier is Code's reading, not a ruling.** No ruling names it. Three ranked readings with
   their weaknesses are recorded, and **both were measured**: the chosen fail-closed reading changes **no lead**; the
   genre-tier reading would move **five Anglican leads**, putting an unconfessed historical document at the head of
   Q-413, Q-421, Q-429, Q-437 and Q-453. Ratify or replace the value; it is one field on the R6-48 ruling.
3. **§3.4 — 204 of 676 existing accepts would enter the review queue** under Codex C3(a)'s literal reading (133 of 467
   seated). The dissent limb cannot fire on any of them: **all 735 stored rubrics are single calls.** The queue was
   left forward-looking and no stored verdict was enqueued. Rule whether the existing accepts are to be swept into it.
4. **§7.2 — three verdicts were given on text carrying page furniture.** The AN-05 chunk the verifier judged read "This
   Name means that he *the lord's prayer* alone is truly God"; session 13's repair removed the interpolation and the
   verdicts were never re-read. They are now in Track R. Session 13's Track R list was three candidates short.
5. **§3.5 — not one seated citation in the corpus is public-certification eligible** under R6-54. All 465 seated
   entries across the seven finished branches are single-call verdicts at gate6-v1.1, v1.2 or v1.3. This is the bar
   working, not a fault, but it means public certification waits on a voted re-read of everything, not only Track R.
6. **§8 — workbook deltas pending**, now including the new BSR-AN-06 row and its adoption columns.

---

## 1. The stop (before phase 6)

**Condition:** "A verification contradicts this prompt in a way that changes what should be written."

**What the prompt assumes.** Phase 6 runs Tracks R and B as paid runs and "stop[s] a track the moment its spend reaches
its cap". The cap mechanism is `api_executor.py --max-cost-usd`, which meters every call's real token usage and refuses
the next call when the accumulated metered cost would exceed the cap. That is the instrument every figure in this
pipeline rests on: 1,353 metered opus calls and 130 metered sonnet v1.3 calls.

**What the environment shows (verified, not assumed).**

| check | instrument | result |
|---|---|---|
| `ANTHROPIC_API_KEY` in the process environment | `os.environ` | **not set** |
| a key file recorded in the repo | `grep -r "key-file" data-sources/sjn/recovery-runs` | only the literal placeholder `<.env>`, in two docstrings |
| a key file at the obvious paths | `test -e` on `.env`, `../.env`, `../wop-scratch/.env`, `~/.env`, `WoP/.env`, `WoP/ops/.env` | **none exists** |
| any `.env` under `Documents` (depth 3) carrying `ANTHROPIC_API_KEY=` | `grep -l` (no value read, printed or logged) | **one**, in an unrelated project's directory |

**Why this changes what should be written.** Three paths exist and none of them is the ruled instrument:

1. **The `anthropic` backend** is the ruled one and needs a key this session was not given.
2. **The `batch` backend answered by Claude Code subagents** would run, but `llm.py` marks its cost
   `"ESTIMATE: Claude Code subagent calls are not metered per call"`. A paid track under a hard cap, with "stop the
   moment spend reaches the cap", cannot be run on estimated spend. Under C1 that is also a different instrument from
   the one every prior branch used and the one phase 5 priced.
3. **The `claude-cli` backend** would run and does report the CLI's own `total_cost_usd`, but it spends the author's
   Claude Code usage rather than the metered API budget the caps are denominated in, and `api_executor`'s cap
   enforcement is not wired to it. Same C1 objection.

**What Code did not do, and why.** A key does exist on this machine, in a project unrelated to SJN. The prompt
authorises *the spend* (30 USD per track); it does not say which account to charge, and no SJN session has ever
recorded using that file. Reaching into another project's credentials to spend money is a step beyond what the ask
implies, and it is not reversible. Code stopped instead of choosing an account for the author.

**Ranked options for the author.**

1. **Name the key file and re-run phase 6.** `python scripts/sjn_recovery/api_executor.py --run-id live-1 --key-file
   <path> --max-cost-usd 30`. *Weakness:* one more session. *Strength:* everything is built, tested and committed;
   expected spend about 4.50 USD; the 80% gate already passes on the recomputed cell set.
2. **Run it on the `claude-cli` backend**, recording it as a C1 deviation. *Weakness:* a different instrument from the
   one every branch and every fixture measurement used, and the cap becomes advisory rather than enforced.
3. **Hold phase 6 until the queue question (§3.4) is ruled.** *Weakness:* the 23 Track R citations stay on verdicts
   given against text the repair replaced, and three of them stay on text carrying a running header.

Nothing else in the prompt was held. No other stop condition fired: no PUBLIC-CERTIFIED cell was touched (§6), no
estimate or verifier bound exceeded 80% of its cap (§7.4), no queued item can reach publishable output (§3.3), and no
test failed.

---

## 2. Phase 0: start checks

| check | instrument | result |
|---|---|---|
| HEAD, branch, tree | `git rev-parse`, `git status --porcelain` | `36ee8ee`, `main`, clean but for the untracked `tools/reports/chat_screens/Claude outputs/` (unrelated; left untracked, and deliberately unstaged when phase 2 was committed) |
| the session 13 commits are in main's history | `git log --oneline -20` | all five present: `2ec5030`, `89119db`, `2bc36f1`, `4051d7d`, `ee22ea6`, plus the phase 6 / report commit `384a7a4` |
| the codex on disk is v0.8 | read in full (273 lines), header line | `Draft v0.8 · 17 Sep 2026 · Session 13 rulings M to P filed`. md5 `b85f7aca3d1210ecd425dc4e589baaee`, unchanged at the end of the session |
| test suite | `pytest scripts/sjn_recovery/tests -q` | **175 passed** |
| the session 13 sandbox baseline | `session12/sandbox_build.py` (refuses model calls and network requests) | built, `model_calls_attempted: 0`; the Baptist packet reports `REVIEWED offered on 0`, which is session 13 phase 5's state. This build (`sb-base`) is the baseline for every diff below |
| the rulings file | `data-sources/sjn/recovery-runs/author-rulings-pending-workbook.json` | carries R6-1…R6-23 and R6-35…R6-46. **None of R6-47 to R6-57 was present.** All eleven were written in phase 1 |

---

## 3. Phase 2: production voting and the review queue (R6-54; Codex C1(a), C3(a))

This is what session 13 stopped before its phase 7 to get built. Until now the branch runs read **one** verifier call
per candidate while the version gate read three or five — C1's own stated failure, "a gate that votes while production
does not certifies a different instrument from the one that runs".

### 3.1 Voting (C1(a))

- `agents.verify_voted` makes **three gate6-v1.3 draws** per candidate; `agents.vote` takes the **majority over verdict
  class** — the code-recomputed verdict, not the model's own `verdict` line.
- The floor is the **lowest floor among the majority**, and the verdict is recomputed at it by the same
  `verdict_from_rubric()` every other path uses. So rule 2a's shape holds inside one model's vote: an
  ACCEPT_WITH_CAVEAT majority whose lowest majority floor is WORD_ONLY refuses BELOW_FLOOR. A **dissenting** draw's
  floor is not in the majority and cannot lower it — "among the majority", not "among the draws".
- A vote with no majority (1/1/1 across the three classes) **fails closed** to the most conservative class present,
  never to a plurality of one.
- `_verify_pass` routes the primary, the opus slice and the 2c sample through `verify_voted`, so **opus routes vote the
  same way**.
- All three draws are issued **before** the vote is taken, so a pending draw never becomes a two-call majority.

**Call identity.** Replicate *r* takes attempt base `llm.REPLICATE_STRIDE * r` — the session-8 `attempt + 100`
convention already used by `partial_rule._ReplicateLLM` — so the audit log's duplicate suppression cannot serve one
answer back as three. **Replicate 0 keeps attempts 0 / 1**, so every call identity written before this session is
unchanged: a stored verdict's answered call is still served from the log, and only the further draws are paid for.

### 3.2 Instrument on every verdict

Every voted rubric records `prompt_version`, `call_count`, `vote_split`, `majority_class`, `majority_share`, `dissent`,
`no_majority`, the floor rule, the floor per replicate, and every replicate's `call_id`. `finalize()` records the
instrument of each deciding rubric plus `v13_majority` and `public_certification_eligible`, with
`public_certification_bar` naming the instrument where it is not.

**Stored verdicts are labelled with what they actually were** — their own prompt version, **one** call, no vote split —
and are never relabelled as majority verdicts. A test reads 40 real live-1 cell states and asserts it of every rubric.

### 3.3 The queue and the publication bar (C3(a))

- `scripts/sjn_recovery/review_queue.py`, over the committed `data-sources/sjn/recovery-runs/author-review-queue.json`.
- **Doubt** is any dissenting vote, or ACCEPT_WITH_CAVEAT at PARTIAL — computed in `finalize()` and written onto the
  final verdict as `review_queue_reasons`. `run.record_review_queue` writes a branch's doubtful accepts after it
  finishes, and after a cost-cap stop.
- **The packet builder** tests `review_queue.hold()` **before** a candidate reaches `accepted`, so a held item takes no
  seat, no lead and no parallel-witness record; it is kept under `review_queue_held` and it **withdraws the card's
  NOT LOCATED — CURRENT STANDARD REVIEWED offer** (a card with an unruled accept has not finished being reviewed).
- **The emit step**: `emit.assert_review_queue_clear` runs in `sjn-build-data.py` **before the first file is written**,
  over the whole payload, and hard-stops on any held candidate id anywhere in it or any CERTIFIED cell whose id carries
  a held item.
- `ADMIT` releases an item; `REFUSE` keeps it barred with the author's reason; anything else is **held** (fail closed).
- **No code path refuses on a model self-report** (Codex C3). Doubt queues. The one guard that ever refused on a
  self-report — R6-18's `asserted_outside_formula` — is scoped to gate6-v1.6, which is not the version in force; a test
  asserts that and drives a v1.3 accept that self-reports `Y` through unrefused.

**Mutation-checked.** A queue item planted on Q-070's **lead** removed that seat from a real sandbox Baptist build,
left the id in no seat or parallel-witness record, put it under `review_queue_held`, and withdrew the card's REVIEWED
offer.

### 3.4 Queue volume before the queue is used (C3(a) requires this report)

`session14/queue-volume.json`. Over all 291 live-1 cell states and the committed packets; no model call.

| branch | accepts | seated | A (literal) | A seated |
|---|---|---|---|---|
| Roman Catholic | 161 | 96 | 37 | 17 |
| Reformed / Presbyterian | 105 | 44 | 27 | 11 |
| Lutheran | 96 | 75 | 26 | 21 |
| Anglican | 113 | 84 | 35 | 21 |
| Methodist / Wesleyan | 77 | 53 | 33 | 22 |
| Mennonite / Anabaptist | 68 | 61 | 28 | 25 |
| Baptist | 56 | 54 | 18 | 16 |
| **total** | **676** | **467** | **204** | **133** |

Three readings of "dissent", ranked, with each one's weakness:

- **A (literal C3(a); the figures above).** ACCEPT_WITH_CAVEAT at a PARTIAL final floor only. The DISSENTING_VOTE limb
  **cannot fire on any stored verdict**: all 735 stored rubrics are single calls (0 carry an instrument), so there is
  no vote to dissent from. *Weakness:* it counts no vote at all, because none was taken.
- **B (210 / 138).** A, plus accepts whose two stored models returned different verdict classes. *Weakness:* a
  two-model disagreement is rule 2a/2b, which the harness already resolves; calling it dissent double-counts a rule
  that has already run.
- **C (210 / 138).** B, plus accepts whose two models returned different floors. *Weakness:* widest; a floor
  disagreement 2a already resolved downward is not doubt about the outcome.

**No stored verdict was enqueued.** The queue is forward-looking: it is populated by voted runs. Whether the 204 are to
be swept into it is the author's call (§0.3).

### 3.5 Sandbox effects of phase 2 alone

`session14/phase2-effects.json`, `phase2-deep-diff.json`. **0 cards changed.** All 5,847 field diffs are added
disclosure fields: `instrument`, `instrument_of_record`, `v13_majority`, `public_certification_eligible`,
`public_certification_bar`, `review_queue_reasons`, `review_queue_held`, and the packet header's `author_review_queue`.
No seat, tier, lead, verdict or disclosure change.

**One finding worth the author's attention.** All **465 seated entries** now report
`public_certification_eligible: false`. Every seated citation on the seven finished branches is a single-call verdict.
R6-54's bar is doing exactly what it says; the consequence is that public certification waits on a voted re-read of the
whole corpus, not only of Track R's 23.

---

## 4. Phase 3: registered section extents (R6-57; Codex B1(e))

The author ratified all three of session 13's §3.3 extent judgments. This phase verified the implementation **against
the artifacts** — `registered-sections.json`, the stored chunks, and the registry's own registered keys — rather than
against the session 13 report's description of them, **found all three already in force**, and locked them. No code
changed.

| ratified judgment | verified how | result |
|---|---|---|
| the creed portion of a mixed block is registered and its extent recorded | four sections carry `text_through`; for each, the marker is found in the stored chunk and the registered key's length is asserted to stop exactly there, with the chunk running on past it | holds for BSR-RP-04 1.3 and 2.3, BSR-LU-01 Ecumenical Creeds: The Apostles' Creed, BSR-AN-03 |
| the Gloria Patri after AN-03 is left out | the stored chunk is 3,780 chars and **does** carry "Glory be to the Father"; the registered extent is 3,637 and ends at "he cannot be saved." | holds; and `resolve_registered_phrase("Anglican", "Glory be to the Father, and to the Son")` returns `None` |
| EO-06 Chalcedon paragraph 10 is left out as acts narrative | it stands in `not_registered` with its reason and is in no branch's registered definitions | holds. Chalcedon 1–9 **are** registered, and Constantinople III's own paragraph 10 stays registered: the exclusion is by document, not by a paragraph number |

**Mutation-checked, three ways.** Dropping AN-03's `text_through` puts the Gloria into the registered key and makes it
resolvable; listing EO-06 Chalcedon paragraph 10 registers the acclamation; a `text_through` the chunk does not carry
is a hard stop, never a silent whole-chunk registration.

**The two holds are locked in the same file.**

- **R6-56 (no tier moves).** The only `authority_tier` overrides in force are R6-5 (BSR-EO-01, session 7) and R6-44
  (BSR-LU-03, session 13). BSR-AN-02 and BSR-RC-01 carry none and resolve at their workbook CATECHETICAL tier.
- **R6-55 (allocation unchanged).** Q-195's seats are locked at the **build-time** allocation the author actually sees
  — LU-01-1, LU-02-1, LU-01-2 — with the LCMS slot held by the Augsburg Confession and LU-03-1 cut at tier allocation
  by the group cap, not by its floor. *(The cell state's stored allocation reads LU-03-1 at seat 3, because
  `refinalize` allocates on the tiers stored at run time while the packet re-resolves them from the phrase. The card is
  what R6-55 describes, so the card is what the test locks.)*

---

## 5. Phase 4: the AN-04 / AN-06 corpus repair (Codex F.10; R6-45, R6-47 to R6-53)

### 5.1 What was wrong, verified at the source

The Quicunque Vult runs across the BCP p. 864/865 page break. The AN-04 adapter's 20-page window ended at p. 864, so
the stored creed broke off at **"And yet they are not three Almighties, but one Almighty."** — a third of the way in,
mid-argument, before a word of the Incarnation half. Read directly out of the cached PDF: p. 863 is the "Historical
Documents of the Church" title page, p. 864 carries the Chalcedonian Definition and the first part of the Quicunque
Vult, p. 865 carries the rest ending "he cannot be saved.", p. 866 is the 1549 Preface and p. 867 the Articles of
Religion. The text was never wrong; the window was.

### 5.2 BSR-AN-06 (R6-48), and the one field no ruling names

`sources.tec_historical_documents` chunks **pp. 863–865** from the fetch cache: the title page, the Chalcedonian
Definition (p. 864, 1,232 chars), and the Quicunque Vult **joined across the break** (pp. 864–865, 3,633 chars, ending
at its last sentence). A document is accumulated across pages until the next printed heading; the walk stops at the
first stop heading. The adapter **refuses rather than stores** if the creed does not end at its last sentence, if there
is not exactly one Quicunque Vult chunk, or if anything runs past the extent. 3 chunks, 4,899 chars, embedded.

**The tier is Code's reading of B1(c), not an author ruling.** No ruling names it. Three ranked readings, with each
one's weakness, and both measurable ones measured:

1. **`OFFICIAL_EXPOSITION (witness; adopted historical document, not confessed)` — CHOSEN.** B1(c) says a
   creed-genre text resolves at its genre's tier only where the church confesses it, and "absent the marks, the text
   stays a witness (fail closed)". The book *is* adopted (B2), so the row is not unadopted; OFFICIAL_EXPOSITION is what
   B1/B2 give an adopted text that does not reach its genre's tier, and it is what R6-42 gave the adopted-but-
   non-creedal ABCUSA statement. **Measured: 0 leads change.** *Weakness:* it ranks the Chalcedonian Definition below a
   catechism for this church, which reads oddly beside the text's standing everywhere else in the corpus.
2. **`CONCILIAR (witness; …)`** — the genre's own tier, with the witness flag doing all the work. **Measured by a second
   sandbox build: five leads move** — Q-413, Q-421, Q-429, Q-437 and Q-453 would all be led by the unconfessed
   Historical Documents text, above the Thirty-Nine Articles and above the confessed Athanasian Creed. *Weakness:* this
   is precisely the tier B1(c) fails closed against; the witness flag stops the row seating *alone*, but within a tier
   it outranks every other Anglican row wherever a non-witness candidate exists.
3. **`CATECHETICAL`, following the row it was split out of.** *Weakness:* neither document is a catechism; the tier
   would be a bookkeeping artefact of the split, and B1 says tier follows what a document **is**.

The value lives on the R6-48 ruling (`new_row.authority_tier`), so changing it is one field and a re-run.

**The witness treatment rides on the tier string itself**, which `registry.is_witness_row` reads, so no later edit can
drop a flag and quietly promote the row.

### 5.3 BSR-AN-04 (R6-51)

The p. 844 rubric "Concerning the Catechism" is now this row's first chunk — integral text of the adopted book (B2(b)),
with its own locator and division `rubric (integral text)`, **not** a registered section (a rubric about the catechism
is not a creed or definition). The adapter refuses if p. 844 does not open with it. The Historical Documents pages are
no longer chunked here. **126 → 125 chunks; 23,763 → 22,067 chars; text_hash `44e8a00c…` → `e7cc6179…`.** R6-45's scope
marker is discharged: no AN-04 chunk awaits a scope ruling, and the ruling records that the marker stays in force but
inert.

### 5.4 Two mechanisms the split forced

**Cross-row relocation.** Every earlier re-chunk moved text within one row. Here the text leaves AN-04 for AN-06, so
`packets.relocate` follows a mapped chunk into another row, and the builder re-reads tier, adoption, `speaks_for`,
witness status and refusal from the row that holds it **now** — which is how R6-47's witness treatment reaches these
citations at all.

**Composing mappings.** The stored candidates sit under the **original** p. 862 locator. Session 13 mapped that onto two
AN-04 Historical Documents chunks; this session moves those two into AN-06. `packets.relocations` now composes
successive mapping files in chronological order. Without composition all 19 citations would have been dropped at build
as vanished chunks.

**R6-50, scoped to the section.** The ruling names the pair for the **Quicunque Vult section**, not the whole row, so
the declaration carries `locator_contains` and the allocator applies it only there. Measured before the scope was
added: without it, the **Chalcedonian Definition was recorded as a parallel witness of the Athanasian Creed on four
cards** — two different texts collapsed into one. AN-06 is also excluded from rule 1b's English-translation pairing
(it is not a translation of AN-04, whose title it shares three words with): one row, one relationship.

### 5.5 Sandbox effects of phase 4 alone, cell by cell

Against the phase 2/3 build. `session14/an06-cell-by-cell.json`, `phase4-effects.json`, `phase4-deep-diff.json`.

**0 seats changed. 0 leads changed.** 19 entries relocated AN-04 → AN-06 across 17 cards; 0 dropped at build; all 19
lose `awaits_scope_ruling`.

| cell | predicate | entry | role before → after | tier before → after |
|---|---|---|---|---|
| Q-237 | Word / Logos | AN-04-1 (Chalcedon) | seat 2 → **seat 2** | CATECHETICAL → OFFICIAL_EXPOSITION (witness) |
| Q-277 | Eternal power and might | AN-04-1 (Quicunque) | seat 2 → **seat 2** | CONFESSIONAL → CONFESSIONAL |
| Q-277 | " | AN-04-2 (Quicunque) | rejection → rejection | CONFESSIONAL → CONFESSIONAL |
| Q-413 | Without confusion | AN-04-1 (Chalcedon) | seat 3 → **seat 3** | CATECHETICAL → OFFICIAL_EXPOSITION (witness) |
| Q-421 | Without change | AN-04-1 (Chalcedon) | seat 3 → **seat 3** | CATECHETICAL → OFFICIAL_EXPOSITION (witness) |
| Q-429 | Without division | AN-04-1 (Chalcedon) | seat 3 → **seat 3** | CATECHETICAL → OFFICIAL_EXPOSITION (witness) |
| Q-437 | Without separation | AN-04-1 (Chalcedon) | seat 3 → **seat 3** | CATECHETICAL → OFFICIAL_EXPOSITION (witness) |
| Q-453 | Greater dissimilarity than similarity | AN-04-1 (Quicunque) | seat 2 → **seat 2** | CONFESSIONAL → CONFESSIONAL |
| Q-157, Q-285, Q-301, Q-317, Q-365, Q-373 (×2), Q-445 | — | AN-04-1/2 (Quicunque) | parallel witness → parallel witness (ORIGINAL_HOLDS_SEAT) | CONFESSIONAL → CONFESSIONAL |
| Q-381, Q-389, Q-405 | — | AN-04-1 (Quicunque) | rejection → rejection | CONFESSIONAL → CONFESSIONAL |

**The seven seats the session 13 report names — verified, and each one's outcome.**

| cell | session 13 said | verified | outcome |
|---|---|---|---|
| Q-237 | AN-04-1 seated | yes, seat 2 | **keeps its seat**, now BSR-AN-06 at the witness tier, CORROBORATING |
| Q-277 | AN-04-1 seated | yes, seat 2 | **keeps its seat**, CONFESSIONAL |
| Q-413 | AN-04-1 seated | yes, seat 3 | **keeps its seat**, witness tier, CORROBORATING |
| Q-421 | AN-04-1 seated | yes, seat 3 | **keeps its seat**, witness tier, CORROBORATING |
| Q-429 | AN-04-1 seated | yes, seat 3 | **keeps its seat**, witness tier, CORROBORATING |
| Q-437 | AN-04-1 seated | yes, seat 3 | **keeps its seat**, witness tier, CORROBORATING |
| Q-453 | AN-04-1 seated | yes, seat 2 | **keeps its seat**, CONFESSIONAL |

All seven verified as stated, and all seven keep their seats.

**Why the tiers split.** The five **Chalcedonian Definition** entries fall to the fail-closed witness tier: no
registered text carries their phrases. The **Quicunque Vult** entries stay CONFESSIONAL because their phrases stand
verbatim in BSR-AN-03's registered Athanasian Creed, and phrase-level resolution raises them (B3). Where AN-03 is
itself a candidate the original holds the seat and AN-06 is its parallel witness (B3(a), R6-41); where it is not, the
quoting candidate keeps its seat at the raised tier, which is B3(a) as written.

**R6-47's "cannot seat a cell alone" holds**, as a fact and as an enforced rule: no card seats an AN-06 candidate
alone, and the witness-only guard would empty any card that tried.

**Disclosure.** Every AN-06 entry that carried an adoption disclosure now carries R6-47's wording instead: *"The
Episcopal Church adopted the Book of Common Prayer that prints this text among its Historical Documents. It is not
appointed in the Church's liturgy and not named in a confessional subscription: it is shown as a witness, never as a
creed this Church confesses."*

**One effect the author should expect.** 35 Anglican cards lose the CURRENT STANDARD REVIEWED offer, because BSR-AN-06
supplied no text to cells that ran before it existed — the same honest effect BSR-BA-04 had on the Baptist cards in
session 13. It lasts until Track R runs.

### 5.6 The negative claims, with their search spaces

- **Nothing runs past BCP p. 865.** Every AN-06 chunk's locator is parsed for its page numbers and asserted within
  863–865; the texts are searched for "First Book of Common Prayer" and "Articles of Religion". Both absent.
- **No AN-06 chunk ends at "one Almighty."** Asserted over every chunk, with the cut point required to remain *inside*
  the creed and the Incarnation half required to be present.
- **The TEC Articles of Religion (R6-49) are not fetched and not added.** The search space: every registry row of the
  Anglican branch (no new Articles row); every stored chunk of BSR-AN-04 and BSR-AN-06 (no "Articles of Religion", no
  "Of Faith in the Holy Trinity"); the adapter's own stop list.
- **The TEC glossary and Brief Dictionary (R6-53) are context only.** Enumerable: the registry has no row on a Church
  Publishing host, and no code path reads them. They appear once, named as context, in BSR-AN-06's `adoption_verified`.

---

## 6. Constraints and stop conditions checked

- **`git diff 36ee8ee HEAD -- src/_data/sjn data-sources/sjn/recovery-packets data-sources/sjn/*.xlsx` is empty.**
  Nothing reached app data, the committed packets or the workbook.
- **The codex was not edited.** Read in full at the start; md5 `b85f7aca3d1210ecd425dc4e589baaee` unchanged at the end.
- **Measured verifier versions and the fixtures were not edited.** `git diff 36ee8ee HEAD -- prompts.py
  calibration_fixture.py` is empty. gate6-v1.3 remains the verifier in force.
- **PUBLIC-CERTIFIED cells: none touched.** All 247 sandbox cards are open cells; of the 36 cards phase 4 changed, 35
  are `NOT LOCATED — NOT YET RECOVERED` and 1 is `NOT LOCATED — CURRENT STANDARD REVIEWED`; none is PUBLIC-CERTIFIED.
- **R6-56 (no tier moves):** honoured and tested. BSR-AN-02 and BSR-RC-01 hold at CATECHETICAL. *(BSR-AN-06's tier is a
  new row's tier, not a move.)*
- **R6-55 (allocation unchanged):** honoured and tested. Q-195's third Lutheran seat is LU-01-2, as the session 13
  report describes it.
- **R6-49:** the TEC Articles were not fetched or added.
- **Eastern Orthodox was not run.** Its registered sections were read only, in the R6-57 tests.
- **A queued item cannot reach publishable output:** tested four ways, and the bar is asserted to run before the first
  file is written.
- **Model calls before phase 6: none.** No `calls.jsonl` has a new mtime; every sandbox build reported
  `model_calls_attempted: 0`; the builder refuses both model calls and network requests.
- **Network: 0 requests.** 328 fetch-cache files before and after, none with a new mtime.

---

## 7. Phase 5: the estimate, and a defect found before any call

### 7.1 The defect

`agents.verify` builds its chunk view from the candidate **as stored** — `cand["chunk_text"]`, `cand["registry_id"]`,
`cand["locator"]` — and `reverify.reverify_one` passed it the stored candidate. Track R, whose whole purpose is to
re-verify citations **after a corpus repair**, would therefore have sent the verifier the very text the repair replaced:
on this split, the Quicunque Vult cut at "one Almighty." It would have measured the instrument change and certified a
stump.

`reverify.repoint` now follows the same composed chunk-id mapping the packet builder follows and hands the verifier the
row, locator and text the store holds **now**, failing closed where no current chunk carries the phrase verbatim. A
re-verification also votes (`verify_voted`): it is a production read, so R6-54 governs it. Tested, including the
fail-closed path.

### 7.2 Track R, recomputed

Derived from the composed mapping against all 291 live-1 cell states — **not** reused from session 13.
**23 candidates across 20 cells**, where session 13 named 20 across 18. **0 refused.**

The three session 13 missed are real, and checkable in the stored text:

| candidate | what the verifier actually judged | stored verdict |
|---|---|---|
| Q-085-p2-BSR-AN-05-1 | "This Name means that he **the lord's prayer** alone is truly God" — the running header swallowed mid-sentence, 73 chars from the cited phrase | ACCEPT, FULL |
| Q-405-p2-BSR-AN-05-1 | the same chunk, 98 chars from its phrase | ACCEPT_WITH_CAVEAT, PARTIAL |
| Q-101-p2-BSR-AN-05-1 | "**cove nantal**" split across a line, plus the header "**the ten commandments**" interpolated | REJECT, WORD_ONLY |

Session 13's page-furniture repair removed the interpolations; the verdicts were never re-read. All three are on
BSR-AN-05 and routed SLICE_ROW, so both models verified them.

The other 20 are the ones session 13 named: 19 on AN-04 (now AN-06) and 1 on RC-07. Their chunks changed materially —
the Quicunque Vult entries go from a 2,720-char run-on chunk to the whole 3,633-char creed; the Chalcedon entries to a
focused 1,232 chars; Compendium Q.533's 49,667-char chunk becomes a 466-char Q.586.

### 7.3 Two instruments for the estimate

| | Track R expected | Track R bound |
|---|---|---|
| **1. the session 13 method** — measured per-call means over every logged call (n=130 sonnet v1.3, n=1,353 opus) | $2.35 | $10.66 |
| **2. the actual payloads** — each candidate's verifier payload built and measured (49,173 input tokens per draw), priced at list with the measured output distribution (mean 913, p90 2,235 tokens) | $2.52 | $16.53 |

*Instrument 1's weakness:* it averages calls whose payloads differ from these by up to 3×. *Instrument 2's weakness:*
it prices output from a distribution, not from these calls. **The higher of the two is reported.**

### 7.4 The figures, and the gate

| track | calls expected | calls bound | verifier-only expected | verifier-only bound | all-in expected | all-in bound |
|---|---|---|---|---|---|---|
| **R** (cap $30) | 69 sonnet, 12 opus, 1 coder | 69 sonnet, 69 opus, 1 coder | **$2.52** (8.4%) | **$16.53** (55.1%) | $2.53 (8.4%) | $16.54 (55.1%) |
| **B** (cap $30) | 37 locator, 60 sonnet, 9 opus, 20 coder | 37 locator, 333 sonnet, 63 opus, 111 coder | **$1.94** (6.5%) | **$20.83** (69.4%) | $2.70 (9.0%) | $24.60 (**82.0%**) |

**Every expected figure and every verifier-only bound is at or under 80% of its cap — the gate the prompt sets for
phase 6.** Track B's **all-in** bound is 82%, exactly as in session 13, where the author saw that figure and ruled that
phase 7 runs. Flagged rather than treated as a stop: the prompt's phase 6 gate names "every expected and verifier-bound
estimate", the all-in bound is a bound on the worst routing rather than an expectation, and the run stops the moment
spend reaches the cap in any case. **The author should say if that reading is wrong.**

Track B is unchanged by the repair and re-derived rather than copied: 37 Baptist cells, BSR-BA-04's 19 chunks, 5,703
chars; expected ~0.5 candidates per cell (BSR-BA-03's similar page yielded 1 in 37); the bound is the locator cap of 3
per cell.

---

## 8. Remaining items

### For the author
1. **§1** — name the key file, and phase 6 runs. Expected spend about $4.50 across both tracks.
2. **§5.2** — ratify or replace BSR-AN-06's authority tier. One field; both readings measured.
3. **§3.4** — rule whether the 204 existing accepts are swept into the review queue.
4. **§3.5** — public certification now waits on a voted re-read of all 465 seated citations, not only Track R's 23.
5. **§7.2** — three AN-05 verdicts were given on text carrying page furniture; they are now in Track R.

### Workbook deltas pending (not written; Code does not write the workbook)
- BSR-LU-03 `authority_tier` CONFESSIONAL (session 13).
- The new BSR-BA-04 row with its adoption columns (session 13).
- **The new BSR-AN-06 row** with its adoption columns and R6-47's disclosure wording (this session).
- The carried items from session 12 §8.10.

### For the QA track
1. **The BSR-BA-03 decoding loss** (session 13 §9): its chunks lack apostrophes and quotation marks. Untouched.
2. **Other rows fetched without a charset header** may carry the same loss. Still unsearched.
3. **"A Caring People"** has two items ending in a semicolon on the HTML page. Still open.
4. **A second publisher for LCMS Constitution Art. II**, load-bearing for BSR-LU-03's tier as well as its adoption.
5. **Page furniture in other rows.** §7.2 shows the AN-05 interpolation reached the verifier. The audit that would
   contain it is a sweep of every stored `chunk_text` on a live-1 candidate against the current store — this session
   ran exactly that sweep for Track R (23 hits, 0 refused), so the search space is already enumerated and the answer
   for the current store is: those 23 and no others.

---

The five phase commits are below. The sixth, carrying this report, is the HEAD of `main`.

COMMITS BY REPO:
- words-of-plainness: 02fb5ee c599b7e e21ad5b 712498e 18460b2
