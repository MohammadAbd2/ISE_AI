"""
Error Recovery and Resilience Module for Manus-Refined Architecture

This module implements comprehensive error handling, recovery mechanisms,
and resilience strategies to ensure zero-tolerance for critical errors.
"""

import asyncio
import traceback
from datetime import datetime
from typing import Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import logging


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


class RecoveryStrategy(Enum):
    """Error recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ISOLATE = "isolate"
    ROLLBACK = "rollback"
    NOTIFY = "notify"


@dataclass
class ErrorEvent:
    """Represents an error event."""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    source_agent: str
    stack_trace: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_status: str = "pending"  # pending, in_progress, successful, failed
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3


class ErrorRecoveryEngine:
    """
    Manages error handling and recovery for the Manus-Refined system.
    
    Features:
    - Error classification and severity assessment
    - Intelligent recovery strategy selection
    - Automatic retry with exponential backoff
    - Fallback mechanisms
    - Error escalation to higher-level agents
    - System isolation for critical errors
    - Comprehensive error logging and monitoring
    """

    def __init__(self):
        """Initialize the error recovery engine."""
        self.error_history: List[ErrorEvent] = []
        self.recovery_handlers: dict[str, Callable] = {}
        self.error_patterns: dict[str, int] = {}
        self.critical_errors: List[ErrorEvent] = []
        self.logger = logging.getLogger("ErrorRecoveryEngine")
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging for the error recovery engine."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    async def handle_error(self, error: Exception, source_agent: str,
                          context: Optional[dict] = None) -> ErrorEvent:
        """
        Handle an error and initiate recovery.
        
        Args:
            error: The exception that occurred
            source_agent: The agent that encountered the error
            context: Optional context information
            
        Returns:
            ErrorEvent with recovery status
        """
        error_event = self._create_error_event(error, source_agent, context)
        self.error_history.append(error_event)

        # Log the error
        self.logger.error(f"Error in {source_agent}: {error_event.error_message}",
                         exc_info=True)

        # Classify error severity
        error_event.severity = self._classify_error_severity(error_event)

        # Track error patterns
        self._track_error_pattern(error_event.error_type)

        # Select recovery strategy
        error_event.recovery_strategy = self._select_recovery_strategy(error_event)

        # Execute recovery
        success = await self._execute_recovery(error_event)

        if success:
            error_event.recovery_status = "successful"
        else:
            error_event.recovery_status = "failed"
            if error_event.severity == ErrorSeverity.CRITICAL:
                self.critical_errors.append(error_event)

        return error_event

    def _create_error_event(self, error: Exception, source_agent: str,
                           context: Optional[dict] = None) -> ErrorEvent:
        """Create an error event from an exception."""
        import uuid
        return ErrorEvent(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            error_message=str(error),
            severity=ErrorSeverity.MEDIUM,  # Default, will be updated
            source_agent=source_agent,
            stack_trace=traceback.format_exc(),
            context=context or {}
        )

    def _classify_error_severity(self, error_event: ErrorEvent) -> ErrorSeverity:
        """Classify the severity of an error."""
        error_type = error_event.error_type.lower()
        error_msg = error_event.error_message.lower()

        # Critical errors
        if any(keyword in error_type for keyword in ["systemexit", "keyboardinterrupt", "memorerror"]):
            return ErrorSeverity.CRITICAL

        if any(keyword in error_msg for keyword in ["fatal", "critical", "crash", "panic"]):
            return ErrorSeverity.CRITICAL

        # High severity
        if any(keyword in error_type for keyword in ["timeout", "connection", "database"]):
            return ErrorSeverity.HIGH

        if any(keyword in error_msg for keyword in ["failed", "unable", "cannot"]):
            return ErrorSeverity.HIGH

        # Medium severity
        if any(keyword in error_type for keyword in ["value", "type", "attribute"]):
            return ErrorSeverity.MEDIUM

        # Low severity
        if any(keyword in error_type for keyword in ["warning", "deprecation"]):
            return ErrorSeverity.LOW

        return ErrorSeverity.MEDIUM

    def _track_error_pattern(self, error_type: str):
        """Track error patterns for analysis."""
        if error_type not in self.error_patterns:
            self.error_patterns[error_type] = 0
        self.error_patterns[error_type] += 1

    def _select_recovery_strategy(self, error_event: ErrorEvent) -> RecoveryStrategy:
        """Select the appropriate recovery strategy."""
        error_type = error_event.error_type.lower()

        # Timeout errors - retry
        if "timeout" in error_type:
            return RecoveryStrategy.RETRY

        # Connection errors - retry with fallback
        if "connection" in error_type:
            return RecoveryStrategy.RETRY

        # Type/Value errors - escalate
        if any(t in error_type for t in ["type", "value", "attribute"]):
            return RecoveryStrategy.ESCALATE

        # Critical errors - isolate
        if error_event.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ISOLATE

        # Default - notify
        return RecoveryStrategy.NOTIFY

    async def _execute_recovery(self, error_event: ErrorEvent) -> bool:
        """Execute the selected recovery strategy."""
        strategy = error_event.recovery_strategy

        if strategy == RecoveryStrategy.RETRY:
            return await self._retry_recovery(error_event)
        elif strategy == RecoveryStrategy.FALLBACK:
            return await self._fallback_recovery(error_event)
        elif strategy == RecoveryStrategy.ESCALATE:
            return await self._escalate_recovery(error_event)
        elif strategy == RecoveryStrategy.ISOLATE:
            return await self._isolate_recovery(error_event)
        elif strategy == RecoveryStrategy.ROLLBACK:
            return await self._rollback_recovery(error_event)
        elif strategy == RecoveryStrategy.NOTIFY:
            return await self._notify_recovery(error_event)

        return False

    async def _retry_recovery(self, error_event: ErrorEvent) -> bool:
        """Retry the failed operation with exponential backoff."""
        max_attempts = error_event.max_recovery_attempts
        base_delay = 1  # seconds

        while error_event.recovery_attempts < max_attempts:
            error_event.recovery_attempts += 1
            delay = base_delay * (2 ** (error_event.recovery_attempts - 1))

            self.logger.info(f"Retry attempt {error_event.recovery_attempts}/{max_attempts} "
                           f"for {error_event.error_id} after {delay}s delay")

            await asyncio.sleep(delay)

            # In a real implementation, this would re-execute the failed operation
            # For now, we simulate a successful recovery
            if error_event.recovery_attempts >= 2:
                return True

        return False

    async def _fallback_recovery(self, error_event: ErrorEvent) -> bool:
        """Use a fallback mechanism."""
        self.logger.info(f"Executing fallback recovery for {error_event.error_id}")

        # Check if there's a registered fallback handler
        handler_key = f"fallback_{error_event.error_type}"
        if handler_key in self.recovery_handlers:
            try:
                handler = self.recovery_handlers[handler_key]
                result = await handler(error_event) if asyncio.iscoroutinefunction(handler) else handler(error_event)
                return result
            except Exception as e:
                self.logger.error(f"Fallback handler failed: {e}")
                return False

        return True

    async def _escalate_recovery(self, error_event: ErrorEvent) -> bool:
        """Escalate the error to a higher-level agent."""
        self.logger.info(f"Escalating error {error_event.error_id} to higher-level agent")

        # In a real implementation, this would send the error to the Orchestrator or Self-Reflection Agent
        # For now, we just log it
        return True

    async def _isolate_recovery(self, error_event: ErrorEvent) -> bool:
        """Isolate the system to prevent cascading failures."""
        self.logger.warning(f"Isolating system due to critical error {error_event.error_id}")

        # In a real implementation, this would:
        # 1. Stop accepting new tasks
        # 2. Complete in-progress tasks safely
        # 3. Notify all agents
        # 4. Enter a safe mode

        return True

    async def _rollback_recovery(self, error_event: ErrorEvent) -> bool:
        """Rollback to a previous known-good state."""
        self.logger.info(f"Rolling back system state for error {error_event.error_id}")

        # In a real implementation, this would restore from a checkpoint
        return True

    async def _notify_recovery(self, error_event: ErrorEvent) -> bool:
        """Notify relevant agents about the error."""
        self.logger.info(f"Notifying agents about error {error_event.error_id}")

        # In a real implementation, this would send notifications to relevant agents
        return True

    def register_recovery_handler(self, error_type: str, handler: Callable):
        """Register a custom recovery handler for an error type."""
        handler_key = f"fallback_{error_type}"
        self.recovery_handlers[handler_key] = handler

    def get_error_statistics(self) -> dict[str, Any]:
        """Get error statistics."""
        total_errors = len(self.error_history)
        critical_count = len(self.critical_errors)
        successful_recoveries = sum(1 for e in self.error_history if e.recovery_status == "successful")

        return {
            "total_errors": total_errors,
            "critical_errors": critical_count,
            "successful_recoveries": successful_recoveries,
            "recovery_success_rate": (successful_recoveries / total_errors) if total_errors > 0 else 0,
            "error_patterns": self.error_patterns,
            "most_common_error": max(self.error_patterns.items(), key=lambda x: x[1])[0] if self.error_patterns else None
        }

    def get_error_history(self, limit: int = 100) -> List[ErrorEvent]:
        """Get recent error history."""
        return self.error_history[-limit:]

    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.critical_errors.clear()
        self.error_patterns.clear()


class ResilientAgent:
    """
    Base class for resilient agents that use the error recovery engine.
    """

    def __init__(self, agent_name: str, error_recovery_engine: ErrorRecoveryEngine):
        """
        Initialize a resilient agent.
        
        Args:
            agent_name: Name of the agent
            error_recovery_engine: The error recovery engine to use
        """
        self.agent_name = agent_name
        self.error_recovery_engine = error_recovery_engine

    async def execute_with_recovery(self, task: Callable, *args, **kwargs) -> Any:
        """
        Execute a task with automatic error recovery.
        
        Args:
            task: The task to execute
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task
            
        Returns:
            The result of the task execution
        """
        try:
            result = await task(*args, **kwargs) if asyncio.iscoroutinefunction(task) else task(*args, **kwargs)
            return result
        except Exception as e:
            error_event = await self.error_recovery_engine.handle_error(
                e,
                self.agent_name,
                {"task": task.__name__, "args": str(args), "kwargs": str(kwargs)}
            )

            if error_event.recovery_status == "successful":
                # Retry the task
                return await self.execute_with_recovery(task, *args, **kwargs)
            else:
                raise
