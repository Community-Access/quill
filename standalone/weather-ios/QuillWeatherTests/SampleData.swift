import Foundation
@testable import QuillWeather

/// Builds a deterministic report for tests.
func sampleReport(
    tempF: Double = 112,
    feelsF: Double = 108,
    condition: String = "sunny",
    provider: WeatherProviderID = .openMeteo,
    name: String = "Phoenix",
    alerts: [WeatherAlert] = []
) -> WeatherReport {
    let location = Location(name: name, latitude: 33.4484, longitude: -112.0740)
    let current = CurrentConditions(
        temperature: .init(value: tempF, unit: .fahrenheit),
        apparentTemperature: .init(value: feelsF, unit: .fahrenheit),
        condition: WeatherCondition(code: condition, symbolName: "sun.max", text: condition),
        humidity: 0.1,
        windSpeed: .init(value: 3, unit: .metersPerSecond),
        isDaylight: true
    )
    return WeatherReport(
        location: location,
        current: current,
        alerts: alerts,
        provider: provider,
        asOf: Date(timeIntervalSince1970: 0)
    )
}
