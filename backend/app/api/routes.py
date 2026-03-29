import json

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from backend.app.core.config import settings
from backend.app.schemas.chat import (
    AIProfileResponse,
    AIProfileUpdateRequest,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionsResponse,
    ModelsResponse,
)
from backend.app.services.agent import ChatAgent
from backend.app.services.chat import ChatService, get_chat_service
from backend.app.services.history import HistoryService, get_history_service
from backend.app.services.profile import ProfileService, get_profile_service


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Simple readiness endpoint for local smoke tests."""
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    profile: ProfileService = Depends(get_profile_service),
) -> ChatResponse:
    agent = ChatAgent(service=service, profile_service=profile)
    return await agent.respond(payload)


@router.post("/api/chat/stream")
async def stream_chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    history: HistoryService = Depends(get_history_service),
    profile: ProfileService = Depends(get_profile_service),
) -> StreamingResponse:
    agent = ChatAgent(service=service, profile_service=profile)
    selected_model = payload.model or settings.default_model
    # Existing sessions keep their stored message history on the server side.
    session = (
        await history.get_session(payload.session_id)
        if payload.session_id
        else await history.create_session(payload.message, selected_model)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    conversation = [
        message for message in session["messages"] if message.role != "system"
    ]
    await history.append_message(session["id"], "user", payload.message, selected_model)
    stream, model = await agent.stream_response(payload, conversation=conversation)

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
            async for chunk in stream:
                chunks.append(chunk)
                yield json.dumps({"type": "token", "content": chunk}) + "\n"
            # Persist the full assistant reply after streaming completes successfully.
            await history.append_message(
                session["id"],
                "assistant",
                "".join(chunks),
                model,
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
