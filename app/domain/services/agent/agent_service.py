"""
Agent service for RAG system.
"""
from typing import Dict, List, Any, Optional, Callable, Type
from app.domain.models.agent import Agent, AgentState, AgentAction
from app.infrastructure.event_bus import event_bus
from app.domain.events.agent_events import (
    AgentCreatedEvent, 
    AgentActionStartedEvent,
    AgentActionCompletedEvent,
    AgentActionFailedEvent
)

class ActionRegistry:
    """Registry for agent actions."""
    
    def __init__(self):
        self.actions: Dict[str, Callable] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_action(self, action_type: str, handler: Callable, 
                       metadata: Dict[str, Any] = None) -> None:
        """Register action handler."""
        self.actions[action_type] = handler
        self.metadata[action_type] = metadata or {}
    
    def get_action(self, action_type: str) -> Optional[Callable]:
        """Get action handler by type."""
        return self.actions.get(action_type)
    
    def get_metadata(self, action_type: str) -> Dict[str, Any]:
        """Get action metadata by type."""
        return self.metadata.get(action_type, {})
    
    def list_actions(self) -> List[str]:
        """List all registered action types."""
        return list(self.actions.keys())
    
    def is_registered(self, action_type: str) -> bool:
        """Check if action type is registered."""
        return action_type in self.actions

class AgentService:
    """Service for working with agents."""
    
    def __init__(self, action_registry: ActionRegistry):
        self.action_registry = action_registry
    
    def create_agent(self, name: str, description: str, conversation_id: str, 
                    config: Dict[str, Any] = None) -> Agent:
        """Create a new agent."""
        agent = Agent.create(name, description, conversation_id, config)
        
        # Publish event
        event_bus.publish(AgentCreatedEvent(
            agent_id=agent.id,
            name=agent.name,
            conversation_id=agent.state.conversation_id
        ))
        
        return agent
    
    def execute_action(self, agent: Agent, action_type: str, 
                      parameters: Dict[str, Any]) -> AgentAction:
        """Execute agent action."""
        # Check if action type is registered
        if not self.action_registry.is_registered(action_type):
            raise ValueError(f"Unknown action type: {action_type}")
        
        # Create and add action to agent state
        action = AgentAction.create(action_type, parameters)
        agent.state.add_action(action)
        
        # Publish action started event
        event_bus.publish(AgentActionStartedEvent(
            agent_id=agent.id,
            action_id=action.id,
            action_type=action.action_type,
            parameters=action.parameters
        ))
        
        try:
            # Get action handler and execute
            handler = self.action_registry.get_action(action_type)
            result = handler(agent, parameters)
            
            # Update action with result
            action.complete(result)
            
            # Publish action completed event
            event_bus.publish(AgentActionCompletedEvent(
                agent_id=agent.id,
                action_id=action.id,
                action_type=action.action_type,
                result=action.result
            ))
            
        except Exception as e:
            # Update action with error
            action.fail(str(e))
            
            # Publish action failed event
            event_bus.publish(AgentActionFailedEvent(
                agent_id=agent.id,
                action_id=action.id,
                action_type=action.action_type,
                error=str(e)
            ))
            
            # Re-raise exception
            raise
        
        return action
    
    def get_available_actions(self, agent: Agent) -> List[str]:
        """Get list of available action types for agent."""
        return self.action_registry.list_actions()
    
    def process_query(self, agent: Agent, query: str) -> Dict[str, Any]:
        """
        Process user query using agent.
        
        This is the main entry point for agent functionality.
        It analyzes the query, determines what actions to take,
        executes them, and returns the result.
        """
        # Store query in agent memory
        agent.state.set_memory("last_query", query)
        
        # Determine required actions (simplified version)
        # In a real system, this would use a more sophisticated decision mechanism
        # such as a LLM prompt or a machine learning model
        
        # Default to search and generate, but this could be extended
        # to support planning, decision-making, etc.
        search_result = self.execute_action(agent, "search", {"query": query})
        
        generation_params = {
            "query": query,
            "context": search_result.result
        }
        generation_result = self.execute_action(agent, "generate", generation_params)
        
        # For demonstration purposes, we'll also perform evaluation
        # and improvement if the evaluation action is registered
        if self.action_registry.is_registered("evaluate"):
            evaluation_params = {
                "query": query,
                "response": generation_result.result,
                "context": search_result.result
            }
            evaluation_result = self.execute_action(agent, "evaluate", evaluation_params)
            
            # Check if response needs improvement
            if (isinstance(evaluation_result.result, dict) and 
                evaluation_result.result.get("needs_improvement", False) and
                self.action_registry.is_registered("improve")):
                
                improvement_params = {
                    "query": query,
                    "response": generation_result.result,
                    "context": search_result.result,
                    "evaluation": evaluation_result.result
                }
                improvement_result = self.execute_action(agent, "improve", improvement_params)
                
                # Return improved response
                return {
                    "response": improvement_result.result.get("improved_response", generation_result.result),
                    "sources": search_result.result,
                    "evaluation": evaluation_result.result,
                    "improved": True
                }
        
        # Return response
        return {
            "response": generation_result.result,
            "sources": search_result.result,
            "improved": False
        }
    
    def update_agent_state(self, agent: Agent, state: AgentState) -> None:
        """Update agent state."""
        agent.update_state(state)
