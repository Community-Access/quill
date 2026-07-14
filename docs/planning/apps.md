# Standalone Companion Apps — Planning

Status: planning / not yet scoped for a release. No code changes yet.

## Idea

Radio, Podcasts, and Audio Studio are useful on their own — someone might want
to listen to internet radio or manage a podcast queue without opening the full
QUILL editor. This document explores splitting them (and possibly other
features) into standalone executables with their own menu bar and Start Menu
shortcut, while keeping them able to call back into full QUILL when the user
needs editing, dictation, or another core feature.

"Shared components" means: one small reusable shell that any of these apps
sits inside, so we're not building three (or five) one-off `wx.App`s.

## Why this is more feasible than it sounds

Checked the current module layout before writing this. The split QUILL
already has is doing most of the work for us:

- **Core logic is already wx-free and reusable.** `quill/core/radio/`,
  `quill/core/podcasts/`, and `quill/core/speech/` (Audio Studio's engine)
  contain zero `wx` imports. They're plain Python: feed readers, download
  queues, recording schedulers, ffmpeg wrappers, catalog/credits tracking.
  Nothing here is coupled to `MainFrame`.
- **The UI pieces are already parent-agnostic dialogs/controllers**, not
  MainFrame internals:
  - `quill/ui/radio/` — `StationBrowserDialog`, `AddStationDialog`,
    `RadioPlayerController`, `LinkFinderDialog`, `RecordingSettingsDialog`,
    `ScheduleRecordingDialog`.
  - `quill/ui/podcasts/` — `ManagerDialog`, `AddPodcastDialog`,
    `PodcastPlayerController`, `ChaptersDialog`, `ShowNotesDialog`, etc.
  - `quill/ui/audio_studio/` — `AudioStudioWizard` and its page panels,
    `AudioEngine`/`MpvEngine`, `PlayerPanel`.

  Every one of these takes a `wx.Window` as `parent` and otherwise only
  touches its own core module. `RadioPlayerController(self.frame, ...)` in
  `main_frame_radio.py:51-55` treats `self.frame` as nothing more than a
  parent window for child controls and modal dialogs.
- **`main_frame_radio.py` / `main_frame_podcasts.py` are thin glue**, not
  where the feature logic lives: menu item registration, keymap commands,
  status-bar mini-player, system tray integration, safe-mode gating. That's
  exactly the layer a standalone shell needs to reimplement in miniature —
  and only that layer.

Net effect: we are not extracting features out of a monolith. We're wrapping
already-decoupled features in a second, smaller frame.

## Proposed shared component: `AppShellFrame`

A new small module, e.g. `quill/ui/app_shell.py`, providing a reusable base
for any standalone companion app:

- Builds a `wx.Frame` + `wx.MenuBar` from a declarative menu spec (reuse the
  existing menu-building helpers `main_frame.py` already has, factored out
  rather than duplicated).
- Wires the same accessibility contract every QUILL dialog already follows:
  `apply_modal_ids`, `show_modal_dialog`, `set_accessible_name` from
  `quill/ui/dialog_contract.py`. A standalone app must not be a second-class
  screen-reader citizen.
- Loads the same `core.settings` / `core.keymap` so keybindings and
  preferences stay consistent between the standalone app and QUILL proper
  (one settings store, not a fork).
- Standard `Help > About`, `Help > Report a problem`, `File > Exit`.
- One shared menu command: **"Open in QUILL"** (see below).
- Respects `QUILL_SAFE_MODE` the same way `MainFrame` does.
- A reusable system-tray helper (see next section) so tray support is a
  checkbox each app turns on, not something reimplemented per app.

Each standalone app is then: `AppShellFrame` subclass + the existing
dialog/controller for that feature, hosted directly in the frame's client
area (or opened as the frame's one modal on launch) instead of as a child of
`MainFrame`.

## System tray, per app

QUILL already has a working tray icon we can lift the pattern from rather
than invent one: `_ensure_tray_icon`/`_remove_tray_icon` in `main_frame.py`
(around line 10104) create a `wx.adv.TaskBarIcon()`, set its icon/tooltip,
and bind left-double-click (restore window) and right-click (popup menu).
Two details worth carrying over as-is rather than rediscovering:

- **macOS caveat**: `wx.adv.TaskBarIcon` on macOS produces a Dock tile, not a
  menu-bar extra, so QUILL deliberately refuses tray mode there today
  (`main_frame.py:10115-10121`) and tells the user via the status bar
  instead. Each standalone app should apply the same guard rather than
  silently misbehaving on macOS.
- **Feature-scoped submenus already exist.** `_on_tray_right_click` builds
  its popup menu from small per-feature builders — `_build_radio_tray_menu`
  (`main_frame_radio.py:234`) and `_build_podcast_tray_menu` — each of which
  only touches that feature's own controller (e.g. radio's shows a
  disabled "Radio: playing <station>" line plus the same play/pause/stop
  items as the status-bar mini-player). These builders are essentially
  already "the standalone app's tray menu" — extracting them out of
  `MainFrame` into the radio/podcasts mixins (or a shared module) means the
  standalone app's tray icon is just `_build_radio_tray_menu` plus
  "Show <App>" and "Exit", with no new UI to design.
- Audio Studio is project/wizard-driven rather than a background player, so
  its tray value is smaller — mainly useful if a batch export job is running
  and the user has switched away; tray icon there could just show
  job progress and a "Show" action. Lower priority than Radio/Podcasts.

## Menu bar — going beyond the bare minimum

The per-app sketches below are a starting skeleton, not the ceiling. Once
each app has its own frame instead of living under `MainFrame`'s giant menu
bar, there's real room to make each one feel like a purpose-built app rather
than a stripped-down QUILL:

- **Now Playing / status as a first-class menu item**, not just a tray
  line — mirrors the disabled "Radio: playing <station>" pattern already
  used in the tray submenu, surfaced in the menu bar too so sighted and
  screen-reader users both get it without opening the tray.
- **Favorites/subscriptions surfaced directly in the menu**, not just behind
  a "Browse..." dialog launch — e.g. Radio's Station menu lists favorite
  stations inline for one-key switching; Podcasts' Subscriptions menu lists
  subscribed shows with unplayed-episode counts.
- **Queue/progress submenus** — Podcasts' Downloads menu showing in-flight
  download progress; Audio Studio's Jobs menu showing batch export
  progress — both apps already track this state in their core managers, so
  this is a menu that reads existing state, not new tracking.
- **Recent items** — Audio Studio's File menu gets Recent Projects; Podcasts
  gets Recently Played.

None of this needs new core functionality — `quill/core/radio/favorites.py`,
the podcast subscription store, and the download queue already hold the data
these richer menus would just be reading.

## Per-app sketch

### Radio Player (pilot candidate — smallest surface)
- Entry point: `python -m quill.apps.radio` (packaged as `Quill Radio.exe`).
- Reuses `RadioPlayerController`, `StationBrowserDialog`, favorites/recording/
  scheduling modules unchanged.
- Menu bar: Station (Browse, Add custom, Link finder, **Favorites list
  inline**), Playback (Play/Pause, Stop, **Now Playing status line**),
  Record, Help.
- Own tray icon built from `_build_radio_tray_menu` + Show/Exit.

### Podcast Manager
- Entry point: `python -m quill.apps.podcasts` (`Quill Podcasts.exe`).
- Reuses `ManagerDialog`/`PodcastPlayerController` and everything under
  `quill/core/podcasts/`.
- Menu bar: Subscriptions (Add, Import OPML, Folders, **subscribed shows
  inline with unplayed counts**), Episode (Play, Download, Notes, Chapters),
  Downloads (**in-flight queue with progress**), Help.
- Own tray icon built from `_build_podcast_tray_menu` + Show/Exit.

### Audio Studio
- Entry point: `python -m quill.apps.audio_studio` (`Quill Audio Studio.exe`).
- Reuses `AudioStudioWizard` as the main content (or launched immediately on
  startup, closing the app if the wizard is cancelled).
- Menu bar: File (New project, **Recent Projects**), Jobs (**batch export
  progress**), Help.
- Tray icon optional/lower priority here (see above) — Show + job-progress
  line only, skip on v1 if it doesn't earn its keep.

### Maybe later
Table/CSV Studio and Story Studio were both built with a similar
core/UI split and could follow the same pattern once the shell exists.
Not scoping them now — revisit after the pilot ships and we know the real
cost per app.

## Calling back into QUILL ("Open in QUILL")

Two options, ordered by how soon we could ship:

1. **v1 (simple):** "Open in QUILL" launches a normal QUILL process
   (`quill.exe`, or `python -m quill` in dev), optionally passing along
   context (e.g., a podcast episode transcript path to open as a document).
   No IPC, no shared-instance awareness. A second QUILL window opening is an
   acceptable cost for v1.
2. **v2 (nicer, more work):** if QUILL is already running, focus the existing
   window and hand it the context instead of spawning a second process. This
   needs a small local IPC mechanism (named pipe on Windows) that QUILL
   doesn't have today. Worth doing only if user feedback says the double-open
   in v1 is actually annoying.

Recommend starting with v1 and treating v2 as a follow-up, not a blocker.

## Packaging / distribution

- New Start Menu shortcuts per app via the Inno Setup script (generator, not
  the checked-in `.iss` — see `project_release_version_mechanics` /
  `project_build_tools` conventions: edit the `.iss` generator, ISCC at
  `C:\Users\jeffb\AppData\Local\Programs\Inno Setup 6\ISCC.exe`).
- Portable build: each app also needs a portable-mode entry point consistent
  with the existing portable launcher design (`docs/design/portable-launcher.md`).
- Each new top-level frame is a new surface for the dialog-inventory gate
  (`dialog_inventory.py`) and likely wants at least smoke coverage in the UIA
  regression suite eventually — not required for the planning phase, but
  should be budgeted into the estimate for whichever app ships first.

## Open questions (need a decision before implementation starts)

1. **Scope for v1**: just Radio (smallest, cleanest pilot), or ship Radio +
   Podcasts together since they share the most shell code?
2. **Settings/data contention**: if the standalone Podcast app and full QUILL
   both run at once, both read/write the same podcast subscription store.
   `write_json_atomic` already makes individual writes safe, but simultaneous
   *feature* use (e.g., both apps downloading the same episode) isn't
   designed for yet — worth a short concurrency review before Podcasts ships
   standalone, less of a concern for Radio (no shared queue state) or Audio
   Studio (project-file based, one project open at a time already).
3. **Branding**: do these ship as "Quill Radio" / "Quill Podcasts" /
   "Quill Audio Studio" (recommended — reinforces they're part of the QUILL
   family and legitimizes "Open in QUILL"), or fully independent branding?
4. **Naming/location of the shell module**: proposed `quill/ui/app_shell.py`
   + a new `quill/apps/` package for the thin per-app entry points — open to
   a different layout if it fits existing conventions better.

## Suggested phasing

1. Build `AppShellFrame` + ship Radio Player standalone as the pilot (small
   surface, proves the shell, cheapest to validate end-to-end including
   accessibility and packaging).
2. Apply learnings from the pilot to Podcast Manager.
3. Apply to Audio Studio.
4. Revisit "maybe others" (Table/CSV Studio, Story Studio) only after the
   shell has shipped for all three above and the real per-app cost is known.

## Effort (qualitative, not a real estimate yet)

Low-risk relative to a typical QUILL feature, because the hard part (feature
logic decoupled from `MainFrame`) is already done, and the two additions
requested here (tray icons, richer menus) both ride on existing patterns and
existing state rather than new mechanisms: the tray icon is the same
`wx.adv.TaskBarIcon` call `MainFrame` already makes, and the richer menu
items (favorites, subscriptions, queues, recents) just read data the core
managers already track. Main unknowns are packaging/installer plumbing and
how much dialog-inventory/UIA test coverage each new top-level frame needs —
both answerable during the Radio Player pilot rather than needing more
research up front.
