"""Tests for OncoRAD prompt generator."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oncorad.models import (
    PatientData, TumorStaging, TumorType, TStage, NStage, MStage,
    ECOGStatus, ProstateSpecificData, RiskLevel
)
from oncorad.prompt_generator import ClinicalPromptGenerator


@pytest.fixture
def generator():
    return ClinicalPromptGenerator(language="es")


@pytest.fixture
def prostate_patient_high_risk():
    return PatientData(
        age=65,
        sex="M",
        tumor_type=TumorType.PROSTATE,
        histology="Adenocarcinoma",
        staging=TumorStaging(
            t_stage=TStage.T3A,
            n_stage=NStage.N0,
            m_stage=MStage.M0
        ),
        ecog_status=ECOGStatus.FULLY_ACTIVE,
        prostate_data=ProstateSpecificData(
            psa=25.0,
            gleason_primary=4,
            gleason_secondary=4
        )
    )


@pytest.fixture
def prostate_patient_low_risk():
    return PatientData(
        age=60,
        sex="M",
        tumor_type=TumorType.PROSTATE,
        histology="Adenocarcinoma",
        staging=TumorStaging(
            t_stage=TStage.T1C,
            n_stage=NStage.N0,
            m_stage=MStage.M0
        ),
        ecog_status=ECOGStatus.FULLY_ACTIVE,
        prostate_data=ProstateSpecificData(
            psa=6.0,
            gleason_primary=3,
            gleason_secondary=3
        )
    )


class TestRiskClassification:
    """Tests for risk classification logic."""

    def test_prostate_high_risk_by_psa(self, generator, prostate_patient_high_risk):
        risk = generator.classify_prostate_risk(prostate_patient_high_risk)
        assert risk == RiskLevel.HIGH

    def test_prostate_low_risk(self, generator, prostate_patient_low_risk):
        risk = generator.classify_prostate_risk(prostate_patient_low_risk)
        assert risk == RiskLevel.LOW

    def test_prostate_very_high_risk_by_t_stage(self, generator):
        patient = PatientData(
            age=70,
            sex="M",
            tumor_type=TumorType.PROSTATE,
            histology="Adenocarcinoma",
            staging=TumorStaging(
                t_stage=TStage.T3B,
                n_stage=NStage.N0,
                m_stage=MStage.M0
            ),
            ecog_status=ECOGStatus.FULLY_ACTIVE,
            prostate_data=ProstateSpecificData(
                psa=10.0,
                gleason_primary=3,
                gleason_secondary=4
            )
        )
        risk = generator.classify_prostate_risk(patient)
        assert risk == RiskLevel.VERY_HIGH

    def test_metastatic_disease(self, generator):
        patient = PatientData(
            age=70,
            sex="M",
            tumor_type=TumorType.PROSTATE,
            histology="Adenocarcinoma",
            staging=TumorStaging(
                t_stage=TStage.T2,
                n_stage=NStage.N0,
                m_stage=MStage.M1
            ),
            ecog_status=ECOGStatus.FULLY_ACTIVE,
            prostate_data=ProstateSpecificData(
                psa=50.0,
                gleason_primary=4,
                gleason_secondary=4
            )
        )
        risk = generator.classify_prostate_risk(patient)
        assert risk == RiskLevel.METASTATIC


class TestClinicalSummary:
    """Tests for clinical summary generation."""

    def test_prostate_summary(self, generator, prostate_patient_high_risk):
        summary = generator.generate_clinical_summary(prostate_patient_high_risk)

        assert "65 años" in summary
        assert "masculino" in summary
        assert "Próstata" in summary or "prostata" in summary.lower()
        assert "PSA" in summary
        assert "Gleason" in summary
        assert "ECOG" in summary

    def test_summary_includes_tnm(self, generator, prostate_patient_high_risk):
        summary = generator.generate_clinical_summary(prostate_patient_high_risk)
        assert "T3a" in summary
        assert "N0" in summary
        assert "M0" in summary


class TestSearchQueries:
    """Tests for search query generation."""

    def test_generates_multiple_queries(self, generator, prostate_patient_high_risk):
        queries = generator.generate_search_queries(
            prostate_patient_high_risk,
            RiskLevel.HIGH
        )

        assert len(queries) >= 4
        assert any("tratamiento" in q.lower() for q in queries)
        assert any("sobrevida" in q.lower() or "outcomes" in q.lower() for q in queries)

    def test_includes_tumor_specific_queries(self, generator, prostate_patient_high_risk):
        queries = generator.generate_search_queries(
            prostate_patient_high_risk,
            RiskLevel.HIGH
        )

        # Should include prostate-specific queries
        assert any("próstata" in q.lower() or "prostata" in q.lower() for q in queries)
        assert any("psa" in q.lower() or "gleason" in q.lower() for q in queries)


class TestRAGPrompt:
    """Tests for RAG prompt generation."""

    def test_rag_prompt_structure(self, generator, prostate_patient_high_risk):
        prompt = generator.generate_rag_prompt(
            prostate_patient_high_risk,
            RiskLevel.HIGH,
            "Fragmento de evidencia de prueba..."
        )

        # Check key sections
        assert "CASO CLÍNICO" in prompt
        assert "CLASIFICACIÓN DE RIESGO" in prompt
        assert "EVIDENCIA DISPONIBLE" in prompt
        assert "INSTRUCCIONES" in prompt
        assert "[Fuente:" in prompt  # Citation format requirement

    def test_includes_custom_question(self, generator):
        patient = PatientData(
            age=65,
            sex="M",
            tumor_type=TumorType.PROSTATE,
            histology="Adenocarcinoma",
            staging=TumorStaging(
                t_stage=TStage.T2,
                n_stage=NStage.N0,
                m_stage=MStage.M0
            ),
            ecog_status=ECOGStatus.FULLY_ACTIVE,
            clinical_question="¿Es candidato a SBRT?"
        )

        prompt = generator.generate_rag_prompt(
            patient,
            RiskLevel.LOW,
            "Evidencia..."
        )

        assert "SBRT" in prompt


class TestChainOfThoughtPrompt:
    """Tests for Chain of Thought prompt generation."""

    def test_cot_includes_all_steps(self, generator, prostate_patient_high_risk):
        chunks = [
            {
                "document_name": "NCCN_Prostate.pdf",
                "page_number": 45,
                "text": "High-risk prostate cancer treatment...",
                "relevance_score": 0.85
            }
        ]

        prompt = generator.generate_chain_of_thought_prompt(
            prostate_patient_high_risk,
            RiskLevel.HIGH,
            chunks
        )

        # Check for reasoning steps
        assert "PASO 1" in prompt
        assert "PASO 2" in prompt
        assert "PASO 3" in prompt
        assert "Verificación" in prompt
        assert "Tratamiento" in prompt

    def test_cot_includes_source_info(self, generator, prostate_patient_high_risk):
        chunks = [
            {
                "document_name": "NCCN_Prostate.pdf",
                "page_number": 45,
                "text": "Treatment guidelines...",
                "relevance_score": 0.9
            }
        ]

        prompt = generator.generate_chain_of_thought_prompt(
            prostate_patient_high_risk,
            RiskLevel.HIGH,
            chunks
        )

        assert "NCCN_Prostate.pdf" in prompt
        assert "45" in prompt
