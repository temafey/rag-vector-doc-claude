"""
Document management commands.
"""
import click
from pathlib import Path
from typing import List, Optional
from ..client import api_client
from ..utils import (
    ProgressTracker, TableFormatter, FileProcessor, 
    AsyncTaskTracker, format_metadata
)
from ..config import config


@click.group()
def documents():
    """Document management commands."""
    pass


@documents.command("add")
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--chunk-size", default=1000, help="Chunk size")
@click.option("--chunk-overlap", default=200, help="Chunk overlap")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
@click.option("--resume", is_flag=True, help="Resume from last processed file using progress.json")
def add_files(files: List[Path], collection: str, chunk_size: int, 
             chunk_overlap: int, metadata: List[str], language: Optional[str], resume: bool):
    """Add files to index with progress tracking and resume support."""
    if not files:
        click.echo("No files specified.", err=True)
        return
    
    progress_tracker = ProgressTracker()
    async_tracker = AsyncTaskTracker(api_client)
    metadata_dict = format_metadata(metadata)
    
    total_files = len(files)
    files_done = 0
    
    for file_idx, file_path in enumerate(files):
        file_name = file_path.name
        
        # Skip if already completed and resume is enabled
        if resume and progress_tracker.is_completed(file_name):
            click.echo(f"Skipping {file_name} (already done)")
            files_done += 1
            continue
        
        click.echo(f"Processing file: {file_path}")
        
        try:
            # Upload file asynchronously
            task_id = api_client.upload_file_async(
                file_path=file_path,
                collection=collection,
                metadata=metadata_dict,
                language=language
            )
            
            # Wait for completion
            result = async_tracker.wait_for_completion(task_id, file_name)
            
            # Mark as completed in progress
            progress_tracker.mark_completed(file_name, result)
            files_done += 1
            
        except Exception as e:
            click.echo(f"Error processing file {file_path}: {str(e)}", err=True)
            progress_tracker.mark_failed(file_name, str(e))
            continue
        
        # Show overall progress
        click.echo(f"Overall progress: {files_done}/{total_files} files ({100*files_done//total_files}%)")
    
    click.echo(f"All files processed. {files_done}/{total_files} done.")


@documents.command("add-text")
@click.argument("text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--title", "-t", help="Document title")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
def add_text(text: str, collection: str, title: Optional[str], 
            metadata: List[str], language: Optional[str]):
    """Add text directly to the system."""
    metadata_dict = format_metadata(metadata)
    
    # Add title to metadata if specified
    if title:
        metadata_dict["title"] = title
    
    try:
        result = api_client.add_document(
            content=text,
            metadata=metadata_dict,
            collection=collection,
            language=language
        )
        
        click.echo(f"Document added with ID: {result['id']}")
        click.echo(f"Chunks generated: {result['chunk_count']}")
        
    except Exception as e:
        click.echo(f"Error adding text: {str(e)}", err=True)


@documents.command("query")
@click.argument("query_text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
@click.option("--language", help="Target language (auto-detected if not specified)")
def query_documents(query_text: str, collection: str, limit: int, language: Optional[str]):
    """Search documents using RAG."""
    try:
        click.echo("Processing query...")
        result = api_client.search_documents(
            query=query_text,
            collection=collection,
            limit=limit,
            language=language
        )
        
        # Show language info if available
        if "query_language" in result and "response_language" in result:
            click.echo(f"Query language: {result['query_language']}")
            click.echo(f"Response language: {result['response_language']}")
        
        # Show response
        click.echo(f"\nResponse: {result.get('response', '')}")
        
        # Show sources
        sources = result.get("sources", [])
        if sources:
            click.echo("\nSources:")
            click.echo(TableFormatter.format_sources(sources))
            
            # Show language info for sources if available
            for i, source in enumerate(sources, 1):
                if 'metadata' in source and 'language' in source['metadata']:
                    click.echo(f"Source {i} language: {source['metadata']['language']}")
        
    except Exception as e:
        click.echo(f"Error executing query: {str(e)}", err=True)


@documents.command("similar")
@click.argument("text")
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
def find_similar(text: str, collection: str, limit: int):
    """Find documents similar to text."""
    try:
        result = api_client.find_similar_documents(
            text=text,
            collection=collection,
            limit=limit
        )
        
        documents = result.get("documents", [])
        if not documents:
            click.echo("No similar documents found.")
            return
        
        click.echo("Similar documents:")
        click.echo(TableFormatter.format_sources(documents))
        
    except Exception as e:
        click.echo(f"Error finding similar documents: {str(e)}", err=True)


@documents.command("delete")
@click.argument("document_id")
def delete_document(document_id: str):
    """Delete a document."""
    try:
        api_client.delete_document(document_id)
        click.echo(f"Document {document_id} deleted successfully.")
        
    except Exception as e:
        click.echo(f"Error deleting document: {str(e)}", err=True)


@documents.command("purge-processed")
@click.argument("files", nargs=-1)
@click.option("--collection", "-c", help="Collection name to purge all processed docs for")
def purge_processed(files: List[str], collection: Optional[str]):
    """Delete all processed data from vector DB for specific document(s) and update progress.json status."""
    progress_tracker = ProgressTracker()
    progress = progress_tracker.load_progress()
    updated = []
    
    # If collection is specified, add all files in progress.json with that collection
    if collection:
        for fname, status in progress.items():
            # Add files that match collection (this is a simplified approach)
            files = list(files) + [fname]
    
    for file_name in files:
        try:
            # Delete from API (assuming filename == document_id for demo)
            api_client.delete_document(file_name)
            click.echo(f"Purged vector DB for: {file_name}")
            
        except Exception as e:
            click.echo(f"Error purging {file_name}: {str(e)}", err=True)
        
        # Update progress.json
        progress_tracker.mark_deleted(file_name)
        updated.append(file_name)
    
    click.echo(f"Purged vector DB for {len(updated)} docs. Updated progress.json for {len(updated)} docs.")


@documents.command("delete-processed")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path))
@click.option("--collection", "-c", help="Collection name to delete all processed files for")
def delete_processed(files: List[Path], collection: Optional[str]):
    """Delete processed document files and update progress.json status."""
    progress_tracker = ProgressTracker()
    deleted = []
    updated = []
    
    # If collection is specified, this would need more sophisticated logic
    # to track which files belong to which collection
    
    for file_path in files:
        file_name = file_path.name
        
        # Remove file from disk if exists
        if file_path.exists():
            try:
                file_path.unlink()
                click.echo(f"Deleted file: {file_path}")
                deleted.append(file_name)
            except Exception as e:
                click.echo(f"Error deleting {file_path}: {str(e)}", err=True)
        
        # Update progress.json
        progress_tracker.mark_deleted(file_name)
        updated.append(file_name)
    
    click.echo(f"Deleted {len(deleted)} files. Updated progress.json for {len(updated)} files.")
