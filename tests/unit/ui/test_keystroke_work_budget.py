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
    frame._refresh_title_bar = lambda: None  # type: ignore[method-assign]
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


def test_deferred_work_reads_the_buffer_never() -> None:
    # Round 3: the deferred pass uses document.text -- the exact string the
    # sync path stored in set_text, which nothing can have changed since (any
    # change fires EVT_TEXT and restarts the timer). Zero marshals.
    source = inspect.getsource(MainFrame._run_deferred_edit_work)
    assert "GetValue()" not in source
    assert "_document_text_for_display()" in source


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


# --------------------------------------------------------------------------- #
# Round 2 (re-examination): costs the first budget missed
# --------------------------------------------------------------------------- #


def test_typing_a_letter_never_opens_the_clipboard() -> None:
    """The abbreviation hook fetched the clipboard on EVERY keystroke.

    Opening the Windows clipboard is a cross-process synchronization point --
    a clipboard manager or a screen reader polling the clipboard contends for
    the same lock, and clipboard_retry can hold the UI thread up to ~200 ms.
    It must now be fetched lazily: only once an abbreviation has matched and
    its expansion actually references ${clipboard}.
    """
    frame = MainFrame.__new__(MainFrame)
    editor = _Editor("hello worl")
    fetches: list[int] = []
    frame.editor = editor  # type: ignore[assignment]
    frame._pending_undo = None
    frame._abbreviation_library = type("L", (), {"abbreviations": []})()
    frame._get_clipboard_text_for_abbreviation = lambda: fetches.append(1) or ""  # type: ignore[method-assign]
    # An ordinary letter: not a trigger character, nothing can match.
    assert frame._expand_abbreviation_if_match("hello worl") is False
    assert fetches == [], "a plain letter keystroke must not touch the clipboard"
    # A trigger character with no matching abbreviation: still no fetch.
    editor2 = _Editor("hello ")
    frame.editor = editor2  # type: ignore[assignment]
    assert frame._expand_abbreviation_if_match("hello ") is False
    assert fetches == [], "a non-matching trigger must not touch the clipboard"


def test_clipboard_is_fetched_only_for_matches_that_want_it() -> None:
    from quill.core.abbreviations import Abbreviation, AbbreviationLibrary, try_expand

    fetches: list[int] = []

    def provider() -> str:
        fetches.append(1)
        return "PASTED"

    plain = AbbreviationLibrary(
        version=1,
        abbreviations=[Abbreviation(id="a1", abbreviation="sig", expansion="Best regards")],
    )
    match = try_expand("sig ", 4, plain, clipboard_provider=provider)
    assert match is not None and match.resolved_text == "Best regards"
    assert fetches == [], "an expansion without ${clipboard} must not fetch it"

    clippy = AbbreviationLibrary(
        version=1,
        abbreviations=[Abbreviation(id="a2", abbreviation="pc", expansion="see: ${clipboard}")],
    )
    match = try_expand("pc ", 3, clippy, clipboard_provider=provider)
    assert match is not None and match.resolved_text == "see: PASTED"
    assert fetches == [1], "a ${clipboard} expansion fetches exactly once"


def test_typing_path_refreshes_the_title_bar_without_the_statusbar() -> None:
    """_refresh_title drags a full statusbar refresh -- several O(n) buffer
    reads -- along with it. The synchronous typing path must use the title-only
    variant; the statusbar catches up in the deferred pass."""
    source = inspect.getsource(MainFrame._sync_editor_change)
    assert "_refresh_title_bar()" in source
    assert "_refresh_title()" not in source
    title_bar = inspect.getsource(MainFrame._refresh_title_bar)
    assert "_refresh_statusbar" not in title_bar
    # And the deferred pass is where the statusbar catches up.
    assert "_refresh_statusbar()" in inspect.getsource(MainFrame._run_deferred_edit_work)


def test_caret_activity_coalesces_its_statusbar_refresh() -> None:
    """EVT_KEY_UP fires per keystroke; a synchronous refresh there was a second
    full set of O(n) statusbar reads per character."""
    source = inspect.getsource(MainFrame._on_editor_caret_activity)
    assert "_schedule_statusbar_refresh()" in source
    assert "self._refresh_statusbar()" not in source


def test_statusbar_cells_read_the_document_not_the_control() -> None:
    """Display cells must use the document's own string (zero marshals), not
    another GetValue() round trip per cell."""
    frame = MainFrame.__new__(MainFrame)
    editor = _Editor("one two three")
    frame.editor = editor  # type: ignore[assignment]
    frame.document = type("D", (), {"text": "one two three"})()
    stats = frame._statusbar_document_stats()
    assert stats is not None and stats.words == 3
    assert editor.get_value_calls == 0, (
        "statusbar stats must come from document.text, not a buffer marshal"
    )
    # Stub frames without a document still work, via the editor fallback.
    frame.document = None  # type: ignore[assignment]
    assert frame._document_text_for_display() == "one two three"
    assert editor.get_value_calls == 1


def test_title_bar_native_calls_are_skipped_when_unchanged() -> None:
    """SetTitle fires MSAA/UIA name-change events; retitling the frame to the
    same string on every keystroke is announcement noise and native churn."""

    class _Frame:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def SetTitle(self, title: str) -> None:  # noqa: N802 - wx casing
            self.calls.append(title)

    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()  # type: ignore[assignment]
    frame.document = type("D", (), {"text": "x", "name": "notes.md", "path": None})()
    frame.settings = type("S", (), {"title_bar_path_mode": "name"})()
    frame._active_tab_index = -1
    frame._dirty_title_suffix = lambda: " *"  # type: ignore[method-assign]
    frame._title_subject = lambda: "notes.md"  # type: ignore[method-assign]
    frame._refresh_title_bar()
    frame._refresh_title_bar()
    frame._refresh_title_bar()
    assert len(frame.frame.calls) == 1, "an unchanged title must not be re-set"


# --------------------------------------------------------------------------- #
# Round 3: the costs round 2 missed
# --------------------------------------------------------------------------- #


def test_quiet_status_does_not_recompute_the_statusbar_synchronously() -> None:
    """_set_status_quiet runs per keystroke; its synchronous _refresh_statusbar
    call quietly undid round 2's removal one line below where round 2 did it."""
    from quill.ui.main_frame_statusbar import StatusBarMixin

    source = inspect.getsource(StatusBarMixin._set_status_quiet)
    assert "_schedule_statusbar_refresh()" in source
    assert "self._refresh_statusbar()" not in source


def test_document_stats_are_memoized_by_revision() -> None:
    frame = MainFrame.__new__(MainFrame)
    editor = _Editor("alpha beta gamma")
    frame.editor = editor  # type: ignore[assignment]
    frame.document = type("D", (), {"text": "alpha beta gamma", "revision": 7})()
    first = frame._statusbar_document_stats()
    second = frame._statusbar_document_stats()
    assert first is second, "same revision must return the cached stats object"
    frame.document.revision = 8
    frame.document.text = "alpha beta gamma delta"
    third = frame._statusbar_document_stats()
    assert third is not first and third.words == 4


def test_spell_hint_inspects_one_word_not_the_rest_of_the_document() -> None:
    """A clean document was spell-checked caret-to-end per pause, for an answer
    the caller discarded. The bounded form looks at exactly one word."""
    from quill.core.spellcheck import misspelling_at

    known = {"alpha", "beta"}
    text = "alpha xzqj " + "beta " * 10_000
    # A misspelled word starting exactly at the position is found...
    hit = misspelling_at(text, 6, known)
    assert hit is not None and hit.word == "xzqj"
    # ...a known word starting there answers None without scanning on...
    assert misspelling_at("alpha xzqj", 0, known) is None
    # ...and a position mid-word (tail fragment) is not a word start.
    assert misspelling_at(text, 8, known) is None


def test_bounded_and_unbounded_spell_scan_agree_at_the_caret() -> None:
    from quill.core.spellcheck import misspelling_at, next_misspelling

    known = {"one", "two", "three"}
    for text in ("one wrng two", "wrng one", "one two wrng", "one  two", ""):
        for position in range(len(text) + 1):
            unbounded = next_misspelling(text, position - 1, known)
            expected = unbounded if unbounded is not None and unbounded.start == position else None
            assert misspelling_at(text, position, known) == expected, (text, position)
