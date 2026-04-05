"""
Agent Configuration and Management System

Provides configuration management, agent profiles, and runtime settings
for the multi-agent orchestration system.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from datetime import UTC, datetime


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 120
    priority: str = "medium"
    model_override: Optional[str] = None
    custom_settings: dict = field(default_factory=dict)


@dataclass
class MultiAgentConfig:
    """Configuration for the multi-agent system."""
    version: str = "1.0.0"
    enable_multi_agent: bool = True
    default_agent: str = "coding-agent"
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 300
    enable_agent_communication: bool = True
    enable_task_delegation: bool = True
    enable_context_sharing: bool = True
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def __post_init__(self):
        if not self.agents:
            self.agents = {
                "planning-agent": AgentConfig(name="planning-agent"),
                "coding-agent": AgentConfig(name="coding-agent"),
                "research-agent": AgentConfig(name="research-agent"),
                "review-agent": AgentConfig(name="review-agent"),
                "testing-agent": AgentConfig(name="testing-agent"),
                "documentation-agent": AgentConfig(name="documentation-agent")
            }


class ConfigManager:
    """Manages configuration for the multi-agent system."""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".ise_ai" / "config.json"
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> MultiAgentConfig:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                return self._dict_to_config(data)
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
        
        return self._create_default_config()
    
    def _dict_to_config(self, data: dict) -> MultiAgentConfig:
        """Convert dictionary to MultiAgentConfig."""
        agents = {}
        for name, agent_data in data.get('agents', {}).items():
            agents[name] = AgentConfig(**agent_data)
        
        return MultiAgentConfig(
            version=data.get('version', '1.0.0'),
            enable_multi_agent=data.get('enable_multi_agent', True),
            default_agent=data.get('default_agent', 'coding-agent'),
            max_concurrent_tasks=data.get('max_concurrent_tasks', 5),
            task_timeout_seconds=data.get('task_timeout_seconds', 300),
            enable_agent_communication=data.get('enable_agent_communication', True),
            enable_task_delegation=data.get('enable_task_delegation', True),
            enable_context_sharing=data.get('enable_context_sharing', True),
            agents=agents,
            created_at=data.get('created_at', datetime.now(UTC).isoformat()),
            updated_at=data.get('updated_at', datetime.now(UTC).isoformat())
        )
    
    def _create_default_config(self) -> MultiAgentConfig:
        """Create default configuration."""
        config = MultiAgentConfig()
        self._save_config(config)
        return config
    
    def _save_config(self, config: MultiAgentConfig):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config.updated_at = datetime.now(UTC).isoformat()
        
        with open(self.config_path, 'w') as f:
            json.dump(self._config_to_dict(config), f, indent=2)
    
    def _config_to_dict(self, config: MultiAgentConfig) -> dict:
        """Convert config to dictionary."""
        data = asdict(config)
        data['agents'] = {
            name: asdict(agent) for name, agent in config.agents.items()
        }
        return data
    
    def get_config(self) -> MultiAgentConfig:
        """Get current configuration."""
        return self.config
    
    def update_config(self, **kwargs):
        """Update configuration with new values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self._save_config(self.config)
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        return self.config.agents.get(agent_name)
    
    def update_agent_config(self, agent_name: str, **kwargs):
        """Update configuration for a specific agent."""
        if agent_name not in self.config.agents:
            self.config.agents[agent_name] = AgentConfig(name=agent_name)
        
        agent_config = self.config.agents[agent_name]
        for key, value in kwargs.items():
            if hasattr(agent_config, key):
                setattr(agent_config, key, value)
        
        self._save_config(self.config)
    
    def enable_agent(self, agent_name: str):
        """Enable an agent."""
        self.update_agent_config(agent_name, enabled=True)
    
    def disable_agent(self, agent_name: str):
        """Disable an agent."""
        self.update_agent_config(agent_name, enabled=False)
    
    def get_enabled_agents(self) -> list[str]:
        """Get list of enabled agents."""
        return [
            name for name, config in self.config.agents.items()
            if config.enabled
        ]
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = self._create_default_config()


# Environment variable support
def get_config_from_env() -> dict:
    """Get configuration from environment variables."""
    return {
        'enable_multi_agent': os.getenv('ISE_AI_ENABLE_MULTI_AGENT', 'true').lower() == 'true',
        'max_concurrent_tasks': int(os.getenv('ISE_AI_MAX_CONCURRENT_TASKS', '5')),
        'task_timeout_seconds': int(os.getenv('ISE_AI_TASK_TIMEOUT', '300')),
        'default_agent': os.getenv('ISE_AI_DEFAULT_AGENT', 'coding-agent')
    }


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the configuration manager singleton."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        # Apply environment variables
        env_config = get_config_from_env()
        _config_manager.update_config(**env_config)
    return _config_manager
