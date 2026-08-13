import SwiftUI

struct RootView: View {
    @Environment(SavedLocationsStore.self) private var locations
    @Environment(WeatherStore.self) private var store
    @Environment(AppSettings.self) private var settings

    var body: some View {
        TabView {
            Tab("Weather", systemImage: "cloud.sun") {
                WeatherTab()
            }
            Tab("Quick", systemImage: "bolt.fill") {
                NavigationStack { QuickWeatherView() }
            }
            Tab("Settings", systemImage: "gearshape") {
                NavigationStack { SettingsView() }
            }
        }
        .task {
            BackgroundRefresh.schedule()
            await store.refreshAll(locations.locations, settings: settings)
        }
    }
}
