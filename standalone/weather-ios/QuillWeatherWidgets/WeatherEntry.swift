import WidgetKit

/// One timeline snapshot for the widgets. Carries the cached/fresh report and
/// the user's unit so the views need no environment.
struct WeatherEntry: TimelineEntry {
    let date: Date
    let report: WeatherReport?
    let unit: TemperatureUnit

    static let placeholder = WeatherEntry(
        date: .now,
        report: nil,
        unit: .fahrenheit
    )
}
