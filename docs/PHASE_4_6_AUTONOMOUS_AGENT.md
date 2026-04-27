# Phase 4–6 Autonomous Agent Upgrade

This build introduces the production autonomous loop used for user project tasks.

## Runtime contract

User project tasks now follow this execution order:

1. **PlannerAgent** analyzes the user request and derives an executable architecture.
2. **BuilderAgent** writes files only through deterministic filesystem tools.
3. **VerifierAgent** runs build checks and optional Playwright UI smoke tests.
4. **DebugAgent** performs targeted repairs when verification fails.
5. **ExportAgent** packages only verified generated output into a registered artifact.

The assistant should not claim that a file, ZIP, or project exists unless the tool layer created and verified it.

## Playwright integration

The autonomous loop includes an optional Playwright smoke-test step. If `@playwright/test` exists in the sandboxed frontend workspace, the engine writes a smoke spec and runs it. If Playwright is not installed, the step is marked as skipped and the build verification result remains the source of truth.

To enable browser verification in a generated frontend project:

```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium
```

## Artifact downloads

ZIP downloads are produced through the backend artifact service. The frontend only renders download buttons for registered artifacts with real artifact IDs. The export service writes ZIP archives under the runtime cache and stores their absolute path in artifact metadata.

## Progress UI

The chat UI now displays a Manus-style progress card with:

- active agent role
- elapsed / estimated time
- progress bar
- per-step status
- tool output and errors

## Design goal

The system is no longer tied to any domain-specific template. It extracts the subject and task type from the user request, then builds the requested files through the autonomous loop.
