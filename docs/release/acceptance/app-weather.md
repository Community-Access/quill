# App — Quill Weather (public standalone app, version 2.2.0)

Quill Weather is a small, screen-reader-first Windows app whose whole job is to
**watch official National Weather Service alerts for the places you care about and
speak new warnings the moment they are issued** — even when its window is closed,
even when nothing of Quill's is running at all. It ships alongside QUILL 1.0.0 and
Quill Radio; the three share the same weather code, so what you verify here is the
same feature a Radio or editor user meets under their **Weather** menu.

This section is written for a tester **who has never opened Quill Weather**. You do
not need to know its menus or shortcuts in advance — every scenario spells out the
keys, the menu path, and exactly what you should hear.

Authoritative surfaces this section is written against:
`../../planning/signoff/SIGNOFF-weather.md` (the Weather menu, the standalone-app
chrome, the four dialog surfaces, and the scenario checks) and the **WEATHER
(public)** block of `../../planning/signoff/SIGNOFF-dialogs.md`. Read §2–§3 of
`README.md` for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

**Two things about this app before you begin.**

- **Live weather needs the network.** Every scenario that fetches conditions,
  forecasts, or real alerts talks to the National Weather Service (and, for the
  extended outlook, Open-Meteo) over the internet. On a machine with **no network**,
  those fetches fail with a spoken, non-silent error — mark such scenarios
  **Blocked** and say "offline", not **Fail**. The scenarios that do **not** need
  the network (Test Alert, the settings and options surfaces, the tray, Safe Mode)
  are called out so you can still run them offline.
- **The background alert check is not a running program.** When you turn on "Check
  for alerts in the background," Quill Weather registers a **Windows Scheduled
  Task** named `QuillWeatherAlertCheck`. That task — not any open window — wakes a
  tiny `quill-weather --check-once` process on a cadence, toasts any new alert, and
  exits. WEATHER-19 walks a newcomer through proving the task exists and fires with
  **no Quill Weather window open at all**.

---

## WEATHER-01 — Launch Quill Weather (`quill-weather`, QuillWeather.exe)

*What & why.* Get the app open the way a real user would — from the Start menu or
its executable. Everything below assumes you have finished this once.

**Before you start**
- QUILL 1.0.0 installed (system installer or portable), which places **Quill
  Weather** alongside it. If you are running from a source checkout instead, the
  console command is `python -m quill.apps.weather` / the `quill-weather` script.
- Your screen reader running and speaking (see Part 0, GS-01).

**Do this**
1. Open the **Start menu** (**Windows key**), type **`Quill Weather`**, and press
   **Enter** on the match. (Portable build: run **`QuillWeather.exe`** from the
   unzipped folder.)
2. Wait for the window to appear and for your screen reader to settle.

**You should see and hear**
- A window titled **Quill Weather** opens. Focus lands on the **Open Weather
  Center…** button (announced as a button). If this is a first-ever run with no
  saved location, you will also hear, a moment later, **"Add a weather location to
  begin monitoring."**
- If a copy of Quill Weather is already running (including one sitting in the
  system tray), a second launch does **not** open a second window — the existing
  one comes to the front instead.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-02 — The Quill Weather window: chrome, focus, and status

*What & why.* Orient yourself. Confirm the menu bar, the three main buttons, and
the spoken monitoring-status line are all present and reachable by keyboard.

**Before you start**
- Quill Weather open (WEATHER-01). No network needed for this scenario.

**Do this**
1. Press **Alt** to enter the menu bar, then **Left/Right Arrow** across every top
   menu, reading each name.
2. Press **Escape** to leave the menu bar, then **Tab** through the window's
   controls and read each one.

**You should see and hear**
- The menu bar reads, in order: **File**, **Weather**, **Options**, (an **Audio
  Description Project** menu may appear — it is a shared pre-release menu, fine to
  skip), **QuillVille**, **Help**. The standalone app does **not** offer an "Open
  the Quill Weather App" item in its own Weather menu (that item is only for host
  apps like the editor and Radio).
- Tabbing the body reaches three buttons: **Open Weather Center…**, **Start/Stop
  Monitoring** (its label reads **Start Monitoring** or **Stop Monitoring** to match
  the current state), and **Add Location…**. There is also a status line that reads
  in substance **"Quill Weather — monitoring is off"** (or "on for <place>") — the
  same text the status bar carries.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-03 — Add a location (`AddLocationDialog`)

*What & why.* Teach the app where you are. You search by ZIP, city, county, or
address and pick the exact match — so two towns named the same are never confused.

**Before you start**
- Quill Weather open. **Network required** (the search uses OpenStreetMap's free US
  geocoder); offline, mark **Blocked**.
- Input to type: a place you can verify, e.g. **`Springfield, IL`** (or a ZIP such
  as **`62701`**).

**Do this**
1. Press **Ctrl+Shift+W** to open Weather Center, then its **Add Location…**
   button; or from the main window press the **Add Location…** button; or **Weather
   menu (Alt, W) ▸ Add Location…**.
2. Focus is in the **Search** field — type **`Springfield, IL`** and press
   **Enter** (or Tab to **Search** and press it).
3. When results arrive, **Arrow** down the **Results** list to the right match.
4. Optionally **Tab** to **Friendly name (optional)** and type **`Home`**.
5. Press the default button **Add Selected** (or double-click a result).

**You should see and hear**
- The dialog is titled **Add Weather Location**. The search field is announced as
  "Search: ZIP, city, county, or address"; **Add Selected** starts **disabled** and
  enables once results exist.
- On search you hear **"Searching for Springfield, IL."**, then, in substance, **"N
  results. Arrow to a place and press Add Selected."** and focus moves into the
  results list. Each entry is a full place name so same-named towns are
  distinguishable.
- On Add you hear **"Added Home."** (or the place's name if you left the friendly
  name blank) and the dialog closes. A bare **`lat,lon`** typed into search resolves
  to that exact point with no lookup. **Escape** cancels with no location added and
  returns focus to the button you opened it from.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-04 — Weather Center: open and read current conditions (`WeatherCenterDialog`, Ctrl+Shift+W)

*What & why.* The Weather Center is the text-only weather workspace: alerts, then
current conditions, then forecasts, laid out as plain screen-reader controls in
reading order. This scenario opens it and reads today's conditions.

**Before you start**
- At least one location saved (WEATHER-03). **Network required**; offline, **Blocked**.

**Do this**
1. Press **Ctrl+Shift+W**, or the main window's **Open Weather Center…** button, or
   **Weather menu ▸ Weather Now…**.
2. Let it load. **Tab** to the **Current conditions** field and read it with your
   screen reader's review keys.

**You should see and hear**
- A **Weather Center** window opens. In the standalone app it is a real window with
  its own menu bar (a **Weather** menu with **Close  Ctrl+W**, plus the shared
  **Window** menu), not a modal box.
- Because refresh-on-open is on by default, you hear **"Loading weather for
  <place>."** then a one-sentence summary in substance — **"Weather for <place>.
  There are no active alerts. <temperature and sky>."** (or the active-alert count
  if any).
- Tab order runs: **Location** chooser, **Refresh**, **Add Location…**, **Remove
  Location**, **Settings…**, then **Active Alerts** list, then **Current
  conditions** (read-only, announced "Current conditions"), then the **Forecast**,
  **Hourly forecast**, and **Daily outlook** lists, then a **status** line, then
  **Close**. The current-conditions box carries temperature and sky at minimum, plus
  whatever details you have enabled in Settings.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-05 — Weather Center: the period forecast

*What & why.* The multi-day forecast is a list you arrow through, with each
period's full detailed text in a read-only box below it.

**Before you start**
- Weather Center open with a report loaded (WEATHER-04). Network required.

**Do this**
1. **Tab** to the **Forecast** list.
2. **Arrow** down through the periods (Today, Tonight, Tomorrow…).
3. **Tab** once to the **Selected period (read-only)** box and read it.

**You should see and hear**
- Each list line reads in substance **"<period name>: <temperature> degrees
  <scale>, <short forecast>"** — e.g. "Tonight: 54 degrees Fahrenheit, Partly
  Cloudy." As you arrow, the **Selected period** box updates to that period's full
  detailed forecast, with abbreviations like "mph" spoken in full ("miles per
  hour"). The number of periods shown follows your Settings choice.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-06 — Weather Center: the hourly forecast

*What & why.* An hour-by-hour list for the near term, each hour a single spoken
line with its full detail below.

**Before you start**
- Weather Center open with a report loaded. Network required. In **Settings**, the
  **Hourly forecast (hours)** value must be **greater than 0** (the default is on).

**Do this**
1. **Tab** to the **Hourly forecast** list (announced "Hourly forecast, one line per
   hour").
2. **Arrow** through several hours, then **Tab** to **Selected hour (read-only)** and
   read it.

**You should see and hear**
- One line per upcoming hour (time, temperature, sky, chance of precipitation as
  provided). The **Selected hour** detail box tracks the highlighted hour. If you
  set **Hourly forecast** to **0** in Settings, the hourly list and its detail box
  disappear from the window entirely (they are not just empty) — a screen-reader
  user never lands on a blank field.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-07 — Weather Center: the extended daily outlook

*What & why.* A longer-range day-by-day outlook (from Open-Meteo) that reaches past
the National Weather Service's seven days.

**Before you start**
- Weather Center open with a report loaded. Network required. In **Settings**, the
  **Extended daily outlook (days)** value must be **greater than 0**.

**Do this**
1. **Tab** to the **Daily outlook (extended)** list.
2. **Arrow** through the days, then **Tab** to **Selected day (read-only)** and read
   it.

**You should see and hear**
- One line per day, each with its high/low and conditions; the **Selected day** box
  gives the fuller detail. Setting **days** to **0** removes this list and its
  detail box from the window (as with the hourly list).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-08 — Moon phase and current-conditions detail toggles

*What & why.* Beyond temperature and sky, you choose which extras — feels-like,
humidity, wind, sunrise/sunset, **moon phase**, UV, air quality, local time — ride
along in the current-conditions block. This proves the toggles reach the reading.

**Before you start**
- Weather Center open with a report loaded, or reopen it after changing Settings.
  Network required for the live values.

**Do this**
1. From Weather Center, press the **Settings…** button (or **Weather menu ▸
   Settings…**).
2. In the current-conditions detail list, confirm **Moon phase, moonrise and
   moonset** is checked (it is on by default); leave it checked. **Save**.
3. Back in Weather Center, read the **Current conditions** field again.

**You should see and hear**
- The current-conditions text now includes a **moon** line in substance — the phase
  name (e.g. "Waxing Gibbous") and moonrise/moonset times. Unchecking a detail in
  Settings and re-reading removes exactly that detail; temperature and sky always
  remain. (Note: the exact moon wording comes from the renderer; verify the phase
  and times are present and sensible rather than matching a fixed string.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-09 — Active Alerts (`Weather ▸ Active Alerts…`)

*What & why.* Jump straight to the alerts list with the full official text of the
selected alert beneath it. This is the safety-critical surface.

**Before you start**
- A location saved. Network required. If your area currently has **no** alerts you
  can still verify the "none" wording; to exercise a real alert, pick a location
  that is under an active watch/warning (the National Weather Service alerts map can
  tell you where).

**Do this**
1. **Weather menu ▸ Active Alerts…** (this opens Weather Center with focus on the
   alerts list). Or open Weather Center and **Tab** to **Active Alerts**.
2. **Arrow** through any alerts; **Tab** to **Selected alert (read-only)** and read
   the full text.

**You should see and hear**
- The alerts label reads **"Active Alerts (N):"** with the count, or **"Active
  Alerts (none):"**. With no alerts the list shows a single **"No active alerts."**
  line and the selected-alert detail box is hidden (no empty box to land on).
- With an alert present, each list line reads event, area, and tier; the detail box
  gives headline; severity/urgency/certainty; area; in-effect window; official
  **Instructions**; and the issuing office. Alerts hidden by your Settings severity
  floor or mute list do not appear.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-10 — Switch and remove locations

*What & why.* Keep several places and move between them; drop one you no longer
want. Removal is by button or the Delete key.

**Before you start**
- **Two** locations saved (run WEATHER-03 twice). Network required for the reload.

**Do this**
1. In Weather Center, **Tab** to the **Location** chooser and **Arrow** to the other
   place.
2. Read the refreshed conditions.
3. With the chooser focused, press **Delete** (or **Tab** to **Remove Location** and
   press it) to remove the shown place.

**You should see and hear**
- Choosing a place makes it the primary and reloads its weather — you hear
  **"Loading weather for <place>."** and then its summary.
- Remove announces **"Removed <place>."** and reloads the remaining one. Remove the
  last location and you hear, in substance, **"Removed <place>. No locations left.
  Choose Add Location to begin."** and every reading field clears.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-11 — Quick Weather (`Weather ▸ Quick Weather`, Ctrl+Shift+Q)

*What & why.* A one-line spoken summary of the primary location with **no window at
all** — the fastest "what's it doing outside" answer.

**Before you start**
- A location saved. Network required; offline, **Blocked**.

**Do this**
1. Press **Ctrl+Shift+Q**, or **Weather menu ▸ Quick Weather**.

**You should see and hear**
- You hear **"Getting weather for <place>."** then, a moment later, a single spoken
  line — temperature and sky, plus whatever Quick Weather extras (feels-like, wind,
  humidity, alert count, data age) you enabled in Settings. No window opens.
- With **no** location saved yet, Quick Weather says **"No weather location yet.
  Opening Add Location."** and opens the Add Location dialog instead of failing
  silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-12 — Weather Settings (`WeatherSettingsDialog`, Weather ▸ Settings…)

*What & why.* Every weather preference in one keyboard-complete dialog: units,
forecast lengths, which details show, alert filtering, refresh cadence, and the
alert sounder (covered on its own in WEATHER-13/14). No network needed.

**Before you start**
- Quill Weather open. This scenario changes and saves settings; note the originals
  so you can restore them.

**Do this**
1. **Weather menu ▸ Settings…**, or the Weather Center **Settings…** button.
2. **Tab** through every control, reading each label: **Temperature unit**, **Wind
   unit**, **Forecast periods to show**, **Extended daily outlook (days)**, **Hourly
   forecast (hours)**, **Alert severity to show**, **Refresh every (minutes)**, the
   checkbox rows (detailed forecast text, announce summary on open, refresh on
   open), the current-conditions detail checks, the Quick Weather include checks,
   and the **Hide these alert events** box.
3. Change **Temperature unit** to **Celsius**, then press the default button
   **Save**.
4. Reopen Settings and confirm the change stuck; restore it.

**You should see and hear**
- The dialog is titled **Weather Settings**. Every control is announced with a
  meaningful name and is reachable and operable by keyboard (choices with arrows,
  spin controls with up/down, checkboxes with Space).
- **Save** announces **"Weather settings saved."** and closes; the change is
  visible on reopen and in the next reading (Celsius temperatures, changed alert
  filtering, etc.). **Escape** / **Cancel** discards changes and closes with no
  save.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-13 — Alert sounder options (enable, repeat count, Play preview, Use Default)

*What & why.* When a new alert arrives, Quill Weather can play a sound as well as
speak it. This proves the on/off toggle, the repeat count, the live **Play**
preview, and **Use Default**. No network needed.

**Before you start**
- Weather Settings open (WEATHER-12). Speakers/headphones on.

**Do this**
1. In Settings, **Tab** to **Play a sound when a new alert is announced** and make
   sure it is **checked** (Space toggles it).
2. **Tab** to **Play the alert sound this many times** and set it to **2**.
3. **Tab** to the **Play** button and press it to preview.
4. **Tab** to **Use Default** and press it.
5. **Save**.

**You should see and hear**
- The sound row exposes a read-only **Alert sound** path field (announced "Chosen
  alert sound file", showing **(default chime)** when no custom file is set), plus
  **Choose…**, **Play**, and **Use Default** buttons and a **repeat** spin control
  (1–10).
- **Play** plays the current sound the chosen number of times back-to-back and says
  **"Playing the alert sound."** **Use Default** resets the path to **(default
  chime)** and says **"Using the default alert sound."** With the sound **unchecked**,
  no sound plays on a real or test alert (the alert is still spoken and shown).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-14 — Choose a custom alert sound (native file dialog)

*What & why.* Point the sounder at your own `.wav`. This exercises the one **native**
dialog in the app — the Windows file picker.

**Before you start**
- Weather Settings open. A `.wav` file on disk you can select.

**Do this**
1. In the alert-sound row, press **Choose…**.
2. In the file dialog, navigate to your `.wav` and press **Enter** (Open).
3. Press **Play** to preview it, then **Save**.

**You should see and hear**
- A standard Windows **Choose an alert sound** file dialog opens, filtered to
  **Sound files (\*.wav)**, fully keyboard-navigable and screen-read. On Open you
  hear **"Alert sound chosen."** and the path field shows your file. **Play** now
  previews your file; **Save** persists it. Cancelling the file dialog leaves the
  prior choice untouched.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-15 — Test Alert (`Weather ▸ Test Alert`)

*What & why.* Preview the **entire** alert experience — sound, forced speech, a
tray toast, and a dialog — clearly marked as a test, so you know exactly what a
real warning will do. It touches **no network** and changes **no** monitoring
state, so it is fully runnable offline.

**Before you start**
- Quill Weather open. Alert sound enabled (WEATHER-13) if you want to hear the cue.
  **No network needed.**

**Do this**
1. **Weather menu ▸ Test Alert (preview sound, tray, and dialog)**.
2. Let the toast appear; read the dialog; press **OK** (or **Enter**).

**You should see and hear**
- In quick succession: the alert **sound** (if enabled), a **spoken** line that
  interrupts other speech — **"Test weather alert. This is a TEST of Quill Weather
  alerts. No action is needed."** — a system-tray **toast** titled **"[TEST]
  Weather alert"**, and a dialog titled **Test Weather Alert** whose body is clearly
  labelled a TEST (sample severity/urgency/certainty, a note that real instructions
  would appear here) with an **OK** button.
- Afterward, nothing about your real monitoring has changed — no location was
  fetched, no alert was recorded as "seen", monitoring is neither started nor
  stopped.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-16 — Start / Stop Weather Monitoring (`Ctrl+Shift+M`)

*What & why.* The live watch: while it runs, Quill Weather polls your places on a
timer and speaks newly issued alerts. Starting it persists the on-state so the next
launch resumes it.

**Before you start**
- At least one location saved. **Network required** for the real polls; offline you
  can still confirm the toggle speaks but mark **Blocked** for the alert content.

**Do this**
1. Press **Ctrl+Shift+M**, or **Weather menu ▸ Start Weather Monitoring**, or the
   main window's **Start Monitoring** button.
2. Listen to the start-up speech.
3. Press **Ctrl+Shift+M** again (now **Stop Weather Monitoring**) to turn it off.

**You should see and hear**
- On start you hear immediate feedback — **"Turning on weather monitoring for
  <place>."** — then, once the first (baseline) poll returns, a one-time summary in
  substance: **"Weather monitoring on for <place>. N active alerts right now… .
  Checking every 10 minutes, or every 60 seconds while an alert is active."** The
  menu item and the main-window button relabel to **Stop…**. The status line
  updates to "monitoring on".
- On stop you hear **"Weather monitoring off for <place>."** and the labels revert.
  With **no** location saved, Start says **"No weather location to monitor yet.
  Opening Add Location."** rather than doing nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-17 — Pause / Resume Alert Checks (`Weather ▸ Pause/Resume Alert Checks`)

*What & why.* A temporary snooze that halts the polling without turning monitoring
off — different from Stop. A paused watch stays "on" and resumes cleanly.

**Before you start**
- Monitoring **on** (WEATHER-16). Network required for the resume poll.

**Do this**
1. **Weather menu ▸ Pause Alert Checks**.
2. Then **Weather menu ▸ Resume Alert Checks** (the same item, relabelled).

**You should see and hear**
- Pause says **"Weather alert checks paused. Choose Resume Alert Checks to
  continue."** and the polling stops. The Pause/Resume item is only enabled while
  monitoring is running.
- Resume says **"Resuming weather alert checks."** and an immediate poll re-arms the
  timer. Choosing Pause/Resume while monitoring is **off** tells you monitoring is
  not on and to Start it first.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-18 — Severe-weather poll tightening

*What & why.* While an alert is active, the watch tightens its cadence toward
near-real-time (down to the National Weather Service's 30-second courtesy floor),
then relaxes back to the normal interval once the alert clears. This approaches
push latency without a paid feed.

**Before you start**
- Monitoring **on** for a location that is currently **under an active alert**
  (choose one from the NWS alerts map). **Network required.** This is inherently a
  timing observation — plan to sit with it a few minutes. If nowhere is alerting
  while you test, mark **Blocked** and note "no live alert available".

**Do this**
1. Start monitoring for the alerting location and note the start summary's cadence
   phrase.
2. Observe the polling rhythm while the alert is active, then (if the alert clears
   during your window, or by switching to a clear location) observe it relax.

**You should see and hear**
- The start summary states both cadences in substance: **"Checking every N minutes,
  or every 60 seconds while an alert is active."** While an alert is active the
  watch polls on the tighter interval (default 60 seconds, never below 30); when no
  alert is active it uses the normal interval (default 10 minutes, never below 5).
  *(Note: cadence is internal timing — verify by observing that fresh polls occur
  markedly more often while an alert is active than when clear, not by a spoken
  string.)*

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-19 — Background alert check with no Quill process running (Windows Scheduled Task)

*What & why.* The headline promise: alerts reach you even when nothing of Quill's
is open. Turning this on registers a **Windows Scheduled Task** that wakes a tiny
one-shot checker on a cadence and toasts new alerts. This scenario proves the task
exists and fires with **every Quill window closed**.

**Before you start**
- A location saved. **Network required.** You will use **Task Scheduler** (or the
  `schtasks` command) to verify — no developer tools needed, both ship with Windows.

**Do this**
1. In Quill Weather, **Options menu (Alt, O) ▸ Check for alerts in the background
   (even when Quill Weather is closed)** — check it (Space).
2. Verify the task now exists: open **Task Scheduler** (Start menu ▸ type "Task
   Scheduler") and find **`QuillWeatherAlertCheck`** in the task library; or open a
   terminal and run **`schtasks /Query /TN QuillWeatherAlertCheck`** and confirm it
   is listed.
3. **Fully exit** Quill Weather (**File ▸ Exit**, and confirm no tray icon remains —
   see WEATHER-26). No Quill window or tray icon should be running.
4. With everything closed, either wait for the task's next scheduled run or, in Task
   Scheduler, select the task and choose **Run** to fire it now.
5. Watch for a Windows toast.

**You should see and hear**
- Checking the option announces **"Quill Weather will check for alerts in the
  background, even when closed."** and the task appears in Task Scheduler /
  `schtasks` output, scheduled on a MINUTE cadence.
- With **no Quill process open**, a scheduled (or manually-run) check that finds a
  **newly issued** alert raises a Windows **toast** that your screen reader
  announces (and plays the alert sound if enabled). The **very first** background
  check after enabling only records a baseline — it does not toast alerts already in
  effect. Unchecking the option says **"Background alert checks are off."** and the
  task disappears. *(Note: on a machine where corporate policy blocks `schtasks`,
  enabling it says background checks need Windows / cannot be created rather than
  crashing — record that as the outcome.)*

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-20 — "Already told you" dedupe across the live watch and the background check

*What & why.* The live in-app watch and the background Scheduled Task share one
record of which alerts you have already been told about, so the same warning is
never announced twice — once by the running app and again by the background task.

**Before you start**
- A location that is (or recently was) under an active alert. **Network required.**
  Both the live watch (WEATHER-16) and the background check (WEATHER-19) available.

**Do this**
1. With monitoring **on** in the running app, let it announce a real alert (or Test
   is not sufficient here — a real alert id is needed; if none is available mark
   **Blocked**).
2. Leave background checks **on**, then either run the Scheduled Task manually or
   wait for its next tick — with the app still running, and again after exiting the
   app.

**You should see and hear**
- The alert is announced **once**. A subsequent background check for the same,
  still-active alert does **not** re-toast it, because the running watch has already
  recorded that alert id to the shared on-disk "notified" record and the background
  checker reads the same record. A genuinely **new** alert (a different id) is still
  announced. *(Note: this is a "no duplicate" observation — the pass condition is
  the absence of a repeat toast for an alert already spoken.)*

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-21 — Options: start with Windows, start in tray, close keeps monitoring

*What & why.* Make Quill Weather watch from login and behave the way you want when
you close its window. No network needed for the toggles themselves.

**Before you start**
- Quill Weather open. Note the current state of each option so you can restore it.

**Do this**
1. **Options menu ▸ Start Quill Weather with Windows** — toggle it (Space).
2. **Options ▸ Start minimized to the tray** — toggle it.
3. **Options ▸ Close button keeps monitoring in the tray** — toggle it.
4. To verify start-with-Windows end-to-end: with it **on** and "start minimized" on,
   sign out and back in (or reboot) and confirm Quill Weather is watching from the
   tray with no window shown.

**You should see and hear**
- Each toggle is a checkable menu item that announces its new state in plain words —
  e.g. **"Quill Weather will start with Windows."** / **"…will not start with
  Windows."**, **"Quill Weather will start minimized to the tray."**, **"Closing the
  window will keep monitoring in the tray."** / **"…will exit Quill Weather."**
- After login (step 4) with both options on, Quill Weather is running in the tray,
  no window is shown, and monitoring is active. *(Note: if a locked-down registry
  refuses the startup entry, the menu reflects what actually took — verify the item
  matches reality rather than assuming it saved.)*

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-22 — Minimize to Tray, the tray menu, and the tray hotkey

*What & why.* Quill Weather lives in the system tray while it watches. Prove you can
send it there, drive it from the tray, and summon it with a global hotkey.

**Before you start**
- Quill Weather open, with **Close button keeps monitoring in the tray** on
  (WEATHER-21) if you want the window's Close/**Ctrl+W** to minimize rather than
  exit. No network needed.

**Do this**
1. **File menu ▸ Minimize to Tray** (or **Ctrl+W**). The window hides.
2. Find the Quill Weather **tray icon** (Windows: the notification area; press
   **Windows+B** to reach it by keyboard, then Arrow to it and press the **Menu/
   Applications key** or **Enter**) and open its menu.
3. Arrow through the tray menu items; choose **Open Weather Center**.
4. Press the global hotkey **Ctrl+Alt+Shift+W** to show/hide the window.

**You should see and hear**
- Minimizing says **"Quill Weather is monitoring in the system tray."** The tray icon
  tooltip reads **Quill Weather**.
- The tray menu offers a disabled status line **"Monitoring: on/off"**, then **Open
  Weather Center**, **Quick Weather**, **Start/Stop Monitoring**, and entries to
  reach the sibling QuillVille apps. Open Weather Center restores the app and opens
  the Center.
- **Ctrl+Alt+Shift+W** brings the window forward (and hides it again), from anywhere.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-23 — Customize Features (`Options ▸ Customize Features…`)

*What & why.* Turn Quill Weather's optional areas — **Alert Monitoring** and **NOAA
Weather Radio** — on or off. Switching an area off drops its Weather-menu items at
the next launch. No network needed.

**Before you start**
- Quill Weather open.

**Do this**
1. **Options menu ▸ Customize Features…**.
2. In the dialog, read the two areas and their descriptions; **uncheck** **NOAA
   Weather Radio**; confirm/Save.
3. Close and relaunch Quill Weather; open the **Weather** menu.

**You should see and hear**
- The dialog lists **Alert Monitoring** and **NOAA Weather Radio**, each with a
  plain-language description, all keyboard-operable. On save you hear, in substance,
  **"Feature settings saved. Menu changes take effect the next time you open Quill
  Weather."**
- After relaunch with NOAA Weather Radio off, the **Listen to your Local NOAA
  Weather Radio** and **Update NOAA Weather Radio Directory** items are gone from the
  Weather menu; re-enabling restores them. Turning off **Alert Monitoring** likewise
  removes the Start/Stop and Pause/Resume items.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-24 — NOAA Weather Radio: find and update the directory

*What & why.* Resolve the NOAA Weather Radio transmitter nearest your location, and
refresh the bundled station directory. The standalone Weather app can **find** the
station but cannot play it (playback needs Quill Radio) — it says so honestly.

**Before you start**
- NOAA Weather Radio area enabled (WEATHER-23). A location saved. **Network
  required** for the directory update; offline, **Blocked**.

**Do this**
1. **Weather menu ▸ Listen to your Local NOAA Weather Radio**.
2. **Weather menu ▸ Update NOAA Weather Radio Directory**.

**You should see and hear**
- "Listen" says **"Finding your local NOAA Weather Radio station for <place>…"** then
  names the nearest station. Because this app has no radio engine, it explains in
  substance that your nearest station is **<name>** and that **playing it needs
  Quill Radio** — it does not silently do nothing. (No location saved → it opens Add
  Location.)
- "Update" says **"Updating the NOAA Weather Radio directory…"** then reports the
  refreshed counts (**"…N stations, M states, as of <date>."**), or a clear error if
  the pull failed — never a silent stale fallback.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-25 — Help: Check for Updates and About Quill Weather

*What & why.* Confirm the app can check for its own updates and reports its
identity and version.

**Before you start**
- Quill Weather open. **Check for Updates needs the network**; About does not.

**Do this**
1. **Help menu (Alt, H) ▸ About Quill Weather**; read the dialog; close it.
2. **Help menu ▸ Check for Updates…**.

**You should see and hear**
- **About** shows a dialog naming **Quill Weather 2.2.0**, describing it as the
  accessible weather watcher that keeps an eye on official NWS alerts even while in
  the tray, with an **OK** button; Escape/OK closes it.
- **Check for Updates** contacts the shared Quill release repo and reports either
  that you are up to date or that an update is available (offline, it reports the
  failure clearly — **Blocked**, not **Fail**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-26 — Exit (`File ▸ Exit`)

*What & why.* A true quit — distinct from Minimize to Tray. Exit always ends the
process (and removes the tray icon), while closing the window may only minimize
depending on your Options.

**Before you start**
- Quill Weather open (windowed or in the tray). No network needed.

**Do this**
1. **File menu ▸ Exit** (from the window), or the tray menu's exit path.
2. Confirm the app is truly gone: no window, **no tray icon**, and (in Task Manager)
   no `quill-weather`/QuillWeather process.

**You should see and hear**
- The app closes fully: the window and the tray icon both disappear and the process
  ends. If monitoring was on, it is left in a state that resumes on the next launch
  (a clean exit does not persist monitoring off). The separate **background**
  Scheduled Task, if you enabled it, keeps running independently — that is expected
  (see WEATHER-19).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WEATHER-27 — Safe Mode: weather is a network service and is turned off

*What & why.* In Safe Mode, Quill Weather's network features are deliberately
disabled and say so — a diagnostic state, not a broken one. No live network activity
should occur.

**Before you start**
- Launch Quill Weather in Safe Mode: set **`QUILL_SAFE_MODE=1`** in the environment
  (or use the `--safe-mode` flag) before starting it.

**Do this**
1. Start Quill Weather in Safe Mode.
2. Try **Weather ▸ Weather Now…** (Ctrl+Shift+W), **Quick Weather**, and
   **Start Weather Monitoring** (Ctrl+Shift+M).

**You should see and hear**
- The network-backed items report, in substance, **"Weather is a network service and
  is turned off in Safe Mode. Restart without Safe Mode to use it."** Monitoring does
  not start; on launch you may hear **"Weather monitoring is off in Safe Mode."** No
  weather fetch occurs. Non-network surfaces (Settings, Options, Test Alert) still
  behave normally.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 27
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
