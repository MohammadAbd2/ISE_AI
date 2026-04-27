from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class TraceEvent:
    ts: float
    run_id: str
    agent: str
    phase: str
    status: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["elapsed_ms"] = int((time.time() - self.ts) * 1000)
        return data


class AgentTraceStore:
    def __init__(self, max_events_per_run: int = 1000) -> None:
        self._events: dict[str, deque[TraceEvent]] = defaultdict(lambda: deque(maxlen=max_events_per_run))

    def record(self, run_id: str, agent: str, phase: str, status: str, message: str, **metadata: Any) -> TraceEvent:
        event = TraceEvent(ts=time.time(), run_id=run_id, agent=agent, phase=phase, status=status, message=message, metadata=metadata)
        self._events[run_id].append(event)
        return event

    def list_runs(self) -> list[dict[str, Any]]:
        rows = []
        for run_id, events in self._events.items():
            if not events:
                continue
            rows.append({"run_id": run_id, "event_count": len(events), "last_status": events[-1].status, "last_message": events[-1].message, "updated_at": events[-1].ts})
        rows.sort(key=lambda item: item["updated_at"], reverse=True)
        return rows

    def get_run(self, run_id: str) -> dict[str, Any]:
        events = list(self._events.get(run_id, []))
        return {"run_id": run_id, "events": [event.to_dict() for event in events]}

_trace_store = AgentTraceStore()

def get_agent_trace_store() -> AgentTraceStore:
    return _trace_store
