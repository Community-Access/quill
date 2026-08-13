import Observation

/// User configuration for the VoiceOver *actions* exposed on elements (the
/// rotor's action menu, PRD §5.2). Actions are on by default; a VoiceOver power
/// user who finds them noisy can turn categories off. Persisted through
/// `SharedStore` so the choice is durable.
///
/// This is the seam the PRD's "configurable rotor" work grows from: today it is
/// two category toggles; it can become per-action ordering and custom rotors
/// without changing the call sites, which already ask this type what to show.
@MainActor
@Observable
final class AccessibilityActionSettings {
    /// "Speak weather" on rows and the current-conditions card.
    var speakActionEnabled: Bool {
        didSet { SharedStore.speakRotorActionEnabled = speakActionEnabled }
    }

    /// "Make primary" and "Delete" on location rows.
    var quickManagementActionsEnabled: Bool {
        didSet { SharedStore.quickManagementActionsEnabled = quickManagementActionsEnabled }
    }

    init() {
        speakActionEnabled = SharedStore.speakRotorActionEnabled
        quickManagementActionsEnabled = SharedStore.quickManagementActionsEnabled
    }
}
