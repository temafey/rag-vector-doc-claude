"""
Service for language detection.
"""
from typing import Dict, Tuple, List
import langdetect
from langdetect.lang_detect_exception import LangDetectException

class LanguageDetector:
    """Service for detecting text language."""
    
    def __init__(self):
        # Set seed for consistent results
        langdetect.DetectorFactory.seed = 0
    
    def detect(self, text: str) -> Tuple[str, float]:
        """
        Detect text language.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or not text.strip():
            return 'en', 0.0
            
        try:
            # Get top result
            lang = langdetect.detect(text)
            # Since langdetect doesn't provide confidence scores directly, 
            # we'll use a placeholder value
            confidence = 0.8
            return lang, confidence
        except LangDetectException:
            # Default to English on error
            return 'en', 0.5
    
    def detect_language_parts(self, text: str) -> Dict[str, float]:
        """
        Detect proportion of different languages in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of language codes and their probabilities
        """
        if not text or not text.strip():
            return {'en': 1.0}
            
        try:
            # Get probabilities for all detected languages
            lang_probs = langdetect.detect_langs(text)
            return {lang.lang: lang.prob for lang in lang_probs}
        except LangDetectException:
            # Default to English on error
            return {'en': 1.0}
    
    def is_supported_language(self, language_code: str, supported_languages: List[str]) -> bool:
        """
        Check if language is in the list of supported languages.
        
        Args:
            language_code: Language code to check
            supported_languages: List of supported language codes
            
        Returns:
            True if language is supported, False otherwise
        """
        return language_code in supported_languages
