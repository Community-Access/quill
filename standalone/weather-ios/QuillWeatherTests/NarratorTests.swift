import Testing
@testable import QuillWeather

@Suite("Narrator")
struct NarratorTests {
    @Test("Mentions the place, temperature, and condition")
    func mentionsCoreFacts() {
        let sentence = Narrator(units: .fahrenheit).quickWeather(for: sampleReport(tempF: 112, condition: "sunny"))
        #expect(sentence.contains("Phoenix"))
        #expect(sentence.contains("112 degrees"))
        #expect(sentence.contains("sunny"))
    }

    @Test("Adds feels-like when it differs by 3+ degrees")
    func addsFeelsLikeWhenDifferent() {
        let sentence = Narrator(units: .fahrenheit).quickWeather(for: sampleReport(tempF: 112, feelsF: 105))
        #expect(sentence.contains("feeling like 105 degrees"))
    }

    @Test("Omits feels-like when it is within 2 degrees")
    func omitsFeelsLikeWhenClose() {
        let sentence = Narrator(units: .fahrenheit).quickWeather(for: sampleReport(tempF: 70, feelsF: 71))
        #expect(!sentence.contains("feeling like"))
    }

    @Test("Appends the most severe alert headline")
    func appendsAlert() {
        let alert = WeatherAlert(
            id: "1", tier: .warning, headline: "Excessive Heat Warning",
            detail: "", source: "NWS", area: "Maricopa County",
            effective: .now, expires: nil
        )
        let sentence = Narrator(units: .fahrenheit).quickWeather(for: sampleReport(alerts: [alert]))
        #expect(sentence.contains("Excessive Heat Warning"))
    }
}
