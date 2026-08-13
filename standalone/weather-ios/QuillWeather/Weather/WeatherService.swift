import Foundation

/// The fusion coordinator (PRD §6). It asks providers in preference order and
/// returns the first that succeeds — the scaffold's simple stand-in for the
/// full per-question fusion in §6.2 (US ground-truth from NWS, worldwide from
/// WeatherKit, Open-Meteo as the keyless floor). Graceful degradation (§6.3) is
/// exactly this fall-through: a provider that throws never takes the app down,
/// it just yields to the next.
struct WeatherService: Sendable {
    let providers: [any WeatherProvider]

    /// Default order: WeatherKit first (best global data, needs the
    /// entitlement), then Open-Meteo (keyless, always available). On the
    /// Simulator or without a WeatherKit-enabled App ID, the first call throws
    /// and Open-Meteo answers — the app still works.
    init(providers: [any WeatherProvider] = [WeatherKitProvider(), OpenMeteoProvider()]) {
        self.providers = providers
    }

    func report(for location: Location) async throws -> WeatherReport {
        var lastError: Error = WeatherProviderError.badResponse
        for provider in providers {
            do {
                return try await provider.report(for: location)
            } catch {
                lastError = error
                continue
            }
        }
        throw lastError
    }
}
