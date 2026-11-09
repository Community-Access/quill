# Quill Weather 2.2.1 — Release Notes

*Version 2.2.1, the beta, November 2026. Help > About shows the exact build
you have.*

Quill Weather now calls a saved place by the friendly name you gave it. If you
save one place as **Home** and another as **Summer Home**, Current conditions and
Quick Weather name the right place instead of leading with a ZIP code, town, or
county. The local-time sentence uses that name too. If you leave the friendly
name empty, Weather continues to use the place name from the search result.

## What you'll notice

- **Friendly names throughout weather reports.** The Location chooser, loading
  message, current conditions, Quick Weather, local-time sentence, and alert
  monitoring now consistently use your saved name.
- **Settings tell you what happened.** If Windows refuses a startup or
  background task change, or Weather cannot save a tray preference, the menu
  reflects the actual state and Weather explains the problem.
- **Tutorials and commands.** Help > Tutorials opens guided lessons. Weather
  commands are also available by name in the Command Palette.
- **Results you can revisit.** Help > Activity (Shift+F9) lists recent results
  and any available retry. Help > Repeat Last Result (F9) speaks the latest
  important result again, as in the other Quill apps.
- **Show and hide key by choice.** Weather no longer reserves a system-wide key
  by default. Choose one under File > Show and Hide Key if you want it.
- **Your own sounds, where you want them.** **Options > App Sounds Play On...**
  (Ctrl+Shift+S) sends Weather's own sounds to the system default, any sound
  card or headset by name, or nowhere; **Alt+Shift+M** turns them off and on.
- **QUILL Transcribe on the QuillVille menu.** The QuillVille menu and the tray
  list QUILL Transcribe, new this month: it types what you say into any program.

## Under the hood

- **Sharp at any display scaling.** Quill Weather handles each monitor's
  scaling itself, so text stays sharp at 125, 150 and 200 percent, and the
  Weather Center's status line has a spoken name.
- **Two complete editions.** This release has a self-contained portable ZIP and
  a shared-runtime installer. The installer includes the runtime it needs; the
  portable ZIP keeps settings and saved places in its own `data` folder. Neither
  edition needs a first-launch runtime download.
- **A cleaner Windows install.** The installer runs per user without an
  administrator prompt and records Weather's own installed version, so About
  and Check for Updates do not mistake another app's runtime version for yours.
- **Portable copies stay portable.** A portable copy does not add a Windows
  startup entry or a scheduled background task. Install Weather to use those
  two Windows features. The portable launcher runs fully offline.
- **Updates follow your edition.** Check for Updates offers the portable ZIP to
  a portable copy and the shared installer to an installed copy. The shared
  installer is checked against current Weather code during the build.
- **A distinct Weather icon.** The sun-and-cloud icon distinguishes Weather
  from Radio in the taskbar, tray, and Alt+Tab.
- **What's New.** Help > What's New (Ctrl+Shift+F1) opens the changelog in your
  browser, on the same key as every other QuillVille app. Help also has the
  Command Palette (Ctrl+Shift+P) and Product Requirements (Alt+Shift+F1).

## AI, when you ask for it

Quill Weather now has an AI (artificial intelligence) menu (Alt+I), and it does nothing until you use it.

- **Should I Go Out?** (Ctrl+Shift+G) answers in plain words from the forecast
  for your primary place. Any active alert comes first, in the Weather
  Service's own words; the AI never rewords one.
- **Ask** (Ctrl+Shift+8) lets you ask about the forecast. Your place's name
  goes with the question, never its coordinates.
- **Choose Your AI** (Ctrl+Shift+F8) picks the free AI, your ChatGPT
  subscription (Alt+F5) or your own key (Alt+F2). A line in the main window
  says which AI is in use; press Enter on it to change it.
- Text only: no radar or maps. The alert watch never uses AI, nothing runs on
  a timer, and Safe Mode turns every AI command off.

## Download and install

- `Quill-Weather-Portable-2.2.1.zip`: extract it and run
  `QuillWeather\QuillWeather.exe` from the extracted folder.
- `Quill-Weather-Setup-Shared-2.2.1.exe`: run the installer for a Start Menu
  entry, uninstaller, and shared QuillVille Runtime.

Your existing saved locations keep their names when you update. Quill Weather
and Quill Radio share weather features but update independently.

For setup and everyday use, open **Help > User Guide**. The previous release's
notes remain in `release-notes-2.2.md`.
