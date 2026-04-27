import asyncio
from datetime import datetime, UTC
from functools import lru_cache
import threading
from uuid import uuid4

from app.core.config import settings
from app.schemas.chat import ChatAttachment, ChatMessage, ImageIntelLog, RenderBlock, WebSearchLog
from app.services.chroma_store import ChromaJSONStore


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _coerce_model_list(model: type, raw: list | None) -> list:
    out: list = []
    for item in raw or []:
        if isinstance(item, dict):
            try:
                out.append(model.model_validate(item))
            except Exception:
                continue
        else:
            out.append(item)
    return out


def _session_title(message: str) -> str:
    compact = " ".join(message.split())
    return compact[:48] + ("..." if len(compact) > 48 else "") or "New chat"


class HistoryService:
    def __init__(self, chroma_path: str | None = None, collection_name: str | None = None) -> None:
        self._lock = threading.Lock()
        self.store = ChromaJSONStore("chat_sessions")

    async def list_sessions(self) -> list[dict]:
        return await asyncio.to_thread(self._list_sessions_sync)

    def _list_sessions_sync(self) -> list[dict]:
        return [self._summary(document) for document in self.store.find(sort_key="updated_at", reverse=True)]

    async def get_session(self, session_id: str) -> dict | None:
        return await asyncio.to_thread(self._get_session_sync, session_id)

    def _get_session_sync(self, session_id: str) -> dict | None:
        document = self.store.get(session_id)
        return self._detail(document) if document else None

    async def create_session(self, message: str, model: str) -> dict:
        return await asyncio.to_thread(self._create_session_sync, message, model)

    def _create_session_sync(self, message: str, model: str) -> dict:
        now = _utc_now().isoformat()
        document_id = str(uuid4())
        document = {"_id": document_id, "title": _session_title(message), "model": model, "messages": [], "pending_action": None, "created_at": now, "updated_at": now}
        self.store.upsert(document_id, document)
        return self._detail(document)

    async def append_message(self, session_id: str, role: str, content: str, model: str, attachments: list[dict] | None = None, search_logs: list[dict] | None = None, image_logs: list[dict] | None = None, render_blocks: list[dict] | None = None) -> None:
        await asyncio.to_thread(self._append_message_sync, session_id, role, content, model, attachments, search_logs, image_logs, render_blocks)

    def _append_message_sync(self, session_id: str, role: str, content: str, model: str, attachments: list[dict] | None = None, search_logs: list[dict] | None = None, image_logs: list[dict] | None = None, render_blocks: list[dict] | None = None) -> None:
        with self._lock:
            document = self.store.get(session_id)
            if document is None:
                return
            document.setdefault("messages", []).append({"role": role, "content": content, "attachments": attachments or [], "search_logs": search_logs or [], "image_logs": image_logs or [], "render_blocks": render_blocks or []})
            document["updated_at"] = _utc_now().isoformat()
            document["model"] = model
            self.store.upsert(session_id, document)

    async def delete_session(self, session_id: str) -> None:
        await asyncio.to_thread(self.store.delete, session_id)

    async def clear_sessions(self) -> None:
        await asyncio.to_thread(self.store.clear)

    async def get_pending_action(self, session_id: str) -> dict | None:
        return await asyncio.to_thread(self._get_pending_action_sync, session_id)

    def _get_pending_action_sync(self, session_id: str) -> dict | None:
        document = self.store.get(session_id)
        return document.get("pending_action") if document else None

    async def set_pending_action(self, session_id: str, action: dict | None) -> None:
        await asyncio.to_thread(self._set_pending_action_sync, session_id, action)

    def _set_pending_action_sync(self, session_id: str, action: dict | None) -> None:
        with self._lock:
            document = self.store.get(session_id)
            if document is not None:
                document["pending_action"] = action
                document["updated_at"] = _utc_now().isoformat()
                self.store.upsert(session_id, document)

    def storage_mode(self) -> str:
        return "chromadb" if self.store.is_persistent else "memory"

    def _summary(self, document: dict) -> dict:
        messages = document.get("messages", [])
        last_message = messages[-1]["content"] if messages else ""
        return {"id": str(document.get("_id", "")), "title": document.get("title", "New chat"), "model": document.get("model", settings.default_model), "updated_at": str(document.get("updated_at", _utc_now().isoformat())), "preview": last_message[:120]}

    def _detail(self, document: dict | None) -> dict | None:
        if document is None:
            return None
        messages = []
        for message in document.get("messages", []):
            messages.append(ChatMessage(role=message.get("role", "assistant"), content=message.get("content", ""), attachments=_coerce_model_list(ChatAttachment, message.get("attachments", [])), search_logs=_coerce_model_list(WebSearchLog, message.get("search_logs", [])), image_logs=_coerce_model_list(ImageIntelLog, message.get("image_logs", [])), render_blocks=_coerce_model_list(RenderBlock, message.get("render_blocks", []))).model_dump())
        return {"id": str(document.get("_id", "")), "title": document.get("title", "New chat"), "model": document.get("model", settings.default_model), "messages": messages, "pending_action": document.get("pending_action"), "created_at": str(document.get("created_at", _utc_now().isoformat())), "updated_at": str(document.get("updated_at", _utc_now().isoformat()))}


@lru_cache
def get_history_service() -> HistoryService:
    return HistoryService()
