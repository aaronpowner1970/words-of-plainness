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

# 3. Calibration (released cells with locators hidden + planted near-misses) — resumable
python scripts/sjn_recovery/calibrate.py run   --run-id cal-1 --locator-model sonnet --verifier-models sonnet,opus
python scripts/sjn_recovery/calibrate.py plant --run-id cal-1 --locator-model sonnet --verifier-models sonnet,opus
python scripts/sjn_recovery/jobs.py status --run-id cal-1
#    ... execute pending jobs (see Backends) and re-run `run` / `plant` until nothing is pending ...
python scripts/sjn_recovery/calibrate.py report --run-id cal-1   # writes recovery-runs/calibration-report.md

# 4. Live run — only after the author has reviewed the calibration report
python scripts/sjn_recovery/run.py --run-id live-1 --all-branches --locator-model sonnet \
       --verifier-models <chosen-verifier> --i-have-author-authorization
```

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
