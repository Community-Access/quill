import SwiftUI

/// The three-second promise (PRD §3): the primary location's weather as one
/// sentence, front and center, speakable in a tap.
struct QuickWeatherView: View {
    @Environment(SavedLocationsStore.self) private var locations
    @Environment(WeatherStore.self) private var store
    @Environment(AppSettings.self) private var settings
    @State private var announcer = SpeechAnnouncer()

    var body: some View {
        Group {
            if let primary = locations.primary, let report = store.report(for: primary) {
                content(primary: primary, report: report)
            } else if let primary = locations.primary {
                ProgressView("Loading \(primary.name)…")
                    .task { await store.refresh(primary) }
            } else {
                ContentUnavailableView(
                    "No primary location",
                    systemImage: "location",
                    description: Text("Add a location to see Quick Weather.")
                )
            }
        }
        .navigationTitle("Quick Weather")
    }

    @ViewBuilder
    private func content(primary: Location, report: WeatherReport) -> some View {
        let sentence = settings.narrator.quickWeather(for: report)
        VStack(spacing: 28) {
            Text(sentence)
                .font(.title2)
                .multilineTextAlignment(.center)
                .accessibilityAddTraits(.updatesFrequently)
            Button("Speak", systemImage: "speaker.wave.2.fill") {
                announcer.speak(sentence)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding()
        .task(id: primary.id) {
            if store.report(for: primary) == nil {
                await store.refresh(primary)
            }
        }
    }
}
