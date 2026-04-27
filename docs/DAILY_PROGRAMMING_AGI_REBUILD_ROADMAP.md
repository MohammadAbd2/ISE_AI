# Daily Programming AGI Rebuild Roadmap

## Goal
Build a genuinely useful daily programming AGI for practical work: full-stack apps, bug fixes, UI components, backend APIs, database schemas, migrations, refactors, testing, and packaging.

## Why this rewrite was needed
The previous agent failed because it relied on generic fallback templates. A request such as “React + C# + MySQL login page” or “full-stack restaurant app” was reduced to a React landing page. That breaks trust and makes the ZIP unusable.

## Implementation phases

1. **Intent contract first** — every task becomes a typed contract: product type, domain, requested stack, capabilities, deliverables, verification gates, and export blockers.
2. **Stack-aware builders** — React-only, full-stack, auth, restaurant, component, repair, and database work use different plans and file sets.
3. **No-template policy** — hardcoded generic landing/CV markers are treated as export blockers for domain-specific/full-stack tasks.
4. **Real artifact graph** — full-stack work must include frontend, backend, database, docs, config, and verification files.
5. **Verification before ZIP** — the agent must run artifact completeness scans and build checks before exporting.
6. **Repair loop with scope** — missing imports, missing stack layers, and template output are repaired directly instead of generating unrelated files.
7. **Outcome-first UI** — frontend now includes a Daily AGI panel that shows the parsed intent, risk, required files, and export gates.
8. **Admin-ready controls** — strictness can be extended to dashboard settings: template bans, required stacks, retry limits, export rules.
9. **Daily programming workflows** — restaurant apps, login systems, CRUD dashboards, API/database tasks, and repair tasks get explicit playbooks.
10. **Learning loop** — failures should become rules, not copied templates.

## Concrete fixes in this package

- Added `backend/app/services/daily_programming_agi.py`.
- Added `backend/app/api/daily_programming_agi_routes.py`.
- Added `backend/app/services/full_stack_restaurant_blueprint.py`.
- Patched `autonomous_loop_engine.py` so “full stack + React” and restaurant/domain apps no longer fall into React-only generic templates.
- Added a full-stack restaurant blueprint with React frontend, ASP.NET Core API, MySQL schema, Docker Compose, API contract, and verifier script.
- Added `frontend/src/components/DailyProgrammingAGIPanel.jsx`.
- Added `frontend/src/styles/daily-programming-agi.css`.
- Added Daily AGI navigation in the main layout.

## Target behavior
A task like:

> create a road map plan for creating a full stack application using react for a restaurant

must produce a full-stack artifact contract, not `frontend/src/App.jsx` and `frontend/src/App.css` only.
