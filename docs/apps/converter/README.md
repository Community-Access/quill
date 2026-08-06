# Quill Converter -- the standalone audio converter app (not part of public QUILL 1.0)

> **Not part of the public 1.0 product.** Quill Converter is one of the five
> companion apps gated behind `RELEASED_APPS` (`quill/core/app_launcher.py`) for
> QUILL 1.0.0. It is not in the QuillVille menu, not in the command palette, and
> its Windows Explorer **"Convert with Quill"** shell verb is never registered in
> a public build (`quill/core/shell_verbs.py` skips the `convert` verb unless
> `is_app_released("converter")`).
>
> The *engine* is public. QUILL's editor-embedded Universal Audio Converter --
> the **Voices > Convert Audio...** dialog, the headless `quill convert` CLI, and
> **Convert from URL...** -- stays fully documented in the public user guide and
> PRD. Only the standalone app's own surfaces were relocated here, during the
> 1.0.0 documentation consolidation. Nothing was deleted.

**Where each part came from**

| Relocated from | Source section |
|---|---|
| `docs/user guide/userguide.md` | "The Universal Audio Converter" -- the standalone-app door and the Explorer shell-verb door |
| `docs/user guide/userguide.md` | "The Universal Audio Converter" -- the Advanced-mode standalone clause |
| `QUILL-PRD.md` | `### 5.25g Universal Audio Converter` -- the standalone surfaces and the deferred build entry |
| `QUILL-PRD.md` | `§35.1 The apps` -- the Quill Converter family entry |

---

# Part 1 -- relocated user guide material

_Moved from the user guide's "The Universal Audio Converter" section, which
stays public and now describes **three** doors (the dialog, the CLI, and Convert
from URL) instead of five._

## The standalone app, as a door onto the shared engine

- **Quill Converter** -- a standalone tray app, launched with `python -m quill.apps.converter` (or its own icon). It carries the QuillVille menu like the other family apps, minimizes to the tray, and has its own show/hide hotkey (Ctrl+Alt+Shift+C).
- **Windows Explorer** -- turn on **Settings -> Integration -> Offer "Convert with QUILL"** and right-clicking an audio or video file gains a **Convert with Quill** entry that opens the standalone converter with that file already queued.

## Advanced mode in the standalone app

The user guide's Advanced-mode paragraph described the panel as "a checkbox that
reveals more controls, or the **Advanced...** button in the standalone app". The
public text now names only the checkbox; the standalone app reaches the same full
processing catalog -- bit rate, sample rate, channels, bit depth, loudness
targets, gain, high-pass, trim silence, speed, compressor, leveler, and fades --
through its **Advanced...** button.

---

# Part 2 -- relocated PRD material

_Moved from `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`.
The PRD keeps 5.25g for the public engine and its three public surfaces and
points here for the app._

## PRD 5.25g -- the standalone surfaces

The single wx-free engine (`core/audio/convert.py`, `presets.py`, `dsp.py`,
`url_import.py`, `convert_cli.py`) is also surfaced through:

- a standalone **Quill Converter** app (`apps/converter.py`, an `AppShellFrame`
  registered in `core/app_launcher.py`);
- a Windows Explorer **"Convert with Quill"** shell verb (`core/shell_verbs.py`,
  gated by `shell_verb_convert`, routed through `--action convert` to the
  converter app). For 1.0.0 the verb is additionally gated on
  `is_app_released("converter")`, so a public build never registers it.

**Deferred:** the standalone app's PyInstaller build entry + launcher tile icon
(after the build refactor settles); the app runs today via
`python -m quill.apps.converter`.

## PRD 35.1 The Quill Converter family entry

_Moved from `## 35. The QuillVille family` / `### 35.1 The apps`, whose inventory
now lists only the publicly released apps and points here for the gated ones._

- **Quill Converter** (`quill/apps/converter.py`) -- the Universal Audio
  Converter as its own app. Was to ship as a standalone product from 1.0.0:
  `standalone/converter/` is the wrapper (launcher package, tile icon +
  regenerable `assets/make_quill_converter_icon.py`, PyInstaller spec,
  `pyproject.toml`), `build_portable.py` carries a `converter` product entry
  (`QuillConverter.exe`, ffmpeg staged, no speech engines and no mpv -- the
  conversion work is entirely FFmpeg's), and `QuillConverter.exe` is in
  `storage_mode`'s portable-evidence allowlist so a portable bundle keeps its
  data next to the exe like every sibling. yt-dlp is never bundled: URL import
  installs it on demand with consent. **Held back from the public QUILL 1.0.0
  release** via `RELEASED_APPS`.
