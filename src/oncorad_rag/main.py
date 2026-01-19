"""
OncoRad AI - Interfaz de Línea de Comandos

CLI principal para el sistema RAG de oncología radioterápica.
Permite ingestar documentos, realizar consultas y validar respuestas.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import SUPPORTED_CANCER_TYPES, get_settings
from .ingest import DocumentIngester
from .query_engine import ClinicalCase, OncoRadQueryEngine, format_response_for_display
from .validator import validate_query_response

app = typer.Typer(
    name="oncorad",
    help="OncoRad AI - Sistema RAG para Oncología Radioterápica",
    add_completion=False,
)
console = Console()


@app.command()
def ingest(
    directory: Optional[Path] = typer.Option(
        None,
        "--dir", "-d",
        help="Directorio con los PDFs a procesar (default: ./data)",
    ),
    cancer_type: Optional[str] = typer.Option(
        None,
        "--cancer-type", "-c",
        help=f"Tipo de cáncer: {', '.join(SUPPORTED_CANCER_TYPES)}",
    ),
    clear: bool = typer.Option(
        False,
        "--clear",
        help="Limpiar la base de datos antes de ingestar",
    ),
):
    """
    Ingesta PDFs de guías clínicas en la base de datos vectorial.

    Procesa todos los archivos PDF en el directorio especificado,
    extrae el texto con metadatos y crea embeddings para búsqueda semántica.
    """
    console.print(Panel(
        "[bold blue]OncoRad AI - Sistema de Ingesta de Documentos[/bold blue]",
        border_style="blue",
    ))

    try:
        ingester = DocumentIngester()

        if clear:
            if Confirm.ask("¿Seguro que deseas eliminar todos los documentos?"):
                ingester.clear_collection()
                console.print("[yellow]Base de datos limpiada.[/yellow]")

        target_dir = directory or ingester.settings.data_dir

        if not target_dir.exists():
            console.print(f"[red]Error: El directorio {target_dir} no existe.[/red]")
            raise typer.Exit(1)

        stats = ingester.ingest_directory(target_dir, cancer_type)

        # Mostrar estadísticas finales
        table = Table(title="Resumen de Ingesta")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")

        table.add_row("Archivos procesados", str(stats["files_processed"]))
        table.add_row("Fragmentos indexados", str(stats["total_nodes"]))
        table.add_row("Errores", str(len(stats.get("errors", []))))

        console.print(table)

    except ValueError as e:
        console.print(f"[red]Error de configuración: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def query(
    histologia: str = typer.Option(
        ...,
        "--histologia", "-h",
        help="Tipo histológico del tumor",
    ),
    tnm: Optional[str] = typer.Option(
        None,
        "--tnm", "-t",
        help="Clasificación TNM (ej: T2bN0M0)",
    ),
    psa: Optional[float] = typer.Option(
        None,
        "--psa", "-p",
        help="Nivel de PSA en ng/mL",
    ),
    gleason: Optional[str] = typer.Option(
        None,
        "--gleason", "-g",
        help="Score de Gleason (ej: 4+3=7)",
    ),
    age: Optional[int] = typer.Option(
        None,
        "--age", "-a",
        help="Edad del paciente",
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Validar la respuesta contra las fuentes",
    ),
    json_output: bool = typer.Option(
        False,
        "--json", "-j",
        help="Salida en formato JSON",
    ),
):
    """
    Realiza una consulta clínica al sistema RAG.

    Proporciona los parámetros del caso clínico y obtiene
    recomendaciones de tratamiento basadas en las guías indexadas.
    """
    try:
        engine = OncoRadQueryEngine()

        stats = engine.get_index_stats()
        if stats["total_documents"] == 0:
            console.print(
                "[yellow]No hay documentos indexados. "
                "Ejecuta primero: oncorad ingest[/yellow]"
            )
            raise typer.Exit(1)

        # Crear caso clínico
        clinical_case = ClinicalCase(
            histologia=histologia,
            tnm=tnm,
            psa=psa,
            gleason=gleason,
            age=age,
        )

        # Ejecutar consulta
        response = engine.query(clinical_case)

        # Validar si está habilitado
        if validate:
            response = validate_query_response(response)

        # Mostrar resultado
        if json_output:
            console.print(response.to_json())
        else:
            console.print(Panel(
                format_response_for_display(response),
                title="[bold green]Resultado OncoRad AI[/bold green]",
                border_style="green",
            ))

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def ask(
    question: str = typer.Argument(
        ...,
        help="Pregunta en texto libre",
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Validar la respuesta contra las fuentes",
    ),
):
    """
    Realiza una pregunta en texto libre al sistema.

    Útil para consultas que no siguen el formato estructurado de caso clínico.
    """
    try:
        engine = OncoRadQueryEngine()

        stats = engine.get_index_stats()
        if stats["total_documents"] == 0:
            console.print(
                "[yellow]No hay documentos indexados. "
                "Ejecuta primero: oncorad ingest[/yellow]"
            )
            raise typer.Exit(1)

        response = engine.query_text(question)

        if validate:
            response = validate_query_response(response)

        console.print(Panel(
            format_response_for_display(response),
            title="[bold green]Resultado OncoRad AI[/bold green]",
            border_style="green",
        ))

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def interactive():
    """
    Modo interactivo para consultas clínicas.

    Guía paso a paso para ingresar datos del caso clínico.
    """
    console.print(Panel(
        "[bold blue]OncoRad AI - Modo Interactivo[/bold blue]\n"
        "Ingrese los datos del caso clínico para obtener recomendaciones.",
        border_style="blue",
    ))

    try:
        engine = OncoRadQueryEngine()

        stats = engine.get_index_stats()
        console.print(f"[dim]Documentos disponibles: {stats['total_documents']}[/dim]\n")

        if stats["total_documents"] == 0:
            console.print(
                "[yellow]No hay documentos indexados. "
                "Ejecuta primero: oncorad ingest[/yellow]"
            )
            raise typer.Exit(1)

        while True:
            console.print("\n[bold]═══ Nuevo Caso Clínico ═══[/bold]")

            histologia = Prompt.ask("Histología del tumor")
            tnm = Prompt.ask("Clasificación TNM (opcional)", default="")
            psa_str = Prompt.ask("PSA en ng/mL (opcional)", default="")
            gleason = Prompt.ask("Score de Gleason (opcional)", default="")
            age_str = Prompt.ask("Edad del paciente (opcional)", default="")

            # Parsear valores opcionales
            psa = float(psa_str) if psa_str else None
            age = int(age_str) if age_str else None

            clinical_case = ClinicalCase(
                histologia=histologia,
                tnm=tnm or None,
                psa=psa,
                gleason=gleason or None,
                age=age,
            )

            console.print("\n[blue]Procesando consulta...[/blue]")

            response = engine.query(clinical_case)
            response = validate_query_response(response)

            console.print(Panel(
                format_response_for_display(response),
                title="[bold green]Resultado[/bold green]",
                border_style="green",
            ))

            if not Confirm.ask("\n¿Desea realizar otra consulta?"):
                break

        console.print("[blue]¡Gracias por usar OncoRad AI![/blue]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """
    Muestra estadísticas del sistema.

    Información sobre documentos indexados, modelos utilizados
    y configuración actual.
    """
    settings = get_settings()

    table = Table(title="Estadísticas del Sistema OncoRad AI")
    table.add_column("Configuración", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Directorio de datos", str(settings.data_dir))
    table.add_row("Base de datos ChromaDB", str(settings.chroma_db_dir))
    table.add_row("Modelo LLM", settings.llm_model)
    table.add_row("Modelo de Embeddings", settings.embedding_model)
    table.add_row("Tamaño de chunk", str(settings.chunk_size))
    table.add_row("Overlap de chunk", str(settings.chunk_overlap))
    table.add_row("Top-K de búsqueda", str(settings.similarity_top_k))

    console.print(table)

    # Intentar mostrar estadísticas de la colección
    try:
        ingester = DocumentIngester()
        collection_stats = ingester.get_collection_stats()

        table2 = Table(title="Estadísticas de la Colección")
        table2.add_column("Métrica", style="cyan")
        table2.add_column("Valor", style="green")

        table2.add_row("Nombre de colección", collection_stats["collection_name"])
        table2.add_row("Total de documentos", str(collection_stats["total_documents"]))

        console.print(table2)

    except ValueError:
        console.print("[yellow]Configure OPENAI_API_KEY para ver estadísticas completas.[/yellow]")
    except Exception as e:
        console.print(f"[yellow]No se pudieron obtener estadísticas: {e}[/yellow]")


@app.command()
def version():
    """Muestra la versión del sistema."""
    from . import __version__

    console.print(f"[bold blue]OncoRad AI[/bold blue] versión {__version__}")


def main():
    """Punto de entrada principal."""
    app()


if __name__ == "__main__":
    main()
