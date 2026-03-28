# Words of Plainness — Code Tab Instructions

## Identity
You are working on the Words of Plainness ministry website (commandments.brotheraaron.org). Aaron Powner is the author and project lead.

## Start of Session
1. Call `memory:read_graph` to load the knowledge graph before responding to any task.
2. If the task relates to content, editorial decisions, or chapter work, call `ministry-rag:search_ministry_knowledge` with a relevant query to load context.

## End of Session
Before closing or when Aaron says "that's it," "done," "wrap up," or similar:
1. Call `ministry-rag:store_session_summary` with:
   - A clear summary of what was implemented, changed, or decided
   - Appropriate tags (e.g., `["chapter-3", "rjw-implementation"]`)
   - A descriptive title
2. Call `memory:create_entities` or `memory:add_observations` if any new architectural decisions, milestones, or technical knowledge should persist.
3. Prompt Aaron: "Before we close, should I store anything else to the graph?"
4. Remind Aaron: "Before you close Claude Code — kill all Claude processes in Task Manager, then delete `.claude\worktrees\*` folders."

## Key References
- Definitive Architecture: see project file `WoP_Definitive_Architecture_20260217.md`
- R·J·W System Spec: see project file `RAG_RJW_System_Feb2026.md`
- RAG has 3 collections: `ministry_knowledge`, `session_summaries`, `legacy_manuscripts`

## Editorial Standards
- Biblical sources lead; Restoration scriptures deepen as additional witnesses
- Church Style Guide compliance required
- Interfaith accessibility for all reader-facing content
