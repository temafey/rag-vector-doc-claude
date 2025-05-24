#!/bin/bash
# Script for activating virtual environment

# Define the virtual environment directory
VENV_DIR=".venv"

if [ -f "$VENV_DIR/bin/activate" ]; then
  source "$VENV_DIR/bin/activate"
  echo "Virtual environment at $VENV_DIR activated."
else
  echo "Error: Activation script not found at $VENV_DIR/bin/activate."
  echo "Please ensure the virtual environment has been created successfully using setup_venv.sh."
  exit 1
fi
