# Roadmap: Conflict-Safe Preview + Truthful Export Reports

## Problem noticed from user logs
- Generated app preview command reused `localhost:5173`, the same port commonly used by the main ISE_AI frontend.
- `RUN_REPORT.json` inside exported ZIP could show `status: running` and `ExportAgent: running` because the report was written while the export step was still executing.
- The frontend passed `window.location.origin` as the preview base URL, accidentally encouraging generated previews to reuse the current app URL.

## Implemented fixes
1. **Preview port isolation**
   - Generated previews now avoid port `5173` by default.
   - Default candidate ports start at `5174`, then `5175`, `5176`, `5177`, `4173`, `4174`, `3000`, `3001`.
   - The backend checks whether a candidate port is free before returning the preview command.

2. **Frontend/backend contract cleanup**
   - The frontend no longer sends `window.location.origin` as `preview_base_url` for AGI runs.
   - The backend owns preview URL/port selection so the UI cannot accidentally collide with itself.

3. **Truthful ZIP run report**
   - After the export step finishes and the workflow reaches a terminal state, the backend rewrites `RUN_REPORT.json` inside the ZIP.
   - Users now unzip a final report that shows `completed` or `failed`, not stale `running` state.

## Next roadmap
- Add a live preview process manager that can start/stop generated previews from the UI instead of only returning a command.
- Add a port reservation registry to prevent two simultaneous generated previews from receiving the same free port.
- Add UI warning badges when a user explicitly requests a port already occupied by the main app.
- Add export validation that opens the ZIP and asserts `RUN_REPORT.status != running` before presenting the download.
- Add cleanup controls for old sandboxes, previews, and exports.
