from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class TemplateVerification:
    passed: bool
    score: int
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "score": self.score, "issues": self.issues, "suggestions": self.suggestions}


class NoTemplateVerifier:
    """Detects canned/generic outputs before a generated project can be exported."""

    FORBIDDEN_MARKERS = [
        "lorem ipsum", "placeholder", "replace with", "sample data", "example.com", "mock data",
        "your company", "generic landing", "clear value",
        "sandbox generated", "built, verified", "generatedcomponent", "generated component",
    ]
    REQUIRED_DOMAIN_HINTS = {
        "restaurant": ["menu", "reservation", "chef", "dining", "table"],
        "market": ["products", "fresh", "shop", "deals", "basket", "delivery"],
        "doctor": ["appointment", "clinic", "care", "patients", "services"],
        "travel": ["destination", "itinerary", "booking", "journey", "trip"],
        "cms": ["dashboard", "content", "editor", "roles", "publish"],
        "cv": ["experience", "skills", "contact", "profile", "career"],
        "login": ["login", "password", "auth", "token", "email"],
    }

    def verify_texts(self, task: str, files: dict[str, str]) -> TemplateVerification:
        issues: list[str] = []
        suggestions: list[str] = []
        joined = "\n".join(files.values()).lower()
        task_lower = task.lower()
        for marker in self.FORBIDDEN_MARKERS:
            if marker in joined:
                issues.append(f"Canned marker found: {marker}")
        domain = self._domain(task_lower)
        if domain:
            hints = self.REQUIRED_DOMAIN_HINTS.get(domain, [])
            matches = [hint for hint in hints if hint in joined]
            if len(matches) < max(2, min(3, len(hints))):
                issues.append(f"Output is not specific enough for domain '{domain}'")
                suggestions.append(f"Add concrete {domain} sections, copy, CTA labels, and domain-specific features.")
        if self._too_similar_to_known_shell(joined):
            issues.append("Output resembles the generic landing-page shell too closely")
            suggestions.append("Regenerate file-by-file from extracted requirements instead of using the shell.")
        score = max(0, 100 - len(issues) * 25)
        return TemplateVerification(passed=not issues, score=score, issues=issues, suggestions=suggestions)

    def verify_paths(self, task: str, workspace: Path, relative_paths: list[str]) -> TemplateVerification:
        files: dict[str, str] = {}
        for rel in relative_paths:
            path = (workspace / rel).resolve()
            if path.is_file() and path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".sass", ".html", ".md"}:
                files[rel] = path.read_text(encoding="utf-8", errors="ignore")
        return self.verify_texts(task, files)

    def _domain(self, task_lower: str) -> str | None:
        for key in self.REQUIRED_DOMAIN_HINTS:
            if key in task_lower:
                return key
        if "dent" in task_lower:
            return "doctor"
        if any(word in task_lower for word in ["cv", "resume", "portfolio", "curriculum vitae"]):
            return "cv"
        if any(word in task_lower for word in ["login", "authentication", "auth", "jwt"]):
            return "login"
        return None

    def _too_similar_to_known_shell(self, text: str) -> bool:
        shell = "clear value trust section conversion flow designed to impress from the first scroll ready to begin"
        ratio = difflib.SequenceMatcher(None, re.sub(r"\s+", " ", text[:1200]), shell).ratio()
        return ratio > 0.62
