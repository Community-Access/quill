# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```powershell
# Install
pip install -e ".[ui,dev]"

# Install, fast (uv resolves/installs the same extras in seconds; dev-only
# tooling — releases still build with pip + the pinned system Python)
uv pip install -e ".[ui,dev]"

# Run the app
python -m quill

# Tests (standard)
pytest -q

# Tests, parallel (~5.5 min vs ~9; wx/UI tests stay on one worker — see
# tests/conftest.py pytest_collection_modifyitems for why loadgroup)
pytest -q -n 8 --dist loadgroup

# Fast smoke subset (high-signal core checks; seconds, not minutes)
pytest -m smoke -q

# Single test
pytest tests/unit/core/test_paths.py -x -q

# Run unit + stability
pytest tests/unit/ tests/stability/ -q

# Lint
ruff check .
ruff format --check .

# Scoped type-check (always scoped — never run unscoped mypy)
mypy quill\core quill\io

# Quillin self-lint
python -m quill.tools.quillin_lint <dir> --strict

# Agent standards lint (default: bundled agents dir; pass a path to lint one)
python -m quill.tools.agent_lint quill/core/ai/agents --strict

# Every gate at once, as one accessible scorecard (exit != 0 on any failure)
python -m quill.tools.platform_report

# App icons (regenerate all; --check fails on drift, --preview writes 256/16 PNGs)
python scripts/build_app_icons.py
```

The `tests/conftest.py` fixture sets `quill.core.paths._DEV_BUILD = True` for the whole test session. Any test that sets `QUILL_DATA_DIR` for isolation depends on this; do not remove it.

## Architecture

QUILL is a layered wxPython desktop application with strict import boundaries:

- **`quill/core`** — pure domain logic (documents, command registry, settings, keymap, storage, AI sessions, recovery). No `wx` imports. Strict-typed; always in scope for `mypy`.
- **`quill/io`** — format readers/writers (`read(path) -> Document`, `write(doc, path)`). No `wx`. Strict-typed.
- **`quill/ui`** — wxPython shell. `main_frame.py` is the primary entry point (~27k lines and still the largest module by far); decomposition into feature mixins (see `main_frame_vault.py`, `main_frame_speech.py`, `main_frame_braille.py`, etc.) is the preferred home for new command handlers — add to a mixin, not to `main_frame.py`. Gradual typing (excluded from `mypy`).
- **`quill/platform/windows`** — Windows-specific bridges: `prism_bridge.py` (screen-reader announcements via Prism/pyttsx3), `sr_detect.py`, `dpapi.py`, `credential_manager.py`.
- **`quill/stability`** — cross-cutting runtime safety: `safe_subprocess.py`, `crash_report.py` (diagnostic bundles), `redaction.py` (secret scrubbing), `task_manager.py`, `wx_heartbeat.py`, `safe_mode.py`.
- **`quill/tools`** — internal CI gates: `check_banned_patterns.py`, `module_size_budget.py`, `network_egress_audit.py`, `dialog_inventory.py`, `dialog_button_contract.py`, `quillin_lint.py`, `error_code_audit.py`.
- **`quill/plugins`** — plugin-facing API surfaces and Quillin (extension) manifest model.

### Key invariants

**Threading:** UI thread owns all wx widgets. Background work runs on `stability.task_manager.QuillTaskManager` (a `ThreadPoolExecutor` wrapper). Cross-thread UI updates always go through `wx.CallAfter`. See `docs/QUILL-PRD.md`.

**Persistence:** All JSON writes are atomic via `core.storage.write_json_atomic` (temp file + `os.replace`). Settings are schema-validated. Sensitive settings use DPAPI on Windows.

**Safe Mode:** `QUILL_SAFE_MODE=1` (or `--safe-mode` flag) disables AI, watch folder, and Quillin contributions. Gated in `assistant_ai.py`, `main_frame.py`, and `main_frame_quillins.py`.

**Dialogs:** All modal dialogs must go through `_show_modal_dialog` (in `MainFrame`) — never call `ShowModal()` directly. `apply_modal_ids` ensures keyboard contract. The dialog inventory gate (`dialog_inventory.py`) audits compliance. A **Close/Cancel button must be bound via `dialog_contract.bind_close_button`**: `wx.Dialog` answers `ID_CANCEL` for free but `wx.Frame` does not, so a surface that can run modeless ships a button that does nothing without it (`test_close_button_contract.py`).

**Menu accelerators (a rule, not a preference):** every enabled menu item — top level, submenu, and dynamic rows alike — must show a keyboard route in its label, and no two items in one menu bar may claim the same key. Walking a menu to discover there is no shortcut is a cost a screen-reader user pays on every visit, and a key claimed twice means one of the pair silently never fires. Prefer `self._menu_label(title, command_id)` over a literal, so the label renders whatever is *actually* bound and follows the user when they rebind it; per-app defaults live in `keymap.APP_KEYMAPS` (app keys, not editor keys: Ctrl+B is Browse in Quill Radio and Bold in QUILL). Only a *disabled* status readout is exempt. Enforced by `tests/unit/ui/test_menu_accelerators.py`, which also rejects keys `wx.AcceleratorEntry` cannot parse (`Ctrl+Shift+Plus` is silently dropped by wx, leaving the menu advertising a key that does nothing).

**Speak only what the screen reader does not already say (GATE-13):** the reader announces window and dialog titles, focus moves, control names, roles and states, selection changes in a list, and the text of a control that just received focus -- the app must never announce any of those, only what it alone knows (a background result, a state change on an unfocused control, an action's outcome). Under-announcing gets filed as a bug; over-announcing is absorbed as "this app is chatty" and never filed, which is why it needs a gate: `check_over_announce.py` flags an announce inside an `EVT_SET_FOCUS` handler, an announce of `GetTitle()`, and an announce of a `title=` literal. A verbosity setting is not the fix -- say less instead of making the user configure how much less. (Announcing a status label after `SetLabel` stays correct: that is GATE-12's cure, since label changes on unfocused text are exactly what the reader does not say.)

**Access keys (GATE-14):** within one window, no two controls may claim the same `&` mnemonic. Windows cycles focus between duplicates instead of pressing, so one of the pair silently cannot be reached and nothing announces the loss (the first sweep found 128 collisions across 76 windows). `check_access_keys.py` scopes a `wx.Dialog`/`wx.Frame` subclass as one window and any other class per method. Three fixes, in order: **OK, Cancel and Close carry no access key at all** (Enter and Escape already serve them, and every letter they give up resolves a collision elsewhere); otherwise move the less important control to a free letter; and when a dense window genuinely runs out — an embedded radio surface is under a menu bar that owns thirteen of twenty-six letters — the loser gets **no** mnemonic rather than a duplicate, because a duplicate advertises a key that may not work while silence is merely silent and Tab still arrives.

**F1 answers everywhere (GATE-<APP>-HELP):** every window in every app answers F1 with its authored purpose and then the focused control's own help. The engine is shared (`quill/ui/app_context_help.py` + `quill/core/control_help.py`); each app owns a `surface_help` catalogue and a help-audit gate over its own modules — radio, cast, player, studio, inkwell, weather, converter and beacon, all eight rostered in `platform_report`. Authored help must be **inline `SetHelpText` at the construction site**: that is what the audit can verify (`helped`); help set anywhere else is `help-elsewhere` and proves nothing. A new control snapshots as `missing` and fails the build until somebody writes a sentence or classifies it deliberately. One load-bearing detail: `SetHelpText` stores nothing without a `wx.HelpProvider`, so `ensure_help_provider()` runs at activation — without it every help string ever written is dead. The complete authored content renders to `docs/f1-help-reference.md` (`build_help_reference.py`, drift-gated).

**Generated references (GATE-KEYREF, GATE-HELPREF, GATE-SETDOC):** three documents are generated from the code rather than written beside it, so they cannot drift — `docs/keyboard-reference.md` from `DEFAULT_KEYMAP`/`APP_KEYMAPS`, `docs/f1-help-reference.md` from the help catalogues, and the settings-documentation inventory from the `Settings` dataclass against the docs corpus. A new setting is `missing` until it is documented or classified `internal`; the `grandfathered` backlog (2026-08-27) may only shrink. Every default QUILL-key chord must also carry an authored Key Describer title (`_CHORD_COMMAND_TITLES`, GATE-DESCRIBE).

**Network egress:** `network_egress_audit.py` inventories every outbound call site. New network calls require explicit consent and a new entry in the audit.

**External-engine allowlist:** `external_engine.py` only accepts executables in `_ENGINE_EXECUTABLE_BASENAMES` (node, python, quill-engine). The allowlist is enforced in both `configure_engine` and `probe_engine`.

**Error codes (GATE-EC):** Every custom top-level exception class in `quill/core`, `quill/io`, and `quill/stability` must inherit `CodedError` (`core/error_codes.py`) — or an already-coded parent — and declare its own unique `code = "QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>"`. The migrated shape is `class X(CodedError):`, never `class X(Exception, CodedError):` (that MRO raises `TypeError`). `error_code_audit.py` enforces this across the live tree; a new uncoded exception class fails the build.

**SSH host keys:** `core/ssh/client.py` defaults to `paramiko.RejectPolicy`. `AutoAddPolicy` requires `trust_first_use=True` (or `settings.ssh_trust_first_use`).

**Windows code signing (Authenticode):** `scripts/code_signing.py` is the single tool for OS code signing via Azure Trusted Signing (`metadata.json` at repo root; auth is the ambient `az login` / workload-identity credential, no PFX). It locates `signtool`, stages+SHA-256-verifies the signing dlib into gitignored `build/deps/trusted-signing/`, and invokes `signtool` with an argv list — never through an MSYS/Git-Bash shell, which mangles `/fd`-style switches. It is **opt-in** (`QUILL_SIGN=1`) and **fail-open** (a failure aborts only under `QUILL_SIGN_REQUIRED=1`), so plain builds are unchanged. Wired into all seven installers — `build_windows_distribution.py` (main app) and every `standalone/*/scripts/build_release.ps1` (`-Sign`): payload `.exe`/`.dll` signed before packaging; each `Setup.exe` and its uninstaller signed by Inno's native `SignTool` + `SignedUninstaller` during compile, gated behind an `#ifdef Sign` block (ISCC gets `/DSign` + a `/Squilltrusted=` mapping) so unsigned builds compile unchanged. This is distinct from `quill/tools/signing.py` (Ed25519 artifact provenance) and the update-feed key. Runbook: `docs/code-signing.md`.

**`QUILL_DATA_DIR`:** Respected only when `_DEV_BUILD=True` (i.e., `QUILL_DEV_BUILD=1`). In release builds the env var is ignored; dev overrides must also stay under `Path.home()`.

**Surface reachability (GATE-REACH):** every module under `quill/ui` that builds a window (`wx.Dialog`, `wx.Frame`, `ShowModal`, `_show_modal_dialog`) must be reachable by imports from an app entry point — `quill/__main__.py`, `quill/apps/*.py`, `quill/ui/main_frame*.py`. **Tests do not count as callers**: Cast's first-run dialog shipped unreachable for two releases with passing tests and a user guide describing it. `surface_reachability_audit.py` walks the import graph and compares against `tests/unit/ui/fixtures/surface_reachability.json`; a surface genuinely reached by a registry or string dispatch is classified `dynamic` (or `parked`) in that snapshot, and the classification *is* the review. Regenerate with `python -m quill.tools.surface_reachability_audit --write`.

**App icons:** every app in `standalone/` that ships a Windows installer must have an entry in `scripts/build_app_icons.py`, which owns the family design system (one rounded tile, one amber accent, a distinct silhouette *and* a distinct hue+lightness per app). Icons are generated, never hand-edited. `tests/unit/scripts/test_app_icons.py` fails if two apps render the same face, if a committed `.ico` has drifted from source, or if a new installer appears with no icon entry — the seam that let four apps ship byte-identical copies of Quill Radio's icon.

### Module size budget

`quill/tools/module_size_budgets.json` tracks line-count ceilings (GATE-11). The budget is a ratchet: values may only decrease as modules are extracted. When a tracked module grows, update the budget entry and add a `_rebaseline_<date>` comment explaining why.

### Quillin extensions

Quillins are sandboxed extensions in `quill/quillins_bundled/` and user-installed paths. Each has a `manifest.json` validated against `quill/core/schemas/extension.json`. Lint with `python -m quill.tools.quillin_lint <dir> --strict`.
