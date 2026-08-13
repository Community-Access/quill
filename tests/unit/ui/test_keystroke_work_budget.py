"""One buffer read per keystroke, and nothing heavy on the typing path (#1346).

The reported symptom -- "long pauses between text entry and reporting from
either NVDA and JAWS", spaces dropped so words run together -- was a blocked
message pump, not a screen-reader misconfiguration. ``_sync_editor_change`` had
accumulated eleven callers, three or four of which each did a full
``GetValue()``; on a multiline ``wx.TextCtrl`` that is a complete copy of the
document across the native boundary, per character.

This is the budget test that stops it happening again. It is deliberately a
source + call-count contract rather than a timing test: a wall-clock assertion
would be flaky in CI and would not say *what* regressed.
"""

from __future__ import annotations

import inspect

from quill.ui.main_frame import MainFrame


class _Editor:
    """A text control that counts how often its buffer is marshalled out."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.get_value_calls = 0

    def GetValue(self) -> str:  # noqa: N802 - wx casing
        self.get_value_calls += 1
        return self._text

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802 - wx casing
        return (0, 0)

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx casing
        return len(self._text)


class _Settings:
    snippet_trigger_expansion = True
    abbreviation_expansion = False
    spellcheck_as_you_type = True
    persistent_undo = True
    auto_side_preview = True
    browse_mode_preload_cache = True


class _Document:
    def __init__(self) -> None:
        self.text = ""
        self.modified = False

    def set_text(self, value: str) -> None:
        self.text = value
        self.modified = True


def _frame(text: str) -> tuple[MainFrame, _Editor, list[str]]:
    frame = MainFrame.__new__(MainFrame)
    editor = _Editor(text)
    deferred: list[str] = []
    frame.editor = editor  # type: ignore[assignment]
    frame.document = _Document()  # type: ignore[assignment]
    frame.settings = _Settings()  # type: ignore[assignment]
    frame._abbreviation_expansion_guard = False
    frame._snippet_expansion_guard = False
    frame._suspend_persistent_undo = False
    frame._browse_navigation_cache = object()
    frame._refresh_title = lambda: None  # type: ignore[method-assign]
    frame._set_status_quiet = lambda _m: None  # type: ignore[method-assign]
    frame._schedule_deferred_edit_work = lambda: deferred.append("scheduled")  # type: ignore[method-assign]
    frame._expand_snippet_trigger_if_match = lambda _text=None: False  # type: ignore[method-assign]
    return frame, editor, deferred


def test_one_get_value_per_text_change() -> None:
    frame, editor, deferred = _frame("x" * 500_000)
    frame._on_text_changed(object())
    assert editor.get_value_calls == 1, (
        "Each EVT_TEXT must marshal the buffer out of the native control exactly "
        "once (#1346). A new caller in the typing path needs the text passed to "
        "it, not another GetValue()."
    )
    assert deferred == ["scheduled"]
    assert frame.document.text == "x" * 500_000


def test_expansion_checks_reuse_the_callers_buffer() -> None:
    # Both expansion hooks take the already-read text; neither may re-read it.
    for method in (
        MainFrame._expand_snippet_trigger_if_match,
        MainFrame._expand_abbreviation_if_match,
    ):
        parameters = list(inspect.signature(method).parameters)
        assert "text" in parameters, f"{method.__qualname__} must accept the caller's buffer"


def test_deferred_consumers_all_accept_the_shared_buffer() -> None:
    for method in (
        MainFrame._schedule_browse_prewarm,
        MainFrame._announce_spellcheck_hint,
        MainFrame._refresh_side_preview,
    ):
        assert "text" in inspect.signature(method).parameters, (
            f"{method.__qualname__} must accept the deferred pass's single read"
        )


def test_only_the_essential_work_is_synchronous() -> None:
    """The keystroke path may not do preview/spell/menu/autosave work inline."""
    source = "\n".join(
        line
        for line in inspect.getsource(MainFrame._sync_editor_change).splitlines()
        if not line.strip().startswith("#")
    )
    for banned in (
        "_refresh_side_preview",
        "_refresh_browser_preview",
        "_announce_spellcheck_hint",
        "_maybe_autosave",
        "_refresh_contextual_menu_items",
        "_schedule_language_detection",
        "_refresh_intellisense_popup",
    ):
        assert banned not in source, (
            f"{banned} runs on every keystroke again (#1346); it belongs in "
            "_run_deferred_edit_work behind the coalescing timer."
        )
    assert "_schedule_deferred_edit_work" in source


def test_deferred_work_reads_the_buffer_once() -> None:
    source = inspect.getsource(MainFrame._run_deferred_edit_work)
    assert source.count("GetValue()") == 1


def test_autosave_writes_off_the_ui_thread() -> None:
    """The autosave disk write is handed to the task manager, not the UI thread."""
    source = inspect.getsource(MainFrame._write_autosave_snapshot)
    assert "_task_manager" in source
    assert "submit(" in source
    worker = inspect.getsource(MainFrame._autosave_worker)
    # Nothing in the worker may touch wx: it runs on a pool thread.
    assert "self.editor" not in worker
    assert "_set_status" not in worker
