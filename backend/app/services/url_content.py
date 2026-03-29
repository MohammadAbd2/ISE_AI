import asyncio
import base64
import html
from html.parser import HTMLParser
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import httpx

from backend.app.services.artifacts import ArtifactService, get_artifact_service
from backend.app.services.documents import DocumentService, get_document_service
from backend.app.services.vision import VisionService, get_vision_service


class _VisibleTextParser(HTMLParser):
    """Collect readable text while ignoring script and style content."""

    def __init__(self) -> None:
        super().__init__()
        self._ignored_tags: list[str] = []
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_tags.append(tag)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_tags and self._ignored_tags[-1] == tag:
            self._ignored_tags.pop()
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignored_tags:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        else:
            self.text_parts.append(cleaned)


class UrlContentService:
    """Read URLs, image links, and YouTube videos into structured prompt context."""

    URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+")

    def __init__(
        self,
        artifact_service: ArtifactService,
        document_service: DocumentService,
        vision_service: VisionService,
    ) -> None:
        self.artifact_service = artifact_service
        self.document_service = document_service
        self.vision_service = vision_service

    def extract_urls(self, text: str) -> list[str]:
        found = [match.group(0).rstrip(".,)") for match in self.URL_PATTERN.finditer(text)]
        return list(dict.fromkeys(found))

    async def build_context(
        self,
        session_id: str | None,
        user_message: str,
    ) -> list[str]:
        if session_id is None:
            return []

        urls = self.extract_urls(user_message)
        if urls:
            context: list[str] = []
            for url in urls[:2]:
                artifact = await self._ingest_url(session_id, url)
                if artifact and artifact.get("content", "").strip():
                    context.append(
                        f"Referenced URL: {artifact['title']}\n"
                        f"Type: {artifact['kind']}\n"
                        f"Content excerpt:\n{artifact['content'][:3200]}"
                    )
            return context

        if not self._should_load_recent(user_message):
            return []

        artifacts = await self.artifact_service.list_artifacts(
            session_id=session_id,
            kinds=["url", "youtube", "image-url", "video-url"],
            limit=3,
        )
        context = []
        for artifact in artifacts:
            excerpt = artifact.get("content", "")[:2200]
            if not excerpt.strip():
                continue
            context.append(
                f"Recent web source: {artifact['title']}\n"
                f"Type: {artifact['kind']}\n"
                f"Content excerpt:\n{excerpt}"
            )
        return context

    async def _ingest_url(self, session_id: str, url: str) -> dict:
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            return await self._ingest_youtube_url(session_id, url)

        filename = Path(parsed.path).name or parsed.netloc or "url"
        suffix = Path(filename).suffix.lower()
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "ISE-AI/1.0"},
            )
            response.raise_for_status()

        content_type = response.headers.get("content-type", "text/html").split(";", 1)[0].strip()
        if content_type in {"text/html", "application/xhtml+xml"}:
            return await self._ingest_webpage_url(session_id, url, response.text)
        if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
            return await self._ingest_image_url(session_id, url, filename, content_type, response.content)
        if content_type.startswith("video/") or suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
            return await self._ingest_remote_video_url(session_id, url, filename, content_type)
        if (
            content_type.startswith("text/")
            or content_type in {
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
            or suffix in {".pdf", ".docx", ".txt", ".md", ".json", ".csv", ".xml"}
        ):
            return await self._ingest_document_url(
                session_id,
                url,
                filename,
                content_type,
                response.content,
            )
        return await self._ingest_webpage_url(session_id, url, response.text)

    async def _ingest_document_url(
        self,
        session_id: str,
        url: str,
        filename: str,
        content_type: str,
        binary: bytes,
    ) -> dict:
        kind, content = await self.document_service.extract_binary_document(
            binary=binary,
            filename=filename,
            content_type=content_type,
        )
        return await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="url",
            title=url,
            content=(
                f"Remote document URL: {url}\n"
                f"Detected type: {kind}\n"
                f"Document excerpt:\n{content[:4000]}"
            ),
            metadata={
                "url": url,
                "source_kind": kind,
            },
        )

    async def _ingest_webpage_url(self, session_id: str, url: str, html_text: str) -> dict:
        title, body = await asyncio.to_thread(self._extract_webpage_text, html_text)
        content = (
            f"Web page URL: {url}\n"
            f"Title: {title or 'Unknown title'}\n"
            f"Page excerpt:\n{body[:4200]}"
        )
        return await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="url",
            title=title or url,
            content=content,
            metadata={"url": url},
        )

    async def _ingest_image_url(
        self,
        session_id: str,
        url: str,
        filename: str,
        content_type: str,
        binary: bytes,
    ) -> dict:
        prompt = (
            "Describe this image fetched from a URL. Mention the main subject, setting, any visible "
            "text, and important details without inventing specifics."
        )
        try:
            summary, model = await self.vision_service.analyze_images(
                images_base64=[base64.b64encode(binary).decode("ascii")],
                prompt=prompt,
            )
            content = f"Image URL: {url}\nVision summary:\n{summary}"
            metadata = {"url": url, "analysis_model": model, "content_type": content_type}
        except Exception as exc:
            content = (
                f"Image URL: {url}\n"
                "Vision summary:\n"
                "Automatic image analysis is unavailable right now."
            )
            metadata = {"url": url, "analysis_error": str(exc), "content_type": content_type}
        return await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="image-url",
            title=filename or url,
            content=content,
            metadata=metadata,
        )

    async def _ingest_remote_video_url(
        self,
        session_id: str,
        url: str,
        filename: str,
        content_type: str,
    ) -> dict:
        info, frames = await asyncio.to_thread(self._sample_remote_video_frames, url)
        lines = [f"Video URL: {url}"]
        if info.get("width") and info.get("height"):
            lines.append(f"Resolution: {info['width']}x{info['height']}")
        if info.get("duration_seconds"):
            lines.append(f"Duration: {info['duration_seconds']} seconds")
        if info.get("codec"):
            lines.append(f"Codec: {info['codec']}")
        if frames:
            try:
                summary, model = await self.vision_service.analyze_images(
                    images_base64=frames,
                    prompt=(
                        "These are sampled frames from a video URL. Summarize the visible content, "
                        "scene changes, and any readable on-screen text. Mention that this is based "
                        "on sampled frames only."
                    ),
                )
                lines.append("Video summary:")
                lines.append(summary)
                metadata = {
                    "url": url,
                    "analysis_model": model,
                    "content_type": content_type,
                }
            except Exception as exc:
                lines.append("Video summary:")
                lines.append("Visual analysis is unavailable right now.")
                metadata = {
                    "url": url,
                    "analysis_error": str(exc),
                    "content_type": content_type,
                }
        else:
            lines.append("Video summary:")
            lines.append("No preview frames could be extracted from this remote video.")
            metadata = {"url": url, "content_type": content_type}
        return await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="video-url",
            title=filename or url,
            content="\n".join(lines),
            metadata=metadata,
        )

    async def _ingest_youtube_url(self, session_id: str, url: str) -> dict:
        metadata = await asyncio.to_thread(self._youtube_metadata, url)
        transcript = await asyncio.to_thread(self._youtube_transcript, url)

        title = metadata.get("title") or url
        duration = metadata.get("duration")
        uploader = metadata.get("uploader") or metadata.get("channel") or "Unknown"
        description = metadata.get("description", "")

        lines = [f"YouTube URL: {url}", f"Title: {title}", f"Channel: {uploader}"]
        if duration:
            lines.append(f"Duration: {duration} seconds")
        if description:
            lines.append(f"Description excerpt:\n{description[:1800]}")
        if transcript:
            lines.append(f"Transcript excerpt:\n{transcript[:2800]}")

        return await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="youtube",
            title=title,
            content="\n".join(lines),
            metadata={
                "url": url,
                "channel": uploader,
                "duration": duration,
            },
        )

    def _extract_webpage_text(self, html_text: str) -> tuple[str, str]:
        parser = _VisibleTextParser()
        parser.feed(html_text)
        title = html.unescape(" ".join(parser.title_parts)).strip()
        body = html.unescape(" ".join(parser.text_parts)).strip()
        body = re.sub(r"\s+", " ", body)
        return title, body

    def _sample_remote_video_frames(self, url: str) -> tuple[dict, list[str]]:
        ffprobe = shutil.which("ffprobe")
        ffmpeg = shutil.which("ffmpeg")
        if not ffprobe or not ffmpeg:
            return {}, []

        info = self._probe_remote_video(url)
        duration = float(info.get("duration_seconds", 0) or 0)
        timestamps = self._video_timestamps(duration)
        frames: list[str] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, timestamp in enumerate(timestamps, start=1):
                frame_path = Path(temp_dir) / f"remote-frame-{index}.jpg"
                result = subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-ss",
                        str(timestamp),
                        "-i",
                        url,
                        "-frames:v",
                        "1",
                        "-q:v",
                        "3",
                        str(frame_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if result.returncode != 0 or not frame_path.exists():
                    continue
                frames.append(base64.b64encode(frame_path.read_bytes()).decode("ascii"))
        return info, frames

    def _probe_remote_video(self, url: str) -> dict:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return {}
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        try:
            import json

            data = json.loads(result.stdout)
        except Exception:
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

    def _video_timestamps(self, duration_seconds: float) -> list[float]:
        if duration_seconds <= 0:
            return [0.0]
        if duration_seconds < 6:
            return [0.0, round(duration_seconds / 2, 2)]
        return [
            round(duration_seconds * 0.15, 2),
            round(duration_seconds * 0.5, 2),
            round(duration_seconds * 0.85, 2),
        ]

    def _youtube_metadata(self, url: str) -> dict:
        yt_dlp = shutil.which("yt-dlp")
        if not yt_dlp:
            return {}
        result = subprocess.run(
            [yt_dlp, "--dump-single-json", "--skip-download", "--no-warnings", url],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        try:
            import json

            return json.loads(result.stdout)
        except Exception:
            return {}

    def _youtube_transcript(self, url: str) -> str:
        yt_dlp = shutil.which("yt-dlp")
        if not yt_dlp:
            return ""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_template = str(Path(temp_dir) / "%(id)s.%(ext)s")
            subprocess.run(
                [
                    yt_dlp,
                    "--skip-download",
                    "--write-auto-subs",
                    "--write-subs",
                    "--sub-langs",
                    "en.*,en",
                    "--sub-format",
                    "vtt",
                    "--no-warnings",
                    "-o",
                    output_template,
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            subtitle_files = sorted(Path(temp_dir).glob("*.vtt"))
            if not subtitle_files:
                return ""
            return self._clean_vtt(subtitle_files[0].read_text(encoding="utf-8", errors="ignore"))

    def _clean_vtt(self, raw_text: str) -> str:
        lines = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped == "WEBVTT":
                continue
            if "-->" in stripped:
                continue
            if stripped.isdigit():
                continue
            lines.append(stripped)
        cleaned = " ".join(lines)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _should_load_recent(self, user_message: str) -> bool:
        lower = user_message.lower()
        phrases = [
            "link",
            "url",
            "website",
            "web page",
            "page",
            "article",
            "youtube",
            "video",
            "that source",
            "that result",
        ]
        return any(phrase in lower for phrase in phrases)


@lru_cache
def get_url_content_service() -> UrlContentService:
    return UrlContentService(
        artifact_service=get_artifact_service(),
        document_service=get_document_service(),
        vision_service=get_vision_service(),
    )
