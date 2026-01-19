"""
OncoRAD FastAPI Server

API server for clinical reasoning and treatment recommendations.
Designed to interface with iOS mobile applications.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from oncorad.config import settings
from oncorad.models import (
    PatientData, ClinicalResponse, ConsultationRequest, ConsultationResponse,
    SourceDocument, SystemStatus, TumorType
)
from oncorad.vector_store import ClinicalVectorStore, DocumentProcessor
from oncorad.query_engine import ClinicalReasoningEngine


# =============================================================================
# Application Setup
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## OncoRAD - Motor de Razonamiento Clínico para Oncología Radioterápica

    API para consultas clínicas basadas en evidencia utilizando RAG
    (Retrieval-Augmented Generation) con razonamiento Chain of Thought.

    ### Características:
    - Clasificación de riesgo automática
    - Recomendaciones basadas en guías clínicas
    - Citación obligatoria de fuentes
    - Validación contra alucinaciones
    - Respuestas estructuradas en JSON

    ### Uso con iOS:
    Esta API está diseñada para integrarse con aplicaciones móviles iOS.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware for iOS app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# =============================================================================
# Dependencies
# =============================================================================

def get_vector_store() -> ClinicalVectorStore:
    """Get or create vector store instance."""
    return ClinicalVectorStore(
        persist_directory=settings.vector_db_path,
        embedding_model=settings.embedding_model,
        use_gpu=settings.use_gpu
    )


def get_reasoning_engine(
    vector_store: ClinicalVectorStore = Depends(get_vector_store)
) -> ClinicalReasoningEngine:
    """Get reasoning engine with injected vector store."""
    return ClinicalReasoningEngine(
        vector_store=vector_store,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        api_key=settings.effective_api_key,
        validate_responses=settings.validate_responses
    )


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if required."""
    if settings.require_api_key:
        if not x_api_key or x_api_key not in settings.allowed_api_keys:
            raise HTTPException(
                status_code=401,
                detail="API key inválida o no proporcionada"
            )
    return x_api_key


# =============================================================================
# Response Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    chunks_created: int
    message: str


class SourcesResponse(BaseModel):
    total_documents: int
    total_chunks: int
    documents: List[dict]


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=settings.app_version
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=settings.app_version
    )


@app.post("/consultar", response_model=ConsultationResponse)
async def consultar(
    request: ConsultationRequest,
    engine: ClinicalReasoningEngine = Depends(get_reasoning_engine),
    _: str = Depends(verify_api_key)
):
    """
    Realizar una consulta clínica.

    Este endpoint recibe los datos del paciente y devuelve una recomendación
    terapéutica estructurada basada en la evidencia disponible.

    ### Ejemplo de uso:
    ```json
    {
      "patient_data": {
        "age": 65,
        "sex": "M",
        "tumor_type": "prostata",
        "histology": "Adenocarcinoma",
        "staging": {
          "t_stage": "T3a",
          "n_stage": "N0",
          "m_stage": "M0"
        },
        "ecog_status": 0,
        "prostate_data": {
          "psa": 15.0,
          "gleason_primary": 4,
          "gleason_secondary": 3
        }
      },
      "include_reasoning": true,
      "max_citations": 5
    }
    ```
    """
    start_time = time.time()

    try:
        # Process consultation
        response = await engine.process_consultation(
            patient=request.patient_data,
            include_reasoning=request.include_reasoning,
            max_citations=request.max_citations
        )

        processing_time = (time.time() - start_time) * 1000

        return ConsultationResponse(
            success=True,
            data=response,
            error=None,
            processing_time_ms=round(processing_time, 2)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return ConsultationResponse(
            success=False,
            data=None,
            error=str(e),
            processing_time_ms=round(processing_time, 2)
        )


@app.get("/fuentes", response_model=SourcesResponse)
async def get_fuentes(
    vector_store: ClinicalVectorStore = Depends(get_vector_store),
    _: str = Depends(verify_api_key)
):
    """
    Obtener lista de documentos cargados.

    Devuelve información sobre todos los documentos indexados
    en la base de datos vectorial.
    """
    stats = vector_store.get_stats()

    return SourcesResponse(
        total_documents=stats['total_documents'],
        total_chunks=stats['total_chunks'],
        documents=stats['documents']
    )


@app.get("/status", response_model=SystemStatus)
async def get_status(
    vector_store: ClinicalVectorStore = Depends(get_vector_store)
):
    """
    Obtener estado del sistema.

    Devuelve información sobre el estado de la base de datos
    y los tipos de tumor soportados.
    """
    stats = vector_store.get_stats()

    return SystemStatus(
        status="operational",
        total_documents=stats['total_documents'],
        total_chunks=stats['total_chunks'],
        vector_db_status="connected" if stats['total_chunks'] >= 0 else "error",
        last_index_update=datetime.now().isoformat(),
        supported_tumor_types=[t.value for t in TumorType]
    )


@app.post("/documentos/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "guideline",
    vector_store: ClinicalVectorStore = Depends(get_vector_store),
    _: str = Depends(verify_api_key)
):
    """
    Cargar un nuevo documento a la base de datos.

    Soporta archivos PDF. El documento será procesado y sus
    fragmentos serán indexados en la base de datos vectorial.

    ### Tipos de documento:
    - `guideline`: Guías de práctica clínica (NCCN, ESMO, etc.)
    - `study`: Estudios clínicos y ensayos
    - `textbook`: Libros de texto y referencias
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Solo se soportan archivos PDF"
        )

    try:
        # Save file temporarily
        upload_dir = Path(settings.documents_path)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        # Process document
        processor = DocumentProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )

        chunks = processor.process_pdf(str(file_path))

        # Add to vector store
        chunks_added = vector_store.add_document_chunks(
            chunks=chunks,
            document_type=document_type
        )

        return DocumentUploadResponse(
            success=True,
            filename=file.filename,
            chunks_created=chunks_added,
            message=f"Documento procesado exitosamente: {chunks_added} fragmentos indexados"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando documento: {str(e)}"
        )


@app.delete("/documentos/{filename}")
async def delete_document(
    filename: str,
    vector_store: ClinicalVectorStore = Depends(get_vector_store),
    _: str = Depends(verify_api_key)
):
    """
    Eliminar un documento de la base de datos.

    Elimina todos los fragmentos asociados al documento especificado.
    """
    deleted_count = vector_store.delete_document(filename)

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Documento '{filename}' no encontrado"
        )

    return {
        "success": True,
        "filename": filename,
        "chunks_deleted": deleted_count,
        "message": f"Documento eliminado: {deleted_count} fragmentos removidos"
    }


@app.get("/tipos-tumor")
async def get_tumor_types():
    """
    Obtener lista de tipos de tumor soportados.

    Útil para validación en el cliente iOS.
    """
    return {
        "tumor_types": [
            {"value": t.value, "name": t.name}
            for t in TumorType
        ]
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Error interno del servidor",
            "detail": str(exc) if settings.debug else None
        }
    )


# =============================================================================
# Startup/Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    # Ensure directories exist
    Path(settings.vector_db_path).mkdir(parents=True, exist_ok=True)
    Path(settings.documents_path).mkdir(parents=True, exist_ok=True)

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    OncoRAD API Server                        ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Version: {settings.app_version:<50} ║
    ║  LLM Provider: {settings.llm_provider:<45} ║
    ║  Vector DB: {settings.vector_db_path:<48} ║
    ║  Docs: http://{settings.api_host}:{settings.api_port}/docs{' ' * 35}║
    ╚══════════════════════════════════════════════════════════════╝
    """)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("Shutting down OncoRAD API Server...")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
