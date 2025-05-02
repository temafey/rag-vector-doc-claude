"""
Service for text translation between languages.
"""
from typing import List, Optional, Dict, Tuple
from app.config.config_loader import get_config

class TranslationService:
    """Service for translating text between languages."""
    
    def __init__(self):
        """
        Initialize translation service.
        """
        self.config = get_config()
        
        # Define translation models mapping
        self.translation_models = {
            ('ru', 'en'): 'Helsinki-NLP/opus-mt-ru-en',
            ('en', 'ru'): 'Helsinki-NLP/opus-mt-en-ru',
        }
        
        # Lazy loading of models and tokenizers
        self.models = {}
        self.tokenizers = {}
        
        # Load specified language pairs only
        self.enabled = self.config["translation"].get("enabled", True)
        if self.enabled:
            try:
                # Import required libraries
                from transformers import MarianMTModel, MarianTokenizer
                
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
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source language to target language.
        
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
        
        pair = (source_lang, target_lang)
        
        try:
            # Import required libraries
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
            
            # Handle long text by splitting into chunks
            max_length = 512
            if len(text) > max_length * 4:  # Arbitrary threshold
                chunks = [text[i:i+max_length*4] for i in range(0, len(text), max_length*4)]
                translated_chunks = []
                
                for chunk in chunks:
                    batch = tokenizer([chunk], return_tensors="pt", padding=True, truncation=True, max_length=max_length)
                    translated = model.generate(**batch)
                    translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
                    translated_chunks.append(translated_text)
                
                return " ".join(translated_chunks)
            else:
                # Translate normally
                batch = tokenizer([text], return_tensors="pt", padding=True, truncation=True, max_length=max_length)
                translated = model.generate(**batch)
                result = tokenizer.decode(translated[0], skip_special_tokens=True)
                
                return result
                
        except Exception as e:
            print(f"Translation error: {str(e)}")
            return text
    
    def get_supported_language_pairs(self) -> List[Tuple[str, str]]:
        """
        Get list of supported language pairs.
        
        Returns:
            List of tuples (source_lang, target_lang)
        """
        return list(self.translation_models.keys())
