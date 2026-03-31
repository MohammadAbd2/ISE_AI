"""
Capability gap detector for identifying when the AI lacks requested features.
Analyzes user messages and suggests capability development.
"""

from dataclasses import dataclass
from typing import Optional

from backend.app.services.capability_registry import CapabilityRegistry


@dataclass
class CapabilityGap:
    """Represents a missing capability."""

    capability_name: str
    description: str
    keywords: list[str]
    suggested_action: str
    complexity: str  # "simple", "medium", "complex"


class CapabilityGapDetector:
    """
    Analyzes user requests to identify missing capabilities.
    Suggests that the AI develop missing features.
    """

    # Known capability gaps and how to detect them
    CAPABILITY_GAPS = {
        "image_generation": CapabilityGap(
            capability_name="image_generation",
            description="Generate images from text descriptions",
            keywords=[
                "generate image",
                "draw",
                "create image",
                "paint",
                "illustration",
                "visual",
                "picture",
                "create a logo",
                "make a logo",
                "design a logo",
                "draw me",
                "text to image",
                "produce an image",
                "imagine a",
            ],
            suggested_action="I don't have image generation capability yet. Would you like me to develop it? I can integrate Flux or Stable Diffusion models.",
            complexity="complex",
        ),
        "web_scraping": CapabilityGap(
            capability_name="web_scraping",
            description="Scrape content from web pages",
            keywords=[
                "scrape",
                "extract from website",
                "parse html",
                "web scrape",
            ],
            suggested_action="I don't have web scraping capability. Would you like me to develop it? I can integrate beautifulsoup or selenium.",
            complexity="medium",
        ),
        "video_generation": CapabilityGap(
            capability_name="video_generation",
            description="Generate videos from text or images",
            keywords=[
                "generate video",
                "create video",
                "animation",
                "video synthesis",
                "make a video",
                "produce video",
                "text to video",
            ],
            suggested_action="I don't have video generation capability yet. This requires installing video generation models like Stable Video Diffusion. Would you like me to develop it?",
            complexity="complex",
        ),
        "audio_generation": CapabilityGap(
            capability_name="audio_generation",
            description="Generate audio or speech from text",
            keywords=[
                "generate audio",
                "text to speech",
                "tts",
                "voice generation",
                "speech synthesis",
            ],
            suggested_action="I don't have audio generation capability. Would you like me to develop it?",
            complexity="medium",
        ),
        "code_execution": CapabilityGap(
            capability_name="code_execution",
            description="Execute arbitrary Python code and return results",
            keywords=[
                "execute code",
                "run python",
                "eval",
                "run this code",
            ],
            suggested_action="I can't safely execute arbitrary code. However, I can develop a sandboxed code execution environment. Would you like that?",
            complexity="complex",
        ),
        "pdf_generation": CapabilityGap(
            capability_name="pdf_generation",
            description="Generate PDF documents",
            keywords=[
                "generate pdf",
                "create pdf",
                "export to pdf",
                "pdf report",
            ],
            suggested_action="I don't have PDF generation capability. Would you like me to develop it?",
            complexity="simple",
        ),
        "database_connection": CapabilityGap(
            capability_name="database_connection",
            description="Connect to and query databases",
            keywords=[
                "connect database",
                "query database",
                "sql query",
                "database",
            ],
            suggested_action="I don't have database connection capability. Would you like me to develop it?",
            complexity="complex",
        ),
    }

    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CapabilityRegistry()

    def detect_gaps(self, user_message: str) -> list[CapabilityGap]:
        """
        Detect missing capabilities from user message.
        
        Args:
            user_message: The user's request
        
        Returns:
            List of detected capability gaps
        """
        gaps = []
        message_lower = user_message.lower()

        for gap_name, gap_info in self.CAPABILITY_GAPS.items():
            # Skip if capability already exists
            if self.registry.has_capability(gap_name):
                continue

            # Check if any keywords match (with flexibility for word spacing)
            matched = False
            for keyword in gap_info.keywords:
                # Try exact match first
                if keyword in message_lower:
                    matched = True
                    break
                # Try matching all words in the keyword (flexible word spacing)
                words = keyword.split()
                if len(words) > 1 and all(word in message_lower for word in words):
                    matched = True
                    break
            
            if matched:
                gaps.append(gap_info)

        return gaps

    def should_offer_capability_development(
        self, user_message: str
    ) -> tuple[bool, Optional[CapabilityGap]]:
        """
        Determine if AI should offer to develop a capability.
        
        Args:
            user_message: The user's request
        
        Returns:
            (should_offer, gap) tuple
        """
        gaps = self.detect_gaps(user_message)
        if gaps:
            # Return the first (most relevant) gap
            return True, gaps[0]
        return False, None

    def generate_capability_offer(self, gap: CapabilityGap) -> str:
        """
        Generate a user-friendly offer to develop a capability.
        
        Args:
            gap: The capability gap
        
        Returns:
            Message to present to user
        """
        return gap.suggested_action

    def register_gap(self, gap: CapabilityGap) -> None:
        """Register a new capability gap."""
        self.CAPABILITY_GAPS[gap.capability_name] = gap

    def check_capability(self, capability_name: str) -> Optional[CapabilityGap]:
        """Get gap info for a specific capability."""
        return self.CAPABILITY_GAPS.get(capability_name)


def get_capability_gap_detector(
    registry: Optional[CapabilityRegistry] = None,
) -> CapabilityGapDetector:
    """Dependency for FastAPI endpoints."""
    return CapabilityGapDetector(registry)
