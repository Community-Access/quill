import SwiftUI

/// The headline "now" card. Combined into one VoiceOver element labelled with
/// the narrator's sentence, so it is read as one coherent statement.
struct CurrentConditionsCard: View {
    @Environment(AppSettings.self) private var settings
    @Environment(WeatherStore.self) private var store
    @Environment(SpeechAnnouncer.self) private var announcer
    @Environment(AccessibilityActionSettings.self) private var actions
    let report: WeatherReport

    private var current: CurrentConditions { report.current }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(current.temperature.shortDisplay(in: settings.temperatureUnit))
                    .font(.system(size: 72, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                Image(systemName: current.condition.symbolName)
                    .font(.system(size: 44))
                    .symbolRenderingMode(.multicolor)
            }
            Text(current.condition.text.capitalized)
                .font(.title3)
            Text("Feels like \(current.apparentTemperature.shortDisplay(in: settings.temperatureUnit))")
                .foregroundStyle(.secondary)
            HStack(spacing: 16) {
                Label("\(Int((current.humidity * 100).rounded()))%", systemImage: "humidity")
                Label(windDescription, systemImage: "wind")
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(settings.narrator.quickWeather(for: report))
        .accessibilityActions {
            if actions.speakActionEnabled {
                Button("Speak weather") {
                    announcer.speak(settings.narrator.quickWeather(for: report))
                }
            }
            Button("Refresh") {
                Task { await store.refresh(report.location) }
            }
        }
    }

    private var windDescription: String {
        let mph = current.windSpeed.converted(to: .milesPerHour).value
        return "\(Int(mph.rounded())) mph"
    }
}
