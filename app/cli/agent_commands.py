"""
CLI commands for agent operations.
"""
import click
import json
import uuid
from typing import Dict, List, Any, Optional

from app.cli.common import get_api_base_url, print_json, handle_request_error
from app.cli.agent_cli import AgentCLI

@click.group(name="agent")
def agent_commands():
    """Agent commands for RAG system."""
    pass

@agent_commands.command("create")
@click.argument("name")
@click.option("--description", "-d", default="RAG Agent", help="Agent description")
@click.option("--conversation", "-c", help="Conversation ID (generated if not provided)")
@click.option("--config", help="JSON config string")
def create_agent(name: str, description: str, conversation: str = None, config: str = None):
    """Create a new agent."""
    # Parse config JSON
    config_dict = {}
    if config:
        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in config")
            return
    
    # Generate conversation ID if not provided
    if not conversation:
        conversation = str(uuid.uuid4())
    
    try:
        # Create agent
        agent_cli = AgentCLI(get_api_base_url())
        agent = agent_cli.create_agent(
            name=name,
            description=description,
            conversation_id=conversation,
            config=config_dict
        )
        
        click.echo(f"Agent created with ID: {agent['id']}")
        click.echo(f"Name: {agent['name']}")
        click.echo(f"Description: {agent['description']}")
        click.echo(f"Conversation ID: {agent['conversation_id']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("get")
@click.argument("agent_id")
def get_agent(agent_id: str):
    """Get agent by ID."""
    try:
        # Get agent
        agent_cli = AgentCLI(get_api_base_url())
        agent = agent_cli.get_agent(agent_id)
        
        click.echo(f"Agent ID: {agent['id']}")
        click.echo(f"Name: {agent['name']}")
        click.echo(f"Description: {agent['description']}")
        click.echo(f"Conversation ID: {agent['conversation_id']}")
        click.echo(f"Created: {agent['created_at']}")
        click.echo(f"Updated: {agent['updated_at']}")
        click.echo(f"Action count: {agent['action_count']}")
        
        if agent.get('config'):
            click.echo("Config:")
            print_json(agent['config'])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("list")
def list_agents():
    """List all agents."""
    try:
        # Get agents
        agent_cli = AgentCLI(get_api_base_url())
        agents = agent_cli.list_agents()
        
        click.echo(f"Found {len(agents)} agents:")
        for agent in agents:
            click.echo(f"- {agent['id']}: {agent['name']} (Conversation: {agent['conversation_id']})")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("delete")
@click.argument("agent_id")
def delete_agent(agent_id: str):
    """Delete agent."""
    try:
        # Delete agent
        agent_cli = AgentCLI(get_api_base_url())
        agent_cli.delete_agent(agent_id)
        
        click.echo(f"Agent {agent_id} deleted")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("query")
@click.argument("agent_id")
@click.argument("query_text")
@click.option("--planning", "-p", is_flag=True, help="Use planning for complex queries")
def process_query(agent_id: str, query_text: str, planning: bool = False):
    """Process a query using an agent."""
    try:
        # Process query
        agent_cli = AgentCLI(get_api_base_url())
        result = agent_cli.process_query(
            agent_id=agent_id,
            query=query_text,
            use_planning=planning
        )
        
        click.echo("Response:")
        click.echo(result["response"])
        
        if result.get("improved", False):
            click.echo("\nResponse was improved based on self-assessment.")
        
        click.echo("\nSources:")
        for i, source in enumerate(result.get("sources", []), 1):
            click.echo(f"{i}. {source.get('title', 'No title')} - Relevance: {source.get('score', 0):.2f}")
            click.echo(f"   {source.get('content', '')[:150]}...")
        
        if "evaluation" in result:
            click.echo("\nEvaluation:")
            click.echo(f"Overall Score: {result['evaluation']['overall_score']:.2f}")
            for criterion, data in result['evaluation'].get('criterion_scores', {}).items():
                click.echo(f"- {criterion}: {data['score']:.2f} - {data['reason']}")
        
        if "plan" in result and result["plan"]:
            click.echo("\nPlan:")
            click.echo(f"Task: {result['plan']['task']}")
            click.echo(f"Status: {result['plan']['status']}")
            click.echo("Steps:")
            for step in result['plan']['steps']:
                click.echo(f"- Step {step['step_number']}: {step['description']} ({step['status']})")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("action")
@click.argument("agent_id")
@click.argument("action_type")
@click.option("--parameters", "-p", help="JSON parameters string")
def execute_action(agent_id: str, action_type: str, parameters: str = None):
    """Execute agent action."""
    # Parse parameters JSON
    params_dict = {}
    if parameters:
        try:
            params_dict = json.loads(parameters)
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in parameters")
            return
    
    try:
        # Execute action
        agent_cli = AgentCLI(get_api_base_url())
        result = agent_cli.execute_action(
            agent_id=agent_id,
            action_type=action_type,
            parameters=params_dict
        )
        
        click.echo(f"Action {action_type} executed:")
        print_json(result)
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("plan")
@click.argument("agent_id")
@click.argument("task")
@click.option("--constraint", "-c", multiple=True, help="Constraint for the plan")
def create_plan(agent_id: str, task: str, constraint: List[str] = None):
    """Create a plan for an agent."""
    try:
        # Create plan
        agent_cli = AgentCLI(get_api_base_url())
        plan = agent_cli.create_plan(
            agent_id=agent_id,
            task=task,
            constraints=list(constraint) if constraint else []
        )
        
        click.echo(f"Plan created with ID: {plan['id']}")
        click.echo(f"Task: {plan['task']}")
        click.echo(f"Status: {plan['status']}")
        click.echo(f"Steps:")
        for step in plan['steps']:
            deps = ", ".join(map(str, step['dependencies'])) if step['dependencies'] else "None"
            click.echo(f"- Step {step['step_number']}: {step['action_type']} - {step['description']}")
            click.echo(f"  Dependencies: {deps}")
            click.echo(f"  Status: {step['status']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("execute-plan")
@click.argument("agent_id")
@click.argument("plan_id")
def execute_plan(agent_id: str, plan_id: str):
    """Execute a plan."""
    try:
        # Execute plan
        agent_cli = AgentCLI(get_api_base_url())
        result = agent_cli.execute_plan(
            agent_id=agent_id,
            plan_id=plan_id
        )
        
        click.echo(f"Plan {plan_id} executed with status: {result['status']}")
        click.echo(f"Completed steps: {', '.join(map(str, result['completed_steps']))}")
        
        click.echo("Results:")
        for step_num, step_result in result.get('results', {}).items():
            click.echo(f"- Step {step_num} result:")
            print_json(step_result)
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("evaluate")
@click.argument("agent_id")
@click.argument("query")
@click.argument("response")
@click.option("--context", "-c", multiple=True, help="Context for evaluation")
def evaluate_response(agent_id: str, query: str, response: str, context: List[str] = None):
    """Evaluate a response."""
    try:
        # Evaluate response
        agent_cli = AgentCLI(get_api_base_url())
        result = agent_cli.evaluate_response(
            agent_id=agent_id,
            query=query,
            response=response,
            context=list(context) if context else []
        )
        
        click.echo(f"Evaluation ID: {result['evaluation_id']}")
        click.echo(f"Overall score: {result['overall_score']:.2f}")
        click.echo(f"Needs improvement: {'Yes' if result['needs_improvement'] else 'No'}")
        
        click.echo("\nCriterion scores:")
        for criterion, score_data in result.get('criterion_scores', {}).items():
            click.echo(f"- {criterion}: {score_data['score']:.2f}")
            click.echo(f"  Reason: {score_data['reason']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@agent_commands.command("improve")
@click.argument("agent_id")
@click.argument("evaluation_id")
def improve_response(agent_id: str, evaluation_id: str):
    """Improve a response based on evaluation."""
    try:
        # Send request
        import requests
        api_base_url = get_api_base_url()
        response = requests.post(
            f"{api_base_url}/evaluations/{evaluation_id}/improve",
            params={"agent_id": agent_id}
        )
        
        # Check response status
        if response.status_code != 200:
            handle_request_error(response, "Error improving response")
            return
        
        # Get result
        result = response.json()
        
        click.echo("Original response:")
        click.echo(result['original_response'])
        
        click.echo("\nImproved response:")
        click.echo(result['improved_response'])
        
        click.echo("\nSuggestions:")
        for suggestion in result.get('suggestions', []):
            click.echo(f"- {suggestion['criterion']} (Priority: {suggestion['priority']})")
            click.echo(f"  {suggestion['suggestion']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

if __name__ == "__main__":
    agent_commands()
