import SwiftUI
import WidgetKit

struct CurrentConditionsWidgetView: View {
    let entry: WeatherEntry

    var body: some View {
        if let report = entry.report {
            let narrator = Narrator(units: entry.unit)
            VStack(alignment: .leading, spacing: 4) {
                Text(report.location.name)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack {
                    Text(report.current.temperature.shortDisplay(in: entry.unit))
                        .font(.system(size: 40, weight: .semibold, design: .rounded))
                    Image(systemName: report.current.condition.symbolName)
                        .symbolRenderingMode(.multicolor)
                        .font(.title2)
                }
                Text(report.current.condition.text.capitalized)
                    .font(.caption)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("\(narrator.quickWeather(for: report)) \(narrator.freshness(report.asOf, now: entry.date)).")
        } else {
            ContentUnavailableView("No location", systemImage: "location.slash")
                .accessibilityLabel("No primary location set. Open Quill Weather to add one.")
        }
    }
}
