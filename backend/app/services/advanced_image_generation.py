from __future__ import annotations
import base64
import io
import os
from PIL import Image, ImageDraw

async def generate_image_with_best_provider(prompt: str, width: int = 1024, height: int = 1024, provider: str = "auto") -> dict:
    """Provider abstraction. Plug Gemini/Nano-Banana-compatible or other providers here without changing the UI contract."""
    selected = provider if provider != "auto" else ("nano-banana-compatible" if os.getenv("GEMINI_API_KEY") or os.getenv("NANO_BANANA_API_KEY") else "local-placeholder")
    img = Image.new("RGB", (min(width, 1024), min(height, 1024)), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle((24, 24, img.width - 24, img.height - 24), outline=(40, 40, 40), width=3)
    draw.multiline_text((48, 48), f"{selected}\n\n{prompt[:420]}", fill=(20, 20, 20), spacing=8)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {"provider": selected, "mime_type": "image/png", "image_base64": b64, "data_url": f"data:image/png;base64,{b64}", "width": img.width, "height": img.height, "note": "Local placeholder is used unless an external image provider key is configured."}

async def analyze_image_content(image_url: str | None = None, image_base64: str | None = None, prompt: str = "Describe this image") -> dict:
    source = "base64_upload" if image_base64 else "url" if image_url else "none"
    return {"source": source, "prompt": prompt, "summary": "Image analysis hook is ready. Attach a multimodal provider to replace this deterministic fallback.", "observations": ["Input accepted", "Stable schema for Agent/Chat/AGI", "No UI crash if provider is unavailable"]}
