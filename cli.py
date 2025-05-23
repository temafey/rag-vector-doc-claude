#!/usr/bin/env python
"""
Command-line interface for RAG system.
"""
import click
import os
import json
import uuid
from typing import List, Dict, Any, Optional
import requests
from pathlib import Path
import sys
import time
from tabulate import tabulate
import threading
from tqdm import tqdm

from app.config.config_loader import get_config

# Get configuration
config = get_config()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@click.group()
def cli():
    """RAG system with Qdrant, LangChain, and Agent capabilities."""
    pass

#####################
# Document commands #
#####################

@cli.command("add")
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--collection", "-c", default="default", help="Collection name")
@click.option("--chunk-size", default=1000, help="Chunk size")
@click.option("--chunk-overlap", default=200, help="Chunk overlap")
@click.option("--metadata", "-m", multiple=True, help="Metadata in key=value format")
@click.option("--language", "-l", help="Document language (auto if not specified)")
@click.option("--resume", is_flag=True, help="Resume from last processed file/page/row using data/progress.json")
def add_files(files: List[str], collection: str, chunk_size: int, 
             chunk_overlap: int, metadata: List[str], language: str = None, resume: bool = False):
    """Add files to index with progress tracking and resume support."""
    PROGRESS_FILE = "data/progress.json"
    os.makedirs("data", exist_ok=True)
    def load_progress():
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        return {}
    def save_progress(progress):
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    progress = load_progress() if resume else {}
    metadata_dict = {}
    for meta in metadata:
        key, value = meta.split("=", 1)
        metadata_dict[key] = value
    total_files = len(files)
    files_done = 0
    for file_idx, file_path in enumerate(files):
        file_name = os.path.basename(file_path)
        file_prog = progress.get(file_name, {}) if resume else {}
        if resume and file_prog.get("status") == "done":
            click.echo(f"Skipping {file_name} (already done)")
            files_done += 1
            continue
        click.echo(f"Processing file: {file_path}")
        files_dict = {'file': open(file_path, 'rb')}
        data = {'collection': collection, 'metadata': json.dumps(metadata_dict)}
        if language:
            data['language'] = language
        # Use async endpoint for progress
        response = requests.post(f"{API_BASE_URL}/documents/upload/async", files=files_dict, data=data)
        if response.status_code != 200:
            click.echo(f"Error processing file {file_path}: {response.text}")
            continue
        result = response.json()
        task_id = result.get("task_id")
        # Poll for progress
        percent = 0
        last_status = None
        while True:
            status_resp = requests.get(f"{API_BASE_URL}/tasks/{task_id}")
            if status_resp.status_code != 200:
                click.echo(f"Error polling status for {file_name}: {status_resp.text}")
                break
            status_data = status_resp.json()
            status = status_data.get("status")
            prog = status_data.get("result", {})
            if status != last_status:
                click.echo(f"Status: {status}")
                last_status = status
            if status == "completed":
                click.echo(f"File {file_name} processed: {prog.get('document_count', 0)} docs, {prog.get('chunk_count', 0)} chunks.")
                progress[file_name] = {"status": "done"}
                save_progress(progress)
                files_done += 1
                break
            elif status == "failed":
                click.echo(f"File {file_name} failed: {status_data.get('error')}")
                progress[file_name] = {"status": "failed", "error": status_data.get('error')}
                save_progress(progress)
                break
            else:
                # Show percent if available
                if "progress" in status_data:
                    percent = status_data["progress"]
                    click.echo(f"Progress: {percent}%", nl=False)
                time.sleep(1)
        click.echo(f"Overall progress: {files_done}/{total_files} files ({100*files_done//total_files}%)")
    click.echo(f"All files processed. {files_done}/{total_files} done.")

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
def query(query_text: str, collection: str, limit: int, language: str = None, 
         agent: bool = False, agent_id: str = None, conversation_id: str = None,
         planning: bool = False, evaluate: bool = False, improve: bool = False):
    """Query RAG system (with optional agent)."""
    if agent:
        # Use agent-based query
        if not agent_id:
            # Create new agent if ID not specified
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # Create agent
            agent_response = requests.post(
                f"{API_BASE_URL}/agents",
                json={
                    "name": config.get("agent", {}).get("default_agent_name", "RAG Assistant"),
                    "description": config.get("agent", {}).get("default_agent_description", "Agent for RAG with self-assessment"),
                    "conversation_id": conversation_id
                }
            )
            
            if agent_response.status_code != 200:
                click.echo(f"Error creating agent: {agent_response.text}")
                return
            
            agent_data = agent_response.json()
            agent_id = agent_data.get("id")
            click.echo(f"Created new agent with ID: {agent_id}")
        
        # Use agent to process query
        payload = {
            "query": query_text,
            "use_planning": planning
        }
        
        click.echo("Processing query with agent...")
        response = requests.post(
            f"{API_BASE_URL}/agents/{agent_id}/query",
            json=payload
        )
    else:
        # Use standard RAG query
        payload = {
            "query": query_text,
            "collection": collection,
            "limit": limit
        }
        
        if language:
            payload["target_language"] = language
        
        # Send request
        click.echo("Processing query...")
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
    
    if agent:
        # Agent response format
        click.echo("\nResponse:")
        click.echo(result.get("response", ""))
        
        # Show improvement info if applicable
        if result.get("improved", False):
            click.echo("\n(Response was improved by self-assessment)")
        
        # Show evaluation if available
        if result.get("evaluation"):
            eval_data = result["evaluation"]
            click.echo("\nEvaluation:")
            click.echo(f"Overall Score: {eval_data.get('overall_score', 0):.2f}")
            
            # Show scores for each criterion
            if "criterion_scores" in eval_data:
                click.echo("\nCriterion Scores:")
                headers = ["Criterion", "Score", "Reason"]
                rows = []
                
                for criterion, data in eval_data["criterion_scores"].items():
                    rows.append([
                        criterion, 
                        f"{data.get('score', 0):.2f}", 
                        data.get("reason", "")[:50] + ("..." if len(data.get("reason", "")) > 50 else "")
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Show plan if available
        if result.get("plan"):
            plan = result["plan"]
            click.echo("\nExecution Plan:")
            click.echo(f"Task: {plan.get('task', '')}")
            
            # Show steps
            if "steps" in plan:
                click.echo("\nSteps:")
                headers = ["#", "Action", "Status", "Description"]
                rows = []
                
                for step in plan["steps"]:
                    rows.append([
                        step.get("step_number", ""),
                        step.get("action_type", ""),
                        step.get("status", ""),
                        step.get("description", "")[:50] + ("..." if len(step.get("description", "")) > 50 else "")
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        # Standard RAG response format
        if "query_language" in result and "response_language" in result:
            click.echo(f"Query language: {result['query_language']}")
            click.echo(f"Response language: {result['response_language']}")
        
        click.echo(f"\nResponse: {result.get('response', '')}")
    
    # Show sources
    sources = result.get("sources", [])
    if sources:
        click.echo("\nSources:")
        headers = ["#", "Title", "Relevance", "Content"]
        rows = []
        
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'No title')
            score = source.get('score', 0)
            content = source.get('content', '')[:100] + ("..." if len(source.get('content', '')) > 100 else "")
            
            rows.append([i, title, f"{score:.2f}", content])
        
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Show language info if available
        for i, source in enumerate(sources, 1):
            if 'metadata' in source and 'language' in source['metadata']:
                click.echo(f"Source {i} language: {source['metadata']['language']}")

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
        
        click.echo(f"Collection {create} created successfully.")
    
    elif delete:
        # Delete collection
        response = requests.delete(
            f"{API_BASE_URL}/collections/{delete}"
        )
        
        # Check response status
        if response.status_code != 200:
            click.echo(f"Error deleting collection: {response.text}")
            return
        
        click.echo(f"Collection {delete} deleted successfully.")
    
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
        
        if not collections:
            click.echo("No collections found.")
            return
        
        # Show collections table
        headers = ["Name", "Documents", "Vector Dimension"]
        rows = [
            [collection["name"], collection["document_count"], collection["vector_dimension"]]
            for collection in collections
        ]
        
        click.echo("Available collections:")
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

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
    
    if not result.get("documents"):
        click.echo("No similar documents found.")
        return
    
    # Show similar documents table
    headers = ["#", "Title", "Relevance", "Content"]
    rows = []
    
    for i, doc in enumerate(result.get("documents", []), 1):
        title = doc.get('title', 'No title')
        score = doc.get('score', 0)
        content = doc.get('content', '')[:100] + ("..." if len(doc.get('content', '')) > 100 else "")
        
        rows.append([i, title, f"{score:.2f}", content])
    
    click.echo("Similar documents:")
    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

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

@cli.command("delete-processed")
@click.argument("files", nargs=-1, type=click.Path())
@click.option("--collection", "-c", default=None, help="Collection name to delete all processed files for")
def delete_processed(files: List[str], collection: Optional[str] = None):
    """Delete processed document files and update progress.json status."""
    import glob
    PROGRESS_FILE = "data/progress.json"
    os.makedirs("data", exist_ok=True)
    def load_progress():
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        return {}
    def save_progress(progress):
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    progress = load_progress()
    deleted = []
    updated = []
    # If collection is specified, find all files in progress.json with that collection
    if collection:
        # This assumes metadata in progress.json includes collection info (if not, skip this logic)
        for fname, status in progress.items():
            # If you want to filter by collection, you need to store collection in progress.json entries
            # For now, just delete all files in data/ matching collection name as prefix
            if fname.startswith(collection):
                files = list(files) + [os.path.join("data", fname)]
    for file_path in files:
        file_name = os.path.basename(file_path)
        # Remove file from disk if exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                click.echo(f"Deleted file: {file_path}")
                deleted.append(file_name)
            except Exception as e:
                click.echo(f"Error deleting {file_path}: {e}")
        # Update progress.json
        if file_name in progress:
            progress[file_name]["status"] = "deleted"
            updated.append(file_name)
    save_progress(progress)
    click.echo(f"Deleted {len(deleted)} files. Updated progress.json for {len(updated)} files.")

@cli.command("purge-processed")
@click.argument("files", nargs=-1, type=click.Path())
@click.option("--collection", "-c", default=None, help="Collection name to purge all processed docs for")
def purge_processed(files: List[str], collection: Optional[str] = None):
    """
    Delete all processed data from vector DB for specific document(s) and update progress.json status.
    Does NOT delete raw files from disk.
    """
    PROGRESS_FILE = "data/progress.json"
    os.makedirs("data", exist_ok=True)
    def load_progress():
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        return {}
    def save_progress(progress):
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    progress = load_progress()
    updated = []
    # If collection is specified, add all files in progress.json with that collection
    if collection:
        for fname, status in progress.items():
            # If you want to filter by collection, you need to store collection in progress.json entries
            # For now, just match all files in progress.json (improve as needed)
            files = list(files) + [fname]
    for file_name in files:
        # 1. Call API to delete all vectors/chunks for this document
        #    (Assume you have an endpoint like /documents/{document_id} DELETE)
        #    If you only have filename, you may need to look up document_id by filename
        #    Here, we assume filename == document_id for demo
        try:
            resp = requests.delete(f"{API_BASE_URL}/documents/{file_name}")
            if resp.status_code == 200:
                click.echo(f"Purged vector DB for: {file_name}")
            else:
                click.echo(f"Error purging {file_name}: {resp.text}")
        except Exception as e:
            click.echo(f"Error purging {file_name}: {e}")
        # 2. Update progress.json
        if file_name in progress:
            progress[file_name]["status"] = "deleted"
            updated.append(file_name)
    save_progress(progress)
    click.echo(f"Purged vector DB for {len(updated)} docs. Updated progress.json for {len(updated)} docs.")

#################
# Agent commands #
#################

@cli.group("agent")
def agent_group():
    """Commands for working with agents."""
    pass

@agent_group.command("create")
@click.option("--name", "-n", default=None, help="Agent name")
@click.option("--description", "-d", default=None, help="Agent description")
@click.option("--conversation-id", "-c", default=None, help="Conversation ID (generates new one if not specified)")
def create_agent(name: str = None, description: str = None, conversation_id: str = None):
    """Create a new agent."""
    # Use defaults from config if not specified
    if not name:
        name = config.get("agent", {}).get("default_agent_name", "RAG Assistant")
    
    if not description:
        description = config.get("agent", {}).get("default_agent_description", "Agent for RAG with self-assessment")
    
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    # Prepare request data
    payload = {
        "name": name,
        "description": description,
        "conversation_id": conversation_id
    }
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/agents",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error creating agent: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    click.echo(f"Agent created:")
    click.echo(f"ID: {result['id']}")
    click.echo(f"Name: {result['name']}")
    click.echo(f"Conversation ID: {result['conversation_id']}")

@agent_group.command("list")
def list_agents():
    """List all agents."""
    # Send request
    response = requests.get(f"{API_BASE_URL}/agents")
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error listing agents: {response.text}")
        return
    
    # Get result
    agents = response.json()
    
    if not agents:
        click.echo("No agents found.")
        return
    
    # Show agents table
    headers = ["ID", "Name", "Conversation ID", "Actions"]
    rows = [
        [agent["id"], agent["name"], agent["conversation_id"], agent.get("action_count", 0)]
        for agent in agents
    ]
    
    click.echo("Available agents:")
    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

@agent_group.command("delete")
@click.argument("agent_id")
def delete_agent(agent_id: str):
    """Delete an agent."""
    # Send request
    response = requests.delete(f"{API_BASE_URL}/agents/{agent_id}")
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error deleting agent: {response.text}")
        return
    
    click.echo(f"Agent {agent_id} deleted successfully.")

@agent_group.command("info")
@click.argument("agent_id")
def get_agent_info(agent_id: str):
    """Get agent information."""
    # Send request
    response = requests.get(f"{API_BASE_URL}/agents/{agent_id}")
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error getting agent information: {response.text}")
        return
    
    # Get result
    agent = response.json()
    
    click.echo(f"Agent Information:")
    click.echo(f"ID: {agent['id']}")
    click.echo(f"Name: {agent['name']}")
    click.echo(f"Description: {agent['description']}")
    click.echo(f"Conversation ID: {agent['conversation_id']}")
    click.echo(f"Created: {agent['created_at']}")
    click.echo(f"Last updated: {agent['updated_at']}")
    click.echo(f"Action count: {agent.get('action_count', 0)}")

@agent_group.command("actions")
@click.argument("agent_id")
@click.option("--limit", "-l", default=10, help="Maximum number of actions to show")
@click.option("--offset", "-o", default=0, help="Offset for pagination")
@click.option("--action-type", "-t", help="Filter by action type")
def get_agent_actions(agent_id: str, limit: int, offset: int, action_type: str = None):
    """Get agent action history."""
    # Build URL with query parameters
    url = f"{API_BASE_URL}/agents/{agent_id}/actions?limit={limit}&offset={offset}"
    if action_type:
        url += f"&action_type={action_type}"
    
    # Send request
    response = requests.get(url)
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error getting agent actions: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    if not result:
        click.echo("No actions found.")
        return
    
    # Show actions table
    headers = ["ID", "Type", "Status", "Created", "Parameters"]
    rows = []
    
    for action in result:
        # Format parameters for display
        params_str = str(action.get("parameters", {}))
        if len(params_str) > 30:
            params_str = params_str[:30] + "..."
        
        rows.append([
            action.get("id", ""),
            action.get("action_type", ""),
            action.get("status", ""),
            action.get("created_at", "")[:19],  # Truncate timestamp
            params_str
        ])
    
    click.echo(f"Actions for agent {agent_id}:")
    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

@agent_group.command("run")
@click.argument("agent_id")
@click.option("--action", "-a", required=True, help="Action type to run")
@click.option("--param", "-p", multiple=True, help="Parameters in key=value format")
def execute_action(agent_id: str, action: str, param: List[str]):
    """Execute an action with an agent."""
    # Convert parameters from list of strings to dict
    parameters = {}
    for p in param:
        key, value = p.split("=", 1)
        # Try to parse as JSON if possible
        try:
            parameters[key] = json.loads(value)
        except:
            parameters[key] = value
    
    # Prepare request data
    payload = {
        "action_type": action,
        "parameters": parameters
    }
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/agents/{agent_id}/actions",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error executing action: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    click.echo(f"Action executed:")
    click.echo(f"ID: {result.get('id', '')}")
    click.echo(f"Type: {result.get('action_type', '')}")
    click.echo(f"Status: {result.get('status', '')}")
    
    # Pretty print result
    click.echo("\nResult:")
    click.echo(json.dumps(result.get("result", {}), indent=2))

@agent_group.command("query")
@click.argument("agent_id")
@click.argument("query_text")
@click.option("--planning", "-p", is_flag=True, help="Use planning for complex queries")
def agent_query(agent_id: str, query_text: str, planning: bool = False):
    """Process a query using an agent."""
    # Prepare request data
    payload = {
        "query": query_text,
        "use_planning": planning
    }
    
    # Send request
    click.echo("Processing query with agent...")
    response = requests.post(
        f"{API_BASE_URL}/agents/{agent_id}/query",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error executing query: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    # Display response
    click.echo("\nResponse:")
    click.echo(result.get("response", ""))
    
    # Show improvement info if applicable
    if result.get("improved", False):
        click.echo("\n(Response was improved by self-assessment)")
    
    # Show evaluation if available
    if result.get("evaluation"):
        eval_data = result["evaluation"]
        click.echo("\nEvaluation:")
        click.echo(f"Overall Score: {eval_data.get('overall_score', 0):.2f}")
        
        # Show scores for each criterion
        if "criterion_scores" in eval_data:
            click.echo("\nCriterion Scores:")
            headers = ["Criterion", "Score", "Reason"]
            rows = []
            
            for criterion, data in eval_data["criterion_scores"].items():
                rows.append([
                    criterion, 
                    f"{data.get('score', 0):.2f}", 
                    data.get("reason", "")[:50] + ("..." if len(data.get("reason", "")) > 50 else "")
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
    
    # Show plan if available
    if result.get("plan"):
        plan = result["plan"]
        click.echo("\nExecution Plan:")
        click.echo(f"Task: {plan.get('task', '')}")
        
        # Show steps
        if "steps" in plan:
            click.echo("\nSteps:")
            headers = ["#", "Action", "Status", "Description"]
            rows = []
            
            for step in plan["steps"]:
                rows.append([
                    step.get("step_number", ""),
                    step.get("action_type", ""),
                    step.get("status", ""),
                    step.get("description", "")[:50] + ("..." if len(step.get("description", "")) > 50 else "")
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
    
    # Show sources
    sources = result.get("sources", [])
    if sources:
        click.echo("\nSources:")
        headers = ["#", "Title", "Relevance", "Content"]
        rows = []
        
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'No title')
            score = source.get('score', 0)
            content = source.get('content', '')[:100] + ("..." if len(source.get('content', '')) > 100 else "")
            
            rows.append([i, title, f"{score:.2f}", content])
        
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

@agent_group.command("evaluate")
@click.argument("agent_id")
@click.option("--query", "-q", required=True, help="Query text")
@click.option("--response", "-r", required=True, help="Response to evaluate")
@click.option("--context", "-c", multiple=True, help="Context (can be specified multiple times)")
def evaluate_response(agent_id: str, query: str, response: str, context: List[str]):
    """Evaluate response quality."""
    # Prepare request data
    payload = {
        "query": query,
        "response": response,
        "context": list(context)
    }
    
    # Send request
    response_obj = requests.post(
        f"{API_BASE_URL}/agents/{agent_id}/evaluate",
        json=payload
    )
    
    # Check response status
    if response_obj.status_code != 200:
        click.echo(f"Error evaluating response: {response_obj.text}")
        return
    
    # Get result
    result = response_obj.json()
    
    # Display evaluation results
    click.echo("Evaluation Results:")
    click.echo(f"Evaluation ID: {result.get('evaluation_id', '')}")
    click.echo(f"Overall Score: {result.get('overall_score', 0):.2f}")
    click.echo(f"Needs Improvement: {'Yes' if result.get('needs_improvement', False) else 'No'}")
    
    # Show criterion scores
    if "criterion_scores" in result:
        click.echo("\nCriterion Scores:")
        headers = ["Criterion", "Score", "Reason"]
        rows = []
        
        for criterion, data in result["criterion_scores"].items():
            rows.append([
                criterion, 
                f"{data.get('score', 0):.2f}", 
                data.get("reason", "")[:100] + ("..." if len(data.get("reason", "")) > 100 else "")
            ])
        
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

@agent_group.command("improve")
@click.argument("agent_id")
@click.argument("evaluation_id")
def improve_response(agent_id: str, evaluation_id: str):
    """Improve response based on evaluation."""
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/evaluations/{evaluation_id}/improve",
        json={"agent_id": agent_id}
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error improving response: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    # Display improvement results
    click.echo("Improvement Results:")
    click.echo(f"Improvement ID: {result.get('id', '')}")
    
    click.echo("\nOriginal Response:")
    click.echo(result.get("original_response", ""))
    
    click.echo("\nImproved Response:")
    click.echo(result.get("improved_response", ""))
    
    # Show suggestions
    if "suggestions" in result:
        click.echo("\nImprovement Suggestions:")
        headers = ["Criterion", "Priority", "Suggestion"]
        rows = []
        
        for suggestion in result["suggestions"]:
            rows.append([
                suggestion.get("criterion", ""),
                suggestion.get("priority", 0),
                suggestion.get("suggestion", "")[:100] + ("..." if len(suggestion.get("suggestion", "")) > 100 else "")
            ])
        
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

@agent_group.command("plan")
@click.argument("agent_id")
@click.argument("task")
@click.option("--constraint", "-c", multiple=True, help="Constraints (can be specified multiple times)")
def create_plan(agent_id: str, task: str, constraint: List[str]):
    """Create a plan for a task."""
    # Prepare request data
    payload = {
        "task": task,
        "constraints": list(constraint)
    }
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/agents/{agent_id}/plans",
        json=payload
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error creating plan: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    # Display plan
    click.echo("Plan Created:")
    click.echo(f"Plan ID: {result.get('id', '')}")
    click.echo(f"Task: {result.get('task', '')}")
    click.echo(f"Status: {result.get('status', '')}")
    
    # Show steps
    if "steps" in result:
        click.echo("\nSteps:")
        headers = ["#", "Action", "Status", "Description", "Dependencies"]
        rows = []
        
        for step in result["steps"]:
            rows.append([
                step.get("step_number", ""),
                step.get("action_type", ""),
                step.get("status", ""),
                step.get("description", "")[:50] + ("..." if len(step.get("description", "")) > 50 else ""),
                step.get("dependencies", [])
            ])
        
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

@agent_group.command("execute-plan")
@click.argument("agent_id")
@click.argument("plan_id")
def execute_plan(agent_id: str, plan_id: str):
    """Execute a plan."""
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/plans/{plan_id}/execute",
        json={"agent_id": agent_id}
    )
    
    # Check response status
    if response.status_code != 200:
        click.echo(f"Error executing plan: {response.text}")
        return
    
    # Get result
    result = response.json()
    
    # Display execution results
    click.echo("Plan Execution Results:")
    click.echo(f"Plan ID: {result.get('plan_id', '')}")
    click.echo(f"Status: {result.get('status', '')}")
    click.echo(f"Completed Steps: {result.get('completed_steps', [])}")
    
    # Show step results
    if "results" in result:
        click.echo("\nStep Results:")
        for step_num, step_result in result["results"].items():
            click.echo(f"\nStep {step_num} Result:")
            # Pretty print result
            click.echo(json.dumps(step_result, indent=2)[:200] + "..." if len(json.dumps(step_result, indent=2)) > 200 else json.dumps(step_result, indent=2))

if __name__ == "__main__":
    cli()
