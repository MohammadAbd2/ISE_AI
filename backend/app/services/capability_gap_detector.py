"""
Capability gap detector — identifies when ISE AI lacks requested features
and suggests autonomous development to fill the gaps.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class CapabilityGap:
    capability_name: str
    description: str
    keywords: list[str]
    suggested_action: str
    complexity: str  # "simple" | "medium" | "complex"


class CapabilityGapDetector:
    CAPABILITY_GAPS: dict[str, CapabilityGap] = {
        "image_generation": CapabilityGap(
            capability_name="image_generation",
            description="Generate images from text descriptions",
            keywords=["generate image","draw","create image","paint","illustration",
                      "text to image","produce an image","imagine a","create a logo","draw me"],
            suggested_action=(
                "I don't have image generation yet. Would you like me to develop it?\n"
                "1. 🔍 Search Hugging Face for best model (FLUX.1)\n"
                "2. 📦 Install required packages\n3. 💻 Generate integration code\n"
                "4. ✅ Test and validate\nReply **yes** to start."
            ),
            complexity="complex",
        ),
        "video_generation": CapabilityGap(
            capability_name="video_generation",
            description="Generate videos from text or images",
            keywords=["generate video","create video","make video","text to video","video generation"],
            suggested_action="I can develop video generation via a diffusion model. Reply **yes** to begin.",
            complexity="complex",
        ),
        "web_scraping": CapabilityGap(
            capability_name="web_scraping",
            description="Scrape and parse content from web pages",
            keywords=["scrape","extract from website","parse html","web scrape","crawl website"],
            suggested_action="I can build web-scraping with BeautifulSoup/Playwright. Reply **yes**.",
            complexity="medium",
        ),
        "computer_use": CapabilityGap(
            capability_name="computer_use",
            description="Control GUIs, click buttons, interact with desktop apps",
            keywords=["click on","open the app","computer use","gui automation",
                      "desktop automation","interact with","move the mouse","take a screenshot"],
            suggested_action=(
                "I can build GUI/computer-use capability using a sandboxed desktop (Xvfb + PyAutoGUI). "
                "Reply **yes** to start autonomous development."
            ),
            complexity="complex",
        ),
        "knowledge_update": CapabilityGap(
            capability_name="knowledge_update",
            description="Research competitors, identify gaps, generate improvement plan, apply upgrades.",
            keywords=[
                "fix the gaps","fix gaps between you and","update knowledge","knowledge update",
                "compare yourself to","keep up with","match gemini","match chatgpt","match gpt",
                "match claude","match manus","improve yourself to match",
                "what can gpt do that you can't","what features are you missing",
                "upgrade yourself","close the gap","self improvement",
                "you're behind","competitors","you are behind",
            ],
            suggested_action=(
                "🧠 **Knowledge Update Workflow**\n\n"
                "I can research what GPT-5, Gemini, Claude and Manus can do that I cannot, "
                "then propose and implement improvements.\n\n"
                "**Steps:**\n"
                "1. 🔍 Research competitor features via web search\n"
                "2. 📋 Compare against my capability registry\n"
                "3. 🗺️ Generate prioritised improvement plan\n"
                "4. 🛠️ Implement in isolated sandbox\n"
                "5. 🧪 Run tests — present results for your approval\n"
                "6. ✅ Merge approved changes\n\n"
                "Reply **yes** to begin. I'll show a full plan before making any changes."
            ),
            complexity="complex",
        ),
        "hardware_model_upgrade": CapabilityGap(
            capability_name="hardware_model_upgrade",
            description="Upgrade to a larger language model",
            keywords=["use a bigger model","upgrade model","better model","use a smarter model",
                      "use a larger model","switch model","70b","72b","30b"],
            suggested_action=(
                "I can scan your hardware and recommend the best model. "
                "Check Settings → Hardware or reply **yes** to see available upgrades."
            ),
            complexity="simple",
        ),
    }

    def detect_gap(self, user_message: str) -> CapabilityGap | None:
        text = user_message.lower()
        for gap in self.CAPABILITY_GAPS.values():
            if any(kw in text for kw in gap.keywords):
                return gap
        return None

    @property
    def fs(self):
        """Expose self as fs for EvolutionAgent compatibility."""
        return self

    def detect_gaps(self, user_message: str, context: dict = None) -> list[CapabilityGap]:
        """Alias for detect_all_gaps to match agent expectations."""
        return self.detect_all_gaps(user_message)

    def detect_all_gaps(self, user_message: str) -> list[CapabilityGap]:
        text = user_message.lower()
        return [g for g in self.CAPABILITY_GAPS.values() if any(kw in text for kw in g.keywords)]

    def is_capability_gap(self, user_message: str) -> bool:
        return self.detect_gap(user_message) is not None

    def should_offer_capability_development(self, user_message: str) -> tuple[bool, CapabilityGap | None]:
        """Check if we should offer to develop a missing capability."""
        gap = self.detect_gap(user_message)
        if not gap:
            return False, None
        
        # Don't offer if it's already being developed or available
        # (This would ideally check the registry, but we'll keep it simple for now)
        return True, gap

    def generate_capability_offer(self, gap: CapabilityGap) -> str:
        """Generate a user-friendly offer to develop a capability."""
        return gap.suggested_action


# Singleton instance
_capability_gap_detector = None


def get_capability_gap_detector(capability_registry: Any = None) -> CapabilityGapDetector:
    """Get or create the capability gap detector singleton."""
    global _capability_gap_detector
    if _capability_gap_detector is None:
        _capability_gap_detector = CapabilityGapDetector()
    return _capability_gap_detector
