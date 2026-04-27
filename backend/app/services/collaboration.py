"""
Real-Time Collaboration Service

Provides:
- WebSocket-based multi-user editing
- Presence indicators
- Session management
- Conflict resolution
- User cursors
"""

import json
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pathlib import Path


@dataclass
class User:
    """Represents a connected user."""
    user_id: str
    username: str
    color: str
    file_path: Optional[str] = None
    line: int = 0
    column: int = 0
    connected_at: str = ""
    last_active: str = ""


@dataclass
class CollaborationSession:
    """A collaboration session."""
    session_id: str
    name: str
    users: Dict[str, User] = field(default_factory=dict)
    created_at: str = ""
    file_path: Optional[str] = None


class CollaborationService:
    """
    Real-time collaboration service.
    
    Manages:
    - User connections
    - Session state
    - Presence tracking
    - Conflict resolution
    """

    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.user_colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A",
            "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
        ]
        self._color_index = 0

    def create_session(self, session_id: str, name: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a new collaboration session."""
        if session_id in self.sessions:
            return {"success": False, "error": "Session already exists"}

        self.sessions[session_id] = CollaborationSession(
            session_id=session_id,
            name=name,
            file_path=file_path,
            created_at=datetime.now().isoformat(),
        )

        return {
            "success": True,
            "session_id": session_id,
            "name": name,
        }

    def join_session(self, session_id: str, user_id: str, username: str) -> Dict[str, Any]:
        """Join a collaboration session."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if user_id in session.users:
            return {"success": False, "error": "User already in session"}

        color = self.user_colors[self._color_index % len(self.user_colors)]
        self._color_index += 1

        session.users[user_id] = User(
            user_id=user_id,
            username=username,
            color=color,
            connected_at=datetime.now().isoformat(),
            last_active=datetime.now().isoformat(),
        )

        return {
            "success": True,
            "user_id": user_id,
            "color": color,
            "users": self._get_user_list(session),
        }

    def leave_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Leave a collaboration session."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if user_id in session.users:
            del session.users[user_id]

        return {
            "success": True,
            "users": self._get_user_list(session) if session.users else [],
        }

    def update_cursor(self, session_id: str, user_id: str, file_path: str, line: int, column: int) -> Dict[str, Any]:
        """Update user cursor position."""
        session = self.sessions.get(session_id)
        if not session or user_id not in session.users:
            return {"success": False, "error": "User not in session"}

        user = session.users[user_id]
        user.file_path = file_path
        user.line = line
        user.column = column
        user.last_active = datetime.now().isoformat()

        return {
            "success": True,
            "user_id": user_id,
            "file_path": file_path,
            "line": line,
            "column": column,
        }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        return {
            "success": True,
            "session_id": session.session_id,
            "name": session.name,
            "file_path": session.file_path,
            "created_at": session.created_at,
            "users": self._get_user_list(session),
            "user_count": len(session.users),
        }

    def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions."""
        return {
            "success": True,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "user_count": len(s.users),
                    "file_path": s.file_path,
                }
                for s in self.sessions.values()
            ],
        }

    def resolve_conflict(self, session_id: str, user_id: str, operation: str, content: str) -> Dict[str, Any]:
        """Resolve editing conflicts (last-write-wins for now)."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        # Simple last-write-wins strategy
        # In production, use operational transforms or CRDTs
        return {
            "success": True,
            "operation": operation,
            "accepted": True,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_user_list(self, session: CollaborationSession) -> List[Dict]:
        """Get list of users in a session."""
        return [
            {
                "user_id": user.user_id,
                "username": user.username,
                "color": user.color,
                "file_path": user.file_path,
                "line": user.line,
                "column": user.column,
                "connected_at": user.connected_at,
                "last_active": user.last_active,
            }
            for user in session.users.values()
        ]


# Global instance
_collab_service: Optional[CollaborationService] = None


def get_collaboration_service() -> CollaborationService:
    """Get or create collaboration service instance."""
    global _collab_service
    if _collab_service is None:
        _collab_service = CollaborationService()
    return _collab_service
