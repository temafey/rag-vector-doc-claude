"""
Configuration loader for YAML files.
"""
import os
import yaml
from typing import Dict, Any
from pathlib import Path

class ConfigLoader:
    """Loader for configuration from YAML files."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.env = os.getenv("APP_ENV", "development")
        self.config_dir = Path(__file__).parent
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration based on current environment.
        
        Returns:
            Configuration dictionary
        """
        # Load base configuration
        base_config_path = self.config_dir / "base.yaml"
        if base_config_path.exists():
            with open(base_config_path, "r") as f:
                self.config = yaml.safe_load(f) or {}
        
        # Load environment configuration
        env_config_path = self.config_dir / f"{self.env}.yaml"
        if env_config_path.exists():
            with open(env_config_path, "r") as f:
                env_config = yaml.safe_load(f) or {}
                self._deep_update(self.config, env_config)
        
        # Load local configuration (not versioned)
        local_config_path = self.config_dir / f"{self.env}.local.yaml"
        if local_config_path.exists():
            with open(local_config_path, "r") as f:
                local_config = yaml.safe_load(f) or {}
                self._deep_update(self.config, local_config)
        
        # Override from environment variables
        self._override_from_env()
        
        return self.config
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Deep update of nested dictionaries.
        
        Args:
            target: Target dictionary
            source: Source dictionary
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _override_from_env(self) -> None:
        """Override configuration from environment variables."""
        # Example: APP_QDRANT_HOST will override config["qdrant"]["host"]
        prefix = "APP_"
        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                parts = env_var[len(prefix):].lower().split("_")
                self._set_nested(self.config, parts, value)
    
    def _set_nested(self, config: Dict[str, Any], keys: list, value: Any) -> None:
        """
        Set value in nested dictionary.
        
        Args:
            config: Configuration dictionary
            keys: List of keys
            value: Value to set
        """
        if len(keys) == 1:
            config[keys[0]] = value
        else:
            key = keys[0]
            if key not in config:
                config[key] = {}
            self._set_nested(config[key], keys[1:], value)

# Create singleton for configuration
config_loader = ConfigLoader()
config = config_loader.load()

def get_config() -> Dict[str, Any]:
    """
    Get current configuration.
    
    Returns:
        Configuration dictionary
    """
    return config
