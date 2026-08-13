# Standalone product build tooling

The QuillVille apps all run the **same code** as QUILL — it lives in the
`quill` package (`quill.apps.radio`, `quill.apps.podcasts`,
`quill.apps.studio`, ...). This directory holds the per-product **packaging
shells** that freeze that shared code into standalone Windows products. Putting
the tooling here (instead of in separate wrapper repos) means QUILL's own repo
can compile and ship every standalone product, and the packaging can never
drift from the code it packages.

Each product folder is a self-contained build shell:

```
standalone/
  radio/            Quill Radio          -> quill.apps.radio
  weather/          Quill Weather        -> quill.apps.weather   (2.2.0, paired with radio)
  cast/             QUILL Cast           -> quill.apps.podcasts
  studio/           Quill Audio Studio   -> quill.apps.studio   (see note)
  inkwell/          Quill Inkwell        -> quill.apps.inkwell  (see note)
  runtime/          QuillVille Runtime   -> shared CPython used by every app
```

Two more folders are **not** build shells of the kind described below:
`beacon/` and `social/` (and the macOS radio port `radio-mac/`) hold apps whose
code is not yet in the `quill` package — see "Not yet migrated" at the end.

Per folder:
- `launcher.py` + `quill_<product>/__init__.py` — PyInstaller entry point.
  The tiny shim anchors `QUILL_APP_ROOT` (portable mode + bundled ffmpeg/mpv
  under `tools/`) and hands off to `quill.apps.<app>:main`. No feature code.
- `quill-<product>.spec` — onedir PyInstaller spec; `collect_all("quill")`
  brings the whole shared package (code + data), `collect_all("nacl")` brings
  the Ed25519 verifier; heavy ML deps QUILL uses elsewhere are excluded.
- `scripts/build_release.ps1` — renders docs, generates the bundled feedback
  token (required), bundles ffmpeg + libmpv, stages docs, builds the onedir,
  zips the portable, compiles the Inno installer. `$version` at the top is the
  single source of the product version and must match the app's `_VERSION` in
  `quill/apps/<app>.py`.
- `installer/quill-<product>.iss` — Inno Setup script (`/dAppVersion=`).
- `run-quill-<product>.bat` — dev launcher (`python -m quill.apps.<app>`).
- `docs/`, `assets/`, `CHANGELOG.md`, `README.md` — product docs and icon.

## Where a change gets documented (the per-app rule)

Every change is documented **with the product it belongs to**, at the time it
ships — never batched, never only in QUILL's files:

- A change to a companion app (Radio, Cast, Weather, Converter, Audio Studio,
  Beacon, Social) is documented in **that app's** `CHANGELOG.md` and, when
  user-visible, its `docs/` user guide / release notes / PRD.
- A change to QUILL proper is documented in the repo-root `CHANGELOG.md`,
  `docs/release notes/release<X>.md`, the user guide, and the PRD.
- A **shared** change (announcement service, QuillVille menu, tray hotkeys,
  self-update, dialog conventions) is documented in QUILL's files **and**
  gets a matching entry in every affected app's changelog — an app's user must be
  able to learn everything about their app from that app's own docs.
- Dates come from git evidence, not memory. Regenerate `.html`/`.epub` twins
  for any doc that has them.

## Building a standalone product

From the quill repo root, with `S:\QUILL\.venv` active (editable `quill`
installed) and the current branch checked out to what you want to ship:

```
pwsh standalone/radio/scripts/build_release.ps1
```

Artifacts land in `standalone/radio/dist/`: the onedir app, the portable zip,
and the setup installer. The build reads the **currently checked-out** quill
source via `collect_all("quill")`, so — as always — do not switch the quill
branch mid-build.

## Releases and the in-app updater

Each shipped product's updater polls its own GitHub repo
(`quill/apps/<app>.py: _REPO`). The build tooling lives here in quill, but
releases are still published to the product repo the updater points at (e.g.
`gh release create --repo Community-Access/quill-radio ...`). That repo is now
only a **release host** — no build tooling, no code. See
`docs/design/2026-07-20-radio-cast-consolidation-plan.md` for the update-safety
rules (never delete a live updater-target repo; archive instead).

## Quill Inkwell

`inkwell/` packages system-wide abbreviation expansion. It is the smallest app
in the family -- a keyboard hook, a matcher, and two dialogs -- so it bundles no
ffmpeg, no mpv, and no media or AI stacks.

One thing about it is unlike every sibling: it shares **live data** with QUILL
rather than only sharing code. Inkwell and QUILL read and write the same
`abbreviations.json`, so an installed build deliberately keeps its data in
`%APPDATA%\Quill`, and only a portable build (a `data` folder beside the exe)
moves the library onto the stick. Anything that changes where that file lives
changes both products at once.

Its icon is currently a placeholder copy of Weather's, and `inkwell` is not yet
in `RELEASED_APPS`, so it is developer-build-only until deliberately released.

## Audio Studio

`studio/` is recreated from the radio template (Audio Studio was folded
into `quill.apps.studio` but never shipped, so it has no wrapper repo and no
users). It builds the same way once its icon and product docs are in place.

## Not yet migrated

Beacon, Social, and the macOS radio port (QRM) are **separate apps** whose code
is not yet in the `quill` package; they need reverse-vendoring first (see the
family consolidation plan). They are not built from this directory yet.
