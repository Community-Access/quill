import Foundation

/// One day of forecast.
struct DailyForecast: Identifiable, Codable, Hashable, Sendable {
    var id: Date { date }
    let date: Date
    let highTemperature: Measurement<UnitTemperature>
    let lowTemperature: Measurement<UnitTemperature>
    let condition: WeatherCondition
    /// Probability of precipitation, 0...1.
    let precipitationChance: Double
}
