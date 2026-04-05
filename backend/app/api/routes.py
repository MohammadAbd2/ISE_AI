import json

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from backend.app.core.config import settings
from backend.app.schemas.chat import (
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
)
from backend.app.services.artifacts import ArtifactService, get_artifact_service
from backend.app.services.agent import ChatAgent
from backend.app.services.chat import ChatService, get_chat_service
from backend.app.services.documents import DocumentService, get_document_service
from backend.app.services.history import HistoryService, get_history_service
from backend.app.services.profile import ProfileService, get_profile_service
from backend.app.services.session_analytics import build_session_analytics_payload


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Simple readiness endpoint for local smoke tests."""
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    history: HistoryService = Depends(get_history_service),
    profile: ProfileService = Depends(get_profile_service),
) -> ChatResponse:
    agent = ChatAgent(service=service, profile_service=profile, history_service=history)
    return await agent.respond(payload, session_id=payload.session_id)


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

    conversation = [
        message for message in session["messages"] if message.role != "system"
    ]
    await history.append_message(
        session["id"],
        "user",
        payload.message,
        selected_model,
        attachments=[attachment.model_dump() for attachment in payload.attachments],
    )
    stream, model, search_logs, image_logs, render_blocks = await agent.stream_response(
        payload,
        conversation=conversation,
        session_id=session["id"],
    )

    async def event_stream():
        chunks: list[str] = []
        try:
            # Send metadata first so the UI can update session and storage badges.
            yield json.dumps(
                {
                    "type": "meta",
                    "model": model,
                    "session_id": session["id"],
                    "storage_mode": history.storage_mode(),
                    "profile_storage_mode": profile.storage_mode(),
                }
            ) + "\n"
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
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


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


@router.get("/api/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    artifacts: ArtifactService = Depends(get_artifact_service),
) -> PlainTextResponse:
    artifact = await artifacts.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    filename = artifact.get("metadata", {}).get("filename") or artifact["title"]
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(
        artifact.get("content", ""),
        headers=headers,
        media_type="text/plain; charset=utf-8",
    )
