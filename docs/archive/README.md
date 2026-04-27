# ISE AI — Phase 70 Autonomous Software Company Platform

This build includes Phase 62–70 production/platform upgrades on top of the Phase 53–61 elite agent platform. See `docs/PHASE_62_70_AUTONOMOUS_SOFTWARE_COMPANY.md` and `PHASE_70_IMPLEMENTATION_MANIFEST.json`.

# ISE AI

ISE AI is a local-first AI engineering workspace for code generation, project analysis, terminal execution, dashboard-driven operations, and self-improvement workflows. It combines a FastAPI backend with a React/Vite frontend and is designed to help users inspect repositories, generate features, fix issues, and export the results.

## What the project does
- analyzes uploaded repositories and source archives
- runs chat and coding workflows with project context
- exposes a dashboard for tools, capabilities, artifacts, approvals, and runtime actions
- provides a built-in terminal surface
- supports self-improvement and planning workflows
- packages generated projects as downloadable zip artifacts

## Key improvements in this revision
- fixed Python test discovery with a root `pytest.ini`
- added a fallback when `bson` is unavailable so local development is less fragile
- created the missing documentation handbook used by the docs page
- fixed the terminal API base path mismatch between frontend and backend
- added project export packaging through `POST /api/project/export`
- upgraded artifact downloads to support binary files such as zip exports
- added a dashboard export panel for downloadable project bundles
- added a roadmap in `docs/ROADMAP.md`

## Repository structure
```text
backend/
  app/
    api/
    core/
    schemas/
    services/
frontend/
  src/
docs/
output/
tests/
```

## Important paths
- `backend/app/main.py`: backend entrypoint
- `backend/app/api/routes.py`: core API routes
- `backend/app/api/project_routes.py`: project analysis and export endpoints
- `backend/app/services/project_exports.py`: zip packaging service
- `frontend/src/App.jsx`: frontend state orchestration
- `frontend/src/components/DashboardView.jsx`: dashboard runtime view
- `frontend/src/components/DocumentationView.jsx`: docs renderer
- `frontend/src/components/TerminalPanel.jsx`: terminal surface
- `docs/ISE_DEVELOPER_HANDBOOK.md`: developer handbook
- `docs/ROADMAP.md`: implementation roadmap

## Quick start
### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`.

## Project export workflow
When ISE AI generates a project such as a landing page, the intended flow is:
1. create or merge the generated project into the output workspace
2. package the project into a zip file
3. register the zip as a `project-export` artifact
4. let the user download it from the dashboard artifact/export area

You can also trigger an export manually with:
```bash
curl -X POST "http://localhost:8000/api/project/export?session_id=my-session"
```

## Documentation
The in-app documentation page reads from:
- `docs/ISE_DEVELOPER_HANDBOOK.md`

This file should be updated whenever architecture, routes, or extension points change.

## Testing
From the repository root:
```bash
pytest -q
```

## Notes
This project includes advanced services for planning, approvals, artifacts, sandbox flows, project analysis, and self-improvement. Some optional features depend on local tooling such as MongoDB, Playwright, Ollama, or other runtime dependencies. The code is structured to fall back more gracefully when some of those pieces are unavailable.

## Latest stability improvements

This revision strengthens the execution pipeline for project generation and safe merge flows:

- explicit task routing prevents accidental self-upgrade runs on normal coding requests
- isolated sandboxes persist under `output/sandboxes/` instead of disappearing temporary folders
- generated sandbox projects can be exported as downloadable ZIP artifacts
- merge operations create backups first and startup cleans backups older than 30 days
- terminal commands support a working directory so frontend builds run from `frontend/` when needed
- tool suggestion ranking is more semantic and description-aware


## Recent critical improvements

- Local HTTPS support with self-signed certificates via `setup_and_run.sh` for both backend and frontend.
- Task-aware sandbox exports: single-file/component requests produce a focused ZIP, while app/page/project requests produce a project-level ZIP.
- Downloadable ZIP artifacts are surfaced directly in chat render blocks with a download icon.
- Sandbox exports exclude recursive runtime output and stale checkpoint data.


## General dynamic agentic workflow

ISE AI is intended to behave as a general programming assistant. It should infer the requested deliverable from the user prompt, build a roadmap, implement inside a sandbox, verify the result, repair failures, and export a ZIP artifact. The sandbox builder avoids domain-specific hardcoded demos and uses request-aware generation for landing pages, components, and project scaffolds.

## Phase 53–61 Elite Agent Platform Additions

This build adds real LLM integration contracts, repo intelligence graphing, adaptive planning, advanced self-healing, UX review, human approval gates, memory graph, cloud job planning, and a frontier product-builder contract. See `docs/PHASE_53_61_ELITE_AGENT_ROADMAP.md`.
