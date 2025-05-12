"""
Tests for TranslationService.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
import asyncio

from app.domain.services.translation_service import TranslationService, TranslationCache

class TestTranslationCache:
    """Test cases for TranslationCache."""
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        cache = TranslationCache(max_size=10)
        
        # Set a translation in cache
        cache.set("Hello world", "en", "ru", "Привет мир")
        
        # Get from cache
        result = cache.get("Hello world", "en", "ru")
        assert result == "Привет мир"
        
        # Check cache stats
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        
        # Try with non-existent entry
        result = cache.get("Goodbye", "en", "ru")
        assert result is None
        
        # Check updated stats
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
    
    def test_cache_size_limit(self):
        """Test cache size limiting."""
        cache = TranslationCache(max_size=3)
        
        # Add multiple entries
        cache.set("One", "en", "ru", "Один")
        cache.set("Two", "en", "ru", "Два")
        cache.set("Three", "en", "ru", "Три")
        cache.set("Four", "en", "ru", "Четыре")
        cache.set("Five", "en", "ru", "Пять")
        
        # Check cache size is limited
        assert len(cache.cache) <= 3
        
        # Check at least recent entries are still available
        assert cache.get("Four", "en", "ru") == "Четыре"
        assert cache.get("Five", "en", "ru") == "Пять"
        
        # Earlier entries should be evicted
        assert cache.get("One", "en", "ru") is None

class TestTranslationService:
    """Test cases for TranslationService."""
    
    @pytest.fixture
    def mock_models(self):
        """Mock transformers models."""
        with patch("app.domain.services.translation_service.MarianMTModel") as model_mock, \
             patch("app.domain.services.translation_service.MarianTokenizer") as tokenizer_mock:
            
            # Setup model mock
            model_instance = MagicMock()
            model_instance.generate.return_value = [[42, 43, 44, 45]]  # Fake token IDs
            model_mock.from_pretrained.return_value = model_instance
            
            # Setup tokenizer mock
            tokenizer_instance = MagicMock()
            tokenizer_instance.return_value = {"input_ids": [[1, 2, 3]]}
            tokenizer_instance.decode.return_value = "Translated text"
            tokenizer_mock.from_pretrained.return_value = tokenizer_instance
            
            yield model_mock, tokenizer_mock
    
    def test_translate_with_cache(self, mock_models):
        """Test translation with caching."""
        service = TranslationService(cache_size=10)
        service.enabled = True
        
        # First translation should use model
        result = service.translate("Hello world", "en", "ru")
        assert result == "Translated text"
        
        # Make sure model was called
        model_mock, _ = mock_models
        model_instance = model_mock.from_pretrained.return_value
        model_instance.generate.assert_called_once()
        
        # Reset mock
        model_instance.generate.reset_mock()
        
        # Second translation of same text should use cache
        result = service.translate("Hello world", "en", "ru")
        assert result == "Translated text"
        
        # Model should not have been called again
        model_instance.generate.assert_not_called()
    
    def test_translate_same_language(self, mock_models):
        """Test translation when source and target languages are the same."""
        service = TranslationService(cache_size=10)
        service.enabled = True
        
        # Translation to same language should return original text
        result = service.translate("Hello world", "en", "en")
        assert result == "Hello world"
        
        # Make sure model was not called
        model_mock, _ = mock_models
        model_instance = model_mock.from_pretrained.return_value
        model_instance.generate.assert_not_called()
    
    def test_translate_disabled(self, mock_models):
        """Test translation when service is disabled."""
        service = TranslationService(cache_size=10)
        service.enabled = False
        
        # Translation when disabled should return original text
        result = service.translate("Hello world", "en", "ru")
        assert result == "Hello world"
        
        # Make sure model was not called
        model_mock, _ = mock_models
        model_instance = model_mock.from_pretrained.return_value
        model_instance.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_translate_async(self, mock_models):
        """Test asynchronous translation."""
        service = TranslationService(cache_size=10)
        service.enabled = True
        
        # Async translation
        result = await service.translate_async("Hello world", "en", "ru")
        assert result == "Translated text"
        
        # Make sure model was called
        model_mock, _ = mock_models
        model_instance = model_mock.from_pretrained.return_value
        model_instance.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_translate_batch_async(self, mock_models):
        """Test batch asynchronous translation."""
        service = TranslationService(cache_size=10)
        service.enabled = True
        
        # Batch async translation
        texts = ["Hello world", "Goodbye world"]
        results = await service.translate_batch_async(texts, "en", "ru")
        
        # Check results
        assert len(results) == 2
        assert results[0] == "Translated text"
        assert results[1] == "Translated text"
        
        # Check model was called for each text
        model_mock, _ = mock_models
        model_instance = model_mock.from_pretrained.return_value
        assert model_instance.generate.call_count == 2
    
    def test_long_text_translation(self, mock_models):
        """Test translation of long text."""
        service = TranslationService(cache_size=10)
        service.enabled = True
        
        # Create long text (over the 512 token limit)
        long_text = "Word " * 1000
        
        # Translate long text
        result = service._translate_long_text(long_text, mock_models[0].from_pretrained.return_value, mock_models[1].from_pretrained.return_value)
        
        # Result should have multiple translated parts joined
        assert result == "Translated text Translated text"  # Assuming at least 2 chunks
        
        # Model should have been called multiple times
        model_mock, _ = mock_models
        model_instance = model_mock.from_pretrained.return_value
        assert model_instance.generate.call_count > 1
