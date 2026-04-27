# Critical Agent Gap Fix v9 — Implementation Report

Implemented in this package:

- Added `docs/ROADMAP_CRITICAL_AGENT_GAP_FIX_V9.md` with phases 1–10 and quality gates.
- Added `backend/app/services/critical_agent_quality.py` for full quoted-content extraction, static HTML generation, result contracts, DebuggingAgent classification, repair plans, IDE patch contracts, and verified text writes.
- Expanded downloadable file metadata with write verification and longer content previews.
- Added `/api/agentic-visual/critical-roadmap`.
- Added `/api/agentic-visual/debug/self-heal`.
- Added `/api/agentic-visual/static-html/generate`.
- Added `/api/agentic-visual/ide/patch`.
- Improved routing for static HTML, file-location, Figma/design and debug/error requests.
- Added chat handling for DebuggingAgent repair plans.
- Replaced static HTML generation with the critical result-contract endpoint.
- Added visual JSON viewer and write-verification display in download cards.
- Added IDE write-back bridge notes for VS Code and JetBrains.
- Added self-healing repair blocks to generic Agent execution when verifier gates fail.

Known boundaries:
- Figma live file JSON still requires a valid Figma API token and permission to the file.
- IDE extensions include the bridge contract and apply-flow guidance; users still approve file changes locally.
- Preview process start depends on local Node/npm availability when rendering Vite projects. Static HTML previews render in-chat without Node.
