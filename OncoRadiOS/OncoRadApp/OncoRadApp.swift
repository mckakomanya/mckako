//
//  OncoRadApp.swift
//  OncoRadApp
//
//  Punto de entrada de la aplicación OncoRad iOS
//

import SwiftUI

@main
struct OncoRadApp: App {
    @StateObject private var viewModel = TreatmentViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}
