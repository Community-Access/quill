# Startup Performance Optimization Implementation Plan

> **For agentic workers:** Execute inline per superpowers:executing-plans discipline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce QUILL's cold-start time and make the remaining startup window visible to screen-reader users, without changing any user-facing feature behavior.

**Architecture:** Cold start splits into two phases: (1) `python -m quill` process start through `MainFrame.__init__`/`frame.Show()` — currently ~1.5s, driven almost entirely by eager module imports in `quill/ui/main_frame.py`'s ~500-line import block, and (2) the already-well-built deferred phase (`_run_deferred_startup_tasks`, timed to `logs/startup_tasks.txt`). This plan (a) instruments phase 1 so it's measurable, (b) removes synchronous Quillin-manifest disk/JSON work from `MainFrame.__init__`, and (c) converts a vetted subset of phase-1 module-level imports (confirmed single-feature, non-hot-path usage via grep) to local imports inside the methods that use them.

**Tech Stack:** Python 3.13, wxPython, pytest, mypy, ruff.

## Global Constraints

- No `wx` imports in `quill/core` or `quill/io` (CLAUDE.md layering rule).
- All new command handlers go in a mixin, not directly in `main_frame.py` — N/A here (no new commands), but do not move existing methods out of their mixins.
- `mypy` is scoped to `quill/core` and `quill/io` only — never run unscoped.
- Module size budget (`quill/tools/module_size_budgets.json`, GATE-11) is a ratchet — if any touched file's line count decreases, that's fine (budget stays as a ceiling); do not increase any tracked module's lines without a budget bump + `_rebaseline_<date>` comment.
- Never call `ShowModal()` directly outside `_show_modal_dialog` — N/A here (no dialog code changes, only import location).
- Update release notes, user guide, and CHANGELOG incrementally per bucket, not batched at the end.

---

### Task 1: Instrument the pre-Show startup phase

**Files:**
- Modify: `quill/__main__.py` (`main()`, around line 410-470)
- Modify: `quill/ui/main_frame.py` (`run_app`, and `_write_startup_timing` at line 1582)

**Interfaces:**
- Produces: `logs/startup_tasks.txt` gets a new leading section "Cold start (pre-window)" with entries for: interpreter-to-main() dispatch, `import quill.ui.main_frame`, `MainFrame.__init__`, `frame.Show()`. Reuses the existing `_write_startup_timing(times: list[tuple[str, float]])` signature — pass the cold-start timings through the same function so there is one file, one format.

- [ ] Read `quill/__main__.py` `main()` and `run_app()` in `main_frame.py` in full to find the exact call sequence and existing timing hooks.
- [ ] Wrap the `from quill.ui.main_frame import run_app` import and the `run_app(...)` call (which builds `wx.App`/`MainFrame`/`Show`) with `time.perf_counter()` measurements. Do not restructure control flow — only add timing capture around existing calls.
- [ ] Thread the collected `(label, seconds)` tuples into `MainFrame._write_startup_timing` so cold-start timings land in the same `logs/startup_tasks.txt`, before the existing deferred-task entries (cold start happened first).
- [ ] Manually run `python -m quill` once, confirm `logs/startup_tasks.txt` (under the dev data dir) now shows a "Cold start" section with plausible millisecond values, then close the app.
- [ ] Run `pytest -m smoke -q` — must stay green (27 passed, 2 skipped baseline).
- [ ] Commit: `git add quill/__main__.py quill/ui/main_frame.py && git commit -m "perf: instrument pre-window cold-start timing"`.

### Task 2: Defer bundled-Quillin manifest discovery off `MainFrame.__init__`

**Files:**
- Modify: `quill/ui/main_frame_quillins.py` (`_register_quillin_contributions` / `discover_bundled_extensions` call site)
- Modify: `quill/ui/main_frame.py` (wherever `_register_quillin_contributions` is invoked from `__init__`)

**Interfaces:**
- Consumes: existing `discover_bundled_extensions()` / `load_enabled_bundled_manifests()` from the Quillins model — signatures unchanged.
- Produces: manifest discovery still populates the same registry/menu structures the Quillins menu and command dispatch already read; only the *timing* changes (moved from synchronous `__init__` to the existing `_run_deferred_startup_tasks` list, or a `wx.CallAfter` scheduled at the end of `__init__`).

- [ ] Find the exact call site of `_register_quillin_contributions()` in `MainFrame.__init__` and confirm nothing later in `__init__` (menu building, command palette population) depends synchronously on Quillin commands being registered before the window shows. If something does depend on it (e.g., menu items must exist for `Show()` to render correctly), defer only the manifest *discovery/parsing* (disk+JSON) but keep command registration synchronous using already-discovered data — check the actual code before deciding which split point is correct.
- [ ] Move the discovery call into `_run_deferred_startup_tasks` (add it to the existing `for label, task in (...)` tuple list, each isolated in its own try/except per the file's existing pattern) if the check above shows it's safe; otherwise wrap just the manifest-parsing loop in a background `TaskManager.submit` call with `wx.CallAfter` to apply results, following the same pattern as `help topics warm-up` in that same list.
- [ ] Confirm the Quillins menu still populates correctly by writing a small unit test (or checking for an existing one) that calls the discovery/registration path and asserts registered commands appear — check `tests/` for existing Quillins menu tests first (e.g. `tests/unit/ui/` or `tests/unit/core/test_*quillin*`) and extend rather than duplicate.
- [ ] Run the Quillins-related test file(s) found above; must pass.
- [ ] Run `pytest -m smoke -q`; must stay green.
- [ ] Commit: `git add quill/ui/main_frame.py quill/ui/main_frame_quillins.py && git commit -m "perf: defer bundled Quillin manifest discovery off the startup critical path"`.

### Task 3: Lazy-import `quill.core.updates` (update-check feature)

**Files:**
- Modify: `quill/ui/main_frame.py` — remove the module-level `from quill.core.updates import (...)` block (currently lines 398-409); add local imports inside the methods that use these names, all located in the contiguous block ~lines 19900-20600 (`_update_check_due`/`check_for_updates` and helpers: `_route_prerelease_to_beta`, `_show_update_available_dialog`, `_confirm_beta_channel`, `_download_update_release`, `_offer_post_download_actions`, `_open_update_download_flow`, and the method containing line 19901-19926).

**Interfaces:** No public signatures change. `GitHubRelease`/`UpdateManifest` are used only in type annotations (safe under `from __future__ import annotations`, already present at top of file — annotations are strings at runtime, not evaluated) and as runtime values inside method bodies (`is_newer_version(...)`, `fetch_releases()`, etc.) — those call sites need a real local import.

- [ ] Grep-confirm (already done in investigation) that all 34 occurrences of `GitHubRelease, UpdateManifest, download_release_asset, fetch_latest_release, fetch_releases, fetch_update_manifest, find_release, is_newer_version, running_portable, select_latest` outside the import block fall within lines 19900-20600. Re-check against current file state before editing (line numbers may have shifted from Task 1/2 edits).
- [ ] Delete the module-level import block for `quill.core.updates`.
- [ ] Add `from quill.core.updates import (...)` (only the names each function actually uses) as a local import at the top of each of the ~7 methods identified above.
- [ ] Run `ruff check quill/ui/main_frame.py` — fix any new unused-import or import-order complaints.
- [ ] Run `pytest -m smoke -q` and any existing update-check unit tests (search `tests/` for `test_updates` or `test_check_for_updates`); must pass.
- [ ] Commit: `git add quill/ui/main_frame.py && git commit -m "perf: lazy-import quill.core.updates in the update-check feature block"`.

### Task 4: Lazy-import `quill.core.glow_updates` (GLOW update-check feature)

**Files:**
- Modify: `quill/ui/main_frame.py` — remove module-level `from quill.core.glow_updates import (GlowUpdateCheck, apply_glow_update, check_for_glow_update)` (currently lines 174-178); add as a local import inside `check_for_glow_updates` (line ~20119-20191), the only method using these names (confirmed via grep — also referenced once as a bound method `self.check_for_glow_updates` at line 2693, which is just a menu command binding and doesn't need the import).

**Interfaces:** No public signatures change.

- [ ] Re-grep to confirm line numbers/usage after Tasks 1-3 edits.
- [ ] Delete the module-level import; add the same three names as a local import at the top of `check_for_glow_updates`.
- [ ] Run `ruff check quill/ui/main_frame.py`.
- [ ] Run `pytest -m smoke -q` and any `test_glow_update*` tests found in `tests/`.
- [ ] Commit: `git add quill/ui/main_frame.py && git commit -m "perf: lazy-import quill.core.glow_updates in the GLOW update-check handler"`.

### Task 5: Lazy-import single-use-site UI dialogs (`session_browser`, `train_style_dialog`)

**Files:**
- Modify: `quill/ui/main_frame.py` — remove module-level `from quill.ui.session_browser import SessionBrowserDialog` (line ~535) and `from quill.ui.train_style_dialog import TrainStyleDialog` (line ~545); add each as a local import immediately before its single instantiation site (`SessionBrowserDialog(` at line ~23495, `TrainStyleDialog(` at line ~22263).

**Interfaces:** No public signatures change — these are dialog classes instantiated exactly once each in the whole file.

- [ ] Re-grep to confirm each class still has exactly one instantiation site after prior tasks' edits.
- [ ] Move each import to be local, immediately above its instantiation call.
- [ ] Run `ruff check quill/ui/main_frame.py`.
- [ ] Run `pytest -m smoke -q`.
- [ ] Commit: `git add quill/ui/main_frame.py && git commit -m "perf: lazy-import single-use dialogs (SessionBrowserDialog, TrainStyleDialog)"`.

### Task 6: Lazy-import the Publishing / Share-Package / Export-Import feature block

**Files:**
- Modify: `quill/ui/main_frame.py` — remove module-level imports for `quill.core.publishing` (lines ~269-276, note: some names already re-imported locally at lines ~13070/13133/13188/13308/13412 — check whether the module-level import becomes fully redundant or still supplies names used elsewhere before deleting), `quill.core.publishing_linkage` (lines ~277-282, grep usage sites first — not yet verified in this investigation), `quill.core.share_package` (lines ~329-335), `quill.ui.publishing_tools` (lines ~529-533), `quill.ui.share_dialogs` (lines ~536-543). All confirmed usages of `share_package`/`publishing_tools`/`share_dialogs` names fall within lines ~13060-13970 (one contiguous publishing/export/import feature region).

**Interfaces:** No public signatures change.

- [ ] Grep `quill.core.publishing_linkage`'s imported names (not yet checked) to confirm they're confined to the same 13060-13970 region before touching that import — if usage is broader, leave that one module-level and only touch the other four.
- [ ] Re-grep all five modules' names to confirm line numbers/usage after prior tasks' edits, and confirm the module-level `quill.core.publishing` import isn't also supplying names used outside the 13060-13970 region (e.g., in a status-bar or menu-enablement check elsewhere in the file).
- [ ] For each of the (up to 5) modules confirmed safe: delete the module-level import, add local imports at the top of each method in the 13060-13970 block that uses its names (follow the existing style already used for the partial local `quill.core.publishing` imports at lines 13070/13133/13188/13308/13412 — consolidate rather than duplicating imports back-to-back in the same method).
- [ ] Run `ruff check quill/ui/main_frame.py`.
- [ ] Run `pytest -m smoke -q` and any `test_publishing*`/`test_share_package*`/`test_export*`/`test_import*` tests in `tests/`.
- [ ] Commit: `git add quill/ui/main_frame.py && git commit -m "perf: lazy-import publishing/share-package/export-import feature block"`.

### Task 7: Full verification pass

**Files:** none (verification only)

- [ ] Run `pytest -q` (full suite). Report pass/fail counts; investigate and fix any failure introduced by Tasks 1-6 before proceeding (do not skip or silence a newly-failing test).
- [ ] Run `mypy quill/core quill/io` (scoped, per CLAUDE.md — never run unscoped).
- [ ] Run `ruff check .` and `ruff format --check .`.
- [ ] Run `python -m quill.tools.module_size_budget` (or the equivalent check command — confirm exact invocation in `quill/tools/`) to confirm `main_frame.py`'s line count is within its existing budget (it should have *shrunk*, since imports moved to smaller local blocks — net file size should be roughly flat or slightly smaller).
- [ ] Run `python -m quill.tools.quillin_lint quill/quillins_bundled --strict` if Task 2 touched Quillin-adjacent code paths.
- [ ] Re-measure cold-start import cost: run `python -X importtime -c "import quill.ui.main_frame" 2> import_after.txt` and compare the `quill.ui.main_frame` cumulative time against the ~852ms baseline recorded in this investigation. Record the before/after numbers.
- [ ] Manually launch `python -m quill`, confirm the app opens, the Quillins menu is populated, Check for Updates / Check for GLOW Updates menu items still work (invoke each once), and `logs/startup_tasks.txt` shows the new "Cold start" section with a lower total than the pre-work baseline.

### Task 8: Documentation updates (per-bucket, not batched)

**Files:**
- Modify: `docs/release/release-notes.md` (or equivalent current file — check `docs/release/` for the exact canonical filename)
- Modify: `CHANGELOG.md`
- Modify: `docs/QUILL-PRD.md` if it tracks startup-performance as a named requirement (check first; skip if not applicable)

- [ ] Check `docs/release/` and repo root for the exact current release-notes/CHANGELOG filenames and format (a prior memory notes docs were relocated to `docs/`, `docs/release/` during a 2026-07-04 reorg — confirm current paths before writing).
- [ ] Add one entry describing the startup-time improvement in user-facing terms (no internal file/line references) with the measured before/after cold-start numbers from Task 7.
- [ ] Run whatever docs-artifact gate exists (check `quill/tools/` or CI config for a docs/pandoc gate mentioned in memory) if touching these files triggers it.
- [ ] Commit: `git add <docs files> && git commit -m "docs: note startup performance improvements"`.

---

## Final Report (for the user, next session)

After all tasks complete, produce a summary covering: measured before/after cold-start time, list of files changed per task, full test suite result, and explicit note that the branch (`worktree-startup-perf-optimization`) has NOT been pushed or opened as a PR — awaiting the user's go-ahead, consistent with "never push without being asked."
