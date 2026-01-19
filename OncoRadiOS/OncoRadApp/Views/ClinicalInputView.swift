//
//  ClinicalInputView.swift
//  OncoRadApp
//
//  Vista principal de entrada de datos clínicos
//

import SwiftUI

struct ClinicalInputView: View {
    @ObservedObject var viewModel: TreatmentViewModel
    @State private var showingAdvancedOptions = false

    var body: some View {
        NavigationStack {
            Form {
                // MARK: - Selector de Patología
                Section {
                    tumorTypePicker
                } header: {
                    Label("Patología", systemImage: "cross.case.fill")
                }

                // MARK: - Datos del Paciente
                Section {
                    patientBasicInfo
                } header: {
                    Label("Paciente", systemImage: "person.fill")
                }

                // MARK: - Estadificación TNM
                Section {
                    tnmStagingSection
                } header: {
                    Label("Estadificación TNM", systemImage: "chart.bar.doc.horizontal")
                }

                // MARK: - Datos Específicos según Tumor
                tumorSpecificSection

                // MARK: - Factores de Riesgo
                if viewModel.selectedTumorType == .prostate {
                    riskFactorsSection
                }

                // MARK: - Estado Funcional
                Section {
                    ecogPicker
                    intentPicker
                } header: {
                    Label("Estado Clínico", systemImage: "heart.text.square")
                }

                // MARK: - Resumen y Acción
                Section {
                    summaryCard
                    generateButton
                } header: {
                    Label("Consulta", systemImage: "waveform.path.ecg")
                }
            }
            .navigationTitle("Entrada Clínica")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    serverStatusIndicator
                }
            }
        }
    }

    // MARK: - Selector de Tipo de Tumor
    private var tumorTypePicker: some View {
        Picker("Tipo de Tumor", selection: $viewModel.selectedTumorType) {
            ForEach(TumorType.allCases) { type in
                Label(type.displayName, systemImage: type.icon)
                    .tag(type)
            }
        }
        .pickerStyle(.navigationLink)
    }

    // MARK: - Información Básica del Paciente
    private var patientBasicInfo: some View {
        Group {
            // Edad
            Stepper(value: $viewModel.age, in: 1...120) {
                HStack {
                    Text("Edad")
                    Spacer()
                    Text("\(viewModel.age) años")
                        .foregroundStyle(.secondary)
                }
            }

            // Sexo (automático según tumor en algunos casos)
            Picker("Sexo", selection: $viewModel.selectedSex) {
                ForEach(Sex.allCases) { sex in
                    Text(sex.displayName).tag(sex)
                }
            }
            .disabled(viewModel.selectedTumorType == .prostate ||
                     viewModel.selectedTumorType == .cervix ||
                     viewModel.selectedTumorType == .endometrium)
        }
    }

    // MARK: - Estadificación TNM
    private var tnmStagingSection: some View {
        Group {
            // T Stage
            Picker("Estadio T", selection: $viewModel.selectedTStage) {
                ForEach(TStage.allCases) { stage in
                    Text(stage.rawValue).tag(stage)
                }
            }

            // N Stage
            Picker("Estadio N", selection: $viewModel.selectedNStage) {
                ForEach(NStage.allCases) { stage in
                    Text(stage.rawValue).tag(stage)
                }
            }

            // M Stage
            Picker("Estadio M", selection: $viewModel.selectedMStage) {
                ForEach(MStage.allCases) { stage in
                    Text(stage.rawValue).tag(stage)
                }
            }

            // TNM Combinado
            HStack {
                Text("Estadificación")
                Spacer()
                Text("\(viewModel.selectedTStage.rawValue) \(viewModel.selectedNStage.rawValue) \(viewModel.selectedMStage.rawValue)")
                    .font(.headline)
                    .foregroundStyle(.blue)
            }
        }
    }

    // MARK: - Sección Específica por Tumor
    @ViewBuilder
    private var tumorSpecificSection: some View {
        switch viewModel.selectedTumorType {
        case .prostate:
            prostateSection
        case .breast:
            breastSection
        case .lung:
            lungSection
        default:
            EmptyView()
        }
    }

    // MARK: - Sección Próstata
    private var prostateSection: some View {
        Section {
            // PSA
            HStack {
                Text("PSA")
                Spacer()
                TextField("ng/mL", text: $viewModel.psaValue)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 80)
                Text("ng/mL")
                    .foregroundStyle(.secondary)
            }

            // Gleason Score
            Picker("Gleason Score", selection: $viewModel.selectedGleason) {
                ForEach(GleasonScore.allCases) { score in
                    Text(score.rawValue).tag(score)
                }
            }

            // ISUP Grade (calculado)
            HStack {
                Text("Grupo ISUP")
                Spacer()
                Text("Grado \(viewModel.selectedGleason.isupGrade)")
                    .foregroundStyle(.secondary)
            }

            // Porcentaje de Cores Positivos
            HStack {
                Text("Cores Positivos")
                Spacer()
                TextField("%", text: $viewModel.positiveCoresPercent)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 60)
                Text("%")
                    .foregroundStyle(.secondary)
            }
        } header: {
            Label("Datos de Próstata", systemImage: "figure.stand")
        }
    }

    // MARK: - Sección Mama
    private var breastSection: some View {
        Section {
            // Receptores Hormonales
            Toggle("Receptor Estrógeno (ER+)", isOn: $viewModel.erPositive)
            Toggle("Receptor Progesterona (PR+)", isOn: $viewModel.prPositive)
            Toggle("HER2 Positivo", isOn: $viewModel.her2Positive)

            // Ki-67
            HStack {
                Text("Ki-67")
                Spacer()
                TextField("%", text: $viewModel.ki67Value)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 60)
                Text("%")
                    .foregroundStyle(.secondary)
            }

            // Tamaño tumoral
            HStack {
                Text("Tamaño Tumoral")
                Spacer()
                TextField("mm", text: $viewModel.tumorSizeMm)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 60)
                Text("mm")
                    .foregroundStyle(.secondary)
            }

            // Subtipo Molecular (calculado)
            HStack {
                Text("Subtipo Molecular")
                Spacer()
                Text(viewModel.breastData.molecularSubtype)
                    .foregroundStyle(.blue)
                    .fontWeight(.medium)
            }
        } header: {
            Label("Datos de Mama", systemImage: "heart.fill")
        }
    }

    // MARK: - Sección Pulmón
    private var lungSection: some View {
        Section {
            // Mutaciones
            Toggle("Mutación EGFR", isOn: $viewModel.egfrMutation)
            Toggle("Reordenamiento ALK", isOn: $viewModel.alkRearrangement)

            // PD-L1
            HStack {
                Text("PD-L1 Expression")
                Spacer()
                TextField("%", text: $viewModel.pdl1Value)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 60)
                Text("%")
                    .foregroundStyle(.secondary)
            }
        } header: {
            Label("Datos de Pulmón", systemImage: "lungs.fill")
        }
    }

    // MARK: - Factores de Riesgo
    private var riskFactorsSection: some View {
        Section {
            Toggle("Invasión Vesículas Seminales", isOn: $viewModel.seminalVesicleInvasion)
            Toggle("Extensión Extracapsular", isOn: $viewModel.extracapsularExtension)
            Toggle("Invasión Linfovascular", isOn: $viewModel.lymphovascularInvasion)
        } header: {
            Label("Factores de Riesgo", systemImage: "exclamationmark.triangle")
        }
    }

    // MARK: - ECOG Picker
    private var ecogPicker: some View {
        Picker("ECOG Performance Status", selection: $viewModel.selectedECOG) {
            ForEach(ECOGStatus.allCases.dropLast()) { status in // Excluir "dead"
                Text(status.displayName).tag(status)
            }
        }
        .pickerStyle(.navigationLink)
    }

    // MARK: - Intent Picker
    private var intentPicker: some View {
        Picker("Intención del Tratamiento", selection: $viewModel.selectedIntent) {
            ForEach(TreatmentIntent.allCases) { intent in
                Text(intent.displayName).tag(intent)
            }
        }
    }

    // MARK: - Tarjeta de Resumen
    private var summaryCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Resumen del Caso")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text(viewModel.clinicalSummary)
                .font(.callout)

            // Estimación de riesgo
            HStack {
                Text("Riesgo Estimado:")
                    .font(.callout)
                RiskBadge(level: viewModel.estimatedRiskLevel)
            }
        }
        .padding(.vertical, 4)
    }

    // MARK: - Botón de Generar
    private var generateButton: some View {
        Button(action: {
            Task {
                await viewModel.requestTreatment()
            }
        }) {
            HStack {
                Image(systemName: "waveform.path.ecg.rectangle")
                Text("Generar Conducta Terapéutica")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .disabled(!viewModel.isFormValid)
        .listRowInsets(EdgeInsets())
        .listRowBackground(Color.clear)
    }

    // MARK: - Indicador de Estado del Servidor
    private var serverStatusIndicator: some View {
        Circle()
            .fill(viewModel.isServerHealthy ? Color.green : Color.orange)
            .frame(width: 10, height: 10)
            .overlay {
                Circle()
                    .stroke(Color.primary.opacity(0.2), lineWidth: 1)
            }
    }
}

// MARK: - Badge de Nivel de Riesgo
struct RiskBadge: View {
    let level: RiskLevel

    var body: some View {
        Text(level.displayName)
            .font(.caption)
            .fontWeight(.medium)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(backgroundColor)
            .foregroundColor(foregroundColor)
            .clipShape(Capsule())
    }

    private var backgroundColor: Color {
        switch level {
        case .veryLow, .low:
            return Color.green.opacity(0.2)
        case .intermediateFavorable, .intermediateUnfavorable:
            return Color.yellow.opacity(0.2)
        case .high, .veryHigh:
            return Color.orange.opacity(0.2)
        case .metastatic:
            return Color.red.opacity(0.2)
        }
    }

    private var foregroundColor: Color {
        switch level {
        case .veryLow, .low:
            return Color.green
        case .intermediateFavorable, .intermediateUnfavorable:
            return Color.orange
        case .high, .veryHigh:
            return Color.orange
        case .metastatic:
            return Color.red
        }
    }
}

// MARK: - Preview
#Preview {
    ClinicalInputView(viewModel: TreatmentViewModel.preview)
}
