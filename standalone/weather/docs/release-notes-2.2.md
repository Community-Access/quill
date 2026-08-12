# Quill Weather 2.2 -- Release Notes

Quill Weather is a small app with a big job: to watch the sky for you and speak
up the moment it matters. It began life inside Quill Radio's Weather menu, and
2.2.0 is the moment it stands on its own -- a program you can install, update,
and leave running by itself, quietly on guard.

It shares Quill Radio's version number on purpose. The two grew from one weather
effort and run the very same code, so 2.2.0 means the same weather in both. But
they are separate apps now, each with its own installer, its own tray icon, and
its own update feed -- install one, both, or neither.

## Headline: the QuillVille Runtime and lighter downloads

Quill Weather now shares one Python runtime -- the **QuillVille Runtime** --
with every other QuillVille app (QUILL, Quill Radio, and QUILL Audio Studio). It
is installed once per user and reused by all of them, so once any Quill app has
installed it, every app you add afterward starts instantly. The runtime is
reference-counted: it is removed only when the last app that needs it is
uninstalled.

That shared runtime adds two feather-light ways to get Quill Weather, alongside
the fully self-contained editions:

- **Companion edition** -- just the app and its docs (about 2 MB). The first
  time you launch it, if the runtime is not already on your machine, it offers
  to download and install it (about 230 MB, once) with a fully accessible
  progress bar. After that, this app and every other QuillVille app start
  instantly.
- **Thin installer** -- a tiny installer that downloads the shared runtime only
  if it is not already present.

Every runtime download, whether triggered by an installer or by the app's own
first launch, shows a fully accessible progress bar that works with NVDA, JAWS,
and Narrator, announcing progress as a percentage. See "Editions and the
QuillVille Runtime" below for the full list of downloads.

The app's launcher is also now a genuine, tiny native program, and the bundled
Python is the official unmodified build. Earlier versions used a renamed and
modified copy of Python's `pythonw.exe` as the launcher, which some antivirus
tools flagged as a false positive. That pattern is gone, so the Quill apps are
far less likely to be flagged.

## The idea: a guardian, not a screen

Most weather apps are something you open, glance at, and close. Quill Weather can
be that -- a clean, fully spoken **Weather Center** you arrow through -- but its
heart is the part that keeps working after you look away.

Turn on **Weather Monitoring** and it keeps a steady eye on your location's
official National Weather Service watches, warnings, and advisories, and
**speaks each new one the instant it is issued** -- interrupting whatever is
being read for the serious ones, a tornado or a flash flood, and telling you
when the all-clear comes. It watches while the window is tucked in the system
tray, resumes on its own the next time you launch, and shows a tray notification
for every new alert. When a warning is live it quickens its pulse, checking as
often as once a minute; when the sky clears, it eases off.

## The documentation is finally reachable from inside the app

A small fix with an embarrassing history: Quill Weather's installer has always
placed this document and the user guide right next to the program, and until now
nothing in the app could open either of them. The Help menu offered Check for
Updates and About, and that was all.

**Help > User Guide** and **Help > Release Notes** now open them in your browser,
where you can read them with the heading, link, and find-in-page navigation your
screen reader already gives you. They are installed alongside the app, so neither
needs an internet connection.

## Every place you have saved, watched at once

This is the change most likely to matter to you. The alert watch used to cover
your **primary** location and nothing else -- so a warning for your workplace,
your daughter's town, or the house you were driving to that weekend went
unheard, even though the place was sitting right there in your list.

Monitoring now covers **every location you have saved**, with no extra setup and
nothing to switch on. Each place is checked on the same schedule, and every new
alert is spoken with its place named -- "A Tornado Warning is in effect for
Tucson, Arizona" -- plays the alert sound, and drops its own tray notification,
so you always know *where* as well as *what*.

When monitoring starts you get one warm summary across all of them rather than a
line per place: "3 places: Tucson, Boston, and Reno. All clear right now." The
status line, the Start and Stop announcements, and the main window all say either
the one place's name or "for 3 places", so the app never leaves you guessing how
much it is actually watching.

Fine-grained picking -- watch these three, skip that one -- is still to come.
Today it is all of them.

## Everything Quill Weather says now reaches braille

Everything the app tells you -- a new warning, the all-clear, "monitoring on for
3 places", a setting you just changed -- is now written to a connected braille
display as well as spoken. Until now the standalone apps sent announcements to
speech only, so a braille reader with speech turned down received nothing at all.

Two refinements keep the display readable rather than frantic: a **burst of
different messages settles into one write** instead of flashing past faster than
fingers can follow (the first message writes through immediately, so nothing
feels delayed), and an **error is held on the display** rather than being wiped
by the next routine message. Braille is written through your screen reader, so it
works wherever NVDA or JAWS is driving the display; Narrator has no braille call
here because it brailles the notification Quill Weather already posts.

Underneath, every spoken message now travels through the same shared
announcement plumbing QUILL uses, so a message reaches speech, braille, the
status line, and the accessibility test capture together. A failure on one
channel -- a display unplugged mid-sentence, a screen reader that went away --
takes down only that channel; you still hear the message. The related preferences
live in QUILL's Preferences and are shared, so setting them once in QUILL is
enough.

## Alerts even when nothing is running

This is the reason Quill Weather exists as its own app. You should not have to
keep a program open to be warned about the weather.

- **Close it, and it keeps watching.** The window minimizes to the tray; the
  watch goes on.
- **Start with Windows.** One checkbox and Quill Weather is on guard from the
  moment you sign in, with no window ever opening.
- **Watch with nothing running at all.** Turn on the background check and Windows
  itself wakes a brief look at your chosen interval, finds any new warning, and
  raises a toast -- no Quill Weather process needed in between.
- **Call it back, or tuck it away, from anywhere -- Ctrl+Alt+Shift+W.** One
  system-wide keystroke, working even while another program has focus, hides the
  window to the tray (the watch never pauses) or brings it back and puts you in
  it -- so you need never hunt for the tray icon. Quill Weather says "hidden to
  the tray" or "shown" so you always know which way it went. Each app in the
  family has its own chord (QUILL is Ctrl+Alt+Shift+Q, Quill Radio is
  Ctrl+Alt+Shift+R), so they never step on one another. It is Windows-only and
  best-effort: if another app already claimed the chord, Quill Weather quietly
  yields it and the tray icon still shows and hides the window as always.

## A warning you cannot miss -- your way

Every new alert plays an attention **sounder**. In **Settings** you can silence
it entirely (the alert is still spoken and shown), swap in **your own sound
file** with a **Play** button to hear it first, and choose **how many times it
repeats**, from once to ten. And so a real warning never catches a setting wrong,
**Test Alert** rehearses the whole thing on demand -- the words, the sound, the
tray toast, and the alert window -- clearly marked as a test.

## The forecast, spoken in full

The Weather Center reads, as plain arrow-navigable, copyable text:

- any active **watches, warnings, and advisories**, with full official
  instructions;
- a warm paragraph of **current conditions** -- temperature, feels-like, sky,
  humidity, dew point, wind and gusts, pressure, visibility, cloud cover, the
  ultraviolet index, sunrise and sunset, the **moon** (phase, how full it is,
  moonrise and moonset -- worked out on your own machine), and air quality;
- an **hour-by-hour forecast**;
- the **National Weather Service forecast**, period by period; and
- an **extended daily outlook** of up to 16 days.

Every value is written for speech -- "the wind is blowing from the
west-northwest at 5 miles per hour", not "WNW 5 mph".

## Two clocks, so a far-off forecast makes sense

Check the weather in another city and the report now grounds you in *time* as
well as place. It reads the current local time **there**, the current local
time **where you are**, and **when the reading was taken** -- "Right now it is
Thursday, April 27, 9:51 AM in Tucson, Arizona, and 6:51 AM where you are. This
reading was checked just now." When you and the place you are checking share a
time zone, it says so once ("the same time zone") instead of repeating an
identical clock, and an older reading names the exact minute it was fetched in
*your* time rather than a vague "a while ago". No mental math, no wondering
whether an early-morning forecast is stale -- the *when* is spoken as plainly
as the *what*.

## Made to fit you

**Options > Customize Features...** turns whole areas of the app on or off --
Alert Monitoring, NOAA Weather Radio -- and the ones you switch off simply
disappear from the menus, exactly the way QUILL and Quill Radio let you tailor
themselves. And the apps stay within reach of one another: **Open Quill Radio**
and **Open QUILL** sit in the File menu and the tray, each opening in its own
window.

## Not a fork -- a guarantee

Quill Weather runs the exact same weather feature code as QUILL and Quill Radio,
from the same upstream `quill` package. Improvements land once, upstream, and
reach all three together. This app is only the wrapper, the installer, the icon,
and these docs -- so choosing Quill Weather never means choosing an older or
lesser version of the weather.

## Editions and the QuillVille Runtime

All QuillVille apps now share one Python runtime, the **QuillVille Runtime**,
installed once per user and reused by every app. Install it a single time and
every Quill app you add afterward starts instantly. It is reference-counted, so
it is removed only when the last app that needs it is uninstalled. Pick the
edition that fits how you want to run Quill Weather:

- **Full portable** (`Quill-Weather-Portable-<version>.zip`, about 82 MB) --
  fully self-contained: runs from a USB stick with no installation and no
  internet. It carries a genuine, unmodified copy of Python. Weather is a small
  app, so this build is already compact. Extract anywhere and run
  `QuillWeather.exe`; a `data` folder next to the exe holding a
  `storage-mode.json` marker (`{"mode": "portable"}`) keeps everything on the
  stick.
- **Companion edition** (`Quill-Weather-Companion-<version>.zip`, about 2 MB) --
  feather-light: just the app and its docs, running on the shared QuillVille
  Runtime. The first time you launch it, if the runtime is not already
  installed, it offers to download and install it (about 230 MB, once) with a
  fully accessible progress bar. After that, this app and every other QuillVille
  app start instantly.
- **Full installer** (`Quill-Weather-Setup-Shared-<version>.exe`) -- installs
  the shared runtime, if it is not already present, plus the app, with a Start
  Menu group, an uninstaller, and the shared data store.
- **Thin installer** (the `-Lite` setup) -- a tiny installer that downloads the
  shared runtime only if it is not already present, then installs the app.

Every runtime download, whether triggered by an installer or by the app's own
first launch, shows a fully accessible progress bar that works with NVDA, JAWS,
and Narrator, and announces progress as a percentage.

## Known notes

- Releases are not yet code-signed: Windows SmartScreen may warn on first run.
  Choose More info, then Run anyway. Signing is planned.
- Antivirus false positives are far less likely now: the launcher is a genuine
  native program and the bundled Python is the official unmodified build, so the
  old renamed-`pythonw.exe` pattern that some tools flagged is gone.
- No audio engine ships here, so NOAA Weather Radio *playback* needs Quill Radio
  installed; Quill Weather still finds your local transmitter.
