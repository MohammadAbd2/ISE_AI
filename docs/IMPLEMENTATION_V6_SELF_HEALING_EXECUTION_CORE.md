# Implementation Report — v6 Self-Healing Execution Core

Implemented in this package:

- Atomic text/binary file writer with checksum verification.
- PDF generation no longer slices messages to tiny prefixes; it wraps visible text.
- Direct downloadable artifacts store larger previews and write verification metadata.
- Programming Agent writes all generated source files atomically.
- Self-healing verifier loop retries failed gates up to five times.
- Import/template failures trigger canonical graph rewrites and marker cleanup.
- Export no longer disappears when repair cannot fully recover; diagnostic exports are generated.
- Preview manager now starts real local Vite processes and runs `npm install` when needed.
- Agent `/plan-and-execute` attempts to start the preview automatically and returns managed preview status/log metadata.
- JetBrains extension detects the project root, sends an instruction, receives rewritten code, and applies it to `src/App.jsx`.
- Added backend IDE rewrite endpoint under `/api/devx/ide/rewrite-file`.

Known operational requirements:

- Backend must be running on `127.0.0.1:8000` for IDE integrations.
- Preview startup needs Node/npm available locally.
- If `npm install` cannot access dependencies, preview reports failed with logs instead of pretending success.
