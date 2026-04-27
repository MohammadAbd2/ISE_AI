
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ReasoningRevision:
    id: str
    phase: str
    critique: str
    decision: str
    confidence: float
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReasoningRun:
    id: str
    task: str
    selected_strategy: str
    revisions: list[ReasoningRevision]
    status: str = "ready"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "revisions": [r.to_dict() for r in self.revisions]}


class ReflectiveReasoningEngine:
    """Deterministic reflective planning layer used before execution.

    This is intentionally tool-first: it does not claim work is done. It produces
    a revisable strategy that downstream agents must execute through filesystem,
    shell, test, preview, and export tools.
    """

    def create_reasoned_strategy(self, task: str, *, max_revisions: int = 3) -> ReasoningRun:
        task = (task or "").strip()
        subject = self._extract_subject(task)
        revisions: list[ReasoningRevision] = []
        candidates = [
            ("thin-slice-first", "Build the smallest working vertical slice, verify, then expand."),
            ("architecture-first", "Define files and contracts before generating code."),
            ("test-driven", "Create verification criteria first and repair until green."),
        ]
        selected = "architecture-first"
        for i, (name, decision) in enumerate(candidates[: max(1, min(max_revisions, len(candidates)))]):
            critique = self._critique(name, subject)
            confidence = 0.72 + (0.07 * i)
            if name == "architecture-first":
                selected = name
            revisions.append(ReasoningRevision(id=str(uuid4()), phase=name, critique=critique, decision=decision, confidence=round(confidence, 2)))
        return ReasoningRun(id=str(uuid4()), task=task, selected_strategy=selected, revisions=revisions)

    def _extract_subject(self, task: str) -> str:
        cleaned = task.lower()
        for phrase in ["create", "build", "roadmap", "download", "zip", "give me", "using react", "using node"]:
            cleaned = cleaned.replace(phrase, " ")
        return " ".join(cleaned.split())[:120] or "software project"

    def _critique(self, strategy: str, subject: str) -> str:
        if strategy == "thin-slice-first":
            return f"Good for fast feedback, but may under-design the {subject} if used alone."
        if strategy == "architecture-first":
            return f"Best default: derive files, components, verification commands, and export mode for {subject} before writing code."
        return f"Useful when failure risk is high; define observable checks for {subject} before declaring success."


@lru_cache
def get_reasoning_engine() -> ReflectiveReasoningEngine:
    return ReflectiveReasoningEngine()
