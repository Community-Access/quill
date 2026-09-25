# QUILL Lite integration — design

**Status: implemented, 2026-09-08.** This document records what was decided and
what actually shipped, including the four places the plan changed under contact
with the code. Where the two differ, the "what shipped" note is the truth.

## Problem

PR #1490 ("Add QUILL Lite: a notepad-scale alternative editor") by Steven Scott
(`doubletaponair`) adds a small editor-only sibling to the QUILL family. The
contributor self-contained the implementation — feature code, RTF scanner,
dialogs, speech path, single-instance inbox, recovery — and explicitly did not
apply one QUILL-side fix they isolated: `_TOM_TRUE = -9999999` in
`quill/ui/richedit_rtf_surface.py`, which `tom.h` defines as `tomUndefined`
rather than `tomTrue`, and which silently breaks every Rich Edit heading QUILL
creates.

Three decisions to make:

1. **How does the wrapper share code with the rest of the family?** Every other
   QuillVille app puts feature code in the shared `quill` package
   (`quill.apps.<name>`) and keeps `standalone/<app>/` as a thin product shell.
   PR #1490 breaks that: it duplicates the TOM-based Rich Edit surface and the
   RTF safety scanner wholesale, even though both already live in `quill/`.
2. **Do the QUILL-side fixes the contributor isolated land in the same PR?**
   They affect every QUILL user today.
3. **Does QUILL Lite ship as a full sibling (four artifacts, four docs, shared
   runtime) or as something smaller?**

## Decision: thin shell + `quill.apps.lite`, full sibling shape

QUILL Lite becomes a full sibling of Radio/Cast/Weather/Studio/Inkwell. **All**
wx and feature code moves into the shared package; the wrapper at
`standalone/quilllite/` is an entry point, an icon, installers and docs, exactly
like Inkwell's. Both QUILL-side fixes ship in the same change.

### What shipped differently from the plan, and why

Four deviations, each recorded because the plan said otherwise.

1. **Nothing feature-shaped stayed in the wrapper.** The plan put dialogs,
   settings, recovery and the inbox under `standalone/quilllite/quill_lite/`.
   They are all in `quill/` instead, because the repository's gates — GATE-11,
   GATE-13, GATE-14, the dialog registry, the F1 audit, GATE-REACH — scope to
   `_REPO_ROOT / "quill"`. A surface no gate can see is a surface that rots;
   Cast shipped an unreachable first-run dialog for two releases exactly that
   way. `standalone/quilllite/quill_lite/` is now two files, both shims.

2. **Documents are MDI children of one window, not separate top-level windows**
   (Jeff, mid-implementation). Numbering is the point: "document 3" is a name a
   person can hold. The cost — MDI children do not appear in Alt+Tab — is real,
   was raised before building, and is carried by binding all four routes
   (Ctrl+F6, Ctrl+Tab, Alt+1..9, the Window menu) and by leading every title
   with its number.

3. **The scope grew, deliberately and on Jeff's instruction**, from "the editor
   and nothing else" to "the editor, with everything switchable". Selection,
   numbered bookmarks, Describe Character, the copy tray, the collector, the
   clip library, abbreviations, the line and case tools, printing, the command
   palette, session restore and encoding conversion all landed, and
   `View > Customize Features` is what keeps that from making the product big:
   turning an area off removes its menu **and** its keys.

4. **QUILL Lite is never allowed to be ahead of QUILL** (Jeff, twice, and it is
   now the governing rule — see below). Everything QUILL Lite needed that the
   editor could not do was added to the editor in the same change.

## Code architecture, as shipped

### Layer A — shared `quill/` package

**Fixes to `quill/ui/richedit_rtf_surface.py`:**

- `_TOM_TRUE` `-9999999` → `-1`, with `_TOM_UNDEFINED` named so nobody
  re-derives the old value as "true", and the measurement in a comment
  (`Bold=-9999999` → `Weight=400`; `Bold=-1` → `Weight=700`, on Riched20
  10.0.26100).
- `caret_format_description` now reads through a new `_format_range()`, which
  probes the character *after* a collapsed caret. A collapsed TOM range reports
  the formatting of the character *before* it, so standing at the head of a
  heading described the paragraph above it.
- `create_richedit_rtf` builds `RichEditDocument` rather than `QuillRichEdit`.

**New shared modules:**

| Module | What |
|---|---|
| `quill/ui/richedit_editing.py` | `RichEditDocument` — a `QuillRichEdit` plus text mode, wrap, zoom, background, whole-story recolour, bullets, line spacing, the point-size ladder, heading enumeration |
| `quill/ui/main_frame_rich_paragraph.py` | QUILL's own Justify / line spacing / Grow / Shrink / Paste Text Only handlers |
| `quill/core/numbered_bookmarks.py` | Nine slots that move with the text. Shared, not under `lite/`, so QUILL can adopt it |
| `quill/core/lite_surface_help.py` | The F1 purpose catalogue |
| `quill/core/lite/` | `paths`, `settings`, `recovery`, `commands`, `filetypes`, `textfile`, `inbox`, `backups`, `features` — all wx-free, all strict-typed |
| `quill/apps/lite*.py` | The shell, the window and its eight mixins, the dialogs, preferences, printing, services |
| `quill/tools/lite_help_audit.py` | GATE-LITE-HELP |

**Deleted during implementation:** a first draft of `quill/core/lite/texttools.py`
duplicated `quill.core.format_ops` and `quill.core.transforms`. It was removed
and the callers point at QUILL's own — two implementations of "sort these lines"
is two places for them to disagree about what a trailing newline means.

### Layer B — `standalone/quilllite/`

`quill_lite/__init__.py` (anchors `QUILL_APP_ROOT` for a portable build, hands
off to `quill.apps.lite:main`), `quill_lite/__main__.py`, `launcher.py`,
`run-quill-lite.bat`, `pyproject.toml`, `quill-lite.spec`, two `.iss` installers
plus their edition markers, the generated icon, `scripts/build_release.ps1`,
`scripts/render_docs.ps1`, four docs, `LICENSE`, `README.md`, and two probes.

### Cross-cutting registrations

- `standalone/runtime/app-profiles.json` — a `quilllite` row declaring no
  components and no layers, with a note on *why* an editor reaches neither the
  documents layer nor the spellcheck layer.
- `scripts/build_native_launcher.py` — a `quilllite` product (`QuillLite.exe`).
- `standalone/studio/scripts/build_portable.py` — a `quilllite` product,
  `dep_groups=("ui", "feedback")`, no engines, no ffmpeg, no mpv.
- `scripts/build_app_icons.py` — the `_quilllite` glyph and its `APPS` entry.
- `quill/tools/platform_report.py` — GATE-LITE-HELP joins the roster.
- `tests/unit/ui/test_app_menu_accelerators.py` — both QUILL Lite menu files.

## The governing rule: QUILL Lite may never be ahead of QUILL

Stated by Jeff during implementation and applied retroactively across the whole
change. If QUILL Lite needs something the editor cannot do, the capability goes
into the **shared** package and the editor gets a way to reach it in the same
change. A feature the small product has and the big one does not is backwards,
and worse, invisible — nobody opens QUILL and notices the absence of a thing
they have only ever seen elsewhere.

What that cost, concretely:

- `create_richedit_rtf` builds the extended surface, so every QUILL tab gains
  the paragraph and view capabilities by construction.
- QUILL gained six commands whose capability was already in the surface with
  nothing bound to it: **Justify**, **single / one-and-a-half / double line
  spacing**, **Grow Font**, **Shrink Font**, plus **Paste Text Only**, which
  neither product had. Keymap, feature map, registrations, menu rows, bindings,
  the id map, and a regenerated `docs/keyboard-reference.md`.
- Numbered bookmarks live in `quill/core/numbered_bookmarks.py`.
- The duplicated text tools were deleted.

**Where the two diverge, they diverge in writing.** QUILL takes `Ctrl+Alt+J` and
`Ctrl+Alt+V` where QUILL Lite uses WordPad's `Ctrl+J` and `Ctrl+Shift+V`, because
`Ctrl+J` has been Set Temporary Bookmark and `Ctrl+Shift+V` has been Preview in
QUILL for far longer. An existing binding somebody's hands already know outranks
a new command's convention; the reason is a comment in `keymap.py`.

Still open, and named rather than implied: QUILL does **not** yet expose
numbered bookmarks, the copy-tray-style clip chooser QUILL Lite uses, or the
File Format dialog. The shared code is in place for all three; the QUILL-side UI
is not, and that is a follow-up rather than a claim.

## Release packaging

| Artifact | Built from | Output |
|---|---|---|
| Full installer | `installer/quilllite.iss` | `QuillLite-Setup-Shared-1.0.0.exe` |
| Lite thin installer | `installer/quilllite-lite.iss` | `QuillLite-Lite-Setup-1.0.0.exe` |
| Full portable | `build_portable.py --product quilllite` | `QuillLite-Portable-1.0.0.zip` |
| Companion zip | the launcher without an interpreter | `QuillLite-Companion-1.0.0.zip` |

The artifact names spell the product as one mixed-case word (Jeff, finalizing,
2026-09-08): `QUILL Lite` is spoken by a screen reader as a name, where
`Quill-Lite` is read out punctuation and all — and the hyphenated thin
installer would have been "Quill dash Lite dash Lite dash Setup". The first
build ran before the rename, so the measured sizes below carry the old names;
nothing had been published under them.

Shared QuillVille Runtime, reused. Neither ffmpeg nor libmpv staged, and the
build strips any a sibling left in the communal work area so build order cannot
change what ships. Code signing opt-in via `-Sign` / `QUILL_SIGN=1`.

The full installer offers an **optional** file association: an *Open With* verb
for `.txt` and `.rtf`, never a default handler.

Releases publish to `Community-Access/quill` with a `QuillLite-*` asset prefix
— a deviation from the siblings' per-app repos, recorded and revisitable.

## Verification

Run and passing at the time of writing:

- `ruff check` / `ruff format --check` clean; `mypy quill/core/lite` clean.
- GATE-11, GATE-13, GATE-14, GATE-EC, GATE-REACH, the banned-pattern gate, the
  dialog registry, GATE-KEYREF, GATE-HELPREF and the new GATE-LITE-HELP.
- 38 wx-free unit tests for the QUILL Lite cores, 19 for the F1 catalogue and the
  stricter control-help check, and 3 new regression tests in
  `tests/unit/ui/test_richedit_rtf_surface.py` pinning both PR #1490 fixes
  against a fake TOM that models the real control's behaviour (assigning
  `tomUndefined` is *accepted* and changes nothing, which is why the bug was
  silent).
- `standalone/quilllite/tests/probe_live.py` — 24 live checks against a real
  `RICHEDIT50W`, all passing: the surface, both fixes, text mode, the theme
  never reaching the file, document numbering, bookmark tracking, feature
  switching, and five byte-exact round trips.
- `standalone/quilllite/tests/repro_tom_true.py` — the contributor's standalone
  reproduction, kept runnable, with a header noting the bug is now fixed.
- `python -m quill.tools.platform_report` — every gate, including the
  `docs-artifacts` gate, which is why the four QUILL Lite docs and the four
  regenerated top-level references all ship with their HTML and EPUB.
- `pytest tests/unit tests/stability -n 8 --dist loadgroup` — 17,551 passed,
  34 skipped, 0 failed.

**Built and measured**, on this machine, 2026-09-08, and rebuilt the same day
under the final names against a freshly built runtime:

| Artifact | Size |
|---|---|
| `QuillLite-Setup-Shared-1.0.0.exe` | 113.9 MB |
| `QuillLite-Lite-Setup-1.0.0.exe` | 2.8 MB |
| `QuillLite-Portable-1.0.0.zip` | 92.2 MB |
| `QuillLite-Companion-1.0.0.zip` | 0.2 MB |

The four pre-rename artifacts were deleted rather than left beside these: two
sets of installers for one product, differing only in the punctuation of their
names, is precisely the ambiguity the rename was meant to remove.

The native launcher compiled (MSVC 14.44, 24 KB `QuillLite.exe`), the portable
bundle's own interpreter was run and reported `quill 1.0.0 | wx 4.3.1 | frames 1
| title "1: Untitled - QUILL Lite (plain text)" | native True`, both installers
compiled under Inno 7, and `portable-inventory.json` was adopted from that build
and re-verified against it.

### One defect this shipped, and the guard added for it

The first full installer compiled, installed, and then failed on launch with
**`No module named quill.apps.lite`**.

The shared QuillVille Runtime is a PyInstaller onedir carrying its **own frozen
copy of the quill package**, and the build reused an existing one
(`-SkipSharedRuntime`) that had been built on 28 August -- three weeks before
`quill/apps/lite.py` existed. Nothing in the build noticed: ISCC compiled a
perfectly valid installer around a runtime that did not contain the app it was
an installer for.

The lesson is the general one: **compiling and installing are not evidence that
the thing runs.** So `scripts/BuildEnv.ps1` gained
`Assert-QuillRuntimeHasModule`, which every sibling can call and QUILL Lite's
`build_release.ps1` now does. Two checks, cheapest first: the module's source
file is present in the frozen tree (universal, instant, and exactly what was
missing), and -- with `-ProbeArgs "--check"` -- the runtime is asked to actually
*run* the module and exit. Verified both ways: it passes on the rebuilt runtime
and rejects a module that does not exist.

The runtime was rebuilt, pruned, marker-stamped and re-gated
(`check_runtime_imports`: 21 modules, all correct), and the full installer
recompiled around it. `QuillVilleRuntime.exe -m quill.apps.lite --check` now
reports `native rich edit: True`, `heading applied: True`, and
`describe: Segoe UI, 20 point, heading 1, bold` -- which is the tomTrue fix
working inside the frozen runtime, not just in the checkout.

### Closed 2026-09-08: the runtime is published, and the guard was not deep enough

The thin installer downloads the runtime from the `runtime-latest` GitHub
release. Two things turned out to be wrong with that, and both are now fixed.

**The tag had never existed.** `gh release view runtime-latest` answered
"release not found" -- not a stale asset, no asset at all, so the Lite edition
of *every* app in the family (seven installers, not just QUILL Lite) downloaded a
404. `build_runtime_installer.ps1 -Publish` creates the release when it is
absent, which is what published it: tag `runtime-latest`,
`QuillVille-Runtime-Setup.exe` (114.0 MB, runtime `3.13.20260908`), marked
`--latest=false` so it cannot hijack the editor's release train (verified: the
repository's latest release is still `v0.6.0`). Confirmed live by the gate's own
opt-in check, `QUILL_CHECK_RELEASE_ASSETS=1 pytest
tests/unit/structure/test_lite_installer_assets.py` -- 4 passed, the fourth
being the HEAD request that had nothing to answer it before.

**`Assert-QuillRuntimeHasModule` asks whether the module is present, not
whether it is current.** Before publishing, the frozen `quill` package in the
built runtime was diffed against the working tree: 28 differences, including
two QUILL Lite modules missing outright (`lite_check.py`,
`lite_window_selection.py`) and changed `lite.py`, `lite_window.py`,
`keymap.py` and `selection.py`. The guard passed on that runtime, because
`quill/apps/lite.py` was there -- an older copy of it. The same lesson one level
down: *present* is not *current*, and a build that reuses a runtime with
`-SkipSharedRuntime` inherits whatever that runtime last froze. A full rebuild
was done instead, after which the frozen tree matches source exactly.

That diff was run by hand, which is not a gate, so it became one:
**`scripts/check_runtime_freshness.py`** compares the frozen
`_internal/quill` tree against the checkout's `quill/` and names every
difference as **stale** (present, contents differ), **missing** (written after
the runtime was built) or **orphan** (deleted after it was built, still
shipping). Only `.py` files are compared -- the question is whether the *code*
is the code -- and three things are excluded with their reasons stated in the
source: `__pycache__`/`.mypy_cache`, the CMake `build` trees under
`quill/native`, and `_feedback_token.py`, which the build itself writes into
the checkout immediately before packaging.

It is wired in twice. `Assert-QuillRuntimeHasModule` now runs it between the
presence check and the probe -- deliberately *before* the probe, because a
stale runtime runs its stale module perfectly well, so `--check` passing proves
nothing about currency. And `build_runtime_installer.ps1` runs it before ISCC,
which is the placement that matters most: every other staleness ships to one
app's users, and that script publishes to the moving tag *every* Lite installer
in the family downloads from. There is no rebaseline flag, because the answer
is never "record this as expected" -- it is always "rebuild the runtime".
Nine tests in `tests/unit/scripts/test_check_runtime_freshness.py` pin each
finding kind, each exclusion, and both exit codes.

**The `dateutil` inventory difference was the reverse of what this document
recorded, and the fix was to put the entry back.** The build machine had it
removed from `runtime-inventory.json` as an uncommitted edit; the fresh build
produced `dateutil` and the inventory gate failed it as undeclared. It arrives
transitively and legitimately (`pip show python-dateutil` names arrow, celery,
csvw, Mastodon.py and pandas as requiring it), and the *committed* inventory
declares it -- so the uncommitted deletion was the error. Restoring the line
made the gate pass without weakening it, which rebaselining would have done.

## Not yet done, and not claimed

- **A JAWS and NVDA pass by hand.** The checklist is written --
  `docs/qa/quilllite-signoff.md`, 89 numbered steps in the house format, with a
  fifteen-minute subset named at the top -- but it needs a person and a screen
  reader. Matching Studio (#839) and Inkwell, this is not required for the
  change to merge but **is** required for the release to publish. It is the only
  item here a machine cannot close.
- **The QUILL Lite artifacts themselves are built but not published.** Only the
  shared runtime went to GitHub, because that one was already broken for the
  whole family; the four `QuillLite-*` files are sitting in
  `standalone/quilllite/dist/` waiting on the screen-reader pass above. That
  ordering is the same one Studio (#839) and Inkwell were held to, and it is
  the reason the artifacts are not simply pushed once they build cleanly.
- **The site sync, and why QUILL Lite is still not in it.** The earlier note
  here said QUILL Lite would join `scripts/sync_site_radio_docs.py` "after its
  first real render". The renders now exist, and it still has not, because the
  sync is not the obstacle: `docs/site/` has no QUILL Lite page and nothing
  linking to one, and the same is true of Cast, Weather, Studio and Inkwell --
  the site carries doc pages for Radio and the editor alone. Adding one app's
  pages to a script named for another, with no page to land on, would be a new
  website section written sideways. The honest shape is a site pass over all
  the siblings at once and a sync script that is no longer Radio-only; that is
  a separate piece of work and it is not started.

## Documents this change kept current

Named so a reader can check rather than trust:

- **Generated, regenerated:** `docs/keyboard-reference.md` (GATE-KEYREF),
  `docs/f1-help-reference.md` (GATE-HELPREF), `docs/CONTROL_REFERENCE.md`
  (`build_docs.py`), and four fixture snapshots (dialog inventory, QUILL Lite
  help inventory, surface reachability, module-size budgets).
- **`CLAUDE.md`** — the help-gate roster is nine, `quill/apps` is described, and
  the "QUILL Lite may never be ahead of QUILL" rule is written down where the
  next person will read it.
- **`docs/Product Requirement Documents and Specifications/QUILL-PRD.md`** —
  "One Editor, Every Format" now records the six commands QUILL gained, the two
  TOM bugs and their measurements, and the deliberate Ctrl+Alt+J / Ctrl+Alt+V
  divergence from QUILL Lite.
- **`quill/core/help/topics.json`** — seven new F1 topics, so
  `check_help_coverage`'s `format:6` warning is gone.
- **`standalone/README.md`** — QUILL Lite listed as a build shell.
- **QUILL Lite's own four:** `docs/prd.md`, `docs/userguide.md`,
  `docs/release-notes-1.0.md`, `docs/CHANGELOG.md`, plus `README.md` and
  `assets/README.md`.

## Provenance

QUILL Lite is derived from PR #1490 by Steven Scott (`doubletaponair`), MIT, with
the reasoning in the upstream files preserved in comments. The two QUILL-side
fixes are attributed in the PRD, the changelog and the release notes so the
contributor's authorship stays intact.
