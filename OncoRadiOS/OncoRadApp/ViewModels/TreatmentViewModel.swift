//
//  TreatmentViewModel.swift
//  OncoRadApp
//
//  ViewModel principal para gestionar el estado del paciente y consultas
//

import Foundation
import SwiftUI

// MARK: - Estados de la Aplicación
enum AppState: Equatable {
    case input
    case processing(ProcessingPhase)
    case result
    case error(String)

    var isProcessing: Bool {
        if case .processing = self {
            return true
        }
        return false
    }
}

// MARK: - Fases del Procesamiento (para animación de carga)
enum ProcessingPhase: String, CaseIterable {
    case connecting = "Conectando con el servidor..."
    case consultingGuidelines = "Consultando Guías NCCN v3.2024..."
    case analyzingRisk = "Analizando estratificación de riesgo..."
    case retrievingEvidence = "Recuperando evidencia clínica..."
    case synthesizing = "Sintetizando recomendación..."
    case validating = "Validando contra alucinaciones..."

    var icon: String {
        switch self {
        case .connecting: return "network"
        case .consultingGuidelines: return "book.closed.fill"
        case .analyzingRisk: return "chart.bar.fill"
        case .retrievingEvidence: return "doc.text.magnifyingglass"
        case .synthesizing: return "brain.head.profile"
        case .validating: return "checkmark.shield.fill"
        }
    }
}

// MARK: - ViewModel Principal
@MainActor
final class TreatmentViewModel: ObservableObject {

    // MARK: - Estado de la App
    @Published var appState: AppState = .input
    @Published var processingPhase: ProcessingPhase = .connecting

    // MARK: - Datos del Paciente
    @Published var patientData: PatientData = PatientData()

    // MARK: - Datos Específicos por Tumor
    @Published var prostateData: ProstateSpecificData = ProstateSpecificData()
    @Published var breastData: BreastSpecificData = BreastSpecificData()
    @Published var lungData: LungSpecificData = LungSpecificData()

    // MARK: - Selecciones de UI
    @Published var selectedTumorType: TumorType = .prostate {
        didSet {
            updatePatientDataForTumorType()
        }
    }
    @Published var selectedSex: Sex = .male
    @Published var selectedGleason: GleasonScore = .g7a
    @Published var selectedECOG: ECOGStatus = .fullyActive
    @Published var selectedIntent: TreatmentIntent = .curative

    // MARK: - Staging
    @Published var selectedTStage: TStage = .t1c
    @Published var selectedNStage: NStage = .n0
    @Published var selectedMStage: MStage = .m0

    // MARK: - Valores Numéricos
    @Published var age: Int = 65
    @Published var psaValue: String = "10.0"
    @Published var ki67Value: String = "20"
    @Published var pdl1Value: String = "50"
    @Published var positiveCoresPercent: String = "30"
    @Published var tumorSizeMm: String = "25"

    // MARK: - Factores de Riesgo (Toggles)
    @Published var seminalVesicleInvasion: Bool = false
    @Published var extracapsularExtension: Bool = false
    @Published var lymphovascularInvasion: Bool = false

    // MARK: - Receptores Mama
    @Published var erPositive: Bool = true
    @Published var prPositive: Bool = true
    @Published var her2Positive: Bool = false

    // MARK: - Mutaciones Pulmón
    @Published var egfrMutation: Bool = false
    @Published var alkRearrangement: Bool = false

    // MARK: - Resultado
    @Published var treatmentResponse: ClinicalResponse?
    @Published var errorMessage: String?

    // MARK: - Estado del Sistema
    @Published var systemStatus: SystemStatus?
    @Published var isServerHealthy: Bool = false

    // MARK: - Servicios
    private let apiService = OncoAPIService.shared
    private var processingTask: Task<Void, Never>?

    // MARK: - Inicialización
    init() {
        updatePatientDataForTumorType()
    }

    // MARK: - Validación
    var isFormValid: Bool {
        guard age > 0 && age <= 120 else { return false }

        switch selectedTumorType {
        case .prostate:
            guard let psa = Double(psaValue), psa >= 0 else { return false }
            return true
        case .breast:
            return true
        case .lung:
            return true
        default:
            return true
        }
    }

    var formValidationMessage: String? {
        if age <= 0 || age > 120 {
            return "La edad debe estar entre 1 y 120 años"
        }

        switch selectedTumorType {
        case .prostate:
            if Double(psaValue) == nil {
                return "El valor de PSA debe ser un número válido"
            }
        default:
            break
        }

        return nil
    }

    // MARK: - Actualizar Datos según Tipo de Tumor
    private func updatePatientDataForTumorType() {
        // Actualizar sexo según tumor
        switch selectedTumorType {
        case .prostate:
            selectedSex = .male
        case .breast, .cervix, .endometrium:
            selectedSex = .female
        default:
            break
        }

        // Actualizar histología por defecto
        patientData.histology = defaultHistology(for: selectedTumorType)
    }

    private func defaultHistology(for tumorType: TumorType) -> String {
        switch tumorType {
        case .prostate: return "Adenocarcinoma acinar"
        case .breast: return "Carcinoma ductal infiltrante"
        case .lung: return "Adenocarcinoma"
        case .headNeck: return "Carcinoma epidermoide"
        case .colorectal: return "Adenocarcinoma"
        case .cervix: return "Carcinoma epidermoide"
        case .endometrium: return "Adenocarcinoma endometrioide"
        case .bladder: return "Carcinoma urotelial"
        case .esophagus: return "Carcinoma epidermoide"
        case .brain: return "Glioblastoma"
        case .lymphoma: return "Linfoma difuso de células grandes B"
        case .other: return "No especificado"
        }
    }

    // MARK: - Construir PatientData para envío
    func buildPatientData() -> PatientData {
        var patient = PatientData()

        // Datos básicos
        patient.age = age
        patient.sex = selectedSex.rawValue
        patient.tumorType = selectedTumorType
        patient.histology = patientData.histology.isEmpty ? defaultHistology(for: selectedTumorType) : patientData.histology
        patient.ecogStatus = selectedECOG
        patient.treatmentIntent = selectedIntent

        // Estadificación
        patient.staging = TumorStaging(
            tStage: selectedTStage,
            nStage: selectedNStage,
            mStage: selectedMStage
        )

        // Datos específicos por tumor
        switch selectedTumorType {
        case .prostate:
            var prostate = ProstateSpecificData()
            prostate.psa = Double(psaValue) ?? 0
            prostate.gleasonPrimary = selectedGleason.primary
            prostate.gleasonSecondary = selectedGleason.secondary
            if let cores = Double(positiveCoresPercent), cores > 0 {
                prostate.percentPositiveCores = cores
            }
            patient.prostateData = prostate

        case .breast:
            var breast = BreastSpecificData()
            breast.erStatus = erPositive
            breast.prStatus = prPositive
            breast.her2Status = her2Positive
            if let ki67 = Double(ki67Value), ki67 > 0 {
                breast.ki67Percent = ki67
            }
            if let size = Double(tumorSizeMm), size > 0 {
                breast.tumorSizeMm = size
            }
            patient.breastData = breast

        case .lung:
            var lung = LungSpecificData()
            lung.histology = patientData.histology
            lung.egfrMutation = egfrMutation
            lung.alkRearrangement = alkRearrangement
            if let pdl1 = Double(pdl1Value) {
                lung.pdl1Expression = pdl1
            }
            patient.lungData = lung

        default:
            break
        }

        // Generar ID
        patient.ensurePatientId()

        return patient
    }

    // MARK: - Consulta de Tratamiento
    func requestTreatment() async {
        // Cancelar tarea previa si existe
        processingTask?.cancel()

        appState = .processing(.connecting)
        errorMessage = nil
        treatmentResponse = nil

        processingTask = Task {
            // Animación de fases de procesamiento
            await animateProcessingPhases()
        }

        do {
            let patient = buildPatientData()
            let response = try await apiService.consultTreatment(
                patientData: patient,
                includeReasoning: true,
                maxCitations: 5
            )

            processingTask?.cancel()
            treatmentResponse = response
            appState = .result

        } catch let error as OncoAPIError {
            processingTask?.cancel()
            errorMessage = error.userFriendlyMessage
            appState = .error(error.userFriendlyMessage)

        } catch {
            processingTask?.cancel()
            errorMessage = error.localizedDescription
            appState = .error(error.localizedDescription)
        }
    }

    // MARK: - Animación de Fases
    private func animateProcessingPhases() async {
        let phases = ProcessingPhase.allCases
        var currentIndex = 0

        while !Task.isCancelled {
            await MainActor.run {
                processingPhase = phases[currentIndex]
                appState = .processing(phases[currentIndex])
            }

            // Esperar antes de cambiar a la siguiente fase
            try? await Task.sleep(nanoseconds: 2_000_000_000) // 2 segundos

            currentIndex = (currentIndex + 1) % phases.count
        }
    }

    // MARK: - Resetear para Nueva Consulta
    func resetForNewConsultation() {
        processingTask?.cancel()
        appState = .input
        treatmentResponse = nil
        errorMessage = nil
    }

    // MARK: - Verificar Estado del Servidor
    func checkServerHealth() async {
        do {
            let health = try await apiService.checkHealth()
            isServerHealthy = health.status == "healthy"
        } catch {
            isServerHealthy = false
        }
    }

    // MARK: - Obtener Estado del Sistema
    func fetchSystemStatus() async {
        do {
            systemStatus = try await apiService.getSystemStatus()
        } catch {
            systemStatus = nil
        }
    }

    // MARK: - Mock para Preview
    #if DEBUG
    func loadMockResponse() {
        treatmentResponse = ClinicalResponse.example
        appState = .result
    }

    static var preview: TreatmentViewModel {
        let vm = TreatmentViewModel()
        vm.age = 65
        vm.psaValue = "15.0"
        vm.selectedGleason = .g7b
        vm.selectedTStage = .t3a
        return vm
    }

    static var previewWithResult: TreatmentViewModel {
        let vm = TreatmentViewModel()
        vm.loadMockResponse()
        return vm
    }
    #endif
}

// MARK: - Extensiones de Conveniencia
extension TreatmentViewModel {
    /// Resumen del caso clínico actual
    var clinicalSummary: String {
        var summary = "\(selectedTumorType.displayName), "
        summary += "\(selectedSex.displayName), \(age) años, "
        summary += "ECOG \(selectedECOG.rawValue), "
        summary += "\(selectedTStage.rawValue)\(selectedNStage.rawValue)\(selectedMStage.rawValue)"

        if selectedTumorType == .prostate {
            summary += ", PSA \(psaValue) ng/mL"
            summary += ", Gleason \(selectedGleason.rawValue)"
        }

        return summary
    }

    /// Nivel de riesgo estimado (simplificado, para UI)
    var estimatedRiskLevel: RiskLevel {
        guard selectedTumorType == .prostate else { return .intermediateUnfavorable }

        let psa = Double(psaValue) ?? 0
        let gleason = selectedGleason.score

        // Simplificación de NCCN para UI
        if selectedMStage != .m0 {
            return .metastatic
        }

        if selectedTStage == .t3a || selectedTStage == .t3b || gleason >= 8 || psa >= 20 {
            return .high
        }

        if gleason == 7 || (psa >= 10 && psa < 20) {
            if selectedGleason == .g7b {
                return .intermediateUnfavorable
            }
            return .intermediateFavorable
        }

        if psa < 10 && gleason <= 6 && (selectedTStage == .t1 || selectedTStage == .t1c || selectedTStage == .t2a) {
            return .low
        }

        return .intermediateFavorable
    }
}
