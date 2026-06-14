# Contributing to QUILL

Thank you for helping improve QUILL.

QUILL is a screen-reader-first Windows writing environment. Contributions should
preserve that core direction: practical keyboard workflows, stable editing,
accessible defaults, and clear user control.

## Before you start

1. Read the product expectations and full architecture in `docs/QUILL-PRD.md`
   (the single source of truth), and the architecture overview below.
2. Review project conduct rules in `CODE_OF_CONDUCT.md`.
3. Check existing issues and pull requests before starting overlapping work.
4. Review project decision process in `GOVERNANCE.md`.

## Architecture overview

QUILL is a layered desktop application with strict boundaries that exist to
preserve accessibility behavior and testability. The canonical, detailed
specification lives in `docs/QUILL-PRD.md`; this section is the short version
contributors need day to day.

### Layers

- **`quill/core`** — pure domain logic: documents, command registry, settings,
  keymap, recent files, history, metrics, and storage primitives. No `wx`
  imports and no direct UI ownership; strict-typed and gated in CI.
- **`quill/io`** — format readers/writers and detection. The contract is
  `read(path) -> Document`, optional `write(doc, path)`, optional `outline(doc)`;
  also strict-typed.
- **`quill/ui`** — wxPython shell, editor surface, menus, status bar, dialogs,
  and command palette. UI composes `core` + `io` and owns widget lifecycle
  (gradual typing).
- **`quill/platform/windows`** — Windows-specific bridges (screen-reader
  announcements, DPAPI secrets, shell integration, single-instance, TTS).
- **`quill/plugins`** — plugin-facing API surfaces and manifest model.
- **`quill/tools`** — internal CLIs and gates (a11y audit, diagnostics,
  characterization and registry checks).

### Primary flow

A user action enters through `quill/ui/main_frame.py` (`MainFrame`), dispatches
to `core.commands.CommandRegistry`, reads/writes a `core.document.Document`,
persists through `io` or `core.storage`, and surfaces the outcome through status
updates and `platform.windows.sr_announce.announce`.

### Boundary and runtime rules

- `core` and `io` never import `wx`; keep `wx` confined to `quill/ui` and
  `quill/platform/windows`.
- `ui` does not perform raw persistence; it calls `core` helpers (settings,
  keymap, recent) and `io` for document I/O.
- Persistent writes are atomic via `core.storage.write_json_atomic`
  (temp file + `os.replace`), with schema validation and `.bak`/recovery.
- The single UI thread owns all widgets; background I/O and heavier compute run
  off-thread, network/AI runs async behind explicit consent, and all cross-thread
  UI updates marshal through `wx.CallAfter`/`wx.CallLater`.
- `core.events.CancelToken` is the shared cancellation primitive; long-running
  tasks accept and check it at safe boundaries.
- No silent network calls: every cloud/AI action is explicit, per-action opt-in
  with visible progress and outcome.

## Development setup

1. Install Python 3.12.
2. Install dependencies:
   - `pip install -e ".[ui,dev]"`
3. Run QUILL locally:
   - `python -m quill`

## Making changes

1. Create a feature branch from `main`.
2. Keep changes focused and small enough to review.
3. Follow the current module boundaries:
   - `quill/core`: no `wx` imports
   - `quill/ui`: UI behavior and dialogs
   - `quill/io`: format readers/writers
   - `quill/platform/windows`: Windows-specific integration
4. Prefer existing helpers and patterns over introducing parallel paths.
5. Keep user-facing text clear and accessibility-friendly.

## Quality checks

Run these before opening a pull request:

- Lint: `ruff check .`
- Format check: `ruff format --check .`
- Scoped strict type-check: `mypy quill\core quill\io`
- Tests: `pytest tests/unit/ tests/stability/ -q --ignore=tests/unit/core/test_net_tls.py --ignore=tests/unit/core/test_thesaurus.py`
- Docs artifact parity (if docs changed): `python scripts/check_docs_artifacts.py`

Type-checking is intentionally **scoped to `quill\core` and `quill\io`**. These
layers are strict-typed and gated in CI. Do not run an unscoped whole-tree
`mypy` scan: `quill\ui` is excluded (gradual typing) in `pyproject.toml`, so a
whole-tree run is both slower and noisier without adding signal. Always use the
scoped command above.

### Optional: install pre-commit hooks

To catch formatting, lint, and undefined-name problems on changed files before
they reach CI, install the hooks once:

```powershell
pip install pre-commit
pre-commit install
```

The hooks run `ruff format`, `ruff check`, and an undefined-name check on the
files you are committing. Commits that fail are blocked locally.

If your change updates `docs/*.md`, regenerate matching artifacts:

- `pandoc docs\\<name>.md -f gfm -t html5 -s -o docs\\<name>.html`
- `pandoc docs\\<name>.md -f gfm -t epub3 -o docs\\<name>.epub`

## Pull request expectations

A strong PR includes:

1. A clear summary of what changed and why.
2. Notes on accessibility impact, if any.
3. Notes on risk or migration impact, if any.
4. Evidence of the checks you ran.

Please avoid mixing unrelated refactors with feature or bug-fix work.

## Contributing a Quillin

Quillins are small, sandboxed extensions that add commands, snippets, menus, and
hotkeys to QUILL. Contributing one has its own dedicated path:

- **Tutorial** — [`docs/quillins.md`](docs/quillins.md): a
  hands-on, build-it-from-scratch walkthrough (Layer 1 snippet → Layer 2
  handler → lint → test → submit).
- **Submission guide** — [`docs/quillins.md`](docs/quillins.md):
  the process, directory layout, review criteria, and acceptance checklist.
- **Author Covenant** — [`docs/quillins.md`](docs/quillins.md):
  the code of conduct for Quillin *code* (accessibility, capability honesty, no
  silent network, security). Every submission attests to it.
- **Self-lint** — `python -m quill.tools.quillin_lint <dir> --strict` must be
  green; the `Quillin Verify` CI gate runs it on every submission.
- **Start a submission** — open the **Quillin submission** issue (it scaffolds
  the `manifest.json`), then open a PR with the **Quillin submission** PR
  template.

## Acknowledgments and Attribution

Quill is built on open-source foundations and integrates best practices from the accessibility community:

- **AccessibleApps** (https://github.com/accessibleapps/) contributes several libraries that enhance Quill's accessibility and cross-platform reliability:
  - `app_updater` (MIT) — cross-platform incremental update delivery and automatic installer bootstrapper.
  - `smart_list` (MIT) — accessible, model-based list view for large outlines and datasets.
  - `accessible_output2` (MIT) — optional fallback for speech and braille output when Prism is unavailable.
  - `html_to_text` (MIT) — convert HTML from web pastes to clean plain text while preserving structure.
  - `app_elements`, `platform_utils`, `keyboard_handler` — small utilities for dialogs, clipboard, and hotkeys.

- **Prism** (NVIDIA) — modern screen-reader backend for announcements and accessibility bridging.

Contributors who integrate third-party libraries from AccessibleApps or other open-source projects should document the license, purpose, and API contract in the relevant module docstring, and update this section when adding a new external dependency.

## Reporting bugs and proposing features

- For product/support issues, users can use in-app `Help -> Report a Bug`.
- For repository work, open a GitHub issue with:
  - expected behavior
  - actual behavior
  - reproduction steps
  - environment details
- Use the most specific issue template available (accessibility, AI, intake,
  snippets, dictation, performance, Quillin submission, or general bug/feature).
- Use GitHub Discussions for Q&A and early design exploration.

## Security issues

Do not open public issues for vulnerabilities. Follow `SECURITY.md` for private
reporting.

Before opening a PR, quickly sanity-check security posture:

1. No secrets or credentials in code, tests, fixtures, or docs.
2. No user document content added to logs/diagnostics paths.
3. New network calls are explicit and user-controlled.
4. New file/command paths are validated and not shell-interpolated.

## Translation contributions

Localization contributors should follow:

- `docs/translating.md`

## Contributors

The following people have contributed code, tests, accessibility feedback, or
documentation to QUILL. Thank you.

- Taylor Arndt ([@taylorarndt](https://github.com/taylorarndt))
- Michael Doise ([@mikedoise](https://github.com/mikedoise))
- Doug Langley ([@douglangley](https://github.com/douglangley))
- Becky K ([@BeckyK102125](https://github.com/BeckyK102125))
- Kelly Ford ([@kellylford](https://github.com/kellylford)) — HEIC/HEIF image support (#164, #165)

## License

By contributing, you agree that your contributions are licensed under the
repository's MIT license.
