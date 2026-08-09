import Foundation

/// Keyless, worldwide provider (open-meteo.com). This is the one that actually
/// runs without a paid WeatherKit entitlement, so it doubles as the app's
/// always-available floor. Values are fetched in Celsius + m/s and stored as
/// `Measurement`s; the UI converts to the user's unit at display time.
struct OpenMeteoProvider: WeatherProvider {
    let id: WeatherProviderID = .openMeteo
    var session: URLSession = .shared

    func report(for location: Location) async throws -> WeatherReport {
        var components = URLComponents(string: "https://api.open-meteo.com/v1/forecast")!
        components.queryItems = [
            .init(name: "latitude", value: String(location.latitude)),
            .init(name: "longitude", value: String(location.longitude)),
            .init(name: "timeformat", value: "unixtime"),
            .init(name: "timezone", value: "auto"),
            .init(name: "wind_speed_unit", value: "ms"),
            .init(name: "temperature_unit", value: "celsius"),
            .init(name: "forecast_days", value: "7"),
            .init(
                name: "current",
                value: "temperature_2m,apparent_temperature,relative_humidity_2m,is_day,weather_code,wind_speed_10m"
            ),
            .init(name: "hourly", value: "temperature_2m,weather_code,precipitation_probability"),
            .init(
                name: "daily",
                value: "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            ),
        ]
        guard let url = components.url else { throw WeatherProviderError.badResponse }

        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw WeatherProviderError.badResponse
        }

        let decoded: Payload
        do {
            decoded = try JSONDecoder().decode(Payload.self, from: data)
        } catch {
            throw WeatherProviderError.decoding(String(describing: error))
        }
        return report(from: decoded, location: location)
    }

    // MARK: - Mapping

    private func report(from payload: Payload, location: Location) -> WeatherReport {
        let c = payload.current
        let current = CurrentConditions(
            temperature: .init(value: c.temperature_2m, unit: .celsius),
            apparentTemperature: .init(value: c.apparent_temperature, unit: .celsius),
            condition: Self.condition(code: c.weather_code, isDay: c.is_day == 1),
            humidity: c.relative_humidity_2m / 100,
            windSpeed: .init(value: c.wind_speed_10m, unit: .metersPerSecond),
            isDaylight: c.is_day == 1
        )

        let hourly = zip4(
            payload.hourly.time, payload.hourly.temperature_2m,
            payload.hourly.weather_code, payload.hourly.precipitation_probability
        )
        .prefix(24)
        .map { time, temp, code, pop in
            HourlyForecast(
                date: Date(timeIntervalSince1970: TimeInterval(time)),
                temperature: .init(value: temp, unit: .celsius),
                condition: Self.condition(code: code, isDay: true),
                precipitationChance: Double(pop ?? 0) / 100
            )
        }

        let daily = zip5(
            payload.daily.time, payload.daily.temperature_2m_max,
            payload.daily.temperature_2m_min, payload.daily.weather_code,
            payload.daily.precipitation_probability_max
        )
        .map { time, high, low, code, pop in
            DailyForecast(
                date: Date(timeIntervalSince1970: TimeInterval(time)),
                highTemperature: .init(value: high, unit: .celsius),
                lowTemperature: .init(value: low, unit: .celsius),
                condition: Self.condition(code: code, isDay: true),
                precipitationChance: Double(pop ?? 0) / 100
            )
        }

        return WeatherReport(
            location: location,
            current: current,
            hourly: Array(hourly),
            daily: daily,
            alerts: [], // Open-Meteo carries no alerts; NWS/WeatherKit do.
            provider: .openMeteo,
            asOf: Date(timeIntervalSince1970: TimeInterval(c.time))
        )
    }

    /// Map a WMO weather-interpretation code to a provider-neutral condition.
    static func condition(code: Int, isDay: Bool) -> WeatherCondition {
        let sun = isDay ? "sun.max" : "moon.stars"
        let partly = isDay ? "cloud.sun" : "cloud.moon"
        switch code {
        case 0: return .init(code: "clear", symbolName: sun, text: isDay ? "clear" : "clear skies")
        case 1: return .init(code: "mostlyClear", symbolName: partly, text: "mostly clear")
        case 2: return .init(code: "partlyCloudy", symbolName: partly, text: "partly cloudy")
        case 3: return .init(code: "cloudy", symbolName: "cloud", text: "cloudy")
        case 45, 48: return .init(code: "fog", symbolName: "cloud.fog", text: "foggy")
        case 51, 53, 55: return .init(code: "drizzle", symbolName: "cloud.drizzle", text: "drizzle")
        case 56, 57: return .init(code: "freezingDrizzle", symbolName: "cloud.sleet", text: "freezing drizzle")
        case 61, 63, 65: return .init(code: "rain", symbolName: "cloud.rain", text: "rain")
        case 66, 67: return .init(code: "freezingRain", symbolName: "cloud.sleet", text: "freezing rain")
        case 71, 73, 75, 77: return .init(code: "snow", symbolName: "cloud.snow", text: "snow")
        case 80, 81, 82: return .init(code: "showers", symbolName: "cloud.heavyrain", text: "rain showers")
        case 85, 86: return .init(code: "snowShowers", symbolName: "cloud.snow", text: "snow showers")
        case 95: return .init(code: "thunderstorms", symbolName: "cloud.bolt.rain", text: "thunderstorms")
        case 96, 99: return .init(code: "hailstorms", symbolName: "cloud.bolt.rain", text: "thunderstorms with hail")
        default: return .unknown
        }
    }

    // MARK: - DTOs

    private struct Payload: Decodable {
        let current: Current
        let hourly: Hourly
        let daily: Daily
    }

    private struct Current: Decodable {
        let time: Int
        let temperature_2m: Double
        let apparent_temperature: Double
        let relative_humidity_2m: Double
        let is_day: Int
        let weather_code: Int
        let wind_speed_10m: Double
    }

    private struct Hourly: Decodable {
        let time: [Int]
        let temperature_2m: [Double]
        let weather_code: [Int]
        let precipitation_probability: [Int?]
    }

    private struct Daily: Decodable {
        let time: [Int]
        let weather_code: [Int]
        let temperature_2m_max: [Double]
        let temperature_2m_min: [Double]
        let precipitation_probability_max: [Int?]
    }
}

// Small zip helpers — Swift's stdlib only ships the two-sequence `zip`.
private func zip4<A, B, C, D>(
    _ a: [A], _ b: [B], _ c: [C], _ d: [D]
) -> [(A, B, C, D)] {
    let n = min(min(a.count, b.count), min(c.count, d.count))
    return (0..<n).map { (a[$0], b[$0], c[$0], d[$0]) }
}

private func zip5<A, B, C, D, E>(
    _ a: [A], _ b: [B], _ c: [C], _ d: [D], _ e: [E]
) -> [(A, B, C, D, E)] {
    let n = min(min(min(a.count, b.count), min(c.count, d.count)), e.count)
    return (0..<n).map { (a[$0], b[$0], c[$0], d[$0], e[$0]) }
}
