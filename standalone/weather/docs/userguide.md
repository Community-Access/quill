# Quill Weather User Guide

Quill Weather is a small, standalone, screen-reader-first weather app. This guide
covers what is specific to the standalone app; the weather features themselves
are the same ones documented in the Quill Radio User Guide's Weather section
(they share the code).

## Starting the app

Launch **Quill Weather** from the Start Menu, or run `QuillWeather.exe` from the
portable folder. On first run there is no saved location yet, so choose
**Weather menu > Add Location...** (or the **Add Location...** button) and search
by ZIP code, city, county, or address.

The main window is small on purpose -- a status line telling you whether
monitoring is on, and buttons for **Open Weather Center**, **Toggle
Monitoring**, and **Add Location**. Everything else is on the menu bar.

## The window, the tray, and starting at login

Quill Weather is built to keep running.

- **Minimize to Tray** (File menu, or Ctrl+W) tucks the window into the system
  tray; monitoring keeps going.
- **Ctrl+Alt+Shift+W** is a global show/hide hotkey: it works from any app, even
  when Quill Weather does not have focus. Press it once to hide the window to the
  tray (monitoring keeps running); press it again to bring the window back and
  focus it. Quill Weather speaks "hidden to the tray" or "shown" so you know
  which happened, and you never have to go looking for the tray icon. The chord
  is unique to Quill Weather (QUILL uses Ctrl+Alt+Shift+Q and Quill Radio uses
  Ctrl+Alt+Shift+R), so the three apps never collide. It is Windows-only; if
  another program has already claimed Ctrl+Alt+Shift+W, Quill Weather leaves it
  alone and you still show and hide the window from the tray icon.
- By default, **closing the window** also goes to the tray rather than quitting
  (so a stray Alt+F4 does not end your watch). Only **Exit** (File menu or the
  tray) truly quits. You can change this in **Options > Close button keeps
  monitoring in the tray**.
- **Options > Start Quill Weather with Windows** launches the app at sign-in.
  Pair it with **Options > Start minimized to the tray** and it comes up already
  watching, with no window.
- **Options > Check for alerts in the background (even when Quill Weather is
  closed)** registers a Windows scheduled task that checks for new alerts on
  your monitor interval and shows a toast if it finds one -- so you are covered
  even with no Quill Weather process running at all.

## The system tray menu

Right-click the tray icon (or use the Applications key) for: the current
monitoring status, **Open Weather Center**, **Quick Weather**, **Start/Stop
Monitoring**, **Open Quill Radio**, **Open QUILL**, **Show**, and **Exit**.
Left-double-click the icon to bring the window back.

## Weather Monitoring (Weather Guardian)

**Weather menu > Start Weather Monitoring** (Ctrl+Shift+M) watches your saved
location's official alerts and speaks each new one as it is issued, with a system
-tray notification and the alert sounder. **Pause Alert Checks** snoozes it
without turning it off. See **Settings** for the alert sounder controls (on/off,
your own sound file with a Play button, and how many times it repeats), and
**Weather menu > Test Alert** to preview the whole experience.

## Customizing features

**Options > Customize Features...** lists the app's switchable areas -- **Alert
Monitoring** and **NOAA Weather Radio** -- each with a short description.
Unchecking one removes its menu items the next time you open Quill Weather, so
you can trim the app to just what you use. (This is the same customization Quill
Radio offers.)

## Reaching the other apps

Quill Weather, Quill Radio, and QUILL are separate apps that can open each other.
**File > Open Quill Radio** and **File > Open QUILL** (also in the tray menu)
launch a sibling in its own window; if it is already running, it simply comes to
the front. On the same machine all three share one data store, so a location you
saved in one is there in the others.

## Updating

**Help > Check for Updates** knows whether you run the installer or the portable
build and downloads the matching one. Quill Weather updates on its own schedule,
separate from Quill Radio.

## Weather features -- full reference

This is the full reference for the weather features, shared by the standalone
**Quill Weather** app and Quill Radio's **Weather** menu (they run the same
code). It brings official U.S. weather to you as clear, screen-reader-first
text: current conditions, the forecast, an extended daily outlook, and -- most
importantly -- active watches, warnings, and advisories for the places you care
about.

Everything comes from free, no-account, no-key sources: the **National Weather
Service** (api.weather.gov) for observations, the forecast, and alerts;
**Open-Meteo** for the extended daily outlook and the air-quality index; and
**OpenStreetMap** for searching locations. Nothing is sent anywhere except your
request for weather at a place you choose.

### A safety note first

Quill Weather is an **additional** accessible weather tool. Delivery can be
delayed or interrupted by network, device, or provider problems. Do not rely on
it as your only source of emergency information. Keep a NOAA Weather Radio,
Wireless Emergency Alerts, and local emergency instructions as your primary
safety channels.

### Adding a location

1. Open the **Weather** menu and choose **Add Location...** (or open **Weather
   Now...** and press the **Add Location** button).
2. Type a **ZIP code**, a **city and state** (`Tucson, AZ`), a **county name**,
   or an **address**, then press **Search**. (You can also type exact
   **coordinates** like `32.2, -110.9`.)
3. A **Results** list appears. Because a search can match more than one place --
   there are Springfields in Illinois, Missouri, and more -- you **arrow to the
   right one and press Add Selected**. Optionally give it a friendly **name**
   like `Home` or `Mom's` first.
4. The first location you add becomes your primary location. Add as many as you
   like and switch between them with the **Location** chooser in Weather Now.

**Removing a location:** in Weather Now, select it in the Location chooser and
press **Remove Location** (or the **Delete** key).

### Weather Now

**Weather menu > Weather Now...** (or **Ctrl+Shift+W**) opens the Weather
Center. It reads top to bottom in priority order:

1. **Active Alerts** -- a list of any watches, warnings, and advisories, most
   severe first. Arrow through them; the full official text, including the
   **instructions**, appears in the read-only box just below (so you can read
   and copy it). When there are no alerts, that box is hidden, so you don't stop
   on an empty field.
2. **Current conditions** -- a complete, warm paragraph from the nearest
   station: temperature, feels-like, sky, humidity, dew point, wind and gusts,
   cloud cover, barometric pressure, visibility, chance of precipitation,
   sunrise, sunset, the ultraviolet index, and air quality. Every value is
   written out for speech, and the observation time is shown in the location's
   own time zone. You choose which of these details appear in Settings.
3. **Forecast** -- the National Weather Service period forecast ("This
   Afternoon", "Tonight", ...). Arrow the list; each period's full detailed
   text appears below, led by its day and temperature so it stands alone.
4. **Daily outlook (extended)** -- an at-a-glance list reaching about 10 days
   out (up to 16), each day a friendly line: "Monday, July 20: Clear. High 98,
   low 75 degrees. Sunrise 5:42 AM, sunset 7:38 PM." Arrow the list to read each
   day in the detail box below.
5. A **status line** naming the National Weather Service office and the
   observation station, so you always know where the data came from.

Press **Refresh** at any time to pull the latest. **Close** leaves any radio
you are playing untouched.

### Quick Weather

**Weather menu > Quick Weather** (or **Ctrl+Shift+Q**) speaks a one-line summary
of your primary location without opening a window -- for example:

> Here is the weather for Tucson, Arizona. It is 96 degrees Fahrenheit and mostly
> clear. It feels like 101 degrees. The wind is blowing from the west-northwest
> at 5 miles per hour. There is one active alert. The most urgent is an Excessive
> Heat Warning.

You choose what that line includes in Settings.

### Active Alerts

**Weather menu > Active Alerts...** opens Weather Now with focus already on the
alerts list, so you can review warnings with the fewest keystrokes.

### Settings

**Weather menu > Settings...** controls:

- **Units** -- temperature in Fahrenheit or Celsius; wind in miles per hour,
  kilometers per hour, knots, or meters per second.
- **Forecast periods to show** and **Extended daily outlook (days)** -- how much
  of the forecast and outlook Weather Now lists (0 days turns the outlook off).
- **Hourly forecast (hours)** -- how many hours of the hour-by-hour forecast the
  Weather Center lists (0 turns it off).
- **Current-conditions details to include** -- a checkbox for each of feels-like,
  humidity, dew point, wind and gusts, cloud cover, pressure, visibility, chance
  of precipitation, sunrise and sunset, **moon phase, moonrise and moonset**, the
  ultraviolet index, air quality, and the **current local time at the location**.
  Temperature and the sky condition always show.
- **Alert severity to show** -- everything, or only Moderate and above, Severe
  and above, and so on -- plus a list of specific **event names to hide** (one
  per line).
- **Alert sound** -- turn the sound on or off, **Choose** your own `.wav` (with a
  **Play** button to hear it and **Use Default** to go back), and set how many
  times it plays for each alert (1 to 10).
- **Refresh interval** -- how often Weather Now refreshes (never faster than the
  NWS-recommended minimum).
- **Quick Weather line** -- turn feels-like temperature, wind, humidity, the
  active-alert count, and data age on or off.

### The hourly forecast, the moon, and local time

Weather Now (and the Weather Center) show three more things:

- **Hourly forecast** -- an **Hourly forecast** list you arrow through, giving the
  temperature, sky, and chance of precipitation for each coming hour (from the NWS
  hourly product). Set its length, or turn it off, in Settings.
- **The moon** -- current conditions and every day of the outlook include the
  moon's phase, how full it is (percent illuminated), and that day's moonrise and
  moonset -- all computed on your own machine, no extra internet lookup.
- **Two clocks and a check time** -- the report leads with a plain-spoken time
  summary: the current local day and time in the place you searched, the current
  local time **where you are**, and **when the reading was taken** ("checked just
  now", or the exact minute in your own time for an older reading). For example:
  "Right now it is Thursday, April 27, 9:51 AM in Tucson, Arizona, and 6:51 AM
  where you are. This reading was checked just now." When you and the place you
  searched are in the same time zone, it says so once instead of repeating the
  clock. Turn the local-time line off in Settings if you prefer.

### Weather monitoring (Weather Guardian)

**Weather menu > Start Weather Monitoring** (or **Ctrl+Shift+M**) watches your
saved location's official watches, warnings, and advisories and **speaks each new
one the moment it is issued** -- with interrupting speech for the most serious
events (tornado, flash flood) -- and tells you when they all clear. It also drops
a notification in the system tray for each new alert, so you can see it there.

- It keeps working while Quill Radio is **minimized to the tray**, and it starts
  again automatically the next time you launch (choose **Stop Weather Monitoring**
  to turn it off for good).
- While a warning is active it checks much more often (as fast as once a minute)
  so you hear about changes quickly, then eases back when the weather clears.
- **Weather menu > Pause Alert Checks** snoozes it temporarily without turning it
  off; the same item then reads **Resume Alert Checks**.

### Test Alert

**Weather menu > Test Alert** shows you exactly what a real alert is like -- the
spoken words, the sound (using your sound settings), a system-tray notification,
and the alert window -- all clearly marked as a **test** and dismissable with OK.
It sends nothing over the internet and does not touch your real monitoring.

### The Quill Weather app -- alerts even when everything else is closed

Quill Weather is a small companion app whose only job is to keep the alert watch
running on its own:

- It lives in the **system tray**; closing its window tucks it back to the tray
  and it keeps watching. Only **Exit** quits it.
- **Options > Start Quill Weather with Windows** (with **Start minimized to the
  tray**) makes it watch from the moment you sign in, without opening a window.
- **Options > Check for alerts in the background (even when Quill Weather is
  closed)** goes further: Windows itself wakes a quick check on your interval,
  looks for new warnings, and shows a toast if it finds one -- so you are covered
  even with no program running at all.

And on the radio side, **Station > Start Quill Radio with Windows** launches Quill
Radio automatically when you sign in.

### Your local NOAA Weather Radio

NOAA Weather Radio is the National Weather Service's own broadcast voice --
continuous forecasts, conditions, and warnings from real VHF transmitters.
Quill Radio carries the authoritative directory of those transmitters and
their internet re-streams:

- **Weather menu > Listen to your Local NOAA Weather Radio** -- one keypress
  plays the transmitter covering your saved Weather location: your county's
  transmitter first, or the nearest one whose coverage includes you. If you
  have not set a Weather location yet, it tells you how instead of failing
  silently. Once playing, it is a normal station -- favorite it, record it,
  schedule it.
- **Weather menu > Update NOAA Weather Radio Directory** -- pull the newest
  directory on demand. It fetches off the UI thread, announces the result,
  and on failure leaves your existing data untouched. The complete directory
  ships inside the app (1,035 transmitters across every state and territory),
  so browsing and the local lookup work even fully offline; an update simply
  layers fresher data on top, and the bundled copy always remains as the
  floor. Off in Safe Mode.
- **Browse Stations > Weather / NOAA** -- the same directory as a browsable
  state-by-state tree; see the Station menu chapter.

The audio stream is a companion to the text weather above, not a replacement
for a dedicated NOAA Weather Radio receiver with alert tones.

### What's coming later

This release shows weather as **text** and streams NOAA Weather Radio audio.
Later phases of Quill Weather add spoken weather with its own voices and
interruption rules, and background alert monitoring that keeps watch while the
window is closed. See the Product Requirements document (Help > Product Requirements) for the full roadmap.

