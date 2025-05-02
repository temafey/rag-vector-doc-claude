# RAG System with Qdrant and LangChain

A multilingual Retrieval Augmented Generation (RAG) system built with Qdrant vector database and LangChain, featuring Domain-Driven Design (DDD), Command Query Responsibility Segregation (CQRS), and event-driven architecture.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [API Reference](#api-reference)
  - [CLI Commands](#cli-commands)
- [Module Reference](#module-reference)
- [Development](#development)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)

## Overview

This system enhances large language model responses by augmenting prompts with relevant information retrieved from your document collection. It supports multiple file formats, languages, and provides both API and CLI interfaces.

### Features

- **Multilingual Support**: Process and search documents in multiple languages (currently Russian and English)
- **Multiple File Formats**: Support for CSV, JSON, TXT, and PDF
- **Vector Search**: Semantic search powered by Qdrant vector database
- **DDD Architecture**: Clean domain separation with CQRS and EventBus
- **API & CLI**: Both REST API and command-line interfaces
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Flexible Configuration**: YAML-based configuration for different environments

## Architecture

The system follows Domain-Driven Design principles, with clear separation of concerns:

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│                     │    │                     │    │                     │
│      API Layer      │    │     CLI Layer       │    │  Claude Integration │
│    (FastAPI)        │    │     (Click)         │    │                     │
│                     │    │                     │    │                     │
└─────────┬───────────┘    └──────────┬──────────┘    └──────────┬──────────┘
          │                           │                          │
          │                           │                          │
          ▼                           ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                            Application Layer                                │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │             │    │             │    │             │    │             │  │
│  │  Commands   │    │  Queries    │    │  Command    │    │   Query     │  │
│  │             │    │             │    │  Handlers   │    │  Handlers   │  │
│  │             │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                              Domain Layer                                   │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │             │    │             │    │             │    │             │  │
│  │   Models    │    │  Services   │    │   Events    │    │  Interfaces │  │
│  │             │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           Infrastructure Layer                              │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │             │    │             │    │             │    │             │  │
│  │ CommandBus  │    │  EventBus   │    │  QueryBus   │    │ Repositories│  │
│  │             │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │             │    │             │    │             │                     │
│  │   Parsers   │    │  Qdrant     │    │ Integrations│                     │
│  │             │    │  Client     │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- OpenAI API key (for LangChain embeddings)

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/rag-system.git
   cd rag-system
   ```

2. Create an `.env` file with your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your_openai_api_key" > .env
   ```

3. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

4. Verify the API is running:
   ```bash
   curl http://localhost:8000/health
   ```

### Using Virtual Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/rag-system.git
   cd rag-system
   ```

2. Set up the virtual environment:
   ```bash
   # Create and setup virtual environment
   make venv
   
   # Activate virtual environment
   source venv/bin/activate
   ```

3. Create an `.env` file with your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your_openai_api_key" > .env
   ```

4. Start Qdrant (either with Docker or standalone)
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 \
     -v $(pwd)/qdrant_data:/qdrant/storage \
     qdrant/qdrant
   ```

5. Start the API server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Configuration

The system uses YAML files for configuration, with environment-specific overrides:

- `app/config/base.yaml` - Base configuration
- `app/config/development.yaml` - Development overrides
- `app/config/production.yaml` - Production overrides
- `app/config/test.yaml` - Test environment overrides

You can also override settings using environment variables with the prefix `APP_`. For example, `APP_QDRANT_HOST=localhost` will override the `qdrant.host` configuration.

Example configuration:

```yaml
# app/config/base.yaml
app:
  name: "RAG System"
  version: "0.1.0"

qdrant:
  host: "localhost"
  port: 6333

langchain:
  embedding_model: "text-embedding-ada-002"
  multilingual_embedding_model: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  llm_model: "gpt-3.5-turbo"

storage:
  document_path: "./storage/documents"
  
indexing:
  chunk_size: 1000
  chunk_overlap: 200
  batch_size: 10

languages:
  supported:
    - "en"
    - "ru"
  default: "en"
  auto_detect: true

translation:
  enabled: true
  enabled_pairs:
    - ["ru", "en"]
    - ["en", "ru"]
```

## Usage

### API Reference

The system provides a RESTful API for document management and search:

#### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

#### Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is RAG?",
    "collection": "default",
    "limit": 5,
    "target_language": "en"
  }'
```

Response:
```json
{
  "response": "RAG (Retrieval Augmented Generation) is a technique that combines retrieval-based and generation-based approaches to enhance language model outputs...",
  "sources": [
    {
      "id": "doc123_1",
      "title": "Introduction to RAG",
      "content": "RAG stands for Retrieval Augmented Generation...",
      "metadata": {
        "source": "api",
        "language": "en",
        "author": "John Doe"
      },
      "score": 0.89
    },
    ...
  ],
  "query_language": "en",
  "response_language": "en"
}
```

#### Add Document

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "content": "RAG stands for Retrieval Augmented Generation...",
    "metadata": {
      "title": "Introduction to RAG",
      "author": "John Doe",
      "language": "en"
    },
    "collection": "default"
  }'
```

Response:
```json
{
  "id": "7f4b8c12-1d2e-4f5a-9b6c-8a7b9c0d1e2f",
  "metadata": {
    "title": "Introduction to RAG",
    "author": "John Doe",
    "language": "en"
  },
  "chunk_count": 1
}
```

#### Upload Document

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@path/to/document.pdf" \
  -F "collection=default" \
  -F 'metadata={"title": "My Document", "author": "Jane Smith"}'
```

Response:
```json
{
  "message": "File uploaded successfully",
  "document_count": 1,
  "chunk_count": 5,
  "collection": "default"
}
```

#### List Collections

```bash
curl http://localhost:8000/collections
```

Response:
```json
[
  {
    "name": "default",
    "document_count": 15,
    "vector_dimension": 1536
  },
  {
    "name": "research",
    "document_count": 42,
    "vector_dimension": 1536
  }
]
```

#### Create Collection

```bash
curl -X POST http://localhost:8000/collections/new_collection
```

Response:
```json
{
  "message": "Collection new_collection created successfully"
}
```

### CLI Commands

The system provides a command-line interface for common operations:

#### Add Files

Add files to the index:

```bash
# Using docker-compose:
docker-compose exec cli python /app/cli.py add /data/file1.pdf /data/file2.txt --collection default

# Using Makefile:
make add-files FILES="data/file1.pdf data/file2.txt" COLLECTION="default"

# Using venv:
python cli.py add path/to/file1.pdf path/to/file2.txt --collection default
```

Options:
- `--collection`, `-c`: Collection name (default: "default")
- `--chunk-size`: Size of text chunks (default: 1000)
- `--chunk-overlap`: Overlap between chunks (default: 200)
- `--metadata`, `-m`: Metadata in key=value format (can be specified multiple times)
- `--language`, `-l`: Document language (auto-detected if not specified)

#### Query

Search for documents:

```bash
# Using docker-compose:
docker-compose exec cli python /app/cli.py query "What is RAG?" --collection default

# Using Makefile:
make query QUERY="What is RAG?" COLLECTION="default"

# Using venv:
python cli.py query "What is RAG?" --collection default --language en
```

Options:
- `--collection`, `-c`: Collection name (default: "default")
- `--limit`, `-l`: Number of results to return (default: 5)
- `--language`: Response language (default: query language)

#### Manage Collections

List, create, and delete collections:

```bash
# List collections
python cli.py collections --list

# Create collection
python cli.py collections --create new_collection

# Delete collection
python cli.py collections --delete old_collection
```

#### Add Text Directly

Add text content directly:

```bash
python cli.py add-text "This is the content to add" --title "Example Document" --language en
```

Options:
- `--collection`, `-c`: Collection name (default: "default")
- `--title`, `-t`: Document title
- `--metadata`, `-m`: Metadata in key=value format
- `--language`, `-l`: Document language (auto-detected if not specified)

#### Find Similar Documents

Find documents similar to provided text:

```bash
python cli.py similar "Text to find similar documents to" --collection default --limit 5
```

Options:
- `--collection`, `-c`: Collection name (default: "default")
- `--limit`, `-l`: Number of results to return (default: 5)

## Module Reference

### Domain Layer

#### Models

- **Document** (`app/domain/models/document.py`): Core entity representing a document with metadata
- **DocumentChunk** (`app/domain/models/document.py`): Represents a chunk of text from a document
- **DocumentMetadata** (`app/domain/models/document.py`): Value object for document metadata

#### Services

- **TextSplitter** (`app/domain/services/text_splitter.py`): Splits documents into smaller chunks
- **MultilingualEmbeddingGenerator** (`app/domain/services/multilingual_embedding_generator.py`): Generates vector embeddings for text in multiple languages
- **ResponseGenerator** (`app/domain/services/response_generator.py`): Generates responses based on retrieved context
- **LanguageDetector** (`app/domain/services/language_detector.py`): Detects the language of text
- **TranslationService** (`app/domain/services/translation_service.py`): Translates text between languages

### Application Layer

#### Commands

- **AddDocumentCommand** (`app/application/commands/document_commands.py`): Adds a document to the system
- **AddFilesCommand** (`app/application/commands/document_commands.py`): Adds multiple files to the system
- **DeleteDocumentCommand** (`app/application/commands/document_commands.py`): Deletes a document
- **CreateCollectionCommand** (`app/application/commands/document_commands.py`): Creates a collection

#### Queries

- **SearchQuery** (`app/application/queries/document_queries.py`): Searches for documents
- **GetDocumentByIdQuery** (`app/application/queries/document_queries.py`): Retrieves a document by ID
- **ListCollectionsQuery** (`app/application/queries/document_queries.py`): Lists all collections

### Infrastructure Layer

#### Repositories

- **DocumentRepository** (`app/infrastructure/repositories/document_repository.py`): Stores and retrieves documents
- **VectorRepository** (`app/infrastructure/repositories/vector_repository.py`): Interfaces with the Qdrant vector database

#### Buses

- **CommandBus** (`app/infrastructure/command_bus.py`): Routes commands to handlers
- **EventBus** (`app/infrastructure/event_bus.py`): Publishes and subscribes to events
- **QueryBus** (`app/infrastructure/query_bus.py`): Routes queries to handlers

#### Parsers

- **ParserFactory** (`app/infrastructure/parsers/parser_factory.py`): Factory for document parsers
- **CsvParser** (`app/infrastructure/parsers/csv_parser.py`): Parses CSV files
- **JsonParser** (`app/infrastructure/parsers/json_parser.py`): Parses JSON files
- **TxtParser** (`app/infrastructure/parsers/txt_parser.py`): Parses text files
- **PdfParser** (`app/infrastructure/parsers/pdf_parser.py`): Parses PDF files

### API Layer

- **FastAPI Routes** (`app/api/routes.py`): REST API endpoints

### CLI Layer

- **CLI Commands** (`cli.py`): Command-line interface

### Integrations

- **ClaudeDesktopIntegration** (`app/integrations/claude_desktop.py`): Integration with Claude Desktop

## Development

### Setting Up Development Environment

1. Create a virtual environment:
   ```bash
   make venv
   source venv/bin/activate
   ```

2. Run tests:
   ```bash
   make test
   ```

3. Format code:
   ```bash
   make format
   ```

### Adding a New Parser

To add support for a new file format:

1. Create a new parser in `app/infrastructure/parsers/`:
   ```python
   from app.infrastructure.parsers.parser_factory import DocumentParser
   from typing import List, Dict, Any

   class NewFormatParser(DocumentParser):
       def can_parse(self, file_path: str) -> bool:
           return file_path.lower().endswith('.new_format')
           
       def parse(self, file_path: str) -> List[Dict[str, Any]]:
           # Implementation
           return [{"content": "...", "metadata": {...}}]
   ```

2. Register the parser in `app/main.py`:
   ```python
   from app.infrastructure.parsers.new_format_parser import NewFormatParser

   # Register parsers
   parser_factory.register_parser(NewFormatParser())
   ```

## Docker

### Container Structure

The system uses the following containers:

- **api**: FastAPI server
- **qdrant**: Qdrant vector database
- **cli**: Command-line interface

### Using Makefile

```bash
# Build containers
make build

# Start services
make up

# View logs
make logs

# Stop services
make down
```

## Troubleshooting

### Common Issues

#### Connection to Qdrant Failed

```
Error: Failed to connect to Qdrant at qdrant:6333
```

**Solution**: 
- Check if Qdrant container is running: `docker-compose ps`
- Verify network connectivity: `docker-compose exec api ping qdrant`

#### OpenAI API Key Not Found

```
Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.
```

**Solution**:
- Make sure you have created an `.env` file with your API key
- Or set the environment variable directly: `export OPENAI_API_KEY=your_key`

#### Out of Memory with Large Documents

```
Error: Process killed due to memory overflow
```

**Solution**:
- Reduce batch size in configuration
- Increase container memory limit in docker-compose.yml
- Split large files before processing

### Logs

To check logs:

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs api

# Follow logs
docker-compose logs -f api
```

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
