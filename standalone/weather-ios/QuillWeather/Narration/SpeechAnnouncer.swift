import AVFoundation
import Observation

/// Speaks a narrated sentence aloud for users who aren't running VoiceOver
/// (VoiceOver users already hear the same text from the view's
/// `accessibilityLabel`). Used by Quick Weather's Speak button.
@MainActor
@Observable
final class SpeechAnnouncer {
    private let synthesizer = AVSpeechSynthesizer()

    func speak(_ text: String) {
        synthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: AVSpeechSynthesisVoice.currentLanguageCode())
        synthesizer.speak(utterance)
    }

    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
    }
}
