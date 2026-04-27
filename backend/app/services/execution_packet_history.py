import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.services.eval_history import EvalHistoryService, get_eval_history_service


class ExecutionPacketHistoryService:
    def __init__(self, history_file: Path | None = None) -> None:
        self.history_file = history_file or (Path(settings.project_root) / ".execution-packet-history.json")

    def record_launch(self, *, packet: dict, session_id: str = "") -> dict:
        entries = self.list_history(limit=200)
        entry = {
            "launched_at": datetime.now(UTC).isoformat(),
            "packet_id": packet.get("packet_id", ""),
            "subsystem": packet.get("subsystem", ""),
            "summary": packet.get("summary", ""),
            "targets": packet.get("targets", [])[:4],
            "eval_score": packet.get("eval_score", 0.0),
            "session_id": session_id,
        }
        entries.append(entry)
        self.history_file.write_text(json.dumps(entries[-50:], indent=2), encoding="utf-8")
        return entry

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

    def list_history_with_outcomes(
        self,
        eval_history: EvalHistoryService | None = None,
        limit: int = 20,
    ) -> list[dict]:
        history = self.list_history(limit=limit)
        eval_service = eval_history or get_eval_history_service()
        eval_runs = eval_service.list_history(limit=100)
        return [self._attach_outcome(entry, eval_runs) for entry in history]

    def _attach_outcome(self, entry: dict, eval_runs: list[dict]) -> dict:
        launched_at_raw = entry.get("launched_at", "")
        try:
            launched_at = datetime.fromisoformat(launched_at_raw.replace("Z", "+00:00"))
        except ValueError:
            launched_at = None

        if launched_at is None:
            return {
                **entry,
                "status": "unknown",
                "score_delta": 0.0,
                "latest_score": entry.get("eval_score", 0.0),
                "eval_runs_after_launch": 0,
                "summary": "Launch timestamp is invalid, so no verification outcome is available.",
            }

        subsequent_runs = []
        for run in eval_runs:
            created_at_raw = run.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            if created_at >= launched_at:
                subsequent_runs.append(run)

        if not subsequent_runs:
            return {
                **entry,
                "status": "pending_verification",
                "score_delta": 0.0,
                "latest_score": entry.get("eval_score", 0.0),
                "eval_runs_after_launch": 0,
                "summary": "No eval run has verified this remediation launch yet.",
            }

        latest_run = subsequent_runs[-1]
        baseline_score = float(entry.get("eval_score", 0.0))
        latest_score = float(latest_run.get("score", baseline_score))
        score_delta = round(latest_score - baseline_score, 2)
        if score_delta > 0.15:
            status = "improved"
            summary = "A later eval run improved after this remediation launch."
        elif score_delta < -0.15:
            status = "regressed"
            summary = "A later eval run regressed after this remediation launch."
        else:
            status = "verified_no_change"
            summary = "A later eval run verified this launch without changing the score."

        return {
            **entry,
            "status": status,
            "score_delta": score_delta,
            "latest_score": latest_score,
            "eval_runs_after_launch": len(subsequent_runs),
            "summary": summary,
        }


@lru_cache
def get_execution_packet_history_service() -> ExecutionPacketHistoryService:
    return ExecutionPacketHistoryService()
