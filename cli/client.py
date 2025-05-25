"""
API client for RAG system.
"""
import requests
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import click
from .config import config


class RAGAPIClient:
    """Centralized API client for RAG system operations."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.api_base_url
        self.session = requests.Session()
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            click.echo(f"Error: {str(e)}", err=True)
            raise
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request."""
        return self._make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request."""
        return self._make_request('POST', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request."""
        return self._make_request('DELETE', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request."""
        return self._make_request('PUT', endpoint, **kwargs)
    
    # Document operations
    def search_documents(self, query: str, collection: str = "default", 
                        limit: int = 5, language: str = None) -> Dict[str, Any]:
        """Search for documents."""
        payload = {
            "query": query,
            "collection": collection,
            "limit": limit
        }
        if language:
            payload["target_language"] = language
        
        response = self.post("/search", json=payload)
        return response.json()
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None, 
                    collection: str = "default", language: str = None) -> Dict[str, Any]:
        """Add document to the system."""
        payload = {
            "content": content,
            "metadata": metadata or {},
            "collection": collection
        }
        if language:
            payload["language"] = language
        
        response = self.post("/documents", json=payload)
        return response.json()
    
    def upload_file(self, file_path: Path, collection: str = "default", 
                   metadata: Dict[str, Any] = None, language: str = None) -> Dict[str, Any]:
        """Upload file to the system."""
        files = {'file': open(file_path, 'rb')}
        data = {
            'collection': collection,
            'metadata': json.dumps(metadata or {})
        }
        if language:
            data['language'] = language
        
        # Remove Content-Type header for file upload
        headers = {k: v for k, v in self.session.headers.items() 
                  if k.lower() != 'content-type'}
        
        try:
            response = requests.post(
                f"{self.base_url}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        finally:
            files['file'].close()
    
    def upload_file_async(self, file_path: Path, collection: str = "default", 
                         metadata: Dict[str, Any] = None, language: str = None) -> str:
        """Upload file asynchronously and return task ID."""
        files = {'file': open(file_path, 'rb')}
        data = {
            'collection': collection,
            'metadata': json.dumps(metadata or {})
        }
        if language:
            data['language'] = language
        
        headers = {k: v for k, v in self.session.headers.items() 
                  if k.lower() != 'content-type'}
        
        try:
            response = requests.post(
                f"{self.base_url}/documents/upload/async",
                files=files,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("task_id")
        finally:
            files['file'].close()
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of async task."""
        response = self.get(f"/tasks/{task_id}")
        return response.json()
    
    def find_similar_documents(self, text: str, collection: str = "default", 
                              limit: int = 5, exclude_ids: List[str] = None) -> Dict[str, Any]:
        """Find similar documents."""
        payload = {
            "reference_text": text,
            "collection": collection,
            "limit": limit,
            "exclude_ids": exclude_ids or []
        }
        
        response = self.post("/documents/similar", json=payload)
        return response.json()
    
    def delete_document(self, document_id: str) -> None:
        """Delete document."""
        self.delete(f"/documents/{document_id}")
    
    # Collection operations
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        response = self.get("/collections")
        return response.json()
    
    def create_collection(self, name: str) -> None:
        """Create new collection."""
        self.post(f"/collections/{name}")
    
    def delete_collection(self, name: str) -> None:
        """Delete collection."""
        self.delete(f"/collections/{name}")
    
    # Agent operations
    def create_agent(self, name: str, description: str, conversation_id: str, 
                    config_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new agent."""
        payload = {
            "name": name,
            "description": description,
            "conversation_id": conversation_id,
            "config": config_dict or {}
        }
        
        response = self.post("/agents", json=payload)
        return response.json()
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        response = self.get("/agents")
        return response.json()
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent by ID."""
        response = self.get(f"/agents/{agent_id}")
        return response.json()
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete agent."""
        self.delete(f"/agents/{agent_id}")
    
    def get_agent_actions(self, agent_id: str, limit: int = 10, offset: int = 0, 
                         action_type: str = None) -> List[Dict[str, Any]]:
        """Get agent action history."""
        params = {"limit": limit, "offset": offset}
        if action_type:
            params["action_type"] = action_type
        
        response = self.get(f"/agents/{agent_id}/actions", params=params)
        return response.json()
    
    def execute_agent_action(self, agent_id: str, action_type: str, 
                           parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute agent action."""
        payload = {
            "action_type": action_type,
            "parameters": parameters or {}
        }
        
        response = self.post(f"/agents/{agent_id}/actions", json=payload)
        return response.json()
    
    def process_agent_query(self, agent_id: str, query: str, 
                          use_planning: bool = False) -> Dict[str, Any]:
        """Process query with agent."""
        payload = {
            "query": query,
            "use_planning": use_planning
        }
        
        response = self.post(f"/agents/{agent_id}/query", json=payload)
        return response.json()
    
    def evaluate_response(self, agent_id: str, query: str, response: str, 
                         context: List[str]) -> Dict[str, Any]:
        """Evaluate response quality."""
        payload = {
            "query": query,
            "response": response,
            "context": context
        }
        
        response = self.post(f"/agents/{agent_id}/evaluate", json=payload)
        return response.json()
    
    def improve_response(self, evaluation_id: str, agent_id: str) -> Dict[str, Any]:
        """Improve response based on evaluation."""
        payload = {"agent_id": agent_id}
        
        response = self.post(f"/evaluations/{evaluation_id}/improve", json=payload)
        return response.json()
    
    def create_plan(self, agent_id: str, task: str, 
                   constraints: List[str] = None) -> Dict[str, Any]:
        """Create plan for agent."""
        payload = {
            "task": task,
            "constraints": constraints or []
        }
        
        response = self.post(f"/agents/{agent_id}/plans", json=payload)
        return response.json()
    
    def execute_plan(self, plan_id: str, agent_id: str) -> Dict[str, Any]:
        """Execute plan."""
        payload = {"agent_id": agent_id}
        
        response = self.post(f"/plans/{plan_id}/execute", json=payload)
        return response.json()


# Global API client instance
api_client = RAGAPIClient()
