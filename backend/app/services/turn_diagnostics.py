from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache


@dataclass(slots=True)
class TurnDiagnostic:
    created_at: str
    message_preview: str
    mode: str
    intent_kind: str
    use_agent: bool
    used_agents: list[str] = field(default_factory=list)
    search_count: int = 0
    image_count: int = 0
    render_block_types: list[str] = field(default_factory=list)
    had_reply: bool = False

    def to_dict(self) -> dict:
        return {
            "created_at": self.created_at,
            "message_preview": self.message_preview,
            "mode": self.mode,
            "intent_kind": self.intent_kind,
            "use_agent": self.use_agent,
            "used_agents": self.used_agents,
            "search_count": self.search_count,
            "image_count": self.image_count,
            "render_block_types": self.render_block_types,
            "had_reply": self.had_reply,
        }


class TurnDiagnosticsService:
    def __init__(self, limit: int = 40) -> None:
        self._entries: deque[TurnDiagnostic] = deque(maxlen=limit)

    def record(
        self,
        *,
        message: str,
        mode: str,
        intent_kind: str,
        use_agent: bool,
        used_agents: list[str] | None = None,
        search_count: int = 0,
        image_count: int = 0,
        render_block_types: list[str] | None = None,
        had_reply: bool = False,
    ) -> None:
        self._entries.appendleft(
            TurnDiagnostic(
                created_at=datetime.now(UTC).isoformat(),
                message_preview=message.strip()[:160],
                mode=mode,
                intent_kind=intent_kind,
                use_agent=use_agent,
                used_agents=used_agents or [],
                search_count=search_count,
                image_count=image_count,
                render_block_types=render_block_types or [],
                had_reply=had_reply,
            )
        )

    def recent(self) -> list[dict]:
        return [entry.to_dict() for entry in self._entries]


@lru_cache
def get_turn_diagnostics_service() -> TurnDiagnosticsService:
    return TurnDiagnosticsService()
