import Foundation
import UserNotifications

/// PRD §9 W-8 — the opt-in app-icon temperature badge, with the honest iOS
/// constraints baked in:
///
/// - The badge is a **whole, non-negative integer**: it shows `112`, never
///   `112°` and never a decimal.
/// - **No 99 ceiling** — `setBadgeCount` accepts any non-negative Int; the badge
///   pill widens, so triple-digit temperatures display in full.
/// - It **cannot show below 1**: `setBadgeCount(0)` *clears* the badge, so 0 and
///   any negative temperature have no badge representation and fall back to the
///   Lock Screen widget (W-1).
///
/// Never driven by push — the app updates it on foreground and via background
/// refresh only, so QuillPush stays location-blind (PRD §8.3).
enum BadgeManager {
    /// The integer to badge, or `nil` when the temperature cannot be represented
    /// (below 1 degree, where 0 would clear the badge). `nil` means "leave it to
    /// the widget".
    static func badgeValue(
        for temperature: Measurement<UnitTemperature>, unit: TemperatureUnit
    ) -> Int? {
        let degrees = temperature.wholeDegrees(in: unit)
        return degrees >= 1 ? degrees : nil
    }

    /// Ask for badge authorization (needed before the badge shows). Idempotent.
    @discardableResult
    static func requestAuthorization() async -> Bool {
        let center = UNUserNotificationCenter.current()
        return (try? await center.requestAuthorization(options: [.badge])) ?? false
    }

    /// Set or clear the badge from a report, honoring the user's toggle.
    static func update(
        from report: WeatherReport?, enabled: Bool, unit: TemperatureUnit
    ) async {
        let center = UNUserNotificationCenter.current()
        guard
            enabled,
            let report,
            let value = badgeValue(for: report.current.temperature, unit: unit)
        else {
            try? await center.setBadgeCount(0)
            return
        }
        try? await center.setBadgeCount(value)
    }

    static func clear() async {
        try? await UNUserNotificationCenter.current().setBadgeCount(0)
    }
}
