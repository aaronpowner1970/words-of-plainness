# Christlike Practices app — implementation constraints

- NEVER model a per-user terminal practice completion state. PracticeCycle is
  append-only; unlimited cycles per (user, practice). No unique_together on
  (user, practice). No "integrated," "mastered," "completed," or "70/70" anywhere.
- Preserve stable CDP-### IDs independent of display order and domain assignment.
- Assessment recommends (two domains), never diagnoses or assigns; never required
  before browsing; hidden domain scoring is never exposed during assessment; no
  psychometric-validity claims.
- No streaks, progress bars toward corpus completion, or spiritual scores.
  Descriptive journey language only ("Domains explored: 5 of 8" as description,
  never as a target).
- Discovery routes (Help Me Choose / Domains / Life Situations / Browse All /
  For Today) all converge on the same practice records.
- Practice detail order: What Jesus Did → How We Practice → How It Blesses
  Lives → How Will You Practice? Evidence first, always.
- Forgiveness-of-others practice teaching home is Vol 1 Ch 19; Grace &
  Restoration practices cross-reference it rather than re-teach.
- User state follows the established dual-persistence pattern: localStorage
  (prefix `wop-cdp-`) for guests, wop-api sync + flush-on-login for accounts.
- Scripture links follow existing churchofjesuschrist.org conventions.
- Content YAML is git-owned; no CMS. Textual-critical flags (e.g. John 7:53–8:11,
  Luke 23:34) must survive every transform.
