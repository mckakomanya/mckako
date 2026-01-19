//
//  OncoAPIService.swift
//  OncoRadApp
//
//  Servicio de red para comunicación con la API de OncoRad
//

import Foundation

// MARK: - Errores de API
enum OncoAPIError: Error, LocalizedError {
    case invalidURL
    case networkError(Error)
    case serverError(Int, String?)
    case decodingError(Error)
    case noData
    case apiError(String)
    case timeout
    case noConnection

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "URL de servidor inválida"
        case .networkError(let error):
            return "Error de red: \(error.localizedDescription)"
        case .serverError(let code, let message):
            return "Error del servidor (\(code)): \(message ?? "Sin descripción")"
        case .decodingError(let error):
            return "Error al procesar respuesta: \(error.localizedDescription)"
        case .noData:
            return "No se recibieron datos del servidor"
        case .apiError(let message):
            return message
        case .timeout:
            return "La solicitud tardó demasiado tiempo"
        case .noConnection:
            return "Sin conexión a internet"
        }
    }

    var userFriendlyMessage: String {
        switch self {
        case .invalidURL:
            return "Configuración de servidor incorrecta"
        case .networkError, .noConnection:
            return "No se pudo conectar con el servidor. Verifica tu conexión."
        case .serverError(let code, _):
            if code >= 500 {
                return "El servidor está experimentando problemas. Intenta más tarde."
            }
            return "Error en la solicitud. Verifica los datos ingresados."
        case .decodingError:
            return "Error al procesar la respuesta del servidor"
        case .noData:
            return "El servidor no devolvió información"
        case .apiError(let message):
            return message
        case .timeout:
            return "La consulta tardó demasiado. El servidor puede estar ocupado."
        }
    }
}

// MARK: - Configuración del Servicio
struct APIConfiguration {
    static let shared = APIConfiguration()

    // URL base del servidor (cambiar para producción)
    var baseURL: String = "http://localhost:8000"

    // Timeout para solicitudes (en segundos)
    var timeoutInterval: TimeInterval = 60

    // Headers comunes
    var defaultHeaders: [String: String] {
        return [
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "es"
        ]
    }
}

// MARK: - Servicio Principal de API
final class OncoAPIService {
    static let shared = OncoAPIService()

    private let session: URLSession
    private var configuration: APIConfiguration

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 60
        config.timeoutIntervalForResource = 120
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config)
        self.configuration = APIConfiguration.shared
    }

    // MARK: - Configuración
    func updateBaseURL(_ url: String) {
        configuration.baseURL = url
    }

    // MARK: - Consulta Principal de Tratamiento
    /// Envía datos del paciente y recibe recomendación de tratamiento
    func consultTreatment(
        patientData: PatientData,
        includeReasoning: Bool = true,
        maxCitations: Int = 5,
        language: String = "es"
    ) async throws -> ClinicalResponse {
        let request = ConsultationRequest(
            patientData: patientData,
            includeReasoning: includeReasoning,
            maxCitations: maxCitations,
            language: language
        )

        let response: ConsultationResponse = try await performRequest(
            endpoint: "/consultar",
            method: "POST",
            body: request
        )

        if response.success, let data = response.data {
            return data
        } else {
            throw OncoAPIError.apiError(response.error ?? "Error desconocido en la consulta")
        }
    }

    // MARK: - Estado del Sistema
    /// Verifica el estado del servidor y la base de datos
    func getSystemStatus() async throws -> SystemStatus {
        return try await performRequest(endpoint: "/status", method: "GET")
    }

    // MARK: - Verificación de Salud
    /// Verifica si el servidor está respondiendo
    func checkHealth() async throws -> HealthResponse {
        return try await performRequest(endpoint: "/health", method: "GET")
    }

    // MARK: - Tipos de Tumor Soportados
    /// Obtiene la lista de tipos de tumor soportados
    func getSupportedTumorTypes() async throws -> [String] {
        struct TumorTypesResponse: Codable {
            let tumorTypes: [String]

            enum CodingKeys: String, CodingKey {
                case tumorTypes = "tumor_types"
            }
        }

        let response: TumorTypesResponse = try await performRequest(
            endpoint: "/tipos-tumor",
            method: "GET"
        )
        return response.tumorTypes
    }

    // MARK: - Fuentes Documentales
    /// Obtiene la lista de documentos cargados en el sistema
    func getLoadedSources() async throws -> [String] {
        struct SourcesResponse: Codable {
            let sources: [String]
            let totalDocuments: Int

            enum CodingKeys: String, CodingKey {
                case sources
                case totalDocuments = "total_documents"
            }
        }

        let response: SourcesResponse = try await performRequest(
            endpoint: "/fuentes",
            method: "GET"
        )
        return response.sources
    }

    // MARK: - Request Genérico
    private func performRequest<T: Decodable>(
        endpoint: String,
        method: String,
        body: (some Encodable)? = nil as String?
    ) async throws -> T {
        guard let url = URL(string: configuration.baseURL + endpoint) else {
            throw OncoAPIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = configuration.timeoutInterval

        // Configurar headers
        for (key, value) in configuration.defaultHeaders {
            request.setValue(value, forHTTPHeaderField: key)
        }

        // Codificar body si existe
        if let body = body {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .useDefaultKeys
            request.httpBody = try encoder.encode(body)
        }

        // Realizar solicitud
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch let urlError as URLError {
            switch urlError.code {
            case .timedOut:
                throw OncoAPIError.timeout
            case .notConnectedToInternet, .networkConnectionLost:
                throw OncoAPIError.noConnection
            default:
                throw OncoAPIError.networkError(urlError)
            }
        } catch {
            throw OncoAPIError.networkError(error)
        }

        // Verificar respuesta HTTP
        guard let httpResponse = response as? HTTPURLResponse else {
            throw OncoAPIError.noData
        }

        // Manejar códigos de error
        guard (200...299).contains(httpResponse.statusCode) else {
            // Intentar extraer mensaje de error del body
            var errorMessage: String?
            if let apiError = try? JSONDecoder().decode(APIError.self, from: data) {
                errorMessage = apiError.errorDescription
            }
            throw OncoAPIError.serverError(httpResponse.statusCode, errorMessage)
        }

        // Decodificar respuesta
        do {
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch {
            throw OncoAPIError.decodingError(error)
        }
    }

    // MARK: - Request sin body
    private func performRequest<T: Decodable>(
        endpoint: String,
        method: String
    ) async throws -> T {
        guard let url = URL(string: configuration.baseURL + endpoint) else {
            throw OncoAPIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = configuration.timeoutInterval

        for (key, value) in configuration.defaultHeaders {
            request.setValue(value, forHTTPHeaderField: key)
        }

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch let urlError as URLError {
            switch urlError.code {
            case .timedOut:
                throw OncoAPIError.timeout
            case .notConnectedToInternet, .networkConnectionLost:
                throw OncoAPIError.noConnection
            default:
                throw OncoAPIError.networkError(urlError)
            }
        } catch {
            throw OncoAPIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw OncoAPIError.noData
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            var errorMessage: String?
            if let apiError = try? JSONDecoder().decode(APIError.self, from: data) {
                errorMessage = apiError.errorDescription
            }
            throw OncoAPIError.serverError(httpResponse.statusCode, errorMessage)
        }

        do {
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch {
            throw OncoAPIError.decodingError(error)
        }
    }
}

// MARK: - Extensión para Debug
#if DEBUG
extension OncoAPIService {
    /// Genera una respuesta mock para testing
    func mockConsultation() async -> ClinicalResponse {
        // Simular delay de red
        try? await Task.sleep(nanoseconds: 2_000_000_000)
        return ClinicalResponse.example
    }
}
#endif
