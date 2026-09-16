# SJN Gate 6 — the verifier measurement rule (standing, R6-13)

Ruled by the author on 16 September 2026 (R6-13). It applies to **every** measurement that decides whether a verifier
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

## How it is applied in the harness

- The replicates are fresh calls under their own run ids (`s<N>-rep-<version>-<n>`). The call cache is per run id, so a
  replicate is never served from the single run's answer.
- Replicates already on record under the same version and the same prompt text may be reused — session 8 reused session
  7's three gate6-v1.3 replicates of TP-049 and TP-050 — and the artifact must say which ones were reused.
- A scoped version (gate6-v1.5 onward) records the variant sent on every call: `gate6-v1.5/spirit` or `gate6-v1.5/base`.
- The reference implementation is `data-sources/sjn/recovery-runs/session8/measure_v15.py`; its artifact
  `measure-v15.json` carries the replicate table, the five checks, and the gate decision.
- The measurement script never changes `PROMPT_VERSIONS`. Putting a version in force is a separate, reviewed edit made
  only when every check passes.

## What the rule does not do

Three replicates are a **decision rule, not a significance test**. A 1/3 against 3/3 split (Q-160, session 8) settles the
gate but does not establish a cause: under a two-sided Fisher exact test that split has p = 0.4. Where the cause matters to
a ruling, say so in the report and do not present a majority as a diagnosis.

## Record

| session | baseline | candidate | replicated items | outcome |
|---|---|---|---|---|
| 7 | gate6-v1.3 | gate6-v1.4 | TP-049, TP-050 (before the rule; 3 per version) | v1.4 failed; never in force |
| 8 | gate6-v1.3 | gate6-v1.5 | TP-049, Q-160, Q-161, Q-213 | v1.5 failed checks 1, 3 and 5; Q-160 implicates the creed carve-out; v1.3 stays in force |
