from pathlib import Path
import json
import asyncio

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse

from app.core.config import settings
from app.schemas.chat import (
    AIProfileResponse,
    AIProfileUpdateRequest,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionsResponse,
    FileUploadRequest,
    FileUploadResponse,
    ModelsResponse,
    ArtifactListResponse,
    ArtifactSummary,
    SessionAnalyticsResponse,
    IntentClassificationRequest,
    IntentClassificationResponse,
)
from app.services.artifacts import ArtifactService, get_artifact_service
from app.services.agent import ChatAgent
from app.services.chat import ChatService, get_chat_service
from app.services.documents import DocumentService, get_document_service
from app.services.history import HistoryService, get_history_service
from app.services.profile import ProfileService, get_profile_service
from app.services.session_analytics import build_session_analytics_payload
from app.services.intent_classifier import get_intent_classifier
from app.services.agent_memory import get_agent_memory_store


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Simple readiness endpoint for local smoke tests."""
    return {"status": "ok"}


@router.get("/api/docs/developer-handbook", response_class=PlainTextResponse)
async def developer_handbook() -> str:
    handbook_path = settings.project_root / "docs" / "ISE_DEVELOPER_HANDBOOK.md"
    if not handbook_path.exists():
        raise HTTPException(status_code=404, detail="Developer handbook not found")
    return handbook_path.read_text(encoding="utf-8")


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    history: HistoryService = Depends(get_history_service),
    profile: ProfileService = Depends(get_profile_service),
) -> ChatResponse:
    agent = ChatAgent(service=service, profile_service=profile, history_service=history)
    return await agent.respond(payload, session_id=payload.session_id)


@router.post("/api/intent/classify", response_model=IntentClassificationResponse)
async def classify_intent(
    payload: IntentClassificationRequest,
) -> IntentClassificationResponse:
    intent = get_intent_classifier().classify(payload.message, payload.mode)
    return IntentClassificationResponse(
        kind=intent.kind,
        confidence=intent.confidence,
        use_agent=intent.use_agent,
        use_visualization=intent.use_visualization,
        use_research=intent.use_research,
        use_project_context=intent.use_project_context,
        use_filesystem=intent.use_filesystem,
    )


@router.post("/api/chat/stream")
async def stream_chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    history: HistoryService = Depends(get_history_service),
    profile: ProfileService = Depends(get_profile_service),
    documents: DocumentService = Depends(get_document_service),
) -> StreamingResponse:
    agent = ChatAgent(
        service=service,
        profile_service=profile,
        history_service=history,
    )
    from app.services.self_reflection import get_self_reflection_service
    self_reflection_service = get_self_reflection_service()

    selected_model = payload.model or settings.default_model
    # Existing sessions keep their stored message history on the server side.
    is_draft_session = bool(payload.session_id and payload.session_id.startswith("draft:"))
    session = (
        await history.get_session(payload.session_id)
        if payload.session_id and not is_draft_session
        else await history.create_session(payload.message, selected_model)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if is_draft_session and payload.session_id:
        await documents.reassign_session(payload.session_id, session["id"])

    def _message_role(message):
        if isinstance(message, dict):
            return message.get("role", "")
        return getattr(message, "role", "")

    conversation = [
        message for message in session.get("messages", []) if _message_role(message) != "system"
    ]
    await history.append_message(
        session["id"],
        "user",
        payload.message,
        selected_model,
        attachments=[attachment.model_dump() for attachment in payload.attachments],
    )

    async def event_stream():
        chunks: list[str] = []
        progress_queue: asyncio.Queue[dict] = asyncio.Queue()
        model = selected_model
        search_logs = []
        image_logs = []
        render_blocks = []

        async def publish_progress(block: dict):
            await progress_queue.put({"type": "render", "block": block})

        response_task = asyncio.create_task(
            agent.stream_response(
                payload,
                conversation=conversation,
                session_id=session["id"],
                progress_callback=publish_progress,
            )
        )
        try:
            yield json.dumps(
                {
                    "type": "meta",
                    "model": selected_model,
                    "session_id": session["id"],
                    "storage_mode": history.storage_mode(),
                    "profile_storage_mode": profile.storage_mode(),
                }
            ) + "\n"
            while not response_task.done():
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=0.12)
                    yield json.dumps(event) + "\n"
                except asyncio.TimeoutError:
                    continue
            stream, model, search_logs, image_logs, render_blocks = await response_task
            if model != selected_model:
                yield json.dumps(
                    {
                        "type": "meta",
                        "model": model,
                        "session_id": session["id"],
                        "storage_mode": history.storage_mode(),
                        "profile_storage_mode": profile.storage_mode(),
                    }
                ) + "\n"
            while not progress_queue.empty():
                yield json.dumps(progress_queue.get_nowait()) + "\n"
            for search_log in search_logs:
                yield json.dumps({"type": "search", "log": search_log.model_dump()}) + "\n"
            for image_log in image_logs:
                yield json.dumps({"type": "images", "log": image_log.model_dump()}) + "\n"
            for render_block in render_blocks:
                yield json.dumps({"type": "render", "block": render_block}) + "\n"
            async for chunk in stream:
                chunks.append(chunk)
                yield json.dumps({"type": "token", "content": chunk}) + "\n"
            # Persist the full assistant reply after streaming completes successfully.
            await history.append_message(
                session["id"],
                "assistant",
                "".join(chunks),
                model,
                search_logs=[search_log.model_dump() for search_log in search_logs],
                image_logs=[image_log.model_dump() for image_log in image_logs],
                render_blocks=render_blocks,
            )
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as exc:
            error_details = str(exc).splitlines()[0]
            error_analysis = await self_reflection_service.analyze_error(error_details, "During streaming response generation.")
            fallback = (
                "I could not get a response from the language model service right now. "
                "The backend is still running, but the model provider failed.\n\n"
                f"Details: {error_details}\n\n"
                f"Diagnosis: {error_analysis.get('diagnosis', '')}\n"
                f"Suggested Fix: {error_analysis.get('suggested_fix', '')}"
            )
            if not chunks:
                chunks.append(fallback)
                yield json.dumps({"type": "token", "content": fallback}) + "\n"
            else:
                suffix = "\n\n[Generation stopped because the model provider failed.]"
                chunks.append(suffix)
                yield json.dumps({"type": "token", "content": suffix}) + "\n"
            await history.append_message(
                session["id"],
                "assistant",
                "".join(chunks),
                model,
                search_logs=[search_log.model_dump() for search_log in search_logs],
                image_logs=[image_log.model_dump() for image_log in image_logs],
                render_blocks=render_blocks,
            )
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/api/agent/memory/search")
async def search_agent_memory(q: str, limit: int = 5) -> dict:
    """Search local autonomous-agent task memory and extracted lessons."""
    store = get_agent_memory_store()
    limit = max(1, min(limit, 20))
    hits = store.search(q, limit=limit)
    lessons = store.search_lessons(q, limit=limit)
    return {"query": q, "hits": [{
        "task": hit.task, "score": hit.score, "success": hit.success, "summary": hit.summary,
        "files": hit.files, "fixes": hit.fixes, "artifact_id": hit.artifact_id,
    } for hit in hits], "lessons": [{
        "problem": item.problem, "solution": item.solution, "when_to_use": item.when_to_use,
        "score": item.score, "source_task": item.source_task,
    } for item in lessons]}


@router.get("/api/models", response_model=ModelsResponse)
async def available_models(
    service: ChatService = Depends(get_chat_service),
    profile: ProfileService = Depends(get_profile_service),
) -> ModelsResponse:
    agent = ChatAgent(service=service, profile_service=profile)
    return ModelsResponse(models=await agent.models())


@router.get("/api/chats", response_model=ChatSessionsResponse)
async def list_chats(
    history: HistoryService = Depends(get_history_service),
) -> ChatSessionsResponse:
    return ChatSessionsResponse(
        sessions=await history.list_sessions(),
        storage_mode=history.storage_mode(),
    )


@router.get("/api/chats/{session_id}", response_model=ChatSessionDetail)
async def get_chat(
    session_id: str,
    history: HistoryService = Depends(get_history_service),
) -> ChatSessionDetail:
    session = await history.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return ChatSessionDetail(**session)


@router.delete("/api/chats/{session_id}")
async def delete_chat(
    session_id: str,
    history: HistoryService = Depends(get_history_service),
) -> dict[str, str]:
    await history.delete_session(session_id)
    return {"status": "deleted"}


@router.delete("/api/chats")
async def clear_chats(
    history: HistoryService = Depends(get_history_service),
) -> dict[str, str]:
    await history.clear_sessions()
    return {"status": "cleared"}


@router.get("/api/ai/profile", response_model=AIProfileResponse)
async def get_ai_profile(
    profile: ProfileService = Depends(get_profile_service),
) -> AIProfileResponse:
    data = await profile.get_profile()
    return AIProfileResponse(
        custom_instructions=data.get("custom_instructions", ""),
        memory="\n".join(data.get("memory", [])),
        storage_mode=profile.storage_mode(),
    )


@router.put("/api/ai/profile", response_model=AIProfileResponse)
async def update_ai_profile(
    payload: AIProfileUpdateRequest,
    profile: ProfileService = Depends(get_profile_service),
) -> AIProfileResponse:
    data = await profile.update_profile(
        custom_instructions=payload.custom_instructions,
        memory=payload.memory,
    )
    return AIProfileResponse(
        custom_instructions=data.get("custom_instructions", ""),
        memory="\n".join(data.get("memory", [])),
        storage_mode=profile.storage_mode(),
    )


@router.post("/api/files/upload", response_model=FileUploadResponse)
async def upload_file(
    payload: FileUploadRequest,
    documents: DocumentService = Depends(get_document_service),
) -> FileUploadResponse:
    try:
        attachment = await documents.ingest_base64_upload(
            session_id=payload.session_id,
            filename=payload.filename,
            content_type=payload.content_type,
            data_base64=payload.data_base64,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"File upload failed: {exc}") from exc
    return FileUploadResponse(
        attachment=attachment,
        storage_mode=documents.storage_mode(),
    )


@router.get("/api/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    session_id: str,
    artifacts: ArtifactService = Depends(get_artifact_service),
) -> ArtifactListResponse:
    rows = await artifacts.list_artifacts(session_id=session_id, limit=24)
    return ArtifactListResponse(
        artifacts=[
            ArtifactSummary(
                id=row["id"],
                session_id=row["session_id"],
                kind=row["kind"],
                title=row["title"],
                preview=row.get("metadata", {}).get("preview", row.get("content", "")[:240]),
                metadata=row.get("metadata", {}),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
    )


@router.get("/api/session-analytics", response_model=SessionAnalyticsResponse)
async def get_session_analytics(
    session_id: str,
    history: HistoryService = Depends(get_history_service),
    artifacts: ArtifactService = Depends(get_artifact_service),
) -> SessionAnalyticsResponse:
    session = await history.get_session(session_id)
    rows = await artifacts.list_artifacts(session_id=session_id, limit=12)
    payload = build_session_analytics_payload(
        session,
        [
            ArtifactSummary(
                id=row["id"],
                session_id=row["session_id"],
                kind=row["kind"],
                title=row["title"],
                preview=row.get("metadata", {}).get("preview", row.get("content", "")[:240]),
                metadata=row.get("metadata", {}),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ],
    )
    return SessionAnalyticsResponse(**payload)


@router.delete("/api/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    artifacts: ArtifactService = Depends(get_artifact_service),
) -> dict[str, bool]:
    deleted = await artifacts.delete_artifact(artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"deleted": True}


@router.get("/api/artifacts/{artifact_id}/manifest")
async def get_artifact_manifest(
    artifact_id: str,
    artifacts: ArtifactService = Depends(get_artifact_service),
):
    artifact = await artifacts.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    metadata = artifact.get("metadata", {})
    if metadata.get("manifest"):
        return metadata["manifest"]
    manifest_path = metadata.get("manifest_path")
    if manifest_path:
        path = Path(manifest_path).expanduser().resolve()
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Artifact manifest not found")


@router.get("/api/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    artifacts: ArtifactService = Depends(get_artifact_service),
):
    artifact = await artifacts.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    metadata = artifact.get("metadata", {})
    filename = str(metadata.get("filename") or artifact["title"] or "artifact").replace("/", "-").replace("\\", "-")
    download_path = metadata.get("download_path")
    if download_path:
        path = Path(download_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact file is missing on disk. Re-run the export step.")
        if metadata.get("sha256"):
            import hashlib
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != metadata.get("sha256"):
                raise HTTPException(status_code=409, detail="Artifact checksum mismatch. Re-run the export step.")
        safe_filename = filename if "." in filename else (f"{filename}.zip" if path.suffix.lower() == ".zip" else filename)
        return FileResponse(
            path,
            filename=safe_filename,
            media_type=metadata.get("content_type") or ("application/zip" if path.suffix.lower() == ".zip" else "application/octet-stream"),
            headers={"X-ISE-AI-Artifact-Id": artifact_id, "X-ISE-AI-Artifact-SHA256": metadata.get("sha256", ""), "X-ISE-AI-Artifact-Files": str(metadata.get("file_count", "")), "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Access-Control-Expose-Headers": "Content-Disposition, X-ISE-AI-Artifact-Id, X-ISE-AI-Artifact-SHA256, X-ISE-AI-Artifact-Files"},
        )
    if artifact.get("kind") == "project-export":
        raise HTTPException(status_code=404, detail="Project export has no downloadable file attached.")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(
        artifact.get("content", ""),
        headers=headers,
        media_type=metadata.get("content_type") or "text/plain; charset=utf-8",
    )
