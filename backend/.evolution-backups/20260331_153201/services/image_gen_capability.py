"""
Image generation capability implementation.
Provides autonomous development and integration of image generation models.
"""

import asyncio
import json
import os
from typing import Optional

from backend.app.services.tool_executor import ToolExecutor
from backend.app.services.implementation_verifier import ImplementationVerifier
from backend.app.services.evolution_logger import EvolutionLogger


class ImageGenerationCapability:
    """
    Manages autonomous development of image generation capability.
    Integrates Flux or Stable Diffusion models.
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
        Research and implement image generation capability.
        
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

            return True, "Image generation capability successfully developed and integrated!"

        except Exception as e:
            return False, f"Error during development: {str(e)}"

    async def _research_models(self) -> tuple[bool, str]:
        """Research available image generation models."""
        try:
            # In real implementation, would search HuggingFace API
            # For now, document the supported models
            models_info = {
                "flux-1": {
                    "name": "Flux.1 (by Black Forest Labs)",
                    "type": "open-source",
                    "library": "diffusers",
                    "note": "High-quality, fast image generation",
                },
                "stable-diffusion-3": {
                    "name": "Stable Diffusion 3",
                    "type": "open-source",
                    "library": "diffusers",
                    "note": "Versatile image generation model",
                },
            }

            message = "Available image generation models:\n"
            for model_id, info in models_info.items():
                message += f"- {info['name']}: {info['note']}\n"

            return True, message

        except Exception as e:
            return False, str(e)

    async def _install_dependencies(self) -> tuple[bool, str]:
        """Install required dependencies for image generation."""
        try:
            dependencies = ["diffusers", "pillow", "numpy", "safetensors", "transformers"]

            # Check if torch is installed
            result = self.tool_executor.execute_command(
                "python -c \"import torch; print('torch installed')\""
            )

            if result.get("returncode") != 0:
                # PyTorch not installed, add it
                dependencies.insert(0, "torch")

            # Install each dependency
            for dep in dependencies:
                result = self.tool_executor.execute_command(
                    f"pip install --quiet {dep}"
                )
                if result.get("returncode") != 0:
                    return False, f"Failed to install {dep}"

            return True, f"Installed dependencies: {', '.join(dependencies)}"

        except Exception as e:
            return False, f"Installation error: {str(e)}"

    async def _create_implementation(self) -> tuple[bool, str]:
        """Create image generation module implementation."""
        try:
            # Create the image generation service module
            service_code = '''"""
Image generation service using Diffusers library.
Supports Flux.1 and Stable Diffusion models.
"""

import asyncio
import io
from typing import Optional
from pathlib import Path

try:
    from diffusers import FluxPipeline, StableDiffusionPipeline
    import torch
    from PIL import Image
    HAS_DIFFUSERS = True
except ImportError:
    HAS_DIFFUSERS = False


class ImageGenerationService:
    """Service for generating images from text prompts."""

    def __init__(self):
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.current_model = None

    async def load_model(self, model_name: str = "flux-1") -> bool:
        """Load image generation model."""
        if not HAS_DIFFUSERS:
            return False
        
        try:
            if model_name == "flux-1":
                # Flux.1-schnell is lighter and faster
                self.pipeline = FluxPipeline.from_pretrained(
                    "black-forest-labs/FLUX.1-schnell",
                    torch_dtype=torch.float16
                )
            else:
                # Fallback to Stable Diffusion 3
                self.pipeline = StableDiffusionPipeline.from_pretrained(
                    "stabilityai/stable-diffusion-3-medium",
                    torch_dtype=torch.float16
                )
            
            self.pipeline = self.pipeline.to(self.device)
            self.current_model = model_name
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    async def generate_image(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
    ) -> Optional[Image.Image]:
        """Generate image from text prompt."""
        if self.pipeline is None:
            if not await self.load_model():
                return None
        
        try:
            # Run generation (async-friendly)
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    prompt=prompt,
                    height=height,
                    width=width,
                    num_inference_steps=steps,
                    guidance_scale=7.5,
                ).images[0]
            )
            return image
        except Exception as e:
            print(f"Error generating image: {e}")
            return None

    async def generate_image_bytes(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
    ) -> Optional[bytes]:
        """Generate image and return as bytes."""
        image = await self.generate_image(prompt, width, height)
        if image is None:
            return None
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


# Global instance
_service = None


async def get_image_service() -> ImageGenerationService:
    """Get or create image generation service."""
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
    return await service.generate_image(prompt, width, height)
'''

            # Write the service file
            service_path = Path("/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/image_generation.py")
            service_path.write_text(service_code)

            # Create API endpoint for image generation
            endpoint_code = '''"""
Image generation API endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.image_generation import generate_image


router = APIRouter(prefix="/api/images", tags=["images"])


class ImageGenerationRequest(BaseModel):
    prompt: str
    width: int = 512
    height: int = 512


@router.post("/generate")
async def generate_image_endpoint(request: ImageGenerationRequest):
    """Generate an image from a text prompt."""
    try:
        image = await generate_image(
            prompt=request.prompt,
            width=request.width,
            height=request.height,
        )
        
        if image is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate image"
            )
        
        # Save to temporary file and return path
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        image_path = os.path.join(temp_dir, f"generated_{hash(request.prompt)}.png")
        image.save(image_path)
        
        return {
            "status": "success",
            "message": f"Image generated from prompt: {request.prompt}",
            "image_path": image_path,
            "width": image.width,
            "height": image.height,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''

            # Write the endpoint file
            endpoint_path = Path(
                "/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/image_routes.py"
            )
            endpoint_path.write_text(endpoint_code)

            return True, "Image generation module created successfully"

        except Exception as e:
            return False, f"Failed to create implementation: {str(e)}"

    async def _validate_implementation(self) -> tuple[bool, str]:
        """Validate the image generation implementation."""
        try:
            # Check that files were created
            service_path = Path("/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/services/image_generation.py")
            endpoint_path = Path("/home/baron/Desktop/Easv/Ai/ISE_AI/backend/app/api/image_routes.py")

            if not service_path.exists() or not endpoint_path.exists():
                return False, "Implementation files not created"

            # Try to compile the Python files
            result = self.tool_executor.execute_command(
                f"python -m py_compile {str(service_path)}"
            )

            if result.get("returncode") != 0:
                return False, "Service module has syntax errors"

            result = self.tool_executor.execute_command(
                f"python -m py_compile {str(endpoint_path)}"
            )

            if result.get("returncode") != 0:
                return False, "API endpoint module has syntax errors"

            return True, "Implementation validated successfully"

        except Exception as e:
            return False, f"Validation error: {str(e)}"
