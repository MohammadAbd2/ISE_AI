# Roadmap: Fix Chat-to-Agent Gaps for Isolated Filesystem Tasks

## Problem found from the chat transcript
The chatbot treated a simple filesystem instruction as a generic project-generation task. When the user asked it to create `test.txt`, verify the content, list the isolated environment, and later provide a ZIP, the system showed a canned Programming AGI project response instead of the actual requested file operation and download.

## Root causes
1. **Intent gap**: direct filesystem tasks were routed into the generic app-generation runtime.
2. **Missing exact-action mode**: the runtime did not have a fast path for create/update/list/export inside the isolated environment.
3. **Download gap**: generated ZIP paths were not always registered as downloadable artifacts, so the UI could display evidence without a real download button.
4. **UI contract gap**: folder listings, file previews, and download cards were not first-class render blocks.

## Implemented in this package
- Added direct isolated filesystem task detection.
- Added exact create/update/list execution for sandbox file requests.
- Added previous-sandbox ZIP export for requests like “give me a downloadable zip file for the isolated env”.
- Added folder listing and file content evidence to the backend UI contract.
- Registered exported ZIPs as ChromaDB artifacts with `/api/artifacts/{id}/download` URLs.
- Added frontend render blocks for folder listings, file previews, and download cards.
- Added a Programming AGI roadmap phase for direct filesystem tasks.

## Expected behavior now
### Request
`create a new file called test.txt in isolated env then update the content of this file to be "Test from isolated env" then display the content of the isolated env folder for me here`

### Response should include
- A clear statement that `test.txt` was created.
- The exact content: `Test from isolated env`.
- A folder listing showing `test.txt` only, unless the sandbox has requested generated files.
- No fake React preview or generic app scaffold unless the user asked for an app.

### Request
`now give me a downloadable zip file for the content of the isolated env`

### Response should include
- A download card with a real ZIP artifact link.
- File count, size, and SHA-256 when available.
- A folder listing of the exported sandbox.

## Next roadmap
1. Add natural-language file operation parser for multiple files and nested folders.
2. Add diff preview before writing to a remembered project folder.
3. Add permission modes: sandbox-only, ask-before-merge, auto-merge allowed paths.
4. Add terminal command evidence for each requested operation.
5. Add regression tests for chat transcripts so this bug does not come back.
6. Add UI smoke tests for download cards and folder listing render blocks.
