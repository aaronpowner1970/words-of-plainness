# SJN Gate 6, session 11 — adoption ratification: written, guarded, rebuilt once (17 September 2026)

**Rulings R6-35 to R6-40 are written, the BSR-LU-03 apparatus guard is built and tested, and the seven finished packets were
rebuilt ONCE. No stop condition held.**

- **Model calls: 0. Spend: 0.00 USD.** The rebuild ran with every model call and network request refused in-process
  (`session11/rebuild_once.py`); 0 attempts were recorded.
- **Not changed:** the workbook, the codex, verifier and locator versions, the tp fixtures, `src/_data/sjn` (app data),
  the live-1 cell states (byte-identical after re-finalisation) and `operational-state.yaml`.
- **Not fetched, not re-chunked:** the stored corpus is unchanged.
- **Tests: 147 passed.**
  - The 135 existing tests pass. Two session 7 tests were rewritten because today's rulings removed their premise (see §6).
  - 12 tests are new.

Every finding in §2 comes from one instrument: local reads of workbook v2.25r4, the chunk store
(`.cache/sjn-recovery/chunks`), the fetch cache and the packets. Nothing was checked against the web in this session.

---

## 1. Files and cells written

| file | what |
|---|---|
| `recovery-runs/author-rulings-pending-workbook.json` | Adds 8 rows to `R6-6_adoption_field.rows`, verbatim (RC-07, AN-02, AN-04, AN-05, LU-03, RP-03, RP-05, BA-03). Amends RP-02 and LU-01 in place, keeping the prior values under `amended.was`. Adds six rulings: `R6-35_an02_adoption`, `R6-36_an05_adoption`, `R6-37_lu03_adoption`, `R6-38_adoption_scope_reach`, `R6-39_ba03_issued_unadopted`, `R6-40_rc07_an04_rp05_adoption`. Marks `R6-16_adoption.discharged`. EO-01, EO-02, EO-04 and RC-01 are asserted unchanged. |
| `recovery-runs/session11/ratified-block-20260917.json` | The ratified block exactly as given, for provenance. |
| `scripts/sjn_recovery/rulings.py` | `adoption_guards()`, which reads and validates each ruling's `guard`. `OVERRIDABLE` gains `canonical_url` and `draft_recommendation` (for goals 3a, 3e and 3f). The summary now reports the guards. |
| `scripts/sjn_recovery/registry.py` | `apparatus_guard(rid, chunk)`. `exposition_tier(rid, tier, chunk)` sends a guarded chunk to OFFICIAL_EXPOSITION and never raises a tier. `adoption_disclosure(rid, chunk)` adds translation_disclosure, disclosure_wording and the apparatus disclosure. `effective_tier` / `tier_resolution` pass the chunk through, and the reason reads "the apparatus guard (R6-37)". |
| `scripts/sjn_recovery/packets.py` | Each card entry gains `apparatus_guard`, and `adoption.adopting_body`. |
| `scripts/sjn_recovery/sources.py` | The Heidelberg chunker accepts "Q & A 80*" (goal 3c). |
| `scripts/sjn_recovery/tests/test_session11_rulings.py` | 12 new tests. |
| `scripts/sjn_recovery/tests/test_session7_rulings.py` | Two tests rewritten (§6). |
| `recovery-packets/*.json`, `recovery-packets/extracts/*` | The seven packets, rebuilt. |
| `recovery-runs/live-1/run.json` | `packets_rebuilt` note for the seven branches. |
| `recovery-runs/live-1/rebuild-diff-20260917.{json,md}` | The rebuild diff. |
| `recovery-runs/session11/` | Scripts: `rebuild_once.py`, `rebuild_diff_s11.py`, `verify_findings.py`. Output: `verify-findings-after-rebuild.txt`. This report. |

**Goal 1c — the loader path: no .xlsx was written.**
- The pipeline does not read adoption from the workbook today. `Registry._migrate_adoption` reads the four adoption columns
  from the workbook only where a row already carries them, and **no row does**. Otherwise it takes the value from
  `rulings.adoption_rows()`, i.e. this JSON file (source `AUTHOR_RULING_R6-6`).
- That is the existing path by which R6-6 rows reach the loader, so the JSON write is the write.
- The rulings' `supersede_with` still names the registry's adoption columns. When Cowork writes them, the harness reads
  them and fails loudly on any disagreement.
- The xlsx round-trip diff is therefore not applicable.

**The registry corrections (goals 3a, 3e, 3f) are in-memory overrides too:**
- They use the existing R6-5 override hook, pending the workbook. The workbook is not written from Code.
- Each override records the workbook value beside the ruled value (`reg.registry_overrides`).

**Card disclosures (goal 1d), as rendered:**
- **ONE_CHURCH rows** read "approved by ⟨body⟩ (one church)".
- **RP-05** reads "approved by Synod of the Christian Reformed Church in North America; General Synod of the Reformed Church
  in America (several churches); English translation: CRC/RCA joint translation, 2011".
- **LU-03** appends "; English translation: Concordia Publishing House (c) 2019".
- **BA-03** reads exactly "Descriptive denominational statement; American Baptist Churches USA does not adopt binding
  creeds".
- **RC-07 and RC-01** (WHOLE_BRANCH, no translation note) carry no disclosure, as before.
- **No packet or extract contains "adoption unverified".**
- **Wording is kept verbatim**, including "(c)". The author may prefer "©", or "and" between RP-05's two bodies.

---

## 2. Verified findings 3a–3h

### 3a — BSR-RC-07 canonical_url: CONFIRMED
- The workbook value is the host note `vatican.va (as cited, 1 released cell)`.
- All 533 stored chunks share one source_url:
  `https://www.vatican.va/archive/compendium_ccc/documents/archive_2005_compendium-ccc_en.html`. That is also the URL
  `sources.compendium` hard-codes.
- That URL is now set in memory (R6-40 override), so the fetcher is not affected.

### 3b — RC-07 Part Four: PARTLY CONTRADICTED
- **The Part Four text is in the store; the Part Four questions are not.**
  - There are no chunks for Q.534–598.
  - The Part Four answers, and then the Appendix lists (precepts, works of mercy, capital sins, last things), were appended
    to the **"Compendium Q.533" chunk** (49,667 characters).
- **Cause (fetch cache, read only):** in Part Four the page sets the number and the question in separate bold tags
  (`<b>534.</b><b>What is prayer?</b>`). The chunker matches `^(\d+)\.\s+(.+)$` inside one tag, so no heading after 533 is
  recognised.
- **Card impact:** three RC-07 candidates are located at "Compendium Q.533" with Part Four phrases:
  - Q-153 "draw us toward him for his glory" (not slotted);
  - Q-313 "Father, whose majesty is boundless" (not slotted);
  - Q-313 "God transcends everything" (cut at tier allocation).
  - **None is on a card, before or after the rebuild**, but each locator is wrong.
- Not fetched and not fixed (outside 3c's permission). **QA track.**

### 3c — RP-05 Q&A 80: CONFIRMED, cause diagnosed, chunker FIXED
- The store has 128 Q&A, and Q&A 80 is missing.
- **Cause:** crcna.org heads that entry "Q & A 80*" (the asterisk marks its edition footnote). The regex `^Q & A (\d{1,3})$`
  required an exact number, so the heading was skipped.
- **Effect:** Q&A 80's question and answer, **and the CRC's two editorial footnotes** (on the editions, and on Synods
  2004/2006 bracketing its last paragraphs), ran on inside the "Q&A 79" chunk.
- **Fix:** `\*{0,2}` is allowed after the number. The test `test_the_heidelberg_chunker_keeps_an_asterisked_heading`
  checks it.
- The stored corpus was **not** re-chunked. No packet entry cites RP-05 "Q&A 79".
- When the row is re-chunked, the footnotes will sit in the Q&A 80 chunk (see §3, guard candidates).

### 3d — AN-05 locators: CONFIRMED
- "Q.1" and "Q.2" are the front-matter drafting principles.
- The "Q.3" chunk holds:
  - the third principle;
  - the Committee's sign-off (Packer);
  - the note on Scripture references and a collect;
  - the Part I introduction and "The Gospel";
  - the two prayers;
  - then the real Q.1–3 ("What is the human condition?", "What is the Gospel?", "How does sin affect you?").
- **Cause:** the numbered principles 1–3 consumed the chunker's expected numbers. From "Q.4 — What is the way of death?"
  on, the labels follow the printed numbers.
- **Cards that cite an AN-05 chunk labelled Q.1, Q.2 or Q.3: none**, in all seven packets (candidates, rejections,
  witness-only, parallel witnesses), before or after the rebuild. None in the extracts either.
- `src/_data/sjn/*.json` mentions "To Be a Christian" once, in the `branches.json` registry block. No locator is cited.
- Workbook: no Evidence-First Cell Queue row cites AN-05.
- **Locators not corrected.** The locator is the chunk id (`store.chunk_id = rid::locator`) and the packet lookup key. No
  card needs a correction, so they are left as they are. **QA track.**

### 3e — BSR-LU-03 note: CONFIRMED and corrected in memory
- The workbook says "INCLUDE WITH CAVEAT (2017 explanation edition; official status implied by lcms.org link)".
- The one stored chunk is Luther's text: the Creed's First Article, "What does this mean?", and Luther's answer ending
  "This is most certainly true."
- It carries no CPH Explanation matter. Its division label "explanation article" names Luther's own explanation.
- The note now reads: "INCLUDE WITH CAVEAT (Luther's Small Catechism text in the Concordia Publishing House translation
  (c) 2019, not the 2017 Explanation; adopted by the LCMS through Constitution Art. II, R6-37)".

### 3f — BA-03 and CURRENT_OFFICIAL_WITNESS: CONFIRMED
- **Yes, it is a defined tier value:**
  - fifth and lowest in APP CONFIG `authority_tier_rank` (`CONCILIAR|CONFESSIONAL|CATECHETICAL|OFFICIAL_EXPOSITION|CURRENT_OFFICIAL_WITNESS`);
  - in `registry.TIER_RANK_DEFAULT`;
  - in `scripts/sjn/sjn_merge_decisions.py`.
- **No registry row carries it.** BA-03's authority_tier is OFFICIAL_EXPOSITION, unchanged.
- The note now reads: "INCLUDE WITH CAVEAT as OFFICIAL_EXPOSITION; ISSUED_UNADOPTED (R6-39): a descriptive denominational
  statement, and American Baptist Churches USA does not adopt binding creeds".

### 3g — same text, LU-01 vs LU-03: CONTRADICTS the premise
- **No LU-01 chunk is identical to the LU-03 chunk**, and none of LU-03's ten sentences stands verbatim in any LU-01 chunk.
  The one "containment" hit is a 12-character Smalcald fragment.
- **The reason is a corpus defect:**
  - LU-01's Small Catechism chunks on bookofconcord.org are almost empty. "II. The Creed, ¶1–3" is 30 characters
    (". –Answer: . –Answer: –Answer:").
  - The Lord's Prayer, Baptism and Sacrament of the Altar chunks are 44–107 characters of "–Answer:" markers.
  - The question and answer text was lost at extraction.
- **The same-text guard therefore has nothing to record:** no LU-03 card entry has an LU-01 parallel witness, before or
  after.
- **QA track:** re-extract LU-01's Small Catechism.

### 3h — Q-085, Q-133, Q-405: no Anglican source other than AN-05 carries any of them

| cell | before (session 6 packet) | after the rebuild |
|---|---|---|
| Q-085 Just / righteous | card: AN-05 Q.173, AN-05 Q.37 (CATECHETICAL); AN-05 Q.106 rejected by verifier | same seats, CATECHETICAL; disclosure "approved by College of Bishops of the Anglican Church in North America (one church)" |
| Q-133 Long-suffering | card: AN-05 Q.77 (CATECHETICAL) | same, with the disclosure |
| Q-405 No adequate likeness | card: AN-05 Q.173, Q.169 (CATECHETICAL); **AN-04** Outline p. 862 rejected by verifier at CATECHETICAL | AN-05 same, with the disclosure; AN-04's rejected candidate now **CONFESSIONAL** (its phrase is verbatim in the AN-03 Athanasian Creed, R6-10). Still rejected |

- Before today's ratification, all three cards rested on AN-05 alone.
- AN-05 is also the Anglican fallback-only row. Under the rules in force it would have sat at OFFICIAL_EXPOSITION.

### LU-01 (goal 1b): a named adopting act IS on record; written with its reach

**Stored text:**
- Host: bookofconcord.org, a private site (not a church). 738 chunks from 132 URLs.
- Text: the public-domain 1921 Concordia Triglotta translation (registry note).

**Church on record:**
- All 12 Evidence-First Cell Queue rows whose Text URL is on bookofconcord.org name "Lutheran Church—Missouri Synod".
- Eight of them give Authority / adoption URL `https://www.lcms.org/about/beliefs/lutheran-confessions` and the note
  "LCMS confessional subscription; not all Lutherans".

**Written:** `ONE_CHURCH`, "The Lutheran Church-Missouri Synod". The ratified `PENDING_VERIFICATION` values and the
evidence are kept under `amended.completed_by_verification`. adoption_act is unchanged.

Ranked candidates:

1. **LCMS Constitution Art. II** (on record under R6-37: accepts the Book of Concord's symbolical books without
   reservation). **Chosen.** It is a church body's act, and it adopts LU-01's own book.
   - *Weakness:* one publisher (a district-hosted Handbook copy).
   - *Weakness:* its reach is the LCMS only, narrower than the row's speaks_for.
2. **The workbook's lcms.org adoption URL** on the Lutheran queue rows.
   - *Weakness:* a URL, not a named act.
   - *Weakness:* not opened in this session.
   - *Weakness:* the same publisher family as candidate 1.
3. **BSR-LU-04, ELCA teaching pages** ("adoption witness only").
   - *Weakness:* a RETIRED row; no act named; never verified.
4. **None:** leave the body pending and put LU-01 on the QA track.
   - *Weakness:* ignores a verified act on record.

**RP-02 check:** confirmed against the registry. Row 24: "Westminster Shorter Catechism — OPC", publisher_domain opc.org,
https://opc.org/sc.html. The entry's own act string names the OPC.

---

## 3. The LU-03 guard (goal 2)

**How it works:**
- A ruling's `guard` object (`registry_id`, `kind: PUBLISHER_APPARATUS`, `resolves_to: OFFICIAL_EXPOSITION`) is read by
  `rulings.adoption_guards()` and applied by `Registry.apparatus_guard(rid, chunk)` to any row that carries one.
- Two tests are applied to the whitespace-normalised chunk; either is enough:
  - **an apparatus marker** in the text, locator or division ("The Central Thought");
  - **fail-closed:** the chunk is not **wholly** the integral text:
    `^I believe in [^?]*?\. What does this mean\? .*?This is most certainly true\.$`.
- A guarded chunk resolves to "OFFICIAL_EXPOSITION (publisher matter, not the adopted text)" and discloses "publisher-added
  matter: it does not inherit the adoption of the text it accompanies".
- It never raises a tier.
- A verbatim creed phrase still resolves by R6-10, since that rule is about the phrase, not the host.

**Results:**
- **Stored LU-03 chunks that trip it: 0 of 1.** The one chunk resolves CATECHETICAL.
- **Tests:**
  - `test_an_lu03_apparatus_chunk_never_resolves_catechetical` covers three chunk shapes × two apparatus texts × four
    phrases. It fails if any resolves CATECHETICAL.
  - Also: generic application, malformed-guard refusal, and the unguarded-row no-op.

**Guard candidates on other rows (reported, NOT applied):**

| row | what | effect if guarded |
|---|---|---|
| BSR-RP-05 | CRC editorial footnotes inside "Q&A 79" (will move to Q&A 80 on re-chunk) | none on tier (CONFESSIONAL is never demoted below its own rank by adoption; the guard would send the footnote chunk to OFFICIAL_EXPOSITION); disclosure only |
| BSR-AN-05 | "Q.1"–"Q.3" chunks: drafting principles, the Committee's sign-off, the introduction | CATECHETICAL → OFFICIAL_EXPOSITION for citations from those chunks; no card cites them |
| BSR-AN-04 | the PDF's Standard Book certificate and other front matter (not audited this session) | unknown until audited |
| BSR-RC-07 | "Q.533" carries the Appendix lists | probably none: the Compendium's appendices are part of the promulgated book (B2(b) integral), so they are not publisher matter; the wrong locator is the defect |

---

## 4. The seven packets

Read from `live-1/run.json` `branches`, each DONE in `live-1/cost-state.json`: Roman Catholic, Lutheran, Reformed /
Presbyterian, Baptist, Methodist / Wesleyan, Anglican, Mennonite / Anabaptist. Eastern Orthodox did not run and was not
touched.

## 5. Rebuild diff summary (`live-1/rebuild-diff-20260917.md`)

**Base:** the committed packets, which are the **session 6** build (13 Sep). Sessions 7–9 never rebuilt a packet, so this
diff carries their resolution rules for the first time beside today's rulings.

**The prompt's expected effects, against the right baseline.**
- The committed packets never showed OFFICIAL_EXPOSITION, because R6-9 was not yet in them. So against HEAD, RC-07,
  AN-02, AN-04, AN-05 and LU-03 show **no** tier move: CATECHETICAL → CATECHETICAL.
- A sandbox rebuild under the rules in force *before* today's rulings (same stored states, 0 calls) shows the moves the
  prompt describes. Today's rulings return all of them to CATECHETICAL:

| row | OFFICIAL_EXPOSITION → CATECHETICAL |
|---|---:|
| BSR-RC-07 | 50 |
| BSR-AN-04 | 29 |
| BSR-AN-02 | 18 |
| BSR-LU-03 | 10 |
| BSR-AN-05 | 7 |

- In that sandbox, RC-07's demotion also reordered 10 RC-07/RC-04/RC-02 seats. Those reorders are gone after
  ratification: no RC-07 seat moves against HEAD.
- Guarded LU-03 apparatus chunks: none exist, so there are no exceptions.

**Against HEAD, by row and move:**

| change | row | count | cause |
|---|---|---:|---|
| disclosure added | BSR-LU-01 | 78 | R6-38 (ONE_CHURCH, LCMS) |
| disclosure added | BSR-AN-04 | 40 | R6-40 |
| disclosure added | BSR-AN-02 | 19 | R6-35 |
| disclosure added | BSR-RP-03 | 19 | R6-38 |
| disclosure added | BSR-RP-05 | 16 | R6-40 (body, reach, translation) |
| disclosure added | BSR-RP-02 | 12 | R6-38 (amended) |
| disclosure added | BSR-LU-03 | 11 | R6-37 (body, reach, translation) |
| disclosure added | BSR-AN-05 | 7 | R6-36 |
| disclosure added | BSR-BA-03 | 1 | R6-39 (its own wording) |
| tier CATECHETICAL → CONFESSIONAL | BSR-AN-04 | 11 | R6-5/R6-10: phrase verbatim in BSR-AN-03's Athanasian Creed (7 on cards, 4 verifier rejections) |
| tier CATECHETICAL → CONFESSIONAL | BSR-AN-02 | 1 | R6-10: Q-205 "he shall come to judge the quick and the dead" (AN-03) |
| tier CATECHETICAL → CONFESSIONAL | BSR-LU-03 | 1 | R6-10: Q-195 "God, the Father Almighty, Maker of heaven and earth" (LU-01 Apostles' Creed) |
| tier CATECHETICAL → CONCILIAR | BSR-RC-01 | 1 | R6-10: Q-297 "begotten not made, consubstantial with the Father" (RC-08 Nicene) |

**Why disclosures appear beyond the prompt's list.** The prompt expected disclosure-only changes on RP-02, RP-03, RP-05,
LU-01 and BA-03. AN-02, AN-04, AN-05 and LU-03 also gain one because goal 1d requires every ONE_CHURCH row to state its body
and reach.

**Seat and lead changes, all from the R6-10 tier moves above and the existing allocator.** The allocator fills the cap
round-robin across tier queues, with the speaks_for group rule inside a tier.
- **Q-195 (Lutheran):** LU-03-1 (now CONFESSIONAL) and LU-03-2 (CATECHETICAL) swap seats.
  - The CONFESSIONAL queue's third place goes behind the 'lcms' group already seated, so the CATECHETICAL queue's first
    takes the slot.
  - **For the author's review:** a lower-tier sentence of the same body is seated over a higher-resolving one.
- **Q-205 (Anglican):** AN-02-1 (now CONFESSIONAL) takes the Church of England CONFESSIONAL slot that AN-03-1 held. AN-03-1
  is cut, and AN-04-1 (the Episcopal Church) gains a seat.
  - **For the author's review:** a catechism's quotation of the Athanasian Creed displaces the creed text itself.
  - This moves Anglican's header `candidates_lower_floor_applied` from 5 to 4 (AN-03-1 carried the lower floor).
- **Q-317 lead:** AN-03 → AN-04. Both CONFESSIONAL, both FULL; registry order puts AN-04's printing of the Creed first.
- **Q-297 lead:** RC-04 → RC-01. Both CONCILIAR; registry order.

**Unchanged:**
- **No cell changed state.** No candidate was dropped from or added to a card except the two swaps.
- **No verdict changed.** Re-finalisation is idempotent; the cell files are byte-identical.
- Methodist/Wesleyan and Mennonite/Anabaptist: no tier or disclosure change.

**Schema-only additions** (sessions 7–9, first build since): `effective_tier_at_run`, `ladder_entered`,
`not_consulted_by_ladder`, `empty_result_option.not_consulted_by_ladder`, `apparatus_guard`, `adoption.adopting_body`.
Plus the header's `author_rulings_applied` and `rebuilt_from`.

## 6. Tests

**147 passed** (was 135).
- **New:** `test_session11_rulings.py`, 12 tests.
- **Rewritten:** in `test_session7_rulings.py`,
  `test_an_unverified_catechetical_row_fails_closed_and_says_adoption_unverified` and
  `test_a_confessional_row_is_never_demoted_by_an_unverified_adoption`.
  - Their premise, a real UNVERIFIED row (RP-03 and RP-05), no longer exists: R6-38/R6-40 adopted them, and **no row in the
    registry is UNVERIFIED now**.
  - Both now apply the migration's own UNVERIFIED record to real rows. The fail-closed rule stays tested rather than being
    skipped.

## 7. Stop conditions (none held)

- **No PUBLIC-CERTIFIED cell is in any packet** (Gate 6 runs only open cells). The rebuild touched no workbook cell and no
  app data.
- **No card cites AN-05 "Q.1"–"Q.2"** anywhere.
- **0 model calls and 0 network requests** were attempted.
- **No .xlsx was written.**
- **The contradictions (3b, 3g, and the tier-move baseline) change no value to be written:**
  - RC-07's adoption is unaffected by where Part Four sits.
  - The same-text premise concerned only a guard record, and there was nothing to record.

## 8. Open QA-track items

1. **ACNA canons in force in 2017–18:** do they assign catechism or authorized-text approval elsewhere? (R6-36; if so,
   AN-05 reverts to UNVERIFIED.)
2. **BSR-RC-07 Part Four:** chunker defect (split bold tags). Q.534–598 and the Appendix sit in "Q.533", and three stored
   candidates carry that wrong locator. Needs a chunker fix and a re-chunk.
3. **BSR-RP-05 Q&A 80:** chunker fixed. Needs a re-chunk; the CRC footnotes then need a guard decision.
4. **BSR-AN-05 "Q.1"–"Q.3" locators:** uncorrected, because the locator is the chunk id. Needs a chunker fix (principles vs
   questions) and a re-chunk. No card affected.
5. **BSR-BA-03:** propose the 1998 ABCUSA Identity Statement as a NEW row after Cowork verification (R6-39). BA-03 is not
   re-pointed.
6. **BSR-LU-01:** the Small Catechism chunks are near-empty (text lost at extraction). Needs re-extraction.
   - A second publisher for LCMS Const. Art. II would strengthen the LU-01 and LU-03 body.
7. **Workbook:** carry the four adoption columns (14 rows ruled), RC-07 canonical_url and the LU-03 and BA-03 notes. Until
   then they apply in memory from the rulings file.
8. **For the author:** the Q-195 / Q-205 / Q-317 seat outcomes in §5 (a catechism quotation of a creed seated over, or
   leading, the creed text or a higher-resolving sentence).
