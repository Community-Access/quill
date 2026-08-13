import Foundation

/// One hour of forecast.
struct HourlyForecast: Identifiable, Codable, Hashable, Sendable {
    var id: Date { date }
    let date: Date
    let temperature: Measurement<UnitTemperature>
    let condition: WeatherCondition
    /// Probability of precipitation, 0...1.
    let precipitationChance: Double
}
