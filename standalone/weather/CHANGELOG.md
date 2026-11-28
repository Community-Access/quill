# Changelog -- Quill Weather

All notable changes to Quill Weather are recorded here. The fuller, more
detailed version of this changelog lives in `docs/CHANGELOG.md` (and its HTML
and EPUB twins) and ships with the app.

Quill Weather shares weather code with Quill Radio, but the two release and
update independently. This version history begins with 2.2.0.

## Unreleased

- **Rain or snow starting soon, in words** (2026-11-28). Next Few Hours
  (Ctrl+Shift+U) and Weather Now now begin with whether rain or snow is starting in
  the next 2 hours, from Open-Meteo's 15-minute forecast: "Light rain starting in
  about 30 minutes", "Moderate rain now, stopping in about 45 minutes", or "No rain
  or snow expected in the next 2 hours". Outside North America and central Europe,
  where Open-Meteo estimates the 15-minute steps from hourly data, it says so. It
  rides the same single request as the glance ahead, and can be turned off in
  Settings.
- **The next four hours and the daylight change** (2026-11-28). **Weather menu >
  Next Few Hours** (Ctrl+Shift+U) speaks the next four hours at a glance (the
  temperature trend, any change in the sky, the highest chance of precipitation and
  notable wind) and how much more or less daylight there is than yesterday. Weather
  Now ends with the same two lines, and each can be turned off in Settings. Both
  come from one Open-Meteo request, inside the same daily budget, and a request
  that fails is said as such.
- **Weather on a Past Date and Weather History** (2026-11-28). **Weather menu >
  Weather on a Past Date** (Ctrl+Alt+D) shows any day since 1940 for any saved
  place, read like the current report and then hour by hour, with how it compared
  with normal. Type the date in plain words: 2011-03-14, March 14, 2011, 3/14/2011
  (in your system's order, and it says which order it read), yesterday, 3 days
  ago, or a year or a month to list every day in it. Alt+Left and Alt+Right move a
  day, with Shift a week, Ctrl+Page Up and Ctrl+Page Down a month, and
  Ctrl+Shift+Page Up and Ctrl+Shift+Page Down a year; each move says the new date
  first. It keeps your last 10 dates, copies a day as text, and saves a date range
  as CSV or text. **Weather History** (Ctrl+Shift+T) looks at today's date or any
  date over up to 85 years, or a date range, and says in plain words how it
  compares with normal and what the records are: US station records and 1991 to
  2020 normals from NOAA's Regional Climate Centers (RCC-ACIS), and Copernicus
  ERA5 history through Open-Meteo. Every day looked up is kept on your computer,
  Quill Weather stays well inside Open-Meteo's free limits and waits when asked
  to slow down, and a service that cannot be reached is said as such, never as
  "no data"; Alert Feed Status now lists these data feeds too.
- **Choose which places and which alerts** (2026-11-27). The new **Weather menu >
  Alert Choices** (Ctrl+Alt+Shift+C) lets you switch saved places on or off
  without deleting them, and choose which alerts you hear about: Everything,
  Essentials (tornado, severe thunderstorm and flash flood warnings, and anything
  Extreme), Safety (all warnings and Extreme or Severe watches), or your own by
  category, kind and severity. Each choice can speak and interrupt, speak quietly,
  play a sound only, or show in the list only, with its own sound for each
  severity, and quiet hours let only Extreme alerts break through. If you never
  open it, nothing changes. Extreme alerts are always told unless you turn that
  off after a plain warning, and an alert your choices keep quiet is never lost: it
  stays in the alert list and in Alert Feed Status, which counts how many were
  hidden. Every save says one sentence about what you chose.
- **Snooze, schedule and group your places** (2026-11-27). A place can be snoozed
  for 1, 4 or 12 hours or until tomorrow morning, watched until a date and time
  (a trip), given a schedule such as weekdays 8 to 6, and put in groups such as
  Family or Travel to watch or stop watching together. A snoozed place is still
  checked, and Extreme alerts still break through. **Weather > Watch This Place**
  (Ctrl+Alt+Shift+U) and a **Watched Places** submenu in the tray switch places
  quickly. The start-watching summary and Alert Feed Status say which places are
  not watched and why.

- **You can tell "no alerts" from "could not reach the service"** (2026-11-27).
  Before, a failed check was silent, which sounded exactly like a quiet sky. Now
  a failed check is never treated as no alerts: it does not clear the alerts you
  already had and it never says all clear. If checks keep failing for about ten
  minutes (sooner while an alert is active), Quill Weather says once, "Quill
  Weather cannot reach the National Weather Service. Alerts may be missing. The
  last successful check was at 3:12 PM, and it found no alerts." It repeats only
  after about half an hour of still failing, and says once when it recovers. The
  background check shows the same as a notification, and the tray tooltip shows
  the state. When monitoring starts, a place that could not be checked is named
  as unchecked rather than counted as clear.
- **Weather menu > Alert Feed Status** (Ctrl+Alt+Shift+H) is a new report, with
  Copy, of how the alert feed is doing for each place you watch: the state, the
  last successful check, the last attempt, what went wrong in plain words, and
  the last alerts the service provided, marked last known when they are old. In
  Safe Mode it says network checks are off, not that the service is unreachable.

## 2.2.1 - 2026-10-08

### Fixes from the November review (2026-11-09)

- **Alert monitoring keeps going after a bad reply** (2026-11-09). One
  reply from the Weather Service that was cut short could stop alert
  monitoring for good, without a word. Now that check is missed and the next
  one runs on time.
- **With the app closed, every watched place is checked** (2026-11-09). The
  background check that runs while Quill Weather is closed looked only at the
  first place you watch. It now checks them all, the same places the app
  watches when it is open, and the alert names the place it is for.
- **"Getting weather" always gets an answer** (2026-11-09). If the forecast
  for an AI question could not be read, Quill Weather said "Getting weather
  for" your place and then nothing. Now it says it could not get the weather.

### AI menu (2026-11-03)

- **One AI menu, the same in every app** (2026-11-03). The AI menu now reads in four groups, in the same order in every QuillVille app: the ways to ask; what this app's AI does; Which AI Am I Using and Choose Your AI; and **Accounts and Usage**, a submenu holding Use My Own AI Key, Use My ChatGPT Subscription, Usage and the Privacy Agreement (and, where the app has them, Connect or Sign Out and Web Searches Left). Every command keeps its key wherever it now sits.
- **Your own key is not only OpenAI** (2026-11-03). Before you have saved a key, Choose Your AI's own-key row now names every service it can use: OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Ollama Cloud, a service of your own, or Ollama on this computer, which is free and sends nothing. It used to say only OpenAI.

### Sound scheme (2026-11-02)

- **A second sound scheme: VS Code Signals** (2026-11-02). Quill Weather plays
  the QUILL family's sound scheme, and there are now two: Ink, still the
  default, and VS Code Signals, the accessibility signal sounds from Visual
  Studio Code, used under the MIT licence. Choose in the Sound Scheme window
  of QUILL or QUILL Lite, or in QUILL's setup wizard, and Quill Weather plays
  it from the next time it starts. Anything it has no sound for stays quiet,
  or is spoken instead.

### AI, when you ask for it (2026-11-01)

- **Choose Your AI comes to Quill Weather.** A new AI menu (Alt+I) holds Ask
  (Ctrl+Shift+8), Which AI Am I Using (Ctrl+F8; press it twice to open the
  window), Choose Your AI (Ctrl+Shift+F8), Use My ChatGPT Subscription
  (Alt+F5), Use My Own AI Key (Alt+F2), AI Usage (Ctrl+Alt+Shift+F2) and the
  Privacy Agreement (Ctrl+Alt+Shift+K). Quill Weather signs in on its own, as
  "QUILL Weather", and keeps its choice in `weather-ai.json`.
- **Should I Go Out?** (Ctrl+Shift+G) answers in plain words from the forecast
  for your primary place. Any active alert comes first, in the Weather
  Service's own words; the AI never rewords one.
- **Ask** talks about the forecast: your place's name (never its coordinates),
  the current conditions, the next hours, the forecast and the alert names go
  with each message.
- **An AI line** in the main window says which AI is in use; Enter on it opens
  Choose Your AI.
- Text only: no radar or maps. The alert watch stays AI-free, nothing runs on a
  timer, and Safe Mode turns every AI command off.

### Since build 2 (2026-10-30 and 2026-10-31)

- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which includes PyMuPDF 1.28.2 under AGPL-3.0 through the shared GLOW
  dependency; Weather does not itself expose GLOW. Its exact source, and that
  of every other GPL, LGPL or AGPL part, is published with each release.
  Portable editions leave GLOW, and with it PyMuPDF, out. See Licences and
  Notices.
- **Controls that had no label now have a spoken name** (2026-10-30).
  JAWS, NVDA and Narrator used to announce them as a bare role, such as
  "edit" or "list". The Weather Center's status line now says "Weather source and freshness status".
- **Sharp text at any display scaling** (2026-10-31). Quill Weather now handles
  each monitor's scaling itself instead of letting Windows stretch it, so
  text stays sharp at 125, 150 and 200 percent and on monitors with
  different scaling, and windows and list columns keep their proportions.
  Setting the environment variable `QUILL_DPI_UNAWARE` to `1` turns this off,
  for diagnosing a display problem (#1702).
- **Pygments in the notices** (2026-10-31). The shared runtime now bundles
  Pygments, which QUILL and QUILL Lite use to read code and web pages for
  spell check, so Quill Weather's third-party notices list it.

### Build 2

- **Where Quill Weather's own sounds play, and Alt+Shift+M to turn them off.** **Options > App Sounds Play On...** (Ctrl+Shift+S) offers System default, None (no sounds), or any sound card or headset by name; a weather alert is still spoken when its sound is off. After a change one sound plays on the new card, so you hear where it went. If that card is unplugged the sounds play on the system default until it is back, and Quill Weather says so once. **Alt+Shift+M** turns Quill Weather's sounds off and back on where they were, and **Options > App Sounds** shows a check mark while they are on. Each QUILL app keeps its own choice; "Share these choices with my other Quill apps" keeps them in step. Your screen reader is never moved. Asked for on QUILLVille by Rick Lewis.

- Current conditions, Quick Weather, and local time now use a saved place's friendly name, such as Home or Summer Home.
- Builds now offer only the shared installer and self-contained portable zip, with matching update selection and shared-runtime freshness checks.
- The installer is per-user and records Weather's own version; the portable launcher stays offline and cannot register Windows startup or scheduled background checks.
- Help now exposes Activity and Repeat Last Result, which were already available through the shared app shell.
- Tray settings and Windows startup/background toggles now report failed changes and restore the menu's actual state.
- **Help > What's New** (Ctrl+Shift+F1) opens the changelog in your browser, on the same key as every other QuillVille app.
- **Help > Command Palette...** (Ctrl+Shift+P) and **Help > Product Requirements...** (Alt+Shift+F1) are on the Help menu.
- **QUILL Transcribe on the QuillVille menu and the tray**, released on 1 November 2026.
- The user guide teaches Ctrl+Alt+Shift+M for Start Weather Monitoring, no longer describes a Quillins menu, and marks Quill Radio's own commands as Radio's.

### Show and hide key off by default (2026-10-05)

- **No show and hide key until you choose one** (2026-10-05). The app
  registered Ctrl+Alt+Shift+W system-wide, and other QuillVille apps use that key for
  menu commands, so while this app ran theirs never fired. It now has no key by
  default; **File > Show and Hide Key...** (Ctrl+Alt+Shift+H) lets you type
  one, or leave it empty for none, and refuses a key any QuillVille app uses as
  a command or as its own show and hide key, in one sentence naming the app.
  Somebody who had the old key is moved to none and told once, at the next
  launch; a key somebody chose is kept (`quill/core/family_chords.py`,
  `quill/core/show_hide_keys.py`, `quill/ui/show_hide_key_picker.py`).

### Tutorials, and every weather verb by name (2026-08-28)

- **Help > Tutorials... (Ctrl+Alt+F1)** -- 11 guided tutorials, 60 steps, in
  three tracks: your first ten minutes, being warned, and making it yours. The
  middle track is the app's whole reason for existing, so it is five lessons:
  start the watch, rehearse an alert, decide what gets through, keep the watch
  running, and NOAA Weather Radio.

- **A step names a command, not a key**; **Try it** runs it; and **Follow me**
  watches the app once a second and moves you on when it can see you have done
  the step -- your saved places growing, the watch starting, alert checks
  pausing. It watches state rather than keystrokes, so the menu, the key, the
  tray and the palette all count.

- **Quill Weather has command ids at all now.** Every weather verb was a bound
  menu item and nothing else, so the Command Palette -- which this app carries
  -- could not reach a single one of them, and a tutorial step could not name
  one. The ids are registered with the keys the menu labels already advertise,
  so the menus are unchanged; they simply have names now.

- **The book is generated from the lessons** (`docs/tutorials.md`, GATE-TUTDOC).

### New

- **Quill Weather has its own icon.** Until now it shipped a byte-identical copy
  of Quill Radio's broadcast-wave icon, carried over when the app was
  scaffolded -- so on a desktop with both installed, two different products wore
  the same face in the taskbar, in Alt+Tab and in the tray, where a
  tray-resident app lives its whole life. Quill Weather's icon is now a sun
  behind a cloud on a sky-blue tile: the same rounded shape and amber accent as
  the rest of the family, its own silhouette and its own colour. It is the one
  glyph in the family that is a picture of a thing rather than a diagram,
  because weather is the one app whose subject is a thing.
- **Weather Guardian watches every place you have saved, not just one.** The
  alert watch used to cover your primary location only, so a warning for work,
  for family, or for where you were travelling went unheard. Now it covers every
  saved location with no extra setup. Each new alert names its place when it is
  spoken, sounds the alert, and posts its own tray notification, so you always
  know *where* as well as *what*. Starting monitoring speaks one combined
  summary -- "3 places: Tucson, Boston, and Reno. All clear right now." -- and
  the status line and Start/Stop messages say either the one place's name or
  "for 3 places". Picking exactly which places to watch is still to come; today
  it is all of them.
- **A QuillVille menu.** A top-level **QuillVille** menu lists the other apps in
  the family -- **Open QUILL**, **Open Quill Radio** -- each opening in its own
  window. Every QuillVille app carries the same menu in the same place, so
  moving around the suite is muscle memory. The tray menu offers the same list.
- **A missing companion app is offered, not refused.** Choosing to open a
  sibling that is not installed used to dead-end at "not installed". Quill
  Weather now asks whether you would like to download and install it, fetches
  and verifies it in the background if you say yes, and opens it when it is
  ready -- or offers the web release page if the download cannot be reached.
  Nothing is downloaded without your yes.
- **Announcements reach your braille display, not just your speech.** Every
  message Quill Weather gives you -- a new warning, the all-clear, "monitoring
  on for 3 places", a saved setting -- is now written to a connected braille
  display as well as spoken. A braille reader with speech turned down previously
  received nothing at all from this app. A burst of different messages settles
  into a single write instead of flashing past faster than fingers can follow
  (the first message still writes through immediately), and an error is held on
  the display rather than being wiped by the next routine message. Braille goes
  out through your screen reader, so it works wherever NVDA or JAWS is driving
  the display.
- **One announcement service behind every message.** Quill Weather's messages
  now travel through the same shared announcement plumbing QUILL uses, reaching
  speech, braille, and the status line together. One channel failing -- a
  display unplugged, a screen reader that went away -- costs only that channel;
  you still hear the message. The related preferences (braille on or off, the
  braille style, how long an identical repeat is suppressed, sticky errors,
  sound cues in the apps) are set in QUILL's Preferences and shared, because the
  apps share one settings store on a machine.
- **The QuillVille Runtime, and two lighter editions.** All the Quill apps now
  share one Python runtime, installed once per user and reused by every app, so
  each app you add after the first starts instantly. It is reference-counted --
  removed only when the last app that needs it is uninstalled. Alongside the
  full portable build and the full installer, there is now a **Companion
  edition** (about 2 MB: just the app and its docs, offering to fetch the shared
  runtime on first launch) and a **thin installer** that downloads the runtime
  only if it is not already there. Every runtime download shows a fully
  accessible progress bar that announces its percentage with NVDA, JAWS, and
  Narrator.
- **Fewer antivirus false positives.** The launcher is now a genuine, tiny
  native program and the bundled Python is the official unmodified build.
  Earlier versions used a renamed, modified copy of Python's `pythonw.exe`,
  a pattern some antivirus tools flagged; it is gone.

### Changed

- **The download is less than half the size.** The portable ZIP went from about
  176 MB to 79 MB and the installer from about 123 MB to 52 MB, by dropping
  libraries Quill Weather never runs (a translation build tool, a PDF stack,
  data-science and video libraries) that a broad packaging rule had been pulling
  in. Nothing was removed from the app itself.
- **Updates come from one shared release feed, each app taking only its own.**
  **Help > Check for Updates...** reads the single Quill release feed but looks
  only at the Quill Weather downloads in it, so a Quill Radio release is never
  mistaken for a Quill Weather one. Each app still updates on its own schedule.
- **Opening a sibling app moved from the File menu to the QuillVille menu.** The
  File menu now holds just **Minimize to Tray** and **Exit**.

## 2.2.0 -- first release

Quill Weather's debut, split out of Quill Radio's weather work so it can be
installed, updated, and left running on its own.

### New

- **A standalone weather watcher that lives in the system tray.** Close the
  window and it keeps monitoring; **Start Quill Weather with Windows** puts it
  on guard from login; and an optional scheduled background check watches with
  no window open at all and toasts you when a new alert appears.
- **A global show/hide hotkey -- Ctrl+Alt+Shift+W.** Press it from any app to
  tuck Quill Weather to the tray (the watch keeps running) or bring it back and
  focus it; it speaks "hidden to the tray" or "shown". The chord is unique to
  Quill Weather in the QuillVille family, so it never collides with QUILL or
  Quill Radio. Windows-only, and best-effort -- if another app already owns the
  chord, Quill Weather simply leaves it be and still shows and hides from the
  tray icon.
- **Weather Guardian -- spoken alerts the moment they are issued.** Background
  monitoring of your location's official National Weather Service watches,
  warnings, and advisories, speaking each new one aloud (interrupting for
  tornado/flash-flood-level events), announcing the all-clear, and tightening
  its poll during severe weather.
- **An alert sounder you control.** A bundled chime, with settings to silence
  it, choose your own sound file (with a Play preview), and set how many times
  it repeats -- plus a **Test Alert** that previews the whole experience (text,
  sound, tray toast, dialog), clearly marked as a test.
- **A full Weather Center.** Current conditions, the NWS forecast, an hourly
  forecast, an extended daily outlook (up to 16 days), air quality, sunrise and
  sunset, a locally-computed moon almanac (phase, illumination, moonrise,
  moonset), and a two-clock time summary -- the current local time at the
  searched location, the current local time where you are, and when the reading
  was taken (collapsing to one clock when both share a time zone) -- all as
  arrow-navigable, copyable, fully spoken text.
- **Quick Weather and Active Alerts.** **Ctrl+Shift+Q** speaks a one-line
  summary of your primary location with no window; **Active Alerts** opens the
  Weather Center with focus already on the alerts list.
- **Your local NOAA Weather Radio.** Find the transmitter covering your saved
  location (and play it, when Quill Radio is installed). The full directory of
  1,035 transmitters ships inside the app, so lookup works offline.
- **Customize Features.** **Options > Customize Features...** turns whole areas
  (Alert Monitoring, NOAA Weather Radio) on or off, hiding what you do not use --
  the same customization Quill Radio offers.
- **Open its siblings.** File > Open Quill Radio / Open QUILL, and the same from
  the tray, so the apps are always a click apart, each in its own window. (These
  moved to the QuillVille menu after this release -- see Unreleased.)
- **Independent distribution and updates.** Its own installer and portable
  build, and **Help > Check for Updates** knows which of the two you are running
  and fetches the matching one.

### Notes

- No audio playback or recording engine ships with Quill Weather (it is a much
  smaller download than Quill Radio). NOAA Weather Radio *playback* needs Quill
  Radio; Quill Weather still finds your local transmitter.
- Weather is also built into QUILL and Quill Radio -- this app is for when you
  want the watch running on its own, independent of everything else.
