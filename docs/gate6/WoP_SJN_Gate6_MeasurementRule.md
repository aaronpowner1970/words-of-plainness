# SJN Gate 6 — the verifier measurement rule (standing, R6-13; amended R6-20)

Ruled by the author on 16 September 2026 (R6-13), and amended the same day (R6-20, third set, applied from session 9). It applies to **every** measurement that decides whether a verifier
prompt version goes into force, from session 8 on. Later measurement prompts should cite this file, not restate it.

## The rule

1. **Run each measured set once per version** — the baseline version and the candidate version.
2. **Any item whose verdict differs** between the baseline and the candidate gets **3 replicates under each version**.
   "Differs" means accept (ACCEPT or ACCEPT_WITH_CAVEAT) against REJECT. A move between ACCEPT and ACCEPT_WITH_CAVEAT
   is not a difference for this rule.
3. **The gate reads the replicate majority** (2 of 3) for those items. Items that did not differ are read from the single
   runs, which agree.
4. An item the author names (for session 8, **Q-160**) is replicated 3 times under both versions **whatever the single
   runs show**.
5. **R6-20 — a STOP item gets 5.** Any item that triggers a STOP condition gets **5 replicates per version** before the
   stop holds, and the stop reads the **majority of those 5** (3 of 5). Items that only differ stay at 3 (rule 2). Where a
   prompt names the stop item's replicate count under the candidate version (session 9: Q-160, 5 under v1.6), those are
   run whatever the single run shows; the baseline is brought up to 5 **only if** the candidate majority would trigger
   the stop, because only then must the stop "hold".

## How it is applied in the harness

- The replicates are fresh calls under their own run ids (`s<N>-rep-<version>-<n>`). The call cache is per run id, so a
  replicate is never served from the single run's answer.
- Replicates already on record under the same version and the same prompt text may be reused — session 8 reused session
  7's three gate6-v1.3 replicates of TP-049 and TP-050 — and the artifact must say which ones were reused.
- A scoped version (gate6-v1.5 onward) records the variant sent on every call: `gate6-v1.5/spirit` or `gate6-v1.5/base`.
- The reference implementation is `data-sources/sjn/recovery-runs/session9/measure_v16.py` (R6-20 included; session 8's
  `session8/measure_v15.py` is the R6-13-only version); its artifact `measure-v16.json` carries the replicate table, every
  check, and the gate decision.
- A check the ruling defines on a fixture that could not be built is **not evaluable**, and a version is not put in force
  on a check that was not run (session 9: check 1 was ruled on tp-5, which R6-17's condition did not allow).
- The measurement script never changes `PROMPT_VERSIONS`. Putting a version in force is a separate, reviewed edit made
  only when every check passes.

## What the rule does not do

Three (or five) replicates are a **decision rule, not a significance test**. A 1/3 against 3/3 split (Q-160, session 8) settles the
gate but does not establish a cause: under a two-sided Fisher exact test that split has p = 0.4. Where the cause matters to
a ruling, say so in the report and do not present a majority as a diagnosis.

## Record

| session | baseline | candidate | replicated items | outcome |
|---|---|---|---|---|
| 7 | gate6-v1.3 | gate6-v1.4 | TP-049, TP-050 (before the rule; 3 per version) | v1.4 failed; never in force |
| 8 | gate6-v1.3 | gate6-v1.5 | TP-049, Q-160, Q-161, Q-213 | v1.5 failed checks 1, 3 and 5; Q-160 implicates the creed carve-out; v1.3 stays in force |
| 9 | gate6-v1.3 | gate6-v1.6 | Q-160 (5, R6-20), TP-045, Q-161, Q-213 (3) | checks 2–5 passed (Q-160 0/5 accept under v1.6); check 1 not evaluable (no tp-5; tp-4 majority-read 58/60); v1.3 stays in force |
