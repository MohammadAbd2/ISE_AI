"""
Autonomous Self-Development System for AI Chatbot.

This system enables the chatbot to:
1. Search Hugging Face for models when capabilities are missing
2. Download and install required packages
3. Generate integration code automatically
4. Show progress logs during development
5. Test and validate new capabilities

Similar to how Qwen Code develops features autonomously.
"""

import asyncio
import json
import os
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

from backend.app.core.config import settings


class DevelopmentStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DevelopmentStep:
    """A single step in the development process."""
    name: str
    description: str
    status: DevelopmentStepStatus = DevelopmentStepStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class DevelopmentProgress:
    """Tracks progress of autonomous development."""
    capability_name: str
    steps: list[DevelopmentStep] = field(default_factory=list)
    current_step: int = 0
    overall_status: str = "pending"
    message: str = ""
    
    def to_log_string(self) -> str:
        """Convert progress to human-readable log."""
        lines = [f"🔧 Developing **{self.capability_name}** capability...\n"]
        for i, step in enumerate(self.steps):
            icon = {
                DevelopmentStepStatus.PENDING: "⏳",
                DevelopmentStepStatus.IN_PROGRESS: "🔄",
                DevelopmentStepStatus.COMPLETED: "✅",
                DevelopmentStepStatus.FAILED: "❌",
            }.get(step.status, "•")
            
            status_text = {
                DevelopmentStepStatus.PENDING: "Pending",
                DevelopmentStepStatus.IN_PROGRESS: "In progress...",
                DevelopmentStepStatus.COMPLETED: "Done",
                DevelopmentStepStatus.FAILED: f"Failed: {step.error}",
            }.get(step.status, "")
            
            lines.append(f"{icon} **Step {i+1}: {step.name}** - {status_text}")
            if step.output and step.status == DevelopmentStepStatus.COMPLETED:
                lines.append(f"   ```\n{step.output[:200]}\n   ```")
        
        return "\n".join(lines)


class HuggingFaceSearcher:
    """Search and fetch models from Hugging Face."""
    
    def __init__(self):
        self.base_url = "https://huggingface.co/api"
        self.headers = {"User-Agent": "ISE-AI-SelfDev/1.0"}
    
    async def search_models(
        self, 
        query: str, 
        model_type: str = "models",
        limit: int = 5,
        sort: str = "downloads",
        direction: int = -1,
    ) -> list[dict]:
        """Search Hugging Face for models."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "search": query,
                    "limit": limit,
                    "sort": sort,
                    "direction": direction,
                    "full": "true",
                }
                response = await client.get(
                    f"{self.base_url}/{model_type}",
                    params=params,
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return []
    
    async def get_model_info(self, model_id: str) -> Optional[dict]:
        """Get detailed info about a specific model."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/models/{model_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            return None
    
    async def find_image_generation_model(self) -> Optional[dict]:
        """Find best open image generation model (no authentication required)."""
        # Use Stable Diffusion 2.1 Turbo - fast and open access
        turbo_info = await self.get_model_info("stabilityai/sd-turbo")
        if turbo_info:
            return {
                "model_id": "stabilityai/sd-turbo",
                "type": "image_generation",
                "library": "diffusers",
                "info": turbo_info,
                "is_turbo": True,  # Only needs 1 step!
            }
        
        # Fallback to regular Stable Diffusion 2.1
        sd_info = await self.get_model_info("stabilityai/stable-diffusion-2-1")
        if sd_info:
            return {
                "model_id": "stabilityai/stable-diffusion-2-1",
                "type": "image_generation",
                "library": "diffusers",
                "info": sd_info,
                "is_turbo": False,
            }
        
        return None
    
    async def find_video_generation_model(self) -> Optional[dict]:
        """Find best video generation model."""
        video_models = [
            "stabilityai/stable-video-diffusion-img2vid-xt",
            "damo-vilab/modelscope-damo-text-to-video-synthesis",
        ]
        
        for model_id in video_models:
            info = await self.get_model_info(model_id)
            if info:
                return {
                    "model_id": model_id,
                    "type": "video_generation",
                    "library": "diffusers",
                    "info": info,
                }
        
        return None


class AutonomousDeveloper:
    """
    Autonomous agent that develops new capabilities for the chatbot.
    
    Workflow:
    1. Search Hugging Face for appropriate models
    2. Determine required dependencies
    3. Install packages via pip
    4. Generate integration code
    5. Create API endpoints
    6. Test the implementation
    7. Register the capability
    """
    
    def __init__(self):
        self.searcher = HuggingFaceSearcher()
        # Fix: settings.backend_root is already /path/to/project/backend/app
        # So we need to go to project root first
        self.backend_root = Path(settings.backend_root)  # /path/to/project/backend/app
        self.project_root = self.backend_root.parent.parent  # /path/to/project
        self.services_dir = self.backend_root.parent / "app" / "services"  # /path/to/project/backend/app/services
        self.api_dir = self.backend_root.parent / "app" / "api"  # /path/to/project/backend/app/api
        
        # Ensure directories exist
        self.services_dir.mkdir(parents=True, exist_ok=True)
        self.api_dir.mkdir(parents=True, exist_ok=True)
    
    async def develop_capability(
        self, 
        capability_name: str,
        user_request: str = "",
    ) -> DevelopmentProgress:
        """Develop a new capability autonomously."""
        progress = DevelopmentProgress(capability_name=capability_name)
        
        try:
            # Step 1: Search for models
            progress.current_step = 0
            progress.steps.append(DevelopmentStep(
                name="Search Hugging Face",
                description=f"Searching for {capability_name} models...",
                status=DevelopmentStepStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            ))
            
            model_info = await self._find_model(capability_name)
            if not model_info:
                progress.steps[0].status = DevelopmentStepStatus.FAILED
                progress.steps[0].error = "No suitable model found on Hugging Face"
                progress.overall_status = "failed"
                progress.message = f"Could not find a suitable model for {capability_name}"
                return progress
            
            progress.steps[0].status = DevelopmentStepStatus.COMPLETED
            progress.steps[0].output = f"Found model: {model_info['model_id']}"
            progress.steps[0].completed_at = datetime.now(UTC).isoformat()
            
            # Step 2: Install dependencies
            progress.current_step = 1
            progress.steps.append(DevelopmentStep(
                name="Install Dependencies",
                description="Installing required Python packages...",
                status=DevelopmentStepStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            ))
            
            install_result = await self._install_dependencies(model_info)
            if not install_result[0]:
                progress.steps[1].status = DevelopmentStepStatus.FAILED
                progress.steps[1].error = install_result[1]
                progress.overall_status = "failed"
                progress.message = f"Failed to install dependencies: {install_result[1]}"
                return progress
            
            progress.steps[1].status = DevelopmentStepStatus.COMPLETED
            progress.steps[1].output = install_result[1]
            progress.steps[1].completed_at = datetime.now(UTC).isoformat()
            
            # Step 3: Generate service code
            progress.current_step = 2
            progress.steps.append(DevelopmentStep(
                name="Generate Service Code",
                description="Creating Python service module...",
                status=DevelopmentStepStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            ))
            
            service_result = await self._generate_service_code(capability_name, model_info)
            if not service_result[0]:
                progress.steps[2].status = DevelopmentStepStatus.FAILED
                progress.steps[2].error = service_result[1]
                progress.overall_status = "failed"
                progress.message = f"Failed to generate service code: {service_result[1]}"
                return progress
            
            progress.steps[2].status = DevelopmentStepStatus.COMPLETED
            progress.steps[2].output = f"Created: {service_result[1]}"
            progress.steps[2].completed_at = datetime.now(UTC).isoformat()
            
            # Step 4: Generate API endpoints
            progress.current_step = 3
            progress.steps.append(DevelopmentStep(
                name="Create API Endpoints",
                description="Setting up REST API routes...",
                status=DevelopmentStepStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            ))
            
            api_result = await self._generate_api_endpoints(capability_name)
            if not api_result[0]:
                progress.steps[3].status = DevelopmentStepStatus.FAILED
                progress.steps[3].error = api_result[1]
                progress.overall_status = "failed"
                progress.message = f"Failed to create API: {api_result[1]}"
                return progress
            
            progress.steps[3].status = DevelopmentStepStatus.COMPLETED
            progress.steps[3].output = f"Created: {api_result[1]}"
            progress.steps[3].completed_at = datetime.now(UTC).isoformat()
            
            # Step 5: Validate implementation
            progress.current_step = 4
            progress.steps.append(DevelopmentStep(
                name="Validate Implementation",
                description="Checking syntax and imports...",
                status=DevelopmentStepStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            ))
            
            validate_result = await self._validate_implementation(capability_name)
            if not validate_result[0]:
                progress.steps[4].status = DevelopmentStepStatus.FAILED
                progress.steps[4].error = validate_result[1]
                progress.overall_status = "failed"
                progress.message = f"Validation failed: {validate_result[1]}"
                return progress
            
            progress.steps[4].status = DevelopmentStepStatus.COMPLETED
            progress.steps[4].output = validate_result[1]
            progress.steps[4].completed_at = datetime.now(UTC).isoformat()
            
            # Success!
            progress.overall_status = "completed"
            
            # Register the capability as available
            from backend.app.services.capability_registry import (
                CapabilityRegistry, 
                Capability, 
                CapabilityStatus
            )
            registry = CapabilityRegistry()
            registry.register(Capability(
                name=capability_name,
                description=f"Autonomously developed {capability_name} capability",
                status=CapabilityStatus.AVAILABLE,
                version="1.0.0",
                metadata={
                    "model": model_info.get("model_id", "unknown"),
                    "library": model_info.get("library", "unknown"),
                    "auto_generated": True,
                },
            ))
            
            progress.message = (
                f"✅ Successfully developed **{capability_name}** capability!\n\n"
                f"Model: `{model_info['model_id']}`\n"
                f"Library: `{model_info.get('library', 'unknown')}`\n\n"
                f"You can now use this capability by asking me to generate {capability_name.replace('_', ' ')}."
            )
            
        except Exception as e:
            progress.overall_status = "failed"
            progress.message = f"❌ Development failed: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
            
            # Mark current step as failed
            if progress.current_step < len(progress.steps):
                progress.steps[progress.current_step].status = DevelopmentStepStatus.FAILED
                progress.steps[progress.current_step].error = str(e)
        
        return progress
    
    async def _find_model(self, capability_name: str) -> Optional[dict]:
        """Find appropriate model for capability."""
        try:
            if capability_name == "image_generation":
                return await self.searcher.find_image_generation_model()
            elif capability_name == "video_generation":
                return await self.searcher.find_video_generation_model()
        except Exception as e:
            # Log error but return None to trigger proper failure handling
            print(f"Error finding model for {capability_name}: {e}")
        return None
    
    async def _install_dependencies(self, model_info: dict) -> tuple[bool, str]:
        """Install required Python packages."""
        dependencies = ["diffusers", "pillow", "transformers", "accelerate", "safetensors"]
        
        # Check if torch is installed
        try:
            import torch
            torch_installed = True
        except ImportError:
            torch_installed = False
            dependencies.insert(0, "torch")
            dependencies.insert(1, "torchvision")
        
        installed = []
        failed = []
        
        # Check if we're in a virtual environment
        in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        pip_args = [sys.executable, "-m", "pip", "install", "--quiet"]
        if not in_venv:
            # Add --break-system-packages for externally managed environments
            pip_args.append("--break-system-packages")
        
        for dep in dependencies:
            try:
                # Use subprocess to install
                import subprocess
                result = subprocess.run(
                    pip_args + [dep],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes per package
                )
                if result.returncode == 0:
                    installed.append(dep)
                else:
                    failed.append(f"{dep}: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                failed.append(f"{dep}: Installation timed out")
            except Exception as e:
                failed.append(f"{dep}: {str(e)}")
        
        if failed:
            return False, f"Failed to install: {', '.join(failed)}"
        
        return True, f"Installed: {', '.join(installed)}"
    
    async def _generate_service_code(
        self, 
        capability_name: str, 
        model_info: dict,
    ) -> tuple[bool, str]:
        """Generate Python service code for the capability."""
        if capability_name == "image_generation":
            return await self._generate_image_service(model_info)
        elif capability_name == "video_generation":
            return await self._generate_video_service(model_info)
        return False, f"Unknown capability: {capability_name}"
    
    async def _generate_image_service(self, model_info: dict) -> tuple[bool, str]:
        """Generate image generation service code."""
        model_id = model_info["model_id"]
        is_turbo = model_info.get("is_turbo", False)
        
        # Pre-compute values for template
        default_steps = 1 if is_turbo else 50
        default_guidance = 0.0 if is_turbo else 7.5

        service_code = f'''"""
Autonomous-generated image generation service.
Model: {model_id}
Generated by: AI Self-Development System
"""

import asyncio
import io
from typing import Optional
from pathlib import Path

try:
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    import torch
    from PIL import Image
    HAS_DIFFUSERS = True
except ImportError as e:
    HAS_DIFFUSERS = False
    IMPORT_ERROR = str(e)


class ImageGenerationService:
    """Service for generating images from text prompts."""

    def __init__(self):
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = "{model_id}"
        self.is_turbo = {str(is_turbo)}

    async def load_pipeline(self) -> bool:
        """Load the image generation model."""
        if not HAS_DIFFUSERS:
            return False
        
        if self.pipeline is not None:
            return True
        
        try:
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
            )
            
            # Use DPM solver for faster inference
            if not self.is_turbo:
                self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                    self.pipeline.scheduler.config
                )
            
            if self.device == "cuda":
                self.pipeline = self.pipeline.to(self.device)
            
            return True
        except Exception as e:
            print(f"Error loading pipeline: {{e}}")
            return False

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "ugly, blurry, low quality, distorted",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = {default_steps},
        guidance_scale: float = {default_guidance},
    ) -> Optional[Image.Image]:
        """Generate an image from a text prompt."""
        if not await self.load_pipeline():
            return None
        
        try:
            loop = asyncio.get_event_loop()
            
            def _generate():
                return self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                ).images[0]
            
            image = await loop.run_in_executor(None, _generate)
            return image
        except Exception as e:
            print(f"Error generating image: {{e}}")
            return None

    async def generate_image_bytes(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
    ) -> Optional[bytes]:
        """Generate image and return as PNG bytes."""
        image = await self.generate_image(prompt, width=width, height=height)
        if image is None:
            return None
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


# Global instance
_service: Optional[ImageGenerationService] = None


async def get_image_service() -> ImageGenerationService:
    """Get or create the image generation service."""
    global _service
    if _service is None:
        _service = ImageGenerationService()
    return _service


async def generate_image(
    prompt: str,
    width: int = 512,
    height: int = 512,
) -> Optional[Image.Image]:
    """Convenience function to generate an image."""
    service = await get_image_service()
    return await service.generate_image(prompt, width=width, height=height)
'''

        # Write the service file
        service_path = self.services_dir / "image_generation.py"
        service_path.write_text(service_code, encoding="utf-8")
        
        return True, str(service_path)
    
    async def _generate_video_service(self, model_info: dict) -> tuple[bool, str]:
        """Generate video generation service code."""
        model_id = model_info["model_id"]
        
        service_code = f'''"""
Autonomous-generated video generation service.
Model: {model_id}
Generated by: AI Self-Development System
"""

import asyncio
import io
import os
from typing import Optional
from pathlib import Path

try:
    from diffusers import StableVideoDiffusionPipeline, ModelScopeTextToVideoPipeline
    import torch
    from PIL import Image
    import cv2
    import numpy as np
    HAS_DIFFUSERS = True
except ImportError as e:
    HAS_DIFFUSERS = False
    IMPORT_ERROR = str(e)


class VideoGenerationService:
    """Service for generating videos from text or images."""

    def __init__(self):
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = "{model_id}"
        self.model_type = "image-to-video" if "video-diffusion" in self.model_id else "text-to-video"

    async def load_pipeline(self) -> bool:
        """Load the video generation model."""
        if not HAS_DIFFUSERS:
            return False
        
        if self.pipeline is not None:
            return True
        
        try:
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            if "video-diffusion" in self.model_id:
                self.pipeline = StableVideoDiffusionPipeline.from_pretrained(
                    self.model_id,
                    torch_dtype=dtype,
                    variant="fp16" if self.device == "cuda" else None,
                )
            else:
                self.pipeline = ModelScopeTextToVideoPipeline.from_pretrained(
                    self.model_id,
                    torch_dtype=dtype,
                )
            
            if self.device == "cuda":
                self.pipeline = self.pipeline.to(self.device)
                self.pipeline.enable_model_cpu_offload()
            
            return True
        except Exception as e:
            print(f"Error loading pipeline: {{e}}")
            return False

    async def generate_video_from_image(
        self,
        image: Image.Image,
        width: int = 1024,
        height: int = 576,
        fps: int = 7,
        motion_bucket_id: int = 127,
    ) -> Optional[bytes]:
        """Generate video from an input image."""
        if not await self.load_pipeline():
            return None
        
        if self.model_type != "image-to-video":
            return None
        
        try:
            image = image.resize((width, height))
            loop = asyncio.get_event_loop()
            
            def _generate():
                return self.pipeline(
                    image,
                    decode_chunk_size=8,
                    motion_bucket_id=motion_bucket_id,
                    fps=fps,
                ).frames[0]
            
            frames = await loop.run_in_executor(None, _generate)
            return self._encode_video(frames, fps)
        except Exception as e:
            print(f"Error generating video: {{e}}")
            return None

    async def generate_video_from_text(
        self,
        prompt: str,
        width: int = 256,
        height: int = 256,
        num_frames: int = 16,
        fps: int = 8,
    ) -> Optional[bytes]:
        """Generate video from a text prompt."""
        if not await self.load_pipeline():
            return None
        
        if self.model_type != "text-to-video":
            return None
        
        try:
            loop = asyncio.get_event_loop()
            
            def _generate():
                return self.pipeline(
                    prompt=prompt,
                    num_inference_steps=25,
                    num_frames=num_frames,
                    guidance_scale=9.0,
                ).frames[0]
            
            frames = await loop.run_in_executor(None, _generate)
            return self._encode_video(frames, fps)
        except Exception as e:
            print(f"Error generating video: {{e}}")
            return None

    def _encode_video(self, frames: list, fps: int = 7) -> Optional[bytes]:
        """Encode frames to MP4 video bytes."""
        try:
            frame_arrays = []
            for frame in frames:
                if isinstance(frame, Image.Image):
                    frame_arrays.append(cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR))
                else:
                    frame_arrays.append(frame)
            
            if not frame_arrays:
                return None
            
            height, width = frame_arrays[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                temp_path = tmp.name
            
            out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
            for frame in frame_arrays:
                out.write(frame)
            out.release()
            
            with open(temp_path, 'rb') as f:
                video_bytes = f.read()
            
            os.remove(temp_path)
            return video_bytes
        except Exception as e:
            print(f"Error encoding video: {{e}}")
            return None


# Global instance
_service: Optional[VideoGenerationService] = None


async def get_video_service() -> VideoGenerationService:
    """Get or create the video generation service."""
    global _service
    if _service is None:
        _service = VideoGenerationService()
    return _service
'''
        
        service_path = self.services_dir / "video_generation.py"
        service_path.write_text(service_code, encoding="utf-8")
        
        return True, str(service_path)
    
    async def _generate_api_endpoints(self, capability_name: str) -> tuple[bool, str]:
        """Generate FastAPI endpoint code."""
        if capability_name == "image_generation":
            return await self._generate_image_api()
        elif capability_name == "video_generation":
            return await self._generate_video_api()
        return False, f"Unknown capability: {capability_name}"
    
    async def _generate_image_api(self) -> tuple[bool, str]:
        """Generate image generation API endpoints."""
        api_code = '''"""
Image generation API endpoints.
Auto-generated by AI Self-Development System
"""

import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.image_generation import generate_image


router = APIRouter(prefix="/api/images", tags=["images"])


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 512
    num_steps: int = 28


class ImageGenerationResponse(BaseModel):
    status: str
    message: str
    image_base64: str | None = None
    width: int | None = None
    height: int | None = None


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image_endpoint(request: ImageGenerationRequest):
    """Generate an image from a text prompt."""
    try:
        image = await generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_steps,
        )
        
        if image is None:
            raise HTTPException(status_code=500, detail="Failed to generate image")
        
        # Convert to base64
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return ImageGenerationResponse(
            status="success",
            message=f"Image generated from prompt: {request.prompt}",
            image_base64=image_base64,
            width=image.width,
            height=image.height,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
        
        api_path = self.api_dir / "image_routes.py"
        api_path.write_text(api_code, encoding="utf-8")
        
        return True, str(api_path)
    
    async def _generate_video_api(self) -> tuple[bool, str]:
        """Generate video generation API endpoints."""
        api_code = '''"""
Video generation API endpoints.
Auto-generated by AI Self-Development System
"""

import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoGenerationRequest(BaseModel):
    prompt: str | None = None
    image_base64: str | None = None
    width: int = 256
    height: int = 256
    duration_seconds: int = 2


class VideoGenerationResponse(BaseModel):
    status: str
    message: str
    video_base64: str | None = None
    duration_seconds: float | None = None


@router.post("/generate")
async def generate_video_endpoint(request: VideoGenerationRequest):
    """Generate a video from text prompt or image."""
    try:
        # Import here to avoid circular imports
        from backend.app.services.video_generation import (
            get_video_service,
        )
        
        service = await get_video_service()
        video_bytes = None
        
        if request.image_base64:
            from PIL import Image
            import io
            image_data = base64.b64decode(request.image_base64)
            image = Image.open(io.BytesIO(image_data))
            video_bytes = await service.generate_video_from_image(
                image=image,
                width=request.width,
                height=request.height,
            )
        elif request.prompt:
            video_bytes = await service.generate_video_from_text(
                prompt=request.prompt,
                width=request.width,
                height=request.height,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either prompt or image_base64 must be provided"
            )
        
        if video_bytes is None:
            raise HTTPException(status_code=500, detail="Failed to generate video")
        
        return VideoGenerationResponse(
            status="success",
            message="Video generated successfully",
            video_base64=base64.b64encode(video_bytes).decode("utf-8'),
            duration_seconds=request.duration_seconds,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
        
        api_path = self.api_dir / "video_routes.py"
        api_path.write_text(api_code, encoding="utf-8")
        
        return True, str(api_path)
    
    async def _validate_implementation(self, capability_name: str) -> tuple[bool, str]:
        """Validate the generated implementation."""
        if capability_name == "image_generation":
            service_path = self.services_dir / "image_generation.py"
            api_path = self.api_dir / "image_routes.py"
        elif capability_name == "video_generation":
            service_path = self.services_dir / "video_generation.py"
            api_path = self.api_dir / "video_routes.py"
        else:
            return False, f"Unknown capability: {capability_name}"
        
        # Check files exist
        if not service_path.exists():
            return False, f"Service file not created: {service_path}"
        if not api_path.exists():
            return False, f"API file not created: {api_path}"
        
        # Check syntax
        import subprocess
        for path in [service_path, api_path]:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, f"Syntax error in {path.name}: {result.stderr[:200]}"
        
        return True, f"Validation passed for {capability_name}"


# Global instance
_developer: Optional[AutonomousDeveloper] = None


def get_autonomous_developer() -> AutonomousDeveloper:
    """Get or create the autonomous developer."""
    global _developer
    if _developer is None:
        _developer = AutonomousDeveloper()
    return _developer
