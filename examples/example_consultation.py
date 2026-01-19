#!/usr/bin/env python3
"""
Example: Clinical Consultation with OncoRAD

This script demonstrates how to use the OncoRAD clinical reasoning engine
to generate treatment recommendations for oncology patients.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oncorad import (
    PatientData,
    TumorStaging,
    ClinicalReasoningEngine,
    ClinicalVectorStore,
    TumorType,
    ECOGStatus,
    TStage,
    NStage,
    MStage,
    ProstateSpecificData
)


async def main():
    """Run example consultation."""

    print("=" * 60)
    print("OncoRAD - Ejemplo de Consulta Clínica")
    print("=" * 60)

    # Create example patient data
    patient = PatientData(
        patient_id="EJEMPLO-001",
        age=65,
        sex="M",
        tumor_type=TumorType.PROSTATE,
        histology="Adenocarcinoma acinar",
        staging=TumorStaging(
            t_stage=TStage.T3A,
            n_stage=NStage.N0,
            m_stage=MStage.M0,
            clinical_stage="IIIA"
        ),
        ecog_status=ECOGStatus.FULLY_ACTIVE,
        prostate_data=ProstateSpecificData(
            psa=15.0,
            gleason_primary=4,
            gleason_secondary=3,
            percent_positive_cores=45.0
        ),
        comorbidities=["Hipertensión controlada", "Diabetes tipo 2"],
        previous_treatments=[],
        clinical_question="¿Cuál es el esquema de fraccionamiento recomendado y duración de ADT?"
    )

    print("\n📋 DATOS DEL PACIENTE:")
    print("-" * 40)
    print(f"  Edad: {patient.age} años")
    print(f"  Sexo: {patient.sex}")
    print(f"  Diagnóstico: {patient.histology}")
    print(f"  Estadio: {patient.staging.tnm_string}")
    print(f"  PSA: {patient.prostate_data.psa} ng/mL")
    print(f"  Gleason: {patient.prostate_data.gleason_score} ({patient.prostate_data.gleason_primary}+{patient.prostate_data.gleason_secondary})")
    print(f"  ISUP: Grupo {patient.prostate_data.isup_grade}")
    print(f"  ECOG: {patient.ecog_status.value}")

    # Initialize vector store
    print("\n🔄 Inicializando motor de razonamiento...")
    vector_store = ClinicalVectorStore(
        persist_directory="./data/vector_db"
    )

    # Check if there are documents loaded
    stats = vector_store.get_stats()
    print(f"  📚 Documentos cargados: {stats['total_documents']}")
    print(f"  📄 Fragmentos indexados: {stats['total_chunks']}")

    if stats['total_chunks'] == 0:
        print("\n⚠️  ADVERTENCIA: No hay documentos cargados.")
        print("   Para una consulta completa, cargue documentos PDF usando:")
        print("   POST /documentos/upload o el script de ingesta.")
        print("\n   Procediendo con demostración sin evidencia...")

    # Initialize reasoning engine
    engine = ClinicalReasoningEngine(
        vector_store=vector_store,
        llm_provider="anthropic",  # Change to "openai" if using GPT
        validate_responses=True
    )

    # Process consultation
    print("\n🧠 Procesando consulta clínica...")
    print("   (Esto puede tardar unos segundos)")

    try:
        response = await engine.process_consultation(
            patient=patient,
            include_reasoning=True,
            max_citations=5
        )

        # Display results
        print("\n" + "=" * 60)
        print("📊 RESULTADO DE LA CONSULTA")
        print("=" * 60)

        print(f"\n🎯 CLASIFICACIÓN DE RIESGO: {response.risk_classification.value}")
        print(f"   Justificación: {response.risk_justification}")

        print(f"\n💊 RECOMENDACIÓN PRINCIPAL:")
        print(f"   {response.primary_recommendation}")

        print(f"\n📝 RESUMEN:")
        print(f"   {response.recommendation_summary}")

        if response.radiotherapy:
            print(f"\n☢️  RADIOTERAPIA:")
            print(f"   Técnica: {response.radiotherapy.technique}")
            print(f"   Esquema: {response.radiotherapy.fractionation_scheme}")

        if response.systemic_therapy:
            print(f"\n💉 TERAPIA SISTÉMICA:")
            for therapy in response.systemic_therapy:
                print(f"   - {therapy.therapy_type}: {therapy.duration} ({therapy.timing})")

        print(f"\n📈 OUTCOMES ESPERADOS:")
        if response.expected_outcomes.overall_survival:
            print(f"   Sobrevida global: {response.expected_outcomes.overall_survival}")
        if response.expected_outcomes.local_control:
            print(f"   Control local: {response.expected_outcomes.local_control}")
        if response.expected_outcomes.progression_free_survival:
            print(f"   SLP: {response.expected_outcomes.progression_free_survival}")

        if response.citations:
            print(f"\n📚 CITAS ({len(response.citations)}):")
            for i, citation in enumerate(response.citations, 1):
                print(f"   [{i}] {citation.document}, Pág. {citation.page or '?'}")
                print(f"       Relevancia: {citation.relevance_score:.2f}")

        print(f"\n✅ MÉTRICAS DE CALIDAD:")
        print(f"   Confianza: {response.confidence_score:.2%}")
        print(f"   Nivel de evidencia: {response.evidence_level}")
        print(f"   Validación anti-alucinación: {'✓ Pasada' if response.hallucination_check_passed else '✗ Fallida'}")

        if response.warnings:
            print(f"\n⚠️  ADVERTENCIAS:")
            for warning in response.warnings:
                print(f"   - {warning}")

        # Export to JSON
        print("\n" + "-" * 60)
        output_file = Path("./data/example_response.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        print(f"💾 Respuesta completa guardada en: {output_file}")

    except Exception as e:
        print(f"\n❌ Error durante la consulta: {e}")
        print("\nVerifique:")
        print("  1. Que ANTHROPIC_API_KEY está configurada en .env")
        print("  2. Que hay documentos cargados en la base de datos")
        raise


if __name__ == "__main__":
    asyncio.run(main())
