//
//  Theme.swift
//  OncoRadApp
//
//  Definición de colores y estilos del tema "Medical Grade"
//

import SwiftUI

// MARK: - Colores del Tema
extension Color {
    // Azul clínico principal
    static let clinicalBlue = Color(hex: "007AFF")

    // Colores de riesgo
    static let riskLow = Color(hex: "34C759")
    static let riskIntermediate = Color(hex: "FF9500")
    static let riskHigh = Color(hex: "FF6B35")
    static let riskMetastatic = Color(hex: "FF3B30")

    // Colores de fondo
    static let cardBackground = Color(.systemBackground)
    static let groupedBackground = Color(.systemGroupedBackground)

    // Colores de texto
    static let primaryText = Color(.label)
    static let secondaryText = Color(.secondaryLabel)
    static let tertiaryText = Color(.tertiaryLabel)
}

// MARK: - Inicializador de Color con Hex
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Estilos de Tarjeta
struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding()
            .background(Color.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .shadow(color: .black.opacity(0.05), radius: 5, y: 2)
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(CardStyle())
    }
}

// MARK: - Estilos de Botón Primario
struct PrimaryButtonStyle: ButtonStyle {
    let isEnabled: Bool

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .fontWeight(.semibold)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isEnabled ? Color.clinicalBlue : Color.gray.opacity(0.3))
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - Estilos de Texto
extension Font {
    static let medicalTitle = Font.system(.title, design: .default, weight: .bold)
    static let medicalHeadline = Font.system(.headline, design: .default, weight: .semibold)
    static let medicalBody = Font.system(.body, design: .default)
    static let medicalCaption = Font.system(.caption, design: .default)
}

// MARK: - Efectos de Animación
extension Animation {
    static let smoothSpring = Animation.spring(response: 0.4, dampingFraction: 0.8)
    static let quickFade = Animation.easeInOut(duration: 0.2)
}

// MARK: - Constantes de Diseño
struct DesignConstants {
    static let cornerRadius: CGFloat = 12
    static let cardPadding: CGFloat = 16
    static let sectionSpacing: CGFloat = 20
    static let itemSpacing: CGFloat = 12
}
