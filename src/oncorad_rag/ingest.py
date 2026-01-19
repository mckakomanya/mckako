"""
Módulo de Ingesta de Documentos - OncoRad AI

Este módulo procesa PDFs de guías clínicas, extrae el texto con metadatos
(incluyendo números de página), y los almacena en ChromaDB con embeddings.
"""

import re
from pathlib import Path
from typing import Optional

import chromadb
import fitz  # PyMuPDF
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import SUPPORTED_CANCER_TYPES, Settings, get_settings

console = Console()


class DocumentIngester:
    """
    Procesador de documentos PDF para el sistema RAG de oncología.

    Extrae texto de PDFs manteniendo metadatos críticos como número de página,
    fuente, versión de la guía y tipo de cáncer para citación precisa.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa el ingester con la configuración proporcionada.

        Args:
            settings: Configuración del sistema. Si es None, usa la configuración por defecto.
        """
        self.settings = settings or get_settings()
        self._validate_api_key()
        self._init_embedding_model()
        self._init_vector_store()
        self._init_node_parser()

    def _validate_api_key(self) -> None:
        """Valida que la API key de OpenAI esté configurada."""
        if not self.settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY no está configurada. "
                "Configúrala en el archivo .env o como variable de entorno."
            )

    def _init_embedding_model(self) -> None:
        """Inicializa el modelo de embeddings de OpenAI."""
        self.embed_model = OpenAIEmbedding(
            model=self.settings.embedding_model,
            api_key=self.settings.openai_api_key,
        )

    def _init_vector_store(self) -> None:
        """Inicializa ChromaDB como almacén vectorial."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.settings.chroma_db_dir)
        )

        # Obtener o crear la colección
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        self.vector_store = ChromaVectorStore(
            chroma_collection=self.chroma_collection
        )

        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

    def _init_node_parser(self) -> None:
        """Inicializa el parser de nodos con configuración de chunking."""
        self.node_parser = SentenceSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )

    def extract_text_from_pdf(self, pdf_path: Path) -> list[dict]:
        """
        Extrae texto de un PDF preservando información de página.

        Args:
            pdf_path: Ruta al archivo PDF.

        Returns:
            Lista de diccionarios con 'text' y 'page_number' por cada página.
        """
        pages_content = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")

                # Limpiar el texto
                text = self._clean_text(text)

                if text.strip():
                    pages_content.append({
                        "text": text,
                        "page_number": page_num + 1  # Páginas empiezan en 1
                    })

            doc.close()

        except Exception as e:
            console.print(f"[red]Error procesando {pdf_path}: {e}[/red]")
            raise

        return pages_content

    def _clean_text(self, text: str) -> str:
        """
        Limpia el texto extraído del PDF.

        Args:
            text: Texto crudo del PDF.

        Returns:
            Texto limpio y normalizado.
        """
        # Eliminar múltiples espacios en blanco
        text = re.sub(r'\s+', ' ', text)
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # Normalizar guiones
        text = text.replace('—', '-').replace('–', '-')

        return text.strip()

    def detect_cancer_type(self, text: str, filename: str) -> str:
        """
        Detecta el tipo de cáncer basándose en el contenido y nombre del archivo.

        Args:
            text: Texto del documento.
            filename: Nombre del archivo.

        Returns:
            Tipo de cáncer detectado.
        """
        combined = (text + " " + filename).lower()

        cancer_keywords = {
            "prostate": ["prostate", "próstata", "psa", "gleason"],
            "breast": ["breast", "mama", "mamario", "her2"],
            "lung": ["lung", "pulmón", "pulmonar", "nsclc", "sclc"],
            "head_neck": ["head", "neck", "cabeza", "cuello", "orofaringe"],
            "colorectal": ["colorectal", "colon", "rectal", "recto"],
            "cervical": ["cervical", "cérvix", "uterino"],
            "esophageal": ["esophag", "esófago"],
            "brain": ["brain", "cerebro", "glioma", "glioblastoma"],
            "lymphoma": ["lymphoma", "linfoma", "hodgkin"],
        }

        for cancer_type, keywords in cancer_keywords.items():
            if any(kw in combined for kw in keywords):
                return cancer_type

        return "other"

    def detect_guideline_version(self, text: str, filename: str) -> str:
        """
        Detecta la versión de la guía clínica.

        Args:
            text: Texto del documento.
            filename: Nombre del archivo.

        Returns:
            Versión detectada de la guía.
        """
        combined = text + " " + filename

        # Patrones comunes de versión
        patterns = [
            r'Version\s*(\d+\.?\d*)',
            r'v(\d+\.?\d*)',
            r'(\d{4})\.(\d+)',  # Año.versión como NCCN 2024.1
            r'(\d{4})',  # Solo año
        ]

        for pattern in patterns:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                return match.group(0)

        return "unknown"

    def create_nodes_with_metadata(
        self,
        pdf_path: Path,
        cancer_type: Optional[str] = None,
        guideline_version: Optional[str] = None,
    ) -> list[TextNode]:
        """
        Crea nodos de texto con metadatos completos para indexación.

        Args:
            pdf_path: Ruta al archivo PDF.
            cancer_type: Tipo de cáncer (opcional, se auto-detecta).
            guideline_version: Versión de la guía (opcional, se auto-detecta).

        Returns:
            Lista de TextNodes listos para indexar.
        """
        pages_content = self.extract_text_from_pdf(pdf_path)

        if not pages_content:
            console.print(f"[yellow]Advertencia: No se extrajo texto de {pdf_path}[/yellow]")
            return []

        # Concatenar texto para detección si no se proporcionan parámetros
        full_text = " ".join([p["text"][:500] for p in pages_content[:5]])

        detected_cancer = cancer_type or self.detect_cancer_type(full_text, pdf_path.name)
        detected_version = guideline_version or self.detect_guideline_version(full_text, pdf_path.name)

        nodes = []

        for page_data in pages_content:
            # Crear documento temporal para parsing
            doc = Document(
                text=page_data["text"],
                metadata={
                    "source_file": pdf_path.name,
                    "page_number": page_data["page_number"],
                    "guideline_version": detected_version,
                    "cancer_type": detected_cancer,
                    "file_path": str(pdf_path),
                }
            )

            # Dividir en chunks más pequeños preservando metadatos
            page_nodes = self.node_parser.get_nodes_from_documents([doc])

            # Asegurar que los metadatos se preserven en cada nodo
            for node in page_nodes:
                node.metadata.update({
                    "source_file": pdf_path.name,
                    "page_number": page_data["page_number"],
                    "guideline_version": detected_version,
                    "cancer_type": detected_cancer,
                })
                nodes.append(node)

        return nodes

    def ingest_pdf(
        self,
        pdf_path: Path,
        cancer_type: Optional[str] = None,
        guideline_version: Optional[str] = None,
    ) -> int:
        """
        Ingesta un único archivo PDF al sistema.

        Args:
            pdf_path: Ruta al archivo PDF.
            cancer_type: Tipo de cáncer (opcional).
            guideline_version: Versión de la guía (opcional).

        Returns:
            Número de nodos creados e indexados.
        """
        console.print(f"[blue]Procesando: {pdf_path.name}[/blue]")

        nodes = self.create_nodes_with_metadata(
            pdf_path, cancer_type, guideline_version
        )

        if not nodes:
            return 0

        # Crear índice con los nodos
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=self.storage_context,
            embed_model=self.embed_model,
        )

        console.print(
            f"[green]✓ Indexados {len(nodes)} fragmentos de {pdf_path.name}[/green]"
        )

        return len(nodes)

    def ingest_directory(
        self,
        directory: Optional[Path] = None,
        cancer_type: Optional[str] = None,
    ) -> dict:
        """
        Ingesta todos los PDFs de un directorio.

        Args:
            directory: Directorio a procesar. Por defecto usa data_dir.
            cancer_type: Tipo de cáncer para todos los archivos (opcional).

        Returns:
            Diccionario con estadísticas de la ingesta.
        """
        directory = directory or self.settings.data_dir

        pdf_files = list(directory.glob("*.pdf"))

        if not pdf_files:
            console.print(
                f"[yellow]No se encontraron archivos PDF en {directory}[/yellow]"
            )
            return {"files_processed": 0, "total_nodes": 0}

        console.print(f"[blue]Encontrados {len(pdf_files)} archivos PDF[/blue]")

        stats = {
            "files_processed": 0,
            "total_nodes": 0,
            "errors": [],
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Procesando PDFs...", total=len(pdf_files))

            for pdf_file in pdf_files:
                try:
                    nodes_count = self.ingest_pdf(pdf_file, cancer_type)
                    stats["files_processed"] += 1
                    stats["total_nodes"] += nodes_count
                except Exception as e:
                    stats["errors"].append({"file": pdf_file.name, "error": str(e)})
                    console.print(f"[red]Error en {pdf_file.name}: {e}[/red]")

                progress.advance(task)

        console.print("\n[bold green]═══ Resumen de Ingesta ═══[/bold green]")
        console.print(f"Archivos procesados: {stats['files_processed']}")
        console.print(f"Fragmentos indexados: {stats['total_nodes']}")

        if stats["errors"]:
            console.print(f"[red]Errores: {len(stats['errors'])}[/red]")

        return stats

    def get_collection_stats(self) -> dict:
        """
        Obtiene estadísticas de la colección de ChromaDB.

        Returns:
            Diccionario con estadísticas de la colección.
        """
        count = self.chroma_collection.count()

        return {
            "collection_name": self.settings.chroma_collection_name,
            "total_documents": count,
            "embedding_model": self.settings.embedding_model,
        }

    def clear_collection(self) -> None:
        """Elimina todos los documentos de la colección."""
        self.chroma_client.delete_collection(self.settings.chroma_collection_name)
        self._init_vector_store()
        console.print("[yellow]Colección eliminada y recreada[/yellow]")


def main():
    """Función principal para ejecutar la ingesta desde línea de comandos."""
    import sys

    console.print("[bold blue]═══ OncoRad AI - Sistema de Ingesta ═══[/bold blue]\n")

    try:
        ingester = DocumentIngester()
        stats = ingester.ingest_directory()

        if stats["total_nodes"] > 0:
            console.print("\n[bold green]Ingesta completada exitosamente.[/bold green]")
        else:
            console.print(
                "\n[yellow]No se procesaron documentos. "
                "Asegúrate de colocar PDFs en la carpeta /data[/yellow]"
            )

    except ValueError as e:
        console.print(f"[red]Error de configuración: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error inesperado: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
