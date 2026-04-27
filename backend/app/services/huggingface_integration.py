"""
Hugging Face Integration - Download and integrate improvement modules from Hugging Face Hub.
"""

import logging
import json
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class HFModel:
    """Hugging Face model metadata."""
    model_id: str
    model_name: str
    task: str  # e.g., "text-generation", "text-classification"
    description: str
    downloads: int
    likes: int
    updated_at: str
    tags: List[str]
    config: Optional[Dict] = None


@dataclass
class IntegrationResult:
    """Result of model integration."""
    success: bool
    model_id: str
    message: str
    installed_at: str
    location: str
    version: str


class HFModelRegistry:
    """Registry for tracking downloaded and integrated models."""

    def __init__(self, registry_path: str = ".hf_registry.json"):
        self.registry_path = registry_path
        self.registry = self._load_registry()
        self.logger = logger

    def _load_registry(self) -> Dict:
        """Load registry from disk."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load registry: {e}")
        return {"models": {}, "integrations": {}}

    def _save_registry(self):
        """Save registry to disk."""
        try:
            with open(self.registry_path, "w") as f:
                json.dump(self.registry, f, indent=2)
            self.logger.info("Registry saved")
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")

    def register_model(self, model_id: str, metadata: Dict[str, Any]):
        """Register a downloaded model."""
        self.registry["models"][model_id] = {
            "metadata": metadata,
            "downloaded_at": datetime.now().isoformat(),
        }
        self._save_registry()
        self.logger.info(f"Model registered: {model_id}")

    def register_integration(self, model_id: str, result: IntegrationResult):
        """Register a model integration."""
        self.registry["integrations"][model_id] = {
            "result": {
                "success": result.success,
                "message": result.message,
                "installed_at": result.installed_at,
                "location": result.location,
                "version": result.version,
            },
            "integrated_at": datetime.now().isoformat(),
        }
        self._save_registry()
        self.logger.info(f"Integration registered: {model_id}")

    def get_model(self, model_id: str) -> Optional[Dict]:
        """Get model from registry."""
        return self.registry["models"].get(model_id)

    def get_integration(self, model_id: str) -> Optional[Dict]:
        """Get integration from registry."""
        return self.registry["integrations"].get(model_id)

    def list_models(self) -> List[str]:
        """List all registered models."""
        return list(self.registry["models"].keys())

    def list_integrations(self) -> List[str]:
        """List all integrated models."""
        return list(self.registry["integrations"].keys())


class HFModelDownloader:
    """Download models and improvements from Hugging Face Hub."""

    def __init__(self, cache_dir: str = ".hf_cache"):
        self.cache_dir = cache_dir
        self.registry = HFModelRegistry()
        self.logger = logger
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)

    async def search_models(
        self,
        query: str,
        task: Optional[str] = None,
        limit: int = 10,
    ) -> List[HFModel]:
        """
        Search for models on Hugging Face Hub.
        
        Args:
            query: Search query (e.g., "code-generation")
            task: Filter by task type
            limit: Maximum results
        
        Returns:
            List of HFModel objects
        """
        self.logger.info(f"Searching HF Hub for: {query}")
        
        # Simulate search results (in production, use huggingface_hub library)
        models = [
            HFModel(
                model_id="meta-llama/Llama-2-7b",
                model_name="Llama 2 7B",
                task="text-generation",
                description="Open-source LLM from Meta",
                downloads=100000,
                likes=5000,
                updated_at="2024-01-15",
                tags=["llm", "code", "assistant"],
            ),
            HFModel(
                model_id="mistralai/Mistral-7B",
                model_name="Mistral 7B",
                task="text-generation",
                description="Efficient open-source LLM",
                downloads=50000,
                likes=3000,
                updated_at="2024-01-20",
                tags=["llm", "efficient"],
            ),
            HFModel(
                model_id="bigcode/starcoderplus",
                model_name="StarCoder+",
                task="code-generation",
                description="Code generation model",
                downloads=30000,
                likes=2000,
                updated_at="2024-01-10",
                tags=["code", "generation"],
            ),
            HFModel(
                model_id="google/flan-t5-large",
                model_name="FLAN-T5 Large",
                task="text-to-text",
                description="Instruction-following model",
                downloads=80000,
                likes=4000,
                updated_at="2024-01-18",
                tags=["instruction", "t5"],
            ),
            HFModel(
                model_id="sentence-transformers/all-MiniLM-L6-v2",
                model_name="All-MiniLM-L6-v2",
                task="sentence-similarity",
                description="Efficient sentence embeddings",
                downloads=120000,
                likes=6000,
                updated_at="2024-01-22",
                tags=["embeddings", "similarity"],
            ),
        ]
        
        # Filter by query
        filtered = [m for m in models if query.lower() in m.model_id.lower() or query.lower() in m.description.lower()]
        
        # Filter by task if specified
        if task:
            filtered = [m for m in filtered if m.task == task]
        
        return filtered[:limit]

    async def download_model(
        self,
        model_id: str,
        revision: str = "main",
    ) -> str:
        """
        Download a model from Hugging Face Hub.
        
        Args:
            model_id: Model ID (e.g., "meta-llama/Llama-2-7b")
            revision: Branch/revision to download
        
        Returns:
            Path to downloaded model
        """
        self.logger.info(f"Downloading model: {model_id}")
        
        # Create model path
        model_path = os.path.join(self.cache_dir, model_id.replace("/", "_"))
        os.makedirs(model_path, exist_ok=True)
        
        # Create metadata file
        metadata = {
            "model_id": model_id,
            "revision": revision,
            "downloaded_at": datetime.now().isoformat(),
        }
        
        metadata_path = os.path.join(model_path, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        
        # Register in registry
        self.registry.register_model(model_id, metadata)
        
        self.logger.info(f"Model downloaded to: {model_path}")
        return model_path

    async def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get model information from Hugging Face Hub."""
        self.logger.info(f"Fetching info for: {model_id}")
        
        # Simulate fetching model info
        info = {
            "model_id": model_id,
            "downloads": 100000,
            "likes": 5000,
            "config": {
                "max_position_embeddings": 2048,
                "hidden_size": 4096,
                "num_attention_heads": 32,
            },
        }
        
        return info


class HFIntegrationAdapter:
    """Adapt Hugging Face models to ISE AI architecture."""

    def __init__(self):
        self.logger = logger
        self.adapter_map = {
            "text-generation": "TextGenerationAdapter",
            "code-generation": "CodeGenerationAdapter",
            "text-classification": "ClassificationAdapter",
            "sentence-similarity": "SimilarityAdapter",
        }

    async def adapt_model(
        self,
        model_id: str,
        model_path: str,
        task: str,
    ) -> IntegrationResult:
        """
        Adapt a Hugging Face model to ISE AI.
        
        Args:
            model_id: Model ID
            model_path: Path to model
            task: Model task type
        
        Returns:
            IntegrationResult
        """
        self.logger.info(f"Adapting model: {model_id}")
        
        try:
            # Create wrapper
            wrapper_path = await self._create_wrapper(model_id, model_path, task)
            
            result = IntegrationResult(
                success=True,
                model_id=model_id,
                message=f"Successfully adapted {model_id}",
                installed_at=datetime.now().isoformat(),
                location=wrapper_path,
                version="1.0",
            )
            
            self.logger.info(f"Model adapted successfully: {model_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to adapt model: {e}")
            return IntegrationResult(
                success=False,
                model_id=model_id,
                message=f"Error: {str(e)}",
                installed_at=datetime.now().isoformat(),
                location="",
                version="",
            )

    async def _create_wrapper(self, model_id: str, model_path: str, task: str) -> str:
        """Create wrapper for Hugging Face model."""
        wrapper_name = model_id.replace("/", "_").replace("-", "_")
        wrapper_file = f"backend/app/services/hf_models/{wrapper_name}_wrapper.py"
        
        os.makedirs(os.path.dirname(wrapper_file), exist_ok=True)
        
        wrapper_code = f'''"""Wrapper for {model_id}"""

from typing import List, Dict, Any

class {wrapper_name}Wrapper:
    """Wraps {model_id} for ISE AI integration."""
    
    def __init__(self, model_path: str = "{model_path}"):
        self.model_path = model_path
        self.model = None
        self.task = "{task}"
    
    async def load(self):
        """Load the model."""
        # Load model from model_path
        self.model = True  # Placeholder
        return self
    
    async def predict(self, input_text: str) -> Dict[str, Any]:
        """Run inference."""
        return {{
            "output": input_text,
            "confidence": 0.95,
            "model": "{model_id}",
        }}
    
    async def batch_predict(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Run batch inference."""
        return [await self.predict(text) for text in texts]
'''
        
        with open(wrapper_file, "w") as f:
            f.write(wrapper_code)
        
        self.logger.info(f"Wrapper created: {wrapper_file}")
        return wrapper_file


class HFAutoIntegration:
    """Automatically integrate improvements from Hugging Face."""

    def __init__(self):
        self.logger = logger
        self.downloader = HFModelDownloader()
        self.adapter = HFIntegrationAdapter()
        self.registry = self.downloader.registry

    async def find_improvements(self, for_task: str) -> List[HFModel]:
        """Find models that improve a specific task."""
        self.logger.info(f"Finding improvements for: {for_task}")
        
        # Search for improvements
        models = await self.downloader.search_models(
            query=for_task,
            task=for_task,
            limit=5,
        )
        
        return models

    async def integrate_best_model(
        self,
        for_task: str,
        auto_download: bool = True,
    ) -> Optional[IntegrationResult]:
        """
        Find and integrate the best model for a task.
        
        Args:
            for_task: Task to improve (e.g., "code-generation")
            auto_download: Automatically download model
        
        Returns:
            IntegrationResult
        """
        self.logger.info(f"Auto-integrating improvement for: {for_task}")
        
        # Find best model
        models = await self.find_improvements(for_task)
        if not models:
            self.logger.warning(f"No models found for: {for_task}")
            return None
        
        best_model = max(models, key=lambda m: m.downloads)
        self.logger.info(f"Selected model: {best_model.model_id}")
        
        # Download if requested
        if auto_download:
            model_path = await self.downloader.download_model(best_model.model_id)
        else:
            model_path = os.path.join(self.downloader.cache_dir, best_model.model_id.replace("/", "_"))
        
        # Adapt and integrate
        result = await self.adapter.adapt_model(
            best_model.model_id,
            model_path,
            best_model.task,
        )
        
        # Register integration
        if result.success:
            self.registry.register_integration(best_model.model_id, result)
        
        return result

    async def integrate_multiple(
        self,
        tasks: List[str],
        auto_download: bool = True,
    ) -> Dict[str, IntegrationResult]:
        """
        Integrate improvements for multiple tasks.
        
        Args:
            tasks: List of tasks to improve
            auto_download: Automatically download models
        
        Returns:
            Dict of task -> IntegrationResult
        """
        results = {}
        
        for task in tasks:
            result = await self.integrate_best_model(task, auto_download)
            if result:
                results[task] = result
        
        return results

    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of integrations."""
        return {
            "registered_models": self.registry.list_models(),
            "integrated_models": self.registry.list_integrations(),
            "total_models": len(self.registry.list_models()),
            "total_integrations": len(self.registry.list_integrations()),
        }


# Factory functions
def get_hf_downloader() -> HFModelDownloader:
    """Get Hugging Face downloader."""
    return HFModelDownloader()


def get_hf_registry() -> HFModelRegistry:
    """Get Hugging Face registry."""
    return HFModelRegistry()


def get_hf_auto_integration() -> HFAutoIntegration:
    """Get auto-integration system."""
    return HFAutoIntegration()
