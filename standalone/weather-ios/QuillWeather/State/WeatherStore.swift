import Observation
import WidgetKit

/// The app-facing weather state. Owns the fusion `WeatherService`, keeps the
/// latest report per location for the UI, caches to the App Group so widgets and
/// the badge stay in sync, and refreshes the badge + widget timelines after a
/// fetch.
@MainActor
@Observable
final class WeatherStore {
    private let service = WeatherService()
    private(set) var reports: [UUID: WeatherReport] = [:]
    private(set) var loadingLocationIDs: Set<UUID> = []
    private(set) var lastError: String?

    /// The freshest report we can show — in-memory first, then the App Group
    /// cache (so a cold launch renders immediately).
    func report(for location: Location) -> WeatherReport? {
        reports[location.id] ?? SharedStore.cachedReport(for: location.id)
    }

    func isLoading(_ location: Location) -> Bool {
        loadingLocationIDs.contains(location.id)
    }

    func refresh(_ location: Location) async {
        loadingLocationIDs.insert(location.id)
        defer { loadingLocationIDs.remove(location.id) }
        do {
            let report = try await service.report(for: location)
            reports[location.id] = report
            SharedStore.cacheReport(report)
            lastError = nil
        } catch {
            lastError = "Couldn't load \(location.name)'s weather."
        }
    }

    /// Refresh every saved location, then reconcile the badge and widgets from
    /// the primary. Called on appear and on pull-to-refresh.
    func refreshAll(_ locations: [Location], settings: AppSettings) async {
        await withTaskGroup(of: Void.self) { group in
            for location in locations {
                group.addTask { await self.refresh(location) }
            }
        }
        await reconcileGlanceSurfaces(primary: locations.first(where: \.isPrimary) ?? locations.first, settings: settings)
    }

    /// Push the primary location's temperature to the badge (W-8) and reload the
    /// widget timelines (W-1) after the toggle or unit changes too.
    func reconcileGlanceSurfaces(primary: Location?, settings: AppSettings) async {
        let report = primary.flatMap { report(for: $0) }
        await BadgeManager.update(
            from: report, enabled: settings.showTemperatureBadge, unit: settings.temperatureUnit
        )
        WidgetCenter.shared.reloadAllTimelines()
    }
}
