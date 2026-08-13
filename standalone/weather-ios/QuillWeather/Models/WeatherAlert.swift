import Foundation

/// A severe-weather alert, normalized across providers. The `tier` maps onto
/// the PRD's delivery tiers (§8.1) that decide notification urgency.
struct WeatherAlert: Identifiable, Codable, Hashable, Sendable {
    /// Delivery tier, ordered least-to-most severe.
    enum Tier: Int, Codable, Sendable, Comparable {
        case routine
        case advisory
        case watch
        case warning
        case urgent
        case critical

        static func < (lhs: Tier, rhs: Tier) -> Bool { lhs.rawValue < rhs.rawValue }

        var spokenName: String {
            switch self {
            case .routine: "routine"
            case .advisory: "advisory"
            case .watch: "watch"
            case .warning: "warning"
            case .urgent: "urgent"
            case .critical: "critical"
            }
        }
    }

    let id: String
    let tier: Tier
    /// Short headline, e.g. "Excessive Heat Warning".
    let headline: String
    /// The full official text (NWS returns this; WeatherKit returns a summary).
    let detail: String
    let source: String
    /// Affected area description, e.g. "Maricopa County".
    let area: String
    let effective: Date
    let expires: Date?
}
