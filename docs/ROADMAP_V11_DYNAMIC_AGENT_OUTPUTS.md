# Roadmap v11 — Dynamic Agent Outputs and Daily Programmer UX

## Goal
Make the unified Agent produce task-specific UI, code, previews, debugging flows, and artifacts instead of generic/static responses.

## Critical phases implemented

1. **Dynamic output intelligence**
   - Add a backend planner that classifies each task as chat, file, preview, project, design, data, image, or debug.
   - Return the specialist agents, visual components, and self-healing loop that should render in chat.

2. **Task-specific visual rendering**
   - Add render blocks for routing contracts, metric grids, file galleries, repair loops, and Agent loop state.
   - Avoid one generic Agent card for every response.

3. **Stronger self-healing surface**
   - Every dynamic plan includes a repair phase: think → analyze → patch → rerun → verify.
   - Debugging requests use visual repair-loop cards first.

4. **Daily-programmer components**
   - Data/table output for payloads and diagnostics.
   - Metric grid for verification and progress signals.
   - File gallery for generated or touched files.
   - Terminal/debug panels for execution evidence.

5. **More specific Agent run steps**
   - Replace generic roadmap/frontend/backend wording with request-specific execution labels.
   - Clarify that verification checks content fidelity, preview readiness, imports, and build gates.

6. **Frontend resilience**
   - Fixed a malformed progress-icon JSX block.
   - Added animated dynamic visual surfaces.
   - Registered a new visual metric grid component.

## Next target
Convert the dynamic output plan from advisory blocks into the primary orchestration contract, so the backend run itself is selected from this plan before any execution begins.
