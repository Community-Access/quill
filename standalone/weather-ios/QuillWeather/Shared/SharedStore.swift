import Foundation

/// The App Group bridge shared by the app and the widget/intent extensions. It
/// persists the saved locations and caches the most recent report per location
/// so a widget can render instantly and the badge can be set without a network
/// round-trip. Pure value APIs, `Sendable`, safe to call from any actor.
enum SharedStore {
    /// Must match the App Group in both targets' entitlements.
    static let appGroup = "group.com.communityaccess.quillweather"

    private static var defaults: UserDefaults {
        UserDefaults(suiteName: appGroup) ?? .standard
    }

    private enum Key {
        static let locations = "savedLocations"
        static let temperatureUnit = "temperatureUnit"
        static let showTemperatureBadge = "showTemperatureBadge"
        static let speakRotorAction = "a11y.speakRotorAction"
        static let quickManagementActions = "a11y.quickManagementActions"
        static func report(_ id: UUID) -> String { "report.\(id.uuidString)" }
    }

    /// Reads a Bool that defaults to `true` when it has never been set.
    private static func bool(_ key: String, default defaultValue: Bool) -> Bool {
        defaults.object(forKey: key) as? Bool ?? defaultValue
    }

    // MARK: - Locations

    static func loadLocations() -> [Location] {
        guard let data = defaults.data(forKey: Key.locations) else { return [] }
        return (try? JSONDecoder().decode([Location].self, from: data)) ?? []
    }

    static func saveLocations(_ locations: [Location]) {
        guard let data = try? JSONEncoder().encode(locations) else { return }
        defaults.set(data, forKey: Key.locations)
    }

    static var primaryLocation: Location? {
        let all = loadLocations()
        return all.first(where: \.isPrimary) ?? all.first
    }

    // MARK: - Units

    static var temperatureUnit: TemperatureUnit {
        get {
            (defaults.string(forKey: Key.temperatureUnit)).flatMap(TemperatureUnit.init) ?? .fahrenheit
        }
        set { defaults.set(newValue.rawValue, forKey: Key.temperatureUnit) }
    }

    /// W-8 opt-in badge toggle. Default off.
    static var showTemperatureBadge: Bool {
        get { defaults.bool(forKey: Key.showTemperatureBadge) }
        set { defaults.set(newValue, forKey: Key.showTemperatureBadge) }
    }

    // MARK: - Configurable VoiceOver actions (PRD §5.2)

    /// Expose a "Speak weather" rotor action on rows and cards. Default on.
    static var speakRotorActionEnabled: Bool {
        get { bool(Key.speakRotorAction, default: true) }
        set { defaults.set(newValue, forKey: Key.speakRotorAction) }
    }

    /// Expose "Make primary" / "Delete" rotor actions on location rows. Default on.
    static var quickManagementActionsEnabled: Bool {
        get { bool(Key.quickManagementActions, default: true) }
        set { defaults.set(newValue, forKey: Key.quickManagementActions) }
    }

    // MARK: - Cached reports

    static func cacheReport(_ report: WeatherReport) {
        guard let data = try? JSONEncoder().encode(report) else { return }
        defaults.set(data, forKey: Key.report(report.location.id))
    }

    static func cachedReport(for id: UUID) -> WeatherReport? {
        guard let data = defaults.data(forKey: Key.report(id)) else { return nil }
        return try? JSONDecoder().decode(WeatherReport.self, from: data)
    }
}
