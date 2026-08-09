# Christlike Practices App Handoff v0.1

## Purpose of this packet

This packet transfers the current design state for a proposed second Words of Plainness discipleship web application into the existing Claude Cowork / Claude Code development workflow.

The proposed application grows out of a behavior-first study of Jesus of Nazareth in the New Testament. It is intended to become the interactive companion to **Volume 1, Chapter 18**, within **Movement 3: Practical Discipleship Practices**.

The core question is deliberately different from the existing **Keep My Commandments** application:

- **Keep My Commandments:** What did Jesus ask disciples to do?
- **Christlike Practices:** How did Jesus Himself behave, and how might a disciple intentionally practice those behaviors?

The new application is **not a checklist to complete**. It is a place the reader returns to repeatedly for discernment, practice, reflection, and renewed growth.

## Read order for Claude Cowork

Read these first, in order:

1. `01_EXECUTIVE_HANDOFF.md`
2. `02_PRODUCT_VISION.md`
3. `03_CONTENT_ARCHITECTURE.md`
4. `04_UX_AND_REPLAYABILITY.md`
5. `05_DATA_MODEL.md`
6. `06_WOP_INTEGRATION_ARCHITECTURE.md`
7. `07_DECISIONS_CONSTRAINTS_AND_GUARDRAILS.md`
8. `08_OPEN_QUESTIONS_AND_NEXT_STEPS.md`

Then inspect the structured content in `/data/`.

Use `09_DEVELOPMENT_THREAD_WITH_VERBATIM_USER_PROMPTS.md` as the developmental record and rationale when a decision needs provenance or nuance. Do **not** treat every exploratory statement in the transcript as equally authoritative with the canonical documents above.

For the first Cowork session, use `10_COWORK_BOOTSTRAP_PROMPT.md`.

For repository implementation handoff, see `11_CLAUDE_CODE_INTEGRATION.md` and `CLAUDE_MD_SNIPPET.md`.

## Authority hierarchy inside this packet

When two documents appear to differ, use this order:

1. `07_DECISIONS_CONSTRAINTS_AND_GUARDRAILS.md`
2. `02_PRODUCT_VISION.md`
3. `04_UX_AND_REPLAYABILITY.md`
4. `03_CONTENT_ARCHITECTURE.md`
5. `05_DATA_MODEL.md`
6. `06_WOP_INTEGRATION_ARCHITECTURE.md`
7. Structured YAML data
8. Verbatim development transcript

The packet is intentionally versioned **v0.1** because the **product vision is mature while the content corpus remains developmental**. The approximately 70 practices still need final normalization, textual-evidence review, naming consistency, domain validation, and editorial completion before a content `1.0` release.

## Existing project context that should outrank this packet when appropriate

Claude Cowork should reconcile this handoff against:

- the existing Words of Plainness codebase and deployment architecture;
- the existing 3+ GB developmental-history RAG;
- current Words of Plainness terminology and design conventions;
- the existing Keep My Commandments application and any reusable components or infrastructure;
- current authentication, persistence, Sanity, Supabase, analytics, accessibility, and deployment patterns.

If an established project decision conflicts with this handoff, **surface the conflict explicitly** rather than silently replacing either one.

## Current public references

- Volume 1: https://www.wordsofplainness.org/volume-1/
- Keep My Commandments: https://commandments.brotheraaron.org/

## Central product principle

> **The unit of content is the Christlike practice. The unit of user experience is the practice cycle.**

The user may finish a practice cycle. The user never “finishes” a Christlike virtue.
