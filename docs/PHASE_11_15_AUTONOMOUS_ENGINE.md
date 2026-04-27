# Phase 11-15 Autonomous Agent Upgrade

This upgrade moves ISE AI toward a production autonomous software-engineer platform.

## Phase 12: Multi-agent collaboration

The runtime has an explicit Planner → Builder → Verifier → Debug → Export protocol. Each agent writes messages into a shared context so the frontend can render real thoughts, decisions, retries, files, errors, and artifacts.

## Phase 13: Testing loop

Generated projects are verified with build commands and optional Playwright smoke checks when Playwright is installed. Failures are routed to DebugAgent and do not get marked as successful exports.

## Phase 15: Artifact perfection

ZIP exports are deterministic, checksum verified, and include manifest sidecars with file hashes and sizes. The download route validates the ZIP before returning it.

## Phase 11: Learning

The agent stores task memories and extracts lessons from successful and failed runs. Future plans retrieve similar memories and lessons before implementation.

## Phase 14: Runtime preview

A runtime-preview registry is included for verified frontend builds. It provides safe local preview commands and URLs without launching untrusted long-running processes by default.

## UI roadmap

The frontend timeline surfaces agent decisions, timing, progress, files, errors, and artifact actions in a Devin/Manus-style execution card.
