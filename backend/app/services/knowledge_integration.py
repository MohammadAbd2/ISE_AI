
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class KnowledgeItem:
    id: str
    title: str
    source: str
    content: str
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KnowledgeStore:
    """Local knowledge/document cache for project-specific documentation snippets."""

    def __init__(self) -> None:
        self.root = (Path.home() / ".cache" / "ise_ai" / "knowledge").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "items.json"
        self._items: dict[str, KnowledgeItem] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            for row in json.loads(self.path.read_text(encoding="utf-8")).get("items", []):
                item = KnowledgeItem(**row)
                self._items[item.id] = item
        except Exception:
            self._items = {}

    def _save(self) -> None:
        self.path.write_text(json.dumps({"items": [i.to_dict() for i in self._items.values()]}, indent=2), encoding="utf-8")

    def add(self, title: str, source: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        item = KnowledgeItem(id=str(uuid4()), title=title, source=source, content=content, tags=tags or [])
        self._items[item.id] = item
        self._save()
        return item.to_dict()

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        terms = {t for t in query.lower().split() if len(t) > 2}
        scored = []
        for item in self._items.values():
            hay = " ".join([item.title, item.source, item.content, " ".join(item.tags)]).lower()
            score = sum(1 for term in terms if term in hay)
            if score or not terms:
                row = item.to_dict()
                row["score"] = score
                scored.append(row)
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:limit]


@lru_cache
def get_knowledge_store() -> KnowledgeStore:
    return KnowledgeStore()
