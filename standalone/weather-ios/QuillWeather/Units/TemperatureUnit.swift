import Foundation

/// The user's preferred temperature scale. Weather values are stored as
/// `Measurement<UnitTemperature>` so conversion is exact; this only decides how
/// they are displayed and spoken.
enum TemperatureUnit: String, CaseIterable, Codable, Sendable, Identifiable {
    case fahrenheit
    case celsius

    var id: Self { self }

    var unit: UnitTemperature {
        switch self {
        case .fahrenheit: .fahrenheit
        case .celsius: .celsius
        }
    }

    /// A short, screen-reader-friendly name ("Fahrenheit", not "°F").
    var spokenName: String {
        switch self {
        case .fahrenheit: "Fahrenheit"
        case .celsius: "Celsius"
        }
    }
}

extension Measurement where UnitType == UnitTemperature {
    /// A compact display string, e.g. `112°`. Whole degrees — weather is never
    /// reported to the app's users with decimals.
    func shortDisplay(in unit: TemperatureUnit) -> String {
        let value = converted(to: unit.unit).value
        return "\(Int(value.rounded()))°"
    }

    /// A spoken string, e.g. `112 degrees`. Used for accessibility labels and
    /// the narrator so VoiceOver never has to interpret a bare number or a
    /// degree glyph.
    func spokenDisplay(in unit: TemperatureUnit) -> String {
        let value = Int(converted(to: unit.unit).value.rounded())
        return "\(value) degrees"
    }

    /// The whole-degree integer used for the app-icon badge (`BadgeManager`).
    func wholeDegrees(in unit: TemperatureUnit) -> Int {
        Int(converted(to: unit.unit).value.rounded())
    }
}
