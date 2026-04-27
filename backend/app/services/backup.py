"""
Backup and versioning system for safe code modifications.
Enables the AI to modify source code with ability to rollback.
"""

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from app.core.config import settings


class BackupManager:
    """
    Manages code backups and version history using git.
    Every modification is committed with metadata.
    """

    def __init__(self):
        self.repo_root = Path(settings.project_root)
        self.backup_dir = self.repo_root / "output" / "backups"
        self.metadata_file = self.backup_dir / "backups.json"
        self._ensure_backup_dir()
        self._load_metadata()

    def _ensure_backup_dir(self) -> None:
        """Create backup directory if it doesn't exist."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        if not self.metadata_file.exists():
            self.metadata_file.write_text(json.dumps({"backups": [], "current": None}))

    def _load_metadata(self) -> None:
        """Load backup metadata from file."""
        try:
            self.metadata = json.loads(self.metadata_file.read_text())
        except Exception:
            self.metadata = {"backups": [], "current": None}

    def _save_metadata(self) -> None:
        """Save backup metadata to file."""
        self.metadata_file.write_text(json.dumps(self.metadata, indent=2))

    def create_backup(
        self, reason: str, files: list[str] | None = None
    ) -> dict:
        """
        Create a backup snapshot of the current code state.
        
        Args:
            reason: Description of why backup was created
            files: Specific files to backup (None = backup entire repo)
        
        Returns:
            dict with backup metadata
        """
        backup_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_entry = {
            "id": backup_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
            "files": files,
        }

        # Create backup snapshot directory
        snapshot_dir = self.backup_dir / backup_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            if files:
                for file_path in files:
                    full_path = self.repo_root / file_path
                    if full_path.exists():
                        target = snapshot_dir / file_path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if full_path.is_file():
                            shutil.copy2(full_path, target)
            else:
                # Full repository backup
                for item in self.repo_root.rglob("*"):
                    if self._should_skip(item):
                        continue
                    if item.is_file():
                        rel_path = item.relative_to(self.repo_root)
                        target = snapshot_dir / rel_path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target)

            backup_entry["status"] = "success"
            self.metadata["backups"].append(backup_entry)
            self.metadata["current"] = backup_id
            self._save_metadata()

            return backup_entry
        except Exception as e:
            backup_entry["status"] = "failed"
            backup_entry["error"] = str(e)
            return backup_entry

    def restore_backup(self, backup_id: str) -> dict:
        """
        Restore code to a specific backup point.
        
        Args:
            backup_id: ID of the backup to restore
        
        Returns:
            dict with restoration status
        """
        backup_path = self.backup_dir / backup_id
        if not backup_path.exists():
            return {
                "status": "failed",
                "error": f"Backup {backup_id} not found",
            }

        try:
            # Restore files from backup
            for item in backup_path.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(backup_path)
                    target = self.repo_root / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)

            self.metadata["current"] = backup_id
            self._save_metadata()

            return {
                "status": "success",
                "backup_id": backup_id,
                "restored_at": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }

    def list_backups(self) -> list[dict]:
        """List all available backups."""
        return self.metadata.get("backups", [])

    def get_backup_info(self, backup_id: str) -> Optional[dict]:
        """Get metadata for a specific backup."""
        for backup in self.metadata["backups"]:
            if backup["id"] == backup_id:
                return backup
        return None

    def get_current_backup(self) -> Optional[dict]:
        """Get metadata for the current backup point."""
        current_id = self.metadata.get("current")
        if current_id:
            return self.get_backup_info(current_id)
        return None


    def cleanup_old_backups(self, max_age_days: int = 30) -> dict:
        """Delete backups older than the requested age."""
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        removed: list[str] = []
        kept: list[dict] = []
        current_id = self.metadata.get("current")

        for backup in self.metadata.get("backups", []):
            backup_id = backup.get("id", "")
            if backup_id == current_id:
                kept.append(backup)
                continue
            timestamp_raw = backup.get("timestamp")
            try:
                created_at = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")) if timestamp_raw else None
            except Exception:
                created_at = None
            if created_at is not None and created_at < cutoff:
                backup_path = self.backup_dir / backup_id
                shutil.rmtree(backup_path, ignore_errors=True)
                removed.append(backup_id)
            else:
                kept.append(backup)

        if removed:
            self.metadata["backups"] = kept
            self._save_metadata()
        return {"status": "success", "removed": removed, "remaining": len(self.metadata.get("backups", []))}

    def delete_backup(self, backup_id: str) -> dict:
        """Delete a backup (cannot delete current)."""
        if backup_id == self.metadata.get("current"):
            return {
                "status": "failed",
                "error": "Cannot delete the current backup",
            }

        backup_path = self.backup_dir / backup_id
        try:
            shutil.rmtree(backup_path)
            self.metadata["backups"] = [
                b for b in self.metadata["backups"] if b["id"] != backup_id
            ]
            self._save_metadata()
            return {"status": "success", "deleted": backup_id}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _should_skip(self, path: Path) -> bool:
        """Determine if a file/directory should be skipped during backup."""
        skip_patterns = {
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".idea",
            "node_modules",
            "dist",
            ".env",
            ".evolution-backups",
        }
        return any(pattern in path.parts for pattern in skip_patterns)


def get_backup_manager() -> BackupManager:
    """Dependency for FastAPI endpoints."""
    return BackupManager()
