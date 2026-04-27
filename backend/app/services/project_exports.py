from __future__ import annotations

import asyncio
import hashlib
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from app.core.config import settings
from app.services.artifacts import ArtifactService, get_artifact_service
from app.services.artifact_manifest import write_manifest_sidecar


DEFAULT_EXCLUDES = {
    '.git', '.idea', '.venv', 'node_modules', '__pycache__', '.pytest_cache', 'dist', 'build',
    '.ise_ai_workspace', '.ise_ai_self_rewrites', '.ise_ai_checkpoints', '.mypy_cache',
}


@dataclass(slots=True)
class ProjectExportResult:
    zip_path: Path
    artifact: dict | None
    file_count: int
    source_dir: Path


def _safe_zip_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in str(name or "generated.zip"))
    cleaned = cleaned.strip(".-_") or "generated"
    return cleaned if cleaned.endswith(".zip") else f"{cleaned}.zip"


class ProjectExportService:
    def __init__(self, artifact_service: ArtifactService | None = None) -> None:
        self.artifact_service = artifact_service or get_artifact_service()
        base_output = Path(getattr(settings, "output_path", Path(settings.project_root) / "output")).resolve()
        if str(base_output).startswith(str(Path(settings.project_root).resolve())):
            base_output = (Path.home() / ".cache" / "ise_ai" / "runtime").resolve()
        self.exports_root = base_output / "_exports"
        self.exports_root.mkdir(parents=True, exist_ok=True)

    async def export_paths(
        self,
        *,
        root_dir: Path,
        relative_paths: Iterable[str],
        session_id: str,
        title: str | None = None,
        filename: str | None = None,
        package_root: str | None = None,
        extra_include_paths: Iterable[str] | None = None,
        export_mode: str = "selected",
    ) -> ProjectExportResult:
        root_dir = root_dir.resolve()
        if not root_dir.exists() or not root_dir.is_dir():
            raise FileNotFoundError(f'Project directory not found: {root_dir}')

        unique_paths: list[Path] = []
        seen: set[str] = set()
        for raw in list(relative_paths or []) + list(extra_include_paths or []):
            if not isinstance(raw, str):
                continue
            candidate = raw.strip().replace('\\', '/')
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            unique_paths.append(Path(candidate))

        if not unique_paths:
            raise FileNotFoundError('No exportable paths were provided')

        safe_name = _safe_zip_name(filename or 'generated-files.zip')
        zip_path, file_count = await asyncio.to_thread(
            self._zip_selected_paths,
            root_dir,
            unique_paths,
            self.exports_root / safe_name,
            package_root or '',
        )
        manifest = write_manifest_sidecar(zip_path, artifact_id='pending')
        artifact = await self.artifact_service.create_artifact(
            session_id=session_id,
            kind='project-export',
            title=title or f'{safe_name} export',
            content=f'Selected export for {safe_name}',
            metadata={
                'filename': zip_path.name,
                'download_path': str(zip_path),
                'source_dir': str(root_dir),
                'file_count': file_count,
                'selected_paths': [path.as_posix() for path in unique_paths],
                'preview': f'ZIP export generated with {file_count} files.',
                'content_type': 'application/zip',
                'size_bytes': zip_path.stat().st_size,
                'sha256': self._sha256(zip_path),
                'download_url': '',
                'manifest': manifest,
                'manifest_path': str(zip_path.with_suffix(zip_path.suffix + '.manifest.json')),
                'export_mode': export_mode,
                'verified': True,
                'download_url': '',
            },
        )
        return ProjectExportResult(zip_path=zip_path, artifact=artifact, file_count=file_count, source_dir=root_dir)

    async def export_directory(
        self,
        source_dir: Path,
        session_id: str,
        title: str | None = None,
        filename: str | None = None,
        exclude_names: Iterable[str] | None = None,
    ) -> ProjectExportResult:
        source_dir = source_dir.resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise FileNotFoundError(f'Project directory not found: {source_dir}')

        safe_name = _safe_zip_name(filename or f"{source_dir.name}.zip")
        zip_path, file_count = await asyncio.to_thread(
            self._zip_directory,
            source_dir,
            self.exports_root / safe_name,
            set(exclude_names or DEFAULT_EXCLUDES),
        )
        manifest = write_manifest_sidecar(zip_path, artifact_id='pending')
        artifact = await self.artifact_service.create_artifact(
            session_id=session_id,
            kind='project-export',
            title=title or f'{source_dir.name} export',
            content=f'Project export for {source_dir.name}',
            metadata={
                'filename': zip_path.name,
                'download_path': str(zip_path),
                'source_dir': str(source_dir),
                'file_count': file_count,
                'preview': f'ZIP export generated from {source_dir.name} with {file_count} files.',
                'content_type': 'application/zip',
                'size_bytes': zip_path.stat().st_size,
                'sha256': self._sha256(zip_path),
                'download_url': '',
                'manifest': manifest,
                'manifest_path': str(zip_path.with_suffix(zip_path.suffix + '.manifest.json')),
                'export_mode': 'directory',
                'verified': True,
                'download_url': '',
            },
        )
        return ProjectExportResult(zip_path=zip_path, artifact=artifact, file_count=file_count, source_dir=source_dir)

    def _zip_directory(self, source_dir: Path, zip_path: Path, exclude_names: set[str]) -> tuple[Path, int]:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            zip_path.unlink()
        staging_root = zip_path.with_suffix('')
        if staging_root.exists():
            shutil.rmtree(staging_root)
        staging_root.mkdir(parents=True, exist_ok=True)
        staging_dir = staging_root / source_dir.name
        shutil.copytree(source_dir, staging_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*exclude_names))
        file_count = sum(1 for path in staging_dir.rglob('*') if path.is_file())
        archive_base = zip_path.with_suffix('')
        created = shutil.make_archive(str(archive_base), 'zip', root_dir=staging_root, base_dir=source_dir.name)
        shutil.rmtree(staging_root, ignore_errors=True)
        self.verify_export(Path(created), min_files=max(1, file_count))
        return Path(created), file_count

    def _ensure_deployment_readme(self, package_dir: Path, title: str = "Generated ISE AI project") -> int:
        readme = package_dir / "README.md"
        if readme.exists():
            return 0
        readme.write_text(
            "# Generated ISE AI project\n\n"
            "## Run locally\n\n"
            "```bash\n"
            "npm install\n"
            "npm run dev\n"
            "```\n\n"
            "## Build\n\n"
            "```bash\n"
            "npm run build\n"
            "```\n",
            encoding="utf-8",
        )
        return 1

    def _ensure_env_example(self, package_dir: Path) -> int:
        env = package_dir / ".env.example"
        if env.exists():
            return 0
        env.write_text("# Add generated project environment variables here\n", encoding="utf-8")
        return 1

    def _zip_selected_paths(self, root_dir: Path, relative_paths: list[Path], zip_path: Path, package_root: str) -> tuple[Path, int]:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            zip_path.unlink()
        staging_root = zip_path.with_suffix('')
        if staging_root.exists():
            shutil.rmtree(staging_root)
        staging_root.mkdir(parents=True, exist_ok=True)

        package_dir = staging_root / package_root if package_root and package_root != '.' else staging_root
        package_dir.mkdir(parents=True, exist_ok=True)
        file_count = 0

        for rel_path in relative_paths:
            source = (root_dir / rel_path).resolve()
            if not source.exists() or not source.is_file():
                continue
            if package_root == "generated-react-project" and rel_path.parts and rel_path.parts[0] == "frontend":
                destination = package_dir / Path(*rel_path.parts[1:])
            elif package_root == "generated-files":
                destination = package_dir / rel_path.name
            else:
                destination = package_dir / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            file_count += 1

        if file_count == 0:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise FileNotFoundError('None of the requested paths exist in the workspace')

        if package_root == "generated-react-project":
            file_count += self._ensure_deployment_readme(package_dir)
            file_count += self._ensure_env_example(package_dir)
        archive_base = zip_path.with_suffix('')
        created = shutil.make_archive(str(archive_base), 'zip', root_dir=staging_root, base_dir='.')
        shutil.rmtree(staging_root, ignore_errors=True)
        self.verify_export(Path(created), min_files=max(1, file_count))
        return Path(created), file_count

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def verify_export(self, zip_path: Path, *, min_files: int = 1) -> None:
        if not zip_path.exists() or not zip_path.is_file() or zip_path.stat().st_size <= 0:
            raise RuntimeError(f'Export archive is missing or empty: {zip_path}')
        import zipfile
        with zipfile.ZipFile(zip_path) as archive:
            names = [name for name in archive.namelist() if not name.endswith('/')]
            if len(names) < min_files:
                raise RuntimeError(f'Export archive contains {len(names)} files; expected at least {min_files}')
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f'Export archive contains corrupt entry: {bad}')


@lru_cache
def get_project_export_service() -> ProjectExportService:
    return ProjectExportService()
