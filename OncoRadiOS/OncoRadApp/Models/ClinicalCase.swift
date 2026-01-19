//
//  ClinicalCase.swift
//  OncoRadApp
//
//  Modelos de entrada para enviar datos del paciente a la API
//

import Foundation

// MARK: - Estadificación Tumoral
struct TumorStaging: Codable, Equatable {
    var tStage: TStage
    var nStage: NStage
    var mStage: MStage
    var clinicalStage: String?

    var tnmString: String {
        return "\(tStage.rawValue) \(nStage.rawValue) \(mStage.rawValue)"
    }

    enum CodingKeys: String, CodingKey {
        case tStage = "t_stage"
        case nStage = "n_stage"
        case mStage = "m_stage"
        case clinicalStage = "clinical_stage"
    }

    init(tStage: TStage = .t1, nStage: NStage = .n0, mStage: MStage = .m0, clinicalStage: String? = nil) {
        self.tStage = tStage
        self.nStage = nStage
        self.mStage = mStage
        self.clinicalStage = clinicalStage
    }
}

// MARK: - Datos Específicos de Próstata
struct ProstateSpecificData: Codable, Equatable {
    var psa: Double
    var gleasonPrimary: Int
    var gleasonSecondary: Int
    var percentPositiveCores: Double?

    var gleasonScore: Int {
        return gleasonPrimary + gleasonSecondary
    }

    var isupGrade: Int {
        let score = gleasonScore
        let primary = gleasonPrimary
        let secondary = gleasonSecondary

        if score <= 6 { return 1 }
        if score == 7 && primary == 3 { return 2 }
        if score == 7 && primary == 4 { return 3 }
        if score == 8 { return 4 }
        return 5
    }

    var gleasonDisplay: String {
        return "\(gleasonPrimary)+\(gleasonSecondary) = \(gleasonScore)"
    }

    enum CodingKeys: String, CodingKey {
        case psa
        case gleasonPrimary = "gleason_primary"
        case gleasonSecondary = "gleason_secondary"
        case percentPositiveCores = "percent_positive_cores"
    }

    init(psa: Double = 0, gleasonPrimary: Int = 3, gleasonSecondary: Int = 3, percentPositiveCores: Double? = nil) {
        self.psa = psa
        self.gleasonPrimary = gleasonPrimary
        self.gleasonSecondary = gleasonSecondary
        self.percentPositiveCores = percentPositiveCores
    }
}

// MARK: - Datos Específicos de Mama
struct BreastSpecificData: Codable, Equatable {
    var erStatus: Bool
    var prStatus: Bool
    var her2Status: Bool
    var ki67Percent: Double?
    var tumorSizeMm: Double?

    var molecularSubtype: String {
        if erStatus || prStatus {
            if her2Status {
                return "Luminal B HER2+"
            } else if let ki67 = ki67Percent, ki67 >= 20 {
                return "Luminal B HER2-"
            } else {
                return "Luminal A"
            }
        } else if her2Status {
            return "HER2 Enriched"
        } else {
            return "Triple Negativo"
        }
    }

    enum CodingKeys: String, CodingKey {
        case erStatus = "er_status"
        case prStatus = "pr_status"
        case her2Status = "her2_status"
        case ki67Percent = "ki67_percent"
        case tumorSizeMm = "tumor_size_mm"
    }

    init(erStatus: Bool = false, prStatus: Bool = false, her2Status: Bool = false, ki67Percent: Double? = nil, tumorSizeMm: Double? = nil) {
        self.erStatus = erStatus
        self.prStatus = prStatus
        self.her2Status = her2Status
        self.ki67Percent = ki67Percent
        self.tumorSizeMm = tumorSizeMm
    }
}

// MARK: - Datos Específicos de Pulmón
struct LungSpecificData: Codable, Equatable {
    var histology: String
    var egfrMutation: Bool?
    var alkRearrangement: Bool?
    var pdl1Expression: Double?
    var fev1Percent: Double?

    enum CodingKeys: String, CodingKey {
        case histology
        case egfrMutation = "egfr_mutation"
        case alkRearrangement = "alk_rearrangement"
        case pdl1Expression = "pdl1_expression"
        case fev1Percent = "fev1_percent"
    }

    init(histology: String = "adenocarcinoma", egfrMutation: Bool? = nil, alkRearrangement: Bool? = nil, pdl1Expression: Double? = nil, fev1Percent: Double? = nil) {
        self.histology = histology
        self.egfrMutation = egfrMutation
        self.alkRearrangement = alkRearrangement
        self.pdl1Expression = pdl1Expression
        self.fev1Percent = fev1Percent
    }
}

// MARK: - Datos del Paciente (Modelo Principal de Entrada)
struct PatientData: Codable, Equatable {
    var patientId: String?
    var age: Int
    var sex: String
    var tumorType: TumorType
    var histology: String
    var staging: TumorStaging
    var ecogStatus: ECOGStatus
    var treatmentIntent: TreatmentIntent?
    var prostateData: ProstateSpecificData?
    var breastData: BreastSpecificData?
    var lungData: LungSpecificData?
    var comorbidities: [String]?
    var previousTreatments: [String]?
    var clinicalQuestion: String?

    enum CodingKeys: String, CodingKey {
        case patientId = "patient_id"
        case age
        case sex
        case tumorType = "tumor_type"
        case histology
        case staging
        case ecogStatus = "ecog_status"
        case treatmentIntent = "treatment_intent"
        case prostateData = "prostate_data"
        case breastData = "breast_data"
        case lungData = "lung_data"
        case comorbidities
        case previousTreatments = "previous_treatments"
        case clinicalQuestion = "clinical_question"
    }

    init(
        patientId: String? = nil,
        age: Int = 65,
        sex: String = "M",
        tumorType: TumorType = .prostate,
        histology: String = "Adenocarcinoma",
        staging: TumorStaging = TumorStaging(),
        ecogStatus: ECOGStatus = .fullyActive,
        treatmentIntent: TreatmentIntent? = .curative,
        prostateData: ProstateSpecificData? = nil,
        breastData: BreastSpecificData? = nil,
        lungData: LungSpecificData? = nil,
        comorbidities: [String]? = nil,
        previousTreatments: [String]? = nil,
        clinicalQuestion: String? = nil
    ) {
        self.patientId = patientId
        self.age = age
        self.sex = sex
        self.tumorType = tumorType
        self.histology = histology
        self.staging = staging
        self.ecogStatus = ecogStatus
        self.treatmentIntent = treatmentIntent
        self.prostateData = prostateData
        self.breastData = breastData
        self.lungData = lungData
        self.comorbidities = comorbidities
        self.previousTreatments = previousTreatments
        self.clinicalQuestion = clinicalQuestion
    }

    /// Valida si los datos mínimos requeridos están completos
    var isValid: Bool {
        guard age > 0 && age <= 120 else { return false }
        guard !histology.isEmpty else { return false }

        switch tumorType {
        case .prostate:
            guard let prostate = prostateData else { return false }
            return prostate.psa >= 0
        case .breast:
            return breastData != nil
        case .lung:
            guard let lung = lungData else { return false }
            return !lung.histology.isEmpty
        default:
            return true
        }
    }

    /// Genera un ID de paciente único si no existe
    mutating func ensurePatientId() {
        if patientId == nil {
            patientId = "PT-\(UUID().uuidString.prefix(8).uppercased())"
        }
    }
}

// MARK: - Request de Consulta
struct ConsultationRequest: Codable {
    var patientData: PatientData
    var includeReasoning: Bool
    var maxCitations: Int
    var language: String

    enum CodingKeys: String, CodingKey {
        case patientData = "patient_data"
        case includeReasoning = "include_reasoning"
        case maxCitations = "max_citations"
        case language
    }

    init(patientData: PatientData, includeReasoning: Bool = true, maxCitations: Int = 5, language: String = "es") {
        self.patientData = patientData
        self.includeReasoning = includeReasoning
        self.maxCitations = maxCitations
        self.language = language
    }
}

// MARK: - Extensión para crear datos de ejemplo
extension PatientData {
    static var prostateExample: PatientData {
        var patient = PatientData(
            patientId: "DEMO-001",
            age: 65,
            sex: "M",
            tumorType: .prostate,
            histology: "Adenocarcinoma acinar",
            staging: TumorStaging(tStage: .t3a, nStage: .n0, mStage: .m0, clinicalStage: "IIIA"),
            ecogStatus: .fullyActive,
            treatmentIntent: .curative,
            prostateData: ProstateSpecificData(psa: 15.0, gleasonPrimary: 4, gleasonSecondary: 3, percentPositiveCores: 45.0),
            comorbidities: ["Hipertensión", "Diabetes tipo 2"]
        )
        return patient
    }

    static var breastExample: PatientData {
        return PatientData(
            patientId: "DEMO-002",
            age: 52,
            sex: "F",
            tumorType: .breast,
            histology: "Carcinoma ductal infiltrante",
            staging: TumorStaging(tStage: .t2, nStage: .n1, mStage: .m0, clinicalStage: "IIB"),
            ecogStatus: .fullyActive,
            treatmentIntent: .curative,
            breastData: BreastSpecificData(erStatus: true, prStatus: true, her2Status: false, ki67Percent: 25.0, tumorSizeMm: 28.0)
        )
    }

    static var lungExample: PatientData {
        return PatientData(
            patientId: "DEMO-003",
            age: 68,
            sex: "M",
            tumorType: .lung,
            histology: "Adenocarcinoma",
            staging: TumorStaging(tStage: .t2a, nStage: .n2, mStage: .m0, clinicalStage: "IIIA"),
            ecogStatus: .restrictedStrenuous,
            treatmentIntent: .curative,
            lungData: LungSpecificData(histology: "adenocarcinoma", egfrMutation: false, alkRearrangement: false, pdl1Expression: 60.0, fev1Percent: 75.0)
        )
    }
}
