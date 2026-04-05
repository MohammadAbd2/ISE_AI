---
name: codebase-intake
description: Use when analyzing uploaded projects, file trees, imports, framework detection, or repo structure in this project.
---

# Codebase Intake

Use this skill when the task is about understanding a repo or uploaded archive before editing it.

Primary files:
- `backend/app/services/documents.py`
- `backend/app/services/dynamic_tool_registry.py`
- `backend/app/services/tool_executor.py`
- `backend/app/services/capability_registry.py`

Workflow:
1. Prefer structure first: frameworks, configs, directories, entrypoints.
2. Use runtime inspection tools where possible instead of reimplementing discovery logic.
3. Keep archive/project understanding aligned with dashboard metadata and coding/planning context.
4. If you add a new project-inspection signal, expose it through artifacts or registries, not only prompt text.

Validate with:
- `python -m unittest tests/test_backend_eval.py -v`
- `python -m compileall backend/app`
