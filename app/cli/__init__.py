"""
Command-line interface for RAG system.
"""
from app.cli.agent_commands import agent_commands
from app.cli.agent_cli import AgentCLI
from app.cli.common import get_api_base_url, print_json, handle_request_error

__all__ = [
    'agent_commands',
    'AgentCLI',
    'get_api_base_url',
    'print_json',
    'handle_request_error'
]
