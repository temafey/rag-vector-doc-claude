"""
Planning service for agent-based RAG system.
"""
from typing import Dict, List, Any, Optional
from app.domain.models.agent import Agent, Plan, PlanStep
from app.domain.services.agent.agent_service import AgentService
from app.infrastructure.event_bus import event_bus
from app.domain.events.agent_events import (
    PlanCreatedEvent,
    PlanStepCompletedEvent,
    PlanCompletedEvent
)
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json

class PlanningService:
    """Service for planning agent actions."""
    
    def __init__(self, agent_service: AgentService, llm_client=None):
        self.agent_service = agent_service
        
        # Initialize LLM for plan generation
        if llm_client:
            self.llm = llm_client
        else:
            from app.config.config_loader import get_config
            config = get_config()
            self.llm = OpenAI(
                temperature=0.2,  # Lower temperature for more deterministic planning
                model_name=config["langchain"].get("llm_model", "gpt-3.5-turbo")
            )
        
        # Create planning prompt template
        self.planning_template = PromptTemplate(
            input_variables=["task", "available_actions", "constraints"],
            template="""Create a step-by-step plan to complete the following task:

Task: {task}

Available actions:
{available_actions}

Constraints:
{constraints}

Create a detailed plan with numbered steps. Each step should include:
1. The action to execute (must be one of the available actions)
2. A description of what this step accomplishes
3. Parameters required for the action
4. Dependencies (which steps must be completed before this one)

Respond in the following JSON format:
```json
{{
  "steps": [
    {{
      "step_number": 1,
      "action_type": "action_name",
      "description": "What this step does",
      "parameters": {{"param1": "value1", "param2": "value2"}},
      "dependencies": []
    }},
    ...
  ]
}}
```
"""
        )
        
        self.planning_chain = LLMChain(llm=self.llm, prompt=self.planning_template)
    
    def create_plan(self, agent: Agent, task: str, constraints: List[str] = None) -> Plan:
        """Create a plan for completing a task."""
        # Get available actions
        available_actions = self.agent_service.get_available_actions(agent)
        
        # Format actions for prompt
        actions_str = "\n".join([f"- {action}" for action in available_actions])
        
        # Format constraints
        constraints_str = "\n".join([f"- {constraint}" for constraint in constraints or []])
        if not constraints_str:
            constraints_str = "- No specific constraints"
        
        # Generate plan using LLM
        plan_text = self.planning_chain.run(
            task=task,
            available_actions=actions_str,
            constraints=constraints_str
        )
        
        # Extract JSON from response
        try:
            # Find JSON block in response
            json_start = plan_text.find("```json") + 7 if "```json" in plan_text else 0
            json_end = plan_text.find("```", json_start) if "```" in plan_text[json_start:] else len(plan_text)
            json_str = plan_text[json_start:json_end].strip()
            
            # Parse JSON
            plan_data = json.loads(json_str)
        except Exception as e:
            # Fallback for when JSON extraction fails
            raise ValueError(f"Failed to parse plan: {str(e)}")
        
        # Create plan entity
        plan = Plan.create(agent.id, task)
        
        # Add steps
        for step_data in plan_data.get("steps", []):
            plan.add_step(
                action_type=step_data.get("action_type"),
                description=step_data.get("description"),
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", [])
            )
        
        # Store plan in agent memory
        agent.state.set_memory("current_plan", plan.id)
        
        # Publish plan created event
        event_bus.publish(PlanCreatedEvent(
            agent_id=agent.id,
            plan_id=plan.id,
            task=task,
            step_count=len(plan.steps)
        ))
        
        return plan
    
    def execute_plan(self, agent: Agent, plan: Plan) -> Dict[str, Any]:
        """Execute a plan step by step."""
        # Update plan status
        plan.status = "in-progress"
        
        # Track completed steps
        completed_steps = []
        results = {}
        
        # Execute until all steps are completed or a step fails
        while plan.status == "in-progress":
            # Get next steps
            next_steps = plan.get_next_steps()
            
            # If no more steps to execute, plan is complete
            if not next_steps:
                if plan._all_steps_completed():
                    plan.status = "completed"
                    
                    # Publish plan completed event
                    event_bus.publish(PlanCompletedEvent(
                        agent_id=agent.id,
                        plan_id=plan.id,
                        task=plan.task
                    ))
                    
                    break
                else:
                    # Some steps are still not completed or skipped, but none are ready
                    # This means there's a dependency cycle or all remaining steps are blocked
                    plan.status = "failed"
                    break
            
            # Execute first available step
            step = next_steps[0]
            step.update_status("in-progress")
            
            try:
                # Execute action
                action_result = self.agent_service.execute_action(
                    agent,
                    step.action_type,
                    step.parameters
                )
                
                # Update step with result
                step.update_status("completed", action_result.result)
                completed_steps.append(step.step_number)
                results[step.step_number] = action_result.result
                
                # Publish step completed event
                event_bus.publish(PlanStepCompletedEvent(
                    agent_id=agent.id,
                    plan_id=plan.id,
                    step_number=step.step_number,
                    action_type=step.action_type,
                    result=action_result.result
                ))
                
            except Exception as e:
                # Update step with error
                step.update_status("failed", str(e))
                
                # Mark plan as failed
                plan.status = "failed"
                break
        
        # Return plan execution results
        return {
            "plan_id": plan.id,
            "task": plan.task,
            "status": plan.status,
            "completed_steps": completed_steps,
            "results": results
        }
    
    def process_complex_query(self, agent: Agent, query: str) -> Dict[str, Any]:
        """
        Process a complex query using planning.
        
        This creates a plan for the query, executes it step by step,
        and returns the final result.
        """
        # Create plan for the query
        plan = self.create_plan(agent, query)
        
        # Execute plan
        execution_result = self.execute_plan(agent, plan)
        
        # If plan failed, return the error
        if plan.status == "failed":
            return {
                "error": "Failed to process query",
                "details": execution_result
            }
        
        # Extract final result
        # We assume the last step in the plan is a generation step
        # that produces the final answer
        final_step = max(execution_result["completed_steps"])
        final_result = execution_result["results"].get(final_step)
        
        # Return response
        return {
            "response": final_result,
            "plan": {
                "id": plan.id,
                "task": plan.task,
                "steps": [
                    {
                        "step_number": step.step_number,
                        "action_type": step.action_type,
                        "description": step.description,
                        "status": step.status,
                        "result": step.result
                    }
                    for step in plan.steps
                ]
            },
            "improved": False
        }
