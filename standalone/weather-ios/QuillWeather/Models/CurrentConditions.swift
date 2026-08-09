import Foundation

/// A point-in-time observation/estimate for a location.
struct CurrentConditions: Codable, Hashable, Sendable {
    var temperature: Measurement<UnitTemperature>
    var apparentTemperature: Measurement<UnitTemperature>
    var condition: WeatherCondition
    /// Relative humidity, 0...1.
    var humidity: Double
    var windSpeed: Measurement<UnitSpeed>
    var isDaylight: Bool

    init(
        temperature: Measurement<UnitTemperature>,
        apparentTemperature: Measurement<UnitTemperature>,
        condition: WeatherCondition,
        humidity: Double,
        windSpeed: Measurement<UnitSpeed>,
        isDaylight: Bool
    ) {
        self.temperature = temperature
        self.apparentTemperature = apparentTemperature
        self.condition = condition
        self.humidity = humidity
        self.windSpeed = windSpeed
        self.isDaylight = isDaylight
    }
}
