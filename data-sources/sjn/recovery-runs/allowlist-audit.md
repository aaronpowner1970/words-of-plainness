# R001 allowlist audit — Seeking_Jesus_Teaching_Predicate_Source_v2.25r2_CONTROLLED_STORAGE_20260912.xlsx (v2.25r2 CONTROLLED STORAGE) · 2026-09-12T15:12:57Z

No model calls. Nothing here writes to the workbook.

## 1. Parser rule

RETIRED rule (cal-1 … cal-3): allowlist = publisher_domain + the host of canonical_url + EVERY domain-shaped token found by regex in canonical_url and standard_title, prose included (sjn_pipeline.registry.admitted_domains, now legacy_admitted_domains). The merge script's domain_of() takes only the first hostname, so the workbook's publisher_domain column and R001's effective allowlist disagreed on every row whose URL field carried prose. CURRENT rule (2026-09-12, registry.admission): allowlist = publisher_domain ONLY; no host is read from prose. AC-15 exception: a row whose publisher_domain is a controlled-storage host is admitted only when its note opens with `LINKED FROM: <url on the official domain>` and APP CONFIG controlled_storage_policy = ADMIT_IF_LINKED_FROM_OFFICIAL_DOMAIN; that official domain is admitted beside it. Absent the prefix, refused.

APP CONFIG `controlled_storage_policy` = ADMIT_IF_LINKED_FROM_OFFICIAL_DOMAIN.

## 2. Effective allowlist per branch — retired parser vs current rule

### Roman Catholic

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| ewtn.com | BSR-RC-03 | BSR-RC-03 |
| papalencyclicals.net | BSR-RC-04 | BSR-RC-04 |
| sourcebooks.web.fordham.edu | BSR-RC-05 | BSR-RC-05 |
| vatican.va | BSR-RC-01 | BSR-RC-01 |
| vaticannews.va | BSR-RC-06 (lineage) | — |

### Lutheran

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| bookofconcord.org | BSR-LU-01 | BSR-LU-01 |
| catechism.cph.org | BSR-LU-03 | BSR-LU-03 |
| files.lcms.org | BSR-LU-02 | BSR-LU-02 |

### Reformed / Presbyterian

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| crcna.org | BSR-RP-05 | BSR-RP-05 |
| opc.org | BSR-RP-01 | BSR-RP-01 |
| pcusa.org | BSR-RP-04 | BSR-RP-04 |

### Baptist

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| abc-usa.org | BSR-BA-03 | BSR-BA-03 |
| bfm.sbc.net | BSR-BA-01 | BSR-BA-01 |
| the1689confession.com | BSR-BA-02 | BSR-BA-02 |

### Methodist / Wesleyan

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| globalmethodist.org | — | BSR-MW-03 (official_link) |
| irp.cdn-website.com | BSR-MW-03 | BSR-MW-03 (controlled_storage) |
| umc.org | BSR-MW-01 | BSR-MW-01 |
| wesleyan.org | BSR-MW-04 | BSR-MW-04 |

### Anglican

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| anglicanchurch.net | BSR-AN-05 | BSR-AN-05 |
| ccel.org | BSR-AN-03 | BSR-AN-03 |
| churchofengland.org | BSR-AN-01 | BSR-AN-01 |
| episcopalchurch.org | BSR-AN-04 | BSR-AN-04 |

### Mennonite / Anabaptist

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| anabaptistresources.org | BSR-MA-02 | BSR-MA-02 |
| mennoniteusa.org | BSR-MA-01 | BSR-MA-01 |

### Eastern Orthodox

| host | retired parser (all tokens) | current rule (publisher_domain + AC-15) |
|---|---|---|
| acrod.org | BSR-EO-07 | BSR-EO-07 |
| antiochpatriarchate.org | BSR-EO-11 | BSR-EO-11 |
| ccel.org | BSR-EO-06 | BSR-EO-06 |
| goarch.org | BSR-EO-03 | BSR-EO-03 |
| goarchdiocese.ca | BSR-EO-14 | BSR-EO-14 |
| holycouncil.org | BSR-EO-10 | BSR-EO-10 |
| immspartis.gr | BSR-EO-12 | BSR-EO-12 |
| maximologia.org | BSR-EO-05 | BSR-EO-05 |
| newadvent.org | BSR-EO-13 | BSR-EO-13 |
| oca.org | BSR-EO-01 | BSR-EO-01 |
| pravoslavieto.com | BSR-EO-04 | BSR-EO-04 |
| roea.org | BSR-EO-08 | BSR-EO-08 |

## 3. Rows where the two rules disagree

| row | branch | publisher_domain | host the retired parser also admitted | the prose that admitted it | inverted (prose disqualifies the host) | still admitted for the branch via another row |
|---|---|---|---|---|---|---|
| BSR-RC-06 | Roman Catholic | vatican.va | **vaticannews.va** | standard_title: “…ostles', Nicene, Athanasian) on vatican.va / vaticannews.va…” | no | no |
| BSR-AN-03 | Anglican | ccel.org | **churchofengland.org** | canonical_url: “…el.org as cited (1 released cell); official: churchofengland.org BCP "At Morning Prayer"…” | no | yes |

AC-15 admissions under the current rule: BSR-MW-03 → globalmethodist.org (AC-15: irp.cdn-website.com admitted as the body's own storage, linked from globalmethodist.org).

Rows REFUSED under the current rule: none.

Rows whose canonical_url host is not their publisher_domain: none.

## 4. Sweep of cal-3 — accepted candidates whose chunk host is not the row's publisher_domain

Chunk store: manifest built 2026-09-12T02:44:52Z from Seeking_Jesus_Teaching_Predicate_Source_v2.25_RECEPTION_AXIS_20260912.xlsx. Cells scanned 148; candidates with a final ACCEPT/ACCEPT_WITH_CAVEAT 671; **off publisher_domain: 4** (cells: Q-037, Q-293, Q-309); primary-accepted but finally rejected and off-domain: 0; chunk not found: 0.

| cell | candidate | row | locator | chunk host | publisher_domain | final |
|---|---|---|---|---|---|---|
| Q-037 | Q-037-p1-BSR-AN-03-1 | BSR-AN-03 | Quicunque Vult (Creed of S. Athanasius), At Mornin | churchofengland.org | ccel.org | ACCEPT |
| Q-037 | Q-037-p1-BSR-AN-03-2 | BSR-AN-03 | Quicunque Vult (Creed of S. Athanasius), At Mornin | churchofengland.org | ccel.org | ACCEPT |
| Q-293 | Q-293-p1-BSR-AN-03-1 | BSR-AN-03 | Quicunque Vult (Creed of S. Athanasius), At Mornin | churchofengland.org | ccel.org | ACCEPT_WITH_CAVEAT |
| Q-309 | Q-309-p1-BSR-AN-03-1 | BSR-AN-03 | Quicunque Vult (Creed of S. Athanasius), At Mornin | churchofengland.org | ccel.org | ACCEPT_WITH_CAVEAT |

Registry rows whose corpus was fetched from a host outside their publisher_domain (manifest fetch log): BSR-AN-03 (ccel.org; fetched churchofengland.org; 1 chunks); BSR-MW-03 (irp.cdn-website.com; fetched globalmethodist.org; 0 chunks); BSR-EO-07 (acrod.org; fetched goarch.org; 0 chunks).

## 5. Gate 2 R001 over the queue — admission flips between the two rules

322 citation URLs checked (non-retired rows with a URL). Flips: 1; refused under the current rule: 1; newly admitted: 0.

| cell | branch | state | url | retired parser | current rule |
|---|---|---|---|---|---|
| Q-169 | Roman Catholic | Q | https://www.vaticannews.va/en/prayers/the-apostles_-creed.html | lineage:BSR-RC-06 | REFUSED |

