"""
Repository for agent storage and retrieval.
"""
from typing import Dict, Optional, List
import json
import os
from app.domain.models.agent import Agent, AgentState

class AgentRepository:
    """Repository for working with agents."""
    
    def __init__(self, storage_path: str):
        """
        Initialize repository.
        
        Args:
            storage_path: Path to directory for agent storage
        """
        self.agents_path = os.path.join(storage_path, "agents")
        os.makedirs(self.agents_path, exist_ok=True)
    
    def _get_agent_path(self, agent_id: str) -> str:
        """Get path to agent file."""
        return os.path.join(self.agents_path, f"{agent_id}.json")
    
    def save(self, agent: Agent) -> None:
        """
        Save agent.
        
        Args:
            agent: Agent to save
        """
        # Create agent directory if it doesn't exist
        os.makedirs(self.agents_path, exist_ok=True)
        
        # Convert agent to dict
        agent_dict = {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "config": agent.config,
            "state": agent.state.to_dict()
        }
        
        # Save agent to file
        agent_path = self._get_agent_path(agent.id)
        with open(agent_path, "w", encoding="utf-8") as f:
            json.dump(agent_dict, f, ensure_ascii=False, indent=2)
    
    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent or None if agent not found
        """
        agent_path = self._get_agent_path(agent_id)
        
        # Check if file exists
        if not os.path.exists(agent_path):
            return None
        
        # Load agent from file
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_dict = json.load(f)
        
        # Create AgentState
        state = AgentState.from_dict(agent_dict["state"])
        
        # Create Agent
        agent = Agent(
            id=agent_dict["id"],
            name=agent_dict["name"],
            description=agent_dict["description"],
            config=agent_dict["config"],
            state=state
        )
        
        return agent
    
    def delete(self, agent_id: str) -> None:
        """
        Delete agent.
        
        Args:
            agent_id: Agent ID
        """
        agent_path = self._get_agent_path(agent_id)
        
        # Check if file exists
        if os.path.exists(agent_path):
            os.remove(agent_path)
    
    def list_all(self) -> List[Agent]:
        """
        Get list of all agents.
        
        Returns:
            List of agents
        """
        agents = []
        
        # Check if agents directory exists
        if not os.path.exists(self.agents_path):
            return agents
        
        # Iterate through all files in agents directory
        for filename in os.listdir(self.agents_path):
            if filename.endswith(".json"):
                agent_id = filename[:-5]  # Remove .json extension
                agent = self.get_by_id(agent_id)
                if agent:
                    agents.append(agent)
        
        return agents
    
    def get_by_conversation_id(self, conversation_id: str) -> Optional[Agent]:
        """
        Get agent by conversation ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Agent or None if no agent found for conversation
        """
        # Get all agents
        agents = self.list_all()
        
        # Find agent with matching conversation ID
        for agent in agents:
            if agent.state.conversation_id == conversation_id:
                return agent
        
        return None
