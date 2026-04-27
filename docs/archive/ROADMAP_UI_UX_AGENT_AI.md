# Agent AI UI/UX Roadmap and Phase 43 Fixes

## Immediate fixes implemented

1. **Live execution timer**
   - Added a reusable `useRunningElapsed` hook in `frontend/src/components/MessageList.jsx`.
   - The timer now advances every second while the agent status is `running`, `working`, `pending`, `queued`, or `in_progress`.
   - The UI no longer depends only on a static `timing.elapsed_seconds` value from the backend payload.

2. **Moving progress bar**
   - Agent timeline progress now combines completed-step progress with elapsed-time progress.
   - Pending/running states show a non-zero live progress value instead of appearing frozen.
   - Running progress is capped below 100% until completion to avoid fake “done” states.

3. **Plan progress consistency**
   - `PlanResultBlock` now uses the same live elapsed-time logic as `AgentTimelineBlock`.
   - Pending steps can show active progress instead of staying at 0% until all steps complete.

4. **Code preview UX**
   - Strengthened the inline code preview styling so generated file previews look closer to normal generated code blocks.
   - Added missing token colors for keywords and plain text.
   - Improved monospace layout, dark code background, line hover state, and language label styling.

5. **Execution credibility**
   - The UI now better represents live work instead of making fast sandbox responses look like mocked data.
   - The renderer remains compatible with real backend events and degrades gracefully when timing metadata is incomplete.

## Product roadmap

### Phase 1 — Stabilize live execution feedback
- Normalize backend status names: `queued`, `planning`, `running`, `verifying`, `exporting`, `completed`, `failed`.
- Stream step events over SSE/WebSocket instead of relying on final batch payloads.
- Display real timestamps per event: created, started, completed, duration.
- Add explicit labels for simulated, cached, sandboxed, and live LLM-generated work.

### Phase 2 — Clean task output hierarchy
- Collapse noisy logs by default.
- Show three primary areas only: Roadmap, Live execution, Result artifacts.
- Move verbose planner memories, raw JSON, and diagnostics into expandable developer details.
- Keep the download action sticky at the bottom of the result card.

### Phase 3 — Better file and code review
- Use one shared code-block component for chat code, generated files, diffs, and previews.
- Add file tabs for multi-file outputs.
- Add syntax-aware highlighting through a lightweight highlighter package when dependencies are available.
- Show generated `.scss`, `.jsx`, and package files in a clear tree.

### Phase 4 — Agent trust and verification
- Show which model/provider generated each step.
- Show verification commands and actual command output separately from generated content.
- Add warnings when node modules or test dependencies are missing.
- Add SHA and manifest details behind a “Verification details” disclosure.

### Phase 5 — Polished Agent AI workbench
- Split the interface into Planner, Builder, Verifier, and Export lanes.
- Add animated live status chips for each agent.
- Add “Apply to project”, “Download ZIP”, and “Preview result” as first-class actions.
- Add recovery UX for failed runs: retry failed step, inspect logs, or export partial result.

## Files changed

- `frontend/src/components/MessageList.jsx`
- `frontend/src/styles/global.css`
- `ROADMAP_UI_UX_AGENT_AI.md`

## Verification note

A frontend build was attempted with `npm run build`, but the uploaded ZIP does not include `frontend/node_modules`, so Vite was unavailable in this sandbox. Run `npm install` inside `frontend/` and then `npm run build` locally to verify the full app bundle.
