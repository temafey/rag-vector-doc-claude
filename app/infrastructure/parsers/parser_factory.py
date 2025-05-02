"""
Factory for document parsers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class DocumentParser(ABC):
    """Base interface for document parsers."""
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        Check if parser can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if parser can handle the file, False otherwise
        """
        pass
        
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse file into list of documents.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of documents, each as a dict with 'content' and optional 'metadata' keys
        """
        pass

class ParserFactory:
    """Factory for creating document parsers based on file type."""
    
    def __init__(self):
        self.parsers: List[DocumentParser] = []
        
    def register_parser(self, parser: DocumentParser) -> None:
        """
        Register a parser in the factory.
        
        Args:
            parser: Parser instance to register
        """
        self.parsers.append(parser)
        
    def get_parser(self, file_path: str) -> DocumentParser:
        """
        Get appropriate parser for the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Parser that can handle the file
            
        Raises:
            ValueError: If no parser is found for the file
        """
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        raise ValueError(f"Unsupported file format: {file_path}")
