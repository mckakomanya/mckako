# OncoRad AI - Sistema RAG para Oncología Radioterápica

Sistema de Retrieval-Augmented Generation (RAG) especializado en oncología radioterápica que proporciona recomendaciones de tratamiento basadas en guías de práctica clínica con citas exactas y verificación de fuentes.

## Características

- **Ingesta Inteligente de PDFs**: Procesa guías clínicas (NCCN, ESTRO, etc.) extrayendo texto con metadatos de página
- **Búsqueda Semántica**: Encuentra información relevante usando embeddings de alta dimensionalidad
- **Citas Verificables**: Cada recomendación incluye el documento fuente y número de página exacto
- **Validación Anti-Alucinación**: Sistema de auto-corrección que verifica que las respuestas estén respaldadas por las fuentes
- **Soporte Multi-Cáncer**: Próstata, mama, pulmón, cabeza y cuello, colorrectal, y más

## Requisitos

- Python 3.11+
- API Key de OpenAI

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/mckakomanya/mckako.git
cd mckako

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# O instalar como paquete
pip install -e .

# Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu OPENAI_API_KEY
```

## Uso

### 1. Ingestar Documentos

Coloca los PDFs de las guías clínicas en la carpeta `/data`:

```bash
# Procesar todos los PDFs en /data
oncorad ingest

# O especificar un directorio
oncorad ingest --dir /ruta/a/mis/pdfs

# Especificar tipo de cáncer
oncorad ingest --cancer-type prostate
```

### 2. Realizar Consultas

#### Consulta Estructurada

```bash
oncorad query \
  --histologia "Adenocarcinoma de próstata" \
  --tnm "T2bN0M0" \
  --psa 15.5 \
  --gleason "4+3=7" \
  --age 68
```

#### Consulta en Texto Libre

```bash
oncorad ask "¿Cuál es la dosis de radioterapia recomendada para cáncer de próstata T2N0M0?"
```

#### Modo Interactivo

```bash
oncorad interactive
```

### 3. Ver Estadísticas

```bash
oncorad stats
```

## Estructura del Proyecto

```
mckako/
├── data/                    # PDFs de guías clínicas
├── chroma_db/              # Base de datos vectorial
├── src/oncorad_rag/
│   ├── __init__.py
│   ├── config.py           # Configuración del sistema
│   ├── ingest.py           # Ingesta de documentos
│   ├── query_engine.py     # Motor de consultas RAG
│   ├── validator.py        # Validación y auto-corrección
│   └── main.py             # CLI principal
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Uso Programático

```python
from oncorad_rag import DocumentIngester, OncoRadQueryEngine
from oncorad_rag.query_engine import ClinicalCase
from oncorad_rag.validator import validate_query_response

# Ingestar documentos
ingester = DocumentIngester()
ingester.ingest_directory()

# Crear motor de consultas
engine = OncoRadQueryEngine()

# Definir caso clínico
case = ClinicalCase(
    histologia="Adenocarcinoma de próstata",
    tnm="T2bN0M0",
    psa=15.5,
    gleason="4+3=7",
    age=68,
)

# Ejecutar consulta
response = engine.query(case)

# Validar respuesta
validated = validate_query_response(response)

# Acceder a resultados
print(validated.response)
print(validated.source_nodes)  # Fuentes citadas
print(validated.to_json())     # Formato JSON
```

## Formato de Respuesta

El sistema devuelve respuestas estructuradas con:

```json
{
  "response": "Recomendación de tratamiento...",
  "source_nodes": [
    {
      "text": "Texto original del PDF",
      "source_file": "NCCN_Prostate_2024.pdf",
      "page_number": 42,
      "guideline_version": "2024.1",
      "cancer_type": "prostate",
      "similarity_score": 0.92
    }
  ],
  "is_validated": true,
  "validation_notes": "Respuesta validada con 95% de confianza"
}
```

## Seguridad y Fiabilidad

El sistema implementa múltiples capas de seguridad:

1. **Citations Enforcement**: Todas las respuestas incluyen fuentes verificables
2. **Refinement Loop**: Auto-corrección antes de mostrar respuestas
3. **Threshold de Similitud**: Solo usa fragmentos con alta relevancia
4. **Declaración de Incertidumbre**: Si no hay evidencia suficiente, lo declara explícitamente

## Tipos de Cáncer Soportados

- Próstata
- Mama
- Pulmón
- Cabeza y Cuello
- Colorrectal
- Cervical
- Esofágico
- Cerebro
- Linfoma

## Contribuir

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir cambios mayores.

## Licencia

MIT License
