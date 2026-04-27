import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class EvalHistoryService:
    def __init__(self, history_file: Path | None = None) -> None:
        self.history_file = history_file or (Path(settings.project_root) / ".eval-history.json")

    def append(self, report: dict) -> None:
        entries = self.list_history(limit=200)
        failing_cases = [
            item.get("name", "")
            for item in report.get("results", [])
            if not item.get("passed", False)
        ]
        failing_contracts = [
            item.get("name", "")
            for item in report.get("contracts", [])
            if not item.get("passed", False)
        ]
        entries.append(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "suite": report.get("suite", "unknown"),
                "score": report.get("score", 0.0),
                "passed": report.get("passed", 0),
                "total": report.get("total", 0),
                "sections": report.get("sections", {}),
                "failing_cases": failing_cases,
                "failing_contracts": failing_contracts,
            }
        )
        self.history_file.write_text(json.dumps(entries[-50:], indent=2), encoding="utf-8")

    def list_history(self, limit: int = 20) -> list[dict]:
        if not self.history_file.exists():
            return []
        try:
            payload = json.loads(self.history_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return payload[-limit:]

    def compare_recent_runs(self) -> dict:
        history = self.list_history(limit=2)
        if len(history) < 2:
            return {
                "available": False,
                "summary": "Not enough eval history to compare runs yet.",
                "score_delta": 0.0,
                "new_failures": [],
                "resolved_failures": [],
            }

        previous, current = history[-2], history[-1]
        previous_failures = set(previous.get("failing_cases", [])) | set(previous.get("failing_contracts", []))
        current_failures = set(current.get("failing_cases", [])) | set(current.get("failing_contracts", []))
        new_failures = sorted(current_failures - previous_failures)
        resolved_failures = sorted(previous_failures - current_failures)
        score_delta = round(current.get("score", 0.0) - previous.get("score", 0.0), 2)

        if score_delta > 0:
            summary = "The latest eval run improved relative to the previous run."
        elif score_delta < 0:
            summary = "The latest eval run regressed relative to the previous run."
        else:
            summary = "The latest eval run matched the previous score."

        return {
            "available": True,
            "summary": summary,
            "score_delta": score_delta,
            "new_failures": new_failures,
            "resolved_failures": resolved_failures,
            "previous_score": previous.get("score", 0.0),
            "current_score": current.get("score", 0.0),
        }

    def unstable_cases(self, limit: int = 5, window: int = 10) -> list[dict]:
        history = self.list_history(limit=window)
        if not history:
            return []

        stats: dict[str, dict] = {}
        for entry in history:
            failure_names = set(entry.get("failing_cases", [])) | set(entry.get("failing_contracts", []))
            for name in failure_names:
                case = stats.setdefault(
                    name,
                    {
                        "name": name,
                        "failures": 0,
                        "last_seen": entry.get("created_at", ""),
                    },
                )
                case["failures"] += 1
                case["last_seen"] = entry.get("created_at", case["last_seen"])

        ranked = sorted(
            stats.values(),
            key=lambda item: (item["failures"], item["last_seen"]),
            reverse=True,
        )
        return ranked[:limit]

    def prioritized_instability(self, limit: int = 5, window: int = 10) -> list[dict]:
        history = self.list_history(limit=window)
        if not history:
            return []

        stats: dict[str, dict] = {}
        total_runs = len(history)
        for index, entry in enumerate(history):
            failure_names = set(entry.get("failing_cases", [])) | set(entry.get("failing_contracts", []))
            recency_weight = index + 1
            score_penalty = max(0.0, 10.0 - float(entry.get("score", 0.0)))
            for name in failure_names:
                case = stats.setdefault(
                    name,
                    {
                        "name": name,
                        "failures": 0,
                        "weighted_score": 0.0,
                        "last_seen": entry.get("created_at", ""),
                    },
                )
                case["failures"] += 1
                case["weighted_score"] += recency_weight + score_penalty
                case["last_seen"] = entry.get("created_at", case["last_seen"])

        ranked = sorted(
            (
                {
                    **item,
                    "failure_rate": round(item["failures"] / total_runs, 2),
                    "weighted_score": round(item["weighted_score"], 2),
                }
                for item in stats.values()
            ),
            key=lambda item: (item["weighted_score"], item["failures"], item["last_seen"]),
            reverse=True,
        )
        return ranked[:limit]

    def _infer_subsystem(self, case_name: str) -> str:
        lower = case_name.lower()
        if "capability::" in lower or "capability" in lower:
            return "capability_contracts"
        if any(token in lower for token in ["chart", "visual", "map"]):
            return "visualization"
        if any(token in lower for token in ["self_development", "self_reflection", "develop yourself", "docs"]):
            return "self_reflection_and_docs"
        if any(token in lower for token in ["project_analysis", "codebase", "archive"]):
            return "project_context"
        if any(token in lower for token in ["search", "research", "latest_docs"]):
            return "research_and_search"
        if any(token in lower for token in ["chat", "small_talk", "intent", "routing"]):
            return "routing"
        return "runtime_misc"

    def subsystem_hotspots(self, limit: int = 5, window: int = 10) -> list[dict]:
        prioritized = self.prioritized_instability(limit=100, window=window)
        if not prioritized:
            return []

        grouped: dict[str, dict] = {}
        for item in prioritized:
            subsystem = self._infer_subsystem(item["name"])
            bucket = grouped.setdefault(
                subsystem,
                {
                    "subsystem": subsystem,
                    "case_count": 0,
                    "total_failures": 0,
                    "weighted_score": 0.0,
                    "cases": [],
                },
            )
            bucket["case_count"] += 1
            bucket["total_failures"] += item["failures"]
            bucket["weighted_score"] += item["weighted_score"]
            bucket["cases"].append(item["name"])

        ranked = sorted(
            (
                {
                    **item,
                    "weighted_score": round(item["weighted_score"], 2),
                    "cases": item["cases"][:5],
                }
                for item in grouped.values()
            ),
            key=lambda item: (item["weighted_score"], item["total_failures"], item["case_count"]),
            reverse=True,
        )
        return ranked[:limit]


@lru_cache
def get_eval_history_service() -> EvalHistoryService:
    return EvalHistoryService()
