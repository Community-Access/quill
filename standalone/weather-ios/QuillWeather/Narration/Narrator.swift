import Foundation

/// Turns a `WeatherReport` into the one spoken sentence that is the app's
/// contract (PRD §3, the three-second promise). The same text is used as the
/// UI's `accessibilityLabel`, the widget's label, and the App Intent's spoken
/// result, so VoiceOver, a widget, and Siri all say exactly the same thing.
struct Narrator: Sendable {
    var units: TemperatureUnit

    init(units: TemperatureUnit = .fahrenheit) {
        self.units = units
    }

    /// e.g. "In Phoenix it's 112 degrees and sunny, feeling like 108 degrees.
    /// Excessive Heat Warning in effect until 8 PM."
    func quickWeather(for report: WeatherReport) -> String {
        let current = report.current
        let temp = current.temperature.spokenDisplay(in: units)
        var sentence = "In \(report.location.name) it's \(temp) and \(current.condition.text)"

        let feels = current.apparentTemperature
        let apparentDelta = abs(
            feels.converted(to: units.unit).value
                - current.temperature.converted(to: units.unit).value
        )
        if apparentDelta >= 3 {
            sentence += ", feeling like \(feels.spokenDisplay(in: units))"
        }
        sentence += "."

        if let alert = report.mostSevereAlert {
            sentence += " \(alert.headline) in effect\(alertWindow(alert))."
        }
        return sentence
    }

    /// A compact glance string for a widget's secondary line, e.g.
    /// "112°, sunny".
    func glance(for report: WeatherReport) -> String {
        "\(report.current.temperature.shortDisplay(in: units)), \(report.current.condition.text)"
    }

    /// A spoken freshness clause for widgets/badges, e.g. "updated 8 minutes
    /// ago". WidgetKit refreshes on a budgeted timeline, so surfaces state their
    /// age rather than implying live data (PRD §9 W-1).
    func freshness(_ asOf: Date, now: Date = .now) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return "updated \(formatter.localizedString(for: asOf, relativeTo: now))"
    }

    private func alertWindow(_ alert: WeatherAlert) -> String {
        guard let expires = alert.expires else { return "" }
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        formatter.dateStyle = .none
        formatter.timeZone = alert.expires == nil ? .current : TimeZone.current
        return " until \(formatter.string(from: expires))"
    }
}
