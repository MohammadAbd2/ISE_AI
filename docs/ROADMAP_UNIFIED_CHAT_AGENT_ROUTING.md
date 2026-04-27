# Roadmap — Unified Chat Agent for Programmers

## Goal
Make the chat box the primary interface. The user should not need to choose between Chat, AGI, or Agent. The frontend sends every message through a small router, and the backend decides whether the message needs normal chat, research, vision, or the full Agent execution loop.

## Implemented in this package

### 1. Unified product language
- User-facing labels now say **Agent** instead of separating AGI and Agent.
- The chat route says “Agent selected” when implementation/debugging/project work is detected.
- The execution card is renamed to “Chat-native Agent.”
- The navigation item is now “Agent Workspace.”

### 2. Chat-first routing
- The chat composer remains the default entry point.
- `auto` mode routes conversational questions to normal chat.
- Build/fix/debug/rewrite/project/download tasks route to `/api/agents/plan-and-execute`.
- Web/research/image requests keep their specialized chat route unless the task also requires implementation.

### 3. Backend route contract
- `/api/agents/route-task` now describes the implementation route as `agent_execute`.
- The route still points to `/api/agents/plan-and-execute` so the existing execution engine remains stable.
- Route payload keeps `requires_agent`, `requires_memory`, `requires_web`, `requires_vision`, and `export_zip` for predictable UI behavior.

### 4. Execution UX
- Agent result cards show planner, memory, sandbox, verifier, repair, preview, and export as one unified pipeline.
- Download and preview behavior remains connected to verified artifacts.

## Next implementation roadmap

### Phase A — Streaming Agent runs
Move `/api/agents/plan-and-execute` from one-shot JSON to event streaming so the chat card updates live while each sub-agent runs.

### Phase B — Workspace chooser in chat
Let the user attach/select a project folder from the composer. The Agent should receive `source_path` automatically when the message refers to “this project.”

### Phase C — Patch preview before merge
Every project-editing Agent run should show file diffs and require approval before writing back to the original workspace.

### Phase D — Unified memory policy
Both normal chat and Agent execution should write useful lessons into ChromaDB, but only Agent execution should store file changes, build failures, and repair patterns.

### Phase E — IDE bridge
VS Code and JetBrains extensions should send selected text, active file, terminal logs, and workspace root into the same chat router.

### Phase F — Safety validators
Before export or merge, validators should prove: command exit codes, touched files, checksums, no stale `running` report, no preview port conflict, and no template mismatch.
