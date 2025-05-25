#!/usr/bin/env python
"""
Optimized Command-line interface for RAG system.
"""
import click
from .commands.documents import documents
from .commands.collections import collections
from .commands.agents import agents
from .config import config


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """RAG system with Qdrant, LangChain, and Agent capabilities."""
    pass


# Add command groups
cli.add_command(documents)
cli.add_command(collections)
cli.add_command(agents)


# Legacy compatibility commands for direct access
@cli.command("add")
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--chunk-size", default=1000, help="Chunk size")
@click.option("--chunk-overlap", default=200, help="Chunk overlap")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
@click.option("--resume", is_flag=True, help="Resume from last processed file using progress.json")
def add_files_legacy(files, collection, chunk_size, chunk_overlap, metadata, language, resume):
    """Add files to index (legacy compatibility)."""
    from pathlib import Path
    from .commands.documents import add_files
    
    # Convert to Path objects
    file_paths = [Path(f) for f in files]
    
    # Call the actual command
    add_files(file_paths, collection, chunk_size, chunk_overlap, metadata, language, resume)


@cli.command("query")
@click.argument("query_text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
@click.option("--language", help="Target language (auto-detected if not specified)")
@click.option("--agent", "-a", is_flag=True, help="Use agent for processing the query")
@click.option("--agent-id", help="Agent ID to use (creates new agent if not specified)")
@click.option("--conversation-id", help="Conversation ID (generates new one if not specified)")
@click.option("--planning", "-p", is_flag=True, help="Use planning for complex queries")
@click.option("--evaluate", "-e", is_flag=True, help="Evaluate response quality")
@click.option("--improve", "-i", is_flag=True, help="Improve response if needed")
def query_legacy(query_text, collection, limit, language, agent, agent_id, 
                conversation_id, planning, evaluate, improve):
    """Query RAG system (with optional agent) - legacy compatibility."""
    from .commands.documents import query_documents
    from .commands.agents import agent_query
    from .client import api_client
    from .utils import generate_conversation_id
    
    if agent:
        # Use agent-based query
        if not agent_id:
            # Create new agent if ID not specified
            if not conversation_id:
                conversation_id = generate_conversation_id()
            
            # Create agent
            try:
                agent_response = api_client.create_agent(
                    name=config.default_agent_name,
                    description=config.default_agent_description,
                    conversation_id=conversation_id
                )
                agent_id = agent_response.get("id")
                click.echo(f"Created new agent with ID: {agent_id}")
            except Exception as e:
                click.echo(f"Error creating agent: {str(e)}", err=True)
                return
        
        # Use agent to process query
        agent_query(agent_id, query_text, planning, evaluate)
    else:
        # Use standard RAG query
        query_documents(query_text, collection, limit, language)


@cli.command("similar")
@click.argument("text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
def find_similar_legacy(text, collection, limit):
    """Find documents similar to text - legacy compatibility."""
    from .commands.documents import find_similar
    find_similar(text, collection, limit)


@cli.command("add-text")
@click.argument("text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--title", "-t", help="Document title")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
def add_text_legacy(text, collection, title, metadata, language):
    """Add text directly to the system - legacy compatibility."""
    from .commands.documents import add_text
    add_text(text, collection, title, metadata, language)


if __name__ == "__main__":
    cli()
