import SwiftUI

/// List-detail weather browsing. `NavigationSplitView` gives iPad/Mac a sidebar
/// and collapses to a stack on iPhone.
struct WeatherTab: View {
    @Environment(SavedLocationsStore.self) private var locations
    @State private var selectedLocationID: UUID?

    var body: some View {
        NavigationSplitView {
            LocationsListView(selectedLocationID: $selectedLocationID)
                .navigationTitle("Weather")
        } detail: {
            if let id = selectedLocationID,
               let location = locations.locations.first(where: { $0.id == id }) {
                NavigationStack {
                    WeatherReportView(location: location)
                }
            } else {
                ContentUnavailableView(
                    "Choose a location",
                    systemImage: "location.circle",
                    description: Text("Pick a saved location to see its full weather.")
                )
            }
        }
        .onAppear {
            if selectedLocationID == nil {
                selectedLocationID = locations.primary?.id
            }
        }
    }
}
