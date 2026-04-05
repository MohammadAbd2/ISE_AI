---
name: runtime-tools
description: Use when adding or fixing tool registry entries, tool execution, artifact tools, or evolution tool APIs in this project.
---

# Runtime Tools

Primary files:
- `backend/app/services/dynamic_tool_registry.py`
- `backend/app/services/tool_executor.py`
- `backend/app/api/evolution_routes.py`
- `backend/.evolution-tools.json`

Workflow:
1. Keep the registry honest: if a tool is listed, prefer making it executable.
2. Prefer thin adapters over duplicate logic; reuse `ArtifactService`, `HistoryService`, `SearchService`, and existing builders.
3. Preserve safe execution boundaries for shell/file tools.
4. If a tool becomes first-class, add a regression test for partial-registry startup or execution behavior.
5. Validate with:
   - `python -m unittest tests/test_backend_eval.py -v`
   - `python -m compileall backend/app`

Do not add tools that only describe behavior without a plausible runtime path.
