"""
API layer for RAG system.
"""
from app.api.routes import router as document_router
from app.api.agent_routes import router as agent_router

__all__ = ['document_router', 'agent_router']
