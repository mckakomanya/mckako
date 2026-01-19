"""
Motor de Consultas RAG - OncoRad AI

Este módulo implementa el motor de consultas que convierte parámetros clínicos
en búsquedas semánticas y genera recomendaciones citando las fuentes.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import chromadb
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
from rich.console import Console
from rich.panel import Panel

from .config import Settings, get_settings

console = Console()


@dataclass
class ClinicalCase:
    """
    Representa un caso clínico para consulta.

    Attributes:
        histologia: Tipo histológico del tumor.
        tnm: Clasificación TNM del tumor.
        psa: Nivel de PSA (para cáncer de próstata).
        gleason: Score de Gleason (para cáncer de próstata).
        age: Edad del paciente.
        comorbidities: Comorbilidades relevantes.
        additional_info: Información adicional del caso.
    """
    histologia: str
    tnm: Optional[str] = None
    psa: Optional[float] = None
    gleason: Optional[str] = None
    age: Optional[int] = None
    comorbidities: Optional[list[str]] = field(default_factory=list)
    additional_info: Optional[str] = None

    def to_query(self) -> str:
        """
        Convierte el caso clínico en una consulta de texto estructurada.

        Returns:
            Consulta formateada para búsqueda semántica.
        """
        parts = [f"Histología: {self.histologia}"]

        if self.tnm:
            parts.append(f"Estadio TNM: {self.tnm}")
        if self.psa is not None:
            parts.append(f"PSA: {self.psa} ng/mL")
        if self.gleason:
            parts.append(f"Gleason: {self.gleason}")
        if self.age:
            parts.append(f"Edad: {self.age} años")
        if self.comorbidities:
            parts.append(f"Comorbilidades: {', '.join(self.comorbidities)}")
        if self.additional_info:
            parts.append(f"Información adicional: {self.additional_info}")

        query = (
            "Caso clínico para evaluación oncológica radioterápica:\n"
            + "\n".join(f"- {p}" for p in parts)
            + "\n\n¿Cuál es la recomendación de tratamiento radioterápico "
            "según las guías de práctica clínica?"
        )

        return query


@dataclass
class SourceNode:
    """Representa un nodo fuente usado en la respuesta."""
    text: str
    source_file: str
    page_number: int
    guideline_version: str
    cancer_type: str
    similarity_score: float


@dataclass
class QueryResponse:
    """
    Respuesta estructurada del motor de consultas.

    Attributes:
        response: Respuesta generada por el LLM.
        source_nodes: Lista de nodos fuente utilizados.
        clinical_case: Caso clínico original.
        is_validated: Si la respuesta pasó la validación.
        validation_notes: Notas de la validación.
    """
    response: str
    source_nodes: list[SourceNode]
    clinical_case: ClinicalCase
    is_validated: bool = False
    validation_notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convierte la respuesta a diccionario para serialización JSON."""
        return {
            "response": self.response,
            "source_nodes": [
                {
                    "text": node.text,
                    "source_file": node.source_file,
                    "page_number": node.page_number,
                    "guideline_version": node.guideline_version,
                    "cancer_type": node.cancer_type,
                    "similarity_score": node.similarity_score,
                }
                for node in self.source_nodes
            ],
            "is_validated": self.is_validated,
            "validation_notes": self.validation_notes,
        }

    def to_json(self) -> str:
        """Serializa la respuesta a JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class OncoRadQueryEngine:
    """
    Motor de consultas RAG para oncología radioterápica.

    Procesa casos clínicos, busca en las guías indexadas, y genera
    recomendaciones con citas verificables.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa el motor de consultas.

        Args:
            settings: Configuración del sistema.
        """
        self.settings = settings or get_settings()
        self._validate_api_key()
        self._init_components()

    def _validate_api_key(self) -> None:
        """Valida que la API key de OpenAI esté configurada."""
        if not self.settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY no está configurada. "
                "Configúrala en el archivo .env o como variable de entorno."
            )

    def _init_components(self) -> None:
        """Inicializa todos los componentes del motor."""
        # Inicializar LLM
        self.llm = OpenAI(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            api_key=self.settings.openai_api_key,
            system_prompt=self.settings.system_prompt,
        )

        # Inicializar modelo de embeddings
        self.embed_model = OpenAIEmbedding(
            model=self.settings.embedding_model,
            api_key=self.settings.openai_api_key,
        )

        # Conectar a ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.settings.chroma_db_dir)
        )

        try:
            self.chroma_collection = self.chroma_client.get_collection(
                name=self.settings.chroma_collection_name
            )
        except Exception:
            raise ValueError(
                f"Colección '{self.settings.chroma_collection_name}' no encontrada. "
                "Ejecuta primero la ingesta de documentos."
            )

        # Configurar vector store
        self.vector_store = ChromaVectorStore(
            chroma_collection=self.chroma_collection
        )

        # Crear índice
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model,
        )

        # Configurar retriever
        self.retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.settings.similarity_top_k,
        )

        # Configurar response synthesizer
        self.response_synthesizer = get_response_synthesizer(
            llm=self.llm,
            response_mode=ResponseMode.COMPACT,
        )

        # Configurar query engine
        self.query_engine = RetrieverQueryEngine(
            retriever=self.retriever,
            response_synthesizer=self.response_synthesizer,
            node_postprocessors=[
                SimilarityPostprocessor(similarity_cutoff=0.3)
            ],
        )

    def query(self, clinical_case: ClinicalCase) -> QueryResponse:
        """
        Procesa una consulta clínica y genera una recomendación.

        Args:
            clinical_case: Caso clínico a evaluar.

        Returns:
            QueryResponse con la respuesta y fuentes citadas.
        """
        # Convertir caso clínico a query
        query_text = clinical_case.to_query()

        console.print(Panel(
            query_text,
            title="[bold blue]Consulta Clínica[/bold blue]",
            border_style="blue"
        ))

        # Ejecutar consulta
        response = self.query_engine.query(query_text)

        # Extraer nodos fuente
        source_nodes = []
        for node in response.source_nodes:
            metadata = node.node.metadata
            source_nodes.append(SourceNode(
                text=node.node.text,
                source_file=metadata.get("source_file", "desconocido"),
                page_number=metadata.get("page_number", 0),
                guideline_version=metadata.get("guideline_version", "desconocido"),
                cancer_type=metadata.get("cancer_type", "desconocido"),
                similarity_score=node.score if node.score else 0.0,
            ))

        # Crear respuesta estructurada
        query_response = QueryResponse(
            response=str(response),
            source_nodes=source_nodes,
            clinical_case=clinical_case,
        )

        return query_response

    def query_with_dict(self, case_data: dict) -> QueryResponse:
        """
        Procesa una consulta usando un diccionario de datos clínicos.

        Args:
            case_data: Diccionario con histologia, tnm, psa, gleason, etc.

        Returns:
            QueryResponse con la respuesta y fuentes citadas.
        """
        clinical_case = ClinicalCase(
            histologia=case_data.get("histologia", "No especificado"),
            tnm=case_data.get("tnm"),
            psa=case_data.get("psa"),
            gleason=case_data.get("gleason"),
            age=case_data.get("age"),
            comorbidities=case_data.get("comorbidities", []),
            additional_info=case_data.get("additional_info"),
        )

        return self.query(clinical_case)

    def query_text(self, query_text: str) -> QueryResponse:
        """
        Procesa una consulta de texto libre.

        Args:
            query_text: Texto de la consulta.

        Returns:
            QueryResponse con la respuesta y fuentes citadas.
        """
        # Crear un caso clínico genérico para consultas de texto libre
        clinical_case = ClinicalCase(
            histologia="Consulta de texto libre",
            additional_info=query_text,
        )

        # Ejecutar consulta directamente
        response = self.query_engine.query(query_text)

        # Extraer nodos fuente
        source_nodes = []
        for node in response.source_nodes:
            metadata = node.node.metadata
            source_nodes.append(SourceNode(
                text=node.node.text,
                source_file=metadata.get("source_file", "desconocido"),
                page_number=metadata.get("page_number", 0),
                guideline_version=metadata.get("guideline_version", "desconocido"),
                cancer_type=metadata.get("cancer_type", "desconocido"),
                similarity_score=node.score if node.score else 0.0,
            ))

        return QueryResponse(
            response=str(response),
            source_nodes=source_nodes,
            clinical_case=clinical_case,
        )

    def get_index_stats(self) -> dict:
        """
        Obtiene estadísticas del índice.

        Returns:
            Diccionario con estadísticas del índice.
        """
        count = self.chroma_collection.count()

        return {
            "total_documents": count,
            "collection_name": self.settings.chroma_collection_name,
            "llm_model": self.settings.llm_model,
            "embedding_model": self.settings.embedding_model,
            "similarity_top_k": self.settings.similarity_top_k,
        }


def format_response_for_display(response: QueryResponse) -> str:
    """
    Formatea la respuesta para mostrar en consola.

    Args:
        response: Respuesta del motor de consultas.

    Returns:
        Texto formateado para display.
    """
    output = []
    output.append("═" * 60)
    output.append("RESPUESTA DEL SISTEMA OncoRad AI")
    output.append("═" * 60)
    output.append("")
    output.append(response.response)
    output.append("")
    output.append("─" * 60)
    output.append("FUENTES CITADAS:")
    output.append("─" * 60)

    for i, node in enumerate(response.source_nodes, 1):
        output.append(f"\n[{i}] {node.source_file} - Página {node.page_number}")
        output.append(f"    Versión: {node.guideline_version}")
        output.append(f"    Tipo de cáncer: {node.cancer_type}")
        output.append(f"    Relevancia: {node.similarity_score:.2%}")
        output.append(f"    Extracto: {node.text[:200]}...")

    if response.is_validated:
        output.append("\n" + "─" * 60)
        output.append(f"[✓] Respuesta validada: {response.validation_notes}")

    return "\n".join(output)


def main():
    """Función principal para pruebas desde línea de comandos."""
    console.print("[bold blue]═══ OncoRad AI - Motor de Consultas ═══[/bold blue]\n")

    try:
        engine = OncoRadQueryEngine()

        stats = engine.get_index_stats()
        console.print(f"[green]Documentos indexados: {stats['total_documents']}[/green]")

        if stats['total_documents'] == 0:
            console.print(
                "[yellow]No hay documentos indexados. "
                "Ejecuta primero: python -m oncorad_rag.ingest[/yellow]"
            )
            return

        # Ejemplo de consulta
        console.print("\n[bold]Ejemplo de consulta:[/bold]")

        case = ClinicalCase(
            histologia="Adenocarcinoma de próstata",
            tnm="T2bN0M0",
            psa=15.5,
            gleason="4+3=7",
            age=68,
        )

        response = engine.query(case)

        console.print(Panel(
            format_response_for_display(response),
            title="[bold green]Resultado[/bold green]",
            border_style="green"
        ))

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error inesperado: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
