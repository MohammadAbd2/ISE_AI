# AGI System v4 — Truth, Reliability, and Real-World Impact

This implementation moves the system from capability expansion to reliable outcomes.

## Implemented phases

- **Phase V — Grounded Intelligence:** evidence-backed claims with source/checksum records.
- **Phase W — Execution Truth Engine:** replayable task traces with per-event and full-trace checksums.
- **Phase X — Continuous Evaluation:** correctness, verification, specificity, safety, and UX scoring.
- **Phase Y — Domain Specialization:** React, backend, DevOps, agent, and UX skill packs selected by task intent.
- **Phase Z — Real-Time Adaptive Execution:** route switching for missing imports, generic output, and standard tasks.
- **Phase AA — Self-Improvement:** improvement proposals based on failed evaluations, requiring admin approval.
- **Phase AB — Collaborative Intelligence:** Planner, Critic, and Verifier debate before high-risk work.
- **Phase AC — Real-World Integrations v2:** guarded integration descriptors for GitHub PRs, CI, deploys, and monitoring.
- **Phase AD — Trust Certification:** safe-to-export, risk, confidence, and required proof categories.
- **Phase AE — Autonomous Project Ownership:** assisted-autonomous backlog and human approval boundaries.
- **UX-V → UX-Z:** outcome-first UI with Beginner, Developer, and Admin complexity modes.

## Backend additions

- `backend/app/services/agi_system_v4.py`
- `backend/app/api/agi_system_v4_routes.py`
- Router mounted from `backend/app/main.py`

## Frontend additions

- `frontend/src/components/AGISystemV4Panel.jsx`
- `frontend/src/styles/agi-v4.css`
- V4 API endpoints added in `frontend/src/lib/api.js`
- V4 panel added to the Super Agent workspace.

## Goal

Every important agent outcome should be shown as:

1. **Outcome** — what changed or what is ready.
2. **Proof** — evidence, trace checksum, evaluation score.
3. **Trust** — risk level, confidence, export readiness.
4. **Details** — available only when the user asks or switches to Admin mode.
