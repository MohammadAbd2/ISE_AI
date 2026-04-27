import shutil
import tempfile
from pathlib import Path
from typing import Optional, List


class WorkspaceManager:
    """Simple workspace manager for staging multi-file changes.

    Creates a temporary workspace directory where file writes/read operate during
    an autonomous run. Provides commit and cleanup operations.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base = Path(tempfile.mkdtemp(prefix="ise_ai_workspace_"))
        else:
            # Place workspace inside project's tmp area
            self.base = Path(base_dir) / ".ise_ai_workspace"
            self.base.mkdir(parents=True, exist_ok=True)

    def stage_path(self, rel_path: str) -> Path:
        p = self.base / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def list_staged_files(self) -> List[str]:
        return [str(p.relative_to(self.base)) for p in self.base.rglob("*") if p.is_file()]

    def commit_to(self, dest_root: Path, allowed_files: List[str] | None = None) -> List[str]:
        """Copy staged files to dest_root. Returns list of copied relative paths.

        If allowed_files is provided, only those relative paths will be copied.
        """
        copied = []
        allowed_set = set(allowed_files) if allowed_files else None
        for p in self.base.rglob("*"):
            if p.is_file():
                rel = p.relative_to(self.base)
                rel_str = str(rel)
                if allowed_set is not None and rel_str not in allowed_set:
                    continue
                dst = Path(dest_root) / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                copied.append(rel_str)
        return copied

    def cleanup(self) -> None:
        try:
            shutil.rmtree(self.base)
        except Exception:
            pass
