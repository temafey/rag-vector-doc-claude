"""
Integration with Claude Desktop.
"""
from typing import Dict, Any, List, Optional
import requests
import json

class ClaudeDesktopIntegration:
    """Integration with Claude Desktop."""
    
    def __init__(self, api_base_url: str):
        """
        Initialize integration.
        
        Args:
            api_base_url: Base URL of RAG API
        """
        self.api_base_url = api_base_url.rstrip('/')
    
    def search(self, query: str, collection: str = "default", limit: int = 5,
              target_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Search using RAG system.
        
        Args:
            query: Query text
            collection: Collection name
            limit: Maximum number of results
            target_language: Target language for response
            
        Returns:
            Search result
        """
        url = f"{self.api_base_url}/search"
        
        payload = {
            "query": query,
            "collection": collection,
            "limit": limit
        }
        
        if target_language:
            payload["target_language"] = target_language
        
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error searching: {response.text}")
        
        return response.json()
    
    def prompt_with_rag(self, query: str, collection: str = "default", limit: int = 5,
                       target_language: Optional[str] = None) -> str:
        """
        Create prompt for Claude with RAG information.
        
        Args:
            query: Query text
            collection: Collection name
            limit: Maximum number of results
            target_language: Target language for response
            
        Returns:
            Prompt for Claude
        """
        search_result = self.search(query, collection, limit, target_language)
        
        context_parts = []
        for i, source in enumerate(search_result["sources"], 1):
            source_info = f"[Source {i}] {source.get('title', 'Unknown')}"
            if "metadata" in source and "source_file" in source["metadata"]:
                source_info += f" (from {source['metadata']['source_file']})"
                
            context_parts.append(f"{source_info}\n{source['content']}")
        
        context = "\n\n".join(context_parts)
        
        # Use appropriate language for prompt template
        response_language = search_result.get("response_language", "en")
        
        if response_language == "ru":
            prompt = f"""Информация из базы данных:

{context}

На основе этой информации, ответь на следующий вопрос:
{query}

Используй только информацию, представленную выше. Если информации недостаточно, скажи, что не можешь ответить на вопрос."""
        else:
            prompt = f"""Information from the database:

{context}

Based on this information, answer the following question:
{query}

Use only the information presented above. If the information is insufficient, say that you cannot answer the question."""
        
        return prompt
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None, 
                    collection: str = "default", language: Optional[str] = None) -> Dict[str, Any]:
        """
        Add document to RAG system.
        
        Args:
            content: Document content
            metadata: Document metadata
            collection: Collection name
            language: Document language
            
        Returns:
            Result of adding document
        """
        url = f"{self.api_base_url}/documents"
        
        payload = {
            "content": content,
            "metadata": metadata or {},
            "collection": collection
        }
        
        if language:
            payload["language"] = language
        
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error adding document: {response.text}")
        
        return response.json()
    
    def upload_file(self, file_path: str, metadata: Dict[str, Any] = None, 
                   collection: str = "default", language: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload file to RAG system.
        
        Args:
            file_path: Path to file
            metadata: Document metadata
            collection: Collection name
            language: Document language
            
        Returns:
            Result of file upload
        """
        url = f"{self.api_base_url}/documents/upload"
        
        # Prepare metadata
        metadata_str = json.dumps(metadata or {})
        
        # Create multipart/form-data request
        files = {
            'file': open(file_path, 'rb')
        }
        
        data = {
            'collection': collection,
            'metadata': metadata_str
        }
        
        if language:
            data['language'] = language
        
        response = requests.post(url, files=files, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Error uploading file: {response.text}")
        
        return response.json()
    
    def create_collection(self, name: str) -> Dict[str, Any]:
        """
        Create new collection.
        
        Args:
            name: Collection name
            
        Returns:
            Result of collection creation
        """
        url = f"{self.api_base_url}/collections/{name}"
        
        response = requests.post(url)
        
        if response.status_code != 200:
            raise Exception(f"Error creating collection: {response.text}")
        
        return response.json()
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        Get list of collections.
        
        Returns:
            List of collections
        """
        url = f"{self.api_base_url}/collections"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Error listing collections: {response.text}")
        
        return response.json()
    
    def find_similar(self, text: str, collection: str = "default", 
                    limit: int = 5, exclude_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Find documents similar to text.
        
        Args:
            text: Reference text
            collection: Collection name
            limit: Maximum number of results
            exclude_ids: Document IDs to exclude
            
        Returns:
            List of similar documents
        """
        url = f"{self.api_base_url}/documents/similar"
        
        payload = {
            "reference_text": text,
            "collection": collection,
            "limit": limit,
            "exclude_ids": exclude_ids or []
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error finding similar documents: {response.text}")
        
        return response.json()["documents"]
