# Codex-Style Dynamic Agent Roadmap

This roadmap fixes the issue shown in the React + Node + SQLite example where the agent stopped on a banned marker instead of repairing itself.

## 1. Contract-first execution
- Parse the prompt into an executable contract before writing files.
- Detect stack spelling variants such as `litesql`, `lite sql`, and `sqlite`.
- Decide required frontend, backend, database, docs, verifier, preview, export, and merge steps from the contract.

## 2. Stack-aware sub-agent routing
- `RequirementAgent` creates `agent-contract.json` and `ROADMAP.md`.
- `FrontendAgent` owns React/Vite files and API client wiring.
- `NodeBackendAgent` owns Express/Fastify routes for React + Node requests.
- `DotnetBackendAgent` owns C# API files for React + C# requests.
- `DatabaseAgent` owns MySQL/SQLite schema and seed data.
- `VerifierAgent` owns static gates and command evidence.
- `DebugAgent` patches exact failures and reruns verification.
- `ExportAgent` can ZIP only when verification passes.

## 3. Terminal-style repair loop
- When a gate fails, the agent does not stop at “Could not repair”.
- It reads the failing gate, patches the responsible layer, reruns validation, and only moves forward when the failure count decreases or the repair budget is exhausted.
- Structural failures rebuild the missing layer from the live contract instead of reusing stale partial files.

## 4. No-template gate
- Old CV/landing-page markers are banned from generated application files.
- Marker cleanup runs during generation and after every repair attempt.
- The verifier ignores policy text inside its own script, but scans application/source files.

## 5. Full-stack completeness
- React + Node + SQLite now creates frontend, Node backend, SQLite schema/seed, API contract, and verifier files.
- React + C# + MySQL still creates .NET API, MySQL schema/seed, Docker compose, and frontend API client.
- Full-stack output cannot be exported as frontend-only.

## 6. Dashboard behavior
- Show real contract, active stack, current step status, repair attempts, blockers, verification score, and generated file list.
- Do not show static success text when export is blocked.

## 7. Export rules
- ZIP is allowed only when all required files exist, imports resolve, domain terms match, banned markers are absent, and stack-specific gates pass.
