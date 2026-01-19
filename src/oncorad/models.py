"""
OncoRAD Clinical Data Models

Pydantic schemas for validating oncology patient data and clinical responses.
Designed for radiation oncology clinical decision support.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# ENUMERATIONS - Clinical Classifications
# =============================================================================

class TumorType(str, Enum):
    """Primary tumor types supported by the system."""
    PROSTATE = "prostata"
    BREAST = "mama"
    LUNG = "pulmon"
    HEAD_NECK = "cabeza_cuello"
    COLORECTAL = "colorrectal"
    CERVIX = "cervix"
    ENDOMETRIUM = "endometrio"
    BLADDER = "vejiga"
    ESOPHAGUS = "esofago"
    BRAIN = "cerebro"
    LYMPHOMA = "linfoma"
    OTHER = "otro"


class TStage(str, Enum):
    """TNM T-Stage classifications."""
    TX = "Tx"
    T0 = "T0"
    TIS = "Tis"
    T1 = "T1"
    T1A = "T1a"
    T1B = "T1b"
    T1C = "T1c"
    T2 = "T2"
    T2A = "T2a"
    T2B = "T2b"
    T2C = "T2c"
    T3 = "T3"
    T3A = "T3a"
    T3B = "T3b"
    T4 = "T4"
    T4A = "T4a"
    T4B = "T4b"


class NStage(str, Enum):
    """TNM N-Stage classifications."""
    NX = "Nx"
    N0 = "N0"
    N1 = "N1"
    N2 = "N2"
    N2A = "N2a"
    N2B = "N2b"
    N2C = "N2c"
    N3 = "N3"
    N3A = "N3a"
    N3B = "N3b"


class MStage(str, Enum):
    """TNM M-Stage classifications."""
    MX = "Mx"
    M0 = "M0"
    M1 = "M1"
    M1A = "M1a"
    M1B = "M1b"
    M1C = "M1c"


class ECOGStatus(int, Enum):
    """ECOG Performance Status Scale."""
    FULLY_ACTIVE = 0  # Fully active, no restrictions
    RESTRICTED_STRENUOUS = 1  # Restricted in strenuous activity
    AMBULATORY_SELFCARE = 2  # Ambulatory, capable of self-care
    LIMITED_SELFCARE = 3  # Limited self-care, confined >50% of waking hours
    COMPLETELY_DISABLED = 4  # Completely disabled
    DEAD = 5  # Dead


class RiskLevel(str, Enum):
    """Clinical risk stratification levels."""
    VERY_LOW = "muy_bajo"
    LOW = "bajo"
    INTERMEDIATE_FAVORABLE = "intermedio_favorable"
    INTERMEDIATE_UNFAVORABLE = "intermedio_desfavorable"
    HIGH = "alto"
    VERY_HIGH = "muy_alto"
    METASTATIC = "metastasico"


class TreatmentIntent(str, Enum):
    """Treatment intent classification."""
    CURATIVE = "curativo"
    PALLIATIVE = "paliativo"
    ADJUVANT = "adyuvante"
    NEOADJUVANT = "neoadyuvante"
    DEFINITIVE = "definitivo"


# =============================================================================
# INPUT MODELS - Patient Data
# =============================================================================

class TumorStaging(BaseModel):
    """TNM Staging information."""
    t_stage: TStage = Field(..., description="Tumor stage (T)")
    n_stage: NStage = Field(..., description="Nodal stage (N)")
    m_stage: MStage = Field(..., description="Metastasis stage (M)")
    clinical_stage: Optional[str] = Field(
        None,
        description="Overall clinical stage (e.g., IIA, IIIB)"
    )

    @property
    def tnm_string(self) -> str:
        """Return formatted TNM string."""
        return f"{self.t_stage.value} {self.n_stage.value} {self.m_stage.value}"


class ProstateSpecificData(BaseModel):
    """Prostate cancer specific parameters."""
    psa: float = Field(..., ge=0, description="PSA level (ng/mL)")
    gleason_primary: int = Field(..., ge=1, le=5, description="Primary Gleason pattern")
    gleason_secondary: int = Field(..., ge=1, le=5, description="Secondary Gleason pattern")
    percent_positive_cores: Optional[float] = Field(
        None, ge=0, le=100,
        description="Percentage of positive biopsy cores"
    )

    @property
    def gleason_score(self) -> int:
        """Calculate total Gleason score."""
        return self.gleason_primary + self.gleason_secondary

    @property
    def isup_grade(self) -> int:
        """Calculate ISUP Grade Group (1-5)."""
        gs = self.gleason_score
        if gs <= 6:
            return 1
        elif gs == 7:
            return 2 if self.gleason_primary == 3 else 3
        elif gs == 8:
            return 4
        else:
            return 5


class BreastSpecificData(BaseModel):
    """Breast cancer specific parameters."""
    er_status: bool = Field(..., description="Estrogen receptor status")
    pr_status: bool = Field(..., description="Progesterone receptor status")
    her2_status: bool = Field(..., description="HER2 status")
    ki67_percent: Optional[float] = Field(
        None, ge=0, le=100,
        description="Ki-67 proliferation index (%)"
    )
    tumor_size_mm: Optional[float] = Field(
        None, ge=0,
        description="Tumor size in millimeters"
    )

    @property
    def molecular_subtype(self) -> str:
        """Determine molecular subtype."""
        if self.her2_status:
            if self.er_status or self.pr_status:
                return "Luminal B HER2+"
            return "HER2 enriched"
        elif self.er_status or self.pr_status:
            if self.ki67_percent and self.ki67_percent > 20:
                return "Luminal B HER2-"
            return "Luminal A"
        return "Triple Negative"


class LungSpecificData(BaseModel):
    """Lung cancer specific parameters."""
    histology: str = Field(..., description="Histological type (e.g., adenocarcinoma, squamous)")
    egfr_mutation: Optional[bool] = Field(None, description="EGFR mutation status")
    alk_rearrangement: Optional[bool] = Field(None, description="ALK rearrangement status")
    pdl1_expression: Optional[float] = Field(
        None, ge=0, le=100,
        description="PD-L1 expression (%)"
    )
    fev1_percent: Optional[float] = Field(
        None, ge=0, le=150,
        description="FEV1 as percentage of predicted"
    )


class PatientData(BaseModel):
    """
    Complete patient clinical data for oncology consultation.

    This is the main input model that combines all patient information
    needed for clinical reasoning and treatment recommendation.
    """
    # Basic Information
    patient_id: Optional[str] = Field(None, description="Anonymous patient identifier")
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    sex: str = Field(..., pattern="^[MF]$", description="Patient sex (M/F)")

    # Tumor Information
    tumor_type: TumorType = Field(..., description="Primary tumor type")
    histology: str = Field(..., description="Histological diagnosis")
    staging: TumorStaging = Field(..., description="TNM staging")

    # Performance Status
    ecog_status: ECOGStatus = Field(..., description="ECOG performance status")

    # Treatment Intent
    treatment_intent: Optional[TreatmentIntent] = Field(
        None,
        description="Intended treatment approach"
    )

    # Disease-Specific Data (Optional based on tumor type)
    prostate_data: Optional[ProstateSpecificData] = Field(
        None,
        description="Prostate-specific parameters"
    )
    breast_data: Optional[BreastSpecificData] = Field(
        None,
        description="Breast-specific parameters"
    )
    lung_data: Optional[LungSpecificData] = Field(
        None,
        description="Lung-specific parameters"
    )

    # Relevant Clinical History
    comorbidities: Optional[List[str]] = Field(
        default_factory=list,
        description="Relevant comorbidities"
    )
    previous_treatments: Optional[List[str]] = Field(
        default_factory=list,
        description="Previous oncological treatments"
    )

    # Clinical Question (Optional)
    clinical_question: Optional[str] = Field(
        None,
        description="Specific clinical question to address"
    )

    @model_validator(mode='after')
    def validate_tumor_specific_data(self) -> 'PatientData':
        """Validate that tumor-specific data matches tumor type."""
        if self.tumor_type == TumorType.PROSTATE and self.prostate_data is None:
            # Allow without specific data, but recommend it
            pass
        if self.tumor_type == TumorType.BREAST and self.breast_data is None:
            pass
        if self.tumor_type == TumorType.LUNG and self.lung_data is None:
            pass
        return self


# =============================================================================
# OUTPUT MODELS - Clinical Response
# =============================================================================

class Citation(BaseModel):
    """A bibliographic citation from source documents."""
    document: str = Field(..., description="Source document name")
    page: Optional[int] = Field(None, ge=1, description="Page number")
    section: Optional[str] = Field(None, description="Document section")
    original_text: str = Field(..., description="Original quoted text")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to query")


class ClinicalOutcome(BaseModel):
    """Expected clinical outcomes based on evidence."""
    overall_survival: Optional[str] = Field(
        None,
        description="Overall survival data (e.g., '85% at 5 years')"
    )
    progression_free_survival: Optional[str] = Field(
        None,
        description="Progression-free survival data"
    )
    local_control: Optional[str] = Field(
        None,
        description="Local control rate"
    )
    disease_free_survival: Optional[str] = Field(
        None,
        description="Disease-free survival data"
    )
    toxicity_profile: Optional[str] = Field(
        None,
        description="Expected toxicity profile"
    )


class RadiotherapyRecommendation(BaseModel):
    """Specific radiotherapy treatment parameters."""
    technique: str = Field(..., description="RT technique (e.g., IMRT, VMAT, SBRT)")
    total_dose_gy: float = Field(..., ge=0, description="Total dose in Gy")
    fractions: int = Field(..., ge=1, description="Number of fractions")
    dose_per_fraction: float = Field(..., ge=0, description="Dose per fraction in Gy")
    target_volumes: List[str] = Field(
        default_factory=list,
        description="Target volumes (PTV, CTV, etc.)"
    )
    oar_constraints: Optional[Dict[str, str]] = Field(
        None,
        description="Organ at risk constraints"
    )

    @property
    def fractionation_scheme(self) -> str:
        """Return formatted fractionation scheme."""
        return f"{self.total_dose_gy} Gy / {self.fractions} fx ({self.dose_per_fraction} Gy/fx)"


class SystemicTherapyRecommendation(BaseModel):
    """Systemic therapy recommendations (if applicable)."""
    therapy_type: str = Field(..., description="Type (chemotherapy, ADT, immunotherapy)")
    regimen: str = Field(..., description="Specific regimen name")
    duration: Optional[str] = Field(None, description="Treatment duration")
    timing: str = Field(..., description="Timing relative to RT (concurrent, adjuvant, etc.)")


class ReasoningStep(BaseModel):
    """A step in the clinical reasoning chain."""
    step_number: int = Field(..., ge=1)
    step_name: str = Field(..., description="Name of reasoning step")
    analysis: str = Field(..., description="Analysis performed")
    conclusion: str = Field(..., description="Conclusion reached")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in conclusion")


class ClinicalResponse(BaseModel):
    """
    Complete clinical response with structured recommendations.

    This is the main output model returned by the clinical reasoning engine.
    """
    # Request Info
    query_id: str = Field(..., description="Unique query identifier")
    timestamp: str = Field(..., description="Response timestamp")

    # Risk Classification
    risk_classification: RiskLevel = Field(..., description="Calculated risk level")
    risk_justification: str = Field(..., description="Justification for risk classification")

    # Main Recommendation
    primary_recommendation: str = Field(
        ...,
        description="Primary treatment recommendation"
    )
    recommendation_summary: str = Field(
        ...,
        description="Brief summary of recommendation"
    )

    # Detailed Treatment Plan
    radiotherapy: Optional[RadiotherapyRecommendation] = Field(
        None,
        description="Radiotherapy specifications"
    )
    systemic_therapy: Optional[List[SystemicTherapyRecommendation]] = Field(
        None,
        description="Systemic therapy recommendations"
    )

    # Clinical Reasoning
    reasoning_chain: List[ReasoningStep] = Field(
        ...,
        description="Chain of thought reasoning steps"
    )

    # Outcomes
    expected_outcomes: ClinicalOutcome = Field(
        ...,
        description="Expected clinical outcomes"
    )

    # Evidence & Citations
    citations: List[Citation] = Field(
        ...,
        description="Supporting citations from source documents"
    )

    # Quality Metrics
    confidence_score: float = Field(
        ..., ge=0, le=1,
        description="Overall confidence in recommendation"
    )
    evidence_level: str = Field(
        ...,
        description="Level of evidence (e.g., 'Level I', 'Level IIA')"
    )
    hallucination_check_passed: bool = Field(
        ...,
        description="Whether response passed hallucination validation"
    )

    # Warnings & Caveats
    warnings: Optional[List[str]] = Field(
        default_factory=list,
        description="Clinical warnings or caveats"
    )
    alternative_options: Optional[List[str]] = Field(
        default_factory=list,
        description="Alternative treatment approaches"
    )


class SourceDocument(BaseModel):
    """Information about a loaded source document."""
    filename: str
    document_type: str  # "guideline", "study", "textbook"
    pages: int
    indexed_chunks: int
    last_updated: str


class SystemStatus(BaseModel):
    """System status information."""
    status: str
    total_documents: int
    total_chunks: int
    vector_db_status: str
    last_index_update: str
    supported_tumor_types: List[str]


# =============================================================================
# API Request/Response Models
# =============================================================================

class ConsultationRequest(BaseModel):
    """API request for clinical consultation."""
    patient_data: PatientData
    include_reasoning: bool = Field(
        default=True,
        description="Include detailed reasoning chain"
    )
    max_citations: int = Field(
        default=5, ge=1, le=20,
        description="Maximum number of citations to include"
    )
    language: str = Field(
        default="es",
        description="Response language (es, en)"
    )


class ConsultationResponse(BaseModel):
    """API response wrapper for clinical consultation."""
    success: bool
    data: Optional[ClinicalResponse] = None
    error: Optional[str] = None
    processing_time_ms: float
