import SwiftUI

struct HourlyStripView: View {
    @Environment(AppSettings.self) private var settings
    let hours: [HourlyForecast]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Hourly")
                .font(.headline)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 20) {
                    ForEach(hours) { hour in
                        VStack(spacing: 6) {
                            Text(hour.date, format: .dateTime.hour())
                            Image(systemName: hour.condition.symbolName)
                                .symbolRenderingMode(.multicolor)
                            Text(hour.temperature.shortDisplay(in: settings.temperatureUnit))
                                .monospacedDigit()
                        }
                        .font(.callout)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel(label(for: hour))
                    }
                }
                .padding(.vertical, 4)
            }
        }
    }

    private func label(for hour: HourlyForecast) -> String {
        let time = hour.date.formatted(.dateTime.hour())
        var text = "At \(time), \(hour.temperature.spokenDisplay(in: settings.temperatureUnit)), \(hour.condition.text)"
        if hour.precipitationChance >= 0.1 {
            text += ", \(Int((hour.precipitationChance * 100).rounded())) percent chance of precipitation"
        }
        return text
    }
}
