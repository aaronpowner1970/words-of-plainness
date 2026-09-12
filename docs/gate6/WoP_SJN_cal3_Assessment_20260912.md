# cal-3 assessment — the gate is met, and I am withdrawing the retrieval redesign

**Cowork · 2026-09-12 · read against the full 570-line report, not the summary**

---

## The verdict holds up

| | sonnet | routed | floor |
|---|---|---|---|
| same-standard (gated) | 130/141 = **0.922** | 132/141 = **0.936** | 0.8 |
| tier-respecting | 0.965 | 0.979 | reported |
| same-division | 0.759 | 0.759 | ungated |
| false-accept, 74 planted | **0.000** | **0.000** | ≤ 0.05 |
| Dositheus slice, 23 planted | **0.000** | **0.000** | ≤ 0.05 |

Reformed 37/37, Baptist 16/16, Mennonite 13/13, Anglican 0.92, Lutheran 0.93 routed,
Roman Catholic 0.85, Eastern Orthodox 0.80 — up from 0.50. Nothing was skipped and
no branch reported corpus unavailable. Thresholds were not moved.

This is a real pass, not a marginal one.

---

## I am withdrawing the retrieval redesign. cal-3 shows the money was buying the recall.

I proposed one locator call per cell with reserved per-standard quotas, to cut a
projected $135 live run to $30–45. Section 3 of the report explains why that would
not have been free:

> "The locator is now called once per AUTHOR_RATIFIED standard with that standard's
> own chunks (**whole when they fit 60,000 characters**, else the hybrid ranking
> within that standard)."

The gain did not come from making more calls. It came from each standard being seen
**whole**. The three recovered cells show it: Q-333 recovered with 39 chunks
supplied, Q-331 with 29, Q-339 with 23 — full-document views of a single standard,
not a ranked sample of a pooled branch.

A single pooled call cannot show twelve Orthodox standards whole; no context window
holds them. Quotas would give the locator a *sample* of each standard instead, which
is materially weaker than what produced 0.922. I would have traded roughly twelve
points of recall for about ninety dollars, and I proposed it before I knew what the
money was buying.

**Drop it as a precondition.** Keep it on the shelf as an optimisation to revisit if
a future re-run makes cost the binding constraint — and if it is ever tried, it must
be calibrated before it ships, not after.

---

## Three cells are lost to defects, not to judgment. All three are cheap.

**Q-063 and Q-071 — the fifteen-word rule fired on a sixteen-word phrase.**
Both cite BSR-MW-01, both had the cited division supplied, both produced a candidate,
and both were dropped: *"after re-cut: phrase exceeds 15 words (16)."* The phrase is

> "one living and true God, everlasting, without body or parts, of infinite power,
> wisdom, and good"

A perfectly good shorter cut exists in the same sentence — "one living and true God,
everlasting" is six words. The re-cut step gave up instead of shortening. That is a
bug in the re-cut, not a limit of the rule, and your ≤15-word standard is doing
exactly what it should.

**Q-341 — a hyphenation artifact in the Anglican corpus.** Dropped as *"phrase not
present verbatim in the named chunk,"* and the report's own quotations from that
corpus read **"ever- lasting"** with a broken hyphen. The Thirty-Nine Articles text
carries line-break hyphenation into the chunks, so any phrase containing
"everlasting" fails verbatim matching. This will silently break citations on the
live run too, across every Anglican cell.

All three recover with two small fixes: shorten rather than drop in the re-cut, and
de-hyphenate at extraction. Projected: sonnet 0.943, routed 0.957.

## The rest of the residue is honest

Q-009, Q-042, Q-290, Q-291 are CITED_STANDARD_LOCATOR_EMPTY — the locator found
nothing in the standard the cell cites. Three of the four have verified evidence
elsewhere in the branch and are tier-respecting hits. Q-201 and Q-209 are Roman
Catholic cells where the Creed's clauses about the Son were correctly rejected as
WRONG_SUBJECT. Q-155 and Q-215 are genuine rejections. That is the verifier working.

---

## Cost, measured rather than guessed

cal-3: **1,325 fresh calls, $57.08** — 9.4 calls and $0.405 per cell. Note that 346
further calls were served from cal-2's audit log; a live run has no such cache.

Live run at 315 open cells: **about $138** on v2.25r2, which carries two more Eastern
Orthodox standards and a now-fetchable Methodist row. My original $19–27 was wrong by
roughly six times and I should have re-priced it when I specified per-standard
retrieval.

---

## Recommendation: fix three things, re-validate cheaply, then run branch by branch

1. **Swap v2.25r2.** Q-034 currently fails R001 under v2.25; BSR-EO-13 repairs it.
   BSR-EO-07 yielded nothing in cal-3 because it was still on goarch — ACROD replaces
   it. BSR-MW-03 becomes fetchable. These are corrections the live run should not
   run without.
2. **Fix the re-cut and the hyphenation.** Both reduce false negatives; neither
   loosens the verifier, so neither can manufacture a false accept.
3. **Re-run the planted set only** — 74 near-misses, both models, roughly $5 — to
   confirm false-accept stays 0.000 after the corpus is de-hyphenated. Do not re-run
   the full calibration; the gate is met and the changes are strictly corrective.
4. **Answer the R001 allowlist question before packets are built.** It costs nothing
   and it is the one open item that could invalidate work already done: packets built
   on a wrong allowlist would need re-ratifying cell by cell.
5. **Then the live run, branch by branch, stopping after the first.** Roman Catholic
   first per the spec's run plan. Inspect those packets before spending the rest of
   the $138 — the first branch is the cheapest place to find out that something in
   the packet shape is wrong.

BSR-EO-07's ACROD host is untested in calibration, since cal-3 ran with goarch
blocked. The risk is low — BSR-EO-08, the same genre of source, yielded candidates on
9 cells with 8 accepted — but it is a real gap, and Eastern Orthodox should not be
the first branch in the live run.
