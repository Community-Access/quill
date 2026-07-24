# Quill Weather 2.2 -- Release Notes

Quill Weather is a small app with a big job: to watch the sky for you and speak
up the moment it matters. It began life inside Quill Radio's Weather menu, and
2.2.0 is the moment it stands on its own -- a program you can install, update,
and leave running by itself, quietly on guard.

It shares Quill Radio's version number on purpose. The two grew from one weather
effort and run the very same code, so 2.2.0 means the same weather in both. But
they are separate apps now, each with its own installer, its own tray icon, and
its own update feed -- install one, both, or neither.

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

## Known notes

- Releases are not yet code-signed: Windows SmartScreen may warn on first run.
  Choose More info, then Run anyway. Signing is planned.
- No audio engine ships here, so NOAA Weather Radio *playback* needs Quill Radio
  installed; Quill Weather still finds your local transmitter.
