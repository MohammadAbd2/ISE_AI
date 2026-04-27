"""Agent-to-agent communication protocol for collaborative autonomous runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AgentMessage:
    sender: str
    recipient: str
    kind: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentSharedContext:
    def __init__(self, task: str, run_id: str | None = None) -> None:
        self.run_id = run_id or str(uuid4())
        self.task = task
        self.messages: list[AgentMessage] = []
        self.decisions: list[dict[str, Any]] = []
        self.files: list[str] = []
        self.errors: list[str] = []
        self.artifacts: list[dict[str, Any]] = []
        self.retries: list[dict[str, Any]] = []

    def send(self, sender: str, recipient: str, kind: str, content: str, **metadata: Any) -> AgentMessage:
        msg = AgentMessage(sender=sender, recipient=recipient, kind=kind, content=content, metadata=metadata)
        self.messages.append(msg)
        if kind == "decision":
            self.decisions.append({"agent": sender, "content": content, "metadata": metadata, "created_at": msg.created_at})
        elif kind == "file" and metadata.get("path"):
            self.files.append(str(metadata["path"]))
        elif kind == "error":
            self.errors.append(content)
        elif kind == "artifact":
            self.artifacts.append(metadata)
        elif kind == "retry":
            self.retries.append({"agent": sender, "content": content, "metadata": metadata, "created_at": msg.created_at})
        return msg

    def transcript(self, limit: int = 20) -> list[dict[str, Any]]:
        return [{"sender": m.sender, "recipient": m.recipient, "kind": m.kind, "content": m.content,
                 "metadata": m.metadata, "created_at": m.created_at} for m in self.messages[-limit:]]

    def to_render_payload(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "task": self.task, "messages": self.transcript(),
                "decisions": self.decisions[-12:], "files": list(dict.fromkeys(self.files)),
                "errors": self.errors[-8:], "retries": self.retries[-8:], "artifacts": self.artifacts[-5:]}


class AgentTeamProtocol:
    """Explicit Planner→Builder→Verifier→Debug→Export collaboration bus."""

    def __init__(self, context: AgentSharedContext) -> None:
        self.context = context

    def planner_to_builder(self, content: str, **metadata: Any) -> AgentMessage:
        return self.context.send("PlannerAgent", "BuilderAgent", "task", content, **metadata)

    def builder_to_verifier(self, content: str, **metadata: Any) -> AgentMessage:
        return self.context.send("BuilderAgent", "VerifierAgent", "file", content, **metadata)

    def verifier_to_debugger(self, content: str, **metadata: Any) -> AgentMessage:
        return self.context.send("VerifierAgent", "DebugAgent", "error", content, **metadata)

    def debugger_to_builder(self, content: str, **metadata: Any) -> AgentMessage:
        return self.context.send("DebugAgent", "BuilderAgent", "retry", content, **metadata)

    def verifier_to_exporter(self, content: str, **metadata: Any) -> AgentMessage:
        return self.context.send("VerifierAgent", "ExportAgent", "decision", content, **metadata)

    def exporter_to_user(self, content: str, **metadata: Any) -> AgentMessage:
        return self.context.send("ExportAgent", "User", "artifact", content, **metadata)
