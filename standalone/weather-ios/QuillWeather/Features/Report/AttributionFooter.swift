import SwiftUI

/// Mandatory data attribution (PRD §6.1 D-5). WeatherKit in particular requires
/// its name and a link to Apple's legal attribution page wherever its data
/// appears.
struct AttributionFooter: View {
    let providers: [WeatherProviderID]
    let asOf: Date

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(providers, id: \.self) { provider in
                if let url = provider.attributionURL {
                    Link(provider.attributionText, destination: url)
                } else {
                    Text(provider.attributionText)
                }
            }
            Text("Updated \(asOf.formatted(date: .omitted, time: .shortened))")
                .foregroundStyle(.tertiary)
        }
        .font(.caption)
        .foregroundStyle(.secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
