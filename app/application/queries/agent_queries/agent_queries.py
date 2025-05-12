"""
Queries for agent retrieval and search.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class GetAgentByIdQuery(BaseModel):
    """Query to get agent by ID."""
    agent_id: str

@dataclass
class AgentResult:
    """Result of GetAgentByIdQuery execution."""
    agent: Optional[Dict[str, Any]]  # Using dict instead of Agent for simplicity in API

class GetAgentByConversationIdQuery(BaseModel):
    """Query to get agent by conversation ID."""
    conversation_id: str

class ListAgentsQuery(BaseModel):
    """Query to list all agents."""
    pass

@dataclass
class AgentListResult:
    """Result of ListAgentsQuery execution."""
    agents: List[Dict[str, Any]]

class GetAgentActionsQuery(BaseModel):
    """Query to get agent actions."""
    agent_id: str
    limit: int = 10
    offset: int = 0
    action_type: Optional[str] = None

@dataclass
class AgentActionsResult:
    """Result of GetAgentActionsQuery execution."""
    actions: List[Dict[str, Any]]
    total: int

class GetPlanByIdQuery(BaseModel):
    """Query to get plan by ID."""
    plan_id: str

@dataclass
class PlanResult:
    """Result of GetPlanByIdQuery execution."""
    plan: Optional[Dict[str, Any]]

class ListPlansByAgentIdQuery(BaseModel):
    """Query to list plans by agent ID."""
    agent_id: str

@dataclass
class PlanListResult:
    """Result of ListPlansByAgentIdQuery execution."""
    plans: List[Dict[str, Any]]

class GetEvaluationByIdQuery(BaseModel):
    """Query to get evaluation by ID."""
    evaluation_id: str

@dataclass
class EvaluationResult:
    """Result of GetEvaluationByIdQuery execution."""
    evaluation: Optional[Dict[str, Any]]

class ListEvaluationsByAgentIdQuery(BaseModel):
    """Query to list evaluations by agent ID."""
    agent_id: str
    limit: int = 10
    offset: int = 0

@dataclass
class EvaluationListResult:
    """Result of ListEvaluationsByAgentIdQuery execution."""
    evaluations: List[Dict[str, Any]]
    total: int

class GetImprovementByIdQuery(BaseModel):
    """Query to get improvement by ID."""
    improvement_id: str

@dataclass
class ImprovementResult:
    """Result of GetImprovementByIdQuery execution."""
    improvement: Optional[Dict[str, Any]]

class GetImprovementByEvaluationIdQuery(BaseModel):
    """Query to get improvement by evaluation ID."""
    evaluation_id: str

@dataclass
class AvailableActionsResult:
    """Result of query for available actions."""
    actions: List[Dict[str, str]]  # List of {action_type, description}
