# What the documents and spell-check layers actually contain

Date: 2026-08-20. The measurement Stage 3 of
[the runtime layering plan](2026-08-17-runtime-layering-delta.md) needs before
it can start, plus three findings the measuring turned up.

Nothing here proposes an architecture. Stage 3 -- building the layer loader --
is still unstarted and should stay that way until the decisions at the end of
this document are made. What changed today is that the split is a number
instead of an estimate, and the declaration is a file a test can read.

## Short version

- The shared runtime's Python payload is **284.1 MB**.
- **113.1 MB of it -- 39.8% -- is reachable by exactly one app of ten.** The
  documents stack is 85.0 MB and the spell checker is 28.1 MB; the editor is
  the only thing that can call either.
- Nine apps install all of it. Quill Weather ships a PDF renderer, an image
  library, Windows OCR and a spell checker to read out a forecast.
- Three apps use media tools and declare none. One of them is a **converter**
  that can only write WAV without the ffmpeg it never asks for.

## How this was measured

`scripts/runtime_layer_report.py` (new) against
`standalone/runtime/dist/QuillVilleRuntime`, built 2026-08-19 14:40. It reads
`standalone/runtime/app-profiles.json` (new) and walks `_internal` for real
byte sizes.

Two things worth saying about the method, because both have already misled
somebody:

- **`du -sm` is useless here.** It rounds every file up to a block, which on a
  tree with this many small `.py` files overstates `_internal` by roughly
  480 MB. Every number in this document is an `os.path.getsize` sum.
- **The report shares its name normalizer with the inventory gate.**
  `check_runtime_inventory.normalize` is imported rather than reimplemented, so
  the two tools cannot disagree about what a top-level entry *is*.

## The split, measured

| Group | MB | Who can call it |
|---|---|---|
| Runtime floor: CPython, its extension modules, `quill` | 70.1 | every app |
| Layer `documents` | 85.0 | the editor only |
| Layer `spellcheck` | 28.1 | the editor only |
| Unattributed | 100.9 | mixed -- see below |
| **Total** | **284.1** | |

### Layer `documents` -- 85.0 MB

| MB | Package | Why it is here |
|---|---|---|
| 39.5 | `pymupdf` | PDF, via `quill/io` |
| 13.4 | `PIL` | `quill/core/ai/vision.py`, `quill/platform/windows/screen_capture.py` |
| 7.9 | `pdfminer` | PDF text extraction |
| 7.2 | `pypdfium2_raw` | second PDF renderer |
| 5.3 | `pydantic_core` | markitdown's closure |
| 3.9 | `curl_cffi.libs` | markitdown's closure |
| 2.6 | `winrt` | Windows OCR |
| 2.2 | `libheif` + 0.9 `libde265` | HEIC images |
| 1.0 | `docx`, 0.3 `pptx` | Office formats |
| <1 | `latex2mathml`, `jiter`, `markupsafe`, `werkzeug`, `itsdangerous`, `click` | math + markitdown closure |

Every member was traced to an import under `quill/io`, `quill/core/math`,
`quill/core/ai/vision.py` or `quill/platform/windows` -- surfaces that exist
only in the editor. The standalone apps open their bundled help as
**pre-rendered HTML** through the system browser
(`app_shell.open_app_document`), so none of them reaches the document path.
That was checked, not assumed: it is the obvious way this analysis could have
been wrong.

### Layer `spellcheck` -- 28.1 MB

`enchant`, after `scripts/prune_enchant_payload.py` has already taken it from
90.7 MB. Only `quill/core/spellcheck.py` and `quill/core/spell_languages.py`
import it, and only the editor reaches those -- the fact that changed the whole
language plan in
[the 2026-08-18 retrospective](../engineering/2026-08-18-runtime-layering-retrospective.md),
where it had looked like a cost shared across eight apps.

QUILL Social has a spell-check keymap entry, a PRD section, and no code. It
joins this layer when that is built and not before.

### Unattributed -- 100.9 MB

The interesting column: packages nobody has decided about. Not proven shared,
not claimed by a layer.

| MB | Package | Best guess |
|---|---|---|
| 24.2 | `wx` | genuinely shared -- every app is wxPython |
| 21.0 | `numpy.libs` + 6.5 `numpy` | shared (audio paths) -- but worth confirming Weather and Inkwell reach it |
| 10.0 | `yt_dlp` | **radio, cast, studio only** -- a media layer candidate |
| 9.2 | `cryptography` + 5.2 `libcrypto` + 0.8 `libssl` | shared (HTTPS, Beacon sync) |
| 8.2 | `sound_lib` | shared -- earcons |
| 2.7 | `libstdc++` | shared C++ runtime |
| 2.4 | `_soundfile_data` + 0.7 `_sounddevice_data` | shared audio I/O |
| 1.6 | `sqlite3.dll` | shared |
| 1.2 | `accessible_output2` | shared -- screen-reader bridge |
| 0.8 | `quill_social` | **Social only** |
| 0.4 | `libipld` | Beacon (AT Protocol) only |

Two clear candidates for a third layer are visible already: `yt_dlp` at 10.0 MB
belongs to the three media apps, and `quill_social` plus `libipld` belong to
one app each. Neither is worth a layer on its own; both are worth naming before
the next person assumes they are shared.

## Three apps use media tools and declare none

This is what the declaration file surfaced on its first day, and none of it was
previously written down anywhere.

`REQUIRED_COMPONENTS` is what makes the component store refcount a tool for an
app, and calling `Stage-QuillMediaTools` in an app's `build_release.ps1` is what
puts the tool in its installer. Radio, Cast and Studio do both. These three do
neither, and use the tools anyway:

1. **Quill Converter** -- `quill/apps/converter.py` calls `find_ffmpeg()` and
   hands the result to `available_output_formats()`, which returns exactly
   `["wav"]` when ffmpeg is absent. **An audio converter that can only write
   WAV.** Nothing installs ffmpeg for it, nothing refcounts it, and nothing
   says so to the person using it.
2. **Quill Media Player** -- `quill/apps/player.py` announces "Audio effects
   need the libmpv engine" and reports which backend it is on, so it knows
   about libmpv and declares nothing. Effects are silently unavailable.
3. **Quill Beacon** -- `quill/apps/beacon/player.py` documents an opt-in libmpv
   backend and falls back to `wx.media`. The mildest of the three: it degrades
   rather than breaks.

All three are recorded in `app-profiles.json` as findings rather than fixed.
Adding a component to an app changes what its installer must stage and what the
store keeps alive, which is a packaging decision, not a refactor.

## What is enforced now, and what is not

**Enforced** (`tests/unit/structure/test_app_profiles.py`, 11 checks):

- every shipped entry point has a profile row -- a new app that declares
  nothing is how the runtime grew in the first place;
- every row names a module and a standalone directory that exist;
- every row's `components` matches that module's own `REQUIRED_COMPONENTS`
  exactly. This is the control for the risk the whole idea carries: if the
  build-side declaration and the runtime one both own the truth, they drift,
  and a declaration that can be wrong is worse than none. Audio Studio shipped
  for months declaring ffmpeg while its build staged libmpv too;
- no package belongs to two layers, and every layer names an owning app that
  actually requires it;
- **the editor is still the only app requiring either heavy layer.** If a
  second app ever legitimately needs one, that test failing is the moment to
  re-price the split rather than discover it after the work.

**Not enforced:** nothing checks a built artifact against layer membership.
`runtime_layer_report.py` measures and prints; it never fails a build. Making
it a gate is Stage 4, and doing that while 100.9 MB is unattributed would just
gate a guess.

## Decisions this needs before Stage 3 starts

The first four are carried forward from the layering delta, unchanged and still
open. The fifth is new.

1. **Is `ffprobe` worth 101.7 MB?** ffmpeg and ffprobe are separate static
   builds totalling 203.6 MB of the 319.5 MB `tools/` tree. A shared-library
   ffmpeg would let them share one set of `libav*` DLLs. ffprobe is genuinely
   used, for M4B/M4A chapter marks and durations, so this is a build question
   and not a deletion.
2. **Which layer owns `markitdown`?** Its closure is already inside the
   documents figure above. Confirm nothing outside `quill/io` calls it.
3. **Does `winrt` (2.6 MB, Windows OCR) belong in core or documents?** It has
   silently vanished from a release once already. It is in `documents` here on
   the strength of its single importer, `windows_ocr.py`.
4. **Radio's offline promise.** Radio must keep working offline out of the box,
   so its FULL installer staging ffmpeg and libmpv is not optional.
5. **Is `numpy` really shared?** 27.5 MB with `numpy.libs`, assumed shared
   because the audio paths use it. If Weather and Inkwell cannot reach it, it
   is the largest single item in the unattributed column and a layer candidate
   in its own right.

## What Stage 3 would take

Recorded so the next estimate does not start from zero.

A layer is a versioned directory beside the runtime that `runtime_launcher.py`
adds to `sys.path` when present, pinned by SHA-256 in the same in-code manifest
the components already use, fetched by the same `fetch_file` core and
refcounted by the same `components.state.json`. The pieces that do not exist
yet are the layer manifest, the launcher's path insertion, and the build split
that produces a core runtime with the layer packages excluded.

One rule from the retrospective governs all of it and is easy to forget: **a
frozen copy shadows an installed one permanently.** PyInstaller's
`FrozenImporter` precedes `PathFinder` on `sys.meta_path`, so a package that
ships in the core runtime *and* in a layer will always resolve to the core
copy. Every package moved into a layer must be added to the spec's `excludes`
in the same change, and `scripts/check_runtime_imports.py` is what proves it.
