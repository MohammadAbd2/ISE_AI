import asyncio
import json
from typing import Dict, Any

# Simple in-memory broadcaster for plan progress events.
# Not persistent across process restarts. Suitable for local dashboard and tests.

_subscribers: Dict[str, list[asyncio.Queue]] = {}
_lock = asyncio.Lock()

async def publish_progress(plan_id: str, event: Dict[str, Any]) -> None:
    """Publish a progress event (dict) for a plan_id to all subscribers."""
    data = json.dumps(event, default=str)
    async with _lock:
        queues = list(_subscribers.get(plan_id, []))
    for q in queues:
        # put_nowait to avoid blocking publisher
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            # drop if subscriber is too slow
            pass

async def subscribe(plan_id: str):
    """Async generator yielding JSON strings for SSE streaming."""
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    async with _lock:
        _subscribers.setdefault(plan_id, []).append(q)
    try:
        while True:
            data = await q.get()
            yield data
    finally:
        # cleanup
        async with _lock:
            lst = _subscribers.get(plan_id, [])
            if q in lst:
                lst.remove(q)
            if not lst:
                _subscribers.pop(plan_id, None)
