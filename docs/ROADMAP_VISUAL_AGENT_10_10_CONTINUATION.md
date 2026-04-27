# Visual + Dynamic Programming AGI Roadmap — 10/10 Continuation

This continuation upgrades the agent from a strong visual runner into a Codex-style programming workspace that can inspect, patch, retry, preview, export, and explain results without falling back to canned templates.

## Phase V10-1 — Real preview lifecycle
- Detect browser-renderable artifacts automatically.
- Return a preview contract containing command, cwd, preview id, and URL.
- Keep preview blocked until verification passes.
- Display an Open Preview action beside file/project actions.

## Phase V10-2 — Per-file developer actions
- Render generated files as an IDE-like tree.
- Show file-type icons by extension.
- Add Preview and Download actions for every file.
- Add a selected-file preview panel with the same download action.

## Phase V10-3 — Workspace path resolver
- Remove hardcoded default paths.
- Parse prompts such as `you are now in ~/Desktop/Easv/`, `your current folder are ...`, and `based on the content of this folder ...`.
- Use the resolved folder as the source for sandbox copy/edit flows.

## Phase V10-4 — Codex-style repair loop
- Every failed verifier/build command enters inspect → patch → rerun.
- Banned markers are repaired in the exact file that contains them.
- Missing imports produce missing files or corrected imports.
- Full-stack gaps trigger the correct sub-agent instead of exporting partial work.

## Phase V10-5 — Tool routing layer
- Route internet/docs learning to WebResearchAgent.
- Route image/asset requests to ImageGenerationAgent.
- Route file/project inspection to ProjectSearchAgent.
- Route previewable frontend work to PreviewAgent.

## Phase V10-6 — Minimal edit discipline
- Text-change requests patch exact text only.
- Do not regenerate full projects for title/button/content edits.
- Show patch evidence in the dashboard.

## Phase V10-7 — Trust-first dashboard
- Outcome first, logs second.
- Show current folder, selected tools, repair attempts, preview status, and export gate state.
- Show no fake 95% progress; progress is derived from step statuses.

## Phase V10-8 — Export discipline
- ZIP/export remains blocked while verification fails.
- A valid browser preview is allowed before ZIP only after frontend verification.
- Merge remains approval-only and target-path controlled.
