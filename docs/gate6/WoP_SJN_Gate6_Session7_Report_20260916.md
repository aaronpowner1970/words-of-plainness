# SJN Gate 6, session 7 — pre-Eastern-Orthodox repairs (16 September 2026)

Rulings R6-5 to R6-12 applied in memory. The workbook was not written, no packet was rebuilt, nothing
in the public app changed, and **Eastern Orthodox did not run**. Spend **2.51 USD** of the 10 USD cap
(107 model calls), below the 6 USD report threshold.

**The headline: gate6-v1.4 is NOT in force.** It failed two of its four regression checks, and the
cause is diagnosed, not guessed. gate6-v1.3 remains the verifier. EO stays blocked.

---

## 1. R6-5 to R6-12 as applied

All eight are in `data-sources/sjn/recovery-runs/author-rulings-pending-workbook.json`, read by
`scripts/sjn_recovery/rulings.py`, each with the workbook change that supersedes it.

| ruling | what the harness now does |
|---|---|
| **R6-5** | A **registry-override hook** (`rulings.registry_overrides`, applied in `Registry.__init__` exactly as a retirement is). BSR-EO-01 is re-typed in memory; once the workbook carries a field it is read from there and a disagreement raises `SystemExit`. |
| **R6-6** | Four adoption columns on every ratified row, in the author's migration order. |
| **R6-7** | A code guard in `agents.CellRunner.verify`: on a family whose required subject **is** the Holy Spirit, an accept whose phrase names no Spirit token is refused `WRONG_SUBJECT`. |
| **R6-8** | `rulings.agency_tags()` carries only the ratified tag; proposals are written to a separate file and never sent to a model. |
| **R6-9** | `Registry.assert_second_tier_rank()` asserts from APP CONFIG and stops on failure; `exposition_tier()` resolves the second tier with its display qualifier. APP CONFIG unchanged. |
| **R6-10** | `registered_definition_texts()` + `resolve_registered_phrase()`. |
| **R6-11** | `prompts.VERIFIER_SYSTEMS["gate6-v1.4"]` built; **not** selected. `guards.creedal_silence_stop()` is the clause-4 hard stop. |
| **R6-12** | Recorded with its exact disclosure text; queued for the next workbook version. |

`Registry()` output for the three rows the report asks for:

```
BSR-EO-01  workbook CONCILIAR / "Nicene-Constantinopolitan Creed / Symbol of Faith (OCA)" / All Orthodox / UNIVERSAL
           ruled     CATECHETICAL / "*The Orthodox Faith*, Vol. I (Hopko) — The Symbol of Faith"
                     / OCA (catechetical series by one author, published by the OCA) / JURISDICTIONAL
           same_work_as BSR-EO-02   eo_ladder_tier B   creed_resolution PHRASE
           adoption  ISSUED_UNADOPTED   exposition tier  OFFICIAL_EXPOSITION (catechism, not synodally adopted)
           card says "not officially adopted (catechism, not synodally adopted)"
BSR-EO-02  CATECHETICAL, ISSUED_UNADOPTED -> OFFICIAL_EXPOSITION (catechism, not synodally adopted)
           card says "not officially adopted (catechism, not synodally adopted)"
BSR-EO-04  CATECHETICAL (historic), ADOPTED, ONE_CHURCH -> CATECHETICAL (historic), unchanged
           card says "approved by Most Holy Governing Synod of the Russian Church (one church)"
           act records BOTH dates: host title page Moscow 1830; registry and Schaff 1839
```

Independence: `HOPKO-OF-VOL1 = [BSR-EO-01, BSR-EO-02]`, one work, one observation.

---

## 2. Task 1d — the Hopko match count. **The trigger did not fire.**

Instrument: the session-6 review's own 27-clause OCA-wording list (`wop-scratch/zz_main_20260915.py`),
re-run against the registered creed texts of the branch under `textutil.punct_key`.
Artifact: `recovery-runs/session7/task1d-hopko-creed-match.json`.

- BSR-EO-01: 19 chunks, **1,203 sentences, 38 creed-bearing** — the session-6 figures reproduce exactly.
- **38 of 38** creed-bearing sentences contain a creed phrase standing verbatim in a registered creed
  text (BSR-EO-07 on 42 clause hits, BSR-EO-09 §2 on 16). **0 misses.**

That first measurement is circular on its own — the same clause list is on both sides — so it is
backed by a second that is not: for each creed-bearing sentence, the **longest contiguous word-run
that stands verbatim in a registered creed text**. Every sentence carries one, and the distribution is

```
words  4  5  6  7  8  9 10 12 13 14 16 20 21 22 26 31
cells  1  4  7  6  2  3  1  4  1  1  1  1  1  2  2  1
```

A locator cutting ≤15 words from any creed-bearing Hopko sentence has a run of at least four words to
land on. **No OCA Creed-as-prayer row is proposed, and the EO blocker (b) is discharged.**

**But four of the 27 listed clause wordings do not match**, and these are exactly the translation
differences the trigger was written to catch. They are listed with the nearest registered wording
because the author should see them even though they do not fire the trigger:

| listed clause | nearest registered wording | shared |
|---|---|---|
| "rose again on the third day" | EO-09: "…and **on the third day** he rose again according to the scriptures…" | 4 words |
| "whose kingdom shall have no end" | EO-07: "…and his **kingdom shall have no end**…" | 5 words |
| "who with the father and the son together is worshipped and glorified" | EO-09: "…**who with the father and the son** is worshiped and glorified…" | 7 words |
| "who spoke by the prophets" | EO-07: "…**who spoke** through the prophets…" | 2 words |

These are the review script's list wording, not Hopko's, so they do not show a failure in EO-01. They
do show that EO-07, EO-09 and EO-12 differ from one another, which matters for any *future* claim that
a particular clause is registered.

---

## 3. Task 2 — the registered texts, the tests, and what moved

Artifact: `recovery-runs/session7/task2-registered-texts.json`.

**The rule, mechanical and stated.** A citation resolves to a creed's or a definition's tier only when
its phrase — NFKC-casefolded, punctuation stripped, whitespace collapsed (`textutil.punct_key`, the
same key R6-4's one-text-one-slot guard uses, so the two rules can never disagree about "the same
words") — stands verbatim in a **registered** text of the **same branch**.

A chunk is a **registered creed text** when its locator names a creed AND its row is either one of
R6-5's allowed rows or a row whose bare tier is CONCILIAR or CONFESSIONAL — the creed printed as a
text inside a conciliar or confessional standard. **A CATECHETICAL row is never a registered creed
text.** *[RATIFIED R6-22, 16 Sep — recorded session 9.]* That is clause 3, made mechanical.

A chunk is a **registered definition text** when its locator names a definition of faith / horos /
confession of faith, its row's bare tier is CONCILIAR, and the locator names no canon or anathema.

**Phrase floor: 3 words and 12 characters.** *[RATIFIED R6-21, 16 Sep — recorded session 9.]* "begotten, not made" (3 words, 17 chars) and "light of
light" (3 words, 14) are the shortest clauses the author's examples turn on, so the floor sits directly
below them. This is a judgement call and I am flagging it: "the Holy Spirit" (3 words, 15 chars) also
clears it, though no such phrase would ever be an accept.

### Registered creed texts, every branch

| branch | registered creed texts | resolves to |
|---|---|---|
| Eastern Orthodox | EO-07 "THE SYMBOL OF FAITH"; EO-14 "THE CREED"; EO-12 ×12 Greek articles; EO-09 "Synodikon §2 — The Symbol of Faith" | CONCILIAR (EO-07, EO-14, EO-12); CONFESSIONAL (EO-09) |
| Roman Catholic | RC-06 "Apostles' Creed", "Nicene Creed"; RC-08 same two | CONCILIAR |
| Anglican | AN-03 "Athanasian Creed (Quicunque Vult)" | CONFESSIONAL |
| Lutheran | LU-01 "Ecumenical Creeds: Apostles' / Nicene / Athanasian" (+12 more creed-located BoC chunks) | CONFESSIONAL |
| Reformed / Presbyterian | RP-04 Book of Confessions 1.x (Nicene) and 2.x (Apostles') | CONFESSIONAL |
| Baptist, Methodist / Wesleyan, Mennonite / Anabaptist | **none** | — |

**A gap worth naming:** the Anglican branch registers the *Athanasian* Creed as a text but not the
Apostles' or the Nicene. So an Apostles'-Creed phrase quoted from AN-04 or AN-05 resolves to the host
row, not CONCILIAR. That is the rule working as written, but it is a registry gap, not a doctrine.

### Registered definition texts (R6-10)

| branch | definition texts | excluded |
|---|---|---|
| Eastern Orthodox | EO-06 ×20 (Chalcedon 451, III Constantinople 680–681); EO-13 ×10 (Session XVIII, a lineage translation of the same horos) | — |
| Roman Catholic | RC-04 ×4 "Constitution 1 (Confession of Faith — Firmiter credimus)" | RC-04 Constitution 2 "Damnamus ergo"; all 18 RC-02 canons |
| every other branch | **none** | — |

**TP-042 to TP-045** — the Catholic Catechism quoting Chalcedon. **The Catholic branch registers no
Chalcedonian definition text.** All four therefore keep BSR-RC-01's tier, CATECHETICAL (RC-01 is
ADOPTED by *Fidei Depositum*). Confirmed in the tp-4 fixture.

### Chunk-level creed resolution, now disabled

Kept only on BSR-EO-07, BSR-EO-14, BSR-RC-06, BSR-RC-08. **Disabled** on BSR-EO-01 (19 of 19 locators
matched), BSR-EO-04 (10), BSR-AN-05 (8), BSR-AN-04 (3), BSR-EO-09, BSR-LU-01 (15), BSR-LU-03, BSR-RP-04 (6).

### Task 2c tests — all pass (`tests/test_session7_rulings.py`)

| test | result |
|---|---|
| an EO-01 exposition sentence | `OFFICIAL_EXPOSITION (catechism, not synodally adopted)`, **not** CONCILIAR |
| "begotten, not made" quoted inside EO-01 | **CONCILIAR** (hit: EO-07 "THE SYMBOL OF FAITH") |
| an AN-05 "Why does the Creed say …" answer | AN-05's resolved tier — `OFFICIAL_EXPOSITION`, since AN-05 is UNVERIFIED. **Not CONCILIAR** |
| the EO-07 creed chunk | CONCILIAR, by phrase and by chunk |
| RC-06 Nicene | CONCILIAR, unchanged |
| a canon phrase (RC-02 Canon I.1) quoted in a catechism | the host tier (RC-01 CATECHETICAL), **not** CONCILIAR |

### Task 2d — what moves on the seven finished branches

No model calls; pure re-resolution plus a re-run of the allocator.
Artifact: `recovery-runs/session7/task2d-card-changes.json`. **Nothing was released.**

| branch | cards | changed | tier moves | order changes | slot changes |
|---|---:|---:|---:|---:|---:|
| Anglican | 43 | 32 | 39 | 5 | 8 |
| Roman Catholic | 34 | 24 | 19 | 4 | 19 |
| Lutheran | 39 | 8 | 9 | 0 | 1 |
| Methodist / Wesleyan | 37 | 1 | 0 | 1 | 0 |
| Reformed / Presbyterian | 16 | 1 | 0 | 1 | 0 |
| Baptist | 37 | 0 | 0 | 0 | 0 |
| Mennonite / Anabaptist | 41 | 0 | 0 | 0 | 0 |
| **total** | **247** | **66** | **67** | **12** | **28** |

Of the 67 tier moves, **57 are the adoption field** (a catechetical row falling to OFFICIAL_EXPOSITION)
and **10 are a registered creed phrase raising a catechetical row**: AN-04 ×7 → CONFESSIONAL (quoting
the Athanasian Creed registered in AN-03), AN-02 ×1 and LU-03 ×1 → CONFESSIONAL, RC-01 ×1 → CONCILIAR
(the CCC quoting the Nicene Creed registered in RC-06).

---

## 4. Task 3 — the adoption field

Artifact: `recovery-runs/session7/task3-adoption.json`.

**The rank assertion.** APP CONFIG `authority_tier_rank` =
`CONCILIAR | CONFESSIONAL | CATECHETICAL | OFFICIAL_EXPOSITION | CURRENT_OFFICIAL_WITNESS`.
OFFICIAL_EXPOSITION is at index 3, CATECHETICAL at 2 — **directly below, as R6-9 requires.** The
harness asserts this at every `Registry()` and stops if it ever ceases to hold. **APP CONFIG was not
changed.** `bare_tier()` strips the display qualifier, so the rank is the rank.

**Migration** (44 ratified rows, in the author's order):

| step | rows |
|---|---:|
| the workbook already carries a value | 0 |
| ADOPTED / ISSUED_UNADOPTED by ruling | 6 — RC-01, RP-02, LU-01, EO-04 (ADOPTED); EO-01, EO-02 (ISSUED_UNADOPTED) |
| NOT_APPLICABLE mechanically | 30 |
| **UNVERIFIED (default)** | **8** — AN-02, AN-04, AN-05, BA-03, LU-03, RC-07, RP-03, RP-05 |

**A narrowing I made, stated plainly.** The ruling says UNVERIFIED fails closed to OFFICIAL_EXPOSITION.
I apply that **only where the row's bare tier is CATECHETICAL**. Applied to a CONFESSIONAL row it would
demote the Westminster **Larger** Catechism (RP-03) and the Heidelberg (RP-05) below the Westminster
Shorter — the Shorter being ADOPTED only because the author happened to name it and not its twin. The
session-6 review states clause 3's reach as "catechetical and expository rows", so that is where I
stopped. If you want the broader reading, say so and it is a one-line change; those two rows would
then fall two ranks and move Reformed cards.

**Rows whose tier moves** (7):

| row | branch | from | to | status | card says |
|---|---|---|---|---|---|
| BSR-AN-02 | Anglican | CATECHETICAL | OFFICIAL_EXPOSITION | UNVERIFIED | "adoption unverified (catechism, not synodally adopted)" |
| BSR-AN-04 | Anglican | CATECHETICAL | OFFICIAL_EXPOSITION | UNVERIFIED | same |
| BSR-AN-05 | Anglican | CATECHETICAL | OFFICIAL_EXPOSITION | UNVERIFIED | same |
| BSR-LU-03 | Lutheran | CATECHETICAL | OFFICIAL_EXPOSITION | UNVERIFIED | same |
| BSR-RC-07 | Roman Catholic | CATECHETICAL | OFFICIAL_EXPOSITION | UNVERIFIED | same |
| BSR-EO-01 | Eastern Orthodox | CATECHETICAL | OFFICIAL_EXPOSITION | ISSUED_UNADOPTED | "not officially adopted (catechism, not synodally adopted)" |
| BSR-EO-02 | Eastern Orthodox | CATECHETICAL | OFFICIAL_EXPOSITION | ISSUED_UNADOPTED | same |

**Eastern Orthodox catechetical rows, the ranks they now resolve to:**

| row | bare tier | adoption | resolves to | rank |
|---|---|---|---|---:|
| BSR-EO-01 | CATECHETICAL | ISSUED_UNADOPTED | OFFICIAL_EXPOSITION | 3 |
| BSR-EO-02 | CATECHETICAL | ISSUED_UNADOPTED | OFFICIAL_EXPOSITION | 3 |
| BSR-EO-04 | CATECHETICAL (historic) | ADOPTED, ONE_CHURCH | CATECHETICAL (historic) | 2, with the one-church disclosure |

So Philaret now outranks Hopko on every EO card — which is the substantive effect of clause 3 on this
branch, and it looks right.

**ADOPTED proposals** (not set; the author rules). None was set on my own judgement.

| row | proposed act | weakness |
|---|---|---|
| BSR-RC-07 | Compendium of the CCC: approved by Benedict XVI, motu proprio, 28 June 2005 | **not verified this session**; proposed from the document's own front matter |
| BSR-AN-02 | BCP 1662 annexed to the Act of Uniformity 1662 | a statute, not a synodal act — whether that is "the institution" here is itself a ruling |
| BSR-AN-04 | BCP 1979 adopted by the General Convention of TEC | **not verified this session** |
| BSR-AN-05 | "To Be a Christian" (2020) approved by the ACNA College of Bishops | "approved edition" is the row's own title, not a cited act |
| BSR-LU-03 | the Small Catechism is a confession of the Book of Concord | the CPH file is a publisher's edition of a confessional text |
| BSR-RP-03 | Westminster Larger Catechism: the same confessional act you named for RP-02 | **no tier change either way** under the narrowing above |
| BSR-RP-05 | Heidelberg Catechism: adopted by the CRC and RCA as a doctrinal standard | as RP-03 |

### Task 3d tests — all pass

EO-01/EO-02 exposition → OFFICIAL_EXPOSITION with "not officially adopted"; EO-04 exposition →
CATECHETICAL with the one-church disclosure; an UNVERIFIED catechetical row → OFFICIAL_EXPOSITION with
"adoption unverified"; `bare_tier()` ignores the qualifier; a CONFESSIONAL row is never demoted.

---

## 5. Task 4 — the four measurements. **v1.4 is NOT in force.**

### (1) tp-4 under gate6-v1.4 — **FAIL**

| run | verifier | items | accepted | recall | refused |
|---|---|---:|---:|---:|---|
| tp-3 | gate6-v1.3 | 60 | 58 | **0.967** | TP-059, TP-060 |
| **tp-4** | **gate6-v1.4** | 60 | 56 | **0.933** | TP-049, TP-050, TP-059, TP-060 |

The two fixtures are **identical item for item** (same 60 family/phrase pairs, same id→item mapping),
so this is a clean comparison. Recall fell below the 0.967 floor.

### (2) Q-161 RC-01-3, the one creedal IDIOM rejection — **PASS, and clean**

`REJECT / BELOW_FLOOR` (WORD_ONLY, IDIOM_OR_FORMULA) → **ACCEPT / OK** at FULL, no hazard raised.
Under the v1.3 control it stays REJECT. The creed carve-out does exactly what it was written to do,
and nothing else is doing it.

### (3) the non-creedal IDIOM rejections — **FAIL, by one**

**A correction to the prompt's arithmetic: there are 12, not 13.** At HEAD, 14 candidates carry the
flag on current rubrics: 1 sits on a card (Q-297), 13 are rejections, and 1 of those 13 is the creedal
one (Q-161). 13 − 1 = **12 non-creedal rejections**.

Two flipped to accept under v1.4. I ran a **gate6-v1.3 control over the same 16 candidates** to
separate the creed lines from run-to-run variance:

| candidate | HEAD | v1.4 | v1.3 control | attributable to v1.4? |
|---|---|---|---|---|
| Q-213 AN-01 "our Lord and Saviour Jesus Christ" | REJECT | ACCEPT | **ACCEPT** | **no** — variance (and opus already accepted it at HEAD) |
| Q-160 MA-01 "To the one holy and ever-loving triune God be glory for ever and ever" | REJECT | ACCEPT_WITH_CAVEAT | **REJECT** | **yes** |
| the other 10 | REJECT | REJECT | REJECT | — |

**One new false accept attributable to v1.4.** Q-160 is a doxology, not a creed; line 4 still lists
doxologies explicitly, so this looks like the "A CREED IS NOT A FIXED FORMULA" carve-out loosening the
model's reading of *fixed formula* generally rather than only for creeds.

### (4) both Q-277 Athanasian candidates — **PASS, but the diagnosis behind it was wrong**

| candidate | phrase | HEAD | v1.4 | v1.3 control |
|---|---|---|---|---|
| Q-277-p1-BSR-AN-04-1 | "the Father is Almighty, the Son Almighty, and the Holy Ghost Almighty" | ACCEPT_WITH_CAVEAT | ACCEPT_WITH_CAVEAT | ACCEPT_WITH_CAVEAT |
| Q-277-p1-BSR-AN-03-1 | "the Father is Almighty, the Son Almighty: and the Holy Ghost Almighty" | REJECT (WRONG_SUBJECT) | ACCEPT_WITH_CAVEAT | ACCEPT_WITH_CAVEAT |

They **agree**, and the Spirit-name guard passes both (`spirit_name_in_phrase = Y` — the phrase carries
"Holy Ghost" and "Almighty", as R6-7 requires). Rubrics: subject Y, speech act Y, floor FULL, hazards
`[FAMILY_VARIATION]`, verdict ACCEPT_WITH_CAVEAT.

**But they agree under the v1.3 control too.** The session-6 finding — that identical Athanasian wording
was accepted from AN-04 and refused from AN-03 — was **model variance in that run, not the rule gap it
was read as.** JOINT PREDICATION did not fix it, because there was nothing to fix. Worth knowing before
any further rule is written on that evidence.

### Why tp-4 lost recall — replicated, not guessed

Both new refusals are family **RNR-H05 (Son)**. Three replicates per item per version
(`recovery-runs/session7/replicate-tp049-tp050.json`):

| item | phrase | v1.3 | v1.4 |
|---|---|---:|---:|
| TP-049 | "the Father, the Son, and the Holy Ghost" | **2 / 3 accept** | **0 / 3 accept** |
| TP-050 | "the only Son, the Word who became flesh" | 3 / 3 accept | 2 / 3 accept |

All three v1.4 refusals of TP-049 reason in the JOINT PREDICATION line's own words — "a bare
enumeration", "a fixed Trinitarian naming formula that mentions 'the Son' without asserting …". **That
line is written for THE HOLY SPIRIT and is leaking onto other families.** TP-050's single refusal is
within variance. TP-049 was also unstable under v1.3 (2/3), so its tp-3 accept was partly luck.

**The fix I would propose, and did not make:** send the JOINT PREDICATION line only where the family's
required subject is or includes the Holy Spirit. The rulings say the line goes in VERBATIM, so I have
left it verbatim and unscoped, and left v1.3 in force.

### The Spirit token set (R6-7)

`{"holy spirit", "holy ghost", "spirit", "pneuma", "πνευμα"}`, matched as substrings after NFKC
casefolding and combining-mark stripping, so πνεῦμα / Πνεύματος fold to the πνευμα stem.

**A consequence you should see.** The guard as the prompt states it is unconditional. On RNR-H34
(Giver of life) and RNR-H35 (Eternal power and might) — the two families whose required subject *is*
the Spirit — the Creed's own **"the Lord, the giver of life"**, cut short of "and in the Holy Spirit",
is refused WRONG_SUBJECT. The locator must cut the clause so the Spirit's name is inside the quoted
fifteen words. That is the rule applied to its own hardest case, not a defect, but it is a live trap
for EO and it is written into the EO prompt.

### Agency tags (R6-8)

`data-sources/sjn/recovery-runs/spirit-family-agency-tags-PROPOSED.json` — 7 families, one line of
reasoning each. **RNR-H35 = ATTRIBUTE is ratified; the other six are proposals and are NOT in force**,
so the verifier receives no class for them and the AGENCY line fails closed. Proposed: H34 ACTION,
H21 ACTION, H26 ACTION, H27 ACTION, H06 ATTRIBUTE, H38 ATTRIBUTE.

### Verdict

`PROMPT_VERSIONS["verifier"]` is still **gate6-v1.3**. gate6-v1.4 exists, is tested, and is selectable
for replays. The locator name gate6-v1.4 reserved for the inference line is released; that line becomes
**gate6-v1.5**, to be measured against v1.4 once v1.4 passes.

---

## 6. Task 5 — the tp-4 fixture

Rebuilt with `truepos build --run-id tp-4`. **tp-1 was not hand-edited.**

- 60 items, 19 excluded — identical item set to tp-1.
- By branch: Roman Catholic 13, Reformed / Presbyterian 13, Anglican 9, Methodist / Wesleyan 8,
  Baptist 7, Mennonite / Anabaptist 4, Lutheran 3, **Eastern Orthodox 3** (TP-046, TP-059, TP-060) —
  **3, not 4**, as the session-6 review corrected.
- By raw tier: CONFESSIONAL 50, CATECHETICAL 7, CONCILIAR 3.
- **By effective tier: CONFESSIONAL 44, CONCILIAR 9, CATECHETICAL 4, OFFICIAL_EXPOSITION 3.**
- **TP-060 reads BSR-EO-01** (its URL maps there and its phrase is verbatim only in EO-01's store) and
  resolves `OFFICIAL_EXPOSITION (catechism, not synodally adopted)` — down from CONCILIAR at HEAD.
- **TP-042 to TP-045**: BSR-RC-01, CATECHETICAL → CATECHETICAL. No Chalcedonian definition text is
  registered in the Catholic branch.
- **The new fixture check passes.** `tier_inflation_check` fails the build when an item resolves above
  its host row with no registered creed or definition phrase behind it and no allowed chunk-level creed
  row — the TP-060 class. Six items resolve above their host (TP-018, 019, 023, 028, 030, 033), every
  one on a warrant: five on RC-06's own Nicene Creed text, one (TP-023) on RC-04 Constitution 1.

---

## 7. Task 6 — the ladder and NO TEXT

`packets.no_text_rows` now returns `(no_text, not_consulted)` and takes `ladder_entered`.

- A row not consulted **because of its ladder tier** is recorded `NOT CONSULTED (ladder tier X)` and
  does **not** block REVIEWED.
- **Tier C rows are excluded from the REVIEWED test** altogether.
- A **Tier B row that was due** — the card is empty after Tier A, so the ladder entered Tier B — and was
  not consulted **still blocks REVIEWED**, as NO TEXT. BSR-EO-01 is Tier B (R6-5) and is in on that footing.

The ladder is data: `config.EO_CONSULTATION_LADDER`, read through `packets.ladder_tier`, which takes a
row's own `eo_ladder_tier` first (workbook, else the R6-5 override) and falls back to the config ladder
for the rows no ruling names. **Flagging this:** the ladder itself had no machine-readable home — it
existed only as prose in the EO launch prompt — and Task 6's rule is untestable without one. I sourced
it from that prompt (author-ruled 13 September) with R6-5's amendment applied. Tier A 5 rows / 85,186
characters; Tier B 6 rows / 524,415; Tier C 2 rows / 11,690.

**Tests, all passing:**

| test | result |
|---|---|
| Tier-A-only **filled** card | `no_text == []`; the six Tier B rows and the two Tier C rows are NOT CONSULTED |
| A+B **empty** card, all read whole | REVIEWED **offered**; EO-11 and EO-13 carried as `NOT CONSULTED (ladder tier C)` and absent from `review_incomplete` |
| A+B empty card with **BSR-EO-01** missing | REVIEWED **refused**, `review_incomplete == ["BSR-EO-01"]`, and `why_not_offered` names it |

---

## 8. Task 7 — the EO prompt

Written to `wop-scratch/WoP_SJN_Gate6_EOPrompt_20260916.txt`, superseding the 13 September prompt.
Changes marked `[S7]`. **Marked NOT LAUNCHABLE at the top**, with the v1.4 failure stated in the banner.

- Tier A loses BSR-EO-01 → 5 rows / 85.2k characters (≈5.4 USD locator, down from 8.8); Tier B gains it
  → 6 rows / 524.4k, of which EO-01 alone is 158.9k (30%), entered only on cells that need it.
- The verifier line names **gate6-v1.4** (R6-11), not v1.2.
- **Launch blockers** as preconditions: (a) the agency tags are not ratified — R6-8 blocks EO by name;
  (b) the OCA Creed-as-prayer row — **discharged**, the trigger did not fire; (c) the stray files —
  **discharged**; (d) the verifier — **open**.
- Added: EO-01 and EO-02 are one observation; Hopko resolves OFFICIAL_EXPOSITION with "not officially
  adopted"; Philaret keeps CATECHETICAL with "approved by the Most Holy Governing Synod of the Russian
  Church (one church)"; Q-274 is ATTRIBUTE, the collective "one God … is X" form does not satisfy it,
  and **an empty Q-274 is an honest empty** (clause 4).
- **3c: stratified** — six cells from families H01–H35 and four from H36–H57, each group in queue order,
  and the report must say the draw was stratified.
- The IDIOM expectation restated: Mennonite is **7 flagged candidates in 5 cells** at HEAD, not 10.
- 1b replaced with the Task 6 rule in full.
- **Q-290 (R6-12)**: at the EO packet review, list any independent witness for Unbegotten found in
  Tier A or B, or state that none was found. The fallback is the author's.

---

## 9. Task 8 — housekeeping. **All four removed, and two loaders did glob them.**

The glob check, before removal:

- `store.load_all_chunks()` lists `CHUNK_DIR` and reads **every** `*.json`, so
  `BSR-AN-03 (1).json` **was** read. Its chunks carry `registry_id: BSR-AN-03` internally, and its text
  hash **differs** from the live `BSR-AN-03.json` — a stale earlier fetch. Its only consumer is
  `sources.Ctx.corpus_vocab`, which skips chunks whose `registry_id` equals the row being repaired, so
  the effect was confined to contributing a stale row's vocabulary to *other* rows' de-hyphenation
  decisions. Small, but real, and unauditable.
- `CellRunner.sample_quota()` lists `state_dir` and reads **every** `*.json` whose `branch` matches, so
  `Q-112 (1).json`, `Q-331 (1).json` and `Q-340 (1).json` **would** be double-counted toward the 2c
  caveat-sample quota on any run whose state dir is `recovery-runs/cal-2/cells`. All three differ byte
  for byte from their originals; none carries a `caveat_sample` record, so nothing was miscounted yet.
- `CellRunner.load(qid)` opens `<qid>.json` by exact name, so no duplicate was ever loaded as a cell.

Removed: `.cache/sjn-recovery/chunks/BSR-AN-03 (1).json`,
`recovery-runs/cal-2/cells/{Q-112,Q-331,Q-340} (1).json`.

---

## 10. Task 9 — Q-290 (R6-12)

Recorded in the rulings file: **PUBLIC-CERTIFIED**, flagged **REVIEW_AT_EO_PACKET**, disclosure text
exactly `"single source: Hopko, OCA Department of Religious Education; not synodally adopted."`,
fallback decision **OPEN** (author, at the EO packet review). Queued for the next workbook version.
**The public app was not changed.**

Independent confirmation of the ground: tp-4 refuses **both** Q-290 citations under v1.4 — TP-059
(EO-02, "There is only one God because there is only one Father", BELOW_FLOOR) and TP-060 (EO-01, "God
is an eternal Father by nature", BELOW_FLOOR). tp-3 refused both under v1.3 too. So the cell's two
citations are one observation *and* neither survives the current verifier. That is worth reading before
the EO packet.

---

## 11. Spend

| run | calls | USD |
|---|---:|---:|
| tp-4 (v1.4, 60 items) | 60 | 1.0697 |
| s7-v14 (16 candidates + retries) | 18 | 0.6370 |
| s7-v13-control (same 16) | 16 | 0.4398 |
| s7-rep-v1.3-1..3 / s7-rep-v1.4-1..3 (TP-049, TP-050 replicates) | 13 | 0.3606 |
| **total** | **107** | **2.5070** |

Against the 10 USD cap and the 6 USD report threshold. The 2–3 USD expectation held.

---

## 12. What I think is wrong, with the artifact

1. **"the 13 non-creedal IDIOM rejections" is 12.** 14 flagged at HEAD = 1 on a card (Q-297) + 13
   rejections, of which Q-161 is the creedal one. Artifact:
   `recovery-runs/session7/idiom-candidates-at-head.json`.
2. **The Q-277 diagnosis was wrong.** Both candidates agree under the v1.3 control as well as under
   v1.4, so the AN-03/AN-04 split was model variance, not a rule gap. R6-7's JOINT PREDICATION line was
   written on that evidence and is now the thing costing recall. Artifact:
   `recovery-runs/session7/measure-results-s7-v13-control.json`.
3. **JOINT PREDICATION is scoped by its opening clause and nothing else.** It says "When the required
   subject is THE HOLY SPIRIT", and the model still applies its reasoning to a Son family, 3 times out
   of 3. A prompt line cannot scope itself; the harness has to withhold it. Artifact:
   `recovery-runs/session7/replicate-tp049-tp050.json`.
4. **The creed carve-out leaks past creeds.** Q-160, a doxology with no creedal content, flips to accept
   under v1.4 and not under v1.3, even though line 4 still lists doxologies. The carve-out appears to
   weaken *fixed formula* in general.
5. **The adoption field's fail-closed rule needed a boundary that no ruling supplies.** As written it
   would demote the Westminster Larger Catechism below the Shorter. I bounded it to CATECHETICAL rows
   on the session-6 review's own statement of clause 3's reach, and flagged RP-03 and RP-05 as
   proposals. That boundary is a judgement and should be ratified or overruled, not inherited.
6. **The EO consultation ladder had no machine-readable home.** Task 6's rule cannot work without one.
   I put it in `config.EO_CONSULTATION_LADDER`, sourced from the EO launch prompt. It belongs in the
   registry as an `eo_ladder_tier` column; the reader already prefers the row's own value.
   *[RATIFIED R6-23, 16 Sep — the ladder stays in config; recorded session 9.]*
7. **The Anglican branch registers the Athanasian Creed as a text but not the Apostles' or Nicene.**
   So an Apostles'-Creed phrase quoted from AN-04 or AN-05 cannot resolve CONCILIAR there. A registry
   gap surfaced by the new rule, not caused by it.
8. **The phrase floor (3 words / 12 characters) is mine.** The author's examples set the lower bound;
   nothing in the rulings sets it. It is stated in the code and in §3 above so it can be overruled.
   *[RATIFIED R6-21, 16 Sep — recorded session 9.]*
