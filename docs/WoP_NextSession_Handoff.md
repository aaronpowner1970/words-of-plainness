# WoP Next Session Handoff

**Date:** March 30, 2026
**Prior session:** R·J·W content authoring complete, reflectMode default changed, full status verification

---

## COMPLETED — Do Not Revisit

- **R·J·W system:** Fully complete. All deployed chapters (1–8, 10) have authored pause-point content. Account save on MySQL. Portable document on /my-reflections/. reflectMode defaults to 'chapter'. Ch. 9 content exists in mockup HTML — transfers when chapter is built.
- **Citation panel:** All chapters (1–10) retrofitted and deployed.
- **Search Writings:** Pagefind live at /search/. FAB and Learning Tools links updated.
- **PauseDoc/Dashboard slug maps:** Fixed and extended to Ch. 10.
- **/about/sources/:** Live and complete.
- **Engagement tracking (Layer 3):** Live.
- **Discord Phase 0:** Complete (server, channels, guidelines, #report-a-concern, widget).

---

## REMAINING TASKS

### Decision Point
**AI Conversational Response Agent (Phase B):** Pagefind static search is live. Aaron decides whether to begin RAG-powered conversational search. Spec exists in Community Safety & Moderation Protocol v1.0. ChromaDB infrastructure ready (3,356+ chunks). Implementation path: chat UI on /search/ or /ask/, Django endpoint queries ministry-rag, passes to Claude API, returns grounded answer with citations. Three-tier response architecture.

### Infrastructure
- **Cloudflare Web Analytics:** Register all four domains (brotheraaron.org, wordsofplainness.org, brotheraaron.faith, wordsofplainness.faith). Was in progress at a prior session close.
- **Admin analytics dashboard:** Django `/admin/dashboard/` ORM query view for engagement summary. Designed, not built.

### Editorial
- **Chapter 11 ("The Living Christ"):** Not yet built. Brief transitional chapter — written last in Movement 2.
- **Jim's credit line:** About page — still unsettled.

### Longer Horizon
- Phase 4–5 Personal Study Layer (gold highlights, voice alternatives, anchor notes, portable doc export)
- "How to Use This Website" guide for New Here page
- "How AI Supports This Ministry" public transparency page
- SCRIBE Origin Story audio (script v2 delivered, not yet executed)
- Calling the Straying Stranger Home (Suno generation + LTX video)

---

## KEY REPO PATHS
- Chapters: `src/chapters/`
- R·J·W system: `chapter.njk` layout + `chapter.js` RJW IIFE
- My Reflections: `src/js/my-reflections.js`
- Search: `src/pages/search.njk`
- Django API: `apowner.pythonanywhere.com` (MySQL: `apowner$default`)

## STANDING RULES
- Every Claude Code prompt ends with: "Push this commit directly to main. Do not create a PR."
- After Claude Code: `git pull origin main` in PowerShell
- After session: `Remove-Item -Recurse -Force ".claude\worktrees\*"`
- `discordChannelId` frontmatter — never touch
- Verify from disk via filesystem MCP — do not hedge or ask Aaron to verify what tools can confirm
