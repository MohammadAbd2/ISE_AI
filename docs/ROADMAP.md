# ISE AI Improvement Roadmap

## Phase 1 — Stabilize the foundation
1. Fix Python test discovery and import paths.
2. Ensure backend services gracefully fall back when MongoDB or bson are missing.
3. Repair broken documentation loading.
4. Fix terminal endpoint mismatches between frontend and backend.

## Phase 2 — Make project generation deliverable
1. Standardize where generated projects are written.
2. Package generated projects into zip files.
3. Register exports as downloadable artifacts.
4. Add dashboard controls so users can export with one click.

## Phase 3 — Strengthen agent workflows
1. Improve project-name extraction and output naming.
2. Persist more execution metadata for generated apps.
3. Add clearer approval and merge summaries.
4. Add tests around merge plus export behavior.

## Phase 4 — Upgrade dashboard and docs
1. Surface recent exports and downloadable artifacts more clearly.
2. Show session status, approvals, and runtime actions together.
3. Expand the developer handbook with architecture, routes, and extension guidance.
4. Keep the README aligned with real capabilities.

## Phase 5 — Hardening and polish
1. Run backend tests.
2. Build the frontend.
3. Fix regressions.
4. Package the improved repository for delivery.

## Additional hardening completed in this revision

- Route normal coding tasks away from self-upgrade unless the user explicitly requests self-improvement.
- Run terminal verification commands from the correct working directory, including frontend builds.
- Persist sandbox workspaces under `output/sandboxes/` so they can be reviewed, zipped, and merged later.
- Create a backup before merge and clean backups older than 30 days at startup.
- Surface sandbox ZIP exports directly through chat artifacts.
- Improve terminal UX with configurable working directory support.
- Improve tool suggestion ranking using tool descriptions and semantic aliases.
