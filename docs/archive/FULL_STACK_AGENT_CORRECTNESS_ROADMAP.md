# Full-Stack Agent Correctness Roadmap and Implementation

## Problem fixed

The agent previously treated complex requests like "React + C# + MySQL login page" as a React-only landing-page template. That is a root planning failure, not a UI-only issue.

## New behavior

1. **Stack-aware intent detection**
   - Detects React, C# / .NET, MySQL, and authentication requirements from the user request.
   - Full-stack requests bypass stale memory/template fallbacks.

2. **Deterministic full-stack blueprint**
   - Generates a React/Vite login frontend.
   - Generates an ASP.NET Core C# authentication API.
   - Generates a MySQL schema.
   - Generates Docker Compose and setup documentation.

3. **Export gate**
   - The ZIP export is refused if a full-stack request is missing frontend, backend, database, or verification files.
   - React-only output is explicitly invalid for full-stack requests.

4. **Verification script inside generated artifacts**
   - Each generated full-stack project includes `scripts/verify_fullstack_artifact.py`.
   - The script checks that React UI, C# API, MySQL schema, and JWT auth are present.

5. **Frontend status fix**
   - Agent progress recognizes backend statuses like `completed`, `ready`, `verified`, `failed`, and `needs_repair`.
   - Progress reaches 100% only when terminal success or a verified artifact exists.

## Files changed

- `backend/app/services/autonomous_loop_engine.py`
- `backend/app/services/full_stack_login_blueprint.py`
- `backend/app/services/production_agent_runtime.py`
- `backend/app/services/no_template_verifier.py`
- `frontend/src/components/agent/AgentStatusBar.jsx`

## Expected result for the example request

A request for a website using React, C#, and MySQL for a login page now produces a full-stack project ZIP containing:

- `frontend/src/App.jsx`
- `frontend/src/App.css`
- `frontend/package.json`
- `backend/Program.cs`
- `backend/AuthApi.csproj`
- `backend/appsettings.example.json`
- `database/schema.sql`
- `docker-compose.yml`
- `scripts/verify_fullstack_artifact.py`
- `README.md`
