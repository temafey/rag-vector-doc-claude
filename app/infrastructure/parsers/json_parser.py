"""
JSON file parser.
"""
import json
from typing import List, Dict, Any
import os

from app.infrastructure.parsers.parser_factory import DocumentParser

class JsonParser(DocumentParser):
    """Parser for JSON files."""
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if parser can handle JSON files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file extension is .json, False otherwise
        """
        return file_path.lower().endswith('.json')
        
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse JSON file into list of documents.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of documents based on JSON structure
        """
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                # If data is a list, process each item as a document
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        # Handle both dict items and simple values
                        if isinstance(item, dict):
                            # Check for 'content' and 'metadata' fields
                            if 'content' in item:
                                content = item['content']
                                metadata = item.get('metadata', {})
                            else:
                                # If no 'content' field, use all fields as content
                                content = json.dumps(item, ensure_ascii=False)
                                metadata = {}
                                
                            # Add basic metadata
                            metadata.update({
                                "source_file": os.path.basename(file_path),
                                "file_type": "json",
                                "item_idx": idx
                            })
                            
                            documents.append({
                                "content": content,
                                "metadata": metadata
                            })
                        else:
                            # Simple value becomes content
                            documents.append({
                                "content": str(item),
                                "metadata": {
                                    "source_file": os.path.basename(file_path),
                                    "file_type": "json",
                                    "item_idx": idx
                                }
                            })
                            
                # If data is a dict, process it as a single document or multiple if it has documents array
                elif isinstance(data, dict):
                    # Check if it has a documents/items array
                    if 'documents' in data or 'items' in data:
                        items = data.get('documents', data.get('items', []))
                        for idx, item in enumerate(items):
                            if isinstance(item, dict):
                                content = item.get('content', json.dumps(item, ensure_ascii=False))
                                metadata = item.get('metadata', {})
                                
                                # Add basic metadata
                                metadata.update({
                                    "source_file": os.path.basename(file_path),
                                    "file_type": "json",
                                    "item_idx": idx
                                })
                                
                                documents.append({
                                    "content": content,
                                    "metadata": metadata
                                })
                            else:
                                documents.append({
                                    "content": str(item),
                                    "metadata": {
                                        "source_file": os.path.basename(file_path),
                                        "file_type": "json",
                                        "item_idx": idx
                                    }
                                })
                    else:
                        # Single document
                        content = data.get('content', json.dumps(data, ensure_ascii=False))
                        metadata = data.get('metadata', {})
                        
                        # Add basic metadata
                        metadata.update({
                            "source_file": os.path.basename(file_path),
                            "file_type": "json"
                        })
                        
                        documents.append({
                            "content": content,
                            "metadata": metadata
                        })
                
                # For any other type, convert to string
                else:
                    documents.append({
                        "content": str(data),
                        "metadata": {
                            "source_file": os.path.basename(file_path),
                            "file_type": "json"
                        }
                    })
                
        except Exception as e:
            raise ValueError(f"Error parsing JSON file {file_path}: {str(e)}")
        
        return documents
