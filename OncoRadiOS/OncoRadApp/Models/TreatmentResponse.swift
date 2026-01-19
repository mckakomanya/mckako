//
//  TreatmentResponse.swift
//  OncoRadApp
//
//  Modelos de respuesta de la API con recomendaciones de tratamiento
//

import Foundation

// MARK: - Cita Bibliográfica
struct Citation: Codable, Identifiable, Equatable {
    var id: String { "\(document)-\(page ?? 0)-\(section ?? "")" }

    let document: String
    let page: Int?
    let section: String?
    let originalText: String
    let relevanceScore: Double

    enum CodingKeys: String, CodingKey {
        case document
        case page
        case section
        case originalText = "original_text"
        case relevanceScore = "relevance_score"
    }

    var formattedReference: String {
        var ref = document
        if let page = page {
            ref += ", p.\(page)"
        }
        if let section = section, !section.isEmpty {
            ref += " - \(section)"
        }
        return ref
    }

    var relevancePercentage: Int {
        return Int(relevanceScore * 100)
    }
}

// MARK: - Resultados Clínicos Esperados
struct ClinicalOutcome: Codable, Equatable {
    let overallSurvival: String?
    let progressionFreeSurvival: String?
    let localControl: String?
    let diseaseFreeSurvival: String?
    let toxicityProfile: String?

    enum CodingKeys: String, CodingKey {
        case overallSurvival = "overall_survival"
        case progressionFreeSurvival = "progression_free_survival"
        case localControl = "local_control"
        case diseaseFreeSurvival = "disease_free_survival"
        case toxicityProfile = "toxicity_profile"
    }

    var hasAnyData: Bool {
        return overallSurvival != nil ||
               progressionFreeSurvival != nil ||
               localControl != nil ||
               diseaseFreeSurvival != nil ||
               toxicityProfile != nil
    }

    var summaryItems: [(String, String)] {
        var items: [(String, String)] = []
        if let os = overallSurvival { items.append(("Supervivencia Global", os)) }
        if let pfs = progressionFreeSurvival { items.append(("Supervivencia Libre de Progresión", pfs)) }
        if let lc = localControl { items.append(("Control Local", lc)) }
        if let dfs = diseaseFreeSurvival { items.append(("Supervivencia Libre de Enfermedad", dfs)) }
        if let tox = toxicityProfile { items.append(("Perfil de Toxicidad", tox)) }
        return items
    }
}

// MARK: - Recomendación de Radioterapia
struct RadiotherapyRecommendation: Codable, Equatable {
    let technique: String
    let totalDoseGy: Double
    let fractions: Int
    let dosePerFraction: Double
    let targetVolumes: [String]
    let oarConstraints: [String: String]?

    enum CodingKeys: String, CodingKey {
        case technique
        case totalDoseGy = "total_dose_gy"
        case fractions
        case dosePerFraction = "dose_per_fraction"
        case targetVolumes = "target_volumes"
        case oarConstraints = "oar_constraints"
    }

    var fractionationScheme: String {
        return "\(Int(totalDoseGy)) Gy / \(fractions) fx (\(String(format: "%.1f", dosePerFraction)) Gy/fx)"
    }

    var targetVolumesDisplay: String {
        return targetVolumes.joined(separator: ", ")
    }
}

// MARK: - Recomendación de Terapia Sistémica
struct SystemicTherapyRecommendation: Codable, Identifiable, Equatable {
    var id: String { "\(therapyType)-\(regimen)" }

    let therapyType: String
    let regimen: String
    let duration: String?
    let timing: String

    enum CodingKeys: String, CodingKey {
        case therapyType = "therapy_type"
        case regimen
        case duration
        case timing
    }

    var displayTitle: String {
        return "\(therapyType) - \(regimen)"
    }
}

// MARK: - Paso de Razonamiento Clínico
struct ReasoningStep: Codable, Identifiable, Equatable {
    var id: Int { stepNumber }

    let stepNumber: Int
    let stepName: String
    let analysis: String
    let conclusion: String
    let confidence: Double

    enum CodingKeys: String, CodingKey {
        case stepNumber = "step_number"
        case stepName = "step_name"
        case analysis
        case conclusion
        case confidence
    }

    var confidencePercentage: Int {
        return Int(confidence * 100)
    }
}

// MARK: - Respuesta Clínica Principal
struct ClinicalResponse: Codable, Equatable {
    let queryId: String
    let timestamp: String
    let riskClassification: RiskLevel
    let riskJustification: String
    let primaryRecommendation: String
    let recommendationSummary: String
    let radiotherapy: RadiotherapyRecommendation?
    let systemicTherapy: [SystemicTherapyRecommendation]?
    let reasoningChain: [ReasoningStep]
    let expectedOutcomes: ClinicalOutcome
    let citations: [Citation]
    let confidenceScore: Double
    let evidenceLevel: String
    let hallucinationCheckPassed: Bool
    let warnings: [String]?
    let alternativeOptions: [String]?

    enum CodingKeys: String, CodingKey {
        case queryId = "query_id"
        case timestamp
        case riskClassification = "risk_classification"
        case riskJustification = "risk_justification"
        case primaryRecommendation = "primary_recommendation"
        case recommendationSummary = "recommendation_summary"
        case radiotherapy
        case systemicTherapy = "systemic_therapy"
        case reasoningChain = "reasoning_chain"
        case expectedOutcomes = "expected_outcomes"
        case citations
        case confidenceScore = "confidence_score"
        case evidenceLevel = "evidence_level"
        case hallucinationCheckPassed = "hallucination_check_passed"
        case warnings
        case alternativeOptions = "alternative_options"
    }

    var confidencePercentage: Int {
        return Int(confidenceScore * 100)
    }

    var hasWarnings: Bool {
        return warnings != nil && !warnings!.isEmpty
    }

    var hasAlternatives: Bool {
        return alternativeOptions != nil && !alternativeOptions!.isEmpty
    }

    var formattedTimestamp: String {
        let dateFormatter = ISO8601DateFormatter()
        if let date = dateFormatter.date(from: timestamp) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .short
            displayFormatter.locale = Locale(identifier: "es_ES")
            return displayFormatter.string(from: date)
        }
        return timestamp
    }
}

// MARK: - Respuesta de la Consulta (Wrapper)
struct ConsultationResponse: Codable {
    let success: Bool
    let data: ClinicalResponse?
    let error: String?
    let processingTimeMs: Double

    enum CodingKeys: String, CodingKey {
        case success
        case data
        case error
        case processingTimeMs = "processing_time_ms"
    }

    var processingTimeFormatted: String {
        if processingTimeMs >= 1000 {
            return String(format: "%.1f s", processingTimeMs / 1000)
        }
        return String(format: "%.0f ms", processingTimeMs)
    }
}

// MARK: - Estado del Sistema
struct SystemStatus: Codable {
    let status: String
    let totalDocuments: Int
    let totalChunks: Int
    let vectorDbStatus: String
    let lastIndexUpdate: String
    let supportedTumorTypes: [String]

    enum CodingKeys: String, CodingKey {
        case status
        case totalDocuments = "total_documents"
        case totalChunks = "total_chunks"
        case vectorDbStatus = "vector_db_status"
        case lastIndexUpdate = "last_index_update"
        case supportedTumorTypes = "supported_tumor_types"
    }

    var isHealthy: Bool {
        return status == "healthy" && vectorDbStatus == "connected"
    }
}

// MARK: - Respuesta de Salud
struct HealthResponse: Codable {
    let status: String
    let version: String
    let timestamp: String
}

// MARK: - Modelo de Error de API
struct APIError: Codable, Error, LocalizedError {
    let detail: String?
    let message: String?

    var errorDescription: String? {
        return detail ?? message ?? "Error desconocido"
    }
}

// MARK: - Datos de Ejemplo para Preview
extension ClinicalResponse {
    static var example: ClinicalResponse {
        ClinicalResponse(
            queryId: "DEMO-001",
            timestamp: "2024-01-15T10:30:00",
            riskClassification: .high,
            riskJustification: "Clasificado como alto riesgo basado en: PSA 15.0 ng/mL, Gleason 7 (4+3), estadio T3a N0 M0",
            primaryRecommendation: "Radioterapia Externa (EBRT) 78Gy + Deprivación Androgénica (ADT) 24 meses",
            recommendationSummary: "VMAT 78 Gy/39 fx + ADT 24 meses",
            radiotherapy: RadiotherapyRecommendation(
                technique: "VMAT",
                totalDoseGy: 78.0,
                fractions: 39,
                dosePerFraction: 2.0,
                targetVolumes: ["PTV", "CTV", "Vesículas Seminales"],
                oarConstraints: [
                    "Recto": "V70 < 25%, V65 < 35%",
                    "Vejiga": "V70 < 35%, V65 < 50%",
                    "Cabezas Femorales": "V50 < 5%"
                ]
            ),
            systemicTherapy: [
                SystemicTherapyRecommendation(
                    therapyType: "Deprivación Androgénica (ADT)",
                    regimen: "Agonista/Antagonista LHRH",
                    duration: "24 meses",
                    timing: "Neoadyuvante/Concurrente/Adyuvante"
                )
            ],
            reasoningChain: [
                ReasoningStep(
                    stepNumber: 1,
                    stepName: "Verificación de Clasificación de Riesgo",
                    analysis: "Análisis de parámetros del paciente: PSA 15.0 ng/mL, Gleason 7 (4+3), T3a con extensión extracapsular",
                    conclusion: "Confirmado como alto riesgo según criterios NCCN",
                    confidence: 0.95
                ),
                ReasoningStep(
                    stepNumber: 2,
                    stepName: "Selección de Modalidad de Tratamiento",
                    analysis: "Paciente con buen estado funcional (ECOG 0), sin metástasis, candidato a tratamiento curativo",
                    conclusion: "Radioterapia definitiva con ADT es la opción preferida",
                    confidence: 0.92
                )
            ],
            expectedOutcomes: ClinicalOutcome(
                overallSurvival: "85% a 5 años",
                progressionFreeSurvival: "75% a 5 años",
                localControl: "90%",
                diseaseFreeSurvival: "78% a 5 años",
                toxicityProfile: "Toxicidad GI/GU grado 2-3 en 20-30% de pacientes"
            ),
            citations: [
                Citation(
                    document: "NCCN_Prostate_v3.2024.pdf",
                    page: 45,
                    section: "High Risk Disease Management",
                    originalText: "For patients with high-risk prostate cancer, the recommended treatment includes external beam radiation therapy (EBRT) to a dose of 75.6-79.2 Gy combined with ADT for 1.5-3 years.",
                    relevanceScore: 0.95
                ),
                Citation(
                    document: "ESTRO_ACROP_Prostate.pdf",
                    page: 12,
                    section: "Dose Escalation",
                    originalText: "Moderate hypofractionation (60 Gy in 20 fractions) is an acceptable alternative to conventional fractionation for localized prostate cancer.",
                    relevanceScore: 0.88
                )
            ],
            confidenceScore: 0.92,
            evidenceLevel: "Nivel I (Guías de Práctica Clínica)",
            hallucinationCheckPassed: true,
            warnings: ["Considerar evaluación cardiovascular previa al inicio de ADT"],
            alternativeOptions: [
                "Braquiterapia HDR boost + EBRT",
                "Prostatectomía radical con linfadenectomía extendida"
            ]
        )
    }
}
