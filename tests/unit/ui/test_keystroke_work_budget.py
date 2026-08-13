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


class _CallLater:
    """A wx.CallLater stand-in that fires only when time is advanced past it."""

    def __init__(self, clock: _Clock, delay_ms: int, target) -> None:
        self._clock = clock
        self.due_at = clock.now + delay_ms
        self.target = target
        self.stopped = False

    def Stop(self) -> None:  # noqa: N802 - wx casing
        self.stopped = True


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.pending: list[_CallLater] = []

    def CallLater(self, delay_ms: int, target):  # noqa: N802 - wx casing
        timer = _CallLater(self, delay_ms, target)
        self.pending.append(timer)
        return timer

    def advance(self, ms: float) -> None:
        """Move time forward, firing any timer that comes due and is not stopped."""
        target_time = self.now + ms
        while True:
            due = [t for t in self.pending if not t.stopped and t.due_at <= target_time]
            if not due:
                break
            timer = min(due, key=lambda t: t.due_at)
            self.now = timer.due_at
            self.pending.remove(timer)
            timer.target()
        self.now = target_time


def _typing_frame() -> tuple[MainFrame, _Clock, list[int]]:
    frame = MainFrame.__new__(MainFrame)
    clock = _Clock()
    runs: list[int] = []
    frame._wx = clock  # type: ignore[assignment]
    frame._deferred_edit_timer = None
    frame._run_deferred_edit_work = lambda: runs.append(1)  # type: ignore[method-assign]
    return frame, clock, runs


def _type_at(wpm: float, characters: int = 100) -> int:
    """Deferred-work runs while typing *characters* at *wpm*, through the real
    scheduler (not a model of it)."""
    frame, clock, runs = _typing_frame()
    gap_ms = 60_000.0 / (wpm * 5.0)
    for _ in range(characters):
        frame._schedule_deferred_edit_work()
        clock.advance(gap_ms)
    clock.advance(MainFrame._DEFERRED_EDIT_DELAY_MS)  # the pause after typing stops
    return len(runs)


def test_a_fast_burst_collapses_to_a_single_deferred_run() -> None:
    # 140 wpm is ~11.7 characters per second, well inside the 120 ms timer, so
    # every keystroke restarts it and the work happens once, at the end. This is
    # the case that matters: it is exactly when the UI thread cannot afford to
    # do the work once per character.
    assert _type_at(140) == 1


def test_ordinary_typing_still_runs_the_work_between_keystrokes() -> None:
    # Below ~8 characters per second the gap exceeds the timer, so the deferred
    # work runs once per keystroke -- in the gap *after* the character has been
    # handed to the screen reader, which is the point, rather than in front of
    # it. Asserted so the documentation cannot drift into claiming that ordinary
    # typing is coalesced: it is not, and it does not need to be.
    assert _type_at(60) == 100
    assert _type_at(40) == 100


def test_each_keystroke_cancels_the_pending_run() -> None:
    frame, clock, runs = _typing_frame()
    frame._schedule_deferred_edit_work()
    first = frame._deferred_edit_timer
    frame._schedule_deferred_edit_work()
    assert first.stopped is True, "a second keystroke must cancel the pending run"
    clock.advance(MainFrame._DEFERRED_EDIT_DELAY_MS)
    assert runs == [1], "only the surviving timer may fire"


def test_without_wx_the_work_runs_inline() -> None:
    # Headless tests and stub surfaces have no CallLater; the work must still
    # happen, synchronously, rather than being silently dropped.
    frame = MainFrame.__new__(MainFrame)
    runs: list[int] = []
    frame._wx = object()  # type: ignore[assignment]
    frame._run_deferred_edit_work = lambda: runs.append(1)  # type: ignore[method-assign]
    frame._schedule_deferred_edit_work()
    assert runs == [1]
