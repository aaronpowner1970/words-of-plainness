# Gate 6 — session 5 report (2026-09-13): repairs before Eastern Orthodox

**Code · workbook v2.25r4 GATE6 SCOPE RATIFIED (unchanged, never written) · run live-1 · packets `recovery-packets/*.json` · extracts `recovery-packets/extracts/`**

Answers `wop-scratch/WoP_SJN_B4_PacketReview_20260913.md` (Cowork). Eastern Orthodox did not run. No bot challenge defeated,
no blocked host routed around. Every `run.py` start asserted `456 = 291 open + 24 closed + 141 released`.
**Spend 9.38 USD of the 25 USD cap** (table at the end). Session artifacts: `recovery-runs/session5/`.

---

## Task 1 — BSR-BA-02

**1a — my own fetch** (instrument: `sjn_pipeline.fetch.Fetcher`, python `requests`, strict host, no cache; `session5/task1a-ba02-fetch.json`)

| URL | status | body | "most pure spirit" in raw body | extracted |
|---|---|---|---|---|
| `https://the1689confession.com/1689/chapter-2` (ratified) | **301** → `https://www.the1689confession.com/1689/chapter-2` | — (hop refused under the old rule) | — | — |
| `https://www.the1689confession.com/1689/chapter-2` | **200**, `text/html;charset=utf-8` | **108,936 bytes** (decoded body re-encoded UTF-8; Cowork's browser measured 108,906) | **yes** (and "subsistences") | **3 chunks** (paragraphs 1–3), 2,938 chars |

All thirteen of Cowork's verbatim matches stand in the chunks ("merciful", "long-suffering", "abundant in goodness and truth",
"most just and terrible in His judgments", "blessedness", "immense", "invisible", "without body, parts, or passions",
"immutable", "incomprehensible", "cannot be comprehended by any but Himself", "the Father is of none").

**1b — registry delta** `wop-scratch/WoP_SJN_BranchSourceRegistries_Draft3r4_20260913.csv`: all 47 workbook rows as v2.25r4 holds
them, plus `r4_change` / `r4_change_note`; only BSR-BA-02 and BSR-LU-02 change. BSR-BA-02: `canonical_url` → www form,
`fetch_mode` stays `HTML`, note records the 301 to the same path on the same registrable domain.

> **Proposed workbook change (author to ratify):** Branch Source Registry, BSR-BA-02: `canonical_url` `https://the1689confession.com/1689/chapter-2` → `https://www.the1689confession.com/1689/chapter-2`; `fetch_mode` unchanged (`HTML`).

**1c — the amended rule, verbatim** (`sjn_pipeline/fetch.py` `STRICT_HOST_REDIRECT_RULE`; `www_label_only()` is its only implementation; 8 refusal cases and 3 admission cases in `tests/test_session5_repairs.py`):

> Under strict_host a redirect that changes the host is refused and reported as REDIRECT-CROSS-HOST, with one exception: a hop whose target differs from the URL requested ONLY by the leading "www." label is not a cross-host redirect and is followed. It qualifies only when all of these hold: one host is exactly the other with "www." prefixed (so the registrable domain, every other label and the port are the same); the path is the same; the query is the same; and the scheme is the same or the hop is an http-to-https upgrade. Such a hop is recorded in FetchResult.www_label_redirects as well as in redirects. Every other cross-host redirect stays refused: another subdomain, another registrable domain, a changed path or query, an https-to-http downgrade, or a hop onto a storage or CDN host.

It is narrower than asked in one respect: the query must also be unchanged. The BA-02 corpus was built from the **ratified
bare URL** under this rule (the manifest records the hop in `www_label_redirects`), so the Baptist pass rests on no
unratified URL at all.

## Task 2 — BSR-LU-02 (recoverable; not proposed for retirement)

**2a — my own fetch and the session-3 pdf-audit discipline** (`session5/task2a-lu02-pdf-audit.json`, `task2a_lu02_audit.py`)

- `https://files.lcms.org/dl/f/the-augsburg-confession` → **302 on the same host** → `/api/download/file/the-augsburg-confession`
  → **HTTP 200, 378,071 bytes, `%PDF-1.6`, 51 `/Font` objects**, 27 pages, served as `application/octet-stream`.
- **Defect found on the way:** the fetcher recognised a PDF only by content-type or a `.pdf` suffix, so this route came back
  as zero PDF bytes. Fixed narrowly: a body starting `%PDF-` is a PDF (`fetch.py`).
- Text layer: **87,848 chars**. Every word is separated by U+2029 (PARAGRAPH SEPARATOR), not a space; the repair path now
  folds U+2028/U+2029 to spaces first (no stored chunk carried either character, so no other row changes).
- New adapter `sources.augsburg_confession_lcms`: Preface, Articles I–XXVIII, the abuses introduction, the Conclusion; long
  articles grouped by their printed paragraph numbers exactly as the Book of Concord adapter groups them. **51 chunks,
  81,873 chars.**
- **Articles intact: 28 of 28**; six opening-sentence spot checks each found only inside their own article.
- **Footer contamination: none.** The running header "Page N of 27" is detected and stripped on all 27 pages by the page-furniture
  repair; 27 "Back to top" link lines and the LCMS address block after the last one are dropped; a scan of every chunk for
  page headers, "Back to top", ©, the address, U+2029 and stray `n]` paragraph markers finds 0 (the 13 `]` hits are the
  Triglot's own bracketed German-text insertions).
- The session-3 audit instrument reports `FIRST_CHUNKED_ON_REPAIRED_PATH`: the LEGACY path cannot chunk this PDF at all (no
  U+2029 fold → no headings found → the adapter refuses loudly). No branch ever ran on a legacy chunking of it.
- **What the row adds:** 46 of 51 chunks are textually the same Triglot translation BSR-LU-01 already carries on
  bookofconcord.org. LU-02 adds the LCMS as the publishing body, not new wording (see Task 5 — this has a cost).

**2b.** Carried into Draft3r4 (`fetch_mode` → "PDF - text layer present (publisher Download href; same-host 302 …)").

> **Proposed workbook change (author to ratify):** Branch Source Registry, BSR-LU-02: `canonical_url` `https://files.lcms.org/file/preview/96D5ADA9-4E71-4C9F-9939-9D40E4E9AD8E` → `https://files.lcms.org/dl/f/the-augsburg-confession`; `fetch_mode` `PDF behind client viewer` → `PDF - text layer present`.

One question under rule 7's own wording: the URL that serves the bytes is strictly `/api/download/file/the-augsburg-confession`;
`/dl/f/…` is the publisher's Download href that 302s to it on the same host. I proposed the href (the publisher's stable,
human-facing link; surface (b) of the rule). Author's call.

Because the workbook was not written, LU-02's corpus was built with `corpus.py build --only BSR-LU-02 --registry-delta <Draft3r4>`:
the change is applied in memory only, and the manifest entry, and every Lutheran packet header (`rows_on_unratified_url`),
carry the delta file, its sha256 and "PENDING AUTHOR RATIFICATION".

## Task 3 — the artifact URL rule

Added verbatim as **rule 7** of `WoP\ops\WoP-Source-Verification-Standard.md` (now v1.1).

**Audit of all 47 rows** (`session5/task3-artifact-url-audit.json`). Instrument: each workbook `canonical_url` requested live,
exactly as written, by the strict fetcher (Playwright for the rendered rows); the body tested against **every** stored chunk of
the row (a 48-character normalised window from each), and the manifest read for which URLs the adapter actually used. Measured,
then named. A PDF row reads 65–100% rather than always 100% because the stored chunks are the repaired extraction.

| row | status | class (measured) | windows present / tested | reading |
|---|---|---|---|---|
| BSR-RC-01 | ratified | SERVES_PART | 29/570 | entry page — one article page of CCC Part One §2 ("I Believe in God the Father"); the adapter crawls the section index (50 source pages) |
| BSR-RC-02 | ratified | SERVES_ARTIFACT | 22/22 | serves the artifact |
| BSR-RC-03 | ratified | SERVES_ARTIFACT | 3/3 | serves the artifact |
| BSR-RC-04 | ratified | SERVES_ARTIFACT | 8/8 | serves the artifact |
| BSR-RC-05 | ratified | NOT_A_URL | — | **NOT A URL** — bare domain "sourcebooks.web.fordham.edu (as cited …)"; LINEAGE row, no corpus |
| BSR-RC-06 | ratified | SERVES_ARTIFACT | 2/2 | serves the artifact |
| BSR-RC-07 | ratified | NOT_A_URL | — | **NOT A URL** — bare domain "vatican.va (as cited …)"; the adapter reads …/archive_2005_compendium-ccc_en.html (533 chunks), which the field never names |
| BSR-RC-08 | ratified | SERVES_ARTIFACT | 2/2 | serves the artifact |
| BSR-EO-01 | ratified | SERVES_PART | 1/19 | entry page — OCA Symbol of Faith "God" page; adapter reads 19 sibling pages |
| BSR-EO-02 | ratified | SERVES_PART | 1/14 | entry page — one of 14 OCA Holy Trinity pages |
| BSR-EO-03 | ratified | NOT_REQUESTED | — | not requested — goarch.org retired |
| BSR-EO-04 | ratified | SERVES_ARTIFACT | 595/610 | serves the artifact |
| BSR-EO-05 | ratified | SERVES_ARTIFACT | 22/22 | serves the artifact |
| BSR-EO-06 | ratified | SERVES_PART | 10/20 | names ONE of two pages: the III Constantinople definition (npnf214.xiii.x.html, 10 of 20 chunks) is not in canonical_url |
| BSR-LU-01 | ratified | SERVES_PART | 2/738 | entry page — Augsburg Art. I page; adapter crawls the whole site from its home page (134 URLs) |
| BSR-LU-02 | ratified | WRAPPER_NO_TEXT | 0/51 | **WRAPPER** — document-library viewer (React shell, 0 characters of text); Draft3r4 moves it to the Download href |
| BSR-LU-03 | ratified | SERVES_ARTIFACT | 1/1 | serves the artifact |
| BSR-LU-04 | RETIRED | NO_TEXT_TO_TEST | 0/0 | RETIRED row — same-host redirect onto an FAQ landing page ("ELCA Worship Information & FAQs") |
| BSR-RP-01 | ratified | SERVES_ARTIFACT | 170/171 | serves the artifact |
| BSR-RP-02 | ratified | SERVES_ARTIFACT | 107/107 | serves the artifact |
| BSR-RP-03 | ratified | SERVES_ARTIFACT | 196/196 | serves the artifact |
| BSR-RP-04 | ratified | SERVES_ARTIFACT | 667/1018 | serves the artifact |
| BSR-RP-05 | ratified | SERVES_ARTIFACT | 69/128 | serves the artifact |
| BSR-RP-06 | ratified | SERVES_ARTIFACT | 35/37 | serves the artifact |
| BSR-AN-01 | ratified | SERVES_ARTIFACT | 39/39 | serves the artifact |
| BSR-AN-02 | ratified | SERVES_ARTIFACT | 24/25 | serves the artifact |
| BSR-AN-03 | ratified | SERVES_ARTIFACT | 1/1 | serves the artifact |
| BSR-AN-04 | ratified | SERVES_ARTIFACT | 117/124 | serves the artifact |
| BSR-AN-05 | ratified | SERVES_ARTIFACT | 322/368 | serves the artifact |
| BSR-BA-01 | ratified | SERVES_ARTIFACT | 21/21 | serves the artifact |
| BSR-BA-02 | ratified | SERVES_ARTIFACT | 3/3 | serves the artifact only through the apex→www 301; Draft3r4 names the www URL |
| BSR-BA-03 | ratified | SERVES_ARTIFACT | 10/10 | serves the artifact |
| BSR-MW-01 | ratified | SERVES_ARTIFACT | 25/25 | serves the artifact |
| BSR-MW-02 | ratified | SERVES_ARTIFACT | 16/16 | serves the artifact |
| BSR-MW-03 | ratified | SERVES_ARTIFACT | 43/43 | serves the artifact |
| BSR-MW-04 | ratified | SERVES_ARTIFACT | 22/22 | serves the artifact |
| BSR-MA-01 | ratified | SERVES_PART | 1/23 | entry page — Article 1 of 24 article pages |
| BSR-MA-02 | ratified | SERVES_ARTIFACT | 18/18 | serves the artifact |
| BSR-MA-03 | RETIRED | NO_TEXT_TO_TEST | 0/0 | RETIRED row — the page carries the confession (14k chars); no corpus to test |
| BSR-EO-07 | ratified | SERVES_ARTIFACT | 25/25 | serves the artifact |
| BSR-EO-08 | ratified | SERVES_ARTIFACT | 12/16 | serves the artifact |
| BSR-EO-09 | ratified | SERVES_ARTIFACT | 5/6 | serves the artifact |
| BSR-EO-10 | ratified | SERVES_PART | 24/45 | names ONE of two pages: the Encyclical (holycouncil.org/encyclical-holy-council, 21 of 45 chunks) is not in canonical_url |
| BSR-EO-11 | ratified | SERVES_ARTIFACT | 2/2 | serves the artifact |
| BSR-EO-12 | ratified | SERVES_ARTIFACT | 12/12 | serves the artifact |
| BSR-EO-13 | ratified | SERVES_ARTIFACT | 7/10 | serves the artifact |
| BSR-EO-14 | ratified | SERVES_ARTIFACT | 19/19 | serves the artifact |

**Rows whose canonical_url is not the served artifact:**
- **Wrapper:** BSR-LU-02 (viewer) — the only one; Draft3r4 fixes it.
- **Not a URL:** BSR-RC-07 (bare "vatican.va"; the corpus comes from the Compendium page the field never names) and BSR-RC-05
  (bare "sourcebooks.web.fordham.edu"; LINEAGE, no corpus).
- **Landing page:** BSR-LU-04 (RETIRED row; now redirects onto an FAQ page).
- **Not a wrapper but not the whole artifact either** (flagged, not defects under the rule's letter): entry pages of multi-page
  artifacts — BSR-RC-01, BSR-LU-01, BSR-EO-01, BSR-EO-02, BSR-MA-01; and two rows that name one of their two pages —
  **BSR-EO-06** (the III Constantinople definition page) and **BSR-EO-10** (the Encyclical page).
- **Eastern Orthodox, all fourteen:** no wrapper, no viewer, no search result. EO-03 not requested (retired). EO-01, EO-02 entry
  pages; EO-06, EO-10 half-named; the other nine serve the artifact.

No row was changed beyond BSR-BA-02 and BSR-LU-02.

## Task 4 — REVIEWED with a row that supplied no text

**4a** (`packets.no_text_rows`, `packets.empty_result_option`; tests in `test_session5_repairs.py`). Read from each **cell's own
record**, never from today's chunk store: a citable ratified row the cell's coverage has no entry for — the locator recorded
`NO_CORPUS`, or the row was not in the branch when the cell ran — goes onto the card as `status: NO TEXT` with its reason, and
blocks REVIEWED exactly as a sampled row does. A fallback-only row counts only on an empty card or where pass two ran. A card
that consulted nothing offers nothing. This matters because building BA-02's corpus afterwards made the old store-based header
read "3 of 3 rows" for cells that never saw BA-02; the header now says so (`branch_ran_on` "… BUT the cells did not all run on
them", `cells_ran_on`, `rows_no_text_on_cards`).

**4b — rebuild of all seven packets, before Task 5** (no model calls; nothing else on any card moved — verified card by card):

| branch | **empty cells** losing the REVIEWED offer | cards of any kind losing `offered: true` | NO TEXT rows on cards |
|---|---|---|---|
| Baptist | **22** (all 22 empties) | 37 | BSR-BA-02 on 37 of 37 |
| Lutheran | **3** (Q-323, Q-403, Q-451; Q-147 already refused) | 5 | BSR-LU-02 on 39 of 39 |
| Roman Catholic | 0 (no empties) | 0 | BSR-RC-05 **and BSR-RC-08** on 34 of 34 |
| Anglican / Reformed / Methodist / Mennonite | 0 | 0 | none |

The expectation "Baptist 22, Lutheran 5" mixes two units: 22 is empty cells, 5 is cards (2 of Lutheran's 5 were filled cards).
New: the Roman Catholic branch ran before BSR-RC-08 was ratified, so no RC cell ever consulted it — invisible until now because
RC has no empties.

**Consequence for Eastern Orthodox:** BSR-EO-03 (goarch.org, HOST_RETIRED) is a citable ratified row with no text, so under 4a it
will block REVIEWED on **every** EO cell unless the author retires it before launch. BSR-RC-05 does the same on Roman Catholic.

## Task 5 — supplementary single-standard passes

`scripts/sjn_recovery/supplement.py --prepare` re-opens pass 1 on each DONE cell by removing only that row's `NO_CORPUS` entry and
snapshots the card; the ordinary loop then issued exactly one locator call per cell for that standard (dry-run counted before any
executor ran: 37 × BSR-BA-02, 39 × BSR-LU-02, nothing else). Verifier gate6-v1.2, the lower floor, opus on reject-all/slice only,
the 2c sample, exhaustion on. Two merge rules were needed so a pass never loses verified evidence, both no-ops on a normal run
(all seven packets rebuilt unchanged after adding them): a re-locate never un-slots an already-verified candidate
(`agents.locate`), and survivors are the union of every pass that ran (`agents.all_survivors`), so earlier exhaustion finds stay in
the running. **5c:** the slot allocation was re-run over all survivors in the cell runner and again in the packet builder.

**5a Baptist / BSR-BA-02 — 1.81 USD** (`live-1/supplement-baptist-BSR-BA-02.json`)
- **Empty → filled: 18** (Q-086, Q-102, Q-118, Q-134, Q-150, Q-158, Q-238, Q-286, Q-294, Q-302, Q-318, Q-326, Q-350, Q-358,
  Q-374, Q-382, Q-390, Q-454). **Still empty: 4** (Q-254 Light, Q-262 Image of the Father, Q-406 No adequate likeness, Q-422
  Without change), all now honestly offering REVIEWED. 15 → **33 filled**; 45 BA-02 candidates verified, 41 accepted.
- **Leads changed: 0.** **Lost a slot: 2** — Q-126 and Q-198 each lost BA-01's third candidate to a first Reformed Baptist slot.
- **Slots by speaks_for:** before SBC 19 / ABC-USA 1 → after **SBC 17 / Reformed Baptist 41 / ABC-USA 1.**
- For the author: three apophatic cells Cowork expected to stay empty filled as **caveated PARTIAL accepts** on "whose essence
  cannot be comprehended by any but Himself" / "incomprehensible" — Q-382 Ineffable, Q-390 Inscrutable, Q-454 Greater
  dissimilarity. The verifier's own floor notes call each "narrower". These are the same class of fill Mennonite made; review them
  before ratifying Baptist.

**5b Lutheran / BSR-LU-02 — 6.62 USD** (`live-1/supplement-lutheran-BSR-LU-02.json`)
- **Empty → filled: 0.** Still empty: Q-147, Q-323, Q-403, Q-451 (all now REVIEWED — LU-02 read whole or exhausted on each).
- **Leads changed: 2** — Q-187 Governor/Ruler (LU-03 → LU-02) and Q-211 Savior (LU-01 → LU-02). **Lost a slot: 9** — Q-123,
  Q-179, Q-195, Q-227 (LU-01's or LU-03's second candidate) and Q-315, Q-411, Q-419, Q-427, Q-435 (LU-01's third).
- **Slots by speaks_for:** before Book of Concord 58 / LCMS 9 → after the pass 50 / 24 → after Task 6 **49 / 24**. LU-02 is on
  14 cards; 31 LU-02 candidates verified, 18 accepted.
- **Defect for the author to rule on:** on **Q-179, Q-227 and Q-235** the card now shows **the same Augsburg sentence twice**
  (bookofconcord.org and lcms.org), and on Q-315 nearly so — the diversity rule gave the LCMS a first slot, which cut a
  *different* Book of Concord passage. The rule was not written for two rows publishing identical text. Proposed guard (not
  implemented): a candidate whose phrase is verbatim a kept candidate's phrase from another row is attached to it as "also published
  by", like the English-witness pairing, and takes no slot.
- **Cost note:** 2.02 USD of the 6.62 was Q-147 reading **LU-01** to the end (27 batches). Q-147 had a survivor when it first ran,
  lost it to the lower-floor rule in session 4, and had never been exhausted; exhaustion covers every sampled standard, so re-entering
  the cell completed it. Result: Q-147 now honestly offers REVIEWED. The pass also questionably accepted "the Maker and Preserver
  of all things" for Q-187 Governor/Ruler (FULL) and Q-195 Sovereign (PARTIAL).

## Task 6 — Q-003 Living (Lutheran)

`scripts/sjn_recovery/reverify.py`: the stored rubrics moved to `superseded_rubrics` (both were pre-v1.2 ACCEPT_WITH_CAVEAT at
PARTIAL), then both models verified the one candidate — Apology XII ¶94–97, "As I live, saith the Lord God" — under gate6-v1.2.
0.13 USD. **The flag decided it; both models raised it on their own, and the floor was the models', not the code cap's.**

**sonnet (gate6-v1.2):** phrase_verbatim Y · subject_is_required Y · grammatical_subject "the Lord God (in the quoted oath: 'the Lord God')" · speech_act_is_assertion Y — "The passage quotes God's oath as authoritative and builds a theological argument on its truth, but the oath formula itself is the vehicle, not a direct assertion of God's intrinsic life." · **floor WORD_ONLY** — "The phrase 'As I live' is a fixed oath formula; the passage's actual assertions concern God's promise, faith, and forgiveness of sins, not God's possession of intrinsic life." · **hazard_flags ['IDIOM_OR_FORMULA']** · asserted_outside_formula **N** · **REJECT / BELOW_FLOOR** — "The oath 'As I live, saith the Lord God' presupposes but does not assert the predicate of Living in its own voice; the surrounding text discusses faith and forgiveness, not God's intrinsic life, so this is WORD_ONLY and must be rejected per the fixed formula rule."

**opus (gate6-v1.2):** phrase_verbatim Y · subject_is_required Y · grammatical_subject "\"I\" (= the Lord God) in \"As I live, saith the Lord God\"" · speech_act_is_assertion Y — "The Apology cites Ezek. 33:11 approvingly via Tertullian and builds its argument on the truth of God's oath, so the citation is endorsed rather than reported as an opponent's view; however, what is asserted is that God swears He does not desire the sinner's death, not that God possesses life intrinsically." · **floor WORD_ONLY** — "The word 'live' occurs only inside the scriptural oath formula 'As I live, saith the Lord God' (and its echo 'Saying, \"I live,\" He desires that He be believed'), which presupposes rather than asserts God's intrinsic life; the passage's actual assertions concern faith, forgiveness, and the reliability of the divine oath." · **hazard_flags ['IDIOM_OR_FORMULA', 'SEMANTIC_FLOOR']** · asserted_outside_formula **N** · **REJECT / BELOW_FLOOR** — "Verbatim phrase and correct subject, but the predicate's word appears solely within an oath formula whose assertoric content is God's unwillingness that the wicked die; nowhere outside the formula does the passage assert that God possesses life intrinsically, so the floor is WORD_ONLY."

**What the cell renders.** Immediately after: EMPTY, "NOT LOCATED — NOT YET RECOVERED", because the new LU-02 corpus was only
sampled on this cell (38 of 51 chunks). The ordinary loop then exhausted LU-02 (one batch, 0.03 USD). **Now: EMPTY, NOT LOCATED —
CURRENT STANDARD REVIEWED** — LU-01 exhausted 738/738, LU-02 exhausted 51/51, LU-03 read whole. (The loop also re-routed the
candidate to PRIMARY_REJECTED_ALL, where opus had already run; the verdict is unchanged.)

**Q-403: closed.** The lower-floor rule rejected its last candidate; it renders NOT LOCATED — CURRENT STANDARD REVIEWED on an
exhausted Book of Concord (now also LU-02 exhausted). Sonnet's floor stood. Recorded as closed in `operational-state.yaml`.

## Task 7 — tp-1, the true-positive fixture

`scripts/sjn_recovery/truepos.py`; `recovery-runs/tp-1/{fixture,tp-results,tp-summary}.json`; 0.79 USD. **Items:** every
author-ratified phrase that names its source — "Citation Phrase Targets" (the released historical citation per family) and "Case
Study Phrase Targets" — kept only when the phrase stands verbatim (the packet builder's own test) in a stored chunk of the row its
URL maps to. 79 → 67 qualify (7 not verbatim in the current corpus, 5 duplicates) → **60** (the 40–60 band; 7 Reformed items
trimmed, Reformed being over-represented). Branches: Reformed 13, Roman Catholic 13, Anglican 9, Methodist 8, Baptist 7,
Mennonite 4, Eastern Orthodox 3, Lutheran 3. Tiers: CONFESSIONAL 50, CATECHETICAL 6, CONCILIAR 4. **Sonnet only**, gate6-v1.2.

| measure | result |
|---|---|
| **recall, overall** | **0.900 (54 of 60)** — ACCEPT 47, ACCEPT_WITH_CAVEAT 7, REJECT 6 |
| recall on cells where IDIOM_OR_FORMULA raises | **undefined — the flag raised on 0 of 60** (including TP-001 "one living and true God") |
| stop rule (below 0.90 stops before Task 8) | **not triggered — at exactly 0.900, with zero margin** |

**Ratified accepts the current verifier refuses (6):**

| item | branch | predicate | phrase | verifier |
|---|---|---|---|---|
| TP-006 | Reformed (BSR-RP-04, Nicene Creed) | Lord | "one Lord, Jesus Christ" | WORD_ONLY · WRONG_SUBJECT |
| TP-018 | Roman Catholic (BSR-RC-06, Nicene Creed) | Life-giving | "the Lord, the giver of life" | WORD_ONLY · WRONG_SUBJECT |
| TP-023 | Roman Catholic (BSR-RC-06, Apostles' Creed) | Judge | "judge the living and the dead" | PARTIAL · WRONG_SUBJECT |
| TP-024 | Methodist (BSR-MW-02, Art. II) | Savior | "eternal Savior and Mediator" | WORD_ONLY · WRONG_SUBJECT |
| TP-033 | Roman Catholic (BSR-RC-06, Nicene Creed) | Not made | "begotten, not made" | PARTIAL · WRONG_SUBJECT |
| TP-060 | Eastern Orthodox (BSR-EO-01) | Unbegotten | "God is an eternal Father by nature" | WORD_ONLY · BELOW_FLOOR |

**None of the six is the lower-floor rule or the formula flag.** Five are WRONG_SUBJECT, and they share one cause:
`registry.subject_scope()` derives `required_subject` from the family definition's wording and defaults to "GOD (the one God, or
the Father …)" for Lord, Life-giving, Judge, Savior and Not made — but the author's ratified citations predicate these of the Son
or the Spirit. The same heuristic stands behind **49 WRONG_SUBJECT rejections** in those five families across the seven packets
(no card emptied by it). This is a doctrinal ruling (which subject each family requires), not a code fix I may make. Under 2a
sonnet's floor is the ceiling, so 0.900 is the upper bound of the routed recall.

## Task 8 — harness

**8c — the Methodist / Wesleyan exit 1, on the record.** Two separate failures:
1. *The crash.* Round 2 of `run.py`, after the executor had answered all 148 locator calls: `agents.py` line 276,
   `locate_standard`, `parsed.get("result", "").startswith("NOT LOCATED")` → `AttributeError: 'NoneType' object has no attribute
   'startswith'`. One locator reply carried an explicit `"result": null` beside its candidates; `.get` with a default returns the
   `None`, not the default. Fixed in session 4 (`str(parsed.get("result") or "")`) and resumed from stored answers at no repeated cost.
2. *Why the launcher said rc=0.* From the session-4 transcript, the launcher was a shell loop — `branch_loop.py … 2>&1 | grep -E
   "…"; echo "=== $br done rc=$? …"` — so `$?` was **grep's** exit status, and nothing broke the loop. `branch_loop.py` itself did
   return 1.

**8a** `scripts/sjn_recovery/launch_branches.py`: reads each `branch_loop.py` exit code from the child process, never through a
pipe; a non-zero exit prints `!! LAUNCH FAILED`, starts no further branch and exits with that code. Exit 0 is not taken on trust:
the packet must be newer than the launch, `partial: false`, `cells_not_finished: 0`, every card finished — otherwise exit 4.

**8b** A branch that ends non-zero leaves a `partial: true` packet whose `cap_state` carries `stopped_by: RUN_FAILED`, the exit code,
the reason, `cells_done`; cards say "branch stopped by a run failure (exit N)"; cost-state marks the branch `RUN_FAILED`. `run.py`
writes it itself when a cell crashes (then re-raises); `branch_loop.py` covers every other failure path (`--write-partial-packet`);
if the packet builder cannot read the states either, a minimal failure record with `partial: true` replaces the packet.

**Tested without spending** on a scratch copy of the Baptist cells, packets redirected by `SJN_PACKETS_DIR`
(`session5/task8-harness-tests/scenario{1..4}.out`): (1) executor fatal → launcher exit 1, Methodist not started; (2) unreadable
cell state → exit 1, minimal failure record, `partial: true`; (3) a crash the builder can read → exit 1, full PARTIAL packet (33
filled, 1 NOT_FINISHED card), `cap_state` populated, `verify_packet` refuses it; (4) clean run → exit 0, packet verified. The
scratch run was deleted.

## Task 9 — review-support extracts

`scripts/sjn_recovery/extract.py`, called by `packets.build_branch_packet` on every packet write from now on:
`recovery-packets/extracts/<branch>-extract.json`, all seven written (53–126 KB against 0.6–1.4 MB packets; totals indented, one
compact line per cell). Fields exactly as specified, plus `verification_slot`, `role`, `slots_by_speaks_for`,
`leads_by_registry_id`, `rows_on_unratified_url`. No chunk text, no rubric narrative.

---

## Spend against the 25 USD cap (metered, audit log; reconciles with cost-state)

| task | calls | USD |
|---|---|---|
| 1–4, 8, 9 | 0 model calls (fetches only) | 0.00 |
| 5a Baptist / BSR-BA-02 | 130 | **1.81** |
| 5b Lutheran / BSR-LU-02 (incl. 2.02 for Q-147's first LU-01 exhaustion) | 118 | **6.62** |
| 6 Q-003 re-verification (0.13) + the LU-02 exhaustion batch it left (0.03) | 3 | **0.17** |
| 7 tp-1 (60 × sonnet) | 60 | **0.79** |
| **session** | **311** | **9.38** |

## Where the Cowork review is wrong (with the artifact)

1. **"Code's narrative report for this session was not on disk … not in the project docs."** It was:
   `docs/gate6/WoP_SJN_Gate6_Session4_Report_20260913.md`, committed in `5969e6e`.
2. **§4 floor disagreements "9 candidates … Anglican 4, Lutheran 4, Reformed 1; Baptist 4, Methodist/Wesleyan 2, Mennonite 1."**
   The breakdown sums to 16, not 9, and the stored-branch figures are wrong: the packets at `5969e6e` hold Anglican 8, Lutheran 6,
   Reformed 8 (22, matching the session-4 report's 13 + 3 + 6). Baptist 4, Methodist 2, Mennonite 1 are right.
3. **§7 "Lutheran: 5 empty cards omit BSR-LU-02."** Lutheran had 4 empty cards; all 39 cards omitted LU-02; 5 cards offered REVIEWED,
   of which 3 were empty (Task 4b).
4. **§1 "The remaining nine are apophatic … would be honest empties."** Of Baptist's 22 empties, 18 filled; Ineffable, Inscrutable and
   Greater dissimilarity filled (as caveated PARTIAL accepts — review them), and **Q-422 Without change**, on Cowork's verbatim
   list, stayed empty: it is the Chalcedonian delimiter on Christ's two natures, and chapter 2's "immutable" is said of God.
5. **§1 "The bare-domain URL in the registry fails outright."** Through Code's fetcher it answers 301 to the same path on www;
   the old strict rule refused the hop. Harmless difference in instrument, but "fails outright" is not what the host does.
6. **§2 "HTTP 200 … no viewer."** True of the bytes, but the Download href is a same-host 302 onto `/api/download/file/…`, served
   as `application/octet-stream` — which a plain fetcher mistakes for text (the defect fixed in Task 2a).
7. **§8 "the failure was caught by a person, not by the harness."** It was caught by Code in-session from the loop log and reported
   in the session-4 report ("stopped after its first executor round on a latent harness defect"). The substance stands: the launcher
   did not catch it.

## Open for the author

1. Ratify the two Draft3r4 URL changes (Tasks 1b, 2b) — and `/dl/f/` vs `/api/download/file/` for LU-02.
2. **Same-text guard** for rows publishing identical wording (Lutheran Q-179, Q-227, Q-235).
3. **`required_subject`** for Lord, Life-giving, Judge, Savior, Not made (tp-1 misses; 49 WRONG_SUBJECT rejections).
4. **Retire BSR-EO-03 before Eastern Orthodox**, or every EO empty will refuse REVIEWED under the NO TEXT rule.
5. Review Baptist's caveated apophatic fills (Q-382, Q-390, Q-454) and Lutheran Q-187 / Q-195 before ratifying those packets.
6. Still open from session 4: whether the reject-all route is exempt from the lower floor; the four derived translation pairs;
   Eastern Orthodox consultation breadth and cap (Code 55–65 USD as-is; Cowork 90–110 USD — the two estimates have not been reconciled).
7. Launch Eastern Orthodox with `launch_branches.py`, alone, on the author's go.
