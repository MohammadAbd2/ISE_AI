from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import hashlib
import html
import json
import re
import textwrap
from uuid import uuid4

from app.services.artifacts import get_artifact_service
from app.services.safe_file_writer import atomic_write_bytes, verify_text_content

GENERATED_DIR = Path(__file__).resolve().parents[3] / "generated_artifacts"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

EXT_MIME = {
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".jsx": "text/javascript; charset=utf-8",
    ".ts": "text/typescript; charset=utf-8",
    ".tsx": "text/typescript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".mmd": "text/plain; charset=utf-8",
}

ICONS = {".txt":"📄",".md":"📝",".js":"🟨",".jsx":"⚛️",".ts":"🔷",".tsx":"⚛️",".json":"{}",".html":"🌐",".css":"🎨",".py":"🐍",".pdf":"📕",".docx":"📘",".mmd":"📊"}

@dataclass
class GeneratedFile:
    artifact_id: str
    filename: str
    extension: str
    path: str
    content_type: str
    size_bytes: int
    sha256: str
    icon: str
    download_url: str
    write_verified: bool = True
    write_attempts: int = 1


def sanitize_filename(name: str, extension: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "generated-file")).strip(".-") or "generated-file"
    ext = extension if extension.startswith(".") else f".{extension}"
    if ext.lower() not in EXT_MIME:
        ext = ".txt"
    if not stem.lower().endswith(ext.lower()):
        stem += ext
    return stem[:120]


def _minimal_pdf_bytes(title: str, content: str) -> bytes:
    # Keep the whole requested message visible by wrapping instead of slicing.
    safe = (title + "\n\n" + content).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    wrapped: list[str] = []
    for raw_line in safe.splitlines() or [safe]:
        wrapped.extend(textwrap.wrap(raw_line, width=92, replace_whitespace=False, drop_whitespace=False) or [""])
    lines = wrapped[:90]
    text_ops = ["BT /F1 11 Tf 50 780 Td 13 TL"]
    for line in lines:
        text_ops.append(f"({line}) Tj T*")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", "replace")
    objs = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode() + stream + b"\nendstream endobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    xrefs = [0]
    for obj in objs:
        xrefs.append(len(out)); out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(xrefs)}\n0000000000 65535 f \n".encode())
    for pos in xrefs[1:]:
        out.extend(f"{pos:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Root 1 0 R /Size {len(xrefs)} >>\nstartxref\n{xref_pos}\n%%EOF".encode())
    return bytes(out)


def _minimal_docx_bytes(title: str, content: str) -> bytes:
    import io, zipfile
    body = "".join(f"<w:p><w:r><w:t>{html.escape(line)}</w:t></w:r></w:p>" for line in (title + "\n\n" + content).splitlines())
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}<w:sectPr/></w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


async def generate_downloadable_file(session_id: str, filename: str, content: str, extension: str = ".txt", title: str | None = None) -> dict:
    filename = sanitize_filename(filename or title or "generated-file", extension)
    ext = Path(filename).suffix.lower()
    file_id = uuid4().hex
    out_path = GENERATED_DIR / f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{file_id}-{filename}"
    if ext == ".pdf":
        data = _minimal_pdf_bytes(title or filename, content)
    elif ext == ".docx":
        data = _minimal_docx_bytes(title or filename, content)
    else:
        if ext == ".json":
            try:
                content = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
            except Exception:
                pass
        data = content.encode("utf-8")
    write_result = atomic_write_bytes(out_path, data)
    sha = write_result.sha256
    text_verification = verify_text_content(out_path, content) if ext not in {".pdf", ".docx"} else {"ok": True, "reason": "binary_document", "expected_chars": len(content)}
    artifact = await get_artifact_service().create_artifact(
        session_id=session_id or "default",
        kind="downloadable-file",
        title=title or filename,
        content=content,
        metadata={
            "filename": filename,
            "download_path": str(out_path),
            "content_type": EXT_MIME.get(ext, "application/octet-stream"),
            "sha256": sha,
            "size_bytes": len(data),
            "extension": ext,
            "icon": ICONS.get(ext, "📦"),
            "preview": content[:12000],
            "write_verified": write_result.verified,
            "write_attempts": write_result.attempts,
            "content_verification": text_verification,
        },
    )
    return GeneratedFile(
        artifact_id=artifact["id"],
        filename=filename,
        extension=ext,
        path=str(out_path),
        content_type=EXT_MIME.get(ext,"application/octet-stream"),
        size_bytes=len(data),
        sha256=sha,
        icon=ICONS.get(ext,"📦"),
        download_url=f"/api/artifacts/{artifact['id']}/download",
        write_verified=write_result.verified,
        write_attempts=write_result.attempts,
    ).__dict__
