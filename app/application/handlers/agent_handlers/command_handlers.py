"""
Command handlers for agent operations.
"""
from app.application.commands.agent_commands import (
    CreateAgentCommand,
    DeleteAgentCommand,
    ExecuteAgentActionCommand,
    ProcessAgentQueryCommand,
    CreatePlanCommand,
    ExecutePlanCommand,
    EvaluateResponseCommand,
    ImproveResponseCommand
)
from app.application.results.agent_results import (
    CreateAgentResult,
    ExecuteAgentActionResult,
    ProcessAgentQueryResult,
    CreatePlanResult,
    ExecutePlanResult,
    EvaluateResponseResult,
    ImproveResponseResult
)
from app.domain.services.agent import (
    AgentService, ActionRegistry, PlanningService, EvaluationService
)
from app.infrastructure.repositories.agent import (
    AgentRepository, PlanRepository, EvaluationRepository
)
from app.infrastructure.command_bus import CommandHandler

class CreateAgentCommandHandler(CommandHandler[CreateAgentCommand, CreateAgentResult]):
    """Handler for CreateAgentCommand."""
    
    def __init__(
        self,
        agent_service: AgentService,
        agent_repository: AgentRepository
    ):
        self.agent_service = agent_service
        self.agent_repository = agent_repository
    
    def handle(self, command: CreateAgentCommand) -> CreateAgentResult:
        # Create agent
        agent = self.agent_service.create_agent(
            name=command.name,
            description=command.description,
            conversation_id=command.conversation_id,
            config=command.config
        )
        
        # Save agent
        self.agent_repository.save(agent)
        
        return CreateAgentResult(
            agent_id=agent.id,
            name=agent.name,
            conversation_id=agent.state.conversation_id
        )

class DeleteAgentCommandHandler(CommandHandler[DeleteAgentCommand, None]):
    """Handler for DeleteAgentCommand."""
    
    def __init__(
        self,
        agent_repository: AgentRepository
    ):
        self.agent_repository = agent_repository
    
    def handle(self, command: DeleteAgentCommand) -> None:
        # Delete agent
        self.agent_repository.delete(command.agent_id)

class ExecuteAgentActionCommandHandler(CommandHandler[ExecuteAgentActionCommand, ExecuteAgentActionResult]):
    """Handler for ExecuteAgentActionCommand."""
    
    def __init__(
        self,
        agent_service: AgentService,
        agent_repository: AgentRepository
    ):
        self.agent_service = agent_service
        self.agent_repository = agent_repository
    
    def handle(self, command: ExecuteAgentActionCommand) -> ExecuteAgentActionResult:
        # Get agent
        agent = self.agent_repository.get_by_id(command.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {command.agent_id}")
        
        # Execute action
        action = self.agent_service.execute_action(
            agent=agent,
            action_type=command.action_type,
            parameters=command.parameters
        )
        
        # Save updated agent
        self.agent_repository.save(agent)
        
        return ExecuteAgentActionResult(
            agent_id=agent.id,
            action_id=action.id,
            action_type=action.action_type,
            parameters=action.parameters,
            result=action.result,
            status=action.status
        )

class ProcessAgentQueryCommandHandler(CommandHandler[ProcessAgentQueryCommand, ProcessAgentQueryResult]):
    """Handler for ProcessAgentQueryCommand."""
    
    def __init__(
        self,
        agent_service: AgentService,
        planning_service: PlanningService,
        agent_repository: AgentRepository
    ):
        self.agent_service = agent_service
        self.planning_service = planning_service
        self.agent_repository = agent_repository
    
    def handle(self, command: ProcessAgentQueryCommand) -> ProcessAgentQueryResult:
        # Get agent
        agent = self.agent_repository.get_by_id(command.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {command.agent_id}")
        
        # Process query
        if command.use_planning:
            # Use planning for complex queries
            result = self.planning_service.process_complex_query(
                agent=agent,
                query=command.query
            )
        else:
            # Use simple agent processing for basic queries
            result = self.agent_service.process_query(
                agent=agent,
                query=command.query
            )
        
        # Save updated agent
        self.agent_repository.save(agent)
        
        # Create result
        return ProcessAgentQueryResult(
            agent_id=agent.id,
            query=command.query,
            response=result.get("response", ""),
            sources=result.get("sources", []),
            improved=result.get("improved", False),
            evaluation=result.get("evaluation"),
            plan=result.get("plan")
        )

class CreatePlanCommandHandler(CommandHandler[CreatePlanCommand, CreatePlanResult]):
    """Handler for CreatePlanCommand."""
    
    def __init__(
        self,
        planning_service: PlanningService,
        agent_repository: AgentRepository,
        plan_repository: PlanRepository
    ):
        self.planning_service = planning_service
        self.agent_repository = agent_repository
        self.plan_repository = plan_repository
    
    def handle(self, command: CreatePlanCommand) -> CreatePlanResult:
        # Get agent
        agent = self.agent_repository.get_by_id(command.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {command.agent_id}")
        
        # Create plan
        plan = self.planning_service.create_plan(
            agent=agent,
            task=command.task,
            constraints=command.constraints
        )
        
        # Save plan
        self.plan_repository.save(plan)
        
        # Save updated agent
        self.agent_repository.save(agent)
        
        return CreatePlanResult(
            agent_id=agent.id,
            plan_id=plan.id,
            task=plan.task,
            step_count=len(plan.steps)
        )

class ExecutePlanCommandHandler(CommandHandler[ExecutePlanCommand, ExecutePlanResult]):
    """Handler for ExecutePlanCommand."""
    
    def __init__(
        self,
        planning_service: PlanningService,
        agent_repository: AgentRepository,
        plan_repository: PlanRepository
    ):
        self.planning_service = planning_service
        self.agent_repository = agent_repository
        self.plan_repository = plan_repository
    
    def handle(self, command: ExecutePlanCommand) -> ExecutePlanResult:
        # Get agent
        agent = self.agent_repository.get_by_id(command.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {command.agent_id}")
        
        # Get plan
        plan = self.plan_repository.get_by_id(command.plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {command.plan_id}")
        
        # Execute plan
        execution_result = self.planning_service.execute_plan(
            agent=agent,
            plan=plan
        )
        
        # Save updated plan
        self.plan_repository.save(plan)
        
        # Save updated agent
        self.agent_repository.save(agent)
        
        return ExecutePlanResult(
            agent_id=agent.id,
            plan_id=plan.id,
            task=plan.task,
            status=plan.status,
            completed_steps=execution_result.get("completed_steps", []),
            results=execution_result.get("results", {})
        )

class EvaluateResponseCommandHandler(CommandHandler[EvaluateResponseCommand, EvaluateResponseResult]):
    """Handler for EvaluateResponseCommand."""
    
    def __init__(
        self,
        evaluation_service: EvaluationService,
        agent_repository: AgentRepository,
        evaluation_repository: EvaluationRepository
    ):
        self.evaluation_service = evaluation_service
        self.agent_repository = agent_repository
        self.evaluation_repository = evaluation_repository
    
    def handle(self, command: EvaluateResponseCommand) -> EvaluateResponseResult:
        # Get agent
        agent = self.agent_repository.get_by_id(command.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {command.agent_id}")
        
        # Evaluate response
        evaluation = self.evaluation_service.evaluate_response(
            agent=agent,
            query=command.query,
            response=command.response,
            context=command.context
        )
        
        # Save evaluation
        self.evaluation_repository.save_evaluation(evaluation)
        
        # Save updated agent
        self.agent_repository.save(agent)
        
        # Determine if improvement is needed
        needs_improvement = evaluation.needs_improvement(
            self.evaluation_service.quality_thresholds,
            self.evaluation_service.overall_threshold
        )
        
        # Create result
        return EvaluateResponseResult(
            agent_id=agent.id,
            evaluation_id=evaluation.id,
            overall_score=evaluation.overall_score,
            criterion_scores={
                criterion: {
                    "score": score.score,
                    "reason": score.reason
                }
                for criterion, score in evaluation.scores.items()
            },
            needs_improvement=needs_improvement
        )

class ImproveResponseCommandHandler(CommandHandler[ImproveResponseCommand, ImproveResponseResult]):
    """Handler for ImproveResponseCommand."""
    
    def __init__(
        self,
        evaluation_service: EvaluationService,
        agent_repository: AgentRepository,
        evaluation_repository: EvaluationRepository
    ):
        self.evaluation_service = evaluation_service
        self.agent_repository = agent_repository
        self.evaluation_repository = evaluation_repository
    
    def handle(self, command: ImproveResponseCommand) -> ImproveResponseResult:
        # Get agent
        agent = self.agent_repository.get_by_id(command.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {command.agent_id}")
        
        # Get evaluation
        evaluation = self.evaluation_repository.get_evaluation_by_id(command.evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation not found: {command.evaluation_id}")
        
        # Improve response
        improvement = self.evaluation_service.improve_response(
            agent=agent,
            evaluation=evaluation
        )
        
        # Save improvement
        self.evaluation_repository.save_improvement(improvement)
        
        # Save updated agent
        self.agent_repository.save(agent)
        
        # Create result
        return ImproveResponseResult(
            agent_id=agent.id,
            evaluation_id=evaluation.id,
            improvement_id=improvement.id,
            original_response=improvement.original_response,
            improved_response=improvement.improved_response,
            suggestions=[
                {
                    "criterion": suggestion.criterion,
                    "suggestion": suggestion.suggestion,
                    "priority": suggestion.priority
                }
                for suggestion in improvement.suggestions
            ]
        )
