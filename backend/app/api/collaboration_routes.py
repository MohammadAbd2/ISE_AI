"""
Collaboration API Routes

Provides real-time collaboration features
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.collaboration import get_collaboration_service

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


class CreateSessionRequest(BaseModel):
    session_id: str
    name: str
    file_path: Optional[str] = None


class JoinSessionRequest(BaseModel):
    session_id: str
    user_id: str
    username: str


class CursorUpdate(BaseModel):
    session_id: str
    user_id: str
    file_path: str
    line: int
    column: int


@router.post("/session/create")
async def create_session(request: CreateSessionRequest):
    """Create a new collaboration session."""
    service = get_collaboration_service()
    result = service.create_session(request.session_id, request.name, request.file_path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/session/join")
async def join_session(request: JoinSessionRequest):
    """Join a collaboration session."""
    service = get_collaboration_service()
    result = service.join_session(request.session_id, request.user_id, request.username)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/session/leave")
async def leave_session(session_id: str, user_id: str):
    """Leave a collaboration session."""
    service = get_collaboration_service()
    return service.leave_session(session_id, user_id)


@router.post("/cursor/update")
async def update_cursor(request: CursorUpdate):
    """Update user cursor position."""
    service = get_collaboration_service()
    return service.update_cursor(
        request.session_id,
        request.user_id,
        request.file_path,
        request.line,
        request.column,
    )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information."""
    service = get_collaboration_service()
    result = service.get_session_info(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    service = get_collaboration_service()
    return service.list_sessions()


@router.post("/resolve-conflict")
async def resolve_conflict(
    session_id: str,
    user_id: str,
    operation: str,
    content: str,
):
    """Resolve editing conflict."""
    service = get_collaboration_service()
    return service.resolve_conflict(session_id, user_id, operation, content)
