"""
Service for generating multilingual embeddings.
"""
from typing import List
from langchain.embeddings import HuggingFaceEmbeddings
from app.config.config_loader import get_config

class MultilingualEmbeddingGenerator:
    """Service for generating multilingual text embeddings."""
    
    def __init__(self):
        """
        Initialize multilingual embedding generator using HuggingFace models.
        """
        config = get_config()
        # Use multilingual model instead of default
        model_name = config["langchain"].get(
            "multilingual_embedding_model", 
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # Initialize HuggingFace embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
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
