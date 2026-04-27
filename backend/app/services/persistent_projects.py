
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import settings


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class PersistentProject:
    id: str
    name: str
    root: str
    description: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    versions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PersistentProjectStore:
    def __init__(self) -> None:
        base = Path.home() / ".cache" / "ise_ai" / "projects"
        self.root = base.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "projects.json"
        self._projects: dict[str, PersistentProject] = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
            for item in raw.get("projects", []):
                project = PersistentProject(**item)
                self._projects[project.id] = project
        except Exception:
            self._projects = {}

    def _save(self) -> None:
        payload = {"projects": [p.to_dict() for p in self._projects.values()]}
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def create(self, name: str, description: str = "") -> dict[str, Any]:
        project_id = str(uuid4())
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name.lower()).strip("-") or "project"
        root = self.root / f"{safe_name}-{project_id[:8]}"
        root.mkdir(parents=True, exist_ok=True)
        project = PersistentProject(id=project_id, name=name, root=str(root), description=description)
        self._projects[project_id] = project
        self._save()
        return project.to_dict()

    def list(self) -> list[dict[str, Any]]:
        return sorted([p.to_dict() for p in self._projects.values()], key=lambda p: p["updated_at"], reverse=True)

    def get(self, project_id: str) -> dict[str, Any] | None:
        project = self._projects.get(project_id)
        return project.to_dict() if project else None

    def snapshot(self, project_id: str, source_dir: str | Path, label: str = "snapshot") -> dict[str, Any]:
        project = self._projects[project_id]
        source = Path(source_dir).expanduser().resolve()
        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source}")
        dest = Path(project.root) / "versions" / f"{len(project.versions)+1:04d}-{label}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns("node_modules", ".git", "dist", "build", "__pycache__"))
        record = {"label": label, "path": str(dest), "created_at": _now()}
        project.versions.append(record)
        project.updated_at = _now()
        self._save()
        return record


@lru_cache
def get_persistent_project_store() -> PersistentProjectStore:
    return PersistentProjectStore()
