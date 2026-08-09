import CoreLocation
import Observation

/// Thin, `@Observable` wrapper over `CLLocationManager` for one-shot "where am
/// I" lookups when adding the current location. CoreLocation delivers its
/// delegate callbacks on the queue the manager was created on (the main actor
/// here), so the `nonisolated` delegate methods hop back with
/// `MainActor.assumeIsolated`.
@MainActor
@Observable
final class LocationManager: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private(set) var authorizationStatus: CLAuthorizationStatus = .notDetermined
    private var continuation: CheckedContinuation<CLLocation, Error>?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
        authorizationStatus = manager.authorizationStatus
    }

    func requestWhenInUseAuthorization() {
        manager.requestWhenInUseAuthorization()
    }

    /// One-shot current location. Throws `CLError` on failure or denial.
    func requestLocation() async throws -> CLLocation {
        if continuation != nil {
            throw CLError(.locationUnknown) // a request is already in flight
        }
        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            manager.requestLocation()
        }
    }

    // MARK: - CLLocationManagerDelegate

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        MainActor.assumeIsolated {
            authorizationStatus = manager.authorizationStatus
        }
    }

    nonisolated func locationManager(
        _ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]
    ) {
        MainActor.assumeIsolated {
            guard let location = locations.last else { return }
            continuation?.resume(returning: location)
            continuation = nil
        }
    }

    nonisolated func locationManager(
        _ manager: CLLocationManager, didFailWithError error: Error
    ) {
        MainActor.assumeIsolated {
            continuation?.resume(throwing: error)
            continuation = nil
        }
    }
}
