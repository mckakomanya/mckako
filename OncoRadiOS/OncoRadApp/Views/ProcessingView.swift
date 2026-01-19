//
//  ProcessingView.swift
//  OncoRadApp
//
//  Vista de estado de carga con animación de fases
//

import SwiftUI

struct ProcessingView: View {
    @ObservedObject var viewModel: TreatmentViewModel
    @State private var pulseAnimation = false
    @State private var rotationAngle: Double = 0

    var body: some View {
        VStack(spacing: 40) {
            Spacer()

            // Logo animado
            animatedLogo

            // Fase actual
            phaseIndicator

            // Barra de progreso
            progressIndicator

            // Mensaje de contexto
            contextMessage

            Spacer()

            // Botón de cancelar
            cancelButton
        }
        .padding()
        .background(
            LinearGradient(
                colors: [Color(.systemBackground), Color.blue.opacity(0.05)],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .onAppear {
            startAnimations()
        }
    }

    // MARK: - Logo Animado
    private var animatedLogo: some View {
        ZStack {
            // Círculo exterior pulsante
            Circle()
                .stroke(Color.blue.opacity(0.3), lineWidth: 4)
                .frame(width: 120, height: 120)
                .scaleEffect(pulseAnimation ? 1.2 : 1.0)
                .opacity(pulseAnimation ? 0.0 : 0.5)

            // Círculo intermedio rotando
            Circle()
                .trim(from: 0.0, to: 0.7)
                .stroke(
                    LinearGradient(
                        colors: [.blue, .cyan],
                        startPoint: .leading,
                        endPoint: .trailing
                    ),
                    style: StrokeStyle(lineWidth: 4, lineCap: .round)
                )
                .frame(width: 100, height: 100)
                .rotationEffect(.degrees(rotationAngle))

            // Círculo interior con icono
            Circle()
                .fill(Color.blue.opacity(0.1))
                .frame(width: 80, height: 80)

            // Icono de la fase actual
            Image(systemName: viewModel.processingPhase.icon)
                .font(.system(size: 32))
                .foregroundStyle(.blue)
                .symbolEffect(.pulse)
        }
    }

    // MARK: - Indicador de Fase
    private var phaseIndicator: some View {
        VStack(spacing: 12) {
            Text(viewModel.processingPhase.rawValue)
                .font(.headline)
                .foregroundStyle(.primary)
                .multilineTextAlignment(.center)
                .contentTransition(.numericText())
                .animation(.easeInOut, value: viewModel.processingPhase)

            // Indicador de pasos
            HStack(spacing: 8) {
                ForEach(Array(ProcessingPhase.allCases.enumerated()), id: \.element) { index, phase in
                    Circle()
                        .fill(phaseColor(for: phase))
                        .frame(width: 8, height: 8)
                        .scaleEffect(phase == viewModel.processingPhase ? 1.3 : 1.0)
                        .animation(.spring(response: 0.3), value: viewModel.processingPhase)
                }
            }
        }
    }

    // MARK: - Indicador de Progreso
    private var progressIndicator: some View {
        VStack(spacing: 8) {
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    // Fondo
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 8)

                    // Progreso animado
                    RoundedRectangle(cornerRadius: 4)
                        .fill(
                            LinearGradient(
                                colors: [.blue, .cyan],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: progressWidth(for: geometry.size.width), height: 8)
                        .animation(.easeInOut(duration: 0.5), value: viewModel.processingPhase)
                }
            }
            .frame(height: 8)
            .padding(.horizontal, 40)
        }
    }

    // MARK: - Mensaje de Contexto
    private var contextMessage: some View {
        VStack(spacing: 8) {
            Text("Analizando caso clínico")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text("Este proceso puede tomar unos segundos mientras consultamos las guías clínicas más recientes.")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
        }
    }

    // MARK: - Botón de Cancelar
    private var cancelButton: some View {
        Button(action: {
            viewModel.resetForNewConsultation()
        }) {
            Text("Cancelar")
                .foregroundStyle(.secondary)
        }
        .buttonStyle(.bordered)
        .padding(.bottom, 20)
    }

    // MARK: - Helpers
    private func phaseColor(for phase: ProcessingPhase) -> Color {
        let currentIndex = ProcessingPhase.allCases.firstIndex(of: viewModel.processingPhase) ?? 0
        let phaseIndex = ProcessingPhase.allCases.firstIndex(of: phase) ?? 0

        if phaseIndex < currentIndex {
            return .blue
        } else if phaseIndex == currentIndex {
            return .cyan
        } else {
            return .gray.opacity(0.3)
        }
    }

    private func progressWidth(for totalWidth: CGFloat) -> CGFloat {
        let totalPhases = ProcessingPhase.allCases.count
        let currentIndex = ProcessingPhase.allCases.firstIndex(of: viewModel.processingPhase) ?? 0
        let progress = CGFloat(currentIndex + 1) / CGFloat(totalPhases)
        return totalWidth * progress
    }

    private func startAnimations() {
        // Animación de pulso
        withAnimation(.easeInOut(duration: 1.5).repeatForever(autoreverses: false)) {
            pulseAnimation = true
        }

        // Animación de rotación
        withAnimation(.linear(duration: 2).repeatForever(autoreverses: false)) {
            rotationAngle = 360
        }
    }
}

// MARK: - Vista Compacta de Procesamiento (para overlay)
struct CompactProcessingView: View {
    let phase: ProcessingPhase

    var body: some View {
        HStack(spacing: 12) {
            ProgressView()
                .progressViewStyle(.circular)

            Text(phase.rawValue)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }
}

// MARK: - Preview
#Preview("Processing View") {
    ProcessingView(viewModel: {
        let vm = TreatmentViewModel()
        vm.appState = .processing(.analyzingRisk)
        return vm
    }())
}

#Preview("Compact Processing") {
    CompactProcessingView(phase: .consultingGuidelines)
        .padding()
}
