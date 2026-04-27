# Roadmap v31 — Render Stability + AI Engineer Workbench Recovery

## Goal
Fix the `path.toLowerCase is not a function` crash and harden the Agent message renderer so Agent output feels like watching an AI engineer work even when backend payloads contain objects instead of plain strings.

## Critical gaps fixed

### Phase 1 — File/path payload safety
- Normalize file arrays that contain strings, file objects, artifact objects, or metadata records.
- Convert every path-like value into a safe string before filtering, previewing, and building the file tree.
- Keep file content maps stable even when backend returns non-string values.

### Phase 2 — Engineer Workbench render hardening
- Guard every workbench lane, item, status, and detail with safe string conversion.
- Do not allow malformed Agent blocks to crash chat.
- Keep the “Thinking → building → debugging → shipping” presentation visible.

### Phase 3 — Stable React block keys
- Replace duplicate `-block-` keys with message-specific keys.
- Prevent incorrect component reuse and confusing UI recovery behavior.

### Phase 4 — Build verification
- Verified the patched frontend with an esbuild JSX bundle syntax check.

## Expected result
The Agent chat panel no longer enters UI recovery mode from file/path payloads. File trees, generated files, and engineer-workbench cards render safely and remain dynamic.
