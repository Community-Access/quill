# NOAA Weather Radio via WeatherIndex (wxindex) — QUILL Radio 2.1.1

Status: approved design (brainstorming). Target release: **QUILL Radio 2.1.1**.

## Goal

Replace QUILL Radio's weak "Weather / NOAA" experience — today a fuzzy
RadioBrowser name-search for the string "NOAA Weather Radio"
(`quill/core/radio/radio_browser.py::noaa_weather_stations`) — with an
authoritative, geography-aware NOAA Weather Radio (NWR) integration powered by
the **WeatherIndex API** (`https://api.wxindex.org`). NWR is broadcast over VHF;
wxindex is a curated directory of NWR transmitters plus internet re-stream URLs,
organized by state, county/SAME, and NWS Weather Forecast Office (WFO).

The integration is "rich": it powers the **Browse** NOAA section, the **Search**
feature, and a location-aware **Weather-menu** entry, and it is resilient to the
third-party API disappearing by shipping a full local snapshot.

## Where the code lives

`quill_radio` (repo `s:\quill-radio`) is a **thin wrapper** over the `quill`
package — it provides only the entry point and depends on `quill`. So all
feature code is developed in the monorepo `s:\quill` and flows to the standalone
automatically at compile time (`s:\quill-radio\scripts\build_release.ps1`). No
vendoring step. New/changed modules all live under `quill/`.

## The WeatherIndex API (no auth, JSON)

Endpoints used:

- `GET /v1/states` — states with station counts.
- `GET /v1/states/{state_slug}/stations` — canonical stations for a state.
- `GET /v1/station_search?c=&s=&same=` — lookup by county name, state, or SAME code.
- `GET /v1/wfo` and `GET /v1/wfo/{wfo_code}/stations` — group by NWS office.
- `GET /v1/stations/all` (active, with feeds) and `/all-known` (incl. no-feed).
- `GET /v1/stations/{callsign}` — full detail: frequency, coordinates, power,
  feed URLs (+ source), county coverage.
- `GET /health` — data counts / freshness (used by the snapshot script and a
  diagnostics line only).

Terms: "cache results where practical instead of polling." Feed uptime depends on
the original stream providers and can change.

## 1. Data + resilience layer — `quill/core/radio/wxindex.py`

A small, `wx`-free client plus a **three-tier resolver** so capability never
depends on a live API call:

1. **Live API** — fetched over HTTPS with a short timeout, blocked in Safe Mode,
   tracked by the network-egress audit (GATE-9), same posture as the other radio
   directory sources.
2. **App-data cache** — successful live responses are cached under
   `<app_data>/radio/wxindex-cache/` with a timestamp; a background refresh
   updates it at most once per configurable interval (default 7 days). Cache is
   consulted when the live call fails or is skipped.
3. **Bundled snapshot** — `quill/data/noaa_directory.json`, a complete dump of
   the directory shipped with the app; the final fallback so Browse/Search/local
   lookup keep working even if wxindex goes away permanently.

Public functions (all return domain objects, never raw JSON):

- `list_states() -> list[WxState]`
- `stations_for_state(slug) -> list[WxStation]`
- `search_stations(*, county=None, state=None, same=None, callsign=None) -> list[WxStation]`
- `station_detail(callsign) -> WxStation | None`
- `local_stations(lat, lon, *, county=None) -> list[WxStation]` — resolves the
  caller's location to covering transmitter(s) (see §4).
- `to_radio_station(WxStation) -> RadioStation` — adapt to Radio's existing
  playable model so Favorites, recording, and the player all work unchanged.

`WxStation` carries callsign, frequency (MHz), state, counties/SAME covered, WFO
code, coordinates, and the ordered list of re-stream feed URLs (best first).

### Refreshing the directory (user-facing)

Anyone can pull the latest directory on demand, not just wait for the 7-day
background refresh:

- A **"Update NOAA Weather Radio directory"** command (in the Weather menu next
  to "Your Local NOAA Weather Radio", and reachable from the Browse dialog's
  existing per-source "Reload from internet"). It re-fetches the full directory
  from the live API (states + `/stations/all-known` + WFO) **atomically** into
  the app-data cache tier, off the UI thread, with progress and cancel, blocked
  in Safe Mode.
- On success it announces the outcome — station/state counts and the upstream
  freshness from `/health` — and stamps a **"directory last updated"** time that
  the station-detail read-out and the command surface. On failure (offline / API
  down) it reports clearly and leaves the existing cache/snapshot intact.
- Precedence is unchanged: a manual refresh writes the **cache** tier, which
  already takes priority over the bundled snapshot, so the fresh data is used
  immediately without a restart. The bundled snapshot is never overwritten (it
  is the permanent floor); "reset to bundled" is available by clearing the cache.
- The Browse dialog's per-source "Reload from internet" refreshes just the
  highlighted branch (e.g. one state) for a lighter, targeted pull.

### Snapshot build script — `scripts/snapshot_wxindex.py`

Walks `/v1/states`, every state's stations, `/v1/stations/all-known`, and
`/v1/wfo`, assembling one normalized document written to
`quill/data/noaa_directory.json` with a `generated_at` stamp and the upstream
`/health` counts. Run manually / in CI when refreshing the bundled data; the
result is committed. Idempotent and safe to re-run.

## 2. Browse — replace the "Weather / NOAA" source

`quill/ui/radio/browse_tree_dialog.py`'s `_SOURCES` "Weather / NOAA" branch stops
calling `noaa_weather_stations` (fuzzy) and becomes a real geography tree:

```
Weather / NOAA
  <State>
    <County or WFO>        (grouping chosen per §"open questions" default: State -> County -> Station)
      <Station: callsign - freq - place>   Enter plays the best feed
```

Lazy-loaded like the other sources. Each leaf is a `RadioStation` via
`to_radio_station`, so Favorites (save to a folder), Record, and Schedule all
work with no new UI. The legacy `noaa_weather_stations` fuzzy path is removed
(no consumer left) rather than left dead.

## 3. Search — authoritative NOAA results

The unified station search gains a NOAA path backed by wxindex
`search_stations`: a query that looks like a **SAME code** (6 digits), a
**callsign** (e.g. `KHB36`), or a **"County, ST"** / state name routes to
wxindex and returns exact stations, blended into the existing results list. Free
text still falls through to the current sources. No separate dialog — it enriches
the search already there.

## 4. Weather menu + "Your Local NOAA Weather Radio"

The Weather feature already geocodes a saved location to latitude/longitude
**and** a county (`quill/core/weather/geocoding.py`). We reuse that:

- `local_stations(lat, lon, county=...)` maps the location to covering
  transmitter(s): prefer a county/SAME match from the directory; fall back to
  nearest-by-coordinates among stations whose coverage includes the point.
- A **"Listen to your local NOAA Weather Radio"** item is added to the Weather
  menu and surfaced at the top of Browse. One keypress plays it; it can be
  pinned to Favorites. If no Weather location is set, the item prompts to pick a
  state/county (or set a Weather location) rather than failing silently.

This is the tie that makes it feel "local" without any new location system.

## 5. Full experience

- **Station detail**: an accessible read-out (callsign, frequency, WFO office,
  covered counties, feed source) reachable from Browse/Search context.
- **Record / Schedule**: reuse the existing recording + scheduler on the adapted
  `RadioStation` — no new recording code.
- **Favorites**: existing folders; a one-action "pin my local NWR".

## Data flow

`UI (Browse/Search/Weather menu)` -> `wxindex.py resolver` -> `live | cache |
snapshot` -> `WxStation` -> `to_radio_station` -> existing player / recorder /
favorites. The UI never sees raw HTTP or JSON.

## Error handling, Safe Mode, egress

- All network calls: HTTPS-only, short timeout, retry/backoff, blocked in Safe
  Mode, and registered with the network-egress audit — identical to iheart /
  tunein / radio_browser.
- Any live failure degrades to cache, then snapshot; a fully offline app still
  browses/searches the bundled directory. A dead **feed** URL (stream provider
  down) surfaces the same "couldn't play that stream" path the other sources use;
  the directory entry remains.
- Snapshot is validated on load; a corrupt/missing snapshot logs and yields an
  empty directory rather than raising.

## Testing

- Pure client: parse fixtures for states/stations/search/detail into `WxStation`;
  `to_radio_station` mapping; SAME/callsign/county query routing in §3.
- Resolver: live-ok, live-fail->cache, cache-miss->snapshot, Safe-Mode-blocked —
  with a fake fetcher (no real network in unit tests).
- Manual refresh: writes the full directory atomically to the cache tier, stamps
  "last updated", takes precedence over the snapshot on the next read, and leaves
  cache/snapshot intact on a failed/cancelled pull.
- `local_stations`: county/SAME match and nearest-by-coordinate fallback on
  fixture data.
- Snapshot script: runs against a small fixture server / recorded fixtures and
  produces a valid `noaa_directory.json`.
- A characterization test that the Browse "Weather / NOAA" branch yields stations
  from the resolver (snapshot-backed, offline).

## Out of scope (YAGNI for 2.1.1)

- Live weather *data* (forecasts/alerts/radar) — wxindex is a station directory,
  not a weather-data API; the Weather feature stays the data source.
- Decoding SAME/EAS alert tones from the audio.
- Editing/curating the directory in-app.

## Open questions (defaults chosen, change if desired)

- **Browse grouping**: default **State -> County -> Station**; WFO grouping
  offered as a secondary view later if wanted.
- **Snapshot refresh cadence**: default background refresh interval 7 days;
  user-triggerable via the existing per-source "Reload from internet".
