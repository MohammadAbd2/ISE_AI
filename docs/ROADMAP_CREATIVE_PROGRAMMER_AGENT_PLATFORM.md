# Creative Programmer AGI Agent Roadmap

## Vision
Turn ISE AI into a daily programmer companion that can chat, plan, execute, generate downloadable outputs, inspect images, draw diagrams, and safely edit a chosen workspace from the web UI, VS Code, or JetBrains.

## Phase 1 — Stable Agent Contract
- One route for chat/task routing so the frontend does not guess silently.
- Shared result schema: summary, plan, timeline, artifacts, files, diagrams, images, warnings.
- Deduplicate web resources and image resources before display.
- Never crash the UI on partial backend failures; return degraded states.

## Phase 2 — Downloadable Output Studio — started here
- Add backend `/api/devx/files/generate` to create `.txt`, `.md`, `.js`, `.jsx`, `.ts`, `.tsx`, `.json`, `.html`, `.css`, `.py`, `.pdf`, and `.docx` artifacts.
- Store generated outputs as ChromaDB artifacts and expose normal artifact download links.
- Frontend renderer should display a file card with icon, language, size, and download action.
- Agent contract: when the user asks for a file, return both chat summary and downloadable artifact metadata.

## Phase 3 — Image + Vision Upgrade — started here
- Add provider abstraction for image generation with local fallback, Gemini/Nano Banana-style environment hook, and future OpenAI/SD hooks.
- Add `/api/devx/images/generate` and `/api/devx/images/analyze` so Chat, AGI, and Agent can create or inspect images.
- Frontend should render generated image previews directly, not base64 text.

## Phase 4 — Dynamic Diagram Engine — started here
- Add `/api/devx/diagrams/generate` for Mermaid, flowcharts, sequence diagrams, JSON data charts, and architecture diagrams.
- Agent can turn plans, logs, CSV-like data, or codebase maps into visual diagrams.
- Frontend should render diagram cards and allow downloading `.mmd` or `.html`.

## Phase 5 — Workspace + IDE Bridge — started here
- Add `/api/devx/workspaces` to remember safe working folders by label.
- Add workspace validation to avoid accidental system-root editing.
- VS Code extension: better sidebar, connect to backend, set workspace, send selection/file/project task.
- JetBrains plugin scaffold: tool window, backend URL, workspace registration, selected file actions.

## Phase 6 — Self-Development Loop
- Agent can propose its own roadmap, create a patch plan, implement a slice, test it, and save lessons to ChromaDB.
- Add approval gates before merge into the user's real workspace.
- Add rollback and diff preview before write operations.

## Phase 7 — Programmer Daily Life Automation
- Morning project summary, stale branch cleanup, PR review assistant, dependency audit, changelog creator, release notes generator.
- Bug reproduction recorder and terminal command planner.
- “Explain this error” from IDE selection with memory of previous fixes.

## Next roadmap after this package
1. Convert all chat/agent responses to a versioned `AgentResultEnvelope`.
2. Render downloadable file cards in the chat timeline.
3. Add IDE auth token support and trusted workspace allowlist.
4. Add a diagram preview component backed by Mermaid.
5. Add image understanding from uploaded files and web images.
6. Add route smoke tests for every new route.
