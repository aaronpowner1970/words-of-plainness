# Open Questions and Recommended Next Steps

## Phase 0 — Reconcile with the existing ecosystem

Before implementation:

1. Audit the current Words of Plainness repository architecture.
2. Audit Keep My Commandments architecture and reusable components.
3. Search the 3+ GB development-history RAG for relevant prior decisions.
4. Identify conflicts with this packet.
5. Identify reusable auth, journal, card, content, analytics, accessibility, and deployment infrastructure.
6. Recommend repo/deployment placement.

**Deliverable:** Reconciled architecture memo before code changes.

## Phase 1 — Canonicalize the content model

1. Confirm/refine eight domains.
2. Audit all 70 practices for overlap.
3. Normalize titles/descriptors.
4. Audit Scripture references.
5. Assign evidence strength.
6. Add textual-critical flags.
7. Merge/split/move/remove where justified.
8. Lock stable CDP IDs.
9. Define production editorial fields.

**Deliverable:** `practices.v1.0` registry.

## Phase 2 — Prototype the replay loop

Prototype before full persistence:

1. Home / entry routes
2. Domain chooser
3. Domain detail
4. Practice detail / What Jesus Did
5. How We Practice / How It Blesses Lives / How Will You Practice?
6. Commitment builder
7. Return/reflection flow
8. My Practice Journey

Test mobile first-class.

## Phase 3 — Behavioral assessment

Resolve:

- item count;
- item order/randomization;
- reverse-keyed items;
- handling of NA/unsure;
- scoring/recommendation logic;
- whether prior assessments are retained;
- language avoiding false psychometric authority.

Do not call the assessment validated unless it is actually validated.

## Phase 4 — Life Situation taxonomy

Review the initial registry, reconcile with recurring ministry contexts, consolidate synonyms, curate mappings, and determine manual vs tag-driven generation.

## Phase 5 — Persistence and privacy

Decide:

- one or multiple active cycles;
- autosave;
- journal privacy;
- anonymous vs authenticated use;
- retention/deletion;
- export;
- search;
- whether old cycles reopen or repeat as new cycles.

## Phase 6 — Chapter 18 integration

Draft final Chapter 18 after product architecture stabilizes enough that the user guide will not immediately become stale.

## Phase 7 — Keep My Commandments cross-links

Develop a pragmatic crosswalk without blocking v1.

## Phase 8 — Quality and accessibility

Test keyboard-only navigation, screen readers, reduced motion, contrast, mobile, long reflections, empty states, long inactivity, abandoned assessment, repeated same-practice cycles, and historical links to archived content.

## Owner decisions still open

1. Public app name
2. Exact Chapter 18 title
3. One vs multiple active practice cycles
4. Save assessment results by default?
5. For Today selection method
6. Journal export?
7. Evidence-methodology disclosure depth
8. Visual similarity to KMC vs main WoP site

## Recommended first Cowork action

Use `10_COWORK_BOOTSTRAP_PROMPT.md` and require architectural reconciliation before implementation.
