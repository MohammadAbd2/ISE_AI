from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Awaitable

from app.core.config import settings
from app.services.self_upgrade_executor import SelfUpgradeExecutor


ProgressPublisher = Callable[[dict], Awaitable[None]] | None


@dataclass(slots=True)
class SelfRewriteDecision:
    should_handle: bool
    reason: str = ""


@dataclass(slots=True)
class SelfRewriteResult:
    reply: str
    render_blocks: list[dict]
    used_agents: list[str]


class SelfRewriteManager:
    """Guarded self-improvement flow that turns vague self-upgrade requests into isolated engineering work."""

    KEYWORDS = (
        "develop yourself",
        "improve yourself",
        "rewrite yourself",
        "rewrite your own code",
        "fix your own code",
        "upgrade yourself",
        "make yourself better",
        "self improve",
        "self-improve",
    )

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root
        self.executor = SelfUpgradeExecutor(project_root=project_root)

    def classify(self, user_message: str) -> SelfRewriteDecision:
        text = (user_message or "").lower()
        if any(keyword in text for keyword in self.KEYWORDS):
            return SelfRewriteDecision(True, "Explicit self-rewrite request detected.")
        return SelfRewriteDecision(False)

    async def execute(self, user_message: str, progress_callback: ProgressPublisher = None) -> SelfRewriteResult:
        packet = self._build_packet(user_message)
        if progress_callback:
            await progress_callback(
                {
                    "type": "report",
                    "payload": {
                        "title": "Self-development workflow started",
                        "summary": "The assistant opened a guarded self-rewrite session, planned the work, and is now applying changes in an isolated workspace.",
                        "highlights": [
                            f"Target subsystem: {packet['subsystem']}",
                            f"Auto-apply on success: {'yes' if packet['apply_on_success'] else 'no'}",
                            "Verification will run before reporting success.",
                        ],
                    },
                }
            )
            await progress_callback(
                {
                    "type": "plan_result",
                    "payload": {
                        "title": "Self-development plan",
                        "status": "in_progress",
                        "steps": [
                            {"step_number": 1, "description": step, "status": "completed" if index == 0 else "pending", "target": "self"}
                            for index, step in enumerate(packet["steps"], start=1)
                        ],
                    },
                }
            )
        execution = await self.executor.execute_packet(packet)
        reply = (
            "I completed a guarded self-development cycle. "
            "The execution summary, changed files, and verification status are now available in the chat. "
            "If verification passed, the rewritten files were applied back to the main project."
            if packet["apply_on_success"]
            else "I completed an isolated self-development cycle. Review the execution summary and changed files in the chat."
        )
        return SelfRewriteResult(
            reply=reply,
            render_blocks=execution.render_blocks,
            used_agents=execution.used_agents + ["self-rewrite-manager"],
        )

    def _build_packet(self, user_message: str) -> dict:
        text = (user_message or "").strip()
        return {
            "ready": True,
            "packet_id": "explicit-self-rewrite",
            "subsystem": "core-runtime",
            "summary": (
                "Improve the assistant's own code so it becomes more reliable for programming tasks, "
                "surfaces execution traces in chat, and repairs itself more safely. "
                f"User request: {text}"
            ),
            "targets": [
                "backend/app/services/agent.py",
                "backend/app/services/chat.py",
                "backend/app/services/model_manager.py",
                "backend/app/services/self_upgrade_executor.py",
                "frontend/src/App.jsx",
                "frontend/src/components/MessageList.jsx",
            ],
            "verification": [
                "python3.11 -m compileall backend/app",
                "cd frontend && npm run build",
            ],
            "steps": [
                "Inspect the current runtime flow and identify reliability gaps.",
                "Strengthen model selection for programming and self-development tasks.",
                "Improve the explicit self-rewrite path so it runs in an isolated workspace and reports visible evidence.",
                "Update the chat UI so progress, changed files, and validation results are clear.",
                "Run backend and frontend verification before declaring success.",
            ],
            "agent_prompt": text,
            "apply_on_success": settings.self_rewrite_apply_on_success,
        }
