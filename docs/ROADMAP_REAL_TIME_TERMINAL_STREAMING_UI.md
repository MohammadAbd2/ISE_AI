# Roadmap: Real-Time Terminal Streaming UI

## Objective
Turn the Agent into a believable programmer daily-driver by showing real command output as it happens. The user should see installs, builds, tests, errors, retries, cancellations, and final proof without waiting for a static response.

## Phase 1 — Streaming Transport (started)
- Add `/api/terminal/run-stream` for fetch-based NDJSON streaming.
- Emit normalized events: `start`, `stdout`, `stderr`, `heartbeat`, and `exit`.
- Track active `run_id` values so the UI can cancel running commands.
- Keep a REST fallback for older browsers or failed streaming negotiation.

## Phase 2 — Live Terminal UI (started)
- Replace delayed terminal output with line-by-line rendering.
- Add command status, current working directory, run id, elapsed heartbeat, cancel, clear, and auto-scroll controls.
- Preserve keyboard shortcuts: Enter to run, Up/Down for history, Ctrl+L to clear.

## Phase 3 — Agent Integration (next)
- Attach every Agent execution step to a streaming run id.
- Show Planner/Executor/Verifier terminal streams in the chat result card.
- Group logs by sub-agent and command.
- Link failed logs directly to the DebugAgent repair proposal.

## Phase 4 — Reliability and Safety (next)
- Add command allowlist profiles per workspace.
- Add process groups so cancelling a run kills child processes too.
- Add max output bytes per run with downloadable full logs.
- Persist logs under `AGI_Output/runs/<run_id>/terminal.ndjson`.

## Phase 5 — Developer Experience (next)
- Add split view: chat on left, live terminal on right.
- Let users pin a terminal to a workspace.
- Add “rerun failed command” and “send log to Agent” buttons.
- Add ANSI color rendering and clickable file paths.

## Phase 6 — Production Hardening (planned)
- WebSocket/SSE gateway for multi-user deployments.
- Queue-backed execution jobs.
- Docker sandbox streaming.
- Role-based permissions for dangerous commands.
- Audit trail and replayable run sessions.

## Acceptance Gates
- A long-running command streams output before completion.
- Cancelling a command updates the UI and terminates the backend process.
- Exit code, duration, cwd, and run id are visible.
- The old `/api/terminal/run` endpoint still works.
- The UI never claims success until an `exit` event is received.
