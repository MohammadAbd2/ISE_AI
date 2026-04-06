"""Image understanding helpers: vision tasks, image search, optional Ollama image generation."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from functools import lru_cache
from urllib.parse import quote_plus, urlparse

import httpx

from app.core.config import settings
from app.schemas.chat import ChatAttachment, ImageHit, ImageIntelLog
from app.services.artifacts import ArtifactService, get_artifact_service
from app.services.vision import VisionService, get_vision_service

_MAX_STORE_IMAGE_BYTES = 6 * 1024 * 1024


def max_image_bytes_for_metadata() -> int:
    return _MAX_STORE_IMAGE_BYTES


class ImageIntelService:
    """DuckDuckGo image search, targeted vision prompts, optional Ollama text-to-image."""

    def __init__(
        self,
        artifact_service: ArtifactService,
        vision_service: VisionService,
    ) -> None:
        self._artifacts = artifact_service
        self._vision = vision_service

    def should_activate_sync(
        self,
        user_message: str,
        attachments: list[ChatAttachment],
        session_id: str | None,
        session_has_image_artifact: bool,
    ) -> bool:
        if session_id is None:
            return False
        lower = user_message.lower()
        has_image_att = any(a.kind == "image" for a in attachments)
        if self._wants_generation(lower):
            return True
        if self._wants_image_search(lower):
            return True
        if has_image_att and (
            self._wants_extra_vision(lower)
            or self._explicit_visual_question(lower)
        ):
            return True
        if session_has_image_artifact and self._references_prior_image(lower) and (
            self._wants_image_search(lower) or self._explicit_visual_question(lower)
        ):
            return True
        if session_has_image_artifact and self._explicit_visual_question(lower) and (
            has_image_att
            or self._references_prior_image(lower)
            or self._has_direct_image_link(user_message)
        ):
            return True
        return False

    @staticmethod
    def _has_direct_image_link(text: str) -> bool:
        return bool(
            re.search(r"https?://[^\s<>\"']+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s]*)?", text, re.I)
        )

    @staticmethod
    def _wants_generation(lower: str) -> bool:
        keys = (
            "generate an image",
            "generate image",
            "create a logo",
            "make a logo",
            "design a logo",
            "draw me",
            "draw a",
            "text to image",
            "produce an image",
            "imagine a",
        )
        if any(k in lower for k in keys):
            return True
        return bool(re.match(r"^\s*imagine\b", lower))

    @staticmethod
    def _wants_image_search(lower: str) -> bool:
        keys = (
            "show me pictures",
            "show me images",
            "show me photos",
            "find images",
            "find pictures",
            "find photos",
            "search for images",
            "image search",
            "pictures of",
            "photos of",
            "stock photo",
            "give me a picture",
            "give me an image",
            "one picture for each",
            "picture for each",
            "image for each",
            "similar images",
            "similar photos",
        )
        if any(k in lower for k in keys):
            return True
        if "picture" in lower and any(w in lower for w in ("each", "every", "per", "three", "3 ", "3 images")):
            return True
        return False

    @staticmethod
    def _wants_extra_vision(lower: str) -> bool:
        keys = (
            "each animal",
            "every animal",
            "per animal",
            "one picture",
            "one image",
            "for each",
            "how many",
            "list the",
            "list all",
            "identify each",
            "separate",
        )
        return any(k in lower for k in keys)

    @staticmethod
    def _explicit_visual_question(lower: str) -> bool:
        keys = (
            "what do you see",
            "what can you see",
            "what is in the picture",
            "what's in the picture",
            "what is in this image",
            "describe the image",
            "describe this picture",
        )
        return any(k in lower for k in keys)

    @staticmethod
    def _references_prior_image(lower: str) -> bool:
        keys = ("this image", "this picture", "this photo", "the upload", "uploaded image", "that image")
        return any(k in lower for k in keys)

    async def session_has_recent_image(self, session_id: str) -> bool:
        rows = await self._artifacts.list_artifacts(
            session_id=session_id,
            kinds=["image", "image-url"],
            limit=1,
        )
        return bool(rows)

    async def run(
        self,
        session_id: str,
        user_message: str,
        attachments: list[ChatAttachment],
    ) -> tuple[list[str], list[ImageIntelLog]]:
        """Return (tool_context_lines, image_logs)."""
        lower = user_message.lower()
        has_image_att = any(a.kind == "image" for a in attachments)
        session_has = await self.session_has_recent_image(session_id)
        if not self.should_activate_sync(user_message, attachments, session_id, session_has):
            return [], []

        b64_list, filenames = await self._load_image_base64(session_id, attachments)
        vision_notes = ""
        contexts: list[str] = []
        logs: list[ImageIntelLog] = []

        need_vision = bool(b64_list) and (
            self._wants_extra_vision(lower)
            or self._explicit_visual_question(lower)
            or (self._wants_image_search(lower) and any(x in lower for x in ("white", "black", "similar", "like", "hair", "fur", "color")))
            or (self._wants_generation(lower) and any(x in lower for x in ("based on", "from the image", "like the", "this style")))
        )

        if need_vision:
            try:
                vision_notes, _model = await self._vision.analyze_images(
                    images_base64=b64_list,
                    prompt=self._vision_prompt_for_message(user_message),
                )
                contexts.append(
                    "Vision analysis (focused on your request):\n"
                    f"{vision_notes}\n"
                    "Use this when proposing image search queries or generation prompts."
                )
            except Exception as exc:
                contexts.append(
                    "Vision analysis was requested but failed or no vision model is available: "
                    f"{exc}"
                )

        if self._wants_generation(lower):
            if settings.ollama_image_model.strip():
                log = await self._try_generate(user_message, vision_notes, b64_list)
                logs.append(log)
                if log.status == "completed" and log.images:
                    contexts.append(self._format_generation_context(log))
                elif log.error:
                    contexts.append(
                        "Local image generation did not return a picture; using photo search instead.\n"
                        f"Generation detail: {log.error}"
                    )
                    async with httpx.AsyncClient(timeout=35.0, follow_redirects=True) as client:
                        await self._add_imagery_search_fallback(
                            client, user_message, vision_notes, logs, contexts, limit=8
                        )
            else:
                contexts.append(self._imagery_generation_unavailable_note())
                async with httpx.AsyncClient(timeout=35.0, follow_redirects=True) as client:
                    await self._add_imagery_search_fallback(
                        client, user_message, vision_notes, logs, contexts, limit=8
                    )

        if self._wants_image_search(lower):
            queries = self._build_image_queries(user_message, vision_notes)
            if not need_vision and not self._wants_extra_vision(lower):
                queries = queries[:1]
            min_images = 3 if any(x in lower for x in ("three", "3 ", "at least 3", "least 3")) else 5
            async with httpx.AsyncClient(timeout=35.0, follow_redirects=True) as client:
                for q in queries[:4]:
                    hits = await self._duckduckgo_image_hits(client, q, limit=max(min_images, 6))
                    if not hits:
                        continue
                    log = ImageIntelLog(
                        kind="search",
                        query=q,
                        provider="duckduckgo-images",
                        status="completed",
                        searched_at=_utc_iso(),
                        summary=f"{len(hits)} image results.",
                        images=hits,
                        vision_notes=vision_notes[:1200] if vision_notes else "",
                    )
                    logs.append(log)
                    contexts.append(self._format_search_context(log))
            if self._wants_image_search(lower) and not any(
                log.kind == "search" and log.images for log in logs
            ):
                err_log = ImageIntelLog(
                    kind="search",
                    query=user_message[:200],
                    status="failed",
                    searched_at=_utc_iso(),
                    error="No image search results were returned.",
                )
                logs.append(err_log)
                contexts.append("Image search returned no results.")

        return contexts, logs

    def _vision_prompt_for_message(self, user_message: str) -> str:
        return (
            "You are helping another model find or generate images.\n"
            "Answer clearly and factually from the image only.\n"
            "1) Short scene summary (one or two sentences).\n"
            "2) List distinct main subjects (e.g. each animal, person, or object type) as a numbered list.\n"
            "3) For each subject, suggest one short image-search query (3–8 words) that would find a representative stock-style photo.\n"
            "4) If the user cares about attributes (color, breed, pose), mention them.\n"
            "If uncertain, say you are uncertain. Do not invent species or brands.\n\n"
            f"User request: {user_message.strip()}"
        )

    def _build_image_queries(self, user_message: str, vision_notes: str) -> list[str]:
        base = re.sub(r"\s+", " ", user_message.strip())
        queries = [base[:220]]
        if vision_notes:
            for line in vision_notes.splitlines():
                m = re.match(r"^\s*\d+[\).\s]+(.+)$", line)
                if m:
                    candidate = m.group(1).strip()
                    if 8 < len(candidate) < 120 and not candidate.lower().startswith("user"):
                        queries.append(candidate)
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            key = q.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(q)
        return out[:6] or [base[:220]]

    async def _load_image_base64(
        self,
        session_id: str,
        attachments: list[ChatAttachment],
    ) -> tuple[list[str], list[str]]:
        b64: list[str] = []
        names: list[str] = []
        for att in attachments:
            if att.kind != "image":
                continue
            art = await self._artifacts.get_artifact(att.id)
            if not art:
                continue
            raw = (art.get("metadata") or {}).get("image_base64")
            if isinstance(raw, str) and raw.strip():
                b64.append(raw.strip())
                names.append(att.name)
        if not b64:
            recent = await self._artifacts.list_artifacts(
                session_id=session_id,
                kinds=["image", "image-url"],
                limit=2,
            )
            if recent:
                raw = (recent[0].get("metadata") or {}).get("image_base64")
                if isinstance(raw, str) and raw.strip():
                    b64.append(raw.strip())
                    names.append(recent[0].get("title", "image"))
        return b64, names

    async def _duckduckgo_image_hits(
        self,
        client: httpx.AsyncClient,
        query: str,
        *,
        limit: int,
    ) -> list[ImageHit]:
        if not query.strip():
            return []
        try:
            landing = await client.get(
                "https://duckduckgo.com/",
                params={"q": query.strip()},
                headers={"User-Agent": "ISE-AI/1.0"},
            )
            landing.raise_for_status()
            vqd_m = re.search(r'vqd="([\d-]+)"', landing.text)
            if not vqd_m:
                return []
            vqd = vqd_m.group(1)
            i_url = (
                f"https://duckduckgo.com/i.js?l=us-en&o=json&q={quote_plus(query.strip())}"
                f"&vqd={quote_plus(vqd)}&p=1&f=,,,,,&"
            )
            resp = await client.get(i_url, headers={"User-Agent": "ISE-AI/1.0"})
            resp.raise_for_status()
            data = json.loads(resp.text)
        except Exception:
            return []

        results = data.get("results") or []
        hits: list[ImageHit] = []
        for row in results:
            if len(hits) >= limit:
                break
            img = (row.get("image") or "").strip()
            if not img or not _allowed_image_host(img):
                continue
            thumb = (row.get("thumbnail") or "").strip() or img
            title = (row.get("title") or "").strip() or "Image"
            page = (row.get("url") or "").strip()
            src = (row.get("source") or "").strip()
            hits.append(
                ImageHit(
                    title=title[:300],
                    image_url=img,
                    thumbnail_url=thumb,
                    page_url=page,
                    source_name=src[:120],
                )
            )
        return hits

    async def _try_generate(
        self,
        user_message: str,
        vision_notes: str,
        reference_b64: list[str],
    ) -> ImageIntelLog:
        model = settings.ollama_image_model
        ts = _utc_iso()
        if not model:
            return ImageIntelLog(
                kind="generation",
                query=user_message[:300],
                provider="ollama",
                generator_model="",
                status="failed",
                searched_at=ts,
                error=(
                    "No text-to-image model configured (OLLAMA_IMAGE_MODEL). Llava/vision models only "
                    "describe existing images. Set OLLAMA_IMAGE_MODEL=flux (after `ollama pull flux`) or similar."
                ),
            )

        prompt_parts = [user_message.strip()]
        if vision_notes:
            prompt_parts.append("Visual reference notes:\n" + vision_notes[:2000])
        prompt = "\n\n".join(prompt_parts)

        payload: dict = {"model": model, "prompt": prompt, "stream": False}
        if reference_b64:
            payload["images"] = reference_b64[:3]

        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=300.0) as client:
                response = await client.post("/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            return ImageIntelLog(
                kind="generation",
                query=prompt[:300],
                provider="ollama",
                generator_model=model,
                status="failed",
                searched_at=ts,
                error=str(exc),
            )

        images_out = data.get("images") or data.get("image") or []
        if isinstance(images_out, str):
            images_out = [images_out]
        if not images_out:
            return ImageIntelLog(
                kind="generation",
                query=prompt[:300],
                provider="ollama",
                generator_model=model,
                status="failed",
                searched_at=ts,
                error="The image model returned no image data. Verify the model supports image output.",
            )

        raw_b64 = images_out[0] if isinstance(images_out[0], str) else str(images_out[0])
        data_uri = f"data:image/png;base64,{raw_b64}"
        hit = ImageHit(
            title="Generated image",
            image_url=data_uri,
            thumbnail_url=data_uri,
            page_url="",
            source_name=model,
        )
        return ImageIntelLog(
            kind="generation",
            query=prompt[:400],
            provider="ollama",
            generator_model=model,
            status="completed",
            searched_at=ts,
            summary="Generated image attached below.",
            images=[hit],
            vision_notes=vision_notes[:800] if vision_notes else "",
        )

    @staticmethod
    def _format_search_context(log: ImageIntelLog) -> str:
        lines = [
            f"Image search ({log.provider}) for `{log.query}` — use these URLs when recommending visuals:",
        ]
        for hit in log.images[:12]:
            lines.append(f"- {hit.title}\n  Image: {hit.image_url}\n  Page: {hit.page_url or hit.image_url}")
        lines.append(
            "In your reply, you may embed thumbnails using markdown like "
            f"![description]({log.images[0].thumbnail_url or log.images[0].image_url}) "
            "when it helps the user."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_generation_context(log: ImageIntelLog) -> str:
        if not log.images:
            return ""
        url = log.images[0].image_url
        return (
            "An image was generated locally. Describe it honestly and offer adjustments.\n"
            f"Embedded form: ![generated]({url})"
        )

    @staticmethod
    def _imagery_generation_unavailable_note() -> str:
        vision_tag = settings.ollama_vision_model.strip()
        vision_line = (
            f"OLLAMA_VISION_MODEL is set to {vision_tag!r} (e.g. llava): that model **describes** images you "
            "upload; it does **not** synthesize new pictures from text.\n"
            if vision_tag
            else "Vision models (e.g. llava via OLLAMA_VISION_MODEL) **describe** existing images only; they do not draw new ones.\n"
        )
        return (
            "Image generation:\n"
            f"- {vision_line}"
            "- To **generate** images locally, install a text-to-image model (e.g. `ollama pull flux`) and set "
            "**OLLAMA_IMAGE_MODEL** to that exact tag, then restart the API.\n"
            "- Below: **stock photo search** as a practical substitute.\n"
        )

    @staticmethod
    def _imagery_query_from_user(user_message: str, vision_notes: str) -> str:
        raw = user_message.strip()
        m = re.search(
            r"(?i)\b(?:a\s+)?(?:picture|image|photo|pic)\s+(?:of|for)\s+(?:the\s+)?([^.!?\n]+)",
            raw,
        )
        if m:
            q = m.group(1).strip()
        else:
            m2 = re.search(r"(?i)\b(?:for|of)\s+(?:the\s+)?([^.!?\n]+)", raw)
            if m2:
                q = m2.group(1).strip()
            else:
                q = re.sub(
                    r"(?i)^[\s,]*(?:please\s+)?(?:can\s+you\s+)?(?:generate|imagine|create|draw)\b(?:\s+or\s+imagine)?[\s,]*(?:a\s+|an\s+)?(?:picture|image|photo|pic)?[\s,]*(?:of|for)?[\s,]*",
                    "",
                    raw,
                )
                q = (q or raw).strip()
        q = re.sub(r"\s+", " ", q).strip(" .,!?")
        if len(q) < 2:
            q = re.sub(r"\s+", " ", raw)[:120]
        if vision_notes and len(q) < 24:
            line = vision_notes.split("\n", 1)[0].strip()[:100]
            if line and not line.lower().startswith("user"):
                q = f"{q} {line}".strip()
        q = q[:200]
        if "photo" not in q.lower() and "wallpaper" not in q.lower():
            q = f"{q} photograph"
        return q

    async def _add_imagery_search_fallback(
        self,
        client: httpx.AsyncClient,
        user_message: str,
        vision_notes: str,
        logs: list[ImageIntelLog],
        contexts: list[str],
        *,
        limit: int = 8,
    ) -> None:
        q = self._imagery_query_from_user(user_message, vision_notes)
        hits = await self._duckduckgo_image_hits(client, q, limit=limit)
        if not hits:
            contexts.append(
                f"No stock images matched the fallback query ({q!r}). "
                "Try different wording or set OLLAMA_IMAGE_MODEL after pulling a generator model."
            )
            return
        log = ImageIntelLog(
            kind="search",
            query=q,
            provider="duckduckgo-images",
            status="completed",
            searched_at=_utc_iso(),
            summary="Photo search (stand-in when AI image generation is not configured or failed).",
            images=hits,
            vision_notes=vision_notes[:800] if vision_notes else "",
        )
        logs.append(log)
        contexts.append(self._format_search_context(log))


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _allowed_image_host(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    blocked = ("malware", "phish")
    return not any(b in host for b in blocked)


@lru_cache
def get_image_intel_service() -> ImageIntelService:
    return ImageIntelService(
        artifact_service=get_artifact_service(),
        vision_service=get_vision_service(),
    )
