"""Tests for OncoRAD models."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oncorad.models import (
    PatientData, TumorStaging, TumorType, TStage, NStage, MStage,
    ECOGStatus, ProstateSpecificData, BreastSpecificData, RiskLevel
)


class TestTumorStaging:
    """Tests for TumorStaging model."""

    def test_tnm_string(self):
        staging = TumorStaging(
            t_stage=TStage.T3A,
            n_stage=NStage.N0,
            m_stage=MStage.M0
        )
        assert staging.tnm_string == "T3a N0 M0"

    def test_staging_with_clinical_stage(self):
        staging = TumorStaging(
            t_stage=TStage.T2,
            n_stage=NStage.N1,
            m_stage=MStage.M0,
            clinical_stage="IIIA"
        )
        assert staging.clinical_stage == "IIIA"


class TestProstateSpecificData:
    """Tests for prostate-specific data."""

    def test_gleason_score(self):
        data = ProstateSpecificData(
            psa=15.0,
            gleason_primary=4,
            gleason_secondary=3
        )
        assert data.gleason_score == 7

    def test_isup_grade_group_1(self):
        data = ProstateSpecificData(psa=5.0, gleason_primary=3, gleason_secondary=3)
        assert data.isup_grade == 1

    def test_isup_grade_group_2(self):
        data = ProstateSpecificData(psa=10.0, gleason_primary=3, gleason_secondary=4)
        assert data.isup_grade == 2

    def test_isup_grade_group_3(self):
        data = ProstateSpecificData(psa=10.0, gleason_primary=4, gleason_secondary=3)
        assert data.isup_grade == 3

    def test_isup_grade_group_4(self):
        data = ProstateSpecificData(psa=20.0, gleason_primary=4, gleason_secondary=4)
        assert data.isup_grade == 4

    def test_isup_grade_group_5(self):
        data = ProstateSpecificData(psa=25.0, gleason_primary=5, gleason_secondary=4)
        assert data.isup_grade == 5


class TestBreastSpecificData:
    """Tests for breast-specific data."""

    def test_luminal_a(self):
        data = BreastSpecificData(
            er_status=True,
            pr_status=True,
            her2_status=False,
            ki67_percent=10.0
        )
        assert data.molecular_subtype == "Luminal A"

    def test_luminal_b_her2_negative(self):
        data = BreastSpecificData(
            er_status=True,
            pr_status=True,
            her2_status=False,
            ki67_percent=30.0
        )
        assert data.molecular_subtype == "Luminal B HER2-"

    def test_luminal_b_her2_positive(self):
        data = BreastSpecificData(
            er_status=True,
            pr_status=False,
            her2_status=True
        )
        assert data.molecular_subtype == "Luminal B HER2+"

    def test_her2_enriched(self):
        data = BreastSpecificData(
            er_status=False,
            pr_status=False,
            her2_status=True
        )
        assert data.molecular_subtype == "HER2 enriched"

    def test_triple_negative(self):
        data = BreastSpecificData(
            er_status=False,
            pr_status=False,
            her2_status=False
        )
        assert data.molecular_subtype == "Triple Negative"


class TestPatientData:
    """Tests for complete patient data model."""

    def test_minimal_patient_data(self):
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
            ecog_status=ECOGStatus.FULLY_ACTIVE
        )
        assert patient.age == 65
        assert patient.tumor_type == TumorType.PROSTATE

    def test_complete_prostate_patient(self):
        patient = PatientData(
            age=70,
            sex="M",
            tumor_type=TumorType.PROSTATE,
            histology="Adenocarcinoma acinar",
            staging=TumorStaging(
                t_stage=TStage.T3A,
                n_stage=NStage.N0,
                m_stage=MStage.M0,
                clinical_stage="IIIA"
            ),
            ecog_status=ECOGStatus.RESTRICTED_STRENUOUS,
            prostate_data=ProstateSpecificData(
                psa=15.0,
                gleason_primary=4,
                gleason_secondary=3,
                percent_positive_cores=50.0
            ),
            comorbidities=["Hipertensión", "Diabetes"],
            clinical_question="¿Cuál es el fraccionamiento recomendado?"
        )
        assert patient.prostate_data is not None
        assert patient.prostate_data.gleason_score == 7

    def test_invalid_sex_raises_error(self):
        with pytest.raises(ValueError):
            PatientData(
                age=65,
                sex="X",  # Invalid
                tumor_type=TumorType.PROSTATE,
                histology="Adenocarcinoma",
                staging=TumorStaging(
                    t_stage=TStage.T2,
                    n_stage=NStage.N0,
                    m_stage=MStage.M0
                ),
                ecog_status=ECOGStatus.FULLY_ACTIVE
            )

    def test_age_bounds(self):
        with pytest.raises(ValueError):
            PatientData(
                age=150,  # Invalid
                sex="M",
                tumor_type=TumorType.PROSTATE,
                histology="Adenocarcinoma",
                staging=TumorStaging(
                    t_stage=TStage.T2,
                    n_stage=NStage.N0,
                    m_stage=MStage.M0
                ),
                ecog_status=ECOGStatus.FULLY_ACTIVE
            )


class TestEnums:
    """Tests for enumeration values."""

    def test_tumor_types(self):
        assert TumorType.PROSTATE.value == "prostata"
        assert TumorType.BREAST.value == "mama"
        assert TumorType.LUNG.value == "pulmon"

    def test_risk_levels(self):
        assert RiskLevel.LOW.value == "bajo"
        assert RiskLevel.HIGH.value == "alto"
        assert RiskLevel.METASTATIC.value == "metastasico"

    def test_ecog_status(self):
        assert ECOGStatus.FULLY_ACTIVE.value == 0
        assert ECOGStatus.COMPLETELY_DISABLED.value == 4
