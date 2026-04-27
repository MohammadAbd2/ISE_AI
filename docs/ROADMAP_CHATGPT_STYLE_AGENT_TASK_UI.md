# Roadmap: ChatGPT-Style Agent Task UI

## Goal
Make every Agent task response feel like ChatGPT task execution: a concise assistant message, a collapsible **Thinking** section, visible tool/terminal evidence when useful, and the correct final artifact/result card.

## Phase 1 — Unified result contract
- Every backend task returns render blocks instead of raw runtime noise.
- Each block has a type: `thinking_trace`, `terminal_command`, `download_card`, `file_preview`, `folder_listing`, `agent_timeline`, `resource_list`, or `diagram`.
- Simple file-generation requests return direct downloadable artifacts, not app previews.

## Phase 2 — ChatGPT-like task trace
- Show a compact **Thinking** row above task results.
- Clicking the row expands planning, routing, command, verification, and artifact-registration details.
- Keep final chat text short and outcome-first.

## Phase 3 — Tool and terminal cards
- Render shell commands as command cards with stdout/stderr previews.
- Collapse noisy logs by default.
- Show failure evidence clearly and link failed checks to repair actions.

## Phase 4 — Result-first artifacts
- For PDF/DOCX/TXT/JS/JSX/etc. requests, show the exact downloadable file card first.
- For app/project requests, show preview, changed files, build status, and ZIP export.
- Avoid duplicate source/resource lists.

## Phase 5 — Progressive streaming
- Replace static “completed” states with live NDJSON/SSE updates.
- Update the same assistant message in place.
- Allow cancel/retry from the message card.

## Phase 6 — IDE-grade task detail
- Add diff viewers, file tree, generated files, command history, and verification summaries.
- Clicking a result title opens the expanded details panel.

## Implementation started in this package
- Added `thinking_trace` render block.
- Added collapsible `Thinking` card in chat messages.
- Direct artifact generation now shows Thinking → Download Card → File Preview.
- Agent execution now shows Thinking → Agent Timeline → Result cards.
- Added CSS for ChatGPT-style compact expandable task traces.
