import SwiftUI

/// One row in the locations list. The whole row is a single VoiceOver element
/// whose label is the narrator's full sentence, so a swipe reads "In Phoenix
/// it's 112 degrees and sunny…" rather than three disconnected fragments.
///
/// The row also carries VoiceOver *actions* (PRD §5.2): from the rotor a
/// VoiceOver user can Speak, Make Primary, or Delete without leaving the row —
/// the same affordances sighted users get from swipe actions. Which actions
/// appear is configurable (`AccessibilityActionSettings`).
struct LocationRow: View {
    @Environment(WeatherStore.self) private var store
    @Environment(SavedLocationsStore.self) private var locations
    @Environment(AppSettings.self) private var settings
    @Environment(SpeechAnnouncer.self) private var announcer
    @Environment(AccessibilityActionSettings.self) private var actions
    let location: Location

    var body: some View {
        let report = store.report(for: location)
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(location.name)
                    .font(.headline)
                if location.isPrimary {
                    Text("Primary")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            if let report {
                Text(report.current.temperature.shortDisplay(in: settings.temperatureUnit))
                    .font(.title3.weight(.semibold))
                    .monospacedDigit()
            } else if store.isLoading(location) {
                ProgressView()
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(label(for: report))
        .accessibilityActions {
            if actions.speakActionEnabled, let report {
                Button("Speak weather") {
                    announcer.speak(settings.narrator.quickWeather(for: report))
                }
            }
            if actions.quickManagementActionsEnabled {
                if !location.isPrimary {
                    Button("Make primary") {
                        locations.setPrimary(location)
                        Task { await store.reconcileGlanceSurfaces(primary: location, settings: settings) }
                    }
                }
                Button("Delete", role: .destructive) {
                    locations.remove(location)
                }
            }
        }
    }

    private func label(for report: WeatherReport?) -> String {
        guard let report else { return "\(location.spokenName), loading weather" }
        return settings.narrator.quickWeather(for: report)
    }
}
