//
//  ContentView.swift
//  OncoRadApp
//
//  Vista principal que gestiona la navegación entre estados
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var viewModel: TreatmentViewModel

    var body: some View {
        Group {
            switch viewModel.appState {
            case .input:
                ClinicalInputView(viewModel: viewModel)
                    .transition(.asymmetric(
                        insertion: .move(edge: .leading).combined(with: .opacity),
                        removal: .move(edge: .leading).combined(with: .opacity)
                    ))

            case .processing:
                ProcessingView(viewModel: viewModel)
                    .transition(.asymmetric(
                        insertion: .scale.combined(with: .opacity),
                        removal: .scale.combined(with: .opacity)
                    ))

            case .result:
                ResultView(viewModel: viewModel)
                    .transition(.asymmetric(
                        insertion: .move(edge: .trailing).combined(with: .opacity),
                        removal: .move(edge: .trailing).combined(with: .opacity)
                    ))

            case .error(let message):
                ErrorView(message: message, viewModel: viewModel)
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.3), value: viewModel.appState)
        .task {
            await viewModel.checkServerHealth()
        }
    }
}

// MARK: - Vista de Error
struct ErrorView: View {
    let message: String
    @ObservedObject var viewModel: TreatmentViewModel
    @State private var showingDetails = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                // Icono de error
                ZStack {
                    Circle()
                        .fill(Color.red.opacity(0.1))
                        .frame(width: 120, height: 120)

                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 50))
                        .foregroundStyle(.red)
                }

                // Título
                Text("Error en la Consulta")
                    .font(.title2)
                    .fontWeight(.bold)

                // Mensaje
                Text(message)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)

                Spacer()

                // Botones de acción
                VStack(spacing: 12) {
                    Button(action: {
                        Task {
                            await viewModel.requestTreatment()
                        }
                    }) {
                        Label("Reintentar", systemImage: "arrow.clockwise")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)

                    Button(action: {
                        viewModel.resetForNewConsultation()
                    }) {
                        Text("Volver al Formulario")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                }
                .padding(.horizontal, 40)
                .padding(.bottom, 40)
            }
            .navigationTitle("Error")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

// MARK: - Preview
#Preview("Input State") {
    ContentView()
        .environmentObject(TreatmentViewModel())
}

#Preview("Processing State") {
    ContentView()
        .environmentObject({
            let vm = TreatmentViewModel()
            vm.appState = .processing(.analyzingRisk)
            return vm
        }())
}

#Preview("Result State") {
    ContentView()
        .environmentObject(TreatmentViewModel.previewWithResult)
}

#Preview("Error State") {
    ContentView()
        .environmentObject({
            let vm = TreatmentViewModel()
            vm.appState = .error("No se pudo conectar con el servidor. Verifica tu conexión a internet.")
            return vm
        }())
}
