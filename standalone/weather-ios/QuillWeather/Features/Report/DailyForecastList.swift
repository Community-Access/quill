import SwiftUI

struct DailyForecastList: View {
    @Environment(AppSettings.self) private var settings
    let days: [DailyForecast]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("7-Day Forecast")
                .font(.headline)
            ForEach(days) { day in
                HStack {
                    Text(day.date, format: .dateTime.weekday(.wide))
                        .frame(width: 110, alignment: .leading)
                    Image(systemName: day.condition.symbolName)
                        .symbolRenderingMode(.multicolor)
                    Spacer()
                    Text(day.lowTemperature.shortDisplay(in: settings.temperatureUnit))
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                    Text(day.highTemperature.shortDisplay(in: settings.temperatureUnit))
                        .monospacedDigit()
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(label(for: day))
            }
        }
    }

    private func label(for day: DailyForecast) -> String {
        let weekday = day.date.formatted(.dateTime.weekday(.wide))
        let high = day.highTemperature.spokenDisplay(in: settings.temperatureUnit)
        let low = day.lowTemperature.spokenDisplay(in: settings.temperatureUnit)
        return "\(weekday), \(day.condition.text), high \(high), low \(low)"
    }
}
