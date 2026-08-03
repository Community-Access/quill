# Quill Weather -- Product Requirements

This is the complete, authoritative product-requirements document for the QUILL Weather feature set -- the weather code shared by the standalone **Quill Weather** app, **Quill Radio**, and **QUILL**. It moved here from the Quill Radio PRD when Quill Weather became its own app (2.2.0). For what is specific to Quill Weather *as a standalone app* (its own process, tray, run-at-login, independent distribution), see the app-specific notes at the end of this document.

### Implementation status (2.2.0)

Much of this roadmap is now shipped. As of 2.2.0 the following are **delivered**:

- **Weather Center** with current conditions, the NWS period forecast, the extended daily outlook, active alerts, and air quality (2.1.0), plus, new in 2.2.0, the **Hourly forecast** pane (§ "Hourly Conditions"), a locally-computed **moon almanac** (phase, illumination, moonrise, moonset), and a **two-clock time summary** (`render.time_summary`) that speaks the local time **at the searched location**, the local time **where the reviewer is**, and **when the reading was checked** — collapsing to a single clock, with "the same time zone", when both share a UTC offset.
- **Weather Guardian (§5.2)** — background monitoring of US alerts that **speaks newly-issued watches/warnings** (forced/interrupting speech for Urgent-and-above), announces all-clear, shows a system-tray toast, keeps running while minimized to the tray, and auto-resumes on launch. A **severe-weather mode** tightens the poll (down to the NWS 30-second courtesy floor, default 60 s) while an alert is active and relaxes afterward — the free-API approximation of push latency. **Pause/Resume** snoozes it without turning it off. Since 2.2.0 the watch covers **every saved location at once** by default (§"Standalone Quill Weather app" item 8), one monitor state per place, with a single combined baseline summary; per-location *selection* UI is still to come.
- **Announcement delivery on multiple channels** — announcements travel through the shared announcement service, reaching speech, a connected **braille display** (with burst coalescing and sticky errors), and the status line's message slot, with each channel isolated from the others' failures. The shared **Repeat Last Announcement** and **Announcement Self-Test** commands exist in the shell but are **not yet surfaced** in Quill Weather (§"Standalone Quill Weather app" item 9).
- **Runs while the app is closed** — the standalone **Quill Weather** tray app (`apps/weather.py`) runs the watch as its own process; **Start Quill Weather with Windows** (per-user Run key + start-in-tray) watches from login; and an **OS-scheduled background check** (`platform/windows/scheduled_task.py` + `core/weather/headless_check.py`) runs a short-lived `quill-weather --check-once` with **no persistent process**, toasting new alerts.
- **An alert sounder** — a bundled chime with settings to disable it, choose a custom `.wav` (with Play preview), and set the repeat count (1–10) — plus a **Test Alert** that previews the whole experience (text, sound, tray, dialog), marked as a test.

**Still planned / not yet shipped:** the full **Voice Studio (§9)** per-feed voices and earcons; **Weather Channels (§5.3)** continuous generated audio; the **QUILL Alert Relay (§17)** NWWS push source (evaluated and deferred — it needs per-user NWS credentials and an XMPP feed for only a marginal gain over the shipped fast poll); condition-change monitoring (announce "now raining"); and a pure OS-level *service* (no process at all until an alert). The sections below remain the authoritative spec for those.

## QUILL Weather
### Product Requirements Document

**Working title:** QUILL Weather  
**Ecosystem:** QUILL / QuillVille  
**Document status:** Product definition and implementation-ready working draft  
**Version:** 1.0  
**Date:** July 19, 2026  
**Primary platforms:** Windows first; macOS next; iOS considered in later phases  
**Product posture:** Accessibility-first, screen-reader-first, keyboard-first, local-first, provider-based, safety-conscious

---

## 1. Executive Summary

QUILL Weather transforms official weather data into an immediate, understandable, highly configurable, and delightfully accessible weather experience.

It is not merely a weather screen. It is a persistent **Weather Guardian**, an accessible **Weather Center**, a flexible **audio weather channel generator**, a location-aware **Alert Center**, and a deeply configurable **Voice Studio** built on the QUILL speech framework.

A user should be able to:

1. Add a home, work, family, travel, event, or temporary location in seconds.
2. Hear current conditions immediately.
3. Receive watches, warnings, advisories, updates, and cancellations as soon as QUILL receives them.
4. Continue receiving alerts while the main QUILL window is closed, provided QUILL Weather Guardian is running.
5. Assign different voices, engines, rates, volumes, earcons, verbosity levels, and interruption rules to different weather feeds and alert scenarios.
6. Build continuous generated audio channels from authoritative weather data.
7. Listen to a live community NOAA Weather Radio stream when one is available.
8. Understand where every piece of weather information came from, when it was issued, when it was last checked, and whether it may be stale.
9. Use every major feature without sight, without a mouse, and without needing to interpret a visual map.

The initial primary data provider will be the United States National Weather Service at `api.weather.gov`. The NWS API provides forecasts, hourly forecasts, observations, alerts, zones, stations, and grid data as open government data. It is cache-aware, supports conditional requests, and requires an identifying User-Agent. NWS recommends requesting alert updates no more frequently than every 30 seconds.

For faster alerts, a later QUILL Alert Relay can subscribe to the NOAA Weather Wire Service Open Interface. NWS describes NWWS as its fastest method for receiving text alerts and weather products, generally within 10 seconds of issuance. The relay will reconcile those pushed products with the public NWS alerts API and deliver normalized updates to subscribed QUILL clients.

QUILL Weather must never imply that it replaces Wireless Emergency Alerts, a physical NOAA Weather Radio, local emergency instructions, or other official safety channels. It is an additional accessible delivery and interpretation tool.

---

## 2. Product Vision

### 2.1 Vision statement

> Weather should never be hidden behind a map, buried in a dashboard, delayed by an inaccessible workflow, or spoken in a voice the user cannot understand.

QUILL Weather meets people where they are. It provides as much or as little weather information as the user wants, in the voice they choose, for the places and people they care about.

### 2.2 Product promise

QUILL Weather makes five promises:

#### Everything can be reached

Every location, alert, forecast period, setting, history item, source status, and audio control is keyboard accessible and represented through native or predictably accessible controls.

#### Important state is never hidden

An alert’s status, severity, urgency, certainty, effective time, expiration, affected area, source, update history, and delivery state are available as text and speech. Color, icon, animation, and screen position are never the only means of conveying meaning.

#### Official information remains official

QUILL preserves the source alert, its identifiers, its lifecycle, and its authoritative text. QUILL may organize or deterministically summarize information, but it will not silently rewrite emergency instructions.

#### The user controls the voice

Different weather content can use different QUILL speech providers, voices, rates, pitches, volumes, pronunciation dictionaries, earcons, and interruption behaviors.

#### Fast does not mean careless

QUILL prioritizes alert speed while using deduplication, update reconciliation, source freshness, delivery logging, and transparent fallback behavior.

---

## 3. Goals

### 3.1 Primary goals

1. Provide fast access to official current conditions, forecasts, and alerts.
2. Keep monitoring selected locations while QUILL Weather Guardian is running.
3. Deliver new, updated, escalated, downgraded, extended, and cancelled alerts without forcing the user to open the main window.
4. Allow unlimited saved locations, subject only to practical local storage and service limits.
5. Support location groups and multi-location weather feeds.
6. Generate highly configurable spoken weather channels from structured data.
7. Provide per-feed, per-content, per-location, and per-alert speech scenarios.
8. Integrate naturally with the existing QUILL speech provider and voice framework.
9. Preserve raw provider data and normalize it into a stable internal weather model.
10. Work without a QUILL account in local mode.
11. Use QuilleSync optionally for encrypted synchronization of saved locations, feed definitions, voice mappings, alert rules, and preferences.
12. Support live NOAA Weather Radio stream catalog entries without making live audio a prerequisite for weather or alert availability.
13. Provide strong diagnostics and a human-readable event history.

### 3.2 Success measures

QUILL Weather will be considered successful when:

- A new user can add a location and hear current conditions within 30 seconds of launching the feature.
- A returning user can hear the primary location’s current conditions within 3 seconds when fresh cached data is available.
- The alert monitor operates while the main window is closed.
- A new alert is announced within one polling cycle in local API mode.
- A relay-delivered alert is normally announced within 15 seconds of relay receipt.
- Alert updates do not produce duplicate announcements unless the user has chosen repeat behavior.
- Every alert action can be completed with a keyboard and screen reader.
- Voice routing works independently for routine weather, watches, warnings, emergency instructions, and system status.
- Source freshness and failure states are always understandable.
- No emergency alert content is replaced by an unmarked generative summary.

---

## 4. Non-Goals

The initial product will not:

1. Claim to be a certified emergency warning receiver.
2. Replace Wireless Emergency Alerts, local emergency management, a physical NOAA Weather Radio, or instructions from public safety officials.
3. Activate the Emergency Alert System.
4. Generate meteorological predictions independent of official providers.
5. Use generative AI to rewrite life-safety instructions as the only presented version.
6. Promise a live NOAA audio stream for every city or transmitter.
7. Require an account, subscription, or cloud relay for basic weather access.
8. Require visual map interaction.
9. Attempt to provide global forecast coverage in the first release.
10. Store continuous precise-location history by default.
11. Treat all provider values as equally current or equally reliable.
12. Infer missing observations or alert instructions and present the inference as source data.

---

## 5. Product Components

### 5.1 QUILL Weather Center

The main accessible weather workspace.

Primary sections:

- Weather Now
- Active Alerts
- Forecast Timeline
- Hourly Conditions
- Weather Details
- Saved Locations
- Location Groups
- Weather Feeds
- NOAA Weather Radio Explorer
- Alert History
- Voice Studio
- Settings
- Source and System Status
- Diagnostics

The Weather Center will use a simple semantic structure with predictable headings, lists, property views, and command menus. Users can choose a compact view or detailed view.

### 5.2 Weather Guardian

A lightweight background process responsible for:

- Alert monitoring
- Forecast refresh scheduling
- Tray presence
- OS notifications
- Speech and earcon delivery
- Feed refreshes
- Relay connectivity
- Network recovery
- Stale-data detection
- Alert lifecycle reconciliation
- Delivery history

Weather Guardian starts with the user only when explicitly enabled. It does not require administrator privileges.

Closing the Weather Center does not close Weather Guardian. Exiting Weather Guardian requires an explicit Exit Monitoring command.

### 5.3 Weather Channels

A Weather Channel is a generated audio feed assembled from selected structured content.

Example channel:

1. Channel identification
2. Active critical alerts
3. Current conditions
4. Next six hours
5. Today and tonight
6. Extended forecast
7. Hazardous weather outlook
8. NOAA Weather Radio transmitter information
9. Last-update status
10. Repeat after a configured interval

Channels can be played on demand or continuously. New alerts can interrupt or queue according to the channel’s alert policy.

### 5.4 Alert Center

A complete, searchable history and current-state view for all monitored locations.

It distinguishes:

- New alert
- Updated alert
- Escalated alert
- Downgraded alert
- Extended alert
- Area changed
- Instructions changed
- Corrected alert
- Cancelled alert
- Expired alert
- Test message
- Unknown lifecycle event

The Alert Center preserves alert revisions and clearly identifies what changed.

### 5.5 Voice Studio

The configuration surface for weather speech scenarios.

Voice Studio allows the user to assign voices and behaviors by:

- Feed
- Location
- Location group
- Content type
- Alert event
- Alert severity
- Alert urgency
- Alert certainty
- Alert lifecycle event
- Language
- Time of day
- Foreground or background state
- Headphones or speakers, where supported
- Routine, important, urgent, or critical priority

### 5.6 NOAA Weather Radio Explorer

A searchable transmitter and stream catalog containing:

- Call sign
- Transmitter city and state
- Frequency
- Counties served
- SAME codes
- Coverage notes
- Operational status
- NWS office
- Community audio stream, when available
- Stream provider
- Stream last verified time
- Stream health
- Official or community provenance
- Receiver-node information, when applicable

QUILL must clearly differentiate:

- Official NWR transmitter metadata
- Official NWS data
- Community-operated audio streams
- QUILL-generated weather audio

---

## 6. Core User Experiences

### 6.1 First launch

On first launch, QUILL Weather asks one accessible question:

> Which location would you like to use first?

Available methods:

- Enter city and state
- Enter ZIP code
- Enter an address
- Use current location
- Enter latitude and longitude
- Search by county
- Search by NOAA Weather Radio call sign
- Skip and explore sample data

The user reviews resolved choices before saving. QUILL announces ambiguities such as multiple cities with the same name.

After selection, QUILL immediately presents:

- Location name
- Current conditions
- Active alert count
- Next forecast period
- Data source
- Last update time

The user is then offered an optional, clearly explained choice to enable Weather Guardian at sign-in.

### 6.2 Quick Weather

A configurable global command speaks:

- Location
- Temperature
- Feels-like temperature, when meaningful
- Current condition
- Wind
- Active alert count
- Next meaningful forecast change
- Data age

Example:

> Phoenix. 108 degrees, feels like 112. Mostly sunny. Southwest wind 8 miles per hour. One Excessive Heat Warning is active. Conditions were updated 6 minutes ago.

The quick response must be deterministic and configurable.

### 6.3 Active alert arrival

When a new alert arrives:

1. Weather Guardian validates and normalizes it.
2. The alert is matched against monitored locations and alert rules.
3. QUILL deduplicates it against existing revisions.
4. QUILL determines its priority scenario.
5. The configured earcon plays.
6. The configured voice announces the headline.
7. An accessible OS notification appears when enabled.
8. The system tray state changes.
9. The Alert Center records receipt and delivery.
10. The user can open details, repeat, acknowledge, snooze allowed repeats, or move directly to instructions.

Example spoken sequence:

> Weather Warning. Tornado Warning for Pima County, including the Tucson area, until 4:45 PM. Take shelter now. Press the configured Alert Details command for the complete official message.

For warnings where the official message contains instructions, the user must be able to hear those instructions immediately without navigating through unrelated details.

### 6.4 Alert update

An update must not be treated as a duplicate merely because the event name is unchanged.

QUILL compares:

- Headline
- Severity
- Urgency
- Certainty
- Effective, onset, expiration, and end times
- Area description
- Geometry and geocodes
- Description
- Instruction
- Response type
- Event codes
- References
- Parameters
- Sender and issuing office

The announcement can say:

> Update to the Tornado Warning for Pima County. The warning now expires at 5:15 PM. The affected area has expanded eastward. Instructions remain unchanged.

A user can choose:

- Headline only
- Changes only
- Changes plus instructions
- Entire updated alert
- Silent log for low-priority updates

### 6.5 All-clear behavior

When an alert is cancelled or expires:

- The Alert Center updates immediately.
- The tray state is recalculated.
- The user’s configured all-clear scenario runs.
- QUILL never says “all clear” unless the source explicitly supports that interpretation.
- Default wording is factual:

> The Severe Thunderstorm Warning for Maricopa County has expired. Two other advisories remain active.

### 6.6 Continuous weather channel

A user starts “Home Weather Radio.”

QUILL generates a continuous audio experience using a selected program clock. Routine content repeats at user-defined intervals, but only changed content needs to be spoken on every cycle.

A new warning can:

- Interrupt immediately
- Finish the current sentence, then interrupt
- Finish the current segment, then interrupt
- Queue behind current content
- Announce headline only and offer details

Critical alerts default to immediate interruption, but the user retains control.

### 6.7 Multi-location monitoring

A user creates a group named “Family” containing:

- Home
- Keri
- David
- Brian

The group can use:

- One shared voice profile
- A unique location-identification voice
- A critical-alert voice
- Different quiet-hour rules
- A combined scan feed

Example:

> Family Weather Scan. Phoenix has one warning. Tucson has no active alerts. Austin has a Heat Advisory.

### 6.8 Travel mode

Travel mode can monitor:

- The current OS-provided location
- A destination
- Saved locations
- A configurable corridor or set of waypoints in a later release

Current location is sampled only with permission. Precise location history is not retained unless the user explicitly enables it.

---

## 7. Location Model

### 7.1 Location types

QUILL supports:

- Fixed point
- Address
- City
- ZIP code
- County
- NWS forecast zone
- Fire weather zone
- Marine zone
- State or territory
- Current location
- Temporary location
- NOAA Weather Radio transmitter
- Custom latitude and longitude
- Location group

### 7.2 Location record

Each saved location includes:

```json
{
  "id": "loc_uuid",
  "display_name": "Home",
  "resolved_name": "Phoenix, Arizona",
  "latitude": 33.4484,
  "longitude": -112.0740,
  "timezone": "America/Phoenix",
  "country": "US",
  "state": "AZ",
  "county_name": "Maricopa",
  "county_zone": "AZC013",
  "forecast_zone": "AZZ543",
  "fire_zone": null,
  "marine_zone": null,
  "nws_office": "PSR",
  "grid_x": 159,
  "grid_y": 57,
  "forecast_url": "...",
  "hourly_forecast_url": "...",
  "grid_data_url": "...",
  "observation_station_ids": [],
  "nwr_transmitters": [],
  "source_resolved_at": "2026-07-19T17:00:00Z",
  "privacy_classification": "precise",
  "sync_enabled": false
}
```

Actual provider URLs are stored as provider-owned metadata and can be refreshed.

### 7.3 Location resolution

The NWS API requires latitude and longitude for point metadata and does not provide general address geocoding. QUILL therefore uses a pluggable Geocoder Provider interface.

Resolution sequence:

1. Use exact coordinates when supplied.
2. Use OS location services when requested.
3. Use the configured geocoder for addresses, cities, and ZIP codes.
4. Present ambiguous results for user selection.
5. Resolve coordinates through the NWS `/points/{lat},{lon}` endpoint.
6. Cache point-to-grid metadata because it changes infrequently.
7. Discover forecast URLs, zones, office, grid, and nearby stations.
8. Resolve NWR transmitter coverage separately.

### 7.4 Location privacy

- No current-location access without explicit permission.
- No continuous location history by default.
- Saved precise coordinates are classified as sensitive application data.
- Local protection uses operating-system secure storage where appropriate.
- QuilleSync synchronization is optional.
- A future encrypted sync design must avoid exposing precise locations to the sync operator.
- Users can sync a coarse county or zone instead of an exact point.
- Removing a location offers to remove its weather history and cached coordinate metadata.

---

## 8. Weather Feed Model

### 8.1 Feed definition

A feed is a named weather experience containing one or more locations and one or more content segments.

Example feed types:

- Quick Weather
- Home Weather Radio
- Morning Briefing
- Evening Outlook
- Family Alert Scan
- Travel Watch
- Severe Weather Only
- Marine Weather
- Fire Weather
- NOAA Radio Stream
- Custom

### 8.2 Feed record

```json
{
  "id": "feed_uuid",
  "name": "Home Weather Radio",
  "locations": ["loc_home"],
  "segments": [
    "identity",
    "critical_alerts",
    "current_conditions",
    "next_six_hours",
    "today_tonight",
    "extended_forecast",
    "hazardous_outlook",
    "source_status"
  ],
  "repeat_interval_minutes": 15,
  "speak_only_changes_after_first_cycle": true,
  "alert_interruption_policy": "critical_immediate",
  "voice_profile_id": "voice_home_radio",
  "output_device_id": "default",
  "live_stream_fallback_policy": "generated_audio",
  "enabled": true
}
```

### 8.3 Content segments

Supported segment types include:

- Feed identification
- Location identification
- Active alert summary
- Critical alert details
- Current conditions
- Observation details
- Feels-like conditions
- Today
- Tonight
- Next period
- Next 3, 6, 12, or 24 hours
- Hourly precipitation timeline
- Temperature trend
- Wind trend
- Visibility
- Humidity and dew point
- Sunrise and sunset, through an appropriate provider
- Extended forecast
- Hazardous weather outlook
- Text products
- Marine forecast
- Fire weather forecast
- Air quality, through an appropriate provider
- NWR transmitter details
- Live stream
- Source and freshness status
- Custom deterministic template

Every segment exposes:

- Source
- Issue/update time
- Valid time range
- Data age
- Missing-field behavior
- Speech template
- Voice scenario
- Repeat policy
- Change detection policy

---

## 9. Voice and Speech Scenario Framework

### 9.1 Design principle

The QUILL speech framework is not merely a text-to-speech output switch. For QUILL Weather it becomes a **scenario router**.

A scenario answers:

- What is being spoken?
- Why is it being spoken?
- For which feed and location?
- How important is it?
- Which provider and voice should speak it?
- At what rate, pitch, volume, and language?
- Which pronunciation rules apply?
- What should it interrupt?
- Should an earcon play?
- Should the full source text or a concise deterministic version be spoken?
- Can it repeat?
- What happens if the selected voice is unavailable?

### 9.2 Speech scopes

Rules can be assigned at these levels, from broadest to most specific:

1. Global QUILL default
2. QUILL Weather default
3. Output device
4. Feed
5. Location group
6. Location
7. Content type
8. Alert priority
9. Alert event type
10. Alert lifecycle event
11. Language
12. Temporary session override

The most specific enabled rule wins. The resolved rule is inspectable.

### 9.3 Voice scenario record

```json
{
  "id": "scenario_uuid",
  "name": "Critical Warning Voice",
  "match": {
    "content_domain": "alert",
    "severity": ["Extreme", "Severe"],
    "urgency": ["Immediate", "Expected"],
    "event_types": ["Tornado Warning", "Flash Flood Warning"],
    "feed_ids": ["*"],
    "location_ids": ["*"]
  },
  "speech": {
    "provider_id": "sapi5",
    "voice_id": "Microsoft David Desktop",
    "rate": -1,
    "pitch": 0,
    "volume": 100,
    "language": "en-US",
    "pronunciation_dictionary_id": "weather_terms",
    "number_style": "natural",
    "time_style": "local_explicit",
    "units_style": "spoken_full"
  },
  "presentation": {
    "earcon_id": "warning_critical",
    "earcon_before": true,
    "earcon_after": false,
    "priority": "critical",
    "interruption": "immediate",
    "duck_other_audio_percent": 80,
    "repeat_policy": "until_acknowledged_or_changed",
    "repeat_interval_minutes": 5,
    "maximum_repeats": 3
  },
  "fallbacks": [
    "weather_default_voice",
    "system_default_voice",
    "screen_reader_announcement"
  ]
}
```

### 9.4 Recommended built-in scenarios

QUILL ships with editable defaults:

- Routine Conditions
- Forecast Narrator
- Watch Announcement
- Warning Announcement
- Immediate Life-Safety Warning
- Alert Update
- Alert Cancellation or Expiration
- Location Identification
- Source and Freshness Status
- System Error
- Live Stream Identification
- Spanish Alert
- Test Alert

### 9.5 Per-feed voices

A user can make each generated feed sound distinct.

Example:

- Home Weather Radio: Piper voice A
- Family Alert Scan: SAPI voice B
- Travel Watch: eSpeak NG voice C
- Tornado and Flash Flood Warnings: high-clarity SAPI voice D
- System and source errors: QUILL system voice
- Spanish CAP content: Spanish-capable provider voice

A feed may also use multiple voices internally:

- Announcer voice for headings
- Forecast voice for routine content
- Warning voice for urgent content
- Location voice for each city
- Status voice for source and freshness messages

### 9.6 Speech rendering rules

The renderer must correctly handle:

- Temperature symbols
- Units
- Decimal values
- Percentages
- Wind directions
- Cardinal and intercardinal abbreviations
- Time zones
- UTC versus local time
- SAME and NWS codes
- Call signs
- County and parish names
- Highway names
- Coordinates
- Acronyms
- Meteorological abbreviations
- VTEC codes in expert mode
- Repeated punctuation
- URLs, which are omitted from routine speech unless requested

Examples:

- `WSW 8 mph` becomes “west southwest wind at 8 miles per hour.”
- `40%` becomes “a 40 percent chance.”
- `AZC013` is normally spoken as “Maricopa County,” with the code available in details.
- `KPHX` can be spoken as “K P H X” or “Phoenix Sky Harbor,” based on context.

### 9.7 Pronunciation dictionaries

Weather Voice Studio supports:

- Global dictionary
- Provider-specific dictionary
- Voice-specific dictionary
- Location dictionary
- Feed dictionary
- Alert dictionary

Users can correct local names without modifying source text.

### 9.8 Voice failure behavior

If a selected voice or engine fails:

1. Try the configured fallback voice.
2. Try the QUILL Weather default voice.
3. Try the system default voice.
4. Send an accessible screen-reader or OS notification.
5. Log the failure.
6. Never silently discard a critical alert.

---

## 10. Alert Architecture

### 10.1 Alert sources

#### Initial source: NWS Alerts API

Default endpoint patterns include:

- Active alerts for a point
- Active alerts for a county or forecast zone
- Active alerts for a state
- Individual alert retrieval
- Alert type metadata

The default local polling interval is 30 seconds, matching NWS guidance not to request alert updates more frequently.

#### Optional fast source: QUILL Alert Relay

The relay can receive NOAA Weather Wire Service products through NWWS-OI, which requires NWS-issued credentials and an XMPP client. The relay:

- Receives pushed products
- Parses CAP and text products
- Normalizes alert messages
- Matches zone subscriptions
- Pushes updates to clients
- Reconciles against the NWS API
- Falls back to public API polling
- Reports relay status and latency

#### Future source: FEMA IPAWS

A future provider may add FEMA IPAWS for non-weather and broader all-hazards alerts, subject to access requirements, agreements, testing, and explicit provenance.

### 10.2 Local-first and relay modes

#### Local mode

- No account required
- Client communicates directly with official NWS endpoints
- Alert polling no more frequent than every 30 seconds
- Uses conditional requests and provider caching guidance
- Best privacy
- Slight polling delay

#### Relay-assisted mode

- Optional
- Uses coarse zones or opaque subscriptions where possible
- Receives server-pushed alert changes
- Falls back locally if relay is unavailable
- Does not require the relay to store exact addresses
- Shows connection and last-message status

#### Hybrid mode

Recommended default after the relay is production ready:

- Relay for speed
- NWS API for verification and reconciliation
- Local cache for continuity
- Independent periodic checks to detect missed messages

### 10.3 Alert normalization

The normalized alert model must preserve at least:

```json
{
  "provider": "nws",
  "source_id": "official-alert-id",
  "status": "Actual",
  "message_type": "Alert",
  "scope": "Public",
  "sent": "...",
  "effective": "...",
  "onset": "...",
  "expires": "...",
  "ends": "...",
  "event": "Flash Flood Warning",
  "sender": "...",
  "sender_name": "...",
  "headline": "...",
  "description": "...",
  "instruction": "...",
  "response": "Shelter",
  "urgency": "Immediate",
  "severity": "Severe",
  "certainty": "Observed",
  "area_description": "...",
  "geometry": {},
  "geocodes": {},
  "affected_zones": [],
  "references": [],
  "parameters": {},
  "language": "en-US",
  "raw_payload_hash": "...",
  "received_at": "...",
  "normalized_at": "..."
}
```

Raw payloads are retained according to the user’s history setting so developers and users can verify interpretation.

### 10.4 Alert matching

An alert can match a location through:

- Direct point query result
- Point-in-polygon calculation
- County or zone code
- Forecast zone
- Fire zone
- Marine zone
- State or territory
- NWR SAME code
- Explicit user rule

Where geometry and zone matching disagree, QUILL records the discrepancy and follows a configurable conservative policy. Default behavior favors notifying the user rather than suppressing a potentially relevant warning.

### 10.5 Alert lifecycle and deduplication

QUILL uses:

- Official alert ID
- Message type
- References
- Event code
- Sender
- Sent time
- Payload hash
- Geometry/geocode changes
- Expiration changes

A revision graph links all related alert versions.

A repeated provider response with no meaningful change is not reannounced unless the user selected periodic reminders.

### 10.6 Alert priority model

QUILL does not reduce urgency, severity, and certainty to a single hidden number. It preserves all three.

For delivery, QUILL computes a transparent priority tier:

- Critical
- Urgent
- Important
- Advisory
- Informational
- Test

Users can inspect why a tier was selected.

The default mapping considers:

- Event type
- Severity
- Urgency
- Certainty
- Response type
- Observed versus forecast condition
- User rules
- Location role
- Time of day
- Lifecycle event

### 10.7 Notification actions

An accessible notification can offer:

- Hear headline
- Hear official instructions
- Hear full alert
- Open Alert Center
- Acknowledge
- Repeat
- Snooze reminders
- Copy official text
- View source details
- Switch to affected location
- Start the related weather feed

### 10.8 Quiet hours and interruption safety

Users can configure:

- Routine quiet hours
- Advisory quiet hours
- Watch quiet hours
- Warning behavior
- Critical override
- Headphone-only behavior
- Earcon-only behavior
- Notification-only behavior
- Repeat limits

Default behavior:

- Routine weather respects quiet hours.
- Advisories are logged and optionally notified.
- Watches use the configured important-alert policy.
- Severe and extreme immediate alerts are allowed to interrupt.
- The user can change every default.

A “Silence all critical alerts” action requires explicit confirmation, states the consequence, and can be time-limited.

### 10.9 Authoritative text and summaries

For life-safety alerts:

1. The official headline and instructions are always available.
2. QUILL can create a deterministic “changes only” summary.
3. Optional plain-language assistance must be labeled as a QUILL interpretation.
4. Generative AI may not replace, suppress, or alter official instructions.
5. The user can always access the raw source message.

---

## 11. Weather Data Architecture

### 11.1 Primary NWS data flow

For each point location:

1. Resolve latitude and longitude.
2. Request NWS point metadata.
3. Cache office, grid, zones, and provider URLs.
4. Retrieve forecast periods.
5. Retrieve hourly forecast periods.
6. Retrieve gridpoint data for detailed time-series values.
7. Retrieve nearby stations.
8. Select observations using freshness and availability rules.
9. Retrieve active alerts.
10. Retrieve optional text products.
11. Normalize all values.
12. store source time, receipt time, and freshness.
13. Render views and speech.

### 11.2 Provider interfaces

```text
WeatherProvider
  get_capabilities()
  resolve_point_metadata()
  get_forecast()
  get_hourly_forecast()
  get_grid_data()
  get_observation_stations()
  get_latest_observations()
  get_alerts()
  get_alert()
  get_zones()
  get_text_products()
  get_source_status()

GeocoderProvider
  search()
  reverse_geocode()
  normalize_result()

AlertPushProvider
  connect()
  subscribe()
  unsubscribe()
  receive()
  acknowledge_cursor()
  get_status()

NwrMetadataProvider
  search_transmitters()
  get_county_coverage()
  get_transmitter_status()
  get_same_codes()

WeatherAudioStreamProvider
  search_streams()
  resolve_stream()
  verify_health()
  get_provenance()
```

Providers register capabilities through stable contribution points. Provider provenance is available in text and speech.

### 11.3 Normalized weather model

QUILL stores:

- Raw source value
- Source unit
- Normalized SI value
- Display value
- Display unit
- Valid time interval
- Source update time
- QUILL receipt time
- Quality or status metadata
- Provider identity
- Missing or null reason, when known

### 11.4 Time-series understanding

NWS gridpoint data may represent values across ISO 8601 time intervals rather than one record per hour. QUILL’s interval engine must:

- Expand intervals only when needed
- Preserve original valid intervals
- Avoid creating false precision
- Merge identical adjacent values for speech
- Select the value valid at a requested time
- Handle gaps explicitly
- Convert to the location’s time zone
- handle daylight-saving transitions
- distinguish issue time from valid time

### 11.5 Units

QUILL supports:

- Fahrenheit and Celsius
- Miles per hour, kilometers per hour, knots, and meters per second
- Inches, millimeters, and centimeters
- Miles, kilometers, feet, and meters
- Inches of mercury, millibars/hectopascals, and pascals

The user can set units globally, by feed, or by content type.

The source value is never destroyed when converted.

### 11.6 Observations

Observation station selection considers:

- Distance
- Data freshness
- Missing values
- Station availability
- Quality-control status when exposed
- User preference
- Airport or station identity

QUILL states the observation source and age.

It must distinguish:

- Reported observation
- Forecast value
- Derived display value
- Missing value

### 11.7 Freshness and staleness

Every view and speech response can expose:

- Issued time
- Updated time
- Valid time
- Retrieved time
- Age
- Next refresh
- Source status

Default stale thresholds are content-specific.

Example:

> Current conditions were last observed 47 minutes ago and may be stale. The forecast was updated 18 minutes ago.

QUILL must not hide stale data behind a generic “updated” label.

### 11.8 Caching

QUILL honors:

- Cache-Control
- Last-Modified
- ETag, when available
- If-Modified-Since
- If-None-Match
- Retry-After

The client avoids cache-busting query parameters.

Point-to-grid mapping is cached long-term and refreshed on provider errors, source changes, or a scheduled maintenance interval.

### 11.9 Failure and fallback

When a request fails:

1. Keep the last successful data.
2. Mark it stale.
3. Attempt a bounded retry with exponential backoff and jitter.
4. Use a secondary provider only when configured.
5. Announce source changes when they affect meaning.
6. Never merge conflicting provider values without attribution.
7. Keep alert monitoring prioritized over routine refreshes.
8. Record errors in diagnostics.

---

## 12. System Tray and Background Experience

### 12.1 Tray states

The tray item has an accessible name reflecting state:

- QUILL Weather: no active alerts
- QUILL Weather: 2 active alerts, highest priority warning
- QUILL Weather: critical alert
- QUILL Weather: data stale
- QUILL Weather: offline
- QUILL Weather: monitoring paused
- QUILL Weather: relay disconnected, local monitoring active

Visual icons may differ, but text state is authoritative.

### 12.2 Tray menu

Keyboard-accessible commands:

- Speak Quick Weather
- Active Alerts
- Repeat Last Alert
- Open Official Instructions
- Open Weather Center
- Start or Stop Current Weather Feed
- Choose Location
- Choose Location Group
- Mute Routine Speech
- Snooze Non-Critical Notifications
- Pause Monitoring
- Source Status
- Last Successful Update
- Settings
- Exit Monitoring

Destructive or safety-relevant commands include confirmation and a clear status announcement.

### 12.3 Accessible notifications

Notifications must:

- Use plain, concise titles
- Identify location
- Identify alert type
- State expiration when relevant
- Expose useful actions
- Avoid icon-only meaning
- Avoid rapidly replacing an unread notification
- Link to the exact alert revision
- remain represented in Alert History

### 12.4 Global commands

Global commands are opt-in and configurable.

Suggested defaults:

- Speak Quick Weather
- Open Active Alerts
- Repeat Last Weather Message
- Silence Current Speech
- Open Weather Center

QUILL checks for conflicts and allows reassignment.

### 12.5 Startup and shutdown

Settings include:

- Start Weather Guardian at sign-in
- Start minimized to tray
- Restore last feed
- Speak startup status
- Check alerts immediately
- Continue monitoring after Weather Center closes
- Confirm before exiting monitoring
- Resume pending alert speech after restart

---

## 13. Settings

### 13.1 General

- Primary location
- Default location group
- Start at sign-in
- Start minimized
- Default Weather Center section
- Compact or detailed mode
- Time format
- Unit system
- Language
- Data retention
- History retention
- Offline cache size
- Diagnostic logging level

### 13.2 Location

Per location:

- Friendly name
- Location role
- Monitoring enabled
- Forecast enabled
- Alerts enabled
- Alert radius or zone policy
- Time zone override
- Observation station preference
- NWR transmitter preference
- Sync behavior
- Privacy precision
- Quiet hours
- Voice profile
- Alert profile

### 13.3 Alerts

- Polling interval, constrained by provider rules
- Relay enabled
- Local fallback enabled
- Event filters
- Severity filters
- Urgency filters
- Certainty filters
- Test alert behavior
- Update announcement style
- Repeat intervals
- Acknowledgment behavior
- Expiration behavior
- Quiet hours
- Critical override
- OS notifications
- Speech
- Earcons
- Tray flashing or animation, when accessible
- Alert history retention

### 13.4 Speech

- Default provider
- Default voice
- Per-feed voices
- Per-location voices
- Per-alert voices
- Rate
- Pitch
- Volume
- Units speaking style
- Time speaking style
- Wind speaking style
- Alert verbosity
- Routine verbosity
- Heading announcements
- Earcons
- Audio ducking
- Interruption policy
- Pronunciation dictionaries
- Fallback chain
- Output device
- Screen-reader-only mode
- Self-voicing mode
- Combined mode

### 13.5 Feeds

- Segment selection
- Segment order
- Repeat interval
- Changes-only mode
- Alert interruption
- Voice profile
- Location sequence
- Silence between segments
- Intro and closing
- Source identification
- Freshness announcement
- Live stream preference
- Generated fallback
- Playback speed
- Output device
- Resume behavior

### 13.6 Privacy and sync

- Local-only mode
- QuilleSync enabled
- Items to sync
- Exact versus coarse location sync
- Current-location use
- Location history
- Clear history
- Export settings
- Delete cloud copy
- Relay subscription privacy

### 13.7 Advanced

- Provider selection
- Provider priority
- Raw data inspector
- Request diagnostics
- Cache controls
- NWWS relay status
- Alert matching strategy
- Conservative matching
- Station selection
- Geocoder provider
- Developer mode
- Simulated alert testing
- Import/export

---

## 14. Accessibility Requirements

### 14.1 Foundational requirements

- Full keyboard operation
- Predictable tab order
- Native controls whenever practical
- Correct accessible names, roles, states, values, and descriptions
- No unlabeled controls
- No custom-drawn control without a complete accessibility implementation
- No color-only, icon-only, position-only, or sound-only meaning
- Screen-reader browse and focus behavior tested
- High contrast support
- Text scaling
- Reduced motion
- Accessible error recovery
- Logical headings and landmarks
- Reviewable, selectable alert and forecast text

### 14.2 Screen-reader behavior

- Routine background refreshes do not constantly interrupt the user.
- New alert announcements use an explicit priority model.
- Changes in alert count are announced only when meaningful.
- Focus is never stolen merely because data refreshed.
- Opening a notification places focus on the alert heading.
- Alert instructions have a direct command and heading.
- Tables provide useful row and column context.
- Charts always have equivalent lists, summaries, and data tables.
- Maps are optional visual enhancements, not required navigation surfaces.

### 14.3 Keyboard behavior

Every context menu is reachable through keyboard commands and Shift+F10 where applicable.

List items support:

- Arrow navigation
- First-letter navigation
- Search
- Sort
- Filter
- Details
- Context menu
- Multi-select where meaningful

### 14.4 Audio accessibility

- Earcons are optional and never the sole signal.
- Speech can be repeated.
- Speech can be paused or stopped without dismissing the alert.
- Critical alert text remains available if audio fails.
- Volume can be configured separately from routine QUILL speech where the platform allows.
- Headphone removal does not silently lose alerts; a fallback rule applies.
- Audio ducking is configurable.
- Every continuous feed has a Stop command that is always available.

### 14.5 Cognitive accessibility

- Compact summaries
- Plain labels
- Consistent alert structure
- Changes-only views
- Optional definitions
- No unnecessary meteorological codes in default mode
- One-action access to official instructions
- Time expressed with context, such as “until 4:45 PM today”
- Clear distinction between current, forecast, and historical information

---

## 15. Safety, Trust, and Integrity

### 15.1 Safety notice

QUILL Weather displays a concise notice during onboarding and in About:

> QUILL Weather is an additional accessible weather information tool. Delivery can be delayed or interrupted by network, device, provider, or software failures. Do not rely on QUILL Weather as your only source of emergency information.

### 15.2 Source attribution

Every weather object has:

- Provider
- Issuing organization
- Source identifier
- Issue/update time
- Retrieval time
- Validity
- Original text or raw data access

Generated audio identifies itself as QUILL-generated weather using official data.

### 15.3 No silent transformation

QUILL does not silently:

- Shorten official instructions
- Change an alert’s severity
- Replace source wording with AI wording
- Merge two conflicting alerts
- Convert an expiration into an all-clear
- Hide a stale source
- suppress a warning because a visual geometry calculation failed

### 15.4 Test and exercise alerts

Test alerts are clearly identified through:

- Spoken prefix
- Text prefix
- Unique earcon
- Notification title
- History classification

Users can choose to announce, log, or ignore provider-designated tests, but development simulation mode cannot impersonate an actual alert without a persistent simulation label.

---

## 16. Data Storage

### 16.1 Local database

SQLite is recommended for:

- Locations
- Location groups
- Feeds
- Feed segments
- Voice scenarios
- Alert rules
- Alert revisions
- Delivery history
- Acknowledgments
- Provider metadata
- Observation and forecast cache
- NWR metadata
- Stream health
- Diagnostic events

### 16.2 Suggested entities

- `locations`
- `location_groups`
- `location_group_members`
- `provider_point_metadata`
- `weather_snapshots`
- `forecast_periods`
- `time_series_values`
- `observation_stations`
- `observations`
- `alerts`
- `alert_revisions`
- `alert_location_matches`
- `alert_deliveries`
- `alert_acknowledgments`
- `feeds`
- `feed_segments`
- `voice_profiles`
- `voice_scenarios`
- `pronunciation_entries`
- `nwr_transmitters`
- `nwr_coverage`
- `weather_streams`
- `stream_health_checks`
- `source_status_events`
- `settings`

### 16.3 Retention

Defaults:

- Active alert revisions: retained while active
- Expired alert history: 30 days
- Delivery logs: 30 days
- Forecast cache: provider-driven plus bounded history
- Observations: 7 days
- Raw payloads: 7 days or user-selected
- Location history: off
- Diagnostics: 14 days

All are configurable within safe storage limits.

---

## 17. QUILL Alert Relay

### 17.1 Purpose

The relay exists to improve speed, scalability, and resilience—not to make local weather dependent on the cloud.

### 17.2 Responsibilities

- Maintain NWWS-OI connection
- Receive CAP and related NWS products
- Parse and validate
- Deduplicate
- Normalize
- Maintain revision graph
- Index by zones, states, offices, and event types
- Push to subscribed clients
- Reconcile with NWS API
- Expose relay health
- Record end-to-end latency
- Avoid retaining precise client coordinates
- Apply backpressure and retry
- Support multiple relay regions later

### 17.3 Subscription privacy

Clients preferably subscribe using:

- County zone IDs
- Forecast zone IDs
- Fire zones
- Marine zones
- State codes
- Opaque server-derived subscription sets

Exact addresses are not sent.

For point-specific polygon matching, options are:

1. Match locally after receiving relevant coarse-zone alerts.
2. Send a short-lived encrypted or coarse point token.
3. Use privacy-preserving regional subscriptions.

The first option is the preferred initial design.

### 17.4 Client connection

Recommended protocol:

- Secure WebSocket for live updates
- HTTPS reconciliation endpoint
- Monotonic event cursor
- Resume after disconnect
- Heartbeats
- Signed message envelope
- Schema version
- Compression
- Rate limiting
- Anonymous client mode
- Optional authenticated QuilleSync mode

### 17.5 Reliability

The client continuously knows:

- Relay connected or disconnected
- Last heartbeat
- Last alert received
- Local fallback status
- Last successful official API check
- Current subscription set

A relay failure automatically activates local polling if enabled.

---

## 18. NOAA Weather Radio and Community Audio

### 18.1 Metadata

QUILL imports and normalizes official transmitter information:

- Station call sign
- Transmitter location
- Frequency
- State
- NWS office
- County coverage
- SAME code
- Partial-county information
- Power, when available
- Status: normal, degraded, or out of service
- Last metadata refresh

### 18.2 Stream catalog

A stream record includes:

```json
{
  "id": "stream_uuid",
  "call_sign": "WXL30",
  "transmitter_name": "Phoenix",
  "stream_url": "...",
  "provider_name": "Community Receiver Operator",
  "provider_type": "community",
  "official_noaa_stream": false,
  "codec": "MP3",
  "bitrate": 32,
  "last_verified": "...",
  "health": "online",
  "terms": "...",
  "redistribution_allowed": true
}
```

### 18.3 Stream rules

- Do not scrape or redistribute streams contrary to provider terms.
- Verify stream health.
- Clearly identify community sources.
- Never use stream silence as the only alert detector.
- The structured alert engine remains independent.
- Allow a warning to interrupt the live stream.
- Offer generated weather audio when the live stream is unavailable.

### 18.4 Receiver network

A later QUILL Community Receiver program may provide:

- Documented receiver hardware
- RTL-SDR or radio line-in support
- Secure stream publishing
- Receiver status
- Silence detection
- Audio-quality checks
- Volunteer attribution
- Geographic gap analysis
- Automated failover among receivers

### 18.5 Delivered implementation: WeatherIndex integration (Quill Radio 2.1.1)

The NWR directory-and-streams portion of this section shipped in Quill Radio
2.1.1, powered by the **WeatherIndex API** (`https://api.wxindex.org`) -- a
curated, no-auth JSON directory of NWR transmitters plus internet re-stream
URLs, organized by state, county/SAME, and NWS Weather Forecast Office.

- **Data layer** (`quill/core/radio/wxindex.py`, wx-free): `list_states`,
  `stations_for_state`, `search_stations(county/state/same/callsign)`,
  `station_detail`, `local_stations(lat, lon, county)`, and
  `to_radio_station` adapting each transmitter to the existing playable model,
  so Favorites, recording, and scheduling required no new code. `WxStation`
  carries call sign, frequency, state, county/SAME coverage, WFO, coordinates,
  and the ordered re-stream feed URLs (best first) -- the metadata set of §18.1
  as far as the upstream directory provides it.
- **Resilience**: a three-tier resolver -- live API (short timeout, HTTPS-only,
  Safe-Mode-blocked, registered in the network-egress audit), app-data cache of
  the last successful pull, bundled snapshot
  (`quill/data/noaa_directory.json`, 1,035 transmitters, regenerated by
  `scripts/snapshot_wxindex.py`) -- so browse, search, and local-station
  resolution work fully offline and survive the API disappearing. A corrupt or
  missing snapshot logs and yields an empty directory rather than raising.
- **Surfaces**: Browse's Weather / NOAA branch is a lazy State -> Station tree;
  unified search routes SAME codes (6 digits), call signs, and "County, ST" /
  state names to the directory; Weather menu > Listen to your Local NOAA
  Weather Radio resolves the saved Weather location (county/SAME match first,
  nearest covering transmitter by coordinates as fallback); Weather menu >
  Update NOAA Weather Radio Directory refreshes the cache tier on demand,
  never overwriting the bundled floor.
- **Still future** (per §18.3-18.4 and §26 phases): alert interruption of the
  live stream, generated weather audio as a stream fallback, stream-health
  verification, and the community receiver network.

### 18.6 Radio Reading Services (delivered in Quill Radio 2.1.1)

Radio reading services -- the audio information services affiliated with IAAIS
(the International Association of Audio Information Services) that read
newspapers, magazines, and local print aloud for people who are blind or
print-disabled -- are a natural companion to community NWR audio and shipped
alongside it:

- A **Radio Reading Services** Browse category and a unified-search blend
  (name, tag, or state match), implemented in
  `quill/core/radio/reading_services.py` and `directory_search.py`.
- **20 vetted services bundled** in `quill/data/reading_services.json` (WRBH
  88.3 Reading Radio, Sun Sounds of Arizona, CRIS Radio / The Chicago
  Lighthouse, Connecticut Radio Information System, KPBS and WKAR reading
  services, WUFT RRS, Down East RRS, Recording Library of West Texas, Audible
  Local Ledger, Owl Radio, Voice Corps, 95alive, ACB Media 1-5, NFB Radio
  Network, and the American Council of the Blind stream), so the category
  works offline.
- **Refresh**: Station > Update Radio Reading Services pulls live from the
  community Radio Browser directory through a cache -> live -> snapshot
  resolver that mirrors the wxindex one; reading-service keyword queries
  ("radio reading", "reading service", "audio information", ...) are filtered
  to stations whose name or tags match a reading-service term and that carry a
  playable stream URL, de-duplicated by stream. Safe Mode refuses the live
  pull and falls back to cache or snapshot.

### 18.7 Reading-service discovery methodology and rights review

The bundled list was built with a discovery pass, kept here as the method for
future refreshes of the curated set:

- **Sources.** The IAAIS national service locator (iaais.org/find-a-service)
  enumerates United States state pages and candidate services but exposes no
  public JSON API; the **Radio Browser API** (docs.radio-browser.info)
  supplies station UUIDs, resolved stream URLs, homepage, state, codec,
  bitrate, health status, tags, language, and popularity, and asks clients to
  use a descriptive User-Agent and discover/fail over among API mirrors
  (which the in-app client honors).
- **Matching.** Each IAAIS-derived service was queried against Radio Browser
  by full name, normalized name, a generic-terms-stripped name, and broader
  reading-service keyword searches. Candidates were scored on station-name
  similarity, distinctive-word overlap, website-domain and stream-domain
  agreement, state agreement, reading-service keywords, and Radio Browser
  health, then tiered: high confidence (82-100), medium (65-81.99), low
  (48-64.99), unlikely (below 48). Every tier -- including high confidence --
  went through human review before a service entered the bundled list.
- **Rights.** A Radio Browser match only establishes that a public directory
  knows the stream. It does not by itself prove the service permits
  redistribution, proxying, recording, revealing a restricted URL, or
  bypassing listener qualification (some reading services restrict listening
  to qualified print-disabled users). The curated set therefore carries only
  publicly listed streams, and per-service review covers redistribution
  permission, official-player-only status, and authentication requirements
  before inclusion. The stream rules of §18.3 apply to reading-service
  streams exactly as to NWR streams.

---

## 19. User Interface Information Architecture

### 19.1 Weather Now

Recommended reading order:

1. Location
2. Active alert summary
3. Temperature and condition
4. Feels-like condition
5. Wind
6. Observation age and station
7. Next meaningful forecast
8. Quick actions

### 19.2 Active Alerts list

Default sort:

1. Critical priority
2. Urgency
3. Severity
4. Most recently updated
5. Location

Each item speaks:

> Tornado Warning. Pima County. Immediate, extreme, observed. Updated 2 minutes ago. Expires at 4:45 PM.

### 19.3 Alert details

Headings:

- Alert headline
- What changed
- Official instructions
- Description
- Affected areas
- Timing
- Severity, urgency, and certainty
- Locations you monitor
- Source
- Revision history
- Delivery history
- Raw message

### 19.4 Forecast timeline

Accessible list alternatives:

- Period-by-period
- Hour-by-hour
- Meaningful changes
- Temperature trend
- Precipitation windows
- Wind windows
- Hazard windows

A visual chart may be included but never replaces the list.

### 19.5 Settings search

All settings are searchable by plain language.

Example search terms:

- tornado voice
- quiet hours
- home location
- alert repeat
- system tray
- Celsius
- NOAA radio
- current location privacy
- provider status

Search results explain the setting path and current value.

---

## 20. Commands and Extensibility

Suggested command IDs:

```text
weather.openCenter
weather.speakQuick
weather.openAlerts
weather.repeatLastMessage
weather.stopSpeech
weather.startFeed
weather.stopFeed
weather.switchLocation
weather.addLocation
weather.openAlertInstructions
weather.acknowledgeAlert
weather.openVoiceStudio
weather.openSourceStatus
weather.refresh
weather.pauseMonitoring
weather.resumeMonitoring
```

Extension-contributed commands use the QUILL extension naming convention, such as:

```text
ext.vendor.weatherCommand
```

Extensions may contribute:

- Weather providers
- Geocoders
- Air-quality providers
- Audio stream catalogs
- Feed segments
- Speech templates
- Pronunciation packs
- Alert classification rules
- Exporters

An extension cannot silently suppress critical alerts. Any suppression capability requires explicit user authorization and is visible in diagnostics.

---

## 21. Diagnostics and Supportability

### 21.1 User-facing status

Source Status answers:

- Is Weather Guardian running?
- Is the network available?
- Is the NWS API responding?
- Is the Alert Relay connected?
- When was each location last checked?
- When was the last alert received?
- Is any data stale?
- Is the selected voice available?
- Is a feed playing?
- Are notifications permitted by the OS?

### 21.2 Diagnostic package

The user can create a privacy-reviewed support bundle containing:

- App version
- Platform version
- Provider versions
- Redacted request timeline
- HTTP status codes
- Cache behavior
- Alert lifecycle events
- Voice resolution results
- Relay state
- Stream health
- Accessibility settings relevant to reproduction

Precise coordinates, addresses, alert text, and account identifiers are excluded by default and require explicit inclusion.

### 21.3 Raw data inspector

Expert users and developers can inspect:

- Raw JSON or CAP
- Normalized object
- Provider headers
- Cache metadata
- Rule match trace
- Voice scenario resolution
- Delivery decision
- Location-match explanation

The inspector is fully accessible and supports copying selected sections.

---

## 22. Performance Requirements

- Fresh cached Quick Weather response: target under 3 seconds.
- Initial uncached location resolution and weather: target under 10 seconds under normal network conditions, excluding geocoder delays.
- Main Weather Center initial usable state: target under 2 seconds with cached content.
- Alert processing after receipt: target under 1 second.
- Speech start for critical alert after processing: target under 2 seconds.
- Tray command response: target under 500 milliseconds.
- Background idle CPU: negligible under normal conditions.
- Memory use: bounded and documented.
- Local database operations must not block the UI thread.
- Provider requests, parsing, audio generation, and stream health checks run asynchronously.
- Alert processing has priority over routine forecast work.

---

## 23. Security Requirements

- HTTPS for all remote providers.
- Validate TLS certificates.
- Validate and bound all remote payloads.
- Treat provider text as untrusted content for rendering.
- No HTML execution from alert content.
- No arbitrary command execution from feed templates.
- Protect local secrets with OS secure storage.
- Relay messages are authenticated and schema validated.
- Stream URLs are validated before use.
- Redirects are bounded.
- Diagnostic exports are redacted.
- Dependencies are pinned and monitored.
- No API credentials embedded in the open-source client.
- NWWS credentials remain on the relay, never in distributed clients.
- QuilleSync encryption keys are not stored in plaintext.

---

## 24. Testing Strategy

### 24.1 Unit tests

- Unit conversion
- Time-zone conversion
- DST transitions
- Interval expansion
- Alert deduplication
- Revision linking
- Geometry matching
- Zone matching
- Priority classification
- Voice-rule resolution
- Speech rendering
- Pronunciation
- Cache behavior
- Retry behavior
- Stale thresholds

### 24.2 Contract tests

Saved fixtures for:

- Point metadata
- Forecast
- Hourly forecast
- Grid data
- Stations
- Observations
- CAP alerts
- Alert updates
- Cancellations
- Missing fields
- Null values
- Malformed payloads
- Provider errors

### 24.3 Alert simulation laboratory

A built-in developer and QA laboratory can simulate:

- Tornado Warning
- Flash Flood Warning
- Severe Thunderstorm Watch
- Heat Advisory
- Red Flag Warning
- Marine Warning
- Alert update
- Area expansion
- Expiration extension
- Cancellation
- Test message
- Duplicate delivery
- Relay disconnect
- API outage
- Voice failure
- Audio device change

Every simulation is unmistakably marked as a simulation.

### 24.4 Accessibility tests

Test with:

- JAWS
- NVDA
- Narrator
- VoiceOver on macOS
- Keyboard only
- High contrast
- 200% and greater text scaling
- Reduced motion
- Multiple speech providers
- Screen-reader-only mode
- Self-voicing mode

### 24.5 Real-world tests

- Multiple locations in one county
- Locations near county borders
- Partial-county alerting
- Locations covered by out-of-state NWR transmitters
- Mountain and rural areas
- Marine zones
- Network interruption
- Sleep and resume
- Clock and time-zone change
- Long-running tray session
- System restart with active alerts
- Multiple simultaneous alerts
- Alert flood during a major event

---

## 25. Acceptance Criteria

### 25.1 Location and forecast

- User can add a location entirely by keyboard.
- Ambiguous search results are understandable.
- NWS point metadata is cached.
- Current, hourly, and period forecasts are available.
- Data source and freshness are exposed.
- Missing data is identified rather than invented.

### 25.2 Background monitoring

- Weather Guardian can run without the Weather Center open.
- User can enable startup without administrator access.
- Tray state has an accurate accessible name.
- Monitoring failure is announced and logged.
- Local API fallback works when relay mode fails.

### 25.3 Alerts

- Active alerts can be queried for every monitored location.
- Default API polling does not exceed NWS guidance.
- New and updated alerts are distinguished.
- Alert revisions are linked.
- Instructions are available in one action.
- Critical alert speech has a fallback.
- Expiration does not produce a false “all clear.”
- Acknowledgment does not delete the alert.
- Test alerts are unmistakable.

### 25.4 Speech

- User can assign a voice per feed.
- User can assign a voice per alert priority.
- User can assign location identification voices.
- Missing voice falls back safely.
- Speech can be repeated and stopped.
- Stopping speech does not dismiss the alert.
- Official text remains accessible.
- Units and abbreviations are spoken naturally.

### 25.5 Accessibility

- No critical function requires a mouse.
- No alert meaning depends only on color, icon, or sound.
- Data refresh does not steal focus.
- Every chart has a text equivalent.
- Alert history is searchable and filterable.
- Settings are searchable.
- Accessible names and states pass automated and manual inspection.

---

## 26. Delivery Phases

### Phase 0: Architecture and prototypes

- Normalized weather schema
- NWS provider prototype
- Location resolution prototype
- Alert lifecycle prototype
- QUILL speech scenario prototype
- Accessible tray prototype
- Alert simulation laboratory
- Threat and privacy review

### Phase 1: Windows minimum lovable product

- Weather Center
- Saved locations
- Current conditions
- Forecast and hourly forecast
- Direct NWS alert polling
- Weather Guardian
- System tray
- Accessible notifications
- Quick Weather command
- Active Alert Center
- Basic per-content voices
- Data freshness and diagnostics
- Local-only operation

### Phase 2: Weather Channels and Voice Studio

- Feed builder
- Continuous generated audio
- Per-feed and per-location voices
- Earcons
- Pronunciation dictionaries
- Advanced interruption rules
- Location groups
- Morning/evening briefings
- Changes-only announcements
- Import/export

### Phase 3: QUILL Alert Relay

- NWWS-OI integration
- Secure push
- Zone subscriptions
- Local reconciliation
- Relay status
- Latency metrics
- Failover
- Privacy validation
- Production monitoring

### Phase 4: NWR Explorer and community audio

- Official transmitter metadata
- County and SAME mapping
- Transmitter status
- Curated stream catalog
- Stream verification
- Generated fallback
- Alert interruption over live audio
- Community receiver toolkit design

### Phase 5: QuilleSync and macOS

- Encrypted settings sync
- Saved location and feed sync
- Voice mapping portability
- macOS Weather Guardian
- macOS status menu
- VoiceOver testing
- Cross-device acknowledgment policy

### Phase 6: Expanded services

Potential future additions:

- Air quality
- Sunrise and sunset
- Lightning
- Radar data and accessible radar interpretation
- River gauges
- Tropical products
- Space weather
- Earthquake and tsunami providers
- FEMA IPAWS
- iOS companion
- Route and corridor monitoring
- Community receiver network

Each addition must preserve provider provenance and accessibility.

---

## 27. Product Risks and Mitigations

### Risk: Users assume QUILL is guaranteed life-safety delivery

**Mitigation:** Clear safety notice, source-status visibility, failure announcements, no claims of certification, and encouragement to use multiple official channels.

### Risk: Duplicate or noisy alerts

**Mitigation:** Revision graph, deterministic change comparison, acknowledgment, changes-only announcements, and configurable repeat rules.

### Risk: Over-customization suppresses important warnings

**Mitigation:** Transparent rule trace, critical-silence confirmation, safety review, reset-to-safe-defaults command, and diagnostics showing suppressed events.

### Risk: NWS API outage or rate limiting

**Mitigation:** Conditional requests, centralized relay for scale, backoff, cache, local fallback, stale-state communication, and provider abstraction.

### Risk: Voice provider failure

**Mitigation:** Multi-step fallback chain, screen-reader/OS notification fallback, and delivery logging.

### Risk: Incorrect location matching

**Mitigation:** Combine point, geometry, and zone methods; conservative default; match explanation; testing near boundaries; user-selected county/zone override.

### Risk: Community stream disappears

**Mitigation:** Health checks, multiple streams, generated audio fallback, and independent structured alert monitoring.

### Risk: Generative summaries change meaning

**Mitigation:** No generative rewrite as the authoritative alert; official text always primary; deterministic summaries; explicit labels.

### Risk: Precise location privacy

**Mitigation:** local-first storage, no default history, optional coarse subscriptions, encrypted sync, redacted diagnostics, and explicit permissions.

---

## 28. Recommended Technical Shape

### 28.1 Client modules

```text
quill_weather/
  providers/
    nws/
    geocoding/
    nwr/
    streams/
  domain/
    locations/
    forecasts/
    observations/
    alerts/
    feeds/
    speech/
  services/
    weather_guardian/
    alert_monitor/
    feed_engine/
    cache/
    sync/
    notifications/
  ui/
    weather_center/
    alert_center/
    location_manager/
    feed_builder/
    voice_studio/
    settings/
    diagnostics/
  platform/
    windows/
    macos/
  storage/
  tests/
```

### 28.2 Threading and process model

- UI process remains responsive.
- Weather Guardian can run as a separate user process.
- Database writes are serialized safely.
- Provider calls use asynchronous workers.
- Alert intake has a high-priority queue.
- Speech uses a serialized, priority-aware dispatcher.
- Critical speech can preempt routine feed speech.
- Crashes do not corrupt alert state or settings.
- Restart recovery checks active alerts immediately.

### 28.3 Speech dispatcher priorities

1. Emergency stop and user control
2. Critical alert
3. Urgent alert update
4. User-requested speech
5. Watch or important alert
6. Advisory
7. Routine weather feed
8. Background status

The user can modify the mapping, but the dispatcher always exposes the active queue and allows immediate stop.

---

## 29. Example Built-In Profiles

### 29.1 Calm and complete

- Speaks all watches and warnings
- Reads official instructions
- Uses one clear voice
- Routine brief every 30 minutes
- No repeat after acknowledgment
- Critical alerts interrupt

### 29.2 Minimal

- Critical and urgent alerts only
- Headline plus instructions
- No routine speech
- Tray and notifications remain active

### 29.3 Weather radio

- Continuous generated channel
- Forecast cycles every 10 minutes
- Alert interruption
- Station-style identification
- Separate alert voice
- Optional community NWR stream

### 29.4 Family guardian

- Multiple locations
- Location spoken first
- Warnings repeat until acknowledged
- Watches announce once
- Combined location scan
- Distinct voice per family location

### 29.5 Screen-reader integrated

- Uses screen-reader announcement path where possible
- No duplicate self-voicing
- Earcons optional
- Opens alert details in accessible text
- Speech provider used only for continuous feeds

---

## 30. Example Spoken Output

### Quick Weather

> Home, Phoenix. 108 degrees and mostly sunny. It feels like 112. Southwest wind at 8 miles per hour. An Excessive Heat Warning is active until 8 PM Monday. The observation is 6 minutes old.

### New warning

> Critical weather alert for Home. Flash Flood Warning. Immediate, severe, and observed. In effect until 6:30 PM. Move to higher ground now. Do not drive through flooded roadways. Press the Alert Details command to hear the complete official message.

### Update

> Update for Home. The Flash Flood Warning has been extended until 7:15 PM. The affected area now includes northern Maricopa County. Official instructions are unchanged.

### Stale data

> Weather data for Travel Location may be stale. QUILL last reached the National Weather Service 38 minutes ago. Alert monitoring is retrying.

### Relay fallback

> QUILL Alert Relay is unavailable. Direct National Weather Service alert monitoring remains active and checks every 30 seconds.

---

## 31. Research Basis and Official Sources

The initial design is grounded in these official NWS capabilities and constraints:

1. The NWS API provides forecasts, alerts, observations, and other weather data as open data without usage fees, subject to reasonable rate limits.  
   https://www.weather.gov/documentation/services-web-api

2. NWS forecast lookup begins with latitude and longitude through `/points/{lat},{lon}`, which returns forecast, hourly forecast, and gridpoint metadata. The point mapping can be cached.  
   https://weather-gov.github.io/api/general-faqs

3. The NWS alerts service supports JSON-LD, CAP v1.2, and Atom. NWS recommends requesting new alerts no more frequently than every 30 seconds.  
   https://www.weather.gov/documentation/services-web-alerts

4. NWS CAP fields such as urgency, severity, and certainty are specifically intended to support decision tools and synthesized voice applications.  
   https://www.weather.gov/documentation/services-web-alerts

5. NOAA Weather Wire Service is described by NWS as its fastest method of receiving text alerts and weather information, within approximately 10 seconds of issuance. NWWS-OI requires NWS-issued credentials and an XMPP client.  
   https://www.weather.gov/nwws/faq

6. NOAA Weather Radio is a nationwide network of more than 1,000 transmitters broadcasting continuous official information on seven VHF frequencies. It is fundamentally a radio transmitter service and requires a compatible receiver.  
   https://www.weather.gov/nwr

7. Official NWR station search and county coverage information includes call signs, frequencies, SAME codes, and transmitter coverage.  
   https://www.weather.gov/nwr/station_search  
   https://www.weather.gov/nwr/county_coverage

---

## 32. Final Product Statement

QUILL Weather should feel like a trusted weather desk that belongs to the user.

It should be fast without being frantic, detailed without being overwhelming, configurable without becoming inaccessible, and powerful without hiding what it is doing.

The product’s defining achievement will not simply be that it speaks the weather. It will be that it understands the structure, timing, source, priority, location, and lifecycle of weather information—and then gives every user direct control over how that information reaches them.

QUILL Weather will turn official data into an accessible living service:

- A Weather Center when the user wants to explore
- A Weather Guardian when the user needs protection
- A Weather Channel when the user wants to listen
- An Alert Center when every second and every word matters
- A Voice Studio when one voice is not enough
- A QuillVille service built around inclusion, clarity, choice, and trust


---

## Standalone Quill Weather app -- requirements

These requirements are specific to Quill Weather **as its own app**, distinct
from the shared weather feature set above.

1. **Own process, own window, own tray icon.** A separate, single-instance app
   (IPC slot `weather`), distinct from QUILL, Quill Radio, and Quill Cast, so
   all can run at once without blocking each other.
2. **Persistent, low-footprint watch.** No audio, AI, transcription, braille, or
   speech-synthesis *stacks* are bundled -- a much smaller download than Quill
   Radio. (Announcements still reach speech and a braille display, via the user's
   screen reader; see item 9. Nothing about that requires bundling an engine.)
   The build MUST also exclude the libraries the app never runs at runtime that a
   broad packaging rule would otherwise force in -- the i18n build tool, the PDF
   stack, data-science, imaging, and video libraries -- which took the portable
   ZIP from about 176 MB to 79 MB and the installer from about 123 MB to 52 MB
   with no loss of function. Keeps the alert watch running while minimized to the
   tray, resumes on launch, and offers a run-at-login option and an OS-scheduled
   background check (no persistent process required).
3. **Independent distribution and updates.** Its own installer and portable
   build. Update checking uses the **one shared Quill release feed**, from which
   each app resolves **only its own release asset** (`Quill-Weather-Setup-*.exe`
   for an installed build, `Quill-Weather-Portable-*.zip` for a portable one) and
   its own app tag's version, so a Quill Radio release can never be offered as a
   Quill Weather update and no app needs a separate repository. It carries the
   **same version number as Quill Radio** (2.2.0,
   shared weather code, released together) but a Quill Weather release can go out
   without a Quill Radio release and vice versa. Quill Weather also participates
   in the shared **QuillVille Runtime** distribution model, with a full portable
   edition, a lightweight companion edition, a full (shared-runtime) installer,
   and a thin installer -- detailed in "Distribution model" below.
4. **Sibling interoperability, through the shared QuillVille menu.** Quill
   Weather carries the family's top-level **QuillVille** menu -- the same menu,
   in the same place, in every QuillVille app -- listing "Open QUILL" and "Open
   Quill Radio", each launching a sibling in its own window; the tray menu offers
   the same list, and Quill Radio's Weather menu offers "Open the Quill Weather
   App" in return. Only released apps are listed. The QuillVille menu is
   deliberately the *family-navigation* menu rather than a functional one, which
   is what a brand name should label; functional menus keep descriptive names.
   Opening a sibling that is **not installed** must not dead-end: on a build that
   can add one, the app offers to download and install it, runs the verified
   download off the UI thread, and opens it on success, falling back to the web
   release page on failure and to an honest "not installed" message when running
   from source. On one machine the apps share a data store.
5. **Feature customization.** Switchable areas (Alert Monitoring, NOAA Weather
   Radio) via Options > Customize Features..., using the shared
   `core/app_features` model and dialog; a disabled area's menu is omitted.
6. **NOAA Weather Radio caveat.** Finds the user's local transmitter but, having
   no audio engine, cannot play it; directs the user to Quill Radio for playback.
7. **Global show/hide hotkey.** A system-wide chord, **Ctrl+Alt+Shift+W**, toggles
   the app between showing and hidden-to-tray from any application, even without
   focus -- hiding tucks the window away while alert monitoring keeps running,
   showing restores and focuses it, and the app speaks "hidden to the tray" or
   "shown". The chord is unique to Quill Weather within the QuillVille family
   (QUILL uses Ctrl+Alt+Shift+Q, Quill Radio uses Ctrl+Alt+Shift+R) so the apps
   never collide. Windows-only, via `RegisterHotKey` (the same mechanism as the
   family's hardware media keys), and strictly best-effort: if another process
   already owns the chord, Quill Weather does not grab it -- no error, no crash --
   and the tray icon still shows and hides the window. Implemented in
   `quill/ui/app_shell.py` (`_register_tray_hotkey`, `toggle_window_to_tray`)
   with a shared wx-free chord parser in `quill/ui/tray_hotkey.py`, wired for
   Quill Weather in `quill/apps/weather.py`.
8. **Multi-location alert monitoring, on by default.** Weather Guardian MUST
   watch every saved location unless an explicit watch list narrows it, so a
   dedicated weather watcher covers home, work, and family out of the box rather
   than the primary location alone. The monitor config carries a location-id list
   resolved as: explicit list, else the legacy single location field, else the
   primary location; loading a pre-multi-location config migrates the single id
   into a one-item list and keeps the legacy field in sync for older readers.
   Each tick is a **round** -- one fetch per watched place, one monitor state per
   place, a round-pending counter so N places arm exactly one next timer rather
   than N overlapping ones, per-location sound/toast/announcement, and a unioned
   save of notified alert ids so the OS-scheduled background check never
   re-toasts an alert the window already spoke. The baseline round speaks **one**
   combined summary ("3 places: Tucson, Boston, and Reno. All clear right now."),
   collapsing to the natural single-place wording for one location; start, stop,
   and status wording say either the place name or "N places". A fine-grained
   per-location selection dialog is a follow-up and warrants its own
   screen-reader validation before it ships.
9. **Announcements on every channel the app can reach.** Quill Weather MUST
   deliver each announcement through the shared announcement service rather than
   straight to speech: speech, a connected **braille display**, the status
   line's message slot, and the accessibility test capture. A failing channel
   MUST be isolated -- a display unplugged mid-sentence or a screen reader that
   went away costs that channel only, never the message. Braille MUST be written
   through the screen-reader bridge (the app bundles no braille stack of its
   own), MUST coalesce a burst of differing messages into one write per short
   window so a display is not flashed faster than it can be read, and MUST hold
   an error rather than let the next routine message wipe it. The governing
   preferences (braille on/off, braille style, dedupe window, sticky errors,
   sound cues in apps) are shared settings edited in QUILL and honored here,
   since the family shares one settings store per machine. Quill Weather does
   **not** currently surface the shared **Repeat Last Announcement** and
   **Announcement Self-Test** commands: it ships no command palette or keymap
   editor, so the shell's command registration is not called. Exposing both --
   the self-test in particular, which distinguishes "braille is broken" from "no
   display is connected" -- is an open requirement.

### Distribution model: editions and the QuillVille Runtime

Quill Weather ships under the shared **QuillVille Runtime** model used by every
QuillVille app (QUILL, Quill Radio, Quill Weather, and QUILL Audio Studio).

**The shared runtime.** All QuillVille apps share one Python runtime, the
QuillVille Runtime, installed once per user and reused by all of them. Install it
a single time -- through any app or installer that needs it -- and every app
added afterward starts instantly, with no second copy of Python. The runtime is
**reference-counted**: each app that depends on it registers a reference, and the
runtime is removed only when the last app that needs it is uninstalled. This
keeps total disk use down (one runtime, not one per app) without ever pulling the
runtime out from under an app that still needs it.

**Editions.** Four downloads are offered for Quill Weather, so the user can trade
download size against self-containment:

1. **Full portable** (`Quill-Weather-Portable-<version>.zip`, about 82 MB) --
   fully self-contained: runs from a USB stick with no installation and no
   internet, carrying a genuine, unmodified copy of Python. Weather bundles no
   audio, AI, transcription, braille, or speech-synthesis stacks, so this build
   is already compact. A `data` folder beside the exe with a `storage-mode.json`
   marker (`{"mode": "portable"}`) keeps all state on the removable medium.
2. **Companion edition** (`Quill-Weather-Companion-<version>.zip`, about 2 MB) --
   feather-light: only the app and its docs, running on the shared QuillVille
   Runtime. On first launch, if the runtime is not already installed, the app
   offers to download and install it (about 230 MB, once) with a fully
   accessible progress bar; afterward this app and every other QuillVille app
   start instantly.
3. **Full installer** (`Quill-Weather-Setup-Shared-<version>.exe`) -- installs
   the shared runtime (if not already present) plus the app, with a Start Menu
   entry, an uninstaller, and the shared data store.
4. **Thin installer** (the `-Lite` setup) -- a tiny installer that downloads the
   shared runtime only if it is not already present, then installs the app.

**Accessible runtime downloads (requirement).** Any time the QuillVille Runtime
is downloaded -- whether triggered by an installer or by an app's own first
launch -- the operation MUST present a fully accessible progress bar that works
with NVDA, JAWS, and Narrator, announcing progress as a spoken percentage. The
one-time nature of the download (once per user, then reused) MUST be clear to the
user before it begins.

**Security and antivirus (requirement).** The app's launcher MUST be a genuine,
tiny native program, and the bundled Python MUST be the official, unmodified
build. Earlier builds used a renamed and modified copy of Python's `pythonw.exe`
as the launcher, a pattern some antivirus engines flagged as a false positive;
that pattern is eliminated. This reduces spurious antivirus detections across the
whole QuillVille family and complements (but does not replace) the still-planned
code-signing work.
