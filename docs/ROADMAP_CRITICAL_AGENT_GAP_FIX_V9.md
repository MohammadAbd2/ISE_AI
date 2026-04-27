# Critical Agent Gap Fix Roadmap v9

North star: the chat Agent must choose the exact specialist for the user's request, execute the real action, verify the output, self-repair errors, and render the result with the best visual component in the chat tab.

## Phase 1 — Routing correctness
- Strictly route file creation to FileArtifactAgent.
- Strictly route file location questions to FileSystemAgent.
- Strictly route static HTML/browser preview tasks to StaticPreviewAgent.
- Strictly route Figma/design/prototype tasks to FigmaDesignAgent.
- Send only true app/project requests to the full implementation Agent.
- Show route decision and confidence in UI trace blocks.

## Phase 2 — File-content reliability
- Use atomic writes for all generated files.
- Verify exact text content for text-like outputs.
- Store sha256, size, attempts, and verification evidence.
- Preserve full user-provided quoted text, including apostrophes and commas.
- Expand PDF/DOCX text rendering so long messages are not silently truncated.

## Phase 3 — Real preview execution
- Start a real preview process for Vite projects.
- Add static HTML preview in chat for single HTML outputs.
- Detect port conflicts and avoid the app's own 5173 port.
- Return preview status, logs, process id, and URL.
- Fall back to srcDoc preview when host process cannot start.

## Phase 4 — Self-healing execution loop
- Never stop at the first verifier failure.
- Convert blocked gates into repair steps.
- Run analyze → patch → verify until success or retry budget is exhausted.
- Return diagnostics only after repair attempts are complete.

## Phase 5 — Better DebuggingAgent
- Classify errors into import graph, template marker, syntax, dependency, preview, file-write, or unknown.
- Produce root cause, affected files, fix plan, patch actions, rerun command, and memory lesson.
- Render repair loops inside chat.

## Phase 6 — Agent chat result contract
- Normalize every response into result kinds: message_result, file_result, preview_result, project_result, debug_result, figma_result, image_result, data_result, terminal_result.
- Prevent noisy generic Agent cards when the expected output is a file, preview, data, image, or design brief.

## Phase 7 — Agent visual components
- Render file cards, folder trees, code previews, browser previews, image galleries, data tables, JSON viewers, error panels, terminal blocks, Figma cards, download cards, and diffs.
- Use visual components in chat and Agent panel.

## Phase 8 — Figma/design pipeline
- Accept Figma URLs and prompt-to-prototype requests.
- Extract URL metadata and design tokens.
- Create a design brief, component plan, implementation plan, previewable prototype, and exportable files.
- Keep generated work original and avoid copying proprietary assets.

## Phase 9 — IDE write-back reliability
- VS Code and JetBrains detect the current project root and selected file.
- Backend returns safe file rewrite/patch payloads.
- Extensions apply changes locally after user action.
- Refresh editor and show diff/backup information.

## Phase 10 — Memory correctness
- Separate project memory, task memory, failure memory, and preference memory.
- Store failed cases as validators, not as reusable truth.
- Inject only relevant memory into planning and debugging.

## Final quality gates
- No generic app generation for direct file tasks.
- No preview claim without a preview block, URL, or srcDoc preview.
- No hard stop before repair attempts.
- Every downloadable file includes write verification metadata.
- Every design/Figma task includes brief + code/prototype path.
- Every IDE edit returns a patch/write-back contract.
