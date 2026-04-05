---
name: research-analytics
description: Use when improving or debugging web research, session analytics, research memory, or chart/map artifact flows in this project.
---

# Research Analytics

Use this skill for work touching:
- `backend/app/services/search.py`
- `backend/app/services/session_analytics.py`
- `frontend/src/lib/visualization.js`
- chat render blocks for `research_result`, `report`, `file_result`, or `visualization`

Workflow:
1. Check whether the request is live research, reusable research memory, or visualization generation.
2. Preserve typed outputs. Prefer adding or fixing render blocks over falling back to plain text.
3. If the task changes ranking or source trust, keep freshness, confidence, authority, and conflict signals aligned.
4. If the task changes analytics persistence, make sure dashboard reopening still works.
5. Validate with:
   - `python -m unittest tests/test_backend_eval.py -v`
   - `npm run test:eval`
   - `npm run build`

When adding new research or visualization behavior, update both backend evals and frontend evals if the behavior is user-visible.
