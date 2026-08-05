# QUILL 1.0.0 Sign-off — Quill Weather (public app)

Weather binds menu handlers directly (no palette/registry ids). **11 menu actions** + standalone-app chrome + **4 dialog surfaces.** Run across every §A environment. Legend: W/S/A.

## Weather menu (shown in editor, Radio, and standalone)
- [ ] W  [ ] S  [ ] A  Weather > Weather Now...  `Ctrl+Shift+W`
- [ ] W  [ ] S  [ ] A  Weather > Quick Weather  `Ctrl+Shift+Q`
- [ ] W  [ ] S  [ ] A  Weather > Active Alerts...
- [ ] W  [ ] S  [ ] A  Weather > Add Location...
- [ ] W  [ ] S  [ ] A  Weather > Settings...
- [ ] W  [ ] S  [ ] A  Weather > Test Alert
- [ ] W  [ ] S  [ ] A  Weather > Listen to Local NOAA Weather Radio [area: noaa_radio]
- [ ] W  [ ] S  [ ] A  Weather > Update NOAA Weather Radio Directory [area: noaa_radio]
- [ ] W  [ ] S  [ ] A  Weather > Start/Stop Weather Monitoring  `Ctrl+Shift+M [area: monitoring]`
- [ ] W  [ ] S  [ ] A  Weather > Pause/Resume Alert Checks [area: monitoring]
- [ ] W  [ ] S  [ ] A  Weather > Open the Quill Weather App (host apps only)

## Standalone Quill Weather app chrome
- [ ] W  [ ] S  [ ] A  File > Minimize to Tray (Ctrl+W)
- [ ] W  [ ] S  [ ] A  File > Exit
- [ ] W  [ ] S  [ ] A  Options > Start Quill Weather with Windows
- [ ] W  [ ] S  [ ] A  Options > Start minimized to tray
- [ ] W  [ ] S  [ ] A  Options > Close keeps monitoring in tray
- [ ] W  [ ] S  [ ] A  Options > Check for alerts in background
- [ ] W  [ ] S  [ ] A  Options > Customize Features...
- [ ] W  [ ] S  [ ] A  Help > Check for Updates
- [ ] W  [ ] S  [ ] A  Help > About Quill Weather
- [ ] W  [ ] S  [ ] A  Tray > Open Weather Center / Quick Weather / Start-Stop Monitoring

## Dialog surfaces
- [ ] W  [ ] S  [ ] A  `quill/ui/weather/add_location_dialog.py::AddLocationDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/weather/settings_dialog.py::WeatherSettingsDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/weather/settings_dialog.py::WeatherSettingsDialog._choose_alert_sound::wx.FileDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/weather/weather_center_dialog.py::WeatherCenterDialog.__init__::wx.Dialog`  _(hardened_custom)_

## Scenario checks
- [ ] W  [ ] S  [ ] A  **Background Scheduled-Task alert check runs with no Quill process open** (Windows toast → SR announces).
- [ ] W  [ ] S  [ ] A  Severe-weather poll tightening (down to NWS 30s floor) then relaxes.
- [ ] W  [ ] S  [ ] A  Alert sounder: on/off, custom .wav, repeat count, Play preview.
- [ ] W  [ ] S  [ ] A  Test Alert previews full experience with no network / no state change.
- [ ] W  [ ] S  [ ] A  'Already-told-you' dedupe shared across the live watch and the background check.
- [ ] W  [ ] S  [ ] A  Tray hotkey (Ctrl+Alt+Shift+W); start-with-Windows minimized.
