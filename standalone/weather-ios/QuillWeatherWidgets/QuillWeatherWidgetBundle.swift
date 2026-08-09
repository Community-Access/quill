import SwiftUI
import WidgetKit

@main
struct QuillWeatherWidgetBundle: WidgetBundle {
    var body: some Widget {
        CurrentConditionsWidget()
        LockScreenTemperatureWidget()
    }
}
