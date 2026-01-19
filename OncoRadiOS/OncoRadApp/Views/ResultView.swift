//
//  ResultView.swift
//  OncoRadApp
//
//  Vista de resultados con recomendación de tratamiento y evidencia
//

import SwiftUI

struct ResultView: View {
    @ObservedObject var viewModel: TreatmentViewModel
    @State private var selectedCitation: Citation?
    @State private var showSourceView = false
    @State private var expandedSections: Set<String> = ["recommendation"]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    if let response = viewModel.treatmentResponse {
                        // Tarjeta principal de recomendación
                        recommendationCard(response)

                        // Advertencias (si existen)
                        if response.hasWarnings {
                            warningsCard(response.warnings!)
                        }

                        // Detalles de Radioterapia
                        if let rt = response.radiotherapy {
                            radiotherapyCard(rt)
                        }

                        // Terapia Sistémica
                        if let systemic = response.systemicTherapy, !systemic.isEmpty {
                            systemicTherapyCard(systemic)
                        }

                        // Outcomes Esperados
                        outcomesCard(response.expectedOutcomes)

                        // Razonamiento Clínico (Acordeón)
                        reasoningCard(response.reasoningChain)

                        // Referencias Bibliográficas
                        citationsCard(response.citations)

                        // Alternativas
                        if response.hasAlternatives {
                            alternativesCard(response.alternativeOptions!)
                        }

                        // Metadatos de la consulta
                        metadataCard(response)
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Recomendación")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Nueva Consulta") {
                        viewModel.resetForNewConsultation()
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    shareButton
                }
            }
            .sheet(isPresented: $showSourceView) {
                if let citation = selectedCitation {
                    SourceView(citation: citation)
                }
            }
        }
    }

    // MARK: - Tarjeta de Recomendación Principal
    private func recommendationCard(_ response: ClinicalResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header con nivel de riesgo
            HStack {
                RiskBadge(level: response.riskClassification)
                Spacer()
                confidenceBadge(response.confidencePercentage)
            }

            Divider()

            // Recomendación principal
            Text(response.primaryRecommendation)
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundStyle(.primary)

            // Resumen
            Text(response.recommendationSummary)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            // Justificación del riesgo
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "info.circle.fill")
                    .foregroundStyle(.blue)
                Text(response.riskJustification)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.top, 4)
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.05), radius: 5, y: 2)
    }

    // MARK: - Tarjeta de Advertencias
    private func warningsCard(_ warnings: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Advertencias", systemImage: "exclamationmark.triangle.fill")
                .font(.headline)
                .foregroundStyle(.orange)

            ForEach(warnings, id: \.self) { warning in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "exclamationmark.circle")
                        .foregroundStyle(.orange)
                        .font(.caption)
                    Text(warning)
                        .font(.subheadline)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.orange.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Tarjeta de Radioterapia
    private func radiotherapyCard(_ rt: RadiotherapyRecommendation) -> some View {
        CollapsibleCard(
            title: "Radioterapia",
            icon: "waveform.path.ecg",
            isExpanded: expandedSections.contains("radiotherapy"),
            onToggle: { toggleSection("radiotherapy") }
        ) {
            VStack(alignment: .leading, spacing: 12) {
                DetailRow(label: "Técnica", value: rt.technique)
                DetailRow(label: "Esquema", value: rt.fractionationScheme)
                DetailRow(label: "Volúmenes", value: rt.targetVolumesDisplay)

                if let constraints = rt.oarConstraints, !constraints.isEmpty {
                    Divider()
                    Text("Restricciones OAR")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    ForEach(Array(constraints.keys.sorted()), id: \.self) { organ in
                        if let constraint = constraints[organ] {
                            HStack {
                                Text(organ)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(constraint)
                                    .font(.caption)
                                    .fontWeight(.medium)
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - Tarjeta de Terapia Sistémica
    private func systemicTherapyCard(_ therapies: [SystemicTherapyRecommendation]) -> some View {
        CollapsibleCard(
            title: "Terapia Sistémica",
            icon: "pills.fill",
            isExpanded: expandedSections.contains("systemic"),
            onToggle: { toggleSection("systemic") }
        ) {
            VStack(alignment: .leading, spacing: 16) {
                ForEach(therapies) { therapy in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(therapy.therapyType)
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        DetailRow(label: "Régimen", value: therapy.regimen)
                        if let duration = therapy.duration {
                            DetailRow(label: "Duración", value: duration)
                        }
                        DetailRow(label: "Timing", value: therapy.timing)
                    }

                    if therapy.id != therapies.last?.id {
                        Divider()
                    }
                }
            }
        }
    }

    // MARK: - Tarjeta de Outcomes
    private func outcomesCard(_ outcomes: ClinicalOutcome) -> some View {
        CollapsibleCard(
            title: "Resultados Esperados",
            icon: "chart.line.uptrend.xyaxis",
            isExpanded: expandedSections.contains("outcomes"),
            onToggle: { toggleSection("outcomes") }
        ) {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(outcomes.summaryItems, id: \.0) { item in
                    HStack {
                        Text(item.0)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(item.1)
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }
                }
            }
        }
    }

    // MARK: - Tarjeta de Razonamiento
    private func reasoningCard(_ steps: [ReasoningStep]) -> some View {
        CollapsibleCard(
            title: "Razonamiento Clínico",
            icon: "brain.head.profile",
            isExpanded: expandedSections.contains("reasoning"),
            onToggle: { toggleSection("reasoning") }
        ) {
            VStack(alignment: .leading, spacing: 16) {
                ForEach(steps) { step in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Paso \(step.stepNumber)")
                                .font(.caption)
                                .fontWeight(.bold)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 2)
                                .background(Color.blue.opacity(0.1))
                                .clipShape(Capsule())

                            Text(step.stepName)
                                .font(.subheadline)
                                .fontWeight(.semibold)

                            Spacer()

                            Text("\(step.confidencePercentage)%")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Text(step.analysis)
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        HStack(alignment: .top) {
                            Image(systemName: "arrow.right.circle.fill")
                                .foregroundStyle(.green)
                                .font(.caption)
                            Text(step.conclusion)
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                    }

                    if step.id != steps.last?.id {
                        Divider()
                    }
                }
            }
        }
    }

    // MARK: - Tarjeta de Citas
    private func citationsCard(_ citations: [Citation]) -> some View {
        CollapsibleCard(
            title: "Referencias Bibliográficas",
            icon: "book.closed.fill",
            isExpanded: expandedSections.contains("citations"),
            onToggle: { toggleSection("citations") }
        ) {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(citations) { citation in
                    Button(action: {
                        selectedCitation = citation
                        showSourceView = true
                    }) {
                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: "doc.text.fill")
                                .foregroundStyle(.blue)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(citation.document)
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                    .foregroundStyle(.primary)
                                    .multilineTextAlignment(.leading)

                                if let section = citation.section {
                                    Text(section)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }

                                HStack {
                                    if let page = citation.page {
                                        Text("Página \(page)")
                                            .font(.caption2)
                                    }
                                    Spacer()
                                    Text("Relevancia: \(citation.relevancePercentage)%")
                                        .font(.caption2)
                                }
                                .foregroundStyle(.tertiary)
                            }

                            Image(systemName: "chevron.right")
                                .foregroundStyle(.tertiary)
                                .font(.caption)
                        }
                        .padding(.vertical, 4)
                    }
                    .buttonStyle(.plain)

                    if citation.id != citations.last?.id {
                        Divider()
                    }
                }
            }
        }
    }

    // MARK: - Tarjeta de Alternativas
    private func alternativesCard(_ alternatives: [String]) -> some View {
        CollapsibleCard(
            title: "Alternativas de Tratamiento",
            icon: "arrow.triangle.branch",
            isExpanded: expandedSections.contains("alternatives"),
            onToggle: { toggleSection("alternatives") }
        ) {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(alternatives, id: \.self) { alternative in
                    HStack(alignment: .top, spacing: 8) {
                        Image(systemName: "circle.fill")
                            .font(.system(size: 6))
                            .foregroundStyle(.secondary)
                            .padding(.top, 6)
                        Text(alternative)
                            .font(.subheadline)
                    }
                }
            }
        }
    }

    // MARK: - Tarjeta de Metadatos
    private func metadataCard(_ response: ClinicalResponse) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("ID Consulta:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(response.queryId)
                    .font(.caption)
                    .fontWeight(.medium)
            }

            HStack {
                Text("Nivel de Evidencia:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(response.evidenceLevel)
                    .font(.caption)
                    .fontWeight(.medium)
            }

            HStack {
                Text("Verificación:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack(spacing: 4) {
                    Image(systemName: response.hallucinationCheckPassed ? "checkmark.shield.fill" : "xmark.shield.fill")
                        .foregroundStyle(response.hallucinationCheckPassed ? .green : .red)
                    Text(response.hallucinationCheckPassed ? "Validado" : "No validado")
                        .font(.caption)
                        .fontWeight(.medium)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Badge de Confianza
    private func confidenceBadge(_ percentage: Int) -> some View {
        HStack(spacing: 4) {
            Image(systemName: "checkmark.seal.fill")
            Text("\(percentage)%")
        }
        .font(.caption)
        .fontWeight(.medium)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.green.opacity(0.1))
        .foregroundStyle(.green)
        .clipShape(Capsule())
    }

    // MARK: - Botón de Compartir
    private var shareButton: some View {
        ShareLink(item: shareText) {
            Image(systemName: "square.and.arrow.up")
        }
    }

    private var shareText: String {
        guard let response = viewModel.treatmentResponse else { return "" }
        return """
        Recomendación Oncológica - \(response.queryId)

        Clasificación: \(response.riskClassification.displayName)
        Recomendación: \(response.primaryRecommendation)

        Resumen: \(response.recommendationSummary)

        Nivel de Evidencia: \(response.evidenceLevel)
        Confianza: \(response.confidencePercentage)%

        Generado por OncoRad IA
        """
    }

    // MARK: - Helpers
    private func toggleSection(_ section: String) {
        withAnimation(.easeInOut(duration: 0.2)) {
            if expandedSections.contains(section) {
                expandedSections.remove(section)
            } else {
                expandedSections.insert(section)
            }
        }
    }
}

// MARK: - Componentes Auxiliares

struct DetailRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .top) {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .multilineTextAlignment(.trailing)
        }
    }
}

struct CollapsibleCard<Content: View>: View {
    let title: String
    let icon: String
    let isExpanded: Bool
    let onToggle: () -> Void
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            Button(action: onToggle) {
                HStack {
                    Label(title, systemImage: icon)
                        .font(.headline)
                    Spacer()
                    Image(systemName: "chevron.right")
                        .rotationEffect(.degrees(isExpanded ? 90 : 0))
                        .foregroundStyle(.secondary)
                }
                .padding()
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            // Content
            if isExpanded {
                Divider()
                    .padding(.horizontal)

                content
                    .padding()
            }
        }
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.05), radius: 5, y: 2)
    }
}

// MARK: - Preview
#Preview {
    ResultView(viewModel: TreatmentViewModel.previewWithResult)
}
