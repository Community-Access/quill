# Copilot instructions for this repository

## Repository state

This repository contains the implementation source tree together with the product requirements document under `docs/Product Requirement Documents and Specifications/QUILL-PRD.md` and `docs/QUILL-PRD.html`.

When generating code or task plans, treat the PRD as the source of truth for intended architecture and conventions.

## Build, test, and lint commands

There are no runnable project commands in this repo yet. The PRD defines the expected toolchain and CI commands for the future codebase:

```powershell
# Environment setup
uv python install 3.12
uv sync --all-extras
pre-commit install

# Lint + type-check (planned CI)
ruff check .
ruff format .
mypy quill\core quill\io

# Tests (planned CI)
pytest tests\unit -n auto
pytest tests\integration
pytest tests\a11y
pytest tests\perf

# Single test pattern (pytest)
pytest tests\unit\path\to\test_file.py::test_name
```

## High-level architecture (from PRD)

Quill is designed as a screen-reader-first Windows desktop app in Python + wxPython, with a strict separation between UI, core logic, I/O format handlers, platform bindings, and optional AI providers.

- `quill/core/*`: document model, commands, history, keymap, backups, events, metrics, schemas. No `wx` imports.
- `quill/io/*`: per-format readers/writers and outline emitters. Contract is `read(path) -> Document`, optional `write(doc, path)`, optional `outline(doc)`.
- `quill/ui/*`: wxPython shell/editor/dialogs/palette/status bar; consumes `core` and `io`.
- `quill/platform/windows/*`: Windows-specific APIs (screen-reader bridges, DPAPI, shell integration, single-instance, high-contrast, TTS).
- `quill/ai/*`: provider adapters and safety/consent gating for networked actions.
- `quill/plugins/*`: plugin API + manifest validation (v1.0 loader skeleton).
- `quill/tools/*`: internal CLIs (a11y audit, docs generators, diagnostics helpers).
- `tests/{unit,integration,a11y,perf,fixtures}`: split test strategy reflected in CI.

Concurrency model in the PRD:

- UI thread owns widgets and editor buffer.
- Thread pools handle file I/O and heavier compute.
- `wxasync`-managed asyncio handles HTTP/network operations.
- OCR runs in a separate worker process.
- Cross-thread UI updates marshal through `wx.CallAfter`/`wx.CallLater`.

Persistence model in the PRD:

- User data rooted at `%APPDATA%\Quill\...`
- JSON stores validated by schemas under `quill/core/schemas/`
- Atomic writes via temp file + `os.replace`

## Key conventions to preserve

- Screen-reader-first UI: use stock controls in the writing path (`wx.TextCtrl`, `wx.ListBox`, `wx.Dialog`), avoid custom-drawn editor controls.
- The editor surface is the primary interaction surface and should remain plain-text-first.
- Announcements should report action outcomes consistently (NVDA/JAWS/Narrator parity).
- No silent network calls: all cloud/AI actions are explicit opt-in per action with visible progress and outcome.
- `core` must stay UI-framework-agnostic; keep `wx` imports confined to `quill/ui` and `quill/platform/windows`.
- Do not bypass `io` contracts for new format handlers; add format logic as isolated `io/*` modules.
- Avoid shared mutable-state locking patterns in `core`; follow snapshot/merge worker model described in PRD.
- Keep storage robust: schema-validated JSON, `.bak`/recovery behavior, atomic writes on all persistent stores.
- Type and lint policy from PRD: ruff formatting/lint, strict mypy in `core` + `io`, gradual typing in `ui`.
- Security/privacy defaults are non-negotiable: DPAPI for secrets, no document content in logs, explicit consent gate before outbound document data.

## Dialog, Window, and Accessibility Lessons

Apply these rules to every UI change in `quill/ui/*`. The full, wx-grounded
authoring guide lives in
`.github/instructions/accessible-dialogs.instructions.md` (auto-applied to
`quill/ui/**/*.py`); the highlights below are the must-knows.

- Keep parent ownership consistent in dialog layout trees.
  - If controls are parented to `panel = wx.Panel(dialog)`, keep that control tree in a panel sizer and attach the panel to an outer dialog sizer.
  - Do not attach the same root sizer to both panel and dialog.
- Prefer stock controls for instructional content users must read.
  - Use `wx.TextCtrl(..., wx.TE_MULTILINE | wx.TE_READONLY)` or list controls for screen-reader review, not transient message boxes when content is long.
- Avoid mutating menu items while menus are open.
  - Defer menu label/enable/check updates until menu close to avoid focus churn and native menu instability under rapid arrow navigation.
- Treat `wx.CallAfter` as optional in tests and fallback environments.
  - Guard with `getattr(wx, "CallAfter", None)` and provide a synchronous fallback where safe.
- Keep dialog focus behavior predictable.
  - Set explicit default buttons, bind Escape/Close consistently, and return focus to editor after modal close.
- Add focused tests for dialog and menu regressions.

## Development environment (local vs cloud)

Read this before deciding whether you can run live UI code.

- **Local development happens on Windows.** The working tree lives on `S:\QUILL`,
  the shell is PowerShell (`pwsh`), and **wxPython is installed and importable**
  (wx 4.2.5 msw / wxWidgets 3.2.9, including `wx.richtext`). When you are working
  locally you **can** create a `wx.App`, instantiate real controls, and run live
  GUI tests with `python -m pytest`. Do **not** assume a headless or Linux
  environment and do **not** refuse to verify GUI behavior locally — actually
  exercise wx (for example for undo, spell-check, dialog focus, and announcement
  behavior) instead of marking an item "needs runtime / cannot verify".
- **The GitHub Copilot cloud coding agent runs on Linux**, where wxPython cannot
  be imported. The Linux/headless constraints below in "Cloud coding agent
  directives" apply **only** to that cloud agent, not to local Windows work.
- Either way, `quill/core` and `quill/io` must stay wx-free — that is an
  architectural rule, independent of the runtime. UI tests under `tests/unit/ui`
  may import wx when running locally.

## Cloud coding agent directives (read this first)

When you run as the GitHub Copilot coding agent in the cloud, follow these standing
rules in addition to everything above.

### Mission and honesty

- Drive QUILL 1.0 work (Tier 2 roadmap items in `ROADMAP.md` plus all associated
  1.0 work, **including documentation**) toward genuine, tested Done.
- HONESTY IS NON-NEGOTIABLE. Only mark an item Done when it is genuinely complete
  and tested. If an item has a real runtime blocker, leave it honestly
  "In progress" with an accurate note explaining why. Never fabricate Done.
- **In the cloud you run on Linux**, so `wxPython` cannot be imported. That is
  expected in the cloud environment only (see "Development environment" above —
  local Windows work can run live wx). Do not
  try to instantiate live wx UI. Validate UI work through the existing bar:
  source-contract tests (read the `.py` file as text and assert wiring
  substrings), the A11Y-4 dialog-contract guard
  (`tests/unit/ui/test_dialog_contract.py`), navigation tests, and the
  public-surface fixture.
- Items that need a real Windows runtime CANNOT be finished in cloud and must stay
  honestly "In progress": OCR-1/OCR-3 (real OCR engine, clipboard, display),
  AI-19 (live device-login endpoint), SET-2 (sensitivity-aware dictation backend),
  AGENT-1 (advisory-only by design). Document them; do not mark them Done.

### Out of scope for 1.0 (do NOT work on these)

- axe-core / vnu (Nu Html Checker) HTML/CSS/SVG validation.
- BITS Whisperer.
- The GLOW watch-action binding (WATCH-8) and the axe-core / Accessibility
  Agents workstream (AX-A..F).

These are deferred to QUILL 2.0 and are already tracked as such in `ROADMAP.md`.
The GLOW engine family (GLOW-1..7) is back in the 1.0 milestone (Tier 2,
sequenced after Tier 4) now that the shared `quill-glow-core` engine is green.

### Per-change discipline (every commit / PR)

- Format and lint: `ruff format` then `ruff check` (use `--fix` where safe).
- Strict typing on changed `quill/core` and `quill/io` files: `mypy` must report
  "Success: no issues found". `quill/core` and `quill/io` must stay wx-free.
- Run the targeted `pytest` for what you changed; keep the suite green.
- After editing `ROADMAP.md`, regenerate `ROADMAP.html` with
  `pandoc -s ROADMAP.md -o ROADMAP.html` and commit both together.
- If a new public `MainFrame` method is added, regenerate the fixture with
  `python -m quill.tools.ui_surface --write` and stage
  `tests/unit/ui/fixtures/main_frame_public_surface.json`.
- Stage SPECIFIC files only. NEVER `git add -A` (it pulls in `.history/` and
  `uv.lock`). Keep `ROADMAP.md`, the living lists, and the tracker totals
  reconciled with each change.
  - Include at least one behavior test (or source-contract test when UI stubs are limited) per bug class.

## Keep dialogs.md current

`docs/qa/dialogs.md` is the master manual regression checklist for every
user-facing dialog in QUILL, each mapped to the keyboard command or menu path
that opens it. It must stay a faithful, complete map of the shipped dialogs.

- Whenever you add, remove, rename, or rebind a dialog anywhere under `quill/ui/`
  (including `main_frame.py`, `palette.py`, `assistant_panel.py`,
  `assistant_tools.py`, `ai_model_panel.py`, `train_style_dialog.py`, `sticky_notes.py`,
  `preview_dialog.py`, and `web_form.py`), update the matching row in `dialogs.md`
  in the same change.
- New dialogs are added as a `- [ ]` checklist item in the correct section, with
  the keyboard command (or "via menu" when there is no default keybinding, using
  the literal binding from `quill/core/keymap.py`). Nested dialogs go in the
  nested section noting their parent; startup-only dialogs go in the startup
  section noting their trigger.
- Do not tick checkboxes in `dialogs.md` from code changes. The checkboxes record
  the outcome of a manual regression pass and are ticked by a human tester.
- The checklist is the manual companion to the A11Y-4 machine-enforced dialog
  contract guard; keep both in mind when touching dialog construction.

## Dialog Excellence Mandates (DLG-3, machine-enforced)

Every dialog in QUILL is governed by a source-of-truth registry generated from
code, not from a checklist. The authoritative inventory is produced by
`quill/tools/dialog_inventory.py`, which scans all of `quill/**/*.py` via AST and
records every dialog *surface* (each `wx.Dialog(...)`, stock wx dialog, and
`show_web_form(...)` invocation) under a stable, line-independent key
(`<module>::<enclosing_qualname>::<kind>`) with its sanctioned classification:

- `native` — stock wx dialogs (`wx.MessageDialog`, `wx.RichMessageDialog`,
  `wx.MessageBox`, choosers, text/file/dir pickers, progress, about). Native-first
  is the default for confirms, choices, simple text, and file/folder selection.
- `web` — sanctioned accessible web surfaces (`show_web_form`).
- `hardened_custom` — a raw `wx.Dialog(...)` base (the only allowed bespoke base).

The committed registry snapshot is
`tests/unit/ui/fixtures/dialog_inventory.json`. Two gates enforce it:

1. `tests/unit/ui/test_dialog_inventory.py` fails if the live source scan and the
   snapshot disagree (new, moved, removed, or reclassified dialog) or if any
   surface carries an unsanctioned classification.
2. The A11Y-4 banned-pattern gate (`quill/tools/check_banned_patterns.py`, run in
   Security CI) cross-checks every scanned dialog surface against the snapshot and
   fails on any unregistered or misclassified dialog.

These rules are non-negotiable for any dialog change:

1. **No unregistered dialogs**: after adding, moving, or removing a dialog, run
   `python -m quill.tools.dialog_inventory --write` and stage
   `tests/unit/ui/fixtures/dialog_inventory.json`. Review the diff — a new key
   appearing with the wrong classification means the dialog uses a non-sanctioned
   surface and must be reworked, not rubber-stamped.
2. **No bespoke surface drift**: only `native`, `web`, or `hardened_custom`
   surfaces are allowed. Do not introduce a new dialog framework or a non-`wx`
   modal surface.
3. **No unlabeled controls**: every actionable control has an explicit accessible
   name.
4. **No implicit defaults**: every modal has an explicit default action (Enter)
   and Escape/close behavior; route modal show through the `dialog_contract`
   helpers (`apply_modal_ids`, `show_modal_dialog`).
5. **No focus ambiguity**: set deterministic initial focus on open and return
   focus to the initiating editor/control on close.
6. **No lifecycle leaks**: a raw `wx.Dialog(...)` must `Destroy()` (or use the
   `with wx.Dialog(...)` form); button sizers use `wx.EXPAND`, never
   `wx.ALIGN_RIGHT`.
7. **No silent regressions**: add at least one focused source-contract or behavior
   test per dialog bug class.

Dialog Change Checklist (every dialog PR):

- [ ] `dialog_inventory.json` snapshot regenerated and staged
- [ ] `dialogs.md` updated (new row, binding, or nested/startup note)
- [ ] classification reviewed (`native` / `web` / `hardened_custom`)
- [ ] A11Y-4 banned-pattern gate and `test_dialog_inventory.py` pass
- [ ] targeted dialog test added/updated
- [ ] manual SR/keyboard verification logged for shipped dialogs

Source-of-truth rule: before closing any dialog work item, run
`python -m quill.tools.dialog_inventory`; if the scan and the committed registry
disagree, the work is incomplete regardless of checklist status.
