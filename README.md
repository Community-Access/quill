# QUILL for All

[![Contributors](https://contrib.rocks/image?repo=Community-Access/quill)](https://github.com/Community-Access/quill/graphs/contributors)

**QUILL for All** is an open-source, accessibility-focused editor from
Community Access. It helps people write, edit, convert, compare, and publish
documents in a screen-reader-friendly environment.

**QUILL** stands for **Quality, Usable, Inclusive, Lightweight, Literate**:

- **Quality** -- dependable, polished, and serious enough for real work.
- **Usable** -- built around practical keyboard, screen reader, and
  low-friction editing needs.
- **Inclusive** -- designed from the beginning for blind users, screen reader
  users, keyboard users, and people with different skill levels.
- **Lightweight** -- fast, focused, not bloated, and friendly to people who
  just want to write or edit.
- **Literate** -- about words, code, Markdown, documents, learning, and
  thoughtful communication.

New to the repository? This README covers getting started; **[REPO-GUIDE.md](REPO-GUIDE.md)**
is the complete map of every folder, and **[CHANGELOG.md](CHANGELOG.md)** is
what shipped, release by release.

## One repository, a family of apps

The current release line is **QUILL 1.0.0**. This repository builds the
editor and a family of companion apps -- together, **QuillVille**:

| App | What it is |
|---|---|
| QUILL (the editor) | The full writing and document environment, for Windows and macOS |
| Quill Radio | Internet radio with a 60k-station offline catalog, recording, and weather |
| QUILL Cast | An accessible podcast player with downloads, queue, and notes |
| QUILL Audio Studio | Audiobook and audio production: chapters, captions, publishing |
| Quill Weather | Forecasts, hourly detail, moon phases, US alert monitoring |
| Quill Inkwell | Text expansion |
| Quill Beacon | Encrypted sync beacon |
| QUILL Social | Accessible social reading (RSS today; a NetworkAdapter contract for more) |

The companion apps share one **QuillVille Runtime** -- a single Python
runtime (about 294 MB) installed once at
`%LOCALAPPDATA%\QuillVille\Runtime\3.13` and reused by every app, so a
person who installs three apps downloads the shared engine once. Media
tools (ffmpeg, libmpv, about 304 MB) ride only with the apps that declare
them: Radio, Cast, and Audio Studio. Everything an installer ships works
offline the moment installation finishes; larger optional components
(dictation engines, neural voices, extra spell-check languages) are offered
in-app as consented, SHA-256-verified downloads.

The [Quillin Hub](https://hub.quillforall.org) hosts community-created
extensions (Quillins) -- from research tools to accessibility auditors --
verified for security and WCAG 2.2 AA compliance.

## Running from source

You need **Python 3.13** on Windows (the version releases are built and
tested against; 3.12 is the floor) or macOS.

```powershell
# 1. Clone, then install the editor with UI and dev tooling
pip install -e ".[ui,dev]"

# ...or the same install in seconds with uv (dev only; releases use pip)
uv pip install -e ".[ui,dev]"

# 2. Run the editor
python -m quill          # pythonw -m quill for no console window

# Companion apps run from the same checkout
python -m quill.apps.radio
python -m quill.apps.podcasts    # QUILL Cast
python -m quill.apps.studio
python -m quill.apps.weather
```

Notes for a working developer setup:

- **Optional extras** are opt-in and named in `pyproject.toml`: `ai`
  (on-device llama.cpp assistant), `spellcheck`, `speech`, `dictation`,
  `ocr`, `glow` (document accessibility engine), and more. The everything
  set a release runtime ships is `pip install -e ".[runtime,packaging]"`.
- **Vendored wheels**: a few first-party dependencies (the GLOW engine,
  feedback-hub) are not yet on PyPI and live in `vendor/wheels`. Installs
  that need them take `--find-links vendor/wheels`.
- **Useful launch flags**: `--safe-mode` (disables AI, watch folder, and
  extensions), `--version`, `--diagnostics`, `--new-window`,
  `--line N --column M`. Safe mode is also `QUILL_SAFE_MODE=1`.
- Running from source uses your real `%APPDATA%\Quill` data folder unless a
  `data\` folder with a portable marker sits next to the app; developers can
  point `QUILL_DATA_DIR` somewhere else (honoured only with
  `QUILL_DEV_BUILD=1`).

## Repository structure

The short version (the full map is [REPO-GUIDE.md](REPO-GUIDE.md)):

- `quill/` -- the application package, layered with strict import
  boundaries: `core/` (pure domain logic, no wx, strict-typed), `io/`
  (format readers/writers, no wx, strict-typed), `ui/` (the wxPython
  shell), `platform/` (Windows and macOS bridges), `stability/` (crash
  reporting, safe subprocess, safe mode), `tools/` (the shipped CI gates),
  `apps/` (the companion apps' source), `quillins_bundled/` (built-in
  extensions).
- `tests/` -- unit, stability, integration, UIA, and repository-structure
  suites; `tests/unit/` mirrors the package layout.
- `docs/` -- all documentation: the PRD, user guides, release runbooks, QA
  books, planning, the published site. Every Markdown file has generated
  `.html`/`.epub` siblings, and CI enforces that parity.
- `scripts/` -- build and release tooling (see the next section).
- `standalone/` -- per-app build wrappers (installer scripts, specs, icons,
  app docs) plus `standalone/runtime/`, the shared QuillVille Runtime build.
- `installer/` -- QUILL's own Inno Setup sources (generated; edit the
  generator).
- `vendor/wheels/` -- vendored wheels for dependencies not yet published.
- `packages/`, `examples/` -- the Node Quillin runtime API and example
  extensions.

Anything else you see at the root after building (`dist/`, `build/`,
`local/`, `data/`) is gitignored output and safe to delete.

## The build process

Everything releasable lands under `dist/` subtrees, and a local build is
laid out identically to a CI build.

**The shared runtime.** `standalone\runtime\build_runtime.ps1` (no
arguments) builds the QuillVille Runtime with PyInstaller from
`quillville-runtime.spec`. What ships is *declared*, not inherited from
whatever the build machine has installed, and three gates hold that
promise:

1. `scripts/check_build_env.py` -- the floor: everything `[runtime]` needs
   is installed.
2. `scripts/check_runtime_inventory.py` -- the ceiling: nothing undeclared
   appeared and nothing declared vanished (baseline:
   `standalone/runtime/runtime-inventory.json`).
3. `scripts/check_runtime_imports.py` -- the proof: runs the finished
   bundle and imports every optional piece, so present-but-broken can
   never ship silently.

**Per-app installers.** Each app's `standalone\<app>\scripts\build_release.ps1`
builds the runtime (or reuses it with `-SkipSharedRuntime`), stages exactly
the media tools the app declares in its `REQUIRED_COMPONENTS` (via
`scripts\StageMediaTools.ps1`, from pinned SHA-256-verified assets --
never from PATH), renders the app's docs, and compiles the Inno Setup
installer plus a portable zip. Code signing is opt-in (`-Sign`, see
`docs/code-signing.md`); a plain build is unchanged.

**QUILL's own installers.** `python scripts/build_windows_distribution.py`
builds the editor's portable bundle and installer into `dist/windows/`;
`--bundle-offline` builds the **Offline Edition** into
`dist/windows-offline/` -- everything bundled, zero downloads ever, for
machines the internet cannot reach.

**When two build machines disagree**,
`python scripts/build_fingerprint.py capture` records what a machine
really is (interpreter, every package, staged-binary hashes, artifact
sizes) and `compare --fail-on-drift` names exactly what differs. The
procedure is `docs/build-machine-sync.md`.

## Tests and quality gates

```powershell
pytest -m smoke -q               # high-signal core checks, seconds
pytest -q                        # the full suite (~9 minutes)
pytest -q -n 8 --dist loadgroup  # parallel (~5.5 minutes)

ruff check .                     # lint
ruff format --check .            # formatting
mypy quill\core quill\io         # type-check (always scoped)

python -m quill.tools.platform_report   # every gate, one scorecard
```

Beyond the usual suite, the repository enforces its own rules with
internal gates: module size budgets (a ratchet -- budgets only decrease),
a banned-pattern gate, a dialog inventory and keyboard contract, menu
accelerator checks (every enabled menu item shows a keyboard route; no
duplicate keys), a network egress audit (every outbound call site is
inventoried and consented), and error-code discipline (every custom
exception carries a `QUILL-*` code). `CLAUDE.md` is the shortest accurate
summary of these invariants; `python -m quill.tools.platform_report` runs
them all and exits non-zero on any failure.

## Documentation workflow

Every `docs/**/*.md` ships with rendered `.html` and `.epub` siblings,
built deterministically (pinned epoch, stable EPUB identifiers, an
accessible HTML template with `lang`, a skip link, and a `main` landmark).
Render through the project's tooling -- `python scripts/release_readiness.py`
rebuilds the `docs/` tree as part of the release flow -- rather than
calling pandoc by hand, and `scripts/check_docs_artifacts.py` fails any
commit that changes a Markdown source without its regenerated siblings.

## Support and issue reporting

Use **Help -> Report a Bug** inside any of the apps: it generates a
diagnostics bundle (secrets scrubbed), previews the report, and submits
it -- with a clipboard-and-browser fallback for users with no GitHub setup.
On GitHub, use Discussions for questions and ideas, Issues for confirmed
bugs and scoped requests.

## Contributing

Community contributions are welcome.

- **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** -- setup, workflow, and PR
  expectations.
- **[CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md)** -- before participating.
- **[SECURITY.md](docs/SECURITY.md)** -- private vulnerability reporting.
- **[PRIVACY.md](docs/legal/PRIVACY.md)** -- data handling and retention.
- **[RESPONSIBLE_AI_USE.md](docs/legal/RESPONSIBLE_AI_USE.md)** -- ethical
  and accountable AI use.
- **[GOVERNANCE.md](docs/GOVERNANCE.md)** and
  **[MAINTAINERS.md](docs/MAINTAINERS.md)** -- how decisions get made.
- Release process and branch policy: **[RELEASE.md](docs/release/RELEASE.md)**.

## License

MIT. See `LICENSE`.

## Legal and trademark notices

QUILL for All is an independent open-source project by Community Access.
It is not affiliated with, sponsored by, or endorsed by Quill.js, QuillBot,
Quill.org, or any other similarly named product, project, company, or
organisation. All trademarks are the property of their respective owners.

See [TRADEMARKS.md](docs/legal/TRADEMARKS.md), [NOTICE](NOTICE), and
[THIRD_PARTY_NOTICES.md](docs/legal/THIRD_PARTY_NOTICES.md) for more
information.
