# QuillVille installer + shared runtime program

Status: proposed (2026-07-21). Author: consolidation work. This is the umbrella
plan for the remaining packaging work requested: a **shared Python runtime**
across all apps, and a **rich installer experience** (standard, portable, and
offline variants, with optional-component selection) for every QuillVille app.

It sits above the earlier `2026-07-20-quillville-runtime-and-component-plan.md`
(which established the shared *component* store for ffmpeg/mpv/models/voices)
and extends the same "fetch once, share, reference-count" philosophy to the
Python runtime itself and to the installer UX.

## Apps in scope

| App | Entry | Today's packaging |
| --- | --- | --- |
| QUILL (editor) | `quill.apps` / main_frame | Inno `installer/quill.iss`, PyInstaller onedir |
| Quill Radio | `quill.apps.radio` | `standalone/radio` shell + `quill-radio.iss` |
| Quill Cast (podcasts) | `quill.apps.podcasts` | `standalone/cast` + `quill-cast.iss` |
| Audio Studio | `quill.apps.studio` | `standalone/studio` + `quill-audio-studio.iss` |
| QUILL Social | `quill_social` (self-contained) | `standalone/social` -- **no installer yet** |
| Quill Radio (macOS) | `quill_radio_mac` | `standalone/radio-mac` -- mac bundle, no Inno |
| Beacon | `quill.apps.beacon` | `standalone/beacon` + `quill-beacon.iss` |

## Part A -- Shared Python runtime

### Problem

Each app is a PyInstaller **onedir** bundle that carries its own
`python3xx.dll`, standard library, and wxPython in `_internal/`. Installing
QUILL + Radio + Cast + Studio + Social today means ~5 copies of CPython and
wxPython (~30-40 MB each). The user wants Python shared so the suite installs
once and the apps reuse it.

### Approach (recommended): a reference-counted "QuillVille Runtime"

A single versioned runtime folder shared by every app, installed to a common,
non-per-app location and reference-counted exactly like the component store:

```
%LOCALAPPDATA%\QuillVille\runtime\<py-version>\   (or Program Files\QuillVille\runtime)
    python.exe, python3xx.dll, Lib\, ...          (embeddable CPython)
    site-packages\wxpython, quill\, quill_social\ (shared libs + app code)
runtime.state.json  { "3.13.1": ["quill","radio","cast","studio","social"] }
```

- Each app ships only a **thin launcher** (a tiny native `.exe` that execs the
  shared `python.exe -m quill.apps.radio`) plus its icon, docs, and app-specific
  data -- kilobytes, not tens of megabytes.
- The installer for any app **installs the shared runtime if absent or older**
  (a bundled payload, extracted to the shared location) and adds the app to
  `runtime.state.json`. The uninstaller decrements; the runtime is removed only
  when the last app referencing it is gone. This mirrors `quill/core/components.py`
  precisely -- extend that module (or add `quill/core/runtime_refs.py`) with the
  same register/unregister/unreferenced API keyed by runtime version.
- **Version safety:** the folder is keyed by exact Python version, so two apps
  pinned to different CPython minors coexist; upgrading an app that needs a newer
  runtime installs the new one alongside and repoints its launcher. No shared
  interpreter is ever mutated in place.

### Why not the alternatives

- *Keep per-app PyInstaller, dedupe at install time (hardlinks):* fragile across
  drives/filesystems, and Windows Inno cannot reliably hardlink; upgrades break
  links. Rejected.
- *One giant "QuillVille" mega-installer with all apps:* loses independent
  install/update per app (a Radio-only user should not download Social). Rejected;
  the shared-runtime + thin-launcher model keeps apps independent AND shared.

### Build-system change (needs a build box to validate)

This replaces the per-app PyInstaller onedir with: (1) build the shared runtime
payload once (embeddable CPython + `pip install` the pinned deps + the `quill`/
`quill_social` wheels), (2) build each thin launcher. Validation MUST happen on
Windows (and macOS for the mac port) -- it cannot be verified in this dev
session. Until then, the existing onedir installers remain the shipping path;
the shared runtime lands behind a build flag and is cut over once green.

## Part B -- Rich installer experience (all apps)

Every app's `.iss` gains the same Inno structure so the experience is uniform:

### `[Types]` -- install profiles

- **Full** -- app + shared runtime + the app's common optional components
  pre-fetched (online) so it works out of the box.
- **Compact** -- app + shared runtime only; optional components fetch on demand.
- **Portable** -- see Part C.
- **Custom** -- user checks exactly the `[Components]` they want.

### `[Components]` -- optional feature selection

Driven by the same per-app catalog as #5 (`_optional_component_allowlist`):
Radio offers ffmpeg/mpv; Studio offers the speech engines + voices + audio pack;
QUILL offers the full set (Pandoc, PDF/OCR, braille, speech, voices, tools,
dictionaries). The installer either bundles the component (offline variant) or
records the user's choice for first-run fetch (online variant). Each component
row shows its size, mirroring the in-app picker.

### Accessibility

Inno's wizard is MSAA-exposed; keep it (the "Installer stays Inno Setup" memory).
Add clear captions, logical tab order, and a plain-text summary page. No custom
owner-drawn pages that break screen readers.

## Part C -- Portable and Offline variants

- **Portable** -- a no-installer `.zip` that runs from any folder (USB stick,
  locked-down machine). Writes settings/data next to the executable (a
  `portable.marker` next to the launcher flips `app_data_dir()` to a local
  `data\` folder). Carries the runtime inside the zip (not shared -- portable is
  self-contained by definition). The `build_release.ps1` scripts already produce
  a portable zip for Radio; generalize that to every app.
- **Offline Edition** -- the installer bundles **every** optional component the
  app can use (no internet needed on the target). The `build_info.is_offline_edition`
  marker and `optional_components.status_label_for` "Bundled (offline edition)"
  path already exist; the offline installer sets the marker and stages the
  components into the bundle at build time. Extend each `build_release.ps1` with
  an `-Offline` switch that stages the app's allowlisted components.

## Part D -- macOS runtime gaps (#6)

`model_mirrors.py` has zero macOS runtime entries. The mac *models* were staged;
the mac *runtime binaries* were not. Close by staging to `assets-v1` and adding
mirror entries:

- **piper (macOS)** -- the official `rhasspy/piper` macOS build (arm64 + x64).
- **whisper.cpp (macOS)** -- the `whisper-cli` macOS build (arm64 + x64).

Same pipeline as the yesterday's Windows staging (download -> SHA-256 ->
`gh release upload assets-v1`), then a `MirrorAsset` per binary keyed
`piper:macos-arm64` etc., and `register_running_app` wiring so the mac port and
Studio-on-mac resolve them. Requires a Mac to validate end to end.

## Sequencing

1. **[done]** Per-app optional-components filtering (#5).
2. **[done]** Social + mac source captured into the monorepo (#10).
3. Social build shell (`.spec`, `.iss`, `build_release.ps1`, `render_docs.ps1`)
   mirroring Radio -- authorable now, validate on a build box.
4. Rich `[Types]`/`[Components]` sections across all `.iss` -- authorable now.
5. Portable + Offline switches in each `build_release.ps1` -- authorable now.
6. Shared runtime: `runtime_refs` core (unit-testable now) + thin launcher +
   build changes -- **build box required**.
7. macOS piper/whisper runtime staging + mirrors (#6) -- **Mac required**.
8. Radio window-model modeless conversion (separate branch) -- **screen-reader
   validation required**.

## Validation ledger (what this dev session cannot prove)

- Inno compiles / installer wizard behavior -> Windows build box.
- PyInstaller / shared-runtime launch -> Windows build box.
- macOS bundles and mac piper/whisper runtimes -> a Mac.
- Modeless radio surfaces with NVDA/JAWS -> the screen-reader user.

Everything authored here is written by mirroring the proven Radio shell and the
existing component/offline machinery, and is gated by ruff/mypy(core)/size/
banned-patterns, but the four items above need their named environment before merge.
