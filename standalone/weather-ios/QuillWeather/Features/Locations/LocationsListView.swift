import SwiftUI

struct LocationsListView: View {
    @Environment(SavedLocationsStore.self) private var locations
    @Environment(WeatherStore.self) private var store
    @Environment(AppSettings.self) private var settings
    @Binding var selectedLocationID: UUID?
    @State private var showingAdd = false

    var body: some View {
        List(selection: $selectedLocationID) {
            ForEach(locations.locations) { location in
                LocationRow(location: location)
                    .tag(location.id)
                    .swipeActions(edge: .leading) {
                        Button("Make Primary", systemImage: "star") {
                            locations.setPrimary(location)
                            Task { await store.reconcileGlanceSurfaces(primary: location, settings: settings) }
                        }
                        .tint(.yellow)
                    }
            }
            .onDelete(perform: delete)
        }
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Add Location", systemImage: "plus") { showingAdd = true }
            }
        }
        .sheet(isPresented: $showingAdd) {
            AddLocationView()
        }
        .refreshable {
            await store.refreshAll(locations.locations, settings: settings)
        }
        .overlay {
            if locations.locations.isEmpty {
                ContentUnavailableView(
                    "No locations",
                    systemImage: "location.slash",
                    description: Text("Add a location to start tracking its weather.")
                )
            }
        }
    }

    private func delete(_ offsets: IndexSet) {
        for location in offsets.map({ locations.locations[$0] }) {
            locations.remove(location)
        }
    }
}
