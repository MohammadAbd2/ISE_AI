# Unified Chat Agent Implementation Report

- Frontend chat now keeps `auto / chat / agent` as the main mode switch.
- Auto routing uses `/api/agents/route-task` and sends implementation tasks to `/api/agents/plan-and-execute`.
- User-facing AGI/Agent split has been reduced to one product name: **Agent**.
- The Agent execution card now describes one pipeline: planner, memory, sandbox, verifier, repair, preview, export.
- The route name for implementation work is now `agent_execute`.
