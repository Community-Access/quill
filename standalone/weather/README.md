# Quill Weather

Accessible, screen-reader-first weather -- with background alert monitoring that watches over you -- as a standalone Windows app, from the QUILL project.

Quill Weather is not a fork. The whole application lives in the [quill](https://github.com/Community-Access/quill) package (`quill.apps.weather`) and runs the exact same weather feature code QUILL and Quill Radio use: the same National Weather Service client, the same Weather Center, the same Weather Guardian alert monitoring. This repository holds only what exists because QUILL is not in the picture: the product wrapper (entry point), the installer, and this app's own documentation. Everything shared stays upstream, so Quill Weather tracks QUILL automatically.

**Quill Weather and Quill Radio are a pair.** They ship the same weather code and are released together, so they share a version line (this is **2.2.0**). But they are separate, independently distributed and **independently updated** apps -- install one, both, or neither. When both are installed they can open each other, and each has its own system-tray icon, so they run happily side by side.

## What it does

- **Weather Center** -- current conditions, the National Weather Service forecast, an hour-by-hour forecast, an extended daily outlook (up to 16 days), air quality, sunrise/sunset, and a locally-computed **moon** almanac (phase, illumination, moonrise, moonset), all as arrow-navigable, copyable, fully spoken text.
- **Weather Guardian** -- turn on monitoring and it watches your location's official watches, warnings, and advisories and **speaks each new one the moment it is issued**, with an attention sounder you can customize (or replace, or silence) and a Test Alert to preview the whole experience. A **severe-weather mode** checks more often while a warning is active.
- **Alerts even when nothing is running** -- Quill Weather lives in the **system tray** and keeps watching after you close the window; turn on **Start Quill Weather with Windows** and it is on guard from login; or let a scheduled background check watch with **no window open at all** and toast you when a new warning appears.
- **Your local NOAA Weather Radio** -- find and (with Quill Radio) play the transmitter covering your saved location.
- **Customize it** -- **Options > Customize Features...** turns whole areas on or off (the same customization Quill Radio has), hiding what you do not use.
- **The local time in another city** -- checking the weather somewhere far away also tells you what time it is there.
- Shares your saved locations and settings with QUILL and Quill Radio (one data store in `%APPDATA%\Quill`).

Deliberately not included: QUILL's editor, AI, transcription, braille, and speech-synthesis stacks -- and, unlike Quill Radio, no audio playback or recording engine (so it is a much smaller download). This is the weather, and just the weather. (NOAA Weather Radio *playback* needs Quill Radio; Quill Weather still finds your local transmitter.)

## Install

Two flavors, both on this repository's Releases page:

- **`Quill-Weather-Setup-<version>.exe`** -- the system install: its own directory, Start Menu entry, uninstaller. Uses the shared Quill data in your Windows profile, so your weather locations are the same ones QUILL and Quill Radio see.
- **`Quill-Weather-Portable-<version>.zip`** -- extract anywhere (a USB stick included) and run `QuillWeather\QuillWeather.exe`. The bundled `data` folder keeps your locations and settings inside the app folder, so the whole thing travels.

Help > Check for Updates knows which flavor you run and downloads the matching artifact directly. **Quill Weather updates independently of Quill Radio** -- updating one never touches the other.

### A note on the SmartScreen warning (unsigned builds)

These releases are not yet code-signed, so Windows SmartScreen may warn the first time you run the installer or the portable exe. Choose **More info**, then **Run anyway**. Code signing is planned.

## Run from source

```powershell
pip install .
quill-weather
# or, with the quill package already installed:
python -m quill.apps.weather
# start hidden in the tray (as run-at-login does):
python -m quill.apps.weather --tray
# or, for quick dev testing against a local QUILL checkout:
.\run-quill-weather.bat
```

## Versioning and releases

Quill Weather carries the **same version number as Quill Radio** (2.2.0), because the two were split from one weather effort and ship the same underlying code. That shared number is a courtesy to users who run both; the two apps otherwise have **separate release cadences and separate update feeds**, so a Quill Weather release can go out without a Quill Radio release and vice versa. See `docs/release-notes-2.2.md` for what is new.
