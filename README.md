# OncoRAD - Motor de Razonamiento Clínico para Oncología Radioterápica

Sistema RAG (Retrieval-Augmented Generation) con razonamiento Chain of Thought para generar recomendaciones terapéuticas basadas en evidencia en oncología radioterápica.

## Características

- **Clasificación de Riesgo Automática**: Clasifica pacientes según criterios NCCN/ESMO
- **Chain of Thought**: Razonamiento estructurado paso a paso
- **Citación Obligatoria**: Todas las recomendaciones incluyen citas de fuentes
- **Validación Anti-Alucinación**: Verifica que las respuestas estén respaldadas por evidencia
- **API REST**: Diseñada para integración con aplicaciones iOS
- **Soporte Multilingüe**: Español e inglés

## Estructura del Proyecto

```
mckako/
├── main.py                    # Servidor FastAPI
├── requirements.txt           # Dependencias Python
├── .env.example              # Plantilla de configuración
│
├── src/
│   └── oncorad/
│       ├── __init__.py
│       ├── models.py          # Esquemas Pydantic
│       ├── config.py          # Configuración centralizada
│       ├── vector_store.py    # Base de datos vectorial (ChromaDB)
│       ├── prompt_generator.py # Generador de prompts dinámicos
│       ├── query_engine.py    # Motor de razonamiento (CoT)
│       └── hallucination_checker.py # Validación de respuestas
│
├── examples/
│   └── example_consultation.py # Script de ejemplo
│
├── data/
│   ├── documents/            # PDFs de guías clínicas
│   └── vector_db/            # Base de datos vectorial
│
└── tests/                    # Tests unitarios
```

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd mckako
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu API key de Anthropic u OpenAI
```

## Uso

### Iniciar el servidor API

```bash
python main.py
```

El servidor estará disponible en `http://localhost:8000`

- Documentación Swagger: `http://localhost:8000/docs`
- Documentación ReDoc: `http://localhost:8000/redoc`

### Cargar documentos

Para que el sistema funcione, necesitas cargar guías clínicas (PDFs):

```bash
# Via API
curl -X POST "http://localhost:8000/documentos/upload" \
  -F "file=@NCCN_Prostata.pdf" \
  -F "document_type=guideline"
```

### Realizar una consulta

```bash
curl -X POST "http://localhost:8000/consultar" \
  -H "Content-Type: application/json" \
  -d '{
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
    }
  }'
```

## Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Estado del servidor |
| POST | `/consultar` | Realizar consulta clínica |
| GET | `/fuentes` | Listar documentos cargados |
| GET | `/status` | Estado del sistema |
| POST | `/documentos/upload` | Cargar nuevo documento |
| DELETE | `/documentos/{filename}` | Eliminar documento |
| GET | `/tipos-tumor` | Listar tipos de tumor soportados |

## Estructura de Respuesta JSON

```json
{
  "success": true,
  "data": {
    "query_id": "abc12345",
    "timestamp": "2024-01-15T10:30:00",
    "risk_classification": "alto",
    "risk_justification": "...",
    "primary_recommendation": "Radioterapia Externa + ADT 24 meses",
    "recommendation_summary": "VMAT 78 Gy/39 fx + ADT 24 meses",
    "radiotherapy": {
      "technique": "VMAT",
      "total_dose_gy": 78.0,
      "fractions": 39,
      "dose_per_fraction": 2.0
    },
    "systemic_therapy": [...],
    "expected_outcomes": {
      "overall_survival": "85% a 5 años",
      "local_control": "90%"
    },
    "citations": [
      {
        "document": "NCCN_Prostata_v3.pdf",
        "page": 45,
        "original_text": "..."
      }
    ],
    "confidence_score": 0.92,
    "evidence_level": "Nivel I",
    "hallucination_check_passed": true
  },
  "processing_time_ms": 2340.5
}
```

## Tipos de Tumor Soportados

- Próstata
- Mama
- Pulmón
- Cabeza y Cuello
- Colorrectal
- Cérvix
- Endometrio
- Vejiga
- Esófago
- Cerebro
- Linfoma

## Configuración

Variables de entorno principales en `.env`:

```env
# LLM
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-...

# Vector DB
VECTOR_DB_PATH=./data/vector_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# API
API_PORT=8000
DEBUG=false
```

## Arquitectura del Sistema

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   iOS App       │────▶│   FastAPI        │────▶│  Query Engine   │
│   (Cliente)     │     │   Server         │     │  (CoT Reasoning)│
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │  Prompt          │◀─────────────┤
                        │  Generator       │              │
                        └──────────────────┘              │
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│  ChromaDB       │◀────│  Vector Store    │◀─────────────┤
│  (Embeddings)   │     │  Search          │              │
└─────────────────┘     └──────────────────┘              │
                                                          │
                        ┌──────────────────┐              │
                        │  Hallucination   │◀─────────────┘
                        │  Checker         │
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Claude/GPT-4    │
                        │  (LLM)           │
                        └──────────────────┘
```

## Flujo de Razonamiento (Chain of Thought)

1. **Clasificación de Riesgo**: Determina el grupo de riesgo del paciente
2. **Recuperación Selectiva**: Busca evidencia relevante por secciones
3. **Generación de Prompt**: Construye prompt estructurado con contexto
4. **Razonamiento LLM**: Proceso paso a paso (verificación, identificación, síntesis)
5. **Validación**: Verifica respuesta contra fuentes
6. **Estructuración**: Formatea respuesta JSON con citas

## Desarrollo

### Ejecutar tests

```bash
pytest tests/
```

### Ejecutar ejemplo

```bash
python examples/example_consultation.py
```

## Licencia

MIT License

## Contribuir

1. Fork el repositorio
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request
