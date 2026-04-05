# ISE AI

ISE AI is a self-hosted AI workspace built around a React frontend and a FastAPI backend. It combines chat, coding-agent workflows, uploaded project understanding, typed UI artifacts, dashboard tooling, and dynamic visualization in one session-aware interface.

The project is no longer just a chatbot shell. It now includes:

- shared intent routing across frontend and backend
- autonomous coding and planning agents with verification
- **multi-agent orchestration with 11 specialized agents and sub-agents**
- **IDE extensions for VS Code and JetBrains (PyCharm, IntelliJ, etc.)**
- **Copilot-like features: inline completions, chat, code actions**
- uploaded ZIP/project analysis with extracted framework metadata
- artifact-style chat outputs for reports, files, plans, and visualizations
- reusable dashboard/workspace generation paths for tools and analytics
- session-aware analytics surfaces that can reopen prior context

## Current Scope

Core implemented capabilities:

- Chat with streamed responses over `POST /api/chat/stream`
- Mode routing for `chat`, `coding`, `research`, `visualization`, and `project_analysis`
- File upload and archive ingestion for project context
- Session artifact listing and download
- Inline 2D chart and 3D map rendering in chat
- Voice input in the frontend via browser speech APIs
- Dashboard surface for tools, capabilities, uploaded context, and live visualizations
- Coding agent with:
  - task understanding
  - existing-file target discovery
  - multi-file generation
  - diffs
  - verification commands
  - one repair attempt
- Planning agent with:
  - explicit/implicit multi-step parsing
  - project-aware step enrichment
  - verification step resolution
  - structured plan results in chat
- **Multi-Agent Orchestration with 11 agents:**
  - **6 main agents (Planning, Coding, Research, Review, Testing, Documentation)**
  - **5 sub-agents (Python, JavaScript, API, Security, Performance)**
  - **Intelligent task decomposition and routing**
  - **Multi-agent collaboration workflows**
- **IDE Extensions (Copilot Alternative):**
  - **VS Code Extension with inline completions, chat, and code actions**
  - **JetBrains Plugin (PyCharm, IntelliJ, WebStorm, etc.)**
  - **Keyboard shortcuts for quick actions**
  - **Context-aware code generation and review**
- Reusable generation flows for:
  - dashboard components
  - workspace views/tabs
  - dashboard tools
  - analytics dashboards

What it is not yet:

- a frontier base model like ChatGPT, Claude, or Gemini
- a full hosted speech stack with backend STT/TTS
- a complete multi-provider model router

## Architecture

```text
frontend (React + Vite)
  - App shell with Chat and Dashboard surfaces
  - Composer with uploads and voice button
  - Message renderer for typed artifacts
  - DynamicVisualization for chart/map rendering
  - Hooks for session artifacts and session analytics

backend (FastAPI)
  - chat routes
  - evolution routes
  - learning/planning routes
  - orchestrator
  - coding agent
  - planning agent
  - document/archive ingestion
  - history and artifact services

storage
  - MongoDB if available
  - in-memory fallback when MongoDB is unavailable
```

Important backend entrypoints:

- [backend/app/main.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/main.py)
- [backend/app/api/routes.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/routes.py)
- [backend/app/api/evolution_routes.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/evolution_routes.py)
- [backend/app/api/learning_routes.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/learning_routes.py)

Important frontend entrypoints:

- [frontend/src/App.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/App.jsx)
- [frontend/src/components/ChatLayout.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/ChatLayout.jsx)
- [frontend/src/components/DashboardView.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/DashboardView.jsx)
- [frontend/src/components/MessageList.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/MessageList.jsx)

## Key Systems

### Intent Routing

Routing is shared across frontend and backend so visualization or project-analysis prompts do not get misrouted into code-generation flows.

- Frontend: [taskIntent.js](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/lib/taskIntent.js)
- Backend: [intent_classifier.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/intent_classifier.py)

### Coding Agent

The coding agent is project-aware and verification-aware.

- Main file: [intelligent_coding_agent.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/intelligent_coding_agent.py)

Implemented behaviors include:

- create/edit file flows
- existing target resolution
- React/FastAPI-specific edits
- router registration in `backend/app/main.py`
- dashboard component registration in `DashboardView.jsx`
- workspace view registration in `App.jsx` and `ChatLayout.jsx`
- dashboard tool registration in `.evolution-tools.json` and `.evolution-registry.json`
- analytics dashboard generation using `DynamicVisualization`

### Planning Agent

The planner now uses project context instead of relying only on text parsing.

- Main file: [planning_agent.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/planning_agent.py)

Implemented behaviors include:

- explicit and implicit step parsing
- project-aware file step enrichment
- verification command resolution
- structured plan-result cards in chat

### Project / ZIP Understanding

Uploaded archives are treated as project context, not just generic text.

- Main file: [documents.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/documents.py)

Archive ingestion extracts:

- frameworks
- dependency signals
- important config files
- prioritized source snippets
- top-level project structure

### Typed Artifact Rendering

Chat messages can render structured blocks, not only plain text.

Supported block types currently include:

- `visualization`
- `report`
- `file_result`
- `plan_result`

Main renderer:

- [MessageList.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/MessageList.jsx)

### Visualization and Analytics

The visualization path supports both ad hoc chat rendering and reusable analytics surfaces.

- [visualization.js](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/lib/visualization.js)
- [DynamicVisualization.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/DynamicVisualization.jsx)
- [useSessionAnalytics.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/hooks/useSessionAnalytics.jsx)

Implemented behaviors include:

- 2D chart parsing from free-form text
- 3D map parsing from coordinate rows
- synthetic yearly salary/profit chart generation
- analytical summary blocks for charts/maps
- structured export-style file blocks for visualization data
- session analytics endpoint for reopening prior visualization context

## API Surfaces

Main routes:

- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/models`
- `GET /api/chats`
- `GET /api/chats/{session_id}`
- `DELETE /api/chats/{session_id}`
- `DELETE /api/chats`
- `GET /api/ai/profile`
- `PUT /api/ai/profile`
- `POST /api/files/upload`
- `GET /api/artifacts`
- `GET /api/artifacts/{artifact_id}/download`
- `GET /api/session-analytics`

Evolution/registry routes:

- `GET /api/evolution/tools`
- `GET /api/evolution/capabilities`
- `GET /api/evolution/status`
- backup / approval / log routes under `/api/evolution/*`

## Setup

### Backend

Requirements file:

- [backend/requirements.txt](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/requirements.txt)

Install and run:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

Package file:

- [frontend/package.json](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/package.json)

Install and run:

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL is usually `http://localhost:5173`.

Backend API base URL defaults to `http://localhost:8000` and can be overridden with:

```bash
VITE_API_ROOT=http://localhost:8000
```

### IDE Extensions (Copilot Alternative)

**Quick Setup:**

```bash
# Build both extensions
./build_extensions.sh

# Install VS Code extension
code --install-extension extensions/vscode/ise-ai-copilot-*.vsix

# Install JetBrains plugin
# In your IDE: Settings → Plugins → Install from Disk → select .zip file
```

**See:**
- [QUICKSTART.md](/home/baron/Desktop/Easv/Ai/ISE_AI/QUICKSTART.md) - Complete setup guide
- [MULTI_AGENT_README.md](/home/baron/Desktop/Easv/Ai/ISE_AI/MULTI_AGENT_README.md) - Multi-agent documentation
- [IMPLEMENTATION_SUMMARY.md](/home/baron/Desktop/Easv/Ai/ISE_AI/IMPLEMENTATION_SUMMARY.md) - What was implemented

## Verification

Frontend:

```bash
cd frontend
npm run test:eval
npm run build
```

Backend:

```bash
python -m unittest tests/test_backend_eval.py -v
python -m compileall backend/app
```

The repo includes eval coverage for:

- intent routing
- archive extraction
- verification command selection
- existing-file edit behavior
- repair behavior
- planning enrichment
- workspace/dashboard/tool generation
- analytics dashboard generation
- session analytics payload assembly

## Notable Files

Backend:

- [backend/app/services/orchestrator.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/orchestrator.py)
- [backend/app/services/intelligent_coding_agent.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/intelligent_coding_agent.py)
- [backend/app/services/planning_agent.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/planning_agent.py)
- [backend/app/services/documents.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/documents.py)
- [backend/app/services/session_analytics.py](/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/session_analytics.py)

Frontend:

- [frontend/src/components/Composer.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/Composer.jsx)
- [frontend/src/components/FeaturesPanel.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/FeaturesPanel.jsx)
- [frontend/src/components/DynamicVisualization.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/components/DynamicVisualization.jsx)
- [frontend/src/hooks/useVoiceCommand.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/hooks/useVoiceCommand.jsx)
- [frontend/src/hooks/useSessionAnalytics.jsx](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/hooks/useSessionAnalytics.jsx)
- [frontend/src/lib/visualization.js](/home/baron/Desktop/Easv/Ai/ISE_AI/frontend/src/lib/visualization.js)

## Docs

There is additional historical/project documentation in [docs](/home/baron/Desktop/Easv/Ai/ISE_AI/docs). Some files there describe earlier versions of the system, so treat this README and the current codebase as the source of truth.

## Next Directions

The strongest remaining improvements are:

- model/provider routing instead of one broad path
- backend speech-to-text / text-to-speech
- persistent analytics-spec artifacts created directly during chat turns
- more robust multi-file semantic editing beyond pattern-based edits
- stronger test/eval coverage for full end-to-end feature generation
