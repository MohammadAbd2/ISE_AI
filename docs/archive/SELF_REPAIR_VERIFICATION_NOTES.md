# Self-Repair Verification Notes

Manual service check performed against the reported failing prompt:

`create a website application using react, node and litesql create a road map plan first start implmenting it then give me the zip file`

Expected contract after the fix:

- `react`
- `node`
- `sqlite`

Expected generated layers:

- `frontend/` React + Vite app
- `backend-node/` Fastify API with product and auth routes
- `database/sqlite/` schema and seed files
- `docs/API_CONTRACT.md`
- `scripts/verify_artifact.py`

The runtime validation gate now checks Node backend presence, SQLite schema presence, import graph, no-template markers, and full-stack completeness. Structural failures rebuild the missing layer from the task contract and rerun the banned-marker scrubber.
