# QUILL Repository Guide

This is the map of the whole repository: what every folder is for, where the
important documents live, what is generated versus hand-written, and which
folders are local build output that never lands in git. If you are looking for
something and do not know where it lives, start here.

Related front doors: `README.md` (the project introduction),
`CHANGELOG.md` (what shipped, release by release), and `CLAUDE.md`
(engineering invariants and commands for AI-assisted work — also the shortest
accurate summary of the architecture).

## Quick orientation

- Application source is under `quill/`, tests under `tests/`, all
  documentation under `docs/`, build and release tooling under `scripts/`.
- Release acceptance testing lives in `docs/release/acceptance/` — open
  `docs/release/acceptance/interactive/index.html` in a browser to run it.
- Anything at the root that is not listed in "Root files" below is local,
  gitignored working output (build trees, logs, caches) and safe to delete.

## Top-level folders (tracked)

### Application

- `quill/` — the application package, layered with strict import boundaries:
  - `quill/core/` — pure domain logic (documents, commands, settings, keymap,
    storage, AI sessions, recovery). No `wx` imports; strict-typed.
  - `quill/io/` — file format readers and writers (`read(path) -> Document`,
    `write(doc, path)`). No `wx`; strict-typed.
  - `quill/ui/` — the wxPython shell. `main_frame.py` plus feature mixins
    (`main_frame_vault.py`, `main_frame_speech.py`, ...). New command handlers
    go in a mixin, not in `main_frame.py`.
  - `quill/platform/` — OS bridges (Windows: screen-reader announcements via
    Prism, DPAPI, Credential Manager, SR detection; macOS app entry).
  - `quill/stability/` — runtime safety: safe subprocess, crash reports,
    secret redaction, task manager, wx heartbeat, safe mode.
  - `quill/tools/` — the internal CI gates (banned patterns, module size
    budget, network egress audit, dialog inventory and button contract,
    quillin lint, error code audit, and friends).
  - `quill/plugins/` — plugin-facing API surfaces and the Quillin (extension)
    manifest model.
  - `quill/quillins_bundled/` — the Quillin extensions that ship in the box.
  - `quill/apps/` — the companion apps' source (radio, weather, and the gated
    apps), sharing core/io/stability with the editor.
- `tests/` — the test suite: `unit/` (mirrors the package layout),
  `stability/`, `integration/` (including live AI provider checks), `uia/`
  (CI-only screen-reader UI automation), `structure/` (repository layout
  gates).

### Build, release, and tooling

- `scripts/` — build and release tooling: Windows distribution and portable
  ZIP builds, update ZIPs, release artifact generation, braille and sound
  pack builds, macOS build/signing, docs artifact parity checks, and the
  generators for the interactive sign-off checklists
  (`gen_signoff_html.py`) and the interactive acceptance runner
  (`gen_acceptance_html.py`).
- `installer/` — the Inno Setup installer sources (`quill.iss` is generated;
  edit the generator, not the .iss).
- `standalone/` — self-contained build wrappers for the companion apps
  (radio, weather, cast, studio, converter, beacon, player, social) plus the
  shared `runtime/`.
- `packages/` — JavaScript packages, currently `@quill/api` for the Node.js
  Quillin runtime.
- `examples/` — example Quillins demonstrating the extension API.
- `vendor/` — vendored third-party artifacts (`wheels/` for offline builds).
- `tools/` — repo-level developer utilities that do not ship (key and token
  generators, speech tooling). Distinct from `quill/tools/`, which holds the
  shipped CI gates.

### Services

- `quill-ai-gateway/` — the hosted AI gateway service (Docker/Caddy deploy)
  that fronts AI providers for QUILL's free tier.
- `quillin-hub/` — the Quillin Hub service (extension publishing and
  distribution) with its worker and smoke test.

### Meta

- `.github/` — CI workflows: PR CI, Accessibility CI (the merge gate), docs
  artifact regeneration, security CI, UIA regression, Windows and macOS
  release pipelines, GitHub Pages for the site.
- `_fork-private/` — fork-local templates (spec template, AI handoff notes);
  not part of the product.

## docs/ — all documentation

`docs/README.md` is the in-tree index of everything below.

- `docs/` (top level) — community and governance docs (`CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, `GOVERNANCE.md`, `MAINTAINERS.md`),
  plus `CONTROL_REFERENCE.md` (generated from `quill/core/help/topics.json`
  by `python -m quill.tools.build_docs` — do not hand-edit) and `signing.md`.
- `docs/Product Requirement Documents and Specifications/` — the PRD
  (`QUILL-PRD.md`) and feature specifications. The PRD is the product's
  canonical description.
- `docs/user guide/` — the end-user guide (`userguide.md`), which also ships
  inside the app.
- `docs/release/` — everything needed to cut and verify a release:
  - `RELEASE.md` — the release checklist/runbook.
  - `acceptance/` — the 1.0.0 Acceptance Test Book (see below).
  - `qa-samples/` — the sample documents the acceptance book opens.
  - `upgrade-test/` — upgrade-path regression runbooks and installers.
  - Screen-reader test plan, core-journey QA plan, UAT and regression
    runbooks, macOS signing/notarization runbooks, the clean-install script.
- `docs/qa/` — cross-release QA references: the manual dialog-regression
  checklist (`dialogs.md`), UI automation notes, platform validation, the
  converter bake-off, audio-studio validation.
- `docs/planning/` — active planning and program tracking: `roadmap.md` (the
  1.0 plan of record), `RELEASE-1.0.0-READINESS.md` (the release readiness
  ledger), consolidated specs, backlogs, and:
  - `signoff/` — the machine-generated 1.0.0 sign-off inventories (every
    command, dialog, and app surface, one line each) with
    `signoff/interactive/` — their checkbox HTML versions.
- `docs/release notes/` — per-release notes (`archived/` for old ones,
  `Github/` for the GitHub release bodies).
- `docs/site/` — the website content (docs, tutorials, podcast pages, update
  manifests) published via GitHub Pages.
- `docs/legal/` — privacy, responsible AI use, trademarks, third-party
  notices.
- `docs/engineering/` — engineering deep-dives and post-mortems.
- `docs/design/` — design notes (e.g. publishing).
- `docs/apps/` — companion app docs (beacon, cast, converter, player).
- `docs/audio-studio/`, `docs/math/`, `docs/quillins/`, `docs/translations/`,
  `docs/tutorials/`, `docs/podcast/` — feature-area documentation; and
  `docs/superpowers/` — internal plans/specs written during AI-assisted
  development.

### Documentation conventions

- Every `docs/**/*.md` has generated `.html` and `.epub` siblings. CI
  enforces parity (`scripts/check_docs_artifacts.py`); after editing a
  Markdown file, regenerate both:
  `pandoc file.md -f gfm -t html5 -s -o file.html` and
  `pandoc file.md -f gfm -t epub3 -o file.epub` (the Docs artifacts workflow
  can also push them for same-repo PRs).
- The repository root allows only sanctioned Markdown (`README.md`,
  `CHANGELOG.md`, `CLAUDE.md`, this guide); everything else belongs under
  `docs/` (enforced by `tests/unit/structure/test_repo_layout.py`).

## Acceptance testing (the 1.0.0 gate)

The hand-held Acceptance Test Book is `docs/release/acceptance/` — one
scenario per feature, each with setup, exact keystrokes, projected outcome,
and a sign-off. Three ways in:

1. **Interactive runner (recommended):** open
   `docs/release/acceptance/interactive/index.html`. Progress saves in the
   browser as you go; Export/Import moves it between machines. Regenerate
   after editing the Markdown with `python scripts/gen_acceptance_html.py`.
2. **The printed book:** the Markdown files themselves, starting at
   `docs/release/acceptance/README.md` (read sections 1-5 first).
3. **The inventories:** `docs/planning/signoff/` lists every command and
   dialog one line each (`signoff/interactive/index.html` for the checkbox
   version). The book is the guided walk; the inventory is the map.

The overall release ledger is `docs/planning/RELEASE-1.0.0-READINESS.md`;
the human sign-off phase is what the acceptance run completes.

## Root files

- `README.md` — project front page. `CHANGELOG.md` — release history (read
  by release tooling; stays at root). `CLAUDE.md` — engineering invariants
  for AI-assisted work. `REPO-GUIDE.md` — this guide.
- `polish.md` — the ranked platform-review worklist (2026-08-17), at the root
  by request so it stays in view while its items are worked off; its header is
  the execution ledger. Graduates under `docs/` when the list is spent.
- `LICENSE`, `NOTICE` — licensing.
- `pyproject.toml`, `requirements.txt`, `uv.lock`, `.quill-reqs.sha256` —
  Python packaging and dependency pinning.
- `run-from-source.bat` / `.sh` / `.command`, `run-current-build.bat`,
  `run-quill-radio.bat`, `run-quill-cast.bat` — convenience launchers.
- `installer/`-adjacent root helpers: `quill-pub.key` (the public update
  signing key), `babel.cfg` (translation extraction).
- Config: `.gitignore`, `.gitattributes`, `.pre-commit-config.yaml`,
  `.markdownlint-cli2.jsonc`.

## Local build output and scratch (untracked, safe to delete)

These folders appear at the root when you build or run; they are gitignored
and never committed.

**`dist/` is the single home for everything releasable.** Every build tool
lands its output in a `dist/` subtree:

- `dist/windows/` — the Windows distribution (`portable/` bundle +
  `installer/` with the compiled setup under `installer/Output/`), from
  `scripts/build_windows_distribution.py`.
- `dist/windows-offline/` — the offline edition of the same build
  (`--bundle-offline`), kept separate so both can coexist.
- `dist/release-artifacts/` — installers' metadata, SBOM, provenance,
  checksums, and update ZIPs, from `scripts/generate_release_artifacts.py`
  and `scripts/build_update_zip.py`.
- `dist/sound-packs/` and the braille pack ZIPs — from
  `scripts/build_sound_packs.py` and `scripts/build_braille_pack.py`.

The release workflows (`windows-release.yml`, `windows-test-build.yml`)
build into the same paths, so a local build and a CI build are laid out
identically.

Other locals:

- `build/` — intermediate Python build tree.
- `local/` — the scratch convention: local notes, logs, and one-off files
  you want near the repo but never in it.
- `data/` — a portable-mode data folder when running from source;
  `files/`, `liblouis/` — local asset staging (e.g. braille pack sources).
- `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.history/` —
  environments and tool caches.
