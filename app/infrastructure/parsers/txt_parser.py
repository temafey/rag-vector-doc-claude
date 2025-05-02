"""
Text file parser.
"""
from typing import List, Dict, Any
import os

from app.infrastructure.parsers.parser_factory import DocumentParser

class TxtParser(DocumentParser):
    """Parser for text files."""
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if parser can handle text files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file extension is .txt, False otherwise
        """
        return file_path.lower().endswith('.txt')
        
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse text file into list of documents.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            List containing a single document with the file content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Extract title from filename
                file_name = os.path.basename(file_path)
                title = os.path.splitext(file_name)[0]
                
                return [{
                    "content": content,
                    "metadata": {
                        "source_file": file_name,
                        "file_type": "txt",
                        "title": title
                    }
                }]
        except Exception as e:
            raise ValueError(f"Error parsing text file {file_path}: {str(e)}")
