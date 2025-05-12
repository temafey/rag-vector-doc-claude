"""
Commands for agent management.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class CreateAgentCommand(BaseModel):
    """Command to create a new agent."""
    name: str
    description: str
    conversation_id: str
    config: Dict[str, Any] = {}

@dataclass
class CreateAgentResult:
    """Result of CreateAgentCommand execution."""
    agent_id: str
    name: str
    conversation_id: str

class DeleteAgentCommand(BaseModel):
    """Command to delete an agent."""
    agent_id: str

class ExecuteAgentActionCommand(BaseModel):
    """Command to execute an agent action."""
    agent_id: str
    action_type: str
    parameters: Dict[str, Any] = {}

@dataclass
class ExecuteAgentActionResult:
    """Result of ExecuteAgentActionCommand execution."""
    agent_id: str
    action_id: str
    action_type: str
    parameters: Dict[str, Any]
    result: Any
    status: str

class ProcessAgentQueryCommand(BaseModel):
    """Command to process a query using an agent."""
    agent_id: str
    query: str
    use_planning: bool = False

@dataclass
class ProcessAgentQueryResult:
    """Result of ProcessAgentQueryCommand execution."""
    agent_id: str
    query: str
    response: str
    sources: List[Dict[str, Any]]
    improved: bool
    evaluation: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None

class CreatePlanCommand(BaseModel):
    """Command to create a plan for an agent."""
    agent_id: str
    task: str
    constraints: List[str] = []

@dataclass
class CreatePlanResult:
    """Result of CreatePlanCommand execution."""
    agent_id: str
    plan_id: str
    task: str
    step_count: int

class ExecutePlanCommand(BaseModel):
    """Command to execute a plan."""
    agent_id: str
    plan_id: str

@dataclass
class ExecutePlanResult:
    """Result of ExecutePlanCommand execution."""
    agent_id: str
    plan_id: str
    task: str
    status: str
    completed_steps: List[int]
    results: Dict[int, Any]

class EvaluateResponseCommand(BaseModel):
    """Command to evaluate a response."""
    agent_id: str
    query: str
    response: str
    context: List[str]

@dataclass
class EvaluateResponseResult:
    """Result of EvaluateResponseCommand execution."""
    agent_id: str
    evaluation_id: str
    overall_score: float
    criterion_scores: Dict[str, Dict[str, Any]]
    needs_improvement: bool

class ImproveResponseCommand(BaseModel):
    """Command to improve a response based on evaluation."""
    agent_id: str
    evaluation_id: str

@dataclass
class ImproveResponseResult:
    """Result of ImproveResponseCommand execution."""
    agent_id: str
    evaluation_id: str
    improvement_id: str
    original_response: str
    improved_response: str
    suggestions: List[Dict[str, Any]]
