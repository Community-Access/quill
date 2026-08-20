# The shared runtime has drifted from its own plan — measurements and a way back

Date: 2026-08-17. A delta against
`2026-07-20-quillville-runtime-and-component-plan.md`, which remains the plan of
record. Nothing here proposes a new architecture. It measures how far the built
artifacts have moved from the one already decided, and what it costs.

## Short version

"Keep the shared runtime minimal and add the layers each app needs" is not a new
idea to adopt — it is §2 and §5 of the 2026-07-20 plan, and most of the
machinery for it is already written and shipping. What has happened is that the
build drifted away from it in two specific, measurable steps, and the result is
that a weather app installs a 34 MB ICU locale database, a PDF renderer, and a
speech-recognition backend.

## What the plan says

- §2: there are **two** shared surfaces with different rules. **The Runtime** is
  "embeddable Python + pip + the `quill` package". **The Component Store**
  (`%APPDATA%\Quill`) holds ffmpeg, mpv, engine packs, voices, models.
- §1: the component store already works and is "the single most important fact:
  the disk-heavy sharing already exists". What was *not* yet shared was the
  Python runtime and the `quill` code — "tens of MB".
- §5: each app declares `REQUIRED_COMPONENTS`; the store refcounts; the last app
  to need a component is the one whose removal makes it collectable. "No
  component is ever stored twice, and no app carries another app's weight."

That last sentence is the one the current build breaks.

## Drift 1: the heavy components moved back into the runtime

`standalone/runtime/build_runtime.ps1` stages ffmpeg, ffprobe, and libmpv into
`dist\QuillVilleRuntime\tools\`, and the shared-runtime installer fragment ships
that whole tree. The rationale in `build_release.ps1` is sound as far as it goes
— "ffmpeg/mpv go here, not into the per-app `$appDir\tools\`, so the per-app
install stays tiny" — but the destination it chose was the runtime rather than
the component store, and the runtime is what *every* app installs.

That is 304 MB, 41% of the runtime:

| Item | MB |
|---|---|
| tools\ffmpeg\ffmpeg.exe | 97 |
| tools\ffmpeg\ffprobe.exe | 97 |
| tools\mpv\libmpv-2.dll | 110 |

The refcount layer that was supposed to govern these is **already implemented
and running**: `quill/core/components.py` maintains
`components.state.json`, and the apps declare their needs —
`quill.apps.radio.REQUIRED_COMPONENTS = ("ffmpeg", "mpv")`,
`podcasts` and `studio` declare `("ffmpeg",)`. The resolver in §6 (store →
staged wheelhouse → verified network → guided prompt) exists too. Bundling into
the runtime means that machinery is bypassed: the app finds the tools beside
`sys.executable` and never consults the store.

**Who does not declare a single component:** `weather`, `inkwell`, `converter`,
`player`, and beacon/social. They ship all 304 MB anyway.
`Quill-Weather-Setup-Shared-2.2.0.exe` is 191.5 MB for an app that reads the
forecast aloud.

## Drift 2: the runtime became the union of every app's Python dependencies

`quillville-runtime.spec` says so explicitly:

> The heavy optional ML stacks are NOT excluded here (unlike a single-app spec):
> the shared runtime is the union of every app's needs.

"Union" is right for a *shared* runtime in the abstract. It is wrong when the
union is delivered whole to every app, because the union is dominated by
QUILL-the-editor's needs and every other app is a fraction of it.

The dead `standalone/radio/quill-radio.spec` still records what Radio actually
needs — it excludes `faster_whisper`, `vosk`, `kokoro_onnx`, `onnxruntime`,
`torch`, `PIL`, `pdfminer`, `pypdfium2` and `lxml` by name. Nothing builds that
spec any more.

Measured on today's build (734.9 MB total, real bytes):

| Layer | MB | Who can actually use it |
|---|---|---|
| Core: CPython, wx, numpy, quill, yt-dlp, networking, a11y bridges | ~150 | every app |
| Media tools (ffmpeg, ffprobe, libmpv) | 304 | radio, cast, studio, QUILL speech |
| Documents (pymupdf 38, PIL 13, pdfminer 8, pypdfium2 7, pyphen 6, docx, pptx, rdflib, latex2mathml, weasyprint) | ~80 | QUILL only |
| Speech in (ctranslate2 59, vosk 26, hf_xet 9, tokenizers 7) | ~101 | QUILL, cast, studio |
| Spellcheck (enchant, post-prune) | 27 | QUILL, maybe social/inkwell |
| Neural TTS (kokoro-onnx, phonemizer-fork) | ~5 + on-demand models | QUILL, studio |

Radio's honest requirement is core + media, about 455 MB. Weather's is core
alone, about 150 MB. Both currently install 735.

## What this costs, per app

Every app's installer is currently sized by QUILL's needs. The saving from
layering is not uniform — it is largest for the smallest apps, which is
precisely backwards today:

- Weather, Inkwell, Converter, Player: ~585 MB of payload they cannot call.
- Radio, Cast: ~280 MB (the document + ASR + spellcheck layers).
- Studio: ~110 MB (documents + spellcheck).
- QUILL: nothing. It is the app the union was sized for.

## The way back

The mechanism exists. This is sequencing, not invention.

**Phase 1 — stop shipping what nothing can call.** No architecture change, no
new mechanism, purely removing dead weight from the union. Done today:

- `scripts/prune_enchant_payload.py` — pyenchant vendors a slice of an MSYS2
  `bin` (Tcl/Tk, a second CPython, GNU readline, the GCC support libraries,
  gettext's toolchain, 34 MB of ICU) as package *data*, invisible to
  PyInstaller `excludes`. The pruner computes libenchant's real PE import
  closure and keeps exactly that: 90.7 MB to 26.8 MB, verified end to end with
  identical `check()` and `suggest()` output. Wired into `build_runtime.ps1`.
- `hypothesis` added to the spec excludes. A property-based test framework was
  being swept into the shipped runtime, the same way `mypy` was before it.

Still open in this phase: `vosk\libstdc++-6.dll` is 25.4 MB where the runtime's
other two copies of libstdc++ are 2.5 and 2.2 MB.

**Phase 2 — return ffmpeg and mpv to the component store.** The largest single
win (304 MB off every app that does not play media, and off the *runtime* for
all of them) and the one the plan already specifies. `build_runtime.ps1` stops
staging `tools\`; the per-app installer either stages them into the store
(offline/FULL flavour) or lets the existing offline-first resolver fetch and
refcount them on first launch (LEAN). Radio, Cast and Studio already declare
what they need; Weather, Inkwell, Converter and Player already declare nothing,
so they get it right for free.

Prerequisite worth stating plainly: this reintroduces a first-launch download
for Radio unless the FULL installer stages the tools. Radio must keep working
offline out of the box, so the FULL flavour is not optional for it.

**Phase 3 — split the Python feature layers.** Build the core runtime with the
document / ASR / spellcheck stacks excluded, and ship each as a separate
versioned layer directory that `runtime_launcher.py` adds to `sys.path` when
present. Layers are pinned by SHA-256 in the same in-code manifest §10b already
defines for components, fetched by the same `fetch_file` core, refcounted by the
same `components.state.json`. An app declares `REQUIRED_LAYERS` beside its
`REQUIRED_COMPONENTS`.

This is the genuinely new engineering, and it is worth doing only after Phase 2
proves the delivery path. It is also where the compatibility rules matter: a
layer contains compiled extension modules and is therefore bound to the
runtime's Python minor version, so layer identity must include it
(`documents/3.13/`), exactly as the runtime root already does.

**Phase 4 — extend the gates.** `check_runtime_inventory.py` grows a
per-layer inventory so "a package appeared in the core that belongs in a layer"
fails the build by name, the same ratchet as today.

## Decisions the owner needs to make

1. **Is ffprobe worth 97 MB?** ffmpeg and ffprobe are separate ~97 MB static
   builds. A shared-library ffmpeg build would let them share one set of
   `libav*` DLLs. Worth pricing before Phase 2 freezes the component shape.
2. **Which layer owns `markitdown`?** It arrived in today's build with 61 MB of
   transitive dependencies (pymupdf 37.7, pydantic_core 5.0, pyphen 5.9,
   cramjam 4.0, curl_cffi 3.7, weasyprint, fonttools, google, opentelemetry,
   werkzeug, lark). It is QUILL's Tier-1 document converter. Documents layer,
   almost certainly — but confirm nothing else calls it.
3. **Does `winrt` (2.5 MB, Windows OCR) belong in core or documents?** It
   silently vanished from a release once already, so wherever it lands it needs
   a declaration.
4. **Radio's offline promise.** Confirm FULL-flavour staging of ffmpeg/mpv
   before Phase 2 removes them from the runtime.

## Note on today's inventory rebaseline

The build interpreter had `pypdf` 6.15.0 against a `[runtime]` floor of 6.16.1
(raised in `09caf8e` when the vulnerable pin was removed). With the old pypdf,
`collect_all("quill")` could not import the PDF subtree, so **everything
reachable through it silently did not ship** — which is how the 181.9 MB
`Quill-Radio-Setup-Shared-3.0.0.exe` currently in `dist\` was produced. Fixing
the interpreter made 61 MB of genuinely-reachable dependencies appear, and
`check_runtime_inventory.py` correctly failed the build naming all 25.

They were declared (rebaselined) rather than excluded, because they *are*
reachable from shipping code and a build that quietly omits them is the worse
failure of the two. That is a decision to revisit in Phase 3, where most of them
belong to the documents layer rather than to core. It is reversible: revert
`standalone/runtime/runtime-inventory.json`.

---

## Status, 2026-08-17 evening: Phases 1 and 2 are done and measured

The shared runtime is **335.2 MB**, down from 734.9 MB. Every QuillVille app
installs that runtime, so it is 399.7 MB off all eight of them.

### What Phase 1 actually found

Phase 1 was scoped as "stop shipping what nothing can call". It turned out to be
"stop shipping three speech engines that were already broken".

Probing the built runtime by importing each optional module inside it -- rather
than reading the file list -- showed:

| Module | In the runtime | What `import` did |
|---|---|---|
| `vosk` | 27.6 MB of mingw support DLLs | `OSError: cannot load library 'libvosk.dll'` |
| `faster_whisper` | pure Python, plus ctranslate2's 59 MB | `ModuleNotFoundError: No module named 'av'` |
| `kokoro_onnx` | pure Python, plus phonemizer-fork | `ModuleNotFoundError: No module named 'onnxruntime'` |

Three causes, one shape. `vosk` loads its 26 MB `libvosk.dll` through cffi at
import time, which PyInstaller's dependency analysis cannot see, so the engine
DLL never shipped while its support libraries did. `av` and `onnxruntime` are
deliberate spec excludes (they were dropped for size), and nothing checked what
else needed them.

Two things made this invisible:

1. **The frozen copy shadows the on-demand engine pack, permanently.**
   `engine_install.activate_engine_packs` adds the pack to `sys.path`, but
   PyInstaller's `FrozenImporter` sits ahead of `PathFinder` on `sys.meta_path`,
   so the frozen module always wins. (This is exactly why `yt_dlp` already needs
   the explicit meta-path finder in `engine_pack_imports.py`.) Installing the
   Vosk engine could not fix Vosk.
2. **`is_vosk_available()` and its siblings ask `find_spec`**, which resolves the
   broken frozen module without importing it. QUILL reported all three engines
   as installed and therefore never offered the pack that would have worked.

Every build carrying this exited 0. `check_runtime_inventory.py` could not catch
it either: it compares top-level *names*, and `faster_whisper` is pure Python, so
it never had a name on disk to compare.

### Changes

- **`quillville-runtime.spec`**: `vosk`, `faster_whisper`, `ctranslate2`,
  `kokoro_onnx` and `sherpa_onnx` added to `excludes`. All five are engine-pack
  owned. `sherpa_onnx` was never on the build machine and so never shipped --
  which is precisely why it is now declared rather than left to luck.
- **`scripts/check_runtime_imports.py`** (new, wired into `build_runtime.ps1`):
  runs the built bundle and asks it directly. Engine-pack-owned modules must be
  **absent**; the deliberately-bundled ones that load native code must **import**,
  not merely resolve. It fails the build naming what broke and how to fix it.
  Verified red against the 2026-08-17 build (named all four) and green after.
- **`build_runtime.ps1`** no longer stages `tools\` and no longer takes
  `-FfmpegDir`/`-LibmpvDir`. That retires the undocumented ordering dependency
  where a Weather build failed unless another app had already built the runtime.
- **`scripts/StageMediaTools.ps1`** (new): the one implementation of media
  staging. Radio stages ffmpeg + libmpv; Studio stages both (ffmpeg for
  recording, libmpv for the player preview it has always shipped). Weather and
  Inkwell stage nothing. Staging is **opt-in**, so there is no per-app exclusion
  list to keep in step -- an app that declares nothing gets it right by default.

### Verified

- Both gates green on the rebuilt runtime; 288 build/structure tests pass.
- The engine-pack path now works where it could not before: with a real `vosk`
  package on `sys.path`, the frozen runtime imports it, loads `libvosk.dll` and
  calls into it. Before the change the broken frozen copy won every time.
- `is_vosk_available()` now answers False on a machine with an empty pack dir,
  so QUILL will offer the install instead of failing at use time.

### Still open

- `ffprobe` (Decision 1) is untouched and still 97 MB. It is genuinely used for
  M4B/M4A chapter marks and durations, so it needs the shared-library ffmpeg
  build priced before anything is dropped -- Phase 4/Stage 4, unchanged.
- Studio's `REQUIRED_COMPONENTS` declares only `("ffmpeg",)` but its build stages
  libmpv too. The build now matches its long-standing behaviour; the declaration
  is what should be corrected, and it wants a decision rather than a guess.
- Cast's `build_release.ps1` does not build the shared runtime at all, so it
  still inherits whatever another app produced. It needs the same treatment.
- Phase 3 (splitting the document layer out of core) is unstarted. Note that
  Phase 1 removed ~96 MB of the ~101 MB "Speech in" layer the original table
  proposed, so that layer no longer needs building -- the engine packs already
  are it.
