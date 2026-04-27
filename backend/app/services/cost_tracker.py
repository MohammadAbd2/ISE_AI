"""
Cost tracking service for monitoring token usage and session costs.
Estimates costs based on model usage and token counts.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings


@dataclass
class TokenUsage:
    """Token usage for a specific model."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class CostTracker:
    """
    Tracks and estimates the cost of AI model usage.
    """

    # Model pricing (USD per 1M tokens) - Estimates for popular models
    PRICING = {
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "deepseek-coder": {"input": 0.10, "output": 0.10},
        "llama-3-70b": {"input": 0.50, "output": 0.50},
        "qwen2.5-coder-32b-instruct": {"input": 0.20, "output": 0.20},
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(settings.backend_root).parent.parent
        self.stats_file = self.project_root / ".evolution-costs.json"
        self.session_usage: Dict[str, TokenUsage] = {}
        self._load_stats()

    def _load_stats(self):
        """Load persistent cost statistics."""
        if self.stats_file.exists():
            try:
                data = json.loads(self.stats_file.read_text())
                self.total_cost_usd = data.get("total_cost_usd", 0.0)
                self.total_sessions = data.get("total_sessions", 0)
            except Exception:
                self.total_cost_usd = 0.0
                self.total_sessions = 0
        else:
            self.total_cost_usd = 0.0
            self.total_sessions = 0

    def _save_stats(self):
        """Save persistent cost statistics."""
        data = {
            "total_cost_usd": self.total_cost_usd,
            "total_sessions": self.total_sessions,
            "last_updated": datetime.now(UTC).isoformat(),
        }
        self.stats_file.write_text(json.dumps(data, indent=2))

    def record_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Record token usage and calculate cost."""
        if model not in self.session_usage:
            self.session_usage[model] = TokenUsage(model=model)
        
        usage = self.session_usage[model]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.total_tokens += (input_tokens + output_tokens)
        
        # Calculate cost
        pricing = self._get_pricing(model)
        cost = (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
        usage.cost_usd += cost
        
        # Update total
        self.total_cost_usd += cost
        self._save_stats()

    def _get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model (with fallbacks)."""
        # Match prefix for specific models (e.g., 'gpt-4o-2024-05-13' -> 'gpt-4o')
        for key in self.PRICING:
            if model.startswith(key):
                return self.PRICING[key]
        
        # Default pricing for unknown models
        return {"input": 0.50, "output": 0.50}

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session usage and costs."""
        total_tokens = sum(u.total_tokens for u in self.session_usage.values())
        total_cost = sum(u.cost_usd for u in self.session_usage.values())
        
        return {
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "models": {
                model: {
                    "input": u.input_tokens,
                    "output": u.output_tokens,
                    "total": u.total_tokens,
                    "cost": u.cost_usd
                }
                for model, u in self.session_usage.items()
            }
        }

    def get_total_stats(self) -> Dict[str, Any]:
        """Get total historical stats."""
        return {
            "total_cost_usd": self.total_cost_usd,
            "total_sessions": self.total_sessions,
        }

    def start_new_session(self):
        """Initialize stats for a new session."""
        self.session_usage = {}
        self.total_sessions += 1
        self._save_stats()


# Global instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker(project_root: Optional[Path] = None) -> CostTracker:
    """Get or create cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker(project_root)
    return _cost_tracker
