//
//  Enums.swift
//  OncoRadApp
//
//  Enumeraciones que coinciden con los modelos Pydantic de la API Python
//

import Foundation

// MARK: - Tipo de Tumor
enum TumorType: String, Codable, CaseIterable, Identifiable {
    case prostate = "prostata"
    case breast = "mama"
    case lung = "pulmon"
    case headNeck = "cabeza_cuello"
    case colorectal = "colorrectal"
    case cervix = "cervix"
    case endometrium = "endometrio"
    case bladder = "vejiga"
    case esophagus = "esofago"
    case brain = "cerebro"
    case lymphoma = "linfoma"
    case other = "otro"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .prostate: return "Próstata"
        case .breast: return "Mama"
        case .lung: return "Pulmón"
        case .headNeck: return "Cabeza y Cuello"
        case .colorectal: return "Colorrectal"
        case .cervix: return "Cérvix"
        case .endometrium: return "Endometrio"
        case .bladder: return "Vejiga"
        case .esophagus: return "Esófago"
        case .brain: return "Cerebro"
        case .lymphoma: return "Linfoma"
        case .other: return "Otro"
        }
    }

    var icon: String {
        switch self {
        case .prostate: return "figure.stand"
        case .breast: return "heart.fill"
        case .lung: return "lungs.fill"
        case .headNeck: return "person.crop.circle"
        case .colorectal: return "cross.vial.fill"
        case .cervix: return "staroflife.fill"
        case .endometrium: return "staroflife"
        case .bladder: return "drop.fill"
        case .esophagus: return "arrow.down.circle.fill"
        case .brain: return "brain.head.profile"
        case .lymphoma: return "circle.grid.cross.fill"
        case .other: return "questionmark.circle"
        }
    }
}

// MARK: - Estadificación TNM
enum TStage: String, Codable, CaseIterable, Identifiable {
    case tx = "Tx"
    case t0 = "T0"
    case tis = "Tis"
    case t1 = "T1"
    case t1a = "T1a"
    case t1b = "T1b"
    case t1c = "T1c"
    case t2 = "T2"
    case t2a = "T2a"
    case t2b = "T2b"
    case t2c = "T2c"
    case t3 = "T3"
    case t3a = "T3a"
    case t3b = "T3b"
    case t4 = "T4"
    case t4a = "T4a"
    case t4b = "T4b"

    var id: String { rawValue }
}

enum NStage: String, Codable, CaseIterable, Identifiable {
    case nx = "Nx"
    case n0 = "N0"
    case n1 = "N1"
    case n2 = "N2"
    case n2a = "N2a"
    case n2b = "N2b"
    case n2c = "N2c"
    case n3 = "N3"
    case n3a = "N3a"
    case n3b = "N3b"

    var id: String { rawValue }
}

enum MStage: String, Codable, CaseIterable, Identifiable {
    case mx = "Mx"
    case m0 = "M0"
    case m1 = "M1"
    case m1a = "M1a"
    case m1b = "M1b"
    case m1c = "M1c"

    var id: String { rawValue }
}

// MARK: - Estado Funcional ECOG
enum ECOGStatus: Int, Codable, CaseIterable, Identifiable {
    case fullyActive = 0
    case restrictedStrenuous = 1
    case ambulatorySelfcare = 2
    case limitedSelfcare = 3
    case completelyDisabled = 4
    case dead = 5

    var id: Int { rawValue }

    var displayName: String {
        switch self {
        case .fullyActive:
            return "0 - Completamente activo"
        case .restrictedStrenuous:
            return "1 - Restricción actividad extenuante"
        case .ambulatorySelfcare:
            return "2 - Ambulatorio, autocuidado"
        case .limitedSelfcare:
            return "3 - Autocuidado limitado"
        case .completelyDisabled:
            return "4 - Completamente discapacitado"
        case .dead:
            return "5 - Fallecido"
        }
    }

    var shortDescription: String {
        switch self {
        case .fullyActive:
            return "Sin restricciones"
        case .restrictedStrenuous:
            return "Trabajo ligero posible"
        case .ambulatorySelfcare:
            return ">50% del día ambulatorio"
        case .limitedSelfcare:
            return ">50% del día en cama"
        case .completelyDisabled:
            return "Encamado"
        case .dead:
            return "Fallecido"
        }
    }
}

// MARK: - Nivel de Riesgo
enum RiskLevel: String, Codable, CaseIterable, Identifiable {
    case veryLow = "muy_bajo"
    case low = "bajo"
    case intermediateFavorable = "intermedio_favorable"
    case intermediateUnfavorable = "intermedio_desfavorable"
    case high = "alto"
    case veryHigh = "muy_alto"
    case metastatic = "metastasico"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .veryLow: return "Muy Bajo"
        case .low: return "Bajo"
        case .intermediateFavorable: return "Intermedio Favorable"
        case .intermediateUnfavorable: return "Intermedio Desfavorable"
        case .high: return "Alto"
        case .veryHigh: return "Muy Alto"
        case .metastatic: return "Metastásico"
        }
    }

    var color: String {
        switch self {
        case .veryLow, .low: return "riskLow"
        case .intermediateFavorable, .intermediateUnfavorable: return "riskIntermediate"
        case .high, .veryHigh: return "riskHigh"
        case .metastatic: return "riskMetastatic"
        }
    }
}

// MARK: - Intención del Tratamiento
enum TreatmentIntent: String, Codable, CaseIterable, Identifiable {
    case curative = "curativo"
    case palliative = "paliativo"
    case adjuvant = "adyuvante"
    case neoadjuvant = "neoadyuvante"
    case definitive = "definitivo"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .curative: return "Curativo"
        case .palliative: return "Paliativo"
        case .adjuvant: return "Adyuvante"
        case .neoadjuvant: return "Neoadyuvante"
        case .definitive: return "Definitivo"
        }
    }
}

// MARK: - Gleason Score para Próstata
enum GleasonPattern: Int, CaseIterable, Identifiable {
    case pattern1 = 1
    case pattern2 = 2
    case pattern3 = 3
    case pattern4 = 4
    case pattern5 = 5

    var id: Int { rawValue }

    var displayName: String {
        return "Patrón \(rawValue)"
    }
}

// MARK: - Gleason Score Combinado (para selector simplificado)
enum GleasonScore: String, CaseIterable, Identifiable {
    case g6 = "6 (3+3)"
    case g7a = "7 (3+4)"
    case g7b = "7 (4+3)"
    case g8 = "8"
    case g9 = "9"
    case g10 = "10"

    var id: String { rawValue }

    var primary: Int {
        switch self {
        case .g6: return 3
        case .g7a: return 3
        case .g7b: return 4
        case .g8: return 4
        case .g9: return 4
        case .g10: return 5
        }
    }

    var secondary: Int {
        switch self {
        case .g6: return 3
        case .g7a: return 4
        case .g7b: return 3
        case .g8: return 4
        case .g9: return 5
        case .g10: return 5
        }
    }

    var score: Int {
        return primary + secondary
    }

    var isupGrade: Int {
        switch self {
        case .g6: return 1
        case .g7a: return 2
        case .g7b: return 3
        case .g8: return 4
        case .g9, .g10: return 5
        }
    }
}

// MARK: - Sexo del Paciente
enum Sex: String, Codable, CaseIterable, Identifiable {
    case male = "M"
    case female = "F"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .male: return "Masculino"
        case .female: return "Femenino"
        }
    }
}
