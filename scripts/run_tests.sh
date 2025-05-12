#!/bin/bash
# Script for running tests

# Exit on error
set -e

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        echo "Activating virtual environment..."
        source .venv/bin/activate
    else
        echo "No virtual environment found. Please run 'make venv' first."
        exit 1
    fi
fi

# Default test category
TEST_CATEGORY=${1:-"all"}

# Run appropriate tests
case $TEST_CATEGORY in
    "unit")
        echo "Running unit tests..."
        pytest tests/unit -v
        ;;
    "integration")
        echo "Running integration tests..."
        pytest tests/integration -v
        ;;
    "api")
        echo "Running API tests..."
        pytest tests/integration/test_api.py -v
        ;;
    "all")
        echo "Running all tests..."
        pytest tests -v
        ;;
    "coverage")
        echo "Running tests with coverage report..."
        pytest --cov=app tests/ --cov-report=term --cov-report=html
        echo "Coverage report generated in htmlcov directory"
        ;;
    *)
        echo "Unknown test category: $TEST_CATEGORY"
        echo "Available categories: unit, integration, api, all, coverage"
        exit 1
        ;;
esac

echo "Tests completed successfully"
