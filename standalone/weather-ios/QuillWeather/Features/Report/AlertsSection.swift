import SwiftUI

struct AlertsSection: View {
    let alerts: [WeatherAlert]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Alerts")
                .font(.headline)
            ForEach(alerts) { alert in
                DisclosureGroup {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(alert.detail)
                            .font(.callout)
                        if !alert.area.isEmpty {
                            Text(alert.area)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.top, 4)
                } label: {
                    Label(alert.headline, systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                }
                .accessibilityHint("\(alert.tier.spokenName) alert")
            }
        }
    }
}
