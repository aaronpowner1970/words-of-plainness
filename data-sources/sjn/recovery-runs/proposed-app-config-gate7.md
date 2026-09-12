# APP CONFIG — Gate 6 record for Gate 7

**Status: PROPOSAL ONLY. Nothing here has been written to the workbook.**

Gate 6 produces packets and run logs. The workbook moves in Gate 7, through Cowork's merge script.
This file records the APP CONFIG keys Gate 6 relies on and the registry corrections cal-3 surfaced.

---

## 1. Keys ratified in v2.25 and honoured by cal-3 (read from the workbook, never hard-coded)

| key | value in v2.25 | read by |
|---|---|---|
| `gate6_threshold_metric` | `SAME_STANDARD` | `calibrate.py` — the gate; tier-respecting and same-division reported, ungated |
| `authority_tier_rank` | `CONCILIAR|CONFESSIONAL|CATECHETICAL|OFFICIAL_EXPOSITION|CURRENT_OFFICIAL_WITNESS` | `registry.set_tier_rank`, scoring, packet ordering |
| `reception_scope_vocabulary` | eight values | `Registry.vocabulary_violations` (none in v2.25) |
| `reception_axis` | `ADOPT_BOTH` | `Registry.public` carries reception_scope and reception_note into every packet entry |
| `creed_tier_resolution` | `TIER_PER_CITED_DOCUMENT` | `Registry.effective_tier` — a creed chunk in BSR-RC-06 / BSR-EO-07 resolves CONCILIAR |
| `lateran_iv_scope` | `EXTEND_TO_CONSTITUTION_2` | `sources.lateran_constitutions` — BSR-RC-04 chunks constitutions 1–2; Q-449 in the denominator |
| `verifier_routing` | `SONNET_WITH_OPUS_SLICE` | `agents.CellRunner` — primary on all, adjudicator on the slice |
| `dialogue_text_policy` | `DIALOGUE_ONLY_NEVER_CITED` | `sjn_pipeline.registry.citation_refusal`, R001, `guards.check_citable_row` |
| `encyclical_1848_status` | `RECORD_STANDING_ONLY` | `sjn_pipeline.registry.NON_CITABLE_DOCUMENTS` — refused by name |
| `registry_fallback_only_rows` | `BSR-AN-05` | two-pass admission; always adjudicated |

No new key is proposed by cal-3.

---

## 2. Registry corrections surfaced by cal-3 (author calls)

| row | finding | proposed action |
|---|---|---|
| BSR-BA-02 | The ratified apex URL `https://the1689confession.com/1689/chapter-2` answers 301 → `https://www.the1689confession.com/1689/chapter-2`. cal-1/cal-2 built the row through that redirect; under the strict-host fetcher a live refetch is refused. The cal-3 corpus reuses the cached text (hash unchanged). | Re-point `canonical_url` to the `www` URL the host actually serves, or ratify that apex→www on this host is the same site. |
| BSR-MW-03 | The ratified apex URL answers 301 → `www.globalmethodist.org/what-we-believe`, which 404s, for every user agent and for a rendered browser (2026-09-11). The apex host served no doctrinal text to any route tried; the 12 September verification could not be reproduced. | Re-verify from the author's own browser and, if the apex text is still served there, record the exact request that reaches it; otherwise the row needs an on-domain host or retirement. Corrected sample phrase stands: "of infinite power, wisdom, and good". |
| BSR-EO-07 | Cloudflare managed challenge on the ratified URL from every route tried (five user agents, Playwright headless and headed, the desktop app's own Chromium). Not a crawl: only the ratified URLs were requested. | An archived snapshot committed under `recovery-runs/archived-fetches/BSR-EO-07.html` with provenance would build (adapter supports it); the author decides whether a snapshot taken from a browser session is an acceptable provenance path. |
| BSR-EO-03 | Same block; the authorised one-time archived fetch could not be executed from this machine. | As above. |
| goarch dogmatic-tradition page | Did not render (403 challenge). | Nothing to register. |
| Q-034 | **R001 now FAILS for this cell under v2.25** (Gate 2 pipeline, run with cached fetches on 2026-09-11): it cites `https://www.newadvent.org/fathers/3813.htm`, and newadvent.org was admitted only through the pre-v2.25 BSR-EO-06 row text ("oca.org as cited; newadvent.org (1 released cell)"). BSR-EO-06 now names ccel.org, so no Eastern Orthodox row admits newadvent. The site's emitted JSON is untouched (the pipeline was run to a scratch directory), but `npm run sjn:pipeline` against v2.25 will block until this is resolved. | Re-point Q-034 to the BSR-EO-06 Constantinople III definition page on ccel.org (and re-cut its phrase from Percival), or add newadvent.org back as a lineage host on the row. Gate 7. |
| Q-434 | PHRASE_REQUIRES_RECUT: "unconfusedly, immutably, indivisibly, inseparably" (BSR-EO-06, Percival) or "inconfusedly, unchangeably, indivisibly, inseparably" (BSR-EO-11, witness). | Author chooses the wording in Gate 7. |

---

## 3. Author calls still open from cal-2

| id | row | matter |
|---|---|---|
| AC-02 | BSR-RC-03 | `canonical_url` is still `ewtn.com`; reception TRANSLATION_WITNESS. MIGRATE_WHERE_OFFICIAL is a Gate 7 action. |
| AC-03 | BSR-EO-04 | `CATECHETICAL (historic)`; caveat travels with every packet entry; always adjudicated. |
| AC-05 / AC-12 | BSR-EO-05 | reception CONTESTED; the reception note records both jurisdictions' positions; always adjudicated. |
| AC-08 | BSR-LU-02 | Adoption URL only, no text corpus. |
