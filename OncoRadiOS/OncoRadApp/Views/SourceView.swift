//
//  SourceView.swift
//  OncoRadApp
//
//  Vista modal para mostrar el texto original de una cita bibliográfica
//

import SwiftUI

struct SourceView: View {
    let citation: Citation
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Header del documento
                    documentHeader

                    // Metadata de la cita
                    citationMetadata

                    // Texto original
                    originalTextSection

                    // Indicador de relevancia
                    relevanceIndicator
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Fuente")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cerrar") {
                        dismiss()
                    }
                }
            }
        }
    }

    // MARK: - Header del Documento
    private var documentHeader: some View {
        HStack(spacing: 16) {
            // Icono del documento
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.blue.opacity(0.1))
                    .frame(width: 60, height: 72)

                Image(systemName: "doc.text.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.blue)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(citation.document)
                    .font(.headline)
                    .lineLimit(2)

                if let section = citation.section {
                    Text(section)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if let page = citation.page {
                    Text("Página \(page)")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Metadata
    private var citationMetadata: some View {
        HStack(spacing: 16) {
            // Tipo de documento
            MetadataItem(
                icon: "doc.badge.clock",
                title: "Tipo",
                value: documentType
            )

            Divider()
                .frame(height: 40)

            // Página
            MetadataItem(
                icon: "book.pages",
                title: "Ubicación",
                value: citation.page != nil ? "Pág. \(citation.page!)" : "N/A"
            )

            Divider()
                .frame(height: 40)

            // Relevancia
            MetadataItem(
                icon: "chart.bar.fill",
                title: "Relevancia",
                value: "\(citation.relevancePercentage)%"
            )
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Texto Original
    private var originalTextSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Texto Original Extraído", systemImage: "text.quote")
                .font(.headline)
                .foregroundStyle(.primary)

            Text("El siguiente fragmento fue extraído directamente del documento fuente:")
                .font(.caption)
                .foregroundStyle(.secondary)

            // Texto citado
            VStack(alignment: .leading, spacing: 0) {
                // Comilla de apertura
                HStack {
                    Image(systemName: "quote.opening")
                        .font(.title2)
                        .foregroundStyle(.blue.opacity(0.5))
                    Spacer()
                }

                // Texto
                Text(citation.originalText)
                    .font(.body)
                    .italic()
                    .lineSpacing(6)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 12)
                    .textSelection(.enabled)

                // Comilla de cierre
                HStack {
                    Spacer()
                    Image(systemName: "quote.closing")
                        .font(.title2)
                        .foregroundStyle(.blue.opacity(0.5))
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.blue.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.blue.opacity(0.2), lineWidth: 1)
                    )
            )
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Indicador de Relevancia
    private var relevanceIndicator: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Puntuación de Relevancia", systemImage: "chart.line.uptrend.xyaxis")
                .font(.headline)

            HStack(spacing: 12) {
                // Barra de progreso
                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.gray.opacity(0.2))

                        RoundedRectangle(cornerRadius: 8)
                            .fill(relevanceColor)
                            .frame(width: geometry.size.width * citation.relevanceScore)
                    }
                }
                .frame(height: 12)

                // Porcentaje
                Text("\(citation.relevancePercentage)%")
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundStyle(relevanceColor)
                    .frame(width: 60)
            }

            Text(relevanceDescription)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Helpers
    private var documentType: String {
        let filename = citation.document.lowercased()
        if filename.contains("nccn") {
            return "Guía NCCN"
        } else if filename.contains("estro") || filename.contains("acrop") {
            return "Guía ESTRO"
        } else if filename.contains("asco") {
            return "Guía ASCO"
        } else if filename.contains("astro") {
            return "Guía ASTRO"
        } else {
            return "Documento Clínico"
        }
    }

    private var relevanceColor: Color {
        switch citation.relevanceScore {
        case 0.8...1.0:
            return .green
        case 0.6..<0.8:
            return .blue
        case 0.4..<0.6:
            return .orange
        default:
            return .gray
        }
    }

    private var relevanceDescription: String {
        switch citation.relevanceScore {
        case 0.9...1.0:
            return "Altamente relevante - Esta cita está directamente relacionada con el caso clínico presentado."
        case 0.8..<0.9:
            return "Muy relevante - Fuerte correlación con los parámetros del paciente."
        case 0.6..<0.8:
            return "Relevante - Información aplicable al contexto clínico."
        case 0.4..<0.6:
            return "Moderadamente relevante - Información contextual de apoyo."
        default:
            return "Información de referencia general."
        }
    }
}

// MARK: - Componente de Metadata
struct MetadataItem: View {
    let icon: String
    let title: String
    let value: String

    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(.blue)

            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)

            Text(value)
                .font(.caption)
                .fontWeight(.semibold)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Preview
#Preview {
    SourceView(citation: Citation(
        document: "NCCN_Prostate_v3.2024.pdf",
        page: 45,
        section: "High Risk Disease Management",
        originalText: "For patients with high-risk prostate cancer (T3a, Gleason score 8-10, or PSA >20 ng/mL), the recommended treatment includes external beam radiation therapy (EBRT) to a dose of 75.6-79.2 Gy combined with androgen deprivation therapy (ADT) for 1.5-3 years. This recommendation is based on multiple randomized controlled trials demonstrating improved overall survival and biochemical control with combined modality treatment.",
        relevanceScore: 0.95
    ))
}
