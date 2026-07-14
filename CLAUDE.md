# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```powershell
# Install
pip install -e ".[ui,dev]"

# Run the app
python -m quill

# Tests (standard)
pytest -q

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

**Dialogs:** All modal dialogs must go through `_show_modal_dialog` (in `MainFrame`) — never call `ShowModal()` directly. `apply_modal_ids` ensures keyboard contract. The dialog inventory gate (`dialog_inventory.py`) audits compliance.

**Network egress:** `network_egress_audit.py` inventories every outbound call site. New network calls require explicit consent and a new entry in the audit.

**External-engine allowlist:** `external_engine.py` only accepts executables in `_ENGINE_EXECUTABLE_BASENAMES` (node, python, quill-engine). The allowlist is enforced in both `configure_engine` and `probe_engine`.

**Error codes (GATE-EC):** Every custom top-level exception class in `quill/core`, `quill/io`, and `quill/stability` must inherit `CodedError` (`core/error_codes.py`) — or an already-coded parent — and declare its own unique `code = "QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>"`. The migrated shape is `class X(CodedError):`, never `class X(Exception, CodedError):` (that MRO raises `TypeError`). `error_code_audit.py` enforces this across the live tree; a new uncoded exception class fails the build.

**SSH host keys:** `core/ssh/client.py` defaults to `paramiko.RejectPolicy`. `AutoAddPolicy` requires `trust_first_use=True` (or `settings.ssh_trust_first_use`).

**`QUILL_DATA_DIR`:** Respected only when `_DEV_BUILD=True` (i.e., `QUILL_DEV_BUILD=1`). In release builds the env var is ignored; dev overrides must also stay under `Path.home()`.

### Module size budget

`quill/tools/module_size_budgets.json` tracks line-count ceilings (GATE-11). The budget is a ratchet: values may only decrease as modules are extracted. When a tracked module grows, update the budget entry and add a `_rebaseline_<date>` comment explaining why.

### Quillin extensions

Quillins are sandboxed extensions in `quill/quillins_bundled/` and user-installed paths. Each has a `manifest.json` validated against `quill/core/schemas/extension.json`. Lint with `python -m quill.tools.quillin_lint <dir> --strict`.
