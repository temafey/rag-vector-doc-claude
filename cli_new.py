#!/usr/bin/env python
"""
Entry point for the optimized RAG CLI.
This replaces the old cli.py with a modular, maintainable structure.
"""
import sys
from pathlib import Path

# Add the CLI package to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main CLI
from cli.main import cli

if __name__ == "__main__":
    cli()
