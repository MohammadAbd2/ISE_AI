# Roadmap — Powerful Agent Response + Backend/Frontend Rewrite

## Goal
Make the agent feel truthful, concise, and production-grade instead of noisy, fake, or generic.

## Implemented
1. **Path-accurate backend repair** — Vite import errors are parsed and the exact missing module is created, e.g. `src/components/GlobalErrorBoundary.jsx`, not unrelated `frontend/src/components/main.jsx`.
2. **Frontend response rewrite** — replaced the noisy timeline with a compact run card: latest meaningful state, truthful progress, elapsed time, agent summaries, expandable details, files, and verified ZIP.
3. **Progress fix** — progress reaches 100% when export artifacts are ready and no longer parks at 95% after completion.
4. **Code preview polish** — corrected language class binding and added syntax-token styling so previews look closer to normal generated code blocks.
5. **Agent planning guardrail** — import-error tasks bypass generic component generation and go directly to an exact repair plan.
6. **LLM prompt hardening** — CV/resume landing tasks explicitly require header, body, footer, identity, skills, experience, selected work, contact, and no placeholders.

## Roadmap next
- Add run IDs and stream each backend event through SSE/WebSocket.
- Persist every agent run as an auditable execution object.
- Add UI controls for retry failed step, download logs, and open changed file diff.
- Add a package-approved syntax highlighter for richer code previews.
