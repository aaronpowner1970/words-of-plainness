# R001's effective allowlist may never have matched the ratified registry

**Cowork · 2026-09-12 · found while repairing Q-034 · needs Code to confirm its parser rule**

---

## What Q-034 exposed

Code reported Q-034 failing R001 because its newadvent.org citation "was only
admitted under the old EO-06 wording." That sentence is the finding. It means
**R001's allowlist is built by extracting every domain-shaped token from the
`canonical_url` field, including tokens sitting in prose** — because the old
wording was:

    oca.org as cited; newadvent.org (1 released cell)

The merge script's own `domain_of()` takes only the FIRST hostname, so the
workbook's `publisher_domain` column for that row read `oca.org`. R001 admitted
newadvent.org anyway. The two have therefore disagreed since the registry was
built.

## Seven other rows are affected, and three of them are inverted

Applying an all-tokens parse to v2.25:

| row | publisher_domain column | R001 would also admit | the prose it comes from |
|---|---|---|---|
| BSR-RC-04 | papalencyclicals.net | **vatican.va** | "(not on vatican.va)" |
| BSR-AN-04 | episcopalchurch.org | **bcponline.org** | "bcponline.org is a third-party convenience copy for reading only" |
| BSR-MA-02 | anabaptistresources.org | **gameo.org** | "gameo.org returns 403" |
| BSR-LU-02 | files.lcms.org | lcms.org | "Linked from lcms.org/about/beliefs" |
| BSR-AN-03 | ccel.org | churchofengland.org | the migration target named in the note |
| BSR-BA-02 | the1689confession.com | founders.org | "Index at founders.org/..." |
| BSR-MA-01 | mennoniteusa.org | mennonitechurch.ca | "mirror available" |

The first three are the serious ones: **the prose that disqualifies a host is what
admits it.** "Not on vatican.va" admits vatican.va. A note calling bcponline.org a
convenience copy "for reading only" admits bcponline.org. A note recording that
gameo.org returns 403 — the host AC-07 decided against — admits gameo.org.

That is the registry-only rule inverted by its own parser, on the exact rows where
the author took care to write down why a host was rejected.

## What this does and does not affect

It does **not** invalidate cal-2's or cal-3's recall or false-accept numbers. The
planted near-misses test content judgment, not domain eligibility, so a false accept
on a domain basis would not have been caught by that metric — but neither would it
have inflated it.

It does mean **cal-3's R001 compliance claim cannot be trusted as written**, because
the rule being enforced is not the rule the registry states. Any candidate drawn
from vatican.va, bcponline.org, gameo.org, founders.org, lcms.org,
churchofengland.org or mennonitechurch.ca would have passed a check that should have
refused it. Whether any did is answerable from the run's own audit log, at no cost.

## Two things Code should be asked, when cal-3 reports

1. **State the parser rule** used to build the R001 allowlist from `canonical_url`,
   and dump the effective allowlist per branch. If it is all-tokens, these eight
   rows are the discrepancy list.
2. **Search the cal-3 audit log** for accepted candidates whose domain is not the
   row's `publisher_domain` column value. Report count and cells. No model calls.

## The fix, and why not the quick one

The quick fix for Q-034 is to put `newadvent.org` back into BSR-EO-06's URL field as
prose. That works only because of the defect above, so it is not the fix.

The registry already has the right shape for this: **BSR-RC-05** is a separate
LINEAGE row carrying the Fordham host for Fourth Lateran. Draft3r1 follows it:

- **BSR-EO-06** keeps only its two CCEL URLs, no prose domains.
- **BSR-EO-13** is new — `newadvent.org/fathers/3813.htm`, Third Constantinople,
  CONCILIAR (translation), reception_scope TRANSLATION_WITNESS, LINEAGE, one
  released cell. Its `publisher_domain` names the host explicitly, so R001 admits it
  by design rather than by reading prose.

This restores what R001 admitted before 12 September, in the shape the registry
already uses, and it is defensible under AC-02: migrate where an official host
exists, and none does for the Third Council of Constantinople.

**BSR-EO-13 is a new row and therefore an author call.** It is a repair rather than
an expansion — nothing is added that was not already admitted before Cowork's Draft2
edit — but it should be ratified rather than merged silently.

The durable fix, once the parser rule is confirmed, is to move host prose out of
`canonical_url` into `author_note`, so the field holds URLs and nothing else. That
is a Gate 7 cleanup across eight rows, not something to do mid-run.
