# Agent AGI Roadmap — Next Implementation Phase

## Goal
Turn the current chatbot into a daily programmer copilot that can decide whether a request is normal chat, web research, image understanding, or autonomous implementation, then show the result in one stable UI contract.

## Phase 1 — Routing and Crash Prevention (implemented in this package)
- Add deterministic backend task router: `/api/agents/route-task`.
- Add lightweight agent health endpoint: `/api/agents/health`.
- Update the frontend to ask the backend which pipeline to use before running expensive work.
- Keep a local fallback router so the app does not crash if the router endpoint is unavailable.
- Route implementation/debug/self-improvement tasks to `/api/agents/plan-and-execute`.

## Phase 2 — Better Result Workspace (implemented in this package)
- Shrink repeated web/image resources to unique cards.
- Separate direct internet images from normal source links.
- Cap displayed resources so repeated searches do not flood the chat.
- Keep source links clickable while preserving a compact answer-first layout.

## Phase 3 — Memory Everywhere (next)
- Ensure chat, research, image analysis, and AGI Agent runs all read from ChromaDB context.
- Store task outcomes, files changed, lessons learned, and source summaries in separate collections.
- Add memory inspector UI with search and delete controls.

## Phase 4 — Image Understanding Toolchain (next)
- Add a single `/api/vision/analyze` contract for uploaded images and remote image URLs.
- Return objects, text, likely intent, safety warnings, and suggested next actions.
- Let chat and AGI Agent attach image understanding to the same memory context.

## Phase 5 — Self-Development Loop (next)
- Support explicit tasks like “create a plan to develop yourself and start implementing it.”
- Require sandboxed edits, verification commands, and rollback metadata.
- Never apply risky operations without approval checkpoints.

## Phase 6 — Programmer Daily-Life Skills (next)
- Project onboarding: summarize architecture, setup steps, and common commands.
- Bug triage: parse logs, reproduce, patch, test, and explain.
- PR assistant: generate diff summaries, tests, and migration notes.
- Learning assistant: explain unfamiliar code and create examples.

## Files changed in this phase
- `backend/app/services/agent_task_router.py`
- `backend/app/api/agent_routes.py`
- `frontend/src/lib/api.js`
- `frontend/src/App.jsx`
- `frontend/src/components/MessageList.jsx`
- `frontend/src/App.css`
