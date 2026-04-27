# Implementation Report: Chat Result Contract and Direct File Output

## Fixed gap
A PDF request was incorrectly rendered as a Programming Agent app-preview run. The UI showed a preview command and ZIP-style workflow instead of the requested downloadable PDF.

## Changes
- `backend/app/services/agent_task_router.py`
  - Added `artifact_generate` route.
  - Added `output_kind` and `suggested_extension` fields.
  - Detects direct downloadable file requests and routes them to `/api/devx/files/generate`.

- `frontend/src/App.jsx`
  - Added `detectDirectFileArtifactRequest`.
  - Direct PDF/DOCX/TXT/etc requests now call the downloadable file API.
  - The Agent chat response renders a file download card and file preview instead of app preview timeline.

- `frontend/src/components/MessageList.jsx`
  - Download card now uses file icons/extensions.
  - Button label now says `Download PDF`, `Download TXT`, etc. instead of always `Download ZIP`.

## Expected behavior
Prompt:
> put this message -> "Hello world" into a pdf file then give me the downloadable pdf file

Expected UI:
- Assistant says the PDF was created.
- Shows a PDF card with icon, size, hash, and `Download PDF` button.
- Shows file content preview: `Hello world`.
- Does not show app preview, localhost port, Vite command, or ZIP-only workflow.
