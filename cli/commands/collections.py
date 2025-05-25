"""
Collection management commands.
"""
import click
from ..client import api_client
from ..utils import TableFormatter


@click.group()
def collections():
    """Collection management commands."""
    pass


@collections.command("list")
def list_collections():
    """List all collections."""
    try:
        collections = api_client.list_collections()
        
        if not collections:
            click.echo("No collections found.")
            return
        
        click.echo("Available collections:")
        click.echo(TableFormatter.format_collections(collections))
        
    except Exception as e:
        click.echo(f"Error getting collections list: {str(e)}", err=True)


@collections.command("create")
@click.argument("name")
def create_collection(name: str):
    """Create new collection."""
    try:
        api_client.create_collection(name)
        click.echo(f"Collection {name} created successfully.")
        
    except Exception as e:
        click.echo(f"Error creating collection: {str(e)}", err=True)


@collections.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this collection?")
def delete_collection(name: str):
    """Delete collection."""
    try:
        api_client.delete_collection(name)
        click.echo(f"Collection {name} deleted successfully.")
        
    except Exception as e:
        click.echo(f"Error deleting collection: {str(e)}", err=True)
