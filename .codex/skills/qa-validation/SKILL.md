---
name: qa-validation
description: Use when adding evals, regression tests, validation passes, or bug-fix safety checks for this project.
---

# QA Validation

Use this skill when a change adds user-visible behavior, runtime tools, render blocks, or agent routing.

Rules:
1. Add the smallest regression test that proves the behavior.
2. Prefer backend evals for service/agent logic and frontend evals for parsing or visualization behavior.
3. If a test hangs on external services, patch the dependency and keep the behavior under test.
4. Treat leaked resources and slow tests as bugs, not noise.

Standard validation:
- `python -m unittest tests/test_backend_eval.py -v`
- `python -m compileall backend/app`
- `npm run build`
