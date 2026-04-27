# Dynamic Agent Maximum Roadmap and Fix Report

## Goal
Turn ISE AI from a template-producing assistant into a dynamic programming AGI workflow for daily customer programming tasks.

## Root issues fixed
1. **Static CV/landing fallback was still reachable**
   - `autonomous_loop_engine.py` still contained the old `agentic-landing`/CV shell path.
   - Non-component app requests now route through the dynamic contract runtime instead of the static landing fallback.

2. **Verifier detected banned markers but DebugAgent could not repair them**
   - The artifact verifier previously scanned policy/docs/scripts and could flag its own banned-marker list.
   - Verification now scans generated application files only and excludes scripts/docs/contracts/reports.
   - The repair loop now overwrites stale template-contaminated files when `no_template_markers`, domain, or import gates fail.

3. **Full-stack commerce tasks were too generic**
   - Commerce requests now generate product catalog, cart, checkout request, C# product/order endpoints, MySQL product/order tables, seed data, API client, Docker MySQL runtime, roadmap, and API docs.

4. **Old memory/vector artifacts could mislead routing**
   - Added backend stale-memory cleanup for `.jsonl`, `.sqlite`, `.db`, vector/embedding/faiss/chroma-like files.
   - Added dashboard button to clear stale memory/vector files while preserving remembered project paths by default.

5. **Dashboard needed AGI control feedback**
   - Added API endpoint and UI control for memory hygiene.
   - The Daily Programming AGI panel continues to show roadmap, contract, real step status, validation score, preview/export/merge, and evidence.

## New roadmap plan

### Phase 1 — Contract-first routing
Every prompt becomes a typed task contract before files are written:
- intent
- domain
- stacks
- capabilities
- required files
- export gates
- responsible sub-agents

### Phase 2 — Sub-agent DAG execution
Tasks route to specialized agents:
- RouterAgent
- RequirementAgent
- FrontendAgent
- BackendAgent
- DatabaseAgent
- VerifierAgent
- RepairAgent
- PreviewAgent
- ExportAgent
- MergeAgent

### Phase 3 — No-template generation
Static fallback components are blocked. Application files must be built from:
- detected domain
- requested stack
- required capabilities
- file graph contract

### Phase 4 — Full-stack completeness
React + C# + MySQL requests cannot export frontend-only ZIPs. Export requires:
- frontend/package.json
- frontend/src/App.jsx
- frontend/src/lib/apiClient.js
- backend/Program.cs
- backend/*.csproj
- backend models/services
- database/schema.sql
- database/seed.sql
- docker-compose.yml
- verification script
- API contract docs

### Phase 5 — Self-repair loop
If validation fails:
- identify failed gate
- route to responsible sub-agent
- regenerate/patch relevant files
- rerun validation
- block export until fixed

### Phase 6 — Memory hygiene
Old memory/vector artifacts are removable from the dashboard so stale runs do not bias future plans.

### Phase 7 — Real customer workflow
Supported workflow:
1. remember project path
2. copy project into sandbox
3. plan
4. implement step-by-step
5. run verification
6. repair errors
7. produce preview command/link contract
8. export ZIP
9. merge after review to original or new folder

## Verification evidence
A simulated request for a full-stack laptop/screen webstore now produces:
- 20 files
- React frontend
- C# backend
- MySQL schema and seed data
- Docker compose
- API contract
- verification script
- validation score: 100/100
- no failed gates

