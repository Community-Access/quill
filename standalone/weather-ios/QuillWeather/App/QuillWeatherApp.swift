import SwiftUI

@main
struct QuillWeatherApp: App {
    @State private var settings = AppSettings()
    @State private var locations = SavedLocationsStore()
    @State private var store = WeatherStore()
    @State private var announcer = SpeechAnnouncer()
    @State private var accessibilityActions = AccessibilityActionSettings()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(settings)
                .environment(locations)
                .environment(store)
                .environment(announcer)
                .environment(accessibilityActions)
        }
        // Keeps the badge (W-8) and widgets (W-1) fresh while the app is closed.
        // Opportunistic and user-disable-able, per PRD §8.1 — never a guarantee.
        .backgroundTask(.appRefresh(BackgroundRefresh.identifier)) {
            await BackgroundRefresh.run()
        }
    }
}
