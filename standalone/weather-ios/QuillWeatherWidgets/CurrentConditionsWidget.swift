import SwiftUI
import WidgetKit

/// Home Screen widget: temperature + condition for the primary location.
struct CurrentConditionsWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "CurrentConditions", provider: WeatherTimelineProvider()) { entry in
            CurrentConditionsWidgetView(entry: entry)
                .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Current Conditions")
        .description("Temperature and conditions for your primary location.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
