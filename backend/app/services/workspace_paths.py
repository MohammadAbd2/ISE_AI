from __future__ import annotations
from pathlib import Path
from app.services.chroma_store import ChromaJSONStore

class WorkspaceRegistry:
    def __init__(self):
        self.store = ChromaJSONStore("workspace_paths")

    def remember(self, label: str, path: str) -> dict:
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError("Workspace path must be an existing folder")
        dangerous = {Path('/').resolve()}
        try:
            dangerous.add(Path.home().resolve())
        except Exception:
            pass
        if resolved in dangerous:
            raise ValueError("Refusing to use a system/home root as an editable workspace")
        row = {"_id": label or "default", "label": label or "default", "path": str(resolved), "exists": True}
        self.store.upsert(row["_id"], row)
        return row

    def list(self) -> list[dict]:
        rows = self.store.find(sort_key="label")
        for row in rows:
            row["exists"] = Path(row.get("path", "")).exists()
        return rows

    def get(self, label: str = "default") -> dict | None:
        return self.store.get(label)

_registry = WorkspaceRegistry()
def get_workspace_registry() -> WorkspaceRegistry:
    return _registry
