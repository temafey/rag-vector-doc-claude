"""
Tests for agent models.
"""
import pytest
from app.domain.models.agent import Agent, AgentState, AgentAction

class TestAgentModels:
    """Tests for agent models."""
    
    def test_agent_create(self):
        """Test Agent.create factory method."""
        agent = Agent.create(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        assert agent.name == "Test Agent"
        assert agent.description == "Test description"
        assert agent.state.conversation_id == "test-conversation"
        assert agent.id is not None
    
    def test_agent_state_create(self):
        """Test AgentState.create factory method."""
        state = AgentState.create(conversation_id="test-conversation")
        
        assert state.conversation_id == "test-conversation"
        assert state.id is not None
        assert state.memory == {}
        assert state.action_history == []
    
    def test_agent_state_add_action(self):
        """Test AgentState.add_action."""
        state = AgentState.create(conversation_id="test-conversation")
        action = AgentAction.create(
            action_type="test-action",
            parameters={"key": "value"}
        )
        
        state.add_action(action)
        
        assert len(state.action_history) == 1
        assert state.action_history[0].action_type == "test-action"
        assert state.action_history[0].parameters == {"key": "value"}
    
    def test_agent_state_memory(self):
        """Test AgentState memory operations."""
        state = AgentState.create(conversation_id="test-conversation")
        
        # Set memory
        state.set_memory("key1", "value1")
        state.set_memory("key2", {"nested": "value"})
        
        # Get memory
        assert state.get_memory("key1") == "value1"
        assert state.get_memory("key2") == {"nested": "value"}
        assert state.get_memory("not-exist") is None
        assert state.get_memory("not-exist", "default") == "default"
    
    def test_agent_execute_action(self):
        """Test Agent.execute_action."""
        agent = Agent.create(
            name="Test Agent",
            description="Test description",
            conversation_id="test-conversation"
        )
        
        action = agent.execute_action(
            action_type="test-action",
            parameters={"key": "value"}
        )
        
        assert action.action_type == "test-action"
        assert action.parameters == {"key": "value"}
        assert len(agent.state.action_history) == 1
        assert agent.state.action_history[0] == action
    
    def test_agent_action_create(self):
        """Test AgentAction.create factory method."""
        action = AgentAction.create(
            action_type="test-action",
            parameters={"key": "value"}
        )
        
        assert action.action_type == "test-action"
        assert action.parameters == {"key": "value"}
        assert action.status == "pending"
        assert action.id is not None
    
    def test_agent_action_complete(self):
        """Test AgentAction.complete."""
        action = AgentAction.create(
            action_type="test-action",
            parameters={"key": "value"}
        )
        
        action.complete("test-result")
        
        assert action.result == "test-result"
        assert action.status == "completed"
        assert action.completed_at is not None
    
    def test_agent_action_fail(self):
        """Test AgentAction.fail."""
        action = AgentAction.create(
            action_type="test-action",
            parameters={"key": "value"}
        )
        
        action.fail("test-error")
        
        assert action.result == "test-error"
        assert action.status == "failed"
        assert action.completed_at is not None
    
    def test_agent_to_from_dict(self):
        """Test AgentState.to_dict and from_dict."""
        # Create agent state
        state = AgentState.create(conversation_id="test-conversation")
        state.set_memory("key1", "value1")
        
        # Add action
        action = AgentAction.create(
            action_type="test-action",
            parameters={"key": "value"}
        )
        state.add_action(action)
        
        # Convert to dict
        state_dict = state.to_dict()
        
        # Create from dict
        state2 = AgentState.from_dict(state_dict)
        
        # Verify
        assert state2.id == state.id
        assert state2.conversation_id == state.conversation_id
        assert state2.memory == state.memory
        assert len(state2.action_history) == len(state.action_history)
        assert state2.action_history[0].id == state.action_history[0].id
        assert state2.action_history[0].action_type == state.action_history[0].action_type
