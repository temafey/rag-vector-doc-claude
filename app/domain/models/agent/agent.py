"""
Agent model for RAG system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import datetime
import uuid

@dataclass
class AgentAction:
    """Value object representing an action performed by the agent."""
    id: str
    action_type: str
    parameters: Dict[str, Any]
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    completed_at: Optional[datetime.datetime] = None
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, completed, failed
    
    @classmethod
    def create(cls, action_type: str, parameters: Dict[str, Any]) -> 'AgentAction':
        """Factory method to create a new action."""
        return cls(
            id=str(uuid.uuid4()),
            action_type=action_type,
            parameters=parameters
        )
    
    def complete(self, result: Any) -> None:
        """Mark action as completed with result."""
        self.result = result
        self.status = "completed"
        self.completed_at = datetime.datetime.now()
    
    def fail(self, error: Any) -> None:
        """Mark action as failed with error."""
        self.result = error
        self.status = "failed"
        self.completed_at = datetime.datetime.now()
    
    def is_pending(self) -> bool:
        """Check if action is pending."""
        return self.status == "pending"
    
    def is_completed(self) -> bool:
        """Check if action is completed."""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if action is failed."""
        return self.status == "failed"

@dataclass
class AgentState:
    """Entity representing agent state."""
    id: str
    conversation_id: str
    memory: Dict[str, Any] = field(default_factory=dict)
    action_history: List[AgentAction] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    @classmethod
    def create(cls, conversation_id: str) -> 'AgentState':
        """Factory method to create a new agent state."""
        return cls(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id
        )
    
    def add_action(self, action: AgentAction) -> None:
        """Add action to history."""
        self.action_history.append(action)
        self.updated_at = datetime.datetime.now()
    
    def set_memory(self, key: str, value: Any) -> None:
        """Set memory value."""
        self.memory[key] = value
        self.updated_at = datetime.datetime.now()
    
    def get_memory(self, key: str, default: Any = None) -> Any:
        """Get memory value."""
        return self.memory.get(key, default)
    
    def get_last_action(self) -> Optional[AgentAction]:
        """Get last action from history."""
        if not self.action_history:
            return None
        return self.action_history[-1]
    
    def get_actions_by_type(self, action_type: str) -> List[AgentAction]:
        """Get actions by type."""
        return [action for action in self.action_history if action.action_type == action_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "memory": self.memory,
            "action_history": [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "parameters": action.parameters,
                    "created_at": action.created_at.isoformat(),
                    "completed_at": action.completed_at.isoformat() if action.completed_at else None,
                    "result": action.result,
                    "status": action.status
                }
                for action in self.action_history
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Create state from dictionary after deserialization."""
        state = cls(
            id=data["id"],
            conversation_id=data["conversation_id"],
            memory=data["memory"],
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.datetime.fromisoformat(data["updated_at"])
        )
        
        # Recreate action history
        for action_data in data["action_history"]:
            action = AgentAction(
                id=action_data["id"],
                action_type=action_data["action_type"],
                parameters=action_data["parameters"],
                created_at=datetime.datetime.fromisoformat(action_data["created_at"]),
                completed_at=datetime.datetime.fromisoformat(action_data["completed_at"]) if action_data["completed_at"] else None,
                result=action_data["result"],
                status=action_data["status"]
            )
            state.action_history.append(action)
        
        return state

@dataclass
class Agent:
    """Entity representing an agent in the RAG system."""
    id: str
    name: str
    description: str
    state: AgentState
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, name: str, description: str, conversation_id: str, config: Dict[str, Any] = None) -> 'Agent':
        """Factory method to create a new agent."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            state=AgentState.create(conversation_id),
            config=config or {}
        )
    
    def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> AgentAction:
        """Execute action (placeholder - actual execution will be handled by service)."""
        action = AgentAction.create(action_type, parameters)
        self.state.add_action(action)
        return action
    
    def update_state(self, state: AgentState) -> None:
        """Update agent state."""
        self.state = state
