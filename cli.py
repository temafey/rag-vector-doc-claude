#!/usr/bin/env python
"""
Command-line interface for RAG system.
"""
import click
import os
import json
from typing import List
import requests
import uuid
from pathlib import Path

from app.config.config_loader import get_config

# Get configuration
config = get_config()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@click.group()
def cli():
    """RAG system with Qdrant and LangChain."""
    pass

@cli.command("add")
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--chunk-size", default=1000, help="Chunk size")
@click.option("--chunk-overlap", default=200, help="Chunk overlap")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
def add_files(files: List[str], collection: str, chunk_size: int, 
             chunk_overlap: int, metadata: List[str], language: str = None):
    """Add files to index."""
    # Convert metadata from list of strings to dict
    metadata_dict = {}
    for meta in metadata:
        key, value = meta.split("=", 1)
        metadata_dict[key] = value
    
    # Counters for statistics
    total_documents = 0
    total_chunks = 0
    
    # Process each file
    for file_path in files:
        click.echo(f"Processing file: {file_path}")
        
        # Create multipart/form-data request
        files_dict = {
            'file': open(file_path, 'rb')
        }
        
        data = {
            'collection': collection,
            'metadata': json.dumps(metadata_dict)
        }
        
        if language:
            data['language'] = language
        
        # Send request
        response = requests.post(
            f"{API_BASE_URL}/documents/upload",
            files=files_dict,
            data=data
        )
        
        # Check response status
        if response.status_code != 200:
            click.echo(f"Error processing file {file_path}: {response.text}")
            continue
        
        # Get result
        result = response.json()
        
        total_documents += result.get("document_count", 0)
        total_chunks += result.get("chunk_count", 0)
    
    click.echo(f"Added {total_documents} documents, {total_chunks} fragments.")

@cli.command("query")
@click.argument("query_text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
@click.option("--language", help="Target language (auto-detected if not specified)")
def query(query_text: str, collection: str, limit: int, language: str = None):
    """Query RAG system."""
    # Prepare request data
    payload = {
        "query": query_text,
        "collection": collection,
        "limit": limit
    }
    
    if language:
        payload["target_language"] = language
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/search",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error executing query: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    click.echo(f"Query language: {result['query_language']}")
    click.echo(f"Response language: {result['response_language']}")
    click.echo(f"Response: {result['response']}")
    
    click.echo("\nSources:")
    for i, source in enumerate(result["sources"], 1):
        click.echo(f"{i}. {source.get('title', 'No title')} - Relevance: {source.get('score', 0):.2f}")
        if 'metadata' in source and 'language' in source['metadata']:
            click.echo(f"   Language: {source['metadata']['language']}")
        click.echo(f"   {source.get('content', '')[:150]}...")

@cli.command("collections")
@click.option("--create", "-c", help="Create new collection")
@click.option("--delete", "-d", help="Delete collection")
@click.option("--list", "-l", is_flag=True, help="List all collections")
def collections(create, delete, list):
    """Manage collections."""
    if create:
        # Create new collection
        response = requests.post(
            f"{API_BASE_URL}/collections/{create}"
        )
        
        # Check response status
        if response.status_code != 200:
            click.echo(f"Error creating collection: {response.text}")
            return
        
        click.echo(f"Collection {create} created.")
    
    elif delete:
        # Delete collection
        response = requests.delete(
            f"{API_BASE_URL}/collections/{delete}"
        )
        
        # Check response status
        if response.status_code != 200:
            click.echo(f"Error deleting collection: {response.text}")
            return
        
        click.echo(f"Collection {delete} deleted.")
    
    elif list:
        # Get collections list
        response = requests.get(
            f"{API_BASE_URL}/collections"
        )
        
        # Check response status
        if response.status_code != 200:
            click.echo(f"Error getting collections list: {response.text}")
            return
        
        # Get result
        collections = response.json()
        
        click.echo("Available collections:")
        for collection in collections:
            click.echo(f"- {collection['name']} ({collection['document_count']} documents)")

@cli.command("similar")
@click.argument("text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
def find_similar(text: str, collection: str, limit: int):
    """Find documents similar to text."""
    # Prepare request data
    payload = {
        "reference_text": text,
        "collection": collection,
        "limit": limit,
        "exclude_ids": []
    }
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/documents/similar",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error finding similar documents: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    click.echo("Similar documents:")
    for i, doc in enumerate(result["documents"], 1):
        click.echo(f"{i}. {doc.get('title', 'No title')} - Relevance: {doc.get('score', 0):.2f}")
        click.echo(f"   {doc.get('content', '')[:150]}...")

@cli.command("add-text")
@click.argument("text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--title", "-t", help="Document title")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
def add_text(text: str, collection: str, title: str = None, metadata: List[str] = None, language: str = None):
    """Add text directly to the system."""
    # Convert metadata from list of strings to dict
    metadata_dict = {}
    if metadata:
        for meta in metadata:
            key, value = meta.split("=", 1)
            metadata_dict[key] = value
    
    # Add title to metadata if specified
    if title:
        metadata_dict["title"] = title
    
    # Prepare request data
    payload = {
        "content": text,
        "metadata": metadata_dict,
        "collection": collection
    }
    
    if language:
        payload["language"] = language
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/documents",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error adding text: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    click.echo(f"Document added with ID: {result['id']}")
    click.echo(f"Chunks generated: {result['chunk_count']}")

if __name__ == "__main__":
    cli()
