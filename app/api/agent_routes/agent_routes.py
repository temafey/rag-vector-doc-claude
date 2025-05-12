"""
FastAPI routes for agent operations.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from app.application.commands import (
    CreateAgentCommand,
    DeleteAgentCommand,
    ExecuteAgentActionCommand,
    ProcessAgentQueryCommand,
    CreatePlanCommand,
    ExecutePlanCommand,
    EvaluateResponseCommand,
    ImproveResponseCommand
)
from app.application.queries import (
    GetAgentByIdQuery,
    GetAgentByConversationIdQuery,
    ListAgentsQuery,
    GetAgentActionsQuery,
    GetPlanByIdQuery,
    ListPlansByAgentIdQuery,
    GetEvaluationByIdQuery,
    ListEvaluationsByAgentIdQuery,
    GetImprovementByIdQuery,
    GetImprovementByEvaluationIdQuery
)
from app.infrastructure.command_bus import command_bus
from app.infrastructure.query_bus import query_bus

# Data models
from pydantic import BaseModel

class CreateAgentRequest(BaseModel):
    """Request to create an agent."""
    name: str
    description: str
    conversation_id: str
    config: Dict[str, Any] = {}

class AgentResponse(BaseModel):
    """Response with agent details."""
    id: str
    name: str
    description: str
    conversation_id: str
    created_at: str
    updated_at: str
    config: Dict[str, Any]
    action_count: int

class ExecuteActionRequest(BaseModel):
    """Request to execute an agent action."""
    action_type: str
    parameters: Dict[str, Any] = {}

class ActionResponse(BaseModel):
    """Response with action result."""
    id: str
    action_type: str
    parameters: Dict[str, Any]
    result: Any
    status: str
    created_at: str
    completed_at: Optional[str] = None

class ProcessQueryRequest(BaseModel):
    """Request to process a query using an agent."""
    query: str
    use_planning: bool = False

class AgentQueryResponse(BaseModel):
    """Response with agent query result."""
    response: str
    sources: List[Dict[str, Any]]
    improved: bool
    evaluation: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None

class CreatePlanRequest(BaseModel):
    """Request to create a plan."""
    task: str
    constraints: List[str] = []

class PlanResponse(BaseModel):
    """Response with plan details."""
    id: str
    agent_id: str
    task: str
    created_at: str
    updated_at: str
    status: str
    steps: List[Dict[str, Any]]

class EvaluateResponseRequest(BaseModel):
    """Request to evaluate a response."""
    query: str
    response: str
    context: List[str]

class EvaluationResponse(BaseModel):
    """Response with evaluation result."""
    id: str
    agent_id: str
    response_id: str
    query: str
    response: str
    overall_score: float
    created_at: str
    scores: Dict[str, Dict[str, Any]]

class ImprovementResponse(BaseModel):
    """Response with improvement result."""
    id: str
    evaluation_id: str
    original_response: str
    improved_response: str
    created_at: str
    suggestions: List[Dict[str, Any]]

# Create router
router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("", response_model=AgentResponse)
async def create_agent(request: CreateAgentRequest):
    """Create a new agent."""
    command = CreateAgentCommand(
        name=request.name,
        description=request.description,
        conversation_id=request.conversation_id,
        config=request.config
    )
    
    result = command_bus.dispatch(command)
    
    # Get created agent
    query = GetAgentByIdQuery(agent_id=result.agent_id)
    agent_result = query_bus.dispatch(query)
    
    if not agent_result.agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent_result.agent

@router.get("", response_model=List[AgentResponse])
async def list_agents():
    """Get list of all agents."""
    query = ListAgentsQuery()
    result = query_bus.dispatch(query)
    
    return result.agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent by ID."""
    query = GetAgentByIdQuery(agent_id=agent_id)
    result = query_bus.dispatch(query)
    
    if not result.agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return result.agent

@router.get("/conversation/{conversation_id}", response_model=AgentResponse)
async def get_agent_by_conversation(conversation_id: str):
    """Get agent by conversation ID."""
    query = GetAgentByConversationIdQuery(conversation_id=conversation_id)
    result = query_bus.dispatch(query)
    
    if not result.agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return result.agent

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete agent."""
    command = DeleteAgentCommand(agent_id=agent_id)
    command_bus.dispatch(command)
    
    return {"message": "Agent deleted"}

@router.post("/{agent_id}/actions", response_model=ActionResponse)
async def execute_action(agent_id: str, request: ExecuteActionRequest):
    """Execute agent action."""
    command = ExecuteAgentActionCommand(
        agent_id=agent_id,
        action_type=request.action_type,
        parameters=request.parameters
    )
    
    result = command_bus.dispatch(command)
    
    return {
        "id": result.action_id,
        "action_type": result.action_type,
        "parameters": result.parameters,
        "result": result.result,
        "status": result.status,
        "created_at": None,  # These would come from the actual action object
        "completed_at": None
    }

@router.get("/{agent_id}/actions", response_model=List[ActionResponse])
async def get_agent_actions(
    agent_id: str,
    limit: int = 10,
    offset: int = 0,
    action_type: Optional[str] = None
):
    """Get agent actions."""
    query = GetAgentActionsQuery(
        agent_id=agent_id,
        limit=limit,
        offset=offset,
        action_type=action_type
    )
    
    result = query_bus.dispatch(query)
    
    return result.actions

@router.post("/{agent_id}/query", response_model=AgentQueryResponse)
async def process_query(agent_id: str, request: ProcessQueryRequest):
    """Process a query using an agent."""
    command = ProcessAgentQueryCommand(
        agent_id=agent_id,
        query=request.query,
        use_planning=request.use_planning
    )
    
    result = command_bus.dispatch(command)
    
    return {
        "response": result.response,
        "sources": result.sources,
        "improved": result.improved,
        "evaluation": result.evaluation,
        "plan": result.plan
    }

@router.post("/{agent_id}/plans", response_model=PlanResponse)
async def create_plan(agent_id: str, request: CreatePlanRequest):
    """Create a plan for agent."""
    command = CreatePlanCommand(
        agent_id=agent_id,
        task=request.task,
        constraints=request.constraints
    )
    
    result = command_bus.dispatch(command)
    
    # Get created plan
    query = GetPlanByIdQuery(plan_id=result.plan_id)
    plan_result = query_bus.dispatch(query)
    
    if not plan_result.plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return plan_result.plan

@router.get("/{agent_id}/plans", response_model=List[Dict[str, Any]])
async def list_plans(agent_id: str):
    """Get list of plans for agent."""
    query = ListPlansByAgentIdQuery(agent_id=agent_id)
    result = query_bus.dispatch(query)
    
    return result.plans

@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    """Get plan by ID."""
    query = GetPlanByIdQuery(plan_id=plan_id)
    result = query_bus.dispatch(query)
    
    if not result.plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return result.plan

@router.post("/plans/{plan_id}/execute")
async def execute_plan(plan_id: str, agent_id: str):
    """Execute a plan."""
    command = ExecutePlanCommand(
        agent_id=agent_id,
        plan_id=plan_id
    )
    
    result = command_bus.dispatch(command)
    
    return {
        "plan_id": result.plan_id,
        "status": result.status,
        "completed_steps": result.completed_steps,
        "results": result.results
    }

@router.post("/{agent_id}/evaluate", response_model=Dict[str, Any])
async def evaluate_response(agent_id: str, request: EvaluateResponseRequest):
    """Evaluate a response."""
    command = EvaluateResponseCommand(
        agent_id=agent_id,
        query=request.query,
        response=request.response,
        context=request.context
    )
    
    result = command_bus.dispatch(command)
    
    return {
        "evaluation_id": result.evaluation_id,
        "overall_score": result.overall_score,
        "criterion_scores": result.criterion_scores,
        "needs_improvement": result.needs_improvement
    }

@router.get("/{agent_id}/evaluations", response_model=List[Dict[str, Any]])
async def list_evaluations(
    agent_id: str,
    limit: int = 10,
    offset: int = 0
):
    """Get list of evaluations for agent."""
    query = ListEvaluationsByAgentIdQuery(
        agent_id=agent_id,
        limit=limit,
        offset=offset
    )
    
    result = query_bus.dispatch(query)
    
    return result.evaluations

@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: str):
    """Get evaluation by ID."""
    query = GetEvaluationByIdQuery(evaluation_id=evaluation_id)
    result = query_bus.dispatch(query)
    
    if not result.evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return result.evaluation

@router.post("/evaluations/{evaluation_id}/improve", response_model=ImprovementResponse)
async def improve_response(evaluation_id: str, agent_id: str):
    """Improve a response based on evaluation."""
    command = ImproveResponseCommand(
        agent_id=agent_id,
        evaluation_id=evaluation_id
    )
    
    result = command_bus.dispatch(command)
    
    return {
        "id": result.improvement_id,
        "evaluation_id": result.evaluation_id,
        "original_response": result.original_response,
        "improved_response": result.improved_response,
        "created_at": None,  # This would come from the actual improvement object
        "suggestions": result.suggestions
    }

@router.get("/improvements/{improvement_id}", response_model=ImprovementResponse)
async def get_improvement(improvement_id: str):
    """Get improvement by ID."""
    query = GetImprovementByIdQuery(improvement_id=improvement_id)
    result = query_bus.dispatch(query)
    
    if not result.improvement:
        raise HTTPException(status_code=404, detail="Improvement not found")
    
    return result.improvement

@router.get("/evaluations/{evaluation_id}/improvement", response_model=ImprovementResponse)
async def get_improvement_by_evaluation(evaluation_id: str):
    """Get improvement by evaluation ID."""
    query = GetImprovementByEvaluationIdQuery(evaluation_id=evaluation_id)
    result = query_bus.dispatch(query)
    
    if not result.improvement:
        raise HTTPException(status_code=404, detail="Improvement not found")
    
    return result.improvement
