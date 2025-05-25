"""
Agent management commands.
"""
import click
import json
from typing import List, Optional
from ..client import api_client
from ..utils import TableFormatter, generate_conversation_id, format_metadata
from ..config import config


@click.group()
def agents():
    """Agent management commands."""
    pass


@agents.command("create")
@click.option("--name", "-n", help="Agent name")
@click.option("--description", "-d", help="Agent description")
@click.option("--conversation-id", "-c", help="Conversation ID (generates new one if not specified)")
def create_agent(name: Optional[str], description: Optional[str], conversation_id: Optional[str]):
    """Create a new agent."""
    # Use defaults from config if not specified
    name = name or config.default_agent_name
    description = description or config.default_agent_description
    conversation_id = conversation_id or generate_conversation_id()
    
    try:
        result = api_client.create_agent(
            name=name,
            description=description,
            conversation_id=conversation_id
        )
        
        click.echo("Agent created:")
        click.echo(f"ID: {result['id']}")
        click.echo(f"Name: {result['name']}")
        click.echo(f"Conversation ID: {result['conversation_id']}")
        
    except Exception as e:
        click.echo(f"Error creating agent: {str(e)}", err=True)


@agents.command("list")
def list_agents():
    """List all agents."""
    try:
        agents = api_client.list_agents()
        
        if not agents:
            click.echo("No agents found.")
            return
        
        click.echo("Available agents:")
        click.echo(TableFormatter.format_agents(agents))
        
    except Exception as e:
        click.echo(f"Error listing agents: {str(e)}", err=True)


@agents.command("delete")
@click.argument("agent_id")
@click.confirmation_option(prompt="Are you sure you want to delete this agent?")
def delete_agent(agent_id: str):
    """Delete an agent."""
    try:
        api_client.delete_agent(agent_id)
        click.echo(f"Agent {agent_id} deleted successfully.")
        
    except Exception as e:
        click.echo(f"Error deleting agent: {str(e)}", err=True)


@agents.command("info")
@click.argument("agent_id")
def get_agent_info(agent_id: str):
    """Get agent information."""
    try:
        agent = api_client.get_agent(agent_id)
        
        click.echo("Agent Information:")
        click.echo(f"ID: {agent['id']}")
        click.echo(f"Name: {agent['name']}")
        click.echo(f"Description: {agent['description']}")
        click.echo(f"Conversation ID: {agent['conversation_id']}")
        click.echo(f"Created: {agent['created_at']}")
        click.echo(f"Last updated: {agent['updated_at']}")
        click.echo(f"Action count: {agent.get('action_count', 0)}")
        
    except Exception as e:
        click.echo(f"Error getting agent information: {str(e)}", err=True)


@agents.command("actions")
@click.argument("agent_id")
@click.option("--limit", "-l", default=10, help="Maximum number of actions to show")
@click.option("--offset", "-o", default=0, help="Offset for pagination")
@click.option("--action-type", "-t", help="Filter by action type")
def get_agent_actions(agent_id: str, limit: int, offset: int, action_type: Optional[str]):
    """Get agent action history."""
    try:
        actions = api_client.get_agent_actions(
            agent_id=agent_id,
            limit=limit,
            offset=offset,
            action_type=action_type
        )
        
        if not actions:
            click.echo("No actions found.")
            return
        
        click.echo(f"Actions for agent {agent_id}:")
        click.echo(TableFormatter.format_actions(actions))
        
    except Exception as e:
        click.echo(f"Error getting agent actions: {str(e)}", err=True)


@agents.command("run")
@click.argument("agent_id")
@click.option("--action", "-a", required=True, help="Action type to run")
@click.option("--param", "-p", multiple=True, help="Parameters in key=value format")
def execute_action(agent_id: str, action: str, param: List[str]):
    """Execute an action with an agent."""
    parameters = format_metadata(param)
    
    try:
        result = api_client.execute_agent_action(
            agent_id=agent_id,
            action_type=action,
            parameters=parameters
        )
        
        click.echo("Action executed:")
        click.echo(f"ID: {result.get('id', '')}")
        click.echo(f"Type: {result.get('action_type', '')}")
        click.echo(f"Status: {result.get('status', '')}")
        
        # Pretty print result
        click.echo("\nResult:")
        click.echo(json.dumps(result.get("result", {}), indent=2))
        
    except Exception as e:
        click.echo(f"Error executing action: {str(e)}", err=True)


@agents.command("query")
@click.argument("agent_id")
@click.argument("query_text")
@click.option("--planning", "-p", is_flag=True, help="Use planning for complex queries")
@click.option("--evaluate", "-e", is_flag=True, help="Show evaluation details")
def agent_query(agent_id: str, query_text: str, planning: bool, evaluate: bool):
    """Process a query using an agent."""
    try:
        click.echo("Processing query with agent...")
        result = api_client.process_agent_query(
            agent_id=agent_id,
            query=query_text,
            use_planning=planning
        )
        
        # Display response
        click.echo("\nResponse:")
        click.echo(result.get("response", ""))
        
        # Show improvement info if applicable
        if result.get("improved", False):
            click.echo("\n(Response was improved by self-assessment)")
        
        # Show evaluation if available
        evaluation = result.get("evaluation")
        if evaluation and evaluate:
            click.echo("\nEvaluation:")
            click.echo(f"Overall Score: {evaluation.get('overall_score', 0):.2f}")
            
            # Show criterion scores
            criterion_scores = evaluation.get("criterion_scores", {})
            if criterion_scores:
                click.echo("\nCriterion Scores:")
                click.echo(TableFormatter.format_evaluation_scores(criterion_scores))
        
        # Show plan if available
        plan = result.get("plan")
        if plan:
            click.echo("\nExecution Plan:")
            click.echo(f"Task: {plan.get('task', '')}")
            
            # Show steps
            steps = plan.get("steps", [])
            if steps:
                click.echo("\nSteps:")
                click.echo(TableFormatter.format_plan_steps(steps))
        
        # Show sources
        sources = result.get("sources", [])
        if sources:
            click.echo("\nSources:")
            click.echo(TableFormatter.format_sources(sources))
            
    except Exception as e:
        click.echo(f"Error executing query: {str(e)}", err=True)


@agents.command("evaluate")
@click.argument("agent_id")
@click.option("--query", "-q", required=True, help="Query text")
@click.option("--response", "-r", required=True, help="Response to evaluate")
@click.option("--context", "-c", multiple=True, help="Context (can be specified multiple times)")
def evaluate_response(agent_id: str, query: str, response: str, context: List[str]):
    """Evaluate response quality."""
    try:
        result = api_client.evaluate_response(
            agent_id=agent_id,
            query=query,
            response=response,
            context=list(context)
        )
        
        # Display evaluation results
        click.echo("Evaluation Results:")
        click.echo(f"Evaluation ID: {result.get('evaluation_id', '')}")
        click.echo(f"Overall Score: {result.get('overall_score', 0):.2f}")
        click.echo(f"Needs Improvement: {'Yes' if result.get('needs_improvement', False) else 'No'}")
        
        # Show criterion scores
        criterion_scores = result.get("criterion_scores", {})
        if criterion_scores:
            click.echo("\nCriterion Scores:")
            click.echo(TableFormatter.format_evaluation_scores(criterion_scores))
            
    except Exception as e:
        click.echo(f"Error evaluating response: {str(e)}", err=True)


@agents.command("improve")
@click.argument("agent_id")
@click.argument("evaluation_id")
def improve_response(agent_id: str, evaluation_id: str):
    """Improve response based on evaluation."""
    try:
        result = api_client.improve_response(evaluation_id, agent_id)
        
        # Display improvement results
        click.echo("Improvement Results:")
        click.echo(f"Improvement ID: {result.get('id', '')}")
        
        click.echo("\nOriginal Response:")
        click.echo(result.get("original_response", ""))
        
        click.echo("\nImproved Response:")
        click.echo(result.get("improved_response", ""))
        
        # Show suggestions
        suggestions = result.get("suggestions", [])
        if suggestions:
            click.echo("\nImprovement Suggestions:")
            click.echo(TableFormatter.format_suggestions(suggestions))
            
    except Exception as e:
        click.echo(f"Error improving response: {str(e)}", err=True)


@agents.command("plan")
@click.argument("agent_id")
@click.argument("task")
@click.option("--constraint", "-c", multiple=True, help="Constraints (can be specified multiple times)")
def create_plan(agent_id: str, task: str, constraint: List[str]):
    """Create a plan for a task."""
    try:
        result = api_client.create_plan(
            agent_id=agent_id,
            task=task,
            constraints=list(constraint)
        )
        
        # Display plan
        click.echo("Plan Created:")
        click.echo(f"Plan ID: {result.get('id', '')}")
        click.echo(f"Task: {result.get('task', '')}")
        click.echo(f"Status: {result.get('status', '')}")
        
        # Show steps
        steps = result.get("steps", [])
        if steps:
            click.echo("\nSteps:")
            click.echo(TableFormatter.format_plan_steps(steps))
            
    except Exception as e:
        click.echo(f"Error creating plan: {str(e)}", err=True)


@agents.command("execute-plan")
@click.argument("agent_id")
@click.argument("plan_id")
def execute_plan(agent_id: str, plan_id: str):
    """Execute a plan."""
    try:
        result = api_client.execute_plan(plan_id, agent_id)
        
        # Display execution results
        click.echo("Plan Execution Results:")
        click.echo(f"Plan ID: {result.get('plan_id', '')}")
        click.echo(f"Status: {result.get('status', '')}")
        click.echo(f"Completed Steps: {result.get('completed_steps', [])}")
        
        # Show step results
        step_results = result.get("results", {})
        if step_results:
            click.echo("\nStep Results:")
            for step_num, step_result in step_results.items():
                click.echo(f"\nStep {step_num} Result:")
                # Pretty print result
                result_str = json.dumps(step_result, indent=2)
                if len(result_str) > 200:
                    result_str = result_str[:200] + "..."
                click.echo(result_str)
                
    except Exception as e:
        click.echo(f"Error executing plan: {str(e)}", err=True)
