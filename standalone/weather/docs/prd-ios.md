# Quill Weather for iOS -- Product Requirements

**Product:** Quill Weather for iOS (iPhone, iPad, Apple Watch, CarPlay-aware)
**Ecosystem:** QUILL / QuillVille
**Language and stack:** Swift 6, SwiftUI + a thin UIKit layer where VoiceOver needs it, WeatherKit, CoreLocation, UserNotifications, App Intents, WidgetKit, ActivityKit, CryptoKit
**Document status:** Product definition, implementation-ready
**Version:** 1.0
**Date:** August 8, 2026
**Windows counterpart:** `standalone/weather/docs/prd.md` (the authoritative feature and behavior spec for the shared weather domain)
**Shared platform spec:** `docs/Product Requirement Documents and Specifications/quillville-apple-platform-spec.md`
**Sibling iOS app:** `standalone/radio/docs/prd-ios.md`
**Product posture:** Accessibility-first, VoiceOver-first, narration-first, local-first, provider-plural, safety-conscious

---

## 1. Product statement

Quill Weather for iOS is the pocket half of the Quill Weather product. It is not
a port of a window; it is a port of a **voice**. The Windows app's defining
property is that every number it knows is already a sentence -- warm, fully
spelled out, never abbreviated, and identical whether it is read on screen or
spoken aloud. iOS inherits that property byte for byte.

What iOS adds is everything the desktop could only describe in its own PRD as
future work: a real current location, real push instead of a 30-second poll
approximation, a device that is with the user when the warning is issued, and a
screen reader that ships with the operating system and has a richer interaction
vocabulary than any Windows screen reader exposes to an application.

The measure of success is blunt. **A blind user should get the weather faster,
more completely, and with less effort on Quill Weather for iOS than a sighted
user gets it from the built-in Weather app.** Not "as well as." Faster and more
completely. Everything in this document exists to serve that sentence.

---

## 2. Architecture requirement: not a fork, and not a rewrite of the voice

- **R-1.** The narration layer is a **port with parity, not a reinterpretation**.
  `quill/core/weather/render.py` is the specification. Its Swift counterpart
  (`QuillNarrate`, see the platform spec) must produce **byte-identical output**
  for the same input. A shared golden corpus of input/expected-string pairs is
  checked into the repo and is run by both the Python test suite and the Swift
  test suite. A divergence is a build failure on both sides, not a stylistic
  choice.
- **R-2.** The domain model is a port with parity. `models.py`, `settings.py`,
  `locations.py`, `monitor.py`, and `astronomy.py` are wx-free, clock-free,
  network-free and unit-tested; their Swift equivalents keep the same field
  names, the same defaults, the same clamps, the same tier derivation
  (`ALERT_TIERS`, `tier_rank`), and the same JSON on-disk shapes so a settings
  file written by either platform is readable by the other without migration.
- **R-3.** Everything reusable lives in **QuillKit**, a Swift package shared with
  Quill Radio for iOS: sync, settings, narration, announcement policy, network
  chokepoint, location model, provider clients. App targets contain only their
  own screens, intents, and widgets. The same "not a fork" discipline that keeps
  the Windows wrappers honest applies here.
- **R-4.** New capability discovered on iOS flows **back** to the shared spec.
  If iOS learns to say something better -- a new phrase, a better disagreement
  wording, a smarter staleness rule -- the sentence is added to the golden
  corpus and to `render.py` in the same change. The two platforms never drift on
  wording, only on delivery.
- **R-5.** Source layout: `standalone/weather-ios/` (app target, widgets, watch
  app, intents, tests) and `apple/QuillKit/` (the shared package). Both sit
  outside QUILL's Python CI gates, exactly as `standalone/radio-mac/` does, and
  carry their own Swift CI.

---

## 3. Users and the three-second promise

Three usage shapes drive every decision:

1. **The glance.** The user raises the phone, triple-clicks or taps once, and
   hears one sentence: what it is doing outside right now, and whether anything
   is wrong. Target: **under three seconds from intent to speech**, from cold,
   using cached data with an honest staleness clause if the network is slow.
2. **The read.** The user wants the whole picture -- hourly, daily, the official
   warning text -- and wants to move through it with the rotor rather than by
   swiping past 200 elements.
3. **The warning.** The user is not looking at the phone. Something dangerous is
   coming. The device must interrupt, must be understood in one hearing, and
   must be re-readable a minute later without hunting.

Every feature below is tagged, in effect, by which of those three it serves. A
feature that serves none of them is a candidate for cutting.

---

## 4. Scope: the full Windows feature set, ported

### 4.1 Shipped on Windows, required at iOS 1.0

**F-1. Weather Now** -- the full narrative report for a location, as one
continuous readable and speakable block, in the fixed priority order: alerts,
current conditions, forecast, hourly, daily, source and freshness. Ported from
`render.current_conditions_block` and `WeatherCenterDialog._render_report`.

**F-2. Quick Weather** -- the one-liner
(`render.quick_weather_line`), reachable without opening the app at all (§9).

**F-3. Current conditions**, every field individually toggleable, with
temperature and sky description always present: temperature, text description,
feels-like (spoken only when it differs by at least one degree), humidity, dew
point, wind with direction and gusts, cloud cover, barometric pressure,
visibility, chance of precipitation today, sunrise and sunset, moon phase and
illumination with moonrise and moonset, UV index with its severity band, air
quality with its category, the two-clock time summary, and the observation time
and station.

**F-4. Period forecast** -- the NWS named periods ("This Afternoon", "Tonight"),
with per-period detail blocks that repeat their own heading so a period read out
of context still stands alone, and with abbreviations widened
(`_spell_out`: `mph` becomes "miles per hour").

**F-5. Hourly forecast** -- 0 to 48 hours, default 24, one self-contained
spoken line per hour.

**F-6. Extended daily outlook** -- 0 to 16 days, default 10, one friendly
sentence per day including sun and moon events.

**F-7. Alerts** -- active alerts, most severe first, with the full official
text in the documented order (headline, severity/urgency/certainty, area,
in-effect window, **instructions before description**, issuing office). The
derived five-tier priority (`Critical`, `Urgent`, `Important`, `Advisory`,
`Informational`) is shown and spoken, never hidden. Severity floor and
per-event mute list both port unchanged.

**F-8. Weather Guardian** -- background alert monitoring across **every saved
location at once**, with new-alert and all-clear announcements, baseline-on-first-poll
semantics so a launch never spams already-active alerts, and forced/interrupting
delivery at `Urgent` and above. On iOS this is re-founded on push and background
refresh rather than a timer (§8).

**F-9. Multi-location** -- unlimited saved locations, one primary, add by ZIP,
city, county, address, worldwide place name, or bare `lat,lon` (parsed locally,
zero network calls). Remove, rename to a friendly name, and -- new on iOS --
**reorder**, which the Windows store supports (`WeatherLocationStore.move`) but
never exposed.

**F-10. Units** -- temperature Fahrenheit/Celsius; wind mph, km/h, knots, m/s.
iOS additionally honors the system measurement system as the initial default,
and extends unit control to **pressure** (inHg / hPa / mb) and **visibility**
(miles / kilometers), which the Windows app hard-coded. That extension is
back-ported to `render.py` under R-4.

**F-11. Alert sounder** -- enable/disable, custom sound, repeat 1 to 10. On iOS
this becomes the notification sound plus an in-app rehearsal, and the **Test
Alert** command ports whole: it exercises sound, notification, haptic, speech,
and the alert surface, marked `[TEST]`, without touching the network or the
real monitor state.

**F-12. NOAA Weather Radio directory** -- find the transmitter covering a saved
location, from the same bundled 1,035-transmitter snapshot
(`quill/data/noaa_directory.json`) via county/SAME match then nearest covering
transmitter. On iOS, unlike Windows, this is not a dead end: **Quill Weather
hands the stream to Quill Radio for iOS** and it plays (§12.2).

**F-13. Customize Features** -- switchable areas, so a user who wants only
alerts can remove everything else from the interface and, critically, from the
VoiceOver focus order.

### 4.2 Documented on Windows, unbuilt there, built here

These are all specified in the Windows PRD and never shipped because Windows
made them awkward. iOS makes them natural, so iOS ships them first and the
design flows back.

**F-14. Current location** (§7). The single biggest greenfield item.

**F-15. Travel mode** -- arrival detection, automatic temporary location,
"you have arrived somewhere with an active warning" (§7.4).

**F-16. Location groups** -- "Family", "Route", "Work" -- as a grouping over
saved locations, used for both display and per-group alert policy.

**F-17. Alert lifecycle and the revision graph** -- updated, escalated,
downgraded, extended, area-changed, corrected, cancelled, expired. The Windows
app dedupes by alert id only and therefore cannot say "this warning has been
extended." iOS carries `references`, `messageType`, and `sent`, and speaks the
transition, which is often the most important sentence of the whole event (§8.5).

**F-18. Conditional HTTP and honest staleness** -- ETag/If-None-Match,
Last-Modified, Retry-After, point-to-grid caching on the location record,
last-good-data retention, and a spoken staleness clause. Windows re-resolves
point metadata on every refresh and never marks stale data; iOS must not, both
because cellular data is precious and because a stale reading presented as
current is a safety defect.

**F-19. Observation station selection by freshness and quality**, rather than
"take the first station in the list."

**F-20. Historical weather** -- yesterday, this date last year, and a "compared
to normal" clause, from Open-Meteo's archive and ERA5 endpoints. This turns
"98 degrees" into "98 degrees, nine degrees above normal for August 8," which
is the sentence people actually want.

**F-21. Marine and fire-weather segments**, where the location has a marine or
fire zone.

### 4.3 New on iOS because iOS makes it possible

**F-22. Apple Weather (WeatherKit) as a first-class provider** (§6).

**F-23. Minute-by-minute precipitation** -- "Rain starting in 12 minutes,
lasting about 25 minutes." From WeatherKit's minute forecast where available.
This is the single most useful weather sentence that exists and neither NWS nor
Open-Meteo can produce it.

**F-24. Audio Graphs** -- the hourly temperature curve, the precipitation
probability curve, and the daily high/low range are exposed as
`AXChartDescriptor` so VoiceOver can **play the forecast as sound**. A rising
tone is a warming afternoon. This is a native VoiceOver capability that has no
Windows equivalent and it changes what "reading a forecast" means (§5.6).

**F-25. Provenance per fact** -- every number in the narrative can be
interrogated for its source, its issuing office, its observation time, and its
age, without leaving the sentence, via the VoiceOver Custom Content rotor
(§5.4).

**F-26. Honest disagreement** -- when two providers disagree materially, the app
says so rather than silently picking one (§6.4).

**F-27. Widgets, Live Activities, Control Center, Siri, Watch** (§9, §10).

### 4.4 Non-goals

- Radar imagery, animated maps, or any surface where the map *is* the
  navigation. A textual and sonified radar interpretation ("a line of storms
  about 20 miles west, moving east at 30 miles per hour, reaching you around
  4:15") is in scope for a later phase; a map that must be looked at is not.
- Any implication that the app replaces Wireless Emergency Alerts, a physical
  NOAA Weather Radio receiver, or local emergency instruction. This is stated in
  the onboarding, in the alert settings screen, and in the App Store
  description. It is a safety requirement, not marketing copy.
- Accounts as a precondition. Nothing in the core product requires signing in to
  anything. Sync is opt-in and, at its default tier, serverless (§11).
- Advertising, analytics, tracking, an IDFA request, or any third-party SDK that
  performs network I/O. The app ships with **zero** third-party runtime
  dependencies.
- Selling or brokering weather data, or presenting derived data as official.

---

## 5. Accessibility: VoiceOver as a first-class interaction language

This section is the heart of the document. Requirements are normative.

### 5.1 The parity invariant

- **A-1.** **What is displayed is what is spoken.** There is no separate
  "accessible version" and no visual-only or audio-only content. The string
  rendered into a `Text` view is the string in its `accessibilityLabel` unless
  the label is *shorter for braille reasons* (A-14), in which case the full
  string is reachable via Custom Content. This is the ported invariant from
  `render.py` and it is the reason the product works.
- **A-2.** Every interactive element has an `accessibilityLabel` that names it
  in the same words the on-screen label uses, an `accessibilityValue` when it
  has state, an `accessibilityHint` only when the action is not obvious from the
  label, and correct traits. Unlabeled elements fail CI (§14.3).
- **A-3.** Reading order is priority order, enforced with
  `accessibilitySortPriority` where the visual layout would otherwise disagree:
  alerts, then current conditions, then forecast, then hourly, then daily, then
  source and freshness.
- **A-4.** An empty region is **removed from the accessibility tree**, not
  blanked. This is the direct port of the Windows `_show_field` rule -- a
  VoiceOver user must never land on an empty detail field. Implemented with
  `.accessibilityHidden(true)` plus removal from the view hierarchy.
- **A-5.** Data refresh never moves VoiceOver focus. New data announces itself
  with a polite `AccessibilityNotification.Announcement`; the cursor stays where
  the user put it.

### 5.2 VoiceOver Actions (the rotor's action menu)

- **A-6.** Every list row that can be acted on exposes its actions as
  `accessibilityCustomActions` / `.accessibilityAction(named:)`, so a user
  swipes down through actions instead of hunting for buttons. Required action
  sets:
  - **Location row:** Show weather, Make primary, Speak quick summary, Rename,
    Move up, Move down, Add to group, Copy report, Remove.
  - **Alert row:** Read full text, Read instructions only, Share, Copy,
    Mute this event type, Show the covered area in words, Snooze this alert.
  - **Hour row:** Speak this hour, Compare to now, Set a reminder for this hour.
  - **Day row:** Speak this day, Open its hourly detail, Compare to normal.
  - **Saved-location group header:** Speak all in this group, Rename group,
    Collapse.
- **A-7.** Adjustable values use `.accessibilityAdjustableAction` so swipe
  up/down changes them without opening a picker: forecast period count, daily
  outlook days, hourly hours, alert repeat count, and the severity floor.

### 5.3 Custom rotors

- **A-8.** The app publishes `AccessibilityCustomRotor`s so a user can move by
  meaning rather than by element: **Alerts**, **Hours**, **Days**, **Sections**,
  and **Locations**. On the Weather Now screen the Alerts rotor jumps directly
  between active alerts even when the alert list is scrolled off screen.
- **A-9.** Headings are real headings (`.accessibilityHeading(.h1/.h2/.h3)`), so
  the standard Headings rotor works with no custom code: the location name is
  h1, each section is h2, each alert event name is h3.

### 5.4 Custom Content -- verbosity without a verbosity setting

- **A-10.** Every fact-bearing element carries
  `.accessibilityCustomContent(_:_:importance:)` entries that VoiceOver reads on
  demand via the "More Content" rotor. This is how the app serves both the
  three-second glance and the exhaustive read from the same element:
  - Default label: `"96 degrees Fahrenheit and mostly clear."`
  - Custom Content: `Source` -> `"National Weather Service, station KTUS"`;
    `Observed` -> `"July 19 at 1:55 PM, 12 minutes ago"`;
    `Also reported` -> `"Apple Weather says 95 degrees"`;
    `Confidence` -> `"Both sources agree within one degree."`
  - Entries marked `.high` importance are spoken inline; the rest wait for the
    rotor.
- **A-11.** Custom Content is the **only** sanctioned place for provenance and
  disagreement detail. It never lengthens the primary sentence, which is what
  keeps the glance fast.

### 5.5 Announcement, priority, and speech shaping

- **A-12.** Announcements use `AttributedString` with
  `accessibilitySpeechAnnouncementPriority`:
  - `.high` for `Critical` and `Urgent` tier alerts -- interrupts, matching the
    Windows `should_force_speech` rule (`tier_rank <= 1`).
  - `.default` for `Important`.
  - `.low` for `Advisory`, `Informational`, all-clear, and refresh completion --
    queued, never interrupting.
- **A-13.** Speech attributes are used where they change comprehension:
  `accessibilitySpeechSpellsOutCharacters` for station identifiers and SAME
  codes; `accessibilitySpeechPunctuation` on the official alert text so the
  structure of an NWS bulletin survives; `accessibilitySpeechPhoneticNotation`
  is deliberately **not** used (it slows everything down).
- **A-14.** **Braille.** iOS derives braille from the accessibility label, so
  there is no separate braille channel to write to. Quill Weather therefore
  ships a **Concise labels** setting (default off) that swaps the primary label
  for the ported `compact_braille()` wording while keeping the full sentence in
  Custom Content. A braille user gets a line that fits the display; a speech
  user is unaffected; nobody loses information. This is the honest iOS answer to
  the Windows braille channel, and its limitation is documented in the user
  guide rather than papered over.
- **A-15.** Nothing is ever truncated for speech. Track-length labels are fine;
  clipping the end of a warning is a defect.
- **A-16.** An identical announcement inside a two-second window is suppressed,
  porting the Windows dedupe policy (`core/announce/policy.py`).

### 5.6 Audio Graphs

- **A-17.** The hourly temperature series, the hourly precipitation-probability
  series, and the ten-day high/low series each publish an `AXChartDescriptor`
  with correctly labeled axes, units, and a summary sentence. VoiceOver's Audio
  Graph player is reachable from the chart element's rotor.
- **A-18.** Every audio graph has a **spoken alternative that is complete on its
  own** -- the same data as a list of sentences. The graph is an accelerator,
  never the only path to the data.

### 5.7 Gestures, focus, and the rest of the contract

- **A-19.** **Magic Tap** (two-finger double tap) speaks the current location's
  quick summary from anywhere in the app. If an alert is active, it leads with
  the alert.
- **A-20.** **Escape** (`.accessibilityAction(.escape)`) dismisses any sheet or
  detail, on every screen.
- **A-21.** Full **Full Keyboard Access** and hardware-keyboard support with a
  documented shortcut set that mirrors the Windows accelerators where the
  platform allows: Command-Shift-W Weather Now, Command-Shift-Q Quick Weather,
  Command-R refresh, Command-1 through Command-9 saved locations, Command-F
  search, and a discoverable keyboard-shortcuts overlay on holding Command.
- **A-22.** Dynamic Type to the largest accessibility sizes, with no truncation
  and no fixed-height rows; the layout reflows rather than clipping. Verified at
  `AX5` in snapshot tests.
- **A-23.** `prefers-reduced-motion` is honored: no parallax, no animated
  transitions on alert arrival, no motion used to convey state.
- **A-24.** Color is never the only carrier of meaning. Alert tier is carried by
  the tier word itself in every surface. Contrast meets WCAG 2.2 AA at minimum
  in both light and dark appearance, and Increase Contrast and Differentiate
  Without Color are both honored.
- **A-25.** Switch Control, Voice Control, and Assistive Access are supported:
  every action is reachable without a gesture, every control has a
  Voice-Control-speakable name matching its visible label, and the app provides
  a reduced Assistive Access presentation that is Quick Weather plus alerts.
- **A-26.** Haptics accompany, never replace: a distinct haptic pattern for a
  new `Critical`/`Urgent` alert, one for all-clear, one for refresh complete.
  All are disableable and none is the sole indicator of anything.
- **A-27.** VoiceOver users can complete **first launch, permission grants,
  adding a location, and receiving a test alert** without sighted assistance.
  This is validated by a scripted end-to-end VoiceOver run before every release
  (§14.2).

---

## 6. Data sources and the fusion model

### 6.1 The provider set

| Provider | Role | Auth | Notes |
|---|---|---|---|
| National Weather Service (`api.weather.gov`) | Authoritative US: alerts (full official text), period forecast, hourly forecast, observations, zones | None; identifying User-Agent required | Alert polling floor 30 s, honored |
| Apple WeatherKit | Global current, hourly, daily, minute precipitation, global alerts, historical | Apple Developer Program; JWT for REST | Attribution mandatory (D-5) |
| Open-Meteo | Air quality (US AQI, PM2.5), worldwide fallback report, historical archive | None | Already the Windows fallback |
| On-device astronomy | Moon phase, illumination, moonrise, moonset | None | Ported `astronomy.py`; zero network |
| Apple `MKLocalSearch` / `CLGeocoder` | Place search and reverse geocoding | None (on-platform) | **Replaces Nominatim**, see D-4 |
| WeatherIndex (`api.wxindex.org`) + bundled snapshot | NOAA Weather Radio transmitter directory | None | Three-tier resolver ported |

- **D-1.** Every outbound request goes through **one** audited chokepoint, the
  Swift counterpart of `_http.py`: HTTPS only (a non-HTTPS URL is a programming
  error and traps), the system trust store, a 15-second timeout, and the
  identifying User-Agent `QUILLWeather-iOS/<version> (https://github.com/Community-Access/quill)`.
  Every call site is inventoried in the ecosystem network-egress audit exactly
  as the Windows call sites are.
- **D-2.** The chokepoint implements conditional requests (ETag, Last-Modified),
  honors `Retry-After`, and applies exponential backoff with jitter. This closes
  Windows gap F-18.
- **D-3.** No provider key is ever embedded in the binary. WeatherKit uses the
  on-device Swift API, which needs no key material in the app.
- **D-4.** **Nominatim is not used on iOS.** The OpenStreetMap public endpoint's
  usage policy does not permit a distributed application to geocode against it
  unthrottled, and the Windows app does so today. iOS uses `MKLocalSearch` and
  `CLGeocoder`, which are free, on-platform, rate-managed by the OS, and better
  at the address forms people actually type. This is also filed as a compliance
  fix for the Windows app.
- **D-5.** **Apple Weather attribution is mandatory and non-negotiable.** Where
  any WeatherKit-derived value is shown or spoken, the app displays the Apple
  Weather trademark and a link to the legal attribution page obtained from
  `WeatherAttribution`, and the *spoken* provenance in Custom Content names
  Apple Weather. Failing to display attribution is both a licensing breach and
  an accessibility failure, since a blind user would otherwise never learn where
  the number came from.

### 6.2 Which provider answers which question

Selection is **by question, not by preference**, and the rule set is fixed and
inspectable:

| Question | Primary | Fallback | Why |
|---|---|---|---|
| US watches, warnings, advisories -- full text | NWS | WeatherKit alert (summary + link) | Only NWS returns the complete official body, instructions, and zone list |
| Non-US alerts | WeatherKit | none | NWS is US-only |
| Named period forecast ("Tonight") | NWS | -- | A uniquely NWS product; nobody else writes prose forecasts |
| Current conditions, US | NWS observation | WeatherKit current | Station observation is the ground truth; WeatherKit fills gaps NWS omits |
| Current conditions, worldwide | WeatherKit | Open-Meteo | |
| Hourly, US | NWS `forecastHourly` | WeatherKit hourly | |
| Hourly, worldwide | WeatherKit | Open-Meteo | Closes the Windows "no hourly outside the US" gap |
| Daily outlook | WeatherKit | Open-Meteo | |
| Minute-by-minute precipitation | WeatherKit | none; the sentence is simply omitted | |
| Air quality | Open-Meteo | none | WeatherKit does not provide AQI |
| Moon and sun | On-device `astronomy.swift` | -- | No network, always available, already correct |
| Historical and normals | Open-Meteo archive | WeatherKit historical | |

- **D-6.** Availability is queried, not assumed. `WeatherService.availability(for:)`
  determines whether minute precipitation and alerts exist for a location before
  the app promises them; an unavailable dataset produces **no sentence at all**,
  never an empty or zeroed one.

### 6.3 Graceful degradation

- **D-7.** The Windows per-subrequest degradation model ports exactly: point
  resolution is required; forecast, hourly, observation, alerts, daily, and air
  quality are each independently recoverable and each failure appends its own
  note to the report, spoken in the source-and-freshness section. The exact note
  strings are shared with Windows through the golden corpus.
- **D-8.** Last-good data is retained per location and per dataset, with its
  fetch time. When the network fails, the app shows the cached report **with an
  explicit staleness clause in the narrative** -- never a spinner, never a blank
  screen, and never a stale number presented as current.

### 6.4 Honest disagreement

- **D-9.** When two providers answer the same question and differ by more than a
  configured threshold -- 3 degrees Fahrenheit for temperature, 20 percentage
  points for precipitation probability, one Beaufort step for wind -- the app
  states the disagreement rather than picking silently:
  > `"The National Weather Service reports 96 degrees; Apple Weather reports 91.
  > Readings differ by 5 degrees."`
  Below the threshold, the primary provider's value is spoken alone and the
  other is available in Custom Content as `Also reported`.
- **D-10.** Disagreement is **never** applied to alerts. If either provider says
  there is a warning, there is a warning. Safety information is a union, never
  an intersection or an average.

---

## 7. Location: the greenfield

- **L-1. Current location** uses `CLLocationManager` with **When In Use**
  authorization by default. **Always** authorization is requested only when the
  user turns on arrival-based alerting or travel mode, and is requested with a
  purpose string that says exactly what it buys them.
- **L-2. Reduced accuracy is the default.** The app requests
  `CLAccuracyAuthorization.reducedAccuracy` and works fully at that level --
  weather is a ~5 km question, not a ~5 m question. Full accuracy is requested
  temporarily, with a stated purpose, only for the NOAA transmitter lookup and
  only if reduced accuracy returns an ambiguous result.
- **L-3. Coordinates are rounded before they leave the device.** Every provider
  request uses four decimal places at most (the NWS point format, roughly 11
  metres) and, for the "current location" case, snaps to a coarse grid so
  repeated requests do not trace a path. Coordinates are never sent to any
  QUILL-operated server; the push service subscribes by **NWS zone or SAME
  code**, never by position (§8.3).
- **L-4. No location history.** Current-location fixes are held in memory and in
  the last-good cache only. There is no track, no visit log persisted beyond
  what travel mode needs for its current session, and an explicit "Forget where
  I have been" control that clears everything in one action.
- **L-5. Saved locations** carry, in addition to the Windows fields, the cached
  resolution results the Windows app throws away on every refresh: IANA time
  zone, NWS office, grid X/Y, forecast zone, county zone, observation station,
  marine and fire zones where present, and `source_resolved_at`. This is the
  single largest performance and battery win available and it is required.
- **L-6. Stable identifiers.** Location ids are UUIDs, not the sequential
  `loc_N` the Windows store uses, because sequential ids collide the instant two
  devices add a location independently. The Windows store gains UUID support in
  the same change, with `loc_N` accepted on read forever.
- **L-7. Geofenced arrival** uses `CLMonitor` circular conditions around saved
  locations, plus significant-location-change, plus `CLVisit` for travel mode.
  Arrival produces one sentence: what it is like here, and whether anything is
  in effect.
- **L-8. Travel mode** creates a temporary location on arrival in a new area,
  marks it as temporary, watches it for the duration of the stay, and offers to
  save it or discard it when the user leaves. Temporary locations never sync.
- **L-9. Permission refusal is a first-class path, not an error.** Everything
  works with location fully denied; the app simply asks the user to add a place.
  The refusal state is announced once, calmly, with a working alternative, and
  never nagged.

---

## 8. Alerts, notifications, and push

### 8.1 Delivery tiers

- **U-1.** Alert delivery uses, in order of preference and with automatic
  fallback:
  1. **APNs push** from the QuillPush relay (§8.3) -- the only mechanism that
     delivers within seconds while the app is not running.
  2. **`BGAppRefreshTask` background refresh** -- opportunistic, scheduled by
     the system, used to reconcile and to cover push outages.
  3. **Foreground fast poll** -- the ported Windows monitor, including
     severe-weather mode down to the 30-second NWS courtesy floor, active only
     while the app is on screen.
  4. **Manual refresh**, always available.
- **U-2.** Whichever tier delivers, the user-visible behavior is identical. The
  tier is inspectable in the diagnostics screen and in Custom Content on the
  alert; it is never something the user has to think about.

### 8.2 Notification behavior

- **U-3.** Interruption level maps to the ported tier:
  `Critical` -> `.critical` (see U-4) or `.timeSensitive`; `Urgent` ->
  `.timeSensitive`; `Important` -> `.active`; `Advisory` and `Informational` ->
  `.passive`. Time Sensitive breaks through Focus, which is the entire point.
- **U-4.** **Critical Alerts** (which bypass silent mode and Do Not Disturb)
  require an Apple entitlement. The app requests the entitlement for
  tornado warnings, flash flood emergencies, and other life-threatening
  short-fuse events only. Until and unless the entitlement is granted, the app
  ships with Time Sensitive as its highest level and **says so plainly in the
  alert settings screen** -- the user must never believe they have a
  wake-them-up alarm that they do not have. This is a safety requirement.
- **U-5.** Notification content is the ported sentence, not a truncated
  headline. Title: `"Weather alert: Excessive Heat Warning"`. Body: the same
  first sentence the app would speak. Notification actions:
  **Read full text**, **Speak it**, **Snooze this alert**, **Mute this event
  type**. Actions are performed without launching the app where possible.
- **U-6.** A **notification summary is never used** for `Critical` or `Urgent`
  tiers; those are excluded from Scheduled Summary delivery.
- **U-7.** **Live Activity and Dynamic Island.** While an `Urgent`-or-worse
  alert is in effect, a Live Activity shows the event name and the time
  remaining until expiry, with fully labeled accessibility content and a
  countdown that VoiceOver reads as words, not as a ticking timer. It ends
  automatically when the alert expires or clears.
- **U-8.** **No repeat-notification spam.** The notified-alert-id union
  (`weather_notified.json` on Windows) ports as a persisted set shared between
  the app, the notification service extension, and the background task, so one
  alert produces one interruption regardless of which tier delivered it.
- **U-9.** **Snooze and quiet hours** are per-event-type and per-tier, and quiet
  hours never suppress `Critical` or `Urgent`. A user can silence every Special
  Weather Statement forever without ever risking a tornado warning.

### 8.3 QuillPush -- the relay

- **U-10.** A QUILL-operated relay subscribes to NWS alerts and fans them out
  over APNs. Its privacy design is load-bearing:
  - The device registers **only** `(device token, list of NWS zone or SAME
    codes, minimum tier)`. No account, no coordinates, no location history, no
    identifier that outlives an uninstall.
  - Zone codes are derived on-device from the saved location's already-cached
    NWS metadata. The server never learns where the user is, only which of
    roughly 4,000 public zones they care about.
  - The push payload carries the alert id and tier only; the **full alert text
    is fetched from NWS by the device**, so the relay is never a source of
    truth for content and cannot inject a fabricated warning body.
  - The relay retains no message history and no per-device log beyond what APNs
    delivery requires.
- **U-11.** Push registration is **opt-in**, is explained in one screen in plain
  language before any token is sent, and is fully revocable. With push off, the
  app degrades to tiers 2 through 4 and says so.
- **U-12.** The relay is specified in the platform spec and is the only
  QUILL-operated network service the weather app talks to.

### 8.4 Non-US alerts

- **U-13.** Outside NWS coverage, WeatherKit alerts drive the same pipeline,
  with the same tier derivation applied to their severity. Where WeatherKit
  supplies only a summary and a details URL, the app says so rather than
  implying it has the full text, and offers the link.

### 8.5 Lifecycle and the revision graph

- **U-14.** The app persists `id`, `messageType`, `sent`, `references`, and a
  content hash per alert, and derives the transition: issued, updated,
  escalated, downgraded, extended, area changed, corrected, cancelled, expired.
  The transition is the lead of the announcement, because "the tornado warning
  has been extended until 5:15" is a different and more useful sentence than a
  second copy of the original warning.
- **U-15.** An alert whose only change is an administrative re-issue with
  identical content does **not** re-interrupt.

---

## 9. Getting the weather without opening the app

The three-second promise (§3) is mostly won outside the app.

- **W-1. Widgets** (WidgetKit, all families plus Lock Screen and StandBy):
  Current conditions; Next alert; Sunrise/sunset; Hourly strip; and a **Speak
  it** interactive widget whose single button speaks Quick Weather. Every widget
  has a complete `accessibilityLabel` that is the same sentence the app would
  say -- a widget that a VoiceOver user cannot read is a broken widget.
- **W-2. Control Center control** (`ControlWidget`): "Speak my weather." One
  press, one sentence, from the Lock Screen, without unlocking.
- **W-3. Action Button and Back Tap** are both supported through the App
  Shortcut, so the hardware affordance can be bound to Quick Weather.
- **W-4. App Intents and Siri.** `GetQuickWeather`, `GetWeatherReport`,
  `GetActiveAlerts`, `AddLocation`, `SetPrimaryLocation`, `SpeakForecast`,
  `FindNOAATransmitter`. All are `AppShortcut`s with natural phrases
  ("What is my Quill weather", "Any weather alerts"), all return spoken dialog
  authored by the same narrator, and all are usable from Shortcuts, Siri, and
  the Shortcuts automation engine.
- **W-5. Apple Watch app** with: complications for current temperature, next
  alert, and sunrise/sunset; a Quick Weather crown-scrollable report;
  notification forwarding with distinct haptics per tier; and full VoiceOver
  support including custom actions. The watch is the right device for a
  warning -- it taps the wrist.
- **W-6. Handoff and Continuity.** Reading a location's report on the watch or
  the phone offers to continue on the Mac or iPad.
- **W-7. Share and export.** Any report or alert can be shared as plain text
  (the narrative, not a screenshot), and the whole current report can be copied
  in one action -- the ported "copyable read-only field" behavior.

---

## 10. iPad, Mac, and CarPlay

- **P-1.** The app is a single SwiftUI codebase shipping to iPhone, iPad, and
  Mac (Catalyst or native, decided at implementation time), so the "macOS next"
  line in the Windows PRD is satisfied by this work rather than by a second
  port. The Mac build additionally exposes the Windows keyboard accelerators.
- **P-2.** iPad: multi-column layout with locations in the sidebar, full
  keyboard support, Stage Manager and multi-window aware. Split view keeps the
  reading order rule (A-3) within each column.
- **P-3.** CarPlay: **alerts only**, presented through CarPlay's notification
  surface, plus a "Speak my weather" list item. No forecast browsing while
  driving. The NOAA Weather Radio hand-off to Quill Radio (§12.2) is available
  from CarPlay because that is the one weather interaction that genuinely
  belongs in a car.

---

## 11. Sync -- settings and identifications that track either way

Full design is in the platform spec; the requirements binding on this app:

- **S-1.** Sync is **opt-in**, **end-to-end encrypted**, and **zero-knowledge**.
  It uses **QuillSync**, the engine that already exists at
  `quill/apps/beacon/quillsync/` -- an append-only commit log of AES-GCM
  encrypted, content-addressed blobs under a scrypt-derived vault key. Nothing
  new is invented.
- **S-2.** Three transports, user-chosen, all carrying the identical encrypted
  log so a user can switch or use several:
  1. **iCloud Drive folder** (default on Apple devices). Because iCloud Drive is
     also available on Windows, this gives Windows-to-iPhone sync **with no
     QUILL server at all**.
  2. **Any folder** -- OneDrive, Dropbox, Syncthing, a USB stick. This is the
     existing `FolderTransport`.
  3. **The QuillSync server** -- passwordless magic link, per-device revocable
     token, for users with no cloud drive.
- **S-3.** What syncs (the "identifications" that must track either way):

  | Scope | Syncs | Rationale |
  |---|---|---|
  | Saved locations, their friendly names, order, groups, and primary | Yes | The core identification set |
  | Units, field toggles, forecast/hourly/daily counts | Yes | The user's voice preferences follow them |
  | Alert severity floor, muted event list, snoozes, quiet hours | Yes | Hard-won tuning must not be re-done per device |
  | Narration preferences (concise labels, announcement verbosity) | Yes | |
  | NOAA transmitter favorites | Yes | Shared with Quill Radio's favorites namespace |
  | Notified-alert id set | Yes, with a short TTL | Prevents a second device re-announcing what the first already did |
  | Push registration, device token | No -- device scope | Meaningless elsewhere |
  | Alert sound file selection, haptics, Critical Alert grant | No -- device scope | Platform-specific |
  | Location permission state, current-location fixes, travel history | **Never** | Privacy floor |
  | Last-good weather cache | No | Regenerated cheaply; syncing it wastes bandwidth |

- **S-4.** Entity ids are partitioned `shared/...` and `device/<device-id>/...`
  exactly as the Beacon integration plan specifies, so device-scoped settings
  can live in the same log without leaking across machines.
- **S-5.** Merge is field-level last-writer-wins on scalars with a union merge
  on lists (muted events, groups, locations), using the existing
  `merge.union_lists`. A location removed on one device and edited on another
  surfaces as a conflict the user resolves in one tap, with the resolution
  spoken.
- **S-6.** The vault key lives in the **iOS Keychain** with
  `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` and is never written to the
  sync log, never sent to any server, and never included in a backup that could
  travel. Losing it means losing sync, not losing data -- local data is always
  intact.
- **S-7.** Wire format parity is mandatory: scrypt N=2^15, r=8, p=1, 32-byte
  key; AES-GCM with a 12-byte nonce and AAD `quillsync:dek`; SHA-256 content
  addressing. The Swift implementation (CryptoKit) must decrypt a blob written
  by the Python implementation and vice versa, verified by a cross-language
  fixture test in CI.
- **S-8.** Sync status is fully accessible: a spoken state ("Last synced 4
  minutes ago over iCloud Drive; everything up to date"), an explicit "Sync
  now", and a plainly worded error that says what to do.

---

## 12. Ecosystem behavior

### 12.1 Two apps, one settings store

- **E-1.** Quill Weather for iOS and Quill Radio for iOS share the QuillKit
  settings and sync layer through an **App Group** container, so a location
  saved in one is instantly present in the other on the same device -- the
  direct equivalent of the shared `%APPDATA%\Quill` store on Windows.
- **E-2.** Neither app requires the other. Each degrades to a described,
  working state alone.

### 12.2 The NOAA Weather Radio hand-off

- **E-3.** Quill Weather finds the transmitter covering a location (F-12) and,
  when Quill Radio for iOS is installed, hands the stream to it via an App
  Intent -- so the desktop's honest limitation ("Quill Weather can find but not
  play it") is finally closed. When Radio is not installed, the app offers the
  App Store link and still shows the callsign, frequency, and SAME code, which
  is what a user with a physical receiver actually needs.

### 12.3 Cross-app announcement etiquette

- **E-4.** A `Critical` or `Urgent` weather alert **ducks Quill Radio's
  playback** and speaks over it, then restores the previous volume -- the ported
  "single-player rule" applied across apps through the shared audio session
  policy. Nothing below `Urgent` ever interrupts audio.

---

## 13. Privacy, security, and safety

- **N-1.** No analytics, no telemetry, no crash-reporting SDK that transmits
  automatically. Diagnostics are generated on request, shown to the user in
  full, redacted through the ported `redaction` rules, and shared only by
  explicit action.
- **N-2.** Every network destination is enumerated in the app's own privacy
  screen, in plain language, with what each one receives. The Privacy Manifest
  (`PrivacyInfo.xcprivacy`) declares the same set and declares **no** tracking
  domains.
- **N-3.** App Transport Security is left at its strict default with no
  exceptions.
- **N-4.** All persisted files use Data Protection
  (`.completeUnlessOpen` minimum), and secrets use the Keychain, never
  `UserDefaults`.
- **N-5.** A "Safe Mode" equivalent -- **Offline Mode** -- disables every
  network surface in one switch, mirroring `QUILL_SAFE_MODE=1`, and the app
  remains usable against cached data.
- **N-6.** The safety disclaimer (§4.4) is shown at first launch, is present in
  the alert settings screen, and cannot be permanently dismissed from the
  settings screen.
- **N-7.** Errors are coded, using the ported `QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>`
  scheme, so a user's report of a failure is actionable and a Swift error can be
  matched to its Python sibling.

---

## 14. Quality, testing, and the definition of done

- **Q-1. Narration golden corpus.** A JSON corpus of report fixtures and their
  expected spoken strings is shared by the Python and Swift test suites. Any
  wording change must update the corpus, and both suites must then pass. This is
  the mechanism that makes R-1 real rather than aspirational.
- **Q-2. Accessibility audit in CI.** Every screen is run through
  `XCUIApplication.performAccessibilityAudit()` for all audit types on every
  pull request. Failures block the build. This is the iOS analogue of QUILL's
  dialog-inventory and banned-pattern gates.
- **Q-3. Scripted VoiceOver run.** Before every release, a scripted end-to-end
  run covers: first launch, permission grant and refusal, add location by ZIP
  and by voice search, read a full report, navigate every rotor, perform every
  custom action, receive a test alert at each tier, and complete a sync pairing.
  It is performed with the screen curtain on.
- **Q-4. Snapshot tests** at the default and `AX5` Dynamic Type sizes, in light
  and dark, with Increase Contrast on and off.
- **Q-5. Provider contract tests** run against recorded fixtures, never the live
  network, so the suite is deterministic; a separate, clearly-labeled live suite
  runs on a schedule to catch provider drift (the same pattern as QUILL's live
  AI regression suite).
- **Q-6. Battery and data budget.** A full day of normal use with push enabled
  and three saved locations must consume less than a stated budget of background
  time and cellular data, measured with Instruments and asserted in the release
  checklist.
- **Q-7. Done means:** the golden corpus passes on both platforms, the
  accessibility audit is clean, the scripted VoiceOver run is complete, the
  privacy manifest matches the actual egress list, attribution is present on
  every WeatherKit-derived surface, and the user guide and CHANGELOG are updated
  in the same change.

---

## 15. Phasing

Each phase is shippable and each ends with a real user able to do something they
could not do before.

**Phase 1 -- The voice, on a phone.**
QuillKit foundation; the narrator port with the golden corpus green; saved
locations with the enriched record; NWS and Open-Meteo providers behind the
audited chokepoint; Weather Now and Quick Weather; the full VoiceOver contract
(§5.1 through §5.5, §5.7); Apple geocoding. No push, no sync, no WeatherKit yet.
*Ships when a blind user can add a place and hear the complete report.*

**Phase 2 -- Apple Weather and the things only iOS can say.**
WeatherKit integration with attribution and availability checks; minute-by-minute
precipitation; the fusion and disagreement model; provenance via Custom Content;
worldwide hourly; Audio Graphs.
*Ships when the app says something the Windows app cannot.*

**Phase 3 -- Being told, not asking.**
Current location, reduced accuracy, geofenced arrival; local notifications and
background refresh; the full alert lifecycle and revision graph; the Critical
Alerts entitlement application; Live Activity; widgets, Control Center, App
Intents, Siri.
*Ships when the phone wakes the user for a tornado warning.*

**Phase 4 -- QuillPush.**
The zone-subscription relay and APNs delivery, with the iCloud-folder-only
degradation path fully working for users who decline it.
*Ships when alerts arrive in seconds rather than minutes.*

**Phase 5 -- Everything tracks either way.**
QuillSync adoption: the Swift engine with cross-language fixture parity, the
three transports, the scope map, conflict resolution, and the Windows-side
adapter that makes Windows a peer.
*Ships when a location added on the desktop is on the phone before the user
picks it up.*

**Phase 6 -- The rest of the ecosystem.**
Apple Watch app and complications; iPad and Mac layouts; CarPlay alerts; the
Quill Radio NOAA hand-off; travel mode; location groups; historical and normals;
marine and fire segments; textual radar interpretation.

---

## 16. Open questions to resolve before Phase 2 and Phase 4

These are called out explicitly rather than assumed, because getting them wrong
is expensive:

1. **WeatherKit call budget.** The Apple Developer Program includes a monthly
   call allowance; beyond it, calls are billed. Confirm the current allowance
   and pricing tiers, then design the cache policy to fit -- per-location
   coalescing, a minimum refresh interval, and a hard per-device daily ceiling.
   Widgets and the watch must share the app's cache, not multiply the call
   count.
2. **WeatherKit alert coverage and content by region.** Confirm which regions
   return alerts, and whether the payload carries a usable body or only a
   summary and a details URL, before promising non-US alert text (U-13).
3. **Minute-precipitation coverage.** Confirm the supported regions so the
   sentence is offered only where it exists (D-6 makes this safe by default).
4. **Critical Alerts entitlement.** Confirm Apple's current criteria and
   turnaround. The product must be fully honest in the interim (U-4).
5. **QuillPush hosting and cost.** The relay's steady-state cost is dominated by
   the NWS poll, not by fan-out; confirm the hosting shape against the existing
   `quill-ai-gateway` deployment pattern before building.
6. **iCloud Drive on Windows behavior** for a directory of many small files
   under concurrent write -- validate the `FolderTransport` commit-log shape
   against real iCloud sync semantics before making it the default transport.
7. **App Store review posture** on a weather app requesting Always location and
   Critical Alerts -- prepare the review notes and the demonstration script
   ahead of first submission.

---

## 17. Relationship to the existing documents

- The Windows Quill Weather PRD (`standalone/weather/docs/prd.md`) remains the
  authoritative specification for the shared weather **domain**: the alert
  model, the tier derivation, the settings keys, the narration rules, and the
  safety posture. This document specifies the **iOS product** and does not
  restate that spec; where the two disagree, the Windows PRD wins on domain
  semantics and this document wins on iOS delivery.
- Items F-14 through F-21 are the Windows PRD's own unbuilt sections. Building
  them here does not fork them; the design flows back under R-4, and the Windows
  PRD's corresponding sections should be updated to reference this document as
  the design of record once each ships.
- `quillville-apple-platform-spec.md` owns QuillKit, QuillSync adoption,
  QuillPush, the narration golden corpus, and the Apple repo layout, and is
  shared with Quill Radio for iOS.
