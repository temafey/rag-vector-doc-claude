#!/bin/bash
# Enhanced script for setting up virtual environment with all dependencies

# Exit on error
set -e

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python version: $python_version"
major_version=$(echo $python_version | cut -d. -f1)
minor_version=$(echo $python_version | cut -d. -f2)

if [ "$major_version" -lt 3 ] || [ "$major_version" -eq 3 -a "$minor_version" -lt 9 ]; then
    echo "Error: Python 3.9 or higher is required"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
if [ -f "requirements-dev.txt" ]; then
    echo "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Install project in development mode
echo "Installing project in development mode..."
pip install -e .

# Verify installation
echo "Verifying installation..."
python -c "from app import __version__; print(f'RAG-Vector-Doc-Claude version: {__version__}')"

echo "Virtual environment setup complete. Activate it with:"
echo "source .venv/bin/activate"

# Setup pre-commit hooks if available
if [ -f ".pre-commit-config.yaml" ]; then
    echo "Setting up pre-commit hooks..."
    pip install pre-commit
    pre-commit install
fi

echo "All done! Your development environment is ready."
