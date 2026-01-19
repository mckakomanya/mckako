# OncoRad iOS - Aplicación de Soporte a Decisiones Clínicas en Oncología Radioterápica

## Descripción

OncoRad iOS es una aplicación nativa de iOS que sirve como interfaz para el motor de IA de soporte a decisiones clínicas en oncología radioterápica. La app prioriza la rapidez de entrada de datos (minimizando el uso del teclado) y la claridad en la presentación de la evidencia clínica.

## Requisitos

- iOS 17.0+
- Xcode 15.0+
- Swift 5.9+
- API Backend ejecutándose en `http://localhost:8000`

## Arquitectura

La aplicación sigue el patrón **MVVM (Model-View-ViewModel)**:

```
OncoRadApp/
├── Models/              # Modelos de datos (Codable)
│   ├── Enums.swift              # Enumeraciones (TumorType, TNM, etc.)
│   ├── ClinicalCase.swift       # Datos de entrada del paciente
│   └── TreatmentResponse.swift  # Respuesta con recomendaciones
├── ViewModels/          # Lógica de negocio y estado
│   └── TreatmentViewModel.swift
├── Views/               # Vistas SwiftUI
│   ├── ContentView.swift        # Vista principal con navegación
│   ├── ClinicalInputView.swift  # Formulario de entrada
│   ├── ProcessingView.swift     # Estado de carga animado
│   ├── ResultView.swift         # Resultados y recomendaciones
│   └── SourceView.swift         # Modal de citas bibliográficas
├── Services/            # Servicios de red
│   └── OncoAPIService.swift     # Cliente HTTP async/await
└── Utilities/           # Utilidades y temas
    └── Theme.swift              # Colores y estilos
```

## Características

### Entrada de Datos Clínicos
- **Selector de Patología**: Próstata, Mama, Pulmón, y más
- **Estadificación TNM**: Pickers visuales (sin texto libre)
- **Datos Específicos por Tumor**:
  - Próstata: PSA, Gleason Score, ISUP Grade
  - Mama: ER/PR/HER2, Ki-67, Subtipo Molecular
  - Pulmón: EGFR, ALK, PD-L1
- **Factores de Riesgo**: Toggles intuitivos
- **Estado Funcional**: ECOG Performance Status

### Procesamiento
- Animación de fases que muestra el progreso:
  1. Conectando con el servidor
  2. Consultando Guías NCCN
  3. Analizando estratificación de riesgo
  4. Recuperando evidencia clínica
  5. Sintetizando recomendación
  6. Validando contra alucinaciones

### Resultados ("The Dynamic Book")
- **Tarjeta Principal**: Recomendación de tratamiento clara
- **Detalles de Radioterapia**: Técnica, dosis, fraccionamiento, restricciones OAR
- **Terapia Sistémica**: Régimen, duración, timing
- **Outcomes Esperados**: Supervivencia, control local, toxicidad
- **Razonamiento Clínico**: Pasos del proceso de decisión
- **Referencias Bibliográficas**: Citas con texto original del PDF fuente

## Instalación

### Opción 1: Xcode Project
1. Abre Xcode
2. File > New > Project > iOS App
3. Copia los archivos de `OncoRadApp/` al proyecto
4. Compila y ejecuta

### Opción 2: Swift Package Manager
```bash
cd OncoRadiOS
swift build
```

## Configuración

### URL del Backend
Por defecto, la app se conecta a `http://localhost:8000`. Para cambiar la URL:

```swift
// En OncoAPIService.swift
OncoAPIService.shared.updateBaseURL("https://tu-servidor.com")
```

### Para desarrollo local
Asegúrate de que el backend de Python esté ejecutándose:

```bash
cd /path/to/mckako
uvicorn main:app --reload
```

## Uso

1. **Selecciona la Patología** (ej. Próstata)
2. **Ingresa los Datos del Paciente**:
   - Edad y sexo
   - Estadificación TNM (T3a N0 M0)
   - Datos específicos (PSA, Gleason)
3. **Revisa el Resumen** del caso y nivel de riesgo estimado
4. **Toca "Generar Conducta Terapéutica"**
5. **Revisa los Resultados**:
   - Recomendación principal
   - Detalles del tratamiento
   - Evidencia y referencias

## Diseño Visual

### Paleta de Colores
- **Azul Clínico**: `#007AFF` - Acciones principales
- **Verde**: Riesgo bajo
- **Naranja**: Riesgo intermedio
- **Rojo**: Riesgo alto/metastásico

### Tipografía
- San Francisco (System Font)
- Diseño "Medical Grade" priorizando legibilidad

## API Endpoints Consumidos

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/consultar` | POST | Consulta de tratamiento |
| `/health` | GET | Estado del servidor |
| `/status` | GET | Estado del sistema |
| `/tipos-tumor` | GET | Tipos de tumor soportados |

## Modelos de Datos

### Request (ConsultationRequest)
```json
{
  "patient_data": {
    "age": 65,
    "sex": "M",
    "tumor_type": "prostata",
    "staging": { "t_stage": "T3a", "n_stage": "N0", "m_stage": "M0" },
    "prostate_data": { "psa": 15.0, "gleason_primary": 4, "gleason_secondary": 3 }
  },
  "include_reasoning": true,
  "max_citations": 5
}
```

### Response (ClinicalResponse)
```json
{
  "risk_classification": "alto",
  "primary_recommendation": "EBRT 78Gy + ADT 24 meses",
  "radiotherapy": { "technique": "VMAT", "total_dose_gy": 78.0, "fractions": 39 },
  "citations": [{ "document": "NCCN_Prostate.pdf", "original_text": "..." }]
}
```

## Licencia

Proyecto desarrollado para uso clínico institucional.

---

**OncoRad iOS** - Fase 3 del Sistema de Soporte a Decisiones Clínicas en Oncología Radioterápica
