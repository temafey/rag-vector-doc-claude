"""
Query handlers for agent retrieval and search.
"""
from app.application.queries.agent_queries import (
    GetAgentByIdQuery, AgentResult,
    GetAgentByConversationIdQuery,
    ListAgentsQuery, AgentListResult,
    GetAgentActionsQuery, AgentActionsResult,
    GetPlanByIdQuery, PlanResult,
    ListPlansByAgentIdQuery, PlanListResult,
    GetEvaluationByIdQuery, EvaluationResult,
    ListEvaluationsByAgentIdQuery, EvaluationListResult,
    GetImprovementByIdQuery, ImprovementResult,
    GetImprovementByEvaluationIdQuery,
    AvailableActionsResult
)
from app.domain.services.agent import AgentService
from app.infrastructure.repositories.agent import (
    AgentRepository, PlanRepository, EvaluationRepository
)
from app.infrastructure.query_bus import QueryHandler

class GetAgentByIdQueryHandler(QueryHandler[GetAgentByIdQuery, AgentResult]):
    """Handler for GetAgentByIdQuery."""
    
    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository
    
    def handle(self, query: GetAgentByIdQuery) -> AgentResult:
        # Get agent
        agent = self.agent_repository.get_by_id(query.agent_id)
        
        # If agent not found, return None
        if not agent:
            return AgentResult(agent=None)
        
        # Convert agent to dict
        agent_dict = {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "conversation_id": agent.state.conversation_id,
            "created_at": agent.state.created_at.isoformat(),
            "updated_at": agent.state.updated_at.isoformat(),
            "config": agent.config,
            "action_count": len(agent.state.action_history)
        }
        
        return AgentResult(agent=agent_dict)

class GetAgentByConversationIdQueryHandler(QueryHandler[GetAgentByConversationIdQuery, AgentResult]):
    """Handler for GetAgentByConversationIdQuery."""
    
    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository
    
    def handle(self, query: GetAgentByConversationIdQuery) -> AgentResult:
        # Get agent by conversation ID
        agent = self.agent_repository.get_by_conversation_id(query.conversation_id)
        
        # If agent not found, return None
        if not agent:
            return AgentResult(agent=None)
        
        # Convert agent to dict
        agent_dict = {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "conversation_id": agent.state.conversation_id,
            "created_at": agent.state.created_at.isoformat(),
            "updated_at": agent.state.updated_at.isoformat(),
            "config": agent.config,
            "action_count": len(agent.state.action_history)
        }
        
        return AgentResult(agent=agent_dict)

class ListAgentsQueryHandler(QueryHandler[ListAgentsQuery, AgentListResult]):
    """Handler for ListAgentsQuery."""
    
    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository
    
    def handle(self, query: ListAgentsQuery) -> AgentListResult:
        # Get all agents
        agents = self.agent_repository.list_all()
        
        # Convert agents to dicts
        agent_dicts = [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "conversation_id": agent.state.conversation_id,
                "created_at": agent.state.created_at.isoformat(),
                "updated_at": agent.state.updated_at.isoformat(),
                "action_count": len(agent.state.action_history)
            }
            for agent in agents
        ]
        
        return AgentListResult(agents=agent_dicts)

class GetAgentActionsQueryHandler(QueryHandler[GetAgentActionsQuery, AgentActionsResult]):
    """Handler for GetAgentActionsQuery."""
    
    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository
    
    def handle(self, query: GetAgentActionsQuery) -> AgentActionsResult:
        # Get agent
        agent = self.agent_repository.get_by_id(query.agent_id)
        if not agent:
            return AgentActionsResult(actions=[], total=0)
        
        # Get actions
        actions = agent.state.action_history
        
        # Filter by action type if specified
        if query.action_type:
            actions = [action for action in actions if action.action_type == query.action_type]
        
        # Get total count
        total = len(actions)
        
        # Apply pagination
        actions = actions[query.offset:query.offset + query.limit]
        
        # Convert actions to dicts
        action_dicts = [
            {
                "id": action.id,
                "action_type": action.action_type,
                "parameters": action.parameters,
                "created_at": action.created_at.isoformat(),
                "completed_at": action.completed_at.isoformat() if action.completed_at else None,
                "result": action.result,
                "status": action.status
            }
            for action in actions
        ]
        
        return AgentActionsResult(actions=action_dicts, total=total)

class GetPlanByIdQueryHandler(QueryHandler[GetPlanByIdQuery, PlanResult]):
    """Handler for GetPlanByIdQuery."""
    
    def __init__(self, plan_repository: PlanRepository):
        self.plan_repository = plan_repository
    
    def handle(self, query: GetPlanByIdQuery) -> PlanResult:
        # Get plan
        plan = self.plan_repository.get_by_id(query.plan_id)
        
        # If plan not found, return None
        if not plan:
            return PlanResult(plan=None)
        
        # Convert plan to dict
        plan_dict = {
            "id": plan.id,
            "agent_id": plan.agent_id,
            "task": plan.task,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "status": plan.status,
            "steps": [
                {
                    "step_number": step.step_number,
                    "action_type": step.action_type,
                    "description": step.description,
                    "parameters": step.parameters,
                    "dependencies": step.dependencies,
                    "status": step.status,
                    "result": step.result
                }
                for step in plan.steps
            ]
        }
        
        return PlanResult(plan=plan_dict)

class ListPlansByAgentIdQueryHandler(QueryHandler[ListPlansByAgentIdQuery, PlanListResult]):
    """Handler for ListPlansByAgentIdQuery."""
    
    def __init__(self, plan_repository: PlanRepository):
        self.plan_repository = plan_repository
    
    def handle(self, query: ListPlansByAgentIdQuery) -> PlanListResult:
        # Get plans for agent
        plans = self.plan_repository.list_by_agent_id(query.agent_id)
        
        # Convert plans to dicts
        plan_dicts = [
            {
                "id": plan.id,
                "agent_id": plan.agent_id,
                "task": plan.task,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat(),
                "status": plan.status,
                "step_count": len(plan.steps)
            }
            for plan in plans
        ]
        
        return PlanListResult(plans=plan_dicts)

class GetEvaluationByIdQueryHandler(QueryHandler[GetEvaluationByIdQuery, EvaluationResult]):
    """Handler for GetEvaluationByIdQuery."""
    
    def __init__(self, evaluation_repository: EvaluationRepository):
        self.evaluation_repository = evaluation_repository
    
    def handle(self, query: GetEvaluationByIdQuery) -> EvaluationResult:
        # Get evaluation
        evaluation = self.evaluation_repository.get_evaluation_by_id(query.evaluation_id)
        
        # If evaluation not found, return None
        if not evaluation:
            return EvaluationResult(evaluation=None)
        
        # Convert evaluation to dict
        evaluation_dict = {
            "id": evaluation.id,
            "agent_id": evaluation.agent_id,
            "response_id": evaluation.response_id,
            "query": evaluation.query,
            "response": evaluation.response,
            "context": evaluation.context,
            "overall_score": evaluation.overall_score,
            "created_at": evaluation.created_at.isoformat(),
            "scores": {
                criterion: {
                    "score": score.score,
                    "reason": score.reason
                }
                for criterion, score in evaluation.scores.items()
            }
        }
        
        return EvaluationResult(evaluation=evaluation_dict)

class ListEvaluationsByAgentIdQueryHandler(QueryHandler[ListEvaluationsByAgentIdQuery, EvaluationListResult]):
    """Handler for ListEvaluationsByAgentIdQuery."""
    
    def __init__(self, evaluation_repository: EvaluationRepository):
        self.evaluation_repository = evaluation_repository
    
    def handle(self, query: ListEvaluationsByAgentIdQuery) -> EvaluationListResult:
        # Get evaluations for agent
        all_evaluations = self.evaluation_repository.list_evaluations(query.agent_id)
        
        # Get total count
        total = len(all_evaluations)
        
        # Apply pagination
        evaluations = all_evaluations[query.offset:query.offset + query.limit]
        
        # Convert evaluations to dicts
        evaluation_dicts = [
            {
                "id": evaluation.id,
                "agent_id": evaluation.agent_id,
                "response_id": evaluation.response_id,
                "query": evaluation.query,
                "overall_score": evaluation.overall_score,
                "created_at": evaluation.created_at.isoformat()
            }
            for evaluation in evaluations
        ]
        
        return EvaluationListResult(evaluations=evaluation_dicts, total=total)

class GetImprovementByIdQueryHandler(QueryHandler[GetImprovementByIdQuery, ImprovementResult]):
    """Handler for GetImprovementByIdQuery."""
    
    def __init__(self, evaluation_repository: EvaluationRepository):
        self.evaluation_repository = evaluation_repository
    
    def handle(self, query: GetImprovementByIdQuery) -> ImprovementResult:
        # Get improvement
        improvement = self.evaluation_repository.get_improvement_by_id(query.improvement_id)
        
        # If improvement not found, return None
        if not improvement:
            return ImprovementResult(improvement=None)
        
        # Convert improvement to dict
        improvement_dict = {
            "id": improvement.id,
            "evaluation_id": improvement.evaluation_id,
            "original_response": improvement.original_response,
            "improved_response": improvement.improved_response,
            "created_at": improvement.created_at.isoformat(),
            "suggestions": [
                {
                    "criterion": suggestion.criterion,
                    "suggestion": suggestion.suggestion,
                    "priority": suggestion.priority
                }
                for suggestion in improvement.suggestions
            ]
        }
        
        return ImprovementResult(improvement=improvement_dict)

class GetImprovementByEvaluationIdQueryHandler(QueryHandler[GetImprovementByEvaluationIdQuery, ImprovementResult]):
    """Handler for GetImprovementByEvaluationIdQuery."""
    
    def __init__(self, evaluation_repository: EvaluationRepository):
        self.evaluation_repository = evaluation_repository
    
    def handle(self, query: GetImprovementByEvaluationIdQuery) -> ImprovementResult:
        # Get improvement by evaluation ID
        improvement = self.evaluation_repository.get_improvement_by_evaluation_id(query.evaluation_id)
        
        # If improvement not found, return None
        if not improvement:
            return ImprovementResult(improvement=None)
        
        # Convert improvement to dict
        improvement_dict = {
            "id": improvement.id,
            "evaluation_id": improvement.evaluation_id,
            "original_response": improvement.original_response,
            "improved_response": improvement.improved_response,
            "created_at": improvement.created_at.isoformat(),
            "suggestions": [
                {
                    "criterion": suggestion.criterion,
                    "suggestion": suggestion.suggestion,
                    "priority": suggestion.priority
                }
                for suggestion in improvement.suggestions
            ]
        }
        
        return ImprovementResult(improvement=improvement_dict)

class GetAvailableActionsQueryHandler:
    """Handler for getting available agent actions."""
    
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service
    
    def handle(self, agent_id: str) -> AvailableActionsResult:
        # Get available actions
        registry = self.agent_service.action_registry
        actions = []
        
        for action_type in registry.list_actions():
            metadata = registry.get_metadata(action_type)
            actions.append({
                "action_type": action_type,
                "description": metadata.get("description", "")
            })
        
        return AvailableActionsResult(actions=actions)
