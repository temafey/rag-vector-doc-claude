"""
Enhanced CLI utilities using Rich for better formatting.
"""
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich import print as rich_print
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to regular print
    def rich_print(*args, **kwargs):
        print(*args, **kwargs)

import json
from typing import Dict, Any, List


class EnhancedFormatter:
    """Enhanced formatter using Rich for better CLI output."""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
    
    def print_success(self, message: str):
        """Print success message."""
        if RICH_AVAILABLE:
            self.console.print(f"✅ {message}", style="green")
        else:
            print(f"✅ {message}")
    
    def print_error(self, message: str):
        """Print error message."""
        if RICH_AVAILABLE:
            self.console.print(f"❌ {message}", style="red")
        else:
            print(f"❌ {message}")
    
    def print_warning(self, message: str):
        """Print warning message."""
        if RICH_AVAILABLE:
            self.console.print(f"⚠️  {message}", style="yellow")
        else:
            print(f"⚠️  {message}")
    
    def print_info(self, message: str):
        """Print info message."""
        if RICH_AVAILABLE:
            self.console.print(f"ℹ️  {message}", style="blue")
        else:
            print(f"ℹ️  {message}")
    
    def format_sources_rich(self, sources: List[Dict[str, Any]]) -> None:
        """Format sources using Rich table."""
        if not RICH_AVAILABLE:
            from .utils import TableFormatter
            print(TableFormatter.format_sources(sources))
            return
        
        if not sources:
            self.console.print("No sources found.", style="yellow")
            return
        
        table = Table(title="Sources")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Relevance", style="green")
        table.add_column("Content", style="blue")
        
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'No title')
            score = f"{source.get('score', 0):.2f}"
            content = source.get('content', '')[:100]
            if len(source.get('content', '')) > 100:
                content += "..."
            
            table.add_row(str(i), title, score, content)
        
        self.console.print(table)
    
    def format_json_rich(self, data: Dict[str, Any], title: str = None):
        """Format JSON data using Rich syntax highlighting."""
        if not RICH_AVAILABLE:
            print(json.dumps(data, indent=2))
            return
        
        json_str = json.dumps(data, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        
        if title:
            panel = Panel(syntax, title=title)
            self.console.print(panel)
        else:
            self.console.print(syntax)
    
    def create_progress_bar(self, description: str = "Processing..."):
        """Create a progress bar context manager."""
        if not RICH_AVAILABLE:
            return None
        
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )


# Global enhanced formatter instance
enhanced_formatter = EnhancedFormatter()
