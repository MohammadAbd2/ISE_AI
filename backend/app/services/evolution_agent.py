"""
Main evolution agent for autonomous capability development.
Orchestrates the full workflow: detect gap → research → implement → validate → deploy.
"""

from dataclasses import dataclass
from typing import Optional

from backend.app.services.backup import BackupManager
from backend.app.services.capability_gap_detector import (
    CapabilityGapDetector,
    CapabilityGap,
)
from backend.app.services.capability_registry import (
    CapabilityRegistry,
    CapabilityStatus,
)
from backend.app.services.evolution_logger import (
    EvolutionLogger,
    EvolutionEventType,
    EventStatus,
)
from backend.app.services.implementation_verifier import ImplementationVerifier
from backend.app.services.tool_executor import ToolExecutor


@dataclass
class EvolutionDecision:
    """Decision made by the evolution agent."""

    action: str  # "offer_development", "decline", "proceed", "failed"
    capability: Optional[str] = None
    message: str = ""
    details: Optional[dict] = None


class EvolutionAgent:
    """
    Main orchestrator for autonomous capability development.
    
    Workflow:
    1. Detect capability gaps in user requests
    2. Offer to develop missing capabilities
    3. Upon user approval, research and plan implementation
    4. Implement the feature
    5. Validate the implementation
    6. Deploy with automatic backups
    7. Support rollback on failure
    """

    def __init__(
        self,
        backup_manager: Optional[BackupManager] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        gap_detector: Optional[CapabilityGapDetector] = None,
        evolution_logger: Optional[EvolutionLogger] = None,
        tool_executor: Optional[ToolExecutor] = None,
        verifier: Optional[ImplementationVerifier] = None,
    ):
        self.backup_manager = backup_manager or BackupManager()
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.gap_detector = gap_detector or CapabilityGapDetector(
            self.capability_registry
        )
        self.evolution_logger = evolution_logger or EvolutionLogger()
        self.tool_executor = tool_executor or ToolExecutor()
        self.verifier = verifier or ImplementationVerifier(self.tool_executor)

    async def analyze_request(self, user_message: str) -> EvolutionDecision:
        """
        Analyze user request for capability gaps.
        
        Args:
            user_message: The user's request
        
        Returns:
            EvolutionDecision with recommended action
        """
        should_offer, gap = self.gap_detector.should_offer_capability_development(
            user_message
        )

        if should_offer and gap:
            offer_message = self.gap_detector.generate_capability_offer(gap)
            self.evolution_logger.log_event(
                event_type=EvolutionEventType.CAPABILITY_REQUESTED,
                capability=gap.capability_name,
                status=EventStatus.PENDING,
                description=f"User requested capability: {gap.description}",
                details={"user_message": user_message},
            )
            return EvolutionDecision(
                action="offer_development",
                capability=gap.capability_name,
                message=offer_message,
                details={"gap": gap.capability_name, "complexity": gap.complexity},
            )

        return EvolutionDecision(
            action="decline",
            message="No missing capabilities detected in this request",
        )

    async def develop_capability(
        self,
        capability_name: str,
        user_instructions: Optional[str] = None,
    ) -> EvolutionDecision:
        """
        Develop a new capability (with user approval).
        
        Args:
            capability_name: Name of capability to develop
            user_instructions: Optional custom instructions from user
        
        Returns:
            EvolutionDecision with development status
        """
        # Log research start
        self.evolution_logger.log_event(
            event_type=EvolutionEventType.RESEARCH_STARTED,
            capability=capability_name,
            status=EventStatus.IN_PROGRESS,
            description=f"Beginning research for {capability_name}",
            details={"instructions": user_instructions},
        )

        # Check if capability can be developed
        if not self.capability_registry.can_develop_capability(capability_name):
            return EvolutionDecision(
                action="decline",
                capability=capability_name,
                message=f"Capability {capability_name} is already available or deprecated",
            )

        # Mark capability as in-development
        self.capability_registry.update_status(
            capability_name, CapabilityStatus.IN_DEVELOPMENT
        )

        # Create backup before any modifications
        backup = self.backup_manager.create_backup(
            reason=f"Pre-development backup for {capability_name}"
        )

        try:
            # Placeholder: In real implementation, would research and implement
            # For now, return a plan
            return EvolutionDecision(
                action="proceed",
                capability=capability_name,
                message=f"Ready to develop {capability_name}. Awaiting implementation details.",
                details={
                    "backup_id": backup.get("id"),
                    "status": "awaiting_implementation",
                },
            )
        except Exception as e:
            # Log failure
            self.evolution_logger.log_event(
                event_type=EvolutionEventType.ERROR_OCCURRED,
                capability=capability_name,
                status=EventStatus.FAILED,
                description=f"Error during development: {str(e)}",
                rollback_backup_id=backup.get("id"),
            )

            # Revert capability status
            self.capability_registry.update_status(
                capability_name, CapabilityStatus.FAILED
            )

            return EvolutionDecision(
                action="failed",
                capability=capability_name,
                message=f"Failed to develop {capability_name}: {str(e)}",
                details={"backup_id": backup.get("id")},
            )

    async def validate_implementation(
        self, file_path: str, capability_name: str
    ) -> dict:
        """
        Validate a new implementation before deployment.
        
        Args:
            file_path: Path to implementation file
            capability_name: Name of capability being implemented
        
        Returns:
            Validation result
        """
        # Log validation start
        self.evolution_logger.log_event(
            event_type=EvolutionEventType.VALIDATION_STARTED
            if False  # Will be replaced with correct constant
            else EvolutionEventType.IMPLEMENTATION_STARTED,
            capability=capability_name,
            status=EventStatus.IN_PROGRESS,
            description=f"Validating implementation for {capability_name}",
            details={"file": file_path},
        )

        result = self.verifier.verify_implementation(file_path)

        if result.get("overall_passed"):
            self.evolution_logger.log_event(
                event_type=EvolutionEventType.VALIDATION_PASSED,
                capability=capability_name,
                status=EventStatus.SUCCESS,
                description=f"Implementation validation passed",
                details=result,
            )
        else:
            self.evolution_logger.log_event(
                event_type=EvolutionEventType.VALIDATION_FAILED,
                capability=capability_name,
                status=EventStatus.FAILED,
                description=f"Implementation validation failed",
                details=result,
            )

        return result

    async def deploy_capability(self, capability_name: str) -> EvolutionDecision:
        """
        Deploy a validated capability (make it available).
        
        Args:
            capability_name: Name of capability to deploy
        
        Returns:
            EvolutionDecision with deployment status
        """
        try:
            self.capability_registry.update_status(
                capability_name, CapabilityStatus.AVAILABLE
            )

            self.evolution_logger.log_event(
                event_type=EvolutionEventType.CAPABILITY_DEPLOYED,
                capability=capability_name,
                status=EventStatus.SUCCESS,
                description=f"Capability {capability_name} successfully deployed",
            )

            return EvolutionDecision(
                action="proceed",
                capability=capability_name,
                message=f"Capability {capability_name} is now available!",
                details={"status": "deployed"},
            )
        except Exception as e:
            return EvolutionDecision(
                action="failed",
                capability=capability_name,
                message=f"Failed to deploy {capability_name}: {str(e)}",
            )

    async def rollback_capability(self, backup_id: str) -> EvolutionDecision:
        """
        Rollback to a previous backup.
        
        Args:
            backup_id: ID of backup to restore
        
        Returns:
            EvolutionDecision with rollback status
        """
        backup_info = self.backup_manager.get_backup_info(backup_id)
        if not backup_info:
            return EvolutionDecision(
                action="failed",
                message=f"Backup {backup_id} not found",
            )

        result = self.backup_manager.restore_backup(backup_id)

        if result.get("status") == "success":
            # Log rollback
            self.evolution_logger.log_event(
                event_type=EvolutionEventType.ROLLBACK_EXECUTED,
                capability="system",
                status=EventStatus.SUCCESS,
                description=f"System rolled back to {backup_id}",
                rollback_backup_id=backup_id,
            )

            return EvolutionDecision(
                action="proceed",
                message=f"System restored to {backup_info.get('reason')}",
                details=result,
            )
        else:
            return EvolutionDecision(
                action="failed",
                message=f"Failed to rollback: {result.get('error')}",
            )

    def get_capability_status(self, capability_name: str) -> dict:
        """Get current status and history of a capability."""
        cap = self.capability_registry.get_capability(capability_name)
        timeline = self.evolution_logger.get_capability_timeline(capability_name)

        return {
            "capability": capability_name,
            "current_status": cap.status.value if cap else "unknown",
            "timeline": timeline,
            "details": cap.to_dict() if cap else None,
        }

    def list_all_capabilities(self) -> list[dict]:
        """List all capabilities and their status."""
        return self.capability_registry.list_capabilities()

    def get_evolution_history(self, limit: int = 50) -> list[dict]:
        """Get recent evolution events."""
        return self.evolution_logger.get_event_history(limit=limit)


def get_evolution_agent(
    backup_manager=None,
    capability_registry=None,
    gap_detector=None,
    evolution_logger=None,
    tool_executor=None,
    verifier=None,
) -> EvolutionAgent:
    """Dependency for FastAPI endpoints."""
    return EvolutionAgent(
        backup_manager=backup_manager,
        capability_registry=capability_registry,
        gap_detector=gap_detector,
        evolution_logger=evolution_logger,
        tool_executor=tool_executor,
        verifier=verifier,
    )
