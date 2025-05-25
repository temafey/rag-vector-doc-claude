"""
Configuration management for CLI.
"""
import os
from typing import Dict, Any
from pathlib import Path
import yaml


class CLIConfig:
    """Centralized configuration for CLI commands."""
    
    def __init__(self):
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.default_collection = "default"
        self.progress_file = "data/progress.json"
        self.data_dir = Path("data")
        
        # Load config from app config if available
        self._load_app_config()
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
    
    def _load_app_config(self):
        """Load configuration from app config files."""
        try:
            from app.config.config_loader import get_config
            app_config = get_config()
            
            # Extract relevant CLI configurations
            self.agent_config = app_config.get("agent", {})
            self.default_agent_name = self.agent_config.get(
                "default_agent_name", "RAG Assistant"
            )
            self.default_agent_description = self.agent_config.get(
                "default_agent_description", 
                "Agent for RAG with self-assessment"
            )
        except ImportError:
            # Fallback to default values if app config is not available
            self.agent_config = {}
            self.default_agent_name = "RAG Assistant"
            self.default_agent_description = "Agent for RAG with self-assessment"


# Global config instance
config = CLIConfig()
