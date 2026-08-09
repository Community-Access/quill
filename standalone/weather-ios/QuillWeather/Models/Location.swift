import CoreLocation
import Foundation

/// A place the user tracks. Stored as plain coordinates (not a
/// `CLLocationCoordinate2D`, which is neither `Codable` nor reliably
/// `Sendable`) so it persists and crosses actor boundaries cleanly.
struct Location: Identifiable, Codable, Hashable, Sendable {
    let id: UUID
    /// User-facing name, e.g. "Phoenix".
    var name: String
    /// Disambiguating region, e.g. "Arizona, United States".
    var adminRegion: String
    var latitude: Double
    var longitude: Double
    /// IANA identifier, e.g. "America/Phoenix", so times display in the
    /// location's own zone rather than the device's.
    var timeZoneIdentifier: String
    /// The one location that drives the badge, the default widget, and Quick
    /// Weather. Exactly one saved location is primary (`SavedLocationsStore`
    /// enforces it).
    var isPrimary: Bool

    init(
        id: UUID = UUID(),
        name: String,
        adminRegion: String = "",
        latitude: Double,
        longitude: Double,
        timeZoneIdentifier: String = TimeZone.current.identifier,
        isPrimary: Bool = false
    ) {
        self.id = id
        self.name = name
        self.adminRegion = adminRegion
        self.latitude = latitude
        self.longitude = longitude
        self.timeZoneIdentifier = timeZoneIdentifier
        self.isPrimary = isPrimary
    }

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    var timeZone: TimeZone {
        TimeZone(identifier: timeZoneIdentifier) ?? .current
    }

    /// Spoken/label form: "Phoenix, Arizona, United States" when a region is
    /// known, otherwise just the name.
    var spokenName: String {
        adminRegion.isEmpty ? name : "\(name), \(adminRegion)"
    }
}
