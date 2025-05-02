"""
Service for generating embeddings using OpenAI.
"""
from typing import List
from langchain.embeddings import OpenAIEmbeddings
from app.config.config_loader import get_config

class EmbeddingGenerator:
    """Service for generating text embeddings."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize embedding generator.
        
        Args:
            api_key: OpenAI API key (if not specified, uses environment variable OPENAI_API_KEY)
        """
        config = get_config()
        model_name = config["langchain"].get("embedding_model", "text-embedding-ada-002")
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            model=model_name
        )
    
    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Source text
            
        Returns:
            Embedding as list of numbers
        """
        return self.embeddings.embed_query(text)
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for list of texts.
        
        Args:
            texts: List of texts
            
        Returns:
            List of embeddings
        """
        return self.embeddings.embed_documents(texts)
