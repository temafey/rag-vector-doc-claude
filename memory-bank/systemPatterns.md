# System Patterns

- Domain-Driven Design (DDD) with clear separation: API, Application, Domain, Infrastructure
- CQRS: Commands/queries/handlers for all operations
- Event-driven: EventBus, CommandBus, QueryBus
- Repository pattern for persistence (see agent_repository.py)
- FastAPI for API, Click for CLI
- YAML config with environment overrides
- Docker for deployment, Makefile for workflow
- Extensible agent model with self-assessment and planning 