# Dynamic No-Template Programming AGI Roadmap

## Objective
Rebuild the assistant into a daily programming AGI that routes every request through agents and sub-agents instead of using templates, mock output, or hardcoded fallback pages.

## Roadmap implemented in this package

1. **Intent contract first** — every prompt becomes a machine-readable task contract with intent, domain, stack, capabilities, required files, sub-agents, and export gates.
2. **Sub-agent routing** — RequirementAgent, FrontendAgent, BackendAgent, DatabaseAgent, VerifierAgent, and ExportAgent each receive scoped inputs and outputs.
3. **Dynamic artifact graph** — required files are derived from the contract. A React + C# + MySQL login request cannot be exported as two React files.
4. **No-template verifier** — banned generic markers such as placeholder landing-page copy, old CSS classes, and mock text block export.
5. **Full-stack completeness** — backend, frontend, database, Docker, API docs, roadmap, and verification files are required when the request asks for them.
6. **Import graph validation** — local JavaScript imports are scanned before export.
7. **Verification truth** — validation score, failed gates, risk, and next action are shown explicitly.
8. **Repair routing** — failed gates identify which sub-agent must repair the artifact instead of writing random unrelated files.
9. **Outcome-first UI** — the dashboard shows outcome, trust score, gates, sub-agent events, and dynamic file graph.
10. **Admin-controlled direction** — this runtime is designed to connect to the existing admin controls for strictness, allowed stacks, retry limits, and export rules.

## Non-negotiable rules

- Never mark a full-stack task complete when only frontend files exist.
- Never export files containing generic template markers.
- Never hide failed verification behind a green “ZIP ready” state.
- Never create missing files in the wrong folder just to satisfy an error message.
- Always derive project files from the task contract.

## Example that must now route correctly

User asks: “Create a new website using React and C# and MySQL for a login page.”

The runtime contract requires:

- React frontend
- .NET API backend
- MySQL schema
- Docker compose
- auth endpoint
- password hashing
- API contract docs
- verification script

If any layer is missing, export is blocked.
