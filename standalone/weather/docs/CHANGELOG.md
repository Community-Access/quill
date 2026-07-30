# Changelog

All notable changes to Quill Weather are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **The QuillVille Runtime -- install Python once, and every Quill app starts instantly.** Every QuillVille app (QUILL, Quill Radio, Quill Weather, and QUILL Audio Studio) now shares one Python runtime, the QuillVille Runtime, installed once per user and reused by all of them. Install it a single time and every app you add afterward launches immediately. The runtime is reference-counted: it is removed only when the last app that needs it is uninstalled. Alongside the existing full portable and full installer builds, two new lightweight editions arrive that ride the shared runtime:
  - **Companion edition** (`Quill-Weather-Companion-<version>.zip`, about 2 MB) -- feather-light: just the app and its docs. The first time you launch it, if the QuillVille Runtime is not already installed, it offers to download and install it (about 230 MB, once) with a fully accessible progress bar; after that, this app and every other QuillVille app start instantly.
  - **Thin installer** (the `-Lite` setup) -- a tiny installer that downloads the shared runtime only if it is not already present, then installs the app.
  - The **full portable** edition (`Quill-Weather-Portable-<version>.zip`, about 82 MB) is fully self-contained: it runs from a USB stick with no installation and no internet, bundling a genuine, unmodified copy of Python. Weather is a small app, so this build is already compact. The **full installer** (`Quill-Weather-Setup-Shared-<version>.exe`) installs the shared runtime, if it is not already present, plus the app.
- **Accessible runtime downloads.** Whenever the QuillVille Runtime is downloaded -- by an installer or by an app's own first launch -- it shows a fully accessible progress bar that works with NVDA, JAWS, and Narrator, announcing progress as a percentage.
- **Fewer antivirus false positives.** The app's launcher is now a genuine, tiny native program, and the bundled Python is the official unmodified build. Earlier versions used a renamed and modified copy of Python's `pythonw.exe` as the launcher, which some antivirus tools flagged as a false positive. That pattern is completely gone, so the Quill apps are far less likely to be flagged.

## [2.2.0] - 2026-07-23

First standalone release: the QUILL weather feature set as a self-contained, screen-reader-first Windows app. Quill Weather began inside Quill Radio's Weather menu; 2.2.0 is the moment it stands on its own, with its own process, tray icon, installer, and update feed. It carries the same version number as Quill Radio because the two run the exact same weather code, but they release independently.

### Added

- Standalone Quill Weather app: a small home window (monitoring status plus Open Weather Center, Toggle Monitoring, and Add Location buttons), a menu bar, a system tray, and single-instance behavior (IPC slot `weather`) so it runs alongside QUILL, Quill Radio, and QUILL Audio Studio.
- Weather Monitoring (Weather Guardian): watches your location's official National Weather Service watches, warnings, and advisories and speaks each new one the instant it is issued, interrupting speech for the most serious events (tornado, flash flood) and announcing the all-clear. Keeps watching while minimized to the tray, resumes on launch, and drops a tray notification for each new alert; it checks as often as once a minute while a warning is live and eases off when the sky clears.
- Alerts even when nothing is running: closing the window keeps the watch going in the tray; Options > Start Quill Weather with Windows begins the watch at sign-in with no window; and Options > Check for alerts in the background registers a Windows scheduled task that checks on your interval and raises a toast even with no Quill Weather process running.
- The Weather Center (Weather Now, Ctrl+Shift+W): active alerts with full official instructions, a warm current-conditions paragraph, an hour-by-hour forecast, the National Weather Service period forecast, and an extended daily outlook of up to 16 days -- all arrow-navigable, copyable text written for speech. Includes moon phase and illumination (computed locally), and a two-clock time summary that grounds a far-off forecast in local time here and there plus when the reading was taken.
- Quick Weather (Ctrl+Shift+Q): a one-line spoken summary of your primary location without opening a window. Active Alerts (Weather menu) opens the Weather Center with focus already on the alerts list.
- A configurable alert sounder: silence it, choose your own `.wav` (with Play and Use Default), and set how many times it repeats (1 to 10). Test Alert rehearses the whole experience -- words, sound, tray toast, and alert window -- clearly marked as a test, sending nothing over the internet.
- Global show/hide hotkey Ctrl+Alt+Shift+W: a system-wide chord that hides the window to the tray (monitoring keeps running) or restores and focuses it, from any app, speaking "hidden to the tray" or "shown". Unique to Quill Weather within the family (QUILL uses Ctrl+Alt+Shift+Q, Quill Radio uses Ctrl+Alt+Shift+R); Windows-only and best-effort.
- Feature customization (Options > Customize Features...): switch whole areas -- Alert Monitoring, NOAA Weather Radio -- on or off, removing their menus.
- Sibling interoperability: File > Open Quill Radio and File > Open QUILL (also in the tray) launch a sibling in its own window; on one machine all apps share a data store, so a location saved in one is there in the others.
- Your local NOAA Weather Radio: finds the transmitter covering your saved location and, with Quill Radio installed for playback, plays it; the full directory (1,035 transmitters) ships inside the app for offline lookup.
- Independent distribution and updates: its own installer, portable build, and update feed. Help > Check for Updates knows whether you run the installer or the portable build and downloads the matching one.
