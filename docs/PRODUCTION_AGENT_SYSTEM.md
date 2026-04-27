# Production Agent System

ISE AI now treats sandbox work as a real execution pipeline instead of a prompt-only response.

## Runtime contract

1. **Plan**: build structured steps with action types, targets, metadata, and verification commands.
2. **Implement**: write/edit files through deterministic filesystem tools inside an isolated sandbox.
3. **Validate**: every generated file must exist and every verification command must finish successfully before the run is considered complete.
4. **Repair**: failed steps are retried with changed strategy, not by repeating the same command blindly.
5. **Export**: ZIP artifacts are created by backend export code after verification; the model is not allowed to invent download links.
6. **Download**: the frontend renders a ZIP button only when the backend artifact registry returns a real artifact id.
7. **Merge**: sandbox output is never merged into the main project unless the user approves it.

## No mocked artifacts

The assistant may explain the plan, but a downloadable artifact is only shown when the backend has created a real ZIP file and registered it in the artifact store.

## Sandbox location

Runtime folders are stored under `~/.cache/ise_ai/runtime` by default so generated sandboxes do not pollute the project folder or Desktop.

## General dynamic generation

Landing pages and apps infer their subject and sections from the user request. The system must not contain one-off hardcoded dentist/restaurant/travel templates; those are just possible domains supplied by the user.
