import SwiftUI

struct WeatherReportView: View {
    @Environment(WeatherStore.self) private var store
    @Environment(AppSettings.self) private var settings
    let location: Location

    var body: some View {
        ScrollView {
            if let report = store.report(for: location) {
                VStack(alignment: .leading, spacing: 24) {
                    CurrentConditionsCard(report: report)
                    if !report.alerts.isEmpty {
                        AlertsSection(alerts: report.alerts)
                    }
                    HourlyStripView(hours: report.hourly)
                    DailyForecastList(days: report.daily)
                    AttributionFooter(providers: report.attributions, asOf: report.asOf)
                }
                .padding()
            } else {
                ProgressView("Loading \(location.name)…")
                    .padding(.top, 80)
            }
        }
        .navigationTitle(location.name)
        .refreshable {
            await store.refresh(location)
        }
        .task(id: location.id) {
            if store.report(for: location) == nil {
                await store.refresh(location)
            }
        }
    }
}
