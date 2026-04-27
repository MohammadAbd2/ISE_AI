from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import tempfile
from typing import Any


@dataclass(slots=True)
class SafeWriteResult:
    path: str
    bytes: int
    sha256: str
    verified: bool
    attempts: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_bytes(path: str | Path, data: bytes, *, max_attempts: int = 3) -> SafeWriteResult:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_bytes(data)
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        tmp_name = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp") as handle:
                tmp_name = handle.name
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            written = Path(tmp_name).read_bytes()
            if sha256_bytes(written) != expected:
                raise IOError("temporary write checksum mismatch")
            os.replace(tmp_name, target)
            final = target.read_bytes()
            if sha256_bytes(final) != expected:
                raise IOError("final write checksum mismatch")
            return SafeWriteResult(str(target), len(data), expected, True, attempt)
        except Exception as exc:  # retry deterministic local IO failures
            last_error = exc
            if tmp_name:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except Exception:
                    pass
    raise IOError(f"safe write failed for {target}: {last_error}")


def atomic_write_text(path: str | Path, content: str, *, encoding: str = "utf-8", max_attempts: int = 3) -> SafeWriteResult:
    return atomic_write_bytes(path, content.encode(encoding), max_attempts=max_attempts)


def verify_text_content(path: str | Path, expected: str, *, encoding: str = "utf-8") -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {"ok": False, "reason": "missing", "path": str(target)}
    actual = target.read_text(encoding=encoding)
    return {
        "ok": actual == expected,
        "reason": "matches" if actual == expected else "content_mismatch",
        "path": str(target),
        "expected_chars": len(expected),
        "actual_chars": len(actual),
        "expected_sha256": hashlib.sha256(expected.encode(encoding)).hexdigest(),
        "actual_sha256": hashlib.sha256(actual.encode(encoding)).hexdigest(),
    }
