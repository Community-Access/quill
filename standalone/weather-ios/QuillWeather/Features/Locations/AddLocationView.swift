import CoreLocation
import SwiftUI

struct AddLocationView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(SavedLocationsStore.self) private var locations
    @Environment(WeatherStore.self) private var store
    @Environment(AppSettings.self) private var settings

    @State private var locationManager = LocationManager()
    @State private var query = ""
    @State private var isWorking = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Search") {
                    TextField("City or place", text: $query)
                        .submitLabel(.search)
                        .onSubmit { Task { await search() } }
                    Button("Search", systemImage: "magnifyingglass") {
                        Task { await search() }
                    }
                    .disabled(query.trimmingCharacters(in: .whitespaces).isEmpty || isWorking)
                }
                Section {
                    Button("Use My Current Location", systemImage: "location") {
                        Task { await useCurrentLocation() }
                    }
                    .disabled(isWorking)
                }
                if let errorMessage {
                    Section {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Add Location")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
            .overlay {
                if isWorking { ProgressView().controlSize(.large) }
            }
        }
    }

    private func search() async {
        await withWork {
            let placemarks = try await geocode(address: query)
            guard let placemark = placemarks.first, let location = location(from: placemark) else {
                errorMessage = "No place matched “\(query)”."
                return
            }
            await add(location)
        }
    }

    private func useCurrentLocation() async {
        await withWork {
            locationManager.requestWhenInUseAuthorization()
            let clLocation = try await locationManager.requestLocation()
            let placemarks = try await reverseGeocode(clLocation)
            guard let placemark = placemarks.first, let location = location(from: placemark) else {
                errorMessage = "Couldn't name your current location."
                return
            }
            await add(location)
        }
    }

    private func add(_ location: Location) async {
        locations.add(location)
        await store.refresh(location)
        dismiss()
    }

    private func location(from placemark: CLPlacemark) -> Location? {
        guard let coordinate = placemark.location?.coordinate else { return nil }
        let name = placemark.locality ?? placemark.name ?? query
        let region = [placemark.administrativeArea, placemark.country]
            .compactMap { $0 }
            .joined(separator: ", ")
        return Location(
            name: name,
            adminRegion: region,
            latitude: coordinate.latitude,
            longitude: coordinate.longitude,
            timeZoneIdentifier: placemark.timeZone?.identifier ?? TimeZone.current.identifier
        )
    }

    private func withWork(_ body: () async throws -> Void) async {
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            try await body()
        } catch {
            errorMessage = "Something went wrong. Please try again."
        }
    }

    // CLGeocoder is completion-based; wrap its two calls as async.
    private func geocode(address: String) async throws -> [CLPlacemark] {
        try await withCheckedThrowingContinuation { continuation in
            CLGeocoder().geocodeAddressString(address) { placemarks, error in
                if let error { continuation.resume(throwing: error) }
                else { continuation.resume(returning: placemarks ?? []) }
            }
        }
    }

    private func reverseGeocode(_ location: CLLocation) async throws -> [CLPlacemark] {
        try await withCheckedThrowingContinuation { continuation in
            CLGeocoder().reverseGeocodeLocation(location) { placemarks, error in
                if let error { continuation.resume(throwing: error) }
                else { continuation.resume(returning: placemarks ?? []) }
            }
        }
    }
}
