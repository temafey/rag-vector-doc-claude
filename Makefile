.PHONY: build up down logs shell test lint format help

# Variables
DOCKER_COMPOSE = docker-compose
API_SERVICE = api
CLI_SERVICE = cli
QDRANT_SERVICE = qdrant

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
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) python /app/cli.py $(ARGS)

# Add files to index
add-files:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) python /app/cli.py add $(FILES) --collection $(COLLECTION)

# Execute query
query:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) python /app/cli.py query "$(QUERY)" --collection $(COLLECTION)

# Collection management
list-collections:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) python /app/cli.py collections --list

create-collection:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) python /app/cli.py collections --create $(NAME)

delete-collection:
	$(DOCKER_COMPOSE) exec $(CLI_SERVICE) python /app/cli.py collections --delete $(NAME)

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
venv:
	./scripts/setup_venv.sh

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
	@echo "CLI commands:"
	@echo "  make cli ARGS=\"command args\"  Execute CLI command"
	@echo "  make add-files FILES=\"file1.pdf file2.txt\" COLLECTION=\"default\"  Add files to index"
	@echo "  make query QUERY=\"your query\" COLLECTION=\"default\"  Execute query"
	@echo "  make list-collections   List collections"
	@echo "  make create-collection NAME=\"name\"  Create collection"
	@echo "  make delete-collection NAME=\"name\"  Delete collection"
	@echo ""
	@echo "Development commands:"
	@echo "  make shell              Start bash in API container"
	@echo "  make test               Run tests"
	@echo "  make lint               Run flake8"
	@echo "  make format             Format code with black and isort"
	@echo "  make venv               Setup virtual environment"
