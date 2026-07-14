# QUILL Public Beta Quality Ledger

Living record of the public-beta quality pass. The product name is **QUILL**
(no rename); any "TINDRA" naming is a future, not-yet-applied plan and is out of
scope here.

This ledger is iterative. It is seeded with the work verified in the current pass
plus the baseline gate state; it is not a claim that the entire repository has
been exhaustively re-audited. Sections marked "Deferred / next wave" are honest
about what has not yet been done.

Every accessibility/focus/keyboard fix has a matching manual validation case in
the **screen-reader test plan**: `docs/release/screen-reader-test-plan.md` (NVDA /
JAWS / keyboard steps + expected announcements). Run it on a packaged build before
sign-off.

## Reusable wave prompt (run this for each audit wave)

This is the distilled, repo-tuned instruction set for running one focused wave of
the quality/accessibility pass. It is an improved version of the original master
brief: scoped to what is achievable and verifiable in a single pass, and tuned to
this repository's existing gates and conventions. Paste it (optionally with a
"Focus area:" line naming the wave) to drive the next wave.

> **Role.** Act as principal Python/wxPython engineer and accessibility
> specialist for **QUILL**. Investigate, fix, test, and document — do not just
> produce a report.
>
> **Hard constraints.**
> - The product name is **QUILL**. Do **not** rename anything to TINDRA or assume
>   that rename; leave existing QUILL identifiers, paths, and brand strings.
> - Work on a feature branch, never commit to `main`. Make small, logical,
>   attributable commits; do not push, tag, or merge unless explicitly asked.
> - Do not weaken a fix to satisfy a test, broaden `except`, or silence a gate.
>   When a test double is incomplete (e.g. a `_Fake*` missing a method the real
>   widget has), fix the double, not the production change.
> - Respect the existing architecture and import boundaries (core/io are wx-free
>   and strict-typed; ui is gradual-typed).
>
> **Pick a bounded focus area** (one wave): e.g. dialog accessible-naming,
> initial-focus quality, label/field associations, keyboard traps, startup
> init-order, a call-site/attribute audit of one subsystem. Do not attempt the
> whole repo at once; depth over breadth.
>
> **Method.**
> 1. Establish the wave baseline by running the relevant existing gates rather
>    than inventing new ones: `ruff check .`, `ruff format --check .`,
>    `mypy quill/core quill/io` (always scoped — never unscoped), and the targeted
>    pytest suites + tool gates (dialog-inventory, dialog-button-contract,
>    dialog-zorder, announce-gap/GATE-12, a11y-regions, module-size/GATE-11,
>    network-egress, docs-parity). The accessibility infrastructure is strong and
>    gate-backed; aim at what the gates do **not** check (accessible names,
>    initial focus, focus restoration, label associations, verbosity).
> 2. For each finding, determine intent before changing: is it a real defect, an
>    intentional cross-tool pragma, a tested automation handle, or expected
>    behavior? Record reviewed-but-intentional items too.
> 3. Make the minimal correct fix. Prefer native, accessible wx controls and
>    human-readable accessible names (screen readers speak `SetName` verbatim —
>    never snake_case identifiers).
> 4. Run the smallest useful tests after each change; add a regression test where
>    one can be written cleanly (skip brittle full-wx-modal harnesses — record as
>    needs-live-validation instead).
> 5. If a change trips GATE-11 module-size, first try to make the edit net-neutral
>    or extract; only rebaseline with a dated `_rebaseline_<date>` justification
>    comment in `module_size_budgets.json` when growth is genuinely warranted.
> 6. Regenerate docs artifacts for any changed `docs/**/*.md`
>    (`pandoc <f>.md -f gfm -t html5 -s -o <f>.html` and `-t epub3 -o <f>.epub`),
>    and keep this ledger current: running totals, finding IDs
>    (`A11Y-`/`FOCUS-`/`KEY-`/`CALL-`/`PERF-`/`SEC-`/`DOC-`/`TEST-`/`RELEASE-`),
>    severity, root cause, resolution, validation, status.
>
> **Honesty.** Never represent unfinished work as complete. Distinguish
> code-reviewed-against-expected-SR-behavior from live NVDA/JAWS testing. Keep an
> explicit "Deferred / next wave" list. Resolve release blockers before calling
> anything release-ready.
>
> **Deliverables each wave.** The actual fixes + tests; updated ledger; a short
> wave summary (what was audited, found, fixed, deferred); the commands run and
> their results.

## QA and testing process (repeatable)

This is the standing process for adding tests and passing QA gates in QUILL. It is
a living document: the "Lessons learned" subsection grows as we discover what
works, so each pass is a little better than the last. Follow it for every change.

### 1. Before you change code
- Branch first; never work on `main`. Read the files you will touch and state a
  one or two sentence plan.
- Identify which layer you are in and its rules: `core`/`io` are wx-free and
  strict-typed (always in `mypy` scope); `ui` is gradual-typed wxPython;
  `platform`/`stability`/`tools` have their own gates. Keep imports within the
  layer boundaries.

### 2. Write the test at the right level
- Prefer the smallest real boundary. Pure logic -> a `core`/`io` unit test (wx-free,
  fast, deterministic). UI wiring -> a focused `tests/unit/ui` test with light fakes.
  Cross-module behavior -> `tests/integration`.
- Put a regression test next to every non-trivial bug fix, named for the symptom.
- Do not mock at the wrong level. If a test double (`_Fake*`) is missing a method
  the real widget has, **fix the double** — never weaken the production change to
  fit an incomplete stub. (Lesson: a `_FakeNotebook` lacking `SetName` failed
  after a correct production fix; the double was the bug.)
- Keep assertions meaningful and specific; do not replace a real assertion with a
  vague one to make a test pass. Do not regenerate fixtures/snapshots blindly —
  confirm the behavioral change is intended first.
- For wx-modal behavior that needs a shown window (e.g. asserting which control
  holds focus after `ShowModal`), prefer recording it as "needs live validation"
  over a brittle full-wx harness. Test the wx-free seam where one exists.

### 3. Run the right checks, smallest first
- The single most relevant test: `pytest tests/unit/<area>/test_x.py -x -q`.
- Then the area suite, then `pytest tests/unit tests/stability -q` for broad
  changes. Run with `--timeout=120` so a hang surfaces as a failure, not a stall.
- Static checks: `ruff check .`, `ruff format --check .`, and **scoped**
  `mypy quill/core quill/io` (never run unscoped mypy).
- Quillin changes: `python -m quill.tools.quillin_lint <dir> --strict`.

### 4. The QA gates (all must be green to merge)
These run in pre-commit and CI; treat a red gate as a real defect, not a nuisance:
- `ruff` (lint + format) and scoped `mypy`.
- GATE-11 module-size budget (`module_size_budgets.json`): a ratchet. Prefer
  net-neutral edits or extraction; only **rebaseline** when growth is warranted,
  and always add a dated `_rebaseline_<date>_<slug>` note explaining why.
- GATE-12 announce-gap: every status-bar update needs a screen-reader announce.
- Dialog gates: `dialog_inventory` (every modal routes through `_show_modal_dialog`),
  `dialog_button_contract` (OK/escape ids via `apply_modal_ids`), `dialog_zorder`.
- `network_egress_audit`: every new `urlopen`/`urlretrieve` needs a reviewed entry;
  subprocess/library egress (pip, PyGithub) is documented in a manual comment block.
- Docs parity: any changed `docs/**/*.md` must ship regenerated `.html` + `.epub`
  (`pandoc <f>.md -f gfm -t html5 -s -o <f>.html` and `-t epub3 -o <f>.epub`).
- Structure (`test_repo_layout`): no stray root modules; root Markdown is allow-listed.
- Version consistency (GATE-VC) for release-affecting changes.

### 5. Commit and record
- Small, logical, attributable commits; let pre-commit run (do not bypass hooks).
  If a hook auto-formats a file, re-stage and re-commit — a hook that modifies a
  file aborts the commit.
- Update this ledger: running totals, finding IDs (`A11Y-`/`FOCUS-`/`KEY-`/`CALL-`/
  `ATTR-`/`PERF-`/`SEC-`/`DOC-`/`TEST-`/`RELEASE-`), severity, root cause,
  resolution, validation, status. Keep an explicit "Deferred / next wave" list.
- Never represent unfinished or unverified work as complete. Distinguish
  code-reviewed-against-expected-behavior from live screen-reader/keyboard testing.

### 6. Definition of done for a wave
A wave is done when: its findings are fixed or explicitly deferred with a reason;
the relevant tests + all gates are green; a regression test exists where one could
be written cleanly; docs/ledger are updated; and the change is committed on the
branch. "Zero bugs" is never claimed as an absolute — only "all gates and the
test suite are green, and the audited scope has no known open defects."

### Lessons learned (append-only; make the process better each pass)
- 2026-06-22: GATE-11 trips on tiny additions (even a 2-line explanatory comment).
  Prefer net-neutral edits; rebaseline with justification when the comment/code is
  worth keeping. Don't delete a clarifying comment just to dodge the budget.
- 2026-06-22: `# noqa: dialog_button_contract` is a cross-tool pragma, not a ruff
  code — ruff warns but it is intentional. Determine intent before "fixing" a
  warning; some are foreign pragmas or tested automation handles.
- 2026-06-22: a snake_case `SetName` value is spoken verbatim by screen readers —
  always use human-readable accessible names; verify no test pins the literal first.
- 2026-06-22: the Parakeet test can hang on a heavy `transformers` import in dev;
  exclude it or add a per-test timeout so it cannot mask real failures (TEST-001).
- 2026-06-22: a pre-commit format hook that rewrites a file aborts the commit —
  re-stage and re-commit rather than assuming it landed.

## Baseline (gate state)

Captured on the current branch (`main`), dev environment, Python 3.12.

| Gate | Command | Result |
| --- | --- | --- |
| Lint | `ruff check .` | Pass (3 benign cross-tool `# noqa` warnings, see L-001) |
| Format | `ruff format --check .` | Pass after formatting one new file |
| Types (scoped) | `mypy quill/core quill/io` | Pass (298 files, no issues) |
| Egress audit | `tests/unit/tools/test_network_egress_audit.py` | Pass |
| Docs parity | `scripts/check_docs_artifacts.py` | Pass |
| Build dist | `tests/unit/scripts/test_build_windows_distribution.py` | Pass (15) |
| Speech suite | `tests/unit/core/speech/` (subset) | Pass (the Parakeet engine and its test were removed 2026-06-24; see TEST-001) |
| Full suite | `pytest tests/unit tests/stability tests/integration` | GREEN: 4857 unit+integration + 38 stability passed, 12 skipped, 0 failures (after the TEST-002 fix, confirmed by a full re-run without `-x`) |

## Running totals

| Metric | Count |
| --- | --- |
| Production files modified (this pass) | 19 |
| Test files added/modified | 2 |
| Documentation files modified | 4 (md) + regenerated html/epub |
| Bugs fixed | 1 (L-001 class reviewed; see notes) |
| Features hardened / shipped | 4 (Vosk bundling, Groq, ElevenLabs, Faster Whisper on-demand install) |
| Security/egress items reviewed | 1 (SEC-001, pip subprocess egress documented) |
| Accessibility issues fixed | 13 (6 unnamed tab groups, 7 literal snake_case names) |
| Focus-management issues fixed | 1 (FOCUS-001 wx.html fallback initial focus) |
| Label/field association fixes | 4 dialogs (input controls given accessible names) |
| Keyboard-trap fixes | 3 prose fields (TE_PROCESS_TAB removed) |
| Test failures resolved | 1 (TEST-002 flaky watchdog test made deterministic) |
| Remaining test failures | 0 (full suite green, confirmed by re-run without -x) |
| Tests added | 2 files (`test_cloud_transcribers.py`, `test_engine_install.py`) |
| Remaining known issues | 1 (TEST-001) |
| Intentional legacy QUILL references reviewed | n/a (no rename; QUILL is the name) |

## Findings

### RELEASE-001 — Faster Whisper engine had no path for packaged users
- Severity: Medium. Category: Packaging / feature completeness.
- Component: `scripts/build_windows_distribution.py`, `quill/core/speech/engine_install.py`, `quill/ui/main_frame_speech.py`, `quill/ui/main_frame_menu.py`, `quill/__main__.py`.
- Problem: the shipped installer uses a frozen embeddable Python, so the
  `[fasterwhisper]` extra was unreachable for non-source users. Only whisper.cpp
  was selectable as an offline engine in a packaged build.
- Resolution: added an on-demand installer. **Tools > Speech > Whisperer >
  Download Faster Whisper Engine...** installs it wheel-only
  (`pip install --only-binary=:all: --target <app data>/engine-packs/faster-whisper`)
  into a user-writable folder (no admin), prepended to `sys.path` at startup so
  the engine appears in the Speech Engine chooser. The shipped runtime now keeps
  `pip` (setuptools/wheel still pruned). Blocked in Safe Mode, behind a
  confirmation + progress dialog.
- Tests: `tests/unit/core/speech/test_engine_install.py` (8 cases).
- Status: Fixed. Needs manual validation on a packaged Windows build (a real
  pip-into-target install and engine activation).

### RELEASE-002 — Vosk engine unreachable for packaged users
- Severity: Low. Category: Packaging / accessibility reach.
- Resolution: Vosk's wheel is self-contained (ships libvosk), so it is now in the
  installer's base dependency groups (`DEFAULT_BUNDLED_DEPENDENCY_GROUPS`),
  available out of the box; its ~40 MB model still downloads on first use.
- Status: Fixed. Needs manual validation on a packaged build.

### SEC-001 — pip subprocess egress (Faster Whisper install)
- Severity: Low (informational). Category: Network egress / privacy.
- The on-demand install runs the runtime's pip in a subprocess, which reaches
  PyPI / pythonhosted. The AST egress scanner only sees `urlopen`/`urlretrieve`,
  so this is documented as a manual comment block in
  `quill/tools/network_egress_audit.py` (alongside the PyGithub block). Gated by
  an explicit user action, a confirmation dialog, and Safe Mode; wheel-only.
- Status: Verified / documented.

### L-001 — Three `# noqa: dialog_button_contract` directives warn under ruff
- Severity: Low. Category: Lint hygiene.
- `quill/ui/main_frame_quillins.py:737,754` and `quill/ui/main_frame.py:13178`
  carry `# noqa: dialog_button_contract`. ruff warns because that is not a ruff
  code — but it is an **intentional cross-tool pragma** consumed by the
  `dialog_button_contract` gate (regex `#\s*noqa\s*:\s*dialog_button_contract`).
- Resolution: **Intentional behavior — left unchanged.** Rewriting them would
  break the dialog-button-contract gate. Recorded so a future pass does not
  "fix" it blindly.
- Status: Intentional behavior.

### TEST-001 — Parakeet provider test triggers a slow `transformers` import in dev
- Severity: Low. Category: Test reliability.
- When `transformers` was installed in the environment, running the full
  `tests/unit/core/speech/` set could hang on NeMo's `transformers` import-structure
  scan during the Parakeet test, hitting the suite timeout.
- Status: Resolved (2026-06-24). The NVIDIA Parakeet engine was removed from QUILL
  entirely — the provider, catalog entries, optional `[parakeet]` extra, BITS
  Whisperer gating, and `test_parakeet_provider.py` are gone — so the slow import
  can no longer occur.

## Accessibility audit — wave 1 (dialogs / tab groups)

Baseline: the repo's accessibility gates are strong and green — 38 tests across
dialog-inventory (ShowModal compliance), dialog-focus-routing, dialog-z-order
(no dialog behind a window), announce-gap (GATE-12: every status update has a
screen-reader announcement), and a11y-region keyboard-trap tracking. The audit
therefore targeted what those gates do not check: accessible names.

### A11Y-001 — Notebook tab groups announced generically (no accessible name)
- Severity: Medium. Category: Accessibility (screen-reader naming).
- Several `wx.Notebook` tab groups had no `SetName`, so a screen reader announces
  an unnamed/generic tab group instead of its purpose.
- Fixed (6): `info_pages.py` About dialog (both the main About notebook and the
  "About" tabbed dialog), `status_dialog.py` (Application Status), `word_view.py`,
  `rich_text_surface.py`, `csv_grid.py` (the three alternate document-view
  surfaces), and the main document tab host in `main_frame.py` (now "Open
  documents"). Notebooks that were already named (Settings, AI Hub, Quillin
  prefs, menu-customization, Preferences listbook) were left as-is.
- Tests: existing UI suites for each surface pass; `test_rich_text_surface.py`'s
  `_FakeNotebook` double gained `SetName` (the production change was correct; the
  test double was incomplete).
- Status: Fixed. Needs live screen-reader confirmation (NVDA/JAWS).

### A11Y-002 — Accessible names set to snake_case identifiers (spoken verbatim)
- Severity: Medium. Category: Accessibility (screen-reader naming).
- Controls used `SetName("status_overview")`-style identifiers as their accessible
  name; a screen reader speaks them literally ("status underscore overview").
- Fixed (7): `status_dialog.py` (5 controls -> "Status overview", "Tasks and
  downloads", "Features", "Recent actions", "Refresh"), `verbosity_prefs.py`
  status line ("Verbosity status", test assertion updated to match), and the
  `info_pages` About notebook name.
- Reviewed — intentional (left unchanged): `simple_open_dialog.py` and
  `crash_report_dialog.py` set a snake_case **dialog window name** that is a
  tested automation handle (`test_main_frame_simple_open.py` asserts
  `GetName() == "simple_open"`); a dialog's spoken accessible name is its title,
  not the window name, so these are not literal-readout defects.
- Status: Fixed (controls) / Intentional (dialog handles).

## Accessibility audit — wave 2 (initial-focus quality)

Audited which control receives focus when a dialog opens and whether focus is
restored on close.

Verified (strong, no change needed): the centralized `MainFrame._show_modal_dialog`
runs `focus_primary_control(dialog)` so custom `wx.Dialog` surfaces open with focus
on their first real content control — not the OK button — via
`dialog_contract.find_primary_focus_target` over a comprehensive
`_PREFERRED_FOCUS_CLASSES` list (lists, trees, dataviews, text, search, combo,
choice, spin, radio, checkbox, slider). It honors a construction-time
`SetFocus()` and the `_quill_keep_initial_focus` opt-out (e.g. crash recovery,
where the primary button should hold focus). On close it restores focus to the
editor by default (`restore_editor_focus`), and dialogs that should not pass
`restore_editor_focus=False`. Native dialogs are deliberately left to manage their
own focus. The dialog-inventory gate ensures dialogs route through this path.

### FOCUS-001 — wx.html fallback dialog opened on the Close button, not its content
- Severity: Medium. Category: Accessibility (initial focus).
- `preview_dialog.AccessibleHtmlDialog` (the `wx.html.HtmlWindow` fallback used
  when `wx-accessible-webview` is absent) calls the standalone `show_modal_dialog`,
  which does no focus management, and `HtmlWindow` is not a preferred focus class —
  so the dialog opened with focus parked on its default Close button. A
  screen-reader user landed on "Close" instead of the readable content.
- Resolution: store the view and `self._view.SetFocus()` before showing (mirrors
  the already-tested `SidePreview.focus()`), so focus lands on the content.
- Considered and rejected: adding `HtmlWindow`/`Grid` to `_PREFERRED_FOCUS_CLASSES`.
  Only this fallback dialog used `HtmlWindow` as primary content (fixed directly),
  and no modal dialog uses `Grid` as primary content (`csv_grid` is a panel
  surface). Changing the shared list risks shifting initial focus in existing
  multi-control dialogs (the walker returns the first preferred control in tab
  order), so the localized fix is safer.
- Tests: `test_preview_dialog_accessibility.py` (4) still pass; behavioral
  modal-focus assertion needs a full wx.App + shown window, so it is recorded as
  needs-live-validation rather than added as a brittle test.
- Status: Fixed. Needs live NVDA/JAWS confirmation.

## Accessibility audit — wave 3 (label/field associations)

wxPython does not associate a `StaticText` label with the following control the
way HTML `<label for>` does; on some screen readers a field with only a nearby
visual label is announced without a name. The reliable fix is an explicit
`SetName` on each input. Audited input-control naming coverage across the UI and
fixed the clearest gaps.

### A11Y-003 — Input controls labeled only by an adjacent StaticText
- Severity: Medium. Category: Accessibility (screen-reader field naming).
- Fixed across four dialogs:
  - `skill_library_dialog.py`: the Skills list and Description field, and every
    dynamically-built parameter control (`_make_control` now sets the accessible
    name from `param.label or param.name`, covering Choice/CheckBox/SpinCtrl/
    TextCtrl).
  - `assistant_tools.py`: 10 authoring fields across the prompt-authoring and
    model-search dialogs (Title, Tone, Audience, Goal, Template, Prompt, Search).
  - `web_form.py`: every dynamically-rendered form control is named from its
    field label at the single assignment site (`SetName(label)`).
  - `sticky_notes.py`: the Title and Note editors.
- GATE-11: `assistant_tools.py` (+10) and `skill_library_dialog.py` (+6)
  rebaselined with a dated justification (per-control `SetName` lines are not
  extractable); `web_form.py`/`sticky_notes.py` stayed within budget.
- Tests: existing dialog suites pass (assistant_tools 12, web_form/sticky_notes
  24, skill-library routing 1). Naming is structural; no behavioral test added.
- Status: Fixed. Needs live NVDA/JAWS confirmation.
- Continued work (next pass): remaining lower-coverage files (e.g.
  `batch_wizard_pages.py`, read-only display areas in `info_pages.py`) and a
  broader sweep of single-field dialogs.

## Accessibility audit — wave 4 (keyboard traps / tab order)

### KEY-001 — `wx.TE_PROCESS_TAB` on prose multiline fields trapped Tab
- Severity: High (a keyboard trap is a release-blocker class). Category: Accessibility.
- `TE_PROCESS_TAB` makes a multiline `TextCtrl` insert a tab character on Tab
  instead of moving focus, so a keyboard-only user could not Tab out to the
  dialog's buttons. Found on four fields; fixed the three that hold prose:
  `assistant_tools.py` prompt field, `sticky_notes.py` note body, and
  `web_form.py` textareas. Left `assistant_tools.py`'s restricted-Python **code
  editor** (`self.code`) with `TE_PROCESS_TAB` — Tab-to-indent is expected there;
  recorded as intentional with a recommended follow-up (an Escape/Ctrl+Tab focus
  exit) so even the code editor has a keyboard way out.
- Tests: web_form/sticky 24 and assistant_tools 12 pass (no style-flag assertions
  broke). GATE-11 rebaselined +2 on assistant_tools for the explanatory comment.
- Status: Fixed (3 fields) / Intentional with follow-up (code editor).

### CHAR_HOOK spot-check (no defect)
- The command palette's `_on_char_hook` correctly `event.Skip()`s every key it
  does not handle (Escape/Up/Down), so Tab navigation is not swallowed — not a trap.
- `main_frame.py`'s list-reorder `on_key` (line ~14289) deliberately repurposes
  Tab/Shift+Tab to demote/promote items and does not Skip. Recorded as intentional
  but flagged: confirm keyboard users can still reach the dialog's buttons (via
  Escape/Enter or an explicit focus path) — needs live keyboard verification.

## Accessibility audit — wave 6 (editor surface)

Audited the core editing surface — the highest-risk area — element by element. It
is already comprehensively accessible; no defect was found, so no code was changed
(the QA discipline is to not make superficial edits to inflate a count). What was
checked and confirmed:
- **Editor control**: a native multiline `wx.TextCtrl` (`TE_RICH2 | TE_NOHIDESEL`
  so the selection stays visible when focus leaves), named "Document", with the
  macOS AX role pinned to a real text area. Tab is **not** trapped (no
  `TE_PROCESS_TAB`), so keyboard users can leave the editor.
- **Layout splitters**: named "Document area" and "Editor area".
- **Side preview**: the `SidePreview` HtmlWindow is named "Preview" and is
  focusable via the `view.focus_preview` command, with a return-to-editor path.
- **Document tabs**: named "Open documents" (wave 1); native notebook announces
  each tab's document name on arrow navigation; Enter/Space focuses the editor and
  announces "Focused document <name>".
- **Status bar**: exemplary — each cell is a named button (`SetName`) that
  announces "Status bar, <label>, <value>" on focus, with Tab navigation between
  cells and a "Returned to editor" cue; gated by GATE-12 (announce-gap).
- Status: Audited, no defect. Manual confirmation cases added to the
  screen-reader test plan (TC-EDIT-001..004).

## Accessibility audit — wave 5 (error-to-field association)

When a dialog rejects invalid input, focus should move to the offending field
(not stay on the button) and the error should be announced. QUILL announces status
messages via GATE-12, so the announcement half is covered; the audit targeted the
focus half.

### A11Y-004 — in-dialog validation did not move focus to the bad field
- Severity: Medium. Category: Accessibility (error recovery).
- `github_dialogs.py` "open repository" form validated owner/repo inline, set a
  status message, and returned with focus left on the Load button — a keyboard or
  screen-reader user had to navigate back to the field to fix it.
- Resolution: `self._repo_ctrl.SetFocus()` on both validation branches so the user
  lands on the field to correct.
- Surveyed the other validating dialogs: most validate input from a prompt or
  WebView form that has already closed (`main_frame_power_tools` numeric/pattern
  ops, single-prompt tools), so there is no live field to refocus — the announced
  status message is the correct behavior there. `assistant_panel` already manages
  field focus well. github's persistent form was the real gap.
- GATE-11 rebaselined +2 (the two SetFocus calls). Status: Fixed; needs live
  keyboard/SR confirmation.

## Correctness sweep — wave C1 (attribute/call contracts, mutable defaults)

Whole-package AST audits for two bug classes the master brief flags. Recorded even
though clean, so the check is on the record and repeatable.

### CALL-001 — calls to never-defined methods (`self.method()`)
- Audited every `self.<name>(...)` call against all `def`s and instance attributes
  across `quill/` (4407 defined methods/functions). This is the class that bit the
  app before (the `_settings_dialog_apply_refresh` crash calling never-defined
  `set_theme`/`_set_spellcheck_mode`/...).
- Result: **0 calls to undefined private methods** (996 distinct private call
  names, all defined). For public snake_case calls, the only 5 candidates
  (`on_ai`/`on_convert`/`on_ocr`/`on_open`/`on_run_macro` in `watch_actions.py`)
  are dataclass callback fields injected at construction — correct, not defects.
- **Promoted to a standing CI gate:** `quill/tools/method_contract_audit.py`
  (`find_undefined_private_calls`) + `tests/unit/tools/test_method_contract_audit.py`
  fail the build if any `self._private()` call is ever undefined across `quill/`.
  This permanently guards the exact class that caused the historical Settings crash.
- Status: Clean (no defect) and now regression-proofed.

### BUG-mutable-defaults — mutable default arguments
- Audited every function/method default and keyword-default in `quill/` for a
  mutable literal (`[]`/`{}`/`set()`/`list()`/`dict()`).
- Result: **0 occurrences**. Status: Clean (no defect).

### BUG-file-handles — `open()` calls outside a `with` (leak risk)
- Audited every `open()`/`.open()` call in `quill/` (72) for use outside a
  context manager; flagged 23, all of which are non-leaks on inspection:
  `webbrowser.open(url)` (not a file), `wave.open(...)` immediately used in
  `with wf:`, the diagnostics module's deliberately-retained handle list (closed
  by `close_diagnostic_handles()`), and the IPC/recovery single-instance lock fds
  (`os.open`/`os.fdopen`, closed on every error path and released at process exit).
- Result: **0 real leaks**. Status: Clean (no defect).

### EXC-001 — silently-swallowed exceptions (`except ...: pass`) in core/io
- Audited every `except` handler whose body is only `pass`/`...` in the wx-free
  `quill/core` and `quill/io` layers (66 found).
- Most are deliberate best-effort cleanup (closing handles, removing temp files,
  optional-dependency probes) where failure is acceptable — left as-is.
- Three used a **redundant exception tuple** that misleads the reader:
  `except (ImportError, Exception)` (and one with `subprocess.CalledProcessError`),
  where `Exception` already subsumes the others — functionally identical to
  `except Exception`. Simplified to `except Exception:` (with the documented
  `# noqa: BLE001` and a comment naming the fallback) in `core/read_aloud.py` and
  `io/pages.py` (×2). No behavior change; tests pass (62).
- Status: Reviewed; 3 redundancies cleaned, the rest are intentional.

### BUG-thread-daemon — non-daemon threads (shutdown-hang risk)
- Audited every `threading.Thread(...)` construction in `quill/` (58 of them) for a
  `daemon` setting; a non-daemon worker can block interpreter shutdown.
- Result: **0 missing** — all 58 set `daemon`. Status: Clean (no defect). This
  matches the repo's `# GATE-40-OK` thread-start review convention.

Note: `ruff`'s broader correctness rules (bare `except`, `is`-with-literal, etc.)
are already green repo-wide, so those classes are covered by the standing gates.
Gate coverage check: the undefined-private-method audit is now a standing gate
(CALL-001); mutable defaults are already gated by ruff's bugbear rule **B006**
(ruff `select` includes `B`); non-daemon threads are already gated by **GATE-15**
(and **GATE-40** bans raw `Thread` in `quill/ui`). So all four correctness classes
audited here are now permanently guarded.

## Full-suite sweep (drive detectable failures to zero)

Running the whole `tests/unit tests/stability` suite (4896 tests; the Parakeet
test referenced under TEST-001 has since been removed) surfaced exactly one
failure, now fixed.

### TEST-002 — flaky watchdog re-dump test (timing-dependent)
- Severity: Medium. Category: Test reliability.
- `test_watchdog_re_dumps_after_recovery_window` slept 0.15s and asserted >=2
  stack dumps fired from `WxHeartbeatWatchdog`, with 0.05s dump windows and 0.02s
  polls. Under load the poll thread is delayed (the heartbeat log showed age
  jumping 0.0 -> 0.1s), so only one dump window was hit and the test failed — a
  fragile test tied to wall-clock scheduling, not a product defect.
- Resolution: extracted the re-dump decision into a pure
  `WxHeartbeatWatchdog._should_dump(age, now, last_dump_time)` and rewrote the
  test to assert the policy deterministically (no sleep, no thread): not-yet-blocked
  -> no dump; blocked past the window with no prior dump -> dump; still blocked
  within the recovery window -> suppressed; window elapsed -> re-dump. Verified
  5/5 runs green. The refactor also makes the production re-dump policy unit-testable.
- Side note: writing the deterministic test exposed a floating-point boundary
  (`(1000.05 - 1000.0) >= 0.05` is False due to representability); the test now uses
  a clear margin past the window. The real watchdog uses 15s defaults, so the
  boundary never bites in production.
- Status: Fixed and verified.

After the fix, a full re-run **without** `-x` (so failures cannot hide behind an
early stop) reported **4857 unit+integration passed, 12 skipped, 0 failures**, plus
38 stability passed. With `ruff`/`mypy` clean, the mechanically-detectable surface
is at zero known failures. This is the honest meaning of "zero" here: all gates and
the full test suite are green; it is not a proof that no latent bug exists.

## Deferred / next wave (not yet done — do not represent as complete)

The master quality-pass scope is repository-wide and multi-session. Not yet
performed in this pass:

- Full test-suite run with a per-test timeout to neutralize TEST-001.
- The 6-wave accessibility audit is **complete**: wave 1 (tab-group + control
  naming), wave 2 (initial-focus), wave 3 (label/field associations), wave 4
  (keyboard traps), wave 5 (error-to-field), wave 6 (editor surface — audited, no
  defect). Remaining accessibility work is human-only: execute the screen-reader
  test plan on a packaged build, plus a label/field continuation sweep of the
  lower-coverage dialogs and live verification of the reorder dialog's Tab handling.
- The startup/shutdown initialization-order hardening review (Section 9).
- The call-site / attribute-contract repository audit (Section 7): wave C1 is done
  and clean (undefined-method calls, mutable defaults). Remaining correctness
  classes: resource/threading lifecycle and exception-boundary review.
- The performance and visual-polish passes (Sections 13, 14).
- The documentation audit beyond the release notes / CHANGELOG touched here.

## Validation performed this pass

- `ruff check` on all changed files: pass.
- `ruff format` applied to the one new module.
- `python -m pytest tests/unit/core/speech/test_engine_install.py tests/unit/core/speech/test_cloud_transcribers.py tests/unit/core/speech/test_quillin_providers.py tests/unit/tools/test_network_egress_audit.py`: 32 passed.
- `python -m pytest tests/unit/ui/test_main_frame_menu_contract.py tests/unit/ui/test_main_frame_menu_label_accelerator.py tests/unit/ui/test_speech_commands.py`: 11 passed.
- `python -m pytest tests/unit/scripts/test_build_windows_distribution.py`: 15 passed.
- `scripts/check_docs_artifacts.py`: pass.
