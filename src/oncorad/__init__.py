# OncoRAD Clinical Reasoning Module
from .models import (
    PatientData,
    ClinicalResponse,
    TumorStaging,
    TumorType,
    RiskLevel,
    Citation,
    ClinicalOutcome,
    ConsultationRequest,
    ConsultationResponse
)
from .query_engine import ClinicalReasoningEngine
from .prompt_generator import ClinicalPromptGenerator
from .vector_store import ClinicalVectorStore, DocumentProcessor
from .hallucination_checker import HallucinationChecker, ValidationResult
from .config import settings, get_settings

__version__ = "0.2.0"
__all__ = [
    # Models
    "PatientData",
    "ClinicalResponse",
    "TumorStaging",
    "TumorType",
    "RiskLevel",
    "Citation",
    "ClinicalOutcome",
    "ConsultationRequest",
    "ConsultationResponse",
    # Engine
    "ClinicalReasoningEngine",
    "ClinicalPromptGenerator",
    # Vector Store
    "ClinicalVectorStore",
    "DocumentProcessor",
    # Validation
    "HallucinationChecker",
    "ValidationResult",
    # Config
    "settings",
    "get_settings",
]
