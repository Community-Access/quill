import Testing
@testable import QuillWeather

@Suite("WeatherService fusion")
struct WeatherServiceTests {
    private struct FailingProvider: WeatherProvider {
        let id = WeatherProviderID.weatherKit
        func report(for location: Location) async throws -> WeatherReport {
            throw WeatherProviderError.badResponse
        }
    }

    private struct StubProvider: WeatherProvider {
        let id = WeatherProviderID.openMeteo
        let canned: WeatherReport
        func report(for location: Location) async throws -> WeatherReport { canned }
    }

    @Test("Falls through a failing provider to the next one")
    func fallsThroughToNextProvider() async throws {
        let stub = sampleReport(provider: .openMeteo)
        let service = WeatherService(providers: [FailingProvider(), StubProvider(canned: stub)])
        let result = try await service.report(for: stub.location)
        #expect(result.provider == .openMeteo)
    }

    @Test("Throws when every provider fails")
    func throwsWhenAllFail() async {
        let service = WeatherService(providers: [FailingProvider(), FailingProvider()])
        await #expect(throws: (any Error).self) {
            _ = try await service.report(for: sampleReport().location)
        }
    }
}
