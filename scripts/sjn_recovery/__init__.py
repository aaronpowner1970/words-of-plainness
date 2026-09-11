"""Seeking Jesus of Nazareth — Gate 6 Evidence Recovery Agent Team.

Spec: docs/gate6/WoP_SJN_Gate6_BuildSpec_20260911.md. Produces recovery packets only;
never writes to the workbook.

Modules
  config.py      paths, constants, model aliases
  registry.py    ratified Branch Source Registry rows + per-row fetch plans
  textutil.py    segmentation, mojibake/footnote repair, normalization wrappers
  sources.py     deterministic per-standard fetch + split adapters (document's own divisions)
  provenance.py  one-off Dositheus provenance diff against the Robertson 1899 edition
  store.py       chunk JSON store, corpus manifest (text_hash drift), ChromaDB `sjn_confessions`
  corpus.py      CLI: build / verify the corpus
  retrieval.py   chunk selection per cell (whole standard when it fits, else hybrid top-k per standard)
  prompts.py     locator / verifier / coder prompts and output contracts
  llm.py         model call backends + audit log (model, prompt hash, input hash, output, cost)
  api_executor.py concurrent Anthropic-API executor for pending batch jobs, with a hard cost cap
  guards.py      code-enforced guards (registry-only, phrase assertion, length, branch, duplicates)
  agents.py      locate / verify / code with the fallback-tier two-pass rule
  packets.py     recovery-packets/<branch>.json builder (re-asserts every phrase; drops failures)
  calibrate.py   calibration harness over the released cells + planted near-misses; report
  run.py         live run driver (built in Gate 6; not executed until the author decides)
"""
