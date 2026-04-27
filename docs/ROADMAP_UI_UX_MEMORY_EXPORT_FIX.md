# Roadmap — UI/UX, Export Gates, Docs Cleanup, and Shared Memory Upgrade

## 1. Repair the export blockers
- Validate only the active artifact graph for the current run.
- Exclude copied legacy files, temp folders, AGI state folders, vector caches, and stale memory artifacts from export gates.
- If `no_template_markers` or `import_graph_resolves` fails, RepairAgent rewrites the exact active graph and re-runs validation before ExportAgent is allowed to create a ZIP.

## 2. Move documentation into `docs/`
- Root-level `.md` files are moved into `docs/archive/`.
- New implementation notes live in `docs/implementation/`.
- Generated projects now use `docs/ROADMAP.md` and `docs/README.md` instead of root roadmap/readme files.

## 3. Remove misleading files
- Remove temporary files, stale manifest JSON, vector/embedding/cache files, old `.ise_ai` state, local DB files, and accidental test files from the distributed project.
- Keep source code and runtime state schemas only.

## 4. Shared AGI memory module
- Add short-term memory for the current run: request, sandbox path, steps, source path, and updated timestamp.
- Add long-term memory for workflow lessons and repair behavior, without storing final-code templates.
- Expose memory context so AI, Agent, and AGI can read the same context.

## 5. Cleaner UI/UX result model
- Dashboard should present outcome first, then blockers, repair attempts, file tree, preview/export actions, and memory state.
- Export errors should be shown as actionable gates, not generic failures.

## 6. Safer sandbox/output lifecycle
- Use `AGI_Output` as the default safe workspace.
- Never copy `AGI_Output`, `.ise_ai`, `sandboxes`, `exports`, `node_modules`, build output, or cache folders into a sandbox.
- For create-new-project prompts, prune unrelated copied files before verification.

## 7. Stronger verification contract
- Required files are based on the task contract.
- Import resolution supports `.js`, `.jsx`, `.ts`, `.tsx`, `.css`, and `index.*` imports.
- Export is blocked only when the active generated artifact still fails validation after repair.
