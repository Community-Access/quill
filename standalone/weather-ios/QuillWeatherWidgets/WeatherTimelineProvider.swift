import WidgetKit

/// Supplies entries for every Quill Weather widget from the primary saved
/// location. It shows the App Group's cached report immediately, then tries a
/// fresh fetch, and asks WidgetKit to refresh in ~30 minutes. WidgetKit budgets
/// refreshes, so "current" means "as of this entry's date" — the views state
/// their freshness (PRD §9 W-1).
struct WeatherTimelineProvider: TimelineProvider {
    func placeholder(in context: Context) -> WeatherEntry {
        .placeholder
    }

    func getSnapshot(in context: Context, completion: @escaping (WeatherEntry) -> Void) {
        let unit = SharedStore.temperatureUnit
        let report = SharedStore.primaryLocation.flatMap { SharedStore.cachedReport(for: $0.id) }
        completion(WeatherEntry(date: .now, report: report, unit: unit))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<WeatherEntry>) -> Void) {
        Task {
            let unit = SharedStore.temperatureUnit
            var report = SharedStore.primaryLocation.flatMap { SharedStore.cachedReport(for: $0.id) }

            if let primary = SharedStore.primaryLocation,
               let fresh = try? await WeatherService().report(for: primary) {
                SharedStore.cacheReport(fresh)
                report = fresh
            }

            let entry = WeatherEntry(date: .now, report: report, unit: unit)
            let next = Calendar.current.date(byAdding: .minute, value: 30, to: .now)
                ?? .now.addingTimeInterval(1800)
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }
}
