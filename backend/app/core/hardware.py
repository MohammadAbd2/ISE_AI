"""
Hardware-aware model selector for ISE AI.

Detects available system RAM and selects the best quantized model
that fits in memory without crashing the system.

Memory tiers (conservative — uses ~60% of available RAM):
  < 6 GB  available → qwen2.5:3b  (smallest safe model)
  6-10 GB available → qwen2.5:7b  or qwen2.5-coder:7b
  10-20 GB available → qwen2.5:14b or qwen2.5-coder:14b
  20-40 GB available → qwen2.5:30b or qwen3-30b-a3b (MoE)
  40+ GB  available → qwen2.5:72b or larger
"""
from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

logger = logging.getLogger(__name__)

# Model catalogue: (model_name, min_ram_gb, vram_gb_4bit, description)
_MODEL_CATALOGUE: list[tuple[str, float, float, str]] = [
    # name,                  min_ram_GB, approx_4bit_GB, desc
    ("qwen2.5:3b",           4.0,  2.0,  "3B — ultra-light, 4-bit Q4"),
    ("qwen2.5-coder:3b",     4.0,  2.0,  "3B coder — ultra-light, 4-bit Q4"),
    ("qwen2.5:7b",           6.0,  4.5,  "7B — good for general tasks"),
    ("qwen2.5-coder:7b",     6.0,  4.5,  "7B coder — excellent code quality"),
    ("qwen2.5:14b",          10.0, 8.5,  "14B — strong reasoning"),
    ("qwen2.5-coder:14b",    10.0, 8.5,  "14B coder — best code model under 20 GB"),
    ("deepseek-coder-v2",    12.0, 9.0,  "DeepSeek Coder V2 — strong MoE coder"),
    ("qwen2.5:32b",          20.0, 18.0, "32B — near GPT-4 quality"),
    ("qwen3-30b-a3b",        20.0, 16.5, "30B MoE A3B — advanced reasoning"),
    ("qwen2.5:72b",          40.0, 44.0, "72B — best open-weight general model"),
    ("qwen3:70b",            48.0, 44.0, "70B Qwen3 — highest quality"),
]

# Preferred coding models by tier
_CODING_TIER: dict[str, str] = {
    "tiny":   "qwen2.5-coder:3b",
    "small":  "qwen2.5-coder:7b",
    "medium": "qwen2.5-coder:14b",
    "large":  "qwen2.5:32b",
    "xlarge": "qwen2.5:72b",
}

_CHAT_TIER: dict[str, str] = {
    "tiny":   "qwen2.5:3b",
    "small":  "qwen2.5:7b",
    "medium": "qwen2.5:14b",
    "large":  "qwen3-30b-a3b",
    "xlarge": "qwen2.5:72b",
}


@dataclass
class HardwareProfile:
    total_ram_gb: float
    available_ram_gb: float
    cpu_count: int
    platform: str
    gpu_vram_gb: float
    tier: str           # tiny / small / medium / large / xlarge
    recommended_model: str
    coding_model: str
    chat_model: str
    context_tokens: int
    safe_ram_limit_gb: float


def _get_gpu_vram() -> float:
    """Try to detect GPU VRAM in GB. Returns 0 on failure."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            total_mb = sum(int(line.strip()) for line in result.stdout.strip().splitlines() if line.strip().isdigit())
            return total_mb / 1024
    except Exception:
        pass
    return 0.0


def _classify_tier(available_gb: float) -> str:
    if available_gb < 6:
        return "tiny"
    if available_gb < 12:
        return "small"
    if available_gb < 22:
        return "medium"
    if available_gb < 44:
        return "large"
    return "xlarge"


def _context_for_tier(tier: str) -> int:
    return {
        "tiny": 4096,
        "small": 8192,
        "medium": 16384,
        "large": 32768,
        "xlarge": 65536,
    }[tier]


@lru_cache(maxsize=1)
def detect_hardware() -> HardwareProfile:
    """Detect hardware and return the recommended model configuration."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        available_gb = mem.available / (1024 ** 3)
        cpu_count = psutil.cpu_count(logical=False) or 4
    except ImportError:
        logger.warning("psutil not installed — using conservative defaults")
        total_gb = 8.0
        available_gb = 4.0
        cpu_count = 4

    gpu_vram = _get_gpu_vram()
    # Effective headroom: use min of RAM and GPU headroom (if GPU present)
    effective_gb = available_gb * 0.65  # reserve 35% for OS + overhead
    if gpu_vram > 0:
        effective_gb = max(effective_gb, gpu_vram * 0.80)

    tier = _classify_tier(effective_gb)
    coding_model = _CODING_TIER[tier]
    chat_model = _CHAT_TIER[tier]
    context = _context_for_tier(tier)

    profile = HardwareProfile(
        total_ram_gb=round(total_gb, 1),
        available_ram_gb=round(available_gb, 1),
        cpu_count=cpu_count,
        platform=platform.system(),
        gpu_vram_gb=round(gpu_vram, 1),
        tier=tier,
        recommended_model=coding_model,
        coding_model=coding_model,
        chat_model=chat_model,
        context_tokens=context,
        safe_ram_limit_gb=round(effective_gb, 1),
    )
    logger.info(
        "Hardware profile: RAM=%.1f GB (avail=%.1f GB), GPU=%.1f GB, tier=%s, model=%s",
        total_gb, available_gb, gpu_vram, tier, coding_model,
    )
    return profile


def get_best_available_model(
    available_models: Sequence[str],
    task: str = "coding",
    user_override: str | None = None,
) -> str:
    """
    Return the best model from `available_models` for the given task,
    constrained by current hardware.
    """
    if user_override and user_override in available_models:
        return user_override

    hw = detect_hardware()
    preferred = hw.coding_model if task == "coding" else hw.chat_model

    # First try: exact match for tier-preferred model
    if preferred in available_models:
        return preferred

    # Second: find best fitting model from catalogue that fits in memory
    avail_set = set(available_models)
    for model_name, min_ram, _, _ in sorted(_MODEL_CATALOGUE, key=lambda x: -x[1]):
        if model_name in avail_set and min_ram <= hw.safe_ram_limit_gb:
            return model_name

    # Fallback: just return the first available model
    return available_models[0] if available_models else preferred
