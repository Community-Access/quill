# Quill Radio for Mac - Design

Date: 2026-07-16
Status: Approved (user, 2026-07-16)

## Purpose

A standalone macOS version of Quill Radio: the screen-reader-first internet
radio app from the QUILL project, rebuilt as a self-contained wxPython package
in this repository. It matches the Windows app's features and behavior as
closely as macOS allows, with no dependency on the `quill` package.

Sources of truth for the port:

- `S:\quill\quill\apps\radio.py` - the Windows app shell
- `S:\quill\quill\core\radio\*` - core radio logic (already cross-platform)
- `S:\quill\quill\ui\radio\*` - dialogs and player controller
- `S:\quill\quill\platform\macos\*` - existing macOS a11y helpers
- Shared infrastructure modules listed below

## Approved decisions

1. **Self-contained port.** New package `quill_radio_mac`; upstream code is
   adapted in, not imported. Roughly 8-10k lines ported.
2. **libmpv only.** The Windows default (wx.media / WMP10 backend) does not
   exist on macOS. The radio-specific mpv engine is ported with `.dylib`
   discovery added. No wx.media fallback.
3. **Dock app, close hides.** No tray. Cmd+W hides the window and playback
   continues; the Dock menu mirrors the Windows tray menu (play/stop,
   favorites, quit); Cmd+Q quits, confirming first if a recording is running.
4. **Source plus build scripts.** Runnable from source anywhere; PyInstaller
   `.app` spec and `build_mac.sh` provided; the bundle itself can only be
   built and verified on a Mac. Core-logic tests run on Windows too.

## Architecture

```
quill_radio_mac/
  __init__.py          version, app metadata
  __main__.py          python -m quill_radio_mac
  app.py               wx.App bootstrap, safe mode, single frame
  core/
    models.py          RadioStation record
    paths.py           app_data_dir(): ~/Library/Application Support/Quill
    storage.py         write_json_atomic
    favorites.py       favorites + folders store (radio_favorites.json)
    history.py         recents + all app preferences (radio_history.json)
    radio_browser.py   radio-browser.info directory client
    soma_fm.py         SomaFM channel list
    acb_media.py       bundled ACB Media stations
    triton.py          StreamTheWorld mount resolution
    icy.py             ICY StreamTitle metadata
    link_finder.py     find streams in arbitrary web pages
    now_playing.py     track-title parsing and templating
    recording.py       ffmpeg subprocess recorder
    recording_schedule.py  in-process scheduler thread
    recordings_index.py    scan of radio_recordings/
    wake_timer.py      wake-up playback watcher
    recovery.py        self-healing stream recovery chain
    audio_enhance.py   EQ/compressor filter-graph builder (mpv af string)
    ffmpeg.py          ffmpeg/ffprobe discovery (PATH, brew, bundle)
    updates.py         GitHub releases check for this repo
    tasks.py           background task manager (wx.CallAfter marshalling)
    safe_mode.py       QUILL_SAFE_MODE network refusal
  ui/
    frame.py           RadioFrame: menus, favorites tree, buttons, status bar
    player_controller.py  state machine, volume/boost/DVR, enhancements
    mpv_engine.py      ctypes libmpv client + dylib discovery
    dialog_contract.py accessible names, modal helpers, transition announces
    dialogs/           station browser, add station, favorites manager,
                       record station, recording settings, recordings manager,
                       schedule recording, wake timer, sleep timer,
                       link finder, close confirm, preferences
  platform/
    macos/
      announce.py      VoiceOver announcements (lazy pyobjc, no-op without)
      tts.py           NSSpeechSynthesizer self-voicing fallback
      sr_detect.py     VoiceOver running detection
      media_keys.py    MPRemoteCommandCenter play/pause/stop (lazy pyobjc)
      dock.py          Dock menu wiring
scripts/
  build_mac.sh         builds the .app and zip on a Mac
quill-radio-mac.spec   PyInstaller onedir spec
tests/                 pytest suite for core/ (cross-platform)
docs/                  user guide, architecture, build guide, PRD
```

## Data flow

- All persistence is JSON via atomic writes under `app_data_dir()`, which on
  macOS is `~/Library/Application Support/Quill` (overridable with
  `QUILL_DATA_DIR`; portable mode via `QUILL_PORTABLE`). File names and
  schemas are identical to Windows (`radio_favorites.json`,
  `radio_history.json`, `radio_recording_settings.json`,
  `radio_recording_schedule.json`, `radio_wake_timer.json`,
  `radio_recordings/`), so a data folder copied from a Windows machine works.
- Network and disk IO run on the task manager's worker threads; results
  marshal to the UI thread via `wx.CallAfter`. Recorder, scheduler, and wake
  watcher run daemon threads and call back the same way.
- Playback: `RadioPlayerController` owns one process-lifetime `MpvRadioEngine`
  (ctypes libmpv). Readiness polled by a 200 ms `wx.Timer` state machine.
  DVR rewind uses the demuxer cache; sound enhancements apply as a native
  mpv `af` filter string; output device routing via mpv `audio-device`.

## macOS behavior mapping

| Windows | Mac |
|---|---|
| System tray icon + menu | Dock menu (play/stop, favorites, quit) |
| Close to tray / Alt+F4 to tray | Cmd+W hides window, playback continues |
| Ctrl+... accelerators | Cmd+... (wx maps wx.ACCEL_CTRL to Cmd on mac) |
| RegisterHotKey VK_MEDIA_* | MPRemoteCommandCenter via pyobjc, no-op without |
| SAPI/UIA announcements | NSAccessibility announcement to VoiceOver; NSSpeechSynthesizer self-voice when VoiceOver is off |
| %APPDATA%\Quill | ~/Library/Application Support/Quill |
| ffmpeg.exe bundled / winget hint | `brew install ffmpeg mpv` documented; bundle dir and PATH searched; recording degrades gracefully when ffmpeg is absent |
| Installer .exe update flow | Update check opens the GitHub release page |

## Dropped from the Windows app (deliberate)

ADP assistant, unlock codes, feedback-token bug report (Help menu links to
GitHub issues instead), the wx.media engine and its localhost enhancement
relay, the ffmpeg auto-downloader, command palette host integration beyond
the app's own commands.

## Error handling

- No libmpv: startup succeeds; pressing Play shows a spoken, focused dialog
  explaining `brew install mpv` (and the bundled-dylib path); everything
  except playback still works.
- No ffmpeg: recording controls disabled with an announced reason.
- Stream failure: the recovery chain (triton -> radio-browser -> link finder)
  attempts self-healing exactly as on Windows, announcing progress.
- No pyobjc: announcements fall back to status-bar text only; media keys and
  Dock menu extras no-op. The app never crashes for a missing optional
  native dependency.
- Safe mode (`QUILL_SAFE_MODE=1`) refuses all network calls.

## Accessibility (non-negotiable, matches upstream PRD)

Every control has an accessible name; focus lands on the favorites tree at
launch; every user action produces an announcement; all dialogs go through
`show_modal_dialog` with transition announcements; VoiceOver is the primary
target, with self-voicing fallback.

## Testing

- pytest over `core/`: models round-trip, favorites/folders operations,
  history preference persistence and migration, recording command builder,
  schedule due-entry logic, wake timer windows, now-playing parsing, ICY
  parsing, triton XML parsing, link-finder HTML scanning, filter-graph
  builder, paths resolution (monkeypatched HOME), safe-mode refusal.
  These run on Windows and on macOS.
- UI and playback verified manually on a Mac per the build guide's smoke
  checklist (also shipped as `docs/mac-smoke-test.md`).

## Documentation deliverables

README (front door), docs/userguide.md (screen-reader-first user guide),
docs/architecture.md (module map, threading and a11y contracts),
docs/build-mac.md (from-source and .app builds), docs/prd.md (feature
requirements, parity table with the Windows app), CHANGELOG.md.
