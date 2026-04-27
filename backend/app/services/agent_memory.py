"""Persistent task memory, lesson extraction, and retrieval for autonomous agent runs."""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.services.chroma_store import ChromaJSONStore


def _tokenize(text: str) -> set[str]:
    stop = {"the", "and", "with", "from", "that", "this", "then", "give", "download", "zip", "roadmap", "plan"}
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in stop}


@dataclass(slots=True)
class MemoryHit:
    task: str
    score: float
    success: bool
    summary: str
    files: list[str]
    fixes: list[str]
    artifact_id: str | None = None


@dataclass(slots=True)
class LessonHit:
    problem: str
    solution: str
    when_to_use: str
    score: float
    source_task: str = ""


class AgentMemoryStore:
    def __init__(self, db_path=None) -> None:
        self.memory_store = ChromaJSONStore("task_memory")
        self.lesson_store = ChromaJSONStore("task_lessons")

    def _init_db(self) -> None:
        return None

    def record_run(self, *, task: str, success: bool, summary: str, files: list[str] | None = None, failures: list[str] | None = None, fixes: list[str] | None = None, artifact_id: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        memory_id = str(uuid4())
        normalized = " ".join(sorted(_tokenize(task)))
        self.memory_store.upsert(memory_id, {"_id": memory_id, "id": memory_id, "created_at": datetime.now(UTC).isoformat(), "task": task, "normalized": normalized, "success": bool(success), "summary": summary[:4000], "files": files or [], "failures": failures or [], "fixes": fixes or [], "artifact_id": artifact_id, "metadata": metadata or {}})
        self.extract_and_store_lessons(task=task, success=success, summary=summary, failures=failures or [], fixes=fixes or [], metadata=metadata or {})
        return memory_id

    def extract_and_store_lessons(self, *, task: str, success: bool, summary: str, failures: list[str], fixes: list[str], metadata: dict[str, Any] | None = None) -> list[str]:
        lessons: list[dict[str, str]] = []
        if failures:
            for failure in failures[:4]:
                repair = next((fix for fix in fixes if fix), summary)
                lessons.append({"problem": failure[:1000], "solution": (repair or summary)[:1000], "when_to_use": f"When a future task resembles: {task[:240]}"})
        elif success:
            lessons.append({"problem": f"How to complete tasks like: {task[:240]}", "solution": summary[:1000], "when_to_use": "Use before planning a similar implementation, verification, or export task."})
        inserted: list[str] = []
        for lesson in lessons:
            lesson_id = str(uuid4())
            normalized = " ".join(sorted(_tokenize(" ".join(lesson.values()))))
            self.lesson_store.upsert(lesson_id, {"_id": lesson_id, "id": lesson_id, "created_at": datetime.now(UTC).isoformat(), "source_task": task, "problem": lesson["problem"], "solution": lesson["solution"], "when_to_use": lesson["when_to_use"], "normalized": normalized, "metadata": metadata or {}})
            inserted.append(lesson_id)
        return inserted

    def search(self, task: str, *, limit: int = 5) -> list[MemoryHit]:
        query_tokens = _tokenize(task)
        if not query_tokens:
            return []
        hits: list[MemoryHit] = []
        for row in self.memory_store.find(sort_key="created_at", reverse=True, limit=200):
            tokens = set(str(row.get("normalized", "")).split())
            if not tokens:
                continue
            overlap = len(query_tokens & tokens)
            if overlap == 0:
                continue
            score = overlap / math.sqrt(len(query_tokens) * len(tokens))
            hits.append(MemoryHit(row.get("task", ""), round(score, 3), bool(row.get("success")), row.get("summary", ""), list(row.get("files", [])), list(row.get("fixes", [])), row.get("artifact_id")))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    def search_lessons(self, query: str, *, limit: int = 5) -> list[LessonHit]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        hits: list[LessonHit] = []
        for row in self.lesson_store.find(sort_key="created_at", reverse=True, limit=300):
            tokens = set(str(row.get("normalized", "")).split())
            if not tokens:
                continue
            overlap = len(query_tokens & tokens)
            if overlap == 0:
                continue
            score = overlap / math.sqrt(len(query_tokens) * len(tokens))
            hits.append(LessonHit(row.get("problem", ""), row.get("solution", ""), row.get("when_to_use", ""), round(score, 3), row.get("source_task", "")))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    def planning_context(self, task: str, *, limit: int = 5) -> dict[str, Any]:
        return {"memories": [asdict(item) for item in self.search(task, limit=limit)], "lessons": [asdict(item) for item in self.search_lessons(task, limit=limit)]}


def get_agent_memory_store() -> AgentMemoryStore:
    return AgentMemoryStore()
