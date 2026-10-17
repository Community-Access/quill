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
- **A key to show and hide Quill Weather from anywhere.** You can choose one
  key that works from any program, even when Quill Weather does not have focus.
  Press it once to hide the window to the tray (monitoring keeps running); press
  it again to bring the window back and focus it. Quill Weather says "hidden to
  the tray" or "shown" so you know which happened, and you never have to go
  looking for the tray icon.

  There is no key until you choose one. Open **File > Show and Hide Key...**
  (Ctrl+Alt+Shift+H), type the key you want, and press Enter. Leave the box
  empty for no key. If another QuillVille app already uses the key you type,
  Quill Weather tells you whose it is and lets you try another, so the apps
  never fight over a key. If some other program already has it, Quill Weather
  says so and keeps the key you had. It is Windows-only, and the tray icon
  always works too.

  If you used an earlier version, you may remember Ctrl+Alt+Shift+W doing this.
  Other QuillVille apps use that key, so it is off now. Quill Weather tells you
  once, the first time you start it after updating.
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

Quill Weather's icon is a gold sun behind a white cloud, on a sky-blue tile. If
you have used an earlier build, this is new: Quill Weather used to share Quill
Radio's broadcast-wave icon, so on a desktop with both installed the two looked
identical in the tray and in the taskbar. Every app in the family now has its
own - the same rounded tile shape and the same gold accent throughout, but its
own colour and its own picture each.

Right-click the tray icon (or use the Applications key) for: the current
monitoring status, **Open Weather Center**, **Quick Weather**, **Start/Stop
Monitoring**, **Open Quill Radio**, **Open QUILL**, **Show**, and **Exit**.
Left-double-click the icon to bring the window back.

## Weather Monitoring (Weather Guardian)

**Weather menu > Start Weather Monitoring** (Ctrl+Alt+Shift+M) watches your saved
locations' official alerts and speaks each new one as it is issued, with a system
-tray notification and the alert sounder. **Pause Alert Checks** snoozes it
without turning it off. See **Settings** for the alert sounder controls (on/off,
your own sound file with a Play button, and how many times it repeats), and
**Weather menu > Test Alert** to preview the whole experience.

**Every place you have saved is watched, not just one.** You do not have to
choose or configure anything: if you have added home, work, and your daughter's
town, all three are covered. Each place is checked on the same schedule, and each
new alert names its place when it is spoken and in its tray notification, so you
always know where as well as what. When monitoring starts you hear one combined
summary rather than a line per place -- for example, "3 places: Tucson, Boston,
and Reno. All clear right now." The status line and the main window say either
the one place's name or "for 3 places". (Picking exactly which of your saved
places to watch is coming; today the watch covers all of them.)

## Customizing features

**Options > Customize Features...** lists the app's switchable areas -- **Alert
Monitoring** and **NOAA Weather Radio** -- each with a short description.
Unchecking one removes its menu items the next time you open Quill Weather, so
you can trim the app to just what you use. (This is the same customization Quill
Radio offers.)

## Quillins

**Quillins** -- QUILL's small, sandboxed, permission-gated add-ons -- are not
loaded by Quill Weather yet, and this release has no Quillins menu. The groundwork
is there: a Quillin can declare that it targets Quill Weather, and the bundled
`weather-extra-alerts` sample shows the idea, an additional alert source whose
alerts would be merged into the ones Weather Monitoring already watches. Until
Quill Weather loads them, that sample does nothing here, and every alert you hear
comes from the National Weather Service.

## How Quill Weather talks to you

Everything Quill Weather tells you -- a new warning, the all-clear, "monitoring
on for 3 places", a setting you just saved -- goes out on more than one channel
at the same time, so you receive it the way you actually read.

- **Speech.** Your screen reader speaks it. Urgent messages interrupt whatever
  is being read; routine confirmations wait their turn.
- **Braille.** The same message is written to a connected braille display. If
  you keep speech turned down and read by touch, you no longer miss Quill
  Weather's messages -- earlier versions spoke only. Two things keep the display
  readable: when several different messages arrive in a rush they settle into a
  single write rather than flashing past faster than your fingers can follow
  (the first one still appears immediately, so nothing feels slow), and an error
  message is held on the display instead of being wiped by the next routine
  update. Braille is written through your screen reader, so it works wherever
  NVDA or JAWS is driving your display.
- **The status line** at the bottom of the window keeps the last message, so you
  can go back and read it with your review cursor.

If one channel fails -- a display unplugged mid-sentence, a screen reader that
went away -- only that channel is affected; the message still reaches you the
other ways.

These preferences are shared with QUILL, because the apps use one settings store
on a machine: **Preferences > Accessibility** in QUILL controls whether
announcements are brailled at all, the braille wording style, how long an
identical repeat is suppressed before it may take the display again, whether
errors stay on the display, and whether the companion apps play sound cues.
Change them once in QUILL and Quill Weather follows.

## Where Quill Weather's own sounds play

Quill Weather makes short sounds of its own, such as the one that marks a new weather alert. You choose where they play, and you can turn them off.

- **Alt+Shift+M** turns Quill Weather's sounds off. Press it again and they come back, on the same sound card as before. You hear a short sound as they go off, and another where they now play when they come back on, and both are spoken too. **Options > App Sounds** has a check mark that shows whether they are on.
- **Options > App Sounds Play On... (Ctrl+Shift+S)** lets you pick where they play:
  - **System default**. This is where it starts. The sounds go where Windows sends sound.
  - **None (no sounds)**. Quill Weather makes no sounds at all. Everything it tells you is still spoken.
  - **Any sound card or headset in the list.** The sounds get a device of their own.

After you choose, one sound plays on the new device, so you know straight away where it went.

If the device you chose is unplugged or asleep, you still hear every sound, on the system default, and Quill Weather tells you once. When the device comes back, the sounds go back to it by themselves.

This changes Quill Weather only. Your other QUILL apps keep their own choice, unless you have checked "Share these choices with my other Quill apps", which copies a change here to the others that share. Your screen reader is never moved. A weather alert is still spoken when its sound is off.

## Reaching the other apps

Quill Weather and the other QuillVille apps are separate apps that can open each
other. The top-level **QuillVille** menu (Alt+Q) lists the others, and each opens
in its own window; if it is already running, it simply comes to the front. Every
row has its own letter, so Alt+Q and then one letter opens an app with nothing
held down:

- **Open QUILL**: Alt+Q, then Q (or Ctrl+Alt+Shift+F7)
- **Open Quill Radio**: Alt+Q, then R (or Ctrl+Alt+Shift+F8)
- **Open Quill Converter**: Alt+Q, then V (or Ctrl+Alt+Shift+F9)
- **Open Quill Inkwell**: Alt+Q, then I (or Ctrl+Alt+Shift+F10)
- **Open QUILL Transcribe**: Alt+Q, then T (or Ctrl+Alt+Shift+F11). QUILL
  Transcribe, released on 1 November 2026, types what you say into any
  program.

For example, to dictate a note about tomorrow's forecast into your email, press
Ctrl+Alt+Shift+F11 to open QUILL Transcribe, then go to your email and press its
start and stop key (Alt+Shift+Backslash unless you changed it). Every
QuillVille app carries the same menu in the same place, so getting from one to
another is the same keystrokes everywhere.

The tray menu offers a shorter list: **Open QUILL**, **Open Quill Radio** and
**Open QUILL Transcribe**.

If the app you pick is not installed yet, Quill Weather does not just tell you
so. It asks whether you would like to download and install it, and if you say
yes it fetches and verifies it in the background and opens it when it is ready.
If the download cannot be reached, it offers the web release page instead.
Nothing is downloaded without your yes.

On the same machine all three apps share one data store, so a location you saved
in one is there in the others.

## Editions and the QuillVille Runtime

Quill Weather shares one Python runtime -- the **QuillVille Runtime** -- with
every other QuillVille app (QUILL, Quill Radio, and QUILL Audio Studio). It is
installed once per user and reused by all of them, so once any Quill app has
installed it, every app you add afterward starts instantly. The runtime is
reference-counted: it is removed only when the last app that needs it is
uninstalled.

There are two downloads. Pick the one that fits how you want to run Quill
Weather:

- **Portable** (`Quill-Weather-Portable-<version>.zip`) is
  fully self-contained: it runs from a USB stick with no installation and no
  internet, and it carries a genuine, unmodified copy of Python. Weather is a
  small app, so this build is already compact. Extract it anywhere and run
  `QuillWeather.exe`. A `data` folder next to the exe (holding a
  `storage-mode.json` marker set to portable) keeps everything on the stick.
- **Shared installer** (`Quill-Weather-Setup-Shared-<version>.exe`) runs per
  user, without an administrator prompt. It includes the shared runtime and
  installs it if it is not already present, plus the app, with a Start Menu
  entry and an uninstaller.

Both downloads include the runtime they need and work without a first-launch
runtime download. The portable launcher also stays offline if its bundled
runtime is damaged: extract a fresh copy to repair it.

The installed copy can start with Windows in the tray and register a scheduled
background alert check through the Options menu. A portable copy does neither:
those choices would leave startup entries or scheduled tasks on the host PC, so
Weather explains that installation is required and leaves its menu checks off.

**Help > Activity...** (Shift+F9) shows recent results and any available
retry. **Help > Repeat Last Result** (F9) speaks the latest important result
again. These commands use the same result history as the other Quill apps.

**A note on antivirus:** the app's launcher is now a genuine, tiny native
program, and the bundled Python is the official unmodified build. Earlier
versions used a renamed and modified copy of Python's `pythonw.exe` as the
launcher, which some antivirus tools flagged as a false positive. That pattern
is gone, so the Quill apps are far less likely to be flagged.

## Help

**Help > User Guide** opens this document, and **Help > Release Notes** opens the
notes for the version you are running. Both ship inside Quill Weather, so they
work with no internet connection. They open in your browser, which means you can
read them with the screen-reader navigation you already know -- headings, links,
and find-in-page.

**Help > Product Requirements... (Alt+Shift+F1)** opens the Product Requirements
document the same way. It is the roadmap: what Quill Weather is for, what it does
today, and what later releases add, such as spoken weather with its own voices
and choosing exactly which saved places the alert watch covers. Alt+Shift+F1 is
the same key Quill Radio and Quill Converter use for their own.

**Help > Command Palette... (Ctrl+Shift+P)** finds any Quill Weather command by
name. Type a few letters and the list narrows; each row shows the command's key,
so it also teaches you the key for next time. For example, press Ctrl+Shift+P,
type `quick`, and the list narrows to **Weather: Quick Weather**; press Enter and
you hear the one-line summary, exactly as if you had pressed Ctrl+Shift+Q.
Escape closes the palette without running anything. It lists only Quill
Weather's own commands, not those of the other QuillVille apps.

## Tutorials

**Help > Tutorials... (Ctrl+Alt+F1)** opens 11 guided tutorials -- 60 steps,
about 47 minutes of material -- covering every feature Quill Weather has, in the order somebody
would actually learn it. They are not a second copy of this guide. A guide
answers "what does this do"; it cannot answer "what do I do now", because a
document cannot see what you have already done. This window can.

- **They show the keys you have.** A step names the *command* it is about, and
  the key is rendered when the step is drawn. Rebind something and the tutorial
  says your key.
- **Try it runs the step.** Any step that names a command can be performed from
  the lesson, so a tutorial can open a window for you and then talk you through
  what you are standing in.
- **Follow me notices that you did it.** Check **Follow me** and the lesson
  watches the app -- once a second, and it watches *what changed*, never which
  key you pressed -- so however you do the step, it says what it saw ("Done:
  the watch is running") and reads you the next one. It never takes the keyboard, and
  nothing is graded: every step still has **Next**, and a check that never comes
  true costs you one keypress.

The Tutorials window is a **real window, not a wizard**: leave it open, move to
the app, do the step there, and hear the lesson move on behind you. A modal
dialog would own the keyboard for the whole lesson, which is the wrong shape
for teaching somebody to use the thing underneath it.

**The contents.** Three tracks, in teaching order. Each row says how many
steps it has, roughly how long it takes, and whether you have finished it. The
filter box narrows the list -- every word you type has to appear somewhere in a
tutorial -- and typing **here** narrows it to the tutorials about the window you
came from.

**Your place is kept.** Close a lesson half way through and it opens there
again. Finishing one is remembered separately from where you are in it. **Forget
my progress** clears the lot and changes nothing else. Nothing about your
progress leaves this computer.

**Reading rather than doing.** **Read it all** shows a whole tutorial as one
page of text, and **The whole book as a document** opens all 11 of them as
one page -- generated from the same lessons the window teaches from, so the two
cannot disagree. It ships as `docs/tutorials.md` beside this guide. The document states the
keys the app ships with; only the window can know the ones you rebound.

## Updating

Help > About shows your version with a build number, such as 2.2.1 (build 1). The
build number tells you which build of a version you have: when a fix comes out
without a new version number, it is a newer build, and Check for Updates offers it.

**Help > Check for Updates** knows whether you run the installer or the portable
build and downloads the matching one. All the Quill apps publish to one release
feed, and each looks only at its own downloads there, so a Quill Radio release is
never offered to you as a Quill Weather update. Quill Weather updates on its own
schedule, separate from Quill Radio. Because the QuillVille Runtime is shared, an app
update is usually just the small app itself; the large runtime is downloaded
only when a new one is required, and again with a fully accessible progress bar.

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

The friendly name is what Weather uses in Current conditions, Quick Weather,
local time, the Location chooser, and spoken monitoring messages. For example,
save two places as **Home** and **Summer Home** and each report names the place
you chose. Leave the name blank to use the search result's place name.

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

> Here is the weather for Home. It is 96 degrees Fahrenheit and mostly
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

**Weather menu > Start Weather Monitoring** (or **Ctrl+Alt+Shift+M**) watches your
saved locations' official watches, warnings, and advisories and **speaks each new
one the moment it is issued** -- with interrupting speech for the most serious
events (tornado, flash flood) -- and tells you when they all clear. It also drops
a notification in the system tray for each new alert, so you can see it there.

- **Every saved location is watched at once**, with no setup: home, work, and
  family are all covered. Each alert names its place when it is spoken and in its
  tray notification. Starting the watch speaks a single combined summary across
  the places ("3 places: Tucson, Boston, and Reno. All clear right now."), and
  turning it off or reading the status line says either the one place's name or
  "for 3 places". Choosing a subset of your saved places is a later addition.
- It keeps working while the app is **minimized to the tray**, and it starts
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

If you also use Quill Radio, its own **Station > Start Quill Radio with Windows**
launches Quill Radio when you sign in. That item is on Quill Radio's menu, not on
Quill Weather's.

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
- **In Quill Radio, Browse Stations > Weather / NOAA** -- the same directory as
  a browsable state-by-state tree; see the Station menu chapter of the Quill
  Radio User Guide. Quill Weather itself has no Browse Stations window.

The audio stream is a companion to the text weather above, not a replacement
for a dedicated NOAA Weather Radio receiver with alert tones.

### What's coming later

This release shows weather as **text**, watches your saved places for alerts in
the background, and streams NOAA Weather Radio audio. Later phases add spoken
weather with its own voices and interruption rules per feed and per alert,
continuously generated weather channels, and choosing exactly which of your saved
places the alert watch covers. See the Product Requirements document
(Help > Product Requirements) for the full roadmap.


## Getting help

Support is run by **Community Access**, and the address is
**support@community-access.org**. A person reads it, and replies come back by
email.

The quickest way there is **Help > Get Help from Support...** (Ctrl+Alt+F2),
which every app in the family answers with the same form: what kind of message
this is, a subject, what happened, and -- if you want an answer -- an email
address to reply to. What you expected and how to reproduce it are optional,
and worth more than anything else when you can give them.

Press Send and your **own mail program opens with the whole message already
written**, addressed to support, with Quill Weather's name and version and your Windows
version filled in at the bottom. Nothing is sent until you send it there, so you
can read it over, add anything, or change your mind.

If this machine has no mail program set up -- webmail only, say -- the app puts
the whole message on your clipboard and tells you the address, so nothing you
typed is lost. And writing to **support@community-access.org** yourself always
works just as well: there is no form you have to use. Say which app you were
using and what happened.
