"""
Results for agent commands.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class CreateAgentResult:
    """Result of CreateAgentCommand execution."""
    agent_id: str
    name: str
    conversation_id: str

@dataclass
class ExecuteAgentActionResult:
    """Result of ExecuteAgentActionCommand execution."""
    agent_id: str
    action_id: str
    action_type: str
    parameters: Dict[str, Any]
    result: Any
    status: str

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

@dataclass
class CreatePlanResult:
    """Result of CreatePlanCommand execution."""
    agent_id: str
    plan_id: str
    task: str
    step_count: int

@dataclass
class ExecutePlanResult:
    """Result of ExecutePlanCommand execution."""
    agent_id: str
    plan_id: str
    task: str
    status: str
    completed_steps: List[int]
    results: Dict[int, Any]

@dataclass
class EvaluateResponseResult:
    """Result of EvaluateResponseCommand execution."""
    agent_id: str
    evaluation_id: str
    overall_score: float
    criterion_scores: Dict[str, Dict[str, Any]]
    needs_improvement: bool

@dataclass
class ImproveResponseResult:
    """Result of ImproveResponseCommand execution."""
    agent_id: str
    evaluation_id: str
    improvement_id: str
    original_response: str
    improved_response: str
    suggestions: List[Dict[str, Any]]
