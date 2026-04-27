# Roadmap — Codex-style Backend Scope and Self-Repair Upgrade

## 1. Backend-only scope lock
Prompts such as `now give me the backend`, `I said backend not front end`, `backend only`, and `API only` are classified as `backend_build`. The required file graph excludes `frontend/*`, and verification fails if frontend files are present.

## 2. Context-correct routing
The RequirementAgent now detects backend-only follow-ups before applying any full-stack defaults. If the user does not specify a backend stack, the agent selects a Node API by default instead of regenerating React.

## 3. Verifier gate improvement
The verifier now includes `backend_only_scope_respected` and `backend_artifact_present` gates. A backend request cannot pass with frontend-only output.

## 4. DebugAgent repair upgrade
The DebugAgent can remove frontend files from a backend-only artifact, rebuild missing backend artifacts through the dynamic graph, patch banned markers, and create missing import targets.

## 5. Executor error playbooks
Common terminal errors become repair actions. Example: `vite: not found` patches `frontend/package.json` to ensure Vite/React dependencies are present and instructs the executor to run `npm install` before `npm run build`.

## 6. Command-aware run reports
Run reports now expose verification commands with `cwd`, `command`, and `purpose` so the frontend can render real next commands rather than static progress.

## 7. Repair transparency
Every repair attempt records changed files, evidence, and remaining failures. The system should only stop when gates pass or the repair budget is exhausted.

## 8. Frontend dashboard impact
The frontend can now display a precise reason for blocked exports: wrong scope, missing backend, missing dependencies, unresolved imports, or remaining verification gates.
