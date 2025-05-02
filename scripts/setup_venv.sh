#!/bin/bash
# Script for setting up virtual environment

# Exit on error
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .

echo "Virtual environment setup complete. Activate it with:"
echo "source venv/bin/activate"
