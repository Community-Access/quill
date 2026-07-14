# Page Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an always-on "page" status bar cell for every document — an exact count for PDFs (via preserved page boundaries) and an estimated word-count-based count for everything else — plus a track-aware Go To Page command, fully documented.

**Architecture:** One status bar cell computed by a single dispatcher branch; two pure, wx-free functions in `quill/core/navigation.py` for the estimate; PDF import changed to preserve real page boundaries as form-feed (`\f`) characters, reusing `navigation.py`'s existing `page_starts()`/`page_start_for_number()` rather than building new exact-page machinery.

**Tech Stack:** Python 3.13, wxPython (UI layer only), pytest.

## Global Constraints

- Word-count basis for estimates: **words per page**, default **300**, clamped **[150, 600]** (setting `page_estimate_words_per_page`).
- Estimated display text always includes both a tilde (`~`) and the word "estimated" — never one without the other, never omitted. Exact display text never includes either.
- The new `"page"` status bar cell is **visible by default** (not in `_default_status_bar_hidden()`), positioned immediately after `"line_column"` in `STATUS_BAR_ITEMS` — not first, but adjacent to the other position-context cell, per direction from Jeff.
- The `"page"` cell is suppressed whenever the existing `"braille"` cell is active (BRF documents keep their own richer page system untouched).
- Track B (exact pages via preserved `\f` boundaries) ships for **PDF only** in this plan. DOCX real page breaks are **out of scope** — DOCX import goes through Pandoc/MarkItDown text conversion, which does not preserve page-break positions; DOCX stays on the estimate track. This is a scope narrowing from the original spec, made during planning; the spec doc is updated in Task 7 to match.
- Closes GitHub issue #872. Ships in 0.9.0 Beta 2 (release notes' "no new headline features" line gets a carve-out, per Jeff).

---

### Task 1: Estimate + exact page-count core functions

**Files:**
- Modify: `quill/core/navigation.py`
- Test: `tests/unit/core/test_navigation.py`

**Interfaces:**
- Produces: `estimate_page_count(text: str, words_per_page: int) -> int`, `estimate_page_for_position(text: str, position: int, words_per_page: int) -> int`, `estimate_page_start_for_number(text: str, page_number: int, words_per_page: int) -> int | None` — all pure, no wx, no I/O. `words_per_page` is always the caller-supplied setting value (no default baked in here — the default of 300 lives in Task 2's setting).

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/core/test_navigation.py` (append after the existing `page_start_for_number` tests):

```python
from quill.core.navigation import (
    estimate_page_count,
    estimate_page_for_position,
    estimate_page_start_for_number,
)


def test_estimate_page_count_empty_text_is_one_page() -> None:
    assert estimate_page_count("", 300) == 1


def test_estimate_page_count_rounds_up() -> None:
    text = " ".join(["word"] * 301)  # 301 words, 300/page -> 2 pages
    assert estimate_page_count(text, 300) == 2


def test_estimate_page_count_exact_multiple() -> None:
    text = " ".join(["word"] * 600)  # exactly 2 pages at 300/page
    assert estimate_page_count(text, 300) == 2


def test_estimate_page_for_position_start_of_document_is_page_one() -> None:
    text = " ".join(["word"] * 900)  # 3 pages at 300/page
    assert estimate_page_for_position(text, 0, 300) == 1


def test_estimate_page_for_position_tracks_caret_forward() -> None:
    words = ["word"] * 900  # 3 pages at 300/page
    text = " ".join(words)
    # Position at the start of the 301st word (i.e. into page 2).
    page_1_text = " ".join(words[:300]) + " "
    position = len(page_1_text)
    assert estimate_page_for_position(text, position, 300) == 2


def test_estimate_page_for_position_clamps_to_final_page() -> None:
    text = " ".join(["word"] * 10)  # 1 page at 300/page
    assert estimate_page_for_position(text, len(text), 300) == 1


def test_estimate_page_start_for_number_page_one_is_zero() -> None:
    text = " ".join(["word"] * 900)
    assert estimate_page_start_for_number(text, 1, 300) == 0


def test_estimate_page_start_for_number_matches_word_boundary() -> None:
    words = ["word"] * 900
    text = " ".join(words)
    expected = len(" ".join(words[:300]) + " ")
    assert estimate_page_start_for_number(text, 2, 300) == expected


def test_estimate_page_start_for_number_out_of_range_is_none() -> None:
    text = " ".join(["word"] * 10)  # 1 page at 300/page
    assert estimate_page_start_for_number(text, 2, 300) is None
    assert estimate_page_start_for_number(text, 0, 300) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_navigation.py -k estimate_page -v`
Expected: FAIL with `ImportError: cannot import name 'estimate_page_count'`

- [ ] **Step 3: Implement the functions**

In `quill/core/navigation.py`, add after `page_start_for_number` (after line 18):

```python
def _word_starts(text: str) -> list[int]:
    """Character offset of each word (maximal run of non-whitespace).

    Matches the token count `text.split()` would produce (used by the
    word-count status cell), so the page estimate always agrees with the
    word count shown elsewhere in the status bar.
    """
    return [match.start() for match in re.finditer(r"\S+", text)]


def estimate_page_count(text: str, words_per_page: int) -> int:
    """Estimate a page count from word count alone.

    This is an approximation for documents with no real page breaks
    (plain text, Markdown, most DOCX) -- it has no knowledge of fonts,
    margins, or paper size, and will not match a printed or exported
    page count. Always returns at least 1.
    """
    words = len(_word_starts(text))
    if words == 0:
        return 1
    return max(1, -(-words // words_per_page))  # ceiling division


def estimate_page_for_position(text: str, position: int, words_per_page: int) -> int:
    """Estimate which page `position` falls on, clamped to the total."""
    starts = _word_starts(text)
    if not starts:
        return 1
    position = max(0, min(position, len(text)))
    words_before = sum(1 for start in starts if start < position)
    page = words_before // words_per_page + 1
    total = estimate_page_count(text, words_per_page)
    return max(1, min(page, total))


def estimate_page_start_for_number(
    text: str, page_number: int, words_per_page: int
) -> int | None:
    """Character offset where estimated `page_number` begins, or None if out of range."""
    if page_number < 1:
        return None
    starts = _word_starts(text)
    total = estimate_page_count(text, words_per_page)
    if page_number > total:
        return None
    if page_number == 1:
        return 0
    index = (page_number - 1) * words_per_page
    if index >= len(starts):
        return len(text)
    return starts[index]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_navigation.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones)

- [ ] **Step 5: Lint and commit**

```bash
ruff check quill/core/navigation.py tests/unit/core/test_navigation.py
ruff format --check quill/core/navigation.py tests/unit/core/test_navigation.py
git add quill/core/navigation.py tests/unit/core/test_navigation.py
git commit -m "feat(navigation): estimate page count and position from word count (#872)"
```

---

### Task 2: `page_estimate_words_per_page` setting

**Files:**
- Modify: `quill/core/settings.py:469` (field), `quill/core/settings.py:1070` (parsing), `quill/core/settings.py:1438` (constructor)
- Modify: `quill/core/settings_specs.py:1827` (SettingSpec)
- Test: `tests/unit/core/test_settings.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Settings.page_estimate_words_per_page: int` (default `300`, clamped `[150, 600]` on load), a searchable `SettingSpec` named `"page_estimate_words_per_page"` in the `"navigation"` group.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/core/test_settings.py`:

```python
def test_page_estimate_words_per_page_defaults_to_300() -> None:
    assert Settings().page_estimate_words_per_page == 300


def test_page_estimate_words_per_page_clamps_on_load(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text(
        '{"page_estimate_words_per_page": 5000}', encoding="utf-8"
    )
    loaded = load_settings()
    assert loaded.page_estimate_words_per_page == 600


def test_page_estimate_words_per_page_invalid_value_falls_back(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text(
        '{"page_estimate_words_per_page": "not a number"}', encoding="utf-8"
    )
    loaded = load_settings()
    assert loaded.page_estimate_words_per_page == 300
```

(This file already imports `Settings`, `load_settings`, `save_settings` at the top — no new imports needed.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_settings.py -k page_estimate_words_per_page -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'page_estimate_words_per_page'`

- [ ] **Step 3: Add the field**

In `quill/core/settings.py`, after line 469 (`braille_lines_per_page: int = 25`), add:

```python
    # Page indicator (#872): word-count basis for the estimated page count
    # shown for documents with no real page breaks (plain text, Markdown,
    # most DOCX). This is an approximation, not a printed page count.
    page_estimate_words_per_page: int = 300
```

- [ ] **Step 4: Add load-time parsing**

In `quill/core/settings.py`, after line 1070 (`braille_lines_per_page = max(20, min(30, braille_lines_per_page))`), add:

```python
        try:
            page_estimate_words_per_page = int(data.get("page_estimate_words_per_page", 300))
        except (TypeError, ValueError):
            page_estimate_words_per_page = 300
        page_estimate_words_per_page = max(150, min(600, page_estimate_words_per_page))
```

- [ ] **Step 5: Wire the constructor**

In `quill/core/settings.py`, after line 1438 (`braille_lines_per_page=braille_lines_per_page,`), add:

```python
            page_estimate_words_per_page=page_estimate_words_per_page,
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_settings.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 7: Add the SettingSpec**

In `quill/core/settings_specs.py`, after the `braille_use_form_feeds` SettingSpec block (ends at line 1838), add:

```python
    SettingSpec(
        "page_estimate_words_per_page",
        "Estimated words per page",
        "navigation",
        "int",
        "Used only for documents without real page breaks (plain text, "
        "Markdown, most DOCX files) to estimate a page count from word "
        "count. This is an approximation, not an exact printed page count -- "
        "it does not account for fonts, margins, or paper size.",
        minimum=150,
        maximum=600,
        keywords=("page", "page count", "page number", "status bar", "estimate"),
        feature_id="core.editor",
    ),
```

- [ ] **Step 8: Test the spec is discoverable**

Run: `pytest tests/unit/core/test_settings_specs.py -v` (if this file doesn't exist, skip this step -- there is no existing per-spec test convention to match)

Run: `pytest tests/unit/core -k settings -v`
Expected: PASS

- [ ] **Step 9: Lint and commit**

```bash
ruff check quill/core/settings.py quill/core/settings_specs.py tests/unit/core/test_settings.py
ruff format --check quill/core/settings.py quill/core/settings_specs.py tests/unit/core/test_settings.py
git add quill/core/settings.py quill/core/settings_specs.py tests/unit/core/test_settings.py
git commit -m "feat(settings): add page_estimate_words_per_page (#872)"
```

---

### Task 3: Register the "page" status bar item

**Files:**
- Modify: `quill/core/settings_normalizers.py:10-61` (`STATUS_BAR_ITEMS` tuple)
- Modify: `quill/ui/main_frame.py:792-891` (`_STATUS_BAR_LABELS`, `_STATUS_BAR_WIDTHS`, `_STATUS_BAR_FEATURES`)
- Test: `tests/unit/core/test_settings.py`, `tests/unit/ui/test_main_frame_statusbar_context.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `"page"` is a member of `STATUS_BAR_ITEMS`, positioned right after `"line_column"`; `"page"` is **not** in `_default_status_bar_hidden()`; `MainFrame._STATUS_BAR_LABELS["page"] == "Page"`, `_STATUS_BAR_WIDTHS["page"] == 220`, `_STATUS_BAR_FEATURES["page"] == "core.analysis"`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/core/test_settings.py`:

```python
def test_page_is_a_status_bar_item_right_after_line_column() -> None:
    from quill.core.settings_normalizers import STATUS_BAR_ITEMS

    assert "page" in STATUS_BAR_ITEMS
    assert STATUS_BAR_ITEMS.index("page") == STATUS_BAR_ITEMS.index("line_column") + 1


def test_page_is_visible_by_default() -> None:
    assert "page" not in Settings().status_bar_hidden
```

Add to `tests/unit/ui/test_main_frame_statusbar_context.py`:

```python
def test_page_status_bar_metadata_is_registered() -> None:
    assert MainFrame._STATUS_BAR_LABELS["page"] == "Page"
    assert MainFrame._STATUS_BAR_WIDTHS["page"] == 220
    assert MainFrame._STATUS_BAR_FEATURES["page"] == "core.analysis"
```

(Confirm `MainFrame` is already imported at the top of `test_main_frame_statusbar_context.py`; if not, add `from quill.ui.main_frame import MainFrame`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_settings.py tests/unit/ui/test_main_frame_statusbar_context.py -k page -v`
Expected: FAIL (`"page" not in STATUS_BAR_ITEMS` / `KeyError: 'page'`)

- [ ] **Step 3: Add "page" to STATUS_BAR_ITEMS**

In `quill/core/settings_normalizers.py`, change:

```python
STATUS_BAR_ITEMS: tuple[str, ...] = (
    "line_column",
    "message",
```

to:

```python
STATUS_BAR_ITEMS: tuple[str, ...] = (
    "line_column",
    # #872: page indicator. Visible by default (not in
    # _default_status_bar_hidden below), placed right after line_column
    # since both are "where am I" position cells -- not first, but adjacent.
    "page",
    "message",
```

Do **not** add `"page"` to `_default_status_bar_hidden()` (lines 68-93) -- its absence from that list is what makes it visible by default.

- [ ] **Step 4: Add the three MainFrame class dicts**

In `quill/ui/main_frame.py`, in `_STATUS_BAR_LABELS` (starts line 792), add after `"line_column": "Position",`:

```python
        "page": "Page",
```

In `_STATUS_BAR_WIDTHS` (starts line 824), add after `"line_column": 140,`:

```python
        "page": 220,
```

In `_STATUS_BAR_FEATURES` (starts line 856), add after `"line_column": "core.editor",`:

```python
        "page": "core.analysis",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_settings.py tests/unit/ui/test_main_frame_statusbar_context.py -v`
Expected: PASS

- [ ] **Step 6: Lint and commit**

```bash
ruff check quill/core/settings_normalizers.py quill/ui/main_frame.py tests/unit/core/test_settings.py tests/unit/ui/test_main_frame_statusbar_context.py
ruff format --check quill/core/settings_normalizers.py quill/ui/main_frame.py tests/unit/core/test_settings.py tests/unit/ui/test_main_frame_statusbar_context.py
git add quill/core/settings_normalizers.py quill/ui/main_frame.py tests/unit/core/test_settings.py tests/unit/ui/test_main_frame_statusbar_context.py
git commit -m "feat(statusbar): register the page item, visible by default (#872)"
```

*(Note: `quill/ui/main_frame.py` may exceed its GATE-11 module size budget after this change -- check with `python -m pytest tests/unit/tools/test_module_size_budget.py -q` and, if it fails, add a dated `_rebaseline_` entry to `quill/tools/module_size_budgets.json` following the pattern of existing entries in that file, as part of this commit.)*

---

### Task 4: Status bar cell rendering, help text, activation, and BRF suppression

**Files:**
- Modify: `quill/ui/main_frame_statusbar.py`
- Test: `tests/unit/ui/test_main_frame_statusbar_context.py`, `tests/unit/ui/test_main_frame_navigation.py`

**Interfaces:**
- Consumes: `estimate_page_count`, `estimate_page_for_position` from `quill.core.navigation` (Task 1); `page_starts` from `quill.core.navigation` (pre-existing); `settings.page_estimate_words_per_page` (Task 2).
- Produces: `StatusBarMixin._statusbar_page_text() -> str`; the `"page"` branch in `_statusbar_text_for_item`; `"page"` entry in the help-text dict; `"page": self.go_to_page` in the activation actions dict; `"page"` removed from `_statusbar_items()`'s visible list whenever the `"braille"` cell is active.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/ui/test_main_frame_statusbar_context.py`:

```python
class _PageEditor:
    def __init__(self, text: str, caret: int) -> None:
        self._text = text
        self._caret = caret

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._caret


def _make_page_frame(text: str, caret: int, *, words_per_page: int = 300) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    frame.settings.page_estimate_words_per_page = words_per_page
    frame.editor = _PageEditor(text, caret)  # type: ignore[assignment]
    return frame


def test_page_cell_is_estimated_when_no_form_feeds() -> None:
    text = " ".join(["word"] * 900)  # 3 pages at 300/page
    frame = _make_page_frame(text, 0)
    assert frame._statusbar_text_for_item("page") == "~1 of ~3 (estimated)"


def test_page_cell_is_exact_when_form_feeds_present() -> None:
    text = "page one\fpage two\fpage three"
    caret = text.index("page two")
    frame = _make_page_frame(text, caret)
    assert frame._statusbar_text_for_item("page") == "2 of 3"


def test_page_cell_empty_when_editor_missing() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    assert frame._statusbar_text_for_item("page") == ""


def test_page_help_text_mentions_go_to_page() -> None:
    frame = _make_page_frame("hello", 0)
    assert "Go To Page" in frame._statusbar_help_text("page")
```

Add to `tests/unit/ui/test_main_frame_navigation.py` (reuses the existing `_build_frame` helper already in that file):

```python
def test_page_cell_activates_go_to_page() -> None:
    frame = _build_frame("hello", insertion_point=0)
    called: list[bool] = []
    frame.go_to_page = lambda: called.append(True)  # type: ignore[method-assign]
    frame._activate_statusbar_cell("page")
    assert called == [True]


def test_page_cell_suppressed_when_braille_active() -> None:
    from quill.core.document import Document

    frame = _build_frame("hello", insertion_point=0)
    frame.document = Document(
        text="hello\fworld",
        source_metadata={
            "source_kind": "brf",
            "brf_suffix": "brf",
            "brf_cell_width": 40,
            "brf_line_height": 25,
            "brf_non_ascii_offsets": [],
            "brf_had_bom": False,
            "brf_profile": "ueb_english",
        },
    )
    frame.editor.GetCurrentPos = lambda: 0  # type: ignore[attr-defined]
    frame._get_action_suggestion = lambda: None  # type: ignore[method-assign]
    frame._ai_engine_should_autoshow = lambda: False  # type: ignore[method-assign]

    items = frame._statusbar_items()

    assert "braille" in items
    assert "page" not in items
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/ui/test_main_frame_statusbar_context.py tests/unit/ui/test_main_frame_navigation.py -k page -v`
Expected: FAIL (empty string / KeyError from the activation dict / "page" present alongside "braille")

- [ ] **Step 3: Add the imports**

In `quill/ui/main_frame_statusbar.py`, change:

```python
from quill.core.marks import line_column_for_position
```

to:

```python
from quill.core.marks import line_column_for_position
from quill.core.navigation import estimate_page_count, estimate_page_for_position, page_starts
```

- [ ] **Step 4: Add `_statusbar_page_text`**

In `quill/ui/main_frame_statusbar.py`, add this method right after `_statusbar_braille_text` (after its closing, before `_active_brf_resolver`):

```python
    def _statusbar_page_text(self) -> str:
        """Return the page cell's text: exact "N of M" or "~N of ~M (estimated)".

        Exact when the document's text contains at least one form-feed
        (real page boundaries, e.g. from PDF import); otherwise estimated
        from word count via ``page_estimate_words_per_page``. Never
        returns one style's punctuation for the other -- the tilde and the
        word "estimated" always travel together.
        """
        editor = getattr(self, "editor", None)
        if editor is None:
            return ""
        try:
            text = editor.GetValue()
            position = editor.GetInsertionPoint()
        except RuntimeError:
            return ""
        starts = page_starts(text)
        if len(starts) > 1:
            current = sum(1 for start in starts if start <= position)
            current = max(1, min(current, len(starts)))
            return f"{current} of {len(starts)}"
        words_per_page = getattr(self.settings, "page_estimate_words_per_page", 300)
        total = estimate_page_count(text, words_per_page)
        current = estimate_page_for_position(text, position, words_per_page)
        return f"~{current} of ~{total} (estimated)"
```

- [ ] **Step 5: Wire the dispatcher branch**

In `quill/ui/main_frame_statusbar.py`, in `_statusbar_text_for_item`, change:

```python
        if item == "braille":
            return self._statusbar_braille_text()
```

to:

```python
        if item == "braille":
            return self._statusbar_braille_text()
        if item == "page":
            return self._statusbar_page_text()
```

- [ ] **Step 6: Add the help text**

In `quill/ui/main_frame_statusbar.py`, in `_statusbar_help_text`'s `labels` dict, add after `"line_column": "Go to line",`:

```python
            "page": "Page position. Press Enter for Go To Page.",
```

- [ ] **Step 7: Add the activation wiring**

In `quill/ui/main_frame_statusbar.py`, in `_activate_statusbar_cell`'s `actions` dict, add after `"line_column": self.go_to_line,`:

```python
            "page": self.go_to_page,
```

- [ ] **Step 8: Add the BRF suppression rule**

In `quill/ui/main_frame_statusbar.py`, in `_statusbar_items`, find:

```python
        if "braille" not in visible and self._statusbar_braille_text():
            visible.append("braille")
```

and add immediately after it:

```python
        if "page" in visible and self._statusbar_braille_text():
            visible = [item for item in visible if item != "page"]
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `pytest tests/unit/ui/test_main_frame_statusbar_context.py tests/unit/ui/test_main_frame_navigation.py -v`
Expected: PASS

- [ ] **Step 10: Lint and commit**

```bash
ruff check quill/ui/main_frame_statusbar.py tests/unit/ui/test_main_frame_statusbar_context.py tests/unit/ui/test_main_frame_navigation.py
ruff format --check quill/ui/main_frame_statusbar.py tests/unit/ui/test_main_frame_statusbar_context.py tests/unit/ui/test_main_frame_navigation.py
git add quill/ui/main_frame_statusbar.py tests/unit/ui/test_main_frame_statusbar_context.py tests/unit/ui/test_main_frame_navigation.py
git commit -m "feat(statusbar): render, help, activate, and suppress the page cell (#872)"
```

---

### Task 5: Track-aware Go To Page command

**Files:**
- Modify: `quill/ui/main_frame.py:15176-15209` (`go_to_page`)
- Test: `tests/unit/ui/test_main_frame_navigation.py`

**Interfaces:**
- Consumes: `estimate_page_count`, `estimate_page_start_for_number` from `quill.core.navigation`; `page_starts`, `page_start_for_number` (already imported in `main_frame.py`, lines 197-198).
- Produces: `MainFrame.go_to_page()` now prompts and jumps using the estimate when the document has no real page breaks, and says so in the prompt.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/ui/test_main_frame_navigation.py`, matching the existing
`_TextEntryDialog` fixture convention already used in this file (see
`test_prompt_table_shape_reprompts_invalid_values`):

```python
def _go_to_page_wx(value: str) -> object:
    class _TextEntryDialog:
        def __init__(self, _parent: object, _message: str, _title: str, value: str) -> None:
            self.message = _message
            self.value = value

        def __enter__(self) -> "_TextEntryDialog":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def GetValue(self) -> str:
            return self.value

    return type(
        "WX",
        (),
        {
            "TextEntryDialog": lambda parent, message, title, value: _TextEntryDialog(
                parent, message, title, value
            ),
            "ICON_ERROR": 8,
            "OK": 16,
            "ID_OK": 1,
        },
    )()


def test_go_to_page_exact_jumps_to_form_feed_boundary() -> None:
    text = "page one\fpage two\fpage three"
    frame = _build_frame(text, insertion_point=0)
    frame._wx = _go_to_page_wx("2")
    frame._show_modal_dialog = lambda dialog, title: frame._wx.ID_OK  # type: ignore[method-assign]
    frame.go_to_page()
    assert frame.editor.GetInsertionPoint() == text.index("page two")


def test_go_to_page_estimated_prompt_says_estimated() -> None:
    text = " ".join(["word"] * 900)  # 3 pages at 300/page
    frame = _build_frame(text, insertion_point=0)
    frame._wx = _go_to_page_wx("1")
    frame._show_modal_dialog = lambda dialog, title: frame._wx.ID_OK  # type: ignore[method-assign]
    # Capture the prompt text passed to TextEntryDialog by wrapping the
    # constructor _go_to_page_wx already installed on frame._wx.
    captured: list[str] = []
    original = frame._wx.TextEntryDialog
    frame._wx.TextEntryDialog = lambda parent, message, title, value: (
        captured.append(message) or original(parent, message, title, value)
    )
    frame.go_to_page()
    assert "estimated" in captured[0].lower()


def test_go_to_page_estimated_out_of_range_reports_total() -> None:
    text = " ".join(["word"] * 10)  # 1 page at 300/page
    frame = _build_frame(text, insertion_point=0)
    frame._wx = _go_to_page_wx("5")
    frame._show_modal_dialog = lambda dialog, title: frame._wx.ID_OK  # type: ignore[method-assign]
    messages: list[str] = []
    frame._show_message_box = (  # type: ignore[method-assign]
        lambda message, *_a, **_k: messages.append(message)
    )
    frame.go_to_page()
    assert "1 page" in messages[0]
```

`_build_frame` in this file already sets `frame.settings` with the fields
the earlier tests need; `page_estimate_words_per_page` comes from the real
`Settings` dataclass default (300) since `_build_frame`'s settings object is
a lightweight stand-in -- confirm it exposes `page_estimate_words_per_page`
(add `"page_estimate_words_per_page": 300,` to its dict literal if it
doesn't; `go_to_page` reads it via `getattr(self.settings, ..., 300)` so a
missing attribute still falls back to 300 safely either way).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/ui/test_main_frame_navigation.py -k go_to_page -v`
Expected: FAIL (either an AttributeError from missing `_wx.TextEntryDialog`/`ID_OK` scaffolding, or the prompt/behavior not yet being track-aware)

- [ ] **Step 3: Rewrite `go_to_page`**

In `quill/ui/main_frame.py`, replace the full body of `go_to_page` (lines 15176-15209) with:

```python
    def go_to_page(self) -> None:
        wx = self._wx
        text = self.editor.GetValue()
        starts = page_starts(text)
        exact = len(starts) > 1
        words_per_page = getattr(self.settings, "page_estimate_words_per_page", 300)
        total_pages = len(starts) if exact else estimate_page_count(text, words_per_page)
        prompt = (
            f"Enter a page number (1-{total_pages}):"
            if exact
            else (
                f"Enter an estimated page number (1-{total_pages}). This is "
                "based on word count, not an exact printed page count:"
            )
        )
        with wx.TextEntryDialog(
            self.frame,
            prompt,
            "Go To Page",
            value="1",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Go To Page") != wx.ID_OK:
                return
            raw_value = dialog.GetValue().strip()
        try:
            page_number = int(raw_value)
        except ValueError:
            self._show_message_box(
                "Page number must be a number.",
                "Go To Page",
                wx.ICON_ERROR | wx.OK,
            )
            return
        if exact:
            target = page_start_for_number(text, page_number)
        else:
            target = estimate_page_start_for_number(text, page_number, words_per_page)
        if target is None:
            self._show_message_box(
                f"Document has only {total_pages} page(s).",
                "Go To Page",
                wx.ICON_ERROR | wx.OK,
            )
            return
        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
```

- [ ] **Step 4: Add the new imports**

In `quill/ui/main_frame.py`, change:

```python
    page_start_for_number,
    page_starts,
```

(around line 197-198) to:

```python
    estimate_page_count,
    estimate_page_start_for_number,
    page_start_for_number,
    page_starts,
```

(Keep the existing alphabetical-ish grouping in that import block; insert alongside the other `navigation` imports.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/ui/test_main_frame_navigation.py -v`
Expected: PASS

- [ ] **Step 6: Lint and commit**

```bash
ruff check quill/ui/main_frame.py tests/unit/ui/test_main_frame_navigation.py
ruff format --check quill/ui/main_frame.py tests/unit/ui/test_main_frame_navigation.py
python -m pytest tests/unit/tools/test_module_size_budget.py -q
git add quill/ui/main_frame.py tests/unit/ui/test_main_frame_navigation.py quill/tools/module_size_budgets.json
git commit -m "feat(navigation): Go To Page falls back to a stated estimate (#872)"
```

*(If the budget test fails, add a dated `_rebaseline_` entry to `quill/tools/module_size_budgets.json` before committing, as in Task 3's note.)*

---

### Task 6: PDF import preserves real page boundaries

**Files:**
- Modify: `quill/io/pdf.py:75-98` (`_extract_with_pdfplumber`, `_extract_with_pypdf`)
- Test: `tests/unit/io/test_pdf.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `extract_pdf_text(path).text` now joins pages with `"\f"` instead of `"\n\n"`, so `quill.core.navigation.page_starts()` on the resulting `Document.text` reports one boundary per real PDF page.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/io/test_pdf.py`:

```python
from quill.core.navigation import page_starts


def test_pdfplumber_extraction_joins_pages_with_form_feed(monkeypatch, tmp_path: Path) -> None:
    class _StubPage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _StubPdf:
        def __init__(self) -> None:
            self.pages = [_StubPage("Page one"), _StubPage("Page two"), _StubPage("Page three")]

        def __enter__(self) -> "_StubPdf":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    fake_pdfplumber = types.ModuleType("pdfplumber")
    fake_pdfplumber.open = lambda _path: _StubPdf()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    result = pdf_module._extract_with_pdfplumber(tmp_path / "sample.pdf")

    assert result.text.count("\f") == 2
    assert len(page_starts(result.text)) == 3
    assert result.page_count == 3


def test_pypdf_extraction_joins_pages_with_form_feed(monkeypatch, tmp_path: Path) -> None:
    class _StubPage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _StubReader:
        def __init__(self, _path: str) -> None:
            self.pages = [_StubPage("Page one"), _StubPage("Page two")]

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _StubReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    result = pdf_module._extract_with_pypdf(tmp_path / "sample.pdf")

    assert result.text.count("\f") == 1
    assert len(page_starts(result.text)) == 2
```

(`types`, `sys`, and `Path` are already imported at the top of this test file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/io/test_pdf.py -k form_feed -v`
Expected: FAIL (`result.text.count("\f") == 0`, joined with `"\n\n"` instead)

- [ ] **Step 3: Change the page join**

In `quill/io/pdf.py`, in `_extract_with_pdfplumber`, change:

```python
    text = "\n\n".join(page_texts).strip()
    score = _score_pdf_text(text, page_count, sum(1 for page_text in page_texts if page_text))
    return PdfExtractionResult(
        text=text + "\n" if text else "",
        quality_score=score,
        engine="pdfplumber",
```

to:

```python
    # #872: join with a form feed, not a blank line, so real page
    # boundaries survive into the editable Document text. This makes
    # quill.core.navigation.page_starts()/page_start_for_number() -- already
    # built for this, previously unreachable for real documents -- report
    # exact pages for PDFs.
    text = "\f".join(page_texts).strip()
    score = _score_pdf_text(text, page_count, sum(1 for page_text in page_texts if page_text))
    return PdfExtractionResult(
        text=text + "\n" if text else "",
        quality_score=score,
        engine="pdfplumber",
```

Make the identical change in `_extract_with_pypdf` (same `"\n\n".join(page_texts)` line, same comment, same replacement).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/io/test_pdf.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones -- confirm none of them assert on `"\n\n"` appearing in extracted text; if one does, it was pinning the old join and should be updated to assert `"\f"` instead)

- [ ] **Step 5: Lint and commit**

```bash
ruff check quill/io/pdf.py tests/unit/io/test_pdf.py
ruff format --check quill/io/pdf.py tests/unit/io/test_pdf.py
git add quill/io/pdf.py tests/unit/io/test_pdf.py
git commit -m "feat(pdf): preserve real page boundaries as form feeds (#872)"
```

---

### Task 7: Documentation — spec amendment, PRD, user guide, CHANGELOG, release notes

**Files:**
- Modify: `docs/superpowers/specs/2026-07-07-page-indicator-design.md`
- Modify: `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`
- Modify: `docs/user guide/userguide.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/release notes/release0.9.0-beta2.md`

- [ ] **Step 1: Amend the spec's Track B section**

In `docs/superpowers/specs/2026-07-07-page-indicator-design.md`, in the "Track B — real pages" section, add this paragraph immediately after the existing DOCX bullet (before "### Go to Page command"):

```markdown
**Scope note (added during implementation planning):** DOCX import goes
through Pandoc or MarkItDown conversion to Markdown text
(`quill/io/structured.py:_read_docx`), neither of which preserves explicit
page-break positions in the converted text. Detecting hard page breaks
would require a separate python-docx scan with no reliable way to map
those positions into the converted text. Track B therefore ships for
**PDF only** in the first implementation; DOCX stays on the Track A
estimate. Real DOCX pagination is left as a follow-up, matching this
issue's own original recommendation to treat exact-format pagination as
separable, incremental work.
```

- [ ] **Step 2: Add the PRD subsection**

In `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`, find the status bar / navigation section (search for `"document_progress"` or the status bar items list to locate it) and add a new subsection:

```markdown
#### Page indicator (#872)

Every document shows a `Page` status bar cell, on by default, positioned
next to the line/column position cell. For PDFs, it reports an exact page
count and current page, derived from page boundaries preserved as
form-feed characters at import (`quill/io/pdf.py`), reusing
`quill/core/navigation.py`'s `page_starts()`/`page_start_for_number()`.
For every other format (plain text, Markdown, DOCX), it reports an
**estimate** derived from word count (`page_estimate_words_per_page`,
default 300, Preferences > Navigation and QUILL Key) -- this is explicitly
not an exact science, and the cell's text always says so ("~N of ~M
(estimated)"), never silently presenting an estimate as a fact. BRF/braille
documents keep their own richer page system (`"braille"` status cell);
the generic `"page"` cell is suppressed whenever that one is active. Go To
Page (`Ctrl+Shift+G`) is track-aware the same way: exact jump for
form-feed-bearing documents, estimated jump (word-count-derived) otherwise,
with the prompt text stating which one is in effect.
```

- [ ] **Step 3: Add the user guide subsection**

In `docs/user guide/userguide.md`, find the Status Bar section (search for an existing heading like `### Status bar cells` or similar; if none exists, add this as a new `###`-level subsection near the other status-bar-cell documentation) and add:

```markdown
### Page indicator

QUILL shows a **Page** cell in the status bar for every document, on by
default, right next to your line/column position.

For PDFs, this is an exact count: QUILL knows the real page boundaries
from the file itself, so it reads, for example, "3 of 12."

For everything else -- plain text, Markdown, and most Word documents --
there is no such thing as a real "page" until you print or export: page
breaks depend on your font, margins, and paper size, none of which QUILL
tracks while you're writing. So for these documents, the Page cell shows
an **estimate** based on word count, clearly marked as such: "~3 of ~12
(estimated)." The tilde and the word "estimated" are always there together
-- if you ever see a page number without them, it's a real count; if you
see them, it's QUILL's best guess, not a promise.

You can tune the estimate's word-per-page basis in **Preferences >
Navigation and QUILL Key > Estimated words per page** (default 300, range
150-600) if your writing runs noticeably longer or shorter per page than
the default assumes.

**Go To Page** (`Ctrl+Shift+G`, also reachable by pressing Enter on the
Page cell) jumps to a page number. For PDFs this is exact; for everything
else, it jumps to QUILL's best estimate of where that page would fall --
the prompt tells you which kind of jump you're about to make.

Braille (BRF) documents keep their own, more detailed page system (see
Braille Mode above) and do not show this generic Page cell.
```

- [ ] **Step 4: Add the CHANGELOG entry**

In `CHANGELOG.md`, in the "0.9.0 Beta 2" section, add this bullet immediately after the intro paragraph (before the existing `#886` bullet):

```markdown
- **Every document now shows a Page indicator (#872).** A beta tester asked whether QUILL could show real page numbers. It can, for PDFs -- QUILL now preserves each PDF's real page boundaries at import, so the status bar's new **Page** cell (on by default, right next to your line/column position) reports an exact "3 of 12," and `Ctrl+Shift+G` (Go To Page) jumps exactly. For plain text, Markdown, and Word documents -- where a "page" has no real meaning until you print or export -- the same cell shows a clearly-labeled **estimate** based on word count instead: "~3 of ~12 (estimated)." The tilde and the word "estimated" always appear together, so an estimate is never mistaken for a fact; tune the words-per-page assumption in Preferences > Navigation and QUILL Key. Braille documents are unaffected -- they keep their own, richer page system.
```

- [ ] **Step 5: Add the release notes entry**

In `docs/release notes/release0.9.0-beta2.md`:

First, soften the "no new headline features" sentence in the intro. Change:

```markdown
Keeping the promise made at Beta 1, there are **no new headline features here** —
just your reports, turned into fixes and polish, especially around getting the optional pieces you want.
```

to:

```markdown
Keeping the promise made at Beta 1, this is overwhelmingly your reports, turned into fixes and polish, especially around getting the optional pieces you want — with **one exception**: a page indicator, because enough of you asked for it that it couldn't wait.
```

Then add a new section right after the "Getting the extras you want, reimagined" section (before "## A simpler installer, and a lighter one"):

```markdown
## A page number, honestly presented

A tester asked directly: "Are we going to be able to see proper page
numbers with QUILL?" Now every document shows one, in the status bar,
on by default, right next to your line/column position.

- **PDFs get a real page count.** QUILL now preserves each PDF's actual
  page boundaries when you open it, so you see an exact "3 of 12" and
  `Ctrl+Shift+G` (Go To Page) jumps exactly.
- **Everything else gets an honest estimate.** Plain text, Markdown, and
  Word documents don't have a real "page" until you print or export --
  it depends on font, margins, and paper size, none of which QUILL
  tracks while you write. So for these, the same cell shows "~3 of ~12
  (estimated)" -- the tilde and the word "estimated" always travel
  together, on purpose, so you never mistake a guess for a fact. Tune
  the words-per-page assumption in Preferences > Navigation and QUILL Key
  if your pages run long or short.
- Braille documents are untouched -- they keep their own, richer page
  system.
```

- [ ] **Step 6: Verify docs build cleanly**

Run: `python -m pytest tests/unit -k "docs or changelog" -v` (best-effort sanity check; if no matching tests exist, this step is a no-op confirmation that no doc-format gate broke)

- [ ] **Step 7: Commit**

```bash
git add "docs/superpowers/specs/2026-07-07-page-indicator-design.md" \
        "docs/Product Requirement Documents and Specifications/QUILL-PRD.md" \
        "docs/user guide/userguide.md" \
        CHANGELOG.md \
        "docs/release notes/release0.9.0-beta2.md"
git commit -m "docs: document the page indicator across PRD, user guide, changelog, release notes (#872)"
```

---

### Task 8: Full regression pass and close #872

**Files:** none (verification only)

- [ ] **Step 1: Run every touched test file together**

```bash
pytest tests/unit/core/test_navigation.py tests/unit/core/test_settings.py \
       tests/unit/ui/test_main_frame_statusbar_context.py \
       tests/unit/ui/test_main_frame_navigation.py \
       tests/unit/io/test_pdf.py -v
```
Expected: PASS, all tests.

- [ ] **Step 2: Run the module size budget gate**

```bash
pytest tests/unit/tools/test_module_size_budget.py -q
```
Expected: PASS (or already fixed via the rebaseline notes in Tasks 3/5).

- [ ] **Step 3: Run the smoke subset**

```bash
pytest -m smoke -q
```
Expected: PASS.

- [ ] **Step 4: Run ruff over every touched file**

```bash
ruff check quill/core/navigation.py quill/core/settings.py quill/core/settings_specs.py \
           quill/core/settings_normalizers.py quill/ui/main_frame.py \
           quill/ui/main_frame_statusbar.py quill/io/pdf.py
ruff format --check quill/core/navigation.py quill/core/settings.py quill/core/settings_specs.py \
           quill/core/settings_normalizers.py quill/ui/main_frame.py \
           quill/ui/main_frame_statusbar.py quill/io/pdf.py
```
Expected: all clean.

- [ ] **Step 5: Push the branch and open a PR**

```bash
git push -u origin feature/page-indicator
gh pr create --title "Add an always-on page indicator (#872)" --body "$(cat <<'EOF'
## Summary
- Exact page count for PDFs (real page boundaries preserved at import as
  form feeds, reusing existing navigation.py machinery)
- Clearly-labeled estimated page count (word-count based) for everything
  else -- never presented as exact
- Page indicator visible by default in the status bar, next to
  line/column; suppressed for BRF/braille documents
- Track-aware Go To Page (Ctrl+Shift+G)
- PRD, user guide, CHANGELOG, and Beta 2 release notes updated

Closes #872.

## Test plan
- [x] All new and existing unit tests pass
- [x] Module size budget gate passes
- [x] Smoke suite passes
- [x] ruff check/format clean
EOF
)"
```

- [ ] **Step 6: Wait for CI, then close #872 once merged**

Once CI is green and the PR is merged to `main`:

```bash
gh issue close 872 --comment "Shipped: an always-on Page status bar cell (exact for PDF, clearly-labeled estimate for everything else) plus a track-aware Go To Page. Documented in the PRD, user guide, CHANGELOG, and 0.9.0 Beta 2 release notes."
```
