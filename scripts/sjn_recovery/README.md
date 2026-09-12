# SJN Gate 6 — Evidence Recovery Agent Team (`scripts/sjn_recovery/`)

Spec: `docs/gate6/WoP_SJN_Gate6_BuildSpec_20260911.md`. Reads the workbook; never writes to it.
Gate 6 produces `data-sources/sjn/recovery-packets/<branch>.json` and the run logs under
`data-sources/sjn/recovery-runs/` — nothing else.

## Commands

```bash
# 1. Corpus (deterministic, idempotent; text_hash drift halts; Dositheus provenance diff runs here)
python scripts/sjn_recovery/corpus.py build                # live fetch; ChromaDB sjn_confessions via Ollama nomic-embed-text
python scripts/sjn_recovery/corpus.py build --reuse-cache  # dev: reuse .cache/sjn-recovery/fetch
python scripts/sjn_recovery/corpus.py status

# 2. Planted near-miss fixture (hand-authored items, re-asserted verbatim at build)
python scripts/sjn_recovery/calibration_fixture.py

# 2b. Fetcher audit (every ratified URL requested as written; cross-host redirects recorded, never followed)
python scripts/sjn_recovery/fetch_audit.py                  # writes recovery-runs/fetch-audit.json

# 2c. Guards: the Synodikon anathema guard, polytonic integrity, R001 refusals
python -m pytest scripts/sjn_recovery/tests -q

# 3. Calibration (released cells with locators hidden + planted near-misses) — resumable
#    --seed-from reuses another run's answered calls (identical role/model/prompt-version/text) at no cost
python scripts/sjn_recovery/calibrate.py run   --run-id cal-3 --locator-model sonnet --verifier-models sonnet,opus --seed-from cal-2
python scripts/sjn_recovery/calibrate.py plant --run-id cal-3 --locator-model sonnet --verifier-models sonnet,opus --seed-from cal-2
python scripts/sjn_recovery/jobs.py status --run-id cal-3
#    ... execute pending jobs (see Backends) and re-run `run` / `plant` until nothing is pending ...
python scripts/sjn_recovery/calibrate.py report --run-id cal-3 --compare cal-2   # writes recovery-runs/calibration-report.md

# 2d. R001 allowlist audit (no model calls): parser rule, allowlist per branch, cal-3 sweep, Gate 2 R001 flips
python scripts/sjn_recovery/allowlist_audit.py --run-id cal-3     # writes recovery-runs/allowlist-audit.md

# 4. Live run — only after the author has reviewed the calibration report; ONE BRANCH AT A TIME
python scripts/sjn_recovery/run.py --run-id live-1 --branch "Roman Catholic" --locator-model sonnet \
       --verifier-models sonnet,opus --branch-cost-cap-usd 25 --i-have-author-authorization
python scripts/sjn_recovery/api_executor.py --run-id live-1 --workers 6 --max-cost-usd 25 --key-file <.env>
#    ... loop run.py / api_executor.py until pending 0; the packet is written when every cell of the branch is DONE
```

## Live-run session 1 (2026-09-12, v2.25r2 CONTROLLED STORAGE)

- **R001 parser rule** (`sjn_pipeline/registry.py`, `admission`): a row admits its `publisher_domain` and nothing
  else — no host is read out of `canonical_url`, `standard_title` or a note. The retired all-tokens parser
  (`legacy_admitted_domains`, kept for the audit) had admitted vaticannews.va from BSR-RC-06's title,
  churchofengland.org from BSR-AN-03's URL prose and newadvent.org from BSR-EO-06's v2.25 URL prose.
  **AC-15** (controlled storage): a row whose `publisher_domain` is a storage endpoint (cdn-website.com,
  blob.core.windows.net, …) is admitted only when its note opens with `LINKED FROM: <url on the official
  domain>` and APP CONFIG `controlled_storage_policy = ADMIT_IF_LINKED_FROM_OFFICIAL_DOMAIN`; that official
  domain is admitted beside it. BSR-MW-03 is the live case. `allowlist_audit.py` reports all of this.
- **Host guard** (`sources.Ctx._check_host`): every URL an adapter requests must sit on a host the row admits;
  otherwise the row builds as HOST_NOT_ADMITTED with no corpus. BSR-AN-03 therefore now fetches the ccel.org
  page (APP CONFIG `athanasian_text_witness`), not churchofengland.org.
- **Retired hosts** (`config.RETIRED_HOSTS`): goarch.org is never requested — not by the builder, the fetch
  audit or a crawl. BSR-EO-03 builds as HOST_RETIRED; BSR-EO-07 moved to acrod.org; BSR-EO-14 (goarchdiocese.ca)
  is the independent-infrastructure alternate; BSR-EO-13 (newadvent.org, witness) repairs Q-034; BSR-MW-03 is the
  2024 Book of Doctrines and Discipline PDF ('wisdom, and good').
- **De-hyphenation at extraction** (`textutil.dehyphenate`, `sources.dehyphenate_chunks`, `Ctx.pdf`): a word
  split across a line break is joined for every row, using the standard's own vocabulary as evidence
  (closed form elsewhere → join; hyphenated compound elsewhere → keep the hyphen; suspended hyphens
  "wine- and beer-cellars" left alone). Residues are reported in the manifest notes.
- **Re-cut shortens to fit** (`agents._recut`, recut prompt gate6-v1.3): up to three re-cut calls, feeding back
  the word count and, on the last, the legal ≤15-word spans of the phrase (enumerated in code, chosen by the
  locator). A candidate is dropped only on NO_VALID_CUT or when every attempt is still over 15 words.
- **Per-branch spend** (`run.py --projection-per-cell-usd --branch-cost-cap-usd`): recorded in run.json against
  the cal-3 projection (0.405 USD/cell); `api_executor.py --max-cost-usd` is what enforces the cap.

## Backends (`llm.py`)

| backend | how calls run | cost basis |
|---|---|---|
| `batch` (default) | the harness writes one job file per call under `.cache/sjn-recovery/jobs/<run>/pending/`; an executor writes the raw reply to `done/<call_id>.txt`; re-running the command ingests it | estimated (chars/3.6 at list prices), marked as estimate |
| `anthropic` | Anthropic SDK, needs `ANTHROPIC_API_KEY` | metered tokens |
| `batch` + `api_executor.py` | the harness writes job files as usual; `api_executor.py` answers them through the Anthropic SDK concurrently, with retry/backoff and a hard `--max-cost-usd` stop, and records real usage in `done/<call_id>.json` | metered tokens |
| `claude-cli` | `claude -p` headless (needs `claude login`) | the CLI's own `total_cost_usd` |
| `ollama` | local model | 0 |

The Gate 6 build session began on the subagent route (one isolated Claude Code session per job) because
no API key or CLI login was available. That route costs roughly five times the necessary tokens per call
in session overhead, so calibration was moved onto `api_executor.py` partway through. Both routes write
into the same `done/` exchange and the same audit log, so a run can switch between them freely; records
answered through the API carry real metered usage, records answered by a subagent carry an estimate and
say so in `cost_basis`. Every call is logged to `recovery-runs/<run>/calls.jsonl` with role, model,
prompt hash, input hash, output and cost.

Execute pending jobs through the API with:

```bash
python scripts/sjn_recovery/api_executor.py --run-id cal-1 --workers 6 --max-cost-usd 50 --key-file path/to/.env
```

`temperature` is not sent: it is deprecated on the Claude 5 family.

## cal-3 design (v2.25 RECEPTION AXIS)

- **APP CONFIG is read, not hard-coded** (`registry.py`): `gate6_threshold_metric` (SAME_STANDARD is the gate;
  tier-respecting and same-division are reported, ungated), `authority_tier_rank`, `reception_scope_vocabulary`,
  `creed_tier_resolution` (a creed cited from a lower-tier row resolves to the tier the row note names),
  `lateran_iv_scope` (BSR-RC-04 chunks constitutions 1–2), `verifier_routing`, `dialogue_text_policy`,
  `encyclical_1848_status`, `registry_fallback_only_rows`.
- **Retrieval per standard** (`retrieval.select_for_standard`, `agents.locate`): one locator call per
  AUTHOR_RATIFIED standard with that standard's own chunks (whole if ≤60k chars, else the hybrid ranking within it);
  every standard's best candidate gets a guaranteed verification slot, then `VERIFY_EXTRA_CANDIDATES` more by
  tier and floor. An over-long phrase is re-cut once by the locator (`recut` role), never repaired by code.
- **Routing SONNET_WITH_OPUS_SLICE**: the primary verifies every slotted candidate; the adjudicator verifies
  candidates on the slice rows (BSR-EO-04, BSR-EO-05, BSR-EO-09, fallback-only rows) and every cell the primary
  rejected outright; where it ran, its verdict is final and overturns are recorded per candidate.
- **Synodikon guard** (`sources.synodikon_guard`, tested in `tests/`): anathema-framed spans are withheld from the
  agent-visible text and refused by name at candidate vetting.
- **Witness rows** (TRANSLATION_WITNESS reception, or a tier qualified "witness"): candidates flagged; a cell may
  not rest on them alone (scored and packeted accordingly). **DIALOGUE_ONLY** rows and the **1848 Encyclical**
  are refused by name (`sjn_pipeline/registry.py`, R001 in `rules.py`, `guards.check_citable_row`).
- **Fetcher**: ratified URLs fetched byte for byte; redirects followed one hop at a time and logged; the corpus
  builder refuses a hop onto another host (`Fetcher(strict_host=True)`). goarch.org is never crawled.
- Agent-visible chunk text has URL tokens scrubbed (`textutil.scrub_urls`); the stored text and hash are untouched.

## Guards enforced in code (`guards.py`, `agents.py`, `packets.py`)

Registry-only chunks (URLs never enter a prompt; `assert_no_urls`) · phrase ≤15 words and verbatim in the
named chunk (checked at locator ingest, at verifier ingest, and again at packet build — failures dropped,
never repaired) · rationale/source_note ≤40 words · one branch per call, registry_id must belong to the
cell's branch · identical locator+phrase collapses · fallback-tier rows (APP CONFIG
`registry_fallback_only_rows`) admitted only in pass two and never rendered beside a non-fallback witness ·
verifier verdict recomputed in code from the rubric lines (any N on 1–3 → REJECT; WORD_ONLY → REJECT) ·
every rejection kept with rubric, chunk context and reason code.

## State and outputs

- `data-sources/sjn/recovery-runs/corpus-manifest.json` — per standard: status, URLs fetched, chunk count, `text_hash`, provenance result.
- `data-sources/sjn/recovery-runs/calibration/planted-near-misses.json` — the near-miss fixture.
- `data-sources/sjn/recovery-runs/<run>/cells/<Q-id>.json` — per-cell state (passes, candidates, rubrics, coding).
- `data-sources/sjn/recovery-runs/<run>/calls.jsonl` — audit log.
- `data-sources/sjn/recovery-runs/calibration-report.md` — the committed calibration table by verifier model.
- `data-sources/sjn/recovery-packets/<branch>.json` — Decision Console packets (live run only).
- `.cache/sjn-recovery/` (gitignored) — fetch cache, chunk JSON, job exchange.
