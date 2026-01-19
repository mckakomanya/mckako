"""
OncoRAD Clinical Reasoning Engine

The core engine that processes patient data through a chain of thought
reasoning process to generate evidence-based treatment recommendations.
"""

import os
import json
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from .models import (
    PatientData, ClinicalResponse, Citation, ClinicalOutcome,
    RadiotherapyRecommendation, SystemicTherapyRecommendation,
    ReasoningStep, RiskLevel
)
from .vector_store import ClinicalVectorStore
from .prompt_generator import ClinicalPromptGenerator
from .hallucination_checker import HallucinationChecker, ResponseSanitizer


class LLMClient:
    """
    Abstract LLM client interface supporting multiple providers.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.api_key = api_key or self._get_api_key()

        # Default models per provider
        default_models = {
            "anthropic": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4-turbo-preview"
        }
        self.model = model or default_models.get(provider, "claude-3-5-sonnet-20241022")
        self._client = None

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif self.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        return None

    @property
    def client(self):
        """Lazy load the client."""
        if self._client is None:
            if self.provider == "anthropic":
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=self.api_key)
                except ImportError:
                    raise ImportError("anthropic package required: pip install anthropic")
            elif self.provider == "openai":
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=self.api_key)
                except ImportError:
                    raise ImportError("openai package required: pip install openai")
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        if self.provider == "anthropic":
            messages = [{"role": "user", "content": prompt}]
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "Eres un oncólogo radioterapeuta experto.",
                messages=messages
            )
            return response.content[0].text

        elif self.provider == "openai":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content

        raise ValueError(f"Unsupported provider: {self.provider}")


class ClinicalReasoningEngine:
    """
    Main clinical reasoning engine using RAG with Chain of Thought.

    This engine:
    1. Classifies patient risk based on clinical parameters
    2. Retrieves relevant evidence from the vector store
    3. Generates structured recommendations using CoT prompting
    4. Validates responses against source documents
    5. Returns structured JSON responses with citations
    """

    SYSTEM_PROMPT = """Eres un oncólogo radioterapeuta con 20 años de experiencia clínica.
Tu rol es proporcionar recomendaciones terapéuticas basadas ÚNICAMENTE en la evidencia proporcionada.

REGLAS FUNDAMENTALES:
1. NUNCA inventes estudios, autores o estadísticas
2. SIEMPRE cita las fuentes con el formato [Fuente: Documento, Pág. X]
3. Si no encuentras información en los documentos, indica "No disponible en la evidencia consultada"
4. Sé preciso con los números y porcentajes
5. Distingue entre recomendaciones de nivel I y opinión de expertos
6. Considera siempre el estado funcional del paciente
7. Menciona alternativas cuando existan"""

    def __init__(
        self,
        vector_store: Optional[ClinicalVectorStore] = None,
        llm_provider: str = "anthropic",
        llm_model: Optional[str] = None,
        api_key: Optional[str] = None,
        validate_responses: bool = True
    ):
        """
        Initialize the clinical reasoning engine.

        Args:
            vector_store: Pre-configured vector store instance
            llm_provider: LLM provider ("anthropic" or "openai")
            llm_model: Specific model to use
            api_key: API key for LLM provider
            validate_responses: Whether to validate responses for hallucinations
        """
        self.vector_store = vector_store or ClinicalVectorStore()
        self.prompt_generator = ClinicalPromptGenerator()
        self.llm = LLMClient(provider=llm_provider, model=llm_model, api_key=api_key)
        self.hallucination_checker = HallucinationChecker(strict_mode=True)
        self.sanitizer = ResponseSanitizer(self.hallucination_checker)
        self.validate_responses = validate_responses

    def _retrieve_evidence(
        self,
        patient: PatientData,
        risk_level: RiskLevel,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant evidence from vector store.

        Uses multiple targeted queries to get comprehensive evidence.
        """
        # Generate search queries
        queries = self.prompt_generator.generate_search_queries(patient, risk_level)

        # Perform hybrid search
        all_chunks = {}

        for query in queries:
            results = self.vector_store.search(
                query=query,
                n_results=n_results // 2
            )

            for chunk in results:
                chunk_id = chunk['chunk_id']
                if chunk_id not in all_chunks:
                    all_chunks[chunk_id] = chunk
                else:
                    # Boost relevance for chunks found by multiple queries
                    current = all_chunks[chunk_id]['relevance_score']
                    all_chunks[chunk_id]['relevance_score'] = min(1.0, current + 0.1)

        # Sort by relevance and limit
        sorted_chunks = sorted(
            all_chunks.values(),
            key=lambda x: x['relevance_score'],
            reverse=True
        )

        return sorted_chunks[:n_results]

    def _parse_reasoning_steps(self, response_text: str) -> List[ReasoningStep]:
        """
        Parse reasoning steps from the LLM response.
        """
        steps = []
        step_patterns = [
            (r'PASO\s*1[:\s]*Verificación.*?(?=PASO\s*2|$)', 'Verificación de Clasificación'),
            (r'PASO\s*2[:\s]*Identificación.*?(?=PASO\s*3|$)', 'Identificación del Tratamiento'),
            (r'PASO\s*3[:\s]*Especificaciones.*?(?=PASO\s*4|$)', 'Especificaciones de Radioterapia'),
            (r'PASO\s*4[:\s]*Terapia.*?(?=PASO\s*5|$)', 'Terapia Sistémica'),
            (r'PASO\s*5[:\s]*Extracción.*?(?=PASO\s*6|$)', 'Extracción de Outcomes'),
            (r'PASO\s*6[:\s]*Síntesis.*', 'Síntesis Final'),
        ]

        for i, (pattern, name) in enumerate(step_patterns, 1):
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(0).strip()
                # Extract conclusion (last paragraph or sentence with conclusion)
                conclusion = content.split('\n')[-1] if '\n' in content else content[-200:]

                steps.append(ReasoningStep(
                    step_number=i,
                    step_name=name,
                    analysis=content[:500],
                    conclusion=conclusion[:200],
                    confidence=0.8 + (0.2 * (i / len(step_patterns)))  # Progressive confidence
                ))

        return steps

    def _extract_citations(
        self,
        response_text: str,
        source_chunks: List[Dict[str, Any]]
    ) -> List[Citation]:
        """
        Extract citations from response and match with source chunks.
        """
        citations = []
        citation_pattern = r'\[Fuente:\s*([^,\]]+)(?:,\s*Pág\.?\s*(\d+))?\]'

        matches = re.finditer(citation_pattern, response_text)

        for match in matches:
            doc_name = match.group(1).strip()
            page_num = int(match.group(2)) if match.group(2) else None

            # Find matching chunk
            matching_chunk = None
            for chunk in source_chunks:
                if doc_name.lower() in chunk.get('document_name', '').lower():
                    if page_num is None or chunk.get('page_number') == page_num:
                        matching_chunk = chunk
                        break

            if matching_chunk:
                citations.append(Citation(
                    document=matching_chunk.get('document_name', doc_name),
                    page=matching_chunk.get('page_number'),
                    section=matching_chunk.get('section'),
                    original_text=matching_chunk.get('text', '')[:300],
                    relevance_score=matching_chunk.get('relevance_score', 0.5)
                ))
            else:
                citations.append(Citation(
                    document=doc_name,
                    page=page_num,
                    section=None,
                    original_text="[Texto no encontrado en fuentes]",
                    relevance_score=0.3
                ))

        return citations

    def _extract_outcomes(self, response_text: str) -> ClinicalOutcome:
        """
        Extract clinical outcomes from the response.
        """
        outcome = ClinicalOutcome()

        # Patterns for extracting outcome data
        patterns = {
            'overall_survival': [
                r'sobrevida\s+global[:\s]*([^.\n]+)',
                r'overall\s+survival[:\s]*([^.\n]+)',
                r'SG[:\s]*([^.\n]+)'
            ],
            'progression_free_survival': [
                r'sobrevida\s+libre\s+de\s+progresi[oó]n[:\s]*([^.\n]+)',
                r'PFS[:\s]*([^.\n]+)',
                r'progression.free\s+survival[:\s]*([^.\n]+)'
            ],
            'local_control': [
                r'control\s+local[:\s]*([^.\n]+)',
                r'local\s+control[:\s]*([^.\n]+)',
                r'CL[:\s]*([^.\n]+)'
            ],
            'disease_free_survival': [
                r'sobrevida\s+libre\s+de\s+enfermedad[:\s]*([^.\n]+)',
                r'DFS[:\s]*([^.\n]+)'
            ]
        }

        text_lower = response_text.lower()

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    value = match.group(1).strip()
                    # Clean up the value
                    value = value.split('[')[0].strip()  # Remove citation brackets
                    if value and len(value) < 100:
                        setattr(outcome, field, value)
                        break

        return outcome

    def _extract_radiotherapy_plan(
        self,
        response_text: str
    ) -> Optional[RadiotherapyRecommendation]:
        """
        Extract radiotherapy parameters from response.
        """
        # Try to find dose/fractionation
        dose_match = re.search(
            r'(\d+(?:\.\d+)?)\s*Gy\s*[/\\en]\s*(\d+)\s*(?:fx|fracciones)',
            response_text,
            re.IGNORECASE
        )

        if not dose_match:
            # Alternative pattern
            dose_match = re.search(
                r'dosis\s+total[:\s]*(\d+(?:\.\d+)?)\s*Gy',
                response_text,
                re.IGNORECASE
            )

        if not dose_match:
            return None

        total_dose = float(dose_match.group(1))

        # Get fractions
        frac_match = re.search(r'(\d+)\s*(?:fx|fracciones)', response_text, re.IGNORECASE)
        fractions = int(frac_match.group(1)) if frac_match else 1

        dose_per_fraction = round(total_dose / fractions, 2) if fractions > 0 else total_dose

        # Extract technique
        technique = "IMRT"  # Default
        technique_patterns = ['VMAT', 'IMRT', 'SBRT', '3D-CRT', 'Braquiterapia', 'IGRT']
        for tech in technique_patterns:
            if tech.lower() in response_text.lower():
                technique = tech
                break

        return RadiotherapyRecommendation(
            technique=technique,
            total_dose_gy=total_dose,
            fractions=fractions,
            dose_per_fraction=dose_per_fraction,
            target_volumes=["PTV", "CTV"]  # Default volumes
        )

    def _extract_systemic_therapy(
        self,
        response_text: str
    ) -> Optional[List[SystemicTherapyRecommendation]]:
        """
        Extract systemic therapy recommendations.
        """
        therapies = []

        # ADT/Hormone therapy for prostate
        adt_match = re.search(
            r'(?:ADT|hormonoterapia|deprivaci[oó]n\s+androg[eé]nica)'
            r'[^.]*?(\d+)\s*(?:meses|a[ñn]os)',
            response_text,
            re.IGNORECASE
        )

        if adt_match:
            duration = adt_match.group(1)
            unit = 'meses' if 'meses' in adt_match.group(0).lower() else 'años'
            therapies.append(SystemicTherapyRecommendation(
                therapy_type="Deprivación Androgénica (ADT)",
                regimen="Agonista/Antagonista LHRH",
                duration=f"{duration} {unit}",
                timing="Neoadyuvante/Concurrente/Adyuvante"
            ))

        # Chemotherapy
        chemo_match = re.search(
            r'(?:quimioterapia|QT)[^.]*?(?:concurrente|adyuvante|neoadyuvante)',
            response_text,
            re.IGNORECASE
        )

        if chemo_match:
            timing = "concurrente"
            if "adyuvante" in chemo_match.group(0).lower():
                timing = "adyuvante"
            elif "neoadyuvante" in chemo_match.group(0).lower():
                timing = "neoadyuvante"

            therapies.append(SystemicTherapyRecommendation(
                therapy_type="Quimioterapia",
                regimen="Según protocolo institucional",
                duration="Por definir",
                timing=timing
            ))

        return therapies if therapies else None

    def _determine_evidence_level(self, citations: List[Citation]) -> str:
        """
        Determine the overall evidence level based on citations.
        """
        if not citations:
            return "Nivel IV (Opinión de experto)"

        # Check for guideline sources
        guideline_keywords = ['nccn', 'esmo', 'astro', 'estro', 'asco']
        has_guideline = any(
            any(kw in c.document.lower() for kw in guideline_keywords)
            for c in citations
        )

        if has_guideline:
            return "Nivel I (Guías de práctica clínica)"

        # Check average relevance
        avg_relevance = sum(c.relevance_score for c in citations) / len(citations)

        if avg_relevance > 0.8:
            return "Nivel IIA (Evidencia alta)"
        elif avg_relevance > 0.6:
            return "Nivel IIB (Evidencia moderada)"
        else:
            return "Nivel III (Evidencia limitada)"

    async def process_consultation(
        self,
        patient: PatientData,
        include_reasoning: bool = True,
        max_citations: int = 5
    ) -> ClinicalResponse:
        """
        Process a clinical consultation request.

        This is the main entry point that orchestrates the entire
        reasoning pipeline.

        Args:
            patient: Patient data for consultation
            include_reasoning: Whether to include detailed reasoning chain
            max_citations: Maximum citations to include

        Returns:
            Structured clinical response
        """
        query_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        # Step 1: Risk Classification
        risk_level = self.prompt_generator.classify_risk(patient)
        risk_justification = self._generate_risk_justification(patient, risk_level)

        # Step 2: Retrieve Evidence
        retrieved_chunks = self._retrieve_evidence(patient, risk_level)

        if not retrieved_chunks:
            # Return response indicating no evidence found
            return ClinicalResponse(
                query_id=query_id,
                timestamp=timestamp,
                risk_classification=risk_level,
                risk_justification=risk_justification,
                primary_recommendation="No se encontró evidencia suficiente en la base de datos",
                recommendation_summary="Se requiere cargar documentos relevantes",
                reasoning_chain=[],
                expected_outcomes=ClinicalOutcome(),
                citations=[],
                confidence_score=0.0,
                evidence_level="Sin evidencia",
                hallucination_check_passed=True,
                warnings=["No hay documentos cargados en el sistema"]
            )

        # Step 3: Generate Chain of Thought Prompt
        cot_prompt = self.prompt_generator.generate_chain_of_thought_prompt(
            patient, risk_level, retrieved_chunks
        )

        # Step 4: Generate LLM Response
        llm_response = self.llm.generate(
            prompt=cot_prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.2  # Low temperature for more deterministic responses
        )

        # Step 5: Validate Response (optional)
        validation_result = None
        hallucination_passed = True

        if self.validate_responses:
            sanitized_response, validation_result = self.sanitizer.sanitize(
                llm_response,
                retrieved_chunks,
                mode="flag"
            )
            llm_response = sanitized_response
            hallucination_passed = validation_result.is_valid

        # Step 6: Parse and Structure Response
        reasoning_steps = self._parse_reasoning_steps(llm_response) if include_reasoning else []
        citations = self._extract_citations(llm_response, retrieved_chunks)[:max_citations]
        outcomes = self._extract_outcomes(llm_response)
        radiotherapy = self._extract_radiotherapy_plan(llm_response)
        systemic = self._extract_systemic_therapy(llm_response)

        # Step 7: Extract primary recommendation
        primary_rec = self._extract_primary_recommendation(llm_response)
        summary = self._generate_summary(patient, risk_level, radiotherapy, systemic)

        # Step 8: Calculate confidence
        confidence = self._calculate_confidence(
            citations, validation_result, retrieved_chunks
        )

        # Step 9: Build warnings
        warnings = []
        if validation_result and validation_result.warnings:
            warnings.extend(validation_result.warnings)
        if patient.ecog_status.value >= 3:
            warnings.append("Paciente con ECOG ≥3: considerar tratamiento paliativo")

        return ClinicalResponse(
            query_id=query_id,
            timestamp=timestamp,
            risk_classification=risk_level,
            risk_justification=risk_justification,
            primary_recommendation=primary_rec,
            recommendation_summary=summary,
            radiotherapy=radiotherapy,
            systemic_therapy=systemic,
            reasoning_chain=reasoning_steps,
            expected_outcomes=outcomes,
            citations=citations,
            confidence_score=confidence,
            evidence_level=self._determine_evidence_level(citations),
            hallucination_check_passed=hallucination_passed,
            warnings=warnings,
            alternative_options=self._extract_alternatives(llm_response)
        )

    def _generate_risk_justification(
        self,
        patient: PatientData,
        risk_level: RiskLevel
    ) -> str:
        """Generate justification for risk classification."""
        parts = [f"Clasificado como riesgo {risk_level.value}"]

        if patient.tumor_type.value == "prostata" and patient.prostate_data:
            pd = patient.prostate_data
            parts.append(f"basado en: PSA {pd.psa}, Gleason {pd.gleason_score}")
            parts.append(f"estadio {patient.staging.tnm_string}")

        return " ".join(parts)

    def _extract_primary_recommendation(self, response_text: str) -> str:
        """Extract the primary recommendation from response."""
        # Look for recommendation section
        patterns = [
            r'Recomendaci[oó]n\s+Principal[:\s]*([^\n]+(?:\n(?![A-Z#])[^\n]+)*)',
            r'Se\s+recomienda[:\s]*([^.\n]+)',
            r'El\s+tratamiento\s+recomendado[:\s]*([^.\n]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:500]

        # Default: first substantial paragraph
        paragraphs = response_text.split('\n\n')
        for p in paragraphs:
            if len(p) > 50 and not p.startswith('#'):
                return p[:500]

        return "Ver análisis detallado"

    def _generate_summary(
        self,
        patient: PatientData,
        risk_level: RiskLevel,
        radiotherapy: Optional[RadiotherapyRecommendation],
        systemic: Optional[List[SystemicTherapyRecommendation]]
    ) -> str:
        """Generate a brief summary of the recommendation."""
        parts = []

        if radiotherapy:
            parts.append(f"{radiotherapy.technique} {radiotherapy.fractionation_scheme}")

        if systemic:
            for s in systemic:
                if s.duration:
                    parts.append(f"{s.therapy_type} {s.duration}")

        if parts:
            return " + ".join(parts)

        return f"Tratamiento para {patient.tumor_type.value} riesgo {risk_level.value}"

    def _calculate_confidence(
        self,
        citations: List[Citation],
        validation_result: Any,
        chunks: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence score."""
        scores = []

        # Citation quality
        if citations:
            avg_relevance = sum(c.relevance_score for c in citations) / len(citations)
            scores.append(avg_relevance)

        # Validation result
        if validation_result:
            scores.append(validation_result.confidence_score)

        # Evidence coverage
        if chunks:
            coverage = min(1.0, len(chunks) / 5)  # Normalize to max 5 chunks
            scores.append(coverage)

        return round(sum(scores) / len(scores), 2) if scores else 0.5

    def _extract_alternatives(self, response_text: str) -> List[str]:
        """Extract alternative treatment options."""
        alternatives = []

        patterns = [
            r'alternativa[s]?[:\s]*([^\n]+)',
            r'otra[s]?\s+opci[oó]n[es]*[:\s]*([^\n]+)',
            r'tambi[eé]n\s+(?:se\s+)?puede[n]?\s+considerar[:\s]*([^\n]+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            alternatives.extend([m.strip()[:200] for m in matches])

        return alternatives[:3]  # Max 3 alternatives

    # Synchronous wrapper for non-async contexts
    def process_consultation_sync(
        self,
        patient: PatientData,
        include_reasoning: bool = True,
        max_citations: int = 5
    ) -> ClinicalResponse:
        """Synchronous version of process_consultation."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.process_consultation(patient, include_reasoning, max_citations)
        )
