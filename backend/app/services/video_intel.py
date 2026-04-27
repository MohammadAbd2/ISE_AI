"""Video generation and understanding services."""

from __future__ import annotations

import base64
import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import Optional

from app.schemas.chat import ChatAttachment


class VideoGenService:
    """Service for handling video generation requests."""

    def __init__(self):
        self._service = None

    def should_generate_video(self, user_message: str) -> bool:
        """Check if the user is requesting video generation."""
        lower = user_message.lower()
        
        # Direct video generation requests
        video_keywords = [
            "generate video",
            "create video", 
            "make a video",
            "produce video",
            "text to video",
            "generate a video",
            "create a video",
            "make video",
            "animation",
        ]
        
        if any(keyword in lower for keyword in video_keywords):
            return True
        
        # Pattern: "generate/create/make X second video"
        duration_pattern = r"(generate|create|make)\s+(a\s+)?(\d+\s*(second|sec|s)?\s*)?video"
        if re.search(duration_pattern, lower):
            return True
        
        # Pattern: "video containing" or "video of" or "X second video"
        if re.search(r"video\s+(containing|of|with)\s+", lower):
            return True
        if re.search(r"\d+\s*(second|sec|s)\s+video", lower):
            return True
            
        return False

    def extract_video_parameters(self, user_message: str) -> dict:
        """Extract video generation parameters from user message."""
        lower = user_message.lower()
        
        # Extract duration
        duration = 3  # default
        duration_match = re.search(r"(\d+)\s*(second|sec|s)?\s*video", lower)
        if duration_match:
            duration = int(duration_match.group(1))
        
        # Extract prompt/content
        prompt = user_message
        prompt_patterns = [
            r"video\s+(?:containing|of|with)\s+(.+?)(?:\.|!|$)",
            r"generate\s+(?:a\s+)?(\d+\s*second\s+)?video\s+(?:of|containing|with)?\s*(.+?)(?:\.|!|$)",
            r"create\s+(?:a\s+)?(\d+\s*second\s+)?video\s+(?:of|containing|with)?\s*(.+?)(?:\.|!|$)",
        ]
        
        for pattern in prompt_patterns:
            match = re.search(pattern, lower)
            if match:
                # Get the last non-None group
                groups = [g for g in match.groups() if g]
                if groups:
                    prompt = groups[-1].strip()
                    break
        
        # Clean up prompt
        prompt = re.sub(r"^\s*(for\s+me|please|can\s+you)\s*", "", prompt)
        prompt = prompt.strip()
        
        return {
            "prompt": prompt,
            "duration_seconds": duration,
            "width": 256,  # default
            "height": 256,  # default
        }

    def get_unavailable_message(self) -> str:
        """Return message when video generation is not available."""
        return (
            "Video generation requires special models to be installed. "
            "Would you like me to develop video generation capability? "
            "I can integrate models like Stable Video Diffusion or ModelScope."
        )

    def format_video_response(self, video_base64: str, prompt: str, duration: float) -> str:
        """Format a video generation response."""
        # Create HTML5 video embed
        video_html = f'<video controls width="320"><source src="data:video/mp4;base64,{video_base64}" type="video/mp4">Your browser does not support the video tag.</video>'
        
        return (
            f"✅ Generated video from prompt: **{prompt}**\n\n"
            f"Duration: {duration} seconds\n\n"
            f"{video_html}\n\n"
            f"![video_thumbnail](data:video/mp4;base64,{video_base64[:1000]}...)"
        )


@lru_cache
def get_video_gen_service() -> VideoGenService:
    """Get or create video generation service."""
    return VideoGenService()
