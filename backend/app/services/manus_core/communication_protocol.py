"""
Enhanced Inter-Agent Communication Protocol for Manus-Refined Architecture

This module implements a robust, reliable communication framework for inter-agent
collaboration with message prioritization, guaranteed delivery, and structured schemas.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import json


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


@dataclass
class EnhancedAgentMessage:
    """Enhanced agent message with reliability features."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_role: str = ""
    recipient_role: Optional[str] = None
    message_type: str = ""
    content: dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    acknowledgment_required: bool = True
    acknowledgment_received: bool = False
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "sender_role": self.sender_role,
            "recipient_role": self.recipient_role,
            "message_type": self.message_type,
            "content": self.content,
            "priority": self.priority.name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


class CommunicationBus:
    """
    Central communication bus for inter-agent messaging.
    
    Features:
    - Message prioritization
    - Guaranteed delivery with retries
    - Message acknowledgment
    - Delivery status tracking
    - Error handling and recovery
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the communication bus.
        
        Args:
            max_queue_size: Maximum size of message queues
        """
        self.agent_queues: dict[str, asyncio.PriorityQueue] = {}
        self.message_history: List[EnhancedAgentMessage] = []
        self.delivery_status: dict[str, MessageStatus] = {}
        self.max_queue_size = max_queue_size
        self.message_callbacks: dict[str, List[Callable]] = {}
        self.failed_messages: List[EnhancedAgentMessage] = []

    def register_agent(self, agent_role: str):
        """Register an agent on the communication bus."""
        if agent_role not in self.agent_queues:
            self.agent_queues[agent_role] = asyncio.PriorityQueue(maxsize=self.max_queue_size)
            self.message_callbacks[agent_role] = []

    async def send_message(self, message: EnhancedAgentMessage) -> bool:
        """
        Send a message through the communication bus.
        
        Args:
            message: The message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if message.recipient_role and message.recipient_role not in self.agent_queues:
            self.register_agent(message.recipient_role)

        try:
            # Store in history
            self.message_history.append(message)
            message.status = MessageStatus.SENT

            # Add to recipient's queue with priority
            if message.recipient_role:
                queue = self.agent_queues[message.recipient_role]
                await queue.put((message.priority.value, message))
                self.delivery_status[message.message_id] = MessageStatus.SENT

                # Trigger callbacks
                await self._trigger_callbacks(message.recipient_role, message)

                return True
            else:
                # Broadcast to all agents
                for role, queue in self.agent_queues.items():
                    await queue.put((message.priority.value, message))
                self.delivery_status[message.message_id] = MessageStatus.SENT
                return True

        except asyncio.QueueFull:
            message.status = MessageStatus.FAILED
            message.error_message = "Queue is full"
            self.failed_messages.append(message)
            return False
        except Exception as e:
            message.status = MessageStatus.FAILED
            message.error_message = str(e)
            self.failed_messages.append(message)
            return False

    async def receive_message(self, agent_role: str) -> Optional[EnhancedAgentMessage]:
        """
        Receive a message for an agent.
        
        Args:
            agent_role: Role of the agent receiving the message
            
        Returns:
            The received message, or None if queue is empty
        """
        if agent_role not in self.agent_queues:
            return None

        try:
            queue = self.agent_queues[agent_role]
            priority, message = queue.get_nowait()
            message.status = MessageStatus.DELIVERED
            self.delivery_status[message.message_id] = MessageStatus.DELIVERED
            return message
        except asyncio.QueueEmpty:
            return None

    async def acknowledge_message(self, message_id: str) -> bool:
        """
        Acknowledge receipt of a message.
        
        Args:
            message_id: ID of the message to acknowledge
            
        Returns:
            True if acknowledged successfully
        """
        for msg in self.message_history:
            if msg.message_id == message_id:
                msg.acknowledgment_received = True
                msg.status = MessageStatus.ACKNOWLEDGED
                self.delivery_status[message_id] = MessageStatus.ACKNOWLEDGED
                return True
        return False

    async def retry_failed_message(self, message: EnhancedAgentMessage) -> bool:
        """
        Retry sending a failed message.
        
        Args:
            message: The message to retry
            
        Returns:
            True if retry was successful
        """
        if message.retry_count >= message.max_retries:
            return False

        message.retry_count += 1
        return await self.send_message(message)

    async def _trigger_callbacks(self, agent_role: str, message: EnhancedAgentMessage):
        """Trigger registered callbacks for a message."""
        callbacks = self.message_callbacks.get(agent_role, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"Error in callback: {e}")

    def register_callback(self, agent_role: str, callback: Callable):
        """Register a callback for when messages arrive for an agent."""
        if agent_role not in self.message_callbacks:
            self.message_callbacks[agent_role] = []
        self.message_callbacks[agent_role].append(callback)

    def get_message_history(self, agent_role: Optional[str] = None,
                           message_type: Optional[str] = None,
                           limit: int = 100) -> List[EnhancedAgentMessage]:
        """Get message history with optional filters."""
        history = self.message_history

        if agent_role:
            history = [m for m in history if m.sender_role == agent_role or m.recipient_role == agent_role]

        if message_type:
            history = [m for m in history if m.message_type == message_type]

        return history[-limit:]

    def get_communication_stats(self) -> dict[str, Any]:
        """Get communication statistics."""
        total_messages = len(self.message_history)
        delivered = sum(1 for m in self.message_history if m.status == MessageStatus.DELIVERED)
        acknowledged = sum(1 for m in self.message_history if m.status == MessageStatus.ACKNOWLEDGED)
        failed = len(self.failed_messages)

        return {
            "total_messages": total_messages,
            "delivered": delivered,
            "acknowledged": acknowledged,
            "failed": failed,
            "delivery_rate": (delivered / total_messages) if total_messages > 0 else 0,
            "acknowledgment_rate": (acknowledged / total_messages) if total_messages > 0 else 0,
            "registered_agents": len(self.agent_queues),
            "average_queue_size": sum(q.qsize() for q in self.agent_queues.values()) / len(self.agent_queues) if self.agent_queues else 0
        }

    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()
        self.delivery_status.clear()
        self.failed_messages.clear()


class MessageRouter:
    """
    Routes messages between agents based on message type and content.
    """

    def __init__(self, communication_bus: CommunicationBus):
        """
        Initialize the message router.
        
        Args:
            communication_bus: The communication bus to use
        """
        self.bus = communication_bus
        self.routing_rules: dict[str, Callable] = {}

    def register_routing_rule(self, rule_name: str, rule_function: Callable):
        """Register a routing rule."""
        self.routing_rules[rule_name] = rule_function

    async def route_message(self, message: EnhancedAgentMessage) -> bool:
        """
        Route a message to the appropriate recipient(s).
        
        Args:
            message: The message to route
            
        Returns:
            True if routing was successful
        """
        # Apply routing rules to determine recipient
        if message.recipient_role:
            return await self.bus.send_message(message)

        # If no recipient specified, apply routing rules
        for rule_name, rule_func in self.routing_rules.items():
            recipient = rule_func(message)
            if recipient:
                message.recipient_role = recipient
                return await self.bus.send_message(message)

        # If no rule matched, broadcast
        return await self.bus.send_message(message)
