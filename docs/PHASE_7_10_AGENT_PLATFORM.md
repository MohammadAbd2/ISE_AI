# Phase 7–10 Agent Platform Upgrade

This build adds the next production layer for ISE AI.

## Phase 7 — Memory + retrieval

The backend now includes `AgentMemoryStore`, a local SQLite memory store under the runtime cache. Each autonomous run records:

- original task
- success/failure
- generated files
- failures and fixes
- summary and verification metadata

Before planning, the autonomous loop retrieves similar prior runs and sends them to the PlannerAgent as lessons. This is retrieval-assisted planning, not template reuse.

## Phase 8 — Agent communication protocol

The backend now includes `AgentSharedContext`, a shared blackboard for:

- PlannerAgent decisions
- BuilderAgent file writes
- VerifierAgent validation outcomes
- DebugAgent failures and repairs
- ExportAgent artifact messages

The shared context is emitted to the UI as an `agent_timeline` render block so the frontend can display agent communication rather than only console logs.

## Phase 9 — Artifact export hardening

ZIP exports now include:

- deterministic selected-path export
- ZIP integrity verification
- file count verification
- SHA-256 checksum metadata
- file size metadata
- strict download behavior: project-export artifacts without a valid file now return an error instead of fake text content

## Phase 10 — Devin-style UI timeline

The frontend now supports an `agent_timeline` card with:

- agent labels
- step phase/status
- elapsed/estimated timing
- progress bar
- decisions panel
- generated-file chips
- inline output/error rendering

## Runtime contract

The expected flow is:

```text
User request
  → memory retrieval
  → PlannerAgent architecture decision
  → BuilderAgent deterministic file writes
  → VerifierAgent build/test/playwright checks
  → DebugAgent repair loop when needed
  → ExportAgent verified ZIP artifact
  → frontend timeline + download action
```

No agent should claim a file or ZIP exists unless the deterministic runtime verified it.
