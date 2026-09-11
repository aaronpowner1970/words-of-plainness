# Gate 6 — Evidence Recovery Agent Team: build specification

**Status:** BUILD SPEC · September 11, 2026 · written in Cowork for Claude Code · Author: Aaron J. Powner (AJP)
**Canonical input:** `Seeking_Jesus_Teaching_Predicate_Source_v2.23_REGISTRY_CORRECTIONS_20260910.xlsx`
**Reads against:** `WoP_SJN_ExpansionPlan_Gates5-9_20260910.md` §5 · `WoP_Pattern_SourceHardening_DataDrivenApps_20260907.md` · `WoP_Teaching_Practices_Standard_v1.0.md`
**Predecessor:** Gate 5 closed 2026-09-10 — 36 registry entries author-ratified, 2 retired.

---

## 1. What this gate builds, and what it does not

Gate 6 builds the machinery that proposes evidence for the 315 open cells of the Evidence-First Cell Queue. It does not decide anything. Every candidate it produces is a proposal that the author ratifies card by card in Gate 7.

**In scope:** `scripts/sjn_recovery/` — a deterministic corpus builder, three agent roles, a packet builder, a calibration harness, and a run log. **Out of scope:** any write to the workbook. Gate 6 produces `recovery-packets/<branch>.json` and nothing else. The workbook changes only in Gate 7, through Cowork's merge script.

**The measure of success is not fill rate.** An honest empty result is a first-class outcome and is worth more than a plausible guess. Agents are scored on verified-or-honestly-empty.

---

## 2. First, three corrections to the existing build

**Swap the workbook.** Code is currently building M3/M3a/M4 against v2.20. Put v2.23 into `data-sources/sjn/` and re-run the pipeline. There is no doctrinal, copy, count or gate-value change from v2.20 through v2.23 — the additions are the registry sheet, nine APP CONFIG keys, and the V100 rewrite. Existing assertions should pass unchanged.

**Update V100.** The workbook's rule is now conditional:

```
=IF(COUNTIF('Author Decision Queue'!$AF$2:$AF$105,"YES")>0,1,0)
```

It keys on the queue's *Needs Author Attention* column (AF), not *Actionability* (F, which still reports 101 READY rows even with every decision answered). Code's own V100 implementation, paired with P028, must match — otherwise the workbook reports PASS while the build reports FAIL. With this change Build Validation recalculates with zero FAIL cells, the first fully green validation sheet since v2.15.

**Add rule R001 to `sjn-verify`.** Any cell citation whose domain is not in its branch's `AUTHOR_RATIFIED` registry rows is a blocking error. `registry_only_enforcement = True` in APP CONFIG is the switch; the `publisher_domain` column is the key.

---

## 3. The corpus builder — deterministic, not an agent

`scripts/sjn_recovery/corpus.py`. Reads the Branch Source Registry sheet, fetches each `AUTHOR_RATIFIED` standard once, normalizes it, splits it by the standard's own structure, and stores the chunks in a ChromaDB collection `sjn_confessions` (internal only, never emitted to the site).

**Per chunk:** `registry_id`, `branch`, `locator`, `text`, `text_hash`, `authority_tier`, `scope_caveat`.

**Normalization** reuses `sjn_pipeline/textnorm.py`: NFKC, quote and dash folding, whitespace collapse, and for PDFs the soft-hyphen, ligature and line-break repairs already written.

**Splitting is by the document's own divisions**, never by character count. Articles for the Thirty-Nine Articles and the Articles of Religion; questions for the catechisms; paragraph numbers for the Catechism of the Catholic Church; canons for the conciliar texts; `Decree 1-18` and `Question 1-4` for the Confession of Dositheus; chapters and paragraphs for Westminster and the 1689. The locator a learner eventually sees is this division, so it must be the real one.

**Idempotent.** Re-running against an unchanged source is a no-op. A changed `text_hash` halts the run and reports which standard drifted — it does not silently re-chunk.

**Fetch modes, confirmed by the author (AC-08):**

| Host | Mode |
|---|---|
| churchofengland.org | RENDERED — Playwright; the body is not in plain HTML |
| goarch.org | RENDERED, 403-prone — Playwright with backoff |
| files.lcms.org | Authority/adoption URL only. **No text extraction.** It is a client-side viewer; register the URL, chunk nothing |
| pcusa.org | Large PDF — normalize, then section-split by constituent confession |
| episcopalchurch.org | Large PDF — the catechism only, pp. 845-863 |

---

## 4. The three agent roles

### Locator

**Input:** one open queue row — family, predicate, the semantic-floor definition from the Predicate sheet, the branch — plus that branch's registry chunks. **Never a URL.** The agent sees text, never an address.

**Output:** zero to three candidates, each `{registry_id, locator, phrase, rationale, floor_claim}` where `phrase` is ≤15 words **verbatim** and `floor_claim` is `FULL | PARTIAL | WORD_ONLY`; or `{result: "NOT LOCATED — CURRENT STANDARD REVIEWED", standards_reviewed: [registry_id]}`.

The prompt forbids sources outside the supplied chunks, forbids paraphrase in the phrase field, and states plainly that an empty result is correct when the standard is silent.

### Verifier — different prompt, different model where practical

**Input:** one candidate and the cold-fetched chunk. Not the locator's reasoning.

**Output: the fixed six-line rubric.**

1. Phrase present verbatim — Y/N.
2. Subject is God, or the Son or the Spirit where the family's predicate is so scoped — Y/N, quoting the grammatical subject.
3. Speech act is an assertion by the standard — not a quotation of an opponent, a denial, or a hypothetical — Y/N.
4. Floor met — `FULL | PARTIAL | WORD_ONLY`, with a one-sentence reason.
5. Hazard flags from the ten-type taxonomy — a list, possibly empty.
6. Verdict — `ACCEPT | ACCEPT_WITH_CAVEAT | REJECT`.

Any N on 1–3 is REJECT. `WORD_ONLY` is REJECT unless the family's floor is itself lexical; the Predicate sheet marks those.

### Coder

For `ACCEPT` and `ACCEPT_WITH_CAVEAT` only. Proposes `rendered_state` (A, A-SF, Q or D relative to the family's Restoration comparator), a ≤40-word learner-facing `source_note`, and inherits the registry `scope_caveat` unchanged.

Where the branch's own witness diverges from the family code, it proposes the divergence explicitly rather than forcing the family code — the way Q-290 was handled.

### Packet builder — a script, not an agent

Assembles per-cell cards for the Decision Console: predicate, floor definition, Restoration comparator, up to three surviving candidates each with its verifier rubric shown, the coder's proposal, and the empty-result option always present.

It re-asserts every phrase against the stored chunk and **drops failures before the author ever sees them**.

---

## 5. Guards — enforced in code, never in a prompt

- **Registry-only.** Chunks are the only text an agent receives. URLs are never passed to agents.
- **Phrase assertion.** Re-asserted at packet build; failures are dropped, never repaired.
- **Length.** Phrase ≤15 words after normalization; rationale ≤40 words; `source_note` ≤40 words.
- **No cross-branch leakage.** One branch at a time. An agent cannot reach another branch's registry.
- **Duplicate suppression.** Identical `locator` + `phrase` from two runs collapses to one candidate.
- **Audit.** Every agent call logged with model, prompt hash, input hash, output and cost, committed to `data-sources/sjn/recovery-runs/`.

### The fallback-tier rule — new in Gate 5, and the one most easily missed

`registry_fallback_only_rows = BSR-AN-05` (ACNA, *To Be a Christian*). The author admitted it as a **fallback tier only**, which requires a two-pass locator run per cell rather than one pass over all chunks:

1. **Pass one** — non-fallback rows of the branch only. For Anglican: the Thirty-Nine Articles, the 1662 Catechism, the Athanasian Creed, the Episcopal Church's 1979 Outline of the Faith.
2. **Pass two** — run **only if pass one returned no surviving candidate.** Then, and only then, the fallback row is admitted.

A fallback citation must never render alongside or against a non-fallback witness for the same cell. This exists so that a learner never sees an intra-branch disagreement flattened into one state, and so ACNA fills rows that would otherwise be hatched rather than competing with Canterbury-communion standards. Read the key from APP CONFIG; do not hard-code the registry id.

### The Dositheus provenance check — one-off, at corpus build

`BSR-EO-05` is the Confession of Dositheus on maximologia.org: the unmodified Robertson 1899 translation, but on a site that credits no translator. The author chose disclosure over relocation, after the alternatives were checked and rejected — CRI/Voice is Bratcher's *adaptation* with modernised wording, which fails verbatim assertion; the Robertson scan on archive.org has no decree-level locators and carries Greek OCR noise.

**Add a one-off build-time check:** diff the maximologia text against the Robertson edition at `archive.org/details/actsdecreesofsyn00orth` across a sample of decrees, and halt if they diverge. This is a provenance check, not a per-cell assertion — it runs once at corpus build and converts "we trust an unattributed page" into "we verified it against the published edition."

---

## 6. Calibration — before any live run

Run the locator and verifier against the **141 already-released cells with their locators hidden**.

**Report per branch:** recall of the existing locator, or of an equivalent passage in the same standard; false-accept rate against deliberately planted near-misses (opponent quotations, Christological passages, predicates of the Church rather than of God); and the empty-result rate where the existing cell is already NOT LOCATED — CURRENT STANDARD REVIEWED.

**Thresholds to proceed: recall ≥ 0.8, false-accept ≤ 0.05.** Below either, fix the prompts or the chunking. Do not move the thresholds.

**Break the calibration report out by verifier model.** If more than one model is tried in the verifier role — and it is worth trying more than one, since rubric items 2 and 3 are the hard judgments — report recall, false-accept and the Dositheus slice separately for each, with the model identifier, the call count and the cost per model, and name the model the live run will use. Commit that table as `data-sources/sjn/recovery-runs/calibration-report.md`. The point is that the model choice is documented rather than remembered: Gate 7 and any later re-run need to know what was measured, not what was decided.

**One branch needs its own calibration slice.** The Confession of Dositheus was written against Cyril Lucaris's Calvinizing confession, so its statements about God frequently sit inside condemnations of a contrary position. That lands directly on rubric item 3, and it raises both the REJECT rate and — more dangerously — the false-accept risk, because a denial of an opposed claim can read like an assertion of its opposite. Report Dositheus false-accept separately from the Eastern Orthodox aggregate, and treat the 0.05 ceiling as applying to it individually.

---

## 7. Run plan

Per branch, in this order: **Roman Catholic → Lutheran → Reformed/Presbyterian → Baptist → Methodist/Wesleyan → Anglican → Mennonite/Anabaptist → Eastern Orthodox.** Highest expected yield first, most caveats last.

Roughly 315 open cells × (one locator call + up to three verifier calls + at most one coder call) ≈ 900–1,300 agent calls with short contexts. Two to four Code sessions including calibration.

Expect a large share of honest empties for the short-confession branches. That is the design working, not a failure.

---

## 8. Preserve the rejections

Every surviving candidate is stored with its verifier rubric whether approved or not — the plan already calls for a Recovery Candidates sheet as the audit trail. **Do not discard rejections.**

Beyond the audit, they are a teaching asset. The Teaching Practices Standard requires examples paired with non-examples, and a verifier rejection is a non-example that already carries the reason it fails: a passage that speaks of divine simplicity while quoting an opponent to condemn the view; a use of *creator* that never meets the floor. That corpus is generated here at no extra cost, and a later module draws from it. Keep the rubric, the chunk context and the reason code intact.

---

## 9. Gate 6 exit criteria

- Calibration thresholds met, with Dositheus reported separately.
- `calibration-report.md` committed, broken out by verifier model where more than one was tried, naming the model chosen for the live run.
- Eight branch packets produced at `recovery-packets/<branch>.json`.
- Run logs committed under `data-sources/sjn/recovery-runs/`.
- `sjn-verify` rule R001 live.
- V100 updated to the conditional form and agreeing with the workbook.
- **No workbook change.** The workbook moves in Gate 7.

---

## 10. Standing rules

Workbook canonical; static JSON only; no branch percentages or rankings anywhere public; `full_branch_map_enabled` stays False until the Gate 9 decision; "Latter-day Saint" never "LDS"/"Mormon" in learner-facing text; "Mormon Christianity" as a book subtitle is a term of art; scripture hyperlinked to churchofjesuschrist.org/study; every citation carries a ≤15-word asserted phrase; agents may read only ratified-registry text; empty is a valid result; the author ratifies every cell.

---

## 11. Spin-up prompt for Claude Code

**The prompt ships as its own file: `WoP_SJN_Gate6_LaunchPrompt_20260911.txt`,
beside this spec in `wop-scratch\` and in the project.** Paste it into Claude Code
verbatim. It is the single source of truth for the launch — do not retype it from
this section, and if the launch instructions change, change the .txt.

What the launch prompt adds beyond this specification, and why:

- **Step 0 copies the workbook and both documents into the repo and commits them.**
  `wop-scratch\` sits outside the repo's working directory, so Code cannot reach it
  without prompting; pulling the inputs in first removes that friction and puts the
  spec under version control beside the code it produced.
- **The three session constraints are restated at the top** — no workbook writes,
  stop after calibration, push directly to main. This is a multi-hour build; early
  context gets compacted, and those three are exactly the instructions that vanish
  when it does.
- **It names the repo and branch explicitly**, so the session cannot start in the
  wrong directory.

The technical body of the prompt is this specification, §2 through §8.
