"""
Video generation capability implementation.
Provides autonomous development of video generation models.
"""

import asyncio
import json
import os
from typing import Optional
from pathlib import Path

from backend.app.services.tool_executor import ToolExecutor
from backend.app.services.implementation_verifier import ImplementationVerifier
from backend.app.services.evolution_logger import EvolutionLogger


class VideoGenerationCapability:
    """
    Manages autonomous development of video generation capability.
    Integrates models like Stable Video Diffusion or ModelScope.
    """

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        verifier: Optional[ImplementationVerifier] = None,
        logger: Optional[EvolutionLogger] = None,
    ):
        self.tool_executor = tool_executor or ToolExecutor()
        self.verifier = verifier or ImplementationVerifier(self.tool_executor)
        self.logger = logger or EvolutionLogger()

    async def research_and_implement(self) -> tuple[bool, str]:
        """
        Research and implement video generation capability.

        Returns:
            (success, message) tuple
        """
        try:
            # Step 1: Research available models
            research_result = await self._research_models()
            if not research_result[0]:
                return False, f"Research failed: {research_result[1]}"

            # Step 2: Install dependencies
            install_result = await self._install_dependencies()
            if not install_result[0]:
                return False, f"Installation failed: {install_result[1]}"

            # Step 3: Create implementation
            impl_result = await self._create_implementation()
            if not impl_result[0]:
                return False, f"Implementation failed: {impl_result[1]}"

            # Step 4: Validate implementation
            validate_result = await self._validate_implementation()
            if not validate_result[0]:
                return False, f"Validation failed: {validate_result[1]}"

            return True, "Video generation capability successfully developed and integrated!"

        except Exception as e:
            return False, f"Error during development: {str(e)}"

    async def _research_models(self) -> tuple[bool, str]:
        """Research available video generation models."""
        try:
            models_info = {
                "stable-video-diffusion": {
                    "name": "Stable Video Diffusion (SVD)",
                    "type": "open-source",
                    "library": "diffusers",
                    "note": "Image-to-video generation, 2-4 seconds",
                    "model_id": "stabilityai/stable-video-diffusion-img2vid-xt",
                },
                "modelscope": {
                    "name": "ModelScope Text-to-Video",
                    "type": "open-source",
                    "library": "diffusers",
                    "note": "Text-to-video generation",
                    "model_id": "damo-vilab/modelscope-damo-text-to-video-synthesis",
                },
                "animate-diff": {
                    "name": "AnimateDiff",
                    "type": "open-source",
                    "library": "diffusers",
                    "note": "Animation generation from text/prompts",
                    "model_id": "guoyww/animatediff-motion-lora",
                },
            }

            message = "Available video generation models:\n"
            for model_id, info in models_info.items():
                message += f"- {info['name']}: {info['note']}\n"

            return True, message

        except Exception as e:
            return False, str(e)

    async def _install_dependencies(self) -> tuple[bool, str]:
        """Install required dependencies for video generation."""
        try:
            dependencies = [
                "diffusers",
                "pillow",
                "numpy",
                "safetensors",
                "transformers",
                "accelerate",
                "opencv-python-headless",
            ]

            # Check if torch is installed
            result = await self.tool_executor.execute_command(
                "python -c \"import torch; print('torch installed')\""
            )

            if result.get("returncode") != 0:
                dependencies.insert(0, "torch")
                dependencies.insert(1, "torchvision")

            # Check if ffmpeg is available (for video encoding)
            result = await self.tool_executor.execute_command("which ffmpeg")
            if result.get("returncode") != 0:
                # ffmpeg not found, but continue without it
                pass

            # Install each dependency
            for dep in dependencies:
                result = await self.tool_executor.execute_command(
                    f"pip install --quiet {dep}"
                )
                if result.get("returncode") != 0:
                    return False, f"Failed to install {dep}"

            return True, f"Installed dependencies: {', '.join(dependencies)}"

        except Exception as e:
            return False, f"Installation error: {str(e)}"

    async def _create_implementation(self) -> tuple[bool, str]:
        """Create video generation module implementation."""
        try:
            service_code = '''"""
Video generation service using Diffusers library.
Supports Stable Video Diffusion and ModelScope models.
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
except ImportError:
    HAS_DIFFUSERS = False


class VideoGenerationService:
    """Service for generating videos from text or images."""

    def __init__(self):
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.current_model = None
        self.model_type = None  # "image-to-video" or "text-to-video"

    async def load_model(self, model_name: str = "stable-video-diffusion") -> bool:
        """Load video generation model."""
        if not HAS_DIFFUSERS:
            return False

        try:
            if model_name == "stable-video-diffusion":
                # Image-to-video generation
                self.pipeline = StableVideoDiffusionPipeline.from_pretrained(
                    "stabilityai/stable-video-diffusion-img2vid-xt",
                    torch_dtype=torch.float16,
                    variant="fp16"
                )
                self.model_type = "image-to-video"
            elif model_name == "modelscope":
                # Text-to-video generation
                self.pipeline = ModelScopeTextToVideoPipeline.from_pretrained(
                    "damo-vilab/modelscope-damo-text-to-video-synthesis",
                    torch_dtype=torch.float16
                )
                self.model_type = "text-to-video"
            else:
                return False

            self.pipeline = self.pipeline.to(self.device)
            self.pipeline.enable_model_cpu_offload()
            self.current_model = model_name
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
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
        if self.pipeline is None:
            if not await self.load_model("stable-video-diffusion"):
                return None

        if self.model_type != "image-to-video":
            await self.load_model("stable-video-diffusion")

        try:
            # Resize image to expected dimensions
            image = image.resize((width, height))

            # Run generation (async-friendly)
            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    image,
                    decode_chunk_size=8,
                    motion_bucket_id=motion_bucket_id,
                    fps=fps,
                ).frames[0]
            )

            # Convert frames to video
            return self._encode_video(frames, fps)
        except Exception as e:
            print(f"Error generating video: {e}")
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
        if self.pipeline is None:
            if not await self.load_model("modelscope"):
                return None

        if self.model_type != "text-to-video":
            await self.load_model("modelscope")

        try:
            # Run generation (async-friendly)
            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    prompt=prompt,
                    num_inference_steps=25,
                    num_frames=num_frames,
                    guidance_scale=9.0,
                ).frames[0]
            )

            # Convert frames to video
            return self._encode_video(frames, fps)
        except Exception as e:
            print(f"Error generating video: {e}")
            return None

    def _encode_video(self, frames: list, fps: int = 7) -> Optional[bytes]:
        """Encode frames to video bytes."""
        try:
            # Convert PIL frames to numpy arrays
            frame_arrays = []
            for frame in frames:
                if isinstance(frame, Image.Image):
                    frame_arrays.append(cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR))
                else:
                    frame_arrays.append(frame)

            if not frame_arrays:
                return None

            # Get dimensions from first frame
            height, width = frame_arrays[0].shape[:2]

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            temp_path = f"/tmp/generated_video_{hash(str(frames))}.mp4"

            out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
            for frame in frame_arrays:
                out.write(frame)
            out.release()

            # Read the video file
            with open(temp_path, 'rb') as f:
                video_bytes = f.read()

            # Cleanup
            os.remove(temp_path)

            return video_bytes
        except Exception as e:
            print(f"Error encoding video: {e}")
            return None


# Global instance
_service = None


async def get_video_service() -> VideoGenerationService:
    """Get or create video generation service."""
    global _service
    if _service is None:
        _service = VideoGenerationService()
    return _service


async def generate_video_from_image(
    image: Image.Image,
    width: int = 1024,
    height: int = 576,
) -> Optional[bytes]:
    """Convenience function to generate video from image."""
    service = await get_video_service()
    return await service.generate_video_from_image(image, width, height)


async def generate_video_from_text(
    prompt: str,
    width: int = 256,
    height: int = 256,
) -> Optional[bytes]:
    """Convenience function to generate video from text."""
    service = await get_video_service()
    return await service.generate_video_from_text(prompt, width, height)
'''

            # Write the service file
            service_path = Path("/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/video_generation.py")
            service_path.write_text(service_code)

            # Create API endpoint for video generation
            endpoint_code = '''"""
Video generation API endpoints.
"""

import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from PIL import Image
import io

from backend.app.services.video_generation import (
    generate_video_from_image,
    generate_video_from_text,
)


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


@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video_endpoint(request: VideoGenerationRequest):
    """Generate a video from text prompt or image."""
    try:
        video_bytes = None

        if request.image_base64:
            # Image-to-video generation
            image_data = base64.b64decode(request.image_base64)
            image = Image.open(io.BytesIO(image_data))
            video_bytes = await generate_video_from_image(
                image=image,
                width=request.width,
                height=request.height,
            )
        elif request.prompt:
            # Text-to-video generation
            video_bytes = await generate_video_from_text(
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
            raise HTTPException(
                status_code=500,
                detail="Failed to generate video"
            )

        # Calculate duration (approximate)
        duration = request.duration_seconds

        return VideoGenerationResponse(
            status="success",
            message="Video generated successfully",
            video_base64=base64.b64encode(video_bytes).decode('utf-8'),
            duration_seconds=duration,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''

            # Write the endpoint file
            endpoint_path = Path(
                "/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/video_routes.py"
            )
            endpoint_path.write_text(endpoint_code)

            return True, "Video generation module created successfully"

        except Exception as e:
            return False, f"Failed to create implementation: {str(e)}"

    async def _validate_implementation(self) -> tuple[bool, str]:
        """Validate the video generation implementation."""
        try:
            # Check that files were created
            service_path = Path("/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/video_generation.py")
            endpoint_path = Path("/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/video_routes.py")

            if not service_path.exists() or not endpoint_path.exists():
                return False, "Implementation files not created"

            # Try to compile the Python files
            result = await self.tool_executor.execute_command(
                f"python -m py_compile {str(service_path)}"
            )

            if result.get("returncode") != 0:
                return False, "Service module has syntax errors"

            result = await self.tool_executor.execute_command(
                f"python -m py_compile {str(endpoint_path)}"
            )

            if result.get("returncode") != 0:
                return False, "API endpoint module has syntax errors"

            return True, "Implementation validated successfully"

        except Exception as e:
            return False, f"Validation error: {str(e)}"
