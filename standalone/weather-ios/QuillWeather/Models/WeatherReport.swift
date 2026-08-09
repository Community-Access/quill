import Foundation

/// The full weather picture for one location at one moment — the unit the UI,
/// the narrator, the widgets, and the App Intents all consume.
struct WeatherReport: Codable, Hashable, Sendable {
    let location: Location
    let current: CurrentConditions
    let hourly: [HourlyForecast]
    let daily: [DailyForecast]
    let alerts: [WeatherAlert]
    /// Primary provider that produced the current conditions. Fusion may draw
    /// other sections from other providers (§6.2); `attributions` lists all.
    let provider: WeatherProviderID
    let attributions: [WeatherProviderID]
    /// When the underlying data was produced (not when it was fetched).
    let asOf: Date

    init(
        location: Location,
        current: CurrentConditions,
        hourly: [HourlyForecast] = [],
        daily: [DailyForecast] = [],
        alerts: [WeatherAlert] = [],
        provider: WeatherProviderID,
        attributions: [WeatherProviderID]? = nil,
        asOf: Date
    ) {
        self.location = location
        self.current = current
        self.hourly = hourly
        self.daily = daily
        self.alerts = alerts
        self.provider = provider
        self.attributions = attributions ?? [provider]
        self.asOf = asOf
    }

    /// The most severe active alert, if any — what the badge/widget "next
    /// alert" surface and the notification tier key off.
    var mostSevereAlert: WeatherAlert? {
        alerts.max { $0.tier < $1.tier }
    }
}
