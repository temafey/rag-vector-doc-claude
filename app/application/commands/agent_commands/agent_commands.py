"""
Commands for agent management.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class CreateAgentCommand(BaseModel):
    """Command to create a new agent."""
    name: str
    description: str
    conversation_id: str
    config: Dict[str, Any] = {}

class DeleteAgentCommand(BaseModel):
    """Command to delete an agent."""
    agent_id: str

class ExecuteAgentActionCommand(BaseModel):
    """Command to execute an agent action."""
    agent_id: str
    action_type: str
    parameters: Dict[str, Any] = {}

class ProcessAgentQueryCommand(BaseModel):
    """Command to process a query using an agent."""
    agent_id: str
    query: str
    use_planning: bool = False

class CreatePlanCommand(BaseModel):
    """Command to create a plan for an agent."""
    agent_id: str
    task: str
    constraints: List[str] = []

class ExecutePlanCommand(BaseModel):
    """Command to execute a plan."""
    agent_id: str
    plan_id: str

class EvaluateResponseCommand(BaseModel):
    """Command to evaluate a response."""
    agent_id: str
    query: str
    response: str
    context: List[str]

class ImproveResponseCommand(BaseModel):
    """Command to improve a response based on evaluation."""
    agent_id: str
    evaluation_id: str
