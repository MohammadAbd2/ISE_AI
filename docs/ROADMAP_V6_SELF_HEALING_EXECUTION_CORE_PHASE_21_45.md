# Roadmap v6 — Production Programmer Agent + Self-Healing Execution Core

This roadmap completes the production-hardening phases and fixes the reliability gaps found in real chat usage: truncated file contents, non-running previews, IDE extensions that do not write back, and Agent runs stopping at verifier gates.

## Phase 21 — Authentication foundation
- Add ownership-aware route contracts and prepare workspace/user metadata.
- Keep all file and workspace actions scoped to a known project root.

## Phase 22 — Sandbox hardening
- Keep generated work under `AGI_Output` and prevent unsafe parent traversal.
- Exclude `.git`, `node_modules`, Chroma vector files, caches, and generated output loops during ingestion.

## Phase 23 — Real preview orchestration
- Start actual local Vite processes instead of returning only command strings.
- Use managed preview sessions, process IDs, captured logs, conflict-safe ports, and stop controls.

## Phase 24 — Test intelligence
- Keep verification gates visible and deterministic.
- Run build/test commands only when toolchains and dependencies exist, and report clear skipped checks.

## Phase 25 — Dependency intelligence
- Auto-run `npm install` for preview startup when `node_modules` is missing.
- Capture install logs and fail preview cleanly when install fails.

## Phase 26 — IDE bridge v2
- JetBrains detects the current project path.
- Extension sends instruction + file path to backend.
- Backend rewrites the file, verifies the write, and returns full content.
- JetBrains applies the code with `WriteCommandAction` and saves the document.

## Phase 27 — Git workflow foundation
- Keep generated changes packaged with reports and checksums so they can be committed or reviewed safely.

## Phase 28 — Background agent foundation
- Managed preview/session registries are process-aware, cancelable, and observable.

## Phase 29 — Collaboration foundation
- Artifacts contain metadata, previews, and verification data so they can be reviewed by humans before merge.

## Phase 30 — Production deployment readiness
- Preview runs on `0.0.0.0` with localhost URL contracts.
- Ports avoid `5173` by default because the main UI usually owns it.

## Phase 31 — Evaluation suite foundation
- Syntax checks cover the patched backend modules.
- Exports include `RUN_REPORT.json` and diagnostic reports.

## Phase 32 — Plugin SDK foundation
- IDE rewrite endpoint acts as a tool/plugin bridge.

## Phase 33 — Advanced memory foundation
- Agent records repaired runs and keeps Chroma-backed execution memory.

## Phase 34 — Autonomous self-maintenance
- Repeated verifier failures route into a multi-attempt self-healing loop.
- The Agent no longer hard-stops on `no_template_markers` or `import_graph_resolves`.

## Phase 35 — Release polish
- Direct file/PDF requests return a file card and preview, not a fake generated app.

## Phase 36 — Deterministic file writing engine
- All generated artifacts use atomic temp-file writes.
- Every write is flushed, fsynced, moved into place, checksummed, and verified.
- Text writes compare the final on-disk content against the requested content.

## Phase 37 — Real command execution engine
- Preview starts with real local subprocesses.
- stdout/stderr logs are captured and kept in preview session state.

## Phase 38 — Preview bridge
- `/api/platform/preview/start` and Agent plan execution use the managed preview registry.
- Generated apps start on `5174+`, not the main app port.

## Phase 39 — JetBrains real code sync
- `extensions/jetbrains/IseAiToolWindow.kt` now applies real edits to `src/App.jsx`.
- Backend endpoint: `POST /api/devx/ide/rewrite-file`.

## Phase 40 — Self-healing verifier
- Blocked gates trigger repair attempts instead of stopping immediately.
- The loop retries up to five times.

## Phase 41 — Import graph auto-fix
- Failed `import_graph_resolves` rewrites the canonical graph and refreshes missing files.

## Phase 42 — No-template marker auto-clean
- Template markers like `TODO`, `TEMPLATE`, and placeholder text are cleaned during repair.

## Phase 43 — Continuous execution loop
- Flow is now: plan → execute → verify → repair → verify → preview → export.

## Phase 44 — Execution state machine
- Runtime exceptions convert into diagnostic exports where possible.
- Runs finish with evidence instead of silently hanging.

## Phase 45 — Guaranteed export behavior
- Verified runs export normally.
- Unresolved runs export a diagnostic package with `AGENT_REPAIR_WARNINGS.md` instead of leaving the user with nothing.

## Implementation notes
- File truncation fix: `backend/app/services/safe_file_writer.py` and `downloadable_files.py`.
- Preview fix: `backend/app/services/preview_runtime.py` and Agent auto-start in `agent_routes.py`.
- Self-healing fix: `ProgrammingAGIRuntime._self_heal_until_stable`.
- IDE fix: `developer_experience_routes.py` and `extensions/jetbrains/IseAiToolWindow.kt`.
