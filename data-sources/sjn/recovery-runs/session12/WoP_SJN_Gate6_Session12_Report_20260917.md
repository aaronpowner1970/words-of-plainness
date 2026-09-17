# SJN Gate 6, session 12: corpus repair, seating rule, new Baptist row (17 September 2026)

**STOPPED at phase 3 on a stop condition. Phases 1 and 2 are committed. Phase 3 is done and tested but held, not committed.
Phases 4–6 did not run.**

- **Model calls: 0. Spend: 0.00 USD. Network requests: 0.** Every page and PDF came from the fetch cache, and no BSR-BA-04 fetch was made.
- **Tests: 154 passed** on the committed tree: the 147 existing tests plus 7 new ones. With the held phase 3 patch applied: **161 passed**
  (7 more new tests; one session 11 test rewritten).
- **Not changed:** the workbook, the codex, verifier and locator versions, the fixtures, `src/_data/sjn`, the live-1 cell states,
  the packets (no rebuild), Eastern Orthodox and `operational-state.yaml`.
- **The chunk store, Chroma and `corpus-manifest.json` are as at 77895e1.** The phase 3 re-chunk was run, measured and then rolled
  back (§4.7).
- **Instruments.**
  - Local reads of workbook v2.25r4, the chunk store (`.cache/sjn-recovery/chunks`), the fetch cache (`.cache/sjn-recovery/fetch`,
    fetched 12–13 Sep) and the committed packets.
  - Sandbox packet builds with every model call and network request refused (`session12/sandbox_build.py`).
  - One instrument throughout; nothing was checked against the web.
- **Repo check at start:** HEAD 77895e1 and a clean tree, except the unrelated untracked `tools/reports/chat_screens/Claude outputs/`.
  One other Claude session was listed, idle; no file in the repo had changed since the session 11 commit.

---

## 1. The stop (phase 3e): what held and why

**Stop condition:** "A verification contradicts this prompt in a way that changes what should be written."

**What the prompt asks for, in two places:**
- Phase 2: a test that *Q-195's pattern is preserved*. R6-41 names Q-195's session 11 outcome, with Luther's explanation seated,
  as the correct pattern.
- Phase 3e: repair LU-01's Small Catechism extraction.

**What the repair does.** It turns "Small Catechism: II. The Creed, ¶1–3" from 30 characters of "–Answer:" markers into the whole
text: the Creed's three articles *and* Luther's explanations.

**Why that changes cards.** `Registry.registered_creed_texts` treats any chunk as a registered creed text when:
- its locator names a creed, and
- its row is CONFESSIONAL.

BSR-LU-01 is CONFESSIONAL, so the repaired Small Catechism chunk becomes a registered creed text. Phrase-level resolution (R6-10/R6-15)
then raises every LU-03 phrase that happens to be worded identically in the 1921 Triglotta. The sandbox rebuild of all seven packets,
under the phase 2 rule plus the full phase 3 re-chunk, shows:

| cell | candidate | phrase | tier | card |
|---|---|---|---|---|
| Q-195 Sovereign | BSR-LU-03-2 | "I believe that God has made me and all creatures" | CATECHETICAL → CONFESSIONAL | **cut** by the group rule ('lcms' already holds a CONFESSIONAL slot); **BSR-LU-01-2** (Large Catechism, "the command of the Supreme Majesty") **takes the seat** |
| Q-163 Life-giving | BSR-LU-03-1 | "He has given me my body and soul" | CATECHETICAL → CONFESSIONAL | seat kept |
| Q-227 Fountain of being | BSR-LU-03-1 | "I believe that God has made me and all creatures" | CATECHETICAL → CONFESSIONAL | seat kept |

In all three the hit is `BSR-LU-01 Small Catechism: II. The Creed, ¶1–3`. The raising words are **Luther's explanation**, not the Creed.

**Why this is a contradiction, not a routine effect:**
- It reverses the Q-195 outcome the author ratified as correct under R6-41.
- It rests on a catechism's exposition being treated as a registered creed text. Codex B1 says "A catechetical source is never a
  registered creed text, even when it quotes one". R6-22 enforces that by *row* only, and LU-01's row is CONFESSIONAL.
- The raise depends on a translation accident. Only 4 of LU-03's 10 sentences match the Triglotta verbatim. Under B2(d), adoption
  attaches to the text, not the translation.

**The rule already reaches the Large Catechism.** Before this session, 11 LU-01 chunks "Large Catechism: The Apostles' Creed, ¶1–70"
(about 26k characters of Luther's exposition) were already registered creed texts.
- In today's packets they raise only LU-01's own candidates, so no tier moves: Q-139 LU-01-2, Q-259 LU-01-b4-1 and Q-379 LU-01-b1-1.
- The Small Catechism repair is what makes the rule reach another row.

**What should be written therefore turns on a ruling that is not mine to make. Ranked options:**

1. **A catechism section is not a registered creed text, even inside a confessional row.**
   - Registered creed texts in LU-01 would be the "Ecumenical Creeds" chunks only. The Small and Large Catechism "Creed" sections
     are left out, by section rather than by row: B1 applied as written, and R6-22 extended.
   - Effect: Q-195 keeps its ratified pattern after the repair; the Large Catechism hits above stop.
   - *Weakness:* for Lutherans both catechisms are confessional writings in the Book of Concord. "Section" needs a rule: a locator or
     division marker per row, or a ruling list.
   - *Weakness:* it touches RP-04's Book of Confessions creed chunks only if they are catechisms (they are not).
2. **Keep the rule and accept the raises.**
   - Q-195 changes as tabled; Q-163 and Q-227 move tier.
   - *Weakness:* it contradicts R6-41's Q-195 precedent.
   - *Weakness:* the raise depends on where two translations happen to coincide.
   - *Weakness:* a CATECHETICAL row's own text is lifted by the same text in an older translation.
3. **Declare LU-03 and LU-01's Small Catechism one text (an R6-4 declared same-text row).**
   - Then the translations compete for one slot rather than raising each other.
   - *Weakness:* which translation holds the seat is itself a ruling.
   - *Weakness:* the declaration mechanism is row-level (all of LU-01), so it would need a section scope.
4. **Commit 3a–3d now and hold 3e only.**
   - None of 3a–3d moves a tier or a seat (§4).
   - *Weakness:* LU-01's Small Catechism stays empty. The session 11 same-text check stays unanswerable, and LU-03 keeps no LU-01
     parallel witness.

**What was done about it:**
- Phase 3 was **not committed**. The prompt says to hold the phase that triggered the stop, and phase 3 is one unit.
- The whole of phase 3 is kept as `session12/phase3-held.patch`, which applies cleanly on this commit. It carries the chunker fixes,
  the relocation mechanism, the two guard entries and 7 tests.
- The re-chunked store was rolled back (§4.7).

---

## 2. Phase 1: rulings written (`author-rulings-pending-workbook.json`)

Written by `session12/write_rulings.py` (idempotent).

- **R6-38 completion.**
  - Added `R6-6_adoption_field.rows.BSR-LU-01.amended.completed_by_verification.author_accepted`, dated 2026-09-17: "ONE_CHURCH;
    The Lutheran Church-Missouri Synod; LCMS Constitution Art. II".
  - The row's amended status now reads "completed by verification, author-accepted 2026-09-17". The values are unchanged.
  - Also added `R6-38_adoption_scope_reach.completion`.
- **R6-36 completion.**
  - Appended the Cowork competence text, verbatim, to `BSR-AN-05.adoption_verified`, after the existing text.
  - Added `R6-36_an05_adoption.completion` with `qa_track_discharged: true`.
  - Status, scope, body and the card disclosure are unchanged. The disclosure still reads "approved by College of Bishops of the
    Anglican Church in North America (one church)" (tested).
- **R6-41** `R6-41_original_holds_the_seat`: the rule text, its four precedents and where it is implemented.
- **R6-42** `R6-42_ba04_identity_statement`:
  - carries every value from the prompt (`new_row`, `adoption`, `chunking_guards`) and the exact card disclosure;
  - `as_implemented` says it is **not yet implemented** (session 12 stopped at phase 3);
  - the registry id and branch spelling are still to be confirmed in phase 4.

---

## 3. Phase 2: the seating rule (R6-41, Codex B3(a)), committed

### 3.1 Implementation

- **`Registry.registered_phrase_hits(branch, phrase)`**: every registered creed or definition text carrying the phrase.
  `resolve_registered_phrase` now returns its head; the ordering is unchanged.
- **`Registry.raised_by(rid, chunk, phrase)`**: the registered texts that *raised* a citation. These are the hits at the tier it
  resolves to, when that tier is above the host tier. The citation's own chunk is excluded, because a creed text does not quote
  itself.
  - `tier_resolution` returns it as `raised_by`.
  - `packets.py` puts it on every entry as `raised_by_registered_text`.
  - The cell runner's `allocation_view` computes it the same way, so the coder allocation and the packet allocation cannot diverge.
- **`allocation.allocate`, step 5a**, runs on the tier sequences before the cap.
  - **When the rule applies:** a raised candidate yields to a *live candidate of the same cell located in one of those registered
    texts*: same registry_id, same locator, same tier.
  - **The seat and the lead:** the original takes the quoting candidate's place in the tier sequence if that is earlier than its own.
  - **The quoting candidate:** takes no slot and is recorded on the original as a parallel witness, rule `ORIGINAL_HOLDS_SEAT`. The
    record carries `original` and `registered_text`.
  - **When no candidate sits in the registered text:** nothing changes, and the quoting candidate keeps its seat at the raised tier.
  - **Choosing among originals:** where several candidates sit in the same registered text, the one whose own phrase overlaps the
    quoted words wins, then slot order.
  - **Chains** (an original that itself yielded) and **an original that is an R6-4 parallel witness** are both followed.
  - **The cap:** if the original is then cut by the cap, the quoting candidate is cut too, and says so.

**Interpretations made (for the author to confirm):**
- "Candidate for the same cell" means a *verifier-accepted* candidate that reaches allocation. A rejected or unslotted original does
  not take a seat.
- "The registered text" means the chunk: registry_id plus locator.

### 3.2 Tests (`tests/test_session12_rulings.py`, 7 new)

**Phase 2:**
- `test_a_quoting_candidate_never_displaces_or_leads_over_the_registered_text_it_resolves_to`:
  - the Q-205 shape in three input orders, and the Q-317 lead shape;
  - a candidate from another chunk of the same row is not the original;
  - **mutation-checked:** it fails with the rule disabled.
- `test_a_quoting_candidate_keeps_its_seat_when_the_original_is_not_a_candidate`:
  - the Q-297 shape, where the result is identical to allocating without the field;
  - a registered text at a different tier is not the original.
- `test_q195_pattern_is_preserved`:
  - the stored Q-195 shape: LU-02-1 holds the 'lcms' slot, LU-03-1 is cut by the group rule, LU-03-2 is seated;
  - the idealised shape with the creed text itself a candidate: the creed holds the slot, the quotation is its parallel witness, and
    the lower-tier sentence is still seated;
  - **mutation-checked.**
- `test_registry_raised_by_names_the_registered_text_and_never_the_candidates_own_chunk`.

**Phase 1:** `test_lu01_completion_…`, `test_an05_completion_…`, `test_r6_41_and_r6_42_are_recorded`.

### 3.3 Per-cell effects on the current packets

These come from a sandbox build with 0 calls against 77895e1's packets (`session12/phase2-seat-effects.json`). The rule changes
**8 Anglican cards and nothing else**. Every quoting candidate is a BSR-AN-04 or BSR-AN-02 phrase verbatim in BSR-AN-03's Athanasian
Creed.

| cell | before (77895e1) | after |
|---|---|---|
| **Q-205** Judge | AN-01-1, **AN-02-1** (CONFESSIONAL, quotes the creed), AN-04-1; AN-03-1 cut | AN-01-1, **AN-03-1** (with AN-02-1 as ORIGINAL_HOLDS_SEAT witness), AN-04-1: **reversed as ruled** |
| **Q-317** Immense | lead **AN-04-1** (reprint), AN-03-2, AN-01-1 | lead **AN-03-2** (with AN-04-1 as witness), AN-01-1: **lead reversed as ruled**; the card goes from 3 seats to 2 and the Episcopal Church has no seat |
| Q-301 Not made | AN-03-1, **AN-04-1**, AN-03-2 | AN-03-1, AN-03-2 (with AN-04-1 as witness), **AN-03-3** seated: the card is all Church of England |
| Q-365 Eternal | AN-01-1, **AN-04-1** (with AN-03-1 as SAME_TEXT witness), AN-03-2 | AN-01-1, **AN-03-1** (with AN-04-1 as witness), AN-03-2: the reprint no longer holds the seat over the identical creed sentence |
| Q-373 Incomprehensible | AN-03-1, AN-03-2, **AN-04-2** | AN-03-1 (with AN-04-1 as witness), AN-03-2 (with AN-04-2 as witness): 3 seats to 2 |
| Q-445 Neither confounding | AN-01-1, **AN-04-1** (with AN-03-1 as SAME_TEXT witness) | AN-01-1, **AN-03-1** (with AN-04-1 as witness) |
| Q-157 Glorious, Q-285 Uncreated | AN-03-1 seated with AN-04-1 as SAME_TEXT witness | same seats; the witness's rule label is now ORIGINAL_HOLDS_SEAT |

- No tier, verdict, state or disclosure changes.
- Anglican's header `candidates_lower_floor_applied` stays at 4 in the sandbox. Session 11's note that AN-03-1 "carried the lower
  floor" is not borne out by this count.

**Q-297, the lead re-decided.**
- **The original.** BSR-RC-01-1 "begotten not made, consubstantial with the Father" (CCC 242) is raised to CONCILIAR by **BSR-RC-08
  "Nicene Creed"**, the Vatican News Credo, CONFESSIONAL with the Nicene resolving CONCILIAR. That is the only registered text that
  carries the phrase.
- **Is the original a candidate for Q-297?** **No.**
  - No BSR-RC-08 candidate exists in the cell: none seated, cut, rejected or unslotted.
  - BSR-RC-06's Nicene Creed *is* a candidate (RC-06-1, seated), but its wording is "begotten, not made, **of one Being** with the
    Father". RC-01's phrase is not verbatim in it, so it is not the text RC-01 resolves to.
- **What BSR-RC-04 is.** The Fourth Lateran Council, constitutions 1–2 (*Firmiter credimus*; *Damnamus ergo*), CONCILIAR, speaks for
  the Universal Church. Its seated candidate RC-04-1, "The Father is from none", comes from Constitution 1, which is itself a
  registered definition text (the "Confession of Faith"). It resolves at its own tier and quotes nothing.
- **Outcome: B3(a) does not apply.** RC-01-1 keeps its seat at CONCILIAR.
  - The lead is decided by the existing keys: one tier, one speaks_for group ("universal church"), all three floor claims FULL.
  - Slot order gives RC-01-1, RC-04-1, RC-06-1. **The lead stays with BSR-RC-01.**
  - RC-07-1 remains RC-01-1's SAME_TEXT parallel witness.

**Q-195, the claim checked (D1).**
- The Codex and the prompt describe Q-195 as "the creed text kept the LCMS slot". In the stored cell, the 'lcms' CONFESSIONAL slot is
  held by **BSR-LU-02-1**, Augsburg Confession Art. I "the Maker and Preserver of all things", not by a creed text.
- LU-03-1's registered text (BSR-LU-01 "Ecumenical Creeds: The Apostles' Creed") is not a candidate of Q-195.
- So the rule does not apply there, and the outcome is **unchanged** under phase 2: LU-01-1, LU-02-1, LU-03-2 seated; LU-03-1 cut
  by the group rule.
- The test preserves both the stored shape and the idealised one.

---

## 4. Phase 3: corpus repair (done, tested, HELD)

Each defect below was confirmed in the stored chunks, and its cause in the cached bytes, before anything was fixed.
- The re-chunk ran with `corpus.py build --reuse-cache --only BSR-RC-07,BSR-AN-04,BSR-AN-05,BSR-RP-05,BSR-LU-01 --accept-drift`:
  0 cache misses, and the cache file count was unchanged at 327.
- "Words lost" compares casefolded word counts of all old chunks against all new chunks.
- The id mapping is `session12/chunk-id-mapping.json`. Chunk ids change only where a locator changed.
- Card effects are from a sandbox build of the phase 2 rule plus the re-chunk (`session12/phase3-card-effects.json`).

### 4.1 BSR-RC-07: Compendium Part Four and the Appendix
- **Defect confirmed.** "Compendium Q.533" held 49,667 characters: Q.533, then Part Four's answers *without* their questions, then
  both Appendix sections. Q.534–598 did not exist.
- **Cause (cache).**
  - Part Four sets the number and the question in separate bold tags: `<b>534.</b>&nbsp;<b>What is prayer?</b>`.
  - Q.568 is set `<b>568</b>.<b>…</b>`.
  - The Appendix is an anchor (`<a name="APPENDIX">`), never the bold tag the old stop looked for.
- **Fix (`sources.compendium`).**
  - A bare bold number opens a question, and the next bold tag supplies its text.
  - The Appendix is chunked as part of the book (B2(b), no guard):
    - A) Common Prayers: one chunk per prayer per column, 23 English and 22 Latin (`language: la`);
    - B) Formulas of Catholic Doctrine: 12 chunks.
- **Result.**
  - 533 → 655 chunks; Q.1–532 byte-identical.
  - Q.533 text changed (now only Q.533); Q.534–598 new; 57 Appendix chunks new. No words lost.
  - Old hash b254dc3ae461… → new 71d4b57eae92… (full hashes in §4.6).
- **Test:** `test_compendium_reads_split_bold_questions_and_chunks_the_appendix`.
- **Stored candidates on the old chunk:**
  - Q-313 RC-07-1 "God transcends everything" (a tier-allocation cut) moves to Q.586;
  - Q-313 RC-07-3 "Father, whose majesty is boundless" (unslotted) is in Appendix A, The Te Deum;
  - Q-153 RC-07-3 "draw us toward him for his glory" (unslotted) is in Q.587.
  - **None is on a card.** No seat or tier changes.

### 4.2 BSR-AN-04: the Outline ends where the Outline ends
- **Defect confirmed.** The last Outline chunk, "(BCP p. 862) … Q. What, then, is our assurance as Christians?", held 2,681
  characters:
  - the end of the Outline;
  - the whole Chalcedonian Definition;
  - the Quicunque Vult as far as "…but one Almighty."
- **Cause (cache).**
  - The PDF page is the BCP page.
  - p. 863 is the title page "Historical / Documents / of the Church", split over three lines, so the old stop never fired.
  - The adapter's 20-page window ends at p. 864, and the Athanasian Creed continues on p. 865.
- **Fix (`sources.tec_outline_of_faith`).**
  - The Outline stops at the title page.
  - The pages after it *inside the same window*, meaning the text the store already held, are chunked one per printed document heading:
    - "Historical Documents of the Church (BCP p. 864) — Definition of the Union of the Divine and Human Natures in the Person of Christ Council of Chalcedon, 451 A.D., Act V"
    - "Historical Documents of the Church (BCP p. 864) — Quicunque Vult commonly called The Creed of Saint Athanasius"
  - Registry scope and tier are unchanged.
- **Result.**
  - 124 → 126 chunks; 123 identical. The p. 862 chunk now ends "…Christ Jesus our Lord. Amen."
  - Words no longer in chunk text: only the printed headings, now in the locators ("Definition of the Union … Act V", "commonly
    called", "of the Church").
  - Hash 9f812410836c… → 44e8a00c337b….
- **Test:** `test_the_outline_ends_at_the_historical_documents_title_page`.
- **Card entries that move (19 candidates, 17 cells).** Each keeps its seat, tier and verdict, with a new locator and a
  `chunk_relocated` record:
  - **Seated, Chalcedon chunk:** Q-237, Q-413, Q-421, Q-429, Q-437 AN-04-1 (CATECHETICAL). The Anglican branch has no registered
    definition text, so the Chalcedonian phrase is not raised.
  - **Seated, Quicunque Vult chunk:** Q-277 AN-04-1 and Q-453 AN-04-1 (CONFESSIONAL, raised by AN-03). AN-03 is not a candidate there.
  - **Parallel witnesses** (after phase 2), Quicunque Vult: Q-157, Q-285, Q-301, Q-317, Q-365, Q-445 AN-04-1; Q-373 AN-04-1 and AN-04-2.
  - **Verifier rejections:** Q-277 AN-04-2, Q-381, Q-389, Q-405 AN-04-1.
  - **Unslotted:** Q-365 AN-04-2.
- **For the author (not decided here).**
  - The row is "An Outline of the Faith", yet its store has always carried the p. 864 Historical Documents text, and seven card seats
    rest on it.
  - The Quicunque Vult chunk holds only the p. 864 portion.
  - Whether AN-04 should carry the Historical Documents at all, and whether as integral to the adopted BCP (B2(b)), is a scope
    ruling.

### 4.3 BSR-AN-05: front matter no longer takes question numbers
- **Defect confirmed.**
  - "Q.1" and "Q.2" were drafting guidelines 1 and 2.
  - "Q.3" (9,302 characters) held: guideline 3; the Committee sign-off (Packer); "concerning scripture references"; the collect;
    Part I "Beginning with Christ" (introduction, The Gospel, turning to Christ, the prayers, next steps); then the real Q.1–3.
  - From Q.4 the labels were right.
- **Cause (cache).** The guidelines are numbered "1."–"3.", and the counter spent Q.1–3 on them.
- **Fix (`sources.acna_to_be_a_christian`).**
  - Before the first question, a numbered line opens a question only if a question mark follows within four lines.
  - The text the store held before Q.1 becomes two front-matter chunks, split at "part i", with division
    `front matter (publisher/editor apparatus)`.
- **Guard.** A `guard` on `R6-36_an05_adoption`, in the held patch: `apparatus_markers` on that division; no fail-closed text pattern,
  so no question chunk can be demoted.
- **Result.**
  - 368 → 370 chunks; Q.4–368 identical.
  - Q.1–3 relabelled to the printed questions, so their ids change. 2 front-matter chunks added. No words lost.
  - Hash 12dbaa057f89… → c77b59013003….
- **Tests:**
  - `test_acna_guidelines_are_front_matter_and_the_questions_keep_their_numbers`;
  - `test_the_an05_guard_takes_front_matter_to_official_exposition_and_never_a_question`, which checks every stored chunk: guarded
    exactly when front matter.
- **Card effects:** none. No stored candidate cites "Q.1"–"Q.3" (confirmed again).
- **Judgment flagged.** Part I's introductory matter ("Beginning with Christ … The Gospel … next steps") is guarded along with the
  Committee's front matter, failing closed.
  - *Candidate 1 (chosen):* all pre-Q.1 text is front matter. Weakness: Part I's introduction is set inside the catechism's own Part I.
  - *Candidate 2:* guard only the introduction (guidelines, sign-off, Scripture note, collect). Weakness: it treats an unnumbered
    teaching section as adopted text without evidence.
  - *Candidate 3:* no guard. Weakness: contrary to the prompt's B2(b) direction.
  - No card is affected either way.

### 4.4 BSR-RP-05: Q&A 80 and the CRC editorial notes
- **Defect confirmed.** "Q&A 79" held Q&A 80 and the two CRC notes (the editions; Synods 2004/2006 and the RCA sentence). There was
  no Q&A 80.
- **Fix.**
  - Session 11's heading fix, plus: paragraphs opening "*" or "**", and what follows them before the next Q&A, are held out of the Q&A
    text as "<Q&A> — CRC editorial note(s)", division `publisher apparatus (CRC editorial note)`.
  - Guard on `R6-40_rc07_an04_rp05_adoption`, in the held patch.
- **Wider than asked.** The same markup carries CRC notes on **Q&A 77** ("broken") and **Q&A 119** (the NRSV Lord's Prayer), so
  they are separated and guarded too.
  - No stored candidate cites Q&A 77, 79, 80 or 119.
  - The author may prefer Q&A 80 only; say so.
- **Result.**
  - 128 → 132 chunks; 125 identical.
  - Q&A 77, 79 and 119 text changed (notes removed); Q&A 80 added; 3 note chunks added. No words lost.
  - Hash e1c55cc456ed… → 6ba939164cd7….
- **Test:** `test_heidelberg_editorial_notes_are_their_own_guarded_chunks` (Q&A 80 text resolves CONFESSIONAL; the note resolves
  OFFICIAL_EXPOSITION).
- **Tier effect on cards:** none, as expected (no cell cites these chunks).

### 4.5 BSR-LU-01: the Small Catechism re-extracted
- **Defect confirmed.** Small Catechism chunks of 30–165 characters: "II. The Creed, ¶1–3" was `. –Answer: . –Answer: –Answer:`, and
  similarly the Ten Commandments, Lord's Prayer, Baptism and Sacrament of the Altar.
- **Diagnosis (cache).**
  - All ten small-catechism pages on bookofconcord.org set the text inside `<span class="forcespan">` within `<h4>` (commandment,
    article, petition) and `<p>`.
  - "What does this mean?" is in `<em>`.
  - The segment reader keeps only an element's *direct* text, and the adapter took only `<p>`. So only "–Answer:" survived.
  - The bytes are in the cache (fetched 12 Sep), so **no network fetch was needed or made**.
- **Fix (`sources._boc_forcespan_paras`, used only on pages carrying `class="forcespan"`).**
  - Each `<h4>` and `<p>` child of `<main>` is read whole.
  - A bare-number anchor starts a paragraph; a lettered one ("1b") continues it.
  - The rubric before the first number is kept.
- **Result.**
  - 738 → 741 chunks; 727 identical.
  - 8 chunks re-filled with ids unchanged: Preface, Creed, Baptism, Confession, Sacrament of the Altar, Daily Prayers, Table of
    Duties ×2.
  - 3 re-ranged, ids changed: Ten Commandments ¶1–11 → ¶1–10 + ¶11; Lord's Prayer ¶1–7 → ¶1–5 + ¶6–7; Christian Questions ¶20 →
    ¶1–15 + ¶16–20.
  - **4,501 words recovered, none lost.** Hash 0c0076c8e73d… → 099501fc8ae0….
- **Test:** `test_book_of_concord_forcespan_pages_keep_the_catechism_text`.
- **Cards citing a Small Catechism chunk:** none, in any cell.
- **Session 11 same-text check re-run (LU-03 vs repaired LU-01):**
  - No LU-01 chunk is identical to the LU-03 chunk.
  - 4 of LU-03's 10 sentences stand verbatim in LU-01:
    - "I believe in God, the Father Almighty, Maker of heaven and earth." (Ecumenical Creeds; Small Catechism Creed; Large Catechism
      preface)
    - "What does this mean?"
    - "I believe that God has made me and all creatures;"
    - "This is most certainly true."
  - The other 6 differ: CPH 2019 vs Triglotta 1921.
  - The same-text guard (R6-4) would record an LU-01 parallel witness only where a *seated* candidate's phrase is identical. Today that
    happens on no card, because no LU-01 Small Catechism candidate exists.
  - The tier effect of the repaired chunk is the stop (§1). Evidence: `session12/phase3e-lutheran-finding.txt`.

### 4.6 Text hashes (old → new, held)

| row | chunks | old text_hash | new text_hash |
|---|---|---|---|
| BSR-RC-07 | 533 → 655 | b254dc3ae461c26d80a3b2a973a9019c4c9fc2bc9c7b2d5339406ce23b9d1b01 | 71d4b57eae924570f94b01a0a82db78c3aa6cb161c3a5e4769b22f19b4f17e6c |
| BSR-AN-04 | 124 → 126 | 9f812410836c434a9b92c1e50925b2332328e54dd2b1d9384b37dc42808a1c9b | 44e8a00c337b3c265331fe8e39cc7454f890185d562612706430b1b92f257831 |
| BSR-AN-05 | 368 → 370 | 12dbaa057f89079570d03da51a4616bb8a4003271487ae805fc8b0a3a10114e5 | c77b59013003fa54b4c16700b3f316f5b4a644de2020edf7654d1fecc4304ab6 |
| BSR-RP-05 | 128 → 132 | e1c55cc456ed6533195e8726a63940ca8d91d4601c9af586e946726b29e7846b | 6ba939164cd748c9bed91483100f12b17381828c3b19afda634aeb63534fd315 |
| BSR-LU-01 | 738 → 741 | 0c0076c8e73d6300bc2c0a31285021fff11c533d5d4a600b6ddbf77785ec04fe | 099501fc8ae0583907dd23782dd3907305e4d224bd591e6e85adc0996d39c369 |

### 4.7 Mechanism, side effects, roll-back

**Relocation (`packets.relocations` / `packets.relocate`, `config.CHUNK_ID_MAPPINGS`; held).**
- A stored candidate whose (registry_id, locator) chunk no longer carries its phrase follows the mapping to a mapped chunk that does.
- The existing rule still applies: the phrase must stand verbatim in *both* the text the verifier judged and the new chunk.
- The entry gets the new locator and `chunk_relocated`, and the header lists `chunk_relocated_after_run`.
- Without this, a rebuild would drop all 19 AN-04 and 2 RC-07 entries at re-assertion.
- Test: `test_a_candidate_follows_the_mapping_only_to_a_chunk_that_carries_its_phrase`.

**Builder side effect.**
- `corpus.py build --only` rewrote the manifest without **BSR-EO-03**, the retired row R6-3 filters out of the registry.
- The entry was restored by hand before the roll-back. Whoever applies the patch must do the same, or fix the builder to keep entries
  of rows it no longer sees.

**Roll-back after the stop:**
- the five chunk files restored from the pre-re-chunk copies (hashes match the committed manifest);
- Chroma re-embedded for the five rows (533 / 124 / 368 / 128 / 738 ids);
- the manifest restored from git;
- the phase 2 sandbox re-run on the restored state is **identical** to `phase2-seat-effects.json`.

**To resume phase 3:**
1. `git apply data-sources/sjn/recovery-runs/session12/phase3-held.patch`.
2. Run the build command in §4, then restore the BSR-EO-03 manifest entry.
3. Re-run `session12/chunk_mapping.py <pre-re-chunk dir>`.
4. Run `sandbox_build.py` and `seat_diff.py`.
5. Decide §1 first.

---

## 5. Phases 4, 5 and 6: not run

- **Phase 4 (BSR-BA-04):** not started. No fetch, no row, no chunks.
  - Nothing was checked: neither the next free Baptist id nor the workbook's branch spelling. The existing Baptist rows are BA-01,
    BA-02 and BA-03, but that is not the confirmation phase 4 asks for.
  - The registry override hook (`rulings.registry_overrides`) only re-types rows that exist in the workbook: it raises
    `SystemExit` for an unknown id. It also keys by registry_id, so a second ruling on the same row silently replaces the first.
  - Phase 4 therefore needs a small "row added by ruling" path, not just the existing override.
- **Phase 5:** no estimate made.
  - For scoping only: Track R would be the cells in §4.1–4.2 whose candidates sit on changed chunks.
    - Anglican: Q-157, Q-237, Q-277, Q-285, Q-301, Q-317, Q-365, Q-373, Q-381, Q-389, Q-405, Q-413, Q-421, Q-429, Q-437, Q-445, Q-453.
    - Roman Catholic: Q-313 (and Q-153 if unslotted candidates count).
  - Lutheran cells Q-163, Q-195 and Q-227 move tier without a cited chunk's text changing, so they are not Track R as defined.
- **Phase 6:** not run. No rebuild.

---

## 6. Constraints and stop conditions checked

- **Constraints:** no verifier, fixture, codex, workbook or app-data edit; Eastern Orthodox untouched; no model call; no rebuild.
- **PUBLIC-CERTIFIED cells:** none in any packet (Gate 6 packets hold open cells only). None changes, and none loses a citation, in
  any sandbox.
- **Cited chunks changed by a re-chunk:**
  - AN-04 p. 862 (7 seats, plus 8 parallel-witness entries in 7 cells) and RC-07 Q.533 (none on a card).
  - Every change is the defect being fixed: the run-on text moved to the chunk named for it, and each phrase is verbatim in both.
- **Held:** the §1 contradiction.

## 7. Files

| file | status |
|---|---|
| `author-rulings-pending-workbook.json` | committed: phase 1 rulings |
| `scripts/sjn_recovery/allocation.py`, `registry.py`, `packets.py`, `agents.py` | committed: phase 2 |
| `scripts/sjn_recovery/tests/test_session12_rulings.py` | committed: 7 tests |
| `session12/write_rulings.py` | committed: the phase 1 writer |
| `session12/sandbox_build.py`, `seat_diff.py`, `phase2-seat-effects.json` | committed: phase 2 measurement |
| `session12/phase3-held.patch` | committed as a record, **not applied**: `sources.py`, `config.py`, `packets.py` (relocation), rulings guard entries, `test_session11_rulings.py` (guard list now AN-05, LU-03, RP-05), `tests/test_session12_corpus_repair.py` (7 tests) |
| `session12/write_guards.py`, `chunk_mapping.py`, `chunk-id-mapping.json`, `phase3-card-effects.json`, `rechunk-build.log` | committed as records of the held re-chunk; `write_guards.py` was run only inside the held state |
| `session12/phase3e-lutheran-finding.txt`, `lu_check.py` | the §1 evidence (`lu_check.py` reads the scratch copies it was run on) |

## 8. Open items for the author and the QA track

1. **§1:** does a catechism section inside a confessional row count as a registered creed text? This decides phase 3e and Q-195.
2. **AN-04 scope (§4.2):** should the Historical Documents text (Chalcedon; the p. 864 part of the Quicunque Vult) belong to "An
   Outline of the Faith"? Seven card seats rest on it.
3. **AN-05 (§4.3):** guard Part I's introductory matter, or only the Committee's front matter?
4. **RP-05 (§4.4):** separate and guard the notes on Q&A 77 and 119 too, or Q&A 80 only?
5. **R6-41 interpretations (§3.1):** a candidate means an accepted candidate, and the registered text means the chunk. Confirm.
6. **Phase 2 consequences to confirm.** Q-317 and Q-373 drop to two seats, and Q-301 becomes all Church of England. Those are the
   rule's plain effects, and the Episcopal Church's reprint becomes a witness.
7. **The Q-195 description in Codex Part E** ("the creed text kept the LCMS slot") does not match the stored cell. The slot is held
   by the Augsburg Confession Art. I (§3.3).
8. **Corpus builder:** `--only` drops manifest entries of rows the registry filters out (BSR-EO-03).
9. **Phase 4:** a row-added-by-ruling path is needed for BSR-BA-04 (§5).
10. **Workbook:** carry the adoption columns (14 rows ruled), the RC-07 canonical_url, the LU-03 and BA-03 notes, and later the BA-04
    row. Until then they apply in memory from the rulings file.
11. **Carried from session 11:** a second publisher for LCMS Constitution Art. II; the Baptist empty-card wording under Codex F.8.
