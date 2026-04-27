# Roadmap: Daily Programmer AGI Agent

## Goal
Build a reliable programming assistant that helps developers with daily work: understand projects, answer questions, search the web once with clean citations, inspect images/files, plan changes, execute safe code edits, verify results, remember useful lessons, and never crash the UI when a backend capability fails.

## Architecture

### 1. Unified frontend/backend contract
- Frontend should send normal Q&A to `/api/chat/stream`.
- Frontend should send implementation, debugging, refactor, self-development, zip/export, frontend/backend/full-stack tasks to `/api/agents/plan-and-execute`.
- The new endpoint performs: `MemoryAgent -> PlannerAgent -> ExecutorAgent -> VerifierAgent`.
- The endpoint returns one normalized response object: `summary`, `memory`, `plan`, `timeline`, `execution`.
- UI renders this as an agent timeline, a plan card, and the Programming AGI run evidence.

### 2. Memory and database
- ChromaDB is the single persistence layer.
- Chat and AGI Agent both use long-term and short-term memory through Chroma-backed services.
- Every successful or failed task records lessons, changed files, failures, repairs, and artifact ids.
- Planner must retrieve related prior runs before executing.

### 3. Developer daily-life abilities
- Project onboarding: index files, build architecture maps, explain modules.
- Code changes: plan, patch, run tests, show diff, export zip.
- Debugging: collect error, locate file, reproduce, patch, verify.
- Review: summarize risky files, security issues, missing tests, performance concerns.
- Git assistant: status, branch summary, commit message, PR summary.
- Terminal assistant: safe command suggestions and sandboxed execution.
- Documentation: generate README, API docs, changelog, migration notes.
- Learning: remember project conventions and user feedback.

### 4. Web and research improvements
- Deduplicate repeated web resources in the frontend.
- Show one compact source list per query, limited to the best unique links.
- Store useful research results in ChromaDB so repeated questions reuse memory first.
- When image search is used, display images directly in a grid with fallback for broken URLs.

### 5. Image understanding
- Upload images as attachments.
- Route image tasks to the backend vision/image intelligence service.
- Store structured observations in memory.
- Let the agent use image observations to plan UI fixes, extract design requirements, or answer questions.

### 6. Crash prevention
- All optional routers stay isolated behind try/except startup loading.
- Frontend renders unknown blocks safely.
- Network failures show a recoverable assistant message, not a blank screen.
- Image failures show `Image unavailable` instead of crashing.
- Agent endpoint returns timeline evidence even on failure.

### 7. Self-development guardrails
- The AGI Agent may plan and implement self-improvements in a sandbox.
- It must verify imports/tests/build before export or merge.
- It must record lessons and failures in memory.
- It should not silently modify user projects without an explicit merge/approval step.

## Implementation phases

### Phase 1: Stability and routing
- Add `/api/agents/plan-and-execute`.
- Route implementation-like chat requests to the unified endpoint.
- Keep `/api/chat/stream` for conversational answers and live web/image search.
- Add compact rendering for duplicate web and image results.

### Phase 2: Better agent UI
- Show a persistent timeline for planner, memory, executor, verifier.
- Show plan cards with steps and status.
- Show code/file changes in grouped components.
- Show export/preview evidence in the result card.

### Phase 3: Memory upgrade
- Use ChromaDB collections for chat history, task memory, lessons, research memory, profile, artifacts, and metrics.
- Add memory summaries per session.
- Retrieve memories before both chat and agent runs.

### Phase 4: Image and visual intelligence
- Add image upload analysis flow.
- Connect image intelligence output to planning context.
- Render direct internet images in search results.
- Let the agent compare screenshots against frontend code.

### Phase 5: Autonomous development loop
- Ask the AGI Agent to propose improvements.
- Convert proposals into sandbox plans.
- Execute small safe patches.
- Verify with import checks, frontend build checks, backend route checks, and zip integrity.
- Store improvement lessons.

### Phase 6: Production hardening
- Add integration tests for `/api/chat/stream`, `/api/agents/plan-and-execute`, image logs, source dedupe, and AGI run rendering.
- Add telemetry for latency, failures, memory retrieval, and verification status.
- Add permissions and approvals for destructive operations.
