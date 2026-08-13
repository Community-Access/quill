import Foundation

/// A source of weather for a location. Providers are `Sendable` value types with
/// a single async entry point, so they can be called from any actor (the app's
/// `WeatherStore`, a widget's timeline provider, or a background task).
protocol WeatherProvider: Sendable {
    var id: WeatherProviderID { get }
    /// Fetch a full report, or throw. Fusion (`WeatherService`) decides what to
    /// do with a failure — usually fall through to the next provider.
    func report(for location: Location) async throws -> WeatherReport
}

/// Errors a provider can surface.
enum WeatherProviderError: Error, Sendable {
    case unsupportedRegion
    case badResponse
    case decoding(String)
}
