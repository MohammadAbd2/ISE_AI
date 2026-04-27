# Chat-Native AGI Preview + UI Roadmap

## Goal
Move the MAX Dynamic AGI from a separate dashboard tab into the normal chat flow, fix sandbox copy/export failures, and make browser previews configurable and trustworthy.

## Implemented phases

1. **Chat-native AGI routing**
   - Programming requests in the chat now call the Maximum Dynamic Agent endpoint directly.
   - The response renders as a structured AGI run block instead of the old static assistant template.

2. **Recursive copy protection**
   - Sandbox/project ingestion skips `.ise_ai`, `AGI_Output`, `node_modules`, `dist`, `build`, virtualenvs, and `.git`.
   - This prevents the previous `File name too long` recursion where sandboxes copied themselves repeatedly.

3. **Safe default output folder**
   - Verified exports are materialized into `./AGI_Output/run-<id>/`.
   - A matching ZIP is created as `./AGI_Output/run-<id>.zip`.
   - Unsafe recursive folders are never copied into generated output.

4. **Configurable preview URL**
   - Preview contracts now accept `preview_base_url` and `preview_port`.
   - The frontend passes the current origin/port instead of relying on a hardcoded localhost URL.
   - Preview command includes the chosen port: `npm install && npm run dev -- --host 0.0.0.0 --port <port>`.

5. **Self-repair hardening**
   - Repair now always reruns banned-marker cleanup and import repair.
   - Backend-only follow-up requests remove accidental frontend files if the verifier detects scope drift.

6. **Chat run evidence UI**
   - The chat block now shows progress, gates, preview action, output folder, verification commands, repair attempts, and changed files.
   - It no longer hides important blocker evidence behind noisy logs.

7. **Validation before export**
   - Export still blocks if verification fails.
   - If verification passes, the agent writes files to `AGI_Output` and creates the ZIP.

## Next recommended phase
Add a real process manager for previews so the backend starts/stops Vite/Node/.NET preview servers and maps preview IDs to running ports, instead of returning only the preview command contract.
