import AppIntents

/// Registers the spoken phrases that reach `GetQuickWeatherIntent` from Siri and
/// the Shortcuts app. `\(.applicationName)` is required in every phrase.
struct QuillWeatherShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: GetQuickWeatherIntent(),
            phrases: [
                "What's my \(.applicationName)",
                "Get my \(.applicationName)",
                "\(.applicationName) quick weather",
            ],
            shortTitle: "Quick Weather",
            systemImageName: "cloud.sun"
        )
    }
}
