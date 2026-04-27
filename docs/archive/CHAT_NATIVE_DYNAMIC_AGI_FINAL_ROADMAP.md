# Chat-Native Dynamic Programming AGI Final Roadmap

## Goal
Move the MAX Dynamic AGI workflow into the normal chat agent so every programming request uses the same dynamic, stateful, sandbox-first AGI path instead of the old static sandbox/template component.

## Implemented phases

### 1. Chat-native AGI routing
- Normal chat coding/build requests now route through `ProgrammingAGIRuntime`.
- The legacy static response path that produced generic sandbox output is bypassed for complex programming tasks.
- Chat render blocks now include a `programming_agi_run` payload with real run state.

### 2. Safe `AGI_Output` workspace
- Default output root is now `./AGI_Output` inside the project folder.
- Runtime state is stored under `AGI_Output/.state`.
- Sandboxes are stored under `AGI_Output/sandboxes`.
- ZIP exports are stored under `AGI_Output/exports`.
- Verified project copies are stored under `AGI_Output/projects`.

### 3. Recursive sandbox-copy bug fix
- Ingestion now excludes `.ise_ai`, `AGI_Output`, `.state`, `sandboxes`, `exports`, `node_modules`, build folders, and caches.
- Copy logic skips the active sandbox/output subtree if it lives inside the source project.
- This prevents the previous `File name too long` failure caused by copying sandboxes into themselves.

### 4. Configurable preview URL
- Preview links no longer use fake `/preview/<id>` routes that produce 404 errors.
- Preview URL defaults to `http://127.0.0.1:5173`.
- Port can be extracted from the prompt, for example `use port 5174`.
- `PREVIEW_BASE_URL` or `AGI_PREVIEW_PORT` can override the default.
- Preview payload includes `url`, `cwd`, `port`, and the exact command to run.

### 5. Export lifecycle correction
- Export now creates both:
  - a downloadable ZIP in `AGI_Output/exports`
  - a project folder copy in `AGI_Output/projects/run-<id>`
- Export still blocks if validation has failed gates.

### 6. Merge lifecycle correction
- Chat stores a pending `programming_agi_merge` action after AGI execution.
- Confirming merge copies the verified run into `AGI_Output/merged/<run_id>` by default unless a target path is supplied.

### 7. Frontend chat rendering
- Added a chat render block for `programming_agi_run`.
- The chat can now show:
  - real status
  - progress
  - step cards
  - preview URL
  - preview command
  - output root
  - changed files summary

### 8. Backend route upgrade
- `/api/programming-agi/run` accepts `preview_base_url`.
- API run method passes preview configuration through to the runtime.

## Verification notes
- Backend runtime was smoke-tested with a React + Node + SQLite ZIP request.
- Preview contract returned a direct URL, not `/preview/<id>`.
- Export produced ZIP metadata and a project copy path under `AGI_Output`.
- Source-project ingestion was adjusted to avoid recursive output copying.
