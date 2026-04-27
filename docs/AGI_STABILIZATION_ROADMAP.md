# AGI Stabilization + Intelligence Upgrade Roadmap

## Goal
Move the chat-native AGI from a visual demo into a Codex-style programming worker: every task is routed through a typed contract, executed step-by-step, repaired from terminal/verifier evidence, previewed with a real URL contract, and exported only after validation.

## Phase 1 — Execution Engine Rewrite
- Add a reusable `ExecutionEngine` with step status, logs, retries, and events.
- Normalize every agent return type before workflow code reads `.get()`.
- Keep progress tied to completed steps, not fixed percentages.

## Phase 2 — True Self-Repair
- Add `ErrorClassifier` for dependency, import, syntax, template-marker, and recursive-copy failures.
- Add `RepairEngine` that patches file graphs and reruns validation up to a repair budget.
- Record every repair attempt as evidence.

## Phase 3 — DAG Planning
- Add `DAGPlanner` so backend/frontend/database/preview/export steps depend on the contract and requested stack.
- Backend-only requests do not generate frontend files.
- Full-stack requests cannot pass as frontend-only.

## Phase 4 — Preview Lifecycle
- Add `PreviewManager` with dynamic port detection.
- Return a command and URL contract instead of fake `/preview/<id>` links.
- Support `PREVIEW_BASE_URL` and prompt-provided ports.

## Phase 5 — File System Safety
- Add `safe_copy_tree` with depth/file-size limits.
- Exclude `.ise_ai`, `AGI_Output`, `node_modules`, `dist`, `build`, `.git`, and cache/vector files.
- Prevent recursive sandbox copy and path-too-long crashes.

## Phase 6 — Tool Routing
- Add a tool router contract for terminal, filesystem, preview, web search, and image generation capabilities.
- Keep high-risk tools disabled unless admin policies enable them.

## Phase 7 — Frontend AGI UX
- Route chat coding requests through `/api/programming-agi/run`.
- Render AGI runs inside chat with timeline, validation gates, preview command, and workspace file tree.
- Add per-file preview/download through the existing file-tree component.

## Phase 8 — Export Discipline
- Export ZIP only after gates pass.
- If gates fail, repair first; if still failing, block export with exact failed gates.

## Implemented Files
- `backend/app/services/agi_execution_engine.py`
- `backend/app/services/agi_repair_engine.py`
- `backend/app/services/agi_preview_manager.py`
- `backend/app/services/agi_safe_filesystem.py`
- `backend/app/services/agi_dag_planner.py`
- `backend/app/services/agi_tool_router.py`
- `backend/app/services/agi_verifier.py`
- `backend/app/services/programming_agi_runtime.py`
- `frontend/src/App.jsx`
- `frontend/src/components/MessageList.jsx`
- `frontend/src/styles/agent-file-tree.css`
