"""Behavior tests for QuillFindDialog (#1327 F1) with real widgets and a stub host.

The dialog's contract is that every action is driven through the FindHost
callbacks, so a buffer-backed stub exercises find/replace/count/peek exactly as
the editor would experience them — including the announcements, which ARE the
user interface for a screen-reader user.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.find_dialog import FindHost, QuillFindDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Buffer:
    """A minimal editor stand-in the FindHost callbacks close over."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.caret = 0
        self.selections: list[tuple[int, int]] = []
        self.announced: list[str] = []

    def host(self) -> FindHost:
        def replace_range(start: int, end: int, value: str) -> None:
            self.text = self.text[:start] + value + self.text[end:]

        return FindHost(
            get_text=lambda: self.text,
            get_insertion_point=lambda: self.caret,
            select_range=lambda s, e: self.selections.append((s, e)),
            replace_range=replace_range,
            announce=self.announced.append,
            is_read_only=lambda: False,
        )


def _make(wx_app, text: str, *, replace: bool = False) -> tuple[_Buffer, QuillFindDialog, wx.Frame]:
    frame = wx.Frame(None)
    buffer = _Buffer(text)
    dialog = QuillFindDialog(frame, buffer.host(), wx=wx, replace=replace)
    return buffer, dialog, frame


def _teardown(dialog: QuillFindDialog, frame: wx.Frame) -> None:
    dialog.close()
    frame.Destroy()


def test_find_selects_and_announces_context(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "The quick brown fox. The slow fox.")
    try:
        dialog.query.SetValue("fox")
        dialog.find(backwards=False)
        assert buffer.selections[-1] == (16, 19)
        assert "fox" in buffer.announced[-1]
        dialog.find(backwards=False)
        assert buffer.selections[-1] == (30, 33)
    finally:
        _teardown(dialog, frame)


def test_find_wraps_and_says_so(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "alpha beta alpha")
    try:
        buffer.caret = 12  # past the last match's start? no — inside final 'alpha'
        dialog.query.SetValue("beta")
        dialog.find(backwards=False)
        assert buffer.announced[-1].startswith("Wrapped past the end.")
    finally:
        _teardown(dialog, frame)


def test_extended_mode_finds_a_tab(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "col1\tcol2")
    try:
        dialog.mode.SetSelection(1)
        dialog.query.SetValue(r"\t")
        dialog.find(backwards=False)
        assert buffer.selections[-1] == (4, 5)
    finally:
        _teardown(dialog, frame)


def test_count_announces_number(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "a b a b a")
    try:
        dialog.query.SetValue("a")
        dialog.announce_count()
        assert buffer.announced[-1] == "3 matches"
    finally:
        _teardown(dialog, frame)


def test_replace_current_uses_range_replacement(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "colour and colour", replace=True)
    try:
        dialog.query.SetValue("colour")
        dialog.replace_with.SetValue("color")
        dialog.replace_current()
        assert buffer.text == "color and colour"
        assert "Replaced 'colour' with 'color'" in buffer.announced[-1]
    finally:
        _teardown(dialog, frame)


def test_replace_everywhere_handles_all_matches(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "aa bb aa bb aa", replace=True)
    try:
        dialog.query.SetValue("aa")
        dialog.replace_with.SetValue("XX")
        dialog.replace_everywhere()
        assert buffer.text == "XX bb XX bb XX"
        assert buffer.announced[-1].startswith("Replaced 3 occurrences")
    finally:
        _teardown(dialog, frame)


def test_read_only_guard_blocks_replace(wx_app) -> None:
    frame = wx.Frame(None)
    buffer = _Buffer("text text")
    host = buffer.host()
    host.is_read_only = lambda: True  # type: ignore[method-assign]
    dialog = QuillFindDialog(frame, host, wx=wx, replace=True)
    try:
        dialog.query.SetValue("text")
        dialog.replace_with.SetValue("other")
        dialog.replace_current()
        assert buffer.text == "text text"
        assert buffer.announced[-1] == "Document is read-only"
    finally:
        _teardown(dialog, frame)


def test_peek_advances_without_committing(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "x one x two x three")
    try:
        dialog.query.SetValue("x")
        dialog.peek(backwards=False)
        first = buffer.selections[-1]
        dialog.peek(backwards=False)
        second = buffer.selections[-1]
        assert first != second, "each peek must advance"
        assert dialog._last_match is None, "peeks never commit a match"
    finally:
        _teardown(dialog, frame)


def test_no_match_announced_plainly(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "nothing here")
    try:
        dialog.query.SetValue("zebra")
        dialog.find(backwards=False)
        assert buffer.announced[-1] == 'No matches for "zebra"'
        assert buffer.selections == []
    finally:
        _teardown(dialog, frame)


def test_direction_group_is_a_labeled_radiobox(wx_app) -> None:
    """The report that started #1327: the group name must be announceable."""
    _buffer, dialog, frame = _make(wx_app, "text")
    try:
        assert isinstance(dialog.direction, wx.RadioBox)
        assert dialog.direction.GetLabel() == "Direction"
    finally:
        _teardown(dialog, frame)


def test_set_action_switches_replace_visibility(wx_app) -> None:
    _buffer, dialog, frame = _make(wx_app, "text", replace=False)
    try:
        assert not dialog.replace_with.IsShown()
        dialog.set_action(replace=True)
        assert dialog.replace_with.IsShown()
        assert dialog.dialog.GetTitle() == "Replace"
    finally:
        _teardown(dialog, frame)


class _KeyEvent:
    """Minimal EVT_CHAR_HOOK stand-in for exercising ``_on_dialog_key``."""

    def __init__(
        self, code: int, *, ctrl: bool = True, alt: bool = False, shift: bool = False
    ) -> None:
        self._code, self._ctrl, self._alt, self._shift = code, ctrl, alt, shift
        self.skipped = False

    def ControlDown(self) -> bool:
        return self._ctrl

    def AltDown(self) -> bool:
        return self._alt

    def ShiftDown(self) -> bool:
        return self._shift

    def GetKeyCode(self) -> int:
        return self._code

    def Skip(self) -> None:
        self.skipped = True


def test_incremental_count_does_not_repeat_identical(wx_app) -> None:
    """An unchanged spoken count is not re-announced (desktop-a11y review #5)."""
    buffer, dialog, frame = _make(wx_app, "a b a b a")
    try:
        dialog.query.SetValue("a")
        dialog._announce_incremental()
        dialog._announce_incremental()
        assert buffer.announced.count("3 matches") == 1
    finally:
        _teardown(dialog, frame)


def test_ctrl_h_switches_to_replace_while_open(wx_app) -> None:
    """Ctrl+H switches to Replace in place; a modeless dialog never receives the
    frame accelerator, so it must be self-handled (desktop-a11y review #3)."""
    _buffer, dialog, frame = _make(wx_app, "text", replace=False)
    try:
        assert not dialog.replace_with.IsShown()
        event = _KeyEvent(ord("H"))
        dialog._on_dialog_key(event)
        assert dialog.replace_with.IsShown()
        assert not event.skipped
    finally:
        _teardown(dialog, frame)


def test_ctrl_f_refocuses_query_while_open(wx_app) -> None:
    _buffer, dialog, frame = _make(wx_app, "text")
    try:
        event = _KeyEvent(ord("F"))
        dialog._on_dialog_key(event)
        assert not event.skipped, "Ctrl+F is handled in-dialog, not passed through"
    finally:
        _teardown(dialog, frame)


def test_unrelated_ctrl_key_is_passed_through(wx_app) -> None:
    """Ctrl+A (select-all) and friends must still reach the focused control."""
    _buffer, dialog, frame = _make(wx_app, "text")
    try:
        event = _KeyEvent(ord("A"))
        dialog._on_dialog_key(event)
        assert event.skipped
    finally:
        _teardown(dialog, frame)


def test_find_previous_repeats_progress_backwards(wx_app) -> None:
    # Regression: anchoring a backwards repeat at the last match's END re-found
    # the same match forever; it must anchor at its START and step back.
    buffer, dialog, frame = _make(wx_app, "fox one fox two fox")
    try:
        buffer.caret = len(buffer.text)
        dialog.query.SetValue("fox")
        dialog.find(backwards=True)
        assert buffer.selections[-1] == (16, 19)
        dialog.find(backwards=True)
        assert buffer.selections[-1] == (8, 11)
        dialog.find(backwards=True)
        assert buffer.selections[-1] == (0, 3)
    finally:
        _teardown(dialog, frame)


def test_peek_reverse_steps_back_not_repeat(wx_app) -> None:
    buffer, dialog, frame = _make(wx_app, "fox one fox two fox")
    try:
        dialog.query.SetValue("fox")
        dialog.peek(backwards=False)
        assert buffer.selections[-1] == (0, 3)
        dialog.peek(backwards=False)
        assert buffer.selections[-1] == (8, 11)
        dialog.peek(backwards=True)
        assert buffer.selections[-1] == (0, 3)
    finally:
        _teardown(dialog, frame)


def test_successful_find_syncs_global_repeat_state(wx_app) -> None:
    remembered: list[tuple[str, bool, bool]] = []
    frame = wx.Frame(None)
    buffer = _Buffer("alpha beta")
    host = buffer.host()
    host.remember_query = lambda q, c, w: remembered.append((q, c, w))
    dialog = QuillFindDialog(frame, host, wx=wx)
    try:
        dialog.query.SetValue("beta")
        dialog.case.SetValue(True)
        dialog.find(backwards=False)
        assert remembered == [("beta", True, False)]
    finally:
        _teardown(dialog, frame)
