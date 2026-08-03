# Rewriting QUILL in Rust: honest assessment and staged plan

Date: 2026-08-02
Status: analysis / decision document. Nothing here is committed work.

## 1. Verdict first

A full Rust rewrite of QUILL would be a **large negative-value project**, and the
"save space" motivation is the weakest of the possible justifications for it.
The binary-size problem is not caused by Python, and the thing a rewrite would
put at risk -- native screen-reader behavior -- is the entire product.

A **targeted** use of Rust, on the other hand, is genuinely valuable and low
risk: compiled sidecar modules for the handful of CPU-bound paths, and possibly
a Rust rewrite of one small standalone app as a controlled experiment.

Short version: do not rewrite the app. Do adopt Rust in specific places.

## 2. What "save space" actually means here, with numbers

Measured 2026-08-02 in this tree.

Source size:

| Layer | Lines of Python |
| --- | --- |
| quill/ui | 136,337 |
| quill/core | 134,853 |
| quill/apps | 19,204 |
| quill/tools | 8,982 |
| quill/io | 8,785 |
| quill/platform | 4,920 |
| quill/stability | 2,019 |
| Total (1,165 files) | 319,702 |

Ship size (dist/):

- QuillVille-Runtime-Setup.exe -- 233 MB (the shared runtime)
- Quill-for-All-Lite-Setup-1.0.0.exe -- 2.3 MB
- QUILL-Audio-Studio-Lite-Setup-2.2.0.exe -- 2.1 MB

Two things follow from that.

**First, the shared-runtime work already solved the duplication problem.** The
per-app installers are ~2 MB. The family of apps (QUILL, Audio Studio, Radio,
Cast) no longer each carry their own Python and wx. The remaining question is
only what is inside the 233 MB runtime.

**Second, most of the 233 MB is not Python code, and Rust does not remove it.**
Roughly, in order of weight: wxWidgets (the installed `wx` package alone is
~62 MB), then the native/vendored payloads (ffmpeg, liblouis, spell
dictionaries, sound packs, and whatever speech assets are still bundled rather
than pulled from assets-v1), then C-extension wheels (Pillow, cryptography,
numpy where present), and only then the CPython runtime plus stdlib plus
QUILL's own bytecode. QUILL's 320k lines of Python compile to well under 20 MB
of `.pyc`.

So a perfect, flawless Rust rewrite plausibly recovers:

- CPython runtime + stdlib: ~35-50 MB
- pure-Python dependency tree: ~20-40 MB
- QUILL's own bytecode: ~15 MB, replaced by maybe 20-40 MB of Rust binary
  (Rust binaries are not small once you link a GUI toolkit, audio, TLS, and
  regex)

and does **not** recover: the GUI toolkit (you still ship one), ffmpeg,
liblouis, dictionaries, models, sound packs, icons.

Realistic net: **maybe 60-90 MB off a 233 MB runtime, for a multi-year
rewrite.** The same 60-90 MB is available for a few weeks of payload work
(see section 6). That is the honest arithmetic, and it is decisive on its own.

## 3. The real blocker: accessibility, and we already have the evidence

QUILL is not a text editor that happens to be accessible. It is an
accessibility product. Its differentiator is that JAWS and NVDA behave
*correctly* in it -- caret tracking, say-line on arrow, indentation
announcements, selection reporting, table navigation, browse mode where
appropriate, focus and modal contracts.

That behavior does not come from our code. It comes from wxWidgets wrapping
**real Win32 controls** (RICHEDIT50W, SysListView32, SysTreeView32, standard
dialogs) that JAWS and NVDA have had two decades of per-control heuristics,
scripts, and workarounds tuned against. We inherit that for free.

Every serious Rust GUI option gives that up:

- **egui, iced, Slint, Xilem, Dioxus-desktop** -- canvas-drawn. No native
  controls at all. Accessibility comes from AccessKit, which is real,
  well-engineered, and improving, but it exposes a synthesized UIA tree. NVDA
  support is decent. JAWS support is partial and inconsistent, and JAWS is the
  larger share of our paying, employed users.
- **Tauri / WebView2** -- accessibility is web accessibility, which is mature,
  but it is a completely different interaction model: browse mode, virtual
  cursor, a different caret story, different keyboard conventions. It is not
  "the same app in Rust", it is a web app in a window. It also does not save
  space in any meaningful way (WebView2 runtime, plus we would still ship
  everything else).
- **Rust + windows-rs driving real Win32 controls directly** -- this is the only
  option that preserves the accessibility we have. It also means writing our
  own widget layer, layout engine, and dialog framework from scratch. That is
  wxWidgets. We would be reimplementing wxWidgets in Rust, badly, for years.

And we have already run this experiment, at small scale, and lost. The
Scintilla/STC editor surface -- a non-native, custom-drawn text control -- was
NVDA-only. Three separate JAWS bridge attempts failed against a live JAWS and
were removed on 2026-07-03 (see the post-mortem in edit.md). Issue #813 was
finally fixed by going *more* native, not less: `SES_EMULATESYSEDIT` plus a
borderless editor.

The lesson generalizes exactly: **when we move off native Windows controls,
JAWS stops working, and we cannot bridge our way back.** A canvas-drawn Rust UI
is that same bet, taken across the entire application at once, with no fallback
and no way to revert incrementally.

That single paragraph is, in my honest opinion, the end of the argument for a
UI rewrite. Everything else below is secondary.

## 4. The other costs, briefly

- **Ecosystem.** wxPython, prismatoid, accessible_output2, comtypes, pyenchant,
  python-docx, feedparser, paramiko, pymupdf, PyNaCl, llama-cpp-python,
  faster-whisper, the AI provider SDKs, pyobjc for the macOS rich-text bridge.
  Rust has good equivalents for maybe half, weak ones for a quarter, and
  nothing for the accessibility bridges -- which are the ones that matter most.
- **Velocity.** QUILL is currently shipping features weekly (Radio 2.1, Audio
  Studio, podcasts, the Vault, competitive-parity work). A rewrite means a hard
  feature freeze for 18+ months while producing something users experience as
  *worse*. This is the textbook second-system trap, and rewrites of this shape
  have killed better-funded products.
- **Bug re-litigation.** 320k lines encode hundreds of small screen-reader
  workarounds discovered the hard way, most of them undocumented because they
  are one-liners. A rewrite rediscovers all of them, in production, on users.
- **Quillins.** The extension model is Python and Node. A Rust host does not
  remove the need to embed a Python interpreter for bundled Quillins -- so we
  would ship CPython anyway, and lose most of the claimed space saving.

## 5. Where Rust genuinely pays, starting now

These are real, incremental, reversible, and worth doing regardless of any
rewrite decision. Build them as `PyO3` + `maturin` extension modules or as
standalone sidecar executables. No UI involvement, no accessibility risk.

Ranked by value-to-effort:

1. **Audio DSP for Audio Studio.** Peak/waveform generation, silence
   detection, normalization scanning, chapter-boundary detection. Currently the
   slowest visible operations on long files. Rust gives 10-50x and removes the
   numpy dependency from that path.
2. **Vault / full-text search and indexing.** As the Accessible Vault grows,
   link graph construction, backlink resolution, and incremental full-text
   search are exactly what Rust is good at (see `tantivy`). A Python
   implementation will be the thing that makes a large vault feel slow.
3. **Large-file editor backend.** Rope/piece-table for the document buffer,
   line indexing, and diff. Keeps the wx control as the *view* -- no
   accessibility exposure changes -- while removing the Python-side cost of
   very large documents. This is the highest-value one for the core product,
   and it is invisible to screen readers by construction.
4. **The UIA table provider.** Already native C++ and already a maintenance
   problem (build broke, issue #823). Rust + `windows-rs` is a strictly better
   home for that code than hand-rolled C++, with the same COM surface.
5. **Braille translation glue and BRF pipeline.** Deterministic, hot, pure
   transformation. Good candidate, low risk.
6. **Watch folder / file scanning.** `notify` is better than what we can do in
   Python, and this path currently costs threads.

Each of these is a self-contained PR. Each can be reverted by deleting one
module and restoring the Python path behind it. That is the correct way to
introduce a second language into a shipping product.

## 6. The space work that actually pays, and is not Rust

If the goal is genuinely "make the download smaller", these dominate a rewrite
by an order of magnitude of effort-to-megabyte:

1. **Finish assets-v1 unbundling.** Anything model-shaped, dictionary-shaped,
   or voice-shaped that is still in the runtime should be on-demand. This is
   already a known program with known mechanics.
2. **Audit the 233 MB runtime, item by item.** Nobody has published a
   per-directory breakdown of what is actually in it. That report is a day of
   work and will almost certainly find 30-60 MB of things nobody intended to
   ship (test suites inside wheels, unused locales, duplicate DLLs, `.pyi`
   stubs, `__pycache__`, unstripped debug symbols, sample data).
3. **Trim wx.** wxPython ships locale catalogs and unused libraries. A
   PyInstaller/Inno exclusion pass is cheap.
4. **Nuitka -- unproven, and weaker than it first looks.** Correction to an
   earlier draft of this document: Nuitka is *documented* as Inkwell's intended
   source-protection strategy (`S:\INKWELL\docs\LICENSING.md`), not
   demonstrated working. QUILL has no Nuitka build script, config, or log in
   any repo, and `docs/planning/roadmap.md:234` already declares freeze/compile
   packaging (PyInstaller / Nuitka) **out of scope** -- embedded CPython + Inno
   Setup is the shipping model. An attempt on QUILL reportedly failed.
   Independent of whether the failure is fixable, the space case is weak:
   Quillins are Python and Node extensions, so a compiled QUILL still ships a
   live CPython for the extension host. Nuitka would trade ~15 MB of our
   bytecode for a larger native binary, and buy startup time and IP protection
   rather than megabytes. Treat it as a startup-latency and licensing tool, not
   a footprint tool. See section 6a for the likely failure causes.
5. **ffmpeg.** Ship the smallest viable build, once, shared across Radio, Cast,
   and Audio Studio. Full ffmpeg is enormous and we use a fraction of it.

Expected recovery from 1-5: comparable to the theoretical Rust-rewrite saving,
at roughly 1% of the cost and 0% of the accessibility risk.

**External benchmark.** A comparable Windows screen-reader-first product built
the same way -- one shared embedded CPython plus satellite apps -- ships a
**119 MB runtime (2,638 files, CPython 3.12.8)**. Ours is 233 MB. Part of that
gap is legitimate (we bundle ffmpeg, liblouis, braille tables, sound packs and
dictionaries that a smaller product either omits or installs separately), but a
~114 MB delta against a directly comparable build is strong evidence that the
runtime audit will find real slack.

That same comparison confirms section 2's argument from the other direction:
the product in question balloons to roughly 2 GB installed from a 322 MB
installer, because ~20 of its 24 apps each carry a duplicate ~50 MB
PyInstaller bundle with identical wxPython, CPython and OpenSSL. That is the
exact failure mode the QuillVille shared-runtime work already eliminated. The
packaging battle was won at the distribution layer, not the language layer --
which is precisely why the language layer is the wrong place to fight it again.

## 6a. Why the Nuitka attempt probably failed

**Probe result (2026-08-02): `quill/core` compiles cleanly.** A scoped run --
`--module quill\core --include-package=quill.core`, with `--nofollow-import-to`
for wx, pytest and the heavy optionals, `--disable-ccache`, Nuitka 4.1.2 on
CPython 3.13.14 with MSVC 14.3 -- produced `core.cp313-win_amd64.pyd`, exit 0.
The compilation report records **638 modules compiled, 0 missing modules, 0
warnings**, linking 642 C object files. Note that `comtypes` was *not*
excluded from that run.

That is a strong, concrete result: the entire pure-domain layer (637 files,
134,853 lines) is Nuitka-clean today. Whatever failed, it is not the core.
Suspicion moves decisively to the wxPython/UI layer, the `python -m quill`
entry point, or the full-application link step.

No log, script, or config from the original attempt survives anywhere under
`S:\`, so the ranking below remains prediction for the layers not yet probed --
with causes 1, 3 and 6 now measured and cleared *for the core layer only*:

1. **comtypes generates COM wrappers at runtime** -- partly mitigated already.
   `comtypes.client` *writes* generated wrapper modules on first use, and a
   compiled build has no writable, importable `comtypes.gen`. QUILL already
   handles the writability half: `quill/platform/windows/comtypes_setup.py`
   redirects `gen_dir` to a per-user data folder and falls back to
   `gen_dir = None` (in-memory codegen, no disk write). That is a good design
   and it removes the usual frozen-build failure. What it does *not* fix is
   static analysis: the generated modules do not exist at compile time, so
   Nuitka cannot see them, and anything that imports from `comtypes.gen` by
   name will fail. Downgraded from "top suspect" to "likely, but survivable".
2. **The link step ran out of resources.** 1,165 modules and 319,702 lines is a
   very large Nuitka job: hours of compile, many GB of RAM, and thousands of
   object files hitting the MSVC linker. `LNK1102`, an out-of-memory kill, or
   an apparent hang are all normal at this size and read as "it failed" without
   a clear error.
3. **Dynamic imports are invisible to static analysis.** Quillins, optional
   components, lazy engine loading, provider registries, and `importlib` by
   name are the architecture. Nuitka compiles what it can see; everything else
   needs explicit `--include-module` / `--include-package`, and the failure
   shows up at runtime as import errors, not at compile time.
4. **wxPython standalone.** The `wx` plugin exists, but wx 4.2.5 plus
   `wx.html2` (WebView2), `wx.stc`, and the accessibility layer is a heavy
   standalone case; typical symptom is a clean compile and a runtime failure on
   missing DLLs or data files.
5. **Screen-reader bridges load DLLs by relative path.** prismatoid and
   accessible_output2 (via libloader) resolve native libraries relative to
   their package directory, which does not survive compilation without
   `--include-data-dir`.
6. **Guarded optional imports still get analyzed.** llama-cpp-python, paramiko,
   pyenchant, faster-whisper and friends are `try/except ImportError` at
   runtime but are still followed at compile time unless excluded with
   `--nofollow-import-to`.

Also worth verifying before budgeting: `S:\INKWELL\docs\LICENSING.md:62` states
that Nuitka Commercial is required for `--onefile`. My understanding is that
`--onefile` ships in the open-source build and Commercial adds source/constant
protection features. That line should be checked against current Nuitka
licensing before it drives a purchase.

Next step now that the core probe is green: repeat it one layer out --
`quill/io`, then `quill/platform`, then a `--standalone` build of the real
`quill/__main__.py` entry point with the wx plugin enabled. Always pass
`--report=` and tee stdout/stderr to a file; the report's missing-module list
is what turns "it seemed to fail" into a specific cause. The UI-layer probe is
the one that matters, and it is also the one most likely to take hours and
stress the linker, so run it detached.

## 7. Future-state read (3-5 years)

Being honest about what could change my answer:

- **AccessKit reaching first-class JAWS support** is the single variable to
  watch. If Vispero ships real, tested support for AccessKit-provided UIA trees
  -- not "it technically exposes a tree", but say-line, caret tracking, and
  browse mode behaving correctly -- then canvas-drawn toolkits become viable
  for *new* accessible apps. Track AccessKit releases and JAWS release notes.
  Even then, it does not justify rewriting QUILL; it would justify choosing
  Rust for something greenfield.
- **wxWidgets stagnating or wxPython falling behind Python releases** would be
  a real forcing function. It has not happened; wxPython 4.2.5 is current and
  we are on 3.12/3.13. Watch it, do not pre-empt it.
- **Windows itself deprecating the classic common controls** would break the
  bet. There is no sign of it, and Microsoft's own accessibility posture makes
  it unlikely this decade.
- **Python packaging improving** (free-threading, better bundling, smaller
  runtimes) cuts the other way and shrinks the rewrite's remaining upside.

My honest expectation: in five years, the correct architecture for QUILL is
still "native Windows controls for anything a screen reader touches, with
compiled hot paths behind them." The language of the hot paths is the part
that should change. The language of the UI should not.

## 8. If you want to test the Rust thesis anyway

Do not test it on QUILL. Test it on **quill-radio**.

Rationale:

- It is a separate repo and a separate product, so failure costs nothing.
- Its real UI surface is small: lists, a tree, buttons, a search field, a few
  dialogs. It is mostly lists. That is the *best* case for AccessKit.
- Its vendored Python line count (282,928 across 1,032 files) is misleading --
  almost all of it is vendored QUILL. The genuinely radio-specific code is a
  small fraction, which is what a rewrite would actually have to reproduce.
- Download size is most visible to users on the small standalone apps, so the
  win, if it exists, shows up where it is most appreciated.
- It has a live, engaged user base that will report screen-reader breakage
  quickly and specifically.

Proposed experiment, time-boxed to two weeks, with a hard kill gate:

- Week 1: Rust + `egui`/AccessKit (or Slint) spike -- station list, favorites
  tree, search field, play/stop, volume. No streaming engine, no persistence.
- Week 2: **Live screen-reader validation** on JAWS 2026 and NVDA 2026.x.
  The gate is not "it announces something". The gate is: arrow through the
  station list and hear each station once, cleanly, with no double-speaking, no
  focus loss, and correct position-in-list reporting; Tab order announced
  correctly; the search field behaving like an edit field.
- Kill gate: if JAWS fails any of those, stop. Write the result up, keep the
  spike as a reference, and close the question for another year.

Cost: two weeks. Value: converts a permanently open architectural question into
a documented, evidence-based answer -- which is exactly what the STC/JAWS
post-mortem did, and that turned out to be one of the most useful documents in
the repo.

## 9. Recommendation

1. **No** to rewriting QUILL, Audio Studio, Cast, or the shared runtime in Rust.
2. **Yes** to Rust for compiled hot paths, starting with Audio Studio DSP and
   Vault indexing. One PR each, PyO3, behind a Python fallback.
3. **Yes** to the runtime-size audit and the assets-v1 finish -- that is the
   actual answer to "save space", and it is weeks not years.
4. **Optionally yes** to the two-week quill-radio spike, purely as an experiment
   with a hard accessibility kill gate, if the curiosity is worth two weeks.
5. **Track** AccessKit + JAWS interop. Revisit this document if that changes.

The instinct behind the question is a good one -- the runtime is too big and
Python is not free. The fix is payload discipline plus a few compiled modules,
not a new language for the UI. The accessibility surface is the one asset we
cannot rebuild, and it is precisely the asset a rewrite would spend first.
