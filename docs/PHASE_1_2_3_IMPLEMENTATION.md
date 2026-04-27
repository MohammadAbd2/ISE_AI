# Phase 1 + 2 + 3 Agent Upgrade

This build moves the sandbox workflow toward a production agent contract.

## Phase 1 — Tool-only execution

Planning can describe intent, but file mutation, command execution, and ZIP export must go through deterministic tools. File-write steps are verified by checking that the target exists and is non-empty before the step can be marked complete.

## Phase 2 — Multi-agent roles

The execution timeline now distinguishes these roles:

- `PlannerAgent`: creates structured task steps.
- `BuilderAgent`: writes or edits files through filesystem tools.
- `VerifierAgent`: runs build/test commands.
- `DebugAgent`: repairs failed commands or steps when possible.
- `ExportAgent`: creates verified downloadable ZIP artifacts.

## Phase 3 — Live execution UI

Progress blocks carry timing and agent labels so the frontend can display which agent is working, elapsed time, estimated time, and step status.

## Export contract

The ZIP button should only appear when the backend has registered a real artifact with a verified file path. `sandbox_export` is no longer treated as a file; it is an export action handled after implementation and verification.
