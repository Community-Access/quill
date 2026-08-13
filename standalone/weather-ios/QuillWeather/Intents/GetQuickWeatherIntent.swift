import AppIntents

/// PRD §9 W-4: "What's my Quill weather" from Siri, Shortcuts, and the Action
/// Button. Returns the same narrated sentence the UI and widgets use.
struct GetQuickWeatherIntent: AppIntent {
    static let title: LocalizedStringResource = "Get Quick Weather"
    static let description = IntentDescription(
        "Speaks the current weather for your primary location."
    )
    static let openAppWhenRun = false

    func perform() async throws -> some IntentResult & ProvidesDialog {
        guard let primary = SharedStore.primaryLocation else {
            return .result(dialog: "You haven't added a location to Quill Weather yet.")
        }
        let report = try await WeatherService().report(for: primary)
        SharedStore.cacheReport(report) // let the badge/widgets benefit from the fetch
        let sentence = Narrator(units: SharedStore.temperatureUnit).quickWeather(for: report)
        return .result(dialog: IntentDialog(stringLiteral: sentence))
    }
}
