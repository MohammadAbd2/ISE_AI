# Phase 16–21: Reliability, Preview, Artifacts, Deployment, Observability

This phase turns the agent runtime from a feature demo into a verifiable platform.

## Phase 16 — Reliability suite

Adds deterministic end-to-end checks for the path that matters most:

`prompt → workspace files → optional build → verified ZIP → manifest → download route`

Endpoint:

```http
POST /api/platform/reliability/react-smoke
```

## Phase 17 — Runtime preview

Adds a preview registry for generated Vite/React apps. It allocates a local port, starts the dev server when dependencies exist, captures logs, and exposes preview status.

Endpoints:

- `POST /api/platform/preview/start`
- `GET /api/platform/preview`
- `GET /api/platform/preview/{id}`
- `DELETE /api/platform/preview/{id}`

## Phase 18 — No-template verifier

Adds a verifier that blocks repeated generic output, placeholder copy, and domain-irrelevant generated content before export.

Endpoint:

```http
POST /api/platform/no-template/check
```

## Phase 19 — Artifact perfection

Exports now include stronger metadata, manifest/hash verification, sanitized ZIP names, and deployment helper files for app exports. Download responses include artifact id, hash, and file count headers.

## Phase 20 — Deployment-ready output

Generated React app ZIPs now include a README and `.env.example` when they are missing.

## Phase 21 — Observability

Adds an agent trace store and endpoints for timeline/debugging tools.

Endpoints:

- `GET /api/platform/traces`
- `GET /api/platform/traces/{run_id}`

## Frontend

Adds a production platform panel for reliability smoke tests, traces, and preview sessions.
