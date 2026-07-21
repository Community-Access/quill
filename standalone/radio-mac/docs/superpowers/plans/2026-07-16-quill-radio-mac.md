# Quill Radio for Mac Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `quill_radio_mac`, a standalone macOS wxPython port of Quill Radio, in S:\qrm, by adapting the upstream `quill` sources with macOS replacements for the Windows-only surface.

**Architecture:** Self-contained package mirroring upstream layout (`core/` wx-free logic, `ui/` wx dialogs and player, `platform/macos/` lazy-pyobjc native helpers). Playback is libmpv-only via the ported radio mpv engine. Data lives in `~/Library/Application Support/Quill` with the exact upstream JSON file names and schemas.

**Tech Stack:** Python 3.11+, wxPython 4.2+, ctypes libmpv, ffmpeg subprocess, lazy pyobjc (optional), pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-16-quill-radio-mac-design.md`. Read it before any task.
- This is a PORT. Upstream files under `S:\quill\quill\...` are the source of truth for behavior. Read the upstream file fully before writing its port. Keep logic, announcements, and dialog copy identical unless a rule below says otherwise.
- Import mapping (apply mechanically everywhere):
  - `quill.core.radio.<m>` -> `quill_radio_mac.core.<m>`
  - `quill.core.error_codes` -> `quill_radio_mac.core.error_codes`
  - `quill.core.safe_xml` -> `quill_radio_mac.core.safe_xml`
  - `quill.core.audio_enhance` -> `quill_radio_mac.core.audio_enhance`
  - `quill.core.speech.ffmpeg` -> `quill_radio_mac.core.ffmpeg`
  - `quill.stability.redaction` -> `quill_radio_mac.core.redaction`
  - `quill.stability.task_manager` -> `quill_radio_mac.core.tasks`
  - `quill.core.paths` -> `quill_radio_mac.core.paths`
  - `quill.core.storage` / `storage_mode` -> `quill_radio_mac.core.storage`
  - `quill.core.updates` -> `quill_radio_mac.core.updates`
  - `quill.ui.dialog_contract` -> `quill_radio_mac.ui.dialog_contract`
  - `quill.ui.accessible_names` -> `quill_radio_mac.ui.accessible_names`
  - `quill.ui.audio_studio.mpv_engine` -> `quill_radio_mac.ui.mpv_client`
  - `quill.ui.radio.mpv_radio_engine` -> `quill_radio_mac.ui.mpv_engine`
  - `quill.ui.radio.player_controller` -> `quill_radio_mac.ui.player_controller`
  - `quill.ui.radio.<dialog module>` -> `quill_radio_mac.ui.dialogs.<same name>`
  - `from quill import __version__` -> `from quill_radio_mac import __version__`
  - `quill.platform.macos.<m>` -> `quill_radio_mac.platform.macos.<m>`
- If a ported module imports a small upstream helper not listed above, vendor it: copy the needed function(s) into the most fitting `quill_radio_mac.core` module (or `quill_radio_mac.core.util` if nothing fits) with an attribution comment naming the upstream module. Never import `quill`.
- Dropped entirely (do not port, remove call sites): ADP mixin, unlock codes, feedback token / Report a Bug token flow, command palette, `WxMediaEngine` and `EnhanceRelay` (wx.media path), ffmpeg auto-downloader (`ffmpeg_install`), all `quill.platform.windows.*`.
- Keep existing `os.name == "nt"` guards (`CREATE_NO_WINDOW` etc.) — they are harmless no-ops on macOS and keep diffs against upstream small.
- User-Agent strings: replace `Quill/...` with `QuillRadioMac/{__version__}`.
- Preserve upstream module docstrings and enrich them: every module gets a rich docstring stating purpose, threading contract, and macOS notes. Every public class/function keeps or gains a docstring. Documentation quality is an explicit deliverable.
- Accessibility is non-negotiable: keep every `set_accessible_name`, announcement, and `show_modal_dialog` call. Never remove an announcement to simplify.
- ASCII-only output in UI strings and docs (screen reader user; no emoji, no decorative Unicode).
- Tests: pytest, under `tests/`, must pass on Windows (`python -m pytest tests -q`). Monkeypatch `HOME`/platform where needed. No network in tests.
- Do NOT create git commits (user rule). Leave changes in the working tree.
- Python floor 3.11. wxPython floor 4.2. No new runtime dependencies beyond wxPython; pyobjc is optional (lazy imports only).

---

### Task 1: Scaffold and core foundation

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `LICENSE` (copy `S:\quill-radio\LICENSE`, MIT)
- Create: `quill_radio_mac/__init__.py`, `quill_radio_mac/__main__.py`
- Create: `quill_radio_mac/core/__init__.py`, `core/paths.py`, `core/storage.py`, `core/error_codes.py`, `core/redaction.py`, `core/tasks.py`, `core/models.py`
- Test: `tests/test_paths.py`, `tests/test_storage.py`, `tests/test_models.py`

**Upstream sources to read and port:**
- `S:\quill\quill\core\paths.py` (rewrite: see below)
- `S:\quill\quill\core\storage.py` (port `write_json_atomic` and whatever it needs)
- `S:\quill\quill\core\error_codes.py` (port `CodedError` and only the error codes the radio modules use)
- `S:\quill\quill\stability\redaction.py` (port `format_args_for_log` only)
- `S:\quill\quill\stability\task_manager.py` (port `TaskManager`)
- `S:\quill\quill\core\radio\models.py` (port verbatim, including `_coerce_int`)

**Interfaces (later tasks rely on):**
- `quill_radio_mac.__init__`: `__version__ = "1.0.0"`, `APP_NAME = "Quill Radio"`, `APP_DISPLAY_NAME = "Quill Radio for Mac"`, `GITHUB_OWNER = "Community-Access"`, `GITHUB_REPO = "quill-radio-mac"`
- `core.paths.app_data_dir() -> Path` and `core.paths.recordings_dir() -> Path`
- `core.storage.write_json_atomic(path: Path, payload: Any) -> None`
- `core.error_codes.CodedError(code: str, message: str)` matching upstream signature
- `core.tasks.TaskManager` with the upstream `submit(...)` API
- `core.models.RadioStation` with upstream `to_dict()/from_dict()`

- [ ] **Step 1: Write `pyproject.toml`** — setuptools project `quill-radio-mac`, `requires-python = ">=3.11"`, dependency `wxPython>=4.2`, optional extra `macos = ["pyobjc-framework-Cocoa", "pyobjc-framework-MediaPlayer"]`, dev extra `["pytest"]`, console script `quill-radio-mac = quill_radio_mac.app:main`, gui-script equivalent.
- [ ] **Step 2: Write package init and `__main__`** (`from quill_radio_mac.app import main; main()` guarded so importing the package never imports wx).
- [ ] **Step 3: Write failing tests for `app_data_dir`:**

```python
def test_app_data_dir_macos(monkeypatch, tmp_path):
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE", raising=False)
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "Library" / "Application Support" / "Quill"

def test_app_data_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "custom"))
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "custom"
```

- [ ] **Step 4: Implement `core/paths.py`.** Resolution order: `QUILL_DATA_DIR` env -> portable mode (`QUILL_PORTABLE=1`: `data/` beside `QUILL_APP_ROOT` or the executable) -> platform default: darwin `~/Library/Application Support/Quill`, win32 `%APPDATA%\Quill` (kept so tests and dev on Windows work), else `~/.local/share/Quill`. `app_data_dir()` creates the directory. `recordings_dir()` = `app_data_dir()/"radio_recordings"`.
- [ ] **Step 5: Port `storage.py`, `error_codes.py`, `redaction.py`, `tasks.py`, `models.py`** per the mapping. Write round-trip tests for `RadioStation` and an atomic-write test (write over existing file, content replaced, no `.tmp` left behind).
- [ ] **Step 6: Run `python -m pytest tests -q`** — expect all pass.

### Task 2: Sound enhancement graph, favorites, history

**Files:**
- Create: `quill_radio_mac/core/audio_enhance.py`, `core/favorites.py`, `core/history.py`
- Test: `tests/test_audio_enhance.py`, `tests/test_favorites.py`, `tests/test_history.py`

**Upstream:** `S:\quill\quill\core\audio_enhance.py` (port `EQ_PRESETS`, `clamp_eq_gain`, `build_filter_graph`, `EnhanceError`; DROP `EnhanceRelay` and every subprocess/HTTP-relay piece), `core\radio\favorites.py`, `core\radio\history.py` (both near-verbatim).

**Interfaces:** `build_filter_graph(...)` keeps the upstream signature (the mpv engine passes its output as the `af` property). `RadioFavoritesStore(path)` and `RadioHistory(path)` keep upstream constructor and method names, including `RadioHistory` preference attributes (`resume_on_launch`, `close_action`, `playback_engine`, `volume_boost`, `output_device`, `eq_bass_db`, `eq_mid_db`, `eq_treble_db`, `compressor_enabled`, `mono`, `night_mode`, `now_playing_template`, `announce_track_titles`, `check_updates_on_startup`, `last_update_check`, `recover_from_website`, `announce_dialog_transitions`, plus the `eq_preset` migration).

- [ ] Step 1: Tests first — filter-graph string for a known EQ/compressor combo (copy expected value by running the upstream function mentally from its source), favorites add/remove/folders round-trip through a tmp JSON file, history dedup and `eq_preset` migration.
- [ ] Step 2: Port the three modules. In `history.py`, drop `playback_engine` values that reference wx ("wx" stays accepted on load but normalizes to "auto" with a docstring note — mac build is mpv-only).
- [ ] Step 3: `python -m pytest tests -q` — pass.

### Task 3: Recording stack

**Files:**
- Create: `quill_radio_mac/core/ffmpeg.py`, `core/recording.py`, `core/recording_schedule.py`, `core/wake_timer.py`, `core/recordings_index.py`
- Test: `tests/test_recording.py`, `tests/test_schedule.py`, `tests/test_wake_timer.py`, `tests/test_recordings_index.py`

**Upstream:** `core\speech\ffmpeg.py` (adapt), `core\radio\recording.py`, `recording_schedule.py`, `wake_timer.py`, `recordings_index.py` (near-verbatim).

**macOS adaptation in `ffmpeg.py`:** search order — `QUILL_FFMPEG` env, bundle dir (`{QUILL_APP_ROOT}/tools/ffmpeg`), `<data>/engine-packs/ffmpeg`, PATH via `shutil.which`, Homebrew fallbacks `/opt/homebrew/bin` and `/usr/local/bin`. Binary names: `ffmpeg`/`ffprobe`, plus `.exe` variants when `os.name == "nt"`. `INSTALL_HINT = "Install FFmpeg with Homebrew: brew install ffmpeg"`.

**Interfaces:** `find_ffmpeg() -> str | None`, `find_ffprobe() -> str | None`, `ffmpeg_available() -> bool`, `INSTALL_HINT: str`; `RadioRecorder`, `RecordingSettings`, `RecordingError`, `RECORD_FORMATS`, `build_record_command` all upstream-shaped.

- [ ] Step 1: Tests first — `build_record_command` golden commands for mp3/copy/duration-cap cases (derive expected argv from upstream source), schedule due-entry logic across once/daily/weekly with `last_fired_date`, wake-timer 5-minute window, recordings-index scan of a tmp dir.
- [ ] Step 2: Port modules; keep `Popen` + stdin `b"q"` stop, part-N reconnect files, `os.name == "nt"` guards.
- [ ] Step 3: ffmpeg discovery tests with monkeypatched env/PATH. Run suite — pass.

### Task 4: Station sources and metadata

**Files:**
- Create: `quill_radio_mac/core/safe_xml.py`, `core/radio_browser.py`, `core/soma_fm.py`, `core/acb_media.py`, `core/triton.py`, `core/icy.py`, `core/link_finder.py`, `core/now_playing.py`, `core/recovery.py`
- Test: `tests/test_station_sources.py`, `tests/test_now_playing.py`, `tests/test_link_finder.py`

**Upstream:** the same-named files under `core\radio\` plus `core\safe_xml.py`. All near-verbatim; replace User-Agent per global rule; vendor any safe-mode helper they use.

- [ ] Step 1: Tests first — triton XML parsing from a canned provisioning document, ICY `StreamTitle` extraction from canned bytes, link-finder scan of a canned HTML page (audio/source/anchor/iframe variants), now-playing template formatting, ACB station table integrity (10 stations, https URLs), radio-browser search-parameter building (no network).
- [ ] Step 2: Port all nine modules.
- [ ] Step 3: Run suite — pass.

### Task 5: Update checker

**Files:**
- Create: `quill_radio_mac/core/updates.py`
- Test: `tests/test_updates.py`

**Upstream:** `core\updates.py`. Adapt: repo comes from `GITHUB_OWNER`/`GITHUB_REPO`; keep `fetch_releases`, `is_newer_version`; the mac flow does not download installers — expose `latest_release_page_url(release) -> str` instead of the asset-download/installer path.

- [ ] Step 1: Tests — `is_newer_version` matrix (1.0.0 vs 1.0.1, prerelease tags, equal), release-page URL extraction from a canned GitHub API payload.
- [ ] Step 2: Port and adapt. Run suite — pass.

### Task 6: macOS platform layer

**Files:**
- Create: `quill_radio_mac/platform/__init__.py`, `platform/macos/__init__.py`, `platform/macos/announce.py`, `platform/macos/tts.py`, `platform/macos/sr_detect.py`, `platform/macos/media_keys.py`, `platform/macos/dock.py`
- Test: `tests/test_platform_noop.py`

**Upstream:** `S:\quill\quill\platform\macos\announce.py`, `tts.py`, `sr_detect.py` — port verbatim (they are already lazy-pyobjc and no-op cleanly off-mac).

**New code — `media_keys.py`:** register `MPRemoteCommandCenter` play/pause/stop/toggle handlers via lazy pyobjc:

```python
def register_media_keys(on_play_pause, on_stop) -> bool:
    """Route the Mac media keys (F8 play/pause) to the radio.

    Uses MPRemoteCommandCenter via pyobjc. Returns False (and stays
    inert) when pyobjc or the MediaPlayer framework is unavailable, or
    when not running on macOS. Handlers are called on the main thread.
    """
    import sys
    if sys.platform != "darwin":
        return False
    try:
        import MediaPlayer  # type: ignore[import-not-found]
    except ImportError:
        return False
    center = MediaPlayer.MPRemoteCommandCenter.sharedCommandCenter()
    ...
```

Also `set_now_playing_info(title, station)` updating `MPNowPlayingInfoCenter` (best-effort), and `clear_media_keys()`.

**New code — `dock.py`:** `set_dock_menu(entries)` where entries are `(label, callback)` or `None` separators, built with `NSMenu`/`NSMenuItem` and installed via the `applicationDockMenu_` pattern (or `NSApp.setDockMenu_` equivalent through pyobjc); lazy, no-op off-mac. Document that wx's Dock integration is bypassed deliberately.

- [ ] Step 1: Port the three upstream modules with enriched docstrings.
- [ ] Step 2: Write `media_keys.py` and `dock.py` per the sketches; every public function returns a usable value off-mac (False/None) and never raises for missing pyobjc.
- [ ] Step 3: Tests — importing every platform module on Windows succeeds; `register_media_keys`, `announce`, `speak_announcement`, `set_dock_menu` all return falsy/no-op on Windows. Run suite — pass.

### Task 7: UI foundation — accessibility contract, mpv client, engine, player controller

**Files:**
- Create: `quill_radio_mac/ui/__init__.py`, `ui/accessible_names.py`, `ui/dialog_contract.py`, `ui/mpv_client.py`, `ui/mpv_engine.py`, `ui/player_controller.py`
- Test: `tests/test_mpv_discovery.py`, `tests/test_player_states.py`

**Upstream:** `ui\accessible_names.py`, `ui\dialog_contract.py` (port; keep darwin branches, drop Windows-only branches that import `quill.platform.windows`), `ui\audio_studio\mpv_engine.py` -> `ui/mpv_client.py`, `ui\radio\mpv_radio_engine.py` -> `ui/mpv_engine.py`, `ui\radio\player_controller.py`.

**Adaptations:**
- `mpv_client.find_libmpv`: library name list becomes `("libmpv.2.dylib", "libmpv.dylib", "libmpv-2.dll", "mpv-2.dll", "libmpv.dll", "libmpv.so.2", "libmpv.so")`; search order `QUILL_LIBMPV` env (file or dir) -> `{QUILL_APP_ROOT}/Frameworks` and `{QUILL_APP_ROOT}/tools/mpv` -> `<data>/engine-packs/mpv` -> beside the executable -> Homebrew `/opt/homebrew/lib` and `/usr/local/lib` -> bare `ctypes.util.find_library("mpv")`.
- `player_controller.py`: remove `WxMediaEngine`, `EnhanceRelay`, and `_attempt_engine_fallback`; engine selection collapses to "mpv or a spoken, actionable error". The no-libmpv error message must include `brew install mpv` and the `QUILL_LIBMPV` override. Keep the `RadioPlayerState` machine, DVR, boost, per-station enhancement resolution, and the RadioBrowser click-vote thread exactly.
- Preferences engine labels: replace "Windows Media (classic)" wording; the engine choice control disappears (mpv-only) but `output_device` selection stays.

**Interfaces:** `RadioPlayerController` keeps upstream public API (`play_station`, `stop`, `toggle_mute`, `set_volume`, `volume_up/down`, `set_boost`, `dvr_rewind/forward/jump_to_live`, `state`, `now_playing_title`, callbacks). Later tasks (frame, dialogs) call exactly these.

- [ ] Step 1: Port `accessible_names.py` + `dialog_contract.py`; keep `set_accessible_name`, `show_modal_dialog`, `apply_modal_ids`, `focus_primary_control`, `set_transition_announcement_policy`, macOS OK/Cancel button order logic.
- [ ] Step 2: Port `mpv_client.py` with the discovery change; tests monkeypatch env/dirs and assert candidate ordering without loading a real library.
- [ ] Step 3: Port `mpv_engine.py` (verbatim plus docstrings) and `player_controller.py` (adaptations above). State-machine tests exercise `next_poll_action` transitions with a stubbed client (no libmpv needed).
- [ ] Step 4: Run suite on Windows — pass (wx imports fine; nothing constructs a wx.App in tests).

### Task 8: Dialogs A — finding stations

**Files:**
- Create: `quill_radio_mac/ui/dialogs/__init__.py`, `ui/dialogs/station_browser_dialog.py`, `ui/dialogs/add_station_dialog.py`, `ui/dialogs/link_finder_dialog.py`

**Upstream:** same names under `ui\radio\`. Near-verbatim ports: import mapping, enriched docstrings, keep every accessibility call. `station_browser_dialog` keeps the RadioBrowser + SomaFM + ACB blend, search-as-you-type, and context menu.

- [ ] Step 1: Port all three.
- [ ] Step 2: Add `tests/test_ui_imports.py` importing every `quill_radio_mac.ui.dialogs` module (import-time safety only, no wx.App). Run suite — pass.

### Task 9: Dialogs B — favorites, recording, timers, preferences

**Files:**
- Create: `ui/dialogs/favorites_manager_dialog.py`, `ui/dialogs/favorite_actions.py`, `ui/dialogs/record_station_dialog.py`, `ui/dialogs/recording_settings_dialog.py`, `ui/dialogs/recordings_manager_dialog.py`, `ui/dialogs/schedule_recording_dialog.py`, `ui/dialogs/wake_timer_dialog.py`, `ui/dialogs/close_confirm_dialog.py`, `ui/dialogs/sleep_timer.py`, `ui/dialogs/preferences_dialog.py`

**Upstream:** same names under `ui\radio\`; `ui\media_sleep_timer.py` + `ui\sleep_timer_dialog.py` merge into `ui/dialogs/sleep_timer.py` (controller + dialog); `ui\app_preferences_dialog.py` -> `preferences_dialog.py`.

**Adaptations:** `recordings_manager_dialog` "show in folder" uses `open -R` on darwin (upstream already branches — keep) and `explorer /select,` on nt. `close_confirm_dialog` copy changes from tray wording to Mac wording: options become "Hide window (keep playing)", "Quit Quill Radio", checkbox "Remember my choice"; the stored `close_action` values stay `minimize`/`exit`/`ask` for data compatibility. `preferences_dialog` drops the playback-engine choice, keeps output device, resume on launch, announce track titles, update check, now-playing template, dialog transition announcements, close action.

- [ ] Step 1: Port favorites + favorite_actions + record/recording settings/recordings manager.
- [ ] Step 2: Port schedule, wake timer, close confirm, sleep timer, preferences.
- [ ] Step 3: Extend `tests/test_ui_imports.py` to cover all dialog modules. Run suite — pass.

### Task 10: App frame and bootstrap

**Files:**
- Create: `quill_radio_mac/ui/frame.py`, `quill_radio_mac/app.py`

**Upstream to read (all of it, carefully):** `apps\radio.py` (`RadioAppFrame` + panel + menus + tree handling), `ui\main_frame_radio.py` (`RadioMixin`), `ui\app_shell.py` (`AppShellFrame`), `ui\main_frame_media_sleep_timer.py`.

**Shape:** one class `RadioFrame(wx.Frame)` in `frame.py` merging the four upstream layers, minus dropped features (ADP, unlock codes, palette, feedback token, tray icon, RegisterHotKey, Get-FFmpeg, open-in-quill, exe-icon loading). Keep: menu bar (Station / Playback / Record / Help), all accelerators via `wx.ACCEL_CTRL` (wx maps to Cmd on mac — document this), favorites TreeCtrl with folders and Enter/Delete/F2/arrow handling, status-bar mini player, now-playing poller, self-healing recovery, wake watcher, scheduler, sleep timer, resume-last-station, startup update check (throttled daily, opens release page), preferences, announcements through `platform.macos.announce` -> `tts` fallback with status-bar text always set.

**Mac behavior (new code):**
- `EVT_CLOSE`: honor `history.close_action` — `ask` shows `RadioCloseConfirmDialog`; `minimize` hides the window (`self.Hide()`, playback continues, announce "Quill Radio is still playing. Use the Dock to reopen."); `exit` quits. Cmd+Q (`wx.ID_EXIT` / `OnExit`) always quits, confirming first when a recording is active.
- Reopen from Dock: bind `wx.EVT_ACTIVATE_APP` in `app.py`; on activate with hidden frame, `Show()` + `Raise()` + focus favorites tree.
- Dock menu via `platform.macos.dock.set_dock_menu`: Play/Stop toggle, up to 10 favorites, separator, Quit. Rebuild when favorites change or playback state changes.
- Media keys via `platform.macos.media_keys.register_media_keys(self.toggle_play, self.stop)`; update `set_now_playing_info` when the station or title changes.
- `app.py` `main()`: reads `QUILL_SAFE_MODE`, sets mac menu conventions (`wx.MenuBar.MacSetCommonMenuBar` not needed; ensure About/Preferences/Quit land in the app menu via standard wx ids `wx.ID_ABOUT`, `wx.ID_PREFERENCES`, `wx.ID_EXIT`).

- [ ] Step 1: Port the merged `RadioFrame` (largest single step; keep upstream method names so diffs are auditable).
- [ ] Step 2: Write `app.py` bootstrap.
- [ ] Step 3: Add `tests/test_frame_import.py` (import `quill_radio_mac.ui.frame` and `quill_radio_mac.app`; assert `main` exists; no wx.App construction). Run full suite — pass.
- [ ] Step 4: On Windows, run `python -c "import quill_radio_mac.app"` as a smoke check.

### Task 11: Packaging

**Files:**
- Create: `quill-radio-mac.spec` (PyInstaller onedir -> .app), `scripts/build_mac.sh`, `run-from-source.command`, `assets/README.md` (icon placeholder instructions: `QuillRadio.icns`)

**Content:** spec bundles the package, optional `Frameworks/libmpv.dylib` and `tools/ffmpeg` when present at build time (warn, do not fail, when absent — document that brew-installed system copies work too); `BUNDLE` step produces `Quill Radio.app` with `CFBundleIdentifier com.communityaccess.quillradio`, `NSHumanReadableCopyright`, `LSApplicationCategoryType public.app-category.music`. `build_mac.sh`: venv, pip install, pytest, pyinstaller, zip artifact. `run-from-source.command`: chmod-friendly double-click launcher.

- [ ] Step 1: Write all four files with rich comments; mark clearly that they are verified on macOS only.
- [ ] Step 2: `bash -n scripts/build_mac.sh` and `bash -n run-from-source.command` for syntax. Suite still green.

### Task 12: Documentation

**Files:**
- Create: `README.md`, `docs/userguide.md`, `docs/architecture.md`, `docs/build-mac.md`, `docs/prd.md`, `docs/mac-smoke-test.md`, `CHANGELOG.md`

**Content requirements:**
- `README.md`: what it is, relationship to QUILL and Quill Radio for Windows (explicitly: an adapted standalone port, not the upstream wrapper model), install (brew deps, pip, .app), run, docs index. Tone and structure modeled on `S:\quill-radio\README.md`.
- `docs/userguide.md`: screen-reader-first walkthrough — first launch, favorites tree, station browser, recording, schedules, wake timer, sleep timer, sound enhancements, DVR, preferences, every keyboard shortcut in a table (Cmd equivalents), VoiceOver notes.
- `docs/architecture.md`: module map, threading contract (UI thread + TaskManager + daemon threads + `wx.CallAfter`), a11y contract, playback state machine, persistence schema table, parity/divergence table vs Windows.
- `docs/build-mac.md`: from-source and .app builds, libmpv/ffmpeg options (brew vs bundled), codesigning/notarization notes, troubleshooting.
- `docs/prd.md`: requirements with IDs (parity with upstream PRD style: R-*, A-* accessibility requirements).
- `docs/mac-smoke-test.md`: numbered manual checklist for first run on a Mac (launch, VoiceOver announces, play ACB station, record 10s, hide/reopen from Dock, media key, quit-while-recording confirm).

- [ ] Step 1: Write all docs. ASCII only, small tables, heading-navigable.
- [ ] Step 2: Cross-check every keyboard shortcut and file name in the docs against the code written in Tasks 1-10 (grep, do not trust memory).

### Task 13: Integration pass

- [ ] Step 1: `python -m pytest tests -q` — full green.
- [ ] Step 2: Import sweep: `python -c` loop importing every module in the package on Windows; zero tracebacks.
- [ ] Step 3: Grep the package for leftovers: `quill\.` imports (must be zero), `wx.media`, `WMP10`, `EnhanceRelay`, `RegisterHotKey`, `winreg`, `os.startfile`, `%APPDATA%` in strings, TODO/TBD/FIXME. Fix anything found.
- [ ] Step 4: `git status` summary for the user; no commits.
