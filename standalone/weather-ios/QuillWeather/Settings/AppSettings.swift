import Observation

/// User preferences, `@Observable` for SwiftUI and persisted through
/// `SharedStore` so the widget and intents read the same values.
@MainActor
@Observable
final class AppSettings {
    var temperatureUnit: TemperatureUnit {
        didSet { SharedStore.temperatureUnit = temperatureUnit }
    }

    /// PRD §9 W-8. Default off; enabling it replaces the unread-alert count on
    /// the app icon (both share the one badge).
    var showTemperatureBadge: Bool {
        didSet { SharedStore.showTemperatureBadge = showTemperatureBadge }
    }

    init() {
        temperatureUnit = SharedStore.temperatureUnit
        showTemperatureBadge = SharedStore.showTemperatureBadge
    }

    var narrator: Narrator {
        Narrator(units: temperatureUnit)
    }
}
