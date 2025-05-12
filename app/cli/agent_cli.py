"""
CLI for agent operations.
"""
import requests
import json
from typing import Dict, List, Any, Optional
import click

class AgentCLI:
    """CLI for agent operations."""
    
    def __init__(self, api_base_url: str):
        """
        Initialize CLI.
        
        Args:
            api_base_url: Base URL for the API
        """
        self.api_base_url = api_base_url.rstrip('/')
    
    def create_agent(self, name: str, description: str, 
                   conversation_id: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new agent.
        
        Args:
            name: Agent name
            description: Agent description
            conversation_id: Conversation ID (generated if not provided)
            config: Agent configuration
            
        Returns:
            Created agent
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            import uuid
            conversation_id = str(uuid.uuid4())
        
        # Prepare request data
        payload = {
            "name": name,
            "description": description,
            "conversation_id": conversation_id,
            "config": config or {}
        }
        
        # Send request
        response = requests.post(
            f"{self.api_base_url}/agents",
            json=payload
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error creating agent: {error_message}")
        
        # Return result
        return response.json()
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent information
        """
        # Send request
        response = requests.get(
            f"{self.api_base_url}/agents/{agent_id}"
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error getting agent: {error_message}")
        
        # Return result
        return response.json()
    
    def get_agent_by_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get agent by conversation ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Agent information
        """
        # Send request
        response = requests.get(
            f"{self.api_base_url}/agents/conversation/{conversation_id}"
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error getting agent: {error_message}")
        
        # Return result
        return response.json()
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of all agents.
        
        Returns:
            List of agents
        """
        # Send request
        response = requests.get(
            f"{self.api_base_url}/agents"
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error listing agents: {error_message}")
        
        # Return result
        return response.json()
    
    def delete_agent(self, agent_id: str) -> None:
        """
        Delete agent.
        
        Args:
            agent_id: Agent ID
        """
        # Send request
        response = requests.delete(
            f"{self.api_base_url}/agents/{agent_id}"
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error deleting agent: {error_message}")
    
    def process_query(self, agent_id: str, query: str, 
                     use_planning: bool = False) -> Dict[str, Any]:
        """
        Process a query using an agent.
        
        Args:
            agent_id: Agent ID
            query: Query text
            use_planning: Whether to use planning for complex queries
            
        Returns:
            Query result
        """
        # Prepare request data
        payload = {
            "query": query,
            "use_planning": use_planning
        }
        
        # Send request
        response = requests.post(
            f"{self.api_base_url}/agents/{agent_id}/query",
            json=payload
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error processing query: {error_message}")
        
        # Return result
        return response.json()
    
    def execute_action(self, agent_id: str, action_type: str, 
                      parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute agent action.
        
        Args:
            agent_id: Agent ID
            action_type: Action type
            parameters: Action parameters
            
        Returns:
            Action result
        """
        # Prepare request data
        payload = {
            "action_type": action_type,
            "parameters": parameters or {}
        }
        
        # Send request
        response = requests.post(
            f"{self.api_base_url}/agents/{agent_id}/actions",
            json=payload
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error executing action: {error_message}")
        
        # Return result
        return response.json()
    
    def get_agent_actions(self, agent_id: str, limit: int = 10, 
                         offset: int = 0, action_type: str = None) -> List[Dict[str, Any]]:
        """
        Get agent actions.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of actions to return
            offset: Pagination offset
            action_type: Filter by action type
            
        Returns:
            List of actions
        """
        # Prepare query parameters
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if action_type:
            params["action_type"] = action_type
        
        # Send request
        response = requests.get(
            f"{self.api_base_url}/agents/{agent_id}/actions",
            params=params
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error getting agent actions: {error_message}")
        
        # Return result
        return response.json()
    
    def create_plan(self, agent_id: str, task: str, 
                   constraints: List[str] = None) -> Dict[str, Any]:
        """
        Create a plan for an agent.
        
        Args:
            agent_id: Agent ID
            task: Task description
            constraints: List of constraints
            
        Returns:
            Created plan
        """
        # Prepare request data
        payload = {
            "task": task,
            "constraints": constraints or []
        }
        
        # Send request
        response = requests.post(
            f"{self.api_base_url}/agents/{agent_id}/plans",
            json=payload
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error creating plan: {error_message}")
        
        # Return result
        return response.json()
    
    def execute_plan(self, agent_id: str, plan_id: str) -> Dict[str, Any]:
        """
        Execute a plan.
        
        Args:
            agent_id: Agent ID
            plan_id: Plan ID
            
        Returns:
            Execution result
        """
        # Send request
        response = requests.post(
            f"{self.api_base_url}/plans/{plan_id}/execute",
            params={"agent_id": agent_id}
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error executing plan: {error_message}")
        
        # Return result
        return response.json()
    
    def evaluate_response(self, agent_id: str, query: str, response: str, 
                        context: List[str]) -> Dict[str, Any]:
        """
        Evaluate a response.
        
        Args:
            agent_id: Agent ID
            query: Query text
            response: Response text
            context: List of context texts
            
        Returns:
            Evaluation result
        """
        # Prepare request data
        payload = {
            "query": query,
            "response": response,
            "context": context
        }
        
        # Send request
        response = requests.post(
            f"{self.api_base_url}/agents/{agent_id}/evaluate",
            json=payload
        )
        
        # Check response status
        if response.status_code != 200:
            error_message = self._get_error_message(response)
            raise Exception(f"Error evaluating response: {error_message}")
        
        # Return result
        return response.json()
    
    def _get_error_message(self, response) -> str:
        """Extract error message from response."""
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "detail" in error_data:
                return error_data["detail"]
            return str(error_data)
        except Exception:
            return response.text
