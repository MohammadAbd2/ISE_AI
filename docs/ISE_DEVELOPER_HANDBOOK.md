# ISE AI Developer Handbook

## Overview
ISE AI is a local-first AI engineering workspace with a FastAPI backend, React/Vite frontend, artifact persistence, project analysis, planning workflows, terminal execution, and self-improvement agents. The system is designed to analyze uploaded repositories, plan changes, modify code, test the result, and surface downloadable outputs.

## Current Architecture
### Backend
- `backend/app/main.py`: FastAPI composition root and router registration.
- `backend/app/api/`: API surface for chat, project analysis, terminal, approvals, docs, dashboard, and optional extensions.
- `backend/app/services/`: agent orchestration, planning, artifact storage, workspace staging, exports, search, terminal execution, and sandbox helpers.
- `backend/app/schemas/`: Pydantic request and response models.

### Frontend
- `frontend/src/App.jsx`: application state, session lifecycle, uploads, and streaming orchestration.
- `frontend/src/components/ChatLayout.jsx`: shell and navigation between dashboard, chat, terminal, and docs.
- `frontend/src/components/DashboardView.jsx`: capabilities, artifacts, approvals, operations, and runtime overview.
- `frontend/src/components/DocumentationView.jsx`: markdown-driven documentation renderer.
- `frontend/src/components/TerminalPanel.jsx`: terminal execution surface.

## Execution Model
1. The user starts in chat or dashboard.
2. Files or archives are uploaded and stored as artifacts.
3. The agent builds context from uploaded artifacts, docs, and codebase maps.
4. Planning or coding services stage or write changes.
5. Generated results are persisted as artifacts.
6. Project exports can be packaged as zip downloads.

## Artifact System
Artifacts can represent:
- uploaded files
- search and research outputs
- generated images or other media
- exported projects as zip archives

Artifacts live in MongoDB when available and fall back to in-memory storage when not.

## Project Export Flow
### Goal
When the agent creates a landing page or another full project, the user should be able to download the complete result as a zip file without manual shell work.

### Implementation
- `backend/app/services/project_exports.py` packages a folder into a zip.
- `POST /api/project/export` creates a downloadable project-export artifact.
- `/api/artifacts/{artifact_id}/download` now supports binary file downloads in addition to plain text artifacts.
- The dashboard includes a dedicated export panel.

## Terminal
The terminal UI uses `POST /api/terminal/run`. The frontend must point to `/api/terminal` as its base path and append `/run` exactly once.

## Documentation Strategy
The documentation view expects this handbook at `docs/ISE_DEVELOPER_HANDBOOK.md`. Keep this file updated whenever:
- routes change
- new services are added
- export behavior changes
- dashboard workflows change

## Safe Improvement Rules
- Prefer additive changes.
- Keep compatibility with in-memory fallback mode.
- Avoid destructive file operations outside project roots.
- Exclude heavy folders like `node_modules`, `.git`, and caches from exports.

## Known Improvement Areas
- Add integration tests for export flows.
- Improve progress reporting from project export actions.
- Surface direct download CTA inside chat render blocks.
- Add per-session output roots for exports initiated from the dashboard.
