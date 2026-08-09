import BackgroundTasks
import WidgetKit

/// Opportunistic background refresh (PRD §8.1 second tier) that keeps the badge
/// and widgets current when the app is closed. It is best-effort by design: iOS
/// schedules it when it sees fit and the user can disable Background App
/// Refresh, so the badge is labeled "approximate, last known" rather than live.
enum BackgroundRefresh {
    static let identifier = "com.communityaccess.quillweather.refresh"

    /// Ask iOS to run us again in roughly an hour. Call after each run and on
    /// launch.
    static func schedule() {
        let request = BGAppRefreshTaskRequest(identifier: identifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60)
        try? BGTaskScheduler.shared.submit(request)
    }

    /// Refresh the primary location, cache it, reconcile the badge, and reload
    /// widget timelines. Always reschedules, even on failure.
    static func run() async {
        defer { schedule() }
        guard let primary = SharedStore.primaryLocation else { return }
        let service = WeatherService()
        guard let report = try? await service.report(for: primary) else { return }
        SharedStore.cacheReport(report)
        await BadgeManager.update(
            from: report,
            enabled: SharedStore.showTemperatureBadge,
            unit: SharedStore.temperatureUnit
        )
        WidgetCenter.shared.reloadAllTimelines()
    }
}
