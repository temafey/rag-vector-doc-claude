.PHONY: build up down logs shell test lint format help clean-containers

# Variables
DOCKER_COMPOSE = docker-compose
API_SERVICE = api
CLI_SERVICE = cli
QDRANT_SERVICE = qdrant
PYTHON_IN_VENV = /app/.venv/bin/python

# Build and run commands
build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

# CLI commands
cli:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) $(PYTHON_IN_VENV) /app/cli.py $(ARGS)

# Add files to index
add-files:
	@if [ -z "$(FILES)" ]; then \
	  FILES="data/*"; \
	fi; \
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) $(PYTHON_IN_VENV) /app/cli.py add $$FILES --collection $(COLLECTION)

# Execute query
query:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) $(PYTHON_IN_VENV) /app/cli.py query "$(QUERY)" --collection $(COLLECTION)

# Collection management
list-collections:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) $(PYTHON_IN_VENV) /app/cli.py collections --list

create-collection:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) $(PYTHON_IN_VENV) /app/cli.py collections --create $(NAME)

delete-collection:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) $(PYTHON_IN_VENV) /app/cli.py collections --delete $(NAME)

# Development commands
shell:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) bash

test:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) pytest

lint:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) flake8 app

format:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) black app
	$(DOCKER_COMPOSE) exec $(API_SERVICE) isort app

# Virtual environment
setup-venv:
	./scripts/setup_venv.sh

activate_venv:
	./scripts/activate_venv.sh

# Run auto-update Taskmaster status script
update-tasks:
	$(DOCKER_COMPOSE) run --rm --entrypoint "" cli $(PYTHON_IN_VENV) scripts/auto_update_taskmaster_status.py

# Help
help:
	@echo "Makefile commands for RAG system:"
	@echo ""
	@echo "Build and run commands:"
	@echo "  make build              Build containers"
	@echo "  make up                 Start containers"
	@echo "  make down               Stop containers"
	@echo "  make logs               View logs"
	@echo ""
	@echo "CLI commands (via Makefile or direct CLI):"
	@echo "  make add-files FILES=\"file1.pdf file2.txt\" COLLECTION=\"default\""
	@echo "    # Add files to index (Makefile wrapper for 'add'). If FILES is not set, defaults to all files in data/ folder."
	@echo "  docker-compose exec cli $(PYTHON_IN_VENV) /app/cli.py add file1.pdf file2.txt --collection default"
	@echo "    # Add files to index (direct CLI)"
	@echo "  make cli ARGS=\"add-text 'Some text' --title 'Doc Title' --collection default\""
	@echo "    # Add text directly to the system"
	@echo "  make cli ARGS=\"query QUERY=\"your query\" COLLECTION=\"default\"\""
	@echo "    # Semantic search"
	@echo "  make cli ARGS=\"similar 'Text to match' --collection default --limit 5\""
	@echo "    # Find similar documents"
	@echo "  make cli ARGS=\"collections --list\""
	@echo "    # List collections"
	@echo "  make cli ARGS=\"collections --create new_collection\""
	@echo "    # Create collection"
	@echo "  make cli ARGS=\"collections --delete old_collection\""
	@echo "    # Delete collection"
	@echo "  make cli ARGS=\"purge-processed file1.pdf file2.txt\""
	@echo "    # Purge all processed data from vector DB for specific docs (does NOT delete raw files) and update progress.json"
	@echo "  make cli ARGS=\"purge-processed --collection mycollection\""
	@echo "    # Purge all processed data for all docs in a collection (does NOT delete raw files) and update progress.json"
	@echo "  make cli ARGS=\"delete-processed file1.pdf file2.txt\""
	@echo "    # Delete processed files from disk and update progress.json"
	@echo "  make cli ARGS=\"delete-processed --collection mycollection\""
	@echo "    # Delete all processed files in a collection from disk and update progress.json"
	@echo "  make cli ARGS=\"agent create --name 'AgentName'\""
	@echo "    # Create a new agent"
	@echo "  make cli ARGS=\"agent list\""
	@echo "    # List all agents"
	@echo "  make cli ARGS=\"agent delete AGENT_ID\""
	@echo "    # Delete an agent"
	@echo "  make cli ARGS=\"agent info AGENT_ID\""
	@echo "    # Get agent information"
	@echo "  make cli ARGS=\"agent actions AGENT_ID\""
	@echo "    # Get agent action history"
	@echo "  make cli ARGS=\"agent run AGENT_ID --action some_action\""
	@echo "    # Execute an action with an agent"
	@echo "  make cli ARGS=\"agent query AGENT_ID 'your query'\""
	@echo "    # Process a query using an agent"
	@echo "  make cli ARGS=\"agent evaluate AGENT_ID --query 'Q' --response 'R'\""
	@echo "    # Evaluate response quality"
	@echo "  make cli ARGS=\"agent improve AGENT_ID EVAL_ID\""
	@echo "    # Improve response based on evaluation"
	@echo "  make cli ARGS=\"agent plan AGENT_ID 'task'\""
	@echo "    # Create a plan for a task"
	@echo "  make cli ARGS=\"agent execute-plan AGENT_ID PLAN_ID\""
	@echo "    # Execute a plan"
	@echo ""
	@echo "Development commands:"
	@echo "  make shell              Start bash in API container"
	@echo "  make test               Run tests"
	@echo "  make lint               Run flake8"
	@echo "  make format             Format code with black and isort"
	@echo "  make venv               Setup virtual environment"
	@echo "  make setup-venv         Setup virtual environment and install requirements in CLI container"
	@echo "  make clean-containers   Remove all containers, networks, and the venv Docker volume"

clean-containers:
	$(DOCKER_COMPOSE) down --remove-orphans
	$(DOCKER_COMPOSE) volume rm $(DOCKER_COMPOSE)_venv || true
