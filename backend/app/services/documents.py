import asyncio
import base64
import binascii
import io
import json
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from backend.app.schemas.chat import ChatAttachment
from backend.app.services.artifacts import ArtifactService, get_artifact_service
from backend.app.services.image_intel import max_image_bytes_for_metadata
from backend.app.services.vision import VisionService, get_vision_service


class DocumentService:
    """Handle uploaded files and turn them into prompt-ready context blocks."""

    def __init__(
        self,
        artifact_service: ArtifactService,
        vision_service: VisionService,
    ) -> None:
        self.artifact_service = artifact_service
        self.vision_service = vision_service

    async def ingest_base64_upload(
        self,
        session_id: str,
        filename: str,
        content_type: str,
        data_base64: str,
    ) -> ChatAttachment:
        try:
            binary = base64.b64decode(data_base64, validate=True)
        except binascii.Error as exc:
            raise ValueError("The uploaded file payload was not valid base64.") from exc

        kind = self._detect_kind(filename, content_type)
        content, metadata = await self._extract_upload_content(
            binary=binary,
            filename=filename,
            content_type=content_type,
            kind=kind,
        )
        artifact = await self.artifact_service.create_artifact(
            session_id=session_id,
            kind=kind,
            title=filename,
            content=content,
            metadata={
                "filename": filename,
                "content_type": content_type,
                "size": len(binary),
                "preview": content[:240],
                **metadata,
            },
        )
        return ChatAttachment(
            id=artifact["id"],
            name=filename,
            kind=kind,
            content_type=content_type,
            size=len(binary),
            preview=content[:240],
        )

    async def build_context(
        self,
        session_id: str | None,
        attachments: list[ChatAttachment],
        user_message: str,
    ) -> list[str]:
        attachment_ids = [attachment.id for attachment in attachments]
        artifacts: list[dict] = []
        for attachment_id in attachment_ids:
            artifact = await self.artifact_service.get_artifact(attachment_id)
            if artifact is not None:
                artifacts.append(artifact)

        if not artifacts and session_id and self._should_load_session_documents(user_message):
            artifacts = await self.artifact_service.list_artifacts(
                session_id=session_id,
                kinds=["txt", "pdf", "docx", "archive", "image", "video"],
                limit=3,
            )

        context: list[str] = []
        total_chars = 0
        for artifact in artifacts:
            excerpt = artifact["content"][:3000]
            if not excerpt.strip():
                continue
            block = self._format_artifact_context(artifact, excerpt)
            if total_chars + len(block) > 8000:
                break
            total_chars += len(block)
            context.append(block)
        return context

    async def extract_binary_document(
        self,
        binary: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        kind = self._detect_kind(filename, content_type)
        if kind not in {"txt", "pdf", "docx"}:
            raise ValueError("Only text, PDF, and DOCX resources can be parsed as documents.")
        text = await asyncio.to_thread(self._extract_text, binary, filename, kind)
        return kind, text

    async def reassign_session(self, old_session_id: str, new_session_id: str) -> None:
        await self.artifact_service.reassign_session(old_session_id, new_session_id)

    def storage_mode(self) -> str:
        return self.artifact_service.storage_mode()

    async def _extract_upload_content(
        self,
        binary: bytes,
        filename: str,
        content_type: str,
        kind: str,
    ) -> tuple[str, dict]:
        if kind in {"txt", "pdf", "docx"}:
            extracted = await asyncio.to_thread(self._extract_text, binary, filename, kind)
            return extracted, {}
        if kind == "archive":
            extracted, metadata = await asyncio.to_thread(self._extract_archive, binary, filename)
            return extracted, metadata
        if kind == "image":
            return await self._summarize_image(binary, filename, content_type)
        if kind == "video":
            return await self._summarize_video(binary, filename, content_type)
        raise ValueError(f"Unsupported file type for {filename}")

    async def _summarize_image(
        self,
        binary: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[str, dict]:
        media_info = await asyncio.to_thread(self._probe_visual_file, binary, filename)
        prompt = (
            "Describe this uploaded image for the assistant. Mention important objects, people, "
            "screens, charts, documents, visible text, and the overall scene. Be explicit about "
            "uncertainty and avoid inventing details."
        )
        metadata: dict[str, str | int | float] = dict(media_info)
        header = self._format_media_header("image", filename, media_info)
        b64 = base64.b64encode(binary).decode("ascii")
        if len(binary) <= max_image_bytes_for_metadata():
            metadata["image_base64"] = b64
        try:
            summary, model = await asyncio.wait_for(
                self.vision_service.analyze_images(
                    images_base64=[b64],
                    prompt=prompt,
                ),
                timeout=30.0,
            )
            metadata["analysis_model"] = model
            content = f"{header}\nVision summary:\n{summary}"
        except asyncio.TimeoutError:
            metadata["analysis_error"] = "vision analysis timeout"
            content = (
                f"{header}\n"
                "Vision summary:\n"
                "Image analysis took too long. The image is stored but analysis was skipped. "
                "The assistant will still have access to the image."
            )
        except Exception as exc:
            metadata["analysis_error"] = str(exc)
            content = (
                f"{header}\n"
                "Vision summary:\n"
                "Automatic image analysis is unavailable: Ollama has no vision model selected. "
                "Install one (for example `ollama pull llava` or `ollama pull moondream`), "
                "restart the backend, or set OLLAMA_VISION_MODEL to the exact model tag (e.g. llava:7b). "
                "The file is still stored and you can retry after that."
            )
        return content, metadata

    async def _summarize_video(
        self,
        binary: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[str, dict]:
        media_info, sampled_frames = await asyncio.to_thread(
            self._prepare_video_analysis,
            binary,
            filename,
        )
        metadata: dict[str, str | int | float] = dict(media_info)
        header = self._format_media_header("video", filename, media_info)
        if not sampled_frames:
            content = (
                f"{header}\n"
                "Video analysis summary:\n"
                "No preview frames could be extracted from this video, so only technical metadata "
                "was saved."
            )
            return content, metadata

        prompt = (
            "These images are sampled frames from an uploaded video. Summarize the visible story, "
            "scene changes, actions, setting, and any readable on-screen text. State clearly that "
            "the result is based on sampled frames and may miss audio-only details."
        )
        try:
            summary, model = await asyncio.wait_for(
                self.vision_service.analyze_images(
                    images_base64=sampled_frames,
                    prompt=prompt,
                ),
                timeout=30.0,
            )
            metadata["analysis_model"] = model
            metadata["sampled_frame_count"] = len(sampled_frames)
            content = f"{header}\nVideo analysis summary:\n{summary}"
        except asyncio.TimeoutError:
            metadata["analysis_error"] = "vision analysis timeout"
            content = (
                f"{header}\n"
                "Video analysis summary:\n"
                "Video analysis took too long. The video is stored but analysis was skipped. "
                "The assistant will still have access to the video frames."
            )
        except Exception as exc:
            metadata["analysis_error"] = str(exc)
            content = (
                f"{header}\n"
                "Video analysis summary:\n"
                "Frame sampling succeeded, but automatic visual analysis is unavailable right now. "
                "The video metadata was still saved."
            )
        return content, metadata

    def _detect_kind(self, filename: str, content_type: str) -> str:
        suffix = Path(filename).suffix.lower()
        normalized_type = content_type.lower()

        text_suffixes = {
            ".txt",
            ".md",
            ".csv",
            ".json",
            ".log",
            ".yaml",
            ".yml",
            ".xml",
            ".html",
            ".css",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".py",
            ".java",
            ".cs",
            ".go",
            ".rs",
            ".sql",
        }
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        video_suffixes = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

        if suffix == ".zip" or normalized_type in {"application/zip", "application/x-zip-compressed"}:
            return "archive"
        if suffix == ".pdf" or normalized_type == "application/pdf":
            return "pdf"
        if suffix == ".docx" or "wordprocessingml" in normalized_type:
            return "docx"
        if normalized_type.startswith("image/") or suffix in image_suffixes:
            return "image"
        if normalized_type.startswith("video/") or suffix in video_suffixes:
            return "video"
        if normalized_type.startswith("text/") or suffix in text_suffixes:
            return "txt"
        raise ValueError(f"Unsupported file type for {filename}")

    def _extract_text(self, binary: bytes, filename: str, kind: str) -> str:
        if kind == "txt":
            return self._extract_txt(binary)
        if kind == "docx":
            return self._extract_docx(binary)
        if kind == "pdf":
            return self._extract_pdf(binary)
        raise ValueError(f"Unsupported file type for {filename}")

    def _extract_txt(self, binary: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return binary.decode(encoding)
            except UnicodeDecodeError:
                continue
        return binary.decode("utf-8", errors="ignore")

    def _extract_archive(self, binary: bytes, filename: str) -> tuple[str, dict]:
        supported_suffixes = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt",
            ".css", ".html", ".yml", ".yaml", ".toml", ".env", ".java",
            ".cs", ".go", ".rs", ".sql", ".xml", ".sh",
        }
        important_names = {
            "package.json", "tsconfig.json", "vite.config.js", "vite.config.ts",
            "requirements.txt", "pyproject.toml", "dockerfile", "docker-compose.yml",
            ".env", ".env.example", "README.md",
        }
        sections: list[str] = [f"Uploaded archive: {filename}"]
        file_count = 0
        total_chars = 0
        max_files = 28
        max_chars = 22000
        file_entries: list[tuple[str, str]] = []
        tree_roots: dict[str, int] = {}
        frameworks: set[str] = set()
        dependencies: list[str] = []
        important_configs: list[str] = []

        with ZipFile(io.BytesIO(binary)) as archive:
            names = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                path = Path(info.filename)
                suffix = path.suffix.lower()
                if suffix not in supported_suffixes and path.name not in important_names:
                    continue
                names.append(info.filename)
                if path.parts:
                    tree_roots[path.parts[0]] = tree_roots.get(path.parts[0], 0) + 1

            sections.append(f"Contained source files: {len(names)}")
            for name in names:
                try:
                    payload = archive.read(name)
                except Exception:
                    continue
                content = self._extract_txt(payload).strip()
                if not content:
                    continue
                file_entries.append((name, content))
                file_path = Path(name)
                if file_path.name in important_names:
                    important_configs.append(name)
                detected = self._detect_archive_frameworks(name, content)
                frameworks.update(detected["frameworks"])
                dependencies.extend(detected["dependencies"])

            unique_dependencies = list(dict.fromkeys(dependencies))
            dependency_preview = ", ".join(unique_dependencies[:12]) if unique_dependencies else "unknown"
            framework_list = sorted(frameworks)
            sections.append(f"Detected frameworks: {', '.join(framework_list) if framework_list else 'unknown'}")
            sections.append(f"Dependency signals: {dependency_preview}")
            if tree_roots:
                top_roots = ", ".join(f"{name} ({count})" for name, count in sorted(tree_roots.items())[:12])
                sections.append(f"Top-level structure: {top_roots}")
            if important_configs:
                sections.append(f"Important config files: {', '.join(sorted(dict.fromkeys(important_configs))[:12])}")

            prioritized_entries = sorted(
                file_entries,
                key=lambda item: self._archive_priority(item[0], important_names),
            )
            for name, content in prioritized_entries[:max_files]:
                snippet = content[:1600]
                block = f"\nFILE: {name}\n```\n{snippet}\n```"
                if total_chars + len(block) > max_chars:
                    break
                sections.append(block)
                total_chars += len(block)
                file_count += 1

        sections.append(f"Indexed files included in prompt context: {file_count}")
        return "\n".join(sections), {
            "frameworks": framework_list,
            "dependencies": unique_dependencies[:20],
            "top_level_entries": sorted(tree_roots.keys())[:20],
            "important_configs": sorted(dict.fromkeys(important_configs))[:20],
            "indexed_file_count": file_count,
            "archive_source_file_count": len(names),
        }

    def _detect_archive_frameworks(self, name: str, content: str) -> dict:
        lower_name = name.lower()
        lower_content = content.lower()
        frameworks: set[str] = set()
        dependencies: list[str] = []

        if lower_name.endswith("package.json"):
            try:
                package = json.loads(content)
            except json.JSONDecodeError:
                package = {}
            dep_map = {}
            dep_map.update(package.get("dependencies", {}))
            dep_map.update(package.get("devDependencies", {}))
            deps = list(dep_map.keys())
            dependencies.extend(deps[:30])
            known = {
                "react": "React",
                "next": "Next.js",
                "vite": "Vite",
                "vue": "Vue",
                "@angular/core": "Angular",
                "svelte": "Svelte",
                "express": "Express",
            }
            for dep, label in known.items():
                if dep in dep_map:
                    frameworks.add(label)

        if lower_name.endswith("requirements.txt") or lower_name.endswith("pyproject.toml"):
            if "fastapi" in lower_content:
                frameworks.add("FastAPI")
            if "django" in lower_content:
                frameworks.add("Django")
            if "flask" in lower_content:
                frameworks.add("Flask")
            for line in content.splitlines():
                normalized = line.strip()
                if normalized and not normalized.startswith("#"):
                    dependencies.append(normalized[:64])

        if lower_name.endswith(".tsx") or lower_name.endswith(".jsx"):
            frameworks.add("React")
        if "vite.config" in lower_name:
            frameworks.add("Vite")

        return {"frameworks": frameworks, "dependencies": dependencies}

    def _archive_priority(self, name: str, important_names: set[str]) -> tuple[int, str]:
        path = Path(name)
        if path.name in important_names:
            return (0, name)
        if any(part in {"src", "app", "components", "pages", "backend"} for part in path.parts):
            return (1, name)
        return (2, name)

    def _extract_docx(self, binary: bytes) -> str:
        with ZipFile(io.BytesIO(binary)) as archive:
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
        text = " ".join(node.text for node in root.iter() if node.text)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_pdf(self, binary: bytes) -> str:
        pdftotext = shutil.which("pdftotext")
        if pdftotext:
            with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
                handle.write(binary)
                handle.flush()
                result = subprocess.run(
                    [pdftotext, handle.name, "-"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()

        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as exc:
            raise ValueError(
                "PDF parsing requires `pdftotext` or the optional `pypdf` package."
            ) from exc

        reader = PdfReader(io.BytesIO(binary))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            raise ValueError("The PDF did not contain extractable text.")
        return text

    def _probe_visual_file(self, binary: bytes, filename: str) -> dict:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return {}
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".bin") as handle:
            handle.write(binary)
            handle.flush()
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_streams",
                    "-show_format",
                    handle.name,
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}
        stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {})
        format_info = data.get("format", {})
        details: dict[str, str | int | float] = {}
        if stream.get("width"):
            details["width"] = int(stream["width"])
        if stream.get("height"):
            details["height"] = int(stream["height"])
        if stream.get("codec_name"):
            details["codec"] = str(stream["codec_name"])
        if format_info.get("duration"):
            try:
                details["duration_seconds"] = round(float(format_info["duration"]), 2)
            except (TypeError, ValueError):
                pass
        return details

    def _prepare_video_analysis(self, binary: bytes, filename: str) -> tuple[dict, list[str]]:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            return {}, []

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / (Path(filename).name or "upload.mp4")
            video_path.write_bytes(binary)
            info = self._probe_visual_file(binary, filename)
            duration = float(info.get("duration_seconds", 0) or 0)
            sampled_frames: list[str] = []
            for index, timestamp in enumerate(self._sample_timestamps(duration), start=1):
                frame_path = Path(temp_dir) / f"frame-{index}.jpg"
                result = subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-ss",
                        str(timestamp),
                        "-i",
                        str(video_path),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "3",
                        str(frame_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=40,
                    check=False,
                )
                if result.returncode != 0 or not frame_path.exists():
                    continue
                sampled_frames.append(base64.b64encode(frame_path.read_bytes()).decode("ascii"))
            return info, sampled_frames

    def _sample_timestamps(self, duration_seconds: float) -> list[float]:
        if duration_seconds <= 0:
            return [0.0]
        if duration_seconds < 6:
            return [0.0, round(duration_seconds / 2, 2)]
        candidates = [
            round(duration_seconds * 0.15, 2),
            round(duration_seconds * 0.5, 2),
            round(duration_seconds * 0.85, 2),
        ]
        return list(dict.fromkeys(candidates))

    def _format_media_header(self, kind: str, filename: str, media_info: dict) -> str:
        lines = [f"Uploaded {kind}: {filename}"]
        if media_info.get("width") and media_info.get("height"):
            lines.append(f"Resolution: {media_info['width']}x{media_info['height']}")
        if media_info.get("duration_seconds"):
            lines.append(f"Duration: {media_info['duration_seconds']} seconds")
        if media_info.get("codec"):
            lines.append(f"Codec: {media_info['codec']}")
        return "\n".join(lines)

    def _format_artifact_context(self, artifact: dict, excerpt: str) -> str:
        labels = {
            "txt": "Attached text file",
            "pdf": "Attached PDF",
            "docx": "Attached Word document",
            "archive": "Attached project archive",
            "image": "Attached image",
            "video": "Attached video",
        }
        label = labels.get(artifact["kind"], "Attached file")
        return (
            f"{label}: {artifact['title']}\n"
            f"Type: {artifact['kind']}\n"
            f"Content excerpt:\n{excerpt}"
        )

    def _should_load_session_documents(self, user_message: str) -> bool:
        lower = user_message.lower()
        phrases = [
            "document",
            "file",
            "project",
            "codebase",
            "repository",
            "repo",
            "archive",
            "zip",
            "attached",
            "attachment",
            "pdf",
            "docx",
            "word file",
            "txt file",
            "summarize this",
            "based on the file",
            "upload",
            "uploaded",
            "image",
            "picture",
            "photo",
            "screenshot",
            "video",
            "clip",
        ]
        return any(phrase in lower for phrase in phrases)


@lru_cache
def get_document_service() -> DocumentService:
    return DocumentService(
        artifact_service=get_artifact_service(),
        vision_service=get_vision_service(),
    )
