"""
Módulo de Validación y Auto-Corrección - OncoRad AI

Este módulo implementa el sistema de validación que asegura que las respuestas
del LLM estén fundamentadas en el texto fuente recuperado, eliminando alucinaciones.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from llama_index.llms.openai import OpenAI
from rich.console import Console

from .config import Settings, get_settings
from .query_engine import QueryResponse, SourceNode

console = Console()


class ValidationStatus(Enum):
    """Estados posibles de validación."""
    VALID = "valid"
    PARTIALLY_VALID = "partially_valid"
    INVALID = "invalid"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class ValidationResult:
    """
    Resultado de la validación de una respuesta.

    Attributes:
        status: Estado de la validación.
        confidence_score: Puntuación de confianza (0-1).
        grounded_claims: Afirmaciones respaldadas por fuentes.
        ungrounded_claims: Afirmaciones no respaldadas.
        corrected_response: Respuesta corregida si es necesario.
        validation_reasoning: Razonamiento del validador.
    """
    status: ValidationStatus
    confidence_score: float
    grounded_claims: list[str]
    ungrounded_claims: list[str]
    corrected_response: Optional[str] = None
    validation_reasoning: str = ""


class ResponseValidator:
    """
    Validador de respuestas del sistema RAG.

    Implementa un loop de auto-corrección donde el LLM verifica si su respuesta
    coincide con el texto recuperado de las guías clínicas.
    """

    VALIDATION_PROMPT = """Eres un auditor de información médica. Tu tarea es verificar si una respuesta está COMPLETAMENTE respaldada por los textos fuente proporcionados.

TEXTOS FUENTE (estos son los únicos datos válidos):
{source_texts}

RESPUESTA A VERIFICAR:
{response}

INSTRUCCIONES DE VERIFICACIÓN:
1. Identifica CADA afirmación factual en la respuesta.
2. Para cada afirmación, busca evidencia EXACTA en los textos fuente.
3. Marca como "RESPALDADA" solo si hay coincidencia textual clara.
4. Marca como "NO RESPALDADA" si la información no aparece en las fuentes.

RESPONDE EN EL SIGUIENTE FORMATO JSON:
{{
    "status": "valid" | "partially_valid" | "invalid" | "insufficient_evidence",
    "confidence_score": 0.0-1.0,
    "grounded_claims": ["afirmación 1", "afirmación 2"],
    "ungrounded_claims": ["afirmación no respaldada 1"],
    "reasoning": "Explicación del análisis",
    "corrected_response": "Solo si status != valid, proporciona una versión corregida que SOLO incluya información de las fuentes"
}}

IMPORTANTE:
- Si encuentras información en la respuesta que NO está en las fuentes, el status NO puede ser "valid".
- Las citas de página DEBEN coincidir con los metadatos de las fuentes.
- Sé estricto: es mejor decir "información insuficiente" que validar información dudosa."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa el validador.

        Args:
            settings: Configuración del sistema.
        """
        self.settings = settings or get_settings()
        self._init_llm()

    def _init_llm(self) -> None:
        """Inicializa el LLM para validación."""
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY no está configurada.")

        # Usar un modelo con temperature=0 para validación determinista
        self.llm = OpenAI(
            model=self.settings.llm_model,
            temperature=0.0,
            api_key=self.settings.openai_api_key,
        )

    def _format_source_texts(self, source_nodes: list[SourceNode]) -> str:
        """
        Formatea los textos fuente para el prompt de validación.

        Args:
            source_nodes: Lista de nodos fuente.

        Returns:
            Texto formateado con las fuentes.
        """
        formatted = []
        for i, node in enumerate(source_nodes, 1):
            formatted.append(
                f"[FUENTE {i}]\n"
                f"Archivo: {node.source_file}\n"
                f"Página: {node.page_number}\n"
                f"Versión: {node.guideline_version}\n"
                f"Texto:\n{node.text}\n"
                f"{'─' * 40}"
            )
        return "\n\n".join(formatted)

    def _parse_validation_response(self, response_text: str) -> ValidationResult:
        """
        Parsea la respuesta del LLM de validación.

        Args:
            response_text: Respuesta del LLM.

        Returns:
            ValidationResult parseado.
        """
        import json

        try:
            # Intentar extraer JSON de la respuesta
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())

                status_str = data.get("status", "invalid")
                try:
                    status = ValidationStatus(status_str)
                except ValueError:
                    status = ValidationStatus.INVALID

                return ValidationResult(
                    status=status,
                    confidence_score=float(data.get("confidence_score", 0.0)),
                    grounded_claims=data.get("grounded_claims", []),
                    ungrounded_claims=data.get("ungrounded_claims", []),
                    corrected_response=data.get("corrected_response"),
                    validation_reasoning=data.get("reasoning", ""),
                )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            console.print(f"[yellow]Advertencia al parsear validación: {e}[/yellow]")

        # Fallback si no se puede parsear
        return ValidationResult(
            status=ValidationStatus.INVALID,
            confidence_score=0.0,
            grounded_claims=[],
            ungrounded_claims=["Error al parsear la validación"],
            validation_reasoning="No se pudo parsear la respuesta del validador",
        )

    def validate(self, query_response: QueryResponse) -> ValidationResult:
        """
        Valida una respuesta del motor de consultas.

        Args:
            query_response: Respuesta a validar.

        Returns:
            Resultado de la validación.
        """
        if not query_response.source_nodes:
            return ValidationResult(
                status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                confidence_score=0.0,
                grounded_claims=[],
                ungrounded_claims=[],
                validation_reasoning="No hay fuentes disponibles para validar la respuesta.",
            )

        # Formatear fuentes
        source_texts = self._format_source_texts(query_response.source_nodes)

        # Crear prompt de validación
        validation_prompt = self.VALIDATION_PROMPT.format(
            source_texts=source_texts,
            response=query_response.response,
        )

        # Ejecutar validación
        response = self.llm.complete(validation_prompt)

        # Parsear resultado
        validation_result = self._parse_validation_response(str(response))

        return validation_result

    def validate_and_correct(self, query_response: QueryResponse) -> QueryResponse:
        """
        Valida y corrige una respuesta si es necesario.

        Este es el "Refinement Loop" que asegura que la respuesta final
        esté completamente respaldada por las fuentes.

        Args:
            query_response: Respuesta original.

        Returns:
            QueryResponse validada y posiblemente corregida.
        """
        console.print("[blue]Ejecutando validación de respuesta...[/blue]")

        validation = self.validate(query_response)

        # Actualizar el response con la validación
        query_response.is_validated = True

        if validation.status == ValidationStatus.VALID:
            query_response.validation_notes = (
                f"✓ Respuesta validada con {validation.confidence_score:.0%} de confianza. "
                f"{len(validation.grounded_claims)} afirmaciones respaldadas."
            )
            console.print("[green]✓ Respuesta validada correctamente[/green]")

        elif validation.status == ValidationStatus.PARTIALLY_VALID:
            # Si hay respuesta corregida, usarla
            if validation.corrected_response:
                original_response = query_response.response
                query_response.response = validation.corrected_response
                query_response.validation_notes = (
                    f"⚠ Respuesta parcialmente válida. Corregida automáticamente. "
                    f"Afirmaciones no respaldadas eliminadas: {validation.ungrounded_claims}"
                )
                console.print(
                    "[yellow]⚠ Respuesta parcialmente válida - Se aplicó corrección[/yellow]"
                )
            else:
                query_response.validation_notes = (
                    f"⚠ Respuesta parcialmente válida ({validation.confidence_score:.0%}). "
                    f"Afirmaciones no respaldadas: {validation.ungrounded_claims}"
                )

        elif validation.status == ValidationStatus.INVALID:
            if validation.corrected_response:
                query_response.response = validation.corrected_response
                query_response.validation_notes = (
                    "✗ Respuesta original inválida. Se generó versión corregida basada "
                    "exclusivamente en las fuentes disponibles."
                )
            else:
                query_response.response = (
                    "No se puede proporcionar una respuesta confiable. "
                    "La información disponible en las guías clínicas es insuficiente "
                    "para responder esta consulta con precisión. "
                    "Razón: " + validation.validation_reasoning
                )
                query_response.validation_notes = (
                    "✗ Respuesta inválida - No fue posible generar una respuesta confiable"
                )
            console.print("[red]✗ Respuesta inválida - Se aplicó corrección[/red]")

        else:  # INSUFFICIENT_EVIDENCE
            query_response.validation_notes = (
                "⚠ Evidencia insuficiente en las fuentes disponibles."
            )
            console.print("[yellow]⚠ Evidencia insuficiente[/yellow]")

        return query_response


class CitationVerifier:
    """
    Verificador de citas para asegurar que las referencias son correctas.
    """

    @staticmethod
    def extract_citations(response_text: str) -> list[dict]:
        """
        Extrae citas del texto de respuesta.

        Args:
            response_text: Texto de la respuesta.

        Returns:
            Lista de citas encontradas.
        """
        citations = []

        # Patrones comunes de citación
        patterns = [
            # Patrón: (documento, página X)
            r'\(([^,]+),\s*(?:página|page|p\.?)\s*(\d+)\)',
            # Patrón: [documento, p. X]
            r'\[([^\]]+),\s*(?:página|page|p\.?)\s*(\d+)\]',
            # Patrón: Fuente: documento, página X
            r'Fuente:\s*([^,]+),\s*(?:página|page|p\.?)\s*(\d+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            for match in matches:
                citations.append({
                    "document": match[0].strip(),
                    "page": int(match[1]),
                })

        return citations

    @staticmethod
    def verify_citations(
        citations: list[dict],
        source_nodes: list[SourceNode]
    ) -> dict:
        """
        Verifica que las citas coincidan con las fuentes.

        Args:
            citations: Lista de citas extraídas.
            source_nodes: Nodos fuente disponibles.

        Returns:
            Resultado de la verificación.
        """
        results = {
            "verified": [],
            "unverified": [],
            "verification_rate": 0.0,
        }

        if not citations:
            return results

        # Crear lookup de fuentes
        source_lookup = {}
        for node in source_nodes:
            key = (node.source_file.lower(), node.page_number)
            source_lookup[key] = node

        for citation in citations:
            doc_name = citation["document"].lower()
            page = citation["page"]

            # Buscar coincidencia flexible
            found = False
            for (source_file, source_page), node in source_lookup.items():
                if doc_name in source_file or source_file in doc_name:
                    if page == source_page:
                        results["verified"].append(citation)
                        found = True
                        break

            if not found:
                results["unverified"].append(citation)

        total = len(citations)
        if total > 0:
            results["verification_rate"] = len(results["verified"]) / total

        return results


def validate_query_response(query_response: QueryResponse) -> QueryResponse:
    """
    Función de conveniencia para validar y corregir una respuesta.

    Args:
        query_response: Respuesta a validar.

    Returns:
        Respuesta validada.
    """
    validator = ResponseValidator()
    return validator.validate_and_correct(query_response)
