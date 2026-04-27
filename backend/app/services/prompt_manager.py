"""
Prompt Manager - Handles dynamic prompt loading, versioning, and optimization.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Manages system prompts dynamically.
    """
    def __init__(self, prompts_dir: str = "/home/ubuntu/ISE_AI/backend/app/prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}

    def get_prompt(self, prompt_id: str, default: Optional[str] = None) -> str:
        """
        Get a prompt by ID. Loads from file if available, otherwise uses default.
        """
        if prompt_id in self._cache:
            return self._cache[prompt_id]
            
        prompt_path = self.prompts_dir / f"{prompt_id}.txt"
        if prompt_path.exists():
            try:
                content = prompt_path.read_text()
                self._cache[prompt_id] = content
                return content
            except Exception as e:
                logger.error(f"Error reading prompt {prompt_id}: {e}")
                
        return default or ""

    def save_prompt(self, prompt_id: str, content: str):
        """
        Save a prompt to disk.
        """
        prompt_path = self.prompts_dir / f"{prompt_id}.txt"
        try:
            prompt_path.write_text(content)
            self._cache[prompt_id] = content
            logger.info(f"Saved prompt {prompt_id}")
        except Exception as e:
            logger.error(f"Error saving prompt {prompt_id}: {e}")

    def list_prompts(self) -> list[str]:
        """
        List all available prompt IDs.
        """
        return [p.stem for p in self.prompts_dir.glob("*.txt")]

_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
