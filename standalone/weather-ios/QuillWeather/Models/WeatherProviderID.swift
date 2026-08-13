import Foundation

/// Which upstream produced a report. Drives the mandatory attribution surface
/// (PRD §6.1 D-5: any WeatherKit-derived value must show Apple's attribution
/// and legal link).
enum WeatherProviderID: String, Codable, Sendable, CaseIterable {
    case weatherKit
    case openMeteo
    case nws

    var displayName: String {
        switch self {
        case .weatherKit: " Weather"
        case .openMeteo: "Open-Meteo"
        case .nws: "National Weather Service"
        }
    }

    /// The one-line attribution string shown wherever this provider's data
    /// appears.
    var attributionText: String {
        switch self {
        case .weatherKit: "Weather data provided by  Weather."
        case .openMeteo: "Weather data by Open-Meteo.com (CC BY 4.0)."
        case .nws: "Data from the U.S. National Weather Service."
        }
    }

    /// Legal/attribution link. WeatherKit mandates a link to Apple's legal
    /// attribution page; the others link to their terms.
    var attributionURL: URL? {
        switch self {
        case .weatherKit: URL(string: "https://weatherkit.apple.com/legal-attribution.html")
        case .openMeteo: URL(string: "https://open-meteo.com/en/license")
        case .nws: URL(string: "https://www.weather.gov/disclaimer")
        }
    }
}
