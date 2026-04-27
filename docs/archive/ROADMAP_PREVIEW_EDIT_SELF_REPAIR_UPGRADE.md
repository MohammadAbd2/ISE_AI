# Roadmap — Preview, Minimal Edits, and Codex-Style Self-Repair Upgrade

## Goal
Make ISE AI behave like a real programming agent instead of a static artifact generator. The agent must preserve successful generated apps, offer browser previews for UI work, apply focused edits when the user asks for a small change, and continue repairing verifier/terminal failures until the artifact is valid or the repair budget is exhausted.

## Phase 1 — Browser preview contract
- Detect whether the generated result is browser-displayable.
- Return a preview contract with `available`, `url`, `command`, `cwd`, and `preview_id`.
- Block preview until verification passes.
- Surface the preview action in the dashboard result card.

## Phase 2 — Minimal edit intent mode
- Detect edit prompts like `change the title from "General Application" to "webstore application"`.
- Apply exact text patches to sandbox/project files.
- Prevent full regeneration for focused edits.
- Emit `PATCH_REPORT.json` with changed files and blockers.

## Phase 3 — Project-path aware sandbox loading
- When a project path is supplied, read source files into the sandbox file graph.
- Skip dependency/build/cache folders.
- Patch copied sandbox files instead of rewriting the project from a generic generator.

## Phase 4 — Stronger self-repair loop
- Verification failures become structured DebugAgent repair attempts.
- Banned marker failures trigger content cleanup.
- Structural failures trigger stack-specific artifact regeneration.
- Import failures trigger missing-file repair.
- Export remains blocked until verification passes.

## Phase 5 — Dashboard clarity
- Show preview status separately from export status.
- Show repair attempts and remaining failures.
- Show changed files and verification evidence.
- Keep logs available but not as the primary result.

## Phase 6 — Future next step
- Add real terminal command execution events for `npm install`, `npm run build`, backend checks, and preview startup.
- Add merge endpoint that copies verified sandbox changes to an approved target path only after user confirmation.
