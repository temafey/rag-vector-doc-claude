"""
Results for document commands.
"""
from dataclasses import dataclass

@dataclass
class AddDocumentResult:
    """Result of AddDocumentCommand execution."""
    document_id: str
    chunk_count: int

@dataclass
class AddFilesResult:
    """Result of AddFilesCommand execution."""
    total_documents: int
    total_chunks: int
