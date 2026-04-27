# Agent AGI Programmer Copilot Roadmap and Started Implementation

## North star
Turn ISE AI into a daily programmer assistant that can chat, research, inspect images, plan implementation work, execute safe code changes in a sandbox, verify results, remember lessons in ChromaDB, and present outcomes without repeated noisy resources.

## Phase 1 — Stabilize the chat-to-agent contract (started)
- Route build/fix/refactor/self-improvement requests through `/api/agents/plan-and-execute`.
- Keep normal Q&A and lightweight web lookup in chat mode.
- Return one normalized UI contract from backend: timeline, resources, files changed, artifact id, and memory hit count.
- Deduplicate web and image resources by canonical URL so repeated search results appear once.
- Make self-development prompts default to the current project root when no source path is provided.

## Phase 2 — Frontend result workspace (started)
- Render agent timeline first, then plan, implementation result, and one compact source/image list.
- Display internet images inline when the backend provides image URLs or thumbnails.
- Keep export/download actions in one place.
- Add clearer failure states so the app reports repair evidence instead of crashing.

## Phase 3 — Memory everywhere
- Store successful runs, failures, fixes, and lessons in ChromaDB collections.
- Query memory for both chat and agent planning.
- Add a memory summary panel that shows which old runs influenced the current plan.
- Add cleanup controls for stale vector/cache data without deleting project path memory.

## Phase 4 — Vision and image understanding
- Detect image attachments and image URLs in messages.
- Send local image bytes or fetched image metadata to the backend vision service.
- Store image understanding notes in memory when useful.
- Use the notes to improve image search, UI generation, bug reports, and code tasks.

## Phase 5 — Real implementation loop
- Planner creates a typed contract: intent, stack, files, commands, risks, verification gates.
- Executor edits only sandbox copies unless merge is explicitly approved.
- Verifier runs allowed build/test/import commands and returns exact stdout/stderr.
- Repair agent retries bounded fixes when verification fails.

## Phase 6 — Programmer daily-life tools
- Project map and dependency explorer.
- Bug reproduction assistant.
- Test generator and failing-test repair loop.
- PR summary, changelog, release notes, and migration assistant.
- Code review with risk levels and patch suggestions.
- Terminal task runner with allowlisted commands and safe cancellation.

## Phase 7 — Long-term autonomy with control
- Autonomy levels: explain-only, plan-only, sandbox-edit, verified-export, approved-merge.
- Kill switch and max-run limits.
- Human approval gates for destructive actions, network installs, and filesystem merge.
- Evaluation suite that runs before claiming success.

## Implementation completed in this pass
- Added `backend/app/services/agent_result_normalizer.py`.
- Updated `/api/agents/plan-and-execute` to return a normalized `ui_contract`.
- Added URL canonicalization and source/image deduplication.
- Added self-development source path defaulting for prompts about improving/developing the app itself.
- Updated frontend AGI response rendering to consume backend `ui_contract` resources.
- Improved resource cards to render internet images directly when available.
- Hardened frontend JSON error handling.

## Next implementation targets
1. Add streaming progress from `/api/agents/plan-and-execute` so the timeline updates while tools run.
2. Add a dedicated image-analysis endpoint for URL and attachment vision.
3. Add a source-path picker and remembered project selector in the chat composer.
4. Add a one-click “continue repair” action when verification returns failed gates.
5. Add automated frontend smoke tests for agent render blocks.
