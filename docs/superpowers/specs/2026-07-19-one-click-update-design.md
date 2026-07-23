# One-Click Update (Apply and Restart) — Design

Date: 2026-07-19
Status: Approved (design), pending implementation
Target release: Quill Radio 2.0.3 (shared `quill` package; Radio, Cast, and QUILL)

## Problem

When Quill Radio (or Cast, or QUILL) finds an update, the in-app flow downloads the
release asset and then, for a **portable** build, only tells the user to "close this app,
extract the zip over your current folder, and start it again" (`app_shell.py`
`_offer_app_update_install`). There is no action that actually applies the update. A
sighted power user can do the manual swap; a screen-reader user is left doing archive
surgery. The user asked for the zip to "auto extract and program restart with updates
loaded."

For an **installed** build the flow launches the setup `.exe` and the user clicks through
it — better, but still not one-click.

## Goal

A single **"Install and restart now"** button on the post-download dialog that applies the
update and relaunches the app, on both portable and installed Windows builds, with no
manual steps. Consented (nothing happens without that click), accessible, and safe (a
failed apply leaves the working install intact).

## Non-goals (this release)

- macOS apply (a `.app`/`.dmg` swap). QUILL on macOS keeps today's download-and-reveal.
  A clean seam is left for a follow-up.
- Silent / forced auto-apply. The download stays consented and the apply is one explicit
  click (chosen over silent-on-quit: a screen-reader user must not have the app mutate and
  restart without a deliberate action).
- Delta/patch updates. The full release asset is downloaded as today.

## Build-flavor split

Detected by the existing `running_portable()` / `_running_portable_build()` check
(`unins000.exe` beside the exe ⇒ installed; absent ⇒ portable). Dev runs report installed
and are unaffected (they never reach a real apply).

### Installed build → silent installer + relaunch

Run the downloaded Inno setup `.exe` with silent flags and a relaunch, then close the app:

```
Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

The installer already handles file replacement and elevation (one UAC prompt, since the
install dir is under Program Files). Relaunch is via the installer's own postinstall run
entry, or by the same apply-helper waiting on PID then starting the exe — whichever the
installer supports. This path largely reuses the current `_launch_installer`.

### Portable build → apply-update helper

A running `.exe` cannot overwrite itself on Windows, so an external helper does the swap
after the app exits:

1. **Stage.** Extract the downloaded zip to `<app_data>/updates/staging/` (reusing
   `extract_portable_update`, which already guards zip-slip and decompression bombs).
   Locate the real app root inside the extraction (the zip may wrap files in a top-level
   folder) and validate it contains the expected exe. Abort before touching anything if it
   does not.
2. **Write helper.** Generate a Windows `.bat` (pure function, unit-tested) into the system
   temp dir — outside the install folder, so copying over the install dir never clobbers
   the running helper. The batch receives: the app PID, the staging source dir, the install
   dir, and the exe to relaunch.
3. **Launch + exit.** Launch the helper detached (`DETACHED_PROCESS` / no console window),
   then shut the app down cleanly through its normal close path, releasing the
   single-instance lock (`ipc.release_primary_instance`) and all file handles, and exit.
4. **Swap.** The helper waits for the app PID to disappear (`robocopy`-friendly poll), then
   mirror-copies the staged files over the install dir **excluding `data`** (favorites,
   recordings, history, settings live there and must survive), relaunches the new exe, and
   deletes the staging dir and itself. All output is appended to
   `<app_data>/updates/apply-update.log`.

Portable folders are user-writable, so the copy never needs elevation. For a portable
build, `<app_data>` is under the portable `data/` folder, so the staging source sits inside
the excluded `data` dir and survives the swap that overwrites everything else.

## Components

### `quill/core/updates.py` (wx-free, unit-tested)

- `install_root_and_exe() -> tuple[Path, Path] | None` — the frozen exe path and its
  containing install dir; `None` in a dev run. Small, so both UI seams share one truth.
- `stage_portable_update(zip_path, staging_dir, *, exe_name) -> Path` — extract via
  `extract_portable_update`, descend a single wrapping folder if present, verify `exe_name`
  exists, and return the app root to copy from. Raises a clear error if the archive does
  not look like a Quill app.
- `build_apply_update_script(*, pid, source_dir, install_dir, exe_path, log_path,
  data_dirname="data") -> str` — pure. Returns the batch text:
  - wait-for-PID-exit loop (with a timeout ceiling so it can never hang forever),
  - `robocopy "<source>" "<install>" /MIR /XD "<install>\data" /R:2 /W:1 /NP` (mirror,
    excluding `data`; retries),
  - `start "" "<exe_path>"` to relaunch,
  - cleanup of the staging dir and the batch itself,
  - every step tee'd to `<log_path>`.
  Paths are quoted; the function is the single place batch quoting/edge-cases live so tests
  pin them.
- `build_silent_installer_command(setup_exe) -> list[str]` — pure. The
  `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` argv.

### `quill/ui/app_shell.py` (Radio + Cast)

Replace `_offer_app_update_install`'s portable "instructions only" branch and installer
branch with a single **"Install and restart now"** default button (plus the existing Open
folder / Close). On click:
- installed ⇒ `build_silent_installer_command`, launch detached, then `self.frame.Close()`;
- portable ⇒ `stage_portable_update`, write + launch the helper, then `self.frame.Close()`.
Both announce "Installing update and restarting…" first. A staging/launch failure is
announced and leaves the app running (fall back to Open folder).

The app's own close handler already releases the lock and shuts controllers down
(`quill/apps/radio.py` `_on_radio_app_close`), so closing after launching the helper is the
clean-exit signal the helper's PID-wait keys on.

### `quill/ui/main_frame_updates.py` (QUILL, Windows)

Give `_offer_post_download_actions` the same apply behavior for Windows portable and
installed builds. macOS falls through to today's reveal/extract. QUILL's close path already
calls `release_primary_instance`.

## Data flow

```
Check for Updates ─▶ download asset (existing) ─▶ post-download dialog
   └─ "Install and restart now"
        ├─ installed:  launch Setup.exe /VERYSILENT ─▶ app closes ─▶ installer swaps + relaunches
        └─ portable:   stage zip ─▶ write helper.bat ─▶ launch detached ─▶ app closes (lock released)
                          └─ helper: wait PID ▸ robocopy staged→install (xd data) ▸ start exe ▸ clean up
```

## Error handling

- Download/extract already fail-soft (announced, install untouched).
- Staging validation failure (no exe in the zip): abort, announce, keep running.
- Helper copy: `robocopy` retries (`/R:2 /W:1`); copy-over/mirror-excluding-data never
  deletes user data; on partial failure the exit code is logged and the old files that were
  already replaced remain (a re-run of the update repairs it). Because `data` is untouched,
  the user never loses favorites/recordings/settings.
- Helper never blocks forever: the PID-wait has a timeout ceiling, after which it proceeds
  anyway (the app is expected to have exited; the copy simply retries locked files).
- All helper steps are logged to `apply-update.log` for support.

## Testing

- `build_apply_update_script`: pure-text assertions — PID wait present, `robocopy` excludes
  the data dir, relaunch targets the exe, paths quoted, log path threaded through.
- `build_silent_installer_command`: argv assertions.
- `stage_portable_update`: real temp zips — flat layout, single-wrapping-folder layout,
  and a bad zip (no exe ⇒ raises); zip-slip already covered in `extract_portable_update`
  tests.
- Helper end-to-end (Windows, non-frozen, no real exe): generate the batch against a temp
  "install" of dummy files with a `data/keep.txt`, run it against a temp "staging" tree with
  a fake exe and a PID that has already exited, assert the dummy exe/files were copied,
  `data/keep.txt` survived, and staging was cleaned. Guarded to Windows.
- UI seams: existing app-close tests already cover clean shutdown; add a unit test that the
  portable branch calls stage+launch+Close and the installed branch calls the silent
  command+Close (fakes, no real subprocess), mirroring `test_radio_app_close_and_keys.py`
  style.

## Rollout

Ships in 2.0.3 (already the target). Adds a release-notes bullet ("Update Quill Radio in one
click — it downloads, applies, and restarts itself"). Version already bumped to 2.0.3.
