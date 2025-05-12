"""
Domain events related to agent operations.
"""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

class AgentCreatedEvent(BaseModel):
    """Event generated when an agent is created."""
    agent_id: str
    name: str
    conversation_id: str

class AgentActionStartedEvent(BaseModel):
    """Event generated when an agent action is started."""
    agent_id: str
    action_id: str
    action_type: str
    parameters: Dict[str, Any]

class AgentActionCompletedEvent(BaseModel):
    """Event generated when an agent action is completed."""
    agent_id: str
    action_id: str
    action_type: str
    result: Any

class AgentActionFailedEvent(BaseModel):
    """Event generated when an agent action fails."""
    agent_id: str
    action_id: str
    action_type: str
    error: Any

class PlanCreatedEvent(BaseModel):
    """Event generated when a plan is created."""
    agent_id: str
    plan_id: str
    task: str
    step_count: int

class PlanStepCompletedEvent(BaseModel):
    """Event generated when a plan step is completed."""
    agent_id: str
    plan_id: str
    step_number: int
    action_type: str
    result: Any

class PlanCompletedEvent(BaseModel):
    """Event generated when a plan is completed."""
    agent_id: str
    plan_id: str
    task: str

class ResponseEvaluatedEvent(BaseModel):
    """Event generated when a response is evaluated."""
    agent_id: str
    evaluation_id: str
    response_id: str
    overall_score: float
    needs_improvement: bool

class ResponseImprovedEvent(BaseModel):
    """Event generated when a response is improved."""
    agent_id: str
    evaluation_id: str
    improvement_id: str
    original_response: str
    improved_response: str
