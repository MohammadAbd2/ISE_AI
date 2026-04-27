from __future__ import annotations

from pathlib import Path

import aiofiles

from app.core.config import settings


def resolve_project_path(raw_path: str, project_root: Path | None = None) -> Path:
    root = (project_root or settings.project_root).resolve()
    candidate = Path((raw_path or "").strip())
    target = candidate if candidate.is_absolute() else (root / candidate)
    resolved = target.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path is outside the project root") from exc
    return resolved


async def read_project_text_file(raw_path: str, project_root: Path | None = None) -> tuple[bool, str]:
    path = resolve_project_path(raw_path, project_root)
    if not path.exists():
        return False, "File not found"
    async with aiofiles.open(path, "r", encoding="utf-8") as handle:
        return True, await handle.read()


async def write_project_text_file(raw_path: str, content: str, project_root: Path | None = None) -> str:
    path = resolve_project_path(raw_path, project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as handle:
        await handle.write(content)
    return f"Successfully wrote to {raw_path}"
