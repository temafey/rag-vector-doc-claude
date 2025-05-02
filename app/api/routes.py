"""
FastAPI routes for RAG system.
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import uuid
import tempfile
import os

from app.application.commands import (
    AddDocumentCommand,
    CreateCollectionCommand,
    DeleteDocumentCommand,
    UpdateDocumentLanguageCommand
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

# Create router
from fastapi import APIRouter
router = APIRouter()

# Data models
class SearchRequest(BaseModel):
    query: str
    collection: str = "default"
    limit: int = 5
    target_language: Optional[str] = None

class SearchResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    query_language: str
    response_language: str

class AddDocumentRequest(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}
    collection: str = "default"
    language: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    metadata: Dict[str, Any]
    chunk_count: int

class CollectionInfo(BaseModel):
    name: str
    document_count: int
    vector_dimension: int

class FilterRequest(BaseModel):
    filter: Dict[str, Any]
    limit: int = 10
    offset: int = 0

# Endpoints
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    config = get_config()
    return {
        "status": "ok",
        "version": config["app"].get("version", "0.1.0")
    }

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search using RAG."""
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

@router.post("/documents", response_model=DocumentResponse)
async def add_document(request: AddDocumentRequest):
    """Add document to collection."""
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
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("default"),
    metadata: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """Upload document file."""
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
        content = await file.read()
        temp_file.write(content)
    
    try:
        # Process file
        from app.application.commands import AddFilesCommand
        
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
        os.unlink(temp_file_path)

@router.get("/collections", response_model=List[CollectionInfo])
async def list_collections():
    """Get list of all collections."""
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
async def create_collection(name: str):
    """Create new collection."""
    command = CreateCollectionCommand(name=name)
    command_bus.dispatch(command)
    return {"message": f"Collection {name} created successfully"}

@router.delete("/collections/{name}")
async def delete_collection(name: str):
    """Delete collection."""
    from app.application.commands import DeleteCollectionCommand
    command = DeleteCollectionCommand(name=name)
    command_bus.dispatch(command)
    return {"message": f"Collection {name} deleted successfully"}

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, collection: str = "default"):
    """Delete document from collection."""
    command = DeleteDocumentCommand(
        document_id=document_id,
        collection=collection
    )
    command_bus.dispatch(command)
    return {"message": f"Document {document_id} deleted successfully"}

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, collection: str = "default"):
    """Get document information."""
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

@router.post("/documents/similar")
async def find_similar_documents(
    query: GetSimilarDocumentsQuery
):
    """Find documents similar to reference text."""
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

@router.post("/documents/filter")
async def filter_documents(
    request: FilterRequest,
    collection: str = "default"
):
    """Get documents by metadata filter."""
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

@router.put("/documents/{document_id}/language")
async def update_document_language(
    document_id: str,
    language: str,
    collection: str = "default"
):
    """Update document language."""
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
async def reindex_document(
    document_id: str,
    collection: str = "default",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    language: Optional[str] = None
):
    """Reindex document with new parameters."""
    from app.application.commands import ReindexDocumentCommand
    
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
