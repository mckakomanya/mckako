"""
OncoRAD Dynamic Prompt Generator

Generates structured clinical queries based on patient data
for the RAG system to process.
"""

from typing import List, Optional, Dict, Any
from .models import (
    PatientData, TumorType, RiskLevel, ECOGStatus,
    TStage, NStage, MStage
)


class ClinicalPromptGenerator:
    """
    Generates dynamic clinical prompts based on patient data.

    Creates structured queries for the RAG system that incorporate
    patient-specific parameters and clinical context.
    """

    # Risk classification rules by tumor type
    PROSTATE_RISK_RULES = {
        "very_low": "T1c, Gleason ≤6, PSA <10, <3 cores positivos, ≤50% afectación por core",
        "low": "T1-T2a, Gleason ≤6, PSA <10",
        "intermediate_favorable": "1 factor IR: T2b-T2c O Gleason 7 (3+4) O PSA 10-20",
        "intermediate_unfavorable": "≥2 factores IR O Gleason 7 (4+3)",
        "high": "T3a O Gleason 8-10 O PSA >20",
        "very_high": "T3b-T4 O Gleason primario 5 O >4 cores con Gleason 8-10"
    }

    def __init__(self, language: str = "es"):
        """
        Initialize the prompt generator.

        Args:
            language: Output language ('es' for Spanish, 'en' for English)
        """
        self.language = language

    def classify_prostate_risk(self, patient: PatientData) -> RiskLevel:
        """
        Classify prostate cancer risk based on NCCN criteria.

        Args:
            patient: Patient data with prostate-specific information

        Returns:
            Risk level classification
        """
        if patient.prostate_data is None:
            return RiskLevel.INTERMEDIATE_UNFAVORABLE  # Default if no data

        psa = patient.prostate_data.psa
        gleason = patient.prostate_data.gleason_score
        gleason_primary = patient.prostate_data.gleason_primary
        t_stage = patient.staging.t_stage
        m_stage = patient.staging.m_stage

        # Check for metastatic disease
        if m_stage in [MStage.M1, MStage.M1A, MStage.M1B, MStage.M1C]:
            return RiskLevel.METASTATIC

        # Very High Risk
        if t_stage in [TStage.T3B, TStage.T4, TStage.T4A, TStage.T4B]:
            return RiskLevel.VERY_HIGH
        if gleason_primary == 5:
            return RiskLevel.VERY_HIGH

        # High Risk
        if t_stage in [TStage.T3, TStage.T3A]:
            return RiskLevel.HIGH
        if gleason >= 8:
            return RiskLevel.HIGH
        if psa > 20:
            return RiskLevel.HIGH

        # Intermediate Risk factors count
        ir_factors = 0
        if t_stage in [TStage.T2B, TStage.T2C]:
            ir_factors += 1
        if gleason == 7:
            ir_factors += 1
        if 10 <= psa <= 20:
            ir_factors += 1

        if ir_factors >= 2 or (gleason == 7 and gleason_primary == 4):
            return RiskLevel.INTERMEDIATE_UNFAVORABLE
        if ir_factors == 1:
            return RiskLevel.INTERMEDIATE_FAVORABLE

        # Low Risk
        if t_stage in [TStage.T1, TStage.T1A, TStage.T1B, TStage.T1C, TStage.T2, TStage.T2A]:
            if gleason <= 6 and psa < 10:
                # Check for very low
                if (t_stage == TStage.T1C and
                    patient.prostate_data.percent_positive_cores and
                    patient.prostate_data.percent_positive_cores < 34):
                    return RiskLevel.VERY_LOW
                return RiskLevel.LOW

        return RiskLevel.INTERMEDIATE_UNFAVORABLE

    def classify_risk(self, patient: PatientData) -> RiskLevel:
        """
        Classify patient risk based on tumor type and parameters.

        Args:
            patient: Complete patient data

        Returns:
            Risk level classification
        """
        if patient.tumor_type == TumorType.PROSTATE:
            return self.classify_prostate_risk(patient)

        # Generic risk classification for other tumors
        m_stage = patient.staging.m_stage
        if m_stage in [MStage.M1, MStage.M1A, MStage.M1B, MStage.M1C]:
            return RiskLevel.METASTATIC

        t_stage = patient.staging.t_stage
        n_stage = patient.staging.n_stage

        # High risk indicators
        if t_stage in [TStage.T3, TStage.T3A, TStage.T3B, TStage.T4, TStage.T4A, TStage.T4B]:
            return RiskLevel.HIGH
        if n_stage in [NStage.N2, NStage.N2A, NStage.N2B, NStage.N2C, NStage.N3, NStage.N3A, NStage.N3B]:
            return RiskLevel.HIGH

        # Intermediate
        if n_stage == NStage.N1:
            return RiskLevel.INTERMEDIATE_UNFAVORABLE
        if t_stage in [TStage.T2B, TStage.T2C]:
            return RiskLevel.INTERMEDIATE_FAVORABLE

        # Low risk
        return RiskLevel.LOW

    def generate_clinical_summary(self, patient: PatientData) -> str:
        """
        Generate a clinical summary paragraph for the patient.

        Args:
            patient: Patient data

        Returns:
            Formatted clinical summary string
        """
        parts = []

        # Basic demographics
        sex_str = "masculino" if patient.sex == "M" else "femenino"
        parts.append(f"Paciente {sex_str} de {patient.age} años")

        # Diagnosis
        tumor_names = {
            TumorType.PROSTATE: "Adenocarcinoma de Próstata",
            TumorType.BREAST: "Carcinoma de Mama",
            TumorType.LUNG: "Carcinoma de Pulmón",
            TumorType.HEAD_NECK: "Carcinoma de Cabeza y Cuello",
            TumorType.COLORECTAL: "Carcinoma Colorrectal",
            TumorType.CERVIX: "Carcinoma de Cérvix",
            TumorType.ENDOMETRIUM: "Carcinoma de Endometrio",
            TumorType.BLADDER: "Carcinoma de Vejiga",
            TumorType.ESOPHAGUS: "Carcinoma de Esófago",
            TumorType.BRAIN: "Tumor Cerebral",
            TumorType.LYMPHOMA: "Linfoma",
        }
        tumor_name = tumor_names.get(patient.tumor_type, patient.histology)
        parts.append(f"con diagnóstico de {tumor_name}")

        # Histology if different
        if patient.histology and patient.histology.lower() not in tumor_name.lower():
            parts.append(f"({patient.histology})")

        # Staging
        parts.append(f"estadio {patient.staging.tnm_string}")

        # Prostate specific
        if patient.tumor_type == TumorType.PROSTATE and patient.prostate_data:
            pd = patient.prostate_data
            parts.append(f"PSA {pd.psa} ng/mL")
            parts.append(f"Gleason {pd.gleason_score} ({pd.gleason_primary}+{pd.gleason_secondary})")
            parts.append(f"Grupo ISUP {pd.isup_grade}")

        # Breast specific
        if patient.tumor_type == TumorType.BREAST and patient.breast_data:
            bd = patient.breast_data
            parts.append(f"subtipo molecular {bd.molecular_subtype}")

        # Performance status
        ecog_descriptions = {
            ECOGStatus.FULLY_ACTIVE: "ECOG 0 (asintomático)",
            ECOGStatus.RESTRICTED_STRENUOUS: "ECOG 1 (sintomático ambulatorio)",
            ECOGStatus.AMBULATORY_SELFCARE: "ECOG 2 (en cama <50% del día)",
            ECOGStatus.LIMITED_SELFCARE: "ECOG 3 (en cama >50% del día)",
            ECOGStatus.COMPLETELY_DISABLED: "ECOG 4 (encamado)",
        }
        ecog_desc = ecog_descriptions.get(patient.ecog_status, f"ECOG {patient.ecog_status.value}")
        parts.append(ecog_desc)

        return ", ".join(parts) + "."

    def generate_search_queries(
        self,
        patient: PatientData,
        risk_level: RiskLevel
    ) -> List[str]:
        """
        Generate multiple search queries for comprehensive retrieval.

        Args:
            patient: Patient data
            risk_level: Calculated risk level

        Returns:
            List of search queries
        """
        tumor_name = patient.tumor_type.value
        risk_name = risk_level.value

        queries = []

        # Main treatment query
        queries.append(
            f"{tumor_name} {patient.staging.tnm_string} "
            f"tratamiento radioterapia recomendación"
        )

        # Risk-specific query
        queries.append(
            f"{tumor_name} riesgo {risk_name} protocolo tratamiento"
        )

        # Fractionation query
        queries.append(
            f"{tumor_name} fraccionamiento dosis esquema radioterapia"
        )

        # Outcomes query
        queries.append(
            f"{tumor_name} sobrevida control local resultados outcomes"
        )

        # Prostate specific queries
        if patient.tumor_type == TumorType.PROSTATE and patient.prostate_data:
            psa = patient.prostate_data.psa
            gleason = patient.prostate_data.gleason_score

            queries.append(
                f"próstata PSA {psa} Gleason {gleason} radioterapia"
            )
            queries.append(
                f"próstata hormonoterapia ADT duración riesgo {risk_name}"
            )

        # Combined modality query
        queries.append(
            f"{tumor_name} radioterapia quimioterapia combinación"
        )

        return queries

    def generate_rag_prompt(
        self,
        patient: PatientData,
        risk_level: RiskLevel,
        retrieved_context: str
    ) -> str:
        """
        Generate the final prompt for the LLM with retrieved context.

        Args:
            patient: Patient data
            risk_level: Calculated risk level
            retrieved_context: Context retrieved from vector store

        Returns:
            Complete prompt for LLM
        """
        clinical_summary = self.generate_clinical_summary(patient)

        # Risk level descriptions
        risk_descriptions = {
            RiskLevel.VERY_LOW: "muy bajo",
            RiskLevel.LOW: "bajo",
            RiskLevel.INTERMEDIATE_FAVORABLE: "intermedio favorable",
            RiskLevel.INTERMEDIATE_UNFAVORABLE: "intermedio desfavorable",
            RiskLevel.HIGH: "alto",
            RiskLevel.VERY_HIGH: "muy alto",
            RiskLevel.METASTATIC: "metastásico"
        }
        risk_desc = risk_descriptions.get(risk_level, str(risk_level.value))

        custom_question = patient.clinical_question or ""

        prompt = f"""Eres un oncólogo radioterapeuta experto. Analiza el siguiente caso clínico y proporciona una recomendación terapéutica basada ÚNICAMENTE en la evidencia proporcionada.

## CASO CLÍNICO
{clinical_summary}

## CLASIFICACIÓN DE RIESGO
Riesgo calculado: {risk_desc}

## EVIDENCIA DISPONIBLE (Documentos recuperados)
{retrieved_context}

## INSTRUCCIONES
Basándote EXCLUSIVAMENTE en los fragmentos de evidencia proporcionados arriba:

1. **Confirma o ajusta** la clasificación de riesgo del paciente
2. **Recomienda** el esquema de tratamiento más apropiado, incluyendo:
   - Técnica de radioterapia (IMRT, VMAT, SBRT, etc.)
   - Dosis total y fraccionamiento
   - Terapia sistémica si corresponde (tipo, duración, timing)
3. **Extrae** los datos de sobrevida y control local de la evidencia
4. **Cita** obligatoriamente cada afirmación con el formato: [Fuente: Nombre_Archivo, Pág. X]

{f"Pregunta específica del usuario: {custom_question}" if custom_question else ""}

## FORMATO DE RESPUESTA
Estructura tu respuesta de la siguiente manera:

### Clasificación de Riesgo
[Tu análisis de riesgo con justificación citada]

### Recomendación Principal
[Tratamiento recomendado con citas]

### Esquema de Radioterapia
- Técnica:
- Dosis total:
- Fraccionamiento:
- Volúmenes:

### Terapia Sistémica (si aplica)
- Tipo:
- Duración:
- Timing:

### Outcomes Esperados
- Sobrevida global: [dato con cita]
- Sobrevida libre de progresión: [dato con cita]
- Control local: [dato con cita]

### Advertencias y Consideraciones
[Cualquier precaución relevante]

IMPORTANTE: Si la información solicitada NO está disponible en los fragmentos proporcionados, indica explícitamente "No disponible en la evidencia consultada" en lugar de inventar datos."""

        return prompt

    def generate_chain_of_thought_prompt(
        self,
        patient: PatientData,
        risk_level: RiskLevel,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a Chain of Thought prompt for structured reasoning.

        Args:
            patient: Patient data
            risk_level: Calculated risk level
            retrieved_chunks: Retrieved document chunks with metadata

        Returns:
            CoT prompt for LLM
        """
        clinical_summary = self.generate_clinical_summary(patient)

        # Format retrieved chunks with clear citations
        formatted_chunks = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            doc = chunk.get('document_name', 'Desconocido')
            page = chunk.get('page_number', '?')
            text = chunk.get('text', '')
            score = chunk.get('relevance_score', 0)

            formatted_chunks.append(
                f"[Fragmento {i}] Fuente: {doc}, Pág. {page} (Relevancia: {score:.2f})\n"
                f"{text}\n"
            )

        context = "\n---\n".join(formatted_chunks)

        prompt = f"""Eres un oncólogo radioterapeuta experto. Sigue estos pasos de razonamiento para analizar el caso y generar una recomendación.

## CASO CLÍNICO
{clinical_summary}

## CLASIFICACIÓN INICIAL
Riesgo preliminar: {risk_level.value}

## DOCUMENTOS DE REFERENCIA
{context}

---

## PROCESO DE RAZONAMIENTO (Chain of Thought)

### PASO 1: Verificación de Clasificación
Primero, verifica si la clasificación de riesgo "{risk_level.value}" es correcta según los criterios encontrados en los documentos.
- ¿Qué criterios de clasificación mencionan los documentos?
- ¿El paciente cumple estos criterios?
- Conclusión sobre el riesgo con cita: [Fuente: X, Pág. Y]

### PASO 2: Identificación del Tratamiento Estándar
Según los documentos, ¿cuál es el tratamiento estándar para este grupo de riesgo?
- Identifica las opciones de tratamiento mencionadas
- Señala cuál es la recomendación principal
- Incluye cita obligatoria: [Fuente: X, Pág. Y]

### PASO 3: Especificaciones de Radioterapia
Extrae de los documentos los parámetros de radioterapia:
- Técnica recomendada
- Dosis y fraccionamiento
- Volúmenes objetivo
- Cita: [Fuente: X, Pág. Y]

### PASO 4: Terapia Sistémica
Si aplica, extrae información sobre terapia sistémica:
- Tipo (quimioterapia, hormonoterapia, inmunoterapia)
- Duración
- Timing respecto a la radioterapia
- Cita: [Fuente: X, Pág. Y]

### PASO 5: Extracción de Outcomes
Busca en los fragmentos datos específicos de:
- Sobrevida global (especifica % y tiempo)
- Sobrevida libre de progresión
- Control local
- Cada dato debe tener cita: [Fuente: X, Pág. Y]

### PASO 6: Síntesis Final
Combina toda la información en una recomendación coherente.

REGLAS CRÍTICAS:
1. SOLO usa información que aparece explícitamente en los fragmentos
2. Si un dato no está en los fragmentos, escribe "No disponible en la evidencia"
3. Cada afirmación clínica DEBE tener una cita
4. No inventes nombres de estudios, autores o estadísticas"""

        return prompt

    def generate_validation_prompt(
        self,
        response_text: str,
        source_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a prompt to validate the response against sources.

        Args:
            response_text: The generated response to validate
            source_chunks: Original source chunks used

        Returns:
            Validation prompt
        """
        chunks_text = "\n\n".join([
            f"[{c.get('document_name', 'Doc')}, Pág. {c.get('page_number', '?')}]: {c.get('text', '')}"
            for c in source_chunks
        ])

        return f"""Verifica la siguiente respuesta clínica contra los documentos fuente.

## RESPUESTA A VERIFICAR
{response_text}

## DOCUMENTOS FUENTE
{chunks_text}

## INSTRUCCIONES DE VERIFICACIÓN
Para cada afirmación en la respuesta:
1. ¿Está respaldada por los documentos fuente? (Sí/No)
2. Si menciona un estudio, autor o estadística, ¿aparece en los documentos?
3. ¿Las citas son correctas?

Responde con un JSON:
{{
  "verificado": true/false,
  "afirmaciones_verificadas": [...],
  "afirmaciones_no_verificadas": [...],
  "posibles_alucinaciones": [...],
  "citas_incorrectas": [...]
}}"""
