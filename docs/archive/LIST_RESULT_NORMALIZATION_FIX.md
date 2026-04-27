# Runtime Fix: Ingestion list result normalization

## Bug observed
The chat-native AGI failed at the first ingestion step with:

```text
'list' object has no attribute 'get'
```

## Root cause
`IngestionAgent` returns a list of copied files, but the workflow executor expected every sub-agent to return a dictionary and immediately called `.get(...)` on the raw result.

## Fix implemented
Added `_normalize_step_result(...)` in `backend/app/services/programming_agi_runtime.py` and routed every sub-agent result through it before reading fields.

The executor now supports:
- `dict` results from planner/verifier/preview/export agents
- `list` results from ingestion/copy agents
- `tuple` results
- `None` results
- plain string/object results as evidence

## Expected behavior now
When project ingestion returns a list of copied files, the step is marked completed, files are attached to the run, evidence is recorded, and the AGI continues to PlannerAgent instead of crashing.
