from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import os
import shutil
from typing import Iterable

DEFAULT_IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    ".ise_ai", "AGI_Output", ".state", "sandboxes", "exports", "tmp", "temp",
}
DEFAULT_IGNORE_SUFFIXES = {".log", ".tmp", ".temp", ".pyc"}
DEFAULT_IGNORE_TOKENS = {"vector", "embedding", "chroma", "faiss", "memory-cache"}

@dataclass
class CopyReport:
    source: str
    target: str
    copied_files: list[str]
    skipped: list[str]
    errors: list[str]
    max_depth: int

    def to_dict(self):
        return asdict(self)


def is_ignored_path(path: Path, rel_parts: Iterable[str] = (), extra_ignore: set[str] | None = None) -> bool:
    ignore_dirs = DEFAULT_IGNORE_DIRS | (extra_ignore or set())
    parts = tuple(rel_parts) or path.parts
    if any(part in ignore_dirs for part in parts):
        return True
    name = path.name.lower()
    if any(token in name for token in DEFAULT_IGNORE_TOKENS):
        return True
    if path.suffix.lower() in DEFAULT_IGNORE_SUFFIXES:
        return True
    return False


def safe_copy_tree(source: str | Path, target: str | Path, *, clean_target: bool = True, max_depth: int = 12, max_files: int = 5000, max_file_bytes: int = 2_500_000, extra_ignore: set[str] | None = None) -> CopyReport:
    src = Path(source).expanduser().resolve()
    dst = Path(target).expanduser().resolve()
    copied: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []
    if not src.exists():
        raise FileNotFoundError(f"Source path does not exist: {src}")
    # Never allow target to be inside source without excluding it. This prevents
    # recursive .ise_ai/sandbox nesting and ENAMETOOLONG crashes.
    skip_roots = {dst}
    try:
        if dst.exists() and clean_target:
            shutil.rmtree(dst)
    except Exception as exc:
        errors.append(f"clean_target failed: {exc}")
    dst.mkdir(parents=True, exist_ok=True)

    if src.is_file():
        if src.stat().st_size <= max_file_bytes:
            shutil.copy2(src, dst / src.name)
            copied.append(src.name)
        else:
            skipped.append(f"{src.name}: larger than max_file_bytes")
        return CopyReport(str(src), str(dst), copied, skipped, errors, max_depth)

    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        try:
            root_resolved = root_path.resolve()
        except Exception:
            continue
        if any(root_resolved == skip or skip in root_resolved.parents for skip in skip_roots):
            dirs[:] = []
            continue
        try:
            rel_root = root_path.relative_to(src)
        except ValueError:
            continue
        rel_parts = () if str(rel_root) == "." else rel_root.parts
        if len(rel_parts) > max_depth or is_ignored_path(root_path, rel_parts, extra_ignore):
            dirs[:] = []
            skipped.append(str(rel_root))
            continue
        dirs[:] = [d for d in dirs if not is_ignored_path(root_path / d, rel_parts + (d,), extra_ignore)]
        for filename in files:
            if len(copied) >= max_files:
                skipped.append("max_files limit reached")
                return CopyReport(str(src), str(dst), copied, skipped, errors, max_depth)
            source_file = root_path / filename
            rel = (rel_root / filename) if str(rel_root) != "." else Path(filename)
            if is_ignored_path(source_file, rel.parts, extra_ignore):
                skipped.append(str(rel))
                continue
            try:
                if source_file.stat().st_size > max_file_bytes:
                    skipped.append(f"{rel}: larger than max_file_bytes")
                    continue
                target_file = dst / rel
                if len(str(target_file)) > 900:
                    skipped.append(f"{rel}: destination path too long")
                    continue
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                copied.append(str(rel))
            except Exception as exc:
                errors.append(f"{rel}: {exc}")
    return CopyReport(str(src), str(dst), copied, skipped, errors, max_depth)
