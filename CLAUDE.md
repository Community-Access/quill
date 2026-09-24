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

# Tests, parallel (~5 min vs ~9). Tests marked `machine_global` — the ones
# that drive the real clipboard, the system-wide hotkey table or the
# screen-reader bridges — share one worker; everything else fans out. Mark a
# new test that reaches for one of those, or it will race the others. The
# grouping was silently wrong twice (ignored, then too coarse to let the
# suite exit); tests/conftest.py pytest_collection_modifyitems has both
# stories and tests/unit/test_parallel_grouping.py asserts them.
#
# This is the FAST path, not the authoritative one: a worker can still die
# ("node down"), which predates the grouping and is unrelated to it. Re-run any
# failure it reports on its own before believing it -- every one so far passed
# serially. `pytest -q` is the answer that counts.
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
- **`quill/apps`** — the QuillVille apps, each an entry point plus its mixins: Radio, Cast, Studio, Weather, Inkwell, Converter, Player, Beacon and QuillLite. `standalone/<app>/` is only a packaging shell; **feature code never lives there**, because every repo-wide gate scopes to `quill/` and a surface no gate can see is one that rots.

**QuillLite may never be ahead of QUILL.** `quill.apps.lite` is the editor-only
sibling (`standalone/quilllite/`), and it exists on one condition: if it needs
something the editor cannot do, the capability goes in the **shared** package and
QUILL gets a way to reach it in the same change. A feature the small product has
and the big one does not is backwards, and invisible — nobody opens QUILL and
notices the absence of a thing they have only ever seen elsewhere. Applying that
rule in 2026-09 moved numbered bookmarks to `quill/core/numbered_bookmarks.py`,
deleted a duplicate of `format_ops`, made `create_richedit_rtf` build the
extended `RichEditDocument`, and gave QUILL six commands it had the capability
for and no binding to (`quill/ui/main_frame_rich_paragraph.py`). Applying it again
in 2026-09 moved the **hosted free AI** out of `quill/apps/lite_ai*.py` into
`quill/ui/hosted_ai_*.py`, where QUILL reaches the same five commands on the same
five chords through one small adapter (`quill/ui/main_frame_hosted_ai.py`) that
has no commands of its own — and a test asserts that absence, because a second
implementation is how this rule gets broken quietly, far more easily than a
missing feature. Where the two must diverge on a key, the reason is a comment in
`keymap.py`.

**The eleven family rules** live in `quill/core/family_rules.py`, and code cites
them **by number** (`keymap.py`: "which rule 6 forbids"; `lite/parity.py`: "the
note keeps the shorter chord (rule 3)"). Add at the end, never renumber --
`tests/unit/core/test_family_rules_and_gates.py` checks that every citation in
the tree resolves, which is what stops a reshuffle turning those comments into
lies. Lower number wins when two conflict. In brief: Microsoft's key wins for a
function both editors have (1); the command both products have keeps the chord
(2); frequency breaks ties (3); destructive habits are fixed first (4); a chord
free in both becomes an alias rather than a move (5); nothing QuillLite reaches
plainly lives on QUILL's leader (6); editor chords are for the editor (7); every
command has a key or a written reason (8); once-a-year commands get *a* key, not
a short one (9); value flows both ways but violations flow one (10); every
remaining divergence is a comment *and* a parity-table row (11).

**The six parity gates** closed the 2026-09 family-parity program. Its worklist
lived in a root `bad.md`, which was spent and deleted on 2026-09-20 (the root
layout gate sanctions no such file); the `bad.md <row>` citations scattered
through the source name rows of that closed program and resolve in git history,
not on disk. Five
are pytest gates and one is a tool in `platform_report`:

- **Bound-command and Quillin-hotkey** (`tests/unit/core/test_family_rules_and_gates.py`):
  every editor command has a chord, a per-command reason, or a family exemption
  under rule 7; and no bundled Quillin claims a chord the editor binds, because
  whichever loses is silent about losing.
- **Menu shape** (`tests/unit/ui/test_menu_shape_against_microsoft.py`): the
  top-level order, and the menu each shared command lives in, against Word,
  WordPad and Notepad. A wrong guess costs a listener seconds per visit.
- **Settings vocabulary** (`quill/tools/settings_vocabulary_audit.py`, in
  `platform_report`): every field on either side is `shared`, `aliased` or a
  reviewed `one_side`. A new setting is `missing` and fails until somebody asks
  whether the other product already has it under another name -- which is how
  `check_updates_on_launch` / `auto_check_updates` went unnoticed twice. Not a
  name-similarity check: two of the five real pairs share no word at all.
  Regenerate with `--write`.
- **Documentation chords** (`tests/unit/ui/test_documentation_chords.py`): a
  chord a user guide *teaches* must be one something binds. The 2026-09 pass
  found 46 stale ones, several since taken by a different command -- so
  following the guide did the wrong thing rather than nothing.
- **GATE-PERF** (`tests/unit/core/test_large_document_budget.py`, marked
  `perf`): a synthetic 50 MB buffer, against a ceiling rather than against the
  other editor -- comparing the two would pass a build where both had become
  slow together. This is what keeps the shared `DocumentText` from rotting.

### Key invariants

**Threading:** UI thread owns all wx widgets. Background work runs on `stability.task_manager.QuillTaskManager` (a `ThreadPoolExecutor` wrapper). Cross-thread UI updates always go through `wx.CallAfter`. See `docs/QUILL-PRD.md`.

**Persistence:** All JSON writes are atomic via `core.storage.write_json_atomic` (temp file + `os.replace`). Settings are schema-validated. Sensitive settings use DPAPI on Windows.

**Safe Mode:** `QUILL_SAFE_MODE=1` (or `--safe-mode` flag) disables AI, watch folder, and Quillin contributions. Gated in `assistant_ai.py`, `main_frame.py`, and `main_frame_quillins.py`.

**Dialogs:** All modal dialogs must go through `_show_modal_dialog` (in `MainFrame`) — never call `ShowModal()` directly. `apply_modal_ids` ensures keyboard contract. The dialog inventory gate (`dialog_inventory.py`) audits compliance. A **Close/Cancel button must be bound via `dialog_contract.bind_close_button`**: `wx.Dialog` answers `ID_CANCEL` for free but `wx.Frame` does not, so a surface that can run modeless ships a button that does nothing without it (`test_close_button_contract.py`).

**Menu accelerators (a rule, not a preference):** every enabled menu item — top level, submenu, and dynamic rows alike — must show a keyboard route in its label, and no two items in one menu bar may claim the same key. Walking a menu to discover there is no shortcut is a cost a screen-reader user pays on every visit, and a key claimed twice means one of the pair silently never fires. Prefer `self._menu_label(title, command_id)` over a literal, so the label renders whatever is *actually* bound and follows the user when they rebind it; per-app defaults live in `keymap.APP_KEYMAPS` (app keys, not editor keys: Ctrl+B is Browse in Quill Radio and Bold in QUILL). Only a *disabled* status readout is exempt. Enforced by `tests/unit/ui/test_menu_accelerators.py`, which also rejects keys `wx.AcceleratorEntry` cannot parse (`Ctrl+Shift+Plus` is silently dropped by wx, leaving the menu advertising a key that does nothing).

**Speak only what the screen reader does not already say (GATE-13):** the reader announces window and dialog titles, focus moves, control names, roles and states, selection changes in a list, and the text of a control that just received focus -- the app must never announce any of those, only what it alone knows (a background result, a state change on an unfocused control, an action's outcome). Under-announcing gets filed as a bug; over-announcing is absorbed as "this app is chatty" and never filed, which is why it needs a gate: `check_over_announce.py` flags an announce inside an `EVT_SET_FOCUS` handler, an announce of `GetTitle()`, and an announce of a `title=` literal. A verbosity setting is not the fix -- say less instead of making the user configure how much less. (Announcing a status label after `SetLabel` stays correct: that is GATE-12's cure, since label changes on unfocused text are exactly what the reader does not say.)

**Access keys (GATE-14):** within one window, no two controls may claim the same `&` mnemonic. Windows cycles focus between duplicates instead of pressing, so one of the pair silently cannot be reached and nothing announces the loss (the first sweep found 128 collisions across 76 windows). `check_access_keys.py` scopes a `wx.Dialog`/`wx.Frame` subclass as one window and any other class per method. Three fixes, in order: **OK, Cancel and Close carry no access key at all** (Enter and Escape already serve them, and every letter they give up resolves a collision elsewhere); otherwise move the less important control to a free letter; and when a dense window genuinely runs out — an embedded radio surface is under a menu bar that owns thirteen of twenty-six letters — the loser gets **no** mnemonic rather than a duplicate, because a duplicate advertises a key that may not work while silence is merely silent and Tab still arrives.

**F1 answers everywhere (GATE-<APP>-HELP):** every window in every app answers F1 with its authored purpose and then the focused control's own help. The engine is shared (`quill/ui/app_context_help.py` + `quill/core/control_help.py`); each app owns a `surface_help` catalogue and a help-audit gate over its own modules — radio, cast, player, studio, inkwell, weather, converter, beacon and QuillLite, all nine rostered in `platform_report`. Authored help must be **inline `SetHelpText` at the construction site**: that is what the audit can verify (`helped`); help set anywhere else is `help-elsewhere` and proves nothing. A new control snapshots as `missing` and fails the build until somebody writes a sentence or classifies it deliberately. One load-bearing detail: `SetHelpText` stores nothing without a `wx.HelpProvider`, so `ensure_help_provider()` runs at activation — without it every help string ever written is dead. The complete authored content renders to `docs/f1-help-reference.md` (`build_help_reference.py`, drift-gated).

**Behavioural coverage (GATE-LITE-COVER):** every handler in QuillLite's command
table is classified `covered` or `shape_only` in
`tests/unit/ui/fixtures/lite_command_coverage.json`, and **the `shape_only` list
is empty** — every handler has a behavioural test (161 of them
when that became true on 2026-09-11, 198 on 2026-09-18), and the gate now
asserts zero rather than a ceiling. `covered` means a test in `tests/unit/apps` **calls** the
handler -- detected by an AST walk, not a grep, because a test that lists handler
names in a table is exactly the shape of test that let the F8 bug through
(`cmd_start_extend_selection` had a key, a label, a handler and a passing test,
and extend mode had never once worked from the keyboard). A new command fails
the build until it is classified; so does a handler that *lost* its test, and so
does one that gained a test and was not re-snapshotted. Regenerate with
`python -m quill.tools.lite_command_coverage --write`.

Two things follow from how detection works, and both bite. **Parametrize over
lambdas, not handler names**: `getattr(win, name)()` over a parametrized string
is invisible to the scan, and it hid fourteen genuinely tested handlers until
2026-09-11 — write `(lambda w: w.cmd_italic(), ...)` so the call is in the
source. And **a dialog imported at module scope must be patched in the module
that imported it**, not where it is defined; `tests/unit/apps/conftest.py`'s
`DialogRecorder` names both ends of every entry point for that reason, and its
`lite_dialogs` / `fake_wx_dialog` fixtures are how a command behind a modal is
reached at all. They answer **cancel** by default, because cancel is the branch
people forget to write.

**Feedback channels (`quill/core/action_feedback.py`):** `action_feedback` and
`find_not_found_feedback` are `sound` / `speech` / `both` / `silent`, and both
editors resolve them through the one shared `resolve(mode, *, has_sound)` rather
than implementing the enum twice. Three invariants: a `sound` moment with no clip
in the pack **speaks** (the setting chooses between two kinds of feedback, never
down to none); `silent` stays silent through that fall-through; and failures and
counts are outside the setting entirely -- always spoken, because no tone carries
a number and none has ever carried "it did not work". Wording for any chooser
comes from `ACTION_FEEDBACK_LABELS`, never retyped.

**Generated references (GATE-KEYREF, GATE-HELPREF, GATE-SETDOC):** three documents are generated from the code rather than written beside it, so they cannot drift — `docs/keyboard-reference.md` from `DEFAULT_KEYMAP`/`APP_KEYMAPS`, `docs/f1-help-reference.md` from the help catalogues, and the settings-documentation inventory from the `Settings` dataclass against the docs corpus. A new setting is `missing` until it is documented or classified `internal`; the `grandfathered` backlog (2026-08-27) may only shrink. Every default QUILL-key chord must also carry an authored Key Describer title (`_CHORD_COMMAND_TITLES`, GATE-DESCRIBE).

**Site links (GATE-SITE-LINKS):** `tests/unit/docs/test_site_links.py` models what `.github/workflows/github-pages.yml` actually assembles — the hand-built shell (`docs/site/**`), every `docs/**/*.html` outside it flattened into `/docs/` **by bare basename**, and the seven governance pages rendered at deploy — then fails on any internal `href`/`src` that resolves to nothing, any podcast transcript without an episode in `episodes.json`, and any episode without a transcript. It exists because nothing in the tree had ever validated a link: 32 transcripts from the 36→54 episode renumbering sat live for months pointing at audio that no longer existed (issue #1558), and its first run found nine more. Two consequences for new work: a new doc needs a **globally unique basename** (the flatten means a second `README.html` anywhere overwrites the first), and `build_feed.py` prunes rather than only adding, because a build that cannot remove cannot notice a rename.

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
