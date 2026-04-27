# Autonomous Dev Platform v4 Roadmap — Phases 9–20

## North star
Make the unified Agent feel like ChatGPT + Cursor + DevTools for programmers: live streaming, durable jobs, safe real-project editing, Git control, codebase intelligence, collaborative approvals, plugin expansion, hard security, and proposal-first self-evolution.

## Phase 9 — Real-time streaming core
- Add WebSocket `/api/platform-v4/ws/{job_id}`.
- Stream structured events: thinking, command output, verification, artifacts.
- Support client interrupts through control messages.

## Phase 10 — Multi-task jobs
- Add durable job state under `AGI_Output/platform_v4`.
- Add queued/running/paused/cancelled/completed/failed lifecycle.
- Add job sidebar-ready REST endpoints.

## Phase 11 — Persistent workspaces
- Save known workspace paths and metadata.
- Reopen projects later without re-entering paths.
- Keep sandboxes and workspace records separate.

## Phase 12 — Git integration
- Expose status, diff, branch, commit primitives.
- Require human review before commit.
- Make rollback and PR generation the next extension.

## Phase 13 — Codebase intelligence
- Index functions/classes/imports across Python, JS, TS, JSX, TSX.
- Return dependency snippets and architecture clues.
- Use this index to ground future Agent planning.

## Phase 14 — Autonomous debugging
- Parse common error classes.
- Produce root-cause candidates and fix loop plan.
- Feed repeated failures into memory and self-evolution.

## Phase 15 — DevTools panel
- Show console/jobs, network endpoints, filesystem, timeline, memory, security policy.
- One place for developers to inspect what the Agent is doing.

## Phase 16 — Memory v2
- Store project-scoped failures, security blocks, fixes, and lessons.
- Retrieval will later inject these into planning automatically.

## Phase 17 — Collaboration
- Add shared comments/activity records.
- Prepare approval workflow and team review surfaces.

## Phase 18 — Plugin ecosystem
- Register plugin manifests with permissions and audit records.
- Future: GitHub, Jira, Docker, cloud deploy plugins.

## Phase 19 — Security and sandbox hardening
- Enforce safe-mode command policy.
- Block dangerous fragments.
- Cap command timeout.
- Expose audit report.

## Phase 20 — Self-evolution v3
- Detect failed jobs and repeated bugs.
- Generate upgrade proposals.
- Keep upgrades proposal-first and human-gated.

## Implemented in this package
- Backend `platform_v4_routes.py`.
- Backend `autonomous_dev_platform_v4.py` service.
- Frontend `AutonomousDevPlatformV4Panel.jsx`.
- API client bindings.
- Platform tab now shows the v4 console above the existing platform panel.
