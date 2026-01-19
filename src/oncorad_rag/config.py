"""
Configuración del sistema OncoRad AI RAG.

Este módulo contiene todas las configuraciones del sistema incluyendo
rutas, modelos de IA, y parámetros de procesamiento.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración principal del sistema OncoRad AI."""

    # Rutas del proyecto
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent
    )
    data_dir: Path = Field(default=None)
    chroma_db_dir: Path = Field(default=None)

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # Modelo LLM
    llm_model: str = Field(default="gpt-4o")
    llm_temperature: float = Field(default=0.1)  # Bajo para respuestas precisas

    # Modelo de Embeddings
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536)

    # Configuración de ChromaDB
    chroma_collection_name: str = Field(default="oncorad_guidelines")

    # Configuración de Chunking
    chunk_size: int = Field(default=1024)
    chunk_overlap: int = Field(default=200)

    # Configuración de Búsqueda
    similarity_top_k: int = Field(default=5)

    # System Prompt para el LLM
    system_prompt: str = Field(
        default="""Eres un experto en Oncología Radioterápica. Tu tarea es analizar el caso clínico del usuario basándote ÚNICAMENTE en el contexto proporcionado de las guías de práctica clínica.

INSTRUCCIONES OBLIGATORIAS:
1. Identifica el estadio del paciente según la clasificación TNM proporcionada.
2. Busca la recomendación de tratamiento con mayor nivel de evidencia (Survival, Local Control).
3. SIEMPRE cita el documento fuente y el número de página exacto.
4. Si la información NO está en los documentos proporcionados, di explícitamente: "No hay evidencia suficiente en la biblioteca actual para responder esta consulta."

FORMATO DE RESPUESTA:
- Estadio identificado: [estadio]
- Recomendación de tratamiento: [tratamiento]
- Nivel de evidencia: [si está disponible]
- Fuente: [nombre del documento, página X]

ADVERTENCIA: NO inventes información. NO uses conocimiento externo. Solo responde con lo que está en el contexto."""
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def model_post_init(self, __context) -> None:
        """Inicializa rutas después de crear el modelo."""
        if self.data_dir is None:
            self.data_dir = self.project_root / "data"
        if self.chroma_db_dir is None:
            self.chroma_db_dir = self.project_root / "chroma_db"

        # Crear directorios si no existen
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_db_dir.mkdir(parents=True, exist_ok=True)


# Metadatos requeridos para cada fragmento de documento
REQUIRED_METADATA_FIELDS = [
    "source_file",      # Nombre del archivo PDF fuente
    "page_number",      # Número de página
    "guideline_version", # Versión de la guía (ej: "NCCN 2024.1")
    "cancer_type",      # Tipo de cáncer (ej: "prostate", "breast", "lung")
]

# Tipos de cáncer soportados
SUPPORTED_CANCER_TYPES = [
    "prostate",
    "breast",
    "lung",
    "head_neck",
    "colorectal",
    "cervical",
    "esophageal",
    "brain",
    "lymphoma",
    "other"
]


def get_settings() -> Settings:
    """Obtiene la instancia de configuración."""
    return Settings()
