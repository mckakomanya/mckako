"""
OncoRAD Hallucination Checker

Validates AI-generated responses against source documents to detect
and flag potential hallucinations or unsupported claims.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of hallucination validation."""
    is_valid: bool
    confidence_score: float
    verified_claims: List[str] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)
    potential_hallucinations: List[str] = field(default_factory=list)
    citation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "confidence_score": self.confidence_score,
            "verified_claims": self.verified_claims,
            "unverified_claims": self.unverified_claims,
            "potential_hallucinations": self.potential_hallucinations,
            "citation_errors": self.citation_errors,
            "warnings": self.warnings
        }


class HallucinationChecker:
    """
    Validates AI responses against source documents.

    Detects potential hallucinations by comparing generated content
    with the actual retrieved evidence.
    """

    # Common patterns that might indicate hallucinations
    STUDY_PATTERNS = [
        r'estudio\s+([A-Z][A-Za-z0-9\-]+)',  # "estudio RTOG-9408"
        r'trial\s+([A-Z][A-Za-z0-9\-]+)',
        r'ensayo\s+([A-Z][A-Za-z0-9\-]+)',
        r'([A-Z]{2,}[\-\s]?\d{2,})',  # RTOG-9408, EORTC 22863
    ]

    AUTHOR_PATTERNS = [
        r'(?:según|por|de)\s+([A-Z][a-z]+(?:\s+et\s+al\.?)?)',
        r'([A-Z][a-z]+)\s+(?:y\s+col\.|et\s+al\.)',
    ]

    STATISTIC_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*%',  # Percentages
        r'HR\s*[=:]\s*(\d+(?:\.\d+)?)',  # Hazard ratios
        r'(\d+(?:\.\d+)?)\s*(?:años|months|years)',  # Time periods
        r'p\s*[=<>]\s*(\d+(?:\.\d+)?)',  # p-values
    ]

    # Citation format expected: [Fuente: Document, Pág. X]
    CITATION_PATTERN = r'\[Fuente:\s*([^,\]]+)(?:,\s*Pág\.?\s*(\d+))?\]'

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the checker.

        Args:
            strict_mode: If True, flag any claim without direct textual support
        """
        self.strict_mode = strict_mode

    def extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract claims and their citations from response text.

        Args:
            text: Generated response text

        Returns:
            List of claims with their associated citations
        """
        claims = []

        # Split into sentences/claims
        sentences = re.split(r'[.!?]\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # Find citations in this sentence
            citations = re.findall(self.CITATION_PATTERN, sentence)

            # Check for studies mentioned
            studies = []
            for pattern in self.STUDY_PATTERNS:
                studies.extend(re.findall(pattern, sentence))

            # Check for statistics
            statistics = []
            for pattern in self.STATISTIC_PATTERNS:
                statistics.extend(re.findall(pattern, sentence))

            # Check for author references
            authors = []
            for pattern in self.AUTHOR_PATTERNS:
                authors.extend(re.findall(pattern, sentence))

            claims.append({
                "text": sentence,
                "citations": citations,
                "studies_mentioned": list(set(studies)),
                "statistics": list(set(statistics)),
                "authors": list(set(authors)),
                "has_citation": len(citations) > 0
            })

        return claims

    def verify_citations(
        self,
        claims: List[Dict[str, Any]],
        source_chunks: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """
        Verify that citations reference actual source documents.

        Args:
            claims: Extracted claims
            source_chunks: Original source chunks

        Returns:
            Tuple of (valid_citations, invalid_citations)
        """
        # Build set of available documents
        available_docs = set()
        doc_pages = {}

        for chunk in source_chunks:
            doc_name = chunk.get('document_name', '')
            page = chunk.get('page_number')

            if doc_name:
                available_docs.add(doc_name.lower())
                # Track pages for each document
                if doc_name.lower() not in doc_pages:
                    doc_pages[doc_name.lower()] = set()
                if page and page > 0:
                    doc_pages[doc_name.lower()].add(page)

        valid = []
        invalid = []

        for claim in claims:
            for citation in claim['citations']:
                doc_cited = citation[0].strip().lower() if citation[0] else ""
                page_cited = int(citation[1]) if citation[1] else None

                # Check if document exists
                doc_found = any(
                    doc_cited in available_doc or available_doc in doc_cited
                    for available_doc in available_docs
                )

                if doc_found:
                    valid.append(f"{citation[0]}, Pág. {citation[1] or '?'}")
                else:
                    invalid.append(f"{citation[0]}, Pág. {citation[1] or '?'} (documento no encontrado)")

        return valid, invalid

    def check_factual_support(
        self,
        claim_text: str,
        source_chunks: List[Dict[str, Any]],
        threshold: float = 0.3
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Check if a claim has factual support in source documents.

        Args:
            claim_text: The claim to verify
            source_chunks: Source document chunks
            threshold: Minimum word overlap ratio for support

        Returns:
            Tuple of (is_supported, support_score, supporting_chunk)
        """
        claim_words = set(claim_text.lower().split())
        claim_words = {w for w in claim_words if len(w) > 3}  # Filter short words

        best_score = 0.0
        best_chunk = None

        for chunk in source_chunks:
            chunk_text = chunk.get('text', '').lower()
            chunk_words = set(chunk_text.split())
            chunk_words = {w for w in chunk_words if len(w) > 3}

            if not claim_words or not chunk_words:
                continue

            # Calculate word overlap
            overlap = len(claim_words & chunk_words)
            score = overlap / len(claim_words) if claim_words else 0

            if score > best_score:
                best_score = score
                best_chunk = chunk.get('text', '')[:200]

        return best_score >= threshold, best_score, best_chunk

    def detect_potential_hallucinations(
        self,
        claims: List[Dict[str, Any]],
        source_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify claims that might be hallucinations.

        Args:
            claims: Extracted claims from response
            source_chunks: Source document chunks

        Returns:
            List of potential hallucinations with details
        """
        hallucinations = []
        source_text = " ".join([c.get('text', '') for c in source_chunks]).lower()

        for claim in claims:
            issues = []

            # Check studies mentioned
            for study in claim.get('studies_mentioned', []):
                study_lower = study.lower()
                if study_lower not in source_text:
                    issues.append(f"Estudio '{study}' no encontrado en fuentes")

            # Check authors mentioned
            for author in claim.get('authors', []):
                author_lower = author.lower().split()[0]  # First name only
                if author_lower not in source_text and len(author_lower) > 3:
                    issues.append(f"Autor '{author}' no encontrado en fuentes")

            # Check statistics if strict mode
            if self.strict_mode and claim.get('statistics'):
                for stat in claim['statistics']:
                    if stat not in source_text and f"{stat}%" not in source_text:
                        # Check if it's a close match (within rounding)
                        try:
                            stat_val = float(stat)
                            found = False
                            for delta in [-1, 0, 1]:
                                if str(int(stat_val + delta)) in source_text:
                                    found = True
                                    break
                            if not found:
                                issues.append(f"Estadística '{stat}' no verificada en fuentes")
                        except ValueError:
                            pass

            if issues:
                hallucinations.append({
                    "claim": claim['text'][:200],
                    "issues": issues,
                    "has_citation": claim.get('has_citation', False)
                })

        return hallucinations

    def validate_response(
        self,
        response_text: str,
        source_chunks: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Perform comprehensive validation of a response.

        Args:
            response_text: The AI-generated response
            source_chunks: Source document chunks used

        Returns:
            ValidationResult with detailed analysis
        """
        result = ValidationResult(
            is_valid=True,
            confidence_score=1.0,
            verified_claims=[],
            unverified_claims=[],
            potential_hallucinations=[],
            citation_errors=[],
            warnings=[]
        )

        # Extract claims
        claims = self.extract_claims(response_text)

        if not claims:
            result.warnings.append("No se pudieron extraer afirmaciones de la respuesta")
            result.confidence_score = 0.5
            return result

        # Verify citations
        valid_citations, invalid_citations = self.verify_citations(claims, source_chunks)
        result.citation_errors = invalid_citations

        # Check factual support for each claim
        for claim in claims:
            is_supported, score, _ = self.check_factual_support(
                claim['text'], source_chunks
            )

            if is_supported or claim.get('has_citation'):
                result.verified_claims.append(claim['text'][:100])
            else:
                result.unverified_claims.append(claim['text'][:100])

        # Detect hallucinations
        hallucinations = self.detect_potential_hallucinations(claims, source_chunks)
        for h in hallucinations:
            result.potential_hallucinations.append(
                f"{h['claim'][:100]}... - Problemas: {', '.join(h['issues'])}"
            )

        # Calculate confidence score
        total_claims = len(claims)
        verified_count = len(result.verified_claims)
        hallucination_count = len(result.potential_hallucinations)
        citation_error_count = len(result.citation_errors)

        if total_claims > 0:
            base_score = verified_count / total_claims
            penalty = (hallucination_count * 0.15) + (citation_error_count * 0.1)
            result.confidence_score = max(0.0, min(1.0, base_score - penalty))

        # Determine validity
        result.is_valid = (
            result.confidence_score >= 0.6 and
            hallucination_count <= 2 and
            citation_error_count <= 1
        )

        # Add warnings
        if hallucination_count > 0:
            result.warnings.append(
                f"Se detectaron {hallucination_count} posibles alucinaciones"
            )
        if citation_error_count > 0:
            result.warnings.append(
                f"Se encontraron {citation_error_count} errores de cita"
            )
        if len(result.unverified_claims) > total_claims * 0.3:
            result.warnings.append(
                "Más del 30% de las afirmaciones no tienen soporte verificable"
            )

        return result

    def suggest_corrections(
        self,
        validation_result: ValidationResult,
        source_chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Suggest corrections for identified issues.

        Args:
            validation_result: Result from validation
            source_chunks: Source chunks for reference

        Returns:
            List of correction suggestions
        """
        suggestions = []

        # Suggest for citation errors
        available_docs = list(set(
            c.get('document_name', '') for c in source_chunks
            if c.get('document_name')
        ))

        for error in validation_result.citation_errors:
            suggestions.append(
                f"Cita incorrecta: {error}. "
                f"Documentos disponibles: {', '.join(available_docs[:5])}"
            )

        # Suggest for unverified claims
        if validation_result.unverified_claims:
            suggestions.append(
                "Considere agregar citas para las afirmaciones no verificadas "
                "o marcarlas como 'No disponible en la evidencia consultada'"
            )

        # Suggest for hallucinations
        if validation_result.potential_hallucinations:
            suggestions.append(
                "Revise las posibles alucinaciones y elimine o corrija "
                "las referencias a estudios/autores no presentes en las fuentes"
            )

        return suggestions


class ResponseSanitizer:
    """
    Sanitizes AI responses to remove or flag unsupported content.
    """

    def __init__(self, checker: HallucinationChecker):
        self.checker = checker

    def sanitize(
        self,
        response_text: str,
        source_chunks: List[Dict[str, Any]],
        mode: str = "flag"  # "flag", "remove", or "annotate"
    ) -> Tuple[str, ValidationResult]:
        """
        Sanitize response by handling unsupported content.

        Args:
            response_text: Original response
            source_chunks: Source document chunks
            mode: How to handle issues ("flag", "remove", "annotate")

        Returns:
            Tuple of (sanitized_text, validation_result)
        """
        validation = self.checker.validate_response(response_text, source_chunks)

        if validation.is_valid and not validation.potential_hallucinations:
            return response_text, validation

        sanitized = response_text

        if mode == "flag":
            # Add warning at the top
            if validation.potential_hallucinations:
                warning = (
                    "\n⚠️ ADVERTENCIA: Esta respuesta contiene "
                    f"{len(validation.potential_hallucinations)} afirmaciones "
                    "que no pudieron ser completamente verificadas contra las fuentes.\n\n"
                )
                sanitized = warning + sanitized

        elif mode == "annotate":
            # Add inline annotations for problematic claims
            for hallucination in validation.potential_hallucinations:
                claim_text = hallucination.split("...")[0]
                if claim_text in sanitized:
                    sanitized = sanitized.replace(
                        claim_text,
                        f"{claim_text} [⚠️ NO VERIFICADO]"
                    )

        elif mode == "remove":
            # Remove sentences with hallucinations (more aggressive)
            for hallucination in validation.potential_hallucinations:
                claim_text = hallucination.split("...")[0]
                if claim_text in sanitized:
                    sanitized = sanitized.replace(
                        claim_text + ".",
                        "[Contenido eliminado por falta de verificación]."
                    )

        return sanitized, validation
