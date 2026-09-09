"""Seeking Jesus of Nazareth — Gate 2 data pipeline package.

Entry point: scripts/sjn-build-data.py (thin CLI wrapper).
Modules:
  workbook.py   — openpyxl loading, table readers, mini formula evaluator, canonical hash
  textnorm.py   — normalization (NFKC/casefold/quotes/dashes/whitespace) + PDF repairs
  fetch.py      — HTTP (requests + retry/backoff/robots), Playwright rendered fetch, PDF, cache
  scope.py      — locator-scoped extraction per source host
  rules.py      — P001–P031 validation rules
  emit.py       — JSON emission (meta, predicates, cells, inferences, godhead, vectors,
                  clarifications, glossary, ranges)
"""
