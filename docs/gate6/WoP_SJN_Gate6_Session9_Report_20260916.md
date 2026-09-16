# SJN Gate 6, session 9 — fixture repair, phrase carries the assertion, EO-09, stop-rule sample size (16 September 2026)

Rulings R6-17 to R6-23 are recorded in the rulings file. The workbook was not written, no packet was rebuilt, nothing in
the public app changed, and **Eastern Orthodox did not run**. Spend was **2.27 USD** of the 10 USD cap (102 model calls),
below the 6 USD report threshold.

**The headline: gate6-v1.6 passed checks (2) to (5) but is NOT in force, because check (1) could not be run.**
- **Q-160 is closed.** It is refused **0 of 5** under v1.6. The model now refuses it itself; the code guard was not
  needed.
- **Check (1) is ruled on tp-5, and tp-5 does not exist.** R6-17 builds it only from an asserting sentence in TP-049's
  own chunk. That chunk is the **Methodist Articles of Religion, Article I**, not Westminster 2.3, and no sentence in
  it asserts the eternal filial relation.
- **v1.3 stays in force.** EO has one open blocker, (d), and it now waits on one author ruling: TP-049's phrase.
- **EO-09 is settled.** Blocker (e) is discharged by R6-19.

---

## 1. Task 1 — R6-17: TP-049's phrase. **STOPPED by its own condition; the fixture is unchanged.**

### What the fixture records

| field | value |
|---|---|
| item | TP-049 (Case Study Phrase Targets row 8, Q-039) |
| family | RNR-H05 "Son"; definition "Names the eternal filial relation of the Logos." |
| row / locator | **BSR-MW-01**, "Article I — Of Faith in the Holy Trinity" (Methodist / Wesleyan, Articles of Religion) |
| chunk hash | `c29f2b15…` (matches the stored chunk) |

The stored chunk, whole:

> There is but one living and true God, everlasting, without body or parts, of infinite power, wisdom, and goodness;
> the maker and preserver of all things, both visible and invisible. And in unity of this Godhead there are three
> persons, of one substance, power, and eternity—the Father, the Son, and the Holy Ghost.

**"the Son is eternally begotten of the Father" is not in it** (`guards.check_phrase` returns "not present verbatim").
I searched every stored chunk to find where it does stand:
- BSR-RP-01 Chapter 2.3 (Westminster)
- BSR-RP-04 Book of Confessions 6.013 (Westminster)
- BSR-BA-02 Chapter 2, paragraph 3 (Second London)

**No sentence in TP-049's chunk asserts the Son's eternal filial relation.** Per the task, three ranked candidates from
the chunk follow, and the fixture is unchanged: **no tp-5, no N-TP-049**. The word counts are the checker's
(`textutil.phrase_word_count`), which counts "eternity—the" as one word.

| rank | candidate (verbatim) | words | its weakness |
|---|---|---:|---|
| 1 | "of one substance, power, and eternity—the Father, the Son" | 9 | It asserts the Son's co-eternity and consubstantiality with the Father, **not his filial relation**. "Son" is a name in apposition. The cut also **drops the Holy Ghost** from a three-member list, so a card would print a two-person clause the Article does not make. |
| 2 | "three persons, of one substance, power, and eternity—the Father, the Son, and the Holy Ghost" | 15 (16 by whitespace) | This is the whole clause, faithful to the Article. But the grammatical subject is **the three persons jointly**, which is exactly the "names the Son in a list" shape the v1.5 refusals described, and it still asserts no filiation. It fits only because the checker joins the em-dash. |
| 3 | "And in unity of this Godhead there are three persons" | 10 | It **does not name the Son** at all. It asserts triunity, so WRONG_SUBJECT on its face. |

**Measured for information only** (not fixture items; `session9/measure-v16.json` → `tp049_in_chunk_candidates_info`), once
per version:

| candidate | gate6-v1.3 | gate6-v1.6 |
|---|---|---|
| C1 (rank 1) | ACCEPT / FULL: "eternal, fully divine identity of the Son" | ACCEPT / FULL |
| C2 (rank 2) | REJECT / WRONG_SUBJECT (subject "three persons … collectively") | REJECT / WRONG_SUBJECT |
| C3 (rank 3) | REJECT / WRONG_SUBJECT | REJECT / WRONG_SUBJECT |

*(In the artifact, rank 1 is `TP-049-C2` and rank 2 is `TP-049-C1`. The artifact ids follow clause order; the ranks
above are mine.)*

**The options for the author, ranked, each with its weakness:**
1. **Move TP-049 to BSR-MW-01 Article II:** "The Son, who is the Word of the Father, the very and eternal God"
   (14 words by the checker, verbatim in the stored Article II chunk). It names the Logos, the Father-relation and eternity together.
   *Weaknesses:*
   - It breaks R6-17's "same locator" constraint.
   - It is unmeasured.
   - Wesley's Article II omits the Anglican "begotten from everlasting of the Father", so it still asserts no
     *generation*.
   - It closely parallels TP-048 (Anglican Article II, "The Son, which is the Word of the Father").
2. **Adopt rank 1 as tp-5's phrase.** The verifier accepts it under both versions, so under the rule tp-5 would read
   **58/60** with no further spend. *Weakness:* by R6-17's own test it does not assert the eternal filial relation, and
   it cuts the Holy Ghost from the list.
3. **Retire TP-049 from the recall set.** *Weakness:* the floor then needs restating on 59 items. 57/59 = 0.966, just
   under 0.967, so the number itself needs a ruling.

---

## 2. Task 2 — R6-18 step A: the outside-formula rescues (no model calls). **The stop did NOT fire.**

Artifact: `session9/task2-rescues.json`, from `session9/task2_rescues.py`.

**Two instruments** (independent by instrument):
- **A:** every stored rubric in every JSON under `recovery-runs/` and `recovery-packets/`, as it stands after the code
  runs.
- **B:** every raw verifier reply in every `recovery-runs/*/calls.jsonl`, as the model returned it.

Both find the same Y set.

### Finished branches (live-1 cells + packets)

| branch | cell | candidate | phrase | final | the rubric the final rests on | on card | loses last citation | disposition |
|---|---|---|---|---|---|---|---|---|
| Roman Catholic | Q-297 (RNR-H38 Not made) | RC-01-1 (CCC 242) | "begotten not made, consubstantial with the Father" | ACCEPT_WITH_CAVEAT | sonnet v1.2, **Y** | **yes** (with RC-04-1, RC-06-1) | no | NO PUBLIC TILE |
| Roman Catholic | Q-297 | RC-07-1 (Compendium) | "begotten, not made, consubstantial with the Father" | ACCEPT_WITH_CAVEAT | sonnet v1.2, **Y** | no (4th survivor) | — | NO PUBLIC TILE |
| Anglican | Q-213 (RNR-H27 Savior) | AN-01-1 | "our Lord and Saviour Jesus Christ" | **REJECT** (lower floor: sonnet WORD_ONLY) | opus v1.2, Y | no | — | NO PUBLIC TILE |

- **Card accepts relying on the rescue: 1** (Q-297 RC-01-1). The threshold is more than 10.
- **Public-certified cells that would lose their last citation: 0.**
- **The stop did not fire.**

### Measurement runs (tp-3, tp-4, tp-4-v1.5, s7-*, s8-*)

| run | item | version | verdict with Y |
|---|---|---|---|
| tp-3 | TP-004 "God the Father Almighty" (Apostles' Creed, RP-04) | v1.3 | ACCEPT_WITH_CAVEAT |
| tp-3 | TP-006 "one Lord, Jesus Christ" (Nicene, RP-04) | v1.3 | ACCEPT_WITH_CAVEAT |
| tp-3 | TP-028 "Light from Light" (Nicene, RC-06) | v1.3 | ACCEPT_WITH_CAVEAT |
| s7-v14 | Q-160 MA-01 doxology | v1.4 | ACCEPT_WITH_CAVEAT |
| s8-rep-v1.3-3 | Q-160 | v1.3 | ACCEPT_WITH_CAVEAT |
| s8-v15, s8-rep-v1.5-1..3 | Q-160 | v1.5 | ACCEPT_WITH_CAVEAT ×4 |

- tp-4 and tp-4-v1.5 have **no** Y accepts. TP-004, TP-006 and TP-028 come back NA there, because the creed carve-out
  stops the flag.
- The Y answers that ended in REJECT (s7-v13-control Q-016 and Q-160; s8-rep-v1.3-2 Q-160) are in the artifact.
- Out of scope, listed rather than dropped: fa-3 PNM-072 (planted, opus v1.2, REJECT).

**The limit of this negative count.** live-1 holds 1,044 verifier calls: **639 on gate6-v1.1** and 405 on v1.2. Only
v1.2 has the field (401 replies carry it). A v1.1 rubric cannot show a rescue, because neither the flag nor its cap
existed. A formula accepted there was accepted outright, and step A does not count it.

---

## 3. Task 3 — R6-19: EO-09 at its own tier. **No resolver change; tests pass.**

`Registry.registered_creed_texts` already registers BSR-EO-09 "Synodikon §2 — The Symbol of Faith" at CONFESSIONAL, and
`resolve_registered_phrase` returns the highest tier. Confirmed live:

| phrase | registered texts holding it | resolves | an EO-01 citation resolves |
|---|---|---|---|
| "the Holy Spirit, the Lord, the Giver of Life" | **BSR-EO-09 only** (and printed in EO-01 "Nicene Creed") | **CONFESSIONAL** via EO-09 | CONFESSIONAL |
| "who proceeds from the Father" | EO-07 **and** EO-09 | **CONCILIAR** via EO-07 | CONCILIAR |

The tests, in `tests/test_session9_rulings.py`, **all pass**:
- `test_hopkos_spirit_clause_is_only_in_eo09_and_resolves_confessional`
- `test_a_phrase_in_both_eo09_and_eo07_resolves_conciliar`
- `test_eo09_is_a_registered_creed_text_on_its_symbol_of_faith_only`

The EO prompt records **blocker (e) as DISCHARGED by R6-19**.

---

## 4. Task 4 — gate6-v1.6 (R6-18 step B)

### What was removed

The permission in v1.5 is **one clause, not a whole sentence**. It sits at the end of line 4's fixed-formula sentence,
verbatim with its leading space:

```
 unless the passage separately asserts the predicate outside the formula.
```

It occurs once in each variant. **I removed that clause only.** The rest of the sentence, "A fixed formula is WORD_ONLY:
when the predicate's word occurs only inside an oath …, a doxology …, a greeting or an acclamation, the passage
PRESUPPOSES the predicate rather than asserting it, and the floor is WORD_ONLY", is the fixed-formula rule itself. It is
what floors Q-160, so removing the whole sentence would have removed the rule R6-18 relies on. The author's text follows
it verbatim.

**Checked and left alone:**
- **Line 5's `asserted_outside_formula` question stays.** It asks the question; it grants nothing. And 4c's guard needs
  the field.
- **The JOINT PREDICATION line** already requires the Spirit's name inside the quoted phrase.
- **The v1.4 flag tail's** "the standard's own assertion lies elsewhere" is a speech-act rule (item 3 = N), not a
  permission.

### The diff against v1.5 (both variants identical in this change; shown split at sentence boundaries)

```diff
 WORD_ONLY: the word appears but the proposition is not asserted (different sense, different subject, mere mention).
-A fixed formula is WORD_ONLY: … the passage PRESUPPOSES the predicate rather than asserting it, and the floor is WORD_ONLY unless the passage separately asserts the predicate outside the formula.
+A fixed formula is WORD_ONLY: … the passage PRESUPPOSES the predicate rather than asserting it, and the floor is WORD_ONLY.
+THE PHRASE CARRIES THE ASSERTION. The quoted phrase must itself assert the property of the required subject.
+Surrounding text may establish who the subject is or what the quoted words mean, but it may not supply an assertion the quoted words do not make.
+If the passage asserts the property only in a different sentence, the citation does not satisfy the family (BELOW_FLOOR); that other sentence is the one to cite.
 A CREED IS NOT A FIXED FORMULA IN THIS SENSE. …
```

**Size:** base goes from 5,346 to 5,691 characters, spirit from 6,624 to 6,969. **Nothing else changed:** the text before
character 2,448 and the text after the replacement are byte-identical.

### Versions (4b)

- `VERIFIER_SYSTEMS` now runs v1.2, v1.3, v1.4, v1.5, v1.6.
- `SCOPED_VERIFIER_SYSTEMS` holds v1.5 and v1.6, with the same spirit/base scoping (R6-13).
- **The inference-neighbouring line is renamed gate6-v1.7** in `prompts.py`, `rulings.py` and the R6-13 entry.

### The code guard (4c)

`agents.verdict_from_rubric` is the one function behind both `verify()` and `finalize()`. It now refuses any ACCEPT or
ACCEPT_WITH_CAVEAT whose rubric has `asserted_outside_formula = Y`:
- **Result:** REJECT / BELOW_FLOOR.
- **Recorded:** `verify()` writes `refused_by: "R6-18"` and `verdict_before_outside_formula_guard`. `finalize()` writes
  `refused_by` on the final verdict.
- **Refinalising cannot re-admit it.** The guard lives in the shared function.
- **The rubric field is kept.**

**Scoped to guarded versions:** `prompts.OUTSIDE_FORMULA_GUARDED_VERSIONS = ("gate6-v1.6",)`. Without the scope, the
guard would silently change the v1.3 baseline that this very measurement reads. It would also change the stored v1.2
rubrics at the R6-16 rebuild. See §9, item 4.

### Tests: **135 passed** (the full suite; 16 in `test_session9_rulings.py`)

| test | result |
|---|---|
| the guard refuses a synthetic Y accept (ACCEPT and ACCEPT_WITH_CAVEAT) | PASS |
| an N accept passes; an NA accept passes | PASS, PASS |
| a Y rubric from v1.3 or v1.5 is not rewritten | PASS |
| through `verify()` with a stubbed reply: `refused_by R6-18`, and `finalize()` keeps it refused | PASS |
| both v1.6 variants contain the new text verbatim, once, and not the removed clause; v1.6 = v1.5 with exactly that replacement | PASS (spirit, base) |
| v1.6 keeps the `asserted_outside_formula` field; scoping unchanged (H05 → base, H35 → spirit) | PASS |
| versions linear (v1.2 … v1.6) | PASS |

**Mutation check:** with `OUTSIDE_FORMULA_GUARDED_VERSIONS = ()`, the synthetic Y rubric comes back ACCEPT_WITH_CAVEAT,
so the refusal test binds. Session 8's `test_versions_stay_linear` pinned the exact four-version list. It now checks the
first four, and the session 9 test pins all five.

---

## 5. Task 5 — gate6-v1.6 under the rule as amended by R6-20

Artifact: `session9/measure-v16.json`, from `session9/measure_v16.py`.

**Baseline, gate6-v1.3, from existing results:**
- tp-3
- s7-v13-control
- session 7's v1.3 replicates of TP-049 and TP-050
- session 8's v1.3 replicates of Q-160, Q-161 and Q-213, reused and named in the artifact

**Candidate runs (new run ids):**
- tp-4-v1.6
- s9-v16: the 16 candidates, plus Q-297 RC-01-1 and the three TP-049 candidates
- s9-v13-info: the TP-049 candidates under v1.3
- s9-rep-v1.3-1..3 and s9-rep-v1.6-1..5

**What was replicated:**
- **Differing items (3 per version):** TP-045, Q-161 and Q-213.
- **Q-160 (5 under v1.6, as ruled):** v1.3 was to be topped up to 5 only if v1.6's majority would trigger the stop. It
  did not.

### Replicate table

| item | v1.3 | v1.6 | read |
|---|---|---|---|
| **Q-160** MA-01 doxology (H20) | R, R, A/C — **1/3** (session 8) | **R, R, R, R, R — 0/5** | rejects |
| TP-045 "without confusion, change, division or separation" (RC-01 CCC 467) | A, A, A — 3/3 | A, A, A — **3/3** | accepts |
| Q-161 RC-01-3 "Lord and giver of life" (H21) | R, R, R — 0/3 (session 8) | A, A, R — **2/3** | accepts |
| Q-213 AN-01 "our Lord and Saviour Jesus Christ" (H27) | R, R, R — 0/3 (session 8) | R, R, R — 0/3 | rejects |

### The seven measurements

| check | result | |
|---|---|---|
| **(1)** recall ≥ 0.967 on **tp-5** | **tp-5 does not exist** (§1). On **tp-4** under v1.6, the single run is 57/60 and the majority read **58/60 = 0.967**. The only item that differed is TP-045: refused once, 3/3 on replicates. Refused by majority: TP-059, TP-060. | **NOT EVALUABLE** |
| (2) Q-161 accepts by majority under v1.6 | 2 of 3 | PASS |
| (3) none of the 12 non-creedal IDIOM rejections accepts by majority under v1.6 | none (Q-160 read on its 5) | PASS |
| (4) both Q-277 candidates agree by majority | AN-03-1 ACCEPT, AN-04-1 ACCEPT_WITH_CAVEAT (single runs agree with v1.3; no replicates) | PASS |
| (5) Q-160 rejects by majority of 5 | **0/5** | PASS, **no STOP** |
| (6) N-TP-049, the old phrase, once under v1.6 | **ACCEPT_WITH_CAVEAT**, floor PARTIAL, "partially but not fully instantiates … eternal filial relation" | **not the expected REJECT**: reported, not a stop |
| (7) the Task 2 card rescue, Q-297 RC-01-1, once under v1.6 | **ACCEPT**, FULL, no hazard, `asserted_outside_formula` NA | **not refused** |

**Decision: gate6-v1.6 is NOT put in force. gate6-v1.3 stays in force** (`PROMPT_VERSIONS["verifier"]` is unchanged).
The ruling says to put v1.6 in force only if (1) to (5) all pass, and (1) was not run on its fixture.

**Two cautions on reading (1) from tp-4:**
- **The 58 counts TP-049's old phrase as accepted.** R6-17 calls that phrase the defect, and it was accepted on a single
  v1.6 call. Across versions it has now gone v1.3 3/4, v1.4 and v1.5 0/8, v1.6 1/1.
- **TP-045 is a ratified creed-in-catechism true positive.** On the single run it was **refused by the new guard**, and
  only the replicate rule restored it (§9, item 3).

### What the Q-160 rubrics show

**The guard was not needed.** All 5 v1.6 replicates and the single run set `asserted_outside_formula = Y` and **refuse in
the model's own verdict**:
- reason codes: BELOW_FLOOR ×2, NOT_ASSERTION ×2, WRONG_SUBJECT ×1 (plus the single run's NOT_ASSERTION);
- `refused_by` is null on every one.

Typical reason: "the actual assertion of God's glory appears elsewhere in the same article … but the cited phrase … is
WORD_ONLY". **The text change closed the rescue; the guard is belt and braces.**

### Q-290 under v1.6

| item | row | phrase | verdict / reason code | variant |
|---|---|---|---|---|
| TP-059 | BSR-EO-02 | "There is only one God because there is only one Father" | **REJECT / BELOW_FLOOR** | base |
| TP-060 | BSR-EO-01 | "God is an eternal Father by nature" | **REJECT / BELOW_FLOOR** | base |

The reasons: TP-059 asserts "a neighbouring claim about divine unity/monarchy, not … unbegotten"; TP-060 "concerns God's
eternal fatherhood … not the denial of the Father's own generation". Neither was refused by R6-18. Both are unchanged
since v1.3.

---

## 6. Task 6 — records

**Rulings file** (`author-rulings-pending-workbook.json`). R6-17 to R6-23 are added as `R6-17_tp049_fixture` …
`R6-23_eo_ladder_config`. The file keeps its existing 1-space indent, and the diff is additions plus four annotated
lines:
- **R6-17** has `outcome: CONDITION NOT MET`, `tp5_built: false` and `n_tp049_added: false`.
- **R6-18** has the verbatim text, the removed clause, the step A result, the guard's location and scope, and the
  version in force.
- **R6-15**'s `eo09_registered_creed_text` now reads "RULED R6-19 … (blocker (e) DISCHARGED)".
- **R6-13** gains `inference_line_version_amended: gate6-v1.7`, and its measurement rule gains `amended_by: R6-20`.

**The measurement rule** (`docs/gate6/WoP_SJN_Gate6_MeasurementRule.md`):
- **Rule 5 (R6-20):** a STOP item gets 5 per version, and the stop reads 3 of 5. The baseline is topped up only when
  the candidate's majority would trigger the stop.
- **A new line:** a check ruled on a fixture that could not be built is *not evaluable*, and no version goes into force
  on it.
- **The reference implementation** is now `session9/measure_v16.py`.
- **The record table** has a session 9 row.

### R6-21, R6-22 and R6-23: where each was marked RATIFIED

| ruling | rulings file | code / config | reports |
|---|---|---|---|
| R6-21 phrase floor | `R6-21_phrase_floor` (status RATIFIED, `as_implemented`) | `registry.py` comment above the constants; `rulings.py` docstring | Session 7 §3 "Phrase floor" and §9 item 8; Session 8 §6 pending list |
| R6-22 catechetical rows | `R6-22_catechetical_rows` | `Registry.registered_creed_texts` docstring; `rulings.py` docstring | Session 7 §3; Session 8 §6 pending list |
| R6-23 EO ladder | `R6-23_eo_ladder_config` | **`config.EO_CONSULTATION_LADDER` comment cites R6-23**; `rulings.py` docstring | Session 7 §9 item 6; Session 8 §6 pending list |

The reports were **annotated in place** ("*[RATIFIED R6-2x, 16 Sep — recorded session 9.]*"), not rewritten.
**No session 7 choice is still pending.**

### R6-21: the phrase floor exactly as implemented (`scripts/sjn_recovery/registry.py`)

```python
CREED_PHRASE_MIN_WORDS = 3
CREED_PHRASE_MIN_CHARS = 12
```

```python
        key = punct_key(phrase)
        if len(key.split()) < CREED_PHRASE_MIN_WORDS or len(key) < CREED_PHRASE_MIN_CHARS:
            return None
```

**The implementation matches session 7's "3 words / 12 characters"**, measured on the punctuation-free key, so R6-21 is
recorded. Pinned by `test_the_phrase_floor_is_three_words_and_twelve_characters`:
- "not made" does not resolve;
- "God of God" (3 words, 10 characters) does not resolve;
- "begotten, not made" does.

One difference in wording, not in the numbers, is in §9.

### R6-22: the test

**No test existed; one was added:** `test_a_catechetical_row_is_never_a_registered_creed_text`. It checks that in all
eight branches no registered creed text comes from a row whose bare tier is CATECHETICAL. **It binds:** it first asserts
that BSR-EO-01 is CATECHETICAL *and* has chunks whose locator names the Creed. R6-23 is pinned by
`test_the_eo_ladder_is_read_from_config`: a config change moves `packets.ladder_tier`, and the R6-23 comment sits above
the dict.

---

## 7. Task 7 — the EO prompt

`wop-scratch/WoP_SJN_Gate6_EOPrompt_20260916.txt` was updated in place, with changes marked `[S9]`. The diff is 185 lines,
committed as `session9/eo-prompt-s9.diff`.

**Banner: still NOT LAUNCHABLE.** It now reads: one blocker open, (d), waiting on one ruling, TP-049's phrase. v1.3 is in
force; v1.6 passed (2) to (5); tp-5 could not be built.

**Blockers:**
- **(d):** the seven measurements, the Q-160 0/5 result, and what remains.
- **(e):** DISCHARGED (R6-19), with the two resolution tests.

**Everything else:**
- **Dependencies:** sessions 5 to 9 and R6-17 to R6-23.
- **Verifier line (Task 3):** v1.3 is in force; v1.6 is the expected version.
- **New Task 3 bullet:** THE PHRASE CARRIES THE ASSERTION, with an instruction to report and *read* every guard refusal
  (TP-045).
- **Registered texts:** EO-09 §2 is marked registered and CONFESSIONAL.
- **R6-21 and R6-22 are stated**, in place of nothing pending; R6-23 is noted at the ladder.
- **Hopko's Spirit clause** resolves CONFESSIONAL.
- **Q-290:** refused under v1.6, and R6-21 does not decide its fallback.
- **The finished-packet rebuild note is kept:** it waits on adoption verification (R6-16) and does not block EO.
  Step A's single card rescue, Q-297 RC-01-1, is added (not refused under v1.6).

The EO prompt never listed a session 7 choice as pending, so nothing there needed replacing. The rulings were added
where the prompt uses them.

---

## 8. Spend

| run | calls | USD |
|---|---:|---:|
| tp-4-v1.6 (60 items + 1 ceiling retry) | 61 | 1.0241 |
| s9-v16 (16 candidates, Q-297, 3 TP-049 candidates) | 20 | 0.5893 |
| s9-v13-info (3 TP-049 candidates under v1.3) | 3 | 0.0722 |
| s9-rep-v1.3-1..3 (TP-045) | 3 | 0.0364 |
| s9-rep-v1.6-1..5 (Q-160 ×5; TP-045, Q-161, Q-213 ×3; + retries) | 15 | 0.5452 |
| **total** | **102** | **2.2672** |

That is against the 10 USD cap and the 6 USD report threshold (`session9/spend.json`), under the ~3–4 USD expectation.

---

## 9. What I think is wrong, with the artifact

1. **The prompt's TP-049 premise is wrong about the chunk.** The expected candidate is Westminster 2.3's wording, but
   TP-049 is the Methodist Articles, Article I. Chat's reading of the *refusals* holds: the old phrase names the Son and
   does not assert filiation. But the fix the ruling names cannot be applied to this item.
   Artifact: `recovery-runs/tp-4/fixture.json` → TP-049; the §1 search.
2. **"The fixture item is the defect, not the verifier" is only half the story.** The item is defective. The verifier
   is also unstable on it:
   - v1.3: 3 of 4 accept
   - v1.4 and v1.5: 0 of 8
   - v1.6: 1 of 1 accept (PARTIAL)

   N-TP-049 as a regression negative "expected REJECT" will not be a stable negative.
   Artifacts: `session7/replicate-tp049-tp050.json`, `session8/replicates.json`, `tp-4-v1.6/tp-results.json`.
3. **The R6-18 guard, as ruled, refuses true positives when the model misuses Y.** The verifier sometimes answers
   `asserted_outside_formula = Y` when the quoted phrase *itself* carries the assertion:
   - **TP-045 under v1.6:** "the quoted phrase itself carries the full assertion", yet Y, so the guard refused it.
   - **Earlier:** TP-004, TP-006 and TP-028 under v1.3; Q-297 RC-01-1 under v1.2.

   The replicate rule rescued TP-045 in measurement. A branch run makes one call per candidate, so on tp-4 the guard
   would drop about 1 true positive in 60. **The fix, if the author wants one, is line 5's definition of Y, not the
   guard**, for example "Y only if the assertion lies in words the quoted phrase does not include". Not done here:
   R6-18's text is verbatim and line 5 was outside it. Artifact: `tp-4-v1.6/tp-results.json` → TP-045
   (`refused_by: R6-18`, `floor_reason`).
4. **The guard's scope is my choice and the author should confirm it.** I applied it only to rubrics from gate6-v1.6
   on. Applied to every rubric, it would:
   - change the v1.3 baseline this measurement reads (Q-160 1/3 would become 0/3);
   - change v1.3 if v1.6 never goes in force;
   - refuse Q-297 RC-01-1 at the R6-16 rebuild, though not its cell's last citation, and v1.6 itself accepts it.

   Widening it is one tuple: `prompts.OUTSIDE_FORMULA_GUARDED_VERSIONS`.
5. **Task 4a says "sentence(s)"; the permission is a clause.** Replacing the whole line 4 sentence would have deleted
   the fixed-formula rule that floors doxologies, the very rule Q-160 needs. I cut the clause and kept the rest (§4).
6. **R6-21's wording differs from the code in one respect.** The ruling says a shorter phrase "is refused BELOW_FLOOR".
   In code, a phrase under the floor simply **does not resolve** to a registered creed or definition text: it keeps
   its host row's exposition tier and is not refused. The numbers match, so R6-21 is recorded, with a `note` in the
   rulings entry. If refusal was meant, that is a behaviour change for a later session.
7. **R6-22 has an unguarded path in code.** `registered_creed_texts` admits any row in R6-5's
   `chunk_level_creed_resolution_allowed_rows` whatever its tier. None of those four rows (EO-07, EO-14, RC-06, RC-08) is
   CATECHETICAL, so the ruling holds today and the new test passes. But adding a catechetical row to that list would
   break "never". I did not add the one-line tier check: the prompt said the ratifications change no behaviour.
8. **Q-161 passes check (2) on 2 of 3.** The one rejection raised IDIOM_OR_FORMULA on the creed title despite the
   carve-out. That is thin. Artifact: `session9/replicates.json` → `Q-161-p1-BSR-RC-01-3|gate6-v1.6|3`.
9. **Check (3)'s wording changed between sessions.** Session 8 used "flip … attributable to the candidate"; this prompt
   says "none may flip to accept by majority". I read it as no accept-majority under v1.6, which is the stricter
   reading. Both readings pass.

The workbook was not written, no packet was rebuilt or released, the public app is untouched, and EO did not run.
`src/_data/operational-state.yaml` was not edited. It takes the blocker change ((e) discharged, (d) waiting on TP-049) at
your end-of-session wrap-up.
