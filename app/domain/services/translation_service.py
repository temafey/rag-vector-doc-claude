"""
Service for text translation between languages with caching and async support.
"""
from typing import List, Optional, Dict, Tuple, Callable, Any
from functools import lru_cache
import hashlib
import asyncio
import concurrent.futures
import time
from app.config.config_loader import get_config

class TranslationCache:
    """Cache for translated text to avoid repeated translations."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize translation cache.
        
        Args:
            max_size: Maximum number of entries in cache
        """
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        
    def get_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key from text and language pair."""
        # Use hash for long texts to keep keys manageable
        if len(text) > 100:
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            return f"{text_hash}_{source_lang}_{target_lang}"
        else:
            return f"{text}_{source_lang}_{target_lang}"
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation if available."""
        key = self.get_key(text, source_lang, target_lang)
        
        if key in self.cache:
            translation, timestamp = self.cache[key]
            self.hits += 1
            return translation
            
        self.misses += 1
        return None
    
    def set(self, text: str, source_lang: str, target_lang: str, translation: str) -> None:
        """Set translation in cache."""
        key = self.get_key(text, source_lang, target_lang)
        
        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            # Sort by timestamp and remove oldest 10%
            sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])
            for old_key in sorted_keys[:max(1, self.max_size // 10)]:
                del self.cache[old_key]
        
        self.cache[key] = (translation, time.time())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

class TranslationService:
    """Service for translating text between languages with caching and async support."""
    
    def __init__(self, cache_size: int = 1000):
        """
        Initialize translation service.
        
        Args:
            cache_size: Size of translation cache
        """
        self.config = get_config()
        
        # Define translation models mapping with more language pairs
        self.translation_models = {
            ('ru', 'en'): 'Helsinki-NLP/opus-mt-ru-en',
            ('en', 'ru'): 'Helsinki-NLP/opus-mt-en-ru',
            ('fr', 'en'): 'Helsinki-NLP/opus-mt-fr-en',
            ('en', 'fr'): 'Helsinki-NLP/opus-mt-en-fr',
            ('de', 'en'): 'Helsinki-NLP/opus-mt-de-en',
            ('en', 'de'): 'Helsinki-NLP/opus-mt-en-de',
            ('es', 'en'): 'Helsinki-NLP/opus-mt-es-en',
            ('en', 'es'): 'Helsinki-NLP/opus-mt-en-es',
            ('zh', 'en'): 'Helsinki-NLP/opus-mt-zh-en',
            ('en', 'zh'): 'Helsinki-NLP/opus-mt-en-zh',
            # Add more language pairs as needed
        }
        
        # Setup better model for multilingual translation
        self.multilingual_model = 'facebook/m2m100_418M'
        
        # Lazy loading of models and tokenizers
        self.models = {}
        self.tokenizers = {}
        
        # Create translation cache
        self.cache = TranslationCache(max_size=cache_size)
        
        # Load specified language pairs only
        self.enabled = self.config["translation"].get("enabled", True)
        if self.enabled:
            try:
                # Import required libraries
                from transformers import MarianMTModel, MarianTokenizer, M2M100ForConditionalGeneration, M2M100Tokenizer
                
                # Load multilingual model if configured
                if self.config["translation"].get("use_multilingual_model", False):
                    print(f"Loading multilingual translation model: {self.multilingual_model}")
                    self.multilingual_model_instance = M2M100ForConditionalGeneration.from_pretrained(self.multilingual_model)
                    self.multilingual_tokenizer = M2M100Tokenizer.from_pretrained(self.multilingual_model)
                
                # Preload models if configured
                if self.config["translation"].get("preload_models", False):
                    enabled_pairs = self.config["translation"].get(
                        "enabled_pairs", 
                        [('ru', 'en'), ('en', 'ru')]
                    )
                    
                    for src_lang, tgt_lang in enabled_pairs:
                        pair = (src_lang, tgt_lang)
                        if pair in self.translation_models:
                            model_name = self.translation_models[pair]
                            print(f"Loading translation model: {model_name}")
                            
                            self.models[pair] = MarianMTModel.from_pretrained(model_name)
                            self.tokenizers[pair] = MarianTokenizer.from_pretrained(model_name)
            except ImportError:
                print("Warning: transformers package not found. Translation service disabled.")
                self.enabled = False
        
        # Initialize thread pool for parallel translation
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source language to target language with caching.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        # Return original text if translation disabled or languages are the same
        if not self.enabled or source_lang == target_lang:
            return text
        
        # Check cache first
        cached_translation = self.cache.get(text, source_lang, target_lang)
        if cached_translation:
            return cached_translation
        
        # Translate and cache result
        translation = self._translate_impl(text, source_lang, target_lang)
        self.cache.set(text, source_lang, target_lang, translation)
        
        return translation
    
    def _translate_impl(self, text: str, source_lang: str, target_lang: str) -> str:
        """Internal implementation of translation logic."""
        pair = (source_lang, target_lang)
        
        try:
            # First try multilingual model if available
            if hasattr(self, 'multilingual_model_instance') and hasattr(self, 'multilingual_tokenizer'):
                return self._translate_with_multilingual(text, source_lang, target_lang)
            
            # Fallback to specialized models
            from transformers import MarianMTModel, MarianTokenizer
            import torch
            
            # Load model if not already loaded
            if pair not in self.models:
                if pair in self.translation_models:
                    model_name = self.translation_models[pair]
                    
                    self.models[pair] = MarianMTModel.from_pretrained(model_name)
                    self.tokenizers[pair] = MarianTokenizer.from_pretrained(model_name)
                else:
                    print(f"Warning: No translation model for {source_lang} to {target_lang}")
                    return text
            
            model = self.models[pair]
            tokenizer = self.tokenizers[pair]
            
            # Handle long text by splitting into sentences for better context preservation
            if len(text) > 1000:
                return self._translate_long_text(text, model, tokenizer)
            else:
                # Translate normally
                batch = tokenizer([text], return_tensors="pt", padding=True, truncation=True, max_length=512)
                translated = model.generate(**batch)
                result = tokenizer.decode(translated[0], skip_special_tokens=True)
                
                return result
                
        except Exception as e:
            print(f"Translation error: {str(e)}")
            return text
    
    def _translate_with_multilingual(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using multilingual M2M100 model."""
        try:
            self.multilingual_tokenizer.src_lang = source_lang
            encoded = self.multilingual_tokenizer(text, return_tensors="pt")
            generated_tokens = self.multilingual_model_instance.generate(
                **encoded, 
                forced_bos_token_id=self.multilingual_tokenizer.get_lang_id(target_lang)
            )
            return self.multilingual_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        except Exception as e:
            print(f"Multilingual translation error: {str(e)}")
            # Fallback to specialized models
            return self._translate_impl(text, source_lang, target_lang)
    
    def _translate_long_text(self, text: str, model, tokenizer) -> str:
        """Translate long text by splitting into sentences and preserving structure."""
        import re
        
        # Split text into sentences
        sentence_endings = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_endings, text)
        
        # Group sentences into manageable chunks (keep paragraphs together when possible)
        max_length = 512
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            if sentence_len > max_length:
                # Very long sentence, split it
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split the long sentence into parts
                for i in range(0, sentence_len, max_length - 50):  # leave room for overlap
                    chunks.append(sentence[i:i + max_length])
                
            elif current_length + sentence_len > max_length:
                # Current chunk is full, start a new one
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_len
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_length += sentence_len
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # Translate each chunk
        translated_chunks = []
        for chunk in chunks:
            batch = tokenizer([chunk], return_tensors="pt", padding=True, truncation=True, max_length=max_length)
            translated = model.generate(**batch)
            translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
            translated_chunks.append(translated_text)
        
        # Join the translated chunks
        return ' '.join(translated_chunks)
    
    async def translate_async(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text asynchronously.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        # Return original text if translation disabled or languages are the same
        if not self.enabled or source_lang == target_lang:
            return text
        
        # Check cache first
        cached_translation = self.cache.get(text, source_lang, target_lang)
        if cached_translation:
            return cached_translation
        
        # Translate in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        translation = await loop.run_in_executor(
            self.executor,
            lambda: self._translate_impl(text, source_lang, target_lang)
        )
        
        # Cache result
        self.cache.set(text, source_lang, target_lang, translation)
        
        return translation
    
    async def translate_batch_async(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        """
        Translate multiple texts asynchronously.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of translated texts
        """
        # Return original texts if translation disabled or languages are the same
        if not self.enabled or source_lang == target_lang:
            return texts
        
        # Create tasks for each text
        tasks = [
            self.translate_async(text, source_lang, target_lang)
            for text in texts
        ]
        
        # Wait for all translations to complete
        return await asyncio.gather(*tasks)
    
    def get_supported_language_pairs(self) -> List[Tuple[str, str]]:
        """
        Get list of supported language pairs.
        
        Returns:
            List of tuples (source_lang, target_lang)
        """
        return list(self.translation_models.keys())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the translation cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache.get_stats()
    
    def clear_cache(self) -> None:
        """Clear the translation cache."""
        self.cache.clear()
