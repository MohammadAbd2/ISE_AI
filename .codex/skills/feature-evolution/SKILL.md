---
name: feature-evolution
description: Use when extending the project’s capability registry, dashboard tool inventory, coding/planning agent bundles, or self-improvement flows.
---

# Feature Evolution

Use this skill when the task is about making the system more capable rather than answering a user prompt.

Targets:
- `backend/app/services/capability_registry.py`
- `backend/app/services/intelligent_coding_agent.py`
- `backend/app/services/planning_agent.py`
- `backend/app/services/evolution_agent.py`
- dashboard/evolution registry JSON files

Rules:
1. Favor capabilities that already have an implementation path.
2. Keep registry metadata specific enough to drive UI and planning decisions.
3. For new generated feature bundles, make integration files explicit.
4. Add evals for routing, file bundle generation, or registry drift whenever behavior changes.

Validation:
- `python -m unittest tests/test_backend_eval.py -v`
- `npm run build`
