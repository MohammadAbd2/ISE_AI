# Roadmap: Autonomous Dev Console v3 — Phase 1 to Phase 8

Goal: make the chat Agent behave like a ChatGPT-style developer execution environment: live progress, inspectable commands, editable plans, file exploration, visual loops, error explanations, controls, and visible self-improvement.

## Phase 1 — Live streaming thinking
Show a live Thinking card immediately when the Agent starts and stream route decisions, planning, command execution, verification, and artifact registration as separate UI events.

## Phase 2 — Interactive terminal
Render command cards with cwd, command, status, stdout, stderr, exit code, copy, rerun placeholder, cancel placeholder, and collapse output.

## Phase 3 — Editable Agent plan
Display plan steps as editable/reviewable rows before and during execution. Future transport endpoints will approve, reject, reorder, and rerun.

## Phase 4 — File system explorer UI
Show generated/sandbox files as a tree-style explorer with artifact download and future inline open/save hooks.

## Phase 5 — Agent loop visualizer
Visualize Plan → Execute → Verify → Repair → Export with current status, failed gates, and retry count.

## Phase 6 — Smart error explainer
Convert stderr and validation failures into readable cause, proposed fix, and safe next action.

## Phase 7 — Developer controls panel
Expose autonomy level, retry limit, preview/export toggles, sandbox safety, and approval requirements.

## Phase 8 — Visible self-improvement UI
Show lessons learned and proposed self-upgrades while keeping core changes approval-gated.

## Started in this build
- Added v3 render blocks to Agent chat results.
- Added frontend components for every phase.
- Added backend roadmap/status endpoint.
- Kept destructive actions disabled until backend approval endpoints exist.
