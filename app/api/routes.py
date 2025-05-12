"""
FastAPI routes for RAG system.
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
import json
import uuid
import tempfile
import os
import asyncio
import logging
from datetime import datetime
from enum import Enum

from app.application.commands import (
    AddDocumentCommand,
    CreateCollectionCommand,
    DeleteDocumentCommand,
    UpdateDocumentLanguageCommand,
    ReindexDocumentCommand,
    AddFilesCommand,
)
from app.application.queries import (
    SearchQuery,
    ListCollectionsQuery,
    GetDocumentByIdQuery,
    GetSimilarDocumentsQuery,
    GetDocumentsByFilterQuery
)
from app.infrastructure.command_bus import command_bus
from app.infrastructure.query_bus import query_bus
from app.config.config_loader import get_config

# Setup logging
logger = logging.getLogger(__name__)

# Create router
from fastapi import APIRouter
router = APIRouter()

# Task status tracking
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# In-memory task storage (would be replaced by Redis or similar in production)
tasks = {}

# Data models with validation
class SearchRequest(BaseModel):
    query: str = Field(..., description="Query text to search for", min_length=1)
    collection: str = Field("default", description="Collection name to search in")
    limit: int = Field(5, description="Maximum number of results to return", ge=1, le=100)
    target_language: Optional[str] = Field(None, description="Target language for response")

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query must not be empty')
        return v

class SearchResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    query_language: str
    response_language: str

class AddDocumentRequest(BaseModel):
    content: str = Field(..., description="Document content", min_length=1)
    metadata: Dict[str, Any] = Field({}, description="Document metadata")
    collection: str = Field("default", description="Collection name")
    language: Optional[str] = Field(None, description="Document language")

    @validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Content must not be empty')
        return v

class DocumentResponse(BaseModel):
    id: str
    metadata: Dict[str, Any]
    chunk_count: int

class CollectionInfo(BaseModel):
    name: str
    document_count: int
    vector_dimension: int

class FilterRequest(BaseModel):
    filter: Dict[str, Any] = Field(..., description="Metadata filter criteria")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)
    offset: int = Field(0, description="Pagination offset", ge=0)

class BatchTranslationRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts to translate", min_items=1)
    source_language: str = Field(..., description="Source language code")
    target_language: str = Field(..., description="Target language code")

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Error handler for consistent error responses
def handle_exceptions(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise FastAPI HTTP exceptions
            raise
        except Exception as e:
            # Log the error
            logger.exception(f"Error in {func.__name__}: {str(e)}")
            
            # Return a consistent error response
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "An internal server error occurred",
                    "error": str(e)
                }
            )
    return wrapper

# Background task processors
async def process_document_upload(
    task_id: str,
    file_path: str, 
    filename: str,
    collection: str, 
    metadata_dict: Dict[str, Any],
    language: Optional[str]
):
    """Process document upload in background."""
    try:
        # Update task status
        tasks[task_id] = {
            "status": TaskStatus.PROCESSING,
            "created_at": datetime.now().isoformat(),
            "progress": 0
        }
        
        # Process file
        command = AddFilesCommand(
            files=[file_path],
            collection=collection,
            metadata={**metadata_dict, "original_filename": filename},
            language=language
        )
        
        # Execute command
        result = command_bus.dispatch(command)
        
        # Update task status
        tasks[task_id] = {
            "status": TaskStatus.COMPLETED,
            "created_at": datetime.now().isoformat(),
            "result": {
                "message": "File processed successfully",
                "document_count": result.total_documents,
                "chunk_count": result.total_chunks,
                "collection": collection
            }
        }
    except Exception as e:
        # Update task status with error
        tasks[task_id] = {
            "status": TaskStatus.FAILED,
            "created_at": datetime.now().isoformat(),
            "error": str(e)
        }
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error removing temporary file {file_path}: {str(e)}")

# Endpoints with improved documentation
@router.get("/health")
@handle_exceptions
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Status and version information
    """
    config = get_config()
    
    # Add more health checks as needed
    health_info = {
        "status": "ok",
        "version": config["app"].get("version", "0.1.0"),
        "timestamp": datetime.now().isoformat()
    }
    
    return health_info

@router.post("/search", response_model=SearchResponse)
@handle_exceptions
async def search(request: SearchRequest):
    """
    Search using RAG and return enhanced response with sources.
    
    Args:
        request: Search request with query, collection, limit, and target language
        
    Returns:
        Generated response with sources
    """
    query = SearchQuery(
        query_text=request.query,
        collection=request.collection,
        limit=request.limit,
        target_language=request.target_language
    )
    
    result = query_bus.dispatch(query)
    return SearchResponse(
        response=result.response,
        sources=[{
            "id": source.id,
            "title": source.title,
            "metadata": source.metadata,
            "score": source.score,
            "content": source.content
        } for source in result.sources],
        query_language=result.query_language,
        response_language=result.response_language
    )

@router.post("/search/similar", response_model=Dict[str, Any])
@handle_exceptions
async def find_similar_documents(query: GetSimilarDocumentsQuery):
    """
    Find documents similar to reference text.
    
    Args:
        query: Query with reference text, collection, limit, and exclusions
        
    Returns:
        List of similar documents
    """
    result = query_bus.dispatch(query)
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "score": doc.score,
                "content": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            }
            for doc in result.documents
        ]
    }

@router.post("/documents", response_model=DocumentResponse)
@handle_exceptions
async def add_document(request: AddDocumentRequest):
    """
    Add document to collection.
    
    Args:
        request: Document content, metadata, collection, and language
        
    Returns:
        Document ID and metadata
    """
    document_id = str(uuid.uuid4())
    command = AddDocumentCommand(
        id=document_id,
        content=request.content,
        metadata=request.metadata,
        collection=request.collection,
        language=request.language
    )
    
    result = command_bus.dispatch(command)
    return DocumentResponse(
        id=document_id,
        metadata=request.metadata,
        chunk_count=result.chunk_count
    )

@router.post("/documents/upload")
@handle_exceptions
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("default"),
    metadata: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    max_file_size: int = 100 * 1024 * 1024  # 100MB limit
):
    """
    Upload document file for synchronous processing.
    
    Args:
        file: File to upload
        collection: Collection name
        metadata: JSON string with metadata
        language: Document language
        
    Returns:
        Processing result
    """
    # Validate file size
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks for reading
    chunks = []
    
    # Read file in chunks to check size and avoid memory issues
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
        file_size += len(chunk)
        
        if file_size > max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_file_size / (1024 * 1024)}MB"
            )
    
    # Reset file position
    await file.seek(0)
    
    # Convert metadata string to dict
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Save file temporarily using context manager
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        temp_file_path = temp_file.name
        # Write all chunks to file
        for chunk in chunks:
            temp_file.write(chunk)
    
    try:
        # Process file
        command = AddFilesCommand(
            files=[temp_file_path],
            collection=collection,
            metadata={**metadata_dict, "original_filename": file.filename},
            language=language
        )
        
        result = command_bus.dispatch(command)
        
        return {
            "message": "File uploaded successfully",
            "document_count": result.total_documents,
            "chunk_count": result.total_chunks,
            "collection": collection
        }
    finally:
        # Remove temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.post("/documents/upload/async", response_model=TaskResponse)
@handle_exceptions
async def upload_document_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form("default"),
    metadata: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    max_file_size: int = 100 * 1024 * 1024  # 100MB limit
):
    """
    Upload document file for asynchronous processing.
    
    Args:
        background_tasks: FastAPI background tasks
        file: File to upload
        collection: Collection name
        metadata: JSON string with metadata
        language: Document language
        
    Returns:
        Task ID for status tracking
    """
    # Validate file size
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks for reading
    chunks = []
    
    # Read file in chunks to check size and avoid memory issues
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
        file_size += len(chunk)
        
        if file_size > max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_file_size / (1024 * 1024)}MB"
            )
    
    # Reset file position
    await file.seek(0)
    
    # Convert metadata string to dict
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        temp_file_path = temp_file.name
        # Write all chunks to file
        for chunk in chunks:
            temp_file.write(chunk)
    
    # Create task ID
    task_id = str(uuid.uuid4())
    
    # Initialize task
    tasks[task_id] = {
        "status": TaskStatus.PENDING,
        "created_at": datetime.now().isoformat()
    }
    
    # Add task to background tasks
    background_tasks.add_task(
        process_document_upload,
        task_id,
        temp_file_path,
        file.filename,
        collection,
        metadata_dict,
        language
    )
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        created_at=tasks[task_id]["created_at"]
    )

@router.get("/tasks/{task_id}", response_model=TaskResponse)
@handle_exceptions
async def get_task_status(task_id: str):
    """
    Get status of background task.
    
    Args:
        task_id: Task ID
        
    Returns:
        Task status and result
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus(task["status"]),
        created_at=task["created_at"],
        result=task.get("result"),
        error=task.get("error")
    )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
@handle_exceptions
async def get_document(document_id: str, collection: str = "default"):
    """
    Get document information.
    
    Args:
        document_id: Document ID
        collection: Collection name
        
    Returns:
        Document information
    """
    query = GetDocumentByIdQuery(
        document_id=document_id,
        collection=collection
    )
    result = query_bus.dispatch(query)
    if not result.document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=result.document.id,
        metadata=result.document.metadata.to_dict(),
        chunk_count=len(result.document.chunks)
    )

@router.delete("/documents/{document_id}")
@handle_exceptions
async def delete_document(document_id: str, collection: str = "default"):
    """
    Delete document from collection.
    
    Args:
        document_id: Document ID
        collection: Collection name
        
    Returns:
        Success message
    """
    command = DeleteDocumentCommand(
        document_id=document_id,
        collection=collection
    )
    command_bus.dispatch(command)
    return {"message": f"Document {document_id} deleted successfully"}

@router.put("/documents/{document_id}/language")
@handle_exceptions
async def update_document_language(
    document_id: str,
    language: str,
    collection: str = "default"
):
    """
    Update document language.
    
    Args:
        document_id: Document ID
        language: New language code
        collection: Collection name
        
    Returns:
        Success message
    """
    command = UpdateDocumentLanguageCommand(
        document_id=document_id,
        language=language,
        collection=collection
    )
    
    command_bus.dispatch(command)
    
    return {
        "message": f"Document {document_id} language updated to {language}"
    }

@router.post("/documents/{document_id}/reindex")
@handle_exceptions
async def reindex_document(
    document_id: str,
    collection: str = "default",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    language: Optional[str] = None
):
    """
    Reindex document with new parameters.
    
    Args:
        document_id: Document ID
        collection: Collection name
        chunk_size: New chunk size
        chunk_overlap: New chunk overlap
        language: New language code
        
    Returns:
        Success message
    """
    command = ReindexDocumentCommand(
        document_id=document_id,
        collection=collection,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        language=language
    )
    
    command_bus.dispatch(command)
    
    return {
        "message": f"Document {document_id} reindexed successfully"
    }

@router.post("/documents/filter")
@handle_exceptions
async def filter_documents(
    request: FilterRequest,
    collection: str = "default"
):
    """
    Get documents by metadata filter.
    
    Args:
        request: Filter criteria, limit, and offset
        collection: Collection name
        
    Returns:
        Filtered documents and total count
    """
    query = GetDocumentsByFilterQuery(
        filter=request.filter,
        collection=collection,
        limit=request.limit,
        offset=request.offset
    )
    
    result = query_bus.dispatch(query)
    
    return {
        "documents": result.documents,
        "total": result.total
    }

@router.get("/collections", response_model=List[CollectionInfo])
@handle_exceptions
async def list_collections():
    """
    Get list of all collections.
    
    Returns:
        List of collections with stats
    """
    query = ListCollectionsQuery()
    result = query_bus.dispatch(query)
    return [
        CollectionInfo(
            name=collection.name,
            document_count=collection.document_count,
            vector_dimension=collection.vector_dimension
        )
        for collection in result.collections
    ]

@router.post("/collections/{name}")
@handle_exceptions
async def create_collection(name: str, vector_size: int = Query(1536, ge=1)):
    """
    Create new collection.
    
    Args:
        name: Collection name
        vector_size: Vector dimension
        
    Returns:
        Success message
    """
    command = CreateCollectionCommand(name=name, vector_size=vector_size)
    command_bus.dispatch(command)
    return {"message": f"Collection {name} created successfully"}

@router.delete("/collections/{name}")
@handle_exceptions
async def delete_collection(name: str):
    """
    Delete collection.
    
    Args:
        name: Collection name
        
    Returns:
        Success message
    """
    command = DeleteCollectionCommand(name=name)
    command_bus.dispatch(command)
    return {"message": f"Collection {name} deleted successfully"}

@router.post("/translate/batch")
@handle_exceptions
async def translate_batch(request: BatchTranslationRequest):
    """
    Translate multiple texts in parallel.
    
    Args:
        request: Texts, source language, and target language
        
    Returns:
        Translated texts
    """
    # Import inside function to avoid circular imports
    from app.domain.services.translation_service import TranslationService
    
    # Create translation service
    translation_service = TranslationService()
    
    # Translate texts asynchronously
    translated_texts = await translation_service.translate_batch_async(
        request.texts,
        request.source_language,
        request.target_language
    )
    
    return {
        "source_language": request.source_language,
        "target_language": request.target_language,
        "translated_texts": translated_texts
    }

@router.get("/translation/supported-languages")
@handle_exceptions
async def get_supported_languages():
    """
    Get supported language pairs for translation.
    
    Returns:
        List of supported language pairs
    """
    # Import inside function to avoid circular imports
    from app.domain.services.translation_service import TranslationService
    
    # Create translation service
    translation_service = TranslationService()
    
    # Get supported language pairs
    language_pairs = translation_service.get_supported_language_pairs()
    
    return {
        "supported_language_pairs": [
            {"source": src, "target": tgt}
            for src, tgt in language_pairs
        ]
    }

@router.get("/stats/translation-cache")
@handle_exceptions
async def get_translation_cache_stats():
    """
    Get statistics about the translation cache.
    
    Returns:
        Cache statistics
    """
    # Import inside function to avoid circular imports
    from app.domain.services.translation_service import TranslationService
    
    # Create translation service
    translation_service = TranslationService()
    
    # Get cache statistics
    stats = translation_service.get_cache_stats()
    
    return stats

@router.post("/stats/translation-cache/clear")
@handle_exceptions
async def clear_translation_cache():
    """
    Clear the translation cache.
    
    Returns:
        Success message
    """
    # Import inside function to avoid circular imports
    from app.domain.services.translation_service import TranslationService
    
    # Create translation service
    translation_service = TranslationService()
    
    # Clear cache
    translation_service.clear_cache()
    
    return {"message": "Translation cache cleared successfully"}
