# Quill Weather for iOS — scaffold

This is the **first-cut SwiftUI scaffold** for the Quill Weather iOS app,
generated from `standalone/weather/docs/prd-ios.md`. It implements the core
architecture (models, provider/fusion layer, location, narration, saved
locations, Quick Weather, settings), the two glance surfaces we specced
(§9 W-1 Lock Screen temperature widget and W-8 app-icon badge), and a first
App Intent + App Shortcut.

> **It has not been compiled.** It was authored on Windows, where no Xcode /
> Swift-for-Apple toolchain exists. Expect to fix a few compile errors when you
> first build on a Mac — treat this as a strong starting point, not a finished
> app. The code targets **iOS 26 / Swift 6.2** with strict concurrency, per the
> `swiftui-pro` skill's defaults; lower `deploymentTarget` in `project.yml` if
> you need wider reach.

## Building (macOS + Xcode 26)

The Xcode project is described by `project.yml` (XcodeGen) rather than a
committed `.xcodeproj`, so the project file never becomes an unreadable merge
conflict.

```bash
brew install xcodegen        # one time
cd standalone/weather-ios
xcodegen generate            # writes QuillWeather.xcodeproj
open QuillWeather.xcodeproj
```

Then in Xcode:

1. Set your **Team** and a unique **bundle identifier** on both targets.
2. Add the **WeatherKit** capability to the app target (needs a paid Apple
   Developer account) and register the App ID for WeatherKit at
   developer.apple.com. Without it, the app still runs against **Open-Meteo**
   (keyless), which is the worldwide fallback provider.
3. Build and run.

## What's implemented vs. stubbed

**Implemented (real code):**

- `Models/` — the weather domain (`Location`, `WeatherReport`, conditions,
  hourly/daily, alerts, units).
- `Weather/` — a `WeatherProvider` protocol, `OpenMeteoProvider` (keyless, real
  network + JSON), a `WeatherKitProvider` (real WeatherKit calls), and a
  `WeatherService` fusion coordinator picking the provider per PRD §6.2.
- `Location/` — `LocationManager` (CoreLocation) and a Codable
  `SavedLocationsStore`.
- `Narration/Narrator` — turns a report into the single spoken sentence used by
  the UI's `accessibilityLabel`, the widget, and the App Intent (the
  three-second promise, PRD §3).
- **VoiceOver actions (PRD §5.2)** — location rows and the weather card carry
  rotor actions (Speak / Make Primary / Delete / Refresh), and which categories
  appear is user-configurable via `AccessibilityActionSettings` and a Settings
  section. This is the seam the fuller "configurable rotor" work grows from.
- `Badge/BadgeManager` — the W-8 app-icon temperature badge, with the honest
  constraints (integer-only, no negatives, clears at 0, no 99 ceiling).
- `Features/` — Locations list (`NavigationSplitView`), report view, Quick
  Weather, and Settings (units + badge toggle).
- `QuillWeatherWidgets/` — a Current Conditions widget and the Lock Screen
  accessory **temperature** widget (W-1), both with full accessibility labels.
- `Intents/` — `GetQuickWeatherIntent` + `QuillWeatherShortcuts` (W-4).
- `QuillWeatherTests/` — Swift Testing tests for the narrator, badge clamping,
  and provider selection.

**Stubbed / deferred (documented in code):** NWS provider (US ground-truth),
QuillPush alert relay (§8), Watch app, iCloud/QuillSync (§11), Live Activities.
These have protocol seams but no implementation yet.
