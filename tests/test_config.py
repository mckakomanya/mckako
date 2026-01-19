"""Tests para el módulo de configuración."""

import pytest
from pathlib import Path


def test_settings_defaults():
    """Verifica que la configuración tenga valores por defecto correctos."""
    from oncorad_rag.config import Settings

    settings = Settings()

    assert settings.llm_model == "gpt-4o"
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.chunk_size == 1024
    assert settings.chunk_overlap == 200
    assert settings.similarity_top_k == 5


def test_supported_cancer_types():
    """Verifica que los tipos de cáncer soportados estén definidos."""
    from oncorad_rag.config import SUPPORTED_CANCER_TYPES

    assert "prostate" in SUPPORTED_CANCER_TYPES
    assert "breast" in SUPPORTED_CANCER_TYPES
    assert "lung" in SUPPORTED_CANCER_TYPES
    assert len(SUPPORTED_CANCER_TYPES) > 0


def test_required_metadata_fields():
    """Verifica que los campos de metadatos requeridos estén definidos."""
    from oncorad_rag.config import REQUIRED_METADATA_FIELDS

    assert "source_file" in REQUIRED_METADATA_FIELDS
    assert "page_number" in REQUIRED_METADATA_FIELDS
    assert "guideline_version" in REQUIRED_METADATA_FIELDS
    assert "cancer_type" in REQUIRED_METADATA_FIELDS
