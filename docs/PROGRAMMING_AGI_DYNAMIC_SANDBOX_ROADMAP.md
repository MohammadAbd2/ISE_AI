# Programming AGI Dynamic Sandbox Roadmap

This roadmap replaces the weak static-template workflow with a customer-grade programming AGI workflow.

## Core problems fixed

1. Static assistant completion text was shown even when the run was incomplete.
2. Full-stack tasks could be downgraded into React-only App.jsx/App.css exports.
3. The fallback builder reused CV/landing-page copy for unrelated tasks such as phone webshops.
4. Progress could show `100%` while events were incomplete.
5. The agent had no formal path memory, sandbox copy, preview, export, or merge lifecycle.
6. Export validation checked too little and allowed missing backend/database files.

## New workflow

1. **PathMemoryAgent** remembers local project roots such as `Current folder, e.g. ~/Desktop/Easv/`.
2. **IngestionAgent** copies a remembered/provided project folder into an isolated sandbox.
3. **RouterAgent** converts the user request into a typed task contract.
4. **PlannerAgent** builds a roadmap and required file graph from the contract.
5. **FrontendAgent** writes React files only if the contract requires frontend work.
6. **BackendAgent** writes API/backend files only if the contract requires backend work.
7. **DatabaseAgent** writes schema/compose files only if the contract requires database work.
8. **VerifierAgent** validates imports, required files, stack coverage, domain coverage, and template markers.
9. **RepairAgent** fixes deterministic missing-file failures and reruns validation.
10. **PreviewAgent** returns preview command/link metadata.
11. **ExportAgent** creates ZIP only after validation passes.
12. **MergeAgent** copies sandbox output into a requested target path only after user approval.

## Dashboard behavior

The dashboard now shows:

- task contract and detected stacks;
- pending/running/completed/failed steps;
- evidence per step;
- validation score and failed gates;
- preview command;
- ZIP export metadata;
- merge target control.

## Strict guarantee

A request like `create a full stack application for a webshop that sell phones` must resolve to:

- React frontend;
- backend/API layer;
- database schema;
- verification script;
- API contract documentation;
- ZIP export only after validation passes.

It must never produce a CV landing page or React-only bundle.
