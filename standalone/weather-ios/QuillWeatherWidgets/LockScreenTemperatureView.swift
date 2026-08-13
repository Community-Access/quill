import SwiftUI
import WidgetKit

struct LockScreenTemperatureView: View {
    @Environment(\.widgetFamily) private var family
    let entry: WeatherEntry

    var body: some View {
        content
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(accessibilityLabel)
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .accessoryInline:
            // The inline slot is a single line beside the clock.
            Label("\(shortTemperature) \(conditionText)", systemImage: symbolName)

        case .accessoryCircular:
            ZStack {
                AccessoryWidgetBackground()
                VStack(spacing: 0) {
                    Image(systemName: symbolName)
                        .font(.caption2)
                    Text(shortTemperature)
                        .font(.headline)
                        .minimumScaleFactor(0.6) // keep triple digits legible
                }
            }

        case .accessoryRectangular:
            HStack(spacing: 8) {
                Image(systemName: symbolName)
                    .font(.title2)
                VStack(alignment: .leading, spacing: 0) {
                    Text(shortTemperature)
                        .font(.headline)
                    Text(conditionText)
                        .font(.caption)
                }
            }

        default:
            Text(shortTemperature)
        }
    }

    // MARK: - Derived content

    private var shortTemperature: String {
        entry.report?.current.temperature.shortDisplay(in: entry.unit) ?? "--°"
    }

    private var conditionText: String {
        entry.report?.current.condition.text.capitalized ?? "No data"
    }

    private var symbolName: String {
        entry.report?.current.condition.symbolName ?? "thermometer.medium"
    }

    private var accessibilityLabel: String {
        guard let report = entry.report else {
            return "No primary location set. Open Quill Weather to add one."
        }
        let narrator = Narrator(units: entry.unit)
        let temperature = report.current.temperature.spokenDisplay(in: entry.unit)
        return "\(temperature), \(report.current.condition.text). \(narrator.freshness(report.asOf, now: entry.date))."
    }
}
