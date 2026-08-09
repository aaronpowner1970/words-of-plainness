# Claude Code Integration Guidance

## Goal

After Claude Cowork reconciles this packet with the existing project history and architecture, convert the **reconciled decisions** into repository-native canonical documentation before implementation.

Do not point Claude Code at the raw transcript as its everyday source of truth.

## Recommended repository shape

Adapt paths to existing project conventions.

```text
CLAUDE.md
.claude/
  rules/
    christlike-practices-app.md

docs/
  ch18-christlike-practices/
    00_READ_ME_FIRST.md
    ...
    canonical/
      PRODUCT_SPEC.md
      CONTENT_MODEL.md
      UX_FLOWS.md
      DATA_MODEL.md
      DECISION_LOG.md
```

The `canonical/` files should be created by Cowork **after reconciliation**, not copied blindly from this v0.1 packet.

## CLAUDE.md use

Keep `CLAUDE.md` concise. Add only enough information that every Claude Code session knows this app exists, where canonical docs live, the non-negotiable replayability rule, shared KMC/WoP conventions, and repository-specific commands/testing expectations.

## .claude/rules use

If the repository uses modular rules, create a focused rule file containing implementation constraints such as:

- never model a per-user terminal practice completion state;
- preserve stable CDP IDs;
- assessment results are suggestions, not diagnoses;
- do not expose hidden domain scoring during assessment;
- follow existing accessibility conventions;
- follow existing auth/privacy patterns;
- preserve established CMS/user-state ownership boundaries.

## Recommended development sequence

1. Create/confirm content schemas.
2. Seed a small subset of practices across several domains.
3. Build domain navigation.
4. Build practice detail.
5. Build commitment/practice-cycle creation.
6. Build reflection/return loop.
7. Build My Practice Journey.
8. Add Life Situations.
9. Add assessment.
10. Add For Today.
11. Add Chapter 18 launch integration.
12. Add KMC cross-links when ready.

Prove the unique replay loop before investing heavily in secondary discovery features.

## Future content-authoring skill

Once the corpus stabilizes, consider a reusable content-authoring skill/specification enforcing:

- behavior-first evidence;
- evidence classification;
- Scripture-reference standards;
- fresh-eyes methodology;
- domain assignment;
- What Jesus Did;
- How We Practice;
- How It Blesses Lives;
- concrete suggested actions;
- non-shaming pastoral language;
- textual-critical flags.
