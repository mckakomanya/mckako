"""Tests para el motor de consultas."""

import pytest


def test_clinical_case_creation():
    """Verifica la creación de un caso clínico."""
    from oncorad_rag.query_engine import ClinicalCase

    case = ClinicalCase(
        histologia="Adenocarcinoma de próstata",
        tnm="T2bN0M0",
        psa=15.5,
        gleason="4+3=7",
        age=68,
    )

    assert case.histologia == "Adenocarcinoma de próstata"
    assert case.tnm == "T2bN0M0"
    assert case.psa == 15.5
    assert case.gleason == "4+3=7"
    assert case.age == 68


def test_clinical_case_to_query():
    """Verifica la conversión de caso clínico a query."""
    from oncorad_rag.query_engine import ClinicalCase

    case = ClinicalCase(
        histologia="Adenocarcinoma",
        tnm="T1N0M0",
    )

    query = case.to_query()

    assert "Adenocarcinoma" in query
    assert "T1N0M0" in query
    assert "radioterápica" in query.lower() or "tratamiento" in query.lower()


def test_source_node_creation():
    """Verifica la creación de un nodo fuente."""
    from oncorad_rag.query_engine import SourceNode

    node = SourceNode(
        text="Texto de ejemplo",
        source_file="guia_nccn.pdf",
        page_number=42,
        guideline_version="2024.1",
        cancer_type="prostate",
        similarity_score=0.85,
    )

    assert node.source_file == "guia_nccn.pdf"
    assert node.page_number == 42
    assert node.similarity_score == 0.85


def test_query_response_to_dict():
    """Verifica la serialización de QueryResponse."""
    from oncorad_rag.query_engine import ClinicalCase, QueryResponse, SourceNode

    case = ClinicalCase(histologia="Test")
    node = SourceNode(
        text="Texto",
        source_file="test.pdf",
        page_number=1,
        guideline_version="1.0",
        cancer_type="prostate",
        similarity_score=0.9,
    )

    response = QueryResponse(
        response="Respuesta de prueba",
        source_nodes=[node],
        clinical_case=case,
        is_validated=True,
    )

    data = response.to_dict()

    assert data["response"] == "Respuesta de prueba"
    assert len(data["source_nodes"]) == 1
    assert data["is_validated"] is True
