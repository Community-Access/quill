# Changelog -- Quill Weather

Quill Weather is versioned in lockstep with Quill Radio (they ship the same
weather code), but updates independently. Its first public release is 2.2.0.

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
- **Your local NOAA Weather Radio.** Find the transmitter covering your saved
  location (and play it, when Quill Radio is installed).
- **Customize Features.** **Options > Customize Features...** turns whole areas
  (Alert Monitoring, NOAA Weather Radio) on or off, hiding what you do not use --
  the same customization Quill Radio offers.
- **Open its siblings.** File > Open Quill Radio / Open QUILL, and the same from
  the tray, so the apps are always a click apart, each in its own window.

### Notes

- No audio playback or recording engine ships with Quill Weather (it is a much
  smaller download than Quill Radio). NOAA Weather Radio *playback* needs Quill
  Radio; Quill Weather still finds your local transmitter.
- Weather is also built into QUILL and Quill Radio -- this app is for when you
  want the watch running on its own, independent of everything else.
