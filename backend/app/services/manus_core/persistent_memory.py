"""
Persistent Memory System for Manus-Core Agent backed by ChromaDB.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.services.chroma_store import ChromaJSONStore


@dataclass
class MemoryEntry:
    entry_id: str
    memory_type: str
    content: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    relevance_score: float = 1.0
    access_count: int = 0


class PersistentMemorySystem:
    def __init__(self, db_path: str = "/tmp/ise_ai_memory"):
        self.store = ChromaJSONStore("manus_core_memory")
        self.connection = None

    def _init_database(self):
        return None

    def _store_memory(self, entry_id: str, memory_type: str, content: dict[str, Any], tags: Optional[list[str]], relevance_score: float) -> bool:
        try:
            timestamp = datetime.now().isoformat()
            self.store.upsert(entry_id, {"_id": entry_id, "entry_id": entry_id, "memory_type": memory_type, "content": content, "timestamp": timestamp, "tags": tags or [], "relevance_score": relevance_score, "access_count": 0})
            return True
        except Exception as exc:
            print(f"Error storing memory: {exc}")
            return False

    def store_episodic_memory(self, entry_id: str, interaction_type: str, user_message: str, agent_response: str, task_id: Optional[str] = None, outcome: Optional[str] = None, tags: Optional[list[str]] = None) -> bool:
        return self._store_memory(entry_id, "episodic", {"interaction_type": interaction_type, "user_message": user_message, "agent_response": agent_response, "task_id": task_id, "outcome": outcome}, tags, 1.0)

    def store_semantic_memory(self, entry_id: str, concept: str, definition: str, related_concepts: Optional[list[str]] = None, confidence_score: float = 1.0, source: Optional[str] = None, tags: Optional[list[str]] = None) -> bool:
        return self._store_memory(entry_id, "semantic", {"concept": concept, "definition": definition, "related_concepts": related_concepts or [], "confidence_score": confidence_score, "source": source}, tags, confidence_score)

    def store_procedural_memory(self, entry_id: str, skill_name: str, steps: list[str], success_rate: float = 1.0, tags: Optional[list[str]] = None) -> bool:
        return self._store_memory(entry_id, "procedural", {"skill_name": skill_name, "steps": steps, "success_rate": success_rate}, tags, success_rate)

    def store_project_memory(self, entry_id: str, project_name: str, codebase_structure: dict[str, Any], technologies: list[str], documentation: str, key_files: Optional[list[str]] = None, tags: Optional[list[str]] = None) -> bool:
        return self._store_memory(entry_id, "project", {"project_name": project_name, "codebase_structure": codebase_structure, "technologies": technologies, "documentation": documentation, "key_files": key_files or []}, tags, 1.0)

    def retrieve_memory(self, memory_type: Optional[str] = None, tags: Optional[list[str]] = None, limit: int = 10) -> list[MemoryEntry]:
        try:
            rows = self.store.find(filters={"memory_type": memory_type} if memory_type else None)
            if tags:
                wanted = set(tags)
                rows = [row for row in rows if wanted.intersection(set(row.get("tags", [])))]
            rows.sort(key=lambda row: (float(row.get("relevance_score", 0)), int(row.get("access_count", 0))), reverse=True)
            entries: list[MemoryEntry] = []
            for row in rows[:limit]:
                entries.append(MemoryEntry(entry_id=row.get("entry_id") or row.get("_id"), memory_type=row.get("memory_type", "semantic"), content=row.get("content", {}), timestamp=datetime.fromisoformat(str(row.get("timestamp"))), tags=list(row.get("tags", [])), relevance_score=float(row.get("relevance_score", 1.0)), access_count=int(row.get("access_count", 0))))
            return entries
        except Exception as exc:
            print(f"Error retrieving memory: {exc}")
            return []

    def update_access_count(self, entry_id: str):
        try:
            row = self.store.get(entry_id)
            if row:
                row["access_count"] = int(row.get("access_count", 0)) + 1
                self.store.upsert(entry_id, row)
        except Exception as exc:
            print(f"Error updating access count: {exc}")

    def clear_memory(self, memory_type: Optional[str] = None):
        try:
            self.store.clear(filters={"memory_type": memory_type} if memory_type else None)
        except Exception as exc:
            print(f"Error clearing memory: {exc}")

    def close(self):
        return None
