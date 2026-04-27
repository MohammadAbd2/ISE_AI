# Roadmap: Chat Result Contract and Output-First Agent UI

## Problem
The chat Agent currently routes many output requests through the full Programming Agent app-preview workflow. A simple request such as “put Hello world into a PDF and give me the downloadable file” should produce a PDF artifact card immediately, not a generated React preview, ZIP export, or generic sandbox timeline.

## North Star
Every chat response should display the result type the user asked for: direct files as file cards, runnable apps as preview cards, coding work as diff/build cards, web tasks as deduplicated source cards, image tasks as vision/image cards, and long-running tasks as terminal/timeline cards.

## Phase 1 — Result intent routing
- Add deterministic routing for direct downloadable files.
- Detect requested extension: PDF, DOCX, TXT, MD, JSON, JS, JSX, TS, TSX, HTML, CSS, PY.
- Route direct artifact requests to the artifact generator instead of app preview.
- Keep full Agent execution for project/app/backend/frontend/debug/refactor tasks.

## Phase 2 — Chat output contract
Every Agent/chat result should expose:
- `output_kind`: message, downloadable_file, project_export, preview_app, diagram, image, terminal_run, code_patch.
- `primary_artifact`: one main result the UI should emphasize.
- `secondary_blocks`: supporting evidence only.
- `actions`: download, preview, apply patch, retry, open folder.

## Phase 3 — Output-first frontend rendering
- Show one primary card at the top.
- Hide unrelated preview/run cards when the task is a direct file artifact.
- Use file-type icons and extension-specific download labels.
- Show a compact content preview under the file card.

## Phase 4 — Agent evidence without clutter
- Display execution proof only when relevant.
- Collapse long timelines by default.
- Show “why this route was selected” only as a secondary expandable block.

## Phase 5 — Regression tests
Add test prompts:
- “Put Hello world into a PDF file and give me the downloadable PDF.”
- “Create test.txt with Hello world and give me the file.”
- “Build a React dashboard and give me a preview.”
- “Fix this project and export a ZIP.”

## Implemented in this iteration
- Backend task router recognizes direct downloadable file requests.
- Frontend detects direct file artifact requests after the router decision.
- Direct PDF/TXT/etc requests call `/api/devx/files/generate`.
- Chat shows a proper download card and file preview.
- Generic preview/ZIP Agent UI is skipped for direct file output.
