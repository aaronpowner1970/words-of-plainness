# Data Layer — Rules and Traps

Loads when Claude Code works in `src/_data/`. This directory is the site's
structured-data and governance layer. Two things here can silently ship stale
content; both are below.

## operational-state.yaml IS the current-state source of truth
Phase, active workstreams, blockers, pipeline health, milestones, and the
governance-document index all live here. Project-knowledge documents (the February
architecture doc, older handoffs) drift and must not be trusted for current state.

**Anti-drift rule:** when a session changes phase, deployment status, or blockers,
update this file in the same session. A stale state file is worse than none,
because it gets obeyed. `chapter-status.yaml` and `infrastructure.yaml` are the
companion YAML files in the same governance layer.

## apparatusData: .js builder → .json artifact (does NOT auto-regenerate)
`apparatusData.js` is the builder; `apparatusData.json` is the emitted artifact the
site actually reads. **Eleventy does not re-run the builder on every build in a way
that refreshes the committed JSON** — after editing `apparatusData.js` (or the
underlying AoID cluster data it draws from), you must regenerate and commit the
JSON, or the deployed citation apparatus will be stale.

Regenerate with:
```
node -e "const b=require('./src/_data/apparatusData.js');const fs=require('fs');const d=b();fs.writeFileSync('./src/_data/apparatusData.json',JSON.stringify(d,null,2)+'\n');console.log('regen ok',Object.keys(d).length,'articles')"
```
Then commit `apparatusData.json` alongside the source change. Verify the deployed
`/articles/` page after push.

## creation_citations.json is compact single-line JSON
The 135-span creation apparatus (`/creation/`) reads `creation_citations.json`,
which is intentionally stored as compact single-line JSON. Preserve that format on
any edit — don't pretty-print it.

## Unicode discipline (all data files)
Literal Unicode throughout (— – " " ' † ‡ ¶). Never escape to `\u2014` etc. YAML
serialization for apparatus-style data: `allow_unicode=True`, `sort_keys=False`,
`default_flow_style=False`, `width=10**9`. Double-backslash `\\uXXXX` on disk is the
failure mode.

## Other data files (reference)
- `navigation.json`, `site.json` — site chrome and metadata.
- `scriptures.json`, `themes.json`, `chapterThemes.json`, `articleThemes.json` —
  content indexes.
- `timestamps/` — per-chapter audio sync JSON (keyed by `chapterId`).
- `concerts/`, `concertList.js`, `ministryMusic.json` — music/concert data.
