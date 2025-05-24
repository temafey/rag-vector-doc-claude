"""
Service for generating responses based on retrieved context.
"""
from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.config.config_loader import get_config

class ResponseGenerator:
    """Service for generating responses based on context."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize response generator.
        
        Args:
            api_key: OpenAI API key (if not specified, uses environment variable OPENAI_API_KEY)
        """
        config = get_config()
        self.llm = ChatOpenAI(
            temperature=config["langchain"].get("temperature", 0),
            openai_api_key=api_key,
            model_name=config["langchain"].get("llm_model", "gpt-3.5-turbo")
        )
        
        # Templates for different languages
        self.prompt_templates = {
            'en': PromptTemplate(
                input_variables=["question", "context"],
                template="""Answer the question using the context below:

Context:
{context}

Question: {question}

Answer:"""
            ),
            'ru': PromptTemplate(
                input_variables=["question", "context"],
                template="""Ответь на вопрос, используя контекст ниже:

Контекст:
{context}

Вопрос: {question}

Ответ:"""
            )
        }
        
        # LLM chains for each language
        self.chains = {}
        for lang, template in self.prompt_templates.items():
            self.chains[lang] = template | self.llm
    
    def generate(self, query: str, context: List[str], language: str = "en") -> str:
        """
        Generate response to query based on context.
        
        Args:
            query: User query
            context: List of text fragments used as context
            language: Response language
            
        Returns:
            Generated response
        """
        # Combine context fragments
        context_text = "\n\n".join(context)
        
        # Use specified language or default to English
        if language not in self.chains:
            language = 'en'
        
        # Generate response
        response = self.chains[language].run(question=query, context=context_text)
        
        return response.strip()
    
    def add_language_template(self, language_code: str, template: str) -> None:
        """
        Add template for new language.
        
        Args:
            language_code: Language code
            template: Template string
        """
        self.prompt_templates[language_code] = PromptTemplate(
            input_variables=["question", "context"],
            template=template
        )
        
        self.chains[language_code] = self.prompt_templates[language_code] | self.llm
