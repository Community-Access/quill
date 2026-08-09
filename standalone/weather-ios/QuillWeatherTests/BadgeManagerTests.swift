import Foundation
import Testing
@testable import QuillWeather

@Suite("BadgeManager")
struct BadgeManagerTests {
    private func fahrenheit(_ value: Double) -> Measurement<UnitTemperature> {
        Measurement(value: value, unit: .fahrenheit)
    }

    @Test("Triple-digit temperatures badge in full — no 99 ceiling")
    func noNinetyNineCeiling() {
        #expect(BadgeManager.badgeValue(for: fahrenheit(112), unit: .fahrenheit) == 112)
        #expect(BadgeManager.badgeValue(for: fahrenheit(130), unit: .fahrenheit) == 130)
    }

    @Test("Zero and below cannot be badged (0 clears the badge)")
    func cannotBadgeZeroOrBelow() {
        #expect(BadgeManager.badgeValue(for: fahrenheit(0), unit: .fahrenheit) == nil)
        #expect(BadgeManager.badgeValue(for: fahrenheit(-5), unit: .fahrenheit) == nil)
    }

    @Test("Rounds to a whole degree")
    func roundsToWholeDegree() {
        #expect(BadgeManager.badgeValue(for: fahrenheit(71.6), unit: .fahrenheit) == 72)
    }

    @Test("Converts to the user's unit before badging")
    func convertsToUserUnit() {
        let freezing = Measurement(value: 0, unit: UnitTemperature.celsius) // 32°F
        #expect(BadgeManager.badgeValue(for: freezing, unit: .fahrenheit) == 32)
        // 0°C would clear the badge, so it has no representation in Celsius.
        #expect(BadgeManager.badgeValue(for: freezing, unit: .celsius) == nil)
    }
}
