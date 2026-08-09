import Foundation
import Observation

/// The app's in-memory, `@Observable` list of saved locations, backed by
/// `SharedStore` (App Group) so the widget and intents see the same data.
/// Enforces the invariant that exactly one location is primary.
@MainActor
@Observable
final class SavedLocationsStore {
    private(set) var locations: [Location]

    init() {
        var loaded = SharedStore.loadLocations()
        if loaded.isEmpty {
            // Seed a sensible default so a fresh install shows something.
            loaded = [
                Location(
                    name: "Phoenix", adminRegion: "Arizona, United States",
                    latitude: 33.4484, longitude: -112.0740,
                    timeZoneIdentifier: "America/Phoenix", isPrimary: true
                )
            ]
        }
        locations = Self.normalizingPrimary(loaded)
        persist()
    }

    var primary: Location? {
        locations.first(where: \.isPrimary) ?? locations.first
    }

    func add(_ location: Location) {
        var new = location
        if locations.isEmpty { new.isPrimary = true }
        locations.append(new)
        locations = Self.normalizingPrimary(locations)
        persist()
    }

    func remove(_ location: Location) {
        locations.removeAll { $0.id == location.id }
        locations = Self.normalizingPrimary(locations)
        persist()
    }

    func setPrimary(_ location: Location) {
        for index in locations.indices {
            locations[index].isPrimary = locations[index].id == location.id
        }
        persist()
    }

    private func persist() {
        SharedStore.saveLocations(locations)
    }

    /// Guarantee exactly one primary: keep the first flagged one, or promote the
    /// first location when none is flagged.
    private static func normalizingPrimary(_ input: [Location]) -> [Location] {
        guard !input.isEmpty else { return input }
        var result = input
        let primaryIndex = result.firstIndex(where: \.isPrimary) ?? 0
        for index in result.indices {
            result[index].isPrimary = index == primaryIndex
        }
        return result
    }
}
