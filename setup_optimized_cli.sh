#!/bin/bash
# Setup script for the optimized CLI
echo "Setting up optimized CLI..."

# Install enhanced dependencies
pip install rich>=13.0.0 typer>=0.9.0 click-completion>=0.5.2

# Make new CLI executable
chmod +x cli_new.py

# Optional: Create symlink for easier access
ln -sf cli_new.py rag-cli

echo "✅ Optimized CLI setup complete!"
echo ""
echo "Usage:"
echo "  python cli_new.py --help                    # Show main help"
echo "  python cli_new.py documents --help          # Document commands help"
echo "  python cli_new.py agents --help             # Agent commands help"
echo "  python cli_new.py collections --help        # Collection commands help"
echo ""
echo "Legacy compatibility:"
echo "  python cli_new.py add file.pdf              # Still works!"
echo "  python cli_new.py query 'your question'     # Still works!"
