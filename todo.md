# QUILL / QuillVille — TODO

Outstanding work, most-actionable first. Status as of 2026-07-21.

Legend: [ ] not started · [~] in progress / code done, validation pending · [x] done this session

---

## 1. Radio window model (modeless frames + &Window menu)

Branch: `radio-window-model` (up to date with `main`).

- [x] Infrastructure: `WindowManager` (`quill/ui/window_menu.py`) + `WindowRegistry`
      (`quill/ui/window_manager.py`) + `show_modeless_surface` (`dialog_contract.py`)
      + conversion recipe (`docs/design/2026-07-21-radio-window-conversion-recipe.md`).
- [x] App wiring in `quill/apps/radio.py` (create/install/register the WindowManager).
- [x] All 5 heavy surfaces converted to dual modal/modeless (modeless wx.Frame when a
      WindowManager is passed by standalone Radio; unchanged modal wx.Dialog for
      embedded QUILL): Browse Stations, Search Stations, Manage Favorites,
      Schedule Recording, Weather Center. Each has a regression test.
- [~] **Screen-reader validation (the human step — can't be verified headlessly).**
      Run standalone Radio and confirm per surface: Alt reaches the menu bar;
      Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 traverse windows; Escape / Ctrl+W close
      and return focus to the previous window. Specifically check NVDA's virtual
      buffer on each surface — the modeless frames use an inner panel (Frames need
      one for tab traversal), which the Search dialog's own note cautioned about.
- [ ] After validation: merge `radio-window-model` -> `main`.
- [ ] Optional: replicate the same modeless conversion to QUILL Cast (podcasts) surfaces.

## 2. Shared Python runtime cutover

Goal: one shared CPython + wxPython + shared packages, reused by every app;
installed once, skipped (ref-bumped) on later installs, removed when the last app goes.

- [x] Reference counting + version marker + installer CLI, all unit-tested:
      `quill/core/runtime_refs.py`, `runtime_marker.py`, `runtime_cli.py`.
- [x] Shared runtime bundle: `standalone/runtime/` (generic `-m <module>` launcher +
      PyInstaller spec + `build_runtime.ps1` that stages ffmpeg/mpv + stamps the marker).
      Built and smoke-tested (`QuillVilleRuntime.exe -m quill.core.runtime_cli` runs).
- [x] Inno install fragment `installer/shared-runtime.iss` (install-if-absent via the
      marker + register/unregister refs + delete the runtime only when orphaned).
- [x] Radio shared-runtime installer `standalone/radio/installer/quill-radio-shared.iss`
      — compiles cleanly (produced `Quill-Radio-Setup-Shared-2.2.0.exe`, 272 MB).
- [~] **Windows install/uninstall test (golden gate — needs a VM or clean machine):**
      install Radio (runtime lands once), install a second app (runtime skipped),
      uninstall one (runtime stays), uninstall the last (runtime removed).
- [ ] After validation: promote `quill-radio-shared.iss` to the default installer and
      replicate the shared-runtime variant to Cast / Studio / Social.
- Note: the proven onedir `quill-radio.iss` remains the shipping installer until then.

## 3. Rich installers + portable/offline (#12)

- [x] `[Types]` (Full/Compact/Custom) + `[Components]` (program + optional docs) added to
      all six `.iss` (quill, radio, cast, studio, social, beacon).
- [x] Social build shell authored (`standalone/social/` spec + iss + build scripts).
- [ ] **ISCC compile-validate** the `[Types]`/`[Components]` changes on a build box
      (only the Radio shared-runtime variant has been compiled so far).
- [ ] Portable build variant for every app (shared-runtime portable zip carrying the
      runtime + a `data\` marker; the onedir `build_release.ps1` already zips a portable).
- [ ] Offline build variant: a `-Offline` switch that bundles each app's allowlisted
      optional components (the `is_offline_edition` marker + labels already exist).

## 4. macOS engine gaps (#6)

- [ ] Stage macOS **runtime binaries** to `assets-v1` and add `model_mirrors.py` entries:
      Piper (macOS arm64 + x64), whisper.cpp (`whisper-cli`, macOS arm64 + x64).
      `model_mirrors.py` currently has zero macOS runtime entries (models were staged;
      runtimes were not). Needs a Mac to validate end to end.

## 5. Runtime-logic consolidation (optional)

- [ ] The macOS Radio port (`standalone/radio-mac/quill_radio_mac/core/*`, ~25 files)
      and QUILL Social (`quill_social/services/*`, ~30 files) carry their **own copies**
      of core logic instead of importing shared `quill.core`. De-duplicate onto shared
      core if desired (the Windows apps already share it).

---

## Done this session (for reference)

- Radio: View menu (Show Station Details, Show Status Bar, Sort Favorites, Expand/Collapse
  All, Text Size); focusable F6 status bar; Favorites Manager Move-buttons fixed from the
  A-Z view; keep-computer-awake while playing/recording; Now Playing full-details on Enter;
  docs (changelog/release notes/user guide/PRD) updated + re-rendered.
- #5 per-app Optional Components filtering (Studio allowlist wired) — done.
- #10 merge quill-social + qrm into the monorepo — verified already done (`de7314b`).

## Validation ledger (what a dev session cannot prove)

| Needs | For |
|---|---|
| A screen reader (NVDA/JAWS) | Radio modeless surfaces (item 1) |
| A Windows VM / clean machine | Shared-runtime install/uninstall (item 2); installer UX (item 3) |
| Inno Setup on a build box | Compiling the other apps' installers (item 3) |
| A Mac | Piper/whisper macOS runtimes (item 4) |
