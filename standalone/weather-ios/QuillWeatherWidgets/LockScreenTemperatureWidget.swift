import SwiftUI
import WidgetKit

/// PRD §9 W-1: the recommended Lock Screen surface for a temperature. Unlike the
/// app-icon badge (W-8), the accessory families render the degree sign, handle
/// negatives, and carry a full VoiceOver label.
struct LockScreenTemperatureWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "LockScreenTemperature", provider: WeatherTimelineProvider()) { entry in
            LockScreenTemperatureView(entry: entry)
                .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Temperature")
        .description("Your primary location's current temperature on the Lock Screen.")
        .supportedFamilies([.accessoryCircular, .accessoryRectangular, .accessoryInline])
    }
}
