# Visual Agent + Dynamic Workflow Upgrade Roadmap

## Goal
Raise ISE AI from approximately 5/10 to at least 8/10 in frontend visualization, agent routing, output clarity, and dynamic programming usefulness.

## Phase 1 — File visualization intelligence
- Render generated output as a collapsible folder tree.
- Display folder icons and arrow expand/collapse controls.
- Display file-type icons for `.jsx`, `.js`, `.css`, `.cs`, `.sql`, `.json`, `.md`, `.yml`, and more.
- Add per-file Preview and Download buttons beside each file.

## Phase 2 — Dynamic current-folder control
- Remove the stale default path from frontend placeholders.
- Allow prompts such as:
  - `your current folder are ~/Desktop/Easv/`
  - `you are now in ~/Desktop/Easv/`
  - `based on the content of this folder ~/Desktop/Easv/`
- Backend extracts those paths and treats them as the active workspace.

## Phase 3 — Workspace-aware sandbox execution
- Copy active project folders to sandbox before modifying them.
- Keep original files untouched until explicit merge approval.
- Show the currently active folder in the result view.

## Phase 4 — Tool-capability routing
- Add explicit capability routes for:
  - project filesystem search
  - browser preview
  - internet research when requested
  - image/media generation when requested
  - terminal verification and self-repair
- Display selected capabilities in the frontend so the user knows which tools the agent used or prepared.

## Phase 5 — Frontend trust panel
- Replace flat file lists with structured file tree + previews.
- Keep ZIP export and browser preview visible, but make individual file download available too.
- Show verification evidence only behind details.

## Phase 6 — Agent performance target
- No template fallback.
- No hardcoded output paths.
- No fake progress.
- Every visible result should be backed by task contract, current folder, generated files, verifier result, and repair status.

## Implemented files
- `frontend/src/components/AgentFileTree.jsx`
- `frontend/src/lib/fileVisuals.js`
- `frontend/src/styles/agent-file-tree.css`
- `frontend/src/components/MaximumDynamicAgentPanel.jsx`
- `frontend/src/styles/maximum-dynamic-agent.css`
- `backend/app/services/maximum_dynamic_agent.py`
- `frontend/src/components/DailyProgrammingAGIPanel.jsx`
