"""
OncoRad AI - Sistema RAG para Oncología Radioterápica
=====================================================

Un sistema de Retrieval-Augmented Generation (RAG) especializado en oncología
radioterápica que proporciona recomendaciones de tratamiento basadas en guías
de práctica clínica con citas exactas y verificación de fuentes.
"""

__version__ = "0.1.0"
__author__ = "OncoRad AI Team"

from .config import Settings
from .ingest import DocumentIngester
from .query_engine import OncoRadQueryEngine

__all__ = ["Settings", "DocumentIngester", "OncoRadQueryEngine"]
