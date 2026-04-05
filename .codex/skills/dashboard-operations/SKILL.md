---
name: dashboard-operations
description: Use when exposing backend capabilities in the frontend dashboard, tool panels, or operator-style controls for this project.
---

# Dashboard Operations

Use this skill when a backend capability already exists and the task is to surface it cleanly in the UI.

Primary files:
- `frontend/src/components/DashboardView.jsx`
- `frontend/src/App.jsx`
- `frontend/src/lib/api.js`
- `frontend/src/styles/global.css`

Rules:
1. Prefer explicit operator actions over passive status-only cards.
2. When a tool returns structured blocks, push them into chat instead of flattening them to text.
3. Keep the dashboard as a control plane and the chat as the execution/result stream.
4. If an operation changes visualization state, sync the dashboard visualization card too.

Validate with:
- `npm run build`
- backend evals if the operation required backend changes
