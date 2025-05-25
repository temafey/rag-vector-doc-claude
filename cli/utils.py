"""
Common utilities for CLI operations.
"""
import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import click
from tabulate import tabulate
from .config import config


class ProgressTracker:
    """Progress tracking utility for file operations."""
    
    def __init__(self, progress_file: str = None):
        self.progress_file = Path(progress_file or config.progress_file)
        self.progress_file.parent.mkdir(exist_ok=True)
    
    def load_progress(self) -> Dict[str, Any]:
        """Load progress from file."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_progress(self, progress: Dict[str, Any]) -> None:
        """Save progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def mark_completed(self, file_name: str, details: Dict[str, Any] = None) -> None:
        """Mark file as completed."""
        progress = self.load_progress()
        progress[file_name] = {"status": "done", **(details or {})}
        self.save_progress(progress)
    
    def mark_failed(self, file_name: str, error: str) -> None:
        """Mark file as failed."""
        progress = self.load_progress()
        progress[file_name] = {"status": "failed", "error": error}
        self.save_progress(progress)
    
    def mark_deleted(self, file_name: str) -> None:
        """Mark file as deleted."""
        progress = self.load_progress()
        if file_name in progress:
            progress[file_name]["status"] = "deleted"
            self.save_progress(progress)
    
    def is_completed(self, file_name: str) -> bool:
        """Check if file is completed."""
        progress = self.load_progress()
        return progress.get(file_name, {}).get("status") == "done"
    
    def get_file_status(self, file_name: str) -> Optional[str]:
        """Get file processing status."""
        progress = self.load_progress()
        return progress.get(file_name, {}).get("status")


class TableFormatter:
    """Utility for consistent table formatting."""
    
    @staticmethod
    def format_sources(sources: List[Dict[str, Any]]) -> str:
        """Format search sources as table."""
        if not sources:
            return "No sources found."
        
        headers = ["#", "Title", "Relevance", "Content"]
        rows = []
        
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'No title')
            score = source.get('score', 0)
            content = source.get('content', '')[:100]
            if len(source.get('content', '')) > 100:
                content += "..."
            
            rows.append([i, title, f"{score:.2f}", content])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_collections(collections: List[Dict[str, Any]]) -> str:
        """Format collections as table."""
        if not collections:
            return "No collections found."
        
        headers = ["Name", "Documents", "Vector Dimension"]
        rows = [
            [
                collection["name"], 
                collection["document_count"], 
                collection["vector_dimension"]
            ]
            for collection in collections
        ]
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_agents(agents: List[Dict[str, Any]]) -> str:
        """Format agents as table."""
        if not agents:
            return "No agents found."
        
        headers = ["ID", "Name", "Conversation ID", "Actions"]
        rows = [
            [
                agent["id"][:8] + "...",  # Truncate ID for readability
                agent["name"], 
                agent["conversation_id"][:8] + "...",
                agent.get("action_count", 0)
            ]
            for agent in agents
        ]
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_actions(actions: List[Dict[str, Any]]) -> str:
        """Format agent actions as table."""
        if not actions:
            return "No actions found."
        
        headers = ["ID", "Type", "Status", "Created", "Parameters"]
        rows = []
        
        for action in actions:
            # Format parameters for display
            params_str = str(action.get("parameters", {}))
            if len(params_str) > 30:
                params_str = params_str[:30] + "..."
            
            rows.append([
                action.get("id", "")[:8] + "...",
                action.get("action_type", ""),
                action.get("status", ""),
                action.get("created_at", "")[:19],  # Truncate timestamp
                params_str
            ])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_evaluation_scores(scores: Dict[str, Dict[str, Any]]) -> str:
        """Format evaluation criterion scores as table."""
        if not scores:
            return "No evaluation scores available."
        
        headers = ["Criterion", "Score", "Reason"]
        rows = []
        
        for criterion, data in scores.items():
            reason = data.get("reason", "")
            if len(reason) > 50:
                reason = reason[:50] + "..."
            
            rows.append([
                criterion, 
                f"{data.get('score', 0):.2f}", 
                reason
            ])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_plan_steps(steps: List[Dict[str, Any]]) -> str:
        """Format plan steps as table."""
        if not steps:
            return "No plan steps available."
        
        headers = ["#", "Action", "Status", "Description"]
        rows = []
        
        for step in steps:
            description = step.get("description", "")
            if len(description) > 50:
                description = description[:50] + "..."
            
            rows.append([
                step.get("step_number", ""),
                step.get("action_type", ""),
                step.get("status", ""),
                description
            ])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_suggestions(suggestions: List[Dict[str, Any]]) -> str:
        """Format improvement suggestions as table."""
        if not suggestions:
            return "No suggestions available."
        
        headers = ["Criterion", "Priority", "Suggestion"]
        rows = []
        
        for suggestion in suggestions:
            suggestion_text = suggestion.get("suggestion", "")
            if len(suggestion_text) > 100:
                suggestion_text = suggestion_text[:100] + "..."
            
            rows.append([
                suggestion.get("criterion", ""),
                suggestion.get("priority", 0),
                suggestion_text
            ])
        
        return tabulate(rows, headers=headers, tablefmt="grid")


class FileProcessor:
    """Utility for processing files with progress tracking."""
    
    def __init__(self, progress_tracker: ProgressTracker = None):
        self.progress_tracker = progress_tracker or ProgressTracker()
    
    def process_files_with_progress(self, files: List[Path], 
                                   processor_func: Callable[[Path], Any],
                                   skip_completed: bool = True) -> Dict[str, Any]:
        """Process files with progress tracking and resume support."""
        results = {
            "total_files": len(files),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "results": {}
        }
        
        for file_path in files:
            file_name = file_path.name
            
            # Skip if already completed and resume is enabled
            if skip_completed and self.progress_tracker.is_completed(file_name):
                click.echo(f"Skipping {file_name} (already completed)")
                results["skipped"] += 1
                continue
            
            try:
                click.echo(f"Processing {file_name}...")
                result = processor_func(file_path)
                
                # Mark as completed
                self.progress_tracker.mark_completed(file_name, {"result": result})
                results["processed"] += 1
                results["results"][file_name] = result
                
            except Exception as e:
                click.echo(f"Error processing {file_name}: {str(e)}", err=True)
                self.progress_tracker.mark_failed(file_name, str(e))
                results["failed"] += 1
        
        return results


class AsyncTaskTracker:
    """Utility for tracking async tasks."""
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    def wait_for_completion(self, task_id: str, file_name: str = None, 
                          poll_interval: int = 1) -> Dict[str, Any]:
        """Wait for async task completion with progress display."""
        last_status = None
        
        while True:
            try:
                status_data = self.api_client.get_task_status(task_id)
                status = status_data.get("status")
                
                if status != last_status:
                    click.echo(f"Status: {status}")
                    last_status = status
                
                if status == "completed":
                    result = status_data.get("result", {})
                    if file_name:
                        click.echo(
                            f"File {file_name} processed: "
                            f"{result.get('document_count', 0)} docs, "
                            f"{result.get('chunk_count', 0)} chunks."
                        )
                    return result
                    
                elif status == "failed":
                    error = status_data.get('error', 'Unknown error')
                    if file_name:
                        click.echo(f"File {file_name} failed: {error}", err=True)
                    raise Exception(error)
                
                else:
                    # Show progress if available
                    if "progress" in status_data:
                        percent = status_data["progress"]
                        click.echo(f"Progress: {percent}%")
                
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                click.echo("Task cancelled by user", err=True)
                raise
            except Exception as e:
                click.echo(f"Error polling task status: {str(e)}", err=True)
                raise


def generate_conversation_id() -> str:
    """Generate unique conversation ID."""
    return str(uuid.uuid4())


def format_metadata(metadata_list: List[str]) -> Dict[str, Any]:
    """Convert metadata list to dictionary."""
    metadata = {}
    for meta in metadata_list:
        if '=' not in meta:
            click.echo(f"Warning: Invalid metadata format '{meta}'. Use key=value format.", err=True)
            continue
        key, value = meta.split("=", 1)
        # Try to parse as JSON if possible
        try:
            metadata[key] = json.loads(value)
        except:
            metadata[key] = value
    return metadata
