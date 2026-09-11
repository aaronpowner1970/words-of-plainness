# Proposed APP CONFIG additions for Gate 7

**Status: PROPOSAL ONLY. Nothing here has been written to the workbook.**

Gate 6 produces packets and run logs. The workbook moves in Gate 7, through Cowork's merge script.
This file records the APP CONFIG keys Gate 6 relied on so the author can ratify or reject them
before that merge runs.

---

## 1. `authority_tier_rank`

```
authority_tier_rank = CONCILIAR|CONFESSIONAL|CATECHETICAL|OFFICIAL_EXPOSITION|CURRENT_OFFICIAL_WITNESS
```

**Source of the value.** AUTHOR RATIFIED 2026-09-11 (AJP): `authority_tier` is a genuine authority
rank, descending, in the order above. Gate 6 used it as given. It was not re-derived from the
workbook and no part of it was inferred.

**What reads it.** The calibration harness scores the tier-respecting recall metric with it
(`scripts/sjn_recovery/registry.py`, `TIER_RANK`), and the packet builder orders each cell's
candidates with it, highest tier first (`scripts/sjn_recovery/packets.py`).

**Ranking is on the bare tier.** Three ratified rows carry a parenthetical qualifier. The qualifier
is disclosure for the reader, not a rank modifier, and is stripped before comparison:

| row | `authority_tier` as written | ranks as |
|---|---|---|
| BSR-RC-03 | `CONCILIAR (translation)` | CONCILIAR |
| BSR-EO-04 | `CATECHETICAL (historic)` | CATECHETICAL |
| BSR-BA-02 | `CONFESSIONAL (voluntary church-level subscription)` | CONFESSIONAL |

**Tiers actually present** in the 36 AUTHOR_RATIFIED registry rows: CONFESSIONAL 21, CATECHETICAL 8,
CONCILIAR 5, OFFICIAL_EXPOSITION 2. No row currently carries CURRENT_OFFICIAL_WITNESS; it is kept in
the rank so the ordering is total if a row is added later.

**How the rank is used in scoring.** A verified candidate counts as a hit when it sits in the same
registry standard the released cell cites, **or** in a different ratified standard of the correct
branch whose tier is equal to or higher than the tier of the cited standard. A substitution into a
**lower** tier is a partial: it is reported in its own column and is never credited toward the
threshold.

**How the rank is used in packets.** Candidates are ordered highest tier first. Where a higher tier
wins and a lower-tier standard of the same branch also asserts the predicate and passes the rubric,
**both are kept** — the candidate cap is filled tier by tier, so a second candidate from the winning
tier can never displace the only witness from another tier. The lower-tier entry is marked
`corroborating_lower_tier: true`.

---

## 2. Keys already in the workbook that Gate 6 depends on

Listed for completeness. No change proposed to either.

| key | value used | read by |
|---|---|---|
| `registry_only_enforcement` | on | rule R001, `scripts/sjn_pipeline/rules.py` |
| `registry_fallback_only_rows` | `BSR-AN-05` | two-pass locator admission, `scripts/sjn_recovery/agents.py` |

---

## 3. Author calls still open

These are recorded here because they change what a Gate 7 merge should write. None was decided by
Gate 6.

| id | row | matter |
|---|---|---|
| AC-02 | BSR-RC-03 | `canonical_url` is still `ewtn.com`. MIGRATE_WHERE_OFFICIAL is a Gate 7 action; expected, not a defect. |
| AC-03 | BSR-EO-04 | Philaret's Longer Catechism is `CATECHETICAL (historic)`. The caveat travels with every packet entry that lands on this row. |
| AC-05 | BSR-EO-05 | Confession of Dositheus is `CONFESSIONAL (local synod)`. Same caveat handling. |
| AC-06 | BSR-MW-03 | Ratified domain returns 404. The row is recorded `UNAVAILABLE_ON_RATIFIED_DOMAIN` and contributes no corpus. |
| AC-08 | BSR-LU-02 | Adoption URL only, no text corpus. Recorded `AUTHORITY_URL_ONLY`; needs nothing further as drafted. |
| new | Q-449 | The cited *maior dissimilitudo* text is Lateran IV **canon 2**; BSR-RC-04 ratifies **canon 1** only. Either widen the row's ratified scope to canon 2 or re-point the cell. Excluded from the cal-2 recall denominator as OUT_OF_RATIFIED_SCOPE. |
