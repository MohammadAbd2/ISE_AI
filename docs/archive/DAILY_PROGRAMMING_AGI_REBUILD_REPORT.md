# Daily Programming AGI Rebuild Report

## Main problem fixed
The agent was still using a generic React landing/CV fallback for complex tasks. This caused full-stack requests such as React + C# + MySQL or restaurant systems to produce only `frontend/src/App.jsx` and `frontend/src/App.css`.

## What changed
- Added a stack-aware daily programming AGI service.
- Added backend API endpoints for roadmap, request analysis, artifact validation, and restaurant full-stack simulation.
- Added a real full-stack restaurant blueprint: React frontend, ASP.NET Core backend, MySQL schema, Docker Compose, API contract, and verification script.
- Patched the autonomous loop so `full stack` + `React` and restaurant/domain requests route to a full-stack plan instead of the old generic landing page.
- Added frontend Daily AGI panel showing intent contract, export risk, required files, and validation gates.
- Added a new roadmap document explaining the rebuild direction.

## Verification performed
- Python syntax compile passed for:
  - `backend/app/services/daily_programming_agi.py`
  - `backend/app/api/daily_programming_agi_routes.py`
  - `backend/app/services/full_stack_restaurant_blueprint.py`
  - `backend/app/services/autonomous_loop_engine.py`

## Verification limitation
- Frontend build could not be run in this extracted package because `frontend/node_modules/vite` is not present and package installation timed out in the sandbox environment. The code changes are included, but run `npm install && npm run build` locally to verify the final UI bundle.

## Expected new behavior
A prompt like:

> create a road map plan for creating a full stack application using react for a restaurant

should no longer export a CV/landing template. It should require a full-stack artifact contract containing frontend, backend, database, docs, config, and verification files.
