# Changelog -- Quill Weather

All notable changes to Quill Weather are recorded here. The fuller, more
detailed version of this changelog lives in `docs/CHANGELOG.md` (and its HTML
and EPUB twins) and ships with the app.

Quill Weather is versioned in lockstep with Quill Radio (they ship the same
weather code), but the two release and update independently. Its first public
release is 2.2.0.

## Unreleased

### New

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
