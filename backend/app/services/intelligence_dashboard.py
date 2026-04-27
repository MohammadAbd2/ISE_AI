
from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.services.agent_memory import get_agent_memory_store
from app.services.agent_observability import get_agent_trace_store
from app.services.benchmark_suite import get_benchmark_suite
from app.services.continuous_improvement import get_improvement_store


class IntelligenceDashboardService:
    def summary(self) -> dict[str, Any]:
        traces = get_agent_trace_store().list_runs()
        benchmarks = get_benchmark_suite().score_static_capabilities()
        lessons = get_improvement_store().search("", limit=10)
        memory = get_agent_memory_store()
        recent = memory.search("", limit=10)
        success_count = sum(1 for item in recent if getattr(item, "success", False))
        total = len(recent)
        return {
            "trace_runs": len(traces),
            "recent_tasks": total,
            "success_rate": round(success_count / total, 2) if total else None,
            "lessons": lessons,
            "benchmark_score": benchmarks.get("score"),
            "benchmark_checks": benchmarks.get("checks", []),
            "top_risks": [
                "Validate every artifact before rendering a download button.",
                "Prefer real tool output over generated status text.",
                "Run preview/browser checks before claiming UI success.",
            ],
        }


@lru_cache
def get_intelligence_dashboard() -> IntelligenceDashboardService:
    return IntelligenceDashboardService()
