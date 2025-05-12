"""
Common utilities for CLI commands.
"""
import os
import requests
import click
import json

def get_api_base_url() -> str:
    """Get the base URL for the API."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")

def print_json(data, indent=2):
    """Print JSON data in a nice format."""
    click.echo(json.dumps(data, indent=indent, ensure_ascii=False))

def handle_request_error(response, message="Error"):
    """Handle error response from API."""
    try:
        error_data = response.json()
        error_message = error_data.get("detail", {})
        if isinstance(error_message, dict) and "message" in error_message:
            click.echo(f"{message}: {error_message['message']}")
        else:
            click.echo(f"{message}: {error_message}")
    except Exception:
        click.echo(f"{message}: {response.text}")
