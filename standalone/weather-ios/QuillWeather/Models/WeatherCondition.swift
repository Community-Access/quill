import Foundation

/// A provider-neutral weather condition. Each provider maps its own raw code
/// into this so the rest of the app (UI, narrator, widgets) never branches on a
/// provider's vocabulary.
struct WeatherCondition: Codable, Hashable, Sendable {
    /// Stable code, e.g. "clear", "partlyCloudy", "rain", "thunderstorms".
    let code: String
    /// SF Symbol name, e.g. "sun.max", "cloud.rain". Chosen day/night aware by
    /// the provider when it knows daylight.
    let symbolName: String
    /// Human, spoken-first description, e.g. "partly cloudy". Lowercased so it
    /// drops naturally into the narrator's sentence.
    let text: String

    init(code: String, symbolName: String, text: String) {
        self.code = code
        self.symbolName = symbolName
        self.text = text
    }

    static let unknown = WeatherCondition(
        code: "unknown", symbolName: "cloud", text: "unknown conditions"
    )
}
