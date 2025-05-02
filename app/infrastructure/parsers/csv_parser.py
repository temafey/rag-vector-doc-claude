"""
CSV file parser.
"""
import csv
from typing import List, Dict, Any
import os

from app.infrastructure.parsers.parser_factory import DocumentParser

class CsvParser(DocumentParser):
    """Parser for CSV files."""
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if parser can handle CSV files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file extension is .csv, False otherwise
        """
        return file_path.lower().endswith('.csv')
        
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse CSV file into list of documents.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of documents, each row as a separate document
        """
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Get column names
                fields = reader.fieldnames or []
                
                # Get content column (if specified in config, default to first column)
                content_column = fields[0] if fields else None
                
                for row_idx, row in enumerate(reader):
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                        
                    # Determine content
                    content = ""
                    if content_column and content_column in row:
                        content = row[content_column]
                    else:
                        # Join all values as content
                        content = " ".join(str(value) for value in row.values() if value)
                    
                    # Create metadata
                    metadata = {
                        "source_file": os.path.basename(file_path),
                        "file_type": "csv",
                        "row_idx": row_idx + 1
                    }
                    
                    # Add all columns as metadata
                    for key, value in row.items():
                        if key != content_column:  # Avoid duplication if content column is used
                            metadata[f"csv_{key}"] = value
                    
                    documents.append({
                        "content": content,
                        "metadata": metadata
                    })
        except Exception as e:
            raise ValueError(f"Error parsing CSV file {file_path}: {str(e)}")
        
        return documents
