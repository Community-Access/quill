import CoreLocation
import Foundation
import WeatherKit

/// Apple WeatherKit provider (PRD §6, F-22). Requires the WeatherKit capability
/// and a registered App ID (paid Apple Developer account); without it,
/// `weather(for:)` throws at runtime and `WeatherService` falls through to
/// `OpenMeteoProvider`. WeatherKit already vends `Measurement`s, so mapping is
/// mostly renaming. WeatherKit's own types are fully qualified to avoid clashing
/// with this app's `WeatherCondition` / `WeatherAlert` / `WeatherService`.
struct WeatherKitProvider: WeatherProvider {
    let id: WeatherProviderID = .weatherKit

    func report(for location: Location) async throws -> WeatherReport {
        let clLocation = CLLocation(latitude: location.latitude, longitude: location.longitude)
        let weather = try await WeatherKit.WeatherService.shared.weather(for: clLocation)

        let current = Self.map(current: weather.currentWeather)
        let hourly = weather.hourlyForecast.forecast.prefix(24).map(Self.map(hour:))
        let daily = weather.dailyForecast.forecast.prefix(7).map(Self.map(day:))
        let alerts = (weather.weatherAlerts ?? []).map(Self.map(alert:))

        return WeatherReport(
            location: location,
            current: current,
            hourly: Array(hourly),
            daily: Array(daily),
            alerts: alerts,
            provider: .weatherKit,
            asOf: weather.currentWeather.date
        )
    }

    // MARK: - Mapping

    private static func map(current w: WeatherKit.CurrentWeather) -> CurrentConditions {
        CurrentConditions(
            temperature: w.temperature,
            apparentTemperature: w.apparentTemperature,
            condition: condition(w.condition, symbol: w.symbolName),
            humidity: w.humidity,
            windSpeed: w.wind.speed,
            isDaylight: w.isDaylight
        )
    }

    private static func map(hour h: WeatherKit.HourWeather) -> HourlyForecast {
        HourlyForecast(
            date: h.date,
            temperature: h.temperature,
            condition: condition(h.condition, symbol: h.symbolName),
            precipitationChance: h.precipitationChance
        )
    }

    private static func map(day d: WeatherKit.DayWeather) -> DailyForecast {
        DailyForecast(
            date: d.date,
            highTemperature: d.highTemperature,
            lowTemperature: d.lowTemperature,
            condition: condition(d.condition, symbol: d.symbolName),
            precipitationChance: d.precipitationChance
        )
    }

    private static func map(alert a: WeatherKit.WeatherAlert) -> WeatherAlert {
        WeatherAlert(
            id: a.summary,
            tier: tier(for: a.severity),
            headline: a.summary,
            detail: a.summary, // WeatherKit returns a summary; NWS carries full text.
            source: a.source,
            area: a.region ?? "",
            effective: .now,
            expires: nil
        )
    }

    private static func condition(
        _ condition: WeatherKit.WeatherCondition, symbol: String
    ) -> WeatherCondition {
        WeatherCondition(
            code: String(describing: condition),
            symbolName: symbol,
            text: condition.description.lowercased()
        )
    }

    private static func tier(for severity: WeatherKit.WeatherSeverity) -> WeatherAlert.Tier {
        switch severity {
        case .minor: .advisory
        case .moderate: .watch
        case .severe: .warning
        case .extreme: .critical
        case .unknown: .advisory
        @unknown default: .advisory
        }
    }
}
