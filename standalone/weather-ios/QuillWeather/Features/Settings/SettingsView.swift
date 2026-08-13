import SwiftUI

struct SettingsView: View {
    @Environment(AppSettings.self) private var settings
    @Environment(SavedLocationsStore.self) private var locations
    @Environment(WeatherStore.self) private var store
    @Environment(AccessibilityActionSettings.self) private var actions

    var body: some View {
        @Bindable var settings = settings
        @Bindable var actions = actions
        Form {
            Section("Units") {
                Picker("Temperature", selection: $settings.temperatureUnit) {
                    ForEach(TemperatureUnit.allCases) { unit in
                        Text(unit.spokenName).tag(unit)
                    }
                }
            }

            Section {
                Toggle("Show current temperature on the app icon", isOn: $settings.showTemperatureBadge)
            } footer: {
                // The honest constraints from PRD §9 W-8, in the user's words.
                Text("""
                The badge is a whole number like 112 — no degree sign, no decimals — and it can't show below zero. \
                It refreshes in the background, so treat it as approximate, not live. Turning this on replaces the \
                unread-alert count on the app icon.
                """)
            }

            Section {
                Toggle("“Speak weather” action", isOn: $actions.speakActionEnabled)
                Toggle("“Make primary” and “Delete” actions", isOn: $actions.quickManagementActionsEnabled)
            } header: {
                Text("VoiceOver Actions")
            } footer: {
                Text("Choose which actions appear in VoiceOver's rotor on location rows and the weather card. Turn a category off if you find the rotor noisy.")
            }
        }
        .navigationTitle("Settings")
        .onChange(of: settings.temperatureUnit) {
            Task { await store.reconcileGlanceSurfaces(primary: locations.primary, settings: settings) }
        }
        .onChange(of: settings.showTemperatureBadge) {
            Task {
                if settings.showTemperatureBadge {
                    await BadgeManager.requestAuthorization()
                }
                await store.reconcileGlanceSurfaces(primary: locations.primary, settings: settings)
            }
        }
    }
}
