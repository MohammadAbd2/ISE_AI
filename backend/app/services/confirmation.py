"""
Human-in-the-Loop Confirmation System

Provides:
- File operation confirmations with buttons
- Allow Always, Allow Once, Cancel options
- Session-based confirmation tracking
- Smart confirmation bypass for trusted operations
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiofiles


class ConfirmationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_ALWAYS = "approved_always"
    REJECTED = "rejected"


class OperationType(str, Enum):
    CREATE_FILE = "create_file"
    EDIT_FILE = "edit_file"
    DELETE_FILE = "delete_file"
    MOVE_FILE = "move_file"
    RUN_COMMAND = "run_command"
    INSTALL_PACKAGE = "install_package"


@dataclass
class ConfirmationRequest:
    """A pending confirmation request."""
    id: str
    operation_type: OperationType
    description: str
    details: dict = field(default_factory=dict)
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    created_at: str = ""
    expires_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation_type": self.operation_type.value,
            "description": self.description,
            "details": self.details,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class ConfirmationPreferences:
    """User's confirmation preferences."""
    allow_always_paths: list[str] = field(default_factory=list)  # Paths that don't need confirmation
    deny_always_paths: list[str] = field(default_factory=list)  # Paths that are always denied
    auto_approve_operations: list[OperationType] = field(default_factory=list)
    last_updated: str = ""


class ConfirmationManager:
    """
    Manages human-in-the-loop confirmations.
    
    Similar to how Cursor and VSCode ask for permissions.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pending_confirmations: dict[str, ConfirmationRequest] = {}
        self.preferences_path = project_root / ".ise_ai_confirmations.json"
        self.preferences = ConfirmationPreferences()
        
        # Confirmation timeout (5 minutes)
        self.confirmation_timeout_seconds = 300
    
    async def load_preferences(self):
        """Load user's confirmation preferences."""
        if self.preferences_path.exists():
            try:
                async with aiofiles.open(self.preferences_path, "r") as f:
                    data = json.loads(await f.read())
                
                self.preferences.allow_always_paths = data.get("allow_always_paths", [])
                self.preferences.deny_always_paths = data.get("deny_always_paths", [])
                self.preferences.auto_approve_operations = [
                    OperationType(op) for op in data.get("auto_approve_operations", [])
                ]
            except Exception:
                pass
    
    async def save_preferences(self):
        """Save user's confirmation preferences."""
        self.preferences.last_updated = datetime.now(UTC).isoformat()
        
        data = {
            "allow_always_paths": self.preferences.allow_always_paths,
            "deny_always_paths": self.preferences.deny_always_paths,
            "auto_approve_operations": [op.value for op in self.preferences.auto_approve_operations],
            "last_updated": self.preferences.last_updated,
        }
        
        async with aiofiles.open(self.preferences_path, "w") as f:
            await f.write(json.dumps(data, indent=2))
    
    def should_skip_confirmation(self, operation_type: OperationType, path: str = "") -> bool:
        """Check if confirmation can be skipped based on preferences."""
        # Check if operation type is auto-approved
        if operation_type in self.preferences.auto_approve_operations:
            return True
        
        # Check if path is in allow-always list
        if path:
            for allowed_path in self.preferences.allow_always_paths:
                if path.startswith(allowed_path) or allowed_path == "*":
                    return True
            
            # Check if path is in deny-always list
            for denied_path in self.preferences.deny_always_paths:
                if path.startswith(denied_path):
                    return False  # Explicit deny overrides allow
        
        return False
    
    async def request_confirmation(
        self,
        operation_type: OperationType,
        description: str,
        details: dict,
    ) -> ConfirmationRequest:
        """Create a new confirmation request."""
        confirmation_id = self._generate_confirmation_id(operation_type, details)
        
        # Check if we can skip confirmation
        path = details.get("path", "")
        if self.should_skip_confirmation(operation_type, path):
            # Auto-approve
            confirmation = ConfirmationRequest(
                id=confirmation_id,
                operation_type=operation_type,
                description=description,
                details=details,
                status=ConfirmationStatus.APPROVED,
                created_at=datetime.now(UTC).isoformat(),
                expires_at=datetime.now(UTC).isoformat(),
            )
            return confirmation
        
        # Check for existing pending confirmation
        if confirmation_id in self.pending_confirmations:
            existing = self.pending_confirmations[confirmation_id]
            if existing.status == ConfirmationStatus.PENDING:
                return existing
        
        # Create new confirmation request
        now = datetime.now(UTC)
        confirmation = ConfirmationRequest(
            id=confirmation_id,
            operation_type=operation_type,
            description=description,
            details=details,
            status=ConfirmationStatus.PENDING,
            created_at=now.isoformat(),
            expires_at=(now.timestamp() + self.confirmation_timeout_seconds),
        )
        
        self.pending_confirmations[confirmation_id] = confirmation
        return confirmation
    
    def _generate_confirmation_id(self, operation_type: OperationType, details: dict) -> str:
        """Generate a unique confirmation ID."""
        content = f"{operation_type.value}:{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def respond_to_confirmation(
        self,
        confirmation_id: str,
        response: str,
        allow_always: bool = False,
    ) -> ConfirmationRequest:
        """
        Process user's response to a confirmation request.
        
        Args:
            confirmation_id: The confirmation request ID
            response: "approve", "reject", or text response
            allow_always: If True, add to allow-always list
        """
        if confirmation_id not in self.pending_confirmations:
            raise ValueError(f"Confirmation {confirmation_id} not found")
        
        confirmation = self.pending_confirmations[confirmation_id]
        
        # Parse response
        response_lower = response.lower().strip()
        
        # Text responses that mean approve
        approve_responses = ["approve", "approved", "yes", "y", "ok", "okay", "sure", "go ahead", "allow"]
        # Text responses that mean reject
        reject_responses = ["reject", "rejected", "no", "n", "cancel", "deny", "block"]
        
        if response_lower in approve_responses or response_lower.startswith("allow"):
            confirmation.status = ConfirmationStatus.APPROVED
            
            # If allow always, add to preferences
            if allow_always or "always" in response_lower:
                confirmation.status = ConfirmationStatus.APPROVED_ALWAYS
                path = confirmation.details.get("path", "")
                if path and path not in self.preferences.allow_always_paths:
                    self.preferences.allow_always_paths.append(path)
                    await self.save_preferences()
                    
        elif response_lower in reject_responses or response_lower.startswith("cancel") or response_lower.startswith("deny"):
            confirmation.status = ConfirmationStatus.REJECTED
            
            # If deny always, add to preferences
            if "always" in response_lower:
                path = confirmation.details.get("path", "")
                if path and path not in self.preferences.deny_always_paths:
                    self.preferences.deny_always_paths.append(path)
                    await self.save_preferences()
        else:
            # Unknown response, treat as reject
            confirmation.status = ConfirmationStatus.REJECTED
        
        # Clean up expired confirmations
        self._cleanup_expired_confirmations()
        
        return confirmation
    
    def get_confirmation(self, confirmation_id: str) -> Optional[ConfirmationRequest]:
        """Get a confirmation request by ID."""
        return self.pending_confirmations.get(confirmation_id)
    
    def get_pending_confirmations(self) -> list[ConfirmationRequest]:
        """Get all pending confirmation requests."""
        return [
            conf for conf in self.pending_confirmations.values()
            if conf.status == ConfirmationStatus.PENDING
        ]
    
    def _cleanup_expired_confirmations(self):
        """Remove expired confirmation requests."""
        now = datetime.now(UTC).timestamp()
        expired = [
            conf_id for conf_id, conf in self.pending_confirmations.items()
            if float(conf.expires_at) < now and conf.status == ConfirmationStatus.PENDING
        ]
        
        for conf_id in expired:
            del self.pending_confirmations[conf_id]
    
    def format_confirmation_message(self, confirmation: ConfirmationRequest) -> dict:
        """Format confirmation request for UI display."""
        icon_map = {
            OperationType.CREATE_FILE: "📁",
            OperationType.EDIT_FILE: "✏️",
            OperationType.DELETE_FILE: "🗑️",
            OperationType.MOVE_FILE: "📦",
            OperationType.RUN_COMMAND: "💻",
            OperationType.INSTALL_PACKAGE: "📦",
        }
        
        icon = icon_map.get(confirmation.operation_type, "❓")
        
        return {
            "confirmation_id": confirmation.id,
            "icon": icon,
            "title": f"{icon} {confirmation.operation_type.value.replace('_', ' ').title()}",
            "description": confirmation.description,
            "details": confirmation.details,
            "requires_confirmation": confirmation.status == ConfirmationStatus.PENDING,
            "buttons": [
                {
                    "label": "Allow Once",
                    "value": "approve",
                    "style": "secondary",
                    "tooltip": "Allow this operation once"
                },
                {
                    "label": "Allow Always",
                    "value": "approve_always",
                    "style": "primary",
                    "tooltip": "Always allow this type of operation"
                },
                {
                    "label": "Cancel",
                    "value": "reject",
                    "style": "danger",
                    "tooltip": "Cancel this operation"
                },
            ],
            "text_hint": "Or type: 'yes', 'no', 'allow always', 'deny always'",
        }


# Global instance
_confirmation_manager: Optional[ConfirmationManager] = None


def get_confirmation_manager(project_root: Optional[Path] = None) -> ConfirmationManager:
    """Get or create confirmation manager instance."""
    global _confirmation_manager
    if _confirmation_manager is None:
        if project_root is None:
            project_root = Path.cwd()
        _confirmation_manager = ConfirmationManager(project_root)
    return _confirmation_manager
