# Next Roadmap — Maximum Dynamic Programming AGI

This roadmap targets the exact failure shown in the laptop/screen webstore run: the agent generated useful files but stopped at a verifier error instead of repairing itself, and the dashboard still showed generic task summary blocks.

## Goal
Build a customer-grade programming AGI that never exports static templates, never treats frontend-only output as full-stack success, and always routes failures back through the correct sub-agent until the artifact is valid or the UI clearly reports the blocking evidence.

## Phase 1 — Memory Quarantine Before Planning
- Scan project-local memory folders, vector stores, cached task examples, and generated artifact history.
- Quarantine misleading JSON/vector files before the planner reads them.
- Keep only neutral rules, validators, and user-approved preferences.

## Phase 2 — Contract-First Planning
- Convert each prompt into a typed task contract.
- Detect requested domain, stack, project path, build commands, preview need, export mode, and merge intent.
- Reject vague fallback plans when the prompt clearly asks for full-stack work.

## Phase 3 — Dynamic Sub-Agent Routing
- Route the task to specialized agents: RequirementAgent, SandboxAgent, FrontendAgent, BackendAgent, DatabaseAgent, VerifierAgent, DebugAgent, PreviewAgent, ExportAgent, MergeAgent.
- Every agent receives exact inputs and expected outputs from the contract.
- No agent may use old saved examples as final code.

## Phase 4 — Real Sandbox Workflow
- If a project path is provided, copy the real project into the sandbox.
- If no path is provided, create the requested project structure from scratch.
- Execute steps one by one with real status transitions: pending → running → done / failed / repairing.

## Phase 5 — Terminal-Driven Repair Loop
- Run verifier/build/test commands.
- Parse failures into actionable repair instructions.
- Patch the responsible files.
- Re-run verification until passed or the max repair budget is reached.
- Never mark a ZIP as verified while any gate fails.

## Phase 6 — Strong Anti-Template Enforcement
- Block banned wording such as placeholder, generated from your request, CV text, generic landing sections, and old CSS classes.
- Repair banned markers automatically by rewriting the affected files.
- Store template failures as blocked patterns, not reusable memory.

## Phase 7 — Full-Stack Completeness Gates
- React + C# + MySQL tasks must include frontend, backend API, schema, seed, docker compose, API contract, and verification evidence.
- E-commerce tasks must include catalog, cart/order API, products schema, and seed records matching the requested domain.

## Phase 8 — Preview and Export Discipline
- Generate preview metadata only after frontend verification passes.
- Export ZIP only after all required gates pass.
- Merge remains a separate user-approved action with original-path and target-path support.

## Phase 9 — Outcome-First Dashboard
- Show task result, current blocker, repair attempts, changed files, and verification evidence first.
- Move raw logs into collapsible details.
- Replace fake elapsed/progress with event-derived progress.

## Phase 10 — Continuous Self-Improvement
- When a bug appears, the agent records the failure pattern and the successful repair rule.
- The next similar task uses the repair rule during planning and verification.
- The system improves validators and routing, not static generated pages.

## Implementation added in this package
- `backend/app/services/maximum_dynamic_agent.py`
- `backend/app/api/maximum_dynamic_agent_routes.py`
- `frontend/src/components/MaximumDynamicAgentPanel.jsx`
- `frontend/src/styles/maximum-dynamic-agent.css`
- `scripts/verify_maximum_dynamic_agent.py`
- updated backend router registration
