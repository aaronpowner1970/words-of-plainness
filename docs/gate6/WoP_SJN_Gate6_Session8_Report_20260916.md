# SJN Gate 6, session 8 — verifier repair, agency tags, creed-match re-run (16 September 2026)

Rulings R6-13 to R6-16 applied in memory. The workbook was not written, no packet was rebuilt, nothing in the public
app changed, and **Eastern Orthodox did not run**. Spend **2.47 USD** of the 10 USD cap (100 model calls), below the
6 USD report threshold.

**The headline: gate6-v1.5 is NOT in force, and the gate STOPPED on its Q-160 condition.** Q-160 is accepted 3 of 3
under v1.5 and 1 of 3 under v1.3, so the creed carve-out is implicated. v1.5 also fails the recall floor (57/60).
gate6-v1.3 stays in force, and the creed lines were not edited. EO has two open blockers: (d) the verifier and (e) the
EO-09 ruling.

**And the TP-049 diagnosis is wrong again.** Under v1.5, TP-049's Son family gets the *base* prompt, which has neither
JOINT PREDICATION nor the deleted sentence. It is still refused 3 of 3.

---

## 1. Task 1 — gate6-v1.5 and its scope (R6-13)

### The diff against v1.4

The only change to the text, in `JOINT_PREDICATION_LINE`:

```diff
 … and never reason from the unity of the divine essence to each person.
-A doxology naming the three persons remains a fixed formula under line 4.
```

`VERIFIER_SYSTEM_V15_SPIRIT` is v1.4 with that sentence (and its leading space) removed: 74 characters, nothing else.
A test asserts the two are byte-identical otherwise.

### The scope, in the harness

| variant | sent to | text |
|---|---|---|
| `gate6-v1.5/spirit` | a family whose `required_subject` names the Holy Spirit | v1.4 minus the sentence |
| `gate6-v1.5/base` | every other family, or a caller that passes no family | v1.3 + the creed lines (formula carve-out, flag tail, creedal silence); **no** JOINT PREDICATION, **no** AGENCY |

- **Scope test:** `prompts.subject_includes_the_spirit` checks the required subject the verifier is actually sent for
  "holy spirit" or "holy ghost". Across the 57 families it selects **exactly** the seven in the tags file: H06, H21,
  H26, H27, H34, H35, H38. The GOD AS TRINITY family is not selected.
- **What gets recorded:** each verifier call records the variant in its call meta (`verifier_variant`, in `calls.jsonl`)
  and on its rubric (`prompt_variant`). tp-4 under v1.5 sent 53 base and 7 spirit.
- **Versions stay in order:** `VERIFIER_SYSTEMS` runs v1.2, v1.3, v1.4, v1.5. `SCOPED_VERIFIER_SYSTEMS["gate6-v1.5"]`
  holds both variants. The pending inference line is renamed **gate6-v1.6**.

### Tests (`tests/test_session8_rulings.py`), all passing

| test | result |
|---|---|
| RNR-H05 (Son) prompt | contains neither "JOINT PREDICATION" nor "AGENCY."; variant `base` |
| RNR-H35 prompt | contains both; variant `spirit` |
| RNR-H06 (admits the Spirit) prompt | contains both; variant `spirit` |
| v1.5 spirit variant | lacks the sentence; otherwise **byte-identical** to v1.4 |
| base variant | has the creed lines and all of v1.3's text; base plus the two lines equals spirit |
| variant recorded | `CellRunner.verify` puts the variant on the rubric and the call meta (H05 → base, H27 → spirit) |

---

## 2. Task 2 — agency tags in force (R6-14)

`data-sources/sjn/recovery-runs/spirit-family-agency-tags.json` (schema v2). Every entry has `ratified: true`,
`ratified_at: 2026-09-16`, the class, and the original proposal beside it:

| family | predicate | class | proposal |
|---|---|---|---|
| RNR-H34 | Giver of life | ACTION | ACTION |
| RNR-H35 | Eternal power and might | ATTRIBUTE | ATTRIBUTE |
| RNR-H06 | Lord | ATTRIBUTE | ATTRIBUTE |
| RNR-H21 | Life-giving | ACTION | ACTION |
| RNR-H26 | Judge | ACTION | ACTION |
| **RNR-H27** | **Savior** | **ATTRIBUTE** | ACTION — *changed by the author; the reasoning field records why* |
| RNR-H38 | Not made | ATTRIBUTE | ATTRIBUTE |

`spirit-family-agency-tags-PROPOSED.json` was removed with `git rm` and stays in history. `rulings.agency_tags()` now
reads the ratified file:
- Only entries with `ratified: true` are carried.
- Each tag must agree with R6-14 (and R6-8 for H35). A disagreement, a class outside ACTION/ATTRIBUTE, or a missing file
  raises `SystemExit`.
- A family not in the file gets no class, so it fails closed.
- `agency_blocks_eo()` is now False, because R6-14 discharges the blocker.

**Tests, all passing:**
- H27 is sent `agency_class: ATTRIBUTE` through `load_predicates` and `verifier_user`.
- When the file lacks H34, H34 is still Spirit-scoped but is sent no class, while H35 keeps its class.
- An unratified entry is not carried.
- Setting H27 back to the proposed ACTION fails loudly.

Session 7's H35-only test was rewritten to check that R6-14 supersedes it.

---

## 3. Task 3 — Task 1d re-run on the conciliar creed texts only (R6-15)

Artifact: `recovery-runs/session8/task3-creed-match-conciliar-only.json`. The instruments come from session 7, imported
rather than copied: the same 27 clauses, sentence split and `punct_key`. BSR-EO-09 is searched separately, only for the
side-by-side comparison, and never counts as a match.

**One instrument difference, stated:** the longest-run search now matches on word boundaries. Session 7 used raw
substrings, which could match inside a word at a run's edge. The new search is stricter, and the conclusion does not
depend on it.

**BSR-EO-12 is Greek.** No English sentence can match it verbatim, so in practice the test runs against EO-07 and EO-14.

### 3a. The two instruments

- BSR-EO-01 has 19 chunks and 1,203 sentences; **38 are creed-bearing** (reproduces session 7).
- **Clause list:** all **38 of 38** sentences carry a listed clause verbatim in EO-07 or EO-14, with **0 misses**.
  At the clause level, 21 of the 27 list wordings match.
- **Longest verbatim run per sentence, against EO-07/EO-14/EO-12:**

```
words  4  5  6  7  8  9 11 12 13 14 16 21 22 26 31
cells  1  4 10  8  1  2  1  3  1  1  1  1  1  2  1      median 7; landed in EO-07 ×26, EO-14 ×12
```

- **Sentences with a longest run under 4 words: none.** The shortest is sentence 22, "came down from heaven" (4 words,
  EO-07). The rest of the short end, for the record: "true God of True God" (5, EO-07), "who proceeds from the Father"
  (5), and "the resurrection of the dead" (5, twice).

**The six list clauses with no verbatim match in EO-07/14/12.** These are the review script's wording, not Hopko's, and
none of them leaves a sentence unmatched:

| listed clause | in EO-09? | nearest conciliar wording |
|---|---|---|
| maker of heaven and earth | yes | EO-07/14: "**creator** of heaven and earth" |
| rose again on the third day | no | EO-14: "he rose on the third day" |
| whose kingdom shall have no end | no | EO-07: "and his kingdom shall have no end" |
| **the lord, the giver of life** | **yes** | EO-07: "the lord **and** giver of life"; EO-14: "the lord the **creator** of life" |
| who with the father and the son together is worshipped and glorified | no | EO-07: "who together with the father and the son is adored and glorified" |
| who spoke by the prophets | no | EO-07: "who spoke **through** the prophets" |

### EO-09 side-by-sides: EO-09's run at least 6 words longer than the best EO-07/14/12 run

**Sentence 2**, "Nicene Creed" locator, margin 13:
> And in one Lord Jesus Christ, the Son of God, the only-begotten, begotten of the Father before all ages.

- **EO-09 (20 words):** "and in one lord jesus christ the son of god the only begotten begotten of the father before all ages"
- **EO-07 (7 words):** "and in one lord jesus christ the"
- **Where EO-07 differs:** "…jesus christ **the only begotten son of god born of** the father before all ages…"

**Sentence 5**, "Nicene Creed" locator, margin 13:
> …And [we believe] in the Holy Spirit, the Lord, the Giver of Life, who proceeds from the Father; who with the Father and the Son together is worshipped and glorified; who spoke by the prophets.

- **EO-09 (22 words):** "in the holy spirit the lord the giver of life who proceeds from the father who with the father and the son"
- **EO-07 (9 words):** "giver of life who proceeds from the father who"
- **Where EO-07 differs:** "…in the holy spirit the lord **and** giver of life who proceeds from the father who **together** with the father and the son is **adored**…"

**The consequence the author should see.** I checked every Spirit-named "giver of life" cut of 15 words or fewer from
BSR-EO-01 against every registered text. **Only one resolves to any creed text: "in the holy spirit the lord the giver of
life", and it matches only EO-09.** Hopko's own Creed text (sentence 35, "in the Holy Spirit, Lord and Giver of Life")
matches none. Because the R6-7 guard requires the Spirit's name inside the phrase, an EO-01 citation for Giver of life,
Life-giving or Lord resolves as follows:
- **CONFESSIONAL** if EO-09 stays a registered creed text;
- **OFFICIAL_EXPOSITION** if it does not.

EO-07 cited directly still resolves CONCILIAR on its own wording.

### 3b. The trigger — did NOT fire

**Share failing on translation differences: 0 of 38 (0%) on both instruments.**

**How I read "meaningful":** a share big enough that the conciliar texts could not carry EO-01's Creed quotations. That
means creed-bearing sentences with no conciliar run above the 3-word phrase floor, at about 10% or more (4 of 38). By
that measure, and by any lower bar, the result is 0.

The translation differences are real, but they sit **at the clause level, not the sentence level**: 6 of the 27 list
wordings, plus the two side-by-sides. None leaves a sentence without a conciliar match. **No row is proposed.**
oca.org/orthodoxy/prayers/symbol-of-faith was **not** fetched.

**Weakness of this reading:** it measures whether a sentence *can* resolve, not whether the clause a locator would
*want* can resolve. The Spirit clause above is exactly that kind of case. If the author reads "meaningful" by the
clauses that matter, the answer turns on (e), not on a new row.

### 3c. EO-09's status

**What EO-09 was excluded from.** The cal-3 prompt (12 September, Fix 0) made BSR-EO-09 "NOT RELEASABLE to the agents"
until a guard was written and tested. The guard had to mark anathema-framed spans non-citable and prove that no
candidate comes from an anathema's inner clause. **Only if the guard was not working** would EO-09 be excluded, and
then only from the cal-3 corpus. The prompt also named section 2, "The Symbol of Faith", as "the safe region" that
"may be cited".

**The guard was built and tested.** Evidence:
- `calibration-report.md` §2 describes it.
- `tests/test_synodikon_guard.py` tests it.
- The chunk store withholds 23 anathema spans across §3–§5, and §2 has 0 withheld spans.

So **EO-09 was never excluded**. It ran in cal-3 and live-1 as a Tier A row on the opus slice. The rulings file says
nothing about EO-09.

**Should that exclusion bar EO-09 as a registered creed text? My reading: no, not on Fix 0's terms.**
- Fix 0 was about the *anathemas*. It barred inner clauses, not §2.
- It named §2 citable.
- The exclusion was conditional, and the condition never happened.

**Three considerations cut the other way, ranked by weight:**

1. **The Synodikon is CONFESSIONAL, not CONCILIAR.** Its §2 is ROEA's translation of the conciliar Creed. Registering
   it gives the *same creed* a lower tier than EO-07's copy, and highest-tier precedence (R6-15) only partly hides that.
   A phrase in EO-09's wording alone, such as the Spirit clause, gets CONFESSIONAL for a conciliar text. Weakness: the
   workbook, not this session, typed the Synodikon CONFESSIONAL.
2. **Fix 0's fallback reasoning is out of date.** It said that if EO-09 were excluded, "the branch loses only the
   Synodikon's copy of the Creed, which BSR-EO-01 and BSR-EO-12 both supply". After R6-5, **EO-01 is not a creed text**,
   and EO-12 is Greek. EO-09 is now the only registered English copy in the ROEA/OCA wording family. Weakness: that
   raises EO-09's practical weight, which is an argument for the author's attention, not against eligibility.
3. **A guarded row as a resolution source.** Registered texts are built from the chunk's full text. For §2 the full text
   is the visible text, because §2 has no withheld spans, so no anathema text can enter the index today. But the rule
   does not *require* that. Weakness: a hypothetical, with no current case.

**Nothing about EO-09 was changed. This is blocker (e), for the author.**

---

## 4. Task 4 — highest-tier precedence (R6-15)

**`Registry.resolve_registered_phrase` already had this rule, and had since session 7.** It collects every creed and
definition hit and returns `sorted(hits, key=tier_rank)[0]`. The "longest match landed in EO-09" pattern came from
session 7's **1d analysis instrument**, which took the first text in list order. It was never the resolver's behavior.
**No resolver code changed.** The tests pin the rule:

| test | result |
|---|---|
| "begotten, not made" (EO-07 and EO-09) | **CONCILIAR** via BSR-EO-07; an EO-01 citation resolves CONCILIAR |
| the same, with the index reordered so EO-09 comes first | still **CONCILIAR** |
| "the Lord, the giver of life" and "light from light, true God from true God" (EO-09 only) | **CONFESSIONAL** via BSR-EO-09; an EO-01 citation resolves CONFESSIONAL |
| RC-06 / RC-08 Nicene chunks | CONCILIAR, unchanged; "begotten, not made" in the Catholic branch → CONCILIAR (RC-06/RC-08) |

**Mutation check:** with `return hits[0]` in place of the sort, the reordering test **fails**. With the sort restored,
it passes. The test binds.

**The Task 2d re-resolution, re-run in memory with no model calls**
(`session8/task4-card-changes-rerun.json`): **66 cards changed**, exactly as in session 7. **0 cards differ from
session 7's `task2d-card-changes.json`.** Per branch the figures are identical: Anglican 32, Roman Catholic 24,
Lutheran 8, Methodist/Wesleyan 1, Reformed/Presbyterian 1, Baptist 0, Mennonite/Anabaptist 0.

---

## 5. Task 5 — gate6-v1.5 under the replicate rule. **STOP. v1.3 stays in force.**

Artifact: `recovery-runs/session8/measure-v15.json`, from `session8/measure_v15.py`. The rule is written into
`docs/gate6/WoP_SJN_Gate6_MeasurementRule.md`.

**The runs:**
- **Baseline, v1.3:** tp-3; the s7-v13-control candidate run; session 7's three v1.3 replicates of TP-049 (reused).
- **Candidate, v1.5:** tp-4-v1.5 and s8-v15 (new run ids).
- **"Differs"** means accept against reject.
- **Replicated:** the four items that differed (TP-049, Q-161, Q-213) plus Q-160 by ruling, 3 fresh calls per version
  (run ids s8-rep-v1.3-1..3 and s8-rep-v1.5-1..3).

### Replicate table

| item | variant | v1.3 (3 replicates) | v1.5 (3 replicates) | read |
|---|---|---|---|---|
| TP-049 "the Father, the Son, and the Holy Ghost" (H05 Son) | **base** | A/C, R, A — **2/3** (session 7) | R, R, R — **0/3** | v1.5 rejects |
| Q-160 MA-01 doxology (H20) | base | R, R, A/C — **1/3** | A/C, A/C, A/C — **3/3** | **flip** |
| Q-161 RC-01-3 "Lord and giver of life" (H21) | spirit | R, R, R — 0/3 | A, A, A — **3/3** | re-opened |
| Q-213 AN-01 "our Lord and Saviour Jesus Christ" (H27) | spirit | R, R, R — 0/3 | R, A, R — 1/3 | both reject |

### The five checks

| check | result | |
|---|---|---|
| (1) tp-4 recall, majority-read ≥ 0.967 | **57/60 = 0.950** (single run 57; tp-3 58). Refused: TP-049, TP-059, TP-060 | **FAIL** |
| (2) Q-161 accepts by majority under v1.5 | 3/3 ACCEPT, floor FULL, no hazard | PASS |
| (3) no flip of the 12 non-creedal IDIOM rejections attributable to v1.5 | **Q-160**: v1.5 accept-majority, v1.3 reject-majority. The other 11 reject under both | **FAIL** |
| (4) both Q-277 candidates agree by majority | single runs agree with the v1.3 control, so no replicates: AN-03 ACCEPT, AN-04 ACCEPT_WITH_CAVEAT | PASS |
| (5) Q-160 under both versions | v1.5 3/3 accept, v1.3 1/3 → **creed carve-out implicated** | **STOP** |

**Decision:** the STOP rule applies. `PROMPT_VERSIONS["verifier"]` is still **gate6-v1.3**. The creed lines were **not**
edited. v1.4 and v1.5 remain selectable for replays.

### What the rubrics show (read these before ruling)

**Q-160.**
- **What happened:** all three v1.5 accepts raise IDIOM_OR_FORMULA, say the quoted doxology *alone* would be WORD_ONLY,
  and then set `asserted_outside_formula = Y`. They credit **a different sentence of the chunk** ("God's awesome glory
  … are perfect in holy love") and lift the cap. **None of the three mentions a creed.**
- **v1.3 permits the same move:** line 4 says a fixed formula is WORD_ONLY "unless the passage separately asserts the
  predicate outside the formula". The one v1.3 accept (replicate 3) reasons the same way.
- **What is measured:** the base prompt adds only the creed lines to v1.3, and under it the model takes that exit 3 of
  3 instead of 1 of 3. That is what the rule measures.
- **What is not established:** the cause. A 1/3-vs-3/3 split has a two-sided Fisher p of 0.4.
- **A question the author may prefer to rule on first:** should an outside-formula assertion *elsewhere in the chunk*
  rescue a citation whose quoted ≤15 words are the doxology? The card would print the doxology.

**TP-049.**
- **The result:** under v1.5 it gets the **base** prompt, with no JOINT PREDICATION and no doxology sentence, and is
  refused **3/3**. Session 7's v1.4 refusal and this session's single run make it **0 of 8** across v1.4 and v1.5.
- **v1.3:** 2 of 3 replicates plus tp-3's accept, so **3 of 4**. Its own v1.3 accepts are split: replicate 1 is
  PARTIAL, replicate 3 FULL.
- **The v1.5 reasons:** "a Trinitarian formula naming the three persons … mere mention within a doctrinal list"; "merely
  enumerates 'the Son'"; the subject is "three persons, not the Son specifically".
- **What this rules out:** both candidate causes session 7 and Chat considered. **The only text common to v1.4 and
  v1.5-base and absent from v1.3 is the creed lines.**
- **My honest read:** the refusal is defensible on the phrase. A bare list of the three names does not predicate the
  Son's *eternal filial relation*. TP-049 may be a weak true positive, and the 0.967 floor (58/60) makes one unstable
  item decide the gate. Worth the author's look as a fixture question, apart from the verifier.

**Q-161.** The spirit variant re-opens it 3/3 on its content ("Lord and giver of life", Life-giving, ACTION). The creed
carve-out does what it was written to do.

### Q-290 under v1.5 — both still refused

| item | row | phrase | verdict / reason code | variant |
|---|---|---|---|---|
| TP-059 | BSR-EO-02 | "There is only one God because there is only one Father" | **REJECT / BELOW_FLOOR** | base |
| TP-060 | BSR-EO-01 | "God is an eternal Father by nature" | **REJECT / BELOW_FLOOR** | base |

Both were refused under v1.3 (tp-3) and v1.4 (tp-4) too.

---

## 6. Task 6 — rulings and the standing rule

**The rulings file** (`author-rulings-pending-workbook.json`) now carries R6-13 to R6-16:
- **R6-13** has the deleted sentence, the variants, the v1.6 rename, and the measurement rule with a pointer to its doc.
- **R6-14** has the seven tags, the H27 change and its reason, and the file path.
- **R6-15** records the precedence rule and marks EO-09 "PENDING AUTHOR RULING".
- **R6-16** holds the adoption boundary, the eight rows to verify in Cowork, and the packet rebuild; `blocks_eo: false`.

Earlier entries were annotated:
- `R6-8.blocks` is now `DISCHARGED_BY_R6-14`.
- R6-11 has an `outcome` line.
- R6-6 has `amended_by`.

The file was re-serialized, so the git diff also re-indents entries that session 7 had compacted by hand. Content is
unchanged apart from the additions.

**The R6-6 amendment is recorded.** Fail-closed demotion applies only to rows whose bare tier is CATECHETICAL. That was
session 7's narrowing, and R6-16 ratifies it. The code (`registry.exposition_tier`) was already bounded this way.

**The standing rule** is in `docs/gate6/WoP_SJN_Gate6_MeasurementRule.md`, with a pointer in `scripts/sjn_recovery/README.md`.
Later measurement prompts will find it in both places.

**Pending: session 7 choices NOT yet ratified**, left exactly as they are:
1. the **3-word / 12-character phrase floor** (`CREED_PHRASE_MIN_WORDS` / `CREED_PHRASE_MIN_CHARS`) — **RATIFIED R6-21** (16 Sep; recorded session 9)
2. **"a CATECHETICAL row is never a registered creed text"** (`Registry.registered_creed_texts`) — **RATIFIED R6-22** (16 Sep; recorded session 9)
3. the **EO ladder** in `config.EO_CONSULTATION_LADDER` — **RATIFIED R6-23** (16 Sep; recorded session 9)

---

## 7. Task 7 — the EO prompt

`wop-scratch/WoP_SJN_Gate6_EOPrompt_20260916.txt`, updated in place with changes marked `[S8]`. The diff is 123 lines.

- **Banner:** still **NOT LAUNCHABLE**. It names the two open blockers, says gate6-v1.3 is in force and v1.5 failed with
  the Q-160 STOP, and states that TP-049 is refused under the base prompt. Session 7's banner, which blamed the JOINT
  PREDICATION line, was replaced.
- **Dependencies:** "sessions 5, 6, 7 AND 8" plus R6-13 to R6-16.
- **Not a blocker:** the finished-packet rebuild waits on the Cowork adoption verification (R6-16). The prompt says it
  does not block EO.
- **(a) agency tags: DISCHARGED (R6-14),** with the seven classes, the H27 reason and the file path.
- **(b) Creed row: DISCHARGED,** restated on the conciliar-only measurement (38/38; no run under 4 words; 0% translation
  failures; nothing fetched). Also: Hopko's Spirit clause stands only in EO-09.
- **(d) verifier: OPEN,** with the five checks and their results. EO does not launch until the author rules on the creed
  lines and a version carrying them passes all five. It may not launch on v1.3.
- **(e) NEW, the author's ruling on BSR-EO-09: OPEN,** with the 3c finding and what turns on it.
- **Task 3:** the verifier line now names **gate6-v1.3 as the version in force**. It says the branch may not run on it,
  and any replacement must pass under the replicate rule. The registered-texts list marks EO-09 §2 as pending (e).
  R6-15 precedence is added with the "begotten, not made" example. The Spirit-guard note gains the EO-09 wording point.
  The R6-14 classes are added.
- **Task 4 (Q-290):** both citations are still refused under v1.5.

**Remaining blockers: (d) the verifier and (e) the EO-09 ruling.**

---

## 8. Spend

| run | calls | USD |
|---|---:|---:|
| tp-4-v1.5 (60 items, v1.5) | 60 | 0.9529 |
| s8-v15 (16 candidates + 1 ceiling retry) | 17 | 0.5264 |
| s8-rep-v1.3-1..3 (Q-160, Q-161, Q-213; + 2 retries) | 11 | 0.4629 |
| s8-rep-v1.5-1..3 (TP-049, Q-160, Q-161, Q-213) | 12 | 0.5238 |
| **total** | **100** | **2.4661** |

That is against the 10 USD cap and the 6 USD report threshold (`session8/spend.json`). The ~3 USD expectation held.

---

## 9. What I think is wrong, with the artifact

1. **TP-049's cause is still unknown, and both earlier readings are ruled out.** Session 7 blamed JOINT PREDICATION.
   Chat blamed the doxology sentence and allowed variance. Under v1.5 TP-049 gets neither line and is refused 0/3. The
   only text common to v1.4 and v1.5-base and absent from v1.3 is the creed lines. Artifact: `session8/measure-v15.json`
   → `replicate_rubrics["TP-049|gate6-v1.5|*"]` (variant `gate6-v1.5/base`).
2. **"The creed carve-out is implicated" is what the rule says. It is not a diagnosis.** The Q-160 accepts reason through
   `asserted_outside_formula = Y` on another sentence of the chunk, a move v1.3's own line 4 allows and one v1.3
   replicate made. None mentions a creed. The rule is right to stop the gate, but ruling on the creed lines by
   *editing* them may miss the real question: whether a chunk-level outside assertion should rescue a quoted doxology.
   Artifact: `replicate_rubrics["Q-160-p1-BSR-MA-01-1|*"]`.
3. **Task 4's rule was already the code.** Highest-tier precedence has been `resolve_registered_phrase`'s behavior since
   session 7. The "longest match in EO-09" came from the 1d analysis script, which took the first text in list order.
   The re-run shows 0 card differences. Artifacts: `scripts/sjn_recovery/registry.py`
   (`resolve_registered_phrase`), `session8/task4-card-changes-rerun.json`.
4. **The recall floor is one item wide.** 0.967 means 58 of 60. With TP-049 unstable even under v1.3 (3 of 4), the floor
   decides a version on one item whose phrase, a bare list of the three names, arguably does not carry the family's
   predicate. Before the next measurement, the fixture item deserves the author's look as much as the verifier does.
5. **EO-09 cannot be decided on Fix 0 alone.** Fix 0's fallback assumed EO-01 supplies the Creed, and R6-5 removed that.
   And the one clause where EO-09's eligibility changes a tier is the Spirit's "the Lord, the Giver of Life", which is
   exactly where the R6-7 guard pushes the locator. Artifact: §3c above; `task3-creed-match-conciliar-only.json`.
6. **The Task 5 STOP wording.** I read "STOP, leave v1.3 in force, and report" as stopping the verifier change. I still
   finished Tasks 6 and 7: record-keeping, with no model calls and no change to the verifier. If you meant the whole
   session to halt, those two sets of edits are in the same commit and easy to review apart.

The workbook was not written, no packet was rebuilt or released, the public app is untouched, and EO did not run.
`src/_data/operational-state.yaml` was not edited; it would take the blocker change at your end-of-session wrap-up.
