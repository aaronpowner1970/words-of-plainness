# SJN Gate 6, session 13: section registration, confessed catechisms, corpus repair resumed, new Baptist row (17 September 2026)

**Phases 1–5 are done, tested, committed and pushed. Phase 6 is done: both estimates are well under 80 percent of their caps.
STOPPED before phase 7 on a stop condition. No model call was made.**

- **Model calls: 0. Spend: 0.00 USD.**
- **Network:** one page fetched, the BSR-BA-04 page (HTTP 200, no redirect). The phase 4 re-chunk used only the fetch cache: 327 files before and after.
- **Commits (all pushed to main):**
  - 2ec5030 phase 1
  - 89119db phase 2
  - 2bc36f1 phase 3
  - 4051d7d phase 4
  - ee22ea6 phase 5
  - the phase 6 estimate and this report follow in one more commit
- **Tests:**

  | point | passed |
  |---|---|
  | start | 154 |
  | phase 1 | 155 |
  | phase 2 | 160 |
  | phase 3 | 162 |
  | phase 4 (session 12's 7 held tests plus 3 new; one test skipped until the re-chunk) | 172 |
  | phase 5 | 175 |

- **Not changed:** the workbook, the codex, verifier versions, the fixtures, `src/_data/sjn`, the committed packets (no rebuild), the live-1 cell states and `operational-state.yaml`. Eastern Orthodox was not run.
- **Instruments:**
  - workbook v2.25r4 (read);
  - the chunk store and fetch cache;
  - the rulings file;
  - Codex v0.6 (the author had already applied it; its B1(a), B1(b) and Part E entries match the prompt);
  - sandbox packet builds with every model call and network request refused (`session12/sandbox_build.py`);
  - one live fetch, for BA-04.
- **Repo check at start:**
  - HEAD eac28f9. The tree was clean except the unrelated untracked `tools/reports/chat_screens/Claude outputs/`.
  - No repo file had changed since the session 12 commit (mtime search).
  - The `claude` processes listed were the desktop app's own.
  - A sandbox build of the unchanged tree reproduced session 12's `phase2-seat-effects.json` exactly. That build (`sb-base`) is the baseline for every phase diff below.

---

## 1. The stop (before phase 7)

**Condition:** "A verification contradicts this prompt in a way that changes what should be written."

**What the prompt assumes.** Phase 7 runs "with production majority voting per Codex C1", and sends doubtful accepts "to the author review queue (Codex C3)", from which nothing may reach app data.

**What the files show.**
- **Scope searched:** all 45 modules of `scripts/sjn_recovery` and `scripts/sjn_pipeline`, for majority, voting, vote, replicate, review queue, publication hold, hold list and author_review.
- **Voting:** there is none in production. Replicates exist only in measurement tools (`partial_rule.py` controls; the session 7–9 replicate scripts). `agents.finalize` reads one rubric per model.
- **Review queue:** there is no Gate 6 author review queue or publication hold list. The only `author_review` hit is the workbook comparator field that `sjn_pipeline/emit.py` passes to app data, which is not a queue with a publication bar.
- **R6-31:** its text is not in the repo. The Codex cites it only as "production voting on gate6-v1.3".

**Why this changes what should be written.** Running phase 7 means building voting and a queue first. Both involve decisions the rulings do not make:
- what the majority is taken over (verdict class, floor, or both);
- how it combines with the lower-floor rule (2a) and the opus routes;
- which rubric is stored;
- what "doubt" means for C3 (a split vote, a caveat, a PARTIAL floor);
- where the queue lives and how it blocks a rebuild from reaching app data.

**A second point for the same decision.** The 20 Track R verdicts were given by gate6-v1.1 (Anglican) and v1.2 (Roman Catholic) single calls. Track R replaces them with v1.3 majority reads, so the cards would mix instruments.

**Ranked options for the author:**
1. **Rule the voting and queue shapes, then run phase 7 as written.**
   - Rule: majority over verdict class of 3 sonnet v1.3 calls; the floor is the lowest floor among the majority (keeping 2a); opus routes unchanged and voted the same way; "doubt" means any dissenting vote or ACCEPT_WITH_CAVEAT at PARTIAL; the queue is a committed file that the packet builder and `emit.py` both refuse.
   - *Weakness:* a new session builds and tests this before any call. The Anglican cards then carry v1.3 majority verdicts beside v1.1 single-call verdicts.
2. **Run Tracks R and B single-call under the existing harness, as every branch so far ran.** Record that as a C1 deviation.
   - *Weakness:* contrary to C1 as ratified. Doubtful accepts would have no queue, which is contrary to C3.
3. **Hold phase 7.**
   - Rebuild nothing. The packets stay at eac28f9 until voting, the queue, and the AN-04 Historical Documents row (R6-45) exist.
   - *Weakness:* the 19 AN-04 and 1 RC-07 relocations, the LU-03 tier move and BA-04 stay unverified and off the cards.
   - *Weakness:* until BA-04 is consulted, the 7 empty Baptist cards cannot be offered "CURRENT STANDARD REVIEWED" (§6.4).

---

## 2. Phase 1: rulings written

`author-rulings-pending-workbook.json`, written by `session13/write_rulings.py`, which is idempotent: a second run leaves the file unchanged.

Each phase then recorded its own implementation through `session13/record_phase.py <phase>`: operative blocks, `as_implemented` and `test`.

| key | recorded | operative block added by |
|---|---|---|
| `R6-43_registration_by_section` | rule, codex B1(a), the LU-01 rows named | phase 2: `registered_sections_file` |
| `R6-44_confessed_catechisms` | rule, codex B1(b), `rows_moved: [BSR-LU-03]`, `keeps` | phase 3: `registry_id` + `overrides {authority_tier: CONFESSIONAL}` + `overrides_why` |
| `R6-45_an04_historical_documents_scope` | rule, `awaits` | phase 4: `scope_marker` |
| `R6-46_session12_confirmations` | items 1–5, per-item `as_implemented` | phases 2, 4, 5 |

**Also updated:**
- **R6-36's guard:** its `why` and `reading` now describe the narrowed scope (R6-46.1), with a `narrowed` note.
- **R6-40's guard:** a `confirmed` note (R6-46.2).
- **R6-42:**
  - the confirmed `registry_id` and `branch` replace the placeholders; the placeholders are kept in `as_ratified_placeholders`;
  - a `confirmation` block and `add_row: true`;
  - `as_implemented` and `test`.

---

## 3. Phase 2: section registration (R6-43)

### 3.1 Implementation
- **The list.** `data-sources/sjn/recovery-runs/registered-sections.json` holds 62 sections: 29 creed and 33 definition. It also has a `not_registered` list of 13 entries, each with its reason. It is the only registration path.
  - `rulings.registered_sections()` reads it. A missing file is a hard stop.
  - `Registry._registered_sections` builds `registered_creed_texts` and `registered_definition_texts` from it.
- **The old row gates now fail loudly as checks on the list.** A listed creed must sit in a creed-carrying row, never CATECHETICAL. A listed definition must sit in a CONCILIAR row. No listed section may name a canon or anathema. Each listed section must exist in the store.
- **Chunk-level creed resolution** (R6-5's allowed rows) also requires a listed section, so there is one registration decision.
- **`text_through` (a judgment; see §3.3).** Where a stored chunk carries more than the creed, the registered key ends after a named string:
  - RP-04 1.3 runs on into the PC(USA) introduction to the Apostles' Creed ("Although not written by apostles … Marcion …");
  - RP-04 2.3 runs on into the introduction to the Scots Confession and "CHAPTER 1 God";
  - LU-01's Apostles' Creed ends with the host's footnote ("* catholic means 'universal' …");
  - AN-03's creed is followed by the Gloria Patri the BCP appoints after it.

### 3.2 Before and after
- **Before:** 75 registered chunks (`session13/registered-before.json`).
- **After:** 62 (`registered-after.json`).
- **Full table:** `session13/registration-before-after.md`.

**Left out (13):**

| row | sections | why |
|---|---|---|
| BSR-LU-01 | Small Catechism: II. The Creed, ¶1–3 | a catechism's treatment of the Creed; named by R6-43 |
| BSR-LU-01 | Large Catechism: The Apostles' Creed, all 11 chunks ¶1–70 | a catechism's treatment of the Creed; named by R6-43 |
| BSR-EO-06 | Definition of Faith, Chalcedon, paragraph 10 | the acts' record of the bishops' acclamation after the reading ("After the reading of the definition, all the most religious Bishops cried out …"), not the definition. *Eastern Orthodox is read only; no packet is built from it.* |

**Kept (62), each checked by reading the chunk:**

| row | sections |
|---|---|
| RC-06, RC-08 | Apostles' and Nicene Creeds |
| RC-04 | Constitution 1, *Firmiter credimus*, ¶1–4 |
| LU-01 | Ecumenical Creeds ×3 |
| RP-04 | Nicene 1.1–1.3 and Apostles' 2.1–2.3 |
| AN-03 | Athanasian Creed |
| EO-07, EO-14 | the Creed (each begins with the one-word rubric "People:"; kept, below the phrase floor) |
| EO-09 | §2 |
| EO-12 | articles 1–12 |
| EO-06 | Chalcedon ¶1–9; Constantinople III ¶1–10 |
| EO-13 | Session XVIII ¶1–10 |

**Sections spanning more than one chunk (reported under R6-46.3).** Each is recorded per entry as `section_spans_chunks`. A phrase that crosses one of these chunk boundaries cannot match.

| row | section | chunks |
|---|---|---|
| RC-04 | Constitution 1 | 4 |
| RP-04 | Nicene | 3 |
| RP-04 | Apostles' | 3 |
| EO-12 | Symbol | 12 |
| EO-06 | Chalcedon | 9 |
| EO-06 | Constantinople III | 10 |
| EO-13 | Constantinople III | 10 |

### 3.3 Judgments for the author
1. **`text_through` extents.**
   - *Chosen:* register the creed portion of a mixed chunk. *Weakness:* it is finer than "implemented as the chunk" (R6-46.3).
   - *Alternative:* register the whole chunk. *Weakness:* it registers PC(USA) commentary, contrary to R6-43.
   - *Alternative:* leave the mixed chunks out. *Weakness:* the Nicene and Apostles' Creeds lose their last articles.
   - No card is affected by any of the three (§3.4).
2. **The Gloria Patri after AN-03.** It is liturgical text, not the Quicunque Vult, so it is left out. *Weakness:* the BCP prints the two together at Morning Prayer.
3. **EO-06 Chalcedon ¶10.** It is left out as acts narrative. *Weakness:* NPNF prints it directly after the definition.

### 3.4 Tests (5 new) and sandbox effects
- **Tests:**
  - `test_r6_27_extends_to_sections_…`: every registered section's locator and division carry no catechism, commentary, exposition, introduction, Q. or Q&A marker; the row is never CATECHETICAL; the registered keys carry no commentary.
  - `test_lu01_small_and_large_catechism_creed_sections_are_not_registered`
  - `test_lu01_ecumenical_creeds_sections_are_registered`
  - `test_every_listed_section_is_stored_and_the_list_is_the_only_registration_path`: an empty list registers nothing; a CATECHETICAL row listed fails loudly.
  - `test_sections_spanning_several_chunks_are_reported`
  - **Mutation-checked:** adding LU-01's catechism Creed sections to a copy of the list makes three of the tests fail.
- **Sandbox (`phase2-effects.json`, `phase2-deep-diff.json`): no seat, tier, lead or disclosure change on any card.**
  - Q-139 LU-01-2, Q-259 LU-01-b4-1 and Q-379 LU-01-b1-1 lose a `registered_phrase_hit` on a Large Catechism chunk. It raised nothing, because it is the same row.
  - Q-195 LU-03-1's `raised_by_registered_text` no longer lists "Large Catechism: The Apostles' Creed, ¶1–9". The two Ecumenical Creeds hits remain.
- **Stop check (`raised_by_check.py`):**
  - It fails on the baseline, with 4 catechism hits.
  - It passes after phases 2, 3, 4 and 5: 96 hits and 9–11 raised_by entries, all on listed creed sections.

---

## 4. Phase 3: confessed catechisms (R6-44)

### 4.1 BSR-LU-03 → CONFESSIONAL
- **Through the override path, with the workbook value recorded.** `_author_ruling_override.applied.authority_tier` = `{workbook: CATECHETICAL, ruled: CONFESSIONAL}`.
- **The override hook fix was pulled forward from phase 5.**
  - LU-03 already carries R6-37's override (`draft_recommendation`).
  - The old hook keyed by registry_id, so R6-44 would have silently replaced R6-37. Shown: the old hook returns only the second ruling's fields for a two-ruling row.
  - `rulings.registry_overrides` now **combines** rulings on a row. Each field names the ruling that set it (`field_rulings`). Two rulings setting one field to different values fail loudly; agreeing rulings combine.
- **Kept, and tested:**
  - the translation disclosure: "approved by The Lutheran Church-Missouri Synod (one church); English translation: Concordia Publishing House (c) 2019";
  - the apparatus guard: a "The Central Thought" chunk still resolves to OFFICIAL_EXPOSITION.
- **Evidence for the move is on record, not re-verified this session.** R6-6 BSR-LU-03 records LCMS Constitution Art. II as accepting the Small Catechism of Luther among the symbolical books: LCMS Handbook 2023 Update Edition, WebFetch, district-hosted copy, one publisher.
- **Two session 11 assertions that encoded LU-03 as CATECHETICAL were updated**, with comments: `ADOPTED_CATECHETICAL` and `test_the_stored_lu03_chunk_…`.
- **Tests (2 new):**
  - `test_lu03_is_confessional_with_the_workbook_value_recorded_and_keeps_disclosure_and_guard`
  - `test_several_rulings_on_one_row_combine_and_a_conflict_fails_loudly`

### 4.2 Catechism rows (for the author): `session13/catechism-rows.md`
- **Scope:** 14 rows are catechisms by title, genre or division, out of all 47 registry rows. EO rows were read only. No row but LU-03 moved.
- **Already CONFESSIONAL, with a subscription or adopting act on record naming them:** LU-01 (its catechisms), RP-02, RP-03, RP-05.
- **RP-04:** CONFESSIONAL, with no act on record naming its catechisms separately.
- **CATECHETICAL, with no naming act on record:** RC-07, EO-04, EO-01, EO-02, AN-04, AN-05.
- **Candidates for a B1(b) move, ranked:**
  1. **AN-02** (BCP 1662 Catechism). *For:* Canon A5 names the BCP, and the Catechism is integral to it (R6-35). *Weakness:* A5 names the book, not the Catechism; one instrument, one publisher.
  2. **RC-01** (Catechism of the Catholic Church). *For:* *Fidei Depositum* may call it a norm for teaching. *Weakness:* the constitution's text was never read, and the Catholic Church has no confessional subscription.
  3. **AN-04, AN-05.** *Weakness:* no naming act on record.

### 4.3 Sandbox effects of phase 3 alone (`phase3-effects.json`): 8 Lutheran cards, all from LU-03's tier

| cell | change |
|---|---|
| Q-075, Q-115, Q-187 | same three seats; LU-03-1 moves from seat 3 to seat 2 (now CONFESSIONAL, PRIMARY) |
| Q-123 | tier only |
| Q-163, Q-227 | tier only; the seats and their order are unchanged (§4.4) |
| **Q-179** | LU-01-1, LU-03-2, LU-03-1 → **LU-01-1, LU-02-2, LU-03-2**. LU-02-2 (Augsburg Confession Art. XIX, "God does create and preserve nature", FULL) is now seated. **It has no coder proposal**: `coder_note`, one coder call when next run. LU-03-1 is cut. |
| **Q-195** | the third seat goes from LU-03-2 to LU-01-2 (§4.4) |

- No disclosure changes except the tier.
- Every LU-03 entry now shows `effective_tier_changed_since_run: true`, because the run stored CATECHETICAL.
- **The verifier payload carries no tier** (`prompts.verifier_user`), so no verdict depends on the move. The coder payload does carry the tier: the stored coder proposals for LU-03 were written with CATECHETICAL.

### 4.4 Q-195, Q-163 and Q-227: full seat and tier pictures (unchanged through phases 4 and 5)

**Allocation rule in force** (allocation.py step 4):
- Within a tier, speaks_for groups take slots round by round.
- Groups are ordered by their first member's keys: non-witness, then floor claim, then slot order.
- The cap is 3, filled tier by tier.
- Two groups are involved in all three cells:
  - "Lutheran churches subscribing the Book of Concord" (LU-01, bookofconcord.org);
  - "LCMS" (LU-02, LU-03).

**Q-195 Sovereign (RNR-H25).**

| slot | candidate | row / locator | phrase | floor | tier | group | why |
|---|---|---|---|---|---|---|---|
| 1 (lead) | Q-195-p1-BSR-LU-01-1 | LU-01 Augsburg Confession Art. III ¶1–6 | "forever reign and have dominion over all creatures" | FULL | CONFESSIONAL | Book of Concord | round 1, first group |
| 2 | Q-195-p1-BSR-LU-02-1 | LU-02 Augsburg Confession Art. I ¶1–6 | "the Maker and Preserver of all things, visible and invisible" | FULL | CONFESSIONAL | LCMS | round 1, second group |
| 3 | **Q-195-p1-BSR-LU-01-2** | LU-01 **Large Catechism**, Ten Commandments ¶171–180 | "the command of the Supreme Majesty" | PARTIAL (ACCEPT_WITH_CAVEAT; coder A-SF) | CONFESSIONAL | Book of Concord | round 2, first group |
| cut | Q-195-p1-BSR-LU-03-1 | LU-03 Small Catechism, Creed First Article | "God, the Father Almighty, Maker of heaven and earth" | FULL | CONFESSIONAL (host; was CATECHETICAL raised by LU-01's Ecumenical Creeds) | LCMS | cap: LCMS already holds slot 2 |
| cut | Q-195-p1-BSR-LU-03-2 | same | "I believe that God has made me and all creatures" | PARTIAL | CONFESSIONAL (was CATECHETICAL) | LCMS | cap: LCMS already holds slot 2 |

- **Before R6-44** (eac28f9 and phase 2): the CONFESSIONAL tier held LU-01-1, LU-02-1, LU-01-2 and LU-03-1 (raised). LU-03-2 was the only CATECHETICAL survivor.
  - Filling tier by tier reserves a slot for the only witness of a lower tier.
  - The seats were LU-01-1, LU-02-1 and **LU-03-2** (CORROBORATING, CATECHETICAL). LU-01-2 and LU-03-1 were cut.
- **After:** with every candidate CONFESSIONAL, no lower tier remains, and round 2 gives the third slot to the Book of Concord group's second candidate.
- **Worth the author's attention:**
  - A PARTIAL Large Catechism exposition now holds the seat over LU-03-1, a FULL Small Catechism sentence. The deciding keys are group order and slot order, not floor, because floor ranks members inside a group only.
  - The codex's Q-195 precedent ("the creed text kept the LCMS slot") was corrected in v0.6. The LCMS CONFESSIONAL slot is held by LU-02-1, the Augsburg Confession, and was held by it before and after.
  - No creed text is a candidate. R6-41 does not apply.

**Q-163 Life-giving (RNR-H21).**

| slot | candidate | locator | phrase | floor | tier | group |
|---|---|---|---|---|---|---|
| 1 | Q-163-p1-BSR-LU-01-1 | LU-01 Ecumenical Creeds: The Nicene Creed | "the Holy Ghost, the Lord and Giver of life" | FULL | CONFESSIONAL (a registered creed text at its own tier) | Book of Concord |
| 2 | Q-163-p1-BSR-LU-02-1 | LU-02 Augsburg Confession Art. XVII ¶1–5 | "He will give to the godly and elect eternal life" | FULL | CONFESSIONAL | LCMS |
| 3 | Q-163-p1-BSR-LU-03-1 | LU-03 Small Catechism, Creed First Article | "He has given me my body and soul" | FULL | **CONFESSIONAL** (was CATECHETICAL, CORROBORATING; now PRIMARY) | LCMS |
| cut | Q-163-p1-BSR-LU-02-2 | LU-02 Augsburg Confession Art. III ¶1–6 | "sending the Holy Ghost into their hearts, to rule, comfort, and quicken them" | FULL | CONFESSIONAL | LCMS |

- **Why LU-03-1 holds slot 3:** it takes the LCMS group's second slot ahead of LU-02-2 on slot order (its GUARANTEED slot precedes LU-02-2's EXTRA). The Book of Concord group has no second candidate.
- **Before:** the same three seats, with LU-03-1 filling the lower tier and LU-02-2 cut by the same rule.

**Q-227 Fountain of being (RNR-H29).**

| slot | candidate | locator | phrase | floor | tier | group |
|---|---|---|---|---|---|---|
| 1 | Q-227-p1-BSR-LU-01-1 (+ LU-02-1 as SAME_TEXT witness, R6-4) | LU-01 Augsburg Confession Art. I ¶1–6 | "the Maker and Preserver of all things, visible and invisible" | FULL | CONFESSIONAL | Book of Concord |
| 2 | Q-227-p1-BSR-LU-01-2 | LU-01 Ecumenical Creeds: The Nicene Creed | "Maker of heaven and earth, and of all things visible and invisible" | FULL | CONFESSIONAL | Book of Concord |
| 3 | Q-227-p1-BSR-LU-03-1 | LU-03 Small Catechism, Creed First Article | "I believe that God has made me and all creatures" | FULL | **CONFESSIONAL** (was CATECHETICAL; now PRIMARY) | LCMS |
| cut | Q-227-p1-BSR-LU-01-3 | LU-01 Large Catechism, Ten Commandments ¶24–27 | "an eternal fountain which gushes forth abundantly nothing but what is good" | PARTIAL | CONFESSIONAL | Book of Concord (round 3) |
| verifier-rejected | Q-227-p1-BSR-LU-02-2 | LU-02 Augsburg Confession Art. XVIII | "of Him and through Him they are and have their being" | — | CONFESSIONAL | LCMS |

- **The card order** is LU-01-1, LU-01-2, LU-03-1, unchanged. Round 1 gives LU-01-1 and LU-03-1; round 2 gives LU-01-2.

**Session 12's §1 stop is resolved.** After phase 4, LU-01's Small Catechism chunk holds Luther's whole text. It is not a registered text, and no LU-03 phrase is raised by it: Lutheran cards show header-only diffs in phase 4.

---

## 5. Phase 4: corpus repair resumed

### 5.1 What was done
1. **The five chunk files and the manifest were snapshotted** before any change (scratch copy).
2. **The held patch was applied:** `git apply session12/phase3-held.patch`, cleanly. Tests: 169 passed.
3. **AN-05 guard (R6-46.1).**
   - `sources.acna_to_be_a_christian` now gives division `front matter (publisher/editor apparatus)` **only** to the chunk before "Part I".
   - Part I's introductory chunk gets division `Part I introductory matter (integral text)` (`ACNA_PART_I_INTRO`) and the locator "To Be a Christian, Part I, Beginning with Christ — introductory matter before Q.1". It is not guarded.
   - The guard's marker is unchanged. Its rulings text says it is narrowed.
   - Session 12's test was updated. A new test checks every stored chunk: exactly one chunk is guarded, the front matter, and the Part I chunk resolves CATECHETICAL.
4. **AN-04 Historical Documents (R6-45).**
   - `R6-45.scope_marker` gives `{locator_prefix: "Historical Documents of the Church", marker: AWAITING_SCOPE_RULING}`.
   - `Registry.scope_marker`, `tier_resolution` and packets put `awaits_scope_ruling` on every entry located in such a chunk, including parallel-witness records. The packet header lists them (`awaiting_scope_ruling`).
   - `_registered_sections` refuses to register a marked section, and none is listed.
   - Tested, including that listing one fails loudly.
5. **Corpus builder fix.**
   - `corpus.keep_unyielded_entries` makes a `--only` build keep the manifest entries of rows the registry no longer yields, in manifest order. A full build is unchanged.
   - Test added. In the real run it kept `BSR-EO-03` (HOST_RETIRED) with no hand restore.
6. **Ollama was checked** (`store.ollama_available()` True, nomic-embed-text).
   - Then: `corpus.py build --reuse-cache --only BSR-RC-07,BSR-AN-04,BSR-AN-05,BSR-RP-05,BSR-LU-01 --accept-drift`.
   - Log: `session13/rechunk-build.log`. 0 cache misses; the five rows were re-embedded.
7. **The mapping was rebuilt** (`session13/chunk_mapping.py` → `session13/chunk-id-mapping.json`). `config.CHUNK_ID_MAPPINGS` now points at it.

### 5.2 Re-chunk results
**The text hashes are identical to session 12's held re-chunk** (its report §4.6). The AN-05 division change does not enter the text hash.

| row | chunks | text_hash (new) | mapping |
|---|---|---|---|
| BSR-RC-07 | 533 → 655 | 71d4b57eae924570… | 532 SAME; Q.533 TEXT_CHANGED (Part Four and Appendix moved out) |
| BSR-AN-04 | 124 → 126 | 44e8a00c337b3c26… | 123 SAME; p. 862 chunk TEXT_CHANGED → itself + the two Historical Documents chunks |
| BSR-AN-05 | 368 → 370 | c77b59013003fa54… | 365 SAME; old "Q.1"–"Q.3" RELOCATED to the front matter, the Part I introduction and the real Q.1–3 |
| BSR-RP-05 | 128 → 132 | 6ba939164cd748c9… | 125 SAME; Q&A 77, 79, 119 TEXT_CHANGED → themselves + CRC note chunks; Q&A 80 added |
| BSR-LU-01 | 738 → 741 | 099501fc8ae05838… | 727 SAME; 8 Small Catechism chunks TEXT_CHANGED; 3 RELOCATED (re-ranged) |

- **Comparison with session 12's mapping:** identical except AN-05's Part I locator, which is the R6-46.1 rename.
- **Candidates on changed chunks:** 23. The same 23 as session 12, and all verbatim in their new chunk.

### 5.3 Sandbox effects of phase 4 alone (`phase4-effects.json`, `phase4-deep-diff.json`): no seat, tier, lead, verdict or disclosure change
- **Locator changes on 11 cards:**
  - Q-313, RC-07-1 (a rejection): Compendium Q.533 → Q.586.
  - Q-237, Q-413, Q-421, Q-429, Q-437: AN-04-1 seated → "Historical Documents of the Church (BCP p. 864) — Definition of the Union … Council of Chalcedon, 451 A.D., Act V".
  - Q-277 (AN-04-1 seated, AN-04-2 rejected) and Q-453 AN-04-1 seated → "… — Quicunque Vult commonly called The Creed of Saint Athanasius".
  - Q-381, Q-389, Q-405: AN-04-1 rejections → the Quicunque Vult chunk.
- **Parallel-witness records with new locators (8 in 7 cards):** Q-157, Q-285, Q-301, Q-317, Q-365, Q-373 (×2), Q-445. All are AN-04 → Quicunque Vult.
- **Totals:**
  - 19 Anglican entries relocated; all 19 carry `awaits_scope_ruling` (R6-45).
  - 0 dropped at build.
  - The raised_by check is clean.
- **Every cited chunk whose text changed is the defect being fixed.** The run-on text moved to the chunk named for it, and each phrase stands verbatim in both.

---

## 6. Phase 5: row added by ruling; BSR-BA-04

### 6.1 The path
- **`rulings.added_rows`** reads a ruling that carries `add_row: true` and a `new_row` block.
  - Refused: missing required fields, a placeholder id ("BSR-BA-04 (confirmed …)"), and two rulings adding one id.
  - The override hook never sees an added row.
- **`Registry._add_ruled_rows`** appends the row in memory as AUTHOR_RATIFIED, with `_author_ruling_added`.
  - A branch spelling the workbook does not use fails loudly.
  - Once the workbook has a row with that id, the workbook row is read. It must agree with the ruled values, or the build fails loudly.
- **`rulings.adoption_rows`** carries the added row's `adoption` block.
- **`Registry.adoption_disclosure`** shows `disclosure_wording` exactly for an ADOPTED row that has one. Only BA-04; BA-03's wording is tested unchanged.
- **Test (1 new):** `test_a_row_added_by_ruling_is_a_separate_path_and_the_workbook_wins_once_it_agrees`. It covers a synthetic ruling, placeholder and missing fields refused, a bad branch, the workbook-agrees case (BA-03's values) and the workbook-disagrees case.
- **The override-combining fix** is described in §4.1.

### 6.2 Confirmations
- **Next free Baptist id: BSR-BA-04.**
  - Every sheet of workbook v2.25r4 was searched for `BSR-BA-NN`. Only BA-01, 02 and 03 occur, all in the Branch Source Registry.
  - The 5 other `BSR-BA-04` strings in `data-sources/sjn` are this rulings file and the session reports.
- **Branch spelling: `Baptist`,** exactly as on BA-01, 02 and 03.

### 6.3 The row, fetch and chunks
- **Row values:** R6-42's `new_row`, verbatim (tested field by field).
  - OFFICIAL_EXPOSITION, with `author_note` "interim, pending Codex F.8".
  - speaks_for, JURISDICTIONAL, abc-usa.org, canonical_url, HTML, and the exact scope_caveat.
  - ADOPTED, ONE_CHURCH, the Board of General Ministries.
- **Card disclosure** (exact): "American Baptist Churches USA holds no binding creed. Its cooperating churches affirm this statement as descriptive of American Baptist faith and practice."
- **Fetch:** `https://www.abc-usa.org/we-are-american-baptists`, HTTP 200, no redirect, 14,928 bytes, strict host. Admitted host: abc-usa.org.
- **First sentence** "American Baptists worship the triune God …": present in the fetched bytes and first in the first chunk.
- **Last sentence** "That Jesus shall reign for ever and ever.": present, and last in the last chunk.
- **The head note is excluded.** It is the italic paragraph "'We Are American Baptists' is an expression … adopted by the covenanting partners … Standing Rules, under Addendum #1". Also excluded: the title heading, the image, the print and brochure links, and all site chrome.
  - The adapter fails closed if the head note is not found exactly once, if either sentence is missing, or if the head note reaches a chunk. Tested on a synthetic page with both failure cases.
- **A decoding defect was found and handled for this row.**
  - The fetcher reads the page as ISO-8859-1 (no charset header).
  - The shared `textutil.fix_mojibake` repairs cp1252 mojibake and here **drops** the C1 bytes, so "God's" becomes "Gods" and "…" vanishes.
  - The BA-04 adapter re-decodes strictly as UTF-8 instead (latin-1 is byte-transparent). "God's reconciling grace" survives (tested).
  - **The existing BSR-BA-03 chunks show the same loss** ("Christs example"). They were not touched; see §9.
- **Chunks:** 19, 5,703 characters, text_hash 1ffa202b70e66a6e…, embedded. Full list with text: `session13/ba04-chunks.json`. Log: `ba04-build.log`.
  - ¶1–¶8, the opening paragraphs;
  - "Therefore, with Baptists around the world, we believe" (the four "That …" items);
  - "American Baptist convictions (introduction to the lists)";
  - one chunk per list: A Redeemed / A Biblical / A Worshiping / A Mission / An Interdependent / A Caring / An Inclusive / A Contemporary People;
  - "We further believe".
- **The lists are kept (B2(b)).** As published, "A Caring People" has two items and ends with a semicolon. Whether an item is missing from the page is for the QA track to compare with the print-ready PDF.
- **Tests (2 new):**
  - `test_ba04_row_resolves_and_discloses_as_ruled`
  - `test_ba04_adapter_keeps_the_statement_and_excludes_the_head_note`

### 6.4 Eligibility, and sandbox effect
- **Eligible for all 37 Baptist open cells:** Q-022, 070, 078, 086, 102, 118, 126, 134, 142, 150, 158, 166, 198, 230, 238, 246, 254, 262, 270, 278, 286, 294, 302, 318, 326, 334, 350, 358, 374, 382, 390, 406, 414, 422, 430, 438, 454.
  - Baptist has no consultation ladder; `CONSULTATION_LADDERS` names only Eastern Orthodox.
  - BA-04 is not fallback-only (APP CONFIG lists BSR-AN-05), not a witness row, and not refused.
  - All 37 cells are DONE, and their pass 1 consulted BA-01..03 only.
  - R6-2's refused Baptist cells (Q-382, Q-390, Q-454) refuse named candidates, not the cell.
  - The 19 chunks fit one locator call per cell (coverage FULL).
- **Sandbox (`phase5-effects.json`): no seat, tier or verdict change.**
  - All 37 Baptist cards now report BA-04 as a ratified row that supplied no text.
  - The 7 empty cards (Q-254, 262, 382, 390, 406, 422, 454) therefore **can no longer be offered "NOT LOCATED — CURRENT STANDARD REVIEWED"**. Their honest state is "NOT LOCATED — NOT YET RECOVERED" (header: reviewed offered 7 → 0).
  - This is the harness working as designed. It lasts until Track B runs.
  - Other branches change only in their headers (rulings applied).

---

## 7. Phase 6: cost estimate (gate6-v1.3, majority of 3 per C1)

Written by `session13/phase6_estimate.py` → `phase6-estimate.json`.

**Unit costs from all recovery-runs call logs:**

| call | n | mean | p90 |
|---|---|---|---|
| sonnet verifier v1.3 | 130 | $0.0215 | $0.0411 |
| opus verifier (all versions; none at v1.3) | 1,353 | $0.0724 | $0.1134 |
| Baptist locator | 201 | $0.0327 | $0.0610 |
| coder | 593 | $0.0093 | $0.0136 |

**Expected** uses the mean; **bound** uses the p90 and the worst routing.

### Track R (cap $30)
- **Cells (18):**
  - Anglican: Q-157, Q-237, Q-277, Q-285, Q-301, Q-317, Q-365, Q-373, Q-381, Q-389, Q-405, Q-413, Q-421, Q-429, Q-437, Q-445, Q-453.
  - Roman Catholic: Q-313.
- **Candidates:** 20 stored verdicts on a chunk whose text changed: 19 on AN-04 and 1 on RC-07. All 20 were sonnet-verified; Q-405's also carries an opus rubric (PRIMARY_REJECTED_ALL).
  - The verifier judges against the chunk text (`verifier_user` sends the chunk), which is why these need a verdict.
  - Not in the track: 3 unslotted candidates that were never verified (Q-153 RC-07-3, Q-313 RC-07-3, Q-365 AN-04-2).
- **Cells whose seat or tier picture changed in phases 2–4: none needs a verdict.**
  - Phase 2 changed no seat or tier.
  - Phase 3's tier moves do not enter the verifier payload, and every newly seated candidate (Q-179 LU-02-2, Q-195 LU-01-2) is already verifier-accepted.
  - Q-179 LU-02-2 needs **one coder call**, not a verdict.
  - Phase 4 changed locators only.
- **Calls and cost:**

  | | sonnet | opus | USD | share of cap |
  |---|---|---|---|---|
  | expected | 60 | 3 | **$1.51** | 5% |
  | bound (every cell routed to opus) | 60 | 54 | **$8.59** | 29% |

### Track B (cap $30)
- **Cells:** the 37 above.
- **Calls:**

  | | locator | sonnet verifier | opus verifier | coder |
  |---|---|---|---|---|
  | expected | 37 | 60 (20 candidates × 3) | 9 | 20 |
  | bound | 37 | 333 (the locator cap: 3 candidates × 37 cells × 3) | 63 (reject-all can fire only on the 7 empty cards) | 111 |

- The expected 20 candidates assumes about 0.5 per cell; BA-03's similar page yielded 1 in 37.
- **Cost:**

  | | verifier only | share | all-in (locator + coder) | share |
  |---|---|---|---|---|
  | expected | **$1.94** | 6% | $2.70 | 9% |
  | bound | **$20.83** | 69% | $24.60 | 82% |

### Gate
- **Both estimates are at or below 80 percent of their caps**, and so are both verifier bounds.
- Only Track B's all-in bound (82%) is above 80%. The prompt's estimate is of verifier cost.
- **Phase 7 did not start** for the reason in §1.

---

## 8. Constraints and stop conditions checked
- **Constraints:**
  - No edit to measured verifier versions, fixtures, the codex, the workbook or `src/_data/sjn`. `git diff eac28f9 -- src/_data/sjn data-sources/sjn/recovery-packets data-sources/sjn/*.xlsx` is empty.
  - Eastern Orthodox was not run; its registered sections were read and listed only.
  - No tier moved except BSR-LU-03's.
  - No rebuild.
  - Nothing reached app data.
- **PUBLIC-CERTIFIED cells:** none. All 247 sandbox cards are open cells (workbook rendered state: 240 "NOT LOCATED — NOT YET RECOVERED", 7 "NOT LOCATED — CURRENT STANDARD REVIEWED"), so none changed or lost a citation.
- **After phase 2:** no candidate is raised by a catechism, confession or commentary section (§3.4).
- **Re-chunk:** every changed cited chunk is explained by its defect (§5.3).
- **BA-04 fetch:** both sentences present; head note excluded.
- **Model calls before phase 7:** none. The sandbox builds refuse model calls and network requests and reported 0 attempts each.
- **Held:** the §1 contradiction, before phase 7.

## 9. Remaining items

### For the author
1. **§1:** choose how phase 7 runs (voting and queue shapes, single-call, or hold).
2. **§4.2:** the catechism-row batch. AN-02 is the strongest B1(b) candidate, then RC-01.
3. **§4.4:** Q-195's third seat now goes to a PARTIAL Large Catechism line over LU-03's FULL Small Catechism sentence, on group and slot order. The precedent text should be restated from this picture.
4. **§3.3:** the `text_through` extents (RP-04 1.3 and 2.3, LU-01 Apostles', AN-03 without the Gloria) and EO-06 Chalcedon ¶10 left out.
5. **R6-45:** the AN-04 Historical Documents row awaits Cowork verification.
   - 19 Anglican entries carry the marker: 7 seats, 8 witness records, 4 rejections. Seated ones: Q-237, Q-277, Q-413, Q-421, Q-429, Q-437, Q-453.
   - They are still unverified against their new chunks (Track R).
6. **Workbook deltas pending:**
   - BSR-LU-03 authority_tier CONFESSIONAL;
   - the new BSR-BA-04 row with its adoption columns;
   - the carried items from session 12 §8.10.

### For the QA track
1. **The BA-03 decoding loss:** its chunks lack apostrophes and quotation marks ("Christs example"). The cause is the fetcher's ISO-8859-1 read plus `fix_mojibake` dropping C1 bytes. A re-chunk with a strict UTF-8 re-decode would change BA-03's text hash; one BA-03 candidate is slotted in live-1.
2. **Other rows fetched without a charset header** may carry the same loss. They have not been searched.
3. **"A Caring People"** has two items ending in a semicolon on the HTML page. Compare it with the print-ready PDF and Standing Rules Addendum #1.
4. **A second publisher for LCMS Constitution Art. II,** now load-bearing for LU-03's tier as well as its adoption.
5. **Q-179 LU-02-2 needs a coder proposal** at the next run.
