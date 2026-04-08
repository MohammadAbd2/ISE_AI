"""
Research Progress Logger

Provides real-time progress updates during internet searches
to give users visibility into what the AI is doing.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Optional


class ResearchStep(str, Enum):
    """Steps in the research process."""
    CHECKING_CACHE = "checking_cache"
    SEARCHING_WEB = "searching_web"
    FETCHING_PAGES = "fetching_pages"
    ANALYZING_SOURCES = "analyzing_sources"
    EXTRACTING_FACTS = "extracting_facts"
    SAVING_MEMORY = "saving_memory"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ResearchProgressEntry:
    """A single progress entry in the research process."""
    step: ResearchStep
    message: str
    timestamp: str
    details: Optional[str] = None
    source_count: Optional[int] = None
    is_complete: bool = False
    is_error: bool = False

    def to_dict(self) -> dict:
        return {
            "step": self.step.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
            "source_count": self.source_count,
            "is_complete": self.is_complete,
            "is_error": self.is_error,
        }


class ResearchProgressLogger:
    """
    Tracks and formats research progress for user display.
    
    Provides human-readable updates during the research process.
    """

    def __init__(self):
        self.entries: list[ResearchProgressEntry] = []
        self.start_time = datetime.now(UTC).isoformat()

    def log_step(
        self,
        step: ResearchStep,
        message: str,
        details: Optional[str] = None,
        source_count: Optional[int] = None,
    ):
        """Log a research progress step."""
        entry = ResearchProgressEntry(
            step=step,
            message=message,
            timestamp=datetime.now(UTC).isoformat(),
            details=details,
            source_count=source_count,
        )
        self.entries.append(entry)

    def log_cache_hit(self, query: str):
        """Log that a cached result was found."""
        self.log_step(
            ResearchStep.CHECKING_CACHE,
            "✓ Found cached research",
            f"Using previous research for: {query}",
        )

    def log_search_start(self, query: str):
        """Log that web search has started."""
        self.log_step(
            ResearchStep.SEARCHING_WEB,
            "🔍 Searching the web",
            f"Query: {query}",
        )

    def log_search_complete(self, source_count: int):
        """Log that search is complete."""
        self.log_step(
            ResearchStep.SEARCHING_WEB,
            f"✓ Found {source_count} sources",
            source_count=source_count,
        )

    def log_fetching_pages(self, count: int):
        """Log that pages are being fetched."""
        self.log_step(
            ResearchStep.FETCHING_PAGES,
            f"📄 Fetching content from {count} pages",
        )

    def log_analyzing_sources(self, count: int):
        """Log that sources are being analyzed."""
        self.log_step(
            ResearchStep.ANALYZING_SOURCES,
            f"🔬 Analyzing {count} sources",
        )

    def log_extracting_facts(self, fact_count: int):
        """Log that facts are being extracted."""
        self.log_step(
            ResearchStep.EXTRACTING_FACTS,
            f"💡 Extracted {fact_count} key facts",
        )

    def log_saving_memory(self):
        """Log that information is being saved to memory."""
        self.log_step(
            ResearchStep.SAVING_MEMORY,
            "💾 Saving to research memory",
        )

    def log_complete(self, source_count: int, fact_count: int):
        """Log research completion."""
        entry = ResearchProgressEntry(
            step=ResearchStep.COMPLETE,
            message=f"✓ Research complete",
            timestamp=datetime.now(UTC).isoformat(),
            details=f"{source_count} sources, {fact_count} facts saved",
            source_count=source_count,
            is_complete=True,
        )
        self.entries.append(entry)

    def log_error(self, error: str):
        """Log an error."""
        entry = ResearchProgressEntry(
            step=ResearchStep.FAILED,
            message="❌ Research failed",
            timestamp=datetime.now(UTC).isoformat(),
            details=error,
            is_error=True,
        )
        self.entries.append(entry)

    def get_progress_log(self) -> list[dict]:
        """Get all progress entries as dictionaries."""
        return [entry.to_dict() for entry in self.entries]

    def get_latest_message(self) -> str:
        """Get the latest progress message."""
        if not self.entries:
            return ""
        return self.entries[-1].message

    def format_for_display(self) -> str:
        """Format progress log for display in chat."""
        if not self.entries:
            return ""
        
        lines = ["**Research Progress:**\n"]
        
        for entry in self.entries:
            icon = "✓" if entry.is_complete else ("❌" if entry.is_error else "•")
            lines.append(f"{icon} {entry.message}")
            if entry.details and not entry.is_complete:
                lines.append(f"  _{entry.details}_")
        
        return "\n".join(lines)

    def to_render_block(self) -> dict:
        """Create a render block for the frontend."""
        return {
            "type": "research_progress",
            "payload": {
                "steps": self.get_progress_log(),
                "latest_message": self.get_latest_message(),
                "is_complete": self.entries[-1].is_complete if self.entries else False,
                "is_error": self.entries[-1].is_error if self.entries else False,
            },
        }
