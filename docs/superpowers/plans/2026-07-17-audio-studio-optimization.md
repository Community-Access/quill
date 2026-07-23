# Audio Studio Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slim the QUILL-AS vendored closure by guarded-import + deny-list, then port four Radio/Cast features (library tree, resume-on-launch + Recently Played, media keys + sleep timer, per-book volume/Mute/Play Queue) into Audio Studio, QUILL-first, re-vendored into the standalone.

**Architecture:** QUILL is source of truth. Trim makes hard references to droppable modules `try/except ImportError`-tolerant in `quill/` (embedded keeps them; standalone deny-lists them). Port-in lands backing modules in `quill/core/audio_studio/` and UI in `quill/ui/audio_studio/`, mirroring the `core/radio/`, `core/podcasts/`, `ui/radio/`, `ui/podcasts/` patterns, then `vendor_from_quill.py` re-syncs into `quillas/`. The standalone shell (`quillas/apps/studio.py`, hand-written) consumes the shared widgets.

**Tech Stack:** wxPython, Python 3.11+, pytest, atomic JSON storage (`core.storage.write_json_atomic`), `QuillTaskManager` for background work, `wx.CallAfter` for cross-thread UI.

## Global Constraints

- Embedded QUILL keeps every DROP module present and functional. Guards are no-ops when modules are present. `pytest -q` in `S:\QUILL` must stay green after every task.
- QUILL-AS uses its own pytest basetemp (`.quill-as-pytest-tmp`); do not remove the `_DEV_BUILD` conftest fixture.
- All JSON writes atomic via `core.storage.write_json_atomic`.
- Background work on `QuillTaskManager`; UI updates via `wx.CallAfter`.
- New network calls require egress-audit entry + consent (none expected in this plan).
- CRLF/LF: after editing QUILL files, check `git diff --stat` for whole-file churn; normalize with a bytes replace if the Edit tool flipped line endings.
- Do not push, publish, or delete branches unless Jeff asks. Create commits only when a task's step says to, on a branch (not main; main is branch-protected - land via PR).
- Reference spec: `docs/superpowers/specs/2026-07-17-audio-studio-optimization-design.md`.

---

# Phase 1 - Trim the vendored closure

**Phase goal:** `quillas` measurably smaller; `pytest -q` green in both `S:\QUILL` and `S:\QUILL-AS`; guarded imports in `quill/`; DENYLIST in `vendor_from_quill.py`.

Only import sites in **vendored** modules need guarding. Authoritative vendored guard-site list (confirmed by grep against `S:/QUILL-AS/quillas/`):

| DROP module        | Vendored importing sites                                              |
|--------------------|----------------------------------------------------------------------|
| quillins           | `core/speech/quillin_providers.py`                                   |
| braille_pack       | `core/optional_components.py`, `core/release_assets.py`, `ui/main_frame_speech_downloads.py` |
| pandoc_install     | `core/optional_components.py`, `core/external_tools.py`, `ui/main_frame_speech_downloads.py` |
| pdf_ocr_install    | `core/optional_components.py`, `ui/main_frame_speech_downloads.py`    |
| node_install       | `core/optional_components.py`, `ui/main_frame_speech_downloads.py`    |
| git_binaries       | `core/optional_components.py`, `core/release_assets.py`               |
| python_sandbox     | `core/watch_actions.py`                                               |
| spellcheck (hunspell) | `core/optional_components.py`                                     |
| glow               | `core/diagnostics.py`, `core/watch_actions.py` (action `glow_audit`, feature `future.glow`) |
| bw_speech          | `core/speech/service.py`                                               |
| math               | `core/speech/earcon.py`, `core/optional_components.py`, `core/release_assets.py`, `ui/main_frame_speech_downloads.py` |

Note: `core/ai/external_engine.py` (node_install) and `core/bw_providers.py` (bw_speech) are NOT vendored, so their import sites do not matter for the trim. `features.py`/`feature_catalog.py` reference spellcheck/glow as feature-definition *data* (not module imports); those entries stay harmless in the standalone - only the installer imports in `optional_components.py` get guarded.

### Task 1.1: Establish the absent-path test harness in QUILL

**Files:**
- Create: `tests/unit/core/test_optional_import_guards.py`

**Interfaces:**
- Produces: a reusable `assert_module_absent(monkeypatch, dotted)` helper later tasks call to simulate a DROP module being missing.

- [ ] **Step 1: Write the failing test**

```python
import importlib
import sys
import pytest


def _simulate_absent(monkeypatch, dotted: str):
    """Make ``import quill.<dotted>`` raise ImportError for this test session."""
    real_import = __builtins__.__import__ if isinstance(__builtins__, dict) else __import__
    # Block both the leaf module and its package reload.
    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        if name == dotted or name.startswith(dotted + "."):
            raise ImportError(f"simulated absence of {dotted}")
        return real_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr("builtins.__import__", blocked)
    for key in list(sys.modules):
        if key == dotted or key.startswith(dotted + "."):
            monkeypatch.delitem(sys.modules, key, raising=False)


@pytest.mark.parametrize("dotted", [
    "quill.core.quillins",
    "quill.core.braille_pack",
    "quill.core.pandoc_install",
    "quill.core.pdf_ocr_install",
    "quill.core.node_install",
    "quill.core.git_binaries",
    "quill.core.python_sandbox",
    "quill.core.spellcheck",
    "quill.core.glow",
    "quill.core.bw_speech",
    "quill.core.math",
])
def test_importing_optional_components_with_module_absent(monkeypatch, dotted):
    _simulate_absent(monkeypatch, dotted)
    # Fresh import so the guard path runs under our simulated absence.
    sys.modules.pop("quill.core.optional_components", None)
    import quill.core.optional_components as oc  # noqa: F401
    assert oc is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_optional_import_guards.py -x -q`
Expected: FAIL with `ImportError: simulated absence of ...` raised from `optional_components.py` import (modules are currently hard-imported).

- [ ] **Step 3: Commit (red baseline)**

```bash
git checkout -b feature/as-trim
git add tests/unit/core/test_optional_import_guards.py
git commit -m "test(as-trim): add absent-path guard harness (red)"
```

### Task 1.2: Guard the optional_components.py imports

**Files:**
- Modify: `quill/core/optional_components.py` (import block near lines 214-263, and usages at 604, 631, 695, 719, 746, 758, 764, 770, 994)
- Test: `tests/unit/core/test_optional_import_guards.py`

**Interfaces:**
- Produces: module-level `None`-or-module sentinels (`_braille_pack`, `_pandoc_install`, `_pdf_ocr_install`, `_node_install`, `_git_binaries`, `_math`, `_spellcheck`) used by the rest of this module; installer functions degrade to "not available" when the sentinel is `None`.

- [ ] **Step 1: Replace the hard import block with guarded imports**

Find the block that imports `braille_pack`, `pandoc_install`, `pdf_ocr_install`, `node_install`, `git_binaries`, `math` (and hunspell/spellcheck), and rewrite each as:

```python
try:
    from quill.core import braille_pack as _braille_pack
except ImportError:  # absent in standalone Audio Studio
    _braille_pack = None
```

Repeat for each: `_pandoc_install`, `_pdf_ocr_install`, `_node_install`, `_git_binaries`, `_math`, `_spellcheck`.

- [ ] **Step 2: Guard each usage site**

At every function that uses the imported names (e.g. `managed_braille_dir`, `is_braille_pack_installed`, `braille_pack_version`, `managed_pandoc_dir`, `managed_pandoc_executable`, `pdf_ocr_pack_dir`, `is_pdf_ocr_available`, `managed_node_dir`, `is_node_available`, `git_available`, `gh_available`, `vendor_dir`, `mathcat_engine`, `managed_hunspell_dir`, `spellcheck`), add an early-out when the sentinel is `None`:

```python
def is_braille_pack_installed() -> bool:
    if _braille_pack is None:
        return False
    return _braille_pack.is_braille_pack_installed()
```

For `gather_optional_components()` and the `OptionalComponent` list, skip components whose backing module is `None`:

```python
if _braille_pack is not None:
    yield OptionalComponent(component_id="braille_pack", ...)
```

- [ ] **Step 3: Run the absent-path test for the modules this file owns**

Run: `pytest tests/unit/core/test_optional_import_guards.py -x -q`
Expected: PASS for `braille_pack`, `pandoc_install`, `pdf_ocr_install`, `node_install`, `git_binaries`, `math`, `spellcheck`; still FAIL for `quillins`, `python_sandbox`, `glow`, `bw_speech` (handled in later tasks).

- [ ] **Step 4: Run the full QUILL suite to confirm no embedded regression**

Run: `pytest -q`
Expected: PASS (modules present, guards fall through).

- [ ] **Step 5: Commit**

```bash
git add quill/core/optional_components.py tests/unit/core/test_optional_import_guards.py
git commit -m "feat(as-trim): guard optional_components imports for standalone absence"
```

### Task 1.3: Guard release_assets.py, external_tools.py, speech/quillin_providers.py, speech/service.py, speech/earcon.py

**Files:**
- Modify: `quill/core/release_assets.py` (braille_pack, git_binaries, math imports)
- Modify: `quill/core/external_tools.py:271` (pandoc_install)
- Modify: `quill/core/speech/quillin_providers.py:24` (quillins)
- Modify: `quill/core/speech/service.py:112,191` (bw_speech)
- Modify: `quill/core/speech/earcon.py` (math)
- Test: `tests/unit/core/test_optional_import_guards.py`

**Interfaces:**
- Produces: guarded sentinels in each module; `quillin_providers` returns no Quillin-sourced providers when `quillins` is absent; `speech/service` degrades GPU detection when `bw_speech` is absent; `release_assets` omits braille/git/math asset entries when absent.

- [ ] **Step 1: Apply the guarded-import pattern to each site**

```python
# release_assets.py
try:
    from quill.core import braille_pack as _braille_pack
except ImportError:
    _braille_pack = None
try:
    from quill.core import git_binaries as _git_binaries
except ImportError:
    _git_binaries = None
try:
    from quill.core import math as _math
except ImportError:
    _math = None
```

```python
# external_tools.py
try:
    from quill.core.pandoc_install import managed_pandoc_executable
except ImportError:
    managed_pandoc_executable = None
```

```python
# speech/quillin_providers.py
try:
    from quill.core.quillins.model import TranscriptionProviderContribution
except ImportError:
    TranscriptionProviderContribution = None
```

```python
# speech/service.py
try:
    from quill.core.bw_speech import has_nvidia_gpu, total_ram_gb
except ImportError:
    has_nvidia_gpu = lambda: False  # noqa: E731
    total_ram_gb = lambda: 0.0
```

```python
# speech/earcon.py
try:
    from quill.core import math as _math
except ImportError:
    _math = None
```

- [ ] **Step 2: Guard each call site**

- `release_assets.py`: wrap braille/git/math asset entries with `if _braille_pack is not None:`, `if _git_binaries is not None:`, `if _math is not None:`.
- `external_tools.py`: `def pandoc_executable(): return managed_pandoc_executable() if managed_pandoc_executable else None`.
- `quillin_providers.py`: `def provider_contributions(): if TranscriptionProviderContribution is None: return []` then existing logic.
- `speech/service.py`: callers of `has_nvidia_gpu`/`total_ram_gb` already get safe fallbacks; verify no `NameError` paths.
- `speech/earcon.py`: guard the math-using earcon builder with `if _math is not None:`.

- [ ] **Step 3: Extend the absent-path test to cover these modules**

Add to the `@pytest.mark.parametrize` list is already present; run:

Run: `pytest tests/unit/core/test_optional_import_guards.py -x -q`
Expected: PASS for `quillins`, `bw_speech`, `math`, `pandoc_install` (release_assets path); still FAIL for `python_sandbox`, `glow` (next task).

- [ ] **Step 4: Run full QUILL suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/release_assets.py quill/core/external_tools.py quill/core/speech/quillin_providers.py quill/core/speech/service.py quill/core/speech/earcon.py tests/unit/core/test_optional_import_guards.py
git commit -m "feat(as-trim): guard release_assets/external_tools/speech imports"
```

### Task 1.4: Guard watch_actions.py and diagnostics.py (python_sandbox, glow)

**Files:**
- Modify: `quill/core/watch_actions.py:361` (python_sandbox), `:654` (glow action)
- Modify: `quill/core/diagnostics.py:17` (glow)
- Test: `tests/unit/core/test_optional_import_guards.py`

**Interfaces:**
- Produces: `watch_actions` skips the python-sandbox action and the `glow_audit` action when their modules are absent; `diagnostics` omits the GLOW engine version summary line when `glow` is absent.

- [ ] **Step 1: Guard watch_actions.py**

The python_sandbox import is already inside a function (line 361: `from .python_sandbox import run_python_sandbox`). Wrap:

```python
def _run_python_sandbox(*args, **kwargs):
    try:
        from .python_sandbox import run_python_sandbox
    except ImportError:
        return None
    return run_python_sandbox(*args, **kwargs)
```

For the `glow_audit` action (line 654, `required_feature_id="future.glow"`): guard the action registration so it is only added when `glow` imports. Add a module-level guard:

```python
try:
    from quill.core import glow as _glow
except ImportError:
    _glow = None
```

and gate the `glow_audit` action entry on `if _glow is not None:`.

- [ ] **Step 2: Guard diagnostics.py:17**

```python
try:
    from quill.core.glow import glow_engine_version_summary
except ImportError:
    def glow_engine_version_summary() -> str:
        return ""
```

Call sites that include the GLOW summary in a diagnostics bundle must tolerate the empty string.

- [ ] **Step 3: Run absent-path test**

Run: `pytest tests/unit/core/test_optional_import_guards.py -x -q`
Expected: PASS for all 11 modules (the optional_components import now succeeds with each absent because its dependencies are guarded).

- [ ] **Step 4: Run full QUILL suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/watch_actions.py quill/core/diagnostics.py tests/unit/core/test_optional_import_guards.py
git commit -m "feat(as-trim): guard watch_actions/diagnostics (python_sandbox, glow)"
```

### Task 1.5: Guard ui/main_frame_speech_downloads.py

**Files:**
- Modify: `quill/ui/main_frame_speech_downloads.py` (imports of braille_pack, pandoc_install, pdf_ocr_install, node_install, math)
- Test: `tests/unit/core/test_optional_import_guards.py` (add a UI-level absent-path import smoke)

**Interfaces:**
- Produces: the downloads mixin offers only components whose backing modules resolved; the existing `_optional_component_allowlist` frame attribute still filters further.

- [ ] **Step 1: Guard each import**

Apply the same `try/except ImportError -> None` pattern to `braille_pack`, `pandoc_install`, `pdf_ocr_install`, `node_install`, `math` imports in this file.

- [ ] **Step 2: Guard the component-listing path**

Where the mixin builds the optional-components list for the dialog, skip entries whose backing module is `None`. The existing `allowed = getattr(frame, "_optional_component_allowlist", None)` filter (line ~191 in quillas) stays; add an upstream skip: `items = [c for c in items if c.component_id in allowed] if allowed is not None else items`, and also `items = [c for c in items if _backing_present(c)]`.

- [ ] **Step 3: Add a UI import-smoke test**

Append to `tests/unit/core/test_optional_import_guards.py`:

```python
def test_speech_downloads_imports_with_all_drop_modules_absent(monkeypatch):
    for dotted in [
        "quill.core.braille_pack", "quill.core.pandoc_install",
        "quill.core.pdf_ocr_install", "quill.core.node_install",
        "quill.core.math", "quill.core.quillins", "quill.core.glow",
        "quill.core.bw_speech", "quill.core.python_sandbox",
        "quill.core.spellcheck", "quill.core.git_binaries",
    ]:
        _simulate_absent(monkeypatch, dotted)
    for mod in list(sys.modules):
        if mod.startswith("quill.ui.main_frame_speech_downloads") or mod.startswith("quill.core.optional_components"):
            sys.modules.pop(mod, None)
    import quill.ui.main_frame_speech_downloads as m  # noqa: F401
    assert m is not None
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/core/test_optional_import_guards.py -q && pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/main_frame_speech_downloads.py tests/unit/core/test_optional_import_guards.py
git commit -m "feat(as-trim): guard speech_downloads imports for standalone absence"
```

### Task 1.6: Add DENYLIST to vendor_from_quill.py and re-vendor

**Files:**
- Modify: `S:/QUILL-AS/scripts/vendor_from_quill.py` (add DENYLIST; extend `copy_module`/`wanted_modules`)
- Run: `python S:/QUILL-AS/scripts/vendor_from_quill.py` then `python S:/QUILL-AS/scripts/vendor_tests.py`

**Interfaces:**
- Produces: a smaller `quillas/` package missing the DROP modules.

- [ ] **Step 1: Add the DENYLIST set**

Near `BLOCKLIST` (line 74):

```python
# Modules the standalone Audio Studio does not need. Guarded imports in
# quill/ make these safely absent. Leaf names only (matches BLOCKLIST
# semantics).
DENYLIST = {
    "quillins", "braille_pack", "pandoc_install", "pdf_ocr_install",
    "node_install", "git_binaries", "python_sandbox", "spellcheck",
    "glow", "bw_speech", "math",
}
```

- [ ] **Step 2: Extend copy_module to treat DENYLIST as deliberately absent**

In `copy_module` (line 127), add DENYLIST alongside BLOCKLIST:

```python
def copy_module(dotted: str) -> bool:
    leaf = dotted.split(".")[-1]
    if leaf in BLOCKLIST or leaf in DENYLIST:
        return True  # deliberately absent; guarded imports handle it
    src = module_source(dotted)
    ...
```

- [ ] **Step 3: Stop the closure walker from chasing DENYLIST modules**

In `wanted_modules` consumers (the `main()` loop, line 188-208), when a wanted module's leaf is in DENYLIST, record it as unresolved-but-expected instead of trying to copy:

```python
if dotted.split(".")[-1] in DENYLIST:
    unresolved.add(dotted)
    continue
```

(Place this before the `module_present`/`module_source` checks so it short-circuits.)

- [ ] **Step 4: Record before counts**

Run: `python -c "import pathlib; p=pathlib.Path('S:/QUILL-AS/quillas'); n=sum(1 for _ in p.rglob('*.py')); l=sum(len(x.read_text(encoding='utf-8').splitlines()) for x in p.rglob('*.py')); print(n, l)"`
Expected: prints current file count and line count (baseline, ~290 files / ~73k lines).

- [ ] **Step 5: Re-vendor**

Run: `python S:/QUILL-AS/scripts/vendor_from_quill.py && python S:/QUILL-AS/scripts/vendor_tests.py`
Expected: closure completes; vendor script reports fewer files/lines than baseline.

- [ ] **Step 6: Commit (QUILL-AS repo)**

```bash
cd S:/QUILL-AS && git add scripts/vendor_from_quill.py quillas tests && git commit -m "feat(as-trim): deny-list unneeded modules; re-vendor slim closure"
```

### Task 1.7: Iterate QUILL-AS tests to green and measure

**Files:**
- Modify (as needed): guarded sites in `quill/` re-vendored into `quillas/`

- [ ] **Step 1: Run the QUILL-AS suite**

Run (in `S:/QUILL-AS`): `pytest -q`
Expected: possibly FAIL with `ImportError` for a missed guard. For each failure:

- Read the traceback's file (it will be a `quillas/...` path that maps 1:1 to a `quill/...` path).
- Add the missing guard in `quill/` (Tasks 1.2-1.5 pattern).
- Re-run `vendor_from_quill.py`.
- Re-run `pytest -q`.

- [ ] **Step 2: Repeat until green**

Iterate until `pytest -q` in `S:/QUILL-AS` is fully green. Each iteration is one guard + one re-vendor. Keep commits small.

- [ ] **Step 3: Measure the result**

Run: `python -c "import pathlib; p=pathlib.Path('S:/QUILL-AS/quillas'); n=sum(1 for _ in p.rglob('*.py')); l=sum(len(x.read_text(encoding='utf-8').splitlines()) for x in p.rglob('*.py')); print(n, l)"`
Expected: measurably fewer files/lines than the Task 1.6 baseline.

- [ ] **Step 4: Run full QUILL suite (embedded safety)**

Run (in `S:/QUILL`): `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit any additional guards**

```bash
# in S:/QUILL, per guard added:
git add quill/<path> && git commit -m "feat(as-trim): guard <module> import (found by QUILL-AS suite)"
# in S:/QUILL-AS, re-vendor result:
cd S:/QUILL-AS && git add quillas tests && git commit -m "chore(as-trim): re-vendor after guard for <module>"
```

### Task 1.8: Phase 1 gate

- [ ] **Step 1: Confirm both suites green**

Run: `pytest -q` in `S:/QUILL` and `cd S:/QUILL-AS && pytest -q`
Expected: both PASS.

- [ ] **Step 2: Record before/after in the spec's delta section**

Append to `docs/superpowers/specs/2026-07-17-audio-studio-optimization-design.md` a "Phase 1 results" line with the file/line before/after.

- [ ] **Step 3: Open the PR (do not merge)**

```bash
gh pr create --base main --head feature/as-trim --title "Audio Studio trim: guarded imports + QUILL-AS deny-list" --body "..."
```

---

# Phase 2 - Port-in Radio/Cast features

**Phase goal:** four features in `quill/` (embedded-verifiable), re-vendored into `quillas/`, green in both suites.

New shared package `quill/core/audio_studio/` (does not exist yet). Each feature: TDD the backing module, then wire UI, then re-vendor. Re-use `vendor_from_quill.py` SEED additions (Task 2.0).

### Task 2.0: Add new package to vendor SEED

**Files:**
- Modify: `S:/QUILL-AS/scripts/vendor_from_quill.py` SEED_PACKAGES / SEED_MODULES

- [ ] **Step 1: Add core/audio_studio and the new UI modules to SEED**

In `SEED_PACKAGES` add `"core/audio_studio"`. In `SEED_MODULES` add `"ui.audio_studio.library_tree"`, `"ui.audio_studio.sleep_timer_dialog"` (if created), `"ui.audio_studio.play_queue_dialog"` (if created). These map 1:1 to `quillas/` after re-vendor.

- [ ] **Step 2: Commit (QUILL-AS)**

```bash
cd S:/QUILL-AS && git add scripts/vendor_from_quill.py && git commit -m "build(as-port): seed core/audio_studio + new audio_studio UI modules"
```

### Task 2.1: Library tree backing - core/audio_studio/library.py

**Files:**
- Create: `quill/core/audio_studio/__init__.py`
- Create: `quill/core/audio_studio/library.py`
- Test: `tests/unit/core/audio_studio/test_library.py`

**Interfaces:**
- Consumes: `quill.core.storage.write_json_atomic`, `quill.core.recent.recent_audiobook_files` (for the Inbox view).
- Produces:
  - `BookEntry` dataclass: `path: str, title: str, folder: str = "", favorite: bool = False, last_played_at: float = 0.0, added_at: float = 0.0`
  - `LibraryState` dataclass: `books: list[BookEntry]`, `folders: list[str]` (path-nested, `/`-separated like radio favorites)
  - `PINNED_VIEWS = ("Favorites", "In Progress", "Recently Played", "Inbox")`
  - `load_library(data_dir: Path) -> LibraryState`
  - `save_library(data_dir: Path, state: LibraryState) -> None` (atomic)
  - `record_play(state: LibraryState, path: str, *, now: float) -> None` (sets `last_played_at`, moves nothing)
  - `toggle_favorite(state: LibraryState, path: str) -> bool`
  - `move_to_folder(state: LibraryState, path: str, folder: str) -> None`
  - `view_query(state: LibraryState, view: str) -> list[BookEntry]` (Favorites -> favorite; In Progress -> has last_played_at but not finished; Recently Played -> sort by last_played_at desc; Inbox -> recent_audiobook_files not yet in state)
  - Persistence file: `data_dir / "audio_studio_library.json"`

- [ ] **Step 1: Write failing tests**

```python
import time
from pathlib import Path
from quill.core.audio_studio.library import (
    BookEntry, LibraryState, load_library, save_library,
    record_play, toggle_favorite, move_to_folder, view_query, PINNED_VIEWS,
)

def _state(books):
    return LibraryState(books=list(books), folders=[])

def test_toggle_favorite_round_trips(tmp_path):
    s = _state([BookEntry(path="b", title="B")])
    assert toggle_favorite(s, "b") is True
    assert s.books[0].favorite is True
    save_library(tmp_path, s)
    assert load_library(tmp_path).books[0].favorite is True

def test_view_query_favorites(tmp_path):
    s = _state([BookEntry(path="a", title="A"), BookEntry(path="b", title="B", favorite=True)])
    assert [e.path for e in view_query(s, "Favorites")] == ["b"]

def test_view_query_recently_played_orders_by_last_played():
    s = _state([BookEntry(path="a", title="A", last_played_at=10),
                BookEntry(path="b", title="B", last_played_at=30)])
    assert [e.path for e in view_query(s, "Recently Played")] == ["b", "a"]

def test_move_to_folder_sets_folder():
    s = _state([BookEntry(path="a", title="A")])
    move_to_folder(s, "a", "Fiction/SF")
    assert s.books[0].folder == "Fiction/SF"
    assert "Fiction/SF" in s.folders

def test_pinned_views_constant():
    assert PINNED_VIEWS == ("Favorites", "In Progress", "Recently Played", "Inbox")

def test_save_is_atomic(tmp_path):
    s = _state([BookEntry(path="a", title="A")])
    save_library(tmp_path, s)
    # write_json_atomic uses a temp + os.replace; the final file is the only one present
    files = [p.name for p in tmp_path.iterdir()]
    assert "audio_studio_library.json" in files
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/unit/core/audio_studio/test_library.py -x -q`
Expected: FAIL with `ModuleNotFoundError: quill.core.audio_studio.library`.

- [ ] **Step 3: Implement library.py**

Create `quill/core/audio_studio/__init__.py` (empty) and `quill/core/audio_studio/library.py` with the dataclasses and functions above. Use `write_json_atomic` for `save_library`. Model the dataclasses on `quill/core/podcasts/history.py`'s `PlayedEpisode` (to_dict/from_dict) and folder handling on `quill/core/radio/favorites.py` (string-path folders).

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from quill.core.storage import write_json_atomic
from quill.core.recent import recent_audiobook_files

PINNED_VIEWS = ("Favorites", "In Progress", "Recently Played", "Inbox")
_FILE_NAME = "audio_studio_library.json"

@dataclass
class BookEntry:
    path: str
    title: str
    folder: str = ""
    favorite: bool = False
    last_played_at: float = 0.0
    added_at: float = 0.0

@dataclass
class LibraryState:
    books: list[BookEntry] = field(default_factory=list)
    folders: list[str] = field(default_factory=list)

def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME

def load_library(data_dir: Path) -> LibraryState:
    p = _store_path(data_dir)
    if not p.exists():
        return LibraryState()
    data = json.loads(p.read_text(encoding="utf-8"))
    return LibraryState(
        books=[BookEntry(**b) for b in data.get("books", [])],
        folders=list(data.get("folders", [])),
    )

def save_library(data_dir: Path, state: LibraryState) -> None:
    write_json_atomic(_store_path(data_dir), {
        "books": [b.__dict__ for b in state.books],
        "folders": list(state.folders),
    })

def record_play(state: LibraryState, path: str, *, now: float) -> None:
    for b in state.books:
        if b.path == path:
            b.last_played_at = now
            return

def toggle_favorite(state: LibraryState, path: str) -> bool:
    for b in state.books:
        if b.path == path:
            b.favorite = not b.favorite
            return b.favorite
    return False

def move_to_folder(state: LibraryState, path: str, folder: str) -> None:
    for b in state.books:
        if b.path == path:
            b.folder = folder
    if folder and folder not in state.folders:
        state.folders.append(folder)

def view_query(state: LibraryState, view: str) -> list[BookEntry]:
    if view == "Favorites":
        return [b for b in state.books if b.favorite]
    if view == "Recently Played":
        return sorted([b for b in state.books if b.last_played_at],
                       key=lambda b: b.last_played_at, reverse=True)
    if view == "In Progress":
        return [b for b in state.books if 0 < b.last_played_at]  # refine with "not finished" in wiring
    if view == "Inbox":
        known = {b.path for b in state.books}
        return [BookEntry(path=str(p), title=p.stem) for p in recent_audiobook_files() if str(p) not in known]
    return []
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/core/audio_studio/test_library.py -x -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/audio_studio tests/unit/core/audio_studio && git commit -m "feat(as-port): add audio_studio library backing store"
```

### Task 2.2: Library tree widget - ui/audio_studio/library_tree.py

**Files:**
- Create: `quill/ui/audio_studio/library_tree.py`
- Test: `tests/unit/ui/audio_studio/test_library_tree.py` (headless build smoke; no wx display needed if guarded)

**Interfaces:**
- Consumes: `quill.core.audio_studio.library` (`LibraryState`, `view_query`, `PINNED_VIEWS`), `quill.ui.podcasts.show_actions` folder-prompt pattern.
- Produces:
  - `build_library_tree(tree: wx.TreeCtrl, state: LibraryState, *, keep_key: tuple[str, str] | None = None) -> None` (mirrors `quill/apps/podcasts.py:_reload_library_tree` at line 131: root "Library", pinned views, folders, books; each item tagged `(kind, key)` via `tree.SetItemData`).
  - `LibraryTreeActions` namespace with `open_book`, `reveal_in_workbench`, `toggle_favorite`, `delete_book`, `new_folder`, `move_to_folder` mirroring `show_actions.py` signatures: `(parent, store: LibraryState, entry: BookEntry, *, announce: Callable[[str], None]) -> bool`.

- [ ] **Step 1: Write a headless build smoke test**

```python
import wx
import pytest
from quill.core.audio_studio.library import LibraryState, BookEntry
from quill.ui.audio_studio.library_tree import build_library_tree

@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    a.Destroy()

def test_build_library_tree_smoke(app):
    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame)
    state = LibraryState(books=[BookEntry(path="a", title="A", favorite=True),
                                BookEntry(path="b", title="B", folder="Fiction")],
                        folders=["Fiction"])
    build_library_tree(tree, state)
    assert tree.GetCount() > 0
    frame.Destroy()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/unit/ui/audio_studio/test_library_tree.py -x -q`
Expected: FAIL `ModuleNotFoundError: quill.ui.audio_studio.library_tree`.

- [ ] **Step 3: Implement build_library_tree and actions**

Model `build_library_tree` on `quill/apps/podcasts.py:131-179` (`_reload_library_tree`): root "Library" item; one child per pinned view in `PINNED_VIEWS` with `SetItemData(("view", view))`; one child per folder (recurse nested `/` paths) with `SetItemData(("folder", folder))`; books sorted by title under their folder (or at root when `folder == ""`) with `SetItemData(("book", path))`. Keep `keep_key` selection across rebuilds.

Model `LibraryTreeActions` on `quill/ui/podcasts/show_actions.py` (`toggle_favorite`, `move_show_to_folder`, `create_folder_prompt`, `delete_folder_prompt`). Delete uses `quill.core.recent.remove_recent_audiobook_file` (the existing QUILL-AS delta) plus `save_library`.

- [ ] **Step 4: Run test**

Run: `pytest tests/unit/ui/audio_studio/test_library_tree.py -x -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/audio_studio/library_tree.py tests/unit/ui/audio_studio && git commit -m "feat(as-port): add audio_studio library tree widget + actions"
```

### Task 2.3: Wire the library tree into the standalone shell

**Files:**
- Modify: `S:/QUILL-AS/quillas/apps/studio.py:213-252` (replace `wx.ListBox` "Your books" with `wx.TreeCtrl` via `build_library_tree`)
- Modify (for embedded parity of the *backing* only; embedded has no list to replace): `quill/core/audio_studio/library.py` already shared.

Note: The standalone shell is hand-written in QUILL-AS, so this wiring is a QUILL-AS local delta (record in the spec delta list). The shared widget + backing live in `quill/` and are vendored.

- [ ] **Step 1: Replace the ListBox with a TreeCtrl**

In `studio.py:_build_main_panel` (line 180), replace lines 213-223 (`library_label`, `self._library_list = wx.ListBox`, accessible name, double-click/key bindings) with:

```python
library_label = wx.StaticText(panel, label="&Your books:")
self._library_tree = wx.TreeCtrl(panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT if False else wx.TR_DEFAULT_STYLE)
self._library_tree.SetName("Your books")
self._library_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_tree_activate)
self._library_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_tree_context_menu)
self._library_tree.Bind(wx.EVT_KEY_DOWN, self._on_tree_key)
```

- [ ] **Step 2: Add load/reload + selection helpers**

Add `self._library_state = load_library(app_data_dir())` in `__init__` near line 152. Add `_reload_library_tree() -> None` calling `build_library_tree(self._library_tree, self._library_state)` and preserving selection. Add `_selected_book_path() -> str | None` reading `GetItemData` for the selected item, returning the path when kind == "book".

- [ ] **Step 3: Wire handlers**

`_on_tree_activate` -> `_open_selected_book()` (existing). `_on_tree_context_menu` -> build a fresh-id popup (keep ids alive via `_keep_menu_ids`, mirroring `quill/apps/podcasts.py:266-270`) with Open / Reveal in Workbench / Toggle Favorite / Move to Folder / Delete / New Folder. `_on_tree_key` -> Enter opens, Delete removes (via `LibraryTreeActions.delete_book`).

- [ ] **Step 4: Persist on changes**

After any mutating action, call `save_library(app_data_dir(), self._library_state)` and `_reload_library_tree()`.

- [ ] **Step 5: Run QUILL-AS smoke (import + a quick launch test)**

Run: `python -c "import quillas.apps.studio"` in `S:/QUILL-AS` (with PYTHONPATH set per `run-quill-audio-studio.bat`).
Then launch via `run-quill-audio-studio.bat` (per Jeff's launch-the-app rule) and confirm the tree shows.
Expected: app launches, "Your books" is a tree.

- [ ] **Step 6: Commit (QUILL-AS)**

```bash
cd S:/QUILL-AS && git add quillas/apps/studio.py && git commit -m "feat(as-port): replace books list with library tree (standalone shell delta)"
```

- [ ] **Step 7: Record the delta in the spec**

Append to the spec's "local deltas" list: `quillas/apps/studio.py: "Your books" wx.ListBox -> wx.TreeCtrl via quill/ui/audio_studio/library_tree.py`.

### Task 2.4: Recently Played store - core/audio_studio/history.py

**Files:**
- Create: `quill/core/audio_studio/history.py`
- Test: `tests/unit/core/audio_studio/test_history.py`

**Interfaces:**
- Consumes: `quill.core.storage.write_json_atomic`.
- Produces (mirror `quill/core/podcasts/history.py:22-126`):
  - `PlayedBook` dataclass: `path: str, title: str, position_ms: int = 0, chapter: int = 0`; `to_dict`/`from_dict`.
  - `AudioStudioHistory` dataclass: `books: list[PlayedBook]`, `resume_on_launch: bool = True`; `record(path, *, title, position_ms, chapter) -> None` (dedup by path, cap `_MAX_ENTRIES=15`, move to front); `last_played` property -> `PlayedBook | None`.
  - `load_history(data_dir: Path) -> AudioStudioHistory`, `save_history(data_dir, history) -> None`.
  - File: `data_dir / "audio_studio_history.json"`.

- [ ] **Step 1: Write failing tests** (mirror the podcasts/history.test shape)

```python
from quill.core.audio_studio.history import AudioStudioHistory, PlayedBook, load_history, save_history

def test_record_moves_to_front_and_dedups():
    h = AudioStudioHistory()
    h.record("a", title="A", position_ms=100, chapter=1)
    h.record("b", title="B", position_ms=200, chapter=0)
    h.record("a", title="A", position_ms=300, chapter=2)
    assert [b.path for b in h.books] == ["a", "b"]
    assert h.books[0].position_ms == 300 and h.books[0].chapter == 2

def test_cap_at_15():
    h = AudioStudioHistory()
    for i in range(20):
        h.record(f"b{i}", title=f"T{i}", position_ms=0, chapter=0)
    assert len(h.books) == 15

def test_last_played():
    h = AudioStudioHistory()
    assert h.last_played is None
    h.record("a", title="A", position_ms=0, chapter=0)
    assert h.last_played.path == "a"

def test_round_trip(tmp_path):
    h = AudioStudioHistory(resume_on_launch=False)
    h.record("a", title="A", position_ms=50, chapter=3)
    save_history(tmp_path, h)
    got = load_history(tmp_path)
    assert got.resume_on_launch is False
    assert got.last_played.path == "a" and got.last_played.chapter == 3
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/unit/core/audio_studio/test_history.py -x -q`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement** (mirror `quill/core/podcasts/history.py:22-126` exactly; swap episode fields for `path/title/position_ms/chapter`; `_MAX_ENTRIES=15`; `_FILE_NAME="audio_studio_history.json"`).

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/core/audio_studio/test_history.py -x -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/audio_studio/history.py tests/unit/core/audio_studio/test_history.py && git commit -m "feat(as-port): add audio_studio recently-played history store"
```

### Task 2.5: Resume-on-launch + Recently Played submenu (standalone shell)

**Files:**
- Modify: `S:/QUILL-AS/quillas/apps/studio.py` (startup hook near line 168; menu in `_build_menu_bar` line 293; resume menu check item mirroring `quill/apps/podcasts.py:607-609`)
- Test: `tests/unit/ui/test_app_shell.py` (extend with a resume-flag toggle test, mirroring the existing QUILL-AS `**_kw` regression pattern)

**Interfaces:**
- Consumes: `quillas.core.audio_studio.history` (`load_history`, `save_history`, `AudioStudioHistory`).
- Produces: `_maybe_resume_last_book()` in `StudioAppFrame`; a "Recently Played" submenu listing `history.books`; a "Resume Last Book on La&unch" check item bound to `_toggle_resume_on_launch`.

- [ ] **Step 1: Add the startup hook**

In `__init__` (after line 168, near the existing `wx.CallAfter(self._maybe_check_updates_on_startup)`), add:

```python
self._history = load_history(app_data_dir())
if self._history.resume_on_launch:
    wx.CallAfter(self._maybe_resume_last_book)
```

- [ ] **Step 2: Implement _maybe_resume_last_book**

```python
def _maybe_resume_last_book(self, **_kw) -> None:
    last = self._history.last_played
    if last is None:
        return
    self._open_book_path(Path(last.path), resume_ms=last.position_ms, chapter=last.chapter)
```

(Where `_open_book_path` opens the workbench on the book; reuse the existing `_open_selected_book` path generalized to take a `Path`.)

- [ ] **Step 3: Add Recently Played submenu + Resume-on-Launch check item**

In `_build_menu_bar` (line 293), in the File/Library menu add a "Recently Played" submenu populated from `self._history.books` (each item opens that book), and `self._resume_menu_item_id = wx.NewIdRef(); subs_menu.AppendCheckItem(self._resume_menu_item_id, "Resume Last Book on La&nch")` with check state from `self._history.resume_on_launch`. Bind toggle to `_toggle_resume_on_launch` which flips `self._history.resume_on_launch` and calls `save_history`.

- [ ] **Step 4: Record a play when a book opens**

Where the shell opens a book (the existing `_open_selected_book` path), call `self._history.record(path=str(p), title=p.stem, position_ms=0, chapter=0)` then `save_history(app_data_dir(), self._history)`. Update `position_ms`/`chapter` on close or on listening-position saves (hook into the existing listening-position resume writer).

- [ ] **Step 5: Write the toggle test**

```python
def test_resume_on_launch_toggle_persists(tmp_path, monkeypatch):
    # Point the shell at an isolated data dir; flip the flag; reload history; assert persisted.
    ...
```

- [ ] **Step 6: Run tests + launch**

Run: `cd S:/QUILL-AS && pytest -q tests/unit/ui/test_app_shell.py -q` then launch via `run-quill-audio-studio.bat`.
Expected: tests pass; app launches; closing a book and relaunching resumes it when the flag is on.

- [ ] **Step 7: Commit (QUILL-AS)**

```bash
cd S:/QUILL-AS && git add quillas/apps/studio.py tests/unit/ui/test_app_shell.py && git commit -m "feat(as-port): resume-on-launch + Recently Played submenu"
```

- [ ] **Step 8: Record delta in spec** (shell wiring is a standalone delta; backing is shared).

### Task 2.6: Sleep timer - core/audio_studio/sleep_timer.py

**Files:**
- Create: `quill/core/audio_studio/sleep_timer.py`
- Test: `tests/unit/core/audio_studio/test_sleep_timer.py`

**Interfaces:**
- Consumes: `quill.core.storage.write_json_atomic`. Model on `quill/core/radio/wake_timer.py` (pure check + daemon-thread watcher).
- Produces:
  - `SleepTimerSetting` dataclass: `enabled: bool, delay_minutes: float = 30.0, end_of_chapter: bool = False, last_started_at: float = 0.0`
  - `should_fire(setting, now: float, *, started_at: float) -> bool` (pure)
  - `SleepTimerWatcher` class: `__init__(self, *, on_sleep: Callable[[], None], check_interval: float = 5.0) -> None`; `start(setting, *, now: float) -> None`; `cancel() -> None`; `shutdown() -> None`; daemon thread named `"quill-as-sleep-timer"`.
  - `load_sleep_setting(data_dir) -> SleepTimerSetting`, `save_sleep_setting(data_dir, setting) -> None`. File: `data_dir / "audio_studio_sleep_timer.json"`.

- [ ] **Step 1: Write failing tests** (mirror wake_timer test shape)

```python
import time
from quill.core.audio_studio.sleep_timer import SleepTimerSetting, should_fire, SleepTimerWatcher

def test_should_fire_after_delay():
    s = SleepTimerSetting(enabled=True, delay_minutes=1.0)
    assert should_fire(s, now=70.0, started_at=0.0) is True
    assert should_fire(s, now=50.0, started_at=0.0) is False

def test_disabled_never_fires():
    s = SleepTimerSetting(enabled=False, delay_minutes=1.0)
    assert should_fire(s, now=999.0, started_at=0.0) is False

def test_watcher_calls_on_sleep_once():
    fired = []
    w = SleepTimerWatcher(on_sleep=lambda: fired.append(True), check_interval=0.05)
    w.start(SleepTimerSetting(enabled=True, delay_minutes=0.02), now=0.0)
    time.sleep(0.2)
    assert fired == [True]
    w.shutdown()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/unit/core/audio_studio/test_sleep_timer.py -x -q`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement** (mirror `quill/core/radio/wake_timer.py:25-160`: dataclass + pure `should_fire` + `SleepTimerWatcher` with a daemon `threading.Thread` that waits on a `threading.Event` for `check_interval`, calls `on_sleep` once on the watcher thread, then stops. Host marshals to UI thread via `wx.CallAfter` at the call site, not inside the watcher.)

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/core/audio_studio/test_sleep_timer.py -x -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/audio_studio/sleep_timer.py tests/unit/core/audio_studio/test_sleep_timer.py && git commit -m "feat(as-port): add audio_studio sleep timer"
```

### Task 2.7: Media keys + Sleep Timer dialog (standalone shell)

**Files:**
- Create: `quill/ui/audio_studio/sleep_timer_dialog.py`
- Modify: `S:/QUILL-AS/quillas/apps/studio.py` (register media keys in `__init__`; add Sleep Timer menu item)

**Interfaces:**
- Consumes: `quillas.ui.app_shell.AppShellFrame._register_media_keys` (already vendored; handler dict shape `{"play_pause": fn, "stop": fn, "next": fn, "previous": fn}`, per `quill/ui/app_shell.py:202-231`); `quillas.core.audio_studio.sleep_timer`.
- Produces: `_register_media_keys({...})` call in `StudioAppFrame.__init__`; `_on_sleep_timer` handler opening `SleepTimerDialog`; a Sleep Timer menu item in the Book Tools menu.

- [ ] **Step 1: Register media keys in __init__**

In `studio.py:__init__` (after the tray icon at line 162), add:

```python
self._register_media_keys({
    "play_pause": self._on_media_play_pause,
    "stop": self._on_media_stop,
    "next": self._on_media_next_chapter,
    "previous": self._on_media_prev_chapter,
})
self._sleep_watcher = SleepTimerWatcher(on_sleep=lambda: wx.CallAfter(self._on_sleep_fired))
```

(`_unregister_media_keys` is already called at close, line 1575; add `self._sleep_watcher.shutdown()` next to it.)

- [ ] **Step 2: Implement the media-key handlers**

`_on_media_play_pause` / `_on_media_stop` / `_on_media_next_chapter` / `_on_media_prev_chapter` delegate to the active workbench's `PlayerPanel` (`self._active_player.play()`/`pause()`/`stop()`/`play_chapter(idx+/-1)`). Keep a reference `self._active_player` set when a workbench opens (mirror how `apps/radio.py` tracks its controller).

- [ ] **Step 3: Implement the Sleep Timer dialog**

`quill/ui/audio_studio/sleep_timer_dialog.py`: a `wx.Dialog` with enable checkbox, delay spin (minutes), end-of-chapter checkbox, Start/Cancel. Returns a `SleepTimerSetting`. Go through `_show_modal_dialog` if wired into MainFrame; in the standalone shell call `ShowModal()` per the existing standalone dialog pattern (the dialog-inventory gate is QUILL-side; standalone is exempt but still use `apply_modal_ids` for keyboard contract).

- [ ] **Step 4: Add the menu item + handler**

In `_build_menu_bar` Book Tools menu: `sleep_id = wx.NewIdRef(); menu.Append(sleep_id, "Sleep &Timer...")`; bind to `_on_sleep_timer` which opens the dialog, persists `save_sleep_setting`, and `self._sleep_watcher.start(setting, now=time.time())`.

- [ ] **Step 5: Implement _on_sleep_fired**

```python
def _on_sleep_fired(self, **_kw) -> None:
    if self._active_player is not None:
        self._active_player.stop()
    self._set_status("Sleep timer: playback stopped")
```

- [ ] **Step 6: Test + launch**

Run: `cd S:/QUILL-AS && pytest -q` then launch via `run-quill-audio-studio.bat`.
Expected: green; media keys control the active book; Sleep Timer stops playback after the delay.

- [ ] **Step 7: Commit (QUILL-AS)**

```bash
cd S:/QUILL-AS && git add quillas/ui/audio_studio/sleep_timer_dialog.py quillas/apps/studio.py && git commit -m "feat(as-port): media keys + sleep timer dialog"
```

- [ ] **Step 8: Re-vendor the new UI module**

`python S:/QUILL-AS/scripts/vendor_from_quill.py` (picks up `ui/audio_studio/sleep_timer_dialog.py` from SEED added in Task 2.0). Commit the re-vendor in QUILL-AS.

### Task 2.8: Per-book volume + Mute - core/audio_studio/book_prefs.py

**Files:**
- Create: `quill/core/audio_studio/book_prefs.py`
- Test: `tests/unit/core/audio_studio/test_book_prefs.py`

**Interfaces:**
- Consumes: `quill.core.storage.write_json_atomic`. Mirror `quill/core/radio/favorites.py:55,169` (`volume_percent`, `set_volume`).
- Produces:
  - `BookPrefs` dataclass: `volume_percent: int = -1` (-1 = unset), `muted: bool = False`
  - `BookPrefsStore` dataclass: `entries: dict[str, BookPrefs]`
  - `get_prefs(store, book_path: str) -> BookPrefs`
  - `set_volume(store, book_path: str, volume_percent: int) -> bool`
  - `set_muted(store, book_path: str, muted: bool) -> None`
  - `load_prefs(data_dir) -> BookPrefsStore`, `save_prefs(data_dir, store) -> None`. File: `data_dir / "audio_studio_book_prefs.json"`.

- [ ] **Step 1: Write failing tests** (mirror radio favorites volume tests)

```python
from quill.core.audio_studio.book_prefs import BookPrefsStore, get_prefs, set_volume, set_muted, load_prefs, save_prefs

def test_default_unset():
    s = BookPrefsStore()
    assert get_prefs(s, "x").volume_percent == -1

def test_set_volume_clamps_and_persists(tmp_path):
    s = BookPrefsStore()
    assert set_volume(s, "x", 150) is True
    assert get_prefs(s, "x").volume_percent == 100
    save_prefs(tmp_path, s)
    assert load_prefs(tmp_path).entries["x"].volume_percent == 100

def test_mute_round_trip(tmp_path):
    s = BookPrefsStore()
    set_muted(s, "x", True)
    save_prefs(tmp_path, s)
    assert load_prefs(tmp_path).entries["x"].muted is True
```

- [ ] **Step 2: Run to verify failure** -> `pytest tests/unit/core/audio_studio/test_book_prefs.py -x -q` (FAIL ModuleNotFoundError).

- [ ] **Step 3: Implement** (mirror `quill/core/radio/favorites.py` set_volume: clamp to 0-100, return True when changed).

- [ ] **Step 4: Run tests** -> PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/audio_studio/book_prefs.py tests/unit/core/audio_studio/test_book_prefs.py && git commit -m "feat(as-port): add per-book prefs store (volume/mute)"
```

### Task 2.9: Wire per-book volume + Mute into PlayerPanel + shell

**Files:**
- Modify: `quill/ui/audio_studio/player_panel.py:80-82, 328-330` (volume slider already exists; apply per-book prefs on load; add Mute toggle button)
- Modify: `S:/QUILL-AS/quillas/apps/studio.py` (load/save book prefs; Mute menu item)
- Test: `tests/unit/ui/audio_studio/test_player_panel_volume.py`

**Interfaces:**
- Consumes: `quill.core.audio_studio.book_prefs` (`get_prefs`, `set_volume`, `set_muted`, `load_prefs`, `save_prefs`).
- Produces: `PlayerPanel.load(path, chapters, *, book_prefs: BookPrefs | None = None, resume_ms=0)` applies `volume_percent`/`muted` to the slider + engine before play; `PlayerPanel.toggle_mute() -> None` caches pre-mute volume (mirror `quill/ui/radio/player_controller.py:506`).

- [ ] **Step 1: Write failing test for per-book volume applied on load**

```python
import wx, pytest
from quill.core.audio_studio.book_prefs import BookPrefs
from quill.ui.audio_studio.player_panel import PlayerPanel

@pytest.fixture
def app():
    a = wx.App(False); yield a; a.Destroy()

def test_load_applies_book_volume(app, tmp_path):
    frame = wx.Frame(None)
    p = PlayerPanel(frame)
    # monkeypatch the engine to capture set_volume calls
    calls = []
    p._engine.set_volume = lambda v: calls.append(v)
    p.load("dummy.mp3", chapters=[], book_prefs=BookPrefs(volume_percent=42, muted=False))
    assert calls and calls[-1] == 42
    frame.Destroy()
```

- [ ] **Step 2: Run to verify failure** -> `pytest tests/unit/ui/audio_studio/test_player_panel_volume.py -x -q` (FAIL: `load()` doesn't accept `book_prefs`).

- [ ] **Step 3: Extend PlayerPanel.load + add Mute**

In `player_panel.py:96` `def load(self, path, chapters, *, resume_ms=0)` -> add `book_prefs: BookPrefs | None = None`. Before the first play:

```python
vp = book_prefs.volume_percent if book_prefs and book_prefs.volume_percent >= 0 else 100
muted = book_prefs.muted if book_prefs else False
if muted:
    self._pre_mute_volume = vp
    vp = 0
self._volume.SetValue(vp)
self._engine.set_volume(vp)
```

Add `self._mute_btn` next to the volume slider; `toggle_mute()` mirrors `quill/ui/radio/player_controller.py:506` (cache `_pre_mute_volume`, set 0 on mute, restore on unmute, update slider + engine, announce via the host's `announce`).

- [ ] **Step 4: Wire the shell**

In `studio.py`, when opening a book: `prefs = get_prefs(self._book_prefs_store, str(path))`; pass `book_prefs=prefs` to the workbench/player load. On volume-slider change or Mute toggle in the player, persist via `set_volume`/`set_muted` + `save_prefs(app_data_dir(), self._book_prefs_store)`. Add a Mute menu item (mirror `quill/apps/radio.py:501/531`).

- [ ] **Step 5: Run tests + launch**

Run: `cd S:/QUILL && pytest tests/unit/ui/audio_studio/test_player_panel_volume.py -q` then `cd S:/QUILL-AS && pytest -q && run-quill-audio-studio.bat`.
Expected: per-book volume recalled on reopen; Mute toggles and persists.

- [ ] **Step 6: Commit (QUILL + QUILL-AS)**

```bash
# QUILL
git add quill/ui/audio_studio/player_panel.py tests/unit/ui/audio_studio/test_player_panel_volume.py && git commit -m "feat(as-port): PlayerPanel applies per-book volume + Mute"
# QUILL-AS
cd S:/QUILL-AS && python scripts/vendor_from_quill.py && git add quillas apps && git commit -m "feat(as-port): wire per-book volume/mute in standalone shell"
```

### Task 2.10: Play Queue - core/audio_studio/play_queue.py

**Files:**
- Create: `quill/core/audio_studio/play_queue.py`
- Test: `tests/unit/core/audio_studio/test_play_queue.py`

**Interfaces:**
- Consumes: `quill.core.storage.write_json_atomic`.
- Produces:
  - `QueueEntry` dataclass: `path: str, title: str, chapter: int = 0`
  - `PlayQueue` dataclass: `entries: list[QueueEntry]`, `current_index: int = -1`
  - `add(queue, entry) -> None` (append, dedup by path), `next(queue) -> QueueEntry | None`, `remove(queue, path) -> None`, `clear(queue) -> None`, `is_empty` property, `at(queue, index) -> QueueEntry | None`.
  - `load_queue(data_dir) -> PlayQueue`, `save_queue(data_dir, queue) -> None`. File: `data_dir / "audio_studio_play_queue.json"`.

- [ ] **Step 1: Write failing tests**

```python
from quill.core.audio_studio.play_queue import PlayQueue, QueueEntry, add, next_entry, remove, clear, load_queue, save_queue

def test_add_append_dedup():
    q = PlayQueue()
    add(q, QueueEntry("a", "A"))
    add(q, QueueEntry("a", "A"))  # dup
    assert len(q.entries) == 1

def test_next_advances_and_wraps():
    q = PlayQueue(current_index=-1)
    add(q, QueueEntry("a", "A")); add(q, QueueEntry("b", "B"))
    assert next_entry(q).path == "a"
    assert next_entry(q).path == "b"
    assert next_entry(q).path == "a"  # wrap

def test_remove_and_clear_and_round_trip(tmp_path):
    q = PlayQueue()
    add(q, QueueEntry("a", "A")); add(q, QueueEntry("b", "B"))
    remove(q, "a")
    assert [e.path for e in q.entries] == ["b"]
    clear(q)
    assert q.is_empty
    add(q, QueueEntry("c", "C"))
    save_queue(tmp_path, q)
    assert load_queue(tmp_path).entries[0].path == "c"
```

(Use `next_entry` as the function name to avoid shadowing the builtin `next`.)

- [ ] **Step 2: Run to verify failure** -> FAIL ModuleNotFoundError.

- [ ] **Step 3: Implement** (simple ordered list; `next_entry` increments `current_index` mod len, returns `at(current_index)`).

- [ ] **Step 4: Run tests** -> PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/audio_studio/play_queue.py tests/unit/core/audio_studio/test_play_queue.py && git commit -m "feat(as-port): add chapter play queue store"
```

### Task 2.11: Play Queue UI + top-level menu/command

**Files:**
- Create: `quill/ui/audio_studio/play_queue_dialog.py`
- Modify: `S:/QUILL-AS/quillas/apps/studio.py` (Play Queue menu item + command; auto-advance on chapter end)
- Modify: `S:/QUILL/quill/core/feature_command_map.py` (register `studio.play_queue` command id; mirror `tools.speech_batch_export` mapping)

**Interfaces:**
- Consumes: `quill.core.audio_studio.play_queue`.
- Produces: `PlayQueueDialog` (a `wx.Dialog` listing queue entries with Add/Next/Remove/Clear); `studio.play_queue` command id; auto-advance wiring in the shell on `EVT_MEDIA_FINISHED` (or the player's end-of-track callback).

- [ ] **Step 1: Write a headless build smoke test**

```python
import wx, pytest
from quill.core.audio_studio.play_queue import PlayQueue, QueueEntry
from quill.ui.audio_studio.play_queue_dialog import PlayQueueDialog

@pytest.fixture
def app():
    a = wx.App(False); yield a; a.Destroy()

def test_dialog_builds(app):
    q = PlayQueue()
    q.entries = [QueueEntry("a", "A"), QueueEntry("b", "B")]
    dlg = PlayQueueDialog(None, q)
    assert dlg is not None
    dlg.Destroy()
```

- [ ] **Step 2: Run to verify failure** -> FAIL ModuleNotFoundError.

- [ ] **Step 3: Implement PlayQueueDialog**

A `wx.Dialog` with a `wx.ListBox` of queue entries, buttons Add (FilePicker), Next, Remove, Clear, Close. `apply_modal_ids` for keyboard contract. Mutations update the queue and `save_queue` (host passes a save callback).

- [ ] **Step 4: Register the command + menu**

In `quill/core/feature_command_map.py`, add `"studio.play_queue": "core.read_aloud"` (same feature gate as the rest of Audio Studio; mirror the `tools.speech_batch_export` entry at line 168). In `studio.py:_build_menu_bar` add a top-level "Play &Queue..." menu item bound to `_on_play_queue` which opens `PlayQueueDialog` with `self._play_queue`.

- [ ] **Step 5: Wire auto-advance**

When the active player's media finishes (the player end-of-track callback), call `next_entry(self._play_queue)` and load+play that entry.

- [ ] **Step 6: Run tests + launch**

Run: `cd S:/QUILL && pytest tests/unit/ui/audio_studio -q` then `cd S:/QUILL-AS && pytest -q && run-quill-audio-studio.bat`.
Expected: Play Queue dialog opens; Next advances; auto-advance on chapter end.

- [ ] **Step 7: Commit (QUILL + QUILL-AS)**

```bash
# QUILL
git add quill/ui/audio_studio/play_queue_dialog.py quill/core/feature_command_map.py tests/unit/ui/audio_studio && git commit -m "feat(as-port): add Play Queue dialog + studio.play_queue command"
# QUILL-AS
cd S:/QUILL-AS && python scripts/vendor_from_quill.py && git add quillas apps && git commit -m "feat(as-port): wire Play Queue top-level menu + auto-advance"
```

### Task 2.12: UIA regression coverage + Phase 2 gate

**Files:**
- Modify: `tests/uia/test_audio_studio_dialogs.py` (extend to cover Sleep Timer dialog, Play Queue dialog, library tree context menu)

- [ ] **Step 1: Extend the UIA suite**

Add tests walking the Sleep Timer dialog and Play Queue dialog by keyboard, asserting the spoken trace announces the dialog title and key controls (mirror the existing 8 tests in `tests/uia/test_audio_studio_dialogs.py`). Add a library-tree context-menu walk.

- [ ] **Step 2: Run the UIA suite (CI-only per Jeff's rule - do NOT run locally unasked)**

Note: per the no-desktop-UI-automation rule, these run in CI, not on Jeff's machine. Commit the tests; let CI run them.

- [ ] **Step 3: Confirm both unit suites green**

Run: `cd S:/QUILL && pytest -q` and `cd S:/QUILL-AS && pytest -q`.
Expected: PASS.

- [ ] **Step 4: Re-vendor final + commit**

```bash
cd S:/QUILL-AS && python scripts/vendor_from_quill.py && python scripts/vendor_tests.py && git add quillas tests && git commit -m "chore(as-port): final re-vendor of port-in features"
```

- [ ] **Step 5: Open the PR (do not merge)**

```bash
gh pr create --base main --head feature/as-port --title "Audio Studio port-in: library tree, resume+recent, media keys+sleep timer, per-book volume/queue" --body "..."
```

---

## Self-review notes (applied during writing)

- Spec coverage: every spec section maps to a task. Phase 1 trim -> Tasks 1.1-1.8 (all DROP modules + deny-list + verify loop). Phase 2 four features -> Tasks 2.1-2.11; UIA + gate -> 2.12.
- The trim is intentionally iterative (Task 1.7) rather than pretending every guard site is known upfront; the authoritative table lists the confirmed vendored sites, and the verify loop catches the rest.
- Embedded Audio Studio has no library list to replace (wizard-only), so the library tree is a standalone-shell feature with shared backing - recorded as a delta. This is a deliberate deviation from "lands in quill/ embedded-first," justified because the embedded Audio Studio surface is a wizard, not a library browser. The backing + widget still live in `quill/` and vendor cleanly.
- All shell-only wiring (media keys, resume, sleep timer menu, per-book volume shell wiring, play queue menu) is in `quillas/apps/studio.py` (hand-written) and recorded in the spec delta list; the shared modules they call are vendored from `quill/`.