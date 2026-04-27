"""Verified artifact manifest utilities for zero-broken-ZIP exports."""
from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(slots=True)
class ManifestEntry:
    path: str
    size: int
    sha256: str


@dataclass(slots=True)
class ArtifactManifest:
    artifact_id: str
    filename: str
    created_at: str
    total_files: int
    total_bytes: int
    zip_sha256: str
    files: list[ManifestEntry]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["files"] = [asdict(item) for item in self.files]
        return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_zip_manifest(zip_path: Path, *, artifact_id: str = "pending") -> ArtifactManifest:
    zip_path = zip_path.resolve()
    if not zip_path.exists() or zip_path.stat().st_size <= 0:
        raise RuntimeError(f"Artifact ZIP is missing or empty: {zip_path}")
    entries: list[ManifestEntry] = []
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"Artifact ZIP has corrupt entry: {bad}")
        for info in archive.infolist():
            if info.is_dir():
                continue
            data = archive.read(info.filename)
            entries.append(ManifestEntry(path=info.filename, size=len(data), sha256=hashlib.sha256(data).hexdigest()))
    if not entries:
        raise RuntimeError("Artifact ZIP has no files")
    return ArtifactManifest(artifact_id, zip_path.name, datetime.now(UTC).isoformat(), len(entries), sum(e.size for e in entries), sha256_file(zip_path), entries)


def write_manifest_sidecar(zip_path: Path, *, artifact_id: str = "pending") -> dict:
    manifest = build_zip_manifest(zip_path, artifact_id=artifact_id)
    sidecar = zip_path.with_suffix(zip_path.suffix + ".manifest.json")
    sidecar.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return manifest.to_dict()
