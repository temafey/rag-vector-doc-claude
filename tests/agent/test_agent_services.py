"""
Tests for agent services.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.domain.models.agent import Agent, AgentState, AgentAction
from app.domain.services.agent import AgentService, ActionRegistry
from app.infrastructure.event_bus import event_bus
from app.domain.events.agent_events import (
    AgentCreatedEvent,
    AgentActionStartedEvent,
    AgentActionCompletedEvent,
    AgentActionFailedEvent
)

class TestAgentServices:
    """Tests for agent services."""
    
    def setup_method(self):
        """Setup method for tests."""
        # Create action registry
        self.action_registry = ActionRegistry()
        
        # Register test action
        self.test_action_handler = MagicMock(return_value="test-result")
        self.action_registry.register_action(
            "test-action",
            self.test_action_handler,
            {"description": "Test action"}
        )
        
        # Register failing action
        self.failing_action_handler = MagicMock(side_effect=Exception("test-error"))
        self.action_registry.register_action(
            "failing-action",
            self.failing_action_handler,
            {"description": "Failing action"}
        )
        
        # Create agent service
        self.agent_service = AgentService(action_registry=self.action_registry)
        
        # Setup event listeners
        self.agent_created_events = []
        self.action_started_events = []
        self.action_completed_events = []
        self.action_failed_events = []
        
        def on_agent_created(event: AgentCreatedEvent):
            self.agent_created_events.append(event)
        
        def on_action_started(event: AgentActionStartedEvent):
            self.action_started_events.append(event)
        
        def on_action_completed(event: AgentActionCompletedEvent):
            self.action_completed_events.append(event)
        
        def on_action_failed(event: AgentActionFailedEvent):
            self.action_failed_events.append(event)
        
        self.created_listener = MagicMock(side_effect=on_agent_created)
        self.started_listener = MagicMock(side_effect=on_action_started)
        self.completed_listener = MagicMock(side_effect=on_action_completed)
        self.failed_listener = MagicMock(side_effect=on_action_failed)
        
        event_bus.subscribe(AgentCreatedEvent, self.created_listener)
        event_bus.subscribe(AgentActionStartedEvent, self.started_listener)
        event_bus.subscribe(AgentActionCompletedEvent, self.completed_listener)
        event_bus.subscribe(AgentActionFailedEvent, self.failed_listener)
    
    def teardown_method(self):
        """Teardown method for tests."""
        # Unsubscribe listeners
        event_bus._subscribers = {}
    
    def test_register_action(self):
        """Test ActionRegistry.register_action."""
        registry = ActionRegistry()
        
        # Register action
        test_handler = MagicMock()
        registry.register_action("test-action", test_handler, {"description": "Test action"})
        
        # Check if action is registered
        assert registry.is_registered("test-action")
        assert registry.get_action("test-action") == test_handler
        assert registry.get_metadata("test-action") == {"description": "Test action"}
        assert "test-action" in registry.list_actions()
        
        # Check non-existent action
        assert not registry.is_registered("non-existent")
        assert registry.get_action("non-existent") is None
        assert registry.get_metadata("non-existent") == {}
    
    def test_create_agent(self):
        """Test AgentService.create_agent."""
        # Create agent
        agent = self.agent_service.create_agent(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation",
            config={"key": "value"}
        )
        
        # Verify agent
        assert agent.name == "Test Agent"
        assert agent.description == "Test description"
        assert agent.state.conversation_id == "test-conversation"
        assert agent.config == {"key": "value"}
        
        # Verify event
        assert len(self.agent_created_events) == 1
        event = self.agent_created_events[0]
        assert event.agent_id == agent.id
        assert event.name == agent.name
        assert event.conversation_id == agent.state.conversation_id
    
    def test_execute_action_success(self):
        """Test AgentService.execute_action with successful action."""
        # Create agent
        agent = self.agent_service.create_agent(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        # Execute action
        action = self.agent_service.execute_action(
            agent=agent,
            action_type="test-action",
            parameters={"key": "value"}
        )
        
        # Verify action
        assert action.action_type == "test-action"
        assert action.parameters == {"key": "value"}
        assert action.status == "completed"
        assert action.result == "test-result"
        
        # Verify agent state
        assert len(agent.state.action_history) == 1
        assert agent.state.action_history[0] == action
        
        # Verify action handler was called
        self.test_action_handler.assert_called_once_with(agent, {"key": "value"})
        
        # Verify events
        assert len(self.action_started_events) == 1
        assert self.action_started_events[0].action_type == "test-action"
        assert self.action_started_events[0].parameters == {"key": "value"}
        
        assert len(self.action_completed_events) == 1
        assert self.action_completed_events[0].action_type == "test-action"
        assert self.action_completed_events[0].result == "test-result"
    
    def test_execute_action_failure(self):
        """Test AgentService.execute_action with failing action."""
        # Create agent
        agent = self.agent_service.create_agent(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        # Execute action (should raise exception)
        with pytest.raises(Exception) as excinfo:
            self.agent_service.execute_action(
                agent=agent,
                action_type="failing-action",
                parameters={"key": "value"}
            )
        
        assert str(excinfo.value) == "test-error"
        
        # Verify agent state
        assert len(agent.state.action_history) == 1
        action = agent.state.action_history[0]
        assert action.action_type == "failing-action"
        assert action.parameters == {"key": "value"}
        assert action.status == "failed"
        assert action.result == "test-error"
        
        # Verify action handler was called
        self.failing_action_handler.assert_called_once_with(agent, {"key": "value"})
        
        # Verify events
        assert len(self.action_started_events) == 1
        assert self.action_started_events[0].action_type == "failing-action"
        
        assert len(self.action_failed_events) == 1
        assert self.action_failed_events[0].action_type == "failing-action"
        assert self.action_failed_events[0].error == "test-error"
    
    def test_execute_unknown_action(self):
        """Test AgentService.execute_action with unknown action type."""
        # Create agent
        agent = self.agent_service.create_agent(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        # Execute unknown action (should raise exception)
        with pytest.raises(ValueError) as excinfo:
            self.agent_service.execute_action(
                agent=agent,
                action_type="unknown-action",
                parameters={"key": "value"}
            )
        
        assert "Unknown action type: unknown-action" in str(excinfo.value)
        
        # Verify no actions were added
        assert len(agent.state.action_history) == 0
        
        # Verify no events were fired
        assert len(self.action_started_events) == 0
        assert len(self.action_completed_events) == 0
        assert len(self.action_failed_events) == 0
    
    def test_get_available_actions(self):
        """Test AgentService.get_available_actions."""
        # Create agent
        agent = self.agent_service.create_agent(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        # Get available actions
        actions = self.agent_service.get_available_actions(agent)
        
        # Verify actions
        assert set(actions) == {"test-action", "failing-action"}
    
    @patch("app.domain.services.agent.agent_service.AgentService.execute_action")
    def test_process_query(self, mock_execute_action):
        """Test AgentService.process_query."""
        # Setup mocks
        def mock_execute_side_effect(agent, action_type, parameters):
            if action_type == "search":
                return AgentAction(
                    id="search-action-id",
                    action_type="search",
                    parameters=parameters,
                    created_at=None,
                    completed_at=None,
                    result=["search-result-1", "search-result-2"],
                    status="completed"
                )
            elif action_type == "generate":
                return AgentAction(
                    id="generate-action-id",
                    action_type="generate",
                    parameters=parameters,
                    created_at=None,
                    completed_at=None,
                    result="generated-response",
                    status="completed"
                )
            elif action_type == "evaluate":
                return AgentAction(
                    id="evaluate-action-id",
                    action_type="evaluate",
                    parameters=parameters,
                    created_at=None,
                    completed_at=None,
                    result={
                        "evaluation_id": "eval-id",
                        "overall_score": 0.85,
                        "criterion_scores": {
                            "relevance": {"score": 0.9, "reason": "Good relevance"}
                        },
                        "needs_improvement": False
                    },
                    status="completed"
                )
        
        mock_execute_action.side_effect = mock_execute_side_effect
        
        # Create agent
        agent = self.agent_service.create_agent(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        # Process query
        result = self.agent_service.process_query(agent, "test query")
        
        # Verify execute_action calls
        assert mock_execute_action.call_count == 3
        mock_execute_action.assert_any_call(agent, "search", {"query": "test query"})
        mock_execute_action.assert_any_call(agent, "generate", {
            "query": "test query",
            "context": ["search-result-1", "search-result-2"]
        })
        mock_execute_action.assert_any_call(agent, "evaluate", {
            "query": "test query",
            "response": "generated-response",
            "context": ["search-result-1", "search-result-2"]
        })
        
        # Verify result
        assert result["response"] == "generated-response"
        assert result["sources"] == ["search-result-1", "search-result-2"]
        assert result["improved"] is False
        
        # Verify memory
        assert agent.state.get_memory("last_query") == "test query"
